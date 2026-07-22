@echo off
setlocal enableextensions
cd /d "%~dp0"

if not exist "OMR-Demo.zip.sha256" (
  echo [ERROR] Checksum file missing.
  pause
  exit /b 1
)

echo Verifying OMR-Demo.zip integrity...
for /f "tokens=1" %%H in (OMR-Demo.zip.sha256) do set "EXPECTED=%%H"

powershell -NoProfile -Command ^
  "$h = (Get-FileHash -Algorithm SHA256 'OMR-Demo.zip').Hash.ToLower(); ^
   if ($h -eq '%EXPECTED%'.ToLower()) { Write-Host 'PASS - zip is intact'; exit 0 } ^
   else { Write-Host 'FAIL - zip may be corrupted. Re-copy from the original USB.'; Write-Host \"Expected: %EXPECTED%\"; Write-Host \"Got:      $h\"; exit 1 }"

if errorlevel 1 pause
exit /b %errorlevel%
