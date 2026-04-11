# KAS Agent Teams 운영 가이드

> Claude Code Agent Teams 설정 파일. CLAUDE.md와 함께 모든 팀원이 자동으로 로드한다.

---

## 팀 구성 (코어 4명)

| 팀원 | 코드명 | 모델 | 소유 영역 | 색상 |
|------|--------|------|-----------|------|
| Backend Developer | `backend-dev` | Sonnet | `src/` 전체 | 🔴 red |
| Frontend Developer | `frontend-dev` | Sonnet | `web/` 전체 | 🔵 blue |
| Quality Reviewer | `quality-reviewer` | Sonnet | Read-only, `tests/` | 🟠 orange |
| Infra & Ops | `infra-ops` | Haiku | `scripts/`, 쿼터, 환경변수 | 🔷 cyan |

**핵심 원칙:**
- `src/`와 `web/`은 **절대 교차 수정 금지** — backend-dev는 web/ 금지, frontend-dev는 src/ 금지
- `quality-reviewer`는 **코드를 직접 수정하지 않음** — 발견 이슈는 해당 팀원에게 메시지
- API 계약 변경 시 **반드시 사전 메시지 교환**

---

## 미션별 소환 프리셋

### 1. 풀스택 Feature 개발
```
kas-feature 팀을 생성해줘.
- backend-dev: API/백엔드 로직 담당
- frontend-dev: 웹 페이지/컴포넌트 담당
- quality-reviewer: plan 모드로 리뷰만 담당
각 팀원에게 plan approval을 요구해줘.
작업: [여기에 구체적 요구사항 작성]
```

### 2. 코드베이스 종합 리뷰 (3각 리뷰)
```
kas-review 팀을 생성해줘. quality-reviewer 타입으로 3명 소환:
- security-reviewer: OWASP Top 10, 경로 트래버설, API 키 노출 집중
- performance-reviewer: N+1 쿼리, 불필요한 렌더링, 번들 크기 집중
- test-reviewer: 누락 테스트, conftest 패턴, edge case 집중
각자 독립적으로 리뷰 후 서로 발견사항을 공유하고 합의해줘.
```

### 3. 경쟁 가설 디버깅
```
kas-debug 팀을 생성해줘. Sonnet으로 3~5명 소환.
버그: [여기에 버그 설명]
각자 다른 가설을 검증하고 서로의 이론을 반박해줘.
합의한 근본 원인을 findings.md에 기록해줘.
```

### 4. 파이프라인 안정화
```
kas-stability 팀을 생성해줘.
- backend-dev: Step05~12 fallback 경로 점검 및 에러 처리 강화
- quality-reviewer: 테스트 커버리지 확인 및 누락 테스트 추가 요청
- infra-ops: 쿼터/환경 검증
각 팀원에게 plan approval을 요구해줘.
```

### 5. 대시보드 리디자인
```
kas-ui 팀을 생성해줘.
- frontend-dev: 디자인 + 구현 (Playwright MCP로 시각 검증)
- quality-reviewer: 접근성, 반응형, CLAUDE.md 규칙 준수 리뷰
```

### 6. 런타임 에이전트 확장
```
kas-agents 팀을 생성해줘.
- backend-dev: 에이전트 설계 및 구현 (비침습적 원칙 준수)
- quality-reviewer: 설계 리뷰 및 테스트 검증
각 팀원에게 plan approval을 요구해줘.
```

---

## 팀원 간 통신 프로토콜

### API 계약 변경 시
```
backend-dev → frontend-dev:
"API /api/pipeline/trigger의 응답 포맷이 변경됩니다.
변경 전: { status: string }
변경 후: { status: string, run_id: string, dry_run: boolean }
frontend-dev에서 대응 수정이 필요합니다."
```

### 이슈 발견 시 (quality-reviewer)
```
quality-reviewer → backend-dev:
"src/pipeline.py:390에서 time.sleep(2) 하드코딩 발견.
CLAUDE.md 규칙에 따르면 설정 파일로 분리해야 합니다.
수정을 요청합니다."
```

### 인프라 변경 시 (infra-ops)
```
infra-ops → [broadcast]:
"scripts/preflight_check.py에 Supabase 연결 테스트가 추가되었습니다.
다음 실행 전 `python scripts/preflight_check.py`로 검증하세요."
```

---

## 작업 크기 가이드라인

| 크기 | 설명 | 팀원당 작업 수 |
|------|------|---------------|
| Small | 단일 파일, 1~2개 함수 | 1~2개 |
| Medium | 여러 파일, 1개 기능 | 3~5개 |
| Large | 서브시스템 전체 | 별도 팀 소환 |

**권장**: 팀원당 5~6개 작업. 너무 많으면 분할, 너무 적으면 비효율.

---

## 자주 쓰는 커맨드

```bash
# Agent Teams 활성화 확인
claude --version  # v2.1.32 이상 필요

# 팀원 목록 확인
claude agents

# 프로젝트 상태 확인
python scripts/preflight_check.py

# 전체 테스트
python -m pytest tests/ -q
```

---

## Anti-Patterns (금지)

- ❌ 7명 이상 팀 구성 (조정 비용 > 생산성)
- ❌ 팀원이 다른 팀원의 소유 파일 수정
- ❌ quality-reviewer가 코드 직접 수정
- ❌ broadcast 남용 (개별 메시지 우선)
- ❌ 팀원 없이 Lead 혼자 전체 구현 (위임 없는 팀)
- ❌ 장시간 무감독 실행 (정기적 방향 확인 필요)
