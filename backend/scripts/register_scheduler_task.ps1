# Windows 작업 스케줄러 등록 스크립트
# TaskName: AIAnimationStudio_V7_Daily_10AM
# 매일 오전 10시 실행

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

$TaskName = "AIAnimationStudio_V7_Daily_10AM"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$WorkingDir = $ProjectRoot

Write-Host "=" * 70
Write-Host "Windows Scheduled Task Registration"
Write-Host "=" * 70
Write-Host ""
Write-Host "Task Name: $TaskName"
Write-Host "Working Directory: $WorkingDir"
Write-Host ""

# 기존 작업이 있으면 삭제
try {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "[INFO] Removing existing task: $TaskName"
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] Existing task removed"
    }
} catch {
    Write-Host "[INFO] No existing task found (this is OK)"
}

# 실행 커맨드 구성 (v7 운영 체인: 3단계)
# (1) 키워드 발굴
$Command1 = "cd `"$WorkingDir`" ; python -m backend.cli.run knowledge keyword-discovery --categories science,history,common_sense,economy,geography,papers --mode run --max-keywords 30"
# (2) 승인 게이트
$Command2 = "cd `"$WorkingDir`" ; python -m backend.cli.run knowledge keyword-approve --cycle latest --categories science,history,common_sense,economy,geography,papers"
# (3) 사이클 실행 (수집→파생→분류 오케스트레이션)
$Command3 = "cd `"$WorkingDir`" ; python -m backend.cli.run knowledge cycle --categories science,history,common_sense,economy,geography,papers --mode run --max-keywords-per-category 20"

# 3단계를 순차 실행 (각 단계 실패 시 즉시 중단)
$Command = "$Command1 ; if (`$LASTEXITCODE -ne 0) { exit 1 } ; $Command2 ; if (`$LASTEXITCODE -ne 0) { exit 1 } ; $Command3 ; if (`$LASTEXITCODE -ne 0) { exit 1 }"

# PowerShell 실행 액션 생성
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$Command`""

# 트리거 생성 (매일 오전 10시)
$Trigger = New-ScheduledTaskTrigger -Daily -At "10:00AM"

# 설정 생성
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# 작업 등록
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "AI Animation Studio V7 Daily Knowledge Pipeline (10AM)" `
        -Force | Out-Null
    
    Write-Host "[OK] Task registered successfully: $TaskName"
    Write-Host ""
    Write-Host "Task Details:"
    Write-Host "  - Name: $TaskName"
    Write-Host "  - Schedule: Daily at 10:00 AM"
    Write-Host "  - Working Directory: $WorkingDir"
    Write-Host ""
    Write-Host "=" * 70
    Write-Host "[OK] REGISTRATION COMPLETED"
    Write-Host "=" * 70
    exit 0
} catch {
    Write-Host "[FAIL] Failed to register task: $_"
    Write-Host ""
    Write-Host "=" * 70
    Write-Host "[FAIL] REGISTRATION FAILED"
    Write-Host "=" * 70
    exit 1
}
