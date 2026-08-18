"""
Audio validation and conversion utilities.

Cross-platform, no OS-specific dependencies.
"""

import wave
import io
from dataclasses import dataclass
from typing import Optional
import subprocess
import shutil

from ..utils.errors import AudioError, AudioInvalidFormatError, AudioTooLargeError, AudioConversionError


@dataclass
class AudioValidation:
    """Result of audio validation."""
    valid: bool
    duration_ms: int
    sample_rate: int
    channels: int
    format: str
    error: Optional[str] = None


def validate_audio(audio_bytes: bytes, format_hint: Optional[str] = None) -> AudioValidation:
    """
    Validate audio bytes and extract metadata.
    
    Args:
        audio_bytes: Raw audio data
        format_hint: Optional format hint (wav, mp3, etc.)
        
    Returns:
        AudioValidation with metadata
        
    Raises:
        AudioError: If validation fails
    """
    if not audio_bytes:
        raise AudioError("AUDIO_NO_INPUT", "No audio data provided")
    
    # Check size (25MB limit)
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > 25:
        raise AudioTooLargeError(f"Audio file too large: {size_mb:.1f}MB (max 25MB)")
    
    # Try to detect format and validate
    if format_hint == "wav" or _is_wav(audio_bytes):
        return _validate_wav(audio_bytes)
    elif format_hint in ("mp3", "m4a", "ogg", "flac", "webm"):
        # For non-WAV formats, we'll convert to WAV
        # Just do basic validation here
        return AudioValidation(
            valid=True,
            duration_ms=0,  # Unknown until converted
            sample_rate=0,
            channels=0,
            format=format_hint,
        )
    else:
        # Try to detect from magic bytes
        if _is_wav(audio_bytes):
            return _validate_wav(audio_bytes)
        else:
            # Assume it's a supported format that needs conversion
            return AudioValidation(
                valid=True,
                duration_ms=0,
                sample_rate=0,
                channels=0,
                format="unknown",
            )


def _is_wav(audio_bytes: bytes) -> bool:
    """Check if bytes are WAV format."""
    return len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"


def _validate_wav(audio_bytes: bytes) -> AudioValidation:
    """Validate WAV file and extract metadata."""
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            frames = wav.getnframes()
            sample_rate = wav.getframerate()
            channels = wav.getnchannels()
            duration_ms = int((frames / sample_rate) * 1000) if sample_rate > 0 else 0
            
            # Check duration (5 min limit)
            if duration_ms > 300_000:
                raise AudioError("AUDIO_TOO_LONG", "Audio exceeds 5 minute limit")
            
            return AudioValidation(
                valid=True,
                duration_ms=duration_ms,
                sample_rate=sample_rate,
                channels=channels,
                format="wav",
            )
    except wave.Error as e:
        raise AudioInvalidFormatError(f"Invalid WAV file: {e}") from e


def convert_to_wav(audio_bytes: bytes, input_format: str) -> bytes:
    """
    Convert audio to WAV format using ffmpeg.
    
    Args:
        audio_bytes: Input audio data
        input_format: Input format (mp3, m4a, ogg, flac, webm, etc.)
        
    Returns:
        WAV audio bytes
        
    Raises:
        AudioConversionError: If conversion fails
    """
    if input_format == "wav":
        return audio_bytes
    
    # Check if ffmpeg is available
    if not shutil.which("ffmpeg"):
        raise AudioConversionError("ffmpeg not installed - cannot convert audio formats")
    
    # Use ffmpeg to convert
    try:
        # Write input to temp file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False) as inp:
            inp.write(audio_bytes)
            input_path = inp.name
        
        output_path = input_path + ".wav"
        
        try:
            # Run ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000",  # 16kHz sample rate (Whisper prefers this)
                "-ac", "1",      # Mono
                "-c:a", "pcm_s16le",  # PCM 16-bit little-endian
                output_path,
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode != 0:
                raise AudioConversionError(f"ffmpeg failed: {result.stderr.decode()}")
            
            # Read output
            with open(output_path, "rb") as f:
                wav_bytes = f.read()
            
            return wav_bytes
            
        finally:
            # Cleanup temp files
            try:
                os.unlink(input_path)
            except OSError:
                pass
            try:
                os.unlink(output_path)
            except OSError:
                pass
                
    except subprocess.TimeoutExpired:
        raise AudioConversionError("Audio conversion timed out")
    except Exception as e:
        raise AudioConversionError(f"Audio conversion failed: {e}") from e