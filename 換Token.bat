@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  大肥魚：把短效 token 換成 60 天長效 token
echo ============================================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\token_helper.py
) else (
  py scripts\token_helper.py
)
echo.
pause
