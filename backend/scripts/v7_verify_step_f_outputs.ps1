param(
    [string]$CycleId = ""
)

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

# cycle_id 확정
if ([string]::IsNullOrWhiteSpace($CycleId)) {
    $cidFile = Join-Path $repoRoot "data\knowledge_v1_store\keyword_discovery\snapshots\last_cycle_id.txt"
    if (!(Test-Path -LiteralPath $cidFile)) {
        Write-Host "FAIL: last_cycle_id.txt missing" -ForegroundColor Red
        exit 1
    }
    $CycleId = (Get-Content $cidFile -Encoding utf8 | Select-Object -First 1).Trim()
}

Write-Host ("CYCLE_ID=" + $CycleId)

# 최신 output_dir 탐지
$baseDir = Join-Path $repoRoot "data\knowledge_v1_store\script_prompts"
if (!(Test-Path -LiteralPath $baseDir)) {
    Write-Host "FAIL: script_prompts base dir missing" -ForegroundColor Red
    Write-Host "STEP F run 실패로 output_dir 미생성 가능. 먼저 v7_run_step_f_script_prompt.ps1 로그 확인" -ForegroundColor Yellow
    exit 1
}

# cycle_id로 시작하는 디렉토리 중 최신 것 선택 (__ 구분자 지원)
$candidates = Get-ChildItem -Path $baseDir -Directory -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "$CycleId*"
} | Sort-Object LastWriteTime -Descending

if ($candidates.Count -eq 0) {
    Write-Host "FAIL: no output dir found for cycle_id=$CycleId" -ForegroundColor Red
    exit 1
}

$outputDir = $candidates[0]
Write-Host ("OUTPUT_DIR=" + $outputDir.FullName)

# 파일 존재 확인
$scriptPromptFile = Join-Path $outputDir.FullName "script_prompt.json"
$manifestFile = Join-Path $outputDir.FullName "prompt_manifest.json"

if (!(Test-Path -LiteralPath $scriptPromptFile)) {
    Write-Host "FAIL: script_prompt.json missing" -ForegroundColor Red
    exit 1
}

if (!(Test-Path -LiteralPath $manifestFile)) {
    Write-Host "FAIL: prompt_manifest.json missing" -ForegroundColor Red
    exit 1
}

# JSON 파싱 및 검증
try {
    $scriptPrompt = Get-Content $scriptPromptFile -Encoding utf8 | Out-String | ConvertFrom-Json
    $manifest = Get-Content $manifestFile -Encoding utf8 | Out-String | ConvertFrom-Json
} catch {
    Write-Host ("FAIL: JSON parse error: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

# script_prompt.json 검증
if ($scriptPrompt.ok -ne $true) {
    Write-Host "FAIL: script_prompt.json ok != true" -ForegroundColor Red
    exit 1
}

if ($scriptPrompt.cycle_id -ne $CycleId) {
    Write-Host ("FAIL: script_prompt.json cycle_id mismatch (expected=$CycleId, got=" + $scriptPrompt.cycle_id + ")") -ForegroundColor Red
    exit 1
}

$snippets = $scriptPrompt.knowledge_context.snippets
if ($null -eq $snippets -or $snippets.Count -lt 1) {
    Write-Host "FAIL: knowledge_context.snippets length < 1" -ForegroundColor Red
    exit 1
}

$citations = $scriptPrompt.knowledge_context.citations
if ($null -eq $citations -or $citations.Count -lt 1) {
    Write-Host "FAIL: knowledge_context.citations length < 1" -ForegroundColor Red
    exit 1
}

$promptText = $scriptPrompt.prompt
if ([string]::IsNullOrWhiteSpace($promptText) -or $promptText.Length -lt 500) {
    Write-Host ("FAIL: prompt text too short (length=" + $promptText.Length + ")") -ForegroundColor Red
    exit 1
}

# prompt_manifest.json 검증
if ($manifest.ok -ne $true) {
    Write-Host "FAIL: prompt_manifest.json ok != true" -ForegroundColor Red
    exit 1
}

$evidenceHashes = $manifest.evidence_hashes
if ($null -eq $evidenceHashes -or $evidenceHashes.Count -lt 1) {
    Write-Host "FAIL: evidence_hashes length < 1" -ForegroundColor Red
    exit 1
}

$sources = $manifest.sources
if ($null -eq $sources -or $sources.Count -lt 1) {
    Write-Host "FAIL: sources length < 1" -ForegroundColor Red
    exit 1
}

# sources 필드 검증
foreach ($source in $sources) {
    if ([string]::IsNullOrWhiteSpace($source.sha256)) {
        Write-Host "FAIL: source missing sha256" -ForegroundColor Red
        exit 1
    }
    if ([string]::IsNullOrWhiteSpace($source.file_path)) {
        Write-Host "FAIL: source missing file_path" -ForegroundColor Red
        exit 1
    }
    if ($null -eq $source.byte_size) {
        Write-Host "FAIL: source missing byte_size" -ForegroundColor Red
        exit 1
    }
}

Write-Host "STEP_F_VERIFY_PASS" -ForegroundColor Green
Write-Host ("SNIPPETS_COUNT=" + $snippets.Count)
Write-Host ("EVIDENCE_HASHES_COUNT=" + $evidenceHashes.Count)
Write-Host ("SOURCES_COUNT=" + $sources.Count)
Write-Host "=== VERIFY PASS ===" -ForegroundColor Green
exit 0

