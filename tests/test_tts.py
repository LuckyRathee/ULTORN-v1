"""
TTS Service Integration Tests.

Tests for ElevenLabs and Azure TTS integration including error paths.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import base64

from src.ultron.services.tts import synthesize_speech, TTSError
from src.ultron.config import settings


class TestTTSService:
    """Test TTS service with mocked HTTP responses."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient."""
        with patch("src.ultron.services.tts.httpx.AsyncClient") as mock_client:
            yield mock_client

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_success(self, mock_httpx_client):
        """Test successful ElevenLabs synthesis."""
        # Create fake audio data
        fake_audio = b"fake_audio_data"
        fake_audio_b64 = base64.b64encode(fake_audio).decode("utf-8")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_audio
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.elevenlabs_api_key
        original_voice_id = settings.elevenlabs_voice_id
        settings.elevenlabs_api_key = "test-api-key"
        settings.elevenlabs_voice_id = "test-voice-id"
        
        try:
            result = await synthesize_speech("Hello world", provider="elevenlabs")
            
            assert result == fake_audio_b64
        finally:
            settings.elevenlabs_api_key = original_api_key
            settings.elevenlabs_voice_id = original_voice_id

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_no_api_key(self):
        """Test error when ElevenLabs API key not configured."""
        original_api_key = settings.elevenlabs_api_key
        settings.elevenlabs_api_key = None
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="elevenlabs")
            
            assert exc_info.value.error_type == "auth"
            assert "not configured" in str(exc_info.value).lower()
        finally:
            settings.elevenlabs_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_timeout(self, mock_httpx_client):
        """Test timeout error handling."""
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.elevenlabs_api_key
        settings.elevenlabs_api_key = "test-api-key"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="elevenlabs")
            
            assert exc_info.value.error_type == "timeout"
        finally:
            settings.elevenlabs_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_401_auth_failure(self, mock_httpx_client):
        """Test 401 authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.elevenlabs_api_key
        settings.elevenlabs_api_key = "test-api-key"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="elevenlabs")
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.elevenlabs_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_429_rate_limit(self, mock_httpx_client):
        """Test 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.elevenlabs_api_key
        settings.elevenlabs_api_key = "test-api-key"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="elevenlabs")
            
            assert exc_info.value.error_type == "rate_limit"
        finally:
            settings.elevenlabs_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_500_server_error(self, mock_httpx_client):
        """Test 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.elevenlabs_api_key
        settings.elevenlabs_api_key = "test-api-key"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="elevenlabs")
            
            assert exc_info.value.error_type == "server_error"
        finally:
            settings.elevenlabs_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_synthesize_azure_success(self, mock_httpx_client):
        """Test successful Azure TTS synthesis."""
        fake_audio = b"fake_azure_audio"
        fake_audio_b64 = base64.b64encode(fake_audio).decode("utf-8")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_audio
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_key = settings.azure_tts_key
        original_region = settings.azure_tts_region
        settings.azure_tts_key = "test-key"
        settings.azure_tts_region = "eastus"
        
        try:
            result = await synthesize_speech("Hello world", provider="azure")
            
            assert result == fake_audio_b64
        finally:
            settings.azure_tts_key = original_key
            settings.azure_tts_region = original_region

    @pytest.mark.asyncio
    async def test_synthesize_azure_no_credentials(self):
        """Test error when Azure credentials not configured."""
        original_key = settings.azure_tts_key
        original_region = settings.azure_tts_region
        settings.azure_tts_key = None
        settings.azure_tts_region = None
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="azure")
            
            assert exc_info.value.error_type == "auth"
            assert "not configured" in str(exc_info.value).lower()
        finally:
            settings.azure_tts_key = original_key
            settings.azure_tts_region = original_region

    @pytest.mark.asyncio
    async def test_synthesize_azure_timeout(self, mock_httpx_client):
        """Test Azure timeout error handling."""
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_key = settings.azure_tts_key
        original_region = settings.azure_tts_region
        settings.azure_tts_key = "test-key"
        settings.azure_tts_region = "eastus"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="azure")
            
            assert exc_info.value.error_type == "timeout"
        finally:
            settings.azure_tts_key = original_key
            settings.azure_tts_region = original_region

    @pytest.mark.asyncio
    async def test_synthesize_azure_401_auth_failure(self, mock_httpx_client):
        """Test Azure 401 authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_key = settings.azure_tts_key
        original_region = settings.azure_tts_region
        settings.azure_tts_key = "test-key"
        settings.azure_tts_region = "eastus"
        
        try:
            with pytest.raises(TTSError) as exc_info:
                await synthesize_speech("Hello", provider="azure")
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.azure_tts_key = original_key
            settings.azure_tts_region = original_region

    @pytest.mark.asyncio
    async def test_synthesize_unknown_provider(self):
        """Test error for unknown provider."""
        with pytest.raises(TTSError) as exc_info:
            await synthesize_speech("Hello", provider="unknown")
        
        assert exc_info.value.error_type == "bad_request"
        assert "unknown" in str(exc_info.value).lower()


class TestTTSError:
    """Test TTSError exception class."""

    def test_tts_error_attributes(self):
        """Test TTSError has correct attributes."""
        error = TTSError("Test message", "timeout")
        
        assert error.error_type == "timeout"
        assert error.code == "TTS_ERROR"
        assert error.user_message == "I couldn't generate the audio response."
        assert str(error) == "Test message"

    def test_tts_error_types(self):
        """Test all valid error types."""
        valid_types = ["timeout", "rate_limit", "server_error", "auth", "bad_request", "unknown"]
        
        for error_type in valid_types:
            error = TTSError("Test", error_type)
            assert error.error_type == error_type
