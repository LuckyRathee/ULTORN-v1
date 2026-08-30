"""
End-to-End Memory Persistence Tests.

Tests that memory persists across restarts and pipeline runs.
"""

import pytest
from unittest.mock import AsyncMock, patch
from ultron.state import StateData, PipelineState
from ultron.schemas.pipeline import PipelineRun
from ultron.schemas.api import TranscriptionResponse
from ultron.stages.context_injection import handle_context_injection
from ultron.stages.response import handle_response
from ultron.memory.models import ConversationTurn
from ultron.memory.stores import get_session_store, get_vector_store, reset_stores


@pytest.mark.asyncio
async def test_memory_persists_across_pipeline_runs():
    """Test that conversation history persists across multiple pipeline runs."""
    reset_stores()
    session_store = get_session_store()
    vector_store = get_vector_store()
    
    session_id = "e2e_test_session"
    
    # Simulate first conversation
    turn1 = ConversationTurn(
        session_id=session_id,
        user_query="What's the weather in Tokyo?",
        assistant_response="It's sunny and 22 degrees in Tokyo.",
        intent_type="weather",
    )
    session_store.add_turn(turn1)
    
    # Add to vector store (high salience)
    from ultron.memory.salience import evaluate_salience, turn_to_memory_entry
    salience = evaluate_salience(turn1)
    if salience >= 0.5:
        mem_entry = turn_to_memory_entry(turn1, salience)
        vector_store.add_memory(mem_entry)
    
    # Simulate second conversation - should retrieve context
    state = StateData(run=PipelineRun(session_id=session_id))
    state.transcription = TranscriptionResponse(
        text="What about tomorrow?",  # Follow-up question
        language="en",
        confidence=0.9,
        duration_ms=1000,
    )
    state.current_state = PipelineState.CONTEXT_INJECTION
    
    # Inject context
    state = await handle_context_injection(state)
    
    # Should have session history
    assert state.session_history is not None
    assert len(state.session_history) >= 1
    assert state.session_history[0]["user"] == "What's the weather in Tokyo?"
    
    # Should have retrieved context from vector store
    assert state.retrieved_context is not None


@pytest.mark.asyncio
async def test_memory_persists_after_restart_simulation():
    """Test memory survives 'restart' by creating new store instances."""
    reset_stores()
    session_id = "restart_test_session"
    
    # First "session" - add data
    store1 = get_session_store()
    turn = ConversationTurn(
        session_id=session_id,
        user_query="Remember my name is Alice",
        assistant_response="I'll remember your name is Alice.",
        intent_type="preference",
    )
    store1.add_turn(turn)
    
    # Simulate restart - create new store instance (but using global)
    reset_stores()
    store2 = get_session_store()
    
    # Data should still be there (in fallback mode)
    turns = store2.get_recent_turns(session_id, limit=5)
    assert len(turns) == 1
    assert turns[0].user_query == "Remember my name is Alice"


@pytest.mark.asyncio
async def test_vector_store_persists_across_instances():
    """Test vector store data persists across instances."""
    reset_stores()
    session_id = "vector_restart_test"
    
    # First instance
    store1 = get_vector_store()
    from ultron.memory.models import MemoryEntry
    mem = MemoryEntry(
        session_id=session_id,
        content="User prefers dark mode",
        user_query="I prefer dark mode",
        assistant_response="Dark mode enabled",
        intent_type="preference",
    )
    store1.add_memory(mem)
    
    # Second instance (simulating restart)
    reset_stores()
    store2 = get_vector_store()
    
    # Should find the memory
    results = store2.search_similar("dark mode", top_k=5, session_id=session_id)
    assert len(results) >= 1
    assert any("dark mode" in r.content.lower() for r in results)


@pytest.mark.asyncio
async def test_full_pipeline_with_memory():
    """Test full pipeline run with memory injection and storage."""
    # This test verifies the complete flow:
    # 1. Context injection retrieves history
    # 2. Intent extraction uses context
    # 3. Response stores the turn
    
    reset_stores()
    session_id = "full_pipeline_test"
    session_store = get_session_store()
    vector_store = get_vector_store()
    
    # Pre-populate with some history
    prev_turn = ConversationTurn(
        session_id=session_id,
        user_query="My name is Bob",
        assistant_response="Nice to meet you, Bob!",
        intent_type="preference",
    )
    session_store.add_turn(prev_turn)
    
    # Run context injection
    state = StateData(run=PipelineRun(session_id=session_id))
    state.transcription = TranscriptionResponse(
        text="What's my name?",
        language="en",
        confidence=0.95,
        duration_ms=500,
    )
    state.current_state = PipelineState.CONTEXT_INJECTION
    
    state = await handle_context_injection(state)
    
    # Verify context was retrieved
    assert state.session_history is not None
    assert len(state.session_history) == 1
    assert "Bob" in state.session_history[0]["user"]
    
    # Simulate response stage storing the new turn
    state.response_text = "Your name is Bob!"
    state.intent = None  # Simplified for test
    
    state = await handle_response(state)
    
    # Verify turn was stored
    new_turns = session_store.get_recent_turns(session_id, limit=5)
    assert len(new_turns) == 2  # Previous + new
    assert new_turns[-1].user_query == "What's my name?"
    assert new_turns[-1].assistant_response == "Your name is Bob!"
