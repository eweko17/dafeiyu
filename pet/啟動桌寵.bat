@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "EXE="
for /r "%~dp0" %%f in (dsh-pet.exe) do (
  if exist "%%f" set "EXE=%%f"
)

if not defined EXE (
  echo 找不到 dsh-pet.exe。
  echo 請確認 pet\dsh-pet-win-x64 已經解壓縮。
  echo.
  pause
  exit /b 1
)

rem 順便啟動記憶同步（每 60 秒跟手機對一次）；沒設定同步會自動略過
if exist "%~dp0..\同步記憶.bat" (
  start "大肥魚記憶同步" /min "%~dp0..\同步記憶.bat" --watch
)

echo 正在啟動桌寵：%EXE%
start "" "%EXE%"
exit /b 0
