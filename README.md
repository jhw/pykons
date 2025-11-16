# pykons

Python tools for Erica Synths Perkons HD-01 drum machine KIT files.

## Overview

`pykons` is a Python library and set of command-line tools for working with Erica Synths Perkons HD-01 drum machine KIT format files. It provides a complete API for reading, writing, and manipulating kit files, plus utilities for working directly with the Perkons SD card.

## Features

- **Complete KIT file API**: Read and write Perkons HD-01 .KIT files
- **Voice-level control**: Access and modify all 11 hardware controls per voice
- **SD card integration**: Direct read/write to connected Perkons SD card
- **Randomization tools**: Generate random kits from source banks
- **Safety checks**: Prevents overwriting existing kit data

## Installation

### From Git (Recommended)

```bash
pip install git+https://github.com/yourusername/pykons.git
```

### For Development

```bash
git clone https://github.com/yourusername/pykons.git
cd pykons
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Quick Start

### Python API

```python
from pykons import Kit

# Load a kit from SD card
kit = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/00.KIT')

# Access voice parameters
voice = kit.get_voice(0)
print(f"TUNE: {voice.tune}")
print(f"DECAY: {voice.decay}")

# Modify parameters
voice.algo = 1      # Change ALGO toggle
voice.tune = 128    # Set TUNE to middle
voice.level = 255   # Set LEVEL to max

# Save modified kit
kit.save('/path/to/output.KIT')
```

### Command-Line Tools

#### Randomize Kits

Generate random kits from source banks and write directly to SD card:

```bash
# Generate 32 random kits from banks 01 and 02, write to bank 10
pykons-randomize --output-bank 10

# Generate 8 random kits
pykons-randomize --output-bank 15 --n 8

# Custom random seed for reproducibility
pykons-randomize --output-bank 20 --seed 12345
```

The randomization tool:
- Reads source kits from banks 01 (kits 00-31) and 02 (kits 32-63) on the SD card
- Generates N random kits by mixing voices
- Checks if output bank exists and is empty before writing
- Never overwrites existing kit data (safety first!)

## SD Card Structure

The Perkons HD-01 SD card should be mounted at `/Volumes/Untitled` (macOS) with the following structure:

```
/Volumes/Untitled/
└── BANKS/
    ├── 01/          # Source bank 1 (kits 00-31)
    │   └── KITS/
    │       ├── 00.KIT
    │       ├── 01.KIT
    │       └── ...
    ├── 02/          # Source bank 2 (kits 32-63)
    │   └── KITS/
    │       ├── 32.KIT
    │       ├── 33.KIT
    │       └── ...
    └── 10/          # Your custom banks
        └── KITS/
            └── ...
```

## File Format

Perkons HD-01 .KIT files have two formats:

- **FORMAT 1** (kits 00-31): Voice 4 = 30 bytes, no sampler support
- **FORMAT 2** (kits 32-63): Voice 4 = 32 bytes, with sampler support

Each kit contains:
- Variable-length header (47-59 bytes)
- 4 voices with parameters for all hardware controls

### Hardware Controls

Each voice exposes 11 hardware controls:

**Toggle switches** (3-position: 0, 1, 2):
- `algo` - Algorithm selector
- `mode` - Mode selector
- `vcf` - Filter mode

**Potentiometers** (0-255):
- `tune` - Pitch/tuning
- `param1` - Algorithm parameter 1
- `param2` - Algorithm parameter 2
- `fx_send` - Effects send level
- `decay` - Envelope decay
- `cutoff` - Filter cutoff
- `drive` - Distortion/drive
- `level` - Output level

## Safety Features

All scripts include safety checks:
- ✅ Verify SD card is mounted at `/Volumes/Untitled`
- ✅ Check if output bank exists before writing
- ✅ Refuse to overwrite banks with existing kit data
- ✅ Validate all file operations

## Requirements

- Python 3.6 or higher
- No external dependencies (standard library only)
- Perkons HD-01 SD card (for scripts)

## License

MIT License - see LICENSE file for details

## Acknowledgments

File format reverse-engineered from Erica Synths Perkons HD-01 factory kits. The Perkons HD-01 and its file formats are property of Erica Synths.
