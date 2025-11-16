#!/usr/bin/env python3
"""
List all non-empty banks and kits on the Perkons HD-01 SD card.

This script scans the SD card and displays all banks that contain kits,
showing kit numbers in a compact format using ranges for contiguous kits.

Output format:
  Bank XX: N kits (YY..ZZ, AA..BB)

Where contiguous kits are shown as ranges (e.g., "0..5" instead of "0,1,2,3,4,5").

Usage:
    # List all banks on SD card
    pykons-list

    # Use custom SD card path
    pykons-list --sd-path /Volumes/PERKONS

    # Show detailed information (individual kit numbers)
    pykons-list --detailed
"""

import argparse
import os
import sys
from pathlib import Path


# SD Card Configuration
DEFAULT_SD_PATH = '/Volumes/Untitled'


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


def get_kit_numbers_in_bank(sd_path, bank_id):
    """
    Get sorted list of kit numbers present in a bank.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID (e.g., '01', '10')

    Returns:
        Sorted list of kit numbers (as integers)
    """
    kits_path = get_banks_directory(sd_path) / bank_id / 'KITS'

    if not kits_path.exists():
        return []

    kit_numbers = []
    for kit_file in kits_path.glob('*.KIT'):
        try:
            # Extract kit number from filename (e.g., "05.KIT" -> 5)
            kit_num = int(kit_file.stem)
            if 0 <= kit_num <= 63:
                kit_numbers.append(kit_num)
        except ValueError:
            # Skip files with non-numeric names
            pass

    # Also check lowercase .kit extension
    for kit_file in kits_path.glob('*.kit'):
        try:
            kit_num = int(kit_file.stem)
            if 0 <= kit_num <= 63 and kit_num not in kit_numbers:
                kit_numbers.append(kit_num)
        except ValueError:
            pass

    return sorted(kit_numbers)


def format_kit_ranges(kit_numbers):
    """
    Format kit numbers as compact ranges.

    Examples:
        [0, 1, 2, 3] -> "0..3"
        [0, 1, 2, 5, 6, 10] -> "0..2, 5..6, 10"
        [5] -> "5"
        [0, 2, 4, 6] -> "0, 2, 4, 6"

    Args:
        kit_numbers: Sorted list of kit numbers

    Returns:
        String representation with ranges
    """
    if not kit_numbers:
        return ""

    ranges = []
    start = kit_numbers[0]
    end = kit_numbers[0]

    for num in kit_numbers[1:]:
        if num == end + 1:
            # Extend current range
            end = num
        else:
            # End current range and start new one
            if start == end:
                ranges.append(f"{start}")
            else:
                ranges.append(f"{start}..{end}")
            start = num
            end = num

    # Add final range
    if start == end:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}..{end}")

    return ", ".join(ranges)


def scan_banks(sd_path):
    """
    Scan all banks on the SD card and return information about non-empty banks.

    Args:
        sd_path: SD card mount point

    Returns:
        Dictionary mapping bank_id -> list of kit numbers
    """
    banks_dir = get_banks_directory(sd_path)

    if not banks_dir.exists():
        return {}

    banks_info = {}

    # Scan for all bank directories (00-63)
    for bank_num in range(64):
        bank_id = f"{bank_num:02d}"
        bank_path = banks_dir / bank_id

        if bank_path.exists() and bank_path.is_dir():
            kit_numbers = get_kit_numbers_in_bank(sd_path, bank_id)

            if kit_numbers:
                banks_info[bank_id] = kit_numbers

    return banks_info


def calculate_total_size(sd_path, bank_id):
    """
    Calculate total size of all kits in a bank.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID

    Returns:
        Total size in bytes
    """
    kits_path = get_banks_directory(sd_path) / bank_id / 'KITS'

    if not kits_path.exists():
        return 0

    total_size = 0
    for kit_file in list(kits_path.glob('*.KIT')) + list(kits_path.glob('*.kit')):
        if kit_file.is_file():
            total_size += kit_file.stat().st_size

    return total_size


def format_size(size_bytes):
    """
    Format size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.2 KB", "3.4 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def main():
    parser = argparse.ArgumentParser(
        description='List banks and kits on Perkons SD card',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all banks on SD card
  %(prog)s

  # Use custom SD card path
  %(prog)s --sd-path /Volumes/PERKONS

  # Show detailed information
  %(prog)s --detailed

Output format:
  Bank XX: N kits (YY..ZZ, AA..BB)

  Contiguous kit ranges shown as "0..5" instead of "0,1,2,3,4,5"
  Non-contiguous kits shown individually: "0..2, 5, 7..10"

Notes:
  - Only shows banks that contain at least one .KIT file
  - Scans banks 00-63
  - Shows kit counts and ranges for quick overview
        """
    )

    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--detailed', action='store_true',
                        help='Show detailed information (sizes, individual kits)')

    args = parser.parse_args()

    try:
        print(f"Perkons SD Card Contents")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
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

        print(f"✓ SD card found")

        # Check if BANKS directory exists
        banks_dir = get_banks_directory(args.sd_path)
        if not banks_dir.exists():
            print(f"\n✗ Error: BANKS directory not found at {banks_dir}")
            print(f"  The SD card may not be formatted for Perkons HD-01.")
            return 1

        print(f"✓ BANKS directory found")
        print()

        # Scan banks
        print("Scanning banks...")
        banks_info = scan_banks(args.sd_path)

        if not banks_info:
            print("\nNo banks with kits found on SD card.")
            print("The SD card appears to be empty or freshly formatted.")
            return 0

        print(f"\nFound {len(banks_info)} bank(s) with kits:")
        print("-" * 70)

        total_kits = 0
        total_size = 0

        for bank_id in sorted(banks_info.keys()):
            kit_numbers = banks_info[bank_id]
            kit_count = len(kit_numbers)
            total_kits += kit_count

            if args.detailed:
                # Detailed output with size information
                bank_size = calculate_total_size(args.sd_path, bank_id)
                total_size += bank_size

                print(f"\nBank {bank_id}:")
                print(f"  Kits: {kit_count}")
                print(f"  Size: {format_size(bank_size)}")
                print(f"  Kit numbers: {format_kit_ranges(kit_numbers)}")
            else:
                # Compact output
                kit_ranges = format_kit_ranges(kit_numbers)
                print(f"Bank {bank_id}: {kit_count:2d} kits  ({kit_ranges})")

        # Summary
        print()
        print("-" * 70)
        print(f"Total: {len(banks_info)} banks, {total_kits} kits")

        if args.detailed:
            print(f"Total size: {format_size(total_size)}")

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
