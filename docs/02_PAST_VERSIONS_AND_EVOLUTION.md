# 02. Past Versions & Project Evolution 📜

This document details the development history, past milestones, and architectural lessons learned during the transition from **Jarvis 2.0** to **Ultron V1**.

---

## ⏳ Project History Timeline

```
                                 PROJECT EVOLUTION
 ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
 │  Jarvis 1.0 / Proto  │ ➔ │      Jarvis 2.0      │ ➔ │      ULTRON V1       │
 │ Basic text/audio bot │    │ 5-Stage State Machine│    │ Autonomous AI Agent  │
 │ (Single script)      │    │ Backend + Next.js UI │    │ Multi-Modal + Vision │
 └──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Phase 1: The Initial Prototype (Jarvis 1.0)
* **Goal**: Build a minimal proof-of-concept voice assistant in Python.
* **Limitations**: 
  * Simple script wrapper around API calls.
  * No state tracking—if an API call timed out, the entire app crashed silently.
  * Microphone audio was recorded to temporary disk files without header validation.

### Phase 2: Scaffold & Typed Schemas (Jarvis 2.0 Architecture)
* **Goal**: Re-architect the application into a production-grade backend using FastAPI.
* **Key Improvements**:
  * Introduced Pydantic Discriminated Unions for intent routing (`WeatherIntent`, `CalendarCreateIntent`, `TaskCreateIntent`).
  * Structured exception taxonomy with typed error codes (`timeout`, `auth`, `rate_limit`, `bad_params`).
  * Added Supabase per-request telemetry tracing.

### Phase 3–6: Action Integration & Frontend Cockpit
* **Goal**: Connect real-world third-party APIs and build a futuristic Next.js user interface.
* **Key Improvements**:
  * Connected WeatherAPI.com, Notion Database API, and Google Calendar.
  * Created browser-native Web Audio API `AnalyserNode` live frequency metering for dynamic mic pulsing and visualizer waveforms.
  * Added hands-free Speech Recognition for **"ultron"** wake-word auto-recording.

### Phase 7: Re-Branding to ULTRON V1
* **Goal**: Evolve the project from a basic voice prototype into an autonomous, screen-aware AI agent.
* **Key Improvements**:
  * Renamed package to `src/ultron/` and frontend to `ultron-frontend`.
  * Added ReAct multi-step planning roadmap & screen vision specs.
  * Fully responsive mobile & tablet HUD UI layout.

---

## 🛠️ 4 Major Engineering Battles Fought & Solved

During the development of Jarvis 2.0 ➔ Ultron V1, four major technical roadblocks were encountered and solved:

### 1. The Browser Audio & `[tone]` Silence Trap
* **The Problem**: Web browsers record audio in WebM format. When sent directly to Speech-to-Text models, models would output `[tone]`, `[music]`, or silence due to missing WAV byte headers.
* **The Solution**: Built a native validation & FFmpeg byte-conversion pipeline that converts incoming WebM streams to clean WAV bytes before STT processing.

### 2. Midnight LLM Model Deprecations
* **The Problem**: Cloud LLM model endpoints (`llama-3.1-8b-instant`) were updated overnight, resulting in 404 errors during intent extraction.
* **The Solution**: Migrated to `qwen/qwen3.6-27b` with strict Pydantic tool-calling, guaranteeing valid JSON schemas instead of relying on unpredictable free-form text.

### 3. Voice API Paywall & Voice Design Workaround
* **The Problem**: Upgrading to ElevenLabs v2 hit tier restrictions blocking default library voice IDs on free accounts.
* **The Solution**: Used ElevenLabs Voice Design to programmatically generate a custom Voice ID (`OFaywfVNe05ncpeSth45`), bypassing API restrictions while keeping voice synthesis crisp.

### 4. Async Callback Spaghetti ➔ 7-Stage State Machine
* **The Problem**: As features expanded, nested `if/elif` async handlers became unmaintainable and hard to debug.
* **The Solution**: Re-architected the pipeline into an explicit 7-stage state machine (`LISTENING ➔ TRANSCRIBING ➔ INTENT ➔ CONFIRMING ➔ EXECUTING ➔ RESPONDING ➔ TTS`). Each stage is a pure function with millisecond latency logging.
