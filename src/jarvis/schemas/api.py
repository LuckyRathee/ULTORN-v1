"""
API request/response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from .intent import Intent


class AudioInputRequest(BaseModel):
    """Request to process audio input (file upload or base64)."""
    audio_base64: Optional[str] = Field(default=None, description="Base64-encoded audio file")
    audio_url: Optional[str] = Field(default=None, description="URL to pre-uploaded audio file")
    session_id: str = Field(..., description="Client session identifier")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID if available")


class TranscriptionResponse(BaseModel):
    """Response from transcription stage."""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language code (e.g., 'en')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Transcription confidence")
    duration_ms: int = Field(..., ge=0, description="Audio duration in milliseconds")


class IntentExtractionResponse(BaseModel):
    """Response from intent extraction stage."""
    intent: Intent = Field(..., description="Structured intent with typed fields")
    raw_llm_output: str = Field(..., description="Raw LLM response for debugging")
    extraction_latency_ms: int = Field(..., ge=0, description="LLM call latency in milliseconds")


class ActionResult(BaseModel):
    """Result from action execution stage."""
    success: bool
    data: Optional[dict] = Field(default=None, description="Action-specific result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_type: Optional[Literal["timeout", "auth", "bad_params", "api_down", "unknown"]] = Field(
        default=None, description="Categorized error type for client handling"
    )
    latency_ms: int = Field(..., ge=0, description="Action execution latency in milliseconds")


class PipelineResponse(BaseModel):
    """Complete pipeline response returned to client."""
    run_id: UUID = Field(..., description="Pipeline run identifier")
    status: Literal["done", "failed"] = Field(..., description="Overall pipeline status")
    transcription: Optional[TranscriptionResponse] = Field(default=None)
    intent: Optional[IntentExtractionResponse] = Field(default=None)
    action_result: Optional[ActionResult] = Field(default=None)
    response_text: str = Field(..., description="Human-readable response text")
    audio_url: Optional[str] = Field(default=None, description="TTS audio URL if generated")
    total_latency_ms: int = Field(..., ge=0, description="Total pipeline latency in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    checks: dict[str, Literal["ok", "fail"]]
    uptime_seconds: int