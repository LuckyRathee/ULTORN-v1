# Ultron V1 Architecture Document

## Overview
Production-grade voice/multimodal AI assistant with explicit 5-stage pipeline, structured logging, and real API integrations.

---

## 1. State Machine

```
┌─────────────┐
│  LISTENING  │  ← Audio capture (mic or file upload)
└──────┬──────┘
       │ success
       ▼
┌──────────────────┐
│  TRANSCRIBING    │  ← Whisper STT (local faster-whisper or Groq API)
└──────┬───────────┘
       │ success + confidence ≥ threshold
       ▼
┌─────────────────────┐
│  EXTRACTING_INTENT  │  ← LLM (Claude Haiku / Groq Llama) → structured JSON
└──────┬──────────────┘
       │ valid schema + confidence ≥ threshold
       ▼
┌────────────────────┐
│  CONFIRMING_INTENT │  ← Optional: user confirmation for destructive actions
└──────┬─────────────┘
       │ confirmed / auto-confirm for safe actions
       ▼
┌──────────────┐
│  EXECUTING   │  ← Real external API call (weather, calendar, tasks, etc.)
└──────┬───────┘
       │ success / typed error
       ▼
┌───────────────┐
│  RESPONDING   │  ← Format result → text + optional TTS (ElevenLabs/Azure)
└──────┬────────┘
       │
       ▼
┌─────────┐     ┌────────┐
│  DONE   │     │ FAILED │  ← Terminal states with full trace logged
└─────────┘     └────────┘
```

### Failure Transitions
- Any stage can transition to `FAILED` with a typed error
- No recursive retries — explicit max-retry (default 2) with exponential backoff only for transient errors (timeout, 5xx)
- All failures logged with stage, input, output, error type, latency

---

## 2. Pydantic Schemas (Single Source of Truth)

### 2.1 Intent Schema
```python
# src/ultron/schemas/intent.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class IntentType(str, Enum):
    WEATHER = "weather"
    CALENDAR_CREATE = "calendar_create"
    CALENDAR_LIST = "calendar_list"
    TASK_CREATE = "task_create"
    TASK_LIST = "task_list"
    UNKNOWN = "unknown"

class WeatherIntent(BaseModel):
    type: Literal[IntentType.WEATHER]
    location: str = Field(..., description="City name or lat,lon")
    units: Literal["metric", "imperial"] = "metric"
    confidence: float = Field(..., ge=0.0, le=1.0)

class CalendarCreateIntent(BaseModel):
    type: Literal[IntentType.CALENDAR_CREATE]
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)

class CalendarListIntent(BaseModel):
    type: Literal[IntentType.CALENDAR_LIST]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    confidence: float = Field(..., ge=0.0, le=1.0)

class TaskCreateIntent(BaseModel):
    type: Literal[IntentType.TASK_CREATE]
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Literal["low", "medium", "high"] = "medium"
    confidence: float = Field(..., ge=0.0, le=1.0)

class TaskListIntent(BaseModel):
    type: Literal[IntentType.TASK_LIST]
    status: Optional[Literal["pending", "completed", "all"]] = "all"
    confidence: float = Field(..., ge=0.0, le=1.0)

class UnknownIntent(BaseModel):
    type: Literal[IntentType.UNKNOWN]
    raw_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)

# Discriminated union for type-safe routing
Intent = WeatherIntent | CalendarCreateIntent | CalendarListIntent | TaskCreateIntent | TaskListIntent | UnknownIntent
```

### 2.2 Pipeline Run Schema (Supabase Row)
```python
# src/ultron/schemas/pipeline.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class StageResult(BaseModel):
    stage: str
    status: StageStatus
    input: Optional[dict] = None
    output: Optional[dict] = None
    error: Optional[str] = None
    latency_ms: int
    retry_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None

class PipelineRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: str
    user_id: Optional[str] = None
    status: Literal["running", "done", "failed"] = "running"
    stages: list[StageResult] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_latency_ms: int = 0
```

### 2.3 API Request/Response Schemas
```python
# src/ultron/schemas/api.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID

class AudioInputRequest(BaseModel):
    audio_base64: Optional[str] = None  # For file upload
    audio_url: Optional[str] = None     # For pre-uploaded files
    session_id: str
    user_id: Optional[str] = None

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_ms: int

class IntentExtractionResponse(BaseModel):
    intent: Intent  # From intent.py
    raw_llm_output: str
    extraction_latency_ms: int

class ActionResult(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    error_type: Optional[Literal["timeout", "auth", "bad_params", "api_down", "unknown"]] = None
    latency_ms: int

class PipelineResponse(BaseModel):
    run_id: UUID
    status: Literal["done", "failed"]
    transcription: Optional[TranscriptionResponse] = None
    intent: Optional[IntentExtractionResponse] = None
    action_result: Optional[ActionResult] = None
    response_text: str
    audio_url: Optional[str] = None  # TTS output
    total_latency_ms: int
```

---

## 3. Folder Structure

```
ultron-v1/
├── docs/
│   └── architecture.md          # This file
├── src/
│   └── ultron/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Settings from .env (pydantic-settings)
│       ├── state/
│       │   ├── __init__.py
│       │   ├── machine.py       # State machine implementation
│       │   └── states.py        # Enum + state data classes
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── intent.py        # Intent Pydantic models (discriminated union)
│       │   ├── pipeline.py      # PipelineRun, StageResult
│       │   └── api.py           # Request/Response models
│       ├── stages/
│       │   ├── __init__.py
│       │   ├── audio_input.py   # Stage 1: capture/validate audio
│       │   ├── transcription.py # Stage 2: Whisper STT
│       │   ├── intent_extraction.py  # Stage 3: LLM → structured JSON
│       │   ├── action_execution.py   # Stage 4: Router + API calls
│       │   └── response.py      # Stage 5: Format + TTS
│       ├── services/
│       │   ├── __init__.py
│       │   ├── stt.py           # Whisper client (local + Groq)
│       │   ├── llm.py           # LLM client (Claude Haiku / Groq)
│       │   ├── tts.py           # ElevenLabs / Azure client
│       │   ├── weather.py       # Weather API integration
│       │   ├── calendar.py      # Calendar API integration
│       │   └── tasks.py         # Task tracker API integration
│       ├── persistence/
│       │   ├── __init__.py
│       │   └── supabase.py      # Supabase client + pipeline logging
│       └── utils/
│           ├── __init__.py
│           ├── audio.py         # Audio validation, conversion
│           ├── errors.py        # Typed exception classes
│           └── logging.py       # Structured JSON logging
├── tests/
│   ├── __init__.py
│   ├── test_audio_input.py
│   ├── test_transcription.py
│   ├── test_intent_extraction.py
│   ├── test_action_execution.py
│   ├── test_pipeline_integration.py
│   └── fixtures/
│       ├── sample_audio.wav
│       └── sample_transcripts.json
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 4. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Discriminated union for Intent** | Type-safe routing, no stringly-typed `if intent.type == "weather"` — router uses `match intent.type` or `isinstance` |
| **Explicit state machine** | Observable, testable, debuggable — each stage is a pure function `State → Result` |
| **Supabase per-request row** | Full traceability: replay any request, measure stage latency, debug failures |
| **Tool-calling for intent extraction** | Guarantees valid JSON schema — no prompt-and-hope, no regex parsing |
| **Typed errors per external call** | `timeout`, `auth`, `bad_params`, `api_down` — caller handles each explicitly |
| **No recursive retries** | Max 2 retries with backoff only for transient errors; everything else fails fast |
| **Cross-platform only** | No `os.startfile`, `pywinauto`, hardcoded paths — runs on Linux/macOS/Windows |
| **Async throughout** | FastAPI + async clients — no blocking I/O in request path |

---

## 5. External API Integrations (v1 Scope)

| Integration | API | Auth | Priority |
|-------------|-----|------|----------|
| Weather | OpenWeatherMap / WeatherAPI | API Key | 1 (simplest) |
| Calendar | Google Calendar API | OAuth2 | 2 |
| Tasks | Notion API / Todoist API | API Key | 3 |
| Personal | NimitAI internal API | Bearer token | 4 |

---

## 6. Configuration (`.env.example`)

```env
# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx

# STT
STT_PROVIDER=groq  # or "local"
GROQ_API_KEY=xxx
WHISPER_MODEL=base  # for local faster-whisper

# LLM (Intent Extraction)
LLM_PROVIDER=groq  # or "anthropic"
GROQ_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
INTENT_MODEL=llama-3.1-8b-instant  # or claude-3-haiku-20240307

# TTS (Optional for v1)
TTS_PROVIDER=elevenlabs  # or "azure" or "none"
ELEVENLABS_API_KEY=xxx
ELEVENLABS_VOICE_ID=xxx
AZURE_TTS_KEY=xxx
AZURE_TTS_REGION=xxx

# Weather API
WEATHER_API_KEY=xxx
WEATHER_API_BASE=https://api.weatherapi.com/v1

# Calendar API (Google)
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Task API (Notion)
NOTION_API_KEY=xxx
NOTION_DATABASE_ID=xxx
```

---

## 7. Error Taxonomy

```python
# src/ultron/utils/errors.py
class ultronError(Exception):
    """Base exception with error code for client handling"""
    code: str
    user_message: str

class AudioError(ultronError): ...
class TranscriptionError(ultronError): ...
class IntentExtractionError(ultronError): ...
class ActionExecutionError(ultronError): ...
class TTSError(ultronError): ...
class PipelineError(ultronError): ...

# Specific error codes:
# AUDIO_NO_INPUT, AUDIO_INVALID_FORMAT, AUDIO_TOO_LARGE
# STT_NO_SPEECH, STT_LOW_CONFIDENCE, STT_TIMEOUT, STT_API_ERROR
# INTENT_MALFORMED_JSON, INTENT_LOW_CONFIDENCE, INTENT_UNKNOWN, INTENT_LLM_TIMEOUT
# ACTION_TIMEOUT, ACTION_AUTH_FAILED, ACTION_BAD_PARAMS, ACTION_API_DOWN, ACTION_VALIDATION_FAILED
# TTS_TIMEOUT, TTS_API_ERROR
```

---

## 8. Health Endpoint

```python
# GET /health
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "supabase": "ok",
    "stt": "ok",
    "llm": "ok",
    "weather_api": "ok"
  },
  "uptime_seconds": 12345
}
```

---

*End of Architecture Document — Ready for review before scaffold creation.*
