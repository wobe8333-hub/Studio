# UTF-8 인코딩
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$taskName = "AIAnimationStudio_V7_Daily_10AM"
$ps1Path = Join-Path $projectRoot "backend\scripts\run_v7_scheduled.ps1"

if (-not (Test-Path $ps1Path)) {
    Write-Error "run_v7_scheduled.ps1 not found: $ps1Path"
    exit 1
}

# 기존 작업 삭제 (있으면)
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Output "Existing task removed: $taskName"
}

# 새 작업 생성 (AllowStartIfOnBatteries, StartWhenAvailable 등 적용)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$ps1Path`"" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At 10:00AM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "AI Animation Studio V7 Daily (10:00 AM)" | Out-Null

# 등록 후 출력 및 검증
Write-Output "Scheduled task registered: $taskName"
Write-Output "Execute: powershell.exe"
Write-Output "Arguments: -ExecutionPolicy Bypass -NoProfile -File `"$ps1Path`""
Write-Output "WorkingDirectory: $projectRoot"
Write-Output "Principal UserId: $($principal.UserId)"
Write-Output "Principal LogonType: $($principal.LogonType)"
Write-Output "Principal RunLevel: $($principal.RunLevel)"
Write-Output "Settings AllowStartIfOnBatteries: True (requested)"
Write-Output "Settings DontStopIfGoingOnBatteries: True (requested)"
Write-Output "Settings StartWhenAvailable: True (requested)"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
$taskSettings = $task.Settings

Write-Output "--- Verification ---"
Write-Output "TaskName: $taskName"
Write-Output "State: $($task.State)"
$act = $task.Actions[0]
Write-Output "Action Execute: $($act.Execute)"
Write-Output "Action Arguments: $($act.Arguments)"
Write-Output "Settings DisallowStartIfOnBatteries: $($taskSettings.DisallowStartIfOnBatteries)"
Write-Output "Settings StartWhenAvailable: $($taskSettings.StartWhenAvailable)"
Write-Output "Settings MultipleInstances: $($taskSettings.MultipleInstances)"

if ($taskSettings.DisallowStartIfOnBatteries -eq $true) {
    Write-Error "[FAIL] Task was registered with DisallowStartIfOnBatteries=True; expected False (AllowStartIfOnBatteries)."
    exit 1
}
if ($taskSettings.StartWhenAvailable -eq $false) {
    Write-Error "[FAIL] Task was registered with StartWhenAvailable=False; expected True."
    exit 1
}

Write-Output "[PASS] Task registered and settings verified."
exit 0
