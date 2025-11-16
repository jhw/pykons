#!/usr/bin/env python3
"""
Generate random kit banks by mixing voices from source banks on SD card.

This script reads kits from banks 01 (kits 00-31) and 02 (kits 32-63) on the
Perkons SD card and generates N random kits by mixing voices. The output is
written directly to the specified bank on the SD card.

Safety features:
- Verifies SD card is mounted at /Volumes/Untitled
- Checks if output bank exists and has content
- Will not overwrite existing banks with kit data
- Validates all paths before writing

Usage:
    # Generate 32 random kits (default) to bank 10
    pykons-randomize --output-bank 10

    # Generate 8 kits to bank 15
    pykons-randomize --output-bank 15 --n 8

    # Use custom seed for reproducibility
    pykons-randomize --output-bank 20 --seed 12345

    # Use custom SD card path
    pykons-randomize --output-bank 10 --sd-path /Volumes/PERKONS
"""

import argparse
import os
import random
import sys
from pathlib import Path

# Import from parent package
from pykons import Kit


# SD Card Configuration
DEFAULT_SD_PATH = '/Volumes/Untitled'
SOURCE_BANKS = ['01', '02']  # Banks 01 and 02 contain source kits
SOURCE_KIT_RANGES = {
    '01': range(0, 32),   # Kits 00-31
    '02': range(32, 64)   # Kits 32-63
}


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


def check_bank_exists(sd_path, bank_id):
    """
    Check if a bank exists on the SD card.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID (e.g., '01', '10')

    Returns:
        True if bank directory exists, False otherwise
    """
    bank_path = get_banks_directory(sd_path) / bank_id
    return bank_path.exists()


def is_bank_empty(sd_path, bank_id):
    """
    Check if a bank is empty (no kits or only empty KITS directory).

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID (e.g., '01', '10')

    Returns:
        True if bank doesn't exist or has no .KIT files, False otherwise
    """
    bank_path = get_banks_directory(sd_path) / bank_id

    if not bank_path.exists():
        return True

    kits_path = bank_path / 'KITS'
    if not kits_path.exists():
        return True

    # Check if any .KIT files exist
    kit_files = list(kits_path.glob('*.KIT')) + list(kits_path.glob('*.kit'))
    return len(kit_files) == 0


def get_kit_count_in_bank(sd_path, bank_id):
    """
    Count the number of .KIT files in a bank.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID

    Returns:
        Number of .KIT files in the bank
    """
    kits_path = get_banks_directory(sd_path) / bank_id / 'KITS'
    if not kits_path.exists():
        return 0

    kit_files = list(kits_path.glob('*.KIT')) + list(kits_path.glob('*.kit'))
    return len(kit_files)


def validate_source_banks(sd_path):
    """
    Validate that source banks 01 and 02 exist and contain kits.

    Args:
        sd_path: SD card mount point

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    banks_dir = get_banks_directory(sd_path)

    if not banks_dir.exists():
        return False, f"BANKS directory not found on SD card at {banks_dir}"

    missing_banks = []
    empty_banks = []

    for bank_id in SOURCE_BANKS:
        bank_path = banks_dir / bank_id
        kits_path = bank_path / 'KITS'

        if not bank_path.exists():
            missing_banks.append(bank_id)
            continue

        if not kits_path.exists():
            empty_banks.append(bank_id)
            continue

        # Check if bank has kits
        kit_count = get_kit_count_in_bank(sd_path, bank_id)
        if kit_count == 0:
            empty_banks.append(bank_id)

    if missing_banks:
        return False, f"Source banks not found: {', '.join(missing_banks)}"

    if empty_banks:
        return False, f"Source banks are empty: {', '.join(empty_banks)}"

    return True, None


def load_source_kits(sd_path):
    """
    Load all source kits from banks 01 and 02.

    Args:
        sd_path: SD card mount point

    Returns:
        List of Kit objects
    """
    kits = []
    banks_dir = get_banks_directory(sd_path)

    for bank_id in SOURCE_BANKS:
        kit_range = SOURCE_KIT_RANGES[bank_id]

        for kit_num in kit_range:
            kit_filename = f"{kit_num:02d}.KIT"
            kit_path = banks_dir / bank_id / 'KITS' / kit_filename

            if kit_path.exists():
                try:
                    kit = Kit.from_file(str(kit_path))
                    kits.append(kit)
                    print(f"  Loaded: {bank_id}/KITS/{kit_filename}")
                except Exception as e:
                    print(f"  Warning: Failed to load {bank_id}/KITS/{kit_filename}: {e}")

    return kits


def select_header_for_format2(input_kits):
    """
    Select an appropriate header for FORMAT 2 output kits.

    Args:
        input_kits: List of Kit objects

    Returns:
        bytearray header for new kits
    """
    # Check if any kits are FORMAT 2 (voice 4 has 32 bytes)
    format2_kits = [kit for kit in input_kits if len(kit.voices[3].data) == 32]

    if format2_kits:
        # Use the first FORMAT 2 kit's header as template
        template_kit = format2_kits[0]
        header = bytearray(template_kit.header)
        print(f"  Using header from FORMAT 2 kit: {len(header)} bytes")
    else:
        # Create new FORMAT 2 header with standard 57 bytes
        header = Kit.create_header(header_size=57, voice_format=2)
        print(f"  Created new FORMAT 2 header: {len(header)} bytes")

    return header


def generate_random_kit(input_kits, output_format=2, template_header=None):
    """
    Generate a single random kit by selecting random voices from input kits.

    Args:
        input_kits: List of Kit objects to mix from
        output_format: 1 or 2 (default 2 for FORMAT 2)
        template_header: Optional header to use for new kit

    Returns:
        Kit object with randomly mixed voices
    """
    # Create new kit with appropriate format
    if template_header is not None:
        new_kit = Kit(header=template_header)
    else:
        new_kit = Kit()
        new_kit.header = Kit.create_header(header_size=57, voice_format=output_format)

    # For each voice position, randomly select from input kits
    for voice_idx in range(4):
        # Pick a random input kit
        source_kit = random.choice(input_kits)
        source_voice = source_kit.get_voice(voice_idx)

        # Set the voice in new kit
        new_kit.set_voice(voice_idx, source_voice)

    return new_kit


def format_kit_filename(kit_number):
    """
    Format kit filename in NN.KIT format.

    Args:
        kit_number: Kit number (0-63)

    Returns:
        Filename string like "00.KIT" or "15.KIT"
    """
    return f"{kit_number:02d}.KIT"


def normalize_bank_id(bank_input):
    """
    Normalize bank ID input to proper format.

    Args:
        bank_input: Bank ID/number (e.g., "3", "03", "10")

    Returns:
        Normalized bank ID string (2 digits)

    Raises:
        ValueError: If numeric bank is out of range 0-63 or if in source banks
    """
    try:
        bank_num = int(bank_input)
        if not 0 <= bank_num <= 63:
            raise ValueError(f"Bank number must be between 0 and 63, got {bank_num}")

        bank_id = f"{bank_num:02d}"

        # Check if trying to write to source banks
        if bank_id in SOURCE_BANKS:
            raise ValueError(f"Cannot write to source bank {bank_id}. Source banks (01, 02) are read-only.")

        return bank_id
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Bank must be a number between 0-63, got '{bank_input}'")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Generate random kits from SD card source banks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 32 random kits (default) to bank 10
  %(prog)s --output-bank 10

  # Generate 8 kits to bank 15
  %(prog)s --output-bank 15 --n 8

  # Use custom seed for reproducibility
  %(prog)s --output-bank 20 --seed 12345

  # Use custom SD card path
  %(prog)s --output-bank 10 --sd-path /Volumes/PERKONS

Safety:
  - Reads from banks 01 (kits 00-31) and 02 (kits 32-63) only
  - Will NOT overwrite banks with existing kit data
  - Verifies SD card is mounted before reading/writing
  - Output uses FORMAT 2 (32-byte voice 4 with sampler support)

Notes:
  - SD card must be mounted at /Volumes/Untitled (or custom path)
  - Source banks 01 and 02 must exist and contain kits
  - Output bank must be 0-63 (excluding 01 and 02)
  - Output kits numbered 00.KIT through (N-1).KIT
        """
    )

    parser.add_argument('--output-bank', required=True,
                        help='Destination bank number (0-63, excluding 01 and 02)')
    parser.add_argument('--n', type=int, default=32,
                        help='Number of output kits to generate (default: 32)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility (optional)')
    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--force', action='store_true',
                        help='Allow overwriting existing non-empty banks (use with caution!)')

    args = parser.parse_args()

    try:
        # Validate arguments
        if args.n < 1 or args.n > 64:
            parser.error("Number of kits must be between 1 and 64")

        # Normalize bank ID
        try:
            output_bank_id = normalize_bank_id(args.output_bank)
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

        print(f"Perkons Random Kit Generator")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print(f"Output bank: {output_bank_id}")
        print(f"Number of kits: {args.n}")
        if args.seed is not None:
            print(f"Random seed: {args.seed}")
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

        # Validate source banks
        print(f"\nValidating source banks...")
        success, error_msg = validate_source_banks(args.sd_path)
        if not success:
            print(f"✗ Error: {error_msg}")
            print(f"\nSource banks 01 and 02 must exist and contain kits.")
            print(f"Expected structure:")
            print(f"  {args.sd_path}/BANKS/01/KITS/00.KIT - 31.KIT")
            print(f"  {args.sd_path}/BANKS/02/KITS/32.KIT - 63.KIT")
            return 1

        print(f"✓ Source banks validated")
        for bank_id in SOURCE_BANKS:
            kit_count = get_kit_count_in_bank(args.sd_path, bank_id)
            print(f"  Bank {bank_id}: {kit_count} kits")

        # Check output bank
        print(f"\nChecking output bank {output_bank_id}...")
        if check_bank_exists(args.sd_path, output_bank_id):
            if not is_bank_empty(args.sd_path, output_bank_id):
                kit_count = get_kit_count_in_bank(args.sd_path, output_bank_id)
                print(f"⚠ Warning: Output bank {output_bank_id} already exists with {kit_count} kit(s)")

                if not args.force:
                    print(f"\n✗ Refusing to overwrite existing bank with content.")
                    print(f"  Use --force to override this safety check.")
                    return 1
                else:
                    print(f"⚠ --force specified, will overwrite existing bank!")
            else:
                print(f"✓ Output bank exists but is empty")
        else:
            print(f"✓ Output bank does not exist (will be created)")

        # Set random seed if provided
        if args.seed is not None:
            random.seed(args.seed)

        # Load source kits
        print(f"\nLoading source kits from banks 01 and 02...")
        input_kits = load_source_kits(args.sd_path)

        if not input_kits:
            print(f"\n✗ Error: No kits could be loaded from source banks")
            return 1

        print(f"\n✓ Loaded {len(input_kits)} source kit(s)")

        # Check kit formats
        voice4_sizes = [len(kit.voices[3].data) for kit in input_kits]
        format1_count = sum(1 for size in voice4_sizes if size == 30)
        format2_count = sum(1 for size in voice4_sizes if size == 32)
        print(f"  FORMAT 1: {format1_count} kits, FORMAT 2: {format2_count} kits")

        # Select template header
        print(f"\nPreparing output format...")
        print(f"  Output format: FORMAT 2 (voice 4 = 32 bytes)")
        template_header = select_header_for_format2(input_kits)

        # Create output directory
        output_path = get_banks_directory(args.sd_path) / output_bank_id / 'KITS'
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"\n✓ Output directory ready: {output_path}")

        # Confirm before proceeding
        if not args.force:
            response = input(f"\nReady to generate {args.n} kit(s). Continue? [y/N]: ")
            if response.lower() not in ('y', 'yes'):
                print("Aborted.")
                return 0

        # Generate and save kits
        print(f"\nGenerating {args.n} random kit(s)...")
        for i in range(args.n):
            kit_filename = format_kit_filename(i)
            kit_path = output_path / kit_filename

            # Generate random kit
            random_kit = generate_random_kit(input_kits,
                                            output_format=2,
                                            template_header=template_header)

            # Save kit
            random_kit.save(str(kit_path))
            print(f"  Generated: {kit_filename}")

        # Write info.md file
        info_path = get_banks_directory(args.sd_path) / output_bank_id / 'info.md'
        with open(info_path, 'w') as f:
            f.write(f"# Bank {output_bank_id} - Random Kits\n\n")
            f.write(f"## Generation Details\n\n")
            f.write(f"- **Script**: pykons-randomise-kits\n")
            f.write(f"- **Number of Kits**: {args.n}\n")
            if args.seed is not None:
                f.write(f"- **Random Seed**: {args.seed}\n")
            f.write(f"- **Generated**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Voice Sources\n\n")
            f.write(f"Random voices sourced from:\n")
            f.write(f"- Bank 01 (kits 00-31)\n")
            f.write(f"- Bank 02 (kits 32-63)\n")

        print(f"\n✓ Successfully generated {args.n} kit(s) in bank {output_bank_id}")
        print(f"  Location: {output_path}")
        print(f"  Info file: {info_path}")
        print(f"\nYou can now eject the SD card and use the kits on your Perkons HD-01.")

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
