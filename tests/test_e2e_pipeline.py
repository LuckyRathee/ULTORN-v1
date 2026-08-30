"""
End-to-End Pipeline Integration Tests.

Tests the full pipeline: audio → transcription → context injection → intent extraction → action execution → response.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timezone

from src.ultron.main import app
from src.ultron.state.machine import StateMachine
from src.ultron.state.states import StateData, PipelineState
from src.ultron.schemas.intent import Intent, IntentType, WeatherIntent
from src.ultron.schemas.pipeline import PipelineRun
from src.ultron.schemas.api import AudioInputRequest, PipelineResponse, TranscriptionResponse
from src.ultron.config import settings
from fastapi.testclient import TestClient


class TestE2EPipeline:
    """Test full pipeline integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data

    def test_process_audio_endpoint_invalid_input(self, client):
        """Test endpoint with invalid input format."""
        response = client.post(
            "/api/v1/process-audio",
            json={"session_id": "test-session"}  # Missing audio_base64 or audio_url
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"


class TestStateMachineTransitions:
    """Test state machine transitions explicitly."""

    @pytest.mark.asyncio
    async def test_state_transitions_order(self):
        """Test that states transition in correct order."""
        from src.ultron.stages.context_injection import handle_context_injection

        run = PipelineRun(session_id="test_e2e")
        state = StateData(run=run)
        state.transcription = TranscriptionResponse(text="What is the weather?", language="en", confidence=0.9, duration_ms=1000)
        state.current_state = PipelineState.CONTEXT_INJECTION

        state = await handle_context_injection(state)
        assert state.current_state == PipelineState.EXTRACTING_INTENT
        assert state.retrieved_context is not None


class TestErrorPropagation:
    """Test error propagation through pipeline."""

    @pytest.mark.asyncio
    async def test_intent_extraction_no_transcription(self):
        """Test intent extraction fails when no transcription is available."""
        from src.ultron.stages.intent_extraction import handle_intent_extraction, NonRetryableError

        run = PipelineRun(session_id="test_err")
        state = StateData(run=run)
        state.transcription = None
        state.current_state = PipelineState.EXTRACTING_INTENT

        with pytest.raises(NonRetryableError):
            await handle_intent_extraction(state)

        assert state.current_state == PipelineState.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
