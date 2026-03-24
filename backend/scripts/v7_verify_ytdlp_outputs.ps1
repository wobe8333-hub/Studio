param(
  [string]$CycleId = ""
)

$ErrorActionPreference = "Stop"

# A) 파라미터 CycleId는 반드시 Trim 처리
$CycleId = $CycleId.Trim()

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

function Resolve-SnapshotsBase([string]$repoRoot) {
  $p = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots"
  if (-not (Test-Path -LiteralPath $p)) { throw "SNAPSHOTS_BASE missing" }
  return (Resolve-Path -LiteralPath $p).Path
}

function Read-LastCycleId([string]$snapBase) {
  $p = Join-Path $snapBase "last_cycle_id.txt"
  if (-not (Test-Path -LiteralPath $p)) { return "" }
  $t = (Get-Content -LiteralPath $p -ErrorAction SilentlyContinue | Select-Object -First 1)
  if ($t) { return $t.Trim() }
  return ""
}

Write-Host "=== v7 yt-dlp OUTPUT VERIFY ==="

# ✅ 하드 금지: search.list 존재 시 즉시 FAIL (쿼터 정책)
$hits = Select-String -Path "backend\**\*.py" -Pattern "search\.list" -SimpleMatch -ErrorAction SilentlyContinue
if ($hits) { Write-Host "FAIL: search.list detected"; exit 1 }

$repoRoot = Resolve-RepoRoot
$snapBase = Resolve-SnapshotsBase $repoRoot
Write-Host ("REPO_ROOT=" + $repoRoot)
Write-Host ("SNAPSHOTS_BASE=" + $snapBase)

# ✅ cycle_id 우선순위: param > env > last_cycle_id.txt
if ([string]::IsNullOrWhiteSpace($CycleId)) { $CycleId = $env:V7_CYCLE_ID }
if ([string]::IsNullOrWhiteSpace($CycleId)) { $CycleId = Read-LastCycleId $snapBase }
if ([string]::IsNullOrWhiteSpace($CycleId)) { Write-Host "FAIL: cycle id not resolvable"; exit 1 }

$cycleDir = Join-Path $snapBase $CycleId
# B) cycle dir not found 시, 아래 증거 3개를 함께 출력 후 exit 1
if (-not (Test-Path -LiteralPath $cycleDir)) {
    Write-Host "FAIL: cycle dir not found in snapshots store"
    Write-Host ("SNAP_BASE=" + $snapBase)
    Write-Host ("CycleId=" + $CycleId)
    Write-Host "Latest snapshot directories:"
    Get-ChildItem -Path $snapBase -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime | Format-Table -Auto | Out-String | Write-Host
    exit 1
}

Write-Host ("cycle_id=" + $CycleId)
Write-Host ("path=" + (Resolve-Path -LiteralPath $cycleDir))

# ✅ Required yt-dlp artifacts (실제 저장 위치 기준)
$chSnap  = Join-Path $cycleDir "ytdlp_channels_snapshot.jsonl"
$metrics = Join-Path $cycleDir "ytdlp_metrics.json"
$errors  = Join-Path $cycleDir "ytdlp_errors.json"

if (-not (Test-Path -LiteralPath $chSnap))  { Write-Host "FAIL: missing ytdlp_channels_snapshot.jsonl"; exit 1 }
if (-not (Test-Path -LiteralPath $metrics)) { Write-Host "FAIL: missing ytdlp_metrics.json"; exit 1 }
if (-not (Test-Path -LiteralPath $errors))  { Write-Host "FAIL: missing ytdlp_errors.json"; exit 1 }

# Snapshot sanity
$sz = (Get-Item -LiteralPath $chSnap).Length
if ($sz -lt 10) { Write-Host "FAIL: snapshot too small"; exit 1 }
$lineCount = (Get-Content -LiteralPath $chSnap | Measure-Object -Line).Lines
if ($lineCount -lt 1) { Write-Host "FAIL: snapshot empty"; exit 1 }

# Metrics sanity
try { $m = Get-Content -LiteralPath $metrics -Raw | ConvertFrom-Json } catch { Write-Host "FAIL: metrics json parse error"; exit 1 }

$videos = 0
$titlesRatio = 0.0
try { $videos = [int]$m.videos_total_raw } catch { $videos = 0 }
try { $titlesRatio = [double]$m.titles_nonempty_ratio } catch { $titlesRatio = 0.0 }

Write-Host ("videos_total_raw=" + $videos)
Write-Host ("titles_nonempty_ratio=" + $titlesRatio)

if ($videos -lt 1) { Write-Host "FAIL: no ytdlp videos"; exit 1 }
if ($titlesRatio -lt 0.95) { Write-Host "FAIL: title ratio low"; exit 1 }

# B) SSOT 파일 존재/STEP 상태 검증
$ssotFile = Join-Path $repoRoot ("data\knowledge_v1_store\ssot\" + $CycleId + "\ytdlp_ssot_summary.json")
if (-not (Test-Path -LiteralPath $ssotFile)) {
    Write-Host "FAIL: ytdlp_ssot_summary.json missing"
    Write-Host ("SSOT_FILE=" + $ssotFile)
    Write-Host "=== VERIFY FAIL ==="
    exit 1
}

# SSOT JSON 파싱
try {
    $ssotContent = Get-Content -LiteralPath $ssotFile -Encoding utf8 | Out-String
    $ssotJson = $ssotContent | ConvertFrom-Json
} catch {
    Write-Host "FAIL: ytdlp_ssot_summary.json parse error"
    Write-Host ("SSOT_FILE=" + $ssotFile)
    Write-Host ("ERROR=" + $_.Exception.Message)
    Write-Host "=== VERIFY FAIL ==="
    exit 1
}

$stepA = $ssotJson.step_status.STEP_A
$stepB = $ssotJson.step_status.STEP_B
$stepC = $ssotJson.step_status.STEP_C

Write-Host ("STEP_A_STATUS=" + $stepA)
Write-Host ("STEP_B_STATUS=" + $stepB)
Write-Host ("STEP_C_STATUS=" + $stepC)

$allPass = $true
if ($stepA -ne "PASS") { $allPass = $false }
if ($stepB -ne "PASS") { $allPass = $false }
if ($stepC -ne "PASS") { $allPass = $false }

if (-not $allPass) {
    Write-Host "=== VERIFY FAIL ==="
    Write-Host "step_status:"
    $ssotJson.step_status | Format-List | Out-String | Write-Host
    Write-Host "summary (key metrics):"
    $tCount = $ssotJson.summary.ytdlp_title_count
    $cCount = $ssotJson.summary.ytdlp_candidate_keyword_count
    $httpsOk = $ssotJson.summary.transport_https_ok
    Write-Host ("ytdlp_title_count=" + $tCount)
    Write-Host ("ytdlp_candidate_keyword_count=" + $cCount)
    Write-Host ("transport_https_ok=" + $httpsOk)
    exit 1
}

Write-Host "STEP_A_PASS"
Write-Host "STEP_B_PASS"
Write-Host "STEP_C_PASS"

# STEP D 검증: anchor 파일 + quota_log (A~C/D PASS면 exit 0)
$stepD = $ssotJson.step_status.STEP_D
if ($stepD -eq "PASS") {
    $anchorFile = Join-Path $repoRoot ("data\knowledge_v1_store\keyword_discovery\anchors\youtube_data_api_anchor_kr.json")
    $quotaLog = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\anchors\quota_log.jsonl"
    
    if (-not (Test-Path -LiteralPath $anchorFile)) {
        Write-Host "FAIL: STEP_D anchor file missing"
        exit 1
    }
    
    try {
        $anchorData = Get-Content -LiteralPath $anchorFile -Encoding utf8 | Out-String | ConvertFrom-Json
        if ($anchorData.keywords.Count -lt 1) {
            Write-Host "FAIL: STEP_D keywords < 1"
            exit 1
        }
    } catch {
        Write-Host "FAIL: STEP_D anchor parse error"
        exit 1
    }
    
    if (-not (Test-Path -LiteralPath $quotaLog)) {
        Write-Host "FAIL: STEP_D quota_log missing"
        exit 1
    }
    
    Write-Host "STEP_D_PASS"
} elseif ($stepD -eq "FAIL") {
    Write-Host "FAIL: STEP_D status=FAIL"
    exit 1
}

# A~C/D PASS면 exit 0 (착시 제거)
Write-Host "=== VERIFY PASS (A~C/D) ==="
exit 0

# STEP E/F는 정보 출력만 (exitcode에 영향 없음)
$stepE = $ssotJson.step_status.STEP_E
$stepF = $ssotJson.step_status.STEP_F_CONTRACT

Write-Host ("STEP_E_STATUS=" + $stepE)
Write-Host ("STEP_F_CONTRACT_STATUS=" + $stepF)
