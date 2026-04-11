# KAS Agent Teams v3.1 — UX/UI 전문가 추가 설계 스펙

**날짜**: 2026-04-11  
**버전**: v3.1 (v3: 5+2=7명 → v3.1: 5+4=9명)  
**목표**: 완전 자동화 가능한 최고 수준의 Agent Team에 UI 디자인 + UX 리뷰 전문가 추가

---

## 1. 배경 및 동기

v3(5+2=7명)에서 frontend-dev가 디자인 시스템 정의, 컴포넌트 구현, 반응형 대응, Playwright 시각 검증까지 UI/UX 전반을 단독 담당했다. 이로 인해:

- **디자인 시스템 드리프트**: 빠른 기능 구현 시 CSS 변수 미사용, CARD_BASE 패턴 위반 발생
- **접근성 사각지대**: WCAG 2.1 준수 여부를 체계적으로 검증하는 에이전트 없음
- **UX 품질 불일치**: 사용자 흐름, 인터랙션 패턴, 모바일 사용성이 개발자 관점으로만 평가

v3.1은 이 세 가지 문제를 해결하기 위해 두 명의 UX/UI 전문 에이전트를 미션별 소환팀에 추가한다.

---

## 2. 팀 구성 변경

### v3 → v3.1 비교

| 구분 | v3 | v3.1 |
|------|-----|------|
| 상시 코어팀 | 5명 | 5명 (변화 없음) |
| 미션별 확장팀 | 2명 | **4명** (+2) |
| 총 상한 | 7명 | **9명** |
| 평시 비용 | ~125% | ~125% (**변화 없음**) |

### v3.1 전체 팀 구성

**상시 코어팀 (5명) — 변화 없음**

| 코드명 | 모델 | maxTurns | 소유 영역 | 색상 |
|--------|------|----------|-----------|------|
| backend-dev | Sonnet | 40 | `src/` 전체 | 🔴 red |
| frontend-dev | Sonnet | 40 | `web/app/`, `web/lib/`, `web/hooks/`, `web/components/`(로직) | 🔵 blue |
| test-engineer | Sonnet | 35 | `tests/` 전체 (conftest 단독) | 🟢 green |
| quality-reviewer | Sonnet | 25 | Read-only, 코드품질+아키텍처+성능 | 🟠 orange |
| infra-ops | Haiku | 20 | `scripts/`, `.github/`, 쿼터 | 🔷 cyan |

**미션별 확장팀 (4명) — 2명 추가**

| 코드명 | 모델 | maxTurns | 소환 시점 | 색상 |
|--------|------|----------|-----------|------|
| security-auditor | Sonnet | 25 | 보안 감사, PR 전 검증 | 🟣 purple |
| doc-keeper | Haiku | 15 | 문서 드리프트 감지 | 🟡 yellow |
| **ui-designer** | **Sonnet** | **30** | **UI 리디자인, 디자인 시스템 업데이트, Figma 연동** | **🩷 pink** |
| **ux-reviewer** | **Sonnet** | **20** | **UX 감사, 접근성 검증, 사용자 흐름 리뷰** | **🩵 teal** |

---

## 3. 신규 에이전트 상세 스펙

### 3.1 ui-designer

**파일**: `.claude/agents/ui-designer.md`

```yaml
name: ui-designer
model: sonnet
permissionMode: acceptEdits
maxTurns: 30
color: pink
mcpServers: [playwright, figma]
```

**파일 소유권:**
- 소유: `web/app/globals.css`, `web/public/`
- 공유(스타일링 담당): `web/components/`
- 금지: `src/`, `tests/`, `web/app/api/`, `web/lib/`

**핵심 책임:**

| 책임 | 상세 |
|------|------|
| 디자인 시스템 수호 | Red Light Glassmorphism CSS 변수 관리, CARD_BASE 패턴 유지 |
| 컴포넌트 스타일링 | className, style, Tailwind 클래스 관리 |
| Figma 연동 | `get_design_context` → CSS 변수 매핑 → 컴포넌트 코드 생성 |
| 시각 검증 | Playwright로 라이트/다크/모바일 3종 스크린샷 |

**web/components/ 소유권 분할:**
- ui-designer 담당: className, style, Tailwind, 애니메이션, CSS 변수
- frontend-dev 담당: onClick, onChange, useState, useEffect, API 호출, JSX 구조

### 3.2 ux-reviewer

**파일**: `.claude/agents/ux-reviewer.md`

```yaml
name: ux-reviewer
model: sonnet
permissionMode: plan
disallowedTools: Write, Edit
maxTurns: 20
color: teal
mcpServers: [playwright]
```

**역할 (Read-only):**

| 검사 영역 | 상세 |
|----------|------|
| WCAG 2.1 접근성 | aria 레이블, 키보드 내비게이션, 색상 대비(4.5:1), 이미지 alt |
| 사용자 흐름 | 주요 경로 3클릭 이내, 에러/로딩/빈 상태 UX |
| 인터랙션 패턴 | 버튼 hover/focus/active 상태, 피드백 200ms 이내 |
| 모바일 사용성 | 터치 타겟 44px+, 스크롤 동작, 텍스트 16px+ |
| 디자인 일관성 | CARD_BASE 준수, CSS 변수 사용, 하드코딩 rgba 탐지 |

**이슈 전달**: 발견 이슈는 SendMessage로 frontend-dev 또는 ui-designer에게 전달. 직접 수정 불가.

---

## 4. 파일 소유권 매트릭스 (v3.1)

| 파일/디렉토리 | backend-dev | frontend-dev | ui-designer | ux-reviewer | test-engineer | infra-ops |
|---|---|---|---|---|---|---|
| `src/` | ✅ 소유 | ❌ | ❌ | ❌ | 기여 | ❌ |
| `web/app/` | ❌ | ✅ 소유 | ❌ | 👁️ 리뷰 | ❌ | ❌ |
| `web/components/` | ❌ | ✅ 로직 | ✅ 스타일 | 👁️ 리뷰 | ❌ | ❌ |
| `web/app/globals.css` | ❌ | ❌ | ✅ 소유 | 👁️ 리뷰 | ❌ | ❌ |
| `web/public/` | ❌ | ❌ | ✅ 소유 | ❌ | ❌ | ❌ |
| `web/lib/`, `web/hooks/` | ❌ | ✅ 소유 | ❌ | ❌ | ❌ | ❌ |
| `tests/` | 기여 | 기여 | ❌ | ❌ | ✅ 소유 | ❌ |
| `scripts/` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ 소유 |

---

## 5. 신규 미션 프리셋

### 미션 #10: UI 리디자인 강화 (kas-ui-pro)

```
kas-ui-pro 팀을 생성해줘.
- ui-designer: 디자인 시스템 관리 + Figma→코드 변환 + 컴포넌트 스타일링
- frontend-dev: 컴포넌트 로직 + 상태 관리 + API 연동
- ux-reviewer: 접근성(WCAG) + 사용자 흐름 + 인터랙션 패턴 리뷰 (plan 모드)
- quality-reviewer: 코드 품질 + 아키텍처 검증 (plan 모드)
ui-designer와 frontend-dev에게 plan approval을 요구해줘.
작업: [리디자인 요구사항]
```

### 미션 #11: UX 감사 (kas-ux-audit)

```
kas-ux-audit 팀을 생성해줘.
- ux-reviewer: WCAG 2.1 접근성 감사 + 사용자 흐름 + 모바일 사용성 (plan 모드)
- ui-designer: ux-reviewer 발견 스타일/일관성 이슈 즉시 수정
- frontend-dev: ux-reviewer 발견 로직/흐름 이슈 즉시 수정
ux-reviewer는 Read-only, 이슈는 SendMessage로 전달.
작업: [감사 범위]
```

---

## 6. 통신 프로토콜 추가 (3종)

### 스타일 변경 알림 (ui-designer → frontend-dev)
```
ui-designer → frontend-dev:
"web/components/kpi-banner.tsx의 className 변경 예정.
카드 레이아웃 grid → flex 전환. 로직 측 영향 없음."
```

### 디자인 토큰 변경 알림 (ui-designer → broadcast)
```
ui-designer → [broadcast]:
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

## 7. 토큰 효율 분석

### 비용 비교

| 운영 모드 | 활성 에이전트 | 상대 비용 |
|----------|-------------|----------|
| 평시 (5명만) | backend, frontend, test, quality, infra | ~125% |
| 보안 감사 (+1) | + security-auditor | ~150% |
| 문서 동기화 (+1) | + doc-keeper | ~130% |
| **UI 리디자인 (+2)** | **+ ui-designer + ux-reviewer** | **~170%** |
| 풀 스펙트럼 (+4) | 전원 소환 | ~200% |

### 최적화 근거

- **Sonnet 선택 이유**: ui-designer는 디자인 판단(Figma 해석, CSS 변수 매핑, 시각 일관성), ux-reviewer는 WCAG/접근성 추론이 필요 → Haiku 부적합
- **maxTurns 차등화**: ui-designer 30턴(코드 수정 포함) vs ux-reviewer 20턴(Read-only) → 낭비 최소화
- **미션별 소환**: 평시 비용 변화 없음. 전체 9명 동시 활성화는 극히 드물게 발생

---

## 8. Anti-Patterns (업데이트)

기존 v3 Anti-Patterns에 추가:
- ❌ `ui-designer`가 `web/components/`에서 이벤트 핸들러/상태 로직 수정 (frontend-dev 영역)
- ❌ `frontend-dev`가 `globals.css` 직접 수정 (ui-designer 소유)
- ❌ `ux-reviewer`가 코드 직접 수정 (Read-only 전용 — 이슈는 SendMessage로 전달)
- ❌ UI 리디자인 시 ui-designer와 frontend-dev가 web/components/ 동일 파일을 동시 수정 (SendMessage 조율 필수)

---

## 9. 수정된 파일 목록

| 파일 | 변경 유형 |
|------|----------|
| `.claude/agents/ui-designer.md` | 신규 생성 |
| `.claude/agents/ux-reviewer.md` | 신규 생성 |
| `.claude/agents/frontend-dev.md` | 소유권 재분배 + 공유 규칙 추가 |
| `AGENTS.md` | 파일 소유권 표, 미션 프리셋 2개, 통신 프로토콜 3개, Anti-Pattern 업데이트 |
| `CLAUDE.md` | Agent Teams 섹션 9명 반영 |
| `docs/agent-teams-visual.html` | v3.1 업데이트, 카드 2개 추가, 미션 11종 |

---

## 10. 검증

```bash
# 에이전트 파일 9개 확인
ls .claude/agents/{backend-dev,frontend-dev,test-engineer,quality-reviewer,\
infra-ops,security-auditor,doc-keeper,ui-designer,ux-reviewer}.md

# 9명 상한 일관성
grep -n "9명\|미션별 4명" AGENTS.md CLAUDE.md

# globals.css 소유자 일관성
grep -rn "globals.css" .claude/agents/ | grep -v "ui-designer"  # 비어야 함

# ux-reviewer Read-only 확인
grep "disallowedTools" .claude/agents/ux-reviewer.md

# 기존 테스트 통과
python -m pytest tests/ -x -q
cd web && npm run build
```
