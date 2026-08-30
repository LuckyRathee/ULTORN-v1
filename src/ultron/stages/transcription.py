"""
Stage 2: Transcription - Whisper STT (Groq API or local faster-whisper).

Converts audio bytes to text with confidence score and language detection.
"""

import time
from typing import Optional

from ..state.states import StateData, PipelineState
from ..schemas.api import TranscriptionResponse
from ..services.stt import transcribe_audio, STTError
from ..config import settings


async def handle_transcription(state: StateData) -> StateData:
    """
    Stage 2 handler: Transcribe audio to text using Whisper.
    
    Reads state.audio_bytes, calls STT service, stores result.
    
    Transitions:
    - Success (confidence >= threshold) -> EXTRACTING_INTENT
    - Low confidence -> FAILED (STT_LOW_CONFIDENCE)
    - No speech detected -> FAILED (STT_NO_SPEECH)
    - API error -> FAILED (STT_API_ERROR)
    
    Args:
        state: Current pipeline state with audio_bytes
        
    Returns:
        Updated state with transcription result
        
    Raises:
        RetryableError: For transient API failures (timeout, 5xx)
        NonRetryableError: For permanent failures (no speech, low confidence, auth)
    """
    if not state.audio_bytes:
        state.current_state = PipelineState.FAILED
        raise NonRetryableError("No audio data available for transcription")
    
    start_time = time.perf_counter()
    
    try:
        # Call STT service (Groq or local)
        result = await transcribe_audio(
            audio_bytes=state.audio_bytes,
            provider=settings.stt_provider,
            model=settings.whisper_model if settings.stt_provider == "local" else None,
        )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Check for no speech
        if not result.text or not result.text.strip():
            state.current_state = PipelineState.FAILED
            raise NonRetryableError("STT_NO_SPEECH: No speech detected in audio")
        
        # Check confidence threshold
        min_confidence = 0.3  # Configurable threshold
        if result.confidence < min_confidence:
            state.current_state = PipelineState.FAILED
            raise NonRetryableError(
                f"STT_LOW_CONFIDENCE: Transcription confidence {result.confidence:.2f} "
                f"below threshold {min_confidence}"
            )
        
        # Store transcription result
        state.transcription = TranscriptionResponse(
            text=result.text.strip(),
            language=result.language,
            confidence=result.confidence,
            duration_ms=state.audio_duration_ms or 0,
        )
        
        # Success - transition to context injection stage
        state.current_state = PipelineState.CONTEXT_INJECTION
        return state

        
    except STTError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Classify error type
        if e.error_type in ("timeout", "rate_limit", "server_error"):
            raise RetryableError(f"STT transient error: {e}") from e
        else:
            raise NonRetryableError(f"STT permanent error: {e}") from e
            
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise NonRetryableError(f"STT unexpected error: {e}") from e


# Exception classes for this stage
class RetryableError(Exception):
    """Transient failure - can be retried."""
    pass


class NonRetryableError(Exception):
    """Permanent failure - should not be retried."""
    pass
