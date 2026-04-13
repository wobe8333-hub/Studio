# finance-monthly.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent finance-manager "월간 P&L 마감 + Slack 리포트 전송"
