# ceo-monthly.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent ceo "월간 경영 보고 초안 생성: 매출·KPI·비용·다음달 전략 data/exec/monthly_report.json"
