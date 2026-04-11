# KAS Agent Teams v3 — 완전 자동화 최고 수준 설계

**날짜**: 2026-04-11
**상태**: 설계 확정, 구현 대기
**원칙**: 완전 자동화 + 토큰 효율 최적화 — 사람 개입은 최종 PR 승인만

---

## 1. Context

### 왜 이 변경이 필요한가

KAS Agent Teams v2(코어 4명)는 파일 소유권 분리와 비용 효율에서 건전한 설계였지만, "완전 자동화" 관점에서 다음 구조적 갭이 발견됨:

1. **테스트 작성자 부재** — backend-dev/frontend-dev 모두 `tests/` 수정 금지, quality-reviewer는 Write/Edit 금지
2. **보안 전담 부재** — quality-reviewer가 겸임하지만 부수적
3. **문서 자동 동기화 부재** — CLAUDE.md/AGENTS.md 업데이트 주체 불명확
4. **자가 치유 루프 부재** — 테스트 실패 시 "보고"로 끝남, 자동 수정 미시도
5. **TaskCompleted 훅 빈약** — pytest만 실행, npm build + 보안 스캔 누락

### 의도하는 결과

사람 개입 지점을 "최종 PR 리뷰 + 머지 승인"으로 축소. 태스크 분배 → 구현 → 테스트 → 보안 → 리뷰 → 문서 → PR 생성까지 자동화.

### v2에서 v3으로의 핵심 교정

| 항목 | v2 (현재) | v3 (목표) |
|------|-----------|-----------|
| 코어팀 | 4명 상시 | **5명 상시 + 2명 미션별** |
| 테스트 | 실행만 (quality-reviewer) | **작성+실행 (test-engineer + 공동)** |
| 보안 | quality-reviewer 겸임 | **전담 security-auditor (미션별)** |
| 문서 | 수동 | **doc-keeper 자동 동기화 (미션별)** |
| 자가 치유 | 없음 | **3회 자동 수정 → 에스컬레이션** |
| 훅 체인 | pytest만 | **pytest + npm build + 보안 스캔** |
| 비용 | 기준 100% | **평시 ~125%, 최대 ~160%** |

---

## 2. 팀 구성

### 상시 코어팀 (5명)

| # | 팀원 | 모델 | maxTurns | 소유 영역 | 금지 영역 | permissionMode |
|---|------|------|----------|-----------|-----------|---------------|
| 1 | `backend-dev` | Sonnet | 40 | `src/` 전체 | `web/` | acceptEdits |
| 2 | `frontend-dev` | Sonnet | 40 | `web/` 전체 | `src/` | acceptEdits |
| 3 | `test-engineer` | Sonnet | 35 | `tests/` 전체 | `src/step*/`, `web/app/` | acceptEdits |
| 4 | `quality-reviewer` | Sonnet | 25 | Read-only 전체 | 모든 소스 수정 | plan |
| 5 | `infra-ops` | Haiku | 20 | `scripts/`, `.github/`, 쿼터 | `src/step*/`, `web/app/` | default |

### 미션별 확장팀 (+2명, 필요 시에만 소환)

| # | 팀원 | 모델 | maxTurns | 소환 시점 | 자동 해산 |
|---|------|------|----------|-----------|----------|
| 6 | `security-auditor` | Sonnet | 25 | 보안 감사 미션, PR 생성 전 | 미션 완료 후 |
| 7 | `doc-keeper` | Haiku | 15 | 주요 기능 완료 후, 주기적 동기화 | 미션 완료 후 |

### 파일 소유권 매트릭스

```
src/pipeline.py          → backend-dev (KAS-PROTECTED: 수정 전 리드 확인)
src/step*/               → backend-dev
src/agents/              → backend-dev
src/core/                → backend-dev
src/quota/               → backend-dev (infra-ops 읽기 가능)
src/cache/               → backend-dev
web/app/                 → frontend-dev
web/components/          → frontend-dev
web/lib/                 → frontend-dev
web/hooks/               → frontend-dev
web/app/globals.css      → frontend-dev
tests/test_step*.py      → test-engineer (backend-dev 기여 가능)
tests/test_agents/       → test-engineer (backend-dev 기여 가능)
tests/conftest.py        → test-engineer (단독 소유)
scripts/                 → infra-ops
.github/workflows/       → infra-ops
data/global/quota/       → infra-ops
CLAUDE.md                → doc-keeper (미션별)
AGENTS.md                → doc-keeper (미션별)
docs/                    → doc-keeper (미션별)
```

**테스트 공동 작성 규칙**:
- backend-dev는 `tests/test_step*.py`, `tests/test_agents/`에 **직접 쓰기 가능**
- frontend-dev는 `tests/test_web*.py` (향후 생성 시)에 **직접 쓰기 가능**
- `tests/conftest.py`는 **test-engineer만 수정** (mock 패턴의 일관성 보장)
- backend/frontend-dev가 tests/에 기여한 코드는 test-engineer가 리뷰 후 확인

---

## 3. 에이전트 상세 설계

### 3.1 backend-dev (기존 + 보강)

**v2 대비 변경사항:**
- `context7` MCP 추가 (Gemini/FFmpeg/Python 라이브러리 문서 참조)
- tests/ 자기 영역 기여 가능 (`tests/test_step*.py`, `tests/test_agents/`)
- 자가 치유 프로토콜 추가

```yaml
# .claude/agents/backend-dev.md frontmatter
name: backend-dev
description: KAS 백엔드 전문가. src/ 디렉토리 전체 담당. 파이프라인 수정, 에러 전략, 에이전트 시스템 확장 작업 시 위임.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
permissionMode: acceptEdits
memory: project
maxTurns: 40
color: red
mcpServers:
  - context7
```

### 3.2 frontend-dev (기존 유지)

변경 없음. 기존 Playwright + context7 MCP 유지.

### 3.3 test-engineer (신규)

```yaml
name: test-engineer
description: KAS 테스트 전문가. tests/ 전체 소유. TDD 주도, conftest.py 관리, 커버리지 추적, E2E 테스트. 새 기능 개발 시 테스트 먼저 작성.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
permissionMode: acceptEdits
memory: project
maxTurns: 35
color: green
```

**system prompt 핵심 규칙:**
- conftest.py 3단계 방어 패턴 유지보수 (google.generativeai mock, import 선점, autouse fixture)
- `_load_and_register()` 패턴으로 `__init__.py` 우회
- `utf-8-sig` 인코딩 준수
- 모듈 바인딩 함정: 타겟 모듈에서 patch
- 커버리지 목표: `pytest --cov=src -q` 실행 후 보고
- backend-dev/frontend-dev의 테스트 기여 코드 리뷰

### 3.4 quality-reviewer (기존 + 역할 재정의)

**v2 대비 변경사항:**
- 보안 검사를 security-auditor에게 이관
- 코드 품질 + 아키텍처 패턴 + 성능에 집중

```yaml
name: quality-reviewer
description: KAS 코드 품질 전문가. 코드 리뷰, 아키텍처 패턴 검증, 성능 리뷰, CLAUDE.md 규칙 준수 검사. 코드를 직접 수정하지 않음.
tools: Read, Glob, Grep, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: plan
memory: project
maxTurns: 25
color: orange
```

**집중 영역:**
- CLAUDE.md 규칙 위반 탐지 (ssot, loguru, CSS 변수 등)
- 아키텍처 패턴 준수 (비침습적 원칙, SSOT, BaseAgent 패턴)
- 성능: N+1 쿼리, 불필요한 렌더링, 번들 크기
- 코드 가독성, 중복 제거

### 3.5 infra-ops (기존 + CI 소유권 확장)

**v2 대비 변경사항:**
- `.github/workflows/` 소유권 추가
- `memory: user → project` (팀 내 일관성)

```yaml
name: infra-ops
description: KAS 인프라/운영 전문가. scripts/, CI 유지보수, 쿼터 시스템, Supabase 동기화, 환경 변수 관리.
tools: Read, Write, Edit, Glob, Grep, Bash
model: haiku
permissionMode: default
memory: project
maxTurns: 20
color: cyan
```

**역할 경계**: CI/CD **유지보수** (의존성 업데이트, 환경변수 추가, 캐시 설정)만 담당. CI/CD **구조 설계** (matrix 전략, 배포 파이프라인 신설)는 리드 또는 backend-dev가 담당.

### 3.6 security-auditor (신규, 미션별)

```yaml
name: security-auditor
description: KAS 보안 전문가. OWASP Top 10, 의존성 취약점, 시크릿 탐지, 경로 트래버설 검증. 보안 감사 미션 또는 PR 전 최종 검증 시 소환.
tools: Read, Glob, Grep, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: plan
memory: project
maxTurns: 25
color: purple
```

**검사 항목:**
- OWASP Top 10 (경로 트래버설, SQL 인젝션, XSS, 인증 우회)
- `validateRunPath()` / `validateChannelPath()` 사용 여부
- `.env` 외부 API 키 하드코딩 탐지
- `pip-audit` / `npm audit` 실행 및 보고
- `getKasRoot()` import 경로 검증

**보고 형식:** quality-reviewer와 동일한 3단계 (치명적/중요/개선)

### 3.7 doc-keeper (신규, 미션별)

```yaml
name: doc-keeper
description: KAS 문서 관리 전문가. CLAUDE.md 자동 동기화, AGENTS.md 업데이트, API 변경 이력 추적. 주요 기능 완료 후 또는 주기적 동기화 시 소환.
tools: Read, Write, Edit, Glob, Grep, Bash
model: haiku
permissionMode: acceptEdits
memory: project
maxTurns: 15
color: yellow
```

**소유 파일:** `CLAUDE.md`, `AGENTS.md`, `docs/`, `README.md`
**금지:** `src/`, `web/`, `tests/` 소스코드

**주요 업무:**
- 새 API 라우트/컴포넌트/에이전트 추가 시 CLAUDE.md 반영
- AGENTS.md 미션 프리셋 업데이트
- `docs/superpowers/specs/` 설계 문서 정리
- git diff 기반 변경 감지 → 문서 드리프트 보고

---

## 4. 자동화 파이프라인

### 4.1 Hooks 설정

```json
{
  "hooks": {
    "TaskCompleted": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "cd \"C:/Users/조찬우/Desktop/ai_stuidio_claude\" && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10 && cd web && npm run build 2>&1 | tail -5"
      }]
    }]
  }
}
```

**3단계 품질 게이트:**
1. `pytest tests/ -x -q --timeout=60` — Python 백엔드 테스트
2. `cd web && npm run build` — TypeScript 타입 체크 + Next.js 빌드 검증
3. (보안 스캔은 security-auditor 미션에서 수행 — 훅에 포함 시 매 태스크마다 실행되어 비효율)

### 4.2 자가 치유(Self-Healing) 프로토콜

모든 구현 에이전트(backend-dev, frontend-dev, test-engineer)의 system prompt에 포함:

```markdown
## 자가 치유 프로토콜
1. 코드 수정 후 TaskCompleted 훅에서 테스트/빌드 실패 감지 시:
   - 실패 로그를 분석하고 원인을 파악한다
   - 자동으로 수정을 시도한다
2. 최대 3회 재시도. 각 시도마다 다른 접근법을 사용한다
3. 3회 실패 시:
   - 변경사항을 git stash로 보존한다
   - 리드에게 상세 실패 원인과 시도한 접근법을 보고한다
   - 다른 팀원에게 도움을 요청할 수 있다
```

### 4.3 자동 롤백 안전장치

```markdown
## 안전장치
- 작업 시작 전: 현재 git status를 기록한다
- 3회 수정 실패 시: `git checkout -- [수정한 파일들]`로 원복한다
- KAS-PROTECTED 파일(src/step08/__init__.py) 수정 시: 반드시 리드 확인 후 진행
- 원복 후 리드에게 상세 실패 원인을 보고한다
```

### 4.4 리뷰 → 자동 수정 루프

```
quality-reviewer/security-auditor가 이슈 발견
  ↓
구조화된 보고 형식으로 SendMessage:
  "🔴 치명적: src/step05/trend_collector.py:120 — open() 직접 사용. ssot.read_json() 사용 필요"
  ↓
해당 소유자 에이전트(backend-dev)가 수신
  ↓
자동 수정 → 테스트 실행 → 완료 보고
```

### 4.5 팀원 간 자동 통신 프로토콜

| 트리거 | 발신자 | 수신자 | 메시지 |
|--------|--------|--------|--------|
| src/ 파일 변경 완료 | backend-dev | test-engineer | "src/step05/ 변경됨. 관련 테스트 업데이트 확인 필요" |
| web/app/api/ 변경 완료 | frontend-dev | test-engineer | "API 라우트 변경됨. E2E 테스트 확인 필요" |
| API 계약 변경 | backend-dev | frontend-dev | "API /api/X 응답 포맷 변경. 변경 전/후 상세" |
| 테스트 실패 발견 | test-engineer | 해당 소유자 | "tests/test_X.py::test_name FAILED. 원인: ..." |
| 보안 취약점 발견 | security-auditor | 해당 소유자 | "CRITICAL: [파일:줄] 경로 트래버설 취약점" |
| 문서 드리프트 감지 | doc-keeper | 해당 소유자 | "CLAUDE.md의 [섹션]이 현재 코드와 불일치" |
| 인프라 변경 | infra-ops | [broadcast] | "scripts/X.py 변경됨. 다음 실행 전 확인" |

---

## 5. 미션별 프리셋 (기존 6개 + 신규 3개 = 9개)

### 기존 6개 (AGENTS.md에서 유지)

1. 풀스택 Feature 개발 (backend-dev + frontend-dev + quality-reviewer)
2. 3각 코드 리뷰 (quality-reviewer × 3)
3. 경쟁 가설 디버깅 (Sonnet × 3~5)
4. 파이프라인 안정화 (backend-dev + quality-reviewer + infra-ops)
5. 대시보드 리디자인 (frontend-dev + quality-reviewer)
6. 런타임 에이전트 확장 (backend-dev + quality-reviewer)

### 신규 3개

7. **보안 감사 미션**
```
kas-security 팀을 생성해줘.
- security-auditor: OWASP Top 10 + 의존성 스캔 + 시크릿 탐지
- quality-reviewer: 코드 품질 관점에서 보안 패턴 검증
- backend-dev: 발견된 취약점 즉시 수정
```

8. **테스트 커버리지 스프린트**
```
kas-test 팀을 생성해줘.
- test-engineer: 누락 테스트 작성 + conftest 최적화
- backend-dev: 백엔드 영역 테스트 기여
- frontend-dev: 프론트엔드 영역 테스트 기여
```

9. **문서 동기화 미션**
```
kas-docs 팀을 생성해줘.
- doc-keeper: CLAUDE.md + AGENTS.md + docs/ 전체 동기화
- quality-reviewer: 문서 정확성 검증
```

---

## 6. 토큰 효율 최적화

### 비용 구조

| 모드 | 활성 팀원 | 예상 비용 (v2 대비) |
|------|-----------|-------------------|
| 평시 (5명) | backend, frontend, test, quality, infra | ~125% |
| 보안 감사 (+1) | + security-auditor | ~150% |
| 문서 동기화 (+1) | + doc-keeper | ~130% |
| 풀 스펙트럼 (+2) | + security + doc-keeper | ~160% |

### 비용 절감 전략

1. **미션별 소환/해산** — security-auditor + doc-keeper는 필요 시에만 활성. 상시 5명으로 운영
2. **maxTurns 차등** — 구현자 35~40, 리뷰어 25, doc-keeper 15. 불필요한 장시간 실행 방지
3. **Haiku 적극 활용** — infra-ops + doc-keeper = Haiku. 반복적/텍스트 중심 작업에 최적
4. **CLAUDE.md 상세화** — 팀원의 컨텍스트 탐색 비용 절감. 모듈 경계가 명확할수록 탐색 토큰 감소
5. **TaskCompleted 훅에서 보안 스캔 제외** — 매 태스크마다 실행하면 비효율. 미션 단위로 수행

### 모델 선택 근거

| 팀원 | Sonnet인 이유 / Haiku인 이유 |
|------|--------------------------|
| backend-dev | 복잡한 파이프라인 코드 작성. Haiku로는 Step08 오케스트레이터 수준 불가 |
| frontend-dev | Next.js 16 + React 19 + Tailwind v4. 최신 프레임워크 조합은 Sonnet 필요 |
| test-engineer | conftest 3단계 방어, mock 패턴 등 복잡한 테스트 설계. Sonnet 필요 |
| quality-reviewer | 아키텍처 패턴 분석, 보안 냄새 감지. 분석 품질이 곧 코드 품질. Sonnet 유지 |
| security-auditor | false negative가 치명적. 보안 분석은 Sonnet 필수 |
| infra-ops | scripts/ 유지보수, 환경변수 추가 등 패턴이 명확. Haiku 충분 |
| doc-keeper | 텍스트 편집, 문서 동기화. 복잡한 추론 불필요. Haiku 충분 |

---

## 7. 수정할 파일 목록

### 신규 생성

| 파일 | 내용 |
|------|------|
| `.claude/agents/test-engineer.md` | 테스트 전문가 에이전트 정의 |
| `.claude/agents/security-auditor.md` | 보안 감사 에이전트 정의 |
| `.claude/agents/doc-keeper.md` | 문서 관리 에이전트 정의 |

### 기존 수정

| 파일 | 변경 내용 |
|------|----------|
| `.claude/agents/backend-dev.md` | context7 MCP 추가, tests/ 기여 권한, 자가 치유 프로토콜 |
| `.claude/agents/frontend-dev.md` | tests/ 기여 권한, 자가 치유 프로토콜 |
| `.claude/agents/quality-reviewer.md` | 보안 역할 이관, 품질+성능 집중으로 재정의 |
| `.claude/agents/infra-ops.md` | .github/ 소유권, memory→project, CI 유지보수 역할 |
| `.claude/settings.local.json` | TaskCompleted 훅 강화 (npm build 추가) |
| `AGENTS.md` | 7명 구성 반영, 신규 미션 프리셋 3개, 통신 프로토콜 업데이트 |
| `CLAUDE.md` | Agent Teams 섹션 업데이트 (7명 구성 반영) |

---

## 8. 검증 방법

### 구현 후 확인 항목

```bash
# 1. Agent Teams 활성화 + 7개 에이전트 확인
claude agents
# 기대 출력: backend-dev, frontend-dev, test-engineer, quality-reviewer,
#            security-auditor, infra-ops, doc-keeper (7개)

# 2. 상시 코어 5명 기능 테스트
#   a) backend-dev에게 간단한 src/ 수정 위임 → TaskCompleted 훅 동작 확인
#   b) test-engineer에게 테스트 작성 위임 → tests/ 파일 생성 확인
#   c) quality-reviewer에게 리뷰 요청 → Write/Edit 없이 리뷰 보고 확인

# 3. TaskCompleted 훅 체인 검증
#   pytest 통과 + npm build 통과 확인

# 4. 미션별 소환 테스트
#   kas-security 미션 실행 → security-auditor 소환/해산 확인
#   kas-docs 미션 실행 → doc-keeper 소환/해산 확인

# 5. 자가 치유 검증
#   의도적으로 테스트 실패하는 코드 작성 → 3회 자동 수정 시도 확인

# 6. 통신 프로토콜 검증
#   backend-dev가 src/ 수정 → test-engineer에게 메시지 도착 확인
```

---

## 9. 참고 자료

- [Claude Code Agent Teams 공식 문서](https://code.claude.com/docs/en/agent-teams)
- [Claude Code Subagents 공식 문서](https://code.claude.com/docs/en/sub-agents)
- [30 Tips for Claude Code Agent Teams — John Kim](https://getpushtoprod.substack.com/p/30-tips-for-claude-code-agent-teams)
- [Claude Code Agent Teams Setup Guide — claudefa.st](https://claudefa.st/blog/guide/agents/agent-teams)
- [Manage costs effectively — Claude Code Docs](https://code.claude.com/docs/en/costs)
- [Multi-Agent Software Development — vibecoding.app](https://vibecoding.app/blog/multi-agent-software-development-workflow)
- [From vibe coding to multi-agent orchestration — CIO](https://www.cio.com/article/4150165/from-vibe-coding-to-multi-agent-ai-orchestration-redefining-software-development.html)
- [Agent Teams in Claude Code: Real Cases — prodfeat.ai](https://www.prodfeat.ai/en/blog/2026-02-25-claude-code-agent-teams)
