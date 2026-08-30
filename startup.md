# Ultron V1 - Quick Startup & Setup Guide

This guide details the complete steps to configure, install, and run both the backend (FastAPI) and frontend (Next.js) servers for the Ultron V1 voice assistant on Windows.

---

## 📋 Prerequisites

Before starting, ensure you have the following installed globally:
1. **Python 3.11+** (Check version: `python --version`)
2. **Node.js & NPM** (Check version: `node -v` and `npm -v`)
3. **FFmpeg** (Required for browser-recorded audio conversion to WAV)
   * **Installation (Windows PowerShell):**
     ```powershell
     winget install Gyan.FFmpeg
     ```
   * *Note: Restart your terminal after installing FFmpeg so the environment variables are updated.*

---

## 🛠️ Step 1: Backend Setup & Installation

Open a **PowerShell** window at the root of the project (`D:\GitRepo\Ultron V1`):

1. **Create the Python Virtual Environment:**
   ```powershell
   python -m venv .venv
   ```

2. **Activate the Virtual Environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If Windows blocks script execution, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first, then run the activation script again).*

3. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

   *Note: Ultron V1 uses native file header signature checking to validate audio formats, so no external DLL libraries (like `libmagic` or `python-magic-bin`) are required on Windows.*

4. **Apply Supabase Migrations:**
   Copy the contents of [001_create_pipeline_runs.sql](file:///D:/GitRepo/ultron%202.0/supabase/migrations/001_create_pipeline_runs.sql) and run it inside the **SQL Editor** of your Supabase dashboard to generate the log tables.

---

## 🚀 Step 2: Running the Servers

There are two ways to run the servers: **Method A (Automatic launcher)** or **Method B (Manual terminals)**.

### Method A: One-Click Startup (Recommended)
Simply double-click the **[run_ultron.bat](file:///D:/GitRepo/ultron%202.0/run_ultron.bat)** script in your project root folder:
* It will open two separate terminal windows.
* It starts the backend (port `8000`) and the frontend (port `2311`).
* It automatically waits 3 seconds and opens `http://localhost:2311` in your default web browser.

---

### Method B: Manual Terminals
If you prefer running the servers manually, open **two separate PowerShell terminals**:

#### Terminal 1: Start the Backend (FastAPI)
Make sure the `.venv` is activated and use the `--app-dir` parameter:
```powershell
# 1. Activate venv (if not already active)
.\.venv\Scripts\Activate.ps1

# 2. Launch FastAPI with App Directory
uvicorn --app-dir src ultron.main:app --reload --host 0.0.0.0 --port 8000
```
* **Backend Endpoint:** `http://localhost:8000`
* **Health Check:** `http://localhost:8000/health`
* **API Documentation:** `http://localhost:8000/docs` (Swagger UI)

#### Terminal 2: Start the Frontend (Next.js)
Navigate to the `frontend` subfolder and run the dev server:
```powershell
# 1. Navigate to frontend
cd frontend

# 2. Launch Dev Server
npm run dev
```
* **Frontend Web App:** `http://localhost:2311`

---

## 📁 Project Directory Links

* [One-Click Startup Script](file:///D:/GitRepo/ultron%202.0/run_ultron.bat)
* [Backend Entry Point (FastAPI)](file:///D:/GitRepo/ultron%202.0/src/ultron/main.py)
* [Frontend App Component](file:///D:/GitRepo/ultron%202.0/frontend/src/app/page.tsx)
* [Backend Env Config File](file:///D:/GitRepo/ultron%202.0/.env)
* [Backend Migration Script](file:///D:/GitRepo/ultron%202.0/supabase/migrations/001_create_pipeline_runs.sql)
* [Setup & API Summary](file:///D:/GitRepo/ultron%202.0/summary.md)
