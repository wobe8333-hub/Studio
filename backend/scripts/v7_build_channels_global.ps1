# v7 GLOBAL 채널 템플릿 생성 스크립트

# UTF-8 고정
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Repo root 강제
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot

try {
    Write-Host "=== v7 GLOBAL 채널 템플릿 생성 ===" -ForegroundColor Cyan
    Write-Host "작업 디렉토리: $(Get-Location)" -ForegroundColor Cyan
    Write-Host ""

    $outputFile = "backend\config\ytdlp_channels_global.txt"

    if (Test-Path $outputFile) {
        Write-Host "[OK] $outputFile 이미 존재합니다" -ForegroundColor Green
        exit 0
    }

    # 최소 5개 기본 채널 URL 샘플 생성
    $sampleChannels = @(
        "# GLOBAL 채널 URL 목록",
        "# UTF-8 인코딩",
        "# 1줄 1채널 URL (yt-dlp 입력 가능한 형태)",
        "# # 으로 시작하는 줄은 주석",
        "",
        "# 예시 채널 URL (실제 사용 시 이 부분을 수정하세요)",
        "# https://www.youtube.com/@example_global_1",
        "# https://www.youtube.com/@example_global_2",
        "# https://www.youtube.com/@example_global_3",
        "# https://www.youtube.com/@example_global_4",
        "# https://www.youtube.com/@example_global_5"
    )

    try {
        $sampleChannels | Out-File -FilePath $outputFile -Encoding UTF8 -NoNewline
        Write-Host "[OK] $outputFile 생성 완료" -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "[FAIL] 파일 생성 실패: $_" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] 스크립트 실행 중 오류: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
}
