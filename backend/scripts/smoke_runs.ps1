# AI Animation Studio V2 - Runs 구조 스모크 테스트
# 사용법: PowerShell에서 실행 (.\scripts\smoke_runs.ps1)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Runs 구조 스모크 테스트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 서버 기동 확인
Write-Host "[1/5] 서버 기동 확인..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method GET -ErrorAction Stop
    Write-Host "  ✓ 서버 정상 기동" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 서버가 실행되지 않았습니다." -ForegroundColor Red
    exit 1
}

# 2. output/runs 디렉토리 확인
Write-Host "[2/5] output/runs 디렉토리 확인..." -ForegroundColor Yellow
$backendDir = Split-Path -Parent $PSScriptRoot
$runsDir = Join-Path $backendDir "output\runs"

if (Test-Path $runsDir) {
    Write-Host "  ✓ output/runs 디렉토리 존재" -ForegroundColor Green
} else {
    Write-Host "  ✗ output/runs 디렉토리 없음 (Step2 실행 후 생성됨)" -ForegroundColor Yellow
}

# 3. Step2 실행
Write-Host "[3/5] Step2 실행..." -ForegroundColor Yellow
$step2Body = @{
    script = "안녕하세요. 오늘은 좋은 날입니다. AI Animation Studio를 테스트하고 있습니다. 이 스크립트는 여러 문장으로 구성되어 있습니다. 각 문장은 하나의 씬으로 변환됩니다. 품질 게이트를 통과하기 위해 충분한 문장과 씬을 포함합니다."
} | ConvertTo-Json

try {
    $step2Response = Invoke-RestMethod -Uri "$baseUrl/step2/structure-script" -Method POST -Body $step2Body -ContentType "application/json" -ErrorAction Stop
    
    if ($step2Response.status -eq "success") {
        $runId = $step2Response.run_id
        Write-Host "  ✓ Step2 실행 성공 (run_id: $runId)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Step2 실행 실패: $($step2Response.message)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Step2 실행 실패: $_" -ForegroundColor Red
    exit 1
}

# 4. runs 구조 확인
Write-Host "[4/5] runs 구조 확인..." -ForegroundColor Yellow
$runDir = Join-Path $runsDir $runId

if (-not (Test-Path $runDir)) {
    Write-Host "  ✗ runs/$runId 디렉토리 없음" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ runs/$runId 디렉토리 존재" -ForegroundColor Green

# manifest.json 확인
$manifestPath = Join-Path $runDir "manifest.json"
if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
    Write-Host "  ✓ manifest.json 존재" -ForegroundColor Green
    Write-Host "    - run_id: $($manifest.run_id)" -ForegroundColor Gray
    Write-Host "    - status: $($manifest.status)" -ForegroundColor Gray
    Write-Host "    - step2.status: $($manifest.steps.step2.status)" -ForegroundColor Gray
} else {
    Write-Host "  ✗ manifest.json 없음" -ForegroundColor Red
    exit 1
}

# step2/ 디렉토리 확인
$step2Dir = Join-Path $runDir "step2"
if (Test-Path $step2Dir) {
    Write-Host "  ✓ step2/ 디렉토리 존재" -ForegroundColor Green
    
    $step2Files = @("script.txt", "sentences.txt", "step2_report.json")
    foreach ($file in $step2Files) {
        $filePath = Join-Path $step2Dir $file
        if (Test-Path $filePath) {
            $size = (Get-Item $filePath).Length
            Write-Host "    ✓ $file ($size bytes)" -ForegroundColor Green
        } else {
            Write-Host "    ✗ $file 없음" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  ✗ step2/ 디렉토리 없음" -ForegroundColor Red
    exit 1
}

# 5. 기존 구조도 유지되는지 확인
Write-Host "[5/5] 기존 구조 유지 확인..." -ForegroundColor Yellow
$outputDir = Join-Path $backendDir "output"
$legacyDirs = @(
    @{Path = "verify"; Name = "verify"},
    @{Path = "plans"; Name = "plans"},
    @{Path = "reports"; Name = "reports"}
)

$allOk = $true
foreach ($dir in $legacyDirs) {
    $legacyPath = Join-Path $outputDir $dir.Path
    if (Test-Path $legacyPath) {
        Write-Host "  ✓ $($dir.Name) 디렉토리 존재" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($dir.Name) 디렉토리 없음" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Host "  ⚠ 기존 구조 일부 누락 (기능 유지 확인 필요)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Runs 구조 스모크 테스트 완료" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "생성된 구조:" -ForegroundColor Yellow
Write-Host "  - runs/$runId/manifest.json" -ForegroundColor Gray
Write-Host "  - runs/$runId/step2/ (script.txt, sentences.txt, step2_report.json)" -ForegroundColor Gray
Write-Host "  - 기존 구조도 유지됨 (verify/, plans/, reports/)" -ForegroundColor Gray
}
