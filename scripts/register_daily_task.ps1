# KAS 일간 파이프라인 — Windows Task Scheduler 등록 스크립트
# 실행 방법: PowerShell을 관리자 권한으로 열고 .\scripts\register_daily_task.ps1 실행
# 매일 오전 6시 자동 실행 (Windows Task Scheduler)

param(
    [string]$TaskName   = "KAS_Daily_Pipeline",
    [string]$RunHour    = "06",
    [string]$RunMinute  = "00",
    [string]$PythonPath = ""   # 비어 있으면 where python으로 자동 탐색
)

$ErrorActionPreference = "Stop"

# ── Python 경로 자동 탐색 ────────────────────────────────────────────────────
if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        Write-Error "Python을 찾을 수 없습니다. --PythonPath 옵션으로 경로를 지정하세요."
        exit 1
    }
}

# ── 프로젝트 루트 (스크립트 위치 기준) ─────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# ── 실행 커맨드 ──────────────────────────────────────────────────────────────
# month_number는 현재 달 기준으로 계산 (실행 시점의 월)
$RunScript = Join-Path $ProjectDir "scripts\run_daily_pipeline.ps1"

# ── run_daily_pipeline.ps1 생성 ─────────────────────────────────────────────
$PipelineScript = @"
# KAS 일간 파이프라인 실행 래퍼
Set-Location "$ProjectDir"
`$month = (Get-Date).Month
& "$PythonPath" -m src.pipeline `$month
"@

$PipelineScript | Set-Content -Path $RunScript -Encoding UTF8
Write-Host "래퍼 스크립트 생성: $RunScript"

# ── Task Scheduler 액션 ──────────────────────────────────────────────────────
$Action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$RunScript`"" `
    -WorkingDirectory $ProjectDir

# ── 트리거: 매일 RunHour:RunMinute ──────────────────────────────────────────
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "$($RunHour):$($RunMinute)"

# ── 설정 ────────────────────────────────────────────────────────────────────
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `          # 예정 시간에 PC가 꺼져 있으면 켜진 후 실행
    -RunOnlyIfNetworkAvailable `   # 네트워크 필수
    -WakeToRun                     # 슬립에서 깨워 실행

# ── 기존 태스크 제거 후 등록 ─────────────────────────────────────────────────
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 태스크 제거: $TaskName"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Description "KAS (Knowledge Animation Studio) 일간 YouTube 콘텐츠 자동 생성 파이프라인"

Write-Host ""
Write-Host "✅ Task Scheduler 등록 완료!"
Write-Host "   태스크명 : $TaskName"
Write-Host "   실행시각 : 매일 $($RunHour):$($RunMinute)"
Write-Host "   Python   : $PythonPath"
Write-Host "   프로젝트 : $ProjectDir"
Write-Host ""
Write-Host "수동 실행 테스트:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
