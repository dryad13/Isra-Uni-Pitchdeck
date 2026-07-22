@echo off
taskkill /IM OMR.exe /F >nul 2>&1
if errorlevel 1 (
  echo OMR is not running.
) else (
  echo OMR stopped.
)
timeout /t 2 >nul
