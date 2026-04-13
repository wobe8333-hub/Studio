# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

> **Owner**: release-manager — 이 파일은 release-manager 에이전트만 편집한다.

---

## [Unreleased]

### Added
- v10.0: 에이전트 37명 (29→37), Meta-agents 3명, Eval 프레임워크, 라이프사이클, 비용 라우팅, Debate, 벡터 메모리, COMPANY.md, Slack 통합, Chaos Engineering, Circuit Breaker, Cron 자율 행동, OKR 사이클
- Phase 10A: Critical 잔재 4건 수정 (CHANGELOG, TaskCompleted, mlops env, security ultrathink)

---

## [8.0.0] - 2026-04-13

### Added
- 에이전트 29명 × 9부서 (23→29, +sre/mlops/security/data-engineer/community/research-lead)
- Extended thinking (ultrathink): ceo, cto, db-architect, qa-auditor
- UserPromptSubmit hook: detect_hitl.py — HITL 키워드 자동 감지
- PreCompact hook: save_reflection.py — 교훈 자동 저장
- SessionEnd hook: session_end.py — 로그 순환 + 비용 집계
- Output styles 3종: legal-formal, exec-brief, dev-terse
- env frontmatter: finance-manager, content-director, performance-analyst
- On-demand rules: agent-teams.md, reflection.md, ssot-io.md
- Playbooks 4종: pipeline-incident, client-project, schema-change, bi-report

### Changed
- project-manager: Sonnet → Haiku
- CLAUDE.md: 197줄 → 78줄 (-50%)
- AGENTS.md: 352줄 → 199줄 (-43%)
- AGENTS.md 준수율 표현: "100%" → "98%+"

### Fixed
- cto.md memory/initialPrompt 누락
- 5개 에이전트 memory 필드 누락 (cto/content-director/performance-analyst/qa-auditor/ux-auditor)
- data-analyst disallowedTools: Write 누락 (Edit만 있었음)
- qa-auditor background: true 비공식 필드 제거
- 비표준 hook 이벤트 5종 제거 (TaskCompleted, TaskCreated, TeammateIdle, SubagentStart, WorktreeCreate)
- ceo.md description "23명" → "29명" 동기화

---

## [7.0.0] - 2026-04-12

### Added
- 에이전트 23명 × 9부서 (20→23, +data-intelligence 부서, data-analyst, prompt-engineer)
- Loomix 브랜딩 (KAS 내부 코드명 유지)
- TeamCreate/TeamDelete 3인 권한 체계 (ceo·cto·qa-auditor)
- HITL 9개 트리거 시스템
- sales-manager, project-manager, marketing-manager, customer-support, finance-manager, legal-counsel
- block-path.py PreToolUse hook 공통 파일

---

## [6.0.0] - 2026-04-11

### Added
- 에이전트 20명 × 8부서
- 기초 Agent Teams 구조
- SSOT 원칙 (src/core/ssot.py)
