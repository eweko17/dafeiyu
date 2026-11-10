@echo off
chcp 65001 >nul
setlocal
taskkill /IM dsh-pet.exe /F >nul 2>&1
if errorlevel 1 (
  echo Desktop pet is not running.
) else (
  echo Desktop pet closed.
)
ping -n 2 127.0.0.1 >nul
exit /b 0
