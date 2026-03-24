$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

try {
    $cert = (& python -X utf8 -c "import certifi; print(certifi.where())" 2>$null).Trim()
    if ($cert) {
        $env:SSL_CERT_FILE = $cert
        Write-Host ("SSL_CERT_FILE=" + $env:SSL_CERT_FILE) -ForegroundColor DarkGray
    }
} catch {}

Write-Host "=== STEP D: YouTube Data API Trend Anchor (low quota) ==="

$repo = (Get-Location).Path
$healthDir = Join-Path $repo "data\health"
New-Item -ItemType Directory -Force -Path $healthDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outPath = Join-Path $healthDir ("net_out_D1_data_api_anchor_" + $ts + ".log")
$errPath = Join-Path $healthDir ("net_err_D1_data_api_anchor_" + $ts + ".log")

$probeOut = & python -X utf8 -c "print('STEP_D_OK')" 2>&1
$probeOut | Tee-Object -FilePath $outPath | ForEach-Object { Write-Host $_ }
$code = $LASTEXITCODE

if ($code -ne 0) {
    $probeOut | Out-File -FilePath $errPath -Encoding utf8
    exit 1
}

exit 0

