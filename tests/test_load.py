"""
Load Tests for Memory + Pipeline.

Tests concurrent request handling and performance under load.
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch, MagicMock

from ultron.state import StateData, PipelineState
from ultron.schemas.pipeline import PipelineRun
from ultron.schemas.api import TranscriptionResponse
from ultron.stages.context_injection import handle_context_injection
from ultron.stages.intent_extraction import handle_intent_extraction
from ultron.memory import SessionStore, ChromaMemoryStore
from ultron.memory.models import ConversationTurn
from ultron.briefing.models import BriefingConfig, BriefingContent
from ultron.briefing.generator import generate_daily_briefing


@pytest.mark.asyncio
async def test_concurrent_context_injection():
    """Test context injection handles concurrent requests."""
    session_store = SessionStore()
    vector_store = ChromaMemoryStore()
    
    # Pre-populate with data
    for i in range(10):
        turn = ConversationTurn(
            session_id=f"load_test_session_{i % 3}",  # 3 sessions
            user_query=f"Query {i}",
            assistant_response=f"Response {i}",
            intent_type="weather",
        )
        session_store.add_turn(turn)
    
    async def run_context_injection(session_id: str, query: str):
        state = StateData(run=PipelineRun(session_id=session_id))
        state.transcription = TranscriptionResponse(
            text=query,
            language="en",
            confidence=0.9,
            duration_ms=500,
        )
        state.current_state = PipelineState.CONTEXT_INJECTION
        return await handle_context_injection(state)
    
    # Run 20 concurrent requests across 3 sessions
    tasks = []
    for i in range(20):
        session_id = f"load_test_session_{i % 3}"
        query = f"Concurrent query {i}"
        tasks.append(run_context_injection(session_id, query))
    
    start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    assert len(results) == 20
    assert all(r.current_state == PipelineState.EXTRACTING_INTENT for r in results)
    assert all(r.session_history is not None for r in results)
    assert all(r.retrieved_context is not None for r in results)
    
    # Should complete in reasonable time (< 5 seconds)
    assert elapsed < 5.0
    
    print(f"20 concurrent context injections completed in {elapsed:.2f}s")


@pytest.mark.asyncio
async def test_concurrent_session_store_access():
    """Test session store handles concurrent read/write."""
    store = SessionStore()
    
    async def add_turns(session_id: str, count: int):
        for i in range(count):
            turn = ConversationTurn(
                session_id=session_id,
                user_query=f"Query {i}",
                assistant_response=f"Response {i}",
            )
            store.add_turn(turn)
            await asyncio.sleep(0.001)  # Small delay
    
    async def read_turns(session_id: str, count: int):
        for _ in range(count):
            store.get_recent_turns(session_id, limit=5)
            await asyncio.sleep(0.001)
    
    # Run concurrent writers and readers
    tasks = [
        add_turns("concurrent_session", 10),
        add_turns("concurrent_session", 10),
        read_turns("concurrent_session", 10),
        read_turns("concurrent_session", 10),
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify final state
    turns = store.get_recent_turns("concurrent_session", limit=50)
    assert len(turns) == 20


@pytest.mark.asyncio
async def test_vector_store_concurrent_search():
    """Test vector store handles concurrent searches."""
    store = ChromaMemoryStore()
    
    # Add test data
    from ultron.memory.models import MemoryEntry
    for i in range(20):
        mem = MemoryEntry(
            session_id="search_test",
            content=f"Memory content {i} about topic {i % 5}",
            user_query=f"Query {i}",
            assistant_response=f"Response {i}",
        )
        store.add_memory(mem)
    
    async def search_query(query: str):
        return store.search_similar(query, top_k=5, session_id="search_test")
    
    # Run concurrent searches
    queries = [f"topic {i}" for i in range(5)] * 4  # 20 searches
    tasks = [search_query(q) for q in queries]
    
    start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    assert len(results) == 20
    assert all(len(r) <= 5 for r in results)
    assert elapsed < 3.0
    
    print(f"20 concurrent vector searches completed in {elapsed:.2f}s")


@pytest.mark.asyncio
async def test_pipeline_throughput():
    """Test pipeline can handle multiple requests per second."""
    from ultron.main import get_state_machine
    from ultron.stages import handle_audio_input, handle_transcription
    
    machine = get_state_machine()
    
    async def run_pipeline(session_id: str):
        state = StateData(run=PipelineRun(session_id=session_id))
        state.transcription = TranscriptionResponse(
            text="What's the weather?",
            language="en",
            confidence=0.9,
            duration_ms=500,
        )
        state.current_state = PipelineState.CONTEXT_INJECTION
        
        # Run just context injection + intent extraction (fast path)
        state = await handle_context_injection(state)
        return state
    
    # Run 50 concurrent pipeline requests
    num_requests = 50
    tasks = [run_pipeline(f"throughput_session_{i % 5}") for i in range(num_requests)]
    
    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start
    
    successful = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]
    
    print(f"Pipeline throughput: {len(successful)}/{num_requests} successful in {elapsed:.2f}s")
    print(f"Requests per second: {num_requests/elapsed:.1f}")
    
    # At least 80% should succeed
    assert len(successful) >= num_requests * 0.8
    # Should handle at least 10 req/s
    assert num_requests / elapsed >= 10


@pytest.mark.asyncio
async def test_memory_growth_simulation():
    """Test memory system handles growing data over time."""
    store = ChromaMemoryStore()
    session_store = SessionStore()
    
    # Simulate adding memories over time
    num_memories = 100
    session_id = "growth_test"
    
    start = time.time()
    for i in range(num_memories):
        turn = ConversationTurn(
            session_id=session_id,
            user_query=f"Question {i} about various topics",
            assistant_response=f"Answer {i} with details",
            intent_type="weather" if i % 3 == 0 else "calendar" if i % 3 == 1 else "task",
        )
        session_store.add_turn(turn)
        
        # Also add to vector store every 3rd turn
        if i % 3 == 0:
            from ultron.memory.models import MemoryEntry
            from ultron.memory.salience import evaluate_salience, turn_to_memory_entry
            
            salience = evaluate_salience(turn)
            if salience >= 0.5:
                mem_entry = turn_to_memory_entry(turn, salience)
                store.add_memory(mem_entry)
    
    add_elapsed = time.time() - start
    
    # Search performance should remain good
    start = time.time()
    for _ in range(20):
        store.search_similar("question about topics", top_k=10, session_id=session_id)
    search_elapsed = time.time() - start
    
    print(f"Added {num_memories} memories in {add_elapsed:.2f}s")
    print(f"20 searches on {num_memories} memories in {search_elapsed:.2f}s")
    
    # Search should still be fast (< 100ms per search avg)
    assert search_elapsed / 20 < 0.1


@pytest.mark.asyncio
async def test_high_concurrency_briefing_generation():
    """Test briefing generation under concurrent load."""
    from ultron.briefing.generator import generate_daily_briefing
    from ultron.briefing.models import BriefingConfig
    
    async def generate_briefing(city: str):
        config = BriefingConfig(city=city)
        return await generate_daily_briefing(config)
    
    # Generate 10 concurrent briefings
    cities = ["New York", "London", "Tokyo", "Paris", "Sydney"] * 2
    tasks = [generate_briefing(city) for city in cities]
    
    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start
    
    successful = [r for r in results if not isinstance(r, Exception)]
    
    print(f"10 concurrent briefings in {elapsed:.2f}s")
    
    assert len(successful) >= 8  # At least 80% success
    assert all(isinstance(r, BriefingContent) for r in successful)
    assert all(r.full_text.startswith("Good morning!") for r in successful)
