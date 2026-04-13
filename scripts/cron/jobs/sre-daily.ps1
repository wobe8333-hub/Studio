# sre-daily.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent sre-engineer "Sentry 최근 24시간 에러 요약 + 조치 필요 항목 data/sre/daily_report.json 기록"
