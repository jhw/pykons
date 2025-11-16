#!/usr/bin/env python3
"""
Tools for reading and writing Erica Perkins HD-01 .KIT files

File Structure (TWO FORMATS):
- Variable-length header (47-59 bytes observed)
- 4 voices with TWO possible structures:

  FORMAT 1 (Kits 00-31): Voice 4 = 30 bytes
    - Voices 1-3: 26 bytes each
    - Voice 4: 30 bytes
    - Total: 108 bytes (26+26+26+30)

  FORMAT 2 (Kits 32-63): Voice 4 = 32 bytes (adds sampler support)
    - Voices 1-3: 26 bytes each
    - Voice 4: 32 bytes (+2 bytes for sampler)
    - Total: 110 bytes (26+26+26+32)

HEADER STRUCTURE (decoded from 64 factory kits):
  Byte 0: File size - 2 (e.g., 163 for 165-byte file)
  Byte 1: 0x01 (constant)
  Byte 2: 0x08 (constant)
  Byte 3: 0x01 (constant)
  Byte 4: 0x12 (constant, decimal 18)
  Byte 5: Header size - 2 (e.g., 55 for 57-byte header)
  Byte 6: 0x0D (constant, decimal 13)
  Bytes 7+: Variable data (possibly floating point values, settings, etc.)

The file structure is determined by finding the marker sequence [26, 24, 10, 22]
which appears at bytes 4-7 of each voice. The header ends where the first voice begins.

Each voice structure:
- Bytes 0-3: Pre-marker parameters (4 bytes)
  - Byte 0: ALGO toggle (0, 1, 2) ✅ Hardware confirmed
  - Byte 1: Unknown
  - Byte 2: MODE toggle (0, 1, 2) ✅ Hardware confirmed
  - Byte 3: Unused (always 0)
- Bytes 4-7: Marker sequence (always 26, 24, 10, 22)
- Bytes 8-25: Voice parameters (18 bytes) - ALL CONFIRMED! ✅
  - Byte 8: TUNE_QUANTIZED (paired with byte 9)
  - Byte 9: TUNE (0-255)
  - Byte 10: PARAM1_QUANTIZED (paired with byte 11)
  - Byte 11: PARAM1 (0-255)
  - Byte 12: PARAM2_QUANTIZED (paired with byte 13)
  - Byte 13: PARAM2 (0-255)
  - Byte 14: FX_SEND_QUANTIZED (paired with byte 15)
  - Byte 15: FX_SEND (0-255)
  - Byte 16: DECAY_QUANTIZED (paired with byte 17)
  - Byte 17: DECAY (0-255)
  - Byte 18: CUTOFF_QUANTIZED (paired with byte 19)
  - Byte 19: CUTOFF (0-255)
  - Byte 20: DRIVE_QUANTIZED (paired with byte 21)
  - Byte 21: DRIVE (0-255)
  - Byte 22: LEVEL_QUANTIZED (paired with byte 23)
  - Byte 23: LEVEL (0-255)
  - Byte 24: VCF toggle (0, 1, 2)
  - Byte 25: Unused (always 0)
- Bytes 26-29: Extra parameters (in voice 4 for FORMAT 1)
- Bytes 30-31: Sampler parameters (in voice 4 for FORMAT 2 only)

Example Usage:
    # Load a kit and modify parameters
    kit = Kit.from_file('01-00.KIT')
    voice = kit.get_voice(0)

    # Hardware-confirmed parameter accessors (ALL 11 CONTROLS!)
    # Toggle switches
    voice.algo = 1        # Set ALGO toggle to position 2 (value 1)
    voice.mode = 2        # Set MODE toggle to position 3 (value 2)
    voice.vcf = 0         # Set VCF toggle to position 1 (value 0)

    # Potentiometers
    voice.tune = 128      # Set TUNE to middle
    voice.decay = 255     # Set DECAY to max (dial position 10)
    voice.param1 = 25     # Set PARAM1 to ~10% (dial position 1)
    voice.param2 = 51     # Set PARAM2 to ~20% (dial position 2)
    voice.cutoff = 77     # Set CUTOFF to ~30% (dial position 3)
    voice.drive = 102     # Set DRIVE to ~40% (dial position 4)
    voice.fx_send = 128   # Set FX_SEND to ~50% (dial position 5)
    voice.level = 153     # Set LEVEL to ~60% (dial position 6)

    kit.save('modified.KIT')
"""


class Voice:
    """Represents a single voice in a kit"""

    def __init__(self, data):
        """
        Initialize voice from byte data

        Args:
            data: bytes object containing voice data (26, 30, or 32 bytes)
        """
        if len(data) not in (26, 30, 32):
            raise ValueError(f"Voice data must be 26, 30, or 32 bytes, got {len(data)}")

        self.data = bytearray(data)
        self.is_voice4 = len(data) in (30, 32)
        self.has_sampler = len(data) == 32  # FORMAT 2 with sampler support

        # Validate marker
        expected_marker = bytes([26, 24, 10, 22])
        if self.data[4:8] != expected_marker:
            print(f"Warning: Expected marker {list(expected_marker)}, got {list(self.data[4:8])}")

    @property
    def pre_marker_params(self):
        """Get the 4 bytes before the marker"""
        return bytes(self.data[0:4])

    @pre_marker_params.setter
    def pre_marker_params(self, value):
        """Set the 4 bytes before the marker"""
        if len(value) != 4:
            raise ValueError("Pre-marker params must be 4 bytes")
        self.data[0:4] = value

    @property
    def marker(self):
        """Get the marker sequence (should always be 26, 24, 10, 22)"""
        return bytes(self.data[4:8])

    @property
    def parameters(self):
        """Get the main parameter data (18 bytes)"""
        return bytes(self.data[8:26])

    @parameters.setter
    def parameters(self, value):
        """Set the main parameter data"""
        if len(value) != 18:
            raise ValueError("Parameters must be 18 bytes")
        self.data[8:26] = value

    @property
    def extra_params(self):
        """Get extra parameters (voice 4: bytes 26-29, always 4 bytes)"""
        if self.is_voice4:
            return bytes(self.data[26:30])
        return None

    @extra_params.setter
    def extra_params(self, value):
        """Set extra parameters (only for voice 4)"""
        if not self.is_voice4:
            raise ValueError("Only voice 4 has extra parameters")
        if len(value) != 4:
            raise ValueError("Extra params must be 4 bytes")
        self.data[26:30] = value

    @property
    def sampler_params(self):
        """Get sampler parameters (FORMAT 2 only: bytes 30-31, 2 bytes)"""
        if self.has_sampler:
            return bytes(self.data[30:32])
        return None

    @sampler_params.setter
    def sampler_params(self, value):
        """Set sampler parameters (only for FORMAT 2 voice 4)"""
        if not self.has_sampler:
            raise ValueError("Only FORMAT 2 voice 4 has sampler parameters")
        if len(value) != 2:
            raise ValueError("Sampler params must be 2 bytes")
        self.data[30:32] = value

    # Hardware-confirmed parameter accessors
    # Based on hardware testing 2025-01

    @property
    def algo(self):
        """Get ALGO toggle switch value (0, 1, or 2)"""
        return self.data[0]

    @algo.setter
    def algo(self, value):
        """Set ALGO toggle switch value (0, 1, or 2)"""
        if value not in (0, 1, 2):
            raise ValueError("ALGO must be 0, 1, or 2")
        self.data[0] = value

    @property
    def mode(self):
        """Get MODE toggle switch value (0, 1, or 2)"""
        return self.data[2]

    @mode.setter
    def mode(self, value):
        """Set MODE toggle switch value (0, 1, or 2)"""
        if value not in (0, 1, 2):
            raise ValueError("MODE must be 0, 1, or 2")
        self.data[2] = value

    @property
    def vcf(self):
        """Get VCF toggle switch value (0, 1, or 2)"""
        return self.data[24]

    @vcf.setter
    def vcf(self, value):
        """Set VCF toggle switch value (0, 1, or 2)"""
        if value not in (0, 1, 2):
            raise ValueError("VCF must be 0, 1, or 2")
        self.data[24] = value

    @property
    def tune(self):
        """Get TUNE potentiometer value (0-255)"""
        return self.data[9]

    @tune.setter
    def tune(self, value):
        """Set TUNE potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("TUNE must be 0-255")
        self.data[9] = value
        # Note: byte 8 (TUNE_QUANTIZED) is paired but relationship unclear

    @property
    def decay(self):
        """Get DECAY potentiometer value (0-255, max=255 is dial position 10)"""
        return self.data[17]

    @decay.setter
    def decay(self, value):
        """Set DECAY potentiometer value (0-255, max=255 is dial position 10)"""
        if not 0 <= value <= 255:
            raise ValueError("DECAY must be 0-255")
        self.data[17] = value
        # Note: byte 16 (DECAY_QUANTIZED) is paired but relationship unclear

    @property
    def param1(self):
        """Get PARAM1 potentiometer value (0-255)"""
        return self.data[11]

    @param1.setter
    def param1(self, value):
        """Set PARAM1 potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("PARAM1 must be 0-255")
        self.data[11] = value
        # Note: byte 10 (PARAM1_QUANTIZED) is paired but relationship unclear

    @property
    def param2(self):
        """Get PARAM2 potentiometer value (0-255)"""
        return self.data[13]

    @param2.setter
    def param2(self, value):
        """Set PARAM2 potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("PARAM2 must be 0-255")
        self.data[13] = value
        # Note: byte 12 (PARAM2_QUANTIZED) is paired but relationship unclear

    @property
    def cutoff(self):
        """Get CUTOFF potentiometer value (0-255)"""
        return self.data[19]

    @cutoff.setter
    def cutoff(self, value):
        """Set CUTOFF potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("CUTOFF must be 0-255")
        self.data[19] = value
        # Note: byte 18 (CUTOFF_QUANTIZED) is paired but relationship unclear

    @property
    def drive(self):
        """Get DRIVE potentiometer value (0-255)"""
        return self.data[21]

    @drive.setter
    def drive(self, value):
        """Set DRIVE potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("DRIVE must be 0-255")
        self.data[21] = value
        # Note: byte 20 (DRIVE_QUANTIZED) is paired but relationship unclear

    @property
    def fx_send(self):
        """Get FX_SEND potentiometer value (0-255)"""
        return self.data[15]

    @fx_send.setter
    def fx_send(self, value):
        """Set FX_SEND potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("FX_SEND must be 0-255")
        self.data[15] = value
        # Note: byte 14 (FX_SEND_QUANTIZED) is paired but relationship unclear

    @property
    def level(self):
        """Get LEVEL potentiometer value (0-255)"""
        return self.data[23]

    @level.setter
    def level(self, value):
        """Set LEVEL potentiometer value (0-255)"""
        if not 0 <= value <= 255:
            raise ValueError("LEVEL must be 0-255")
        self.data[23] = value
        # Note: byte 22 (LEVEL_QUANTIZED) is paired but relationship unclear

    def to_bytes(self):
        """Convert voice back to bytes"""
        return bytes(self.data)

    def __repr__(self):
        return f"Voice(size={len(self.data)}, params={list(self.parameters[:6])}...)"


class Kit:
    """Represents a complete .KIT file with header and 4 voices"""

    @staticmethod
    def create_header(header_size=57, voice_format=1):
        """
        Create a valid header with proper size encoding

        Args:
            header_size: desired header size (47-59 bytes)
            voice_format: 1 for FORMAT 1 (voice 4 = 30 bytes), 2 for FORMAT 2 (voice 4 = 32 bytes)

        Returns:
            bytearray with proper header structure
        """
        if header_size < 7:
            raise ValueError("Header size must be at least 7 bytes")

        if voice_format not in (1, 2):
            raise ValueError("voice_format must be 1 or 2")

        header = bytearray(header_size)

        # Calculate voice data size based on format
        voice_data_size = 108 if voice_format == 1 else 110  # FORMAT 1: 108, FORMAT 2: 110

        # Fixed bytes based on analysis of 64 factory kits
        total_size = header_size + voice_data_size
        header[0] = total_size - 2      # Byte 0: file size - 2 (CORRECTED)
        header[1] = 0x01                # Byte 1: constant
        header[2] = 0x08                # Byte 2: constant
        header[3] = 0x01                # Byte 3: constant
        header[4] = 0x12                # Byte 4: constant (18)
        header[5] = header_size - 2     # Byte 5: header size - 2
        header[6] = 0x0D                # Byte 6: constant (13)

        # Bytes 7+ are left as zeros (or could be filled with defaults)
        # In real kits, these contain variable data

        return header

    @staticmethod
    def _find_voice_boundaries(data):
        """
        Find voice boundaries by locating marker sequences

        Returns:
            List of (start, end) tuples for each voice section
        """
        marker = bytes([26, 24, 10, 22])
        marker_positions = []

        for i in range(len(data) - len(marker) + 1):
            if data[i:i+len(marker)] == marker:
                marker_positions.append(i)

        if len(marker_positions) != 4:
            raise ValueError(f"Expected 4 voice markers, found {len(marker_positions)}")

        # Voice starts 4 bytes before marker (pre-marker params)
        voice_starts = [pos - 4 for pos in marker_positions]
        voice_ends = voice_starts[1:] + [len(data)]

        return list(zip(voice_starts, voice_ends))

    def __init__(self, data=None, header=None):
        """
        Initialize kit from byte data

        Args:
            data: bytes object containing kit file data (variable length)
            header: optional header bytes to use (for creating new kits)
        """
        if data is not None:
            # Find voice boundaries dynamically
            boundaries = self._find_voice_boundaries(data)

            # Header is everything before first voice
            header_size = boundaries[0][0]
            self.header = bytearray(data[0:header_size])

            # Extract voices
            self.voices = []
            for start, end in boundaries:
                self.voices.append(Voice(data[start:end]))
        else:
            # Create empty kit with proper markers and header
            if header is not None:
                self.header = bytearray(header)
            else:
                # Create proper header with size encoding
                self.header = self.create_header(57)  # Default: 57 bytes (most common)

            # Create voices with correct marker sequence
            empty_voice_26 = bytearray(26)
            empty_voice_26[4:8] = bytes([26, 24, 10, 22])  # Set marker
            empty_voice_30 = bytearray(30)
            empty_voice_30[4:8] = bytes([26, 24, 10, 22])  # Set marker

            self.voices = [
                Voice(bytes(empty_voice_26)),
                Voice(bytes(empty_voice_26)),
                Voice(bytes(empty_voice_26)),
                Voice(bytes(empty_voice_30))
            ]

    @classmethod
    def from_file(cls, filename):
        """
        Load a kit from a .KIT file

        Args:
            filename: path to .KIT file

        Returns:
            Kit object
        """
        with open(filename, 'rb') as f:
            data = f.read()
        return cls(data)

    def to_bytes(self):
        """
        Convert kit back to bytes

        Returns:
            bytes object of complete kit (165 bytes)
        """
        result = bytes(self.header)
        for voice in self.voices:
            result += voice.to_bytes()
        return result

    def save(self, filename):
        """
        Save kit to a .KIT file

        Args:
            filename: path to save .KIT file
        """
        with open(filename, 'wb') as f:
            f.write(self.to_bytes())

    def get_voice(self, index):
        """
        Get a voice by index (0-3)

        Args:
            index: voice index (0-3)

        Returns:
            Voice object
        """
        if not 0 <= index < 4:
            raise ValueError("Voice index must be 0-3")
        return self.voices[index]

    def set_voice(self, index, voice):
        """
        Replace a voice at the given index

        Args:
            index: voice index (0-3)
            voice: Voice object to set

        Note: Voice 4 (index 3) can be 30 or 32 bytes, others must be 26 bytes
        """
        if not 0 <= index < 4:
            raise ValueError("Voice index must be 0-3")

        # Voices 1-3 must be 26 bytes
        if index < 3:
            if len(voice.data) != 26:
                # Try to convert from voice 4
                if len(voice.data) in (30, 32):
                    # Strip extra/sampler params
                    voice = Voice(bytes(voice.data[0:26]))
                else:
                    raise ValueError(f"Voice {index+1} must be 26 bytes")
        else:
            # Voice 4 can be 26, 30, or 32 bytes
            if len(voice.data) == 26:
                # Determine current kit format by checking existing voice 4
                current_v4_size = len(self.voices[3].data) if len(self.voices) > 3 else 30

                # Convert to appropriate size
                new_data = bytearray(voice.data)
                new_data.extend([1, 0, 1, 0])  # Add extra params
                if current_v4_size == 32:
                    new_data.extend([0, 0])  # Add sampler params for FORMAT 2
                voice = Voice(bytes(new_data))
            elif len(voice.data) not in (30, 32):
                raise ValueError(f"Voice 4 must be 26, 30, or 32 bytes")

        self.voices[index] = voice

    def __repr__(self):
        return f"Kit(header={len(self.header)} bytes, voices={len(self.voices)})"


def mix_kits(kit_files, voice_selections):
    """
    Create a new kit by mixing voices from different kit files

    Args:
        kit_files: list of .KIT file paths
        voice_selections: list of tuples (kit_index, voice_index) for each of 4 voices
                         Example: [(0, 0), (1, 2), (0, 1), (2, 3)]
                         This would take voice 1 from kit 0, voice 3 from kit 1,
                         voice 2 from kit 0, and voice 4 from kit 2

    Returns:
        Kit object with mixed voices
    """
    if len(voice_selections) != 4:
        raise ValueError("Must select exactly 4 voices")

    # Load all kits
    kits = [Kit.from_file(f) for f in kit_files]

    # Create new kit starting with first kit's header
    new_kit = Kit()
    new_kit.header = bytearray(kits[0].header)

    # Mix voices
    for target_idx, (kit_idx, voice_idx) in enumerate(voice_selections):
        if kit_idx >= len(kits):
            raise ValueError(f"Kit index {kit_idx} out of range")
        if not 0 <= voice_idx < 4:
            raise ValueError(f"Voice index {voice_idx} must be 0-3")

        source_voice = kits[kit_idx].get_voice(voice_idx)
        new_kit.set_voice(target_idx, source_voice)

    return new_kit
