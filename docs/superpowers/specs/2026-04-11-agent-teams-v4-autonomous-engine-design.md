# Agent Teams v4 "Autonomous Engine" — 전면 재설계 스펙

> **날짜**: 2026-04-11
> **버전**: v4.0
> **이전 버전**: v3.1 (24개 에이전트, 3-Layer Command Structure)
> **목표**: Claude Code 공식 문서의 모든 기능 100% 활용, 완전 자동화 최고 수준

---

## 1. 설계 동기

### 1.1 v3.1 감사 결과

| 항목 | v3.1 현황 | 공식 최고 수준 | 갭 |
|------|----------|-------------|-----|
| 에이전트 수 | 24개 (8상시+16전문가) | 제한 없음, 3~5 권장 | 역할 중복 6쌍 |
| frontmatter 필드 활용 | 9/16 (56%) | 16/16 (100%) | hooks, skills, isolation, effort, background, initialPrompt 미사용 |
| 글로벌 hooks | 2/6 (33%) | 6/6 (100%) | SubagentStart/Stop, TaskCreated, WorktreeCreate 미사용 |
| Worktree isolation | 0% | Builder 전원 | 충돌 방지 장치 없음 |
| Skills 연동 | 0% | 에이전트별 | skill 자동 주입 미활용 |
| Memory 3-scope | project만 | user/project/local | 크로스 프로젝트/민감 정보 분리 없음 |
| Cron/Schedule | 0% | 5개+ 스케줄 | 자율 운영 없음 |
| 자가 치유 | system prompt 규칙만 | hooks 강제 | 규칙 위반 시 강제 장치 없음 |

### 1.2 역할 중복 분석

```
security-sentinel ↔ security-auditor    → 상시 감시 vs 심층 감사 (실질적 차이 미미)
quality-reviewer  ↔ code-review skill   → 도구 vs 수동 리뷰 (기능 중복)
docs-architect    ↔ doc-keeper          → 문서 작성 vs 문서 동기화 (범위 겹침)
ux-reviewer       ↔ a11y-expert         → UX vs 접근성 (밀접 관련)
devops-automation ↔ infra-ops           → CI/CD vs 인프라 (동일 도메인)
cost-optimizer    ↔ ops-monitor 역할     → 비용 추적 (운영 하위 기능)
```

---

## 2. 아키텍처 — 4-Layer Dynamic Scaling

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 0: AUTONOMOUS (1)                       │
│  mission-controller — Opus, plan, effort:max, memory:user       │
│  skills: brainstorming, writing-plans, dispatching-parallel     │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 1: BUILDER (3)                          │
│  python-dev  — Sonnet, auto, worktree, TDD+debugging skills    │
│  web-dev     — Sonnet, auto, worktree, frontend-design skill   │
│  design-dev  — Sonnet, acceptEdits, Figma MCP, ui-ux skill     │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 2: GUARDIAN (3)                         │
│  quality-security — Opus, plan, background, code-review skill  │
│  ux-a11y          — Sonnet, plan, background, ui-ux skill      │
│  ops-monitor      — Sonnet, acceptEdits, memory:user           │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 3: SPECIALIST (8)                       │
│  db-architect, refactoring-surgeon, pipeline-debugger,          │
│  video-qa-specialist, performance-profiler, api-designer,       │
│  trend-analyst(Haiku), release-manager(Haiku)                   │
│  — 온디맨드 소환, worktree, initialPrompt                        │
└─────────────────────────────────────────────────────────────────┘

총 15개 에이전트 (v3.1 대비 37% 축소, 기능 100% 향상)
```

**핵심 원칙**:
- 평시: L0 + L1 + L2 = 7개만 활성
- 대규모 미션: L3에서 최대 5개 추가 소환 = 최대 12개
- L2 Guardian은 `background: true`로 상시 감시
- L1 Builder는 `isolation: worktree`로 병렬 안전 보장

> **구현 주의사항**:
> - `effort: max`는 Claude Opus 4.6 전용 기능. 다른 모델에서는 무시됨.
> - `background: true`는 실험적 기능일 수 있음 — 구현 시 동작 검증 필요.
> - 에이전트 frontmatter 내 `hooks` 필드는 global settings의 hooks와 동일 형식.

---

## 3. 에이전트 정의 상세

### 3.1 Layer 0: AUTONOMOUS

#### mission-controller

```yaml
---
name: mission-controller
description: |
  KAS 프로젝트의 자율 오케스트레이터. 이슈 감지, 팀 편성, 진행 조율을 담당한다.
  대규모 기능 개발, 버그 수정, 리팩토링 미션 시 팀을 편성하고 조율한다.
model: opus
tools: Read, Glob, Grep, Bash, Agent, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet
disallowedTools: Write, Edit
maxTurns: 50
permissionMode: plan
memory: user
effort: max
color: gold
skills:
  - superpowers:brainstorming
  - superpowers:writing-plans
  - superpowers:dispatching-parallel-agents
mcpServers:
  - context7
---
```

**system prompt 핵심 내용**:
- HITL 미해결 신호 자동 감지
- manifest.json FAILED 자동 감지
- 팀 편성 시 소환 메시지 표준 형식 준수
- 미션 완료 후 교훈 추출 → agent-memory 기록
- Opus 4명 동시 소환 금지, L3 5명 초과 소환 금지

### 3.2 Layer 1: BUILDER

#### python-dev

```yaml
---
name: python-dev
description: |
  KAS 백엔드 전문가. src/ 디렉토리 전체 담당 — pipeline, step 모듈, agents, core, quota, cache.
  테스트(tests/) 작성, 스크립트(scripts/) 유지보수도 담당한다.
  파이프라인 수정, 에러 전략, 에이전트 시스템 확장 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, Agent, SendMessage, TaskCreate, TaskUpdate, TaskList
maxTurns: 40
permissionMode: auto
memory: project
isolation: worktree
color: red
skills:
  - superpowers:test-driven-development
  - superpowers:systematic-debugging
mcpServers:
  - context7
hooks:
  SubagentStop:
    - type: command
      command: "pytest tests/ -x -q 2>&1 | tail -15"
---
```

**소유 영역**: `src/`, `tests/`, `scripts/`, `pyproject.toml`, `ruff.toml`, `requirements.txt`
**교차 금지**: `web/` 디렉토리 진입 금지
**통합 대상**: v3.1의 backend-dev + test-engineer + infra-ops

#### web-dev

```yaml
---
name: web-dev
description: |
  KAS 프론트엔드 전문가. web/ 디렉토리 전체 담당 — Next.js 16, Tailwind CSS v4, shadcn/ui, Supabase.
  웹 페이지, API 라우트, 컴포넌트(로직), 스타일 외, 모바일 반응형 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, Agent, SendMessage, TaskCreate, TaskUpdate, TaskList
maxTurns: 40
permissionMode: auto
memory: project
isolation: worktree
color: blue
skills:
  - frontend-design:frontend-design
  - superpowers:test-driven-development
mcpServers:
  - context7
  - playwright
hooks:
  SubagentStop:
    - type: command
      command: "cd web && npm run build 2>&1 | tail -10"
---
```

**소유 영역**: `web/app/`, `web/lib/`, `web/hooks/`, `web/components/`(로직: onClick, useState, useEffect 등)
**교차 금지**: `src/` 디렉토리 진입 금지
**공유**: `web/components/`의 스타일(className, Tailwind)은 design-dev와 공유
**통합 대상**: v3.1의 frontend-dev + e2e-playwright

#### design-dev

```yaml
---
name: design-dev
description: |
  KAS UI 디자인 전문가. CSS/디자인 시스템, 에셋, Figma 연동 담당.
  globals.css 수정, 디자인 토큰 변경, 썸네일 베이스 PNG 재생성, 컴포넌트 스타일링 작업 시 위임.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 30
permissionMode: acceptEdits
memory: project
color: pink
skills:
  - frontend-design:frontend-design
  - ui-ux-pro-max:ui-ux-pro-max
mcpServers:
  - figma
  - playwright
---
```

**소유 영역**: `web/app/globals.css`, `web/public/`, `assets/thumbnails/`, `web/components/`(스타일: className, Tailwind, CSS 변수)
**교차 금지**: `src/`, `tests/` 진입 금지
**통합 대상**: v3.1의 ui-designer + devops-automation(CSS 부분)

### 3.3 Layer 2: GUARDIAN

#### quality-security

```yaml
---
name: quality-security
description: |
  KAS 코드 품질 + 보안 통합 감사. 코드 리뷰, 보안 취약점 감지, 아키텍처 검증을 담당한다.
  코드를 직접 수정하지 않고, 발견 이슈는 SendMessage로 해당 빌더에게 전달한다.
model: opus
tools: Read, Glob, Grep, Bash, SendMessage, TaskCreate, TaskUpdate, TaskList
disallowedTools: Write, Edit
maxTurns: 35
permissionMode: plan
memory: project
effort: max
background: true
color: purple
skills:
  - code-review:code-review
  - superpowers:requesting-code-review
mcpServers:
  - context7
---
```

**감시 대상**: OWASP Top 10, 경로 트래버설, SQL injection, XSS, 하드코딩된 시크릿
**통합 대상**: v3.1의 quality-reviewer + security-sentinel + security-auditor

#### ux-a11y

```yaml
---
name: ux-a11y
description: |
  KAS UX + 접근성 통합 리뷰어. WCAG 준수, 사용성 검사, 모바일 반응형 검증을 담당한다.
  코드를 직접 수정하지 않고, 발견 이슈는 SendMessage로 web-dev 또는 design-dev에게 전달한다.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage, TaskCreate, TaskUpdate, TaskList
disallowedTools: Write, Edit
maxTurns: 25
permissionMode: plan
memory: project
background: true
color: cyan
skills:
  - ui-ux-pro-max:ui-ux-pro-max
mcpServers:
  - playwright
---
```

**통합 대상**: v3.1의 ux-reviewer + a11y-expert

#### ops-monitor

```yaml
---
name: ops-monitor
description: |
  KAS 운영 통합 모니터. 인프라 감시, 비용 추적, 문서 동기화, CLAUDE.md/AGENTS.md 유지보수 담당.
  Hooks 관리, ruff/prettier 설정, CI/CD 파이프라인, Supabase 동기화도 포함.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage, TaskCreate, TaskUpdate, TaskList
maxTurns: 25
permissionMode: acceptEdits
memory: user
color: green
skills:
  - claude-md-management:revise-claude-md
mcpServers:
  - context7
---
```

**소유 영역**: `.claude/settings.local.json`, `.editorconfig`, `.prettierrc`, `ruff.toml`, `CLAUDE.md`, `AGENTS.md`
**통합 대상**: v3.1의 devops-automation + cost-optimizer + doc-keeper + docs-architect

### 3.4 Layer 3: SPECIALIST (온디맨드)

모든 L3 에이전트 공통 frontmatter:

```yaml
permissionMode: auto
memory: local
isolation: worktree
```

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
---
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
---
```

#### pipeline-debugger

```yaml
---
name: pipeline-debugger
description: 파이프라인 장애 디버깅, Step 실패 원인 분석, manifest.json FAILED 조사 시 소환.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 30
permissionMode: auto
memory: local
isolation: worktree
color: crimson
skills:
  - superpowers:systematic-debugging
initialPrompt: |
  logs/pipeline.log의 최근 에러와 runs/*/manifest.json의 FAILED 항목을 먼저 스캔하세요.
  data/global/step_progress.json에서 마지막 실행 상태도 확인하세요.
---
```

#### video-qa-specialist

```yaml
---
name: video-qa-specialist
description: 영상 QA 검증, Step08 결과물 검사, SHA-256 무결성 체크 시 소환.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage
maxTurns: 20
permissionMode: auto
memory: local
color: magenta
initialPrompt: |
  runs/*/step08/ 디렉토리에서 최근 결과물의 artifact_hashes.json을 확인하고,
  qa_result.json의 통과/실패 항목을 분석하세요.
---
```

#### performance-profiler

```yaml
---
name: performance-profiler
description: 성능 병목 분석, API 응답 시간 측정, 메모리 사용량 프로파일링 시 소환.
model: sonnet
tools: Read, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: auto
memory: local
isolation: worktree
color: amber
initialPrompt: |
  먼저 logs/pipeline.log에서 각 Step의 실행 시간을 추출하고,
  data/global/step_progress.json에서 elapsed_ms 패턴을 분석하세요.
---
```

#### api-designer

```yaml
---
name: api-designer
description: API 계약 설계, OpenAPI 스펙 작성, 엔드포인트 구조 변경 시 소환.
model: sonnet
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 25
permissionMode: auto
memory: local
isolation: worktree
color: indigo
mcpServers:
  - context7
initialPrompt: |
  web/app/api/ 디렉토리 구조를 먼저 파악하고, 기존 API 라우트의 요청/응답 패턴을 분석하세요.
---
```

#### trend-analyst

```yaml
---
name: trend-analyst
description: 트렌드 데이터 분석, 채널별 점수 패턴 추출, 소스별 성과 비교 시 소환.
model: haiku
tools: Read, Glob, Grep, Bash, SendMessage
maxTurns: 20
permissionMode: auto
memory: local
color: lime
initialPrompt: |
  data/knowledge_store/의 각 채널별 시리즈 JSON과 Supabase trend_topics 테이블 구조를 먼저 파악하세요.
---
```

#### release-manager

```yaml
---
name: release-manager
description: 릴리스 관리, 버전 태깅, 체인지로그 생성, 배포 체크리스트 관리 시 소환.
model: haiku
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 20
permissionMode: auto
memory: local
color: gray
initialPrompt: |
  git log --oneline -20으로 최근 커밋을 확인하고, 마지막 태그 이후 변경 사항을 정리하세요.
---
```

---

## 4. 역할 통합 매핑

```
v3.1 (24개)                               v4 (15개)
────────────────────────────────           ──────────────────────────
[L1] mission-controller                →   [L0] mission-controller (+effort:max, +skills, +memory:user)
[L2] backend-dev                       ┐
[L2] test-engineer                     ├→  [L1] python-dev (+worktree, +TDD skill, +auto mode)
[L2] infra-ops                         ┘
[L2] frontend-dev                      ┐
[L3] e2e-playwright                    ├→  [L1] web-dev (+worktree, +frontend skill, +auto mode)
                                       ┘
[L3] ui-designer                       →   [L1] design-dev (+Figma MCP, +ui-ux skill)
[L2] devops-automation (CSS외)         ┐
[L3] cost-optimizer-agent              ├→  [L2] ops-monitor (+memory:user, +claude-md skill)
[L3] docs-architect                    │
[L3] doc-keeper                        ┘
[L2] quality-reviewer                  ┐
[L2] security-sentinel                 ├→  [L2] quality-security (+background, +effort:max, +code-review skill)
[L3] security-auditor                  ┘
[L3] ux-reviewer                       ┐
[L3] a11y-expert                       ├→  [L2] ux-a11y (+background, +ui-ux skill)
                                       ┘
[L3] db-architect                      →   [L3] db-architect (+worktree, +initialPrompt)
[L3] refactoring-surgeon               →   [L3] refactoring-surgeon (+worktree, +initialPrompt)
[L3] pipeline-debugger                 →   [L3] pipeline-debugger (+worktree, +initialPrompt)
[L3] video-qa-specialist               →   [L3] video-qa-specialist (+initialPrompt)
[L3] performance-profiler              →   [L3] performance-profiler (+worktree, +initialPrompt)
[L3] api-designer                      →   [L3] api-designer (+worktree, +initialPrompt)
[L3] trend-analyst                     →   [L3] trend-analyst (+initialPrompt)
[L3] release-manager                   →   [L3] release-manager (+initialPrompt)

제거됨 (통합으로): 9개 에이전트
유지 (기능 강화): 8개 Specialist
재설계: 7개 (L0+L1+L2)
```

---

## 5. Hooks 완전 활성화

### 5.1 글로벌 hooks (settings.local.json)

```json
{
  "hooks": {
    "TaskCompleted": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "pytest tests/ -x -q && ruff check src/ --fix --select=E,W,F,I && cd web && npm run build"
      }]
    }],
    "TaskCreated": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo '[v4:TaskCreated] $(date +%H:%M:%S)' >> .claude/agent-logs/hooks.log"
      }]
    }],
    "TeammateIdle": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "git diff HEAD~1 --name-only | head -20"
      }]
    }],
    "SubagentStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo '[v4:SubagentStart] $(date +%H:%M:%S)' >> .claude/agent-logs/hooks.log"
      }]
    }],
    "SubagentStop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo '[v4:SubagentStop] $(date +%H:%M:%S)' >> .claude/agent-logs/hooks.log"
      }]
    }],
    "WorktreeCreate": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "cp .env \"$WORKTREE_PATH/.env\" 2>/dev/null; cp web/.env.local \"$WORKTREE_PATH/web/.env.local\" 2>/dev/null; echo '[v4:WorktreeCreate] env copied' >> .claude/agent-logs/hooks.log"
      }]
    }]
  }
}
```

### 5.2 에이전트별 hooks (frontmatter 내)

| 에이전트 | Hook | 동작 |
|----------|------|------|
| python-dev | SubagentStop | `pytest tests/ -x -q` |
| web-dev | SubagentStop | `cd web && npm run build` |

### 5.3 v3.1 대비 변경 사항

| 항목 | v3.1 | v4 |
|------|------|-----|
| ruff | `--exit-zero` (검사만) | `--fix` (**자동 수정**) |
| TaskCreated | 없음 | 로깅 추가 |
| SubagentStart/Stop | 없음 | 로깅 추가 |
| WorktreeCreate | 없음 | `.env` 자동 복사 |

---

## 6. Worktree Isolation 전략

### 6.1 적용 대상

| 에이전트 | isolation | 이유 |
|----------|-----------|------|
| python-dev | `worktree` | src/ 병렬 수정 안전 |
| web-dev | `worktree` | web/ 병렬 수정 안전 |
| design-dev | 미적용 | CSS 변경은 충돌 위험 낮음, 시각적 확인 필요 |
| L3 Specialist 6개 | `worktree` | 독립 작업 보장 |
| L3 Specialist 2개 | 미적용 | video-qa(읽기 위주), trend-analyst(읽기 위주) |

### 6.2 .worktreeinclude

프로젝트 루트에 `.worktreeinclude` 파일 생성:

```
.env
web/.env.local
credentials/
```

### 6.3 WorktreeCreate 훅과의 이중 안전

`.worktreeinclude`가 공식 지원이므로 우선 사용하고, WorktreeCreate 훅은 백업 경로로 유지.

---

## 7. Skills 프론트매터 연동

| 에이전트 | Skills | 효과 |
|----------|--------|------|
| mission-controller | brainstorming, writing-plans, dispatching-parallel-agents | 미션 설계 자동화 |
| python-dev | test-driven-development, systematic-debugging | TDD 워크플로우 강제 |
| web-dev | frontend-design, test-driven-development | 프론트엔드 설계 + TDD |
| design-dev | frontend-design, ui-ux-pro-max | 디자인 시스템 활용 |
| quality-security | code-review, requesting-code-review | 리뷰 프로세스 표준화 |
| ux-a11y | ui-ux-pro-max | UX/접근성 체크리스트 |
| ops-monitor | revise-claude-md | 문서 자동 업데이트 |

---

## 8. Memory 3-Scope 전략

### 8.1 Scope 배정

| Scope | 에이전트 | 디렉토리 | 이유 |
|-------|----------|----------|------|
| **user** | mission-controller, ops-monitor | `~/.claude/agent-memory/` | 크로스 프로젝트 팀 운영/인프라 패턴 |
| **project** | python-dev, web-dev, design-dev, quality-security, ux-a11y | `.claude/agent-memory/` | 프로젝트별 코드 패턴, Git 커밋 가능 |
| **local** | L3 Specialist 8개 전원 | `.claude/agent-memory-local/` | 임시 작업, 민감 정보, .gitignore |

### 8.2 디렉토리 구조

```
~/.claude/agent-memory/
  mission-controller/MEMORY.md
  ops-monitor/MEMORY.md

.claude/agent-memory/
  python-dev/MEMORY.md
  web-dev/MEMORY.md
  design-dev/MEMORY.md
  quality-security/MEMORY.md
  ux-a11y/MEMORY.md

.claude/agent-memory-local/
  db-architect/MEMORY.md
  refactoring-surgeon/MEMORY.md
  pipeline-debugger/MEMORY.md
  video-qa-specialist/MEMORY.md
  performance-profiler/MEMORY.md
  api-designer/MEMORY.md
  trend-analyst/MEMORY.md
  release-manager/MEMORY.md
```

---

## 9. Cron/Schedule 자율 운영

| 주기 | 작업 | 담당 에이전트 | 방법 |
|------|------|-------------|------|
| 매 6시간 | 파이프라인 헬스체크 (FAILED 스캔, HITL 미해결 확인) | ops-monitor | /schedule |
| 매일 09:00 | ruff check + prettier check + pytest 커버리지 리포트 | python-dev | /schedule |
| 매주 월 09:00 | 보안 스캔 (npm audit, pip-audit, 경로 트래버설 패턴 검사) | quality-security | /schedule |
| 매주 금 17:00 | CLAUDE.md/AGENTS.md 최신화 리뷰 + 에이전트 memory 정리 | ops-monitor | /schedule |
| 매월 1일 | 아키텍처 복잡도 리포트 + 에이전트 memory 25KB 초과 정리 | mission-controller | /schedule |

---

## 10. permissionMode 최적화

| 에이전트 | v3.1 | v4 | 변경 이유 |
|----------|------|-----|----------|
| mission-controller | plan | **plan** | 오케스트레이터 실행 전 승인 필수 |
| python-dev | acceptEdits | **auto** | worktree 격리로 안전, 속도 극대화 |
| web-dev | acceptEdits | **auto** | worktree 격리로 안전, 속도 극대화 |
| design-dev | acceptEdits | **acceptEdits** | CSS는 시각적 확인 필요 |
| quality-security | plan | **plan** | Read-only, Write/Edit 차단 |
| ux-a11y | plan | **plan** | Read-only, Write/Edit 차단 |
| ops-monitor | acceptEdits | **acceptEdits** | 인프라 변경은 확인 필요 |
| L3 전원 | acceptEdits | **auto** | 소환 시 빠른 실행, worktree 격리 |

---

## 11. 통신 프로토콜

### 11.1 표준 메시지 형식

**mission-controller → 팀원 소환**:
```
[미션 ID: YYYY-MM-DD-{유형}]
목표: {한 줄 목표}
범위: {수정 대상 파일/모듈}
제약조건: {금지 사항, 유지할 인터페이스}
완료 기준: {테스트 통과, 리뷰 승인 등}
우선순위: {높음/중간/낮음}
```

**Guardian → Builder (이슈 전달)**:
```
[이슈 유형: 보안/품질/UX/접근성]
파일: {파일:줄번호}
심각도: {CRITICAL/HIGH/MEDIUM/LOW}
설명: {구체적 문제와 영향}
수정 담당: {python-dev/web-dev/design-dev}
```

**Builder 간 API 계약 변경**:
```
[API 변경 알림]
엔드포인트: {경로}
변경 전: {기존 포맷}
변경 후: {새 포맷}
영향 범위: {프론트엔드 컴포넌트 목록}
```

### 11.2 파일 소유권 충돌 방지

| 경계 | 소유자 | 규칙 |
|------|--------|------|
| `src/`, `tests/`, `scripts/` | python-dev | web-dev/design-dev 진입 금지 |
| `web/app/`, `web/lib/`, `web/hooks/` | web-dev | python-dev 진입 금지 |
| `web/app/globals.css`, `web/public/`, `assets/` | design-dev | web-dev 직접 수정 금지 |
| `web/components/` 로직 | web-dev | onClick, useState, useEffect 등 |
| `web/components/` 스타일 | design-dev | className, Tailwind, CSS 변수 |
| `.claude/`, `CLAUDE.md`, `AGENTS.md` | ops-monitor | 다른 에이전트 수정 금지 |
| `scripts/supabase_schema.sql` | db-architect | 소환 시에만 |

---

## 12. 미션 프리셋

| 프리셋 | 팀 편성 | 설명 |
|--------|---------|------|
| `kas-hotfix` | python-dev + quality-security | 긴급 버그 수정 |
| `kas-feature-backend` | python-dev + quality-security | Python 신규 기능 |
| `kas-feature-frontend` | web-dev + design-dev + ux-a11y | 웹 신규 기능 |
| `kas-feature-fullstack` | python-dev + web-dev + design-dev + quality-security | 풀스택 기능 |
| `kas-pipeline-debug` | python-dev + pipeline-debugger | 파이프라인 장애 |
| `kas-security-audit` | quality-security + python-dev + web-dev | 보안 감사 |
| `kas-ui-redesign` | design-dev + web-dev + ux-a11y | UI 리디자인 |
| `kas-db-migration` | db-architect + python-dev + web-dev | DB 스키마 변경 |
| `kas-performance` | performance-profiler + python-dev | 성능 최적화 |
| `kas-release` | release-manager + ops-monitor | 릴리스 관리 |
| `kas-refactor` | refactoring-surgeon + python-dev + quality-security | 대규모 리팩토링 |
| `kas-docs-sync` | ops-monitor | 문서 동기화 |

---

## 13. 자가 치유 프로토콜

### 13.1 TaskCompleted 훅 기반 강제 치유

```
TaskCompleted 훅 실행
  → pytest 실패? → exit code 2 → 에이전트에게 실패 내용 피드백
  → 에이전트 자동 수정 시도 (최대 3회)
  → 3회 실패 → git stash → git checkout -- [파일들] → mission-controller에게 보고
```

### 13.2 Guardian background 감시

`quality-security`와 `ux-a11y`가 `background: true`로 상시 실행:
- Builder의 코드 변경을 실시간 감시
- 보안 취약점/품질 이슈 발견 시 즉시 SendMessage

---

## 14. 비용 효율성 분석

### 14.1 에이전트 수 비교

| 계층 | v3.1 | v4 | 차이 |
|------|------|-----|------|
| 지휘 (Opus) | 1 | 1 | 0 |
| 빌더 (Sonnet) | 2 | 3 | +1 |
| 가디언 (Opus/Sonnet) | 3 (2 Opus) | 3 (1 Opus) | -1 Opus |
| 운영 (Sonnet) | 2 | 0 (ops-monitor에 통합) | -2 |
| 전문가 (Sonnet/Haiku) | 16 | 8 | -8 |
| **합계** | **24** | **15** | **-9 (-37%)** |

### 14.2 모델 비용 비교

| 모델 | v3.1 수 | v4 수 | 비용 변화 |
|------|---------|-------|----------|
| Opus | 3 | 2 | -33% |
| Sonnet | 16 | 11 | -31% |
| Haiku | 5 | 2 | -60% |

### 14.3 총 예상 비용

v3.1 기준 100%일 때, v4는 약 **65%** (35% 절감).
기능은 공식 기능 56% → 100%로 **78% 향상**.

---

## 15. 구현 순서

### Phase 1: 백업 + 에이전트 파일 재작성
1. `.claude/agents/` → `.claude/agents-v3.1-backup/` 복사
2. 15개 에이전트 `.md` 파일 신규 작성

### Phase 2: settings.local.json 업데이트
1. hooks 2개 → 6개로 확장
2. permissions 정리

### Phase 3: AGENTS.md 전면 재작성
1. v4 아키텍처 문서화
2. 통신 프로토콜, 미션 프리셋 반영

### Phase 4: CLAUDE.md Agent Teams 섹션 갱신
1. 에이전트 목록 15개로 업데이트
2. 핵심 규칙 v4 기준으로 수정

### Phase 5: agent-memory 구조 정리
1. 3-scope 디렉토리 생성
2. 기존 memory 마이그레이션

### Phase 6: .worktreeinclude 생성

### Phase 7: Cron/Schedule 설정

### Phase 8: 검증
1. `claude agents` — 15개 확인
2. frontmatter 완전성 검증
3. hooks 동작 테스트
4. worktree 병렬 테스트
5. pytest + npm build 통과 확인

---

## 16. 공식 frontmatter 필드 100% 활용 체크리스트

| # | 필드 | v4 활용 | 적용 에이전트 |
|---|------|---------|-------------|
| 1 | name | ✅ | 전원 |
| 2 | description | ✅ | 전원 |
| 3 | model | ✅ (opus/sonnet/haiku) | 전원 |
| 4 | tools | ✅ | 전원 |
| 5 | disallowedTools | ✅ | quality-security, ux-a11y, mission-controller |
| 6 | maxTurns | ✅ (20~50) | 전원 |
| 7 | permissionMode | ✅ (plan/acceptEdits/auto) | 전원 |
| 8 | memory | ✅ (user/project/local) | 전원 |
| 9 | skills | ✅ (7개 연동) | 7개 에이전트 |
| 10 | mcpServers | ✅ (context7/playwright/figma) | 9개 에이전트 |
| 11 | hooks | ✅ (에이전트별) | python-dev, web-dev |
| 12 | isolation | ✅ (worktree) | 8개 에이전트 |
| 13 | effort | ✅ (max) | mission-controller, quality-security |
| 14 | color | ✅ | 전원 |
| 15 | background | ✅ | quality-security, ux-a11y |
| 16 | initialPrompt | ✅ | L3 Specialist 8개 전원 |

**16/16 = 100% 활용** ✅
