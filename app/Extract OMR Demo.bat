@echo off
setlocal enableextensions
cd /d "%~dp0"

if exist "OMR\OMR.exe" (
  echo Already extracted.
  pause
  exit /b 0
)

if not exist "OMR-Demo.zip" (
  echo [ERROR] OMR-Demo.zip not found.
  pause
  exit /b 1
)

echo Step 1/2 - Verifying zip...
if exist "OMR-Demo.zip.sha256" (
  for /f "tokens=1" %%H in (OMR-Demo.zip.sha256) do set "EXPECTED=%%H"
  powershell -NoProfile -Command "$h=(Get-FileHash -Algorithm SHA256 'OMR-Demo.zip').Hash.ToLower(); if($h -ne '%EXPECTED%'.ToLower()){Write-Host 'FAIL - zip corrupted. Re-copy from USB.'; exit 1}; Write-Host 'Checksum OK'"
  if errorlevel 1 ( pause & exit /b 1 )
) else (
  echo [WARN] No checksum file - skipping verify.
)

echo Step 2/2 - Extracting (1-3 minutes on older PCs)...
where tar >nul 2>&1
if not errorlevel 1 (
  tar -xf "OMR-Demo.zip" -C "%~dp0"
) else (
  powershell -NoProfile -Command "Expand-Archive -Path 'OMR-Demo.zip' -DestinationPath '.' -Force"
)

if errorlevel 1 (
  echo [ERROR] Extraction failed.
  pause
  exit /b 1
)

if not exist "OMR\OMR.exe" (
  echo [ERROR] Extraction incomplete - OMR.exe missing.
  pause
  exit /b 1
)

echo.
echo Extract complete. Next: double-click "Start OMR.bat"
pause
