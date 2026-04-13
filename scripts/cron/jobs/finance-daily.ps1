# finance-daily.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent finance-manager "API 비용 일일 집계: data/ops/agent_cost.json → data/finance/daily_{date}.json"
