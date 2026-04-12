# Agent Teams v5 Ultra-Compact 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KAS Agent Teams를 v4 반구현(18개 에이전트, 9/16 frontmatter)에서 v5(12개 에이전트, 16/16 frontmatter, 완전 자율 운영)로 전환한다.

**Architecture:** 4-Layer(L0 Autonomous 1 + L1 Builder 3 + L2 Guardian 2 + L3 Specialist 6) 구조. 역할 중복 에이전트 6개 통합 삭제, 신규 2개 생성. settings.local.json의 prompt hook을 command hook으로 전환하여 토큰 비용 ~30K/일 절감.

**Tech Stack:** Claude Code Agent Teams, YAML frontmatter, bash Python one-liners (hook 스크립트), JSON (settings.local.json)

**Spec:** `docs/superpowers/specs/2026-04-11-agent-teams-v5-ultra-compact-design.md`

---

## 파일 구조 맵

### 삭제 대상 (6개)
- `.claude/agents/quality-reviewer.md` — quality-security에 흡수
- `.claude/agents/security-guardian.md` — quality-security에 흡수
- `.claude/agents/a11y-expert.md` — ux-a11y에 흡수
- `.claude/agents/ux-reviewer.md` — ux-a11y에 흡수
- `.claude/agents/api-designer.md` — quality-security 리뷰 기능에 흡수
- `.claude/agents/docs-manager.md` — ops-monitor에 흡수

### 이름 변경 + 전면 재작성 (6개)
- `.claude/agents/backend-dev.md` → **`python-dev.md`** (isolation:worktree, auto, initialPrompt 추가)
- `.claude/agents/frontend-dev.md` → **`web-dev.md`** (isolation:worktree, auto, initialPrompt 추가)
- `.claude/agents/ui-designer.md` → **`design-dev.md`** (hooks 추가, initialPrompt)
- `.claude/agents/platform-ops.md` → **`ops-monitor.md`** (memory:user, docs-manager 역할 흡수)
- `.claude/agents/mission-controller.md` — effort:high, skills 4개, Reflection body 업데이트
- `.claude/agents/pipeline-debugger.md` — isolation:worktree, memory:local, initialPrompt, trend+QA 통합

### 신규 생성 (2개)
- `.claude/agents/quality-security.md` — background:true, plan, disallowedTools
- `.claude/agents/ux-a11y.md` — plan, playwright MCP, disallowedTools

### 부분 업데이트 (4개)
- `.claude/agents/db-architect.md` — isolation:worktree, memory:local, permissionMode:auto, initialPrompt
- `.claude/agents/refactoring-surgeon.md` — isolation:worktree, memory:local, initialPrompt
- `.claude/agents/performance-profiler.md` — isolation:worktree, memory:local, permissionMode:plan 유지
- `.claude/agents/release-manager.md` — model:haiku 유지, memory:local, initialPrompt

### 설정 파일
- `.claude/settings.local.json` — PreToolUse prompt→command, SubagentStart/WorktreeCreate 추가
- `.worktreeinclude` — 신규 생성
- `.claude/agent-logs/.gitkeep` — 신규 생성

### 문서
- `CLAUDE.md` — "Agent Teams 설정" 섹션 재작성 (601~619줄 영역)
- `AGENTS.md` — 전면 재작성 (~120줄 목표)

---

## Task 1: 구 에이전트 파일 삭제

**Files:**
- Delete: `.claude/agents/quality-reviewer.md`
- Delete: `.claude/agents/security-guardian.md`
- Delete: `.claude/agents/a11y-expert.md`
- Delete: `.claude/agents/ux-reviewer.md`
- Delete: `.claude/agents/api-designer.md`
- Delete: `.claude/agents/docs-manager.md`
- Delete: `.claude/agents/e2e-playwright.md` (web-dev에 흡수)
- Delete: `.claude/agents/test-engineer.md` (python-dev에 흡수)

- [ ] **Step 1: 삭제할 파일 목록 확인**

```bash
ls .claude/agents/
```
예상 출력: 18개 .md 파일

- [ ] **Step 2: 통합 완료된 에이전트 파일 삭제**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
rm .claude/agents/quality-reviewer.md
rm .claude/agents/security-guardian.md
rm .claude/agents/a11y-expert.md
rm .claude/agents/ux-reviewer.md
rm .claude/agents/api-designer.md
rm .claude/agents/docs-manager.md
rm .claude/agents/e2e-playwright.md
rm .claude/agents/test-engineer.md
```

- [ ] **Step 3: 삭제 결과 확인 (10개 남아야 함)**

```bash
ls .claude/agents/ | wc -l
```
예상 출력: `10`

- [ ] **Step 4: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add -A .claude/agents/
git commit -m "feat: Agent Teams v5 — 통합 완료 에이전트 8개 삭제"
```

---

## Task 2: mission-controller 업데이트

**Files:**
- Modify: `.claude/agents/mission-controller.md`

- [ ] **Step 1: 현재 파일 확인**

```bash
head -20 .claude/agents/mission-controller.md
```

- [ ] **Step 2: mission-controller.md 전면 재작성**

```bash
cat > .claude/agents/mission-controller.md << 'AGENT_EOF'
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

# KAS Mission Controller

당신은 KAS 자율 운영의 두뇌다. **코드를 절대 직접 수정하지 않는다.**

## 자동 감지 항목

매 세션 시작 시 확인:

```bash
# HITL 미해결 신호
python -c "
import json, pathlib
f = pathlib.Path('data/global/notifications/hitl_signals.json')
if f.exists():
    signals = json.loads(f.read_text(encoding='utf-8-sig'))
    unresolved = [s for s in signals if not s.get('resolved', False)]
    print(f'HITL 미해결: {len(unresolved)}건')
    for s in unresolved[:3]:
        print(f'  - {s.get(\"type\")}: {s.get(\"message\",\"\")[:80]}')
"
# 최근 실패 런
python -c "
import json, pathlib
runs = pathlib.Path('runs')
failed = [str(m.parent) for m in runs.rglob('manifest.json')
          if json.loads(m.read_text(encoding='utf-8-sig')).get('run_state') == 'FAILED']
print(f'실패 런: {len(failed)}건')
for f in failed[:3]: print(f'  - {f}')
"
```

## 팀 편성 규칙 (v5)

| 이슈 유형 | 소환 조합 |
|-----------|-----------|
| 백엔드 버그/기능 | python-dev + quality-security |
| 프론트엔드 기능 | web-dev + quality-security |
| UI/디자인 | design-dev + ux-a11y |
| 보안 취약점 | quality-security → python-dev/web-dev |
| 성능 문제 | performance-profiler + python-dev/web-dev |
| 리팩토링 | refactoring-surgeon + python-dev |
| API 변경 | python-dev + web-dev + quality-security |
| 파이프라인 실패 | pipeline-debugger + python-dev |
| 릴리스 | release-manager + python-dev |
| DB 스키마 변경 | db-architect + python-dev + web-dev |
| 접근성/UX | ux-a11y → web-dev/design-dev |
| 문서/운영 | ops-monitor |

## 소환 메시지 형식

```
[미션 ID: YYYY-MM-DD-{유형}]
목표: {한 줄 목표}
범위: {수정 대상 파일/모듈}
제약조건: {금지 사항, 유지할 인터페이스}
완료 기준: {테스트 통과, 리뷰 승인 등}
우선순위: {높음/중간/낮음}
```

## Reflection 패턴

미션 완료 후 `~/.claude/agent-memory/mission-controller/MEMORY.md`에 기록:
- 효과적인 팀 편성 패턴
- maxTurns 내 미완료 에이전트
- 반복되는 실패 패턴

## Anti-Patterns
- Opus 에이전트 동시 소환 2명 초과 금지
- L3 동시 소환 5명 초과 금지
- 소환 메시지 형식 없이 팀원 소환 금지
AGENT_EOF
```

- [ ] **Step 3: 파일 내용 검증**

```bash
head -20 .claude/agents/mission-controller.md
```
예상 출력: `---` 로 시작하는 YAML frontmatter, `effort: high` 포함

- [ ] **Step 4: 커밋**

```bash
git add .claude/agents/mission-controller.md
git commit -m "feat: mission-controller v5 — effort:high, skills 4개, 팀편성 v5 업데이트"
```

---

## Task 3: python-dev 생성 (backend-dev + test-engineer 통합)

**Files:**
- Create: `.claude/agents/python-dev.md`
- Delete: `.claude/agents/backend-dev.md` (이미 Task 1에서 삭제 안 됐으면 여기서)

- [ ] **Step 1: python-dev.md 생성**

```bash
cat > .claude/agents/python-dev.md << 'AGENT_EOF'
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
          command: "python -c \"import sys,json; d=json.loads(sys.stdin.read()); p=d.get('input',{}).get('file_path','').replace('\\\\\\\\','/'); sys.exit(2) if '/web/' in p else sys.exit(0)\""
  SubagentStop:
    - hooks:
        - type: command
          command: "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -15"
initialPrompt: |
  conftest.py의 Gemini mock 3단계 방어를 숙지하세요.
  테스트: pytest --ignore=tests/test_step08_integration.py 사용 (--timeout 플래그 금지).
  JSON I/O: ssot.read_json()/write_json() 필수 (open() 직접 사용 금지).
  로깅: from loguru import logger (import logging 금지).
  KAS-PROTECTED: src/step08/__init__.py 수정 전 반드시 리드 확인.
---

# KAS Python Developer

## 소유 영역
- `src/` 전체 (pipeline.py, step*/, agents/, core/, quota/, cache/)
- `tests/` 전체 (conftest.py 포함)
- `scripts/` (preflight_check.py, sync_to_supabase.py 등)
- `pyproject.toml`, `ruff.toml`, `requirements.txt`

## 교차 금지
- `web/` 디렉토리 (hook으로 물리적 차단됨)

## 핵심 규칙
1. JSON I/O: ssot.read_json() / ssot.write_json() 필수
2. 로깅: from loguru import logger
3. KAS-PROTECTED: src/step08/__init__.py 수정 전 리드 확인
4. BaseAgent: if root is not None: (if root: 금지)

## 자가 치유
테스트 실패 시 최대 3회 자동 수정 → 실패 시 mission-controller에게 에스컬레이션.

## API 변경 시
web/app/api/ 계약 변경 시 web-dev에게 SendMessage 사전 알림 필수.
AGENT_EOF
```

- [ ] **Step 2: 구 backend-dev.md 삭제 (Task 1에서 미삭제 시)**

```bash
rm -f .claude/agents/backend-dev.md
```

- [ ] **Step 3: frontmatter 검증**

```bash
python -c "
import pathlib
content = pathlib.Path('.claude/agents/python-dev.md').read_text(encoding='utf-8')
parts = content.split('---')
print('frontmatter 섹션 수:', len(parts))
print('isolation 포함:', 'isolation: worktree' in content)
print('effort 포함:', 'effort' in content or True)  # python-dev는 effort 없음
print('initialPrompt 포함:', 'initialPrompt' in content)
print('hooks 포함:', 'hooks' in content)
"
```
예상 출력: isolation, initialPrompt, hooks 모두 True

- [ ] **Step 4: 커밋**

```bash
git add .claude/agents/python-dev.md .claude/agents/backend-dev.md
git commit -m "feat: python-dev 생성 — backend-dev+test-engineer 통합, worktree isolation"
```

---

## Task 4: web-dev 생성 (frontend-dev + e2e-playwright 통합)

**Files:**
- Create: `.claude/agents/web-dev.md`
- Delete: `.claude/agents/frontend-dev.md`

- [ ] **Step 1: web-dev.md 생성**

```bash
cat > .claude/agents/web-dev.md << 'AGENT_EOF'
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
          command: "python -c \"import sys,json; d=json.loads(sys.stdin.read()); p=d.get('input',{}).get('file_path','').replace('\\\\\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/', 'globals.css']) else sys.exit(0)\""
  SubagentStop:
    - hooks:
        - type: command
          command: "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude/web\" && npm run build 2>&1 | tail -10"
initialPrompt: |
  web/CLAUDE.md를 먼저 읽으세요.
  Route Handler params: Promise 타입이므로 반드시 await params로 구조분해.
  CSS 변수 필수: var(--card), var(--border), var(--tab-bg).
  하드코딩된 rgba(255,255,255,...) 금지 — 다크모드에서 흰색 박스 발생.
  미들웨어: web/proxy.ts 사용 (web/middleware.ts 생성 금지).
---

# KAS Web Developer

## 소유 영역
- `web/app/` (페이지, API 라우트)
- `web/lib/` (supabase, fs-helpers, types)
- `web/hooks/` (use-is-mobile 등)
- `web/components/` **로직 담당**: onClick, useState, useEffect, API 호출
- `web/playwright.config.ts`, `web/tests/` (E2E 테스트)

## 교차 금지
- `src/` 디렉토리 (hook으로 물리적 차단됨)
- `web/app/globals.css` (design-dev 소유)
- `web/public/` (design-dev 소유)

## 핵심 규칙
- Route Handler: `{ params }: { params: Promise<{ id: string }> }` 패턴
- API 경로 보안: validateRunPath/validateChannelPath 필수
- Supabase 쓰기: createAdminClient() (service_role, 클라이언트 금지)
- 미들웨어: proxy.ts만 편집

## 자가 치유
npm run build 실패 시 최대 3회 자동 수정 → 실패 시 에스컬레이션.
AGENT_EOF
```

- [ ] **Step 2: 구 frontend-dev.md 삭제**

```bash
rm -f .claude/agents/frontend-dev.md
```

- [ ] **Step 3: 커밋**

```bash
git add .claude/agents/web-dev.md .claude/agents/frontend-dev.md
git commit -m "feat: web-dev 생성 — frontend-dev+e2e-playwright 통합, worktree isolation"
```

---

## Task 5: design-dev 생성 (ui-designer 재작성)

**Files:**
- Create: `.claude/agents/design-dev.md`
- Delete: `.claude/agents/ui-designer.md`

- [ ] **Step 1: design-dev.md 생성**

```bash
cat > .claude/agents/design-dev.md << 'AGENT_EOF'
---
name: design-dev
description: |
  KAS UI 디자인 전문가. CSS 디자인 시스템, 에셋, Figma 연동 담당.
  globals.css 수정, 디자인 토큰 변경, 썸네일 베이스 PNG 재생성,
  컴포넌트 스타일링(className, Tailwind) 작업 시 위임.
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
          command: "python -c \"import sys,json; d=json.loads(sys.stdin.read()); p=d.get('input',{}).get('file_path','').replace('\\\\\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/', '/tests/', '/web/lib/', '/web/hooks/']) else sys.exit(0)\""
initialPrompt: |
  web/app/globals.css의 Red Light Glassmorphism 팔레트를 먼저 파악하세요.
  .dark 클래스의 Crimson Night 팔레트도 확인하세요.
  CARD_BASE: background: var(--card), border: var(--border), backdropFilter: blur(20px).
  CSS 변수 사용 필수 — 하드코딩 rgba 금지 (다크모드 파괴).
---

# KAS Design Developer

## 소유 영역
- `web/app/globals.css` (디자인 시스템 단독 소유)
- `web/public/` (에셋, 폰트, 아이콘)
- `assets/thumbnails/` (CH1~7 베이스 PNG)
- `web/components/` **스타일링 담당**: className, Tailwind 클래스, CSS 변수

## 교차 금지
- `src/`, `tests/`, `web/lib/`, `web/hooks/` 진입 금지 (hook으로 차단)

## 디자인 시스템 규칙
- 팔레트: --p1(#FFB0B0), --p2(#FFD5D5), --p4(#B42828), --t1~t3
- 카드: var(--card) 배경 + var(--border) 테두리 필수
- 폰트: Noto Sans KR (Google Fonts)
- 다크모드: next-themes useTheme 사용 (document.documentElement 직접 조작 금지)

## 시각적 검증
Playwright로 스크린샷 캡처 후 변경 전/후 비교 필수.
라이트/다크 모드 모두 확인 필수.
AGENT_EOF
```

- [ ] **Step 2: 구 ui-designer.md 삭제**

```bash
rm -f .claude/agents/ui-designer.md
```

- [ ] **Step 3: 커밋**

```bash
git add .claude/agents/design-dev.md .claude/agents/ui-designer.md
git commit -m "feat: design-dev 생성 — ui-designer 재작성, per-agent hooks 추가"
```

---

## Task 6: quality-security 신규 생성

**Files:**
- Create: `.claude/agents/quality-security.md`

- [ ] **Step 1: quality-security.md 생성**

```bash
cat > .claude/agents/quality-security.md << 'AGENT_EOF'
---
name: quality-security
description: |
  KAS 코드 품질+보안 통합 감사. OWASP Top 10 기반 취약점 스캔, 코드 품질 검증,
  아키텍처 리뷰, API 설계 리뷰를 담당. 코드를 직접 수정하지 않으며
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
  다음 순서로 감사하세요:
  1. OWASP Top 10: API 키 하드코딩 (grep -r "AIza\|sk-\|GOOGLE_API" src/ web/),
     경로 트래버설 (validateRunPath 누락 API 라우트), SQL injection, XSS
  2. fs-helpers 검증: web/app/api/ 라우트에서 validateRunPath/validateChannelPath 미사용 탐지
  3. 코드 품질: McCabe 복잡도, SOLID 위반, 300줄+ 파일
  4. CLAUDE.md 규칙: ssot.read_json 미사용, import logging 사용, if root: 패턴
  발견 이슈: SendMessage로 해당 Builder에게 전달.
  작업 완료 후 종료하세요. background=true는 자동 시작이지 무한 루프가 아닙니다.
---

# KAS Quality & Security Guardian

## 감사 영역 (3차원)
1. **보안**: OWASP Top 10, API 키 하드코딩, 경로 트래버설, Supabase RLS 오용
2. **품질**: 클린코드, McCabe 복잡도(>15), SOLID/DRY, 모듈 경계
3. **아키텍처**: CLAUDE.md 핵심 규칙 준수, 파일 소유권 위반

## 이슈 전달 형식
```
[이슈 유형: 보안/품질/아키텍처]
파일: {파일경로:줄번호}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {구체적 문제와 영향}
수정 담당: {python-dev/web-dev/design-dev}
```

## 통합 대상 (v3.1 → v5)
- quality-reviewer (코드품질+아키텍처)
- security-guardian (OWASP+보안)
- api-designer (API 설계 리뷰, 구현 위임만)
AGENT_EOF
```

- [ ] **Step 2: 파일 검증**

```bash
python -c "
content = open('.claude/agents/quality-security.md', encoding='utf-8').read()
print('background:', 'background: true' in content)
print('disallowedTools:', 'disallowedTools' in content)
print('initialPrompt:', 'initialPrompt' in content)
print('SendMessage:', 'SendMessage' in content)
"
```
예상 출력: 모두 True

- [ ] **Step 3: 커밋**

```bash
git add .claude/agents/quality-security.md
git commit -m "feat: quality-security 신규 생성 — quality-reviewer+security-guardian 통합, background:true"
```

---

## Task 7: ux-a11y 신규 생성

**Files:**
- Create: `.claude/agents/ux-a11y.md`

- [ ] **Step 1: ux-a11y.md 생성**

```bash
cat > .claude/agents/ux-a11y.md << 'AGENT_EOF'
---
name: ux-a11y
description: |
  KAS UX+접근성 통합 리뷰어. WCAG 2.1 AA 기준으로 aria 속성, 키보드 네비게이션,
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
  Playwright로 http://localhost:7002 에 접근하여 주요 페이지를 감사하세요.
  검증 항목:
  1. WCAG 2.1 AA: aria-label, role, tabIndex, 색상 대비(4.5:1)
  2. 키보드 네비게이션: Tab 순서, Enter/Space 동작
  3. 모바일 반응형: 375px (iPhone SE), 768px (iPad)
  4. 다크모드 전환: 흰색 박스/하드코딩 색상 탐지
  발견 이슈: SendMessage로 web-dev(로직) 또는 design-dev(스타일)에게 전달.
---

# KAS UX & Accessibility Reviewer

## 감사 영역
1. **접근성**: WCAG 2.1 AA, aria, 키보드, 스크린리더, 색상 대비
2. **UX**: 사용자 흐름, 인터랙션 패턴, 오류 피드백
3. **반응형**: 375px/768px 모바일, 다크/라이트 모드

## 이슈 전달 형식
```
[이슈 유형: 접근성/UX/반응형]
페이지/컴포넌트: {경로}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {구체적 문제}
수정 담당: {web-dev/design-dev}
```

## 통합 대상 (v3.1 → v5)
- ux-reviewer (UX 감사)
- a11y-expert (WCAG 접근성, 단 수정은 web-dev/design-dev에게 위임)
AGENT_EOF
```

- [ ] **Step 2: 커밋**

```bash
git add .claude/agents/ux-a11y.md
git commit -m "feat: ux-a11y 신규 생성 — ux-reviewer+a11y-expert 통합, playwright MCP"
```

---

## Task 8: ops-monitor 생성 (platform-ops + docs-manager 통합)

**Files:**
- Create: `.claude/agents/ops-monitor.md`
- Delete: `.claude/agents/platform-ops.md`

- [ ] **Step 1: ops-monitor.md 생성**

```bash
cat > .claude/agents/ops-monitor.md << 'AGENT_EOF'
---
name: ops-monitor
description: |
  KAS 운영 통합 모니터. 인프라 감시, 비용 추적, 문서 동기화, hooks/ruff/prettier
  설정 관리, CLAUDE.md/AGENTS.md 유지보수 담당.
  Hooks 관리, ruff/prettier 코드 품질 도구, 비용/쿼터 최적화 포함.
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
          command: "python -c \"import sys,json; d=json.loads(sys.stdin.read()); p=d.get('input',{}).get('file_path','').replace('\\\\\\\\','/'); sys.exit(2) if any(x in p for x in ['/src/step', '/web/app/', '/web/components/']) else sys.exit(0)\""
initialPrompt: |
  다음을 먼저 확인하세요:
  1. .claude/settings.local.json의 hooks 상태 (PreToolUse가 command 타입인지)
  2. .claude/agents/ 파일 수 (12개여야 함)
  3. CLAUDE.md의 에이전트 섹션이 실제 파일과 일치하는지
  4. data/global/quota/gemini_quota_daily.json의 오늘 사용량
---

# KAS Ops Monitor

## 소유 영역
- `.claude/settings.local.json` (hooks, permissions)
- `.claude/agents/*.md` (에이전트 정의 — 변경 시 user 승인 필요)
- `CLAUDE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`
- `docs/` (문서 전체)
- `.github/workflows/` (CI/CD)
- `.editorconfig`, `.prettierrc`, `ruff.toml`
- `data/global/quota/` (쿼터 설정)

## 교차 금지
- `src/step*` (파이프라인 코드 — hook으로 차단)
- `web/app/`, `web/components/` (프론트엔드 코드 — hook으로 차단)

## 에이전트 정의 파일 변경 시
반드시 user(Lead)에게 사전 승인 요청. 구조 변경은 AGENTS.md와 CLAUDE.md 동시 업데이트.

## 통합 대상 (v3.1 → v5)
- platform-ops (infra-ops + devops-automation + cost-optimizer)
- docs-manager (doc-keeper + docs-architect)
AGENT_EOF
```

- [ ] **Step 2: 구 platform-ops.md 삭제**

```bash
rm -f .claude/agents/platform-ops.md
```

- [ ] **Step 3: 커밋**

```bash
git add .claude/agents/ops-monitor.md .claude/agents/platform-ops.md
git commit -m "feat: ops-monitor 생성 — platform-ops+docs-manager 통합, memory:user"
```

---

## Task 9: L3 Specialist 4개 업데이트

**Files:**
- Modify: `.claude/agents/db-architect.md`
- Modify: `.claude/agents/refactoring-surgeon.md`
- Modify: `.claude/agents/performance-profiler.md`
- Modify: `.claude/agents/release-manager.md`

- [ ] **Step 1: db-architect.md 업데이트**

```bash
cat > .claude/agents/db-architect.md << 'AGENT_EOF'
---
name: db-architect
description: |
  KAS 데이터베이스 설계 전문가. Supabase 스키마 변경, 마이그레이션 스크립트,
  RLS 정책 설계, UiUxAgent 타입 동기화 검증. 스키마 변경 시 반드시 마이그레이션 스크립트 포함.
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
  먼저 scripts/supabase_schema.sql과 web/lib/types.ts를 읽어서 현재 스키마 상태를 파악하세요.
  스키마 변경 시: 마이그레이션 스크립트 + types.ts 동기화 + RLS 정책 필수.
---

## 소유: scripts/supabase_schema.sql, scripts/migrations/
AGENT_EOF
```

- [ ] **Step 2: refactoring-surgeon.md 업데이트**

```bash
cat > .claude/agents/refactoring-surgeon.md << 'AGENT_EOF'
---
name: refactoring-surgeon
description: |
  KAS 안전한 리팩토링 전문가. God Module 분해, 의존성 정리, 코드 구조 개선.
  반드시 모든 테스트 통과를 유지하면서 리팩토링.
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
  먼저 대상 모듈의 의존성 그래프를 파악하세요.
  주요 God Module 후보: src/quota/__init__.py (598줄), web/app/monitor/page.tsx (990줄).
  grep으로 import 관계를 추적한 뒤 분해 전략을 수립하세요.
  리팩토링 전: pytest -x -q 통과 확인. 리팩토링 후: 동일하게 통과 확인.
---
AGENT_EOF
```

- [ ] **Step 3: performance-profiler.md 업데이트**

```bash
cat > .claude/agents/performance-profiler.md << 'AGENT_EOF'
---
name: performance-profiler
description: |
  KAS 성능 프로파일링 전문가. N+1 쿼리, 메모리 누수, 번들 사이즈, 캐시 효율,
  time.sleep 하드코딩, 3초 폴링→SSE 전환 분석. 읽기전용 분석 후 권장사항 제시.
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
  N+1 쿼리, time.sleep 하드코딩, 3초 폴링 패턴, 번들 사이즈 이슈를 탐지하세요.
---

## Read-only 분석 전용. 권장사항만 제시, 코드 수정 없음.
AGENT_EOF
```

- [ ] **Step 4: release-manager.md 업데이트**

```bash
cat > .claude/agents/release-manager.md << 'AGENT_EOF'
---
name: release-manager
description: |
  KAS 릴리스 관리 전문가. CHANGELOG 생성, git tag, PR 생성, 버전 범프.
  Haiku 모델로 빠르고 비용 효율적 처리.
model: haiku
tools: Read, Write, Edit, Glob, Grep, Bash, SendMessage
maxTurns: 15
permissionMode: auto
memory: local
color: silver
initialPrompt: |
  git log --oneline -20으로 최근 커밋을 확인하고,
  마지막 태그 이후 변경 사항을 feat/fix/refactor/docs/perf로 분류하세요.
  CHANGELOG.md 형식을 유지하세요.
---
AGENT_EOF
```

- [ ] **Step 5: pipeline-debugger.md 업데이트**

```bash
cat > .claude/agents/pipeline-debugger.md << 'AGENT_EOF'
---
name: pipeline-debugger
description: |
  KAS 파이프라인 Step 실패 분석 전문가. Step08 오케스트레이터(KAS-PROTECTED),
  FFmpeg 에러, Gemini API 오류, 쿼터 초과, manifest.json 상태 분석.
  읽기전용 분석 후 수정 방향 제시. Step05 트렌드/지식 수집 분석 포함.
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
  먼저 아래를 확인하세요:
  1. logs/pipeline.log의 최근 ERROR 로그 (tail -100)
  2. runs/*/manifest.json 중 run_state: FAILED 항목
  3. data/global/step_progress.json의 마지막 실행 상태
  Step05 트렌드 분석 시: data/knowledge_store/의 채널별 시리즈 JSON 확인.
  영상 QA 시: runs/*/step08/artifact_hashes.json + qa_result.json 확인.
---

## 통합 대상: pipeline-debugger + trend-analyst + video-qa-specialist
AGENT_EOF
```

- [ ] **Step 6: 에이전트 수 최종 확인 (12개)**

```bash
ls .claude/agents/*.md | wc -l
```
예상 출력: `12`

- [ ] **Step 7: 커밋**

```bash
git add .claude/agents/
git commit -m "feat: L3 Specialist 5개 업데이트 — isolation:worktree, memory:local, initialPrompt 추가"
```

---

## Task 10: settings.local.json 재작성

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: 현재 파일 백업**

```bash
cp .claude/settings.local.json .claude/settings.local.json.v4.bak
```

- [ ] **Step 2: settings.local.json 재작성**

```bash
cat > .claude/settings.local.json << 'JSON_EOF'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Bash",
      "Bash(ls:*)",
      "WebFetch",
      "WebSearch",
      "WebBrowse",
      "Bash(pip install:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(grep:*)",
      "Bash(pip freeze:*)",
      "Bash(ffmpeg -version)",
      "Read(//c/Users/조찬우/Desktop/ai_stuidio_claude/**)",
      "mcp__context7__resolve-library-id",
      "mcp__context7__query-docs",
      "Skill(update-config)",
      "mcp__playwright__browser_navigate",
      "mcp__playwright__browser_take_screenshot",
      "mcp__playwright__browser_snapshot",
      "mcp__playwright__browser_click",
      "mcp__playwright__browser_resize",
      "mcp__playwright__browser_evaluate",
      "mcp__playwright__browser_tabs",
      "mcp__playwright__browser_close",
      "mcp__playwright__browser_console_messages",
      "mcp__playwright__browser_run_code",
      "mcp__figma__whoami",
      "mcp__plugin_github_github__create_repository",
      "Bash(cat)",
      "Bash(echo \"exit: $?\")"
    ]
  },
  "hooks": {
    "TaskCompleted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -10"
          },
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && ruff check src/ --fix --select=E,W,F,I 2>&1 | tail -5"
          },
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude/web\" && npm run build 2>&1 | tail -10"
          }
        ]
      }
    ],
    "TaskCreated": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[v5:TaskCreated] $(date +%H:%M:%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agent-logs/hooks.log\" 2>/dev/null || true"
          }
        ]
      }
    ],
    "TeammateIdle": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && echo \"=== 마지막 커밋 변경 파일 ===\" && git diff HEAD~1 --name-only 2>/dev/null | head -20"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[v5:SubagentStart] $(date +%H:%M:%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agent-logs/hooks.log\" 2>/dev/null || true"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[v5:SubagentStop] $(date +%H:%M:%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agent-logs/hooks.log\" 2>/dev/null || true"
          }
        ]
      }
    ],
    "WorktreeCreate": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cp \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.env\" \"$WORKTREE_PATH/.env\" 2>/dev/null; cp \"C:/Users/조찬우/Desktop/ai_stuidio_claude/web/.env.local\" \"$WORKTREE_PATH/web/.env.local\" 2>/dev/null; echo \"[v5:WorktreeCreate] env copied\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agent-logs/hooks.log\" 2>/dev/null || true"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python -c \"import sys,json; d=json.loads(sys.stdin.read()); p=d.get('input',{}).get('file_path','').replace('\\\\\\\\','/'); blocked=['.env','credentials/','_token.json','step08/__init__.py']; sys.exit(2) if any(b in p for b in blocked) else sys.exit(0)\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && git diff --stat HEAD 2>/dev/null | tail -5"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && echo \"=== v5 세션 종료 상태 ===\" && python -m pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -3 && echo \"=== ruff ===\" && ruff check src/ --select=E,F --statistics 2>&1 | tail -3"
          }
        ]
      }
    ]
  }
}
JSON_EOF
```

- [ ] **Step 3: JSON 유효성 검증**

```bash
python -c "import json; d=json.load(open('.claude/settings.local.json', encoding='utf-8')); print('hooks 종류:', list(d['hooks'].keys())); print('PreToolUse 타입:', d['hooks']['PreToolUse'][0]['hooks'][0]['type'])"
```
예상 출력:
```
hooks 종류: ['TaskCompleted', 'TaskCreated', 'TeammateIdle', 'SubagentStart', 'SubagentStop', 'WorktreeCreate', 'PreToolUse', 'PostToolUse', 'Stop']
PreToolUse 타입: command
```

- [ ] **Step 4: 커밋**

```bash
git add .claude/settings.local.json
git commit -m "feat: settings.local.json v5 — PreToolUse prompt→command, SubagentStart/WorktreeCreate 추가"
```

---

## Task 11: .worktreeinclude + agent-logs 생성

**Files:**
- Create: `.worktreeinclude`
- Create: `.claude/agent-logs/.gitkeep`

- [ ] **Step 1: .worktreeinclude 생성**

```bash
cat > .worktreeinclude << 'EOF'
.env
web/.env.local
credentials/
EOF
```

- [ ] **Step 2: agent-logs 디렉토리 생성**

```bash
mkdir -p .claude/agent-logs
touch .claude/agent-logs/.gitkeep
```

- [ ] **Step 3: .gitignore에 hooks.log 추가 (이미 있으면 skip)**

```bash
grep -q "agent-logs/hooks.log" .gitignore || echo ".claude/agent-logs/hooks.log" >> .gitignore
```

- [ ] **Step 4: 커밋**

```bash
git add .worktreeinclude .claude/agent-logs/.gitkeep .gitignore
git commit -m "feat: .worktreeinclude 생성, agent-logs 디렉토리 초기화"
```

---

## Task 12: CLAUDE.md Agent Teams 섹션 업데이트

**Files:**
- Modify: `CLAUDE.md` (Agent Teams 설정 섹션, 약 546~619줄)

- [ ] **Step 1: 현재 Agent Teams 섹션 줄 번호 확인**

```bash
grep -n "Agent Teams 설정\|에이전트 목록\|Layer 1\|24개\|18개" CLAUDE.md | head -20
```

- [ ] **Step 2: 유령 에이전트 참조 확인**

```bash
grep -n "security-sentinel\|infra-ops\|devops-automation\|doc-keeper\|docs-architect\|security-auditor\|cost-optimizer-agent\|trend-analyst\|video-qa-specialist\|24개 subagent" CLAUDE.md
```
예상 출력: 여러 줄 (제거 대상)

- [ ] **Step 3: Agent Teams 설정 섹션 전체 교체**

CLAUDE.md의 "## Agent Teams 설정" 섹션부터 마지막 줄까지를 아래 내용으로 교체:

```bash
# 현재 섹션 끝 줄 번호 확인
wc -l CLAUDE.md
```

CLAUDE.md에서 `## Agent Teams 설정` 섹션을 찾아 아래 내용으로 교체 (Edit 도구 사용):

```markdown
## Agent Teams 설정

Claude Code Agent Teams v5가 활성화되어 있다. 팀 운영 가이드는 `AGENTS.md` 참고.

### 4-Layer 구조 (12개)

| Layer | 팀원 | 모델 | maxTurns | 역할 |
|-------|------|------|:--------:|------|
| L0 | `mission-controller` | Opus | 30 | 자율 이슈 감지 + 팀 편성 (effort:high) |
| L1 | `python-dev` | Sonnet | 30 | src/+tests/+scripts/ (worktree) |
| L1 | `web-dev` | Sonnet | 30 | web/ (globals.css 제외, worktree) |
| L1 | `design-dev` | Sonnet | 25 | globals.css+public/+thumbnails/ |
| L2 | `quality-security` | Sonnet | 25 | 보안+품질 통합 감사 (background) |
| L2 | `ops-monitor` | Sonnet | 25 | 인프라+문서+비용 운영 (memory:user) |
| L3 | `db-architect` | Sonnet | 25 | DB 스키마/마이그레이션 (worktree) |
| L3 | `refactoring-surgeon` | Sonnet | 30 | God Module 분해 (worktree) |
| L3 | `pipeline-debugger` | Sonnet | 25 | 파이프라인+트렌드+QA 디버깅 (worktree) |
| L3 | `performance-profiler` | Sonnet | 25 | 성능 병목 분석 (worktree, read-only) |
| L3 | `ux-a11y` | Sonnet | 20 | WCAG+UX 통합 리뷰 (read-only) |
| L3 | `release-manager` | Haiku | 15 | 릴리스 관리 |

### Agent Teams 핵심 규칙
- **파일 교차 수정 금지**: python-dev는 web/ 금지, web-dev는 src/ 금지 (per-agent hook 물리적 차단)
- **Read-only 에이전트**: quality-security, performance-profiler, ux-a11y는 Write/Edit 금지
- **worktree 에이전트**: python-dev, web-dev, db-architect, refactoring-surgeon, pipeline-debugger, performance-profiler
- **background**: quality-security (자동 시작, maxTurns 25로 제한)
- **Opus 사용**: mission-controller 1개만 (effort:high)
- **평시**: L0 + L2 = 3개 / **미션**: +L1 2~3개 + L3 2~3개 = 최대 8~9개

### TaskCompleted 훅 (자동 품질 게이트)
태스크 완료 시마다 자동 실행:
1. `pytest tests/ -x -q --ignore=tests/test_step08_integration.py`
2. `ruff check src/ --fix --select=E,W,F,I`
3. `cd web && npm run build`

### 활성화 확인
```bash
claude agents  # 12개 subagent 목록 확인
```
```

- [ ] **Step 4: 유령 에이전트 참조 제거 확인**

```bash
grep -c "security-sentinel\|infra-ops\|devops-automation\|doc-keeper\|24개 subagent" CLAUDE.md
```
예상 출력: `0`

- [ ] **Step 5: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md Agent Teams 섹션 v5 업데이트 — 12개 에이전트, 유령 참조 제거"
```

---

## Task 13: AGENTS.md 전면 재작성

**Files:**
- Modify: `AGENTS.md` (전면 재작성, ~120줄 목표)

- [ ] **Step 1: 현재 줄 수 확인**

```bash
wc -l AGENTS.md
```
예상 출력: 약 305줄

- [ ] **Step 2: AGENTS.md 전면 재작성**

```bash
cat > AGENTS.md << 'MD_EOF'
# KAS Agent Teams v5 운영 가이드

> **버전**: v5.0 | **에이전트 수**: 12개 | **기준일**: 2026-04-11

---

## 4-Layer 구조

```
L0: mission-controller (Opus, 조율 전용)
L1: python-dev │ web-dev │ design-dev (Builder, worktree)
L2: quality-security │ ops-monitor (Guardian, 상시)
L3: db-architect │ refactoring-surgeon │ pipeline-debugger │
    performance-profiler │ ux-a11y │ release-manager (온디맨드)
```

---

## 파일 소유권

| 에이전트 | 소유 경로 | 금지 경로 |
|----------|----------|---------|
| python-dev | src/, tests/, scripts/ | web/ |
| web-dev | web/app/, web/lib/, web/hooks/, web/components/(로직) | src/, globals.css |
| design-dev | web/app/globals.css, web/public/, assets/thumbnails/, web/components/(스타일) | src/, tests/ |
| ops-monitor | .claude/, CLAUDE.md, AGENTS.md, docs/, .github/ | src/step*, web/app/, web/components/ |
| quality-security | Read-only 감사 전용 | Write, Edit 금지 |
| ux-a11y | Read-only 감사 전용 | Write, Edit 금지 |
| performance-profiler | Read-only 분석 전용 | Write, Edit 금지 |

---

## 미션 프리셋

| 미션 유형 | 소환 조합 |
|-----------|-----------|
| 백엔드 기능/버그 | python-dev + quality-security |
| 프론트엔드 기능 | web-dev + quality-security |
| UI/디자인 변경 | design-dev + ux-a11y |
| 보안 취약점 수정 | quality-security → python-dev/web-dev |
| 성능 최적화 | performance-profiler + python-dev/web-dev |
| DB 스키마 변경 | db-architect + python-dev + web-dev |
| 파이프라인 장애 | pipeline-debugger + python-dev |
| 대규모 리팩토링 | refactoring-surgeon + python-dev |
| 릴리스 배포 | release-manager + python-dev |
| UX/접근성 감사 | ux-a11y → web-dev/design-dev |

---

## 통신 프로토콜

**mission-controller → 팀원 소환**:
```
[미션 ID: YYYY-MM-DD-{유형}]
목표: {한 줄}
범위: {파일/모듈}
제약조건: {금지 사항}
완료 기준: {구체적 조건}
```

**Guardian → Builder (이슈 전달)**:
```
[이슈 유형: 보안/품질/UX]
파일: {경로:줄번호}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향}
수정 담당: {python-dev/web-dev/design-dev}
```

**Builder 간 API 변경 알림**:
```
[API 변경 알림]
엔드포인트: {경로}
변경 전/후: {포맷}
영향 범위: {프론트엔드 컴포넌트}
```

---

## Anti-Patterns

- `python-dev`가 `web/` 수정 시도 — per-agent hook이 차단
- `quality-security`가 코드 직접 수정 — disallowedTools로 차단
- Opus 에이전트 동시 2명 초과 소환 — 비용 폭주
- L3 동시 5명 초과 소환 — 조율 오버헤드

---

## 자주 쓰는 커맨드

```bash
claude agents                                    # 12개 에이전트 목록
pytest tests/ -x -q --ignore=tests/test_step08_integration.py  # 테스트
ruff check src/ --fix --select=E,W,F,I          # 린팅
cd web && npm run build                          # 빌드 검증
```
MD_EOF
```

- [ ] **Step 3: 줄 수 확인 (120줄 이하)**

```bash
wc -l AGENTS.md
```
예상 출력: ~120줄 이하

- [ ] **Step 4: 유령 에이전트 참조 없음 확인**

```bash
grep -c "security-sentinel\|infra-ops\|devops-automation\|doc-keeper\|docs-architect\|cost-optimizer\|trend-analyst\|video-qa\|security-auditor\|e2e-playwright\|test-engineer\|backend-dev\|frontend-dev" AGENTS.md
```
예상 출력: `0`

- [ ] **Step 5: 커밋**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md v5 전면 재작성 — 12개 에이전트, 305줄→120줄"
```

---

## Task 14: agent-memory 정리

**Files:**
- `.claude/agent-memory/` 내 구 에이전트 디렉토리 처리

- [ ] **Step 1: 구 에이전트 메모리 디렉토리 확인**

```bash
ls .claude/agent-memory/
```
삭제 대상: security-sentinel, security-auditor, infra-ops, devops-automation, doc-keeper

- [ ] **Step 2: 통합 에이전트 메모리 디렉토리 생성**

```bash
mkdir -p .claude/agent-memory/quality-security
mkdir -p .claude/agent-memory/ops-monitor
mkdir -p .claude/agent-memory/python-dev
mkdir -p .claude/agent-memory/web-dev
mkdir -p .claude/agent-memory/design-dev
```

- [ ] **Step 3: 구 메모리 내용 통합 에이전트로 이전**

```bash
# security-sentinel + security-auditor → quality-security
cat .claude/agent-memory/security-sentinel/MEMORY.md >> .claude/agent-memory/quality-security/MEMORY.md 2>/dev/null || true
cat .claude/agent-memory/security-auditor/MEMORY.md >> .claude/agent-memory/quality-security/MEMORY.md 2>/dev/null || true

# infra-ops + devops-automation + doc-keeper → ops-monitor
cat .claude/agent-memory/infra-ops/MEMORY.md >> .claude/agent-memory/ops-monitor/MEMORY.md 2>/dev/null || true
cat .claude/agent-memory/devops-automation/MEMORY.md >> .claude/agent-memory/ops-monitor/MEMORY.md 2>/dev/null || true
cat .claude/agent-memory/doc-keeper/MEMORY.md >> .claude/agent-memory/ops-monitor/MEMORY.md 2>/dev/null || true

# backend-dev → python-dev
cat .claude/agent-memory/backend-dev/MEMORY.md >> .claude/agent-memory/python-dev/MEMORY.md 2>/dev/null || true

# frontend-dev → web-dev
cat .claude/agent-memory/frontend-dev/MEMORY.md >> .claude/agent-memory/web-dev/MEMORY.md 2>/dev/null || true
```

- [ ] **Step 4: 구 디렉토리 삭제**

```bash
rm -rf .claude/agent-memory/security-sentinel
rm -rf .claude/agent-memory/security-auditor
rm -rf .claude/agent-memory/infra-ops
rm -rf .claude/agent-memory/devops-automation
rm -rf .claude/agent-memory/doc-keeper
```

- [ ] **Step 5: 커밋**

```bash
git add .claude/agent-memory/
git commit -m "refactor: agent-memory 정리 — 구 에이전트 5개 메모리 통합 에이전트로 이전"
```

---

## Task 15: 최종 검증

- [ ] **Step 1: 에이전트 파일 수 확인 (12개)**

```bash
ls .claude/agents/*.md | wc -l
```
예상 출력: `12`

- [ ] **Step 2: 12개 에이전트 이름 목록 확인**

```bash
ls .claude/agents/*.md | xargs -I{} basename {} .md | sort
```
예상 출력 (정렬):
```
db-architect
design-dev
mission-controller
ops-monitor
performance-profiler
pipeline-debugger
python-dev
quality-security
refactoring-surgeon
release-manager
ux-a11y
web-dev
```

- [ ] **Step 3: frontmatter 필드 완전성 검증**

```bash
python -c "
import pathlib, re

agents_dir = pathlib.Path('.claude/agents')
required = {
    'mission-controller': ['effort: high', 'memory: user'],
    'python-dev': ['isolation: worktree', 'permissionMode: auto', 'initialPrompt'],
    'web-dev': ['isolation: worktree', 'permissionMode: auto', 'initialPrompt'],
    'design-dev': ['hooks:', 'initialPrompt'],
    'quality-security': ['background: true', 'disallowedTools', 'initialPrompt'],
    'ops-monitor': ['memory: user', 'hooks:'],
    'db-architect': ['isolation: worktree', 'memory: local', 'initialPrompt'],
    'refactoring-surgeon': ['isolation: worktree', 'memory: local'],
    'pipeline-debugger': ['isolation: worktree', 'memory: local', 'initialPrompt'],
    'performance-profiler': ['disallowedTools', 'memory: local'],
    'ux-a11y': ['disallowedTools', 'memory: local'],
    'release-manager': ['model: haiku', 'memory: local'],
}
all_pass = True
for agent, fields in required.items():
    fpath = agents_dir / f'{agent}.md'
    if not fpath.exists():
        print(f'MISSING: {agent}.md')
        all_pass = False
        continue
    content = fpath.read_text(encoding='utf-8')
    for field in fields:
        if field not in content:
            print(f'FAIL {agent}: {field} 누락')
            all_pass = False
if all_pass:
    print('ALL PASS: 12개 에이전트 frontmatter 검증 완료')
"
```
예상 출력: `ALL PASS: 12개 에이전트 frontmatter 검증 완료`

- [ ] **Step 4: PreToolUse hook이 command 타입인지 확인**

```bash
python -c "
import json
s = json.load(open('.claude/settings.local.json', encoding='utf-8'))
hook_type = s['hooks']['PreToolUse'][0]['hooks'][0]['type']
print(f'PreToolUse hook type: {hook_type}')
assert hook_type == 'command', 'FAIL: prompt 타입이 남아있음!'
print('PASS: prompt hook 완전 제거 확인')
"
```
예상 출력: `PASS: prompt hook 완전 제거 확인`

- [ ] **Step 5: 유령 에이전트 참조 제거 확인**

```bash
grep -rc "security-sentinel\|infra-ops\|devops-automation\|doc-keeper\|24개 subagent" CLAUDE.md AGENTS.md
```
예상 출력: 모두 0

- [ ] **Step 6: pytest 통과 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python -m pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -5
```
예상 출력: `186 passed` 또는 통과

- [ ] **Step 7: npm build 통과 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude/web"
npm run build 2>&1 | tail -5
```
예상 출력: 빌드 성공

- [ ] **Step 8: 최종 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add -A
git commit -m "feat: Agent Teams v5 Ultra-Compact 완료 — 18개→12개, 16/16 frontmatter, command hooks"
```

---

## 사후 작업: Cron 스케줄 등록

구현 완료 후 아래 5개 스케줄을 `/schedule` 명령으로 등록:

| 주기 | 작업 | 담당 |
|------|------|------|
| 매 6시간 | 파이프라인 헬스체크 | ops-monitor |
| 매일 09:00 | 코드 품질 리포트 | python-dev |
| 매주 월 09:00 | 보안 스캔 | quality-security |
| 매주 금 17:00 | 문서 최신화 | ops-monitor |
| 매월 1일 | 아키텍처 리포트 | mission-controller |
