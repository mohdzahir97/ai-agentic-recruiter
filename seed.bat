@echo off
REM Loads demo accounts, jobs, resumes and applications.
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
python seed.py %*
