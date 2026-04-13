# register_all.ps1 - Loomix v10.0 Windows Task Scheduler batch registration
# Usage: Set-ExecutionPolicy Bypass -Scope Process -Force; .\scripts\cron\register_all.ps1

$kasRoot = $env:KAS_ROOT
if (-not $kasRoot) {
    $kasRoot = (Get-Location).Path
    Write-Host "KAS_ROOT not set - using current directory: $kasRoot"
}

$pythonExe = if ($env:PYTHON_EXECUTABLE) { $env:PYTHON_EXECUTABLE } else { "py" }
$jobsDir = "$kasRoot\scripts\cron\jobs"

# Create Loomix folder in Task Scheduler
try {
    $taskService = New-Object -ComObject Schedule.Service
    $taskService.Connect()
    $rootFolder = $taskService.GetFolder("\")
    try { $rootFolder.CreateFolder("Loomix") | Out-Null } catch {}
} catch {}

# --- Daily / Weekly tasks (New-ScheduledTaskTrigger supported) ---
function Register-PeriodicJob {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Trigger,
        [string]$Description
    )

    $triggerParts = $Trigger -split " "
    $scheduleType = $triggerParts[0]

    $taskTrigger = switch ($scheduleType) {
        "Daily" {
            $time = [datetime]::ParseExact($triggerParts[1], "HH:mm", $null)
            New-ScheduledTaskTrigger -Daily -At $time
        }
        "Weekly" {
            $day  = $triggerParts[1]
            $time = [datetime]::ParseExact($triggerParts[2], "HH:mm", $null)
            New-ScheduledTaskTrigger -Weekly -DaysOfWeek $day -At $time
        }
        default { $null }
    }

    if (-not $taskTrigger) {
        Write-Host "  SKIP (unsupported trigger type): $Trigger"
        return
    }

    $action = New-ScheduledTaskAction `
        -Execute $pythonExe `
        -Argument "`"$ScriptPath`"" `
        -WorkingDirectory $kasRoot

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable

    $fullTaskName = "Loomix\$TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath "\Loomix\" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName $fullTaskName `
        -Action $action `
        -Trigger $taskTrigger `
        -Settings $settings `
        -Description "Loomix v10.0 - $Description" `
        -RunLevel Highest `
        -Force | Out-Null

    Write-Host "  OK Loomix\$TaskName ($Trigger)"
}

# --- Monthly tasks (schtasks.exe - New-ScheduledTaskTrigger has no -Monthly) ---
function Register-MonthlyJob {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [int]$Day,
        [string]$Time,
        [string]$Description
    )

    $fullTaskName = "Loomix\$TaskName"

    # Remove existing task first
    schtasks /Delete /TN $fullTaskName /F 2>$null | Out-Null

    # Register monthly task via schtasks.exe
    $result = schtasks /Create `
        /TN $fullTaskName `
        /TR "$pythonExe `"$ScriptPath`"" `
        /SC MONTHLY `
        /D $Day `
        /ST $Time `
        /F `
        /RL HIGHEST 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK Loomix\$TaskName (Monthly $Day $Time)"
    } else {
        Write-Host "  ERROR: $fullTaskName - $result"
    }
}

Write-Host "=== Loomix v10.0 Cron Jobs Registration ==="

# Daily jobs
Register-PeriodicJob "compliance-daily"   "$jobsDir\compliance-daily.ps1"   "Daily 09:00"         "compliance-officer YouTube policy audit"
Register-PeriodicJob "sre-daily"          "$jobsDir\sre-daily.ps1"          "Daily 10:00"         "sre-engineer Sentry 24h error summary"
Register-PeriodicJob "community-daily"    "$jobsDir\community-daily.ps1"    "Daily 18:00"         "community-manager 7ch comment digest"
Register-PeriodicJob "finance-daily"      "$jobsDir\finance-daily.ps1"      "Daily 19:00"         "finance-manager API cost daily report"
Register-PeriodicJob "daily-digest"       "$jobsDir\daily-digest.ps1"       "Daily 18:30"         "daily_digest.py Slack notification"

# Weekly jobs
Register-PeriodicJob "performance-weekly" "$jobsDir\performance-weekly.ps1" "Weekly Monday 10:00" "performance-analyst agent KPI review"
Register-PeriodicJob "revenue-weekly"     "$jobsDir\revenue-weekly.ps1"     "Weekly Monday 14:00" "revenue-strategist scorer rerun"

# Monthly jobs (schtasks.exe)
Register-MonthlyJob  "finance-monthly"    "$jobsDir\finance-monthly.ps1"    1  "09:00" "finance-manager PL monthly close"
Register-MonthlyJob  "ceo-monthly"        "$jobsDir\ceo-monthly.ps1"        1  "11:00" "ceo monthly management report draft"

Write-Host ""
Write-Host "=== Done. Current Loomix task list ==="
Get-ScheduledTask -TaskPath "\Loomix\" -ErrorAction SilentlyContinue |
    Select-Object TaskName, State |
    Format-Table -AutoSize
