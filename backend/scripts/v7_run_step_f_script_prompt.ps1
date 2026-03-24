$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $root = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($root)) {
        if ($MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) {
            $root = Split-Path -Parent $MyInvocation.MyCommand.Path
        }
    }
    if ([string]::IsNullOrWhiteSpace($root)) { $root = (Get-Location).Path }

    $scriptsDir = (Resolve-Path -LiteralPath $root).Path
    $backendDir = Split-Path -Parent $scriptsDir
    $repoRoot = Split-Path -Parent $backendDir
    return $repoRoot
}

$repoRoot = Resolve-RepoRoot

# base dir 생성 보장 (중복 방어)
$scriptPromptsBase = Join-Path $repoRoot "data\knowledge_v1_store\script_prompts"
New-Item -ItemType Directory -Force -Path $scriptPromptsBase | Out-Null
if (!(Test-Path -LiteralPath $scriptPromptsBase)) {
    Write-Host ("FATAL: Failed to create script_prompts base directory: " + $scriptPromptsBase) -ForegroundColor Red
    exit 1
}

# SSL_CERT_FILE 주입 (환경 일관성)
$env:SSL_CERT_FILE = (& python -X utf8 -c "import certifi; print(certifi.where())")
Write-Host ("SSL_CERT_FILE=" + $env:SSL_CERT_FILE)

# UTF-8 강제
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== STEP F: Script Prompt Generation ==="

# cycle_id SSOT: 최신 snapshot 디렉토리 기반 (LastWriteTime 기준)
$snapBase = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots"
$latest = Get-ChildItem $snapBase -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latest) {
    Write-Host ("FATAL: No snapshot directories found in: " + $snapBase) -ForegroundColor Red
    exit 1
}

$cycleId = $latest.Name
if ([string]::IsNullOrWhiteSpace($cycleId)) {
    Write-Host "FATAL: Latest snapshot directory name is empty" -ForegroundColor Red
    exit 1
}

# 포인터 파일 2개 동기화 (UTF-8)
$lastCycleIdFile1 = Join-Path $snapBase "last_cycle_id.txt"
$lastCycleIdFile2 = Join-Path $repoRoot "data\last_cycle_id.txt"
[System.IO.File]::WriteAllText($lastCycleIdFile1, $cycleId.Trim(), [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($lastCycleIdFile2, $cycleId.Trim(), [System.Text.Encoding]::UTF8)

Write-Host ("CYCLE_ID=" + $cycleId)
$env:V7_CYCLE_ID = $cycleId

# script-prompt 실행 (cycle_id 전달)
$ErrorActionPreference = "Continue"
$lines = & python -X utf8 -m backend.cli.run knowledge script-prompt --cycle-id $cycleId 2>&1
$code = $LASTEXITCODE
$ErrorActionPreference = "Stop"

$lines | ForEach-Object { Write-Host $_ }

if ($code -ne 0) {
    Write-Host ("FATAL: STEP F script-prompt failed (exit=" + $code + ")") -ForegroundColor Red
    exit 1
}

Write-Host "=== STEP F PASS ==="
exit 0

