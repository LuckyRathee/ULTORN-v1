# Ultron V1 — Implementation Plan: Conversational Memory + Daily Proactive Briefing

> **Status**: Planning phase — ready for execution when you are  
> **Target**: Always-on desktop (Windows/macOS/Linux) → later mobile  
> **Architecture**: Hybrid local-first (STT/TTS/Embeddings/VAD/Wake) + Cloud LLM (Groq primary, Anthropic fallback)  
> **Frontend**: Tauri (Rust + WebView) talking to local FastAPI backend  
> **Privacy**: Zero cloud for audio/embeddings; cloud only for LLM reasoning  

---

## 1. Local Model Footprint & Cost

| Component | Model | Size (Disk) | RAM (Runtime) | Source | License | Cost |
|-----------|-------|-------------|---------------|--------|---------|------|
| **Wake Word** | openWakeWord (TensorFlow Lite) | 12 MB | 50 MB | GitHub | Apache 2.0 | Free |
| **VAD** | Silero VAD (ONNX) | 4 MB | 20 MB | GitHub | MIT | Free |
| **STT (local)** | whisper.cpp `ggml-base.en.bin` | 148 MB | 500 MB | GitHub | MIT | Free |
| **STT (cloud)** | Groq Whisper API | — | — | Groq | — | **Free tier**: 100 hrs/mo |
| **TTS (local)** | Piper `en_US-lessac-medium.onnx` | 52 MB | 100 MB | GitHub | MIT | Free |
| **TTS (cloud)** | ElevenLabs API | — | — | ElevenLabs | — | **Free tier**: 10k chars/mo |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | 91 MB | 120 MB | HuggingFace | Apache 2.0 | Free |
| **Vector DB** | ChromaDB (embedded) | ~50 MB | 150 MB | GitHub | Apache 2.0 | Free |
| **Session Store** | Redis (Alpine) | 30 MB | 30 MB | Docker Hub | BSD-3 | Free |
| **Scheduler** | APScheduler | <1 MB | minimal | PyPI | MIT | Free |

**Total Local Footprint**: ~350 MB disk, ~1 GB RAM (with headroom)  
**Cloud Cost**: $0/month on free tiers for typical personal use (≈50 queries/day)

> **All local models are open source (MIT/Apache 2.0), no license fees, fully offline-capable.**

---

## 2. Cloud API Free Tier Limits (Estimated Monthly)

| Service | Free Tier | Est. Personal Usage | Overhead if Exceeded |
|---------|-----------|---------------------|----------------------|
| **Groq (LLM + STT)** | 14,400 req/day (Llama 3.1 8B), 100 hrs STT | ~1,500 req/day | $0.27/M tokens / $0.11/hr STT |
| **Anthropic (fallback)** | $5 credit → ~1M tokens | Rare fallback only | $0.25/M input, $1.25/M output |
| **ElevenLabs (TTS fallback)** | 10k chars/mo | ~50k chars/mo if local fails | $5/mo for 100k chars |
| **WeatherAPI** | 1M calls/mo | 30/day = 900/mo | Free |
| **Google Calendar** | Free (OAuth) | Unlimited | Free |
| **Notion API** | Free (personal) | Unlimited | Free |

**Projected monthly cost**: **$0** (well within free tiers for single user)

---

## 3. Implementation Phases

### Phase 0: Foundation & Config (Week 0) — 4 hrs
| Task | Files | Est. |
|------|-------|------|
| Add memory/briefing config to `config.py` | `src/ultron/config.py` | 1h |
| Create `requirements-memory.txt`, `requirements-briefing.txt` | new files | 0.5h |
| Add Docker Compose for Redis + ChromaDB | `docker-compose.yml` | 0.5h |
| Model download script (whisper.cpp, piper, MiniLM) | `scripts/download_models.py` | 1h |
| Update `.env.example` with new vars | `.env.example` | 0.5h |
| Tauri sidecar config for Python backend | `src-tauri/tauri.conf.json`, `Cargo.toml` | 1h |

### Phase 1: Memory Foundation (Week 1) — 6 hrs
| Task | Files | Est. |
|------|-------|------|
| `memory/models.py` — Pydantic: `MemoryEntry`, `ConversationTurn` | `src/ultron/memory/models.py` | 0.5h |
| `memory/embeddings.py` — MiniLM wrapper (sentence-transformers) | `src/ultron/memory/embeddings.py` | 1h |
| `memory/vector_store.py` — ChromaDB client (add/query/delete) | `src/ultron/memory/vector_store.py` | 1.5h |
| `memory/session_store.py` — Redis client (get/set history, TTL) | `src/ultron/memory/session_store.py` | 1h |
| Unit tests for memory layer | `tests/test_memory.py` | 1h |
| Integration: init clients in `main.py` lifespan | `src/ultron/main.py` | 1h |

### Phase 2: Context Injection Pipeline Stage (Week 1-2) — 5 hrs
| Task | Files | Est. |
|------|-------|------|
| New stage: `stages/context_injection.py` — retrieve + format context | `src/ultron/stages/context_injection.py` | 2h |
| Register `CONTEXT_INJECTION` in state machine | `src/ultron/state/machine.py`, `states.py` | 0.5h |
| Modify `intent_extraction.py` to accept context param | `src/ultron/stages/intent_extraction.py` | 1h |
| Update `llm.py` prompt builder to inject context | `src/ultron/services/llm.py` | 1h |
| Update schemas: add `context_summary` to intent response | `src/ultron/schemas/intent.py`, `api.py` | 0.5h |

### Phase 3: Memory Persistence & Salience (Week 2) — 4 hrs
| Task | Files | Est. |
|------|-------|------|
| Post-response hook: store turn in Redis + ChromaDB | `src/ultron/stages/response.py` | 1.5h |
| Salience heuristic (topic shift, time gap, explicit "remember") | `src/ultron/memory/salience.py` (new) | 1h |
| Background task: periodic ChromaDB compaction | `src/ultron/memory/maintenance.py` | 0.5h |
| Tests: memory retrieval accuracy | `tests/test_memory_retrieval.py` | 1h |

### Phase 4: Daily Briefing Generator (Week 2-3) — 5 hrs
| Task | Files | Est. |
|------|-------|------|
| `briefing/models.py` — `BriefingConfig`, `BriefingContent` | `src/ultron/briefing/models.py` | 0.5h |
| `briefing/generator.py` — aggregate weather/calendar/tasks + format | `src/ultron/briefing/generator.py` | 2h |
| Add `get_today_events()` to calendar service | `src/ultron/services/calendar.py` | 0.5h |
| Add `get_pending_tasks()` to tasks service | `src/ultron/services/tasks.py` | 0.5h |
| Ensure weather works with default location | `src/ultron/services/weather.py` | 0.5h |
| TTS integration: generate + cache audio (piper local) | `src/ultron/briefing/tts_cache.py` (new) | 1h |

### Phase 5: Scheduler & Tauri Notifier (Week 3) — 5 hrs
| Task | Files | Est. |
|------|-------|------|
| `briefing/scheduler.py` — APScheduler job at configurable time | `src/ultron/briefing/scheduler.py` | 1h |
| `briefing/notifier.py` — abstract + `TauriNotifier` impl | `src/ultron/briefing/notifier.py` | 1h |
| Tauri Rust: notification plugin + audio playback | `src-tauri/src/notifications.rs`, `audio.rs` | 2h |
| Tauri permissions: `notification`, `fs`, `shell` | `src-tauri/tauri.conf.json` | 0.5h |
| Manual trigger endpoint: `POST /api/v1/briefing/trigger` | `src/ultron/main.py` | 0.5h |

### Phase 6: Tauri Frontend Integration (Week 3-4) — 5 hrs
| Task | Files | Est. |
|------|-------|------|
| React hook: `useBriefing` — listen for events, play audio | `frontend/src/hooks/useBriefing.ts` | 1h |
| Settings UI: briefing time, enabled toggles, test button | `frontend/src/components/BriefingSettings.tsx` | 1.5h |
| System tray menu: "Trigger Briefing Now", "Pause/Resume" | `src-tauri/src/tray.rs` | 1h |
| Auto-start on boot (Tauri plugin) | `src-tauri/tauri.conf.json`, `Cargo.toml` | 0.5h |
| Notification permission handling (macOS prompt) | `src-tauri/src/permissions.rs` | 1h |

### Phase 7: Testing, Polish, Docs (Week 4) — 4 hrs
| Task | Files | Est. |
|------|-------|------|
| E2E test: memory persists across restarts | `tests/test_e2e_memory.py` | 1h |
| E2E test: briefing fires at scheduled time | `tests/test_e2e_briefing.py` | 1h |
| Load test: 100 concurrent requests (memory + pipeline) | `tests/test_load.py` | 0.5h |
| Update README with memory/briefing setup | `README.md` | 0.5h |
| Create `AGENTS.md` for future contributors | `AGENTS.md` | 0.5h |
| Final lint/typecheck: `ruff`, `mypy`, `pytest` | — | 0.5h |

---

## 4. Total Estimates

| Metric | Value |
|--------|-------|
| **Total Implementation Time** | ~38 hours (≈1 week full-time, 2-3 weeks part-time) |
| **New Files Created** | 22 |
| **Modified Files** | 12 |
| **Test Files Added** | 4 |
| **Local Disk Footprint** | ~350 MB models + ~100 MB DB = **~450 MB** |
| **Runtime RAM** | **~1.1 GB** (fits 4 GB machine comfortably) |
| **Monthly Cloud Cost** | **$0** (free tiers) |
| **License** | All MIT/Apache 2.0 — commercial friendly |

---

## 5. Open Source / Free Tooling Used

| Category | Tool | License |
|----------|------|---------|
| Wake Word | openWakeWord | Apache 2.0 |
| VAD | Silero VAD | MIT |
| STT (local) | whisper.cpp | MIT |
| STT (cloud) | Groq API | Free tier |
| TTS (local) | Piper | MIT |
| TTS (cloud) | ElevenLabs | Free tier |
| Embeddings | sentence-transformers (MiniLM) | Apache 2.0 |
| Vector DB | ChromaDB | Apache 2.0 |
| Session Store | Redis | BSD-3 |
| Scheduler | APScheduler | MIT |
| LLM (primary) | Groq (Llama 3.1) | Free tier |
| LLM (fallback) | Anthropic Claude | Free credit |
| Frontend | Tauri | MIT/Apache 2.0 |
| Backend | FastAPI, Pydantic | MIT |
| Logging | structlog | Apache 2.0 |
| Testing | pytest | MIT |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Local STT accuracy lower than cloud | Medium | User frustration | Confidence threshold → fallback to Groq STT |
| Piper TTS voice quality | Low | Robotic sound | Offer ElevenLabs cloud fallback; test voices early |
| ChromaDB memory growth | Medium | Disk pressure | Compaction job + configurable retention (default 90 days) |
| macOS notification permission denied | High | Silent briefings | Graceful degrade: play TTS via app window + log |
| Tauri mobile (iOS/Android) not ready | Medium | Delayed mobile | Desktop-first; mobile as Phase 8+ |
| Groq rate limits hit | Low | Failed intent extraction | Exponential backoff + Anthropic fallback |

---

## 7. Open Decisions (Resolve Before Phase 0)

1. **Local STT engine**: `whisper.cpp` (C++, subprocess, smaller) vs `faster-whisper` (Python, CTranslate2, easier integration) — *leaning whisper.cpp*
2. **Piper TTS voice**: `en_US-lessac-medium` (52 MB, natural) vs `en_US-amy-low` (15 MB, smaller/faster)
3. **Model download strategy**: Script on first run vs Tauri sidecar bundle (sidecar preferred for offline install)
4. **Redis/ChromaDB**: Docker Compose (recommended) vs embedded Chroma + local Redis binary
5. **GPU acceleration**: Auto-detect Metal/CUDA/Vulkan for whisper.cpp, or CPU-only config flag

---

## 8. File Tree After Implementation

```
src/ultron/
├── memory/
│   ├── __init__.py
│   ├── models.py
│   ├── vector_store.py
│   ├── session_store.py
│   ├── embeddings.py
│   ├── salience.py
│   ├── maintenance.py
│   └── context_injection.py     # NEW STAGE (or in stages/)
├── briefing/
│   ├── __init__.py
│   ├── models.py
│   ├── scheduler.py
│   ├── generator.py
│   ├── notifier.py
│   └── tts_cache.py
├── stages/
│   ├── __init__.py
│   ├── audio_input.py
│   ├── transcription.py
│   ├── intent_extraction.py     # MODIFIED: accepts context
│   ├── context_injection.py     # NEW (or in memory/)
│   ├── action_execution.py
│   └── response.py              # MODIFIED: persists memory
├── services/
│   ├── llm.py                   # MODIFIED: context param
│   ├── weather.py               # MODIFIED: get_default_location()
│   ├── calendar.py              # MODIFIED: get_today_events()
│   └── tasks.py                 # MODIFIED: get_pending_tasks()
├── config.py                    # MODIFIED: new env vars
└── main.py                      # MODIFIED: init memory, scheduler
```

---

## 9. Next Steps

When ready to execute:

1. **Resolve open decisions** above (STT engine, Piper voice, download strategy, DB deployment, GPU)
2. **Run Phase 0** tasks to establish foundation
3. **Proceed sequentially** through Phases 1-7
4. **Run lint/typecheck/tests** after each phase: `ruff check`, `mypy src/ultron`, `pytest tests/ -v`

---

*Generated on 2026-08-27 — Ultron V1 Implementation Plan v1.0*
