---
paths:
  - .claude/agents/**
  - AGENTS.md
---

# Team Protocol — 팀 결성·통신·미션 프리셋

> on-demand 로드 — `.claude/agents/**` 또는 `AGENTS.md` 접근 시 자동 로드.

## TeamCreate 빠른 참조

**권한 3명만**: ceo · cto · qa-auditor

```
TeamCreate(team_name="{유형}-{id}")
Agent(team_name=..., name="{역할}", subagent_type="{에이전트명}")
TaskCreate(subject="{작업}")  # 팀원들이 pull 방식으로 claim
→ 완료 후: SendMessage("*", shutdown) → TeamDelete
→ data/exec/team_lifecycle.json 기록
```

팀 유형: `kas-weekly-ops` · `client-{id}` · `incident-{날짜}` · `feature-{ticket}` · `weekly-audit-{날짜}`
최대 동시 활성: 5팀

## 미션 프리셋 (빠른 소환)

| 미션 | 소환 조합 |
|---|---|
| 백엔드 기능/버그 | backend-engineer + qa-auditor |
| 프론트엔드 기능 | frontend-engineer + qa-auditor |
| UI/디자인 | ui-designer + ux-auditor |
| 보안 취약점 | qa-auditor + security-engineer → backend-engineer |
| 성능 최적화 | performance-analyst + backend-engineer |
| DB 스키마 변경 | db-architect + backend-engineer + frontend-engineer |
| 파이프라인 장애 | sre-engineer + pipeline-debugger + backend-engineer |
| MLOps 드리프트 | mlops-engineer + media-engineer |
| 대규모 리팩토링 | code-refactorer + backend-engineer |
| 릴리스 배포 | release-manager + backend-engineer |
| UX/접근성 감사 | ux-auditor → frontend-engineer/ui-designer |
| 영상 콘텐츠 감사 | content-director → backend-engineer/ui-designer |
| 수익 전략 감사 | revenue-strategist + pipeline-debugger → backend-engineer |
| 수주 프로젝트 | ceo: TeamCreate + sales-manager + project-manager + 제작팀 |
| 법률 검토 | sales-manager → legal-counsel → ceo HITL |
| BI 대시보드 | data-analyst + data-engineer |
| 프롬프트 최적화 | prompt-engineer + backend-engineer |
| 시청자 피드백 | community-manager → content-director |
| AI 신기술 탐색 | research-lead → mlops-engineer |
| YouTube 정책 | compliance-officer → ceo HITL |
| 위기 대응 | content-moderator + community-manager + ceo HITL |
| 미디어 최적화 | media-engineer + backend-engineer |
| 파트너십 | partnerships-manager → legal-counsel → ceo HITL |
| 신규 에이전트 제안 | devops-engineer → ceo HITL |
| **고위험 결정** | debate-facilitator (자동 소환) → ceo |

## Guardian → Builder 통신 포맷

```
[이슈 유형: 보안/품질/UX/수익/법률/컴플라이언스]
파일: {경로:줄번호} | 심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향}
수정 담당: {에이전트명}
```

## cto → 기술 미션팀 결성 예시

```python
TeamCreate(team_name="incident-2026-04-15")
Agent(team_name="incident-...", name="sre", subagent_type="sre-engineer")
Agent(team_name="incident-...", name="debugger", subagent_type="pipeline-debugger")
Agent(team_name="incident-...", name="backend", subagent_type="backend-engineer")
TaskCreate(subject="Step08 3회 연속 실패 원인 분석 + 핫픽스")
```
