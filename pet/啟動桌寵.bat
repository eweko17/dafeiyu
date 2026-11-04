@echo off
chcp 950 >nul
setlocal
cd /d "%~dp0"

set "EXE="
for /r "%~dp0" %%f in (dsh-pet.exe) do (
  if exist "%%f" set "EXE=%%f"
)

if not defined EXE (
  echo 找不到 dsh-pet.exe。
  echo 請確認 pet\dsh-pet-win-x64 已經解壓縮完成。
  echo.
  pause
  exit /b 1
)

echo 正在啟動桌寵：%EXE%
start "" "%EXE%"
exit /b 0
