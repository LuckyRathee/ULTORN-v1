"""
Tests for Memory Retrieval Accuracy.
"""

import pytest
from ultron.memory.models import ConversationTurn, MemoryEntry
from ultron.memory.stores import get_session_store, get_vector_store, reset_stores
from ultron.memory.embeddings import EmbeddingService
from ultron.memory.salience import evaluate_salience


@pytest.mark.asyncio
async def test_vector_store_search_accuracy():
    """Test that vector store returns relevant memories for queries."""
    reset_stores()
    store = get_vector_store()
    
    # Add test memories
    memories = [
        MemoryEntry(
            session_id="test_session",
            content="User prefers coffee in the morning",
            user_query="I like coffee",
            assistant_response="Noted, you prefer coffee in the morning",
            intent_type="preference",
        ),
        MemoryEntry(
            session_id="test_session",
            content="User lives in San Francisco",
            user_query="I live in San Francisco",
            assistant_response="Got it, you're in San Francisco",
            intent_type="location",
        ),
        MemoryEntry(
            session_id="test_session",
            content="User has a meeting at 10 AM tomorrow",
            user_query="Schedule meeting for 10 AM",
            assistant_response="Meeting scheduled for 10 AM tomorrow",
            intent_type="calendar_create",
        ),
    ]
    
    for mem in memories:
        store.add_memory(mem)
    
    # Search for coffee preference
    results = store.search_similar("coffee", top_k=5, session_id="test_session")
    assert len(results) >= 1
    assert any("coffee" in r.content.lower() for r in results)
    
    # Search for location
    results = store.search_similar("San Francisco", top_k=5, session_id="test_session")
    assert len(results) >= 1
    assert any("san francisco" in r.content.lower() for r in results)
    
    # Search for meeting
    results = store.search_similar("meeting tomorrow", top_k=5, session_id="test_session")
    assert len(results) >= 1
    assert any("meeting" in r.content.lower() for r in results)



@pytest.mark.asyncio
async def test_session_store_recent_turns():
    """Test session store returns most recent turns in order."""
    reset_stores()
    store = get_session_store()
    
    turns = [
        ConversationTurn(session_id="test_sess", user_query="First", assistant_response="Response 1"),
        ConversationTurn(session_id="test_sess", user_query="Second", assistant_response="Response 2"),
        ConversationTurn(session_id="test_sess", user_query="Third", assistant_response="Response 3"),
        ConversationTurn(session_id="test_sess", user_query="Fourth", assistant_response="Response 4"),
        ConversationTurn(session_id="test_sess", user_query="Fifth", assistant_response="Response 5"),
    ]
    
    for turn in turns:
        store.add_turn(turn)
    
    # Get recent 3
    recent = store.get_recent_turns("test_sess", limit=3)
    assert len(recent) == 3
    assert recent[0].user_query == "Third"
    assert recent[1].user_query == "Fourth"
    assert recent[2].user_query == "Fifth"


@pytest.mark.asyncio
async def test_embedding_consistency():
    """Test that embeddings are consistent for same text."""
    service = EmbeddingService()
    
    vec1 = service.embed_text("Hello world")
    vec2 = service.embed_text("Hello world")
    
    assert vec1 == vec2
    assert len(vec1) == 384


@pytest.mark.asyncio
async def test_salience_high_for_preferences():
    """Test that preference statements get high salience scores."""
    turn = ConversationTurn(
        session_id="s1",
        user_query="My favorite color is blue",
        assistant_response="Noted, your favorite color is blue.",
    )
    score = evaluate_salience(turn)
    assert score >= 0.5


@pytest.mark.asyncio
async def test_salience_low_for_greetings():
    """Test that simple greetings get low salience scores."""
    turn = ConversationTurn(
        session_id="s1",
        user_query="Hi",
        assistant_response="Hello!",
    )
    score = evaluate_salience(turn)
    assert score < 0.5


@pytest.mark.asyncio
async def test_salience_high_for_calendar_tasks():
    """Test that calendar/task creation gets high salience."""
    turn = ConversationTurn(
        session_id="s1",
        user_query="Create a meeting for tomorrow at 2pm",
        assistant_response="Meeting created for tomorrow at 2pm.",
        intent_type="calendar_create",
    )
    score = evaluate_salience(turn)
    assert score >= 0.5


@pytest.mark.asyncio
async def test_cross_session_isolation():
    """Test that memories don't leak across sessions."""
    reset_stores()
    store = get_vector_store()
    
    mem1 = MemoryEntry(
        session_id="session_a",
        content="User A likes pizza",
        user_query="I like pizza",
        assistant_response="Noted",
    )
    mem2 = MemoryEntry(
        session_id="session_b",
        content="User B likes burgers",
        user_query="I like burgers",
        assistant_response="Noted",
    )
    
    store.add_memory(mem1)
    store.add_memory(mem2)
    
    # Search in session_a should only find pizza
    results_a = store.search_similar("pizza", top_k=5, session_id="session_a")
    assert len(results_a) >= 1
    assert all(r.session_id == "session_a" for r in results_a)
    
    # Search in session_b should only find burgers
    results_b = store.search_similar("burgers", top_k=5, session_id="session_b")
    assert len(results_b) >= 1
    assert all(r.session_id == "session_b" for r in results_b)
