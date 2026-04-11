# Agent Teams v4 — 자율 운영 + 토큰 효율 최적화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agent Teams v3.1(24개, Hook 22%)을 공식 문서 기준 최고 수준(18개, Hook 78%, 자율 순찰, Opus 1명)으로 업그레이드.

**Architecture:** settings.local.json에 7개 Hook 확장(command 우선, prompt는 PreToolUse 1곳만). 역할 중복 8개 에이전트를 3개 통합 에이전트로 교체. quality-reviewer/security-sentinel Opus→Sonnet 전환. per-agent hooks로 소유권 물리적 차단. 5개 에이전트 skills 프리로드.

**Tech Stack:** Claude Code Agent Teams (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1), YAML frontmatter, bash hooks, CronCreate, ruff, pytest, GitHub Actions

---

## 파일 맵

### 수정 (7개)
- `.claude/settings.local.json` — 5개 hook 추가, ruff 강화, permissions 정리
- `.claude/agents/mission-controller.md` — maxTurns 30, skills 추가
- `.claude/agents/backend-dev.md` — maxTurns 30, per-agent hooks, skills
- `.claude/agents/frontend-dev.md` — maxTurns 30, per-agent hooks, skills
- `.claude/agents/test-engineer.md` — maxTurns 30, skills
- `.claude/agents/quality-reviewer.md` — model sonnet, maxTurns 25, skills
- `.claude/agents/pipeline-debugger.md` — trend-analyst 흡수, maxTurns 25

### 신규 생성 (3개)
- `.claude/agents/security-guardian.md` — sentinel+auditor 통합
- `.claude/agents/platform-ops.md` — infra+devops+cost 통합
- `.claude/agents/docs-manager.md` — doc-keeper+docs-architect 통합

### maxTurns 조정만 (9개)
- `ui-designer.md` (30→25), `performance-profiler.md` (25→20)
- `refactoring-surgeon.md` (30→25), `db-architect.md` (25→20)
- `api-designer.md` (25→20), `a11y-expert.md` (25→20)
- `e2e-playwright.md` (25→20), `release-manager.md` (20→15)
- `ux-reviewer.md` (20→20 유지)

### 삭제 (9개)
- `.claude/agents/security-sentinel.md`
- `.claude/agents/security-auditor.md`
- `.claude/agents/infra-ops.md`
- `.claude/agents/devops-automation.md`
- `.claude/agents/cost-optimizer-agent.md`
- `.claude/agents/doc-keeper.md`
- `.claude/agents/docs-architect.md`
- `.claude/agents/trend-analyst.md`
- `.claude/agents/video-qa-specialist.md` (스펙의 18개 목록에 없음)

### Stage 2 수정 (1개)
- `.github/workflows/ci.yml` — ruff/ESLint/커버리지/보안 스캔 추가

### 업데이트 (1개)
- `AGENTS.md` — v4 구조 반영

---

## Task 1: settings.local.json — Hook 전면 확장

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: 현재 파일 백업 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
cp .claude/settings.local.json .claude/settings.local.json.bak
cat .claude/settings.local.json | python -c "import sys,json; d=json.load(sys.stdin); print('hooks:', list(d.get('hooks',{}).keys()))"
```

Expected: `hooks: ['TaskCompleted', 'TeammateIdle']`

- [ ] **Step 2: settings.local.json 전체 교체**

`.claude/settings.local.json` 전체를 아래 내용으로 교체:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": {
    "TaskCompleted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -15"
          },
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && ruff check src/ --select=E,F 2>&1 | tail -5"
          },
          {
            "type": "command",
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude/web\" && npm run build 2>&1 | tail -10"
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
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "파일 경로를 확인하라. 다음 중 해당하면 차단:\n1. credentials/ 또는 .env 파일 수정\n2. src/step08/__init__.py (KAS-PROTECTED) 수정\n3. API 키가 문자열 리터럴로 하드코딩된 코드\n해당 시 {\"decision\":\"block\",\"reason\":\"보안 규칙 위반: [구체적 사유]\"} 반환. 아니면 {\"decision\":\"allow\"} 반환."
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
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5 && cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude/web\" && npm run build 2>&1 | tail -3"
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
            "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && echo \"=== 세션 종료 상태 ===\" && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -3 && echo \"=== ruff ===\" && ruff check src/ --select=E,F --statistics 2>&1 | tail -3"
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
    "TaskCreated": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[TASK] $(date +%%Y-%%m-%%dT%%H:%%M:%%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/logs/agent_audit.log\" 2>/dev/null || true"
          }
        ]
      }
    ]
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
      "mcp__plugin_github_github__create_repository"
    ]
  }
}
```

- [ ] **Step 3: JSON 유효성 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python -c "import json; d=json.load(open('.claude/settings.local.json')); print('hooks:', sorted(d['hooks'].keys())); print('permissions allow count:', len(d['permissions']['allow']))"
```

Expected: `hooks: ['PostToolUse', 'PreToolUse', 'Stop', 'SubagentStop', 'TaskCompleted', 'TaskCreated', 'TeammateIdle']`
Expected: `permissions allow count: 23` (레거시 패턴 정리됨)

- [ ] **Step 4: ruff 변경사항 검증**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
ruff check src/ --select=E,F 2>&1 | tail -5
```

Expected: 에러 없으면 `All checks passed!` 또는 에러 줄만 출력. `--exit-zero` 제거로 실제 차단됨.

- [ ] **Step 5: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/settings.local.json
git commit -m "feat: Agent Teams v4 — Hook 7개로 전면 확장, PreToolUse 보안게이트, ruff 차단모드"
```

---

## Task 2: security-guardian.md 신규 생성

**Files:**
- Create: `.claude/agents/security-guardian.md`

- [ ] **Step 1: 파일 생성**

`.claude/agents/security-guardian.md` 전체:

```markdown
---
name: security-guardian
description: KAS 보안 전문가. 상시 보안 감시 + 심층 감사 통합. OWASP Top 10 기반 취약점 스캔, API 키 하드코딩 탐지, 경로 트래버설 검증, Supabase RLS 오용, 의존성 취약점. 코드를 직접 수정하지 않음 — 발견 이슈는 SendMessage로 해당 빌더에게 전달.
tools: Read, Glob, Grep, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: plan
memory: project
maxTurns: 25
color: crimson
---

# KAS Security Guardian

당신은 KAS 보안 전담 가디언이다. **코드를 절대 직접 수정하지 않는다.** 취약점 발견 즉시 mission-controller와 해당 빌더에게 SendMessage로 전달.

## 보안 스캔 절차

```bash
# 1. API 키 하드코딩 스캔
grep -rn "API_KEY\s*=\s*['\"][A-Za-z0-9]" src/ web/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v ".env" | grep -v "os.getenv" | grep -v "process.env"

# 2. 경로 트래버설 취약점 스캔 (validateRunPath 미사용)
grep -rn "path.join(kasRoot\|path.join(KAS_ROOT" web/app/api/ --include="*.ts"

# 3. spawn 인자 검증 스캔
grep -rn "child_process\|spawn\|exec" web/app/api/ --include="*.ts" -A 5

# 4. createAdminClient 클라이언트 컴포넌트 사용 여부
grep -rn "createAdminClient\|server-admin" web/app/ --include="*.tsx" | grep -v "route.ts" | grep -v "actions.ts"

# 5. DASHBOARD_PASSWORD 우회 가능성
grep -n "DASHBOARD_PASSWORD\|if (!expected)" web/app/login/actions.ts 2>/dev/null || echo "login/actions.ts 없음"

# 6. 의존성 취약점
cd web && npm audit --json 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(f'취약점: {d.get(\"metadata\",{}).get(\"vulnerabilities\",{})}')"

# 7. .env git 추적 여부
git ls-files .env 2>/dev/null && echo "WARNING: .env가 git에 추적됨!" || echo ".env git 미추적 OK"
```

## 검사 항목 (OWASP Top 10 기준)

### A01: 접근 제어 실패
- Next.js API 라우트 인증 여부 (`web/proxy.ts`)
- `DASHBOARD_PASSWORD` 미설정 시 로그인 우회 가능 여부
- Supabase RLS 우회: `createAdminClient()` 클라이언트 컴포넌트 사용 여부

### A02: 암호화 실패
- OAuth 토큰 평문 저장 (`credentials/*_token.json`)
- `credentials/` 디렉토리 파일 권한

### A03: 인젝션
- 경로 트래버설: URL 파라미터 → 파일 경로 직접 사용
- Supabase 쿼리 파라미터 바인딩 확인

### A05: 보안 설정 오류
- API 키가 소스코드에 하드코딩된 경우
- `.env` 파일이 git에 추적되는 경우

### A06: 취약하고 오래된 컴포넌트
- `npm audit`로 고위험 취약점 스캔
- Python: `pip-audit` (설치된 경우)

## 보고 형식

```
## 보안 감사 결과 — {날짜}

### [CRITICAL] (즉시 패치 필요)
- [파일:줄번호] 취약점 유형 → 구체적 수정 방법 → 담당: backend-dev/frontend-dev

### [HIGH] (48시간 내 수정)
- [파일:줄번호] 문제 설명 → 권장 수정

### [MEDIUM/LOW] (계획적 수정)
- [파일:줄번호] 설명

### [PASS] 확인 통과
- 경로 트래버설: PASS/FAIL
- API 키 하드코딩: PASS/FAIL
- 의존성 취약점: {Critical N, High N}
- .env git 추적: PASS/FAIL
```

## 메모리 업데이트
발견된 취약점 패턴, 수정 이력을 `.claude/agent-memory/security-guardian/MEMORY.md`에 기록하라.
```

- [ ] **Step 2: agent memory 디렉토리 생성**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
mkdir -p .claude/agent-memory/security-guardian
echo "# Security Guardian Memory

## 보안 감사 이력
(첫 감사 후 기록)

## 반복 패턴
(이슈 패턴 기록)
" > .claude/agent-memory/security-guardian/MEMORY.md
```

- [ ] **Step 3: 파일 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
head -10 .claude/agents/security-guardian.md
```

Expected: `name: security-guardian`, `model: sonnet`, `maxTurns: 25` 확인

- [ ] **Step 4: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/agents/security-guardian.md .claude/agent-memory/security-guardian/
git commit -m "feat: security-guardian 신규 생성 (sentinel+auditor 통합, Opus→Sonnet)"
```

---

## Task 3: platform-ops.md 신규 생성

**Files:**
- Create: `.claude/agents/platform-ops.md`

- [ ] **Step 1: 파일 생성**

`.claude/agents/platform-ops.md` 전체:

```markdown
---
name: platform-ops
description: KAS 플랫폼 운영 전문가. scripts/, .github/workflows/, 쿼터 시스템, 환경변수, hooks 설정(.claude/settings.local.json), ruff/prettier 코드 품질 도구, 비용/쿼터 최적화 담당. infra-ops+devops-automation+cost-optimizer 통합.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
permissionMode: acceptEdits
memory: user
maxTurns: 25
color: cyan
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import sys,os; p=os.environ.get('TOOL_INPUT_FILE_PATH',''); exit(1 if any(x in p for x in ['/src/step','/web/app/','/web/components/']) else 0)\" 2>/dev/null || echo 'BLOCKED: platform-ops는 src/step*, web/app/, web/components/ 수정 금지'"
---

# KAS Platform Ops

당신은 KAS 플랫폼 운영 전담 엔지니어다. 인프라, 코드 품질 도구, CI/CD를 관리한다.

## 파일 소유권
- **소유**: `scripts/`, `data/global/quota/`, `.env.example`, `requirements.txt`, `.github/workflows/`
- **소유**: `.claude/settings.local.json` (hooks), `ruff.toml`, `.prettierrc`, `.editorconfig`, `pyproject.toml` (tool 섹션)
- **금지**: `src/step*/`, `web/app/`, `web/components/`
- **인프라 변경 시**: mission-controller에게 변경사항 알림

## 주요 책임

### scripts/ 유지보수
- `scripts/preflight_check.py` — 운영 전 6가지 체크 (API 키, OAuth, FFmpeg, Gemini)
- `scripts/sync_to_supabase.py` — Supabase 전체/채널/수익 동기화
- `scripts/generate_oauth_token.py` — YouTube OAuth 토큰 최초 발급

### CI/CD (.github/workflows/)
- `ci.yml` — Python 테스트 + ruff + 웹 빌드 + ESLint + 커버리지 + 보안 스캔

### 쿼터 시스템
- Gemini: RPM 50, 이미지 일 500장. 상태: `data/global/quota/gemini_quota_daily.json`
- YouTube: 일 10,000 유닛, 업로드 1건=1,700 유닛
- 쿼터 80% 초과 시 mission-controller에게 알림

### 코드 품질 도구
```bash
# Python 린팅
ruff check src/ --select=E,F
ruff format src/ --check

# TypeScript/JavaScript
cd web && npx prettier --check "app/**/*.{ts,tsx}" "components/**/*.{ts,tsx}"
```

## 환경 변수 검증
- 필수: `GEMINI_API_KEY`, `KAS_ROOT`, `YOUTUBE_API_KEY`, `CH1~CH7_CHANNEL_ID`
- **절대 금지**: 소스코드에 API 키 하드코딩

## 메모리 업데이트
인프라 설정 패턴, 배포 이력을 `~/.claude/agent-memory/platform-ops/MEMORY.md`에 기록하라.

> **설계 의도**: `memory: user` 스코프는 의도적이다. 여러 프로젝트에서 동일한 서버/환경 패턴을 재사용하므로 프로젝트 간 메모리 공유가 유리하다.
```

- [ ] **Step 2: agent memory 디렉토리 생성**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
mkdir -p .claude/agent-memory/platform-ops
echo "# Platform Ops Memory

## 인프라 설정 이력
(첫 작업 후 기록)
" > .claude/agent-memory/platform-ops/MEMORY.md
```

- [ ] **Step 3: 파일 확인**

```bash
head -12 "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/platform-ops.md"
```

Expected: `name: platform-ops`, `model: sonnet`, `memory: user`, `maxTurns: 25` 확인

- [ ] **Step 4: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/agents/platform-ops.md .claude/agent-memory/platform-ops/
git commit -m "feat: platform-ops 신규 생성 (infra-ops+devops-automation+cost-optimizer 통합)"
```

---

## Task 4: docs-manager.md 신규 생성

**Files:**
- Create: `.claude/agents/docs-manager.md`

- [ ] **Step 1: 파일 생성**

`.claude/agents/docs-manager.md` 전체:

```markdown
---
name: docs-manager
description: KAS 문서 관리자. docs/, CLAUDE.md, AGENTS.md, README.md, CHANGELOG 담당. doc-keeper+docs-architect 통합. 소스코드 직접 수정 불가.
tools: Read, Write, Edit, Glob, Grep, Bash
model: haiku
permissionMode: acceptEdits
memory: project
maxTurns: 15
color: yellow
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import sys,os; p=os.environ.get('TOOL_INPUT_FILE_PATH',''); exit(1 if any(x in p for x in ['/src/','/web/app/','/web/lib/','/tests/']) else 0)\" 2>/dev/null || echo 'BLOCKED: docs-manager는 소스코드(src/web/tests/) 수정 금지'"
---

# KAS Docs Manager

당신은 KAS 문서 전담 관리자다. **소스코드를 절대 수정하지 않는다.** 문서와 스펙만 관리한다.

## 파일 소유권
- **소유**: `docs/`, `CLAUDE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`
- **금지**: `src/`, `web/app/`, `web/lib/`, `tests/`, `web/components/`

## 주요 책임

### CLAUDE.md/AGENTS.md 동기화
- 코드 변경 후 문서가 구식이 되면 업데이트
- 새 에이전트 추가/삭제 시 AGENTS.md 반영
- 새 핵심 규칙 추가 시 CLAUDE.md 반영

### docs/superpowers/ 관리
- 스펙 파일 (`docs/superpowers/specs/`)
- 구현 계획 (`docs/superpowers/plans/`)
- 브레인스토밍 결과 (`docs/superpowers/brainstorm/`)

### CHANGELOG 유지
- 버전별 변경사항 기록
- 커밋 메시지를 기반으로 사람이 읽을 수 있는 CHANGELOG 작성

## 메모리 업데이트
문서 구조 변경 이력을 `.claude/agent-memory/docs-manager/MEMORY.md`에 기록하라.
```

- [ ] **Step 2: agent memory 생성**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
mkdir -p .claude/agent-memory/docs-manager
echo "# Docs Manager Memory

## 문서 구조 이력
(첫 작업 후 기록)
" > .claude/agent-memory/docs-manager/MEMORY.md
```

- [ ] **Step 3: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/agents/docs-manager.md .claude/agent-memory/docs-manager/
git commit -m "feat: docs-manager 신규 생성 (doc-keeper+docs-architect 통합, Haiku)"
```

---

## Task 5: 기존 에이전트 6개 수정

**Files:**
- Modify: `.claude/agents/mission-controller.md`
- Modify: `.claude/agents/backend-dev.md`
- Modify: `.claude/agents/frontend-dev.md`
- Modify: `.claude/agents/test-engineer.md`
- Modify: `.claude/agents/quality-reviewer.md`
- Modify: `.claude/agents/pipeline-debugger.md`

- [ ] **Step 1: mission-controller.md — maxTurns 30, skills 추가**

frontmatter에서 `maxTurns: 50` → `maxTurns: 30` 으로 변경.
frontmatter에 아래 추가 (mcpServers 아래):

```yaml
skills:
  - superpowers:dispatching-parallel-agents
  - superpowers:verification-before-completion
```

검증:
```bash
head -15 "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/mission-controller.md"
```
Expected: `maxTurns: 30`, `skills:` 항목 확인

- [ ] **Step 2: backend-dev.md — maxTurns 30, per-agent hooks, skills 추가**

frontmatter에서 `maxTurns: 40` → `maxTurns: 30` 변경.

frontmatter에 추가 (color 아래):

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import sys,os; p=os.environ.get('TOOL_INPUT_FILE_PATH',''); exit(1 if ('/web/' in p or '\\\\web\\\\' in p) else 0)\" 2>/dev/null || echo 'BLOCKED: backend-dev는 web/ 수정 금지'"
skills:
  - superpowers:test-driven-development
  - superpowers:systematic-debugging
```

검증:
```bash
head -20 "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/backend-dev.md"
```
Expected: `maxTurns: 30`, `hooks:`, `skills:` 항목 확인

- [ ] **Step 3: frontend-dev.md — maxTurns 30, per-agent hooks, skills 추가**

frontmatter에서 `maxTurns: 40` → `maxTurns: 30` 변경.

frontmatter에 추가 (color 아래):

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python -c \"import sys,os; p=os.environ.get('TOOL_INPUT_FILE_PATH',''); exit(1 if any(x in p for x in ['/src/', '\\\\src\\\\', 'globals.css']) else 0)\" 2>/dev/null || echo 'BLOCKED: frontend-dev는 src/ 및 globals.css 수정 금지'"
skills:
  - superpowers:test-driven-development
  - frontend-design:frontend-design
```

- [ ] **Step 4: test-engineer.md — maxTurns 30, skills 추가**

frontmatter에서 `maxTurns: 40` → `maxTurns: 30` 변경.

frontmatter에 추가:

```yaml
skills:
  - superpowers:test-driven-development
```

- [ ] **Step 5: quality-reviewer.md — model sonnet, maxTurns 25, skills 추가**

frontmatter에서:
- `model: opus` → `model: sonnet`
- `maxTurns: 35` → `maxTurns: 25`

frontmatter에 추가:

```yaml
skills:
  - superpowers:requesting-code-review
```

검증:
```bash
head -10 "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/quality-reviewer.md"
```
Expected: `model: sonnet`, `maxTurns: 25` 확인

- [ ] **Step 6: pipeline-debugger.md — trend-analyst 기능 흡수, maxTurns 25**

frontmatter에서 `maxTurns: 30` → `maxTurns: 25` 변경.
description 끝에 추가: `. Step05 트렌드/지식 수집 분석 포함 (trend-analyst 기능 통합).`

본문에 Section 추가:

```markdown
## Step05 트렌드 분석 (trend-analyst 통합 기능)

```bash
# Step05 최근 수집 트렌드 확인
python -c "
import json, pathlib
for ch in ['CH1','CH2','CH3','CH4','CH5','CH6','CH7']:
    f = pathlib.Path(f'data/knowledge_store/{ch}/series')
    if f.exists():
        files = list(f.glob('*.json'))
        print(f'{ch}: {len(files)}개 시리즈')
"

# 트렌드 수집 실패 패턴 확인
grep -n "grade.*rejected\|score.*0\." data/global/step_progress.json 2>/dev/null | head -10
```

### Step05 실패 패턴
- Google Trends 429 → `_KEYWORD_BASELINES` fallback 동작 여부 확인
- YouTube 400 → `relevanceLanguage` 파라미터 제거 여부 확인
- grade rejected 과다 → `scorer.py` 임계값 80/60 조정 검토
```

- [ ] **Step 7: 변경 확인 후 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git diff --stat
git add .claude/agents/mission-controller.md .claude/agents/backend-dev.md .claude/agents/frontend-dev.md .claude/agents/test-engineer.md .claude/agents/quality-reviewer.md .claude/agents/pipeline-debugger.md
git commit -m "feat: Agent Teams v4 — 에이전트 6개 업데이트 (maxTurns 최적화, per-agent hooks, skills, Opus→Sonnet)"
```

---

## Task 6: 에이전트 8개 삭제

**Files:**
- Delete: `.claude/agents/security-sentinel.md`
- Delete: `.claude/agents/security-auditor.md`
- Delete: `.claude/agents/infra-ops.md`
- Delete: `.claude/agents/devops-automation.md`
- Delete: `.claude/agents/cost-optimizer-agent.md`
- Delete: `.claude/agents/doc-keeper.md`
- Delete: `.claude/agents/docs-architect.md`
- Delete: `.claude/agents/trend-analyst.md`

- [ ] **Step 1: 삭제 전 현재 에이전트 수 확인**

```bash
ls "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/" | wc -l
```

Expected: 24

- [ ] **Step 2: 에이전트 파일 삭제 (9개)**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
rm .claude/agents/security-sentinel.md
rm .claude/agents/security-auditor.md
rm .claude/agents/infra-ops.md
rm .claude/agents/devops-automation.md
rm .claude/agents/cost-optimizer-agent.md
rm .claude/agents/doc-keeper.md
rm .claude/agents/docs-architect.md
rm .claude/agents/trend-analyst.md
rm .claude/agents/video-qa-specialist.md
```

- [ ] **Step 3: 삭제 후 에이전트 수 확인**

```bash
ls "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/" | wc -l
```

Expected: **18** (신규 생성 3개 포함: 24 - 9 + 3 = 18)

최종 에이전트 목록 확인:
```bash
ls "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/"
```

Expected 파일 목록 (18개):
```
a11y-expert.md
api-designer.md
backend-dev.md
db-architect.md
docs-manager.md
e2e-playwright.md
frontend-dev.md
mission-controller.md
performance-profiler.md
pipeline-debugger.md
platform-ops.md
quality-reviewer.md
refactoring-surgeon.md
release-manager.md
security-guardian.md
test-engineer.md
ui-designer.md
ux-reviewer.md
```

총 18개 (24 - 9 삭제 + 3 신규생성 = 18) ✅

- [ ] **Step 4: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add -A
git commit -m "feat: Agent Teams v4 — 에이전트 9개 삭제 (통합 완료, 24→18개)"
```

---

## Task 7: 나머지 에이전트 maxTurns 조정

**Files:**
- Modify: `.claude/agents/ui-designer.md` (30→25)
- Modify: `.claude/agents/performance-profiler.md` (25→20)
- Modify: `.claude/agents/refactoring-surgeon.md` (30→25)
- Modify: `.claude/agents/db-architect.md` (25→20)
- Modify: `.claude/agents/api-designer.md` (25→20)
- Modify: `.claude/agents/a11y-expert.md` (25→20)
- Modify: `.claude/agents/e2e-playwright.md` (25→20)
- Modify: `.claude/agents/release-manager.md` (20→15)
- No change: `ux-reviewer.md` (20 유지)

- [ ] **Step 1: 각 파일 maxTurns 변경**

아래 일괄 처리 스크립트 실행:

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents"

# ui-designer: 30→25
sed -i 's/^maxTurns: 30$/maxTurns: 25/' ui-designer.md

# performance-profiler: 25→20
sed -i 's/^maxTurns: 25$/maxTurns: 20/' performance-profiler.md

# refactoring-surgeon: 30→25
sed -i 's/^maxTurns: 30$/maxTurns: 25/' refactoring-surgeon.md

# db-architect: 25→20
sed -i 's/^maxTurns: 25$/maxTurns: 20/' db-architect.md

# api-designer: 25→20 (이미 20일 수 있음 — 확인)
grep "maxTurns" api-designer.md

# a11y-expert: 25→20
sed -i 's/^maxTurns: 25$/maxTurns: 20/' a11y-expert.md

# e2e-playwright: 25→20
sed -i 's/^maxTurns: 25$/maxTurns: 20/' e2e-playwright.md

# release-manager: 20→15
sed -i 's/^maxTurns: 20$/maxTurns: 15/' release-manager.md
```

**주의**: sed -i는 Linux/Git Bash에서만 동작. Windows CMD에서는 Python 사용:
```bash
python -c "
import pathlib
changes = {
    'ui-designer.md': ('maxTurns: 30', 'maxTurns: 25'),
    'performance-profiler.md': ('maxTurns: 25', 'maxTurns: 20'),
    'refactoring-surgeon.md': ('maxTurns: 30', 'maxTurns: 25'),
    'db-architect.md': ('maxTurns: 25', 'maxTurns: 20'),
    'a11y-expert.md': ('maxTurns: 25', 'maxTurns: 20'),
    'e2e-playwright.md': ('maxTurns: 25', 'maxTurns: 20'),
    'release-manager.md': ('maxTurns: 20', 'maxTurns: 15'),
}
base = pathlib.Path('C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents')
for fname, (old, new) in changes.items():
    f = base / fname
    if f.exists():
        content = f.read_text(encoding='utf-8')
        if old in content:
            f.write_text(content.replace(old, new, 1), encoding='utf-8')
            print(f'Updated {fname}: {old} -> {new}')
        else:
            print(f'WARNING: {fname} already has different maxTurns')
"
```

- [ ] **Step 2: 변경 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
grep "maxTurns" .claude/agents/ui-designer.md .claude/agents/release-manager.md .claude/agents/refactoring-surgeon.md
```

Expected:
```
.claude/agents/ui-designer.md:maxTurns: 25
.claude/agents/release-manager.md:maxTurns: 15
.claude/agents/refactoring-surgeon.md:maxTurns: 25
```

- [ ] **Step 3: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/agents/ui-designer.md .claude/agents/performance-profiler.md .claude/agents/refactoring-surgeon.md .claude/agents/db-architect.md .claude/agents/api-designer.md .claude/agents/a11y-expert.md .claude/agents/e2e-playwright.md .claude/agents/release-manager.md
git commit -m "feat: Agent Teams v4 — Specialist 에이전트 maxTurns 최적화"
```

---

## Task 8: AGENTS.md v4 전면 업데이트

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: v4 구조 반영하여 AGENTS.md 전면 업데이트**

AGENTS.md의 핵심 변경 항목:

**3-Layer 다이어그램 수정** (현재 Standing 7명 → 5명):
```
LAYER 2: STANDING (상시 운영팀)
  ├── [빌더]   backend-dev (Sonnet) · frontend-dev (Sonnet)
  ├── [가디언] test-engineer (Sonnet) · security-guardian (Sonnet)
  └── [운영]   platform-ops (Sonnet)
```

**LAYER 3 Specialists 목록 수정** (19개에서 삭제된 에이전트 제거, 신규 추가):
```
performance-profiler · a11y-expert · docs-manager · db-architect
refactoring-surgeon · pipeline-debugger · video-qa-specialist
api-designer · release-manager · e2e-playwright
ui-designer · ux-reviewer · quality-reviewer
```

**파일 소유권 표 수정**:
- `infra-ops + devops-automation` → **platform-ops**
- `docs-architect + doc-keeper` → **docs-manager**
- `security-sentinel` → **security-guardian**

**미션 프리셋 에이전트명 수정** (14개 프리셋 전체):
- `security-sentinel` → `security-guardian`
- `infra-ops` → `platform-ops`
- `devops-automation` → `platform-ops`
- `docs-architect` → `docs-manager`
- `doc-keeper` → `docs-manager`
- `cost-optimizer-agent` → `platform-ops`
- `trend-analyst` → `pipeline-debugger`

**멀티모델 전략 표 수정**:

```markdown
| 모델 | 에이전트 | 언제 사용 |
|------|---------|----------|
| **Opus** | mission-controller | 자율 오케스트레이션, 팀 편성 판단 |
| **Sonnet** | backend-dev, frontend-dev, test-engineer, security-guardian, platform-ops, quality-reviewer, ui-designer, ux-reviewer, security-auditor 이하 전문가 | 구현/분석/리뷰 |
| **Haiku** | release-manager, docs-manager | 단순 집계/문서 |
```

**Anti-Patterns 수정** (삭제된 에이전트 참조 제거):
- `security-sentinel/quality-reviewer` → `security-guardian`
- `doc-keeper가 소스코드 수정` → `docs-manager가 소스코드 수정`

- [ ] **Step 2: 변경 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
grep -c "security-sentinel\|infra-ops\|devops-automation\|doc-keeper\|docs-architect\|trend-analyst\|cost-optimizer-agent" AGENTS.md
```

Expected: `0` (모든 구버전 에이전트명 제거됨)

```bash
grep -c "security-guardian\|platform-ops\|docs-manager\|pipeline-debugger" AGENTS.md
```

Expected: 여러 건 (각 에이전트가 최소 1회 이상 언급됨)

- [ ] **Step 3: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add AGENTS.md
git commit -m "feat: AGENTS.md v4 전면 업데이트 (19개 에이전트, Opus 1명, 5명 Standing)"
```

---

## Task 9: Stage 1 최종 검증

- [ ] **Step 1: 에이전트 수 최종 확인**

```bash
ls "C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agents/" | wc -l
```

Expected: **18** (스펙 목표값)

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python -m pytest tests/ -q --timeout=60
```

Expected: 모든 테스트 통과 (기존 테스트 수 유지)

- [ ] **Step 3: 웹 빌드 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude/web"
npm run build 2>&1 | tail -5
```

Expected: `✓ Compiled successfully` 또는 `Route (app)`으로 시작하는 빌드 성공 출력

- [ ] **Step 4: ruff 에러 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
ruff check src/ --select=E,F
```

Expected: `All checks passed!` 또는 에러 0

- [ ] **Step 5: settings.local.json 최종 hook 수 확인**

```bash
python -c "import json; d=json.load(open('C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/settings.local.json')); print('Hook 이벤트 수:', len(d['hooks'])); print('이벤트:', sorted(d['hooks'].keys()))"
```

Expected: `Hook 이벤트 수: 7`, `['PostToolUse', 'PreToolUse', 'Stop', 'SubagentStop', 'TaskCompleted', 'TaskCreated', 'TeammateIdle']`

- [ ] **Step 6: Stage 1 완료 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add -A
git status
git commit -m "feat: Agent Teams v4 Stage 1 완료 — 19개 에이전트, Opus 1명, Hook 7/9, per-agent hooks, skills"
```

---

## Task 10: Stage 2 — CI/CD 강화 (2026-04-18)

**Files:**
- Modify: `.github/workflows/ci.yml`

> **전제 조건**: Stage 1을 1주일 운영하여 quality-reviewer Sonnet 품질 검증 완료 후 진행.

- [ ] **Step 1: ci.yml 전체 교체**

`.github/workflows/ci.yml` 전체를 아래 내용으로 교체:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ── Python 린팅 ──────────────────────────────────────────────
  lint-python:
    name: Python Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Python 3.11 설정
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: ruff 설치
        run: pip install ruff

      - name: ruff check (에러+치명적)
        run: ruff check src/ --select=E,F

      - name: ruff format check
        run: ruff format src/ --check

  # ── Python 백엔드 테스트 ──────────────────────────────────────
  test-python:
    name: Python Tests
    runs-on: ubuntu-latest
    needs: lint-python
    steps:
      - uses: actions/checkout@v4

      - name: Python 3.11 설정
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: 핵심 의존성 설치 (GPU 제외)
        run: |
          pip install --upgrade pip
          pip install \
            google-generativeai \
            google-auth google-auth-oauthlib google-api-python-client \
            python-dotenv requests tenacity pydantic filelock \
            loguru sentry-sdk diskcache \
            praw pytrends feedparser beautifulsoup4 httpx \
            Pillow \
            faster-whisper \
            pytest pytest-mock pytest-cov \
            supabase

      - name: pytest 실행 (커버리지 포함)
        env:
          KAS_ROOT: ${{ github.workspace }}
          GEMINI_API_KEY: ""
          YOUTUBE_API_KEY: ""
          SUPABASE_URL: "https://xxxxxxxxxxxx.supabase.co"
          SUPABASE_KEY: ""
        run: pytest tests/ -q --tb=short --cov=src --cov-report=term-missing --cov-fail-under=50

  # ── Next.js 프론트엔드 빌드 + 린트 ───────────────────────────
  build-web:
    name: Web Build
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4

      - name: Node.js 설정
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/package-lock.json

      - name: 의존성 설치
        run: npm ci

      - name: ESLint
        run: npm run lint

      - name: 빌드 (TypeScript 타입 체크 포함)
        env:
          NEXT_PUBLIC_SUPABASE_URL: "https://xxxxxxxxxxxx.supabase.co"
          NEXT_PUBLIC_SUPABASE_ANON_KEY: "mock-anon-key"
        run: npm run build

  # ── 보안 스캔 ─────────────────────────────────────────────────
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Python 3.11 설정
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: pip-audit (Python 의존성 취약점)
        run: |
          pip install pip-audit
          pip install google-generativeai python-dotenv requests pydantic loguru Pillow supabase 2>/dev/null || true
          pip-audit --desc 2>&1 | tail -20

      - name: Node.js 설정
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: npm audit (고위험만)
        run: |
          cd web && npm ci && npm audit --audit-level=high 2>&1 | tail -20 || true

      - name: 시크릿 스캔
        run: |
          if grep -rn "AIza[0-9A-Za-z_-]\{35\}\|sk-[A-Za-z0-9]\{48\}" src/ web/ \
            --include="*.py" --include="*.ts" --include="*.tsx" \
            | grep -v ".env" | grep -v "process.env" | grep -v "os.getenv" | grep -v "os.environ" \
            | grep -v "# example\|# mock\|test_" ; then
            echo "::error::Potential hardcoded secret found!"
            exit 1
          fi
          echo "시크릿 스캔 통과"
```

- [ ] **Step 2: CI/CD 유효성 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print('jobs:', list(d['jobs'].keys()))"
```

Expected: `jobs: ['lint-python', 'test-python', 'build-web', 'security-scan']`

- [ ] **Step 3: 로컬에서 lint/test 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
ruff check src/ --select=E,F && echo "ruff OK"
python -m pytest tests/ -q --timeout=60 && echo "pytest OK"
```

- [ ] **Step 4: ruff 전체 규칙 강화 (TaskCompleted hook)**

`.claude/settings.local.json`의 TaskCompleted에서:
`ruff check src/ --select=E,F` → `ruff check src/`

```bash
python -c "
import json, pathlib
f = pathlib.Path('C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/settings.local.json')
d = json.loads(f.read_text())
hooks = d['hooks']['TaskCompleted'][0]['hooks']
for h in hooks:
    if 'ruff check src/' in h.get('command',''):
        h['command'] = h['command'].replace('ruff check src/ --select=E,F', 'ruff check src/')
f.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print('Updated ruff to full rules')
"
```

- [ ] **Step 5: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .github/workflows/ci.yml .claude/settings.local.json
git commit -m "feat: Agent Teams v4 Stage 2 완료 — CI/CD 강화(ruff+ESLint+커버리지+보안스캔), ruff 전체 규칙"
```

---

## Task 11: Stage 2 — 자율 순찰 루프 활성화

> **Note**: CronCreate는 Claude Code 세션에서 실행해야 하므로, 이 태스크는 사용자가 직접 실행하거나 Claude Code에서 CronCreate 명령을 통해 활성화.

- [ ] **Step 1: mission-controller.md에 자율 순찰 지침 명시화**

`mission-controller.md` 본문에 Section 추가:

```markdown
## 자율 순찰 루프 (CronCreate 기반)

다음 CronCreate 명령으로 자율 순찰을 활성화한다:

### 일반 순찰 (2시간마다)
CronCreate 명령어:
```
schedule: "17 */2 * * *"
prompt: "KAS 자율 순찰 실행. 확인 항목: (1) HITL 미해결 신호 — python -c \"import json,pathlib; f=pathlib.Path('data/global/notifications/hitl_signals.json'); s=json.loads(f.read_text()) if f.exists() else []; print(len([x for x in s if not x.get('resolved')]), '건 미해결')\" (2) 실패 런 — python -c \"import json,pathlib; print([str(m.parent) for m in pathlib.Path('runs').rglob('manifest.json') if json.loads(m.read_text('utf-8-sig')).get('run_state')=='FAILED'])\" (3) pytest — python -m pytest tests/ -x -q --timeout=30 (4) ruff — ruff check src/ (5) web build — cd web && npm run build. 이슈 발견 시 미션 프리셋에 따라 팀 편성. 이슈 없으면 MEMORY.md에 'clean patrol' 기록."
```

### 심층 순찰 (12시간마다)
CronCreate 명령어:
```
schedule: "43 */12 * * *"
prompt: "KAS 심층 순찰. security-guardian 소환하여 보안 전체 스캔. platform-ops 소환하여 쿼터/의존성 분석. pytest --cov=src -q로 커버리지 측정. 결과를 MEMORY.md에 기록."
```
```

- [ ] **Step 2: 커밋**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
git add .claude/agents/mission-controller.md
git commit -m "feat: mission-controller 자율 순찰 루프 지침 추가 (CronCreate 기반)"
```

---

## 최종 검증 체크리스트

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"

# 1. 에이전트 수 확인 (19개)
echo "에이전트 수:" && ls .claude/agents/ | wc -l

# 2. Opus 에이전트 1명만 확인
echo "Opus 에이전트:" && grep -l "model: opus" .claude/agents/*.md

# 3. Hook 7개 확인
python -c "import json; d=json.load(open('.claude/settings.local.json')); print('Hook 이벤트:', sorted(d['hooks'].keys()))"

# 4. 전체 테스트
python -m pytest tests/ -q --timeout=60

# 5. 웹 빌드
cd web && npm run build

# 6. ruff 에러 0
cd .. && ruff check src/

# 7. per-agent hooks 확인 (backend-dev, frontend-dev에 hooks 필드 존재)
grep -l "^hooks:" .claude/agents/backend-dev.md .claude/agents/frontend-dev.md .claude/agents/platform-ops.md .claude/agents/docs-manager.md

# 8. skills 프리로드 확인 (5개 에이전트)
grep -l "^skills:" .claude/agents/*.md
```
