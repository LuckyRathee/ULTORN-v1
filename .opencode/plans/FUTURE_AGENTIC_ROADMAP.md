# Ultron V1 — Future Roadmap: Full Agentic AI

> **Vision**: Transform from voice assistant → autonomous agent that plans, executes, learns, and operates across your digital life.
> **Current State**: 5-stage pipeline (STT → Intent → Execute → Respond) with memory + briefing (Phases 0-7)
> **Target**: Persistent agent with planning, tool use, screen awareness, and cross-app automation

---

## Agentic Capability Ladder

| Level | Capability | Current Status | Target |
|-------|------------|----------------|--------|
| **L1** | Single-turn command execution | ✅ Done | — |
| **L2** | Multi-turn conversation + memory | 🚧 Phases 1-3 | Phase 3 complete |
| **L3** | Proactive briefings + scheduling | 🚧 Phases 4-6 | Phase 6 complete |
| **L4** | **Multi-step planning & tool chaining** | ❌ | **Phase 8-10** |
| **L5** | **Screen/context awareness (vision)** | ❌ | **Phase 11-12** |
| **L6** | **OS/app automation (RPA)** | ❌ | **Phase 13-15** |
| **L7** | **Autonomous goal pursuit** | ❌ | **Phase 16-18** |
| **L8** | **Self-improvement / skill learning** | ❌ | **Phase 19+** |

---

## Phase 8-10: Planning & Tool Chaining (The "Agent Core")

### 8.1 Task Planner (Weeks 1-2)
```
User: "Plan my trip to Tokyo next month"
Agent: 
  1. Decompose → [Flights, Hotels, Itinerary, Visa, Budget]
  2. Create subtasks with dependencies
  3. Execute each via tools (web search, calendar, email)
  4. Report progress, ask for confirmations at decision points
```

**New Components:**
| File | Purpose |
|------|---------|
| `src/ultron/agent/planner.py` | LLM-based task decomposition (ReAct / Plan-and-Execute) |
| `src/ultron/agent/executor.py` | Executes plan steps, handles retries/branching |
| `src/ultron/agent/tools/__init__.py` | Tool registry (weather, calendar, web, email, shell) |
| `src/ultron/agent/tools/web_search.py` | Brave/SerpAPI + summarization |
| `src/ultron/agent/tools/shell.py` | Safe command execution (allowlist) |
| `src/ultron/agent/state.py` | Plan state: `Plan`, `Step`, `StepStatus`, `Artifact` |

**Key Patterns:**
- **ReAct**: Thought → Action → Observation loop
- **Plan-and-Execute**: Generate full plan first, then execute
- **Tool schema**: Pydantic models for each tool (type-safe, like current intents)

### 8.2 Tool Ecosystem (Weeks 2-3)
| Tool | API / Method | Priority |
|------|--------------|----------|
| Web Search | Brave Search API / SerpAPI | P0 |
| Email (Gmail/Outlook) | OAuth2 + Gmail API | P0 |
| File Ops | Local FS (read/write/list/glob) | P0 |
| Calendar (write) | Google Calendar API | P0 |
| Notion (write) | Notion API | P0 |
| Browser Automation | Playwright (headless) | P1 |
| API Connector | Generic REST/GraphQL client | P1 |
| Code Execution | Sandboxed Python (Docker/Wasmer) | P2 |

### 8.3 Approval Gates (Week 3)
- **Destructive actions** (send email, delete file, spend money) → require explicit voice confirmation
- **Reversible actions** (search, read, draft) → auto-execute
- **Policy engine**: `src/ultron/agent/policy.py` with rules per tool/action

---

## Phase 11-12: Screen & Context Awareness (Vision)

### 11.1 Screen Capture Pipeline (Week 1)
| Component | Tech | Notes |
|-----------|------|-------|
| Screen capture | `mss` (cross-platform) / Windows GraphicsCapture | 1-2 fps continuous |
| OCR | Tesseract / PaddleOCR / Apple Vision | Local, fast |
| UI Element Detection | YOLO / OmniParser (Microsoft) | Detect buttons, fields |
| Vision LLM | Local (LLaVA, Moondream) or Cloud (GPT-4V, Claude) | For "what's on screen?" queries |

### 11.2 Context Injection (Week 2)
- **Always-on context**: "Current screen: Chrome tab 'GitHub PR #234', VS Code open on `main.py`"
- **Privacy**: Local-only processing; screen bytes never leave machine
- **Trigger**: User says "look at this" or agent proactively notices relevant context

**New Files:**
```
src/ultron/vision/
├── capture.py          # Cross-platform screen grab
├── ocr.py              # Text extraction
├── ui_detector.py      # Element detection
├── vision_llm.py       # Local/cloud vision model wrapper
└── context_provider.py # Injects screen context into LLM prompt
```

---

## Phase 13-15: OS & App Automation (RPA)

### 13.1 Cross-Platform Automation Layer (Week 1-2)
| Platform | Library | Capabilities |
|----------|---------|--------------|
| Windows | `uiautomation` / `pywinauto` (but cross-platform!) | Click, type, scroll, window mgmt |
| macOS | `atomacos` / Accessibility API | Same |
| Linux | `atspi` / `dogtail` | Same |

**Abstraction**: `src/ultron/automation/controller.py` with unified `click(selector)`, `type(text)`, `scroll()`, `switch_app(name)`

### 13.2 Skill System (Week 2-3)
- **Skills** = reusable automation scripts (e.g., "book_flight", "format_notion_page")
- **Discovery**: Agent learns skills from user demonstrations (programming by demonstration)
- **Storage**: `src/ultron/skills/registry.py` — versioned, shareable, parameterized

### 13.3 App-Specific Connectors (Week 3)
| App | Connector | Actions |
|-----|-----------|---------|
| VS Code | Extension + MCP | Open file, run command, get diagnostics |
| Browser | CDP / Playwright | Navigate, extract, fill forms |
| Terminal | PTY wrapper | Run cmd, capture output, send keys |
| Slack/Discord | Bot API + User Token | Read channels, send DM, search |

---

## Phase 16-18: Autonomous Goal Pursuit

### 16.1 Goal Manager (Week 1)
```
User: "Keep my inbox at zero"
Agent:
  - Creates persistent goal: InboxZeroGoal
  - Schedules periodic check (every 30 min)
  - Auto-archives newsletters, labels important, drafts replies
  - Reports daily: "Archived 47, labeled 3, drafted 2 replies"
```

**Components:**
- `Goal` class: objective, success criteria, schedule, constraints
- `GoalMonitor`: evaluates progress, triggers actions
- `GoalMemory`: persists across restarts (ChromaDB + Redis)

### 16.2 Background Agent Loop (Week 2)
- **Event-driven**: File changes, calendar events, email arrivals, system notifications
- **Polling fallback**: For apps without webhooks
- **Resource budget**: CPU/RAM limits, quiet hours, battery awareness

### 16.3 Multi-Agent Delegation (Week 3)
- **Specialist agents**: `EmailAgent`, `ResearchAgent`, `CodingAgent`, `CalendarAgent`
- **Orchestrator**: Routes tasks, merges results, handles conflicts
- **Communication**: Message bus (Redis pub/sub or in-process)

---

## Phase 19+: Self-Improvement & Learning

### 19.1 Feedback Loop (Week 1)
- **Explicit**: "That was wrong", "Good job", thumbs up/down
- **Implicit**: User repeats request → previous attempt failed; User interrupts → annoyance
- **Storage**: `FeedbackEntry` in ChromaDB with embedding for similarity

### 19.2 Prompt / Tool Optimization (Week 2)
- **Prompt tuning**: A/B test system prompts, few-shot examples
- **Tool selection**: Learn which tools work for which intents
- **Failure analysis**: Categorize errors, suggest new tools/skills

### 19.3 Skill Synthesis (Week 3)
- **From demonstration**: User shows "do X, then Y, then Z" → agent generates skill
- **From code**: User pastes Python snippet → agent wraps as tool
- **From natural language**: "Whenever I get a GitHub notification, summarize it and add to Notion" → agent creates automation rule

---

## Architecture Evolution

```
CURRENT (Pipeline)                    FUTURE (Agentic)
┌─────────────────────┐               ┌─────────────────────────────┐
│  FastAPI Server     │               │  Agent Runtime (Persistent)  │
│  - Request/Response │               │  - Event Loop               │
│  - Stateless        │               │  - Goal Manager             │
└─────────┬───────────┘               │  - Skill Registry           │
          │                           │  - Tool Executor            │
          ▼                           │  - Planner                  │
┌─────────────────────┐               │  - Memory (Vector + KV)     │
│  State Machine      │               └──────────────┬──────────────┘
│  - 5 Fixed Stages   │                              │
└─────────────────────┘                              ▼
                           ┌─────────────────────────────────────┐
                           │           Tool / Skill Layer        │
                           │  Web │ Email │ FS │ Browser │ OS   │
                           └─────────────────────────────────────┘
```

---

## Resource Requirements (Projected)

| Phase | RAM | Disk | CPU | GPU |
|-------|-----|------|-----|-----|
| Current (Ph 0-7) | 1.1 GB | 450 MB | 2 cores | Optional |
| + Planning (8-10) | +500 MB | +200 MB | +1 core | Optional |
| + Vision (11-12) | +1.5 GB | +2 GB | +2 cores | **Recommended** (4GB VRAM) |
| + Automation (13-15) | +300 MB | +100 MB | +1 core | No |
| + Autonomy (16-18) | +200 MB | +100 MB | +0.5 core | No |
| **Full Stack** | **~3.5 GB** | **~3 GB** | **6 cores** | **4 GB VRAM** |

> Still runs on a modern laptop (16 GB RAM, 8 cores, dGPU or Apple Silicon).  
> For low-power: disable vision, use cloud vision API, drop local LLM.

---

## Open Source / Free Stack Commitment

| Layer | Tools (All MIT/Apache/BSD) |
|-------|----------------------------|
| Planning | LangGraph, AutoGen, or custom ReAct (no framework lock-in) |
| Vision | Moondream (1.8B, Apache 2.0), LLaVA, OmniParser |
| Automation | `uiautomation`, `atomacos`, `atspi` — all open source |
| Browser | Playwright (Apache 2.0) |
| Local LLM | llama.cpp, ollama, LM Studio — all open weights |
| Embeddings | BGE, Nomic, MiniLM — all open |
| Vector DB | ChromaDB, Qdrant — Apache 2.0 |
| Scheduler | APScheduler — MIT |

**Zero proprietary dependencies required.** Cloud APIs only for convenience/quality fallback.

---

## Milestone Timeline (If Full-Time)

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| **M1: Agent Core** | Month 1 | Planner + 5 tools + approval gates |
| **M2: Vision** | Month 2 | Screen context + "look at this" |
| **M3: Automation** | Month 3 | Cross-platform click/type + 3 app connectors |
| **M4: Autonomy** | Month 4 | Persistent goals + background loop |
| **M5: Learning** | Month 5 | Feedback loop + skill synthesis |
| **M6: Polish** | Month 6 | Installer, auto-update, docs, tests |

**Part-time (nights/weekends)**: ~12-18 months to M6.

---

## Immediate Next Steps (After Phase 7)

1. **Add `agent/` package** to `src/ultron/` — planner, executor, tool registry
2. **Define `Tool` protocol** — mirror `Intent` discriminated union pattern
3. **Implement 3 tools**: Web Search, File Read, Shell (allowlisted)
4. **Add `PLANNING` stage** to state machine (after `EXTRACTING_INTENT`)
5. **Build minimal ReAct loop** in executor — test with "Research X and save to Notion"

---

## Decision Points (Resolve at Each Milestone)

| Milestone | Decision |
|-----------|----------|
| M1 | Custom planner vs LangGraph vs AutoGen |
| M2 | Local vision model (Moondream) vs Cloud (GPT-4V/Claude) |
| M3 | Accessibility API vs Playwright vs Hybrid for automation |
| M4 | Single agent with skills vs Multi-agent orchestration |
| M5 | Fine-tuning vs RAG vs Prompt optimization for learning |

---

*This roadmap is a living document. Update as you complete Phases 0-7 and learn what works.*
