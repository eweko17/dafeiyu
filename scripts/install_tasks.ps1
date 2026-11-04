# 建立 Windows 工作排程：一天 3 篇 + 每 30 分鐘回覆 + 每週更新 token
# 使用方式：powershell -ExecutionPolicy Bypass -File .\scripts\install_tasks.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'

if (-not (Test-Path $pythonw)) {
    throw "找不到 $pythonw。請先執行 install.ps1。"
}

Write-Host "資料夾：$root"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

$slots = @('09:30', '14:30', '21:30')
for ($i = 0; $i -lt $slots.Count; $i++) {
    $number = $i + 1
    $name = "DaFeiYu-Post-$number"
    $action = New-ScheduledTaskAction `
        -Execute $pythonw `
        -Argument "-m app.cli post --slot $number" `
        -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Daily -At $slots[$i]
    Register-ScheduledTask `
        -TaskName $name `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "DaFeiYu daily post $number" `
        -Force | Out-Null
    Write-Host "已建立：$name（每天 $($slots[$i])）"
}

$replyName = 'DaFeiYu-Replies'
$replyAction = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "-m app.cli replies" `
    -WorkingDirectory $root
# 用「每天 09:00」當基底，再掛上重複間隔，排程才會每天都重複。
$replyTrigger = New-ScheduledTaskTrigger -Daily -At '09:00'
$replyTrigger.Repetition = (New-ScheduledTaskTrigger `
    -Once `
    -At '09:00' `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Hours 14)).Repetition
Register-ScheduledTask `
    -TaskName $replyName `
    -Action $replyAction `
    -Trigger $replyTrigger `
    -Settings $settings `
    -Description "DaFeiYu reply poller (09:00-23:00 every 30 min)" `
    -Force | Out-Null
Write-Host "已建立：$replyName（09:00-23:00，每 30 分鐘）"

$refreshName = 'DaFeiYu-RefreshToken'
$refreshAction = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "-m app.cli refresh-token" `
    -WorkingDirectory $root
$refreshTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '03:00'
Register-ScheduledTask `
    -TaskName $refreshName `
    -Action $refreshAction `
    -Trigger $refreshTrigger `
    -Settings $settings `
    -Description "DaFeiYu refresh Threads token weekly" `
    -Force | Out-Null
Write-Host "已建立：$refreshName（每週日 03:00）"

Write-Host ""
Write-Host "完成。查看排程：Get-ScheduledTask -TaskName 'DaFeiYu-*'"
Write-Host "移除排程：powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_tasks.ps1"
