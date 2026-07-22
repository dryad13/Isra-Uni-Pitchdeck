@echo off
taskkill /IM OMR.exe /F >nul 2>&1
echo OMR stopped.
timeout /t 2 >nul
