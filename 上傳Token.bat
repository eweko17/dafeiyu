@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  Dafeiyu: upload a 60-day token to GitHub Secrets
echo ============================================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\push_token.py
) else (
  py scripts\push_token.py
)
echo.
pause
