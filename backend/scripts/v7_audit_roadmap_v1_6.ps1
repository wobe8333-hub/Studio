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

# UTF-8 강제
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
chcp 65001 | Out-Null

Write-Host "=== v7 Audit Roadmap v1.6 ==="

# cycle_id 결정 우선순위: 1) last_cycle_id.txt, 2) snapshots 최신 디렉토리명
$snapBase = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots"
$lastCycleIdFile = Join-Path $snapBase "last_cycle_id.txt"

$cycleId = $null

# 우선순위 1: last_cycle_id.txt
if (Test-Path -LiteralPath $lastCycleIdFile) {
    $cycleId = [System.IO.File]::ReadAllText($lastCycleIdFile, [System.Text.Encoding]::UTF8).Trim()
}

# 우선순위 2: snapshots 최신 디렉토리명
if ([string]::IsNullOrWhiteSpace($cycleId) -and (Test-Path -LiteralPath $snapBase)) {
    $dirs = Get-ChildItem -Path $snapBase -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($dirs.Count -gt 0) {
        $cycleId = $dirs[0].Name
    }
}

if ([string]::IsNullOrWhiteSpace($cycleId)) {
    Write-Host "FATAL: cycle_id not resolvable (last_cycle_id.txt missing and no snapshots directories)" -ForegroundColor Red
    exit 2
}

Write-Host ("CYCLE_ID=" + $cycleId)

# SSOT gate1 파일 강제 생성
Write-Host ""
Write-Host "=== Writing SSOT Gate1 ===" -ForegroundColor Cyan
$ErrorActionPreference = "Continue"
$gate1Lines = & python -X utf8 -m backend.scripts.v7_write_ssot_gate1 --cycle-id $cycleId 2>&1
$gate1Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"

$gate1Lines | ForEach-Object { Write-Host $_ }

if ($gate1Code -ne 0) {
    Write-Host ("FATAL: Failed to write SSOT gate1 file (exit=" + $gate1Code + ")") -ForegroundColor Red
    exit 2
}

# SSOT summary 판정: data/knowledge_v1_store/ssot/<CID>/daily_keywords_gate1.json
$ssotFile = Join-Path $repoRoot ("data\knowledge_v1_store\ssot\" + $cycleId + "\daily_keywords_gate1.json")

if (-not (Test-Path -LiteralPath $ssotFile)) {
    Write-Host ("FATAL: SSOT file not found: " + $ssotFile) -ForegroundColor Red
    exit 2
}

Write-Host ("SSOT_FILE=" + $ssotFile)

try {
    $ssotContent = Get-Content -LiteralPath $ssotFile -Encoding utf8 | Out-String
    $ssotJson = $ssotContent | ConvertFrom-Json
} catch {
    Write-Host ("FATAL: SSOT JSON parse error: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    exit 1
}

# summary 필드 확인
if (-not $ssotJson.summary) {
    Write-Host "FATAL: SSOT summary field missing" -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    exit 1
}

$ytdlpTitleCount = $ssotJson.summary.ytdlp_title_count
$ytdlpKeywordCount = $ssotJson.summary.ytdlp_keyword_count

Write-Host ("SSOT_GATE1_PATH=" + $ssotFile)
Write-Host ("ytdlp_title_count=" + $ytdlpTitleCount)
Write-Host ("ytdlp_keyword_count=" + $ytdlpKeywordCount)

# 추가 카운트 출력
$stepDAnchorCount = $ssotJson.summary.step_d_anchor_keywords_count
$stepEAssetsCount = $ssotJson.summary.step_e_assets_count
$stepFEvidenceCount = $ssotJson.summary.step_f_evidence_hashes_count

if ($null -ne $stepDAnchorCount) {
    Write-Host ("step_d_anchor_keywords_count=" + $stepDAnchorCount)
}
if ($null -ne $stepEAssetsCount) {
    Write-Host ("step_e_assets_count=" + $stepEAssetsCount)
}
if ($null -ne $stepFEvidenceCount) {
    Write-Host ("step_f_evidence_hashes_count=" + $stepFEvidenceCount)
}

# 빈 값 체크 (빈 문자열 또는 null)
if ([string]::IsNullOrWhiteSpace($ytdlpTitleCount) -or [string]::IsNullOrWhiteSpace($ytdlpKeywordCount)) {
    Write-Host "FATAL: ssot_field_empty" -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    Write-Host ("ytdlp_title_count=" + $ytdlpTitleCount)
    Write-Host ("ytdlp_keyword_count=" + $ytdlpKeywordCount)
    exit 2
}

# 숫자 변환 및 검증
try {
    $titleCountInt = [int]$ytdlpTitleCount
    $keywordCountInt = [int]$ytdlpKeywordCount
} catch {
    Write-Host ("FATAL: SSOT count fields are not numbers: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    exit 2
}

if ($titleCountInt -lt 1) {
    Write-Host ("FATAL: ytdlp_title_count < 1 (value=" + $titleCountInt + ")") -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    exit 2
}

if ($keywordCountInt -lt 1) {
    Write-Host ("FATAL: ytdlp_keyword_count < 1 (value=" + $keywordCountInt + ")") -ForegroundColor Red
    Write-Host ("SSOT_FILE=" + $ssotFile)
    exit 2
}

# 선택적 검증 (가능하면)
if ($null -ne $stepEAssetsCount) {
    try {
        $assetsCountInt = [int]$stepEAssetsCount
        if ($assetsCountInt -lt 200) {
            Write-Host ("WARNING: step_e_assets_count < 200 (value=" + $assetsCountInt + ")") -ForegroundColor Yellow
        } else {
            Write-Host ("PASS: step_e_assets_count >= 200 (value=" + $assetsCountInt + ")") -ForegroundColor Green
        }
    } catch {
        Write-Host ("WARNING: step_e_assets_count is not a number") -ForegroundColor Yellow
    }
}

if ($null -ne $stepFEvidenceCount) {
    try {
        $evidenceCountInt = [int]$stepFEvidenceCount
        if ($evidenceCountInt -lt 1) {
            Write-Host ("WARNING: step_f_evidence_hashes_count < 1 (value=" + $evidenceCountInt + ")") -ForegroundColor Yellow
        } else {
            Write-Host ("PASS: step_f_evidence_hashes_count >= 1 (value=" + $evidenceCountInt + ")") -ForegroundColor Green
        }
    } catch {
        Write-Host ("WARNING: step_f_evidence_hashes_count is not a number") -ForegroundColor Yellow
    }
}

Write-Host "SSOT_SUMMARY_PASS" -ForegroundColor Green

# Scheduler 등록 확인 (자동 탐지)
Write-Host ""
Write-Host "=== Scheduler Check ===" -ForegroundColor Cyan

$schtasks = "C:\Windows\System32\schtasks.exe"
$schedulerTaskCandidates = @(
    "AIAnimationStudio_V7_Daily_10AM",
    "AIAnimationStudio_V7_Daily",
    "AIAnimationStudio_V7_Daily_10AM "
)

$foundTaskName = $null
$queryResult = $null
$queryExitCode = -1

# 후보 배열을 순회하며 첫 성공 항목 선택
foreach ($taskName in $schedulerTaskCandidates) {
    $taskNameTrimmed = $taskName.Trim()
    $out = & $schtasks /Query /TN $taskNameTrimmed /FO LIST /V 2>&1
    $ec = $LASTEXITCODE
    
    if ($ec -eq 0) {
        $foundTaskName = $taskNameTrimmed
        $queryResult = $out
        $queryExitCode = 0
        break
    }
}

if ($queryExitCode -ne 0) {
    Write-Host ("WARN: Scheduler task not found (checked: " + ($schedulerTaskCandidates -join ", ") + ")") -ForegroundColor Yellow
    Write-Host ""
    Write-Host "=== Scheduler Registration Command ===" -ForegroundColor Cyan
    Write-Host "Run the following command to register the scheduler task:"
    Write-Host ""
    $registerCmd = "schtasks /Create /F /SC DAILY /ST 10:00 /TN `"AIAnimationStudio_V7_Daily_10AM`" /TR `"powershell -NoProfile -ExecutionPolicy Bypass -File \`"$repoRoot\backend\scripts\v7_audit_roadmap_v1_6.ps1\`"`""
    Write-Host $registerCmd -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Note: Run this command as Administrator" -ForegroundColor Yellow
    Write-Host "Note: Scheduler check failure does not affect audit PASS/FAIL" -ForegroundColor Yellow
} else {
    Write-Host ("PASS: Scheduler task found: " + $foundTaskName) -ForegroundColor Green
    Write-Host ""
    
    # 필수 필드 추출 및 출력
    $taskName = $null
    $nextRunTime = $null
    $status = $null
    $lastResult = $null
    $taskToRun = $null
    $startIn = $null
    
    foreach ($line in $queryResult) {
        if ($line -match "^TaskName:\s*(.+)$") {
            $taskName = $matches[1].Trim()
        } elseif ($line -match "^Next Run Time:\s*(.+)$") {
            $nextRunTime = $matches[1].Trim()
        } elseif ($line -match "^Status:\s*(.+)$") {
            $status = $matches[1].Trim()
        } elseif ($line -match "^Last Result:\s*(.+)$") {
            $lastResult = $matches[1].Trim()
        } elseif ($line -match "^Task To Run:\s*(.+)$") {
            $taskToRun = $matches[1].Trim()
        } elseif ($line -match "^Start In:\s*(.+)$") {
            $startIn = $matches[1].Trim()
        }
    }
    
    if ($taskName) { Write-Host ("TaskName: " + $taskName) }
    if ($nextRunTime) { Write-Host ("Next Run Time: " + $nextRunTime) }
    if ($status) { Write-Host ("Status: " + $status) }
    if ($lastResult) { Write-Host ("Last Result: " + $lastResult) }
    if ($taskToRun) { Write-Host ("Task To Run: " + $taskToRun) }
    if ($startIn) { Write-Host ("Start In: " + $startIn) }
    
    # 전체 출력도 제공 (최대 30줄)
    Write-Host ""
    Write-Host "--- Full Output (first 30 lines) ---" -ForegroundColor Gray
    $queryResult | Select-Object -First 30 | ForEach-Object { Write-Host $_ }
}

Write-Host ""
Write-Host "=== AUDIT PASS ===" -ForegroundColor Green
exit 0

