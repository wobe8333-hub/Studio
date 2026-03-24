$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
trap {
    Write-Host "[FATAL] $($_.Exception.Message)"
    Write-Host "[FATAL][POSITION] $($_.InvocationInfo.PositionMessage)"
    Write-Host "[FATAL][STACK] $($_.ScriptStackTrace)"
    exit 99
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
Set-Location $projectRoot

Write-Host "[RUN_VERIFY] Project root: $projectRoot"

if (-not (Test-Path (Join-Path $projectRoot "backend"))) {
    Write-Host "[RUN_VERIFY][FAIL] backend folder not found. Run from repo root."
    exit 2
}

$ssotPath = Join-Path $projectRoot "data\knowledge_v1_store"
if (-not (Test-Path $ssotPath)) {
    Write-Host "[SSOT][FAIL] missing data\knowledge_v1_store"
    exit 10
}

# 1) Bootstrap venv
$bootstrap = Join-Path $projectRoot "backend\scripts\bootstrap_venv.ps1"
Write-Host "[RUN_VERIFY] Bootstrapping venv via $bootstrap"
& powershell -ExecutionPolicy Bypass -File $bootstrap
$bootExit = $LASTEXITCODE
if ($bootExit -ne 0) {
    Write-Host "[RUN_VERIFY][FAIL] bootstrap_venv.ps1 failed with exit $bootExit"
    exit 40
}

# 2) Run V7 REAL in OPS mode
$env:AAS_VERIFY_MODE = "OPS"
$verify = Join-Path $projectRoot "backend\scripts\v7_verify_real.ps1"
Write-Host "[RUN_VERIFY] Running v7_verify_real.ps1 (OPS) via $verify"
& powershell -ExecutionPolicy Bypass -File $verify
$exitCode = $LASTEXITCODE
Write-Host "[RUN_VERIFY] v7_verify_real.ps1 exit code: $exitCode"
exit $exitCode

