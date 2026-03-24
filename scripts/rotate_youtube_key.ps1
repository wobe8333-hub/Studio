# ================================
# rotate_youtube_key.ps1 (PS 5.1 SAFE / NO KEY LEAK)
# ================================
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host '[STEP] KEY-ROTATE-AFTER - START' -ForegroundColor Cyan

# 항상 repo root로 이동(스케줄러/상대경로 사고 방지)
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

# 1) backend/.env 존재 확인(키 값 출력 금지)
$envPath = Join-Path $repoRoot 'backend\.env'
if (-not (Test-Path $envPath)) {
  Write-Host '[FAIL] backend/.env not found. Put YOUTUBE_API_KEY first.' -ForegroundColor Red
  exit 1
}
Write-Host '[OK] backend/.env found' -ForegroundColor Green

# 2) 과거 산출물 정화(youtube_error_*.json / youtube_integration_*.json) - 파서 안전 버전
Write-Host '[STEP] sanitize legacy youtube jsons' -ForegroundColor Cyan
$targets = Get-ChildItem -Path $repoRoot -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'youtube_(error|integration).*\.json' }

foreach ($f in $targets) {
  try {
    $txt = Get-Content -LiteralPath $f.FullName -Raw -ErrorAction Stop

    # key= 파라미터 값 제거 (PS 파서 충돌 방지: & 미사용)
    $txt = $txt -replace 'key=[^ \t\r\n"''>]+', 'key=***REDACTED***'

    # 실제 토큰 형태 제거
    $txt = $txt -replace 'AIza[0-9A-Za-z\-_]{20,}', 'AIza***REDACTED***'

    Set-Content -LiteralPath $f.FullName -Value $txt -Encoding UTF8
    Write-Host ("[CLEAN] " + $f.FullName) -ForegroundColor DarkGreen
  } catch {
    Write-Host ("[WARN] Failed to sanitize: " + $f.FullName + " :: " + $_.Exception.Message) -ForegroundColor Yellow
  }
}

# 3) health check
Write-Host '[STEP] verify_repo_health' -ForegroundColor Cyan
python -m backend.scripts.verify_repo_health
if ($LASTEXITCODE -ne 0) {
  Write-Host '[FAIL] verify_repo_health failed' -ForegroundColor Red
  exit 1
}
Write-Host '[OK] verify_repo_health PASS' -ForegroundColor Green

# 4) live 실행
Write-Host '[STEP] v7-run --mode live' -ForegroundColor Cyan
python -m backend.cli.run knowledge v7-run --mode live --max-keywords-per-category 80 --daily-total-limit 400
if ($LASTEXITCODE -ne 0) {
  Write-Host '[FAIL] v7-run live failed' -ForegroundColor Red
  exit 1
}
Write-Host '[OK] v7-run live PASS' -ForegroundColor Green

# 5) SSOT에서 youtube 포함 여부 확인 (PowerShell heredoc 금지 → python -c)
Write-Host '[STEP] SSOT source_counts check' -ForegroundColor Cyan
python -c "import json,glob,os,collections; p=max(glob.glob('data/knowledge_v1_store/ssot/*/daily_keywords_gate1.json'), key=os.path.getmtime); d=json.load(open(p,'r',encoding='utf-8')); c=collections.Counter([r.get('source','?') for r in d.get('keywords',[])]); print('source_counts=',dict(c)); import sys; sys.exit(0 if 'youtube' in c else 1)"
if ($LASTEXITCODE -ne 0) {
  Write-Host '[WARN] youtube source missing in SSOT' -ForegroundColor Yellow
  exit 1
}

Write-Host '[PASS] KEY-ROTATE-AFTER verification complete' -ForegroundColor Green
exit 0
