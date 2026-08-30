"""
Global instances for memory stores.

This module provides singleton access to memory stores
to avoid circular imports.
"""

from typing import Optional
from ..memory import SessionStore, ChromaMemoryStore
from ..config import settings


_session_store: Optional[SessionStore] = None
_vector_store: Optional[ChromaMemoryStore] = None


def get_session_store() -> SessionStore:
    """Get or create the global session store."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore(
            redis_url=settings.redis_url,
            ttl_seconds=settings.memory_ttl_seconds,
        )
    return _session_store


def get_vector_store() -> ChromaMemoryStore:
    """Get or create the global vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaMemoryStore(
            persist_directory=settings.chroma_persist_dir,
        )
    return _vector_store


def set_session_store(store: SessionStore) -> None:
    """Set the global session store (for testing)."""
    global _session_store
    _session_store = store


def set_vector_store(store: ChromaMemoryStore) -> None:
    """Set the global vector store (for testing)."""
    global _vector_store
    _vector_store = store


def reset_stores() -> None:
    """Reset global stores (for testing)."""
    global _session_store, _vector_store
    _session_store = None
    _vector_store = None
