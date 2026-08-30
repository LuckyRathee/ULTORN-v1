"""
Pydantic schemas - Single source of truth for all data models.

Exports:
- Intent schemas (discriminated union for type-safe routing)
- Pipeline schemas (per-request logging to Supabase)
- API schemas (request/response models)
"""

from .intent import (
    IntentType,
    WeatherIntent,
    CalendarCreateIntent,
    CalendarListIntent,
    TaskCreateIntent,
    TaskListIntent,
    UnknownIntent,
    Intent,
)
from .pipeline import StageStatus, StageResult, PipelineRun
from .api import (
    AudioInputRequest,
    TranscriptionResponse,
    IntentExtractionResponse,
    ActionResult,
    PipelineResponse,
    HealthResponse,
)

__all__ = [
    # Intent
    "IntentType",
    "WeatherIntent",
    "CalendarCreateIntent",
    "CalendarListIntent",
    "TaskCreateIntent",
    "TaskListIntent",
    "UnknownIntent",
    "Intent",
    # Pipeline
    "StageStatus",
    "StageResult",
    "PipelineRun",
    # API
    "AudioInputRequest",
    "TranscriptionResponse",
    "IntentExtractionResponse",
    "ActionResult",
    "PipelineResponse",
    "HealthResponse",
]
