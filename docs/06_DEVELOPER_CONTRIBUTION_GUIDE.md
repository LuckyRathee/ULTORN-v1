# 06. Developer Contribution & File System Guide 💻

Welcome to the Developer & Contributor Guide for **Ultron V1**. This document is designed for engineers, contributors, or future developers who want to understand the codebase structure, how data flows through the files, and how to add new features, tools, or stages to Ultron V1.

---

## 🗂️ Complete File System Directory Map

```
Jarvis 2.0/                          # Project Root
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore patterns
├── pyproject.toml                   # Python dependencies & build config
├── requirements.txt                 # Pip requirements file
├── run_ultron.bat                   # One-click Windows launcher script
├── docker-compose.yml               # Container deployment configuration
│
├── docs/                            # Documentation Hub
│   ├── README.md                    # Master documentation index
│   ├── 01_PROJECT_OVERVIEW.md       # Non-technical conceptual overview
│   ├── 02_PAST_VERSIONS_AND_EVOLUTION.md # History & lessons learned
│   ├── 03_CURRENT_ARCHITECTURE.md   # 7-Stage State Machine specification
│   ├── 04_FUTURE_ROADMAP.md        # 8-Level Agentic Capability Ladder
│   ├── 05_NON_TECH_USER_GUIDE.md    # End-user setup & prompt guide
│   ├── 06_DEVELOPER_CONTRIBUTION_GUIDE.md # (This file) Codebase map & developer guide
│   └── architecture.md              # Technical engineering spec
│
├── src/
│   └── ultron/                      # Core Backend Python Package
│       ├── __init__.py
│       ├── main.py                  # FastAPI application entry point & routes
│       ├── config.py                # Pydantic Settings (.env configuration loader)
│       │
│       ├── schemas/                 # Pydantic Data Models (Single Source of Truth)
│       │   ├── api.py               # Request & Response HTTP API models
│       │   ├── intent.py            # Discriminated Union Intent schemas (Weather, Tasks, Calendar)
│       │   └── pipeline.py          # PipelineRun, StageResult, & StageStatus models
│       │
│       ├── state/                   # Typed State Machine Engine
│       │   ├── states.py            # PipelineState Enum & StateData data carrier
│       │   └── machine.py           # StateMachine class (orchestrates stage transitions)
│       │
│       ├── stages/                  # Pipeline Stage Execution Functions
│       │   ├── audio_input.py       # Stage 1: Native header validation & WebM➔WAV conversion
│       │   ├── transcription.py     # Stage 2: STT Whisper / ElevenLabs Scribe transcript
│       │   ├── context_injection.py # Context Provider (injects memory/session history)
│       │   ├── intent_extraction.py # Stage 3: LLM function-calling → Intent object
│       │   ├── action_execution.py  # Stage 4: Router → executes Weather/Tasks/Calendar services
│       │   └── response.py          # Stage 5: Formats natural response text + TTS speech
│       │
│       ├── services/                # External API Connectors & Integrations
│       │   ├── stt.py               # ElevenLabs Scribe v2 + Groq Whisper STT API
│       │   ├── llm.py               # Groq Qwen/Llama3 & Anthropic Claude tool-calling
│       │   ├── tts.py               # ElevenLabs Multilingual v2 + Azure TTS
│       │   ├── weather.py           # WeatherAPI.com client
│       │   ├── calendar.py          # Google Calendar API (OAuth2) client
│       │   └── tasks.py             # Notion Database API client
│       │
│       ├── memory/                  # Session & Vector Memory Engine
│       │   ├── session_store.py     # Short-term session memory store
│       │   ├── vector_store.py      # ChromaDB / Vector memory retriever
│       │   ├── embeddings.py        # Local/Cloud text embedding generator
│       │   └── salience.py          # Conversation salience & memory ranker
│       │
│       ├── briefing/                # Daily Briefing System
│       │   ├── generator.py         # Daily briefing content generator
│       │   ├── scheduler.py         # Scheduled cron briefing trigger
│       │   └── notifier.py          # Console & webhook briefing notifier
│       │
│       ├── persistence/             # Telemetry & Storage Logging
│       │   └── supabase.py          # Supabase client (persists request stage latency)
│       │
│       └── utils/                   # Helper Utilities
│           ├── audio.py             # Native FFmpeg audio converter wrapper
│           ├── errors.py            # Typed exception hierarchy (UltronError base)
│           └── logging.py           # Structlog JSON line formatter
│
├── frontend/                        # Next.js Frontend Web App
│   ├── package.json                 # Frontend dependencies (Next 16, React 19, Tailwind)
│   ├── next.config.ts               # Next.js compiler settings
│   └── src/
│       ├── app/                     # Next.js App Router
│       │   ├── layout.tsx           # Global HTML layout & metadata
│       │   ├── page.tsx             # Main Dashboard Cockpit page
│       │   └── globals.css          # Tailwind CSS & sci-fi HUD theme styles
│       │
│       ├── components/ui/           # Modular Futuristic React Components
│       │   ├── HudHeader.tsx        # Top telemetry navigation header & ping indicator
│       │   ├── PulsarCore.tsx       # Central glowing visualizer orb & mic button
│       │   ├── PipelineTracker.tsx  # 7-stage state machine timeline & diagnostic modal
│       │   ├── ConsoleInput.tsx     # Command prompt bar & suggestion chips
│       │   ├── UltronWidgets.tsx    # Response output & tactical tab widgets
│       │   ├── TelemetrySidebar.tsx # Right drawer run history telemetry logs
│       │   ├── SettingsModal.tsx    # Configuration modal dialog
│       │   └── SciFiBackground.tsx  # Animated background grid canvas
│       │
│       └── utils/
│           └── audioSynthesizer.ts  # Web Audio API sound FX synthesizer (clicks, beeps)
│
└── tests/                           # Pytest Test Suite
    ├── test_audio_transcription.py  # Stage 1-2 audio input & STT unit tests
    ├── test_intent_extraction.py   # Stage 3 LLM tool-calling intent extraction tests
    ├── test_weather.py              # Weather service integration & error handling tests
    ├── test_calendar.py             # Calendar service unit tests
    ├── test_tasks.py                # Notion tasks service unit tests
    ├── test_tts.py                  # ElevenLabs/Azure TTS synthesis tests
    ├── test_supabase_logging.py     # Persistence run logging tests
    ├── test_e2e_pipeline.py         # Full end-to-end state machine pipeline tests
    ├── test_memory.py               # Memory persistence tests
    └── test_briefing.py             # Daily briefing generator unit tests
```

---

## 🔄 Execution Data Flow (Trace of a Request)

Here is exactly what happens in the codebase when a user types or speaks a query:

```
1. Frontend User Action (page.tsx)
   └─ User speaks or enters text prompt into ConsoleInput.tsx.

2. HTTP POST Request 
   └─ Page sends POST to `http://localhost:8000/api/v1/process-text` (or `/api/v1/process-audio`).

3. FastAPI Route Handler (src/ultron/main.py)
   └─ Instantiates `PipelineRun` and `StateData` object.
   └─ Calls `get_state_machine().run(state)`.

4. State Machine Loop (src/ultron/state/machine.py)
   └─ Executes pure stage handlers sequentially:
      1. handle_audio_input()      (audio_input.py)
      2. handle_transcription()    (transcription.py)
      3. handle_context_injection()(context_injection.py)
      4. handle_intent_extraction()(intent_extraction.py)
      5. handle_action_execution() (action_execution.py)
      6. handle_response()         (response.py)

5. External Service Execution (src/ultron/services/)
   └─ Calls Weather API, Notion, Google Calendar, or ElevenLabs TTS.

6. Telemetry Logging (src/ultron/persistence/supabase.py)
   └─ Logs request status, stage output, and latency_ms to Supabase DB.

7. Frontend HUD Update (page.tsx ➔ UltronWidgets.tsx)
   └─ UI updates response text, plays synthesized base64 voice MP3, and highlights pipeline stage telemetry.
```

---

## 👩‍💻 How to Extend Ultron V1 (Developer Recipes)

### Recipe 1: How to Add a New Action / Tool (e.g., Spotify, Gmail, Email)

To add a new tool or integration (e.g. `EmailIntent`), follow these 6 simple steps:

1. **Define the Intent Schema** (`src/ultron/schemas/intent.py`):
   ```python
   class SendEmailIntent(BaseModel):
       type: Literal["send_email"] = "send_email"
       recipient: str = Field(description="Email address of recipient")
       subject: str = Field(description="Subject line")
       body: str = Field(description="Body message text")
       confidence: float = Field(default=1.0)
   
   # Add to Intent union:
   Intent = Union[WeatherIntent, TaskCreateIntent, SendEmailIntent, UnknownIntent]
   ```

2. **Add LLM Tool Function Schema** (`src/ultron/services/llm.py`):
   Add the JSON Schema function tool definition to `EXTRACTION_TOOLS` so Groq LLM can extract it automatically.

3. **Create the Service Connector Module** (`src/ultron/services/email.py`):
   Create your API wrapper function `async def send_email(...)` inheriting from `UltronError` for typed exception handling.

4. **Register in Action Router** (`src/ultron/stages/action_execution.py`):
   Add a match case inside `handle_action_execution`:
   ```python
   case "send_email":
       result = await send_email(intent.recipient, intent.subject, intent.body)
   ```

5. **Add Unit Tests** (`tests/test_email.py`):
   Write pytest unit tests covering success, timeout, and authentication error paths.

6. **Add UI Widget** (`frontend/src/components/ui/UltronWidgets.tsx`):
   Add display formatting to render the result nicely in the cockpit dashboard.

---

### Recipe 2: How to Add a New Pipeline Stage

1. Add the new state enum to `PipelineState` in `src/ultron/state/states.py`.
2. Create the stage handler file `src/ultron/stages/my_new_stage.py` with signature `async def handle_my_new_stage(state: StateData) -> StateData`.
3. Register the stage in `get_state_machine()` inside `src/ultron/main.py`.

---

## 🧪 Testing & Verification Commands

```bash
# 1. Run all backend unit tests (excluding integration tests requiring API keys):
python -m pytest -m "not integration" -v

# 2. Run full backend test suite with coverage report:
python -m pytest --cov=src/ultron tests/

# 3. Test Next.js production build:
cd frontend
npm run build

# 4. Start Next.js dev server with hot reload:
cd frontend
npm run dev
```
