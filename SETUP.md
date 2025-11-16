# pykons Setup & Development Guide

## Project Structure

```
pykons/
├── .gitignore              # Python and project-specific ignores
├── LICENSE                 # MIT License
├── README.md               # Main documentation
├── SETUP.md               # This file
├── pyproject.toml         # Python project configuration (PEP 621)
├── requirements.txt       # No external dependencies
├── venv/                  # Virtual environment (gitignored)
├── examples/              # Usage examples
│   └── basic_usage.py    # API usage examples
└── pykons/               # Main package
    ├── __init__.py       # Package exports (Kit, Voice, mix_kits)
    ├── kit_tools.py      # Core API for reading/writing .KIT files
    └── scripts/          # Command-line tools
        ├── __init__.py
        └── randomize.py  # Random kit generator with SD card integration

```

## Installation

### For End Users

Install directly from GitHub:

```bash
pip install git+https://github.com/yourusername/pykons.git
```

Or with a specific version tag:

```bash
pip install git+https://github.com/yourusername/pykons.git@v0.1.0
```

### For Development

```bash
# Clone the repository
git clone https://github.com/yourusername/pykons.git
cd pykons

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## Usage

### Command-Line Tool

```bash
# Generate 32 random kits to bank 10
pykons-randomize --output-bank 10

# Generate 8 kits with custom seed
pykons-randomize --output-bank 15 --n 8 --seed 12345
```

### Python API

```python
from pykons import Kit

# Load a kit
kit = Kit.from_file('/Volumes/Untitled/BANKS/01/KITS/00.KIT')

# Access voice parameters
voice = kit.get_voice(0)
print(f"TUNE: {voice.tune}")
print(f"DECAY: {voice.decay}")

# Modify and save
voice.tune = 128
voice.level = 255
kit.save('modified.KIT')
```

## Key Features

### Core API (pykons/kit_tools.py)

- **Kit class**: Complete .KIT file with header and 4 voices
- **Voice class**: Individual voice with 11 hardware control accessors
- **Two formats supported**:
  - FORMAT 1 (banks 00-31): Voice 4 = 30 bytes
  - FORMAT 2 (banks 32-63): Voice 4 = 32 bytes (sampler support)

### Randomization Script (pykons/scripts/randomize.py)

- Reads source kits from SD card banks 01 and 02
- Generates N random kits by mixing voices
- Writes directly to specified output bank
- **Safety features**:
  - Verifies SD card is mounted at `/Volumes/Untitled`
  - Checks if output bank exists and has content
  - Refuses to overwrite existing data (unless --force)
  - Validates all paths before writing
  - Never writes to source banks 01 and 02

## SD Card Structure

```
/Volumes/Untitled/
└── BANKS/
    ├── 01/                 # Source bank 1 (kits 00-31, FORMAT 1)
    │   └── KITS/
    │       ├── 00.KIT
    │       ├── 01.KIT
    │       └── ... (through 31.KIT)
    ├── 02/                 # Source bank 2 (kits 32-63, FORMAT 2)
    │   └── KITS/
    │       ├── 32.KIT
    │       ├── 33.KIT
    │       └── ... (through 63.KIT)
    └── 10/                 # Your custom banks (00-63, excluding 01-02)
        └── KITS/
            ├── 00.KIT
            └── ...
```

## Development Notes

### No External Dependencies

The project uses only Python standard library:
- `pathlib` for path manipulation
- `argparse` for CLI parsing
- `random` for randomization
- `os`, `sys` for file operations

### Version Management

Update version in two places:
1. `pyproject.toml` - `version = "0.1.0"`
2. `pykons/__init__.py` - `__version__ = "0.1.0"`

### Creating Releases

```bash
# Tag the release
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# Users can then install with:
# pip install git+https://github.com/yourusername/pykons.git@v0.1.0
```

## File Format Details

### Hardware Controls (per voice)

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

### Voice Structure

```
Voice (26/30/32 bytes):
  Bytes 0-3:   Pre-marker parameters (ALGO, MODE, etc.)
  Bytes 4-7:   Marker sequence [26, 24, 10, 22]
  Bytes 8-25:  Main parameters (TUNE, DECAY, LEVEL, etc.)
  Bytes 26-29: Extra parameters (voice 4 only)
  Bytes 30-31: Sampler parameters (FORMAT 2 voice 4 only)
```

## Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Test package import
python3 -c "from pykons import Kit, Voice; print('✓ Import successful')"

# Test CLI tool
pykons-randomize --help

# Run examples (adjust paths as needed)
python3 examples/basic_usage.py
```

## Troubleshooting

### SD Card Not Found

- Ensure SD card is mounted at `/Volumes/Untitled` (macOS)
- Or specify custom path: `--sd-path /Volumes/PERKONS`
- Check available volumes: `ls /Volumes/`

### Source Banks Missing

- Banks 01 and 02 must exist with kits
- Copy factory kits to these banks before randomizing

### Permission Errors

- Ensure SD card is not write-protected
- Check file permissions on SD card

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
