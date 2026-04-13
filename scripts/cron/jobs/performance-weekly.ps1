# performance-weekly.ps1 — Loomix v10.0 cron job
# KAS_ROOT 환경변수 필요
Set-Location :KAS_ROOT

claude --agent performance-analyst "에이전트별 주간 KPI 리뷰: eval 점수 + 호출 빈도 + 비용 data/exec/agent_performance/ 기록"
