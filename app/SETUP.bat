@echo off
cd /d "%~dp0"
if errorlevel 1 (
  echo Could not open this folder.
  pause
  exit /b 1
)

if exist "OMR\OMR.exe" (
  echo Already set up. Double-click START.vbs
  pause
  exit /b 0
)

if not exist "OMR-Demo.zip" (
  echo OMR-Demo.zip is missing from this folder.
  pause
  exit /b 1
)

echo Extracting... wait 1-3 minutes on older PCs.
cd /d "%~dp0"
tar -xf "OMR-Demo.zip" -C .
if errorlevel 1 (
  echo tar failed, trying PowerShell...
  powershell -NoProfile -Command "Set-Location -LiteralPath '%~dp0'; Expand-Archive -LiteralPath 'OMR-Demo.zip' -DestinationPath '.' -Force"
)

if not exist "OMR\OMR.exe" (
  echo Extract failed. Copy the whole folder from USB and try again.
  pause
  exit /b 1
)

echo Done. Double-click START.vbs
pause
