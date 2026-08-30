# 04. Future Roadmap: The 8-Level Agentic Capability Ladder 🚀

## Vision

The long-term vision of **Ultron V1** is to evolve from a voice-command tool into a **fully autonomous, screen-aware AI agent** that plans, executes, learns, and operates across your entire digital life.

---

## 🪜 The 8-Level Agentic Capability Ladder

```
 LEVEL 8 │ Autonomous Skill Synthesis & Learning      [Planned]
 LEVEL 7 │ Autonomous Background Goal Pursuit         [Planned]
 LEVEL 6 │ OS & App Automation (RPA Clicking/Typing)  [Planned]
 LEVEL 5 │ Screen & Context Awareness (Vision LLMs)   [Planned]
 LEVEL 4 │ Multi-Step ReAct Planning & Tool Chaining   [In Progress]
 LEVEL 3 │ Proactive Daily Briefings & Memory         [LIVE ✅]
 LEVEL 2 │ Multi-Turn Conversation History            [LIVE ✅]
 LEVEL 1 │ Single-Turn Voice Command Execution        [LIVE ✅]
```

---

## 📅 Roadmap Phase Breakdown

### Level 1–3: The Voice Foundation (LIVE ✅)
* **What it does**: Voice capture, 7-stage state machine, structured intent routing, Supabase run tracing, memory persistence, and daily briefings.

---

### Level 4: The Agent Core — Multi-Step Planning (In Progress 🚧)
* **Goal**: Enable Ultron to break complex user goals into multi-step action plans.
* **Example**:
  > *User*: "Plan my 3-day business trip to London next month."  
  > *Ultron*: 
  > 1. Decomposes into subtasks: [Search Flights ➔ Check Weather ➔ Draft Calendar ➔ Create Notion Itinerary].
  > 2. Executes each step via tools (web search, calendar, email).
  > 3. Reports progress and asks for user confirmation at key decision points.

---

### Level 5: Screen Vision & Context Awareness 👁️
* **Goal**: Give Ultron eyes to see what is currently open on your monitor.
* **Technology**:
  * **Screen Grab**: Continuous 1-2 fps screen capture using `mss`.
  * **Local Vision LLM**: Lightweight vision models (Moondream 1.8B / LLaVA) running locally.
  * **Use Case**: Say *"Ultron, look at this document"* and Ultron reads the open window on your monitor without requiring file uploads.

---

### Level 6–7: OS Automation & Autonomous Goals 🤖
* **Goal**: Enable hands-free desktop control (clicking buttons, typing forms, operating apps) and persistent background goals.
* **Example**:
  > *Goal*: "Keep my email inbox at zero."  
  > *Ultron*: Runs a background loop every 30 minutes, archiving newsletters, labeling important client emails, and drafting responses.

---

### Level 8: Self-Improvement & Skill Learning 🧠
* **Goal**: Allow Ultron to learn new workflow skills directly from user demonstrations.
* **Mechanism**: If you show Ultron a repetitive sequence of actions twice, Ultron synthesizes a reusable, versioned automation skill script for the future.

---

## 🔒 Open Source & Privacy Commitment

* **100% Local Privacy Option**: Screen capture bytes and vision processing stay strictly on your local computer.
* **Zero Proprietary Lock-In**: Built using open standards (Playwright, ChromaDB, Ollama, Moondream) so you own your assistant completely.
