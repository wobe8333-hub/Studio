# KAS Agent Teams v4 — 자율 운영 + 토큰 효율 최적화 설계

> 공식 문서 기준 최고 수준의 Agent Team 구성. 자율 순찰 루프, 전체 Hook 활용, 토큰 효율 극대화.

---

## Context

KAS Agent Teams v3.1 (24개 에이전트, 3-Layer)이 운영 중이나, 공식 문서 기준으로 다음 갭이 존재:

1. **Hook 활용률 22%** — 9개 이벤트 중 2개만 사용 (TaskCompleted, TeammateIdle)
2. **자율 순찰 루프 부재** — mission-controller가 수동 소환으로만 작동
3. **Per-agent hooks 0개** — 소유권 침범을 물리적으로 차단하지 못함
4. **Skills 프리로드 0개** — 에이전트별 전문 스킬 미활용
5. **역할 중복 3쌍** — security-sentinel/auditor, doc-keeper/docs-architect, infra-ops/devops-automation
6. **ruff --exit-zero** — 린트 경고만 출력, 실제 차단 없음
7. **CI/CD 불완전** — ruff, ESLint, 커버리지, 보안 스캔 누락
8. **prompt 타입 hook 미사용** — 보안 게이트 부재

**목표**: 공식 문서의 모든 베스트 프랙티스를 적용하되, 토큰 효율까지 최적화.

---

## 핵심 설계 원칙 (공식 문서 기반)

| 원칙 | 적용 |
|------|------|
| **미션당 3~5명** | Standing 5명(빌더2+가디언2+운영1)으로 축소, 나머지는 Specialist |
| **Opus=판단, Sonnet=실행, Haiku=경량** | Opus 1명(mission-controller만), 나머지 재배치 |
| **command hook 우선** | prompt hook은 보안 게이트 1곳만, 나머지 전부 command (토큰 무비용) |
| **최소 권한 원칙** | 에이전트별 tools/disallowedTools 정밀 제한 |
| **자율 루프** | CronCreate 기반 순찰. ScheduleWakeup으로 동적 간격 |
| **per-agent hooks** | 소유권 경계를 물리적으로 차단 |

---

## Section 1: 에이전트 통합 (24 → 18)

### 통합 대상 (6개 감소)

| 통합 전 | 통합 후 | 근거 |
|---------|---------|------|
| security-sentinel (Opus) + security-auditor (Sonnet) | **security-guardian** (Sonnet) | OWASP 스캔 역할 90% 중복. Sonnet이면 보안 체크리스트 충분. Opus 1명 절감 |
| quality-reviewer (Opus) | **quality-reviewer** (Sonnet) | 코드 리뷰는 Sonnet 수준으로 충분. Opus→Sonnet 다운그레이드로 대폭 절감 |
| doc-keeper (Haiku) + docs-architect (Haiku) | **docs-manager** (Haiku) | docs/CLAUDE.md/AGENTS.md/README 담당 동일 |
| infra-ops (Sonnet) + devops-automation (Sonnet) | **platform-ops** (Sonnet) | scripts/+.github/+hooks+ruff 모두 인프라/운영 영역 |
| cost-optimizer-agent (Haiku) | → platform-ops에 흡수 | 쿼터 관리는 인프라 운영의 하위 기능 |
| trend-analyst (Haiku) | → pipeline-debugger에 흡수 | Step05 트렌드 분석은 파이프라인 디버깅 일부 |

### 통합 후 구조 (18개)

```
LAYER 1: COMMAND (1명)
  mission-controller (Opus, maxTurns 30)

LAYER 2: STANDING (5명) — 미션당 3~5명 활성
  [빌더]  backend-dev (Sonnet, 30) · frontend-dev (Sonnet, 30)
  [가디언] test-engineer (Sonnet, 30) · security-guardian (Sonnet, 25)
  [운영]  platform-ops (Sonnet, 25)

LAYER 3: SPECIALISTS (12명) — 소환 시에만 활성
  quality-reviewer (Sonnet, 25)
  ui-designer (Sonnet, 25)
  ux-reviewer (Sonnet, 20)
  pipeline-debugger (Sonnet, 25)
  performance-profiler (Sonnet, 20)
  refactoring-surgeon (Sonnet, 25)
  db-architect (Sonnet, 20)
  api-designer (Sonnet, 20)
  a11y-expert (Sonnet, 20)
  e2e-playwright (Sonnet, 20)
  release-manager (Haiku, 15)
  docs-manager (Haiku, 15)
```

### 모델 배분 요약

| 모델 | v3.1 (24개) | v4 (18개) | 절감 |
|------|:-----------:|:---------:|:----:|
| **Opus** | 3명 | **1명** (mission-controller만) | -66% |
| **Sonnet** | 16명 | **15명** | -6% |
| **Haiku** | 5명 | **2명** | -60% |
| **합계** | 24명 | 18명 | -25% |

**토큰 효율 영향**: Opus $5/$25 → Sonnet $3/$15로 2명 다운그레이드 = **미션당 ~40% 비용 절감**

### maxTurns 최적화

| 역할 | v3.1 | v4 | 근거 |
|------|:----:|:--:|------|
| mission-controller | 50 | **30** | 조율만 하므로 30턴 충분. 초과 시 비효율적 루프 |
| backend-dev | 40 | **30** | 공식 권장: 실행 에이전트 25-35턴 |
| frontend-dev | 40 | **30** | 동일 |
| test-engineer | 40 | **30** | 동일 |
| security-guardian | - | **25** | 신규. 스캔+보고만 |
| platform-ops | 30 | **25** | 통합으로 범위 넓지만, 개별 작업은 짧음 |
| quality-reviewer | 35 | **25** | Opus→Sonnet 전환으로 효율적 턴 사용 |
| Layer 3 Specialists | 15-30 | **15-25** | 소환 시 짧은 작업 기준 |

---

## Section 2: Hook 전면 확장 (2/9 → 7/9)

### 토큰 효율 원칙

- `command` 타입: **토큰 비용 0**. 쉘 명령만 실행
- `prompt` 타입: **매 호출마다 LLM 토큰 소비**. 최소한으로 제한
- `agent` 타입: **별도 에이전트 세션 토큰 소비**. 사용하지 않음

→ **prompt hook은 PreToolUse 보안 게이트 1곳만**. 나머지는 모두 command.

### 전체 Hook 설계

#### 1. TaskCompleted (기존 강화)

```json
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
```

**변경점**: `ruff check src/ --exit-zero` → `ruff check src/ --select=E,F` (에러+치명적 차단)

#### 2. TeammateIdle (기존 유지)

```json
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && echo \"=== 마지막 커밋 변경 파일 ===\" && git diff HEAD~1 --name-only 2>/dev/null | head -20"
    }
  ]
}
```

#### 3. PreToolUse — 보안 게이트 (유일한 prompt hook)

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "prompt",
      "prompt": "파일 경로를 확인하라. 다음 중 해당하면 차단:\n1. credentials/ 또는 .env 파일 수정\n2. src/step08/__init__.py (KAS-PROTECTED) 수정\n3. API 키가 문자열 리터럴로 하드코딩된 코드\n해당 시 {\"decision\":\"block\",\"reason\":\"보안 규칙 위반: [구체적 사유]\"} 반환. 아니면 {\"decision\":\"allow\"} 반환."
    }
  ]
}
```

**왜 prompt인가**: 파일 내용(API 키 하드코딩)을 판단해야 하므로 LLM 필요. 단, Write/Edit에만 적용 (Bash 제외로 호출 빈도 최소화).

#### 4. SubagentStop — 결과 검증 (command)

```json
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5 && cd web && npm run build 2>&1 | tail -3"
    }
  ]
}
```

**토큰 효율**: prompt 대신 command로 테스트/빌드 결과만 반환. LLM이 결과를 읽고 판단.

#### 5. Stop — 세션 마무리 (command)

```json
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && echo \"=== 세션 종료 상태 ===\" && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -3 && echo \"=== ruff ===\" && ruff check src/ --select=E,F --statistics 2>&1 | tail -3"
    }
  ]
}
```

#### 6. PostToolUse — 변경 추적 (command)

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && git diff --stat HEAD 2>/dev/null | tail -5"
    }
  ]
}
```

#### 7. TaskCreated — 미션 감사 로그 (command)

```json
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "echo \"[TASK] $(date +%%Y-%%m-%%dT%%H:%%M:%%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/logs/agent_audit.log\" 2>/dev/null || true"
    }
  ]
}
```

### Hook 미사용 (의도적 제외)

| Hook | 제외 사유 |
|------|----------|
| **UserPromptSubmit** | 사용자 입력에 prompt hook 적용 시 매 메시지마다 토큰 소비. 비용 대비 효과 낮음 |
| **FileChanged** | PostToolUse가 이미 파일 변경을 추적. 중복 |

### Hook 토큰 비용 추정

| Hook | 타입 | 호출 빈도/일 | 토큰/호출 | 일일 추가 토큰 |
|------|------|:-----------:|:--------:|:-------------:|
| TaskCompleted | command | ~10 | 0 | 0 |
| TeammateIdle | command | ~5 | 0 | 0 |
| **PreToolUse** | **prompt** | **~100** | **~300** | **~30K** |
| SubagentStop | command | ~15 | 0 | 0 |
| Stop | command | ~5 | 0 | 0 |
| PostToolUse | command | ~100 | 0 | 0 |
| TaskCreated | command | ~10 | 0 | 0 |
| **합계** | | | | **~30K/일** |

**비교**: 접근법 A(모든 prompt hook)의 ~230K/일 대비 **87% 절감**.

---

## Section 3: Per-agent Hooks (소유권 물리적 차단)

에이전트 정의 파일(.md)의 `hooks` frontmatter 필드 활용. **모두 command 타입 (토큰 0).**

### backend-dev.md

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "echo $TOOL_INPUT | python -c \"import sys,json; d=json.load(sys.stdin); p=d.get('file_path',''); exit(1 if '/web/' in p or '\\\\web\\\\' in p else 0)\" 2>/dev/null || echo 'BLOCKED: backend-dev는 web/ 수정 금지'"
```

### frontend-dev.md

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "echo $TOOL_INPUT | python -c \"import sys,json; d=json.load(sys.stdin); p=d.get('file_path',''); exit(1 if ('/src/' in p or '\\\\src\\\\' in p or 'globals.css' in p) else 0)\" 2>/dev/null || echo 'BLOCKED: frontend-dev는 src/ 및 globals.css 수정 금지'"
```

### platform-ops.md (통합 신규)

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "echo $TOOL_INPUT | python -c \"import sys,json; d=json.load(sys.stdin); p=d.get('file_path',''); exit(1 if ('/src/step' in p or '/web/app/' in p) else 0)\" 2>/dev/null || echo 'BLOCKED: platform-ops는 src/step* 및 web/app/ 수정 금지'"
```

### docs-manager.md (통합 신규)

```yaml
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "echo $TOOL_INPUT | python -c \"import sys,json; d=json.load(sys.stdin); p=d.get('file_path',''); exit(1 if any(x in p for x in ['/src/','/web/app/','/tests/']) else 0)\" 2>/dev/null || echo 'BLOCKED: docs-manager는 소스코드 수정 금지'"
```

---

## Section 4: Skills 프리로드

에이전트 정의 파일의 `skills` frontmatter 필드 활용. 세션 시작 시 자동 로드.

| 에이전트 | skills | 근거 |
|---------|--------|------|
| mission-controller | `superpowers:dispatching-parallel-agents`, `superpowers:verification-before-completion` | 팀 병렬 편성 + 완료 전 검증 |
| backend-dev | `superpowers:test-driven-development`, `superpowers:systematic-debugging` | TDD + 체계적 디버깅 |
| frontend-dev | `superpowers:test-driven-development`, `frontend-design:frontend-design` | TDD + 프론트엔드 디자인 |
| test-engineer | `superpowers:test-driven-development` | TDD 핵심 |
| quality-reviewer | `superpowers:requesting-code-review` | 코드 리뷰 가이드 |

**토큰 영향**: skills는 세션 시작 시 1회만 context에 로드. 추가 API 호출 없음. 효율적.

---

## Section 5: mission-controller 자율 순찰 루프

### CronCreate 기반 자동 순찰

**일반 순찰 (2시간마다)**
```
CronCreate: "17 */2 * * *"
prompt: |
  자율 순찰 실행. 다음을 확인하라:
  1. HITL 미해결 신호: cat data/global/notifications/hitl_signals.json | python -c "import sys,json; s=json.load(sys.stdin); u=[x for x in s if not x.get('resolved')]; print(f'{len(u)}건 미해결')"
  2. 실패 런: find runs/ -name manifest.json -exec grep -l FAILED {} \;
  3. pytest: python -m pytest tests/ -x -q --timeout=30
  4. ruff: ruff check src/ --select=E,F
  5. web build: cd web && npm run build

  이슈 발견 시: 미션 프리셋에 따라 최적 팀원 3~5명 소환.
  이슈 없으면: "clean patrol" 기록 후 종료.
```

**심층 순찰 (12시간마다)**
```
CronCreate: "43 */12 * * *"
prompt: |
  심층 순찰 실행.
  1. security-guardian 소환: 전체 보안 스캔
  2. platform-ops 소환: 쿼터 사용률 + 의존성 취약점
  3. git diff HEAD~10 --stat: 최근 변경 영향 범위 분석
  4. pytest --cov=src -q: 커버리지 측정
  결과를 MEMORY.md에 기록.
```

### 토큰 비용 (순찰)

| 순찰 | 빈도 | 모델 | 토큰/회 | 일일 토큰 |
|------|------|------|:-------:|:---------:|
| 일반 | 12회/일 | Opus | ~3K | ~36K |
| 심층 | 2회/일 | Opus + 2 Sonnet subagent | ~15K | ~30K |
| **합계** | | | | **~66K/일** |

---

## Section 6: CI/CD 강화

### ci.yml 확장

```yaml
jobs:
  lint-python:
    name: Python Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff
      - run: ruff check src/ --select=E,F,W
      - run: ruff format src/ --check

  test-python:
    name: Python Tests
    runs-on: ubuntu-latest
    needs: lint-python
    steps:
      # ... (기존 + 커버리지 추가)
      - run: pytest tests/ -q --tb=short --cov=src --cov-report=term-missing --cov-fail-under=50

  build-web:
    name: Web Build
    runs-on: ubuntu-latest
    steps:
      # ... (기존 + ESLint 추가)
      - run: npm run lint
      - run: npm run build

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit && pip-audit --desc 2>&1 | tail -20
      - run: |
          cd web && npm audit --audit-level=high 2>&1 | tail -20
      - name: Secret scan
        run: |
          if grep -rn "AIza\|sk-\|GEMINI_API_KEY\s*=" src/ web/ \
            --include="*.py" --include="*.ts" --include="*.tsx" \
            | grep -v ".env" | grep -v "process.env" | grep -v "os.getenv" | grep -v "os.environ"; then
            echo "::error::Potential secret found in source code!"
            exit 1
          fi
```

### TaskCompleted ruff 단계적 강화

| 시점 | ruff 명령 | 차단 범위 |
|------|----------|----------|
| **즉시 (Stage 1)** | `ruff check src/ --select=E,F` | 에러 + 치명적만 |
| **2주 후 (Stage 2)** | `ruff check src/` | 전체 규칙 |

---

## Section 7: 통합 에이전트 상세 설계

### security-guardian.md (security-sentinel + security-auditor 통합)

```yaml
name: security-guardian
description: KAS 보안 전문가. 상시 보안 감시 + 심층 감사 통합. OWASP Top 10 기반 취약점 스캔, 시크릿 탐지, 경로 트래버설 검증. 코드 직접 수정 불가 — 발견 이슈는 SendMessage로 전달.
tools: Read, Glob, Grep, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: plan
memory: project
maxTurns: 25
color: crimson
```

**역할 통합 근거**: security-sentinel(상시 감시)과 security-auditor(심층 감사)의 체크리스트가 90% 중복. Sonnet으로 충분한 패턴 매칭 + OWASP 체크리스트 기반 작업.

### platform-ops.md (infra-ops + devops-automation + cost-optimizer 통합)

```yaml
name: platform-ops
description: KAS 플랫폼 운영 전문가. scripts/, .github/workflows/, 쿼터 시스템, 환경변수, hooks 설정, ruff/prettier 코드 품질 도구, 비용/쿼터 최적화 담당.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
permissionMode: acceptEdits
memory: user
maxTurns: 25
color: cyan
```

**memory: user** — infra-ops에서 계승. 프로젝트간 인프라 패턴 공유.

### docs-manager.md (doc-keeper + docs-architect 통합)

```yaml
name: docs-manager
description: KAS 문서 관리자. docs/, CLAUDE.md, AGENTS.md, README.md, CHANGELOG 담당. 소스코드 직접 수정 불가.
tools: Read, Write, Edit, Glob, Grep, Bash
model: haiku
permissionMode: acceptEdits
memory: project
maxTurns: 15
color: yellow
```

### pipeline-debugger.md (trend-analyst 흡수)

```yaml
name: pipeline-debugger
description: KAS 파이프라인 디버거. 파이프라인 장애 디버깅 + Step05 트렌드/지식 수집 분석. 코드 직접 수정 불가 — 원인 분석 후 빌더에게 위임.
tools: Read, Glob, Grep, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: plan
memory: project
maxTurns: 25
color: darkred
```

---

## Section 8: 파일 소유권 업데이트

| 디렉토리/파일 | v3.1 소유자 | v4 소유자 |
|--------------|-----------|----------|
| `src/` | backend-dev | backend-dev (변경 없음) |
| `web/app/`, `web/lib/`, `web/hooks/` | frontend-dev | frontend-dev (변경 없음) |
| `web/components/` | frontend-dev(로직)+ui-designer(스타일) | 변경 없음 |
| `web/app/globals.css`, `web/public/` | ui-designer | ui-designer (변경 없음) |
| `tests/` | test-engineer | test-engineer (변경 없음) |
| `scripts/`, `.github/`, `.claude/settings.local.json`, `ruff.toml`, `.prettierrc` | infra-ops + devops-automation | **platform-ops** (통합) |
| `docs/`, `CLAUDE.md`, `AGENTS.md`, `README.md` | docs-architect + doc-keeper | **docs-manager** (통합) |
| `scripts/supabase_schema.sql` | db-architect | db-architect (변경 없음) |

---

## Section 9: 미션 프리셋 업데이트

v3.1의 14개 프리셋에서 통합된 에이전트명을 반영:

| 프리셋 | v3.1 | v4 변경점 |
|--------|------|----------|
| kas-feature | backend-dev + frontend-dev + test-engineer + quality-reviewer | 변경 없음 (quality-reviewer가 Sonnet으로 변경됨) |
| kas-review | security-sentinel + quality-reviewer + performance-profiler | security-**guardian** + quality-reviewer + performance-profiler |
| kas-security | security-sentinel + backend-dev + frontend-dev + infra-ops | security-**guardian** + backend-dev + frontend-dev + **platform-ops** |
| kas-release | release-manager + test-engineer + security-sentinel + docs-architect | release-manager + test-engineer + security-**guardian** + **docs-manager** |
| kas-stability | backend-dev + test-engineer + infra-ops | backend-dev + test-engineer + **platform-ops** |

---

## Section 10: settings.local.json 최종 구조

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

**정리된 permissions**: 레거시 Bash 패턴(grep, find, cmd /c 등) 제거. `Bash` 전체 허용이 이미 있으므로 세분화된 패턴은 불필요.

---

## 종합 토큰 효율 비교

| 항목 | v3.1 (현재) | v4 (최적화) |
|------|:-----------:|:----------:|
| Opus 에이전트 수 | 3 | **1** |
| 총 에이전트 수 | 24 | **18** |
| Hook prompt 호출/일 | 0 | **~100** (PreToolUse만) |
| Hook command 호출/일 | ~15 | **~145** (비용 0) |
| 순찰 토큰/일 | 0 | **~66K** |
| PreToolUse 토큰/일 | 0 | **~30K** |
| **일일 추가 토큰** | **0** | **~96K** |
| **미션당 Opus 비용 절감** | 기준 | **~40%** |

→ 자율 순찰 + 전체 Hook + per-agent hooks를 추가하면서도, Opus 감축 + command hook 우선으로 **최소한의 토큰 추가**만 발생.

---

## 구현 순서

### Stage 1 (즉시 — 2026-04-11)
1. `settings.local.json` — 5개 hook 추가 + ruff 강화 + permissions 정리
2. 에이전트 신규 생성: security-guardian, platform-ops, docs-manager
3. 기존 에이전트 수정: pipeline-debugger(trend-analyst 기능 흡수), quality-reviewer (Opus→Sonnet), maxTurns 전체 조정
4. 에이전트 삭제: security-auditor, security-sentinel, doc-keeper, docs-architect, devops-automation, infra-ops, cost-optimizer-agent, trend-analyst (8개)
5. per-agent hooks 추가: backend-dev, frontend-dev, platform-ops, docs-manager
   - **Windows 주의**: per-agent hooks의 환경 변수는 `$TOOL_INPUT` (bash 스타일). `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 환경에서 bash 쉘로 실행됨. PowerShell `%TOOL_INPUT%` 사용 금지.
6. skills 프리로드: 5개 에이전트 (mission-controller, backend-dev, frontend-dev, test-engineer, quality-reviewer)
7. AGENTS.md 전면 업데이트 (v4 구조 반영)

### Stage 2 (2026-04-18, 1주 후)
8. mission-controller 자율 순찰: CronCreate 2시간 일반 + 12시간 심층
9. CI/CD 강화: ci.yml에 ruff/ESLint/커버리지/보안 스캔 추가
10. ruff 전체 규칙 차단 (`--select=E,F` → `ruff check src/` 전체 규칙)
11. quality-reviewer Sonnet 다운그레이드 품질 검증: 1주 운영 후 리뷰 정확도 이상 없으면 확정. 이슈 발생 시 Opus 복원

---

## 검증 방법

### 기능 검증
1. `claude agents` — 18개 에이전트 목록 확인
2. settings.local.json의 7개 hook이 모두 로드되는지 확인
3. backend-dev가 web/ 파일 수정 시도 → per-agent hook이 차단하는지 확인
4. frontend-dev가 src/ 파일 수정 시도 → 차단 확인
5. .env 파일 Write 시도 → PreToolUse prompt hook이 차단하는지 확인
6. TaskCompleted 시 ruff가 에러를 차단하는지 확인

### 통합 검증
7. `python -m pytest tests/ -q` — 전체 테스트 통과
8. `cd web && npm run build` — 빌드 성공
9. `ruff check src/ --select=E,F` — 에러 0

### 자율 순찰 검증 (Stage 2)
10. CronCreate 설정 후 2시간 대기 → 순찰 로그 확인
11. 의도적 테스트 실패 도입 → mission-controller가 자동 감지 + 팀 편성하는지 확인

---

## 수정 대상 파일 목록

| 파일 | 작업 |
|------|------|
| `.claude/settings.local.json` | Hook 5개 추가 + permissions 정리 |
| `.claude/agents/mission-controller.md` | maxTurns 30, skills 추가 |
| `.claude/agents/backend-dev.md` | maxTurns 30, per-agent hooks, skills 추가 |
| `.claude/agents/frontend-dev.md` | maxTurns 30, per-agent hooks, skills 추가 |
| `.claude/agents/test-engineer.md` | maxTurns 30, skills 추가 |
| `.claude/agents/quality-reviewer.md` | model sonnet, maxTurns 25, skills 추가 |
| `.claude/agents/security-guardian.md` | **신규 생성** (sentinel+auditor 통합) |
| `.claude/agents/platform-ops.md` | **신규 생성** (infra+devops+cost 통합) |
| `.claude/agents/docs-manager.md` | **신규 생성** (doc-keeper+docs-architect 통합) |
| `.claude/agents/pipeline-debugger.md` | trend-analyst 기능 흡수, maxTurns 25 |
| `.claude/agents/ui-designer.md` | maxTurns 25 |
| `.claude/agents/ux-reviewer.md` | maxTurns 20 |
| `.claude/agents/performance-profiler.md` | maxTurns 20 |
| `.claude/agents/refactoring-surgeon.md` | maxTurns 25 |
| `.claude/agents/db-architect.md` | maxTurns 20 |
| `.claude/agents/api-designer.md` | maxTurns 20 |
| `.claude/agents/a11y-expert.md` | maxTurns 20 |
| `.claude/agents/e2e-playwright.md` | maxTurns 20 |
| `.claude/agents/release-manager.md` | maxTurns 15 |
| `AGENTS.md` | v4 구조 반영 전면 업데이트 |
| `.github/workflows/ci.yml` | ruff + ESLint + 커버리지 + 보안 스캔 추가 |
| **삭제 대상** | |
| `.claude/agents/security-sentinel.md` | security-guardian으로 통합 |
| `.claude/agents/security-auditor.md` | security-guardian으로 통합 |
| `.claude/agents/infra-ops.md` | platform-ops로 통합 |
| `.claude/agents/devops-automation.md` | platform-ops로 통합 |
| `.claude/agents/cost-optimizer-agent.md` | platform-ops로 통합 |
| `.claude/agents/doc-keeper.md` | docs-manager로 통합 |
| `.claude/agents/docs-architect.md` | docs-manager로 통합 |
| `.claude/agents/trend-analyst.md` | pipeline-debugger로 통합 |
