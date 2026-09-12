@echo off
REM Opens the backend and frontend in two terminals.
echo Starting the AI Recruitment MVP...
start "AI Recruitment - Backend" cmd /k "%~dp0run_backend.bat"
timeout /t 5 /nobreak >nul
start "AI Recruitment - Frontend" cmd /k "%~dp0run_frontend.bat"
echo.
echo   Frontend  http://localhost:3000
echo   API docs  http://localhost:8000/docs
echo.
echo Load demo data with:  cd backend ^&^& .venv\Scripts\python seed.py --reset
