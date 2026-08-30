"""
Stage: Context Injection & Conversational Memory Retrieval.

Retrieves recent short-term session history and semantic long-term memories
to provide context for LLM intent extraction.
"""

import time
from typing import Optional

from ..state import StateData, PipelineState
from ..memory.stores import get_session_store, get_vector_store
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def handle_context_injection(state: StateData) -> StateData:
    """
    Stage Handler: Context Injection.
    
    1. Fetch recent turns from SessionStore for session_id.
    2. Search ChromaMemoryStore for relevant semantic memories matching transcribed query text.
    3. Attach context to StateData.
    4. Transition state to EXTRACTING_INTENT.
    """
    start_time = time.time()
    state.mark_stage_start("context_injection")

    session_id = state.run.session_id or "default_session"
    user_query = state.transcription.text if state.transcription else ""

    try:
        session_store = get_session_store()
        vector_store = get_vector_store()

        # Fetch recent session turns
        recent_turns = session_store.get_recent_turns(session_id=session_id, limit=5)
        history_list = [
            {"user": turn.user_query, "assistant": turn.assistant_response}
            for turn in recent_turns
        ]
        state.session_history = history_list

        # Search long-term vector store if we have a query
        semantic_memories = []
        if user_query.strip():
            memories = vector_store.search_similar(
                query=user_query,
                top_k=settings.memory_top_k,
            )
            semantic_memories = [m.content for m in memories]

        state.retrieved_context = semantic_memories

        latency_ms = int((time.time() - start_time) * 1000)
        state.mark_stage_success(
            stage="context_injection",
            output={
                "session_turns_count": len(recent_turns),
                "semantic_memories_count": len(semantic_memories),
            },
            latency_ms=latency_ms,
        )
        logger.info(
            "context_injected",
            session_id=session_id,
            history_turns=len(recent_turns),
            memories_found=len(semantic_memories),
        )

        state.current_state = PipelineState.EXTRACTING_INTENT
        return state

    except Exception as e:
        logger.error("context_injection_failed", error=str(e))
        # Non-fatal stage: proceed with empty context
        state.retrieved_context = []
        state.session_history = []
        latency_ms = int((time.time() - start_time) * 1000)
        state.mark_stage_success(
            stage="context_injection",
            output={"error": str(e), "fallback": True},
            latency_ms=latency_ms,
        )
        state.current_state = PipelineState.EXTRACTING_INTENT
        return state
