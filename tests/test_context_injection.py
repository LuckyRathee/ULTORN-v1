"""
Tests for Context Injection Stage.
"""

import pytest
from ultron.state import StateData, PipelineState
from ultron.schemas import PipelineRun, TranscriptionResponse
from ultron.stages.context_injection import handle_context_injection


@pytest.mark.asyncio
async def test_handle_context_injection_stage():
    run = PipelineRun(session_id="test_sess_ci")
    state = StateData(run=run)
    state.transcription = TranscriptionResponse(text="What is the weather in Tokyo?", language="en", confidence=0.9, duration_ms=1000)
    state.current_state = PipelineState.CONTEXT_INJECTION

    next_state = await handle_context_injection(state)
    assert next_state.current_state == PipelineState.EXTRACTING_INTENT
    assert isinstance(next_state.retrieved_context, list)
    assert isinstance(next_state.session_history, list)
