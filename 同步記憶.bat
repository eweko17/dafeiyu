@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

echo ============================================================
echo  大肥魚：記憶同步（手機 ^<-> 電腦）
echo ============================================================
echo.
echo  直接執行      = 同步一次
echo  加上 --watch  = 常駐，每 60 秒同步一次
echo  加上 --status = 看目前設定
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\memory_sync.py %*
) else (
  py scripts\memory_sync.py %*
)

if errorlevel 1 pause
