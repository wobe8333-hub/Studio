# Step2 리팩토링 검증 테스트 스크립트
# 사용법: PowerShell에서 .\backend\test_step2.ps1 실행

Write-Host "=== Step2 리팩토링 검증 테스트 ===" -ForegroundColor Cyan
Write-Host ""

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDir = Join-Path $backendDir "output"

# API 엔드포인트
$baseUrl = "http://127.0.0.1:8000"
$endpoint = "$baseUrl/debug/step2"

# 샘플 입력 (core.sample_inputs의 STEP2_TEXT 사용)
$sampleText = "안녕하세요. 오늘은 자영업자 폐업률에 대해 이야기해보겠습니다.`n`n최근 통계에 따르면 자영업자 폐업률이 급증하고 있습니다. 이는 우리 사회 전반에 큰 영향을 미치고 있습니다.`n`n먼저 폐업률이 증가하는 주요 원인을 살펴보겠습니다. 경기 침체와 소비 위축이 가장 큰 요인입니다. 사람들의 소비 패턴이 바뀌면서 매출이 급감하고 있습니다."

$requestBody = @{
    text = $sampleText
} | ConvertTo-Json

Write-Host "[1] Step2 API 호출 중..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $endpoint -Method Post -Body $requestBody -ContentType "application/json; charset=utf-8"
    $runId = $response.run_id
    Write-Host "✓ API 호출 성공: run_id=$runId" -ForegroundColor Green
} catch {
    Write-Host "✗ API 호출 실패: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2] 산출물 4종 생성 확인 중..." -ForegroundColor Yellow

# 산출물 경로
$scriptFile = Join-Path $outputDir "verify" "${runId}_script.txt"
$sentencesFile = Join-Path $outputDir "verify" "${runId}_sentences.txt"
$scenesFile = Join-Path $outputDir "plans" "${runId}_scenes.json"
$reportFile = Join-Path $outputDir "reports" "${runId}_step2_report.json"

$files = @(
    @{Path=$scriptFile; Name="script.txt"},
    @{Path=$sentencesFile; Name="sentences.txt"},
    @{Path=$scenesFile; Name="scenes.json"},
    @{Path=$reportFile; Name="step2_report.json"}
)

$allExist = $true
foreach ($file in $files) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        if ($size -gt 0) {
            Write-Host "  ✓ $($file.Name): 존재, 크기=$size bytes" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $($file.Name): 존재하지만 크기 0" -ForegroundColor Red
            $allExist = $false
        }
    } else {
        Write-Host "  ✗ $($file.Name): 파일 없음" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host ""
    Write-Host "✗ 일부 파일이 생성되지 않았습니다." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3] 파일 내용 확인 (한글 포함 확인)..." -ForegroundColor Yellow
try {
    $sentencesContent = Get-Content $sentencesFile -Encoding utf8 -TotalCount 5
    Write-Host "  sentences.txt 첫 5줄:" -ForegroundColor Cyan
    $sentencesContent | ForEach-Object { Write-Host "    $_" }
    
    # 한글 포함 여부 간단 체크
    $hasKorean = $sentencesContent -match "[\uAC00-\uD7A3]"
    if ($hasKorean) {
        Write-Host "  ✓ 한글 포함 확인됨" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 한글이 보이지 않습니다 (인코딩 문제 가능성)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ 파일 읽기 실패: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "[4] 리포트 구조 확인 중..." -ForegroundColor Yellow
try {
    $reportContent = Get-Content $reportFile -Encoding utf8 -Raw | ConvertFrom-Json
    
    # 기본 필드 확인
    $checks = @(
        @{Field="status"; Expected="success"; Actual=$reportContent.status},
        @{Field="run_id"; Expected=$runId; Actual=$reportContent.run_id},
        @{Field="step"; Expected=2; Actual=$reportContent.step}
    )
    
    foreach ($check in $checks) {
        if ($check.Actual -eq $check.Expected) {
            Write-Host "  ✓ $($check.Field): $($check.Actual)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $($check.Field): 예상=$($check.Expected), 실제=$($check.Actual)" -ForegroundColor Red
            $allExist = $false
        }
    }
    
    # errors 배열 확인
    if ($reportContent.errors.Count -eq 0) {
        Write-Host "  ✓ errors: [] (비어있음)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ errors: $($reportContent.errors.Count)개 오류 있음" -ForegroundColor Red
        $reportContent.errors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
        $allExist = $false
    }
    
    # generated_files 확인
    if ($reportContent.generated_files.Count -eq 4) {
        Write-Host "  ✓ generated_files: 4개 파일 경로" -ForegroundColor Green
    } else {
        Write-Host "  ✗ generated_files: 예상 4개, 실제 $($reportContent.generated_files.Count)개" -ForegroundColor Red
        $allExist = $false
    }
    
    # generated_files_relative 확인 (새로 추가된 필드)
    if ($reportContent.generated_files_relative) {
        if ($reportContent.generated_files_relative.Count -eq 4) {
            Write-Host "  ✓ generated_files_relative: 4개 상대경로" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ generated_files_relative: 예상 4개, 실제 $($reportContent.generated_files_relative.Count)개" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠ generated_files_relative 필드 없음 (리팩토링 버전 아님)" -ForegroundColor Yellow
    }
    
    # checkprompt 관련 필드 없음 확인
    if ($reportContent.PSObject.Properties.Name -contains "checkprompt") {
        Write-Host "  ✗ checkprompt 필드가 여전히 존재함 (제거되어야 함)" -ForegroundColor Red
        $allExist = $false
    } else {
        Write-Host "  ✓ checkprompt 필드 없음 (정상)" -ForegroundColor Green
    }
    
    # summary 확인
    if ($reportContent.summary.sentence_count -gt 0) {
        Write-Host "  ✓ summary.sentence_count: $($reportContent.summary.sentence_count)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ summary.sentence_count: 0 (비정상)" -ForegroundColor Yellow
    
} catch {
    Write-Host "  ✗ 리포트 읽기/파싱 실패: $_" -ForegroundColor Red
    $allExist = $false
}

Write-Host ""
if ($allExist) {
    Write-Host "=== 모든 검증 통과 ✓ ===" -ForegroundColor Green
    Write-Host "run_id: $runId" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "=== 일부 검증 실패 ✗ ===" -ForegroundColor Red
    exit 1
}
}
