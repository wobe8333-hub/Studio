---
paths:
  - .claude/agents/**
  - AGENTS.md
---

# Agent Teams — 파일 소유권 + 팀 구조 (on-demand)

> 상세 조직도·미션 프리셋·Anti-Patterns → AGENTS.md 참고

## 파일 소유권 (v8.0)

| 에이전트 | 소유 경로 | 금지 경로 |
|----------|----------|----------|
| backend-engineer | src/, tests/, scripts/ (migrations 제외) | web/ |
| frontend-engineer | web/app/, web/lib/, web/hooks/, web/components/(로직) | src/, globals.css |
| ui-designer | web/app/globals.css, web/public/, assets/thumbnails/ | src/, tests/ |
| devops-engineer | .claude/, CLAUDE.md, AGENTS.md, docs/, .github/, scripts/ (migrations 제외) | src/step*, web/app/ |
| qa-auditor | Read-only 감사 전용 | Write, Edit 금지 |
| ux-auditor | Read-only 감사 전용 | Write, Edit 금지 |
| content-director | Read-only 영상 콘텐츠 감사 | Write, Edit 금지 |
| performance-analyst | Read-only 분석 전용 | Write, Edit 금지 |
| pipeline-debugger | Read-only 파이프라인 분석 | Write, Edit 금지 |
| revenue-strategist | Read-only 수익 전략 감사 | Write, Edit 금지 |
| legal-counsel | Read-only 법률 검토 · data/legal/ 단독 | Edit 금지 |
| cto | 조율 전용 | Write, Edit 금지 |
| ceo | 조율 전용 | Write, Edit 금지 |
| db-architect | scripts/supabase_schema.sql, scripts/migrations/, web/lib/types.ts | src/, web/app/ |
| code-refactorer | src/ 리팩토링 (worktree) | web/, tests/ 삭제, src/step08/__init__.py |
| release-manager | CHANGELOG.md (단독), git tag | src/step*, web/app/ |
| sales-manager | data/sales/ | src/, web/ |
| project-manager | data/pm/ | src/, web/ |
| marketing-manager | data/marketing/ | src/, web/ |
| customer-support | data/cs/ | src/, web/ |
| finance-manager | data/finance/ | src/, web/ |
| data-analyst | data/bi/ (단독) | src/, web/, data/global/ |
| prompt-engineer | src/step*/prompts.py, data/prompts/ | src/ 로직 코드, web/ |
| sre-engineer | data/sre/ (Read-only) | Write, Edit 금지 |
| mlops-engineer | data/mlops/, assets/lora/ (worktree) | data/global/, web/ |
| security-engineer | data/security/audit/ (Read-only) | Write, Edit 금지 |
| data-engineer | data/etl/, scripts/sync_to_supabase.py (worktree) | src/ 로직, web/ |
| community-manager | data/community/ (Read-only) | Write, Edit 금지 |
| research-lead | data/research/ (Read-only, plan mode) | Write, Edit 금지 |

## TeamCreate 권한

**TeamCreate 허가 3명만**: ceo · cto · qa-auditor

팀 유형:
- `kas-weekly-ops` — 상설팀 (월요일 생성, 일요일 종료)
- `client-{id}` / `incident-{날짜}` / `feature-{ticket}` — 동적 미션팀
- `weekly-audit-{날짜}` — 감사팀

최대 동시 활성: 5팀 (상설1 + 미션3 + 감사1)

## v8.0 신규 에이전트 배치

| 부서 | 신규 | 역할 |
|------|------|------|
| Executive | research-lead | AI 신기술 탐색·POC (read-only, plan) |
| Engineering | mlops-engineer | SD XL/LoRA/ElevenLabs 모델 운영 (worktree) |
| Platform Ops | sre-engineer | Sentry 알람·런타임 대응 (read-only) |
| Quality | security-engineer | OAuth 회전·RLS 런타임 보안 (read-only) |
| Growth&Brand | community-manager | 7채널 시청자 커뮤니티 (read-only) |
| Data Intelligence | data-engineer | Step05 ETL·Supabase idempotency (worktree) |
