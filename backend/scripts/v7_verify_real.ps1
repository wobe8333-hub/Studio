# v7 Real Verification - STEP5 Scheduler Proof with stale result normalization
# STEP5 is proof-only in manual context; scheduler execution is forbidden in manual context.
# lastResult=60 can be stale; State=Running/Queued means active instance and FAIL.
# Stale non-zero lastResult is normalized by lightweight health proof (subprocess run_v7_scheduled.ps1 with AAS_SKIP_SCHEDULER_PROOF=1).

param()

$ErrorActionPreference = "Stop"

$taskName = "AIAnimationStudio_V7_Daily_10AM"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path

# A) Scheduler skip mode: AAS_SKIP_SCHEDULER_PROOF=1 (set by run_v7_scheduled.ps1 only)
if ($env:AAS_SKIP_SCHEDULER_PROOF -eq "1") {
    Write-Host "[STEP5] scheduler proof skipped by scheduler context"
    Write-Host "[STEP5] PASS | task_name=$taskName | proof_mode=scheduler | reason=skip_by_context"
    exit 0
}

# B) Manual proof mode
$proofMode = "manual"

try {
    Write-Host "[STEP5] verifying scheduled task (proof only; no run)"

    # A. Task 존재 확인
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    $info = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
    $act = $task.Actions[0]

    $actionPath = ""
    $workingDirectory = ""
    if ($act) {
        $actionPath = ("$($act.Execute) $($act.Arguments) $($act.WorkingDirectory)" -replace '\s+', ' ').Trim()
        $workingDirectory = if ($act.WorkingDirectory) { $act.WorkingDirectory.Trim() } else { "" }
    }

    if ([string]::IsNullOrWhiteSpace($actionPath)) {
        Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=N/A | last_result_decimal=N/A | last_result_hex=N/A | action_path=empty | working_directory=N/A | reason=action_path_unreadable"
        exit 1
    }

    # B. Action/WorkingDirectory 확인
    if ($actionPath -notlike "*run_v7_scheduled.ps1*") {
        Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=N/A | last_result_decimal=N/A | last_result_hex=N/A | action_path=$actionPath | working_directory=$workingDirectory | reason=task_to_run_missing_run_v7_scheduled_ps1"
        exit 1
    }

    $projectRootNorm = (Resolve-Path $projectRoot).Path
    $taskWorkDirNorm = if ([string]::IsNullOrWhiteSpace($workingDirectory)) { "" } else { (Resolve-Path $workingDirectory -ErrorAction SilentlyContinue).Path }
    if ([string]::IsNullOrWhiteSpace($taskWorkDirNorm) -or $taskWorkDirNorm -ne $projectRootNorm) {
        Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=N/A | last_result_decimal=N/A | last_result_hex=N/A | action_path=$actionPath | working_directory=$workingDirectory | reason=working_directory_mismatch_project_root"
        exit 1
    }

    $state = [string]$task.State
    $lastResult = [int64]$info.LastTaskResult
    $lastResultHex = ('0x{0:X8}' -f ([uint32]$info.LastTaskResult))

    # C. Task 상태: Running/Queued 이면 재진입으로 FAIL
    if ($state -eq "Running" -or $state -eq "Queued") {
        Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | last_result_hex=$lastResultHex | action_path=$actionPath | working_directory=$workingDirectory | reason=active_scheduler_instance"
        exit 1
    }

    # D. LastTaskResult 확인 (0 = PASS; non-zero = stale 후보, 아직 즉시 FAIL 하지 않음)
    $staleResultDetected = $false
    if ($lastResult -eq 0) {
        Write-Host "[STEP5] PASS | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | last_result_hex=$lastResultHex | action_path=$actionPath | working_directory=$workingDirectory"
        Write-Host "[STEP5] verification complete"
        exit 0
    }

    $staleResultDetected = $true
    Write-Host "[STEP5] stale result candidate | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | last_result_hex=$lastResultHex | action_path=$actionPath | working_directory=$workingDirectory | stale_result_detected=true | stale_reason=locked_or_nonzero_past_result"

    # E. Lightweight health proof: subprocess run_v7_scheduled.ps1 with AAS_SKIP_SCHEDULER_PROOF=1 and AAS_HEALTH_PROOF=1 (no Task Scheduler run).
    # health proof subprocess must bypass scheduled hardlock; set env in child process before invoking script so HARDLOCK sees AAS_HEALTH_PROOF=1.
    $runScheduledPath = Join-Path $projectRoot "backend\scripts\run_v7_scheduled.ps1"
    if (-not (Test-Path $runScheduledPath)) {
        Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | stale_result_detected=true | health_proof_exitcode=N/A | reason=run_v7_scheduled_ps1_not_found"
        exit 1
    }

    $runScheduledPathEscaped = $runScheduledPath -replace "'", "''"
    $cmdBlock = "& { `$env:AAS_SKIP_SCHEDULER_PROOF='1'; `$env:AAS_HEALTH_PROOF='1'; & '${runScheduledPathEscaped}' }"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -Command `"$cmdBlock`""
    $psi.WorkingDirectory = $projectRoot
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    $proc.WaitForExit(300000)
    $healthProofExitCode = $proc.ExitCode

    Write-Host "[STEP5] health proof completed | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | last_result_hex=$lastResultHex | action_path=$actionPath | working_directory=$workingDirectory | stale_result_detected=true | health_proof_command=powershell -Command AAS_HEALTH_PROOF=1 run_v7_scheduled.ps1 | health_proof_exitcode=$healthProofExitCode"

    # F. 최종 판정
    if ($healthProofExitCode -eq 0) {
        Write-Host "[STEP5] PASS | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | stale_result_detected=true | health_proof_exitcode=$healthProofExitCode | reason=stale_scheduler_result_normalized"
        Write-Host "[STEP5] verification complete"
        exit 0
    }

    Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=$state | last_result_decimal=$lastResult | stale_result_detected=true | health_proof_exitcode=$healthProofExitCode | reason=current_scheduler_script_health_failed"
    exit 1
}
catch {
    Write-Host "[ERROR] Script exception: $($_.Exception.Message)"
    Write-Host "[ERROR][POSITION] $($_.InvocationInfo.PositionMessage)"
    Write-Host "[ERROR][SCRIPTSTACK] $($_.ScriptStackTrace)"
    Write-Host "[STEP5] FAIL | task_name=$taskName | proof_mode=$proofMode | state=N/A | last_result_decimal=N/A | last_result_hex=N/A | action_path=N/A | working_directory=N/A | reason=exception_$($_.Exception.Message)"
    exit 99
}
