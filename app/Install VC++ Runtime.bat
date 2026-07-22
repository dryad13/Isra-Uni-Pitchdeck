@echo off
setlocal enableextensions
cd /d "%~dp0"

if exist "%SystemRoot%\System32\vcruntime140.dll" (
  echo Visual C++ runtime is already installed.
  pause
  exit /b 0
)

if exist "vc_redist.x64.exe" (
  echo Installing Visual C++ 2015-2022 runtime (one-time)...
  vc_redist.x64.exe /install /quiet /norestart
  if errorlevel 1 (
    echo Install failed. Try running vc_redist.x64.exe manually.
    pause
    exit /b 1
  )
  echo Install complete. Now run Start OMR.bat
  pause
  exit /b 0
)

echo vc_redist.x64.exe not found on this USB folder.
echo Download "Microsoft Visual C++ 2015-2022 Redistributable (x64)" from Microsoft
echo and install it once, then run Start OMR.bat again.
pause
