"""
Pipeline state definitions and data carrier.

Defines the explicit state machine states and the data structure
that flows between stages.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from ..schemas.pipeline import PipelineRun, StageResult, StageStatus
from ..schemas.intent import Intent
from ..schemas.api import TranscriptionResponse, ActionResult


class PipelineState(str, Enum):
    """Explicit pipeline states - no implicit control flow."""
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    CONTEXT_INJECTION = "context_injection"
    EXTRACTING_INTENT = "extracting_intent"
    CONFIRMING_INTENT = "confirming_intent"
    EXECUTING = "executing"
    RESPONDING = "responding"
    DONE = "done"
    FAILED = "failed"


@dataclass
class StateData:
    """
    Data carrier that flows through the pipeline stages.
    Each stage reads what it needs, writes its output.
    """
    # Pipeline tracking
    run: PipelineRun
    current_state: PipelineState = PipelineState.LISTENING

    # Stage 1: Audio Input
    audio_bytes: Optional[bytes] = None
    audio_format: Optional[str] = None  # wav, mp3, etc.
    audio_duration_ms: Optional[int] = None

    # Stage 2: Transcription
    transcription: Optional[TranscriptionResponse] = None

    # Memory & Context Injection
    retrieved_context: Optional[list] = None
    session_history: Optional[list] = None

    # Stage 3: Intent Extraction
    intent: Optional[Intent] = None
    raw_llm_output: Optional[str] = None

    # Stage 4: Confirmation (optional)
    requires_confirmation: bool = False
    confirmed: bool = False

    # Stage 5: Action Execution
    action_result: Optional[ActionResult] = None

    # Stage 6: Response
    response_text: str = ""
    audio_url: Optional[str] = None


    # Error handling
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_stage: Optional[str] = None

    def add_stage_result(self, stage: str, status: StageStatus, **kwargs) -> None:
        """Add a stage result to the pipeline run."""
        result = StageResult(
            stage=stage,
            status=status,
            started_at=datetime.utcnow(),
            **kwargs
        )
        self.run.add_stage(result)

    def mark_stage_start(self, stage: str) -> None:
        """Mark a stage as running."""
        self.add_stage_result(stage, StageStatus.RUNNING)

    def mark_stage_success(self, stage: str, output: dict, latency_ms: int) -> None:
        """Mark a stage as successful."""
        self.add_stage_result(stage, StageStatus.SUCCESS, output=output, latency_ms=latency_ms, completed_at=datetime.utcnow())

    def mark_stage_failed(self, stage: str, error: str, latency_ms: int, error_type: Optional[str] = None) -> None:
        """Mark a stage as failed."""
        self.add_stage_result(stage, StageStatus.FAILED, error=error, latency_ms=latency_ms, completed_at=datetime.utcnow())
        self.error = error
        self.error_type = error_type
        self.error_stage = stage
