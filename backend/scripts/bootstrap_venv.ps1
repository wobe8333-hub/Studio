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
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..") | Select-Object -ExpandProperty Path
Set-Location $projectRoot

Write-Host "[BOOTSTRAP] Project root: $projectRoot"

if (-not (Test-Path (Join-Path $projectRoot "backend"))) {
    Write-Host "[BOOTSTRAP][FAIL] backend folder not found. Run from repo root."
    exit 2
}

# Ensure venv (.venv) exists
$venvDir = Join-Path $projectRoot ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "[BOOTSTRAP] .venv not found. Creating..."
    $created = $false
    try {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -3.11 -m venv $venvDir
            $created = $true
        }
    } catch { }
    if (-not $created) {
        try {
            if (Get-Command python -ErrorAction SilentlyContinue) {
                python -m venv $venvDir
                $created = $true
            }
        } catch { }
    }
    if (-not $created) {
        Write-Host "[BOOTSTRAP][FAIL] Unable to create venv (.venv). 'py' or 'python' not found."
        exit 30
    }
}

$venvPyPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPyPath)) {
    Write-Host "[BOOTSTRAP][FAIL] venv python missing: $venvPyPath"
    exit 31
}

Write-Host "[BOOTSTRAP] Using venv python: $venvPyPath"

# Upgrade pip
& $venvPyPath -m pip install --upgrade pip

# Hard-locked dependencies from requirements.lock.txt
$lockPath = Join-Path $projectRoot "requirements.lock.txt"
if (-not (Test-Path $lockPath)) {
    Write-Host "[BOOTSTRAP][FAIL] requirements.lock.txt missing at $lockPath"
    exit 51
}

try {
    & $venvPyPath -m pip install -r $lockPath
} catch {
    Write-Host "[BOOTSTRAP][FAIL] pip install -r requirements.lock.txt failed: $_"
    exit 33
}

# Import smoke test (external + backend CLI)
Write-Host "[BOOTSTRAP] Running import smoke test..."
try {
    & $venvPyPath -c "import requests; import feedparser; import backend.cli.run"
} catch {
    Write-Host "[BOOTSTRAP][FAIL] import smoke failed: $_"
    exit 34
}

Write-Host "[BOOTSTRAP] OK (.venv ready and imports succeeded)"
exit 0

