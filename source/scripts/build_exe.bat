@echo off
REM ============================================================
REM  Build the On-Premises OMR System as a standalone Windows
REM  executable (PyInstaller one-folder bundle).
REM
REM  Run this ON the Windows machine (PyInstaller is not a
REM  cross-compiler). Requires Python 3.10+ and Node.js LTS.
REM
REM  Output: backend\dist\OMR\OMR.exe
REM  Ship the ENTIRE backend\dist\OMR folder to target machines.
REM ============================================================
setlocal enableextensions
cd /d "%~dp0.."

echo ============================================================
echo   Building OMR standalone executable
echo ============================================================

REM --- Prerequisites ---
where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.10+ not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
  )
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found. Install Node.js LTS to build the operator console.
  pause
  exit /b 1
)

REM --- Python environment + build tooling ---
if not exist ".venv\Scripts\activate.bat" (
  echo Creating Python virtual environment...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
if errorlevel 1 ( echo [ERROR] Runtime dependency install failed. & pause & exit /b 1 )
pip install -r backend\requirements-build.txt
if errorlevel 1 ( echo [ERROR] Build tooling install failed. & pause & exit /b 1 )

REM --- Frontend build ---
echo Building operator console...
pushd frontend
call npm install
call npm run build
if errorlevel 1 ( echo [ERROR] Frontend build failed. & popd & pause & exit /b 1 )
popd

REM --- PyInstaller (run from backend so spec relative paths resolve) ---
echo Running PyInstaller...
pushd backend
pyinstaller --clean --noconfirm omr.spec
set "PYI_ERR=%errorlevel%"
popd
if not "%PYI_ERR%"=="0" ( echo [ERROR] PyInstaller build failed. & pause & exit /b 1 )

echo.
echo ============================================================
echo   Build complete.
echo   Executable: backend\dist\OMR\OMR.exe
echo   Distribute the ENTIRE backend\dist\OMR folder.
echo ============================================================
pause
endlocal
