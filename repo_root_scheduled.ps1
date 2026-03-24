Set-Location "C:\Users\조찬우\Desktop\AI_Animation_Stuidio"
$env:PYTHONPATH = "C:\Users\조찬우\Desktop\AI_Animation_Stuidio"
$lockFile = "C:\Users\조찬우\Desktop\AI_Animation_Stuidio\.kas_running.lock"
if (Test-Path $lockFile) { Write-Error "이미 실행 중 (exit 60)"; exit 60 }
Set-Content $lockFile "running"
try {
    if (!(Test-Path "C:\Users\조찬우\Desktop\AI_Animation_Stuidio\data\global\channel_registry.json")) {
        .venv\Scripts\python.exe -m src.step00.global_init
        if ($LASTEXITCODE -ne 0) { throw "STEP00_FAIL" }
    }
    $month = [int](Get-Date -Format "M")
    .venv\Scripts\python.exe -m src.pipeline $month
    if ($LASTEXITCODE -ne 0) { throw "PIPELINE_FAIL" }
    exit 0
}
catch { Write-Error "FAIL: $_"; exit 1 }
finally { Remove-Item $lockFile -Force -ErrorAction SilentlyContinue }
