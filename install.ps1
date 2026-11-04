# 大肥魚 - 一鍵安裝（Windows）
# 使用方式：在這個資料夾上按右鍵 →「在終端機中開啟」→ 執行：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# 這個腳本只會：建立 .venv、安裝 Python 套件、複製設定檔、建立排程。
# 不會修改系統設定，也不會要求管理員權限。

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "=== 大肥魚安裝開始 ===" -ForegroundColor Cyan
Write-Host "資料夾：$root"
Write-Host ""

# 1. Python
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    throw "找不到 Python。請先安裝 Python 3.10 以上（安裝時記得勾 Add to PATH）。"
}
Write-Host "[1/5] Python 版本：$(& py --version 2>&1)"

# 2. 虛擬環境
$venv = Join-Path $root '.venv'
if (-not (Test-Path $venv)) {
    Write-Host "[2/5] 建立虛擬環境 .venv ..."
    & py -3 -m venv $venv
} else {
    Write-Host "[2/5] 虛擬環境已存在，跳過。"
}

$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "虛擬環境建立失敗：找不到 $python"
}

# 3. 套件
Write-Host "[3/5] 安裝 Python 套件 ..."
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r (Join-Path $root 'requirements.txt')

# 4. 設定檔
$config = Join-Path $root 'config.json'
$example = Join-Path $root 'config.example.json'
if (-not (Test-Path $config)) {
    Copy-Item $example $config
    Write-Host "[4/5] 已建立 config.json"
} else {
    Write-Host "[4/5] config.json 已存在，保留原設定。"
}

# 5. Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
$configPath = Join-Path $root 'config.json'
$model = 'qwen2.5:3b-instruct'
if (Test-Path $configPath) {
    try {
        $parsed = Get-Content $configPath -Raw | ConvertFrom-Json
        if ($parsed.brain.ollama.model) { $model = $parsed.brain.ollama.model }
    } catch {
        Write-Host "讀取 config.json 失敗，使用預設模型 $model" -ForegroundColor Yellow
    }
}
if ($ollama) {
    Write-Host "[5/5] 檢查本機模型 $model（第一次會下載約 2–5 GB）..."
    & ollama pull $model
} else {
    Write-Host "[5/5] 警告：找不到 ollama 指令。" -ForegroundColor Yellow
    Write-Host "      請先安裝 Ollama：https://ollama.com/download/windows"
    Write-Host "      安裝後執行：ollama pull $model"
}

Write-Host ""
Write-Host "=== 安裝完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "接下來依序執行："
Write-Host "  1. .\大肥魚.bat setup          （貼上 Threads token）"
Write-Host "  2. .\大肥魚.bat doctor         （健康檢查）"
Write-Host "  3. .\大肥魚.bat post --dry-run （預覽一篇，不會發出去）"
Write-Host "  4. powershell -ExecutionPolicy Bypass -File .\scripts\install_tasks.ps1"
Write-Host ""
Write-Host "完整說明：docs\設定步驟.md"
