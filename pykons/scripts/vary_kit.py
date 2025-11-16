#!/usr/bin/env python3
"""
Generate variations of a specific kit by mutating selected voices.

This script creates N variations of a source kit by randomly replacing
n-mutations voices with voices from the source banks 01 and 02.

Each variation:
- Starts as a copy of the source kit
- Randomly selects n-mutations voices to replace (1-4)
- Replaces those voices with random voices from banks 01/02
- Preserves voice positions (voice 1 stays voice 1, etc.)

Usage:
    # Generate 32 variations of kit 01:05, mutating 2 voices each
    pykons-variation --source 01:05 --output-bank 10

    # Generate 8 variations, mutating 3 voices each
    pykons-variation --source 02:45 --output-bank 15 --n-variants 8 --n-mutations 3

    # Mutate all 4 voices for maximum variation
    pykons-variation --source 01:10 --output-bank 20 --n-mutations 4

    # Use custom seed for reproducibility
    pykons-variation --source 01:00 --output-bank 25 --seed 12345
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
SOURCE_BANKS = ['01', '02']
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


def parse_kit_spec(kit_spec):
    """
    Parse kit specification in format XX:YY.

    Args:
        kit_spec: Kit specification string (e.g., "01:05", "02:32")

    Returns:
        Tuple of (bank_id: str, kit_id: str)

    Raises:
        ValueError: If format is invalid or numbers out of range
    """
    if ':' not in kit_spec:
        raise ValueError(f"Kit spec must be in format XX:YY, got '{kit_spec}'")

    parts = kit_spec.split(':')
    if len(parts) != 2:
        raise ValueError(f"Kit spec must be in format XX:YY, got '{kit_spec}'")

    bank_str, kit_str = parts

    # Validate bank
    try:
        bank_num = int(bank_str)
        if not 0 <= bank_num <= 63:
            raise ValueError(f"Bank number must be 00-63, got {bank_num}")
        bank_id = f"{bank_num:02d}"
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Bank must be numeric 00-63, got '{bank_str}'")
        raise

    # Validate kit
    try:
        kit_num = int(kit_str)
        if not 0 <= kit_num <= 63:
            raise ValueError(f"Kit number must be 00-63, got {kit_num}")
        kit_id = f"{kit_num:02d}"
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Kit must be numeric 00-63, got '{kit_str}'")
        raise

    return bank_id, kit_id


def validate_kit_exists(sd_path, bank_id, kit_id):
    """
    Check if a kit file exists on the SD card.

    Args:
        sd_path: SD card mount point
        bank_id: Bank ID (e.g., '01')
        kit_id: Kit ID (e.g., '05')

    Returns:
        Tuple of (exists: bool, kit_path: Path, error_msg: str or None)
    """
    kit_path = get_banks_directory(sd_path) / bank_id / 'KITS' / f"{kit_id}.KIT"

    if not kit_path.exists():
        return False, kit_path, f"Kit file not found: {bank_id}:KITS/{kit_id}.KIT"

    return True, kit_path, None


def normalize_bank_id(bank_input):
    """
    Normalize bank ID input to proper format.

    Args:
        bank_input: Bank ID/number (e.g., "3", "03", "10")

    Returns:
        Normalized bank ID string (2 digits)

    Raises:
        ValueError: If bank is out of range or in protected range
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
                except Exception as e:
                    print(f"  Warning: Failed to load {bank_id}/KITS/{kit_filename}: {e}")

    return kits


def generate_variation(source_kit, mutation_kits, n_mutations):
    """
    Generate a variation of the source kit by mutating n voices.

    Args:
        source_kit: Kit object to vary
        mutation_kits: List of Kit objects to pull replacement voices from
        n_mutations: Number of voices to mutate (1-4)

    Returns:
        Kit object with mutated voices
    """
    # Create a copy of the source kit
    variation = Kit()
    variation.header = bytearray(source_kit.header)

    # Copy all voices initially
    for i in range(4):
        variation.set_voice(i, source_kit.get_voice(i))

    # Select which voices to mutate
    voice_indices = list(range(4))
    voices_to_mutate = random.sample(voice_indices, n_mutations)

    # Mutate selected voices
    for voice_idx in voices_to_mutate:
        # Pick a random source kit
        mutation_source = random.choice(mutation_kits)
        replacement_voice = mutation_source.get_voice(voice_idx)

        # Replace the voice
        variation.set_voice(voice_idx, replacement_voice)

    return variation, voices_to_mutate


def format_kit_filename(kit_number):
    """
    Format kit filename in NN.KIT format.

    Args:
        kit_number: Kit number (0-63)

    Returns:
        Filename string like "00.KIT" or "15.KIT"
    """
    return f"{kit_number:02d}.KIT"


def main():
    parser = argparse.ArgumentParser(
        description='Generate variations of a source kit with voice mutations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 32 variations of kit 01:05, mutating 2 voices each
  %(prog)s --source 01:05 --output-bank 10

  # Generate 8 variations, mutating 3 voices each
  %(prog)s --source 02:45 --output-bank 15 --n-variants 8 --n-mutations 3

  # Mutate all 4 voices for maximum variation
  %(prog)s --source 01:10 --output-bank 20 --n-mutations 4

  # Use custom seed for reproducibility
  %(prog)s --source 01:00 --output-bank 25 --seed 12345

How it works:
  - Starts with the source kit
  - For each variation:
    * Randomly selects n-mutations voices to replace
    * Replaces them with voices from banks 01/02 (voice position preserved)
  - Writes variations to output bank

Safety:
  - Source kit must exist on SD card
  - Reads mutation voices from banks 01 (kits 00-31) and 02 (kits 32-63)
  - Will NOT overwrite banks with existing kit data
  - Output bank must be 0-63 (excluding 01 and 02)

Notes:
  - Voice positions are always preserved (voice 1 stays voice 1, etc.)
  - n-mutations determines how different variants are from source
  - n-mutations=1: Subtle variations (1 voice changed)
  - n-mutations=4: Maximum variation (all voices changed)
        """
    )

    parser.add_argument('--source', required=True,
                        help='Source kit in format XX:YY (e.g., 01:05, 02:32)')
    parser.add_argument('--output-bank', required=True,
                        help='Destination bank number (0-63, excluding 01 and 02)')
    parser.add_argument('--n-variants', type=int, default=32,
                        help='Number of variations to generate (default: 32)')
    parser.add_argument('--n-mutations', type=int, default=2,
                        help='Number of voices to mutate per variant (1-4, default: 2)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility (optional)')
    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--force', action='store_true',
                        help='Allow overwriting existing non-empty banks (use with caution!)')

    args = parser.parse_args()

    try:
        # Validate arguments
        if args.n_variants < 1 or args.n_variants > 64:
            parser.error("Number of variants must be between 1 and 64")

        if args.n_mutations < 1 or args.n_mutations > 4:
            parser.error("Number of mutations must be between 1 and 4")

        # Parse source kit
        try:
            source_bank_id, source_kit_id = parse_kit_spec(args.source)
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

        # Normalize output bank ID
        try:
            output_bank_id = normalize_bank_id(args.output_bank)
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

        print(f"Perkons Kit Variation Generator")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print(f"Source kit: {source_bank_id}:{source_kit_id}")
        print(f"Output bank: {output_bank_id}")
        print(f"Number of variants: {args.n_variants}")
        print(f"Mutations per variant: {args.n_mutations}")
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

        # Validate source kit exists
        print(f"\nValidating source kit...")
        exists, source_kit_path, error_msg = validate_kit_exists(
            args.sd_path, source_bank_id, source_kit_id
        )
        if not exists:
            print(f"✗ Error: {error_msg}")
            return 1

        print(f"✓ Source kit found: {source_bank_id}/KITS/{source_kit_id}.KIT")

        # Load source kit
        try:
            source_kit = Kit.from_file(str(source_kit_path))
            print(f"  Header: {len(source_kit.header)} bytes")
            print(f"  Voices: {[len(v.data) for v in source_kit.voices]} bytes")
        except Exception as e:
            print(f"✗ Error: Failed to load source kit: {e}")
            return 1

        # Validate source banks
        print(f"\nValidating source banks for mutations...")
        success, error_msg = validate_source_banks(args.sd_path)
        if not success:
            print(f"✗ Error: {error_msg}")
            print(f"\nSource banks 01 and 02 must exist and contain kits.")
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

        # Load mutation source kits
        print(f"\nLoading mutation source kits from banks 01 and 02...")
        mutation_kits = load_source_kits(args.sd_path)

        if not mutation_kits:
            print(f"\n✗ Error: No kits could be loaded from source banks")
            return 1

        print(f"\n✓ Loaded {len(mutation_kits)} mutation source kit(s)")

        # Create output directory
        output_path = get_banks_directory(args.sd_path) / output_bank_id / 'KITS'
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"\n✓ Output directory ready: {output_path}")

        # Confirm before proceeding
        if not args.force:
            response = input(f"\nReady to generate {args.n_variants} variant(s). Continue? [y/N]: ")
            if response.lower() not in ('y', 'yes'):
                print("Aborted.")
                return 0

        # Generate and save variants
        print(f"\nGenerating {args.n_variants} variant(s) of {source_bank_id}:{source_kit_id}...")
        for i in range(args.n_variants):
            kit_filename = format_kit_filename(i)
            kit_path = output_path / kit_filename

            if i == 0:
                # First kit is always the unvaried source kit
                variant_kit = Kit()
                variant_kit.header = bytearray(source_kit.header)
                for v_idx in range(4):
                    variant_kit.set_voice(v_idx, source_kit.get_voice(v_idx))

                variant_kit.save(str(kit_path))
                print(f"  Generated: {kit_filename} (original, unvaried)")
            else:
                # Generate variation
                variant_kit, mutated_voices = generate_variation(
                    source_kit, mutation_kits, args.n_mutations
                )

                # Save kit
                variant_kit.save(str(kit_path))
                voice_names = [f"V{v+1}" for v in mutated_voices]
                print(f"  Generated: {kit_filename} (mutated: {', '.join(voice_names)})")

        # Write info.md file
        info_path = get_banks_directory(args.sd_path) / output_bank_id / 'info.md'
        with open(info_path, 'w') as f:
            f.write(f"# Bank {output_bank_id} - Kit Variations\n\n")
            f.write(f"## Generation Details\n\n")
            f.write(f"- **Script**: pykons-vary-kit\n")
            f.write(f"- **Source Kit**: {source_bank_id}:{source_kit_id}\n")
            f.write(f"- **Number of Variants**: {args.n_variants}\n")
            f.write(f"- **Mutations per Variant**: {args.n_mutations} voices\n")
            if args.seed is not None:
                f.write(f"- **Random Seed**: {args.seed}\n")
            f.write(f"- **Generated**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Kit Details\n\n")
            f.write(f"- **Kit 00**: Original source kit (unvaried)\n")
            f.write(f"- **Kits 01-{args.n_variants-1:02d}**: Variations with {args.n_mutations} voice(s) mutated\n\n")
            f.write(f"## Voice Sources\n\n")
            f.write(f"Mutation voices sourced from:\n")
            f.write(f"- Bank 01 (kits 00-31)\n")
            f.write(f"- Bank 02 (kits 32-63)\n")

        print(f"\n✓ Successfully generated {args.n_variants} variant(s) in bank {output_bank_id}")
        print(f"  Source: {source_bank_id}:{source_kit_id}")
        print(f"  Mutations per variant: {args.n_mutations} voices")
        print(f"  Location: {output_path}")
        print(f"  Info file: {info_path}")
        print(f"\nYou can now eject the SD card and use the variants on your Perkons HD-01.")

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
