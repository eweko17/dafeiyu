# 建立 Windows 工作排程：每 10 分鐘跑一次 auto（發文時間由程式隨機決定）+ 每週更新 token
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

# 舊版是「固定 3 個時間各建一個工作」，先清掉避免重複發文。
foreach ($old in @('DaFeiYu-Post-1', 'DaFeiYu-Post-2', 'DaFeiYu-Post-3', 'DaFeiYu-Post-4', 'DaFeiYu-Post-5', 'DaFeiYu-Replies')) {
    if (Get-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $old -Confirm:$false
        Write-Host "已移除舊工作：$old"
    }
}

# 一天 5 篇（時間隨機）＋回覆留言，都交給 auto 判斷，所以只需要一個每 10 分鐘的工作。
$autoName = 'DaFeiYu-Auto'
$autoAction = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "-m app.cli auto" `
    -WorkingDirectory $root
$autoTrigger = New-ScheduledTaskTrigger -Once -At '08:00'
$autoTrigger.Repetition = (New-ScheduledTaskTrigger `
    -Once `
    -At '08:00' `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Hours 15)).Repetition
Register-ScheduledTask `
    -TaskName $autoName `
    -Action $autoAction `
    -Trigger $autoTrigger `
    -Settings $settings `
    -Description "DaFeiYu auto (08:00-23:00 every 10 min; 5 random posts/day)" `
    -Force | Out-Null
Write-Host "已建立：$autoName（08:00-23:00，每 10 分鐘；一天 5 篇，時間隨機）"

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
