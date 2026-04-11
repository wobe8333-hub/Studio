# Ultimate Agent Teams v3 — Design Spec

**날짜**: 2026-04-11
**목표**: KAS 프로젝트의 코드 품질, 보안, 자동화를 최고 수준으로 끌어올리는 완전 자율 운영 Agent Teams 설계

---

## 1. 배경 및 동기

### 현재 상태 (Agent Teams v2)
- 코어 4명: backend-dev(Sonnet), frontend-dev(Sonnet), quality-reviewer(Sonnet/plan), infra-ops(Haiku)
- 런타임 Sub-Agent 6개: DevMaintenance, AnalyticsLearning, UiUx, VideoStyle, ScriptQuality, CostOptimizer
- 미션별 소환 프리셋 6가지

### 핵심 문제점
1. **tests/ 소유권 모호**: quality-reviewer는 읽기전용, backend-dev/frontend-dev는 tests/ 금지 → 테스트를 누가 작성하는지 불명확
2. **웹 프론트엔드 테스트 완전 부재**: web/ 5,924줄에 테스트 0개
3. **핵심 모듈 테스트 없음**: `ssot.py`, `config.py`, `manifest.py` 등 SSOT 모듈 테스트 0개
4. **Python 린터/포매터 미설정**: ruff, black, mypy 등 어떤 도구도 없음
5. **API 라우트 인증 부재**: Next.js middleware 없음, `DASHBOARD_PASSWORD` 미설정 시 완전 우회
6. **런타임 에이전트 오케스트레이션 부재**: 6개 에이전트가 독립 실행, 자동 트리거 없음
7. **mission-controller 부재**: 이슈 자동 감지 및 팀 편성 자동화 없음
8. **접근성 극히 부족**: aria 속성 28건 (대부분 shadcn 기본 제공)
9. **ssot 규칙 위반**: ScriptQualityAgent, CostOptimizerAgent가 `ssot.write_json()` 미사용
10. **infra-ops 모델 부적합**: Haiku로 스크립트 수정 시 품질 문제

### 목표
- 완전 자율 운영: 에이전트가 이슈를 자동 감지하고, 팀을 편성하고, 수정하고, PR 생성
- 사용자(Lead)는 최종 머지 승인만 담당
- 토큰 효율: 상시 활성 최소화, 필요 시에만 전문가 소환

---

## 2. 아키텍처 — 3-Layer Command Structure

```
Lead (사용자) — 최종 머지 승인만 담당
  │
  ├── LAYER 1: COMMAND (지휘부) ── 1명, 상시
  │   └── mission-controller (Opus)
  │
  ├── LAYER 2: STANDING (상시 운영팀) ── 7명, 미션 시 활성
  │   ├── [빌더] backend-dev (Sonnet), frontend-dev (Sonnet)
  │   ├── [가디언] test-engineer (Sonnet), security-sentinel (Opus), quality-gate (Opus)
  │   └── [운영] infra-ops (Sonnet), devops-automation (Sonnet)
  │
  └── LAYER 3: SPECIALISTS (전문가 풀) ── 12명, 소환 시에만 활성
      performance-profiler, a11y-expert, docs-architect, db-architect,
      refactoring-surgeon, pipeline-debugger, video-qa-specialist,
      trend-analyst, api-designer, release-manager, e2e-playwright,
      cost-optimizer
```

**총 20명 정의** — 일상 작업 시 2-4명 활성, 대규모 미션 시 최대 6-7명.

---

## 3. Layer 1: mission-controller (신규)

### 역할
- 자율적 이슈 감지, 팀 편성, 작업 분배, 충돌 조율
- Reflection 패턴으로 세션 간 교훈 누적
- HITL 신호 모니터링 및 자동 에스컬레이션

### 에이전트 정의
```yaml
name: mission-controller
description: 자율적 이슈 감지 및 팀 편성 오케스트레이터. HITL 신호, 테스트 실패, 빌드 실패를 자동 감지하고 최적의 팀원 조합을 소환하여 해결.
model: opus
maxTurns: 50
permissionMode: plan
disallowedTools: [Write, Edit]
mcpServers: [context7]
memory: project
color: gold
```

### 자동 감지 트리거
| 트리거 | 소스 | 대응 |
|--------|------|------|
| HITL 미해결 신호 | `data/global/notifications/hitl_signals.json` | 유형별 적절한 팀원 소환 |
| pytest 실패 | TaskCompleted 훅 exit code 2 | test-engineer + 해당 빌더 소환 |
| npm build 실패 | TaskCompleted 훅 exit code 2 | frontend-dev 소환 |
| 보안 스캔 경고 | security-sentinel 보고 | security-sentinel + 해당 빌더 소환 |
| 커버리지 < 80% | test-engineer 보고 | 테스트 커버리지 블리츠 미션 발동 |
| 쿼터 95% 초과 | cost-optimizer 보고 | infra-ops + cost-optimizer 소환 |

### 팀 편성 규칙
```
백엔드 버그       → backend-dev + test-engineer + quality-gate
프론트엔드 기능    → frontend-dev + e2e-playwright + quality-gate
보안 이슈         → security-sentinel + 해당 빌더 + quality-gate
성능 문제         → performance-profiler + 해당 빌더
리팩토링          → refactoring-surgeon + test-engineer + quality-gate
API 변경          → api-designer + backend-dev + frontend-dev + docs-architect
릴리스            → release-manager + test-engineer + security-sentinel + docs-architect
파이프라인 실패    → pipeline-debugger + backend-dev + infra-ops
```

---

## 4. Layer 2: 상시 운영팀 (7명)

### 4-1. backend-dev (기존 유지, tests/ 기여 허용)

```yaml
name: backend-dev
description: KAS 백엔드 전문가. src/ 전체 및 Python tests/ 기여.
model: sonnet
maxTurns: 40
permissionMode: acceptEdits
memory: project
color: red
```

**변경사항**: `tests/` 금지 해제 → 기여 가능 (단, test-engineer 리뷰 필요)
**소유 영역**: `src/pipeline.py`, `src/step*/`, `src/agents/`, `src/core/`, `src/quota/`, `src/cache/`
**금지 영역**: `web/`
**MCP**: 없음

### 4-2. frontend-dev (기존 유지, tests/ 기여 허용)

```yaml
name: frontend-dev
description: KAS 프론트엔드 전문가. web/ 전체 및 웹 tests/ 기여.
model: sonnet
maxTurns: 40
permissionMode: acceptEdits
memory: project
color: blue
mcpServers: [playwright, context7]
```

**변경사항**: `tests/` 금지 해제 → 기여 가능 (단, test-engineer 리뷰 필요)
**소유 영역**: `web/app/`, `web/components/`, `web/lib/`, `web/hooks/`, `web/public/`
**금지 영역**: `src/`

### 4-3. test-engineer (신규)

```yaml
name: test-engineer
description: 테스트 전담 엔지니어. tests/ 소유자. TDD 강제, 커버리지 90% 목표. 백엔드 pytest + 프론트엔드 Vitest/Playwright 모두 담당.
model: sonnet
maxTurns: 40
permissionMode: acceptEdits
memory: project
color: green
mcpServers: [playwright]
```

**소유 영역**: `tests/`, `web/**/*.test.{ts,tsx}`, `web/**/*.spec.{ts,tsx}`, `conftest.py`, `pytest.ini`, `vitest.config.ts`
**금지 영역**: `src/step*/` (구현 코드 수정 불가, 테스트만 작성)
**핵심 규칙**:
- 새 기능/버그 수정 시 반드시 테스트부터 작성 (TDD)
- `conftest.py` 3단계 방어 패턴 준수
- `_load_and_register()` 패턴으로 Step08 모듈 격리 테스트
- `utf-8-sig` 인코딩 필수
- 커버리지 목표: Python 90%, Web 80%

### 4-4. security-sentinel (신규)

```yaml
name: security-sentinel
description: 상시 보안 감시 에이전트. OWASP Top 10, 경로 트래버설, API 키 하드코딩, 인증 미들웨어, Supabase RLS 검증.
model: opus
maxTurns: 30
permissionMode: plan
disallowedTools: [Write, Edit]
memory: project
color: crimson
```

**역할**: 읽기전용 보안 감사
**검사 항목**:
1. 경로 트래버설: `validateRunPath()`/`validateChannelPath()` 미사용 감지
2. API 키 하드코딩: `src/`, `web/` 전체 스캔
3. 인증 우회: `DASHBOARD_PASSWORD` 미설정 시 동작 검증
4. Supabase RLS: `createAdminClient()` 남용 감지
5. spawn 입력 검증: `child_process.spawn` 인자 검증
6. 의존성 취약점: `requirements.txt`, `package.json` CVE 스캔
**보고**: 치명적/중요/개선/정보 4단계 구조화 리포트

### 4-5. quality-gate (기존 강화, Opus 승격)

```yaml
name: quality-gate
description: 3차원 코드 리뷰어. 코드 품질(클린코드), 아키텍처(SOLID/DRY), CLAUDE.md 규칙 준수를 동시 검증. 기존 quality-reviewer에서 Opus로 승격.
model: opus
maxTurns: 35
permissionMode: plan
disallowedTools: [Write, Edit]
memory: project
color: orange
```

**변경사항**: Sonnet → Opus 승격, maxTurns 30 → 35
**3차원 리뷰**:
1. **코드 품질**: 클린코드 원칙, 네이밍, 복잡도, 중복
2. **아키텍처**: SOLID, DRY, 모듈 경계, 의존성 방향
3. **규칙 준수**: CLAUDE.md 핵심 규칙 6가지(ssot, loguru, 경로보안, CSS 변수, 비침습, BaseAgent)

### 4-6. infra-ops (기존 수정, Sonnet 승격)

```yaml
name: infra-ops
description: 인프라 운영 전문가. scripts/, 쿼터 시스템, 환경변수, CI/CD 파이프라인 관리.
model: sonnet
maxTurns: 30
permissionMode: acceptEdits
memory: user
color: cyan
```

**변경사항**: Haiku → Sonnet 승격, permissionMode default → acceptEdits
**소유 영역**: `scripts/`, `data/global/quota/`, `.env.example`, `requirements.txt`, `.github/workflows/`
**금지 영역**: `src/step*/`, `web/components/`, `web/app/`

### 4-7. devops-automation (신규)

```yaml
name: devops-automation
description: 자동화 파이프라인 전문가. Hooks 설정, Cron 스케줄, CI/CD 통합, 린터/포매터 설정.
model: sonnet
maxTurns: 30
permissionMode: acceptEdits
memory: project
color: purple
```

**소유 영역**: `.claude/settings.local.json` (hooks), `ruff.toml`, `.prettierrc`, `pyproject.toml` (tool 섹션), `.editorconfig`
**금지 영역**: `src/step*/`, `web/app/`
**핵심 역할**:
- Hooks 설정 관리 (TaskCompleted, TeammateIdle, PreCommit)
- ruff + prettier 설정 및 CI 통합
- Cron 스케줄 설정 및 유지보수

---

## 5. Layer 3: 전문가 풀 (12명)

모든 전문가는 `.claude/agents/`에 정의 파일만 존재. mission-controller가 필요 시 소환.

### 5-1. performance-profiler

```yaml
name: performance-profiler
description: 성능 프로파일링 전문가. N+1 쿼리, 메모리 누수, 번들 사이즈, 캐시 효율, 폴링→SSE 전환 분석.
model: sonnet
maxTurns: 25
permissionMode: plan
disallowedTools: [Write, Edit]
color: yellow
```

### 5-2. a11y-expert

```yaml
name: a11y-expert
description: 접근성 전문가. WCAG 2.1 AA 준수, aria 속성, 키보드 네비게이션, 스크린리더 호환성 검증 및 수정.
model: sonnet
maxTurns: 25
permissionMode: acceptEdits
color: teal
```

**소유 영역**: `web/` (접근성 속성 추가에 한정)

### 5-3. docs-architect

```yaml
name: docs-architect
description: 문서 전문가. API OpenAPI 스펙, CHANGELOG, RUNBOOK 현행화, 코드 주석 정리.
model: haiku
maxTurns: 20
permissionMode: acceptEdits
color: gray
```

**소유 영역**: `docs/`, `CHANGELOG.md`, `README.md`

### 5-4. db-architect

```yaml
name: db-architect
description: 데이터베이스 설계 전문가. Supabase 스키마 변경, 마이그레이션 스크립트, RLS 정책, 타입 동기화.
model: sonnet
maxTurns: 25
permissionMode: acceptEdits
color: indigo
```

**소유 영역**: `scripts/supabase_schema.sql`, `web/lib/types.ts` (auto-generated 섹션)

### 5-5. refactoring-surgeon

```yaml
name: refactoring-surgeon
description: 안전한 리팩토링 전문가. God Module 분해, 의존성 정리, 코드 구조 개선. 반드시 테스트 통과 유지.
model: sonnet
maxTurns: 30
permissionMode: acceptEdits
color: pink
```

**대상 후보**: `src/quota/__init__.py` (598줄), `web/app/monitor/page.tsx` (990줄)

### 5-6. pipeline-debugger

```yaml
name: pipeline-debugger
description: 파이프라인 Step 실패 분석 전문가. Step08 오케스트레이터, FFmpeg, Gemini API, 쿼터 에러 디버깅.
model: sonnet
maxTurns: 30
permissionMode: plan
disallowedTools: [Write, Edit]
color: darkred
```

### 5-7. video-qa-specialist

```yaml
name: video-qa-specialist
description: 영상 품질 검증 전문가. SHA-256 무결성, 해상도/코덱 검증, 자막 동기화, Shorts 크롭 검증.
model: sonnet
maxTurns: 20
permissionMode: plan
disallowedTools: [Write, Edit]
color: coral
```

### 5-8. trend-analyst

```yaml
name: trend-analyst
description: 트렌드 분석 전문가. Step05 소스별 수집 성능, 점수 캘리브레이션, 채널별 주제 적합도 분석.
model: haiku
maxTurns: 20
permissionMode: plan
disallowedTools: [Write, Edit]
color: olive
```

### 5-9. api-designer

```yaml
name: api-designer
description: API 설계 전문가. RESTful 엔드포인트 설계, 타입 안전성, 요청/응답 스키마, 버전 관리.
model: sonnet
maxTurns: 25
permissionMode: plan
color: navy
```

### 5-10. release-manager

```yaml
name: release-manager
description: 릴리스 관리 전문가. CHANGELOG 생성, git tag, PR 생성, 버전 범프, 릴리스 노트.
model: haiku
maxTurns: 20
permissionMode: acceptEdits
color: silver
```

### 5-11. e2e-playwright

```yaml
name: e2e-playwright
description: E2E 테스트 전문가. Playwright MCP로 시각적 회귀 테스트, 사용자 흐름 검증, 모바일 반응형 테스트.
model: sonnet
maxTurns: 25
permissionMode: acceptEdits
mcpServers: [playwright]
color: lime
```

### 5-12. cost-optimizer

```yaml
name: cost-optimizer
description: 비용 최적화 전문가. Gemini/YouTube 쿼터 사용 패턴 분석, 채널별 비용 집계, 최적화 권장.
model: haiku
maxTurns: 20
permissionMode: plan
disallowedTools: [Write, Edit]
color: bronze
```

---

## 6. 자동화 체계

### 6-1. Hooks

#### TaskCompleted (기존 강화)
```bash
#!/bin/bash
# 모든 팀원 작업 완료 시 실행
set -e
cd "$KAS_ROOT"
python -m pytest tests/ -x -q --timeout=60
ruff check src/ --exit-zero  # 린트 (초기에는 경고만, 점진적 강화)
cd web && npm run build
```
실패 시 `exit 2` → 작업 완료 차단, mission-controller에 피드백

#### TeammateIdle (신규)
```bash
#!/bin/bash
# 팀원 유휴 시 실행 — 자동 품질 스캔
echo "idle-scan: checking last commit for issues"
cd "$KAS_ROOT"
git diff HEAD~1 --name-only | head -20
# 변경 파일 목록을 피드백으로 전달 → mission-controller가 판단
```

### 6-2. Cron 스케줄

| 주기 | 작업 | 담당 에이전트 | 설명 |
|------|------|-------------|------|
| 30분 | 헬스체크 | devops-automation | `step_progress.json` + `hitl_signals.json` 상태 확인 |
| 1시간 | 커버리지 리포트 | test-engineer | `pytest --cov=src -q` → 갭 보고 |
| 6시간 | 보안 스캔 | security-sentinel | OWASP, 의존성, API 키 전체 스캔 |
| 일 1회 | 쿼터 분석 | cost-optimizer | Gemini/YouTube 사용량 + 비용 리포트 |
| 일 1회 | 규칙 감사 | quality-gate | CLAUDE.md 핵심 규칙 준수 검사 |
| 주 1회 | 복잡도 리포트 | refactoring-surgeon | 파일별 라인 수, 복잡도 초과 후보 |

### 6-3. Reflection 패턴

```
세션 완료 시:
  1. mission-controller가 세션 교훈 추출
  2. .claude/agent-memory/{agent}/MEMORY.md에 기록
  3. 반복 실패 패턴 감지 시 CLAUDE.md 규칙 추가 제안
  4. Lead 승인 후 CLAUDE.md 업데이트 (claude-md-management 스킬 활용)
```

---

## 7. 미션 프리셋 (12가지)

| # | 미션명 | 소환 조합 | 트리거 조건 |
|---|--------|-----------|------------|
| 1 | 풀스택 Feature | backend + frontend + test + quality-gate | 기능 요청 |
| 2 | 3차원 코드 리뷰 | security + quality-gate + performance | PR 생성 시 |
| 3 | 경쟁 가설 디버깅 | pipeline-debugger x3 (다른 가설 할당) | Step 실패 |
| 4 | 파이프라인 안정화 | backend + pipeline-debugger + infra-ops | HITL 신호 |
| 5 | 대시보드 리디자인 | frontend + a11y + e2e-playwright | UI 변경 요청 |
| 6 | 런타임 에이전트 확장 | backend + test + quality-gate | Sub-Agent 추가 |
| 7 | 보안 강화 | security + backend + frontend + infra-ops | 취약점 발견 |
| 8 | 테스트 커버리지 블리츠 | test + backend + frontend + e2e-playwright | 커버리지 < 80% |
| 9 | 리팩토링 스프린트 | refactoring + test + quality-gate | 복잡도 초과 |
| 10 | API 계약 변경 | api-designer + backend + frontend + docs | API 변경 시 |
| 11 | 릴리스 준비 | release + test + security + docs | 릴리스 요청 |
| 12 | 성능 최적화 | performance + backend or frontend + test | 응답시간 초과 |

---

## 8. 멀티모델 전략

| 모델 | 에이전트 | 역할 유형 | 비용 수준 |
|------|---------|----------|----------|
| **Opus** | mission-controller, security-sentinel, quality-gate | 판단/리뷰/감사 | 높음 (정확도 중요) |
| **Sonnet** | backend-dev, frontend-dev, test-engineer, infra-ops, devops-automation, performance-profiler, a11y-expert, db-architect, refactoring-surgeon, pipeline-debugger, video-qa-specialist, api-designer, e2e-playwright | 구현/테스트/분석 | 중간 (비용-성능 최적) |
| **Haiku** | docs-architect, trend-analyst, release-manager, cost-optimizer | 문서/집계/단순 분석 | 낮음 (비용 절감) |

**비용 분배**: Opus 3명(15%), Sonnet 13명(70%), Haiku 4명(15%)

---

## 9. AGENTS.md 업데이트 사항

### 팀 규모 변경
- 코어팀: 4명 → **8명** (mission-controller + 상시 7명)
- 미션별 추가 소환: 최대 3명 → **최대 5명** (총 동시 활성 최대 13명)
- 전문가 풀: 0명 → **12명 정의**

### 파일 소유권 변경
```
src/                → backend-dev (독점)
web/                → frontend-dev (독점)
tests/              → test-engineer (소유) + backend-dev/frontend-dev (기여)
scripts/            → infra-ops (독점)
docs/               → docs-architect (소유, 다른 팀원 기여 가능)
.claude/            → devops-automation (hooks/설정), mission-controller (memory)
.github/workflows/  → infra-ops + devops-automation (공동)
```

### 통신 프로토콜 추가
- **mission-controller → 팀원**: 미션 할당 메시지 (목표, 범위, 제약조건 명시)
- **팀원 → mission-controller**: 작업 완료/실패 보고 (결과 요약 + 교훈)
- **security-sentinel → 빌더**: 취약점 발견 즉시 알림 (파일:줄번호 + 심각도 + 수정 가이드)
- **test-engineer → 빌더**: 테스트 실패 알림 (실패 테스트 + 재현 단계)

### Anti-Patterns 추가
- mission-controller 우회하여 직접 대규모 팀 편성 금지
- 전문가 풀 에이전트가 소유권 없는 파일 수정 금지
- security-sentinel/quality-gate가 코드를 직접 수정하는 것 금지 (반드시 빌더에게 위임)
- 같은 미션에 Opus 에이전트 4명 이상 동시 소환 금지 (비용 폭주)

---

## 10. 구현 범위

### Phase 1: 에이전트 정의 파일 생성
- `.claude/agents/`에 20개 에이전트 정의 파일 생성/수정
- 기존 4개 수정: backend-dev, frontend-dev, quality-reviewer → quality-gate, infra-ops
- 신규 4개 (상시): mission-controller, test-engineer, security-sentinel, devops-automation
- 신규 12개 (전문가 풀): 각 1개 파일

### Phase 2: AGENTS.md 전면 개편
- 3-Layer 구조 반영
- 미션 프리셋 12가지 문서화
- 통신 프로토콜 및 Anti-Patterns 업데이트
- 멀티모델 전략 문서화

### Phase 3: Hooks 설정
- `.claude/settings.local.json` TaskCompleted 훅 강화 (ruff 추가)
- TeammateIdle 훅 신규 설정
- ruff.toml, .prettierrc 설정 파일 생성

### Phase 4: agent-memory 디렉토리 구조
- `.claude/agent-memory/` 8개 에이전트별 디렉토리 생성
- 각 디렉토리에 초기 `MEMORY.md` 생성

---

## 11. v2 → v3 마이그레이션

| 항목 | v2 (현재) | v3 (목표) |
|------|-----------|-----------|
| 코어팀 | 4명 | 8명 |
| 전문가 풀 | 0명 | 12명 |
| 총 정의 | 4개 | 20개 |
| 모델 | Sonnet 3 + Haiku 1 | Opus 3 + Sonnet 13 + Haiku 4 |
| tests/ 소유 | 모호 | test-engineer 명확 소유 |
| 자동화 | TaskCompleted 훅 1개 | Hooks 3개 + Cron 6개 |
| Reflection | 없음 | mission-controller 세션별 누적 |
| 미션 프리셋 | 6가지 | 12가지 |

### 하위 호환성
- 기존 4개 에이전트의 이름과 핵심 역할 유지
- quality-reviewer → quality-gate 이름 변경 (모델 승격 반영)
- 기존 에이전트 정의 파일은 내용 수정만 (삭제하지 않음)

---

## 12. 검증 방법

### 구현 후 검증
1. `claude agents` 명령으로 20개 에이전트 목록 확인
2. 각 에이전트 정의 파일의 YAML frontmatter 유효성 검증
3. 미션 프리셋별 소환 테스트 (1-2개 대표 미션)
4. TaskCompleted 훅 실행 테스트 (pytest + ruff + npm build)
5. agent-memory 디렉토리 구조 확인

### 품질 지표 (구현 후 추적)
- Python 테스트 커버리지: 현재 → 90% 목표
- Web 테스트 커버리지: 0% → 80% 목표
- 보안 스캔 통과율: 측정 시작
- CLAUDE.md 규칙 위반 건수: 추적 시작
- 평균 미션 완료 시간: 추적 시작

---

## 13. 참고 자료

- [Orchestrate teams of Claude Code sessions - 공식 문서](https://code.claude.com/docs/en/agent-teams)
- [Create custom subagents - 공식 문서](https://code.claude.com/docs/en/sub-agents)
- [Building a C compiler with parallel Claudes - Anthropic](https://www.anthropic.com/engineering/building-c-compiler)
- [The Code Agent Orchestra - Addy Osmani](https://addyosmani.com/blog/code-agent-orchestra/)
- [From Tasks to Swarms - alexop.dev](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
- [30 Tips for Claude Code Agent Teams - John Kim](https://getpushtoprod.substack.com/p/30-tips-for-claude-code-agent-teams)
- [Agent Teams Controls - claudefa.st](https://claudefa.st/blog/guide/agents/agent-teams-controls)
- [VoltAgent/awesome-claude-code-subagents - GitHub](https://github.com/VoltAgent/awesome-claude-code-subagents)
