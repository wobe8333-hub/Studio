# KAS 자율 기동 -- Windows 작업 스케줄러 등록 스크립트
# 사용법: .\scripts\register_autonomous_task.ps1
# 효과:  매일 17:00 에 Claude Code 가 '/mission autorun' 을 실행 -> KAS 상태 자동 점검
# 제거:  Unregister-ScheduledTask -TaskName "KAS-Mission-Controller" -Confirm:$false

$TaskName = "KAS-Mission-Controller"
$KasRoot  = (Split-Path $PSScriptRoot) -replace "\\", "/"

# claude CLI 경로 탐색 (PowerShell 5.1 호환)
$ClaudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if (-not $ClaudeCmd) {
    Write-Error "[ERROR] 'claude' CLI 를 찾을 수 없습니다. claude --version 으로 설치를 확인하세요."
    exit 1
}
$ClaudeExe = $ClaudeCmd.Source

Write-Host "[INFO] Claude 경로: $ClaudeExe"
Write-Host "[INFO] KAS 루트:    $KasRoot"

$Action = New-ScheduledTaskAction `
    -Execute    $ClaudeExe `
    -Argument   "--print '/mission autorun'" `
    -WorkingDirectory $KasRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At "17:00"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -RunLevel  Limited `
    -Force | Out-Null

Write-Host ""
Write-Host "[OK] '$TaskName' 등록 완료"
Write-Host "     - 실행 시각: 매일 17:00"
Write-Host "     - 작업 디렉토리: $KasRoot"
Write-Host ""
Write-Host "확인 명령: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "즉시 실행: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "제   거: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
