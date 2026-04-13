# community-daily.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent community-manager "7채널 댓글 digest 생성 + content-director 루프백 SendMessage"
