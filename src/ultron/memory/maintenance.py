"""
Background maintenance tasks for memory system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .vector_store import ChromaMemoryStore
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MemoryMaintenance:
    """Handles periodic maintenance of the memory system."""

    def __init__(
        self,
        vector_store: Optional[ChromaMemoryStore] = None,
        retention_days: int = 90,
        compaction_interval_hours: int = 24,
    ):
        self.vector_store = vector_store or ChromaMemoryStore(
            persist_directory=settings.chroma_persist_dir
        )
        self.retention_days = retention_days
        self.compaction_interval_hours = compaction_interval_hours
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the maintenance background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._maintenance_loop())
        logger.info("memory_maintenance_started", interval_hours=self.compaction_interval_hours)

    async def stop(self):
        """Stop the maintenance background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("memory_maintenance_stopped")

    async def _maintenance_loop(self):
        """Background loop that runs maintenance tasks periodically."""
        while self._running:
            try:
                await self.run_maintenance()
            except Exception as e:
                logger.error("memory_maintenance_failed", error=str(e))
            
            await asyncio.sleep(self.compaction_interval_hours * 3600)

    async def run_maintenance(self):
        """Run all maintenance tasks."""
        logger.info("memory_maintenance_running")
        
        await self._compact_old_memories()
        await self._cleanup_orphaned_embeddings()

    async def _compact_old_memories(self):
        """Remove memories older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        try:
            if self.vector_store._collection is not None:
                results = self.vector_store._collection.get()
                
                if results and "ids" in results and results["ids"]:
                    ids_to_delete = []
                    metadatas = results.get("metadatas", [])
                    
                    for metadata, mem_id in zip(metadatas, results["ids"]):
                        if "created_at" in metadata:
                            try:
                                created = datetime.fromisoformat(metadata["created_at"])
                                if created < cutoff_date:
                                    ids_to_delete.append(mem_id)
                            except (ValueError, TypeError):
                                pass
                    
                    if ids_to_delete:
                        self.vector_store._collection.delete(ids=ids_to_delete)
                        logger.info("chroma_old_memories_deleted", count=len(ids_to_delete))
        except Exception as e:
            logger.error("chroma_compaction_failed", error=str(e))

    async def _cleanup_orphaned_embeddings(self):
        """Clean up any orphaned embeddings in fallback store."""
        if hasattr(self.vector_store, '_fallback_memories'):
            initial_count = len(self.vector_store._fallback_memories)
            self.vector_store._fallback_memories = [
                item for item in self.vector_store._fallback_memories
                if item["entry"].created_at >= datetime.utcnow() - timedelta(days=self.retention_days)
            ]
            removed = initial_count - len(self.vector_store._fallback_memories)
            if removed > 0:
                logger.info("fallback_orphaned_cleaned", count=removed)


async def run_maintenance_once(
    persist_directory: str = None,
    retention_days: int = 90
) -> None:
    """Run maintenance once (for manual invocation or testing)."""
    store = ChromaMemoryStore(persist_directory=persist_directory or settings.chroma_persist_dir)
    maintenance = MemoryMaintenance(vector_store=store, retention_days=retention_days)
    await maintenance.run_maintenance()
