# compliance-daily.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent compliance-officer "YouTube 정책 일일 감사 실행: 7채널 콘텐츠 체크 + data/compliance/daily_audit.json 갱신"
