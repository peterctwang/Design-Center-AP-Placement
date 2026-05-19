@echo off
setlocal
cd /d "%~dp0\.."

echo === 1/3 Backend venv + pip install ===
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo === 2/3 Frontend npm install + build ===
cd ..\frontend
call npm install
if errorlevel 1 goto error
call npm run build
if errorlevel 1 goto error

echo.
echo === 3/3 Done! ===
echo.
echo Start the server with:
echo     scripts\run.bat
echo.
echo Or manually:
echo     cd backend
echo     venv\Scripts\activate
echo     uvicorn app.main:app --port 8000
echo.
goto :eof

:error
echo.
echo *** Setup FAILED. Scroll up for details. ***
exit /b 1
