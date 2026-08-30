"""
Ultron 2.0 Conversational Memory Package.

Provides short-term session state storage and long-term vector memory retrieval.
"""

from .models import MemoryEntry, ConversationTurn, ContextQuery, ContextRetrievalResult
from .embeddings import EmbeddingService
from .vector_store import ChromaMemoryStore
from .session_store import SessionStore
from .salience import evaluate_salience

__all__ = [
    "MemoryEntry",
    "ConversationTurn",
    "ContextQuery",
    "ContextRetrievalResult",
    "EmbeddingService",
    "ChromaMemoryStore",
    "SessionStore",
    "evaluate_salience",
]
