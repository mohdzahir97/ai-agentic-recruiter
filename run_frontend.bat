@echo off
REM Starts the Next.js dev server.
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo Starting the frontend on http://localhost:3000
call npm run dev
