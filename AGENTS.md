# KAS Agent Teams v3 — 운영 가이드

> Claude Code Agent Teams 설정 파일. CLAUDE.md와 함께 모든 팀원이 자동으로 로드한다.

---

## 3-Layer Command Structure

```
Lead (사용자) — 최종 머지 승인만 담당
  │
  ├── LAYER 1: COMMAND
  │   └── mission-controller (Opus) — 자율 이슈 감지 & 팀 편성
  │
  ├── LAYER 2: STANDING (상시 운영팀)
  │   ├── [빌더]   backend-dev (Sonnet) · frontend-dev (Sonnet)
  │   ├── [가디언] test-engineer (Sonnet) · security-sentinel (Opus) · quality-reviewer (Opus)
  │   └── [운영]   infra-ops (Sonnet) · devops-automation (Sonnet)
  │
  └── LAYER 3: SPECIALISTS (소환 시에만 활성)
      performance-profiler · a11y-expert · docs-architect · db-architect
      refactoring-surgeon · pipeline-debugger · video-qa-specialist · trend-analyst
      api-designer · release-manager · e2e-playwright · cost-optimizer-agent
```

---

## 파일 소유권

| 디렉토리/파일 | 소유자 | 비고 |
|--------------|--------|------|
| `src/` | backend-dev | frontend-dev 진입 금지 |
| `web/` | frontend-dev | backend-dev 진입 금지 |
| `tests/` | test-engineer | backend-dev/frontend-dev 기여 가능 (리뷰 필수) |
| `scripts/` | infra-ops | |
| `.github/workflows/` | infra-ops + devops-automation | 공동 (infra-ops: 인프라 변경, devops-automation: CI/CD 도구) |
| `docs/` | docs-architect | 누구나 기여 가능 |
| `.claude/settings.local.json` | devops-automation | |
| `ruff.toml`, `.prettierrc` | devops-automation | |
| `scripts/supabase_schema.sql` | db-architect | |

---

## 미션 프리셋 (12가지)

### 1. 풀스택 Feature 개발
```
kas-feature 팀:
- backend-dev: API/백엔드 로직
- frontend-dev: 웹 페이지/컴포넌트
- test-engineer: 테스트 작성 (TDD)
- quality-reviewer: plan 모드 리뷰
plan approval 요구, 완료 후 security-sentinel 자동 스캔
```

### 2. 3차원 코드 리뷰
```
kas-review 팀:
- security-sentinel: 보안/OWASP
- quality-reviewer: 코드품질/아키텍처
- performance-profiler: 성능 병목
각자 독립 리뷰 후 mission-controller에게 통합 보고
```

### 3. 경쟁 가설 디버깅
```
kas-debug 팀 (pipeline-debugger 타입 3명):
- debugger-1: 쿼터/네트워크 가설
- debugger-2: 코드 로직 가설
- debugger-3: 환경/설정 가설
서로 이론 반박, findings.md에 합의 결과 기록
```

### 4. 파이프라인 안정화
```
kas-stability 팀:
- backend-dev: Step05~12 fallback 강화
- test-engineer: 누락 테스트 추가
- infra-ops: 쿼터/환경 검증
plan approval 요구
```

### 5. 대시보드 리디자인
```
kas-ui 팀:
- frontend-dev: 구현 + Playwright 시각 검증
- a11y-expert: 접근성 속성 보강
- e2e-playwright: E2E 회귀 테스트
```

### 6. 런타임 에이전트 확장
```
kas-agents 팀:
- backend-dev: 에이전트 설계/구현 (비침습적 원칙 준수)
- test-engineer: 에이전트 테스트 작성
- quality-reviewer: 설계 리뷰
plan approval 요구
```

### 7. 보안 강화
```
kas-security 팀:
- security-sentinel: 전체 보안 감사
- backend-dev: 백엔드 취약점 수정
- frontend-dev: API 라우트 인증 강화
- infra-ops: 환경변수 보안 점검
```

### 8. 테스트 커버리지 블리츠
```
kas-coverage 팀:
- test-engineer: 핵심 모듈 테스트 (ssot, config, manifest 우선)
- backend-dev: Python 테스트 기여
- frontend-dev: 웹 테스트 기여
- e2e-playwright: E2E 시나리오 추가
목표: Python 90%, 웹 80%
```

### 9. 리팩토링 스프린트
```
kas-refactor 팀:
- refactoring-surgeon: God Module 분해
- test-engineer: 리팩토링 전/후 테스트 보호
- quality-reviewer: 아키텍처 검증
```

### 10. API 계약 변경
```
kas-api 팀:
- api-designer: 설계 문서 작성
- backend-dev: 서버 구현
- frontend-dev: 클라이언트 구현
- docs-architect: API 문서 업데이트
backend-dev가 변경 전 frontend-dev에게 사전 메시지 필수
```

### 11. 릴리스 준비
```
kas-release 팀:
- release-manager: CHANGELOG, 버전 태그, PR
- test-engineer: 릴리스 전 전체 테스트
- security-sentinel: 릴리스 전 보안 스캔
- docs-architect: 문서 현행화
```

### 12. 성능 최적화
```
kas-perf 팀:
- performance-profiler: 병목 분석
- backend-dev 또는 frontend-dev: 수정 구현
- test-engineer: 성능 테스트 추가
```

---

## 통신 프로토콜

### mission-controller → 팀원 소환
```
[미션 ID: 2026-04-11-security]
목표: API 라우트 인증 미들웨어 추가
범위: web/proxy.ts, web/app/api/ 라우트들
제약조건: middleware.ts 생성 금지(proxy.ts만 사용), 기존 DRY RUN 동작 유지
완료 기준: 모든 API 라우트 인증 통과, pytest/build 성공
우선순위: 높음
```

### API 계약 변경 시 (backend-dev → frontend-dev)
```
"API /api/pipeline/trigger 응답 포맷 변경:
변경 전: { status: string }
변경 후: { status: string, run_id: string, dry_run: boolean }
frontend-dev 대응 수정 필요합니다."
```

### 이슈 발견 시 (가디언 → mission-controller + 빌더)
```
"[보안 이슈] web/app/api/agents/run/route.ts:45
spawn 인자에 channel_id가 미검증 상태로 전달됨.
validateChannelPath() 적용 필요. 담당: frontend-dev"
```

### 인프라 변경 시 (infra-ops → mission-controller)
```
"[인프라 변경] .github/workflows/ci.yml에 ruff 린팅 단계 추가.
다음 PR부터 ruff check src/ 통과 필요."
```

---

## 멀티모델 전략

| 모델 | 에이전트 | 언제 사용 |
|------|---------|----------|
| **Opus** | mission-controller, security-sentinel, quality-reviewer | 판단/리뷰/감사 (정확도 최우선) |
| **Sonnet** | backend-dev, frontend-dev, test-engineer, infra-ops, devops-automation + 8 specialists | 구현/분석 (비용-성능 균형) |
| **Haiku** | docs-architect, trend-analyst, release-manager, cost-optimizer-agent | 단순 집계/문서 (비용 절감) |

**동시 Opus 제한**: 같은 미션에 Opus 에이전트 4명 이상 소환 금지.

---

## Anti-Patterns (금지)

- ❌ mission-controller 우회하여 직접 대규모 팀 편성 (소환 메시지 형식 필수)
- ❌ 파일 소유권 교차 수정 (src/ ↔ web/ 경계 절대적)
- ❌ security-sentinel/quality-reviewer/performance-profiler가 코드 직접 수정 (빌더에게 위임)
- ❌ 같은 미션에 Opus 4명 이상 소환 (비용 폭주)
- ❌ tests/ 파일 test-engineer 리뷰 없이 병합
- ❌ 전문가 풀 에이전트가 소환 없이 상시 운영팀처럼 자주 활성화

---

## 자주 쓰는 커맨드

```bash
# 에이전트 목록 확인
claude agents

# 헬스체크
python scripts/preflight_check.py

# 전체 테스트
python -m pytest tests/ -q

# 린팅
ruff check src/
cd web && npm run lint
```
