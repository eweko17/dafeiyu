# 恢復大肥魚的自動排程
$ErrorActionPreference = 'Stop'

$tasks = Get-ScheduledTask -TaskName 'DaFeiYu-*' -ErrorAction SilentlyContinue
if (-not $tasks) {
    Write-Host '找不到 DaFeiYu 排程，可能還沒安裝（見 scripts\install_tasks.ps1）。'
    exit 1
}

foreach ($t in $tasks) {
    Enable-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath | Out-Null
}

Write-Host '已恢復大肥魚排程。'
Get-ScheduledTask -TaskName 'DaFeiYu-*' | Select-Object TaskName, State | Format-Table -AutoSize
