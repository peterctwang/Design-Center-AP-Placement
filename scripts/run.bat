@echo off
setlocal
cd /d "%~dp0\..\backend"
call venv\Scripts\activate
start "" http://localhost:8000
uvicorn app.main:app --port 8000
