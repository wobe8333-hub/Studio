# Loomix Owner Command Center — 설계 문서

> **작성일:** 2026-04-13  
> **파일 대상:** `docs/loomix-owner.html`  
> **목적:** 오너 전용 스탠드얼론 HTML 커맨드센터 (서버 불필요)

---

## 1. 개요

Loomix 오너가 회사를 운영하는 전용 홈페이지. AI ceo 에이전트가 일상 운영을 담당하고, 오너는 HITL 승인·파이프라인 실행·명령 전달만 하면 된다. `docs/loomix-agents.html`과 동일하게 서버 없이 브라우저에서 바로 열 수 있는 단독 HTML 파일로 제작한다.

**사용자:** Loomix 오너 (1인). AI CEO가 아닌 회사 소유자.  
**주 사용 시나리오:**
1. HITL 신호 확인 → 승인/거부
2. 파이프라인 수동 실행 또는 중지
3. AI CEO에게 자연어 명령 전달
4. 수익·채널·에이전트 현황 빠른 확인

---

## 2. 비주얼 스타일

### 아이스 화이트 × 글래스모피즘

| 속성 | 값 |
|------|-----|
| 배경 | `linear-gradient(140deg, #dbeafe, #bfdbfe, #e0f2fe, #cffafe)` |
| 배경 장식 | 블러 원 2개 (rgba 파랑·인디고, filter: blur 40px) |
| 카드 기본 | `background: rgba(255,255,255,0.58)`, `backdrop-filter: blur(14px)` |
| 카드 테두리 | `1px solid rgba(255,255,255,0.88)` |
| 카드 라운드 | `18px` |
| 메인 컨테이너 | `border-radius: 24px`, max-width 480px, 중앙 정렬 |
| 강조색 | `#0284c7` (sky-600), `#38bdf8` (sky-400) |
| 경고색 | `#ea580c` (orange-600), `rgba(255,237,213,0.75)` |
| 폰트 | `'Inter', system-ui, sans-serif` |
| 그림자 | `0 4px 20px rgba(2,132,199,0.12)` |

---

## 3. 레이아웃 — 위젯 보드 그리드

```
┌─────────────────────────────────────┐
│  안녕하세요, 오너님 👋               │  ← 인사 헤더 + 연결 상태 뱃지
│  오늘도 37명이 일하고 있습니다        │
├─────────────────────────────────────┤
│  ▶ 파이프라인 [대기중 — 준비 완료]  ○ │  ← 전체 너비, 글래스 카드
├──────────────────┬──────────────────┤
│  💰 수익          │  ⚠️ HITL 승인    │
│  ₩0              │  2건             │
│  ▓░░░░ 0%        │  즉시 확인 →     │
├──────────────────┼──────────────────┤
│  📺 채널          │  🤖 에이전트     │
│  2/7             │  37              │
├─────────────────────────────────────┤
│  ⌘ AI CEO에게 명령하기...    [전송] │  ← 전체 너비
└─────────────────────────────────────┘
```

---

## 4. 위젯별 기능 상세

### 4-1. 파이프라인 위젯

- **기본 상태:** "대기 중 — 실행 준비 완료" 표시, `▶` 원형 버튼
- **실행 전 플로우:**
  1. `▶` 클릭 → 채널 선택 팝업 (CH1~CH7 체크박스, 월 선택)
  2. 확인 클릭 → 하이브리드 실행 (아래 §6 참조)
- **실행 중:** 상태 텍스트 → "실행 중 — CH1 Step 05 처리중", 스피너
- **추가 버튼:** DRY RUN, 중지 (작은 보조 버튼)

### 4-2. HITL 위젯

- **기본:** 승인 대기 건수 크게 표시
- **클릭 시:** 위젯 확장 → 개별 항목 목록
  - 각 항목: 제목 + 짧은 설명 + [승인] [거부] 버튼
- **데이터 소스:** `data/global/notifications/hitl_signals.json`
- **0건:** "✓ 승인 대기 없음" 초록색 표시

### 4-3. 수익 위젯

- 이번 달 수익 금액 (₩)
- 목표 달성률 프로그레스 바
- **데이터 소스:** `data/global/monthly_plan/{YYYY-MM}/portfolio_plan.json`

### 4-4. 채널 위젯

- 활성 채널 / 전체 채널 (2/7)
- **데이터 소스:** `src/step00/channel_registry.py` 반영 JSON 또는 config

### 4-5. 에이전트 위젯

- 에이전트 총 수 (37 고정 표시)
- `docs/loomix-agents.html` 링크 버튼

### 4-6. AI CEO 명령창

- 플레이스홀더: "⌘ AI CEO에게 명령하기..."
- Enter / [전송] 클릭 시 하이브리드 전송
- 최근 명령 3개 히스토리 (localStorage)

---

## 5. 데이터 로딩

파일이 `file://` 프로토콜로 열릴 경우 fetch가 차단되므로:

1. **`file://` 감지:** `window.location.protocol === 'file:'`이면 정적 플레이스홀더 데이터 사용
2. **localhost 서버 감지:** `http://localhost:8000/health` 또는 `http://localhost:7002/api/health` 호출
3. **성공 시:** 실시간 JSON 데이터 로드
4. **실패 시:** `data/` 경로 직접 fetch 시도 (Next.js dev server가 정적 파일 서빙)

### 로드 대상 JSON
| 파일 | 용도 |
|------|------|
| `data/global/notifications/hitl_signals.json` | HITL 목록 |
| `data/global/step_progress.json` | 파이프라인 상태 |
| `data/global/monthly_plan/{YYYY-MM}/portfolio_plan.json` | 수익 목표·달성 (JS로 현재 월 동적 계산) |

---

## 6. 하이브리드 인터랙션

서버 주소: `http://localhost:7002` (Next.js 대시보드)

```
페이지 로드
  └→ checkServerConnection()
       GET http://localhost:7002/api/pipeline/status
       ├─ 성공 → serverMode = true, 상단 뱃지 "● LIVE", KPI 데이터 로드
       └─ 실패 → serverMode = false, 상단 뱃지 "○ 오프라인"

버튼 클릭 (파이프라인 실행)
  ├─ serverMode = true  → POST /api/pipeline/trigger
  │                        body: { month_number, channel_id, dry_run: false }
  └─ serverMode = false → navigator.clipboard.write("python -m src.pipeline {month}")
                          → 토스트: "📋 명령어 복사됨!"

HITL 승인 (resolve)
  ├─ serverMode = true  → PATCH /api/hitl-signals  body: { id }
  └─ serverMode = false → clipboard.write("data/global/notifications/hitl_signals.json 수동 처리")
                          → 파일 경로 표시

AI CEO 명령 (API 없음 → 항상 클립보드)
  └─ clipboard.write(message) → 토스트: "📋 명령어 복사됨! 터미널에 붙여넣기"
```

---

## 7. 구현 범위

### 포함
- 완전한 글래스모피즘 UI (CSS only, 외부 의존성 없음)
- 위젯 6개 (파이프라인, 수익, HITL, 채널, 에이전트, 명령창)
- 하이브리드 인터랙션 (서버 감지 + API / 클립보드 폴백)
- HITL 목록 펼침/승인/거부 UI
- 파이프라인 채널 선택 팝업
- 연결 상태 실시간 표시
- localStorage 기반 명령 히스토리
- 모바일 반응형 (max-width: 480px 중심)

### 제외
- 다크 모드 (아이스 화이트 단일 테마)
- 채널별 상세 통계 (별도 페이지)
- 실시간 웹소켓 (폴링 없음, 새로고침으로 갱신)
- 인증/로그인 (로컬 전용)

---

## 8. 파일 구조

```
docs/
  loomix-owner.html    ← 단독 파일 (모든 CSS·JS 인라인)
```

`loomix-agents.html`과 동일한 패턴으로 외부 파일 없이 완전 독립.

---

## 9. API 엔드포인트 (localhost:7002 — 실존 라우트)

| 메서드 | 경로 | 용도 | 상태 |
|--------|------|------|------|
| GET | `/api/pipeline/status` | 파이프라인 현황 + 헬스체크 대용 | ✅ 존재 |
| POST | `/api/pipeline/trigger` | 파이프라인 실행 `{month_number, channel_id, dry_run}` | ✅ 존재 |
| GET | `/api/hitl-signals` | 미해결 HITL 신호 목록 | ✅ 존재 |
| PATCH | `/api/hitl-signals` | HITL 신호 resolve `{id}` | ✅ 존재 |
| GET | `/api/agents/status` | 에이전트 상태 (선택적) | ✅ 존재 |
| POST | `/api/command` | AI CEO 명령 전달 | ❌ 없음 → 클립보드 폴백 |
