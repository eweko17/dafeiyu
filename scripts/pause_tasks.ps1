# 暫停大肥魚的自動排程（不會再自動發文、回覆、更新 token）
$ErrorActionPreference = 'Stop'

$tasks = Get-ScheduledTask -TaskName 'DaFeiYu-*' -ErrorAction SilentlyContinue
if (-not $tasks) {
    Write-Host '找不到 DaFeiYu 排程，可能還沒安裝（見 scripts\install_tasks.ps1）。'
    exit 1
}

foreach ($t in $tasks) {
    Disable-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath | Out-Null
}

Write-Host '已暫停大肥魚排程。恢復請執行 scripts\resume_tasks.ps1。'
Get-ScheduledTask -TaskName 'DaFeiYu-*' | Select-Object TaskName, State | Format-Table -AutoSize
