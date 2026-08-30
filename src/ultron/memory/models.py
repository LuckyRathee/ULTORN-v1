"""
Pydantic schemas for Conversational Memory models.
"""

from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """Represents a single back-and-forth interaction in a session."""
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_query: str
    assistant_response: str
    intent_type: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntry(BaseModel):
    """Represents a stored semantic memory entry in vector storage."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    content: str
    user_query: str
    assistant_response: str
    intent_type: Optional[str] = None
    salience_score: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextQuery(BaseModel):
    """Query object for retrieving semantic memory context."""
    query_text: str
    session_id: Optional[str] = None
    top_k: int = 5


class ContextRetrievalResult(BaseModel):
    """Result of context retrieval for injection into LLM prompts."""
    recent_turns: List[ConversationTurn] = Field(default_factory=list)
    semantic_memories: List[MemoryEntry] = Field(default_factory=list)
    formatted_context_str: str = ""
