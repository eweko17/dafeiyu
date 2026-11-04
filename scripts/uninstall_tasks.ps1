# 移除大肥魚的 Windows 工作排程
# 使用方式：powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_tasks.ps1

$names = @(
    'DaFeiYu-Post-1',
    'DaFeiYu-Post-2',
    'DaFeiYu-Post-3',
    'DaFeiYu-Replies',
    'DaFeiYu-RefreshToken'
)

foreach ($name in $names) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "已移除：$name"
    } else {
        Write-Host "不存在：$name"
    }
}
