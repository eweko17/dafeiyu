@echo off
chcp 950 >nul
setlocal
taskkill /IM dsh-pet.exe /F >nul 2>&1
if errorlevel 1 (
  echo 桌寵本來就沒有在執行。
) else (
  echo 桌寵已關閉。
)
ping -n 2 127.0.0.1 >nul
exit /b 0
