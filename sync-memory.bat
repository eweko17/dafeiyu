@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

echo ============================================================
echo  Dafeiyu: memory sync (phone and PC)
echo ============================================================
echo.
echo   no option  = sync once
echo   --watch    = keep running, sync every 60 seconds
echo   --status   = show current settings
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\memory_sync.py %*
) else (
  py scripts\memory_sync.py %*
)

if errorlevel 1 (
  if /i not "%~1"=="--watch" pause
)
