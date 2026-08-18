"""
End-to-End Pipeline Integration Tests.

Tests the full pipeline: audio → transcription → intent extraction → action execution → response.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timezone

from src.jarvis.main import app
from src.jarvis.state.machine import StateMachine
from src.jarvis.state.states import StateData, PipelineState
from src.jarvis.schemas.intent import Intent, IntentType, WeatherIntent
from src.jarvis.schemas.api import AudioInputRequest, PipelineResponse
from src.jarvis.config import settings
from fastapi.testclient import TestClient


class TestE2EPipeline:
    """Test full pipeline integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_all_services(self):
        """Mock all external services."""
        with patch("src.jarvis.stages.audio_input.validate_and_convert_audio") as mock_audio, \
             patch("src.jarvis.stages.transcription.transcribe_audio") as mock_transcribe, \
             patch("src.jarvis.stages.intent_extraction.extract_intent") as mock_intent, \
             patch("src.jarvis.stages.action_execution.handle_action_execution") as mock_action, \
             patch("src.jarvis.stages.response.format_response") as mock_response, \
             patch("src.jarvis.persistence.supabase.log_pipeline_run") as mock_log:
            
            yield {
                "audio": mock_audio,
                "transcribe": mock_transcribe,
                "intent": mock_intent,
                "action": mock_action,
                "response": mock_response,
                "log": mock_log
            }

    def test_health_endpoint(self, client):
        """Test health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_full_pipeline_weather_intent(self, mock_all_services):
        """Test full pipeline with weather intent."""
        # Setup mocks
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].return_value = "What's the weather in London?"
        mock_all_services["intent"].return_value = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            units="metric",
            confidence=0.95
        )
        mock_all_services["action"].return_value = StateData(
            current_state=PipelineState.RESPONDING,
            action_result=MagicMock(
                success=True,
                data={"location": "London, UK", "temperature": 15.5, "condition": "Cloudy"},
                error=None,
                error_type=None,
                latency_ms=100
            )
        )
        mock_all_services["response"].return_value = "The weather in London is 15.5°C and Cloudy."
        mock_all_services["log"].return_value = "run-123"

        # Create state machine and run
        machine = StateMachine()
        state = StateData(
            session_id="test-session",
            audio_base64="fake_base64_audio"
        )
        
        result = await machine.run(state)
        
        assert result.current_state == PipelineState.DONE
        assert result.final_response == "The weather in London is 15.5°C and Cloudy."
        assert result.action_result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_handles_transcription_failure(self, mock_all_services):
        """Test pipeline handles transcription failure gracefully."""
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].side_effect = Exception("STT failed")
        mock_all_services["log"].return_value = "run-123"

        machine = StateMachine()
        state = StateData(
            session_id="test-session",
            audio_base64="fake_base64_audio"
        )
        
        result = await machine.run(state)
        
        assert result.current_state == PipelineState.FAILED
        assert "failed" in result.final_response.lower() or "error" in result.final_response.lower()

    @pytest.mark.asyncio
    async def test_pipeline_handles_low_confidence_intent(self, mock_all_services):
        """Test pipeline handles low confidence intent."""
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].return_value = "Some unclear audio"
        mock_all_services["intent"].return_value = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.3
        )
        mock_all_services["log"].return_value = "run-123"

        machine = StateMachine()
        state = StateData(
            session_id="test-session",
            audio_base64="fake_base64_audio"
        )
        
        result = await machine.run(state)
        
        assert result.current_state == PipelineState.FAILED
        assert result.intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_pipeline_handles_action_failure(self, mock_all_services):
        """Test pipeline handles action execution failure."""
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].return_value = "What's the weather in London?"
        mock_all_services["intent"].return_value = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            units="metric",
            confidence=0.95
        )
        mock_all_services["action"].return_value = StateData(
            current_state=PipelineState.FAILED,
            action_result=MagicMock(
                success=False,
                data=None,
                error="Weather API timeout",
                error_type="timeout",
                latency_ms=5000
            )
        )
        mock_all_services["response"].return_value = "I couldn't retrieve the weather information."
        mock_all_services["log"].return_value = "run-123"

        machine = StateMachine()
        state = StateData(
            session_id="test-session",
            audio_base64="fake_base64_audio"
        )
        
        result = await machine.run(state)
        
        assert result.current_state == PipelineState.DONE  # Response stage still runs
        assert "couldn't retrieve" in result.final_response.lower()

    def test_process_audio_endpoint_mock(self, client, mock_all_services):
        """Test /api/v1/process-audio endpoint with mocked pipeline."""
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].return_value = "What's the weather in London?"
        mock_all_services["intent"].return_value = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            units="metric",
            confidence=0.95
        )
        mock_all_services["action"].return_value = StateData(
            current_state=PipelineState.RESPONDING,
            action_result=MagicMock(
                success=True,
                data={"location": "London, UK", "temperature": 15.5, "condition": "Cloudy"},
                error=None,
                error_type=None,
                latency_ms=100
            )
        )
        mock_all_services["response"].return_value = "The weather in London is 15.5°C and Cloudy."
        mock_all_services["log"].return_value = "run-123"

        response = client.post(
            "/api/v1/process-audio",
            json={"audio_base64": "fake_base64", "session_id": "test-session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "London" in data["response"]
        assert data["run_id"] == "run-123"

    def test_process_audio_endpoint_invalid_input(self, client):
        """Test endpoint with invalid input."""
        response = client.post(
            "/api/v1/process-audio",
            json={"session_id": "test-session"}  # Missing audio
        )
        
        assert response.status_code == 422  # Validation error

    def test_process_audio_file_endpoint_mock(self, client, mock_all_services):
        """Test /api/v1/process-audio/file endpoint with mocked pipeline."""
        mock_all_services["audio"].return_value = b"fake_wav_data"
        mock_all_services["transcribe"].return_value = "What's the weather in London?"
        mock_all_services["intent"].return_value = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            units="metric",
            confidence=0.95
        )
        mock_all_services["action"].return_value = StateData(
            current_state=PipelineState.RESPONDING,
            action_result=MagicMock(
                success=True,
                data={"location": "London, UK", "temperature": 15.5, "condition": "Cloudy"},
                error=None,
                error_type=None,
                latency_ms=100
            )
        )
        mock_all_services["response"].return_value = "The weather in London is 15.5°C and Cloudy."
        mock_all_services["log"].return_value = "run-123"

        # Create a fake WAV file
        fake_wav = b"RIFF" + b"\x00" * 44  # Minimal WAV header
        
        response = client.post(
            "/api/v1/process-audio/file",
            files={"audio_file": ("test.wav", fake_wav, "audio/wav")},
            data={"session_id": "test-session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "London" in data["response"]


class TestStateMachineTransitions:
    """Test state machine transitions explicitly."""

    @pytest.mark.asyncio
    async def test_state_transitions_order(self):
        """Test that states transition in correct order."""
        from src.jarvis.stages.audio_input import handle_audio_input
        from src.jarvis.stages.transcription import handle_transcription
        from src.jarvis.stages.intent_extraction import handle_intent_extraction
        from src.jarvis.stages.action_execution import handle_action_execution
        from src.jarvis.stages.response import handle_response

        state = StateData(session_id="test", audio_base64="fake")
        
        # Stage 1: Audio input
        state = await handle_audio_input(state)
        assert state.current_state == PipelineState.TRANSCRIBING
        assert state.audio_bytes is not None
        
        # Stage 2: Transcription
        state.transcription = "test transcription"
        state = await handle_transcription(state)
        assert state.current_state == PipelineState.EXTRACTING_INTENT
        assert state.transcription == "test transcription"
        
        # Stage 3: Intent extraction
        state = await handle_intent_extraction(state)
        assert state.current_state in [PipelineState.CONFIRMING_INTENT, PipelineState.EXECUTING]
        assert state.intent is not None
        
        # Stage 4: Action execution (if not UNKNOWN)
        if state.intent.type != IntentType.UNKNOWN:
            state = await handle_action_execution(state)
            assert state.current_state in [PipelineState.RESPONDING, PipelineState.FAILED]
        
        # Stage 5: Response
        state = await handle_response(state)
        assert state.current_state in [PipelineState.DONE, PipelineState.FAILED]
        assert state.final_response is not None


class TestErrorPropagation:
    """Test error propagation through pipeline."""

    @pytest.mark.asyncio
    async def test_audio_input_error_propagates(self):
        """Test audio input error propagates to FAILED state."""
        from src.jarvis.stages.audio_input import handle_audio_input
        from src.jarvis.utils.errors import AudioError
        
        state = StateData(session_id="test", audio_base64="invalid_base64!!!")
        
        with pytest.raises(AudioError):
            await handle_audio_input(state)
        
        assert state.current_state == PipelineState.FAILED

    @pytest.mark.asyncio
    async def test_intent_extraction_error_propagates(self):
        """Test intent extraction error propagates."""
        from src.jarvis.stages.intent_extraction import handle_intent_extraction
        from src.jarvis.utils.errors import LLMError
        
        state = StateData(
            session_id="test",
            transcription=""  # Empty transcription should fail
        )
        
        with pytest.raises(LLMError):
            await handle_intent_extraction(state)
        
        assert state.current_state == PipelineState.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])