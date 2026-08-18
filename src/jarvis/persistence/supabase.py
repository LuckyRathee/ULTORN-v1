"""
Supabase client for pipeline run logging.

Stores one row per request with per-stage status, latency, and trace data.
"""

import json
from typing import Optional
from uuid import UUID
from supabase import create_client, Client

from ..config import settings
from ..schemas.pipeline import PipelineRun, StageResult, StageStatus


# Global client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase credentials not configured")
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase_client


class SupabaseClient:
    """Wrapper for Supabase operations with pipeline logging."""
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase_client()
    
    async def log_pipeline_run(self, run: PipelineRun) -> None:
        """
        Insert or update a pipeline run in Supabase.
        
        Uses upsert to handle both new runs and updates.
        """
        # Convert to dict for Supabase
        data = self._pipeline_run_to_dict(run)
        
        try:
            # Upsert on id
            result = self.client.table("pipeline_runs").upsert(data).execute()
            if not result.data:
                raise RuntimeError("Failed to log pipeline run")
        except Exception as e:
            # Log but don't fail the pipeline
            print(f"Supabase logging error: {e}")
    
    async def get_pipeline_run(self, run_id: UUID) -> Optional[PipelineRun]:
        """Retrieve a pipeline run by ID."""
        try:
            result = self.client.table("pipeline_runs").select("*").eq("id", str(run_id)).single().execute()
            if result.data:
                return self._dict_to_pipeline_run(result.data)
        except Exception as e:
            print(f"Supabase retrieval error: {e}")
        return None
    
    async def list_pipeline_runs(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[PipelineRun]:
        """List pipeline runs with optional filters."""
        try:
            query = self.client.table("pipeline_runs").select("*").order("created_at", desc=True).limit(limit)
            
            if session_id:
                query = query.eq("session_id", session_id)
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            return [self._dict_to_pipeline_run(row) for row in result.data]
        except Exception as e:
            print(f"Supabase listing error: {e}")
            return []
    
    def _pipeline_run_to_dict(self, run: PipelineRun) -> dict:
        """Convert PipelineRun to Supabase-compatible dict."""
        return {
            "id": str(run.id),
            "session_id": run.session_id,
            "user_id": run.user_id,
            "status": run.status,
            "stages": [self._stage_result_to_dict(s) for s in run.stages],
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_latency_ms": run.total_latency_ms,
        }
    
    def _stage_result_to_dict(self, stage: StageResult) -> dict:
        """Convert StageResult to dict."""
        return {
            "stage": stage.stage,
            "status": stage.status.value,
            "input": stage.input,
            "output": stage.output,
            "error": stage.error,
            "latency_ms": stage.latency_ms,
            "retry_count": stage.retry_count,
            "started_at": stage.started_at.isoformat() if stage.started_at else None,
            "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
        }
    
    def _dict_to_pipeline_run(self, data: dict) -> PipelineRun:
        """Convert Supabase dict to PipelineRun."""
        stages = []
        for s in data.get("stages", []):
            stages.append(StageResult(
                stage=s["stage"],
                status=StageStatus(s["status"]),
                input=s.get("input"),
                output=s.get("output"),
                error=s.get("error"),
                latency_ms=s["latency_ms"],
                retry_count=s.get("retry_count", 0),
                started_at=s["started_at"],
                completed_at=s.get("completed_at"),
            ))
        
        return PipelineRun(
            id=UUID(data["id"]),
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            status=data["status"],
            stages=stages,
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
            total_latency_ms=data["total_latency_ms"],
        )


# Convenience function for logging
async def log_pipeline_run(run: PipelineRun) -> None:
    """Log a pipeline run to Supabase."""
    client = SupabaseClient()
    await client.log_pipeline_run(run)