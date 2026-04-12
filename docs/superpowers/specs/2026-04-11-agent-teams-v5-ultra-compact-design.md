# Agent Teams v5 "Ultra-Compact" — 전면 재설계 스펙

> **날짜**: 2026-04-11
> **버전**: v5.0
> **이전 버전**: v4 반구현 (18개 에이전트, 9/16 frontmatter)
> **목표**: Claude Code 공식 기능 16/16 완전 활용, 12개 에이전트 토큰 최적 구성, 완전 자율 운영

---

## 1. 설계 동기

### 1.1 v4 반구현 감사 결과

| 항목 | v4 반구현 (현재) | v5 목표 | 갭 |
|------|----------------|---------|-----|
| 에이전트 수 | 18개 | **12개** | 6개 추가 통합 |
| frontmatter 활용 | 9/16 (56%) | **16/16 (100%)** | isolation, effort, background, initialPrompt 등 7개 |
| hooks 활용 | 7종 (prompt 1개 포함) | **9종 (100% command)** | prompt→command 전환, SubagentStart/WorktreeCreate 추가 |
| worktree isolation | 0% | **Builder+L3 60%** | 7개 에이전트에 적용 |
| background guardian | 0% | **1개 상시 감시** | quality-security |
| memory 3-scope | project만 | **user/project/local** | 크로스 프로젝트+임시 분리 |
| Cron/Schedule | 0% | **5개 스케줄** | 완전 자율 운영 |
| 문서 동기화 | v3.1 기준 (유령 에이전트 7개) | **v5 완전 동기화** | CLAUDE.md/AGENTS.md 재작성 |
| PreToolUse 보안 | prompt (토큰 소비) | **command (토큰 0)** | 비용 절감 |
| per-agent hooks | 4개 (22%) | **Builder 전원 (100%)** | 파일 경계 완전 강제 |

### 1.2 통합 대상 역할 중복

```
quality-reviewer  ↔ security-guardian  → OWASP 검사 완전 중복
ux-reviewer       ↔ a11y-expert       → WCAG 접근성 완전 중복
platform-ops      ↔ docs-manager      → 운영/문서 동일 도메인
api-designer      → quality-security에 흡수 (설계 리뷰)
video-qa-specialist → pipeline-debugger에 흡수 (QA 검증)
```

---

## 2. 아키텍처 — 4-Layer Dynamic Scaling (12개)

```
┌───────────────────────────────────────────────────────────────┐
│                  Layer 0: AUTONOMOUS (1)                       │
│  mission-controller — Opus, plan, effort:high, memory:user    │
│  역할: 이슈 감지, 팀 편성, 진행 조율, Reflection 교훈 누적      │
├───────────────────────────────────────────────────────────────┤
│                  Layer 1: BUILDER (3)                          │
│  python-dev  — Sonnet, auto, worktree                         │
│    소유: src/, tests/, scripts/, pyproject.toml, ruff.toml     │
│                                                               │
│  web-dev     — Sonnet, auto, worktree                         │
│    소유: web/app/, web/lib/, web/hooks/, web/components/(로직)  │
│                                                               │
│  design-dev  — Sonnet, acceptEdits                             │
│    소유: web/app/globals.css, web/public/, assets/thumbnails/  │
├───────────────────────────────────────────────────────────────┤
│                  Layer 2: GUARDIAN (2)                          │
│  quality-security — Sonnet, background, plan (Read-only)       │
│    역할: OWASP + 코드품질 + 아키텍처 + API 설계 리뷰            │
│                                                               │
│  ops-monitor     — Sonnet, acceptEdits, memory:user            │
│    소유: .claude/, CLAUDE.md, AGENTS.md, docs/, .github/       │
├───────────────────────────────────────────────────────────────┤
│                  Layer 3: SPECIALIST (6, 온디맨드)              │
│  db-architect         — Sonnet, worktree, auto                │
│  refactoring-surgeon  — Sonnet, worktree, auto                │
│  pipeline-debugger    — Sonnet, worktree, auto (+trend+QA)    │
│  performance-profiler — Sonnet, worktree, auto (Read-only)    │
│  ux-a11y             — Sonnet, plan (WCAG+UX, Read-only)      │
│  release-manager     — Haiku, auto                            │
└───────────────────────────────────────────────────────────────┘

평시: L0 + L2 = 3개 (background 포함)
미션: + L1 2~3개 + L3 2~3개 = 최대 8~9개
공식 권장(3~5명/미션)에 완전 부합
```

---

## 3. 에이전트 정의 상세 (12개)

### 3.1 Layer 0: AUTONOMOUS

#### mission-controller

```yaml
---
name: mission-controller
description: |
  KAS 자율 오케스트레이터. HITL 신호/테스트 실패/빌드 오류를 자동 감지하고
  최적 팀원 조합을 소환하여 해결. 코드를 직접 수정하지 않으며 조율에만 집중.
  Reflection 패턴으로 세션 간 교훈 누적.
model: opus
tools: Read, Glob, Grep, Bash, Agent, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet
disallowedTools: Write, Edit
maxTurns: 30
permissionMode: plan
memory: user
effort: high
color: gold
mcpServers:
  - context7
skills:
  - superpowers:brainstorming
  - superpowers:writing-plans
  - superpowers:dispatching-parallel-agents
  - superpowers:verification-before-completion
---

## 자동 감지 대상
1. `data/global/notifications/hitl_signals.json` — resolved: false 항목
2. `runs/*/manifest.json` — run_state: FAILED
3. TaskCompleted hook 실패 (pytest/build)

## 팀 편성 원칙
- 평시: L0 + L2 = 3개만 활성
- 미션 시: L1에서 2~3명 + L3에서 2~3명 소환
- L3 동시 소환 5명 초과 금지

## Reflection 패턴
미션 완료 후 교훈 추출 → agent-memory에 기록:
- 어떤 팀 편성이 효과적이었나?
- 어떤 에이전트가 maxTurns 내에 완료하지 못했나?
- 반복되는 실패 패턴이 있나?
```

### 3.2 Layer 1: BUILDER

#### python-dev

```yaml
---
name: python-dev
description: |
  KAS 백엔드+테스트 전문가. src/ 디렉토리 전체 담당 — pipeline, step 모듈,
  agents, core, quota, cache. tests/ 작성, scripts/ 유지보수도 담당.
  파이프라인 수정, 에러 전략, 에이전트 시스템 확장 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 30
permissionMode: auto
memory: project
isolation: worktree
color: red
mcpServers:
  - context7
skills:
  - superpowers:test-driven-development
  - superpowers:systematic-debugging
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import os,sys,json; p=json.loads(sys.stdin.read()).get('input',{}).get('file_path',''); sys.exit(2) if '/web/' in p.replace('\\\\','/') else sys.exit(0)\""
  SubagentStop:
    - hooks:
        - type: command
          command: "pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -15"
initialPrompt: |
  conftest.py의 Gemini mock 3단계 방어를 숙지하세요.
  테스트: pytest --ignore=tests/test_step08_integration.py 사용.
  JSON I/O는 반드시 ssot.read_json()/write_json() 사용.
  로깅은 loguru만 사용 (import logging 금지).
---

## 소유 영역
- `src/` 전체 (pipeline.py, step*/, agents/, core/, quota/, cache/)
- `tests/` 전체 (conftest.py 포함)
- `scripts/` (preflight_check.py, sync_to_supabase.py 등)
- `pyproject.toml`, `ruff.toml`, `requirements.txt`

## 교차 금지
- `web/` 디렉토리 진입 금지 (per-agent hook으로 물리적 차단)

## 자가 치유
테스트 실패 시 최대 3회 자동 수정 시도 → 실패 시 mission-controller에게 에스컬레이션.
```

#### web-dev

```yaml
---
name: web-dev
description: |
  KAS 프론트엔드+E2E 전문가. web/ 디렉토리 담당 — Next.js 16, Tailwind CSS v4,
  shadcn/ui, Supabase. 웹 페이지, API 라우트, 컴포넌트 로직, E2E 테스트 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 30
permissionMode: auto
memory: project
isolation: worktree
color: blue
mcpServers:
  - context7
  - playwright
skills:
  - superpowers:test-driven-development
  - frontend-design:frontend-design
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import os,sys,json; p=json.loads(sys.stdin.read()).get('input',{}).get('file_path','').replace('\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/', 'globals.css']) else sys.exit(0)\""
  SubagentStop:
    - hooks:
        - type: command
          command: "cd web && npm run build 2>&1 | tail -10"
initialPrompt: |
  web/CLAUDE.md를 먼저 읽으세요.
  Route Handler params는 Promise 타입 (await params).
  CSS 변수 필수: var(--card), var(--border), var(--tab-bg).
  하드코딩된 rgba(255,255,255,...) 금지 (다크모드 깨짐).
---

## 소유 영역
- `web/app/` (페이지, API 라우트)
- `web/lib/` (supabase, fs-helpers, types)
- `web/hooks/` (use-is-mobile 등)
- `web/components/` **로직 담당**: onClick, useState, useEffect, API 호출 (className/스타일은 design-dev 소유)
- `web/tests/` (E2E Playwright 테스트)
- `web/playwright.config.ts`

## 교차 금지
- `src/` 디렉토리 진입 금지
- `web/app/globals.css` 직접 수정 금지 (design-dev 소유)
- `web/public/` 직접 수정 금지 (design-dev 소유)

## 자가 치유
npm run build 실패 시 최대 3회 자동 수정 → 실패 시 에스컬레이션.
```

#### design-dev

```yaml
---
name: design-dev
description: |
  KAS UI 디자인 전문가. CSS 디자인 시스템, 에셋, Figma 연동 담당.
  globals.css 수정, 디자인 토큰 변경, 썸네일 베이스 PNG 재생성,
  컴포넌트 스타일링 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: acceptEdits
memory: project
color: pink
mcpServers:
  - figma
  - playwright
skills:
  - frontend-design:frontend-design
  - ui-ux-pro-max:ui-ux-pro-max
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import os,sys,json; p=json.loads(sys.stdin.read()).get('input',{}).get('file_path','').replace('\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/', '/tests/', '/web/lib/']) else sys.exit(0)\""
initialPrompt: |
  web/app/globals.css의 Red Light Glassmorphism 팔레트를 먼저 파악하세요.
  .dark 클래스의 Crimson Night 팔레트도 확인하세요.
  CARD_BASE 상수 패턴: background: var(--card), border: var(--border).
---

## 소유 영역
- `web/app/globals.css` (디자인 시스템 단독 소유)
- `web/public/` (에셋)
- `assets/thumbnails/` (CH1~7 베이스 PNG)
- `web/components/` (스타일링: className, Tailwind, CSS 변수)

## 교차 금지
- `src/`, `tests/`, `web/lib/` 진입 금지

## 시각적 검증
Playwright로 스크린샷 캡처 후 변경 전/후 비교 필수.
```

### 3.3 Layer 2: GUARDIAN

#### quality-security

```yaml
---
name: quality-security
description: |
  KAS 코드 품질+보안 통합 감사. OWASP Top 10 기반 취약점 스캔, 코드 품질 검증,
  아키텍처 리뷰, API 설계 리뷰를 담당. 코드를 직접 수정하지 않고
  발견 이슈는 SendMessage로 해당 Builder에게 전달.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage
disallowedTools: Write, Edit
maxTurns: 25
permissionMode: plan
memory: project
background: true
color: purple
mcpServers:
  - context7
skills:
  - superpowers:requesting-code-review
initialPrompt: |
  1. OWASP Top 10 스캔: API 키 하드코딩, 경로 트래버설, SQL injection, XSS
  2. fs-helpers 사용 검증: validateRunPath/validateChannelPath 누락 탐지
  3. 코드 품질: SOLID 원칙, 중복 코드, 복잡도 (McCabe > 15)
  4. CLAUDE.md 규칙 준수 여부
  발견 이슈는 심각도 태깅 후 SendMessage로 Builder에게 전달.
  작업 완료 후 종료하세요. background=true는 자동 시작 허용이지, 무한 루프가 아닙니다.
---

## 감사 영역 (3차원)
1. **보안**: OWASP Top 10, API 키 하드코딩, 경로 트래버설, Supabase RLS 오용
2. **품질**: 클린코드, McCabe 복잡도, SOLID/DRY, 모듈 경계
3. **아키텍처**: CLAUDE.md 핵심 규칙 준수, 파일 소유권 위반

## 이슈 전달 형식
```
[이슈 유형: 보안/품질/아키텍처]
파일: {파일:줄번호}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {구체적 문제}
수정 담당: {python-dev/web-dev/design-dev}
```

## 통합 대상 (v3.1 → v5)
- quality-reviewer: 코드품질+아키텍처 리뷰
- security-guardian: OWASP+보안 감사
- api-designer: API 설계 리뷰 (구현은 Builder에게 위임)
```

#### ops-monitor

```yaml
---
name: ops-monitor
description: |
  KAS 운영 통합 모니터. 인프라 감시, 비용 추적, 문서 동기화, hooks/ruff/prettier
  설정 관리, CLAUDE.md/AGENTS.md 유지보수 담당.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: acceptEdits
memory: user
color: green
mcpServers:
  - context7
skills:
  - claude-md-management:revise-claude-md
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import os,sys,json; p=json.loads(sys.stdin.read()).get('input',{}).get('file_path','').replace('\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/step', '/web/app/', '/web/components/']) else sys.exit(0)\""
initialPrompt: |
  .claude/settings.local.json의 hooks 상태를 먼저 확인하세요.
  CLAUDE.md와 AGENTS.md의 에이전트 수/이름이 실제 .claude/agents/ 파일과 일치하는지 검증하세요.
  ruff/prettier 설정, CI/CD, Gemini 쿼터 상태도 점검하세요.
---

## 소유 영역
- `.claude/settings.local.json` (hooks, permissions)
- `.claude/agents/*.md` (에이전트 정의 관리)
- `CLAUDE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`
- `docs/` (문서 전체)
- `.github/workflows/` (CI/CD)
- `.editorconfig`, `.prettierrc`, `ruff.toml`
- `data/global/quota/` (쿼터 설정)

## 교차 금지
- `src/step*` (파이프라인 코드)
- `web/app/`, `web/components/` (프론트엔드 코드)

## 통합 대상 (v3.1 → v5)
- platform-ops (infra-ops + devops-automation + cost-optimizer)
- docs-manager (doc-keeper + docs-architect)
```

### 3.4 Layer 3: SPECIALIST (6개)

#### db-architect

```yaml
---
name: db-architect
description: DB 스키마 설계, Supabase 마이그레이션, SQL 최적화 시 소환.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: auto
memory: local
isolation: worktree
color: orange
mcpServers:
  - context7
initialPrompt: |
  scripts/supabase_schema.sql과 web/lib/types.ts를 먼저 읽어서 현재 스키마 상태를 파악하세요.
  스키마 변경 시 반드시 마이그레이션 스크립트를 포함하세요.
---

## 소유: scripts/supabase_schema.sql, scripts/migrations/
## 스키마 변경 시 UiUxAgent 타입 동기화 검증 필수.
```

#### refactoring-surgeon

```yaml
---
name: refactoring-surgeon
description: God Module 분해, 코드 복잡도 감소, 아키텍처 개선 시 소환.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 30
permissionMode: auto
memory: local
isolation: worktree
color: teal
skills:
  - superpowers:systematic-debugging
initialPrompt: |
  먼저 대상 모듈의 의존성 그래프를 파악하세요. grep으로 import 관계를 추적한 뒤 분해 전략을 수립하세요.
  대상 후보: src/quota/__init__.py (598줄), web/app/monitor/page.tsx (990줄).
  반드시 모든 테스트 통과를 유지하면서 리팩토링하세요.
---
```

#### pipeline-debugger

```yaml
---
name: pipeline-debugger
description: |
  파이프라인 장애 디버깅, Step 실패 원인 분석, 트렌드 데이터 분석 시 소환.
  Step08 오케스트레이터(KAS-PROTECTED), FFmpeg 에러, Gemini API 오류,
  쿼터 초과, manifest.json 상태 분석 + Step05 트렌드/지식 수집 분석.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: auto
memory: local
isolation: worktree
color: crimson
skills:
  - superpowers:systematic-debugging
initialPrompt: |
  logs/pipeline.log의 최근 에러와 runs/*/manifest.json의 FAILED 항목을 먼저 스캔하세요.
  data/global/step_progress.json에서 마지막 실행 상태도 확인하세요.
  Step05 트렌드 분석 시: data/knowledge_store/의 채널별 시리즈 JSON을 확인하세요.
---

## 통합 대상: pipeline-debugger + trend-analyst + video-qa-specialist
```

#### performance-profiler

```yaml
---
name: performance-profiler
description: 성능 병목 분석, N+1 쿼리, 메모리 누수, 번들 사이즈, 캐시 효율 분석 시 소환.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage
disallowedTools: Write, Edit
maxTurns: 25
permissionMode: plan
memory: local
isolation: worktree
color: amber
initialPrompt: |
  logs/pipeline.log에서 각 Step의 실행 시간을 추출하고,
  data/global/step_progress.json에서 elapsed_ms 패턴을 분석하세요.
  N+1 쿼리, time.sleep 하드코딩, 3초 폴링→SSE 전환 대상을 탐지하세요.
---

## Read-only 분석 전용. 권장사항만 제시.
```

#### ux-a11y

```yaml
---
name: ux-a11y
description: |
  WCAG 2.1 AA 접근성 + UX 사용성 통합 리뷰어. aria 속성, 키보드 네비게이션,
  스크린리더 호환성, 색상 대비, 사용자 흐름, 모바일 반응형 검증.
  코드를 직접 수정하지 않고 SendMessage로 web-dev/design-dev에게 전달.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage
disallowedTools: Write, Edit
maxTurns: 20
permissionMode: plan
memory: local
color: teal
mcpServers:
  - playwright
initialPrompt: |
  web/app/ 디렉토리의 주요 페이지를 Playwright로 접근성 감사하세요.
  WCAG 2.1 AA 기준: aria 속성, tabIndex, role, 색상 대비(4.5:1), 키보드 탐색.
  모바일 반응형 (375px/768px) 검증도 포함하세요.
---

## 통합 대상: ux-reviewer + a11y-expert
## 발견 이슈는 SendMessage로 web-dev(로직) 또는 design-dev(스타일)에게 전달.
```

#### release-manager

```yaml
---
name: release-manager
description: 릴리스 관리, 버전 태깅, CHANGELOG 생성, PR 생성 시 소환.
model: haiku
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 15
permissionMode: auto
memory: local
color: silver
initialPrompt: |
  git log --oneline -20으로 최근 커밋을 확인하고,
  마지막 태그 이후 변경 사항을 정리하세요.
---
```

---

## 4. 역할 통합 매핑

```
v3.1 (24개)                               v5 (12개)
────────────────────────────────           ──────────────────────────
[L1] mission-controller                →   [L0] mission-controller (+effort:high, +skills 4개, +memory:user)
[L2] backend-dev                       ┐
[L2] test-engineer                     ├→  [L1] python-dev (+worktree, +auto, +initialPrompt)
[L2] infra-ops (scripts 부분)          ┘
[L2] frontend-dev                      ┐
[L3] e2e-playwright                    ├→  [L1] web-dev (+worktree, +auto, +initialPrompt)
                                       ┘
[L3] ui-designer                       →   [L1] design-dev (+Figma MCP, +ui-ux skill)
[L2] quality-reviewer                  ┐
[L2] security-sentinel                 ├→  [L2] quality-security (+background, +code-review skill)
[L3] security-auditor                  │
[L3] api-designer (리뷰 기능)          ┘
[L2] devops-automation                 ┐
[L3] cost-optimizer-agent              │
[L3] docs-architect                    ├→  [L2] ops-monitor (+memory:user, +claude-md skill)
[L3] doc-keeper                        │
[L2] infra-ops (설정 부분)             ┘
[L3] ux-reviewer                       ┐
[L3] a11y-expert                       ├→  [L3] ux-a11y (+playwright MCP)
                                       ┘
[L3] pipeline-debugger                 ┐
[L3] trend-analyst                     ├→  [L3] pipeline-debugger (+trend+QA 통합)
[L3] video-qa-specialist               ┘
[L3] db-architect                      →   [L3] db-architect (+worktree, +initialPrompt)
[L3] refactoring-surgeon               →   [L3] refactoring-surgeon (+worktree, +initialPrompt)
[L3] performance-profiler              →   [L3] performance-profiler (+worktree, +plan)
[L3] release-manager                   →   [L3] release-manager (Haiku 유지)

삭제됨 (통합으로 흡수): 12개 에이전트
유지 (기능 강화): 6개 Specialist
재설계: 6개 (L0+L1+L2)
```

---

## 5. Hooks 완전 활성화

### 5.1 글로벌 hooks (settings.local.json)

```jsonc
{
  "hooks": {
    "TaskCompleted": [{
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -10"
        },
        {
          "type": "command",
          "command": "ruff check src/ --fix --select=E,W,F,I 2>&1 | tail -5"
        },
        {
          "type": "command",
          "command": "cd web && npm run build 2>&1 | tail -10"
        }
      ]
    }],
    "TaskCreated": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo \"[v5:TaskCreated] $(date +%H:%M:%S)\" >> .claude/agent-logs/hooks.log"
      }]
    }],
    "TeammateIdle": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "git diff HEAD~1 --name-only 2>/dev/null | head -20"
      }]
    }],
    "SubagentStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo \"[v5:SubagentStart] $(date +%H:%M:%S)\" >> .claude/agent-logs/hooks.log"
      }]
    }],
    "SubagentStop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo \"[v5:SubagentStop] $(date +%H:%M:%S)\" >> .claude/agent-logs/hooks.log"
      }]
    }],
    "WorktreeCreate": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "cp .env \"$WORKTREE_PATH/.env\" 2>/dev/null; cp web/.env.local \"$WORKTREE_PATH/web/.env.local\" 2>/dev/null; echo \"[v5:WorktreeCreate] env copied\" >> .claude/agent-logs/hooks.log"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python -c \"import sys,json; p=json.loads(sys.stdin.read()).get('input',{}).get('file_path','').replace('\\\\\\\\','/'); blocked=['.env','credentials/','_token.json','step08/__init__.py']; sys.exit(2) if any(b in p for b in blocked) else sys.exit(0)\""
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "git diff --stat HEAD 2>/dev/null | tail -5"
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo '=== v5 Session End ===' && pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -3 && ruff check src/ 2>&1 | tail -3"
      }]
    }]
  }
}
```

### 5.2 토큰 비용 분석

| Hook | 타입 | v4 반구현 | v5 | 절감 |
|------|:----:|:--------:|:--:|:----:|
| PreToolUse 보안 | prompt→**command** | ~30K 토큰/일 | **0** | 100% |
| 기타 8종 | command | 0 | 0 | - |
| **총 hook 토큰/일** | | **~30K** | **0** | **100%** |

---

## 6. Worktree Isolation 전략

| 에이전트 | isolation | 이유 |
|----------|:---------:|------|
| python-dev | **worktree** | src/ 병렬 수정 안전 |
| web-dev | **worktree** | web/ 병렬 수정 안전 |
| design-dev | - | CSS 시각적 확인 필요 |
| quality-security | - | Read-only |
| ops-monitor | - | 설정 파일 순차 수정 |
| db-architect | **worktree** | 스키마 변경 독립 |
| refactoring-surgeon | **worktree** | 리팩토링 광범위 변경 격리 |
| pipeline-debugger | **worktree** | 디버깅 임시 수정 격리 |
| performance-profiler | **worktree** | 프로파일링 코드 삽입 격리 |
| ux-a11y | - | Read-only |
| release-manager | - | 태그/CHANGELOG만 |

**`.worktreeinclude`** (프로젝트 루트):
```
.env
web/.env.local
credentials/
```

---

## 7. Cron/Schedule 자율 운영

| 주기 | 작업 | 담당 | 설명 |
|------|------|------|------|
| 매 6시간 | 파이프라인 헬스체크 | ops-monitor | FAILED 스캔, HITL 미해결, step_progress.json |
| 매일 09:00 | 코드 품질 리포트 | python-dev | pytest 커버리지 + ruff + npm build |
| 매주 월 09:00 | 보안 스캔 | quality-security | npm audit, pip-audit, 경로 트래버설 |
| 매주 금 17:00 | 문서 최신화 | ops-monitor | CLAUDE.md/AGENTS.md 일치 검증, memory 정리 |
| 매월 1일 | 아키텍처 리포트 | mission-controller | 복잡도 분석, memory 25KB 초과 정리 |

---

## 8. Memory 3-Scope 전략

| Scope | 에이전트 | 저장 위치 | 이유 |
|-------|----------|----------|------|
| **user** | mission-controller, ops-monitor | `~/.claude/agent-memory/` | 크로스 프로젝트 운영 패턴 |
| **project** | python-dev, web-dev, design-dev, quality-security | `.claude/agent-memory/` | 프로젝트별 코드 패턴 |
| **local** | L3 전원 (6개) | `.claude/agent-memory-local/` | 임시, .gitignore |

---

## 9. 모델 배분 전략

| 모델 | 에이전트 수 | 에이전트 | 비용 특성 |
|------|:---------:|---------|----------|
| **Opus** | 1 | mission-controller | effort:high, 조율/판단만 |
| **Sonnet** | 10 | python-dev, web-dev, design-dev, quality-security, ops-monitor, db-architect, refactoring-surgeon, pipeline-debugger, performance-profiler, ux-a11y | 실행/리뷰 주력 |
| **Haiku** | 1 | release-manager | CHANGELOG/태그만 |

**v3.1 → v5 비용 변화**:
- Opus: 3명 → 1명 (−66%)
- 에이전트 수: 24 → 12 (−50%)
- prompt hooks: 1개 → 0개 (−100%)
- 미션당 AGENTS.md 토큰: 305줄 → ~120줄 (−60%)

---

## 10. 문서 동기화 계획

### CLAUDE.md "Agent Teams 설정" 섹션 (재작성)

```markdown
## Agent Teams 설정 (v5)

### 4-Layer 구조 (12개)

| Layer | 팀원 | 모델 | 역할 |
|-------|------|------|------|
| L0 | mission-controller | Opus | 자율 이슈 감지 + 팀 편성 |
| L1 | python-dev | Sonnet | src/+tests/+scripts/ |
| L1 | web-dev | Sonnet | web/ (globals.css 제외) |
| L1 | design-dev | Sonnet | globals.css+public/+thumbnails/ |
| L2 | quality-security | Sonnet | 보안+품질 통합 감사 (background) |
| L2 | ops-monitor | Sonnet | 인프라+문서+비용 운영 |
| L3 | db-architect | Sonnet | DB 스키마/마이그레이션 |
| L3 | refactoring-surgeon | Sonnet | God Module 분해 |
| L3 | pipeline-debugger | Sonnet | 파이프라인+트렌드+QA 디버깅 |
| L3 | performance-profiler | Sonnet | 성능 병목 분석 |
| L3 | ux-a11y | Sonnet | WCAG+UX 통합 리뷰 |
| L3 | release-manager | Haiku | 릴리스 관리 |
```

### AGENTS.md (전면 재작성, ~120줄 목표)

핵심 변경:
- 24개 → 12개 에이전트 반영
- 유령 에이전트 7개 완전 제거
- 미션 프리셋 14가지 → 7가지로 축소
- 통신 프로토콜 3가지로 간소화

---

## 11. 마이그레이션 단계

### Phase 1: 에이전트 파일 변경

1. **삭제** (6개): `quality-reviewer.md`, `security-guardian.md`, `a11y-expert.md`, `ux-reviewer.md`, `api-designer.md`, `docs-manager.md`
2. **이름 변경+재작성** (4개): `backend-dev.md`→`python-dev.md`, `frontend-dev.md`→`web-dev.md`, `ui-designer.md`→`design-dev.md`, `platform-ops.md`→`ops-monitor.md`
3. **신규 생성** (2개): `quality-security.md`, `ux-a11y.md`
4. **body 업데이트** (4개): `mission-controller.md`, `pipeline-debugger.md`, `performance-profiler.md`, `refactoring-surgeon.md`

### Phase 2: 설정 파일

1. `settings.local.json` 재작성 (hooks 전체, prompt→command)
2. `.worktreeinclude` 생성
3. `.claude/agent-logs/` 디렉토리 생성

### Phase 3: 문서

1. CLAUDE.md "Agent Teams 설정" 섹션 재작성
2. AGENTS.md 전면 재작성 (~120줄)

### Phase 4: 정리

1. 구 agent-memory 마이그레이션:
   - `security-sentinel/` → `quality-security/`
   - `security-auditor/` → `quality-security/`
   - `infra-ops/` → `ops-monitor/`
   - `devops-automation/` → `ops-monitor/`
   - `doc-keeper/` → `ops-monitor/`
2. 구 에이전트 메모리 디렉토리 제거

### Phase 5: 검증

1. 모든 12개 에이전트 파일 frontmatter 유효성 검증
2. per-agent hooks 동작 테스트 (파일 경계 차단)
3. worktree isolation 동작 테스트
4. TaskCompleted hook 3중 게이트 통과 확인
5. pytest + npm run build 최종 검증

---

## 12. 검증 계획

| 단계 | 검증 항목 | 방법 |
|------|---------|------|
| 1 | 에이전트 파일 유효성 | `.claude/agents/` 12개 파일 존재 + frontmatter 파싱 |
| 2 | per-agent hooks | python-dev로 web/ 수정 시도 → 차단 확인 |
| 3 | worktree isolation | python-dev 소환 시 worktree 생성 확인 |
| 4 | background guardian | quality-security 자동 실행 확인 |
| 5 | PreToolUse 보안 | .env 파일 수정 시도 → 차단 확인 |
| 6 | TaskCompleted | 태스크 완료 시 pytest+ruff+build 3중 게이트 |
| 7 | 문서 일관성 | CLAUDE.md, AGENTS.md가 12개 에이전트 정확히 반영 |
| 8 | Cron 등록 | `/schedule` 명령으로 5개 스케줄 등록 확인 |
