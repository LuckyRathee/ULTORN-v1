"""
Short-term session history store (Redis with in-memory dict fallback).
"""

import json
from typing import List, Optional, Dict
from datetime import datetime

from .models import ConversationTurn
from ..utils.logging import get_logger

logger = get_logger(__name__)


_shared_fallback_store: Dict[str, List[ConversationTurn]] = {}


class SessionStore:
    """Stores recent conversation history per session for short-term context."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl_seconds: int = 86400):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis_client = None
        self._fallback_store = _shared_fallback_store
        self._connect_redis()


    def _connect_redis(self):
        try:
            import redis
            client = redis.Redis.from_url(self.redis_url, socket_timeout=2.0)
            client.ping()
            self._redis_client = client
            logger.info("redis_connected", url=self.redis_url)
        except Exception as e:
            logger.info("redis_unavailable_using_inmemory_store", reason=str(e))
            self._redis_client = None

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a conversation turn to session history."""
        session_id = turn.session_id
        
        if self._redis_client is not None:
            try:
                key = f"Ultron:session:{session_id}"
                turn_json = turn.model_dump_json()
                self._redis_client.rpush(key, turn_json)
                self._redis_client.expire(key, self.ttl_seconds)
                return
            except Exception as e:
                logger.error("redis_add_turn_failed", error=str(e))

        # Fallback to in-memory dictionary
        if session_id not in self._fallback_store:
            self._fallback_store[session_id] = []
        self._fallback_store[session_id].append(turn)

    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[ConversationTurn]:
        """Fetch the most recent N turns for a session."""
        if self._redis_client is not None:
            try:
                key = f"Ultron:session:{session_id}"
                items = self._redis_client.lrange(key, -limit, -1)
                turns = []
                for item in items:
                    data = json.loads(item.decode("utf-8") if isinstance(item, bytes) else item)
                    turns.append(ConversationTurn(**data))
                return turns
            except Exception as e:
                logger.error("redis_get_turns_failed", error=str(e))

        # Fallback in-memory
        turns = self._fallback_store.get(session_id, [])
        return turns[-limit:]

    def clear_session(self, session_id: str) -> None:
        """Clear all stored turns for a session."""
        if self._redis_client is not None:
            try:
                self._redis_client.delete(f"Ultron:session:{session_id}")
            except Exception:
                pass
        self._fallback_store.pop(session_id, None)
