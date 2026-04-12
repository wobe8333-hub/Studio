# KAS Agent Team v5 → S급(100점) 업그레이드 실행 계획

## Context

이전 감사 결과 현재 KAS Agent Team은 **A급 (61/100점)** 으로 판정됐다. 사용자는 즉시 **S급 (목표 100점)** 으로 승격을 요청. 본 계획은 공식 Anthropic Claude Code 문서(sub-agents · hooks · agent-teams)에 100% 부합하면서 토큰 효율을 최대화하고 완전 자율 운영을 달성하는 9-Phase 실행 절차다.

**목표 점수**: Before 61 → **After 100 (+39)**
**주요 변경 범위**: `.claude/settings.local.json`, `.claude/agents/*.md` 13개, `.claude/commands/*.md` 신규 6개, `CLAUDE.md`, `AGENTS.md`
**실행 주도**: mission-controller 감독 · ops-monitor 실 수정 · python-dev는 테스트 검증

---

## 승급 기준 매트릭스 (S급 100점 = 3축 각 100점)

| 축 | Before | After | 핵심 변경 |
|---|:---:|:---:|---|
| A. 토큰 효율 | 58 | **100** | 훅 1회 실행·async 전환·matcher if·initialPrompt 슬림·CLAUDE.md 분할 |
| B. 완전 자동화 | 55 | **100** | cron 일일 기동·slash 6개·Reflection 13개·UserPromptSubmit 훅 |
| C. 공식 부합 | 70 | **100** | 비공식 필드 제거·skills/MCP 우회·CLI 버전 검증·문서화 |

---

## Phase 1 — 훅 체계 재설계 (토큰 효율 P0)

### 1-1. `.claude/settings.local.json` 훅 블록 재구성
- **TaskCompleted** (유지, async 전환)
  ```json
  "TaskCompleted": [{
    "matcher": "",
    "hooks": [
      {"type":"command","command":"cd /c/Users/조찬우/Desktop/ai_stuidio_claude && python -m pytest tests/ -x -q --ignore=tests/test_step08_integration.py 2>&1 | tail -10","async":true},
      {"type":"command","command":"cd /c/Users/조찬우/Desktop/ai_stuidio_claude && ruff check src/ --fix --select=E,W,F,I 2>&1 | tail -5","async":true},
      {"type":"command","command":"cd /c/Users/조찬우/Desktop/ai_stuidio_claude/web && npm run build 2>&1 | tail -10","async":true}
    ]
  }]
  ```
- **Stop** (pytest/ruff 제거 → sanity check만, async)
  ```json
  "Stop": [{"matcher":"","hooks":[{"type":"command","command":"echo \"[v5:Stop] $(date +%H:%M:%S)\" >> \"C:/Users/조찬우/Desktop/ai_stuidio_claude/.claude/agent-logs/hooks.log\" 2>/dev/null || true","async":true}]}]
  ```
- **TaskCreated · SubagentStart · SubagentStop · TeammateIdle · WorktreeCreate · PostToolUse**: 전부 `"async":true` 추가
- **PreToolUse**: 동기 유지(차단 로직이므로), 단 matcher를 `"Write|Edit"` 유지

### 1-2. 에이전트별 SubagentStop 훅 제거
- `python-dev.md:25-28` SubagentStop pytest 블록 **제거** (TaskCompleted가 담당)
- `web-dev.md:25-28` SubagentStop npm build 블록 **제거** (TaskCompleted가 담당)
- 단일 책임 원칙: 품질 게이트는 `TaskCompleted` 한 곳에만

**검증**: 단일 태스크 완료 시 `pytest`가 정확히 **1회**만 실행됨 (로그에서 타임스탬프 체크)

---

## Phase 2 — Agent frontmatter 공식화 (공식 부합 P0)

### 2-1. 비공식 필드 처리 (13개 에이전트 모두)

공식 문서 `sub-agents` 에 명시된 필드만 유지하고, 나머지는 **주석으로 하강**:
- ✅ 공식: `name`, `description`, `tools`, `model`
- ⚠️ 비공식 (experimental flag 하에서만 동작, 주석 처리):
  - `maxTurns`, `permissionMode`, `isolation`, `background`, `memory`, `color`, `mcpServers`, `skills`, `hooks`, `initialPrompt`, `disallowedTools`, `effort`

실제 전략: **Agent Teams 문서가 skills/mcpServers 무시를 명시**했지만 `permissionMode`, `maxTurns`, `hooks`, `disallowedTools` 등 다른 필드는 Claude Code 2.1+에서 실동작하므로 유지. 단 `effort: high`는 공식 근거 0건이므로 **제거**.

### 2-2. mission-controller.md 개정
- `effort: high` **제거** (공식 미지원)
- `memory: user` → 주석으로 하강 + `# 실험적: agent-memory 디렉토리 수동 관리 대체 권장`
- 나머지 필드 유지
- initialPrompt 슬림화: CLAUDE.md 중복 제거 (아래 Phase 6)

### 2-3. 모든 에이전트의 `memory:` 필드 주석화
- `memory: project/user/local` → frontmatter에서 제거
- 대체: `.claude/agent-memory/{agent_name}/MEMORY.md` 디렉토리 관례 (Phase 7)

---

## Phase 3 — CLAUDE.md에 Agent Team 한계 우회 섹션 추가 (공식 부합 P0)

### 3-1. `CLAUDE.md` 하단에 신규 섹션 추가 (ops-monitor 작업)

```markdown
## Agent Team 한계 대응 (공식 agent-teams 문서 기반)

> **⚠️ 중요**: Agent Team mode (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1) 에서 
> teammate로 실행되는 subagent definition의 `skills`, `mcpServers` frontmatter 
> 필드는 **무시됨** (공식 문서 명시). Teammate는 프로젝트/사용자 세션의 
> skills와 MCP를 그대로 로드한다.

### 우회 정책
- `.claude/agents/*.md` 의 `skills:`, `mcpServers:` 는 subagent 단독 호출 시에만 유효
- Agent Team teammate 호출 시 필요한 스킬은 **본 CLAUDE.md** 에서 명시적으로 로딩되도록 안내
- MCP 서버(context7, playwright, figma)는 프로젝트 루트 `.claude/settings.local.json` 의 MCP 설정으로 전역 로드

### 에이전트별 필수 스킬 로딩 안내 (teammate 모드용)
| 에이전트 | 필수 스킬 | 필수 MCP |
|---|---|---|
| mission-controller | superpowers:brainstorming, superpowers:writing-plans, superpowers:dispatching-parallel-agents | context7 |
| python-dev | superpowers:test-driven-development, superpowers:systematic-debugging | context7 |
| web-dev | superpowers:test-driven-development, frontend-design:frontend-design | context7, playwright |
| design-dev | example-skills:frontend-design | figma, playwright |
| quality-security | superpowers:requesting-code-review | context7 |
| ops-monitor | claude-md-management:revise-claude-md | context7 |
| refactoring-surgeon | superpowers:systematic-debugging | context7 |
| pipeline-debugger | superpowers:systematic-debugging | — |
| video-specialist | superpowers:requesting-code-review | playwright |

### CLI 버전 요구사항
Agent Teams는 **Claude Code v2.1.32+** 필요. 
검증: `claude --version` → 2.1.32 이상인지 확인.
```

---

## Phase 4 — `.claude/commands/*.md` 6개 신설 (자동화 P0)

### 4-1. `.claude/commands/mission.md`
```markdown
---
description: mission-controller 소환 — 이슈 감지 + 팀 편성
---

mission-controller를 소환해서 다음 순서로 진행:
1. HITL 신호 스캔 (data/global/notifications/hitl_signals.json)
2. FAILED run 스캔 (runs/*/manifest.json)
3. 발견된 이슈 유형별로 팀 편성 (AGENTS.md 미션 프리셋 참조)
4. 소환 메시지 형식(미션 ID, 목표, 범위, 제약, 완료 기준) 으로 dispatch

$ARGUMENTS 가 있으면 특정 미션 설명으로 사용, 없으면 자율 감지.
```

### 4-2. `.claude/commands/audit.md`
```markdown
---
description: quality-security + performance-profiler 병렬 감사
---

quality-security 와 performance-profiler 를 병렬 소환 (dispatching-parallel-agents 스킬 활용).
- quality-security: OWASP Top 10 + 품질 + 아키텍처
- performance-profiler: N+1 쿼리, 번들 사이즈, 훅 실행 시간
결과를 mission-controller 에게 통합 리포트.
$ARGUMENTS: 감사 범위 (기본 "전체")
```

### 4-3. `.claude/commands/release.md`
```markdown
---
description: release-manager 로 CHANGELOG + tag + PR 생성
---

release-manager 소환.
1. git log --oneline 확인 (마지막 태그 이후)
2. feat/fix/refactor/docs/perf 분류
3. CHANGELOG.md 갱신
4. git tag $ARGUMENTS (버전 미지정 시 자동 계산)
5. gh pr create
```

### 4-4. `.claude/commands/kpi.md`
```markdown
---
description: Sub-Agent KPI 수집 및 AnalyticsLearningAgent 실행
---

python -c "from src.agents.analytics_learning import AnalyticsLearningAgent; print(AnalyticsLearningAgent().run())"
실행 후 결과를 mission-controller 에게 요약 전달.
Phase 승격/강등 알림은 notifications.json 에서 확인.
```

### 4-5. `.claude/commands/debug-pipeline.md`
```markdown
---
description: pipeline-debugger 소환 — Step 실패 분석
---

pipeline-debugger 소환. 다음을 분석:
1. logs/pipeline.log 의 최근 ERROR (tail -100)
2. runs/*/manifest.json 중 run_state=FAILED
3. data/global/step_progress.json
4. $ARGUMENTS 가 있으면 특정 Step 번호 집중 분석 (예: step08)
수정 제안은 python-dev 에게 SendMessage 로 위임.
```

### 4-6. `.claude/commands/verify.md`
```markdown
---
description: superpowers:verification-before-completion 실행
---

superpowers:verification-before-completion 스킬을 호출해서 
현재 변경사항이 완료 기준을 만족하는지 확인:
1. pytest tests/ --ignore=tests/test_step08_integration.py
2. ruff check src/
3. cd web && npm run build
4. git status 확인
실패 시 해당 Builder(python-dev/web-dev) 에게 자동 에스컬레이션.
```

---

## Phase 5 — CronCreate 기반 일일 자율 기동 (자동화 P1)

### 5-1. `.claude/settings.local.json` 에 cron 블록 추가 (혹은 CronCreate 도구로 생성)

사용자 수동 실행 1회 필요:
```bash
# Claude Code 내부에서 CronCreate 호출
# 매일 09:00 Asia/Seoul 에 mission-controller 자동 기동
```

CronCreate 설정:
- **schedule**: `0 9 * * *` (매일 09:00)
- **prompt**: "mission-controller 를 소환해서 HITL 신호와 FAILED run 을 자동 감지하고 필요 시 팀 편성해서 대응. 대응이 필요 없으면 로그만 남기고 종료."
- **model**: sonnet (비용 절감 — mission-controller 가 필요 시 Opus 소환)

**검증**: `CronList` 로 cron 등록 확인, 익일 09:00 로그 확인

---

## Phase 6 — initialPrompt 슬림화 (토큰 효율 P1)

모든 13개 에이전트의 `initialPrompt:` 에서 CLAUDE.md 와 중복되는 규칙 제거. 예:

### python-dev.md (Before)
```
initialPrompt: |
  conftest.py의 Gemini mock 3단계 방어를 숙지하세요.
  테스트: pytest --ignore=tests/test_step08_integration.py 사용 (--timeout 플래그 금지).
  JSON I/O: ssot.read_json()/write_json() 필수 (open() 직접 사용 금지).
  로깅: from loguru import logger (import logging 금지).
  KAS-PROTECTED: src/step08/__init__.py 수정 전 반드시 리드 확인.
```

### python-dev.md (After — 에이전트 고유 체크리스트만)
```
initialPrompt: |
  # CLAUDE.md 의 "핵심 규칙" 섹션 준수 (프로젝트 규칙 자동 로드됨).
  # python-dev 고유 체크:
  1. 테스트 변경 전 conftest.py 의 Gemini mock 3단계 방어 구조 Read.
  2. src/step08/__init__.py (KAS-PROTECTED) 수정 전 Read 필수.
  3. 실패 3회 후 mission-controller 에스컬레이션.
```

평균 60% 축소 예상. 유사 작업 12개 에이전트에 일괄 적용.

---

## Phase 7 — Reflection 패턴 13개 표준화 (자동화 P1)

### 7-1. `~/.claude/agent-memory/{agent_name}/MEMORY.md` 디렉토리 생성 관례

각 에이전트의 시스템 프롬프트 하단에 공통 섹션 추가:
```markdown
## Reflection 패턴 (세션 종료 전 필수)

미션 완료 후 `~/.claude/agent-memory/{본인 이름}/MEMORY.md` 에 기록:
- 효과적이었던 접근법
- maxTurns 내 미완료 작업
- 반복되는 함정/실패 패턴
- 다음 세션에서 참조할 교훈

파일이 없으면 신규 생성. 기존 있으면 append.
```

### 7-2. ops-monitor 가 13개 에이전트 정의에 Reflection 섹션 추가
현재 mission-controller.md 만 이 패턴을 명시 → **13개 모두** 적용.

---

## Phase 8 — CLI 버전 검증 + 문서화 (공식 부합 P2)

### 8-1. 사용자 실행
```bash
claude --version
```

### 8-2. 결과가 v2.1.32+ 이상이면 CLAUDE.md 에 기록
Phase 3 에서 이미 추가된 "CLI 버전 요구사항" 섹션에 검증 완료 주석 추가:
```markdown
### CLI 버전 요구사항
Agent Teams는 **Claude Code v2.1.32+** 필요.
**검증 완료**: 2026-04-12 기준 v2.1.XX (확인 명령: `claude --version`)
```

미달 시 업그레이드 안내.

---

## Phase 9 — 검증 & 결과 측정 (필수)

### 9-1. 정량 검증 체크리스트
- [ ] `.claude/settings.local.json` 의 pytest 훅 **1곳**만 존재 (grep -c "pytest" → 1)
- [ ] `async: true` 적용 훅 **6개 이상**
- [ ] `.claude/commands/` 에 `.md` 파일 **6개** 존재
- [ ] `.claude/agents/*.md` 전체에서 `effort:` 필드 **0건** (grep -l "effort:" → 없음)
- [ ] `CLAUDE.md` 에 "Agent Team 한계 대응" 섹션 존재
- [ ] `claude --version` **v2.1.32+** 확인
- [ ] `~/.claude/agent-memory/` 에 13개 에이전트 하위 디렉토리
- [ ] CronList 에 일일 mission-controller 트리거 1건

### 9-2. 토큰 절감 실측
- Before: 가상 태스크 1회 완료 시 pytest 3회 × ruff 2회 × build 2회 = 7개 동기 명령
- After: pytest 1회 × ruff 1회 × build 1회 (전부 async) = 3개 비동기 명령
- **실측 방법**: `.claude/agent-logs/hooks.log` 에서 TaskCompleted 전후 체감 지연 비교

### 9-3. 최종 점수 산출
위 체크리스트를 모두 통과하면 3축 각 100점, 종합 **100/100 S급** 달성.

---

## 수정 파일 총목록 (사전 승인 대상)

| # | 파일 | 변경 | 담당 Phase |
|---|---|---|---|
| 1 | `.claude/settings.local.json` | 훅 재설계 + async | 1 |
| 2 | `.claude/agents/mission-controller.md` | effort 제거 + initialPrompt 슬림 + Reflection | 2·6·7 |
| 3 | `.claude/agents/python-dev.md` | SubagentStop 제거 + initialPrompt 슬림 + Reflection | 1·6·7 |
| 4 | `.claude/agents/web-dev.md` | SubagentStop 제거 + initialPrompt 슬림 + Reflection | 1·6·7 |
| 5 | `.claude/agents/design-dev.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 6 | `.claude/agents/quality-security.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 7 | `.claude/agents/ops-monitor.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 8 | `.claude/agents/db-architect.md` | Reflection | 7 |
| 9 | `.claude/agents/refactoring-surgeon.md` | Reflection | 7 |
| 10 | `.claude/agents/pipeline-debugger.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 11 | `.claude/agents/performance-profiler.md` | Reflection | 7 |
| 12 | `.claude/agents/ux-a11y.md` | Reflection | 7 |
| 13 | `.claude/agents/video-specialist.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 14 | `.claude/agents/release-manager.md` | initialPrompt 슬림 + Reflection | 6·7 |
| 15 | `.claude/commands/mission.md` | 신규 | 4 |
| 16 | `.claude/commands/audit.md` | 신규 | 4 |
| 17 | `.claude/commands/release.md` | 신규 | 4 |
| 18 | `.claude/commands/kpi.md` | 신규 | 4 |
| 19 | `.claude/commands/debug-pipeline.md` | 신규 | 4 |
| 20 | `.claude/commands/verify.md` | 신규 | 4 |
| 21 | `CLAUDE.md` | Agent Team 한계 섹션 + CLI 버전 | 3·8 |
| 22 | `AGENTS.md` | 변경 반영 (Phase 1·2·4·7) | 후반 |
| 23 | `docs/superpowers/specs/2026-04-12-agent-team-audit-design.md` | 감사 리포트 보존 (이전 plan file 내용) | 0 |

**총 23개 파일 (신규 7 · 수정 16)**

---

## 사용자 개입 필요 항목 (수동)

1. **Phase 5**: `CronCreate` 호출은 Claude Code 내부 도구이나 처음 등록 시 사용자 확인 필요
2. **Phase 8**: `claude --version` 실행은 자동이나 **결과가 v2.1.32 미만이면 사용자가 CLI 업그레이드 필요**
3. 각 Phase 완료 후 중간 검증 (사용자가 원하는 경우)

---

## 예상 소요 (참고)

- Phase 1~4: 훅·frontmatter·commands 일괄 (ops-monitor 주도)
- Phase 5: cron 등록 (1회성)
- Phase 6~7: 13개 에이전트 initialPrompt·Reflection 일괄 (ops-monitor)
- Phase 8~9: 검증 & 점수 산출

모든 변경은 git에 단일 커밋으로 기록:
`feat: Agent Team v5 → S급(100점) 업그레이드 — 공식 부합·토큰 효율·완전 자동화`

---

## 롤백 전략

- 각 Phase 별 단일 커밋으로 분리 (9개 커밋)
- Phase N 실패 시 `git revert <phase-N-commit>` 로 해당 Phase만 되돌림
- `.claude/settings.local.json` 은 사전에 `.backup` 복사본 생성

---

## 승인 요청

본 9-Phase 계획대로 진행할지 승인 요청.
- **Y**: Phase 1부터 순차 실행 (ops-monitor 위임 / 큰 변경 시마다 중간 승인)
- **부분 선택**: 특정 Phase만 실행 (예: "Phase 1·2·4만")
- **수정 요청**: 우선순위나 범위 조정

---

## 참조 공식 문서

- sub-agents: <https://code.claude.com/docs/en/sub-agents>
- hooks: <https://code.claude.com/docs/en/hooks>
- agent-teams: <https://code.claude.com/docs/en/agent-teams>
