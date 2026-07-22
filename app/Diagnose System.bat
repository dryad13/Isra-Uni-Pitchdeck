@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"
set "LOG=%~dp0diagnose.log"

echo OMR Demo - System Diagnosis > "%LOG%"
echo ============================= >> "%LOG%"
echo Date: %date% %time% >> "%LOG%"
echo. >> "%LOG%"

echo Checking this PC... (results also saved to diagnose.log)
echo.

echo --- Windows --- >> "%LOG%"
ver >> "%LOG%" 2>&1
for /f "tokens=*" %%v in ('ver') do echo Windows: %%v

echo. >> "%LOG%"
echo --- Architecture --- >> "%LOG%"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
  echo CPU/OS: 64-bit >> "%LOG%"
  echo CPU/OS: 64-bit
) else (
  echo CPU/OS: %PROCESSOR_ARCHITECTURE% >> "%LOG%"
  echo CPU/OS: %PROCESSOR_ARCHITECTURE%  *** 64-bit Windows required ***
)

echo. >> "%LOG%"
echo --- Memory --- >> "%LOG%"
for /f "skip=1" %%m in ('wmic computersystem get TotalPhysicalMemory 2^>nul') do (
  if not "%%m"=="" (
    set /a RAMMB=%%m/1024/1024
    echo RAM: !RAMMB! MB >> "%LOG%"
    echo RAM: !RAMMB! MB
  )
)

echo. >> "%LOG%"
echo --- Files --- >> "%LOG%"
if exist "OMR\OMR.exe" (
  echo OMR.exe: found >> "%LOG%"
  echo OMR.exe: found
) else (
  echo OMR.exe: MISSING - run Extract OMR Demo.bat first >> "%LOG%"
  echo OMR.exe: MISSING - run Extract OMR Demo.bat first
)

if exist "OMR\data\omr.db" (
  echo omr.db: found >> "%LOG%"
) else (
  echo omr.db: missing >> "%LOG%"
)

echo. >> "%LOG%"
echo --- Visual C++ runtime --- >> "%LOG%"
if exist "%SystemRoot%\System32\vcruntime140.dll" (
  echo vcruntime140.dll: found >> "%LOG%"
  echo VC++ runtime: found
) else (
  echo vcruntime140.dll: MISSING >> "%LOG%"
  echo VC++ runtime: MISSING - run Install VC++ Runtime.bat once
)

echo. >> "%LOG%"
echo --- Quick launch test (15 sec) --- >> "%LOG%"
if not exist "OMR\OMR.exe" goto :done

cd OMR
start /b "" OMR.exe >> "%LOG%" 2>&1
timeout /t 15 /nobreak >nul
powershell -NoProfile -Command "try { (Invoke-WebRequest 'http://127.0.0.1:8080/api/health' -UseBasicParsing -TimeoutSec 5).StatusCode } catch { $_.Exception.Message }" >> "%LOG%" 2>&1
taskkill /f /im OMR.exe >nul 2>&1
cd ..

:done
echo.
echo Done. Open diagnose.log for full details.
echo.
echo Minimum required:
echo   - Windows 10 64-bit (Windows 7/8 will NOT work)
echo   - 8 GB RAM
echo   - Visual C++ 2015-2022 x64 runtime
echo.
pause
