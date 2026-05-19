@echo off
REM Design Center - AP Placement / Windows stop script
REM 殺掉占用指定 port 的 uvicorn process (預設 8000)
setlocal

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

echo === Stopping server on port %PORT% ===

set "FOUND="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo Killing PID %%P
    taskkill /F /PID %%P >nul 2>&1
    if not errorlevel 1 (
        echo   [OK] PID %%P terminated
        set "FOUND=1"
    ) else (
        echo   [WARN] PID %%P already gone
    )
)

if not defined FOUND (
    echo No process listening on port %PORT%.
    exit /b 0
)

echo === Done ===
endlocal
