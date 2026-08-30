"""
Unit tests for Ultron 2.0 Conversational Memory package.
"""

import pytest
from datetime import datetime
from ultron.memory.models import ConversationTurn, MemoryEntry
from ultron.memory.embeddings import EmbeddingService
from ultron.memory.vector_store import ChromaMemoryStore
from ultron.memory.session_store import SessionStore
from ultron.memory.salience import evaluate_salience, turn_to_memory_entry


def test_embedding_service():
    service = EmbeddingService()
    vec = service.embed_text("Hello Ultron memory test")
    assert isinstance(vec, list)
    assert len(vec) == 384


def test_session_store_fallback():
    store = SessionStore()
    turn = ConversationTurn(
        session_id="test_sess_1",
        user_query="What is the weather in Tokyo?",
        assistant_response="It is sunny in Tokyo.",
        intent_type="weather"
    )
    store.add_turn(turn)
    turns = store.get_recent_turns("test_sess_1", limit=5)
    assert len(turns) == 1
    assert turns[0].user_query == "What is the weather in Tokyo?"


def test_vector_store():
    vstore = ChromaMemoryStore()
    mem = MemoryEntry(
        session_id="test_sess_1",
        content="User prefers Tokyo weather in Japanese",
        user_query="Prefer Tokyo weather",
        assistant_response="Understood"
    )
    assert vstore.add_memory(mem) is True

    results = vstore.search_similar("Tokyo weather", top_k=1)
    assert len(results) >= 1


def test_salience_scoring():
    turn_high = ConversationTurn(
        session_id="s1",
        user_query="My favorite city is Tokyo",
        assistant_response="I will remember your favorite city is Tokyo."
    )
    score_high = evaluate_salience(turn_high)
    assert score_high >= 0.5

    turn_low = ConversationTurn(
        session_id="s1",
        user_query="hi",
        assistant_response="Hello!"
    )
    score_low = evaluate_salience(turn_low)
    assert score_low < 0.5
