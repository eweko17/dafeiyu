@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  大肥魚：把 60 天 token 自動上傳到 GitHub Secrets
echo ============================================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\push_token.py
) else (
  py scripts\push_token.py
)
echo.
pause
