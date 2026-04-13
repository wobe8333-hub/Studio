# daily-digest.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

python scripts/daily_digest.py
