#!/usr/bin/env python3
"""
Basic usage examples for pykons library.

This script demonstrates how to use the pykons API to read, modify,
and write Perkons HD-01 .KIT files.
"""

from pykons import Kit, Voice


def example_read_kit():
    """Example: Load and inspect a kit file"""
    print("Example: Reading a kit file")
    print("-" * 50)

    # Load a kit from the SD card
    kit = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/00.KIT')

    print(f"Kit loaded: {kit}")
    print(f"Header size: {len(kit.header)} bytes")

    # Inspect each voice
    for i in range(4):
        voice = kit.get_voice(i)
        print(f"\nVoice {i+1}:")
        print(f"  Size: {len(voice.data)} bytes")
        print(f"  ALGO: {voice.algo}")
        print(f"  MODE: {voice.mode}")
        print(f"  VCF: {voice.vcf}")
        print(f"  TUNE: {voice.tune}")
        print(f"  DECAY: {voice.decay}")
        print(f"  LEVEL: {voice.level}")

    print()


def example_modify_kit():
    """Example: Modify kit parameters"""
    print("Example: Modifying a kit")
    print("-" * 50)

    # Load a kit
    kit = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/00.KIT')

    # Get the first voice
    voice = kit.get_voice(0)

    print(f"Original values:")
    print(f"  TUNE: {voice.tune}")
    print(f"  DECAY: {voice.decay}")
    print(f"  LEVEL: {voice.level}")

    # Modify parameters
    voice.tune = 128    # Set to middle
    voice.decay = 200   # Increase decay
    voice.level = 255   # Max level

    print(f"\nModified values:")
    print(f"  TUNE: {voice.tune}")
    print(f"  DECAY: {voice.decay}")
    print(f"  LEVEL: {voice.level}")

    # Save to a new file
    kit.save('/tmp/modified.KIT')
    print(f"\n✓ Saved modified kit to /tmp/modified.KIT")
    print()


def example_create_kit():
    """Example: Create a new kit from scratch"""
    print("Example: Creating a new kit")
    print("-" * 50)

    # Create an empty FORMAT 2 kit
    kit = Kit()
    kit.header = Kit.create_header(header_size=57, voice_format=2)

    print(f"Created new kit: {kit}")

    # Set parameters for each voice
    for i in range(4):
        voice = kit.get_voice(i)

        # Set toggle switches
        voice.algo = i % 3      # Cycle through 0, 1, 2
        voice.mode = (i + 1) % 3
        voice.vcf = (i + 2) % 3

        # Set potentiometers
        voice.tune = 128
        voice.decay = 150 + (i * 20)  # Different decay for each voice
        voice.level = 200
        voice.fx_send = 100

        print(f"Voice {i+1}: ALGO={voice.algo}, MODE={voice.mode}, DECAY={voice.decay}")

    # Save the kit
    kit.save('/tmp/new_kit.KIT')
    print(f"\n✓ Saved new kit to /tmp/new_kit.KIT")
    print()


def example_mix_voices():
    """Example: Mix voices from different kits"""
    print("Example: Mixing voices from different kits")
    print("-" * 50)

    # Load two source kits
    kit1 = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/00.KIT')
    kit2 = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/01.KIT')

    # Create a new kit
    mixed_kit = Kit()
    mixed_kit.header = bytearray(kit1.header)

    # Mix voices: Take voices 0,1 from kit1 and voices 2,3 from kit2
    mixed_kit.set_voice(0, kit1.get_voice(0))
    mixed_kit.set_voice(1, kit1.get_voice(1))
    mixed_kit.set_voice(2, kit2.get_voice(2))
    mixed_kit.set_voice(3, kit2.get_voice(3))

    print(f"Created mixed kit with:")
    print(f"  Voice 1: from kit1")
    print(f"  Voice 2: from kit1")
    print(f"  Voice 3: from kit2")
    print(f"  Voice 4: from kit2")

    # Save the mixed kit
    mixed_kit.save('/tmp/mixed.KIT')
    print(f"\n✓ Saved mixed kit to /tmp/mixed.KIT")
    print()


if __name__ == '__main__':
    print("=" * 50)
    print("pykons - Basic Usage Examples")
    print("=" * 50)
    print()

    try:
        # Note: These examples assume the SD card is mounted
        # and contains kits in banks 01. Adjust paths as needed.

        # example_read_kit()
        # example_modify_kit()
        # example_create_kit()
        # example_mix_voices()

        print("Uncomment the function calls above to run examples.")
        print("\nNote: Update file paths to match your SD card structure.")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("  1. SD card is mounted at /Volumes/Untitled")
        print("  2. Banks 01 contains kits")
        print("  3. Update paths in the examples as needed")
