@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "EXE="
for /r "%~dp0" %%f in (dsh-pet.exe) do (
  if exist "%%f" set "EXE=%%f"
)

if not defined EXE (
  echo Cannot find dsh-pet.exe.
  echo Please make sure pet\dsh-pet-win-x64 is extracted.
  echo.
  pause
  exit /b 1
)

tasklist /FI "IMAGENAME eq dsh-pet.exe" 2>nul | find /I "dsh-pet.exe" >nul
if not errorlevel 1 (
  echo Desktop pet is already running.
  echo If you cannot see it, close it first, then start again.
  timeout /t 3 >nul
  exit /b 0
)

echo Starting desktop pet...
start "" "%EXE%"

rem Start memory sync in the background. Optional: skipped if the file is absent.
if exist "%~dp0..\sync-memory.bat" (
  start "Dafeiyu Sync" /min "%~dp0..\sync-memory.bat" --watch
)

exit /b 0
