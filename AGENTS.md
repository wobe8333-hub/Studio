# KAS Agent Teams v3.1 — 운영 가이드

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
      ui-designer · ux-reviewer · doc-keeper · security-auditor
```

---

## 파일 소유권

| 디렉토리/파일 | 소유자 | 비고 |
|--------------|--------|------|
| `src/` | backend-dev | frontend-dev 진입 금지 |
| `web/app/` | frontend-dev | backend-dev 진입 금지 |
| `web/components/` | frontend-dev(로직) + ui-designer(스타일) | 공유 — 동시 수정 시 SendMessage 조율 필수 |
| `web/app/globals.css` | ui-designer | frontend-dev 직접 수정 금지 |
| `web/public/` | ui-designer | |
| `web/lib/`, `web/hooks/` | frontend-dev | |
| `tests/` | test-engineer | backend-dev/frontend-dev 기여 가능 (리뷰 필수) |
| `scripts/` | infra-ops | |
| `.github/workflows/` | infra-ops + devops-automation | 공동 (infra-ops: 인프라 변경, devops-automation: CI/CD 도구) |
| `docs/` | docs-architect | 누구나 기여 가능 |
| `.claude/settings.local.json` | devops-automation | |
| `ruff.toml`, `.prettierrc` | devops-automation | |
| `scripts/supabase_schema.sql` | db-architect | |
| `CLAUDE.md`, `AGENTS.md`, `README.md` | doc-keeper | 소스코드 수정 금지 |

---

## web/components/ 공유 규칙

| 수정 유형 | 담당 |
|-----------|------|
| onClick, onChange 핸들러 | **frontend-dev** |
| useState, useEffect | **frontend-dev** |
| API 호출, 데이터 바인딩 | **frontend-dev** |
| JSX 구조 변경 (새 요소 추가) | **frontend-dev** |
| 조건부 렌더링 | **frontend-dev** |
| className, style 속성 | **ui-designer** |
| Tailwind 클래스, 애니메이션 | **ui-designer** |
| CSS 변수 참조 변경 | **ui-designer** |

**동일 파일 동시 수정 시**: SendMessage로 작업 범위 합의 후 순차 작업.
**globals.css 변경 필요 시**: ui-designer에게 SendMessage로 요청. frontend-dev 직접 수정 금지.

---

## 미션 프리셋 (14가지)

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

### 5-A. UI 리디자인 강화 (v3.1 신규)
```
kas-ui-pro 팀:
- ui-designer: 디자인 시스템 관리 + Figma→코드 변환 + 컴포넌트 스타일링
- frontend-dev: 컴포넌트 로직 + 상태 관리 + API 연동
- ux-reviewer: 접근성(WCAG) + 사용자 흐름 + 인터랙션 패턴 리뷰 (plan 모드)
- quality-reviewer: 코드 품질 + 아키텍처 검증 (plan 모드)
ui-designer와 frontend-dev에게 plan approval 요구
작업: [리디자인 요구사항]
```

### 5-B. UX 감사 (v3.1 신규)
```
kas-ux-audit 팀:
- ux-reviewer: WCAG 2.1 접근성 감사 + 사용자 흐름 + 모바일 사용성 (plan 모드, Read-only)
- ui-designer: ux-reviewer 발견 스타일/일관성 이슈 즉시 수정
- frontend-dev: ux-reviewer 발견 로직/흐름 이슈 즉시 수정
ux-reviewer는 이슈를 SendMessage로 전달. 직접 수정 불가.
작업: [감사 범위]
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

### 스타일 변경 알림 (ui-designer → frontend-dev)
```
"web/components/kpi-banner.tsx의 className 변경 예정.
카드 레이아웃 grid → flex 전환. 로직 측 영향 없음."
```

### 디자인 토큰 변경 알림 (ui-designer → broadcast)
```
"globals.css의 --card 변수 값 변경.
변경 전: rgba(255,255,255,0.60)
변경 후: rgba(255,255,255,0.65)
모든 카드 컴포넌트에 시각적 영향 있을 수 있음."
```

### UX 이슈 전달 (ux-reviewer → frontend-dev / ui-designer)
```
ux-reviewer → frontend-dev:
"home-ops-tab.tsx에서 파이프라인 실행 완료 후 피드백 없음.
토스트 알림 또는 상태 변경 UI 추가 요청."

ux-reviewer → ui-designer:
"sidebar-nav.tsx 활성 메뉴 색상 대비 WCAG 4.5:1 미달.
색상 강화 요청."
```

---

## 멀티모델 전략

| 모델 | 에이전트 | 언제 사용 |
|------|---------|----------|
| **Opus** | mission-controller, security-sentinel, quality-reviewer | 판단/리뷰/감사 (정확도 최우선) |
| **Sonnet** | backend-dev, frontend-dev, test-engineer, infra-ops, devops-automation, ui-designer, ux-reviewer, security-auditor + 7 specialists | 구현/분석/디자인 (비용-성능 균형) |
| **Haiku** | docs-architect, trend-analyst, release-manager, cost-optimizer-agent, doc-keeper | 단순 집계/문서 (비용 절감) |

**동시 Opus 제한**: 같은 미션에 Opus 에이전트 4명 이상 소환 금지.

---

## Anti-Patterns (금지)

- ❌ mission-controller 우회하여 직접 대규모 팀 편성 (소환 메시지 형식 필수)
- ❌ 파일 소유권 교차 수정 (src/ ↔ web/ 경계 절대적)
- ❌ security-sentinel/quality-reviewer/performance-profiler가 코드 직접 수정 (빌더에게 위임)
- ❌ 같은 미션에 Opus 4명 이상 소환 (비용 폭주)
- ❌ tests/ 파일 test-engineer 리뷰 없이 병합
- ❌ 전문가 풀 에이전트가 소환 없이 상시 운영팀처럼 자주 활성화
- ❌ ui-designer가 web/components/에서 이벤트 핸들러/상태 로직 수정 (frontend-dev 영역)
- ❌ frontend-dev가 globals.css 직접 수정 (ui-designer 소유)
- ❌ ux-reviewer/security-auditor가 코드 직접 수정 (Read-only 전용 — 이슈는 SendMessage로 전달)
- ❌ UI 리디자인 시 ui-designer와 frontend-dev가 web/components/ 동일 파일 동시 수정 (SendMessage 조율 필수)
- ❌ Layer 3 스페셜리스트 6명 초과 동시 소환 (비용 폭주 — 미션당 최대 5명 권장)
- ❌ doc-keeper가 src/, web/, tests/ 소스코드 직접 수정 (문서 파일만 허용)

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
