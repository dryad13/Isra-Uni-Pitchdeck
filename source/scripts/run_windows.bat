@echo off
REM ============================================================
REM  On-Premises OMR System - Windows launcher
REM  Creates venv, installs deps, builds UI, starts the server.
REM ============================================================
setlocal enableextensions
cd /d "%~dp0.."

set "HOST=127.0.0.1"
set "PORT=8080"
set "DROPZONE=C:\OMR_Dropzone"

echo ============================================================
echo   On-Premises OMR System
echo ============================================================

REM --- Prerequisite checks ---
where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.10+ not found. Install from https://www.python.org/downloads/ and re-run.
    pause
    exit /b 1
  )
)

REM --- Folders ---
if not exist "data" mkdir "data"
if not exist "data\crops" mkdir "data\crops"
if not exist "data\backups" mkdir "data\backups"
if not exist "%DROPZONE%" (
  echo Creating dropzone folder %DROPZONE% ...
  mkdir "%DROPZONE%"
)

REM --- Python virtual environment ---
if not exist ".venv\Scripts\activate.bat" (
  echo Creating Python virtual environment...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing/updating Python dependencies...
python -m pip install --upgrade pip >nul
pip install -q -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed. Check your internet connection for first-time setup.
  pause
  exit /b 1
)

REM --- Frontend build (only if missing) ---
if not exist "frontend\dist\index.html" (
  echo Building operator console ^(first run only^)...
  where npm >nul 2>&1
  if errorlevel 1 (
    echo [WARN] npm not found - skipping UI build. Install Node.js LTS to build the console.
  ) else (
    pushd frontend
    call npm install
    call npm run build
    popd
  )
)

echo.
echo Starting OMR Platform on http://%HOST%:%PORT%
echo Dropzone: %DROPZONE%
echo Press Ctrl+C to stop.
echo.

REM Open the operator console in the default browser after a short delay.
start "" /min cmd /c "timeout /t 3 >nul & start http://%HOST%:%PORT%/"

cd backend
python -m uvicorn app.main:app --host %HOST% --port %PORT%

endlocal
