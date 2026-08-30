"""
TTS Service - Text-to-speech via ElevenLabs or Azure.

Optional for v1 - can be disabled via config.
"""

import asyncio
import base64
from dataclasses import dataclass
from typing import Optional, Literal
import httpx

from ..config import settings
from ..utils.errors import UltronError


@dataclass
class TTSResult:
    """Result from TTS synthesis."""
    audio_base64: str
    format: str = "mp3"
    duration_ms: int = 0


class TTSError(UltronError):
    """TTS-specific error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_request", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "TTS_ERROR"
    user_message = "I couldn't generate the audio response."


async def synthesize_speech(
    text: str,
    provider: Literal["elevenlabs", "azure"] = "elevenlabs",
    voice_id: Optional[str] = None,
) -> str:
    """
    Synthesize speech from text.
    
    Args:
        text: Text to synthesize
        provider: "elevenlabs" or "azure"
        voice_id: Voice ID (provider-specific)
        
    Returns:
        Base64-encoded audio data (or URL in production)
        
    Raises:
        TTSError: With typed error_type
    """
    if provider == "elevenlabs":
        return await _synthesize_elevenlabs(text, voice_id)
    elif provider == "azure":
        return await _synthesize_azure(text, voice_id)
    else:
        raise TTSError(f"Unknown TTS provider: {provider}", "bad_request")


async def _synthesize_elevenlabs(text: str, voice_id: Optional[str]) -> str:
    """Synthesize using ElevenLabs API."""
    if not settings.elevenlabs_api_key:
        raise TTSError("ElevenLabs API key not configured", "auth")
    
    voice = voice_id or settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise TTSError("ElevenLabs API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise TTSError(f"ElevenLabs API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise TTSError("ElevenLabs API authentication failed", "auth")
    elif response.status_code == 429:
        raise TTSError("ElevenLabs API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise TTSError(f"ElevenLabs API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise TTSError(f"ElevenLabs API error: {response.text}", "bad_request")
    
    # Return base64-encoded audio
    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return audio_base64


async def _synthesize_azure(text: str, voice_id: Optional[str]) -> str:
    """Synthesize using Azure Cognitive Services Speech."""
    if not settings.azure_tts_key or not settings.azure_tts_region:
        raise TTSError("Azure TTS credentials not configured", "auth")
    
    # Azure TTS uses a different API - this is a simplified version
    # In production, use the azure-cognitiveservices-speech SDK
    url = f"https://{settings.azure_tts_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_tts_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "Ultron-2.0",
    }
    
    voice = voice_id or "en-US-JennyNeural"
    
    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="{voice}">{text}</voice>
    </speak>"""
    
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
        except httpx.TimeoutException as e:
            raise TTSError("Azure TTS API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise TTSError(f"Azure TTS API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise TTSError("Azure TTS authentication failed", "auth")
    elif response.status_code == 429:
        raise TTSError("Azure TTS rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise TTSError(f"Azure TTS server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise TTSError(f"Azure TTS error: {response.text}", "bad_request")
    
    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return audio_base64
