@echo off
cd /d "%~dp0"
if not exist "OMR\OMR.exe" (
  echo Run "Extract OMR Demo.bat" first.
  pause
  exit /b 1
)
wscript.exe "%~dp0Launch OMR.vbs"
