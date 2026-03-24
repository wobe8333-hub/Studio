param()
$ErrorActionPreference="Stop"

function Invoke-PythonModule([string]$label, [string[]]$moduleArgs) {
  # moduleArgs 예: @("-m","backend.scripts.import_sanity")
  $cmdLine = "python " + ($moduleArgs -join " ")
  Write-Host ("RUN {0}: {1}" -f $label, $cmdLine)

  $p = Start-Process -FilePath "python" -ArgumentList $moduleArgs -NoNewWindow -Wait -PassThru
  if ($p.ExitCode -ne 0) {
    Write-Host ("FAIL {0} (exit={1})" -f $label, $p.ExitCode)
    exit 1
  }

  Write-Host ("PASS {0}" -f $label)
}

Invoke-PythonModule "IMPORT_SANITY" @("-m","backend.scripts.import_sanity")
Invoke-PythonModule "VERIFY_RUNS_RELEASE" @("-m","backend.scripts.verify_runs","--mode","release")

exit 0
