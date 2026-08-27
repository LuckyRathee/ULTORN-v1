@echo off
echo ==========================================
echo Starting Jarvis 2.0 Development Servers...
echo ==========================================

:: 1. Start the Backend server in a new CMD window
echo [Backend] Launching Uvicorn server in a new terminal...
start cmd /k "title Jarvis Backend && .\.venv\Scripts\activate.bat && set PYTHONPATH=src && uvicorn --app-dir src jarvis.main:app --reload --host 0.0.0.0 --port 8000"

:: 2. Start the Frontend server in a new CMD window
echo [Frontend] Launching Next.js server in a new terminal...
start cmd /k "title Jarvis Frontend && cd frontend && npm run dev"

:: 3. Wait for 3 seconds to let servers initialize, then open default web browser
echo [Browser] Waiting for servers to spin up...
timeout /t 3 /nobreak >nul

echo [Browser] Opening http://localhost:2311 in your default browser...
start http://localhost:2311

echo ==========================================
echo Jarvis 2.0 is launching!
echo * Frontend: http://localhost:2311
echo * Backend:  http://localhost:8000
echo ==========================================
echo Keep this window open, or press any key to close this launcher script.
pause
