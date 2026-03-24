# fix_scheduler_task.ps1
# Scheduler Action을 run_v7_scheduled.ps1로 단일화하고 Start In을 레포 루트로 교정

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "[FIX][FAIL] This script must be run as Administrator."
    exit 41
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$taskName = "AIAnimationStudio_V7_Daily_10AM"
$repoRoot = $projectRoot   # Start In

$ssotPath = Join-Path $projectRoot "data\knowledge_v1_store"
if (-not (Test-Path $ssotPath)) {
    Write-Host "[SSOT][FAIL] missing data\knowledge_v1_store"
    exit 10
}

$dataRuns = Join-Path $projectRoot "data\runs"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupXml = Join-Path $dataRuns ("scheduler_backup_{0}.xml" -f $ts)

Write-Host "[FIX] ProjectRoot (repo root): $repoRoot"
Write-Host "[FIX] TaskName: $taskName"

New-Item -ItemType Directory -Force -Path $dataRuns | Out-Null

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop

# A) Backup
Export-ScheduledTask -TaskName $taskName | Out-File -FilePath $backupXml -Encoding UTF8
Write-Host "[FIX] Backup: $backupXml"

# B) Capture existing principal (to preserve highest privileges if set)
$principal = $task.Principal

# C) Unregister existing task
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false

# D) Register new task pointing to run_v7_scheduled.ps1
$runScheduledPath = Join-Path $projectRoot "backend\scripts\run_v7_scheduled.ps1"
if (-not (Test-Path $runScheduledPath)) {
    Write-Host "[FIX][FAIL] run_v7_scheduled.ps1 not found at $runScheduledPath"
    exit 42
}

$execute = "powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runScheduledPath`""

Write-Host "[FIX] New Execute: $execute"
Write-Host "[FIX] New Arguments: $arguments"
Write-Host "[FIX] New WorkingDirectory: $repoRoot"

$actionNew = New-ScheduledTaskAction -Execute $execute -Argument $arguments -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At "10:00AM"
if ($principal) {
    # Try to keep highest privileges if originally configured
    try { $principal.RunLevel = "Highest" } catch { }
    Register-ScheduledTask -TaskName $taskName -Action $actionNew -Trigger $trigger -Principal $principal -Description "AI Animation Studio V7 Daily Knowledge Pipeline (10AM)" | Out-Null
} else {
    Register-ScheduledTask -TaskName $taskName -Action $actionNew -Trigger $trigger -Description "AI Animation Studio V7 Daily Knowledge Pipeline (10AM)" | Out-Null
}

# D) Verify Task configuration via schtasks
$query = schtasks /Query /TN $taskName /V /FO LIST 2>$null
if (-not $query) {
    Write-Host "[FIX][FAIL] schtasks query failed for $taskName"
    exit 42
}

$expectedCmd = "$execute $arguments"
$expectedStartIn = $repoRoot

if ($query -notmatch [regex]::Escape($expectedCmd)) {
    Write-Host "[FIX][FAIL] Task 'Task To Run' does not match expected: $expectedCmd"
    exit 42
}
if ($query -notmatch [regex]::Escape($expectedStartIn)) {
    Write-Host "[FIX][FAIL] Task 'Start In' does not match expected: $expectedStartIn"
    exit 42
}

Write-Host "[FIX] Scheduler task updated successfully."
exit 0
