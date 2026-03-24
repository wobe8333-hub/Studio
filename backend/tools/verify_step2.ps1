# Step2 결과 자동 검증 스크립트
# 사용법: .\backend\tools\verify_step2.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step2 결과 자동 검증" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# UTF-8 인코딩 설정
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$backendDir = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $backendDir "output"

# 1. 최신 리포트 찾기
$reports = Get-ChildItem (Join-Path $outputDir "reports") -Filter "*_step2_report.json" -ErrorAction SilentlyContinue | 
    Sort-Object LastWriteTime -Descending

if (-not $reports) {
    Write-Host "❌ 리포트 파일을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "   경로: $(Join-Path $outputDir 'reports')" -ForegroundColor Yellow
    exit 1
}

$latestReport = $reports[0]
$reportData = Get-Content $latestReport.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$runId = $reportData.run_id

Write-Host "✓ 최신 리포트 발견: $($latestReport.Name)" -ForegroundColor Green
Write-Host "  run_id: $runId" -ForegroundColor Cyan
Write-Host "  생성 시간: $($reportData.generated_at)" -ForegroundColor Cyan
Write-Host ""

# 2. 필수 파일 4개 확인
Write-Host "=== 필수 파일 확인 ===" -ForegroundColor Yellow
$requiredFiles = @(
    @{key="script_path"; name="script.txt"; dir="verify"},
    @{key="sentences_path"; name="sentences.txt"; dir="verify"},
    @{key="scenes_path"; name="scenes.json"; dir="plans"},
    @{key="report_path"; name="step2_report.json"; dir="reports"}
)

$allFilesExist = $true
foreach ($fileInfo in $requiredFiles) {
    $filePath = $reportData.generated_files | Where-Object { $_ -like "*$($fileInfo.name)" } | Select-Object -First 1
    
    if ($filePath) {
        $file = Get-Item $filePath -ErrorAction SilentlyContinue
        if ($file) {
            $size = $file.Length
            Write-Host "  ✓ $($fileInfo.name): $size bytes" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $($fileInfo.name): 파일 없음" -ForegroundColor Red
            Write-Host "    경로: $filePath" -ForegroundColor Yellow
            $allFilesExist = $false
        }
    } else {
        Write-Host "  ✗ $($fileInfo.name): 경로 없음" -ForegroundColor Red
        $allFilesExist = $false
    }
}

Write-Host ""

# 3. 한글 깨짐 확인
Write-Host "=== 한글 깨짐 확인 ===" -ForegroundColor Yellow

$scriptFile = Get-ChildItem (Join-Path $outputDir "verify") -Filter "${runId}_script.txt" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($scriptFile) {
    $content = Get-Content $scriptFile.FullName -Raw -Encoding UTF8
    $hasCorruption = $content -match '|??'
    $koreanCount = ([regex]::Matches($content, '[가-힣]')).Count
    
    if ($hasCorruption) {
        Write-Host "  ✗ script.txt에 깨짐 문자 발견" -ForegroundColor Red
    } else {
        Write-Host "  ✓ script.txt 한글 정상 ($koreanCount 자)" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠ script.txt 파일 없음" -ForegroundColor Yellow
}

$scenesFile = Get-ChildItem (Join-Path $outputDir "plans") -Filter "${runId}_scenes.json" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($scenesFile) {
    $content = Get-Content $scenesFile.FullName -Raw -Encoding UTF8
    $hasCorruption = $content -match '|??'
    
    if ($hasCorruption) {
        Write-Host "  ✗ scenes.json에 깨짐 문자 발견" -ForegroundColor Red
    } else {
        Write-Host "  ✓ scenes.json 한글 정상" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠ scenes.json 파일 없음" -ForegroundColor Yellow
}

Write-Host ""

# 4. 리포트 내용 확인
Write-Host "=== 리포트 요약 ===" -ForegroundColor Yellow
Write-Host "  상태: $($reportData.status)" -ForegroundColor $(if ($reportData.status -eq "success") { "Green" } else { "Red" })
Write-Host "  문장 수: $($reportData.counts.sentences)" -ForegroundColor Cyan
Write-Host "  씬 수: $($reportData.counts.scenes)" -ForegroundColor Cyan

if ($reportData.warnings) {
    Write-Host "  경고:" -ForegroundColor Yellow
    foreach ($warning in $reportData.warnings) {
        Write-Host "    - $warning" -ForegroundColor Yellow
    }
}

if ($reportData.validation) {
    Write-Host ""
    Write-Host "=== 검증 결과 ===" -ForegroundColor Yellow
    $status = $reportData.validation.status
    $statusColor = switch ($status) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "FAIL" { "Red" }
        default { "White" }
    }
    Write-Host "  상태: $status" -ForegroundColor $statusColor
    
    if ($reportData.validation.failed_rules) {
        Write-Host "  실패 규칙:" -ForegroundColor Red
        foreach ($rule in $reportData.validation.failed_rules) {
            Write-Host "    - $($rule.name): $($rule.message)" -ForegroundColor Red
        }
    }
    
    if ($reportData.validation.warnings) {
        Write-Host "  경고:" -ForegroundColor Yellow
        foreach ($warning in $reportData.validation.warnings) {
            Write-Host "    - $($warning.name): $($warning.message)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allFilesExist) {
    Write-Host "✓ 검증 완료: 모든 파일이 정상적으로 생성되었습니다." -ForegroundColor Green
} else {
    Write-Host "⚠ 검증 완료: 일부 파일이 누락되었습니다." -ForegroundColor Yellow
}
}
