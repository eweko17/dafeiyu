@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  Dafeiyu: exchange a short token for a 60-day long token
echo ============================================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\token_helper.py
) else (
  py scripts\token_helper.py
)
echo.
pause
