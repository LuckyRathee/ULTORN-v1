# 05. Non-Tech User Guide: How to Use Ultron V1 🛠️

Welcome! You don't need to be a programmer to use **Ultron V1**. This guide shows you step-by-step how to launch, configure, and talk to Ultron on your computer.

---

## ⚡ Step 1: One-Click Launch

1. Open the project folder on your computer (`D:\GitRepo\Jarvis 2.0`).
2. Double-click the file named **`run_ultron.bat`**.
3. Two terminal windows will pop up automatically starting the backend engine and frontend interface.
4. After 3 seconds, your default web browser will open to:
   👉 **`http://localhost:2311`**

---

## 🎙️ Step 2: Talking to Ultron V1

Once the sci-fi HUD screen loads in your browser, you have **3 easy ways** to interact with Ultron:

```
┌─────────────────────────────────────────────────────────────┐
│                    3 WAYS TO TALK TO ULTRON                 │
├───────────────────┬─────────────────────────────────────────┤
│ 1. CLICK THE ORB  │ Click the glowing cyan microphone button│
│                   │ in the center to start & stop recording.│
├───────────────────┼─────────────────────────────────────────┤
│ 2. SAY "ULTRON"   │ Speak the wake word "ultron" out loud   │
│                   │ and recording starts automatically.     │
├───────────────────┼─────────────────────────────────────────┤
│ 3. TYPE A COMMAND │ Press Ctrl + K (or click the bottom bar)│
│                   │ and type your query like a search bar.  │
└───────────────────┴─────────────────────────────────────────┘
```

---

## 💬 Try These Example Voice Commands Right Away!

Here are some great commands to try out loud:

* ☀️ **Weather**:  
  > *"What's the weather like in London today?"*  
  > *"Is it raining in Tokyo right now?"*

* 📝 **Notion Tasks**:  
  > *"Add 'Deploy production update' to my Notion tasks."*  
  > *"List my current tasks."*

* 📅 **Calendar Agenda**:  
  > *"Schedule a team sync meeting tomorrow at 3 PM."*  
  > *"What's on my calendar for today?"*

---

## ❓ Simple Troubleshooting Guide

| Problem | Cause | Quick Solution |
|---------|-------|----------------|
| **Mic visualizer doesn't bounce** | Browser microphone access blocked | Click the lock icon 🔒 next to `localhost:2311` in your browser URL bar and change **Microphone** to **Allow**. |
| **Ultron says "OFFLINE" in header** | Backend server not running | Make sure the terminal window titled **Ultron Backend** is running on `http://localhost:8000`. |
| **"Microphone permission denied"** | No mic connected | Ensure your computer microphone is plugged in and unmuted in your system sound settings. |

---

## ⚙️ Customizing Settings

Click the **Settings icon** ⚙️ in the top right corner of the screen to:
* Change your backend connection URL.
* Reset your Session ID history.
* Enable or disable hands-free wake word recognition (**"ultron"**).
