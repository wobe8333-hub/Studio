---
name: Agent Teams 구성 현황
description: KAS Agent Teams v3 — 현재 활성 에이전트 파일 목록 및 역할 분담 요약
type: project
---

## Agent Teams v3 구성 (2026-04-11 기준)

`.claude/agents/` 디렉토리에 존재하는 에이전트 정의 파일:

| 파일 | 에이전트명 | 모델 | 소유 영역 |
|------|----------|------|----------|
| `backend-dev.md` | backend-dev | sonnet | `src/` 전체 |
| `frontend-dev.md` | frontend-dev | sonnet | `web/` 전체 |
| `quality-reviewer.md` | quality-reviewer | sonnet | Read-only, `tests/` |
| `infra-ops.md` | infra-ops | sonnet | `scripts/`, 쿼터, 환경변수 |
| `mission-controller.md` | mission-controller | sonnet | 오케스트레이션 전용 |
| `doc-keeper.md` | doc-keeper | sonnet | 문서화 전용 |
| `test-engineer.md` | test-engineer | sonnet | `tests/` 소유, Vitest/pytest, maxTurns=40 |
| `security-sentinel.md` | security-sentinel | opus | 보안 감시 Read-only, maxTurns=30 |
| `performance-profiler.md` | performance-profiler | sonnet | Read-only 성능 분석, plan 모드, maxTurns=25 |
| `a11y-expert.md` | a11y-expert | sonnet | `web/` 접근성 속성 추가, playwright MCP, maxTurns=25 |
| `docs-architect.md` | docs-architect | haiku | `docs/`, CHANGELOG, README, maxTurns=20 |
| `db-architect.md` | db-architect | sonnet | `scripts/supabase_schema.sql`, 마이그레이션, maxTurns=25 |
| `refactoring-surgeon.md` | refactoring-surgeon | sonnet | God Module 분해, 의존성 정리, acceptEdits 모드, maxTurns=30 |
| `pipeline-debugger.md` | pipeline-debugger | sonnet | 파이프라인 Step 실패 분석, Read-only, plan 모드, maxTurns=30 |
| `video-qa-specialist.md` | video-qa-specialist | sonnet | SHA-256/해상도/자막/Shorts 검증, Read-only, plan 모드, maxTurns=20 |
| `trend-analyst.md` | trend-analyst | haiku | Step05 트렌드 수집 성능 분석, Read-only, plan 모드, maxTurns=20 |

## v3 추가 사항

**test-engineer**: quality-reviewer와 역할 분리. tests/ 디렉토리 단독 소유, TDD 강제, 커버리지 목표 Python 90% / 웹 80%. playwright MCP 포함.

**security-sentinel**: 기존 security-auditor를 대체. Opus 모델 사용(보안 판단 정확도), crimson 색상, OWASP Top 10 + KAS 전용 스캔 절차 포함. Write/Edit 완전 금지.

**Why:** v3에서 테스트 전담(test-engineer)과 보안 전담(security-sentinel)을 분리함으로써 quality-reviewer의 역할 과부하 방지 및 보안 감사의 정확도 향상.

**How to apply:** 테스트 관련 작업은 test-engineer에게, 보안 감사는 security-sentinel에게 위임. backend-dev는 두 에이전트와의 협력 인터페이스만 유지.

## 전문가 풀 B (2026-04-11 추가)

**refactoring-surgeon**: God Module 분해 전담. `src/quota/__init__.py`(598줄)와 `web/app/monitor/page.tsx`(990줄)가 주요 후보. 리팩토링 전/후 테스트 통과 필수 원칙 적용.

**pipeline-debugger**: 파이프라인 실패 분석 전용. Step08(KAS-PROTECTED) 수정 없이 진단만 수행. Gemini ResourceExhausted / FFmpeg No such file / Manim TimeoutExpired / ElevenLabs 429 패턴 포함.

**video-qa-specialist**: SHA-256 무결성 + 영상 파일 우선순위(video_narr.mp4 > video.mp4 > video_subs.mp4) + Shorts 9:16 검증. Read-only.

**trend-analyst**: Haiku 모델로 비용 효율적 Step05 분석. grade 분포(80+→auto, 60-79→review, <60→rejected) 및 Google Trends Fallback(_KEYWORD_BASELINES) 모니터링.

## 전문가 풀 C (2026-04-11 추가)

**api-designer**: RESTful API 설계 전문가. Write/Edit 금지(설계 문서만 작성), plan 모드. fs-helpers 보안 패턴(validateRunPath/validateChannelPath) 적용 검토. 설계 후 backend-dev/frontend-dev에게 구현 위임.

**release-manager**: Haiku 모델로 비용 효율적 릴리스 관리. CHANGELOG(Keep a Changelog 형식), git tag, gh pr create. pytest + npm build + security-sentinel 스캔 통과 후 릴리스 승인.

**e2e-playwright**: Playwright MCP 기반 E2E 테스트. 375px/768px 모바일 반응형, 다크모드 전환(흰색 박스 탐지), 파이프라인 트리거 흐름 검증. `web/tests/e2e/` 소유.

**cost-optimizer-agent**: Haiku 모델로 Gemini/YouTube 쿼터 사용 분석. Write/Edit 금지(읽기 전용 분석). 쿼터 80% → 경고, 95% → HITL 신호. ssot.write_json() 미사용 시 backend-dev에게 수정 위임.
