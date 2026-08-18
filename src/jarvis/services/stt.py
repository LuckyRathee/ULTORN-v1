"""
STT Service - Whisper transcription via Groq API or local faster-whisper.

Provides unified interface with typed errors and explicit timeouts.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Literal
import httpx

from ..config import settings
from ..utils.errors import JarvisError


@dataclass
class STTResult:
    """Result from transcription."""
    text: str
    language: str
    confidence: float
    duration_ms: int


class STTError(JarvisError):
    """STT-specific error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_request", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "STT_ERROR"
    user_message = "I had trouble transcribing the audio. Please try again."


async def transcribe_audio(
    audio_bytes: bytes,
    provider: Literal["groq", "local"] = "groq",
    model: Optional[str] = None,
) -> STTResult:
    """
    Transcribe audio bytes to text.
    
    Args:
        audio_bytes: Raw audio data (WAV format preferred)
        provider: "groq" for Groq Whisper API, "local" for faster-whisper
        model: Model name (for local: tiny, base, small, medium, large)
        
    Returns:
        STTResult with text, language, confidence, duration
        
    Raises:
        STTError: With typed error_type for handling
    """
    if provider == "groq":
        return await _transcribe_groq(audio_bytes)
    elif provider == "local":
        return await _transcribe_local(audio_bytes, model or "base")
    else:
        raise STTError(f"Unknown STT provider: {provider}", "bad_request")


async def _transcribe_groq(audio_bytes: bytes) -> STTResult:
    """Transcribe using Groq Whisper API."""
    if not settings.groq_api_key:
        raise STTError("Groq API key not configured", "auth")
    
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    
    # Prepare multipart form data
    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
        "model": (None, "whisper-large-v3"),
        "response_format": (None, "verbose_json"),
        "temperature": (None, "0"),
    }
    
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, files=files)
        except httpx.TimeoutException as e:
            raise STTError("Groq API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise STTError(f"Groq API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise STTError("Groq API authentication failed", "auth")
    elif response.status_code == 429:
        raise STTError("Groq API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise STTError(f"Groq API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise STTError(f"Groq API error: {response.text}", "bad_request")
    
    try:
        data = response.json()
    except Exception as e:
        raise STTError(f"Invalid JSON response: {e}", "server_error") from e
    
    # Extract fields from verbose_json response
    text = data.get("text", "").strip()
    language = data.get("language", "en")
    
    # Calculate confidence from segments if available
    segments = data.get("segments", [])
    if segments:
        avg_confidence = sum(s.get("avg_logprob", 0) for s in segments) / len(segments)
        # Convert logprob to 0-1 confidence (rough approximation)
        confidence = max(0.0, min(1.0, (avg_confidence + 1.0) / 1.0))
    else:
        confidence = 0.8  # Default if no segments
    
    # Duration from audio (approximate)
    duration_ms = data.get("duration", 0) * 1000
    
    return STTResult(
        text=text,
        language=language,
        confidence=confidence,
        duration_ms=int(duration_ms),
    )


async def _transcribe_local(audio_bytes: bytes, model: str) -> STTResult:
    """Transcribe using local faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise STTError("faster-whisper not installed", "bad_request")
    
    # Run in thread pool since faster-whisper is blocking
    loop = asyncio.get_event_loop()
    
    def _transcribe_sync() -> STTResult:
        # Load model (cached in production)
        whisper_model = WhisperModel(model, device="cpu", compute_type="int8")
        
        # Write audio to temp file (faster-whisper needs file path)
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            segments, info = whisper_model.transcribe(tmp_path, beam_size=5)
            
            # Collect all segments
            text_parts = []
            total_logprob = 0.0
            segment_count = 0
            
            for segment in segments:
                text_parts.append(segment.text)
                if segment.avg_logprob is not None:
                    total_logprob += segment.avg_logprob
                    segment_count += 1
            
            text = " ".join(text_parts).strip()
            language = info.language
            
            # Calculate confidence
            if segment_count > 0:
                avg_logprob = total_logprob / segment_count
                confidence = max(0.0, min(1.0, (avg_logprob + 1.0) / 1.0))
            else:
                confidence = 0.5
            
            duration_ms = int(info.duration * 1000) if info.duration else 0
            
            return STTResult(
                text=text,
                language=language,
                confidence=confidence,
                duration_ms=duration_ms,
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    
    try:
        return await loop.run_in_executor(None, _transcribe_sync)
    except Exception as e:
        raise STTError(f"Local transcription failed: {e}", "server_error") from e