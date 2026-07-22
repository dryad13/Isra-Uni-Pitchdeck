@echo off
REM ============================================================
REM  Nightly backup of the OMR SQLite database.
REM  Copies data\omr.db to data\backups\omr_YYYYMMDD_HHMMSS.db
REM  and prunes backups older than RETENTION_DAYS.
REM
REM  Schedule via Task Scheduler (see docs/deployment.md):
REM    schtasks /create /tn "OMR DB Backup" /tr "C:\path\to\scripts\backup_db.bat" /sc daily /st 23:30
REM ============================================================
setlocal enableextensions
cd /d "%~dp0.."

set "RETENTION_DAYS=30"
set "DB=data\omr.db"
set "BACKUP_DIR=data\backups"

if not exist "%DB%" (
  echo [ERROR] Database not found at %DB%.
  exit /b 1
)
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Use PowerShell for a reliable, locale-independent timestamp and pruning.
powershell -NoProfile -Command "$ts = Get-Date -Format 'yyyyMMdd_HHmmss'; $dest = Join-Path '%BACKUP_DIR%' ('omr_' + $ts + '.db'); Copy-Item -Path '%DB%' -Destination $dest -Force; Write-Host ('Backup created: ' + $dest); Get-ChildItem -Path '%BACKUP_DIR%' -Filter 'omr_*.db' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-%RETENTION_DAYS%) } | Remove-Item -Force"

endlocal
