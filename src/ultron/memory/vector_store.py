"""
ChromaDB persistent vector store wrapper for long-term semantic memory.
"""

import os
import math
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import MemoryEntry
from .embeddings import EmbeddingService
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


_shared_fallback_memories: List[dict] = []


class ChromaMemoryStore:
    """Vector database storage for persistent semantic memory entries."""

    def __init__(self, persist_directory: str = "./scratch/chroma_db", embedding_service: Optional[EmbeddingService] = None):
        self.persist_directory = persist_directory
        self.embedding_service = embedding_service or EmbeddingService()
        self._client = None
        self._collection = None
        self._fallback_memories = _shared_fallback_memories
        self._init_db()


    def _init_db(self):
        try:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(name="Ultron_memories")
            logger.info("chromadb_initialized", path=self.persist_directory)
        except Exception as e:
            logger.warning("chromadb_init_fallback", error=str(e))
            self._client = None

    def add_memory(self, memory: MemoryEntry) -> bool:
        """Add a memory entry to the vector store."""
        embedding = self.embedding_service.embed_text(memory.content)
        
        if self._collection is not None:
            try:
                self._collection.add(
                    ids=[memory.id],
                    embeddings=[embedding],
                    documents=[memory.content],
                    metadatas=[{
                        "session_id": memory.session_id,
                        "user_query": memory.user_query,
                        "assistant_response": memory.assistant_response,
                        "intent_type": memory.intent_type or "unknown",
                        "salience_score": memory.salience_score,
                        "created_at": memory.created_at.isoformat(),
                    }]
                )
                logger.info("memory_added_to_chroma", memory_id=memory.id)
                return True
            except Exception as e:
                logger.error("chroma_add_failed", error=str(e))

        # Fallback in-memory list
        self._fallback_memories.append({
            "entry": memory,
            "embedding": embedding
        })
        logger.info("memory_added_to_fallback_store", memory_id=memory.id)
        return True

    def search_similar(self, query: str, top_k: int = 5, session_id: Optional[str] = None) -> List[MemoryEntry]:
        """Search for relevant semantic memories matching query string."""
        query_vec = self.embedding_service.embed_text(query)
        
        if self._collection is not None:
            try:
                where_clause = {"session_id": session_id} if session_id else None
                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=top_k,
                    where=where_clause
                )
                
                memories = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0] if "metadatas" in results else []
                    ids = results["ids"][0] if "ids" in results else []
                    
                    for doc, meta, m_id in zip(docs, metas, ids):
                        memories.append(MemoryEntry(
                            id=m_id,
                            session_id=meta.get("session_id", "default"),
                            content=doc,
                            user_query=meta.get("user_query", ""),
                            assistant_response=meta.get("assistant_response", ""),
                            intent_type=meta.get("intent_type"),
                            salience_score=meta.get("salience_score", 1.0),
                            created_at=datetime.fromisoformat(meta["created_at"]) if "created_at" in meta else datetime.utcnow()
                        ))
                return memories
            except Exception as e:
                logger.error("chroma_search_failed", error=str(e))

        # Fallback search using cosine similarity
        scored = []
        for item in self._fallback_memories:
            if session_id and item["entry"].session_id != session_id:
                continue
            sim = _cosine_similarity(query_vec, item["embedding"])
            scored.append((sim, item["entry"]))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]
