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
    return (Split-Path -Parent $backendDir)
}

$repoRoot = Resolve-RepoRoot
$repo = (Get-Location).Path

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

$healthDir = Join-Path $repo "data\health"
New-Item -ItemType Directory -Force -Path $healthDir | Out-Null

$ps1Path = $MyInvocation.MyCommand.Path
$kagPath = Join-Path $repoRoot "backend\knowledge_v1\keyword_approval_gate.py"
$cycPath = Join-Path $repoRoot "backend\knowledge_v1\cycle.py"

Write-Host "=== SOURCE CONFIRM ===" -ForegroundColor Cyan
if (Test-Path -LiteralPath $ps1Path) { Write-Host ("PS1_SHA256=" + (Get-FileHash $ps1Path -Algorithm SHA256).Hash) }
if (Test-Path -LiteralPath $kagPath) { Write-Host ("KAG_SHA256=" + (Get-FileHash $kagPath -Algorithm SHA256).Hash) }
if (Test-Path -LiteralPath $cycPath) { Write-Host ("CYC_SHA256=" + (Get-FileHash $cycPath -Algorithm SHA256).Hash) }
Write-Host "=== SOURCE CONFIRM OK ===" -ForegroundColor Green

# parser-risk read-only scan/report: '$<name>:'
$scanStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$parserScanLog = Join-Path $healthDir ("parser_risk_scan_" + $scanStamp + ".log")
$rawNow = Get-Content -LiteralPath $ps1Path -Encoding UTF8 -Raw
$allRisk = [regex]::Matches($rawNow, '\$[A-Za-z_][A-Za-z0-9_]*:')
$riskCount = $allRisk.Count
if ($riskCount -eq 0) {
    Write-Host "PARSER_RISK_SCAN_PASS" -ForegroundColor Green
    "PARSER_RISK_SCAN_PASS" | Out-File -FilePath $parserScanLog -Encoding utf8
} else {
    Write-Host ("PARSER_RISK_SCAN_FOUND=" + $riskCount) -ForegroundColor Yellow
    ("PARSER_RISK_SCAN_FOUND=" + $riskCount) | Out-File -FilePath $parserScanLog -Encoding utf8
    $scanLines = Get-Content -LiteralPath $ps1Path -Encoding UTF8
    for ($i = 0; $i -lt $scanLines.Count; $i++) {
        $line = $scanLines[$i]
        if ($line -match '\$[A-Za-z_][A-Za-z0-9_]*:') {
            $entry = ("L" + ($i + 1) + ": " + $line.Trim())
            Write-Host $entry -ForegroundColor DarkYellow
            $entry | Out-File -FilePath $parserScanLog -Encoding utf8 -Append
        }
    }
}

Write-Host "=== STEP E: Knowledge Ingest ==="

$snapBase = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots"
$latest = Get-ChildItem -LiteralPath $snapBase -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) { throw ("E1_CONTRACT_FAIL: " + $snapBase) }

$cycleId = $latest.Name
if ([string]::IsNullOrWhiteSpace($cycleId)) { throw "E1_CONTRACT_FAIL: cycle_id_empty" }

$lastCycleIdFile1 = Join-Path $snapBase "last_cycle_id.txt"
$lastCycleIdFile2 = Join-Path $repoRoot "data\last_cycle_id.txt"
[System.IO.File]::WriteAllText($lastCycleIdFile1, $cycleId.Trim(), [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($lastCycleIdFile2, $cycleId.Trim(), [System.Text.Encoding]::UTF8)

Write-Host ("CYCLE_ID=" + $cycleId)
$env:V7_CYCLE_ID = $cycleId
$ts = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host ""
Write-Host "[E1] Keyword Approval Gate" -ForegroundColor Cyan
$e1OutPath = Join-Path $healthDir ("net_out_E1_keyword_approve_" + $ts + ".log")
$e1ErrPath = Join-Path $healthDir ("net_err_E1_keyword_approve_" + $ts + ".log")
$e1Lines = & python -X utf8 -m backend.cli.run knowledge keyword-approve --cycle-id $cycleId 2>&1 | Tee-Object -FilePath $e1OutPath
$e1Code = $LASTEXITCODE
$e1Lines | ForEach-Object { Write-Host $_ }
if ($e1Code -ne 0) {
    $e1Lines | Out-File -FilePath $e1ErrPath -Encoding utf8
    throw ("STEP E1 FAILED (exit code=" + $e1Code + "). See: " + $e1ErrPath)
}

Write-Host ""
Write-Host "[E1] Verifying E1 outputs (filesystem contract)" -ForegroundColor Cyan
$approvalApprovedDir = Join-Path $repoRoot "data\knowledge_v1_store\keyword_approval\approved"
$inputsKeywordsDir = Join-Path $repoRoot "data\knowledge_v1_store\inputs\keywords"

if (-not (Test-Path -LiteralPath $approvalApprovedDir)) { throw ("E1_CONTRACT_FAIL: " + $approvalApprovedDir) }
if (-not (Test-Path -LiteralPath $inputsKeywordsDir)) { throw ("E1_CONTRACT_FAIL: " + $inputsKeywordsDir) }

$approvedCount = @(Get-ChildItem -LiteralPath $approvalApprovedDir -File -ErrorAction SilentlyContinue).Count
Write-Host ("approval_approved_files=" + $approvedCount) -ForegroundColor DarkGray

$requiredCats = @("science", "history", "common_sense", "economy", "geography", "papers")
$totalApprovedLines = 0
$totalInputLines = 0
foreach ($cat in $requiredCats) {
    $approvedTxt = Join-Path $approvalApprovedDir ($cat + ".txt")
    $kwPath = Join-Path $inputsKeywordsDir ($cat + ".txt")
    if (-not (Test-Path -LiteralPath $approvedTxt)) { throw ("E1_CONTRACT_FAIL: " + $approvedTxt) }
    if (-not (Test-Path -LiteralPath $kwPath)) { throw ("E1_CONTRACT_FAIL: " + $kwPath) }

    $approvedLines = (Get-Content -LiteralPath $approvedTxt -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" -and -not $_.Trim().StartsWith("#") } | Measure-Object -Line).Lines
    $inputLines = (Get-Content -LiteralPath $kwPath -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" -and -not $_.Trim().StartsWith("#") } | Measure-Object -Line).Lines
    if ($approvedLines -lt 1) { throw ("E1_CONTRACT_FAIL: " + $approvedTxt) }
    if ($inputLines -lt 1) { throw ("E1_CONTRACT_FAIL: " + $kwPath) }
    $totalApprovedLines += $approvedLines
    $totalInputLines += $inputLines
    Write-Host ("cat=" + $cat + " approved_lines=" + $approvedLines + " input_lines=" + $inputLines) -ForegroundColor DarkGray
}
Write-Host ("E1_TOTAL_APPROVED_LINES=" + $totalApprovedLines) -ForegroundColor DarkGray
Write-Host ("E1_TOTAL_INPUT_LINES=" + $totalInputLines) -ForegroundColor DarkGray
Write-Host "[E1] CONTRACT PASS" -ForegroundColor Green

Write-Host ""
Write-Host "[E2] Cycle Ingest" -ForegroundColor Cyan
$e2OutPath = Join-Path $healthDir ("net_out_E2_cycle_ingest_" + $ts + ".log")
$e2ErrPath = Join-Path $healthDir ("net_err_E2_cycle_ingest_" + $ts + ".log")
$e2TbPath = Join-Path $healthDir ("net_tb_E2_cycle_ingest_" + $ts + ".log")
New-Item -ItemType File -Force -Path $e2OutPath | Out-Null
New-Item -ItemType File -Force -Path $e2ErrPath | Out-Null
New-Item -ItemType File -Force -Path $e2TbPath | Out-Null

$env:V7_TRACEBACK_FILE = $e2TbPath
$python = (Get-Command python -ErrorAction Stop).Source
$argsE2 = @(
    "-u",
    "-X", "utf8",
    "-m", "backend.cli.run",
    "knowledge", "cycle",
    "--mode", "run",
    "--cycle-id", $cycleId,
    "--approve-fallback"
)

("PY_EXE=" + $python) | Out-File -FilePath $e2OutPath -Encoding utf8 -Append
("ARGS=" + ($argsE2 -join " ")) | Out-File -FilePath $e2OutPath -Encoding utf8 -Append
("START_UTC=" + (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")) | Out-File -FilePath $e2OutPath -Encoding utf8 -Append

Write-Host "[E2] Starting Python process..." -ForegroundColor Cyan
$p = Start-Process -FilePath $python -ArgumentList $argsE2 -WorkingDirectory $repoRoot -RedirectStandardOutput $e2OutPath -RedirectStandardError $e2ErrPath -PassThru -NoNewWindow
Write-Host ("PY_PID=" + $p.Id)

$assetsPath = Join-Path $repoRoot "data\knowledge_v1_store\discovery\raw\assets.jsonl"
$chunksPath = Join-Path $repoRoot "data\knowledge_v1_store\discovery\derived\chunks.jsonl"
$timeoutMin = 60
if ($env:V7_E2_TIMEOUT_MIN) {
    try { $timeoutMin = [int]$env:V7_E2_TIMEOUT_MIN } catch { $timeoutMin = 60 }
}
$timeoutSec = $timeoutMin * 60
$start = Get-Date
$prevOut = if (Test-Path -LiteralPath $e2OutPath) { (Get-Item -LiteralPath $e2OutPath).Length } else { 0 }
$prevErr = if (Test-Path -LiteralPath $e2ErrPath) { (Get-Item -LiteralPath $e2ErrPath).Length } else { 0 }
$prevAssets = if (Test-Path -LiteralPath $assetsPath) { (Get-Item -LiteralPath $assetsPath).Length } else { 0 }
$prevChunks = if (Test-Path -LiteralPath $chunksPath) { (Get-Item -LiteralPath $chunksPath).Length } else { 0 }
$timedOut = $false

$hb0 = ("[HB] elapsed_sec=0 proc_alive=" + (-not $p.HasExited) + " out_len=" + $prevOut + " out_delta=0 err_len=" + $prevErr + " err_delta=0 assets_len=" + $prevAssets + " assets_delta=0 chunks_len=" + $prevChunks + " chunks_delta=0 pid=" + $p.Id)
Write-Host $hb0 -ForegroundColor DarkGray
$hb0 | Out-File -FilePath $e2OutPath -Encoding utf8 -Append

while (-not $p.HasExited) {
    Start-Sleep -Seconds 15
    $elapsed = [int]((Get-Date) - $start).TotalSeconds
    $outLen = if (Test-Path -LiteralPath $e2OutPath) { (Get-Item -LiteralPath $e2OutPath).Length } else { 0 }
    $errLen = if (Test-Path -LiteralPath $e2ErrPath) { (Get-Item -LiteralPath $e2ErrPath).Length } else { 0 }
    $assetsLen = if (Test-Path -LiteralPath $assetsPath) { (Get-Item -LiteralPath $assetsPath).Length } else { 0 }
    $chunksLen = if (Test-Path -LiteralPath $chunksPath) { (Get-Item -LiteralPath $chunksPath).Length } else { 0 }

    $outDelta = $outLen - $prevOut
    $errDelta = $errLen - $prevErr
    $assetsDelta = $assetsLen - $prevAssets
    $chunksDelta = $chunksLen - $prevChunks

    $hb = ("[HB] elapsed_sec=" + $elapsed + " proc_alive=" + (-not $p.HasExited) + " out_len=" + $outLen + " out_delta=" + $outDelta + " err_len=" + $errLen + " err_delta=" + $errDelta + " assets_len=" + $assetsLen + " assets_delta=" + $assetsDelta + " chunks_len=" + $chunksLen + " chunks_delta=" + $chunksDelta + " pid=" + $p.Id)
    Write-Host $hb -ForegroundColor DarkGray
    $hb | Out-File -FilePath $e2OutPath -Encoding utf8 -Append

    $prevOut = $outLen
    $prevErr = $errLen
    $prevAssets = $assetsLen
    $prevChunks = $chunksLen

    if ($elapsed -ge $timeoutSec) {
        $timedOut = $true
        try { $p.Kill() } catch {}
        break
    }
}

if (-not $p.HasExited) { $null = $p.WaitForExit(15000) }
$code3 = if ($p.HasExited) { $p.ExitCode } else { -1 }

Write-Host ("E2_OUT=" + $e2OutPath)
Write-Host ("E2_ERR=" + $e2ErrPath)
Write-Host ("E2_TB=" + $e2TbPath)
Write-Host ("E2 EXITCODE=" + $code3)

if ($timedOut -or $code3 -ne 0) {
    Write-Host "--- E2 ERR tail ---" -ForegroundColor Yellow
    if (Test-Path -LiteralPath $e2ErrPath) { Get-Content -LiteralPath $e2ErrPath -Encoding UTF8 -Tail 120 -ErrorAction SilentlyContinue }
    Write-Host "--- E2 TB tail ---" -ForegroundColor Yellow
    if (Test-Path -LiteralPath $e2TbPath) { Get-Content -LiteralPath $e2TbPath -Encoding UTF8 -Tail 120 -ErrorAction SilentlyContinue }
    throw ("STEP E2 FAILED (exit code=" + $code3 + "). See: " + $e2ErrPath + " / " + $e2TbPath)
}

Write-Host "[E2] STEP E2 SUCCESS" -ForegroundColor Green

Write-Host ""
Write-Host "[E3] Verify Ingestion Stats" -ForegroundColor Cyan
$e3OutPath = Join-Path $healthDir ("net_out_E3_verify_stats_" + $ts + ".log")
$e3ErrPath = Join-Path $healthDir ("net_err_E3_verify_stats_" + $ts + ".log")
$e3Lines = & python -X utf8 -m backend.scripts.verify_v7_ingestion_stats 2>&1 | Tee-Object -FilePath $e3OutPath
$e3Code = $LASTEXITCODE
$e3Lines | ForEach-Object { Write-Host $_ }
if ($e3Code -ne 0) {
    $e3Lines | Out-File -FilePath $e3ErrPath -Encoding utf8
    throw ("STEP E3 FAILED (exit code=" + $e3Code + "). See: " + $e3ErrPath)
}

Write-Host "=== STEP E PASS ===" -ForegroundColor Green
exit 0

