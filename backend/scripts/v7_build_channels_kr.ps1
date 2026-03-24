# v7 KR 채널 자동 생성/보강 스크립트

# UTF-8 고정
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Repo root 강제
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot

try {
    Write-Host "=== v7 KR 채널 자동 발굴 ===" -ForegroundColor Cyan
    Write-Host "작업 디렉토리: $(Get-Location)" -ForegroundColor Cyan
    Write-Host ""

    $outputFile = "backend\config\ytdlp_channels_kr.txt"
    
    # 환경변수 (캐스팅 전 null/빈값 체크로 0값 버그 방지)
    if ([string]::IsNullOrWhiteSpace($env:YTDLP_DISCOVERY_SEARCH_PER_SEED)) {
        $searchPerSeed = 20
    } else {
        $searchPerSeed = [int]$env:YTDLP_DISCOVERY_SEARCH_PER_SEED
    }
    
    if ([string]::IsNullOrWhiteSpace($env:YTDLP_DISCOVERY_MAX_CHANNELS_ADD)) {
        $maxChannelsAdd = 200
    } else {
        $maxChannelsAdd = [int]$env:YTDLP_DISCOVERY_MAX_CHANNELS_ADD
    }
    
    if ([string]::IsNullOrWhiteSpace($env:YTDLP_DISCOVERY_LOOKBACK_DAYS)) {
        $lookbackDays = 30
    } else {
        $lookbackDays = [int]$env:YTDLP_DISCOVERY_LOOKBACK_DAYS
    }
    
    if ([string]::IsNullOrWhiteSpace($env:YTDLP_KR_TITLE_HANGUL_RATIO_MIN)) {
        $hangulRatioMin = 0.25
    } else {
        $hangulRatioMin = [double]$env:YTDLP_KR_TITLE_HANGUL_RATIO_MIN
    }

    Write-Host "설정:" -ForegroundColor Cyan
    Write-Host "  output_file: $outputFile"
    Write-Host "  search_per_seed: $searchPerSeed"
    Write-Host "  max_channels_add: $maxChannelsAdd"
    Write-Host "  hangul_ratio_min: $hangulRatioMin"
    Write-Host ""

    # 0값 검증 (FAIL-FAST)
    if ($searchPerSeed -lt 1) {
        Write-Host "[FAIL] search_per_seed < 1: $searchPerSeed" -ForegroundColor Red
        exit 1
    }
    if ($maxChannelsAdd -lt 1) {
        Write-Host "[FAIL] max_channels_add < 1: $maxChannelsAdd" -ForegroundColor Red
        exit 1
    }
    if ($hangulRatioMin -le 0) {
        Write-Host "[FAIL] hangul_ratio_min <= 0: $hangulRatioMin" -ForegroundColor Red
        exit 1
    }

    # 실행
    Write-Host "채널 발굴 실행 중..." -ForegroundColor Cyan
    Write-Host ""

    $resultJson = python -m backend.knowledge_v1.channel_discovery.discover_channels --scope KR --out $outputFile --search-per-seed $searchPerSeed --max-channels-add $maxChannelsAdd --lookback-days $lookbackDays --hangul-ratio-min $hangulRatioMin

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] 채널 발굴 실패 (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }

    try {
        $result = $resultJson | ConvertFrom-Json
        
        Write-Host "[OK] 채널 발굴 완료" -ForegroundColor Green
        Write-Host "  channels_discovered: $($result.channels_discovered)"
        Write-Host "  channels_filtered: $($result.channels_filtered)"
        Write-Host "  channels_appended: $($result.channels_appended)"
        Write-Host "  metrics_path: $($result.metrics_path)"
        Write-Host ""

        # 결과 파일 라인 수 확인
        if (Test-Path $outputFile) {
            $urlCount = 0
            $content = Get-Content $outputFile -Encoding UTF8
            foreach ($line in $content) {
                $trimmed = $line.Trim()
                if ($trimmed -and -not $trimmed.StartsWith("#")) {
                    if ($trimmed -match "^https?://") {
                        $urlCount++
                    }
                }
            }
            Write-Host "현재 $outputFile 라인 수: $urlCount" -ForegroundColor Cyan
        }

        exit 0
    } catch {
        Write-Host "[FAIL] 결과 파싱 실패: $_" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] 스크립트 실행 중 오류: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

