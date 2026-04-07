# KAS 대시보드 경영·운영 듀얼 뷰 재구성 설계 문서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 홈(`/`) 페이지를 KPI 배너 고정 + 경영/운영 탭 전환 구조로 재구성하고, Glassmorphism Pink 디자인 시스템을 전체 대시보드에 적용한다.

**Architecture:** `page.tsx`(서버 컴포넌트)에 KPI 배너와 탭 컨테이너를 추가하고, 경영 탭과 운영 탭 각각을 `'use client'` 컴포넌트로 분리한다. 사이드바는 접이식으로 교체한다.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 · Lucide React · Noto Sans KR · Glassmorphism (backdrop-filter)

---

## 1. 디자인 시스템

### 색상 팔레트
```css
--p1: #FFC7C7;   /* 살구핑크 — 프로그레스 바, 강조 */
--p2: #FFE2E2;   /* 연핑크 — KPI 배너 배경 */
--p3: #F6F6F6;   /* 라이트그레이 — 페이지 배경 */
--p4: #8785A2;   /* 뮤트 퍼플 — 탑바, 사이드바 활성, 버튼 */
--t1: #2d2b3d;   /* 진한 텍스트 */
--t2: #5c5a74;   /* 서브 텍스트 */
--t3: #9896b0;   /* 뮤트 텍스트 */
```

기존 `globals.css`의 Red Light 팔레트(`--c-dark`, `--c-red` 등)를 위 팔레트로 교체한다.

### 폰트
- Noto Sans KR (400/500/600/700/800) — Google Fonts
- `layout.tsx`에서 Libre Baskerville, M PLUS Rounded 1c 를 Noto Sans KR 로 교체

### Glassmorphism 표준 토큰
```tsx
// 카드
background: 'rgba(255,255,255,0.55)'
backdropFilter: 'blur(20px)'
border: '1px solid rgba(255,199,199,0.3)'
borderRadius: '0.75rem'
boxShadow: '0 4px 16px rgba(135,133,162,0.08)'

// KPI 배너
background: 'rgba(255,226,226,0.62)'
backdropFilter: 'blur(16px)'

// 탑바
background: 'rgba(135,133,162,0.82)'
backdropFilter: 'blur(20px)'
```

### 아이콘
Lucide React (`lucide-react` 패키지, 이미 설치됨) 선형 아이콘 사용.

| 메뉴 | 아이콘 |
|---|---|
| 홈/KPI | `LayoutDashboard` |
| 수익 | `TrendingUp` |
| 트렌드 | `BarChart2` |
| QA | `CheckSquare` |
| 런 목록 | `List` |
| 모니터 | `Monitor` |
| 채널 | `Tv` |
| 알림 | `Bell` |
| 설정 | `Settings` |
| 사이드바 토글 | `ChevronsRight` |

---

## 2. 페이지 구조

```
홈 (/)
├── [Topbar] 탑바 — 로고 + 아이콘 네비 (hover 시 한글 라벨 슬라이드)
├── [KPI Banner] 항상 고정
│     ₩0 이번달 수익 | 0% 달성률 | 2/7 활성 채널 | 18 총 Runs | 0건 HITL
├── [Tab Bar] 📊 경영 | 🔧 운영  (아이콘만, hover 시 한글)
└── [Body]
    ├── [Sidebar] 접이식 — 아이콘 전용 → 토글 시 아이콘+라벨
    └── [Main]
        ├── 경영 탭
        │   ├── KPI 카드 4개 (수익/달성률/총Runs/활성채널)
        │   ├── 채널별 목표 진행 바 + 6개월 추이 차트
        │   └── 채널 카드 7개 그리드 (수익% + 파이프라인 상태)
        └── 운영 탭
            ├── 파이프라인 스텝 현황 (Step05~12)
            ├── 최신 런 목록 (썸네일 + 상태)
            └── QA 대기 + HITL 신호 + 실시간 미리보기
```

---

## 3. 수정 파일 목록

### 신규 생성
| 파일 | 역할 |
|---|---|
| `web/app/home-exec-tab.tsx` | 경영 탭 클라이언트 컴포넌트 (채널 카드 포함) |
| `web/app/home-ops-tab.tsx` | 운영 탭 클라이언트 컴포넌트 |
| `web/components/kpi-banner.tsx` | KPI 배너 클라이언트 컴포넌트 |

### 수정
| 파일 | 변경 내용 |
|---|---|
| `web/app/globals.css` | 팔레트 교체 (Red Light → Pink Glassmorphism), 폰트 교체 |
| `web/app/layout.tsx` | Noto Sans KR 폰트 + 새 사이드바 적용 |
| `web/app/page.tsx` | KPI 배너 + 탭 컨테이너 구조로 재작성 |
| `web/components/sidebar-nav.tsx` | 접이식 사이드바로 직접 수정 (아이콘 전용 ↔ 아이콘+라벨) |

---

## 4. 컴포넌트 상세 설계

### 4-1. `globals.css` — 팔레트 교체
`@theme inline` 블록과 `:root` 변수를 Pink Glassmorphism 팔레트로 교체.
페이지 배경: `linear-gradient(135deg, #f0ecff 0%, #ffe8e8 45%, #f6f6f6 100%)`

### 4-2. `layout.tsx` — 폰트·사이드바
```tsx
// 폰트: Libre Baskerville 제거, Noto Sans KR 추가
import { Noto_Sans_KR } from 'next/font/google'
const notoSansKR = Noto_Sans_KR({ subsets: ['latin'], weight: ['400','500','600','700','800'] })
```
사이드바를 `CollapsibleSidebar`로 교체.

### 4-3. `kpi-banner.tsx` — 서버 데이터 fetch
서버 컴포넌트에서 다음을 계산하여 props로 전달:
- 이번달 수익 (Supabase `revenue_monthly` 또는 mock `₩0`)
- 목표 달성률 (수익 / 목표 * 100)
- 활성 채널 수 (`launch_phase === 1` 필터)
- 총 Runs (`runs/` 디렉토리 카운트)
- HITL 대기 건수 (`hitl_signals.json` 미해결 건수)

### 4-4. `home-exec-tab.tsx` — 경영 탭
`'use client'` 컴포넌트. 레이아웃:
```
[KPI 카드 ×4]
[채널별 목표 진행] [6개월 추이 차트]
[채널 카드 ×7 그리드]
```
- KPI 카드: hover 시 `translateY(-2px)` + 그림자 강화
- 채널 카드: 활성(`launch_phase === 1`) 컬러 + hover lift, 비활성(준비중) 흐리게 (opacity 0.35)
- 6개월 추이 차트: CSS flexbox 바 차트 (mock 데이터, Recharts 미사용 — 실 데이터 없음)

### 4-5. `home-ops-tab.tsx` — 운영 탭
`'use client'` 컴포넌트. `/api/pipeline/steps`, `/api/pipeline/preview`, `/api/hitl-signals` 폴링(3초).
```
[파이프라인 스텝] [최신 런 목록] [QA·HITL·미리보기]
```
- 기존 `monitor/page.tsx`의 파이프라인 UI를 컴포넌트로 추출하여 재사용
- 테스트 런 버튼 → `/api/pipeline/trigger` POST

### 4-6. `collapsible-sidebar.tsx`
```
[토글 버튼 ChevronsRight]
[아이콘 전용 (width: 44px)]
  ↕ 클릭
[아이콘 + 라벨 (width: 80px)]
```
- `useState`로 open/closed 상태 관리
- CSS `transition: width 0.25s ease`
- 아이콘: Lucide React, stroke 1.8

### 4-7. 탑바 네비 아이콘
아이콘 전용 → hover 시 라벨 슬라이드:
```tsx
// max-width 0 → hover 시 50px 트랜지션
<span className="label">홈</span>  // transition: max-width 0.2s
```

### 4-8. 탭 버튼
아이콘 전용 → hover 시 한글, active 시 `#8785A2` 배경 + 흰 텍스트.

---

## 5. 데이터 흐름

```
page.tsx (서버)
  └── KPI 데이터 fetch (Supabase + readKasJson)
      ├── KpiBanner props 전달
      └── 채널 목록 (launch_phase, 수익) 전달
          ├── HomeExecTab props
          └── HomeOpsTab (자체 폴링)
```

운영 탭은 클라이언트 폴링으로 자체 데이터 수집 (`/api/pipeline/steps` 3초 간격).

---

## 6. 인터랙션 규칙

| 요소 | hover 효과 |
|---|---|
| KPI 카드 | `translateY(-2px)` + 그림자 강화 |
| 채널 카드 | `translateY(-2px)` + 핑크 테두리 |
| 런 목록 행 | `rgba(255,199,199,0.15)` 배경 |
| 버튼 | `translateY(-1px)` + 퍼플 그림자 |
| 차트 바 | `#FFC7C7` 강조 |
| 탑바 아이콘 | 라벨 슬라이드 (max-width 트랜지션) |
| 탭 버튼 | 라벨 슬라이드 |
| 사이드바 아이템 | `rgba(135,133,162,0.12)` 배경 |

---

## 7. 기존 페이지 영향 범위

- `/monitor` — **유지**. 운영 탭과 동일 API 공유하므로 변경 없음.
- `/revenue`, `/trends`, `/qa`, `/runs` 등 — **변경 없음**.
- 사이드바 교체 시 `layout.tsx`의 `AppSidebar` import 경로만 변경.

---

## 8. 비기능 요구사항

- `backdrop-filter: blur()` 미지원 브라우저 폴백: `background` opacity 높임 (`rgba(255,255,255,0.85)`)
- 탭 전환 시 스크롤 위치 유지 (`overflow: hidden` 컨테이너 내부)
- KPI 배너 데이터는 서버 컴포넌트에서 1회 fetch (실시간 갱신 불필요)
- 운영 탭 폴링은 탭이 활성일 때만 실행 (`useEffect` cleanup으로 interval 해제)
