"""
Pipeline schemas - Per-request logging to Supabase.

Each request gets one row with per-stage status, latency, and trace data.
Enables full observability and replay capability.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class StageStatus(str, Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    """Result of a single pipeline stage."""
    stage: str = Field(..., description="Stage name: audio_input, transcription, intent_extraction, action_execution, response")
    status: StageStatus
    input: Optional[dict] = Field(default=None, description="Stage input data (sanitized)")
    output: Optional[dict] = Field(default=None, description="Stage output data (sanitized)")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    latency_ms: int = Field(default=0, ge=0, description="Stage execution time in milliseconds")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    started_at: datetime = Field(..., description="Stage start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Stage completion timestamp")


class PipelineRun(BaseModel):
    """Complete pipeline run record - one row per request in Supabase."""
    id: UUID = Field(default_factory=uuid4, description="Unique run identifier")
    session_id: str = Field(..., description="Client session identifier")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID if available")
    status: Literal["running", "done", "failed"] = Field(default="running", description="Overall pipeline status")
    stages: list[StageResult] = Field(default_factory=list, description="Ordered stage results")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Pipeline start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Pipeline completion timestamp")
    total_latency_ms: int = Field(default=0, ge=0, description="Total pipeline latency in milliseconds")

    def add_stage(self, stage: StageResult) -> None:
        """Add a stage result and update total latency."""
        self.stages.append(stage)
        self.total_latency_ms = sum(s.latency_ms for s in self.stages)

    def mark_completed(self, final_status: Literal["done", "failed"]) -> None:
        """Mark pipeline as completed."""
        self.status = final_status
        self.completed_at = datetime.utcnow()