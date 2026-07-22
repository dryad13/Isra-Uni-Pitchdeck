@echo off
setlocal enableextensions
cd /d "%~dp0"

if exist "OMR\OMR.exe" (
  echo Already extracted.
  echo Next: double-click "NEW 2 - Launch OMR (no black window).vbs"
  pause
  exit /b 0
)

if not exist "OMR-Demo.zip" (
  echo [ERROR] OMR-Demo.zip not found in this folder.
  pause
  exit /b 1
)

echo Step 1/2 - Verifying zip...
if exist "OMR-Demo.zip.sha256" (
  for /f "tokens=1" %%H in (OMR-Demo.zip.sha256) do set "EXPECTED=%%H"
  powershell -NoProfile -Command "$h=(Get-FileHash -Algorithm SHA256 'OMR-Demo.zip').Hash.ToLower(); if($h -ne '%EXPECTED%'.ToLower()){Write-Host 'FAIL - zip corrupted. Re-copy from USB.'; exit 1}; Write-Host 'Checksum OK'"
  if errorlevel 1 ( pause & exit /b 1 )
)

echo Step 2/2 - Extracting (1-3 minutes on older PCs)...
where tar >nul 2>&1
if not errorlevel 1 (
  tar -xf "OMR-Demo.zip" -C "%~dp0"
) else (
  powershell -NoProfile -Command "Expand-Archive -Path 'OMR-Demo.zip' -DestinationPath '.' -Force"
)

if not exist "OMR\OMR.exe" (
  echo [ERROR] Extraction incomplete.
  pause
  exit /b 1
)

echo.
echo Done. Now double-click:
echo   NEW 2 - Launch OMR (no black window).vbs
pause
