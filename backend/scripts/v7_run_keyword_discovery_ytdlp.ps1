$ErrorActionPreference = "Stop"

# REPO_ROOT 계산 (스크립트 위치 기반)
$scriptRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($scriptRoot) -and $MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) {
  $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($scriptRoot)) { $scriptRoot = (Get-Location).Path }
$backendDir = Split-Path -Parent $scriptRoot
$repoRoot = Split-Path -Parent $backendDir

# 실키 흔적 삭제: .env / backend/credentials/youtube_api_key.txt / Youtube_API_key.txt
$filesToDelete = @(
  (Join-Path $repoRoot ".env"),
  (Join-Path $repoRoot "backend\credentials\youtube_api_key.txt"),
  (Join-Path $repoRoot "Youtube_API_key.txt")
)
foreach ($f in $filesToDelete) {
  if (Test-Path -LiteralPath $f) {
    Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
  }
}

# API 키 유출 방지 게이트: 레포 내에 'AIza[0-9A-Za-z\-_]{20,}' 패턴이 있으면 즉시 FAIL (.env.example 제외)
$leakPatterns = @(
  (Join-Path $repoRoot "backend\**\*.py"),
  (Join-Path $repoRoot "backend\**\*.ps1"),
  (Join-Path $repoRoot "backend\**\*.json"),
  (Join-Path $repoRoot "backend\**\*.txt"),
  (Join-Path $repoRoot "backend\**\*.md"),
  (Join-Path $repoRoot "data\**\*.json"),
  (Join-Path $repoRoot "data\**\*.jsonl"),
  (Join-Path $repoRoot "data\**\*.log"),
  (Join-Path $repoRoot "data\**\*.txt"),
  "*.ps1", "*.py", "*.txt", "*.md", "*.json", "*.log"
)
$leakHits = @()
foreach ($p in $leakPatterns) {
  $h = Select-String -Path $p -Pattern "AIza[0-9A-Za-z\-_]{20,}" -ErrorAction SilentlyContinue
  if ($h) { $leakHits += $h }
}
if ($leakHits) {
  $filtered = $leakHits | Where-Object { $_.Path -notlike "*\.env.example" }
  if ($filtered) {
    Write-Host "FATAL: API_KEY_LEAK_DETECTED"
    $filtered | Select-Object Path, LineNumber, Line | Format-Table -AutoSize | Out-String | Write-Host
    exit 1
  }
}

# A-1: PowerShell 출력/파이프라인 UTF-8 강제
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
chcp 65001 | Out-Null

# A-1: Python UTF-8 모드 강제(UnicodeEncodeError 구조적 차단)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# YouTube Data API 키 존재 사전 게이트 (Windows 환경변수 SSOT)
$ytKey = $env:YOUTUBE_DATA_API_KEY
if ([string]::IsNullOrWhiteSpace($ytKey)) {
  Write-Host "YOUTUBE_DATA_API_KEY_PRESENT=False"
  Write-Host "YOUTUBE_DATA_API_KEY_LEN=0"
  Write-Host "FATAL: YOUTUBE_DATA_API_KEY_NOT_SET"
  exit 1
}
else {
  $len = $ytKey.Length
  Write-Host ("YOUTUBE_DATA_API_KEY_PRESENT=True")
  Write-Host ("YOUTUBE_DATA_API_KEY_LEN=" + $len)

  # 마스킹된 키 출력 (앞 6자 + ... + 길이만 노출)
  $head = $ytKey.Substring(0, [Math]::Min(6, $len))
  Write-Host ("YOUTUBE_DATA_API_KEY_MASKED=" + $head + "...(len=" + $len + ")")

  # 호환 환경변수로도 주입 (기존 코드 호환용)
  $env:YTDAPI_API_KEY  = $ytKey
  $env:YOUTUBE_API_KEY = $ytKey
}

# A-1: 증거 출력
& python -X utf8 -c "import sys; print('STDOUT_ENCODING', sys.stdout.encoding)"

# A-1: SSL_CERT_FILE 강제 주입
$env:SSL_CERT_FILE = (& python -X utf8 -c "import certifi; print(certifi.where())")
Write-Host ("SSL_CERT_FILE=" + $env:SSL_CERT_FILE)

# A-1: HTTPS Health Gate(실패 즉시 종료)
$env:STEP_A_HTTPS_OK = "false"
& python -X utf8 -c "import urllib.request; urllib.request.urlopen('https://www.youtube.com',timeout=10).read(200); print('HTTPS_OK')"
if ($LASTEXITCODE -ne 0) { Write-Host 'FATAL: HTTPS_GATE_FAILED'; exit 1 }
$env:STEP_A_HTTPS_OK = "true"

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

function Ensure-Dir([string]$p) {
  New-Item -ItemType Directory -Force -Path $p | Out-Null
  return (Resolve-Path -LiteralPath $p).Path
}

function Resolve-SnapshotsBase([string]$repoRoot) {
  return (Ensure-Dir (Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots"))
}

function Parse-CycleId-FromStdout([string[]]$lines) {
  $jsonLine = ($lines | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1)
  if ([string]::IsNullOrWhiteSpace($jsonLine)) { throw "cycle json line not found" }
  try { $obj = $jsonLine | ConvertFrom-Json } catch { throw "cycle json parse failed" }
  $cid = $obj.result.cycle_id
  if ([string]::IsNullOrWhiteSpace($cid)) { throw "cycle_id missing in json" }
  return $cid
}

Write-Host "=== v7 Keyword Discovery with yt-dlp (RUN: STEP D~E) ==="

# yt-dlp enable (STEP D inputs)
$env:YTDLP_ENABLED = "1"
$env:YTDLP_CHANNELS_ENABLED = "1"
$env:ENABLE_YTDLP = "1"

$repoRoot = Resolve-RepoRoot
$snapBase = Resolve-SnapshotsBase $repoRoot
Write-Host ("REPO_ROOT=" + $repoRoot)
Write-Host ("SNAPSHOTS_BASE=" + $snapBase)

# yt-dlp 강제 ON 플래그 주입
$env:V7_ENABLE_YTDLP = "1"
$env:V7_YTDLP_MIN_TITLES_REQUIRED = "10"

# ----------------------------
# STEP D: keyword-discovery (yt-dlp 포함)
# ----------------------------
$runLog = Join-Path $repoRoot ("data\knowledge_v1_store\debug\v7_run_stream_" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
New-Item -ItemType Directory -Force (Split-Path -Parent $runLog) | Out-Null
$ErrorActionPreference = "Continue"
$lines = & python -X utf8 -m backend.cli.run knowledge keyword-discovery --mode run 2>&1 | Tee-Object -FilePath $runLog
$code = $LASTEXITCODE
$ErrorActionPreference = "Stop"

$lines | ForEach-Object { Write-Host $_ }
if ($code -ne 0) { Write-Host ("FATAL: STEP D keyword-discovery failed (exit=" + $code + ")"); exit 1 }

try { $cycleId = Parse-CycleId-FromStdout $lines } catch { Write-Host ("FATAL: " + $_.Exception.Message); exit 1 }
$env:V7_CYCLE_ID = $cycleId
Write-Host ("V7_CYCLE_ID=" + $cycleId)

# cycle_id 단일화: last_cycle_id.txt에 저장 (Step E/F에서 사용)
$lastCycleIdFile = Join-Path $snapBase "last_cycle_id.txt"
try {
    [System.IO.File]::WriteAllText($lastCycleIdFile, $cycleId, [System.Text.Encoding]::UTF8)
    Write-Host ("last_cycle_id.txt saved: " + $cycleId)
} catch {
    Write-Host ("WARNING: Failed to save last_cycle_id.txt: " + $_.Exception.Message)
}

# 기존 verify (ytdlp 산출물 검증) 유지
$verifyPs1 = Join-Path $repoRoot "backend\scripts\v7_verify_ytdlp_outputs.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $verifyPs1 -CycleId $cycleId
if ($LASTEXITCODE -ne 0) { Write-Host "FATAL: STEP D verify failed"; exit 1 }

Write-Host "=== STEP D PASS ==="

Write-Host "=== STEP D PASS ==="
Write-Host "=== RUN PASS (Step E/F는 별도 스크립트로 실행) ==="
exit 0
