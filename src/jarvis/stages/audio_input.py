"""
Stage 1: Audio Input - Validate and prepare audio data.

Accepts base64-encoded audio or URL, validates format/size,
converts to standard format for transcription.
"""

from typing import Optional
import base64
import httpx

from ..state.states import StateData, PipelineState
from ..schemas.api import AudioInputRequest
from ..utils.errors import AudioError
from ..utils.audio import validate_audio, convert_to_wav
from ..config import settings


def detect_audio_format(audio_bytes: bytes) -> Optional[str]:
    """
    Detect audio format from file headers (magic bytes) natively in Python.
    Does not require libmagic or any external system DLLs.
    """
    if len(audio_bytes) < 12:
        return None
        
    # WAV: RIFF....WAVE
    if audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
        return "wav"
        
    # MP3: ID3 or standard frame headers
    if audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xFF\xFB") or audio_bytes.startswith(b"\xFF\xF3") or audio_bytes.startswith(b"\xFF\xF2"):
        return "mp3"
        
    # FLAC: fLaC
    if audio_bytes.startswith(b"fLaC"):
        return "flac"
        
    # OGG: OggS
    if audio_bytes.startswith(b"OggS"):
        return "ogg"
        
    # WebM: EBML header starting with 1A 45 DF A3
    if audio_bytes.startswith(b"\x1A\x45\xDF\xA3"):
        return "webm"
        
    # M4A / MP4: search for ftyp box at offset 4
    ftyp_box = audio_bytes[4:8]
    if ftyp_box == b"ftyp":
        brand = audio_bytes[8:12]
        if brand in (b"M4A ", b"mp42", b"isom", b"MSNV", b"dash"):
            return "m4a"
            
    return None


# Supported audio formats
SUPPORTED_MIME_TYPES = {
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
}

MAX_AUDIO_SIZE_MB = 25
MAX_AUDIO_DURATION_SECONDS = 300  # 5 minutes


async def handle_audio_input(state: StateData) -> StateData:
    """
    Stage 1 handler: Validate and prepare audio input.
    
    Reads from state.run (which has session_id, user_id from request),
    fetches/decodes audio, validates, stores bytes in state.
    
    Transitions:
    - Success -> TRANSCRIBING
    - Failure -> FAILED (with AudioError)
    
    Args:
        state: Current pipeline state with run info
        
    Returns:
        Updated state with audio_bytes, audio_format, audio_duration_ms
        
    Raises:
        NonRetryableError: For validation failures (bad format, too large, etc.)
    """
    # The request data should be in state.run or passed via context
    # For now, we expect audio_bytes to be pre-populated or fetch from URL
    
    if not state.audio_bytes and not hasattr(state, '_audio_request'):
        state.current_state = PipelineState.FAILED
        raise NonRetryableError("No audio input provided")
    
    audio_bytes = state.audio_bytes
    audio_format = state.audio_format
    
    # If we have a request object, process it
    if hasattr(state, '_audio_request'):
        request: AudioInputRequest = state._audio_request
        try:
            audio_bytes, audio_format = await _fetch_and_decode_audio(request)
            state.audio_bytes = audio_bytes
            state.audio_format = audio_format
        except AudioError as e:
            state.current_state = PipelineState.FAILED
            raise NonRetryableError(str(e)) from e
    
    # Validate audio
    try:
        validation = validate_audio(audio_bytes, audio_format)
        state.audio_duration_ms = validation.duration_ms
    except AudioError as e:
        state.current_state = PipelineState.FAILED
        raise NonRetryableError(str(e)) from e
    
    # Convert to WAV if needed (Whisper prefers WAV)
    if audio_format != "wav":
        try:
            state.audio_bytes = convert_to_wav(audio_bytes, audio_format)
            state.audio_format = "wav"
        except Exception as e:
            state.current_state = PipelineState.FAILED
            raise NonRetryableError(f"Audio conversion failed: {e}") from e
    
    # Success - transition to transcription
    state.current_state = PipelineState.TRANSCRIBING
    return state


async def _fetch_and_decode_audio(request: AudioInputRequest) -> tuple[bytes, str]:
    """
    Fetch audio from base64 or URL and detect format.
    
    Returns:
        Tuple of (audio_bytes, detected_format)
    """
    if request.audio_base64:
        # Decode base64
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
        except Exception as e:
            raise AudioError("AUDIO_INVALID_BASE64", "Invalid base64 encoding") from e
        
        # Detect format from magic bytes natively
        audio_format = detect_audio_format(audio_bytes)
        if not audio_format:
            raise AudioError("AUDIO_UNSUPPORTED_FORMAT", "Unsupported or unrecognized audio format")
        
    elif request.audio_url:
        # Fetch from URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request.audio_url)
            response.raise_for_status()
            audio_bytes = response.content
            
        # Detect format from Content-Type or magic bytes natively
        content_type = response.headers.get("content-type", "").lower()
        format_map = {
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/mp3": "mp3",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/m4a": "m4a",
            "audio/ogg": "ogg",
            "audio/webm": "webm",
            "audio/flac": "flac",
        }
        audio_format = format_map.get(content_type)
        if not audio_format:
            audio_format = detect_audio_format(audio_bytes)
            
        if not audio_format:
            raise AudioError("AUDIO_UNSUPPORTED_FORMAT", f"Unsupported audio format: {content_type}")
    else:
        raise AudioError("AUDIO_NO_INPUT", "No audio data provided (base64 or URL required)")
    
    # Check size
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > MAX_AUDIO_SIZE_MB:
        raise AudioError("AUDIO_TOO_LARGE", f"Audio file too large: {size_mb:.1f}MB (max {MAX_AUDIO_SIZE_MB}MB)")
    
    return audio_bytes, audio_format


# Exception classes for this stage
class NonRetryableError(Exception):
    """Permanent failure - should not be retried."""
    pass