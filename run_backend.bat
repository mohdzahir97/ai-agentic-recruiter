@echo off
REM Starts the FastAPI backend with auto-reload.
cd /d "%~dp0backend"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if not exist ".env" (
    echo No .env found - copying .env.example
    copy .env.example .env
    echo.
    echo Edit backend\.env to add an LLM key. Without one the app still runs
    echo using the rule-based fallback agents.
    echo.
)

echo Starting API on http://localhost:8000  (docs at /docs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
