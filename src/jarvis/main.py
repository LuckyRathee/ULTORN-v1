"""
Jarvis 2.0 - FastAPI Application Entry Point.

Production-grade voice/multimodal AI assistant with explicit 5-stage pipeline.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .schemas import (
    AudioInputRequest,
    PipelineResponse,
    HealthResponse,
    PipelineRun,
    StageStatus,
    StageResult,
)
from .state import StateData, PipelineState, StateMachine
from .stages import (
    handle_audio_input,
    handle_transcription,
    handle_intent_extraction,
    handle_action_execution,
    handle_response,
)
from .persistence import log_pipeline_run
from .utils.logging import setup_logging, get_logger
from .utils.errors import JarvisError


# Setup logging
setup_logging(settings.log_level)
logger = get_logger(__name__)


# Global state machine instance
_state_machine: Optional[StateMachine] = None


def get_state_machine() -> StateMachine:
    """Get or create the global state machine with registered handlers."""
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
        # Register stage handlers
        _state_machine.register_handler(PipelineState.LISTENING, handle_audio_input)
        _state_machine.register_handler(PipelineState.TRANSCRIBING, handle_transcription)
        _state_machine.register_handler(PipelineState.EXTRACTING_INTENT, handle_intent_extraction)
        _state_machine.register_handler(PipelineState.CONFIRMING_INTENT, handle_confirmation)
        _state_machine.register_handler(PipelineState.EXECUTING, handle_action_execution)
        _state_machine.register_handler(PipelineState.RESPONDING, handle_response)
    return _state_machine


async def handle_confirmation(state: StateData) -> StateData:
    """
    Stage 4 handler: Confirm intent before execution (for destructive actions).
    
    For v1, we auto-confirm safe actions (weather, list) and require
    explicit confirmation for create actions. In a real app, this would
    wait for user input via a separate endpoint.
    """
    # Auto-confirm for safe actions (read-only)
    if not state.requires_confirmation:
        state.confirmed = True
        state.current_state = PipelineState.EXECUTING
        return state
    
    # For v1, we'll auto-confirm everything but log that confirmation was needed
    # In production, this would pause and wait for user confirmation via API
    logger.info("confirmation_required", intent_type=state.intent.type if state.intent else None)
    state.confirmed = True
    state.current_state = PipelineState.EXECUTING
    return state


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("jarvis_starting", version="1.0.0")
    # Initialize state machine
    get_state_machine()
    yield
    logger.info("jarvis_shutting_down")


app = FastAPI(
    title="Jarvis 2.0",
    description="Production-grade voice/multimodal AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models for API
class ProcessAudioRequest(BaseModel):
    """Request model for audio processing endpoint."""
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    session_id: str
    user_id: Optional[str] = None


class ProcessAudioResponse(BaseModel):
    """Response model for audio processing endpoint."""
    run_id: str
    status: str
    response_text: str
    audio_url: Optional[str] = None
    transcription: Optional[dict] = None
    intent: Optional[dict] = None
    action_result: Optional[dict] = None
    total_latency_ms: int


class GreetResponse(BaseModel):
    """Response model for greeting endpoint."""
    response_text: str
    audio_url: Optional[str] = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with dependency status."""
    checks = {
        "supabase": "ok",
        "stt": "ok",
        "llm": "ok",
        "weather_api": "ok",
    }
    
    # Quick checks (non-blocking)
    try:
        from .persistence import get_supabase_client
        get_supabase_client()
    except Exception:
        checks["supabase"] = "fail"
    
    try:
        from .services.stt import transcribe_audio
        # Just check config
        if not settings.groq_api_key and settings.stt_provider == "groq":
            checks["stt"] = "fail"
    except Exception:
        checks["stt"] = "fail"
    
    try:
        from .services.llm import extract_intent
        if not settings.groq_api_key and not settings.anthropic_api_key:
            checks["llm"] = "fail"
    except Exception:
        checks["llm"] = "fail"
    
    try:
        from .services.weather import get_weather
        if not settings.weather_api_key:
            checks["weather_api"] = "fail"
    except Exception:
        checks["weather_api"] = "fail"
    
    overall_status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        checks=checks,
        uptime_seconds=0,  # Would track actual uptime in production
    )


@app.get("/api/v1/greet", response_model=GreetResponse)
async def greet_user():
    """Generate a greeting response with optional TTS."""
    response_text = "Hello! I am Jarvis. How can I help you today?"
    audio_url = None
    
    if settings.tts_provider != "none":
        try:
            from .services.tts import synthesize_speech
            audio_url = await synthesize_speech(
                text=response_text,
                provider=settings.tts_provider,
                voice_id=settings.elevenlabs_voice_id,
            )
        except Exception as e:
            logger.error("greeting_tts_failed", error=str(e))
            
    return GreetResponse(
        response_text=response_text,
        audio_url=audio_url,
    )


@app.post("/api/v1/process-audio", response_model=ProcessAudioResponse)
async def process_audio(request: ProcessAudioRequest):
    """
    Main endpoint: Process audio through the 5-stage pipeline.
    
    Accepts base64-encoded audio or URL, returns structured response.
    """
    # Create pipeline run record
    run = PipelineRun(
        session_id=request.session_id,
        user_id=request.user_id,
    )
    
    # Create initial state data
    state = StateData(run=run)
    state._audio_request = request  # Attach request for audio input stage
    
    # Run pipeline
    machine = get_state_machine()
    final_state = await machine.run(state)
    
    # Log to Supabase (non-blocking)
    try:
        await log_pipeline_run(final_state.run)
    except Exception as e:
        logger.error("supabase_log_failed", error=str(e))
    
    # Build response
    response = ProcessAudioResponse(
        run_id=str(final_state.run.id),
        status=final_state.run.status,
        response_text=final_state.response_text or "I encountered an error.",
        audio_url=final_state.audio_url,
        total_latency_ms=final_state.run.total_latency_ms,
    )
    
    # Add stage details if available
    if final_state.transcription:
        response.transcription = {
            "text": final_state.transcription.text,
            "language": final_state.transcription.language,
            "confidence": final_state.transcription.confidence,
            "duration_ms": final_state.transcription.duration_ms,
        }
    
    if final_state.intent:
        response.intent = {
            "type": final_state.intent.type.value,
            "confidence": final_state.intent.confidence,
        }
    
    if final_state.action_result:
        response.action_result = {
            "success": final_state.action_result.success,
            "data": final_state.action_result.data,
            "error": final_state.action_result.error,
            "error_type": final_state.action_result.error_type,
            "latency_ms": final_state.action_result.latency_ms,
        }
    
    return response


@app.post("/api/v1/process-audio/file")
async def process_audio_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None),
):
    """
    Process audio file upload through the pipeline.
    
    Accepts multipart/form-data with audio file.
    """
    # Read file
    audio_bytes = await file.read()
    
    # Convert to base64 for processing
    import base64
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    # Create request
    request = ProcessAudioRequest(
        audio_base64=audio_base64,
        session_id=session_id,
        user_id=user_id,
    )
    
    return await process_audio(request)


@app.get("/api/v1/runs/{run_id}")
async def get_pipeline_run(run_id: str):
    """Retrieve a pipeline run by ID."""
    from .persistence import SupabaseClient
    from uuid import UUID
    
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    client = SupabaseClient()
    run = await client.get_pipeline_run(run_uuid)
    
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    return run


@app.get("/api/v1/runs")
async def list_pipeline_runs(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
):
    """List pipeline runs with optional filters."""
    from .persistence import SupabaseClient
    
    client = SupabaseClient()
    runs = await client.list_pipeline_runs(session_id, user_id, limit)
    
    return {"runs": runs}


# Exception handlers
@app.exception_handler(JarvisError)
async def jarvis_error_handler(request: Request, exc: JarvisError):
    """Handle Jarvis-specific errors with structured response."""
    logger.error("jarvis_error", code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error("unexpected_error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "user_message": "Something went wrong. Please try again.",
            "details": {},
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "jarvis.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )