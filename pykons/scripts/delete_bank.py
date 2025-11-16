#!/usr/bin/env python3
"""
Delete or clean banks on the Perkons HD-01 SD card.

This script safely removes banks from the SD card with strict validation
and confirmation requirements.

Special handling for source banks:
- Banks 01 and 02 are protected and cannot be deleted
- For bank 01: "clean bank 01" removes kits 32-63 only (keeps 00-31)
- For bank 02: "clean bank 02" removes kits 00-31 only (keeps 32-63)
- All other banks: "delete bank XX" removes the entire bank

Safety features:
- Requires exact confirmation text match
- Validates bank format (XX) and range (00-63)
- Prevents deletion of source banks 01 and 02
- Shows what will be deleted before confirmation

Usage:
    # Delete a regular bank (will prompt for confirmation)
    pykons-delete-bank --bank 10

    # Clean source bank 01 (removes kits 32-63, keeps 00-31)
    pykons-delete-bank --bank 01

    # Clean source bank 02 (removes kits 00-31, keeps 32-63)
    pykons-delete-bank --bank 02

    # Use custom SD card path
    pykons-delete-bank --bank 10 --sd-path /Volumes/PERKONS
"""

import argparse
import os
import sys
from pathlib import Path


# SD Card Configuration
DEFAULT_SD_PATH = '/Volumes/Untitled'
SOURCE_BANKS = ['01', '02']


def check_sd_card_mounted(sd_path):
    """
    Check if the SD card is mounted at the expected path.

    Args:
        sd_path: Expected mount point of SD card

    Returns:
        True if SD card is mounted, False otherwise
    """
    return os.path.exists(sd_path) and os.path.isdir(sd_path)


def get_banks_directory(sd_path):
    """
    Get the BANKS directory path on the SD card.

    Args:
        sd_path: SD card mount point

    Returns:
        Path object for BANKS directory
    """
    return Path(sd_path) / 'BANKS'


def normalize_bank_id(bank_input):
    """
    Normalize bank ID input to proper format.

    Args:
        bank_input: Bank ID/number (e.g., "3", "03", "10")

    Returns:
        Normalized bank ID string (2 digits)

    Raises:
        ValueError: If bank is out of range 0-63
    """
    try:
        bank_num = int(bank_input)
        if not 0 <= bank_num <= 63:
            raise ValueError(f"Bank number must be between 0 and 63, got {bank_num}")
        return f"{bank_num:02d}"
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Bank must be a number between 0-63, got '{bank_input}'")
        raise


def get_bank_info(sd_path, bank_id):
    """
    Get information about a bank.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID (e.g., '01', '10')

    Returns:
        Tuple of (exists: bool, kit_files: list, total_size: int)
    """
    bank_path = get_banks_directory(sd_path) / bank_id

    if not bank_path.exists():
        return False, [], 0

    kits_path = bank_path / 'KITS'
    if not kits_path.exists():
        return True, [], 0

    kit_files = sorted(list(kits_path.glob('*.KIT')) + list(kits_path.glob('*.kit')))
    total_size = sum(f.stat().st_size for f in kit_files if f.is_file())

    return True, kit_files, total_size


def get_kit_ranges_for_cleaning(bank_id):
    """
    Get the kit ranges that should be deleted when cleaning a source bank.

    Args:
        bank_id: Bank ID ('01' or '02')

    Returns:
        Tuple of (keep_range: range, delete_range: range, description: str)
    """
    if bank_id == '01':
        # Bank 01: Keep 00-31, delete 32-63
        return (range(0, 32), range(32, 64), "kits 32-63")
    elif bank_id == '02':
        # Bank 02: Keep 32-63, delete 00-31
        return (range(0, 32), range(32, 64), "kits 00-31")
    else:
        return (None, None, None)


def delete_entire_bank(sd_path, bank_id):
    """
    Delete an entire bank directory.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID to delete

    Returns:
        Tuple of (success: bool, message: str)
    """
    import shutil

    bank_path = get_banks_directory(sd_path) / bank_id

    if not bank_path.exists():
        return True, "Bank does not exist (nothing to delete)"

    try:
        shutil.rmtree(bank_path)
        return True, f"Successfully deleted bank {bank_id}"
    except Exception as e:
        return False, f"Failed to delete bank: {e}"


def clean_source_bank(sd_path, bank_id):
    """
    Clean a source bank by removing specific kit ranges.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID ('01' or '02')

    Returns:
        Tuple of (success: bool, message: str, deleted_count: int)
    """
    keep_range, delete_range, description = get_kit_ranges_for_cleaning(bank_id)

    if keep_range is None:
        return False, "Invalid bank ID for cleaning", 0

    kits_path = get_banks_directory(sd_path) / bank_id / 'KITS'

    if not kits_path.exists():
        return True, f"Bank {bank_id} has no KITS directory (nothing to clean)", 0

    deleted_count = 0
    errors = []

    # Delete kits in the delete range
    for kit_num in delete_range:
        kit_filename = f"{kit_num:02d}.KIT"
        kit_path = kits_path / kit_filename

        if kit_path.exists():
            try:
                kit_path.unlink()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete {kit_filename}: {e}")

    if errors:
        error_msg = "\n  ".join(errors)
        return False, f"Partial clean - some errors occurred:\n  {error_msg}", deleted_count

    return True, f"Successfully cleaned bank {bank_id} ({description} removed)", deleted_count


def main():
    parser = argparse.ArgumentParser(
        description='Delete or clean banks on Perkons SD card',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete bank 10 (requires confirmation "delete bank 10")
  %(prog)s --bank 10

  # Clean bank 01 (removes kits 32-63, keeps 00-31)
  %(prog)s --bank 01

  # Clean bank 02 (removes kits 00-31, keeps 32-63)
  %(prog)s --bank 02

  # Use custom SD card path
  %(prog)s --bank 10 --sd-path /Volumes/PERKONS

Safety:
  - Banks 01 and 02 CANNOT be deleted (only cleaned)
  - Bank 01 clean: removes kits 32-63 only (preserves source kits 00-31)
  - Bank 02 clean: removes kits 00-31 only (preserves source kits 32-63)
  - All other banks: complete deletion
  - Requires exact confirmation text match before deletion

Confirmation prompts:
  - Regular banks: "delete bank XX"
  - Source banks: "clean bank XX"

Notes:
  - SD card must be mounted at /Volumes/Untitled (or custom path)
  - Bank must be in format XX (00-63)
  - Deletion is permanent and cannot be undone
        """
    )

    parser.add_argument('--bank', required=True,
                        help='Bank number to delete/clean (0-63)')
    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')

    args = parser.parse_args()

    try:
        # Normalize bank ID
        try:
            bank_id = normalize_bank_id(args.bank)
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

        # Determine if this is a source bank
        is_source_bank = bank_id in SOURCE_BANKS
        operation = "clean" if is_source_bank else "delete"

        print(f"Perkons Bank {'Cleaner' if is_source_bank else 'Deleter'}")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print(f"Target bank: {bank_id}")
        print(f"Operation: {operation.upper()}")
        print()

        # Check SD card is mounted
        if not check_sd_card_mounted(args.sd_path):
            print(f"✗ Error: SD card not found at {args.sd_path}")
            print(f"  Please ensure the Perkons SD card is mounted.")
            print(f"\nAvailable volumes:")
            volumes = Path('/Volumes').iterdir() if Path('/Volumes').exists() else []
            for vol in volumes:
                if vol.is_dir():
                    print(f"    - {vol}")
            return 1

        print(f"✓ SD card found at {args.sd_path}")

        # Get bank info
        exists, kit_files, total_size = get_bank_info(args.sd_path, bank_id)

        if not exists:
            print(f"\n✗ Error: Bank {bank_id} does not exist on SD card")
            return 1

        # Show what will be affected
        print(f"\nBank {bank_id} information:")
        print(f"  Total kits: {len(kit_files)}")
        print(f"  Total size: {total_size:,} bytes")

        if is_source_bank:
            # Source bank - show cleaning details
            keep_range, delete_range, description = get_kit_ranges_for_cleaning(bank_id)

            # Count kits in delete range
            delete_count = 0
            delete_size = 0
            for kit_file in kit_files:
                kit_name = kit_file.stem
                try:
                    kit_num = int(kit_name)
                    if kit_num in delete_range:
                        delete_count += 1
                        delete_size += kit_file.stat().st_size
                except ValueError:
                    pass

            print(f"\n⚠ This is a SOURCE BANK - cannot be deleted, only cleaned")
            print(f"  Will REMOVE: {description} ({delete_count} kits, {delete_size:,} bytes)")
            print(f"  Will KEEP: kits {min(keep_range):02d}-{max(keep_range):02d}")

            confirmation_text = f"clean bank {bank_id}"
        else:
            # Regular bank - show deletion details
            print(f"\n⚠ WARNING: This will DELETE the entire bank")
            print(f"  All {len(kit_files)} kit(s) will be permanently removed")
            print(f"  This operation CANNOT be undone")

            confirmation_text = f"delete bank {bank_id}"

        # Require exact confirmation text
        print(f"\nTo confirm, type exactly: {confirmation_text}")
        user_input = input(f"Confirmation: ").strip()

        if user_input != confirmation_text:
            print(f"\n✗ Confirmation text does not match. Operation aborted.")
            print(f"  Expected: '{confirmation_text}'")
            print(f"  Got: '{user_input}'")
            return 1

        # Perform operation
        print(f"\n{operation.capitalize()}ing bank {bank_id}...")

        if is_source_bank:
            success, message, deleted_count = clean_source_bank(args.sd_path, bank_id)
            if success:
                print(f"\n✓ {message}")
                print(f"  Deleted {deleted_count} kit(s)")
            else:
                print(f"\n✗ {message}")
                return 1
        else:
            success, message = delete_entire_bank(args.sd_path, bank_id)
            if success:
                print(f"\n✓ {message}")
            else:
                print(f"\n✗ {message}")
                return 1

        print(f"\nOperation completed successfully.")

    except KeyboardInterrupt:
        print(f"\n\nAborted by user.")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
