$ErrorActionPreference = "Stop"

# HARDLOCK: prevent real concurrent v7_verify_real.ps1 runs only.
# health proof subprocess must bypass scheduled hardlock.
# hardlock must prevent real concurrent runs, not parent-child proof execution.
# exit 60 remains reserved for real re-entrant/concurrent execution only.
$healthProofFlag = if ($env:AAS_HEALTH_PROOF -eq "1") { "1" } else { "0" }

if ($env:AAS_HEALTH_PROOF -eq "1") {
    Write-Host "[HARDLOCK] bypassed_by_health_proof=1 | mode=scheduled | health_proof_flag=$healthProofFlag | lock_check_enabled=false | detected_competitor_count=N/A | reason=health_proof_subprocess"
} else {
    $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -match "v7_verify_real\.ps1" }
    $detectedCompetitorCount = if ($running) { @($running).Count } else { 0 }

    if ($detectedCompetitorCount -gt 0) {
        Write-Host "[HARDLOCK] Already running | mode=scheduled | health_proof_flag=$healthProofFlag | lock_check_enabled=true | detected_competitor_count=$detectedCompetitorCount | reason=concurrent_verify_detected"
        exit 60
    }
}

powershell -ExecutionPolicy Bypass -File .\backend\scripts\bootstrap_venv.ps1
if ($LASTEXITCODE -ne 0) { exit 33 }

$env:AAS_VERIFY_MODE = "OPS"
$env:AAS_SKIP_SCHEDULER_PROOF = "1"

powershell -ExecutionPolicy Bypass -File .\backend\scripts\v7_verify_real.ps1
$code = $LASTEXITCODE
exit $code