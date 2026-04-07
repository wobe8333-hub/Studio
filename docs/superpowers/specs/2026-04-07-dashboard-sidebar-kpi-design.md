# 대시보드 개선 설계 — 사이드바 카테고리화 + KPI 페이지 요약

**작성일**: 2026-04-07  
**대상 파일**: `web/components/sidebar-nav.tsx`, `web/app/page.tsx`

---

## 1. 사이드바 카테고리화

### 현재 상태
9개 메뉴 항목이 "대시보드"라는 단일 그룹 아래 평탄하게 나열됨.

### 변경 후 구조 (3그룹)

| 그룹 헤더 | 포함 항목 |
|---|---|
| **대시보드** | 전체 KPI (`/`) |
| **콘텐츠** | 트렌드 관리 (`/trends`), 지식 수집 (`/knowledge`), QA 검수 (`/qa`) |
| **수익 / 비용** | 수익 추적 (`/revenue`), 비용/쿼터 (`/cost`), 리스크 모니터링 (`/risk`) |
| **시스템** | 파이프라인 모니터 (`/monitor`), 학습 피드백 (`/learning`) |
| **채널별 상세** | 기존 채널 목록 섹션 유지 |

### 구현 방법
- `sidebar-nav.tsx`의 단일 `navItems` 배열을 그룹 배열(`NAV_GROUPS`)로 교체
- 각 그룹에 `label: string`, `items: NavItem[]` 속성 부여
- 그룹 헤더는 `SidebarGroupLabel`(shadcn) 컴포넌트로 렌더링
- 그룹 간 시각적 구분: `SidebarSeparator` 또는 `mt-4` 간격

---

## 2. 전체 KPI 페이지 요약화

### 현재 상태 (388줄)
- KPI 카드 4개
- 채널별 수익 현황 7열 그리드
- 파이프라인 타임라인 (Card + TimelineNode)
- 채널별 현황 그리드 (ChannelCard × 7, 각 카드에 수익/CTR/신뢰도)

### 변경 후 구조

#### KPI 카드 — 6개 (3×2 그리드)
| 번호 | 레이블 | 값 출처 |
|---|---|---|
| 1 | 월 목표 | 하드코딩 ₩14,000,000 |
| 2 | 활성 채널 | `channels.filter(launch_phase===1).length / 7` |
| 3 | 총 Runs | `/api/pipeline/status` → `total_runs` |
| 4 | 이번달 달성률 | Supabase `revenue_monthly` 또는 mock `0%` |
| 5 | 리스크 채널 | Supabase `risk_monthly` HIGH 건수 또는 `0` |
| 6 | HITL 대기 | `/api/hitl-signals` 미해결 건수 |

#### 채널 상태 섹션 — 도트 7개
- 각 채널을 32px 원형 컬러 도트로 표시
- 도트 아래 카테고리명 + LIVE/준비 상태 텍스트
- 활성 채널: 채널 고유색, 불활성: `#ddd` + 0.4 opacity

#### 제거 항목
- 파이프라인 타임라인 섹션 전체 (`TimelineNode`, `RunStateBadge` 포함)
- 채널별 현황 그리드 (`ChannelCard` 컴포넌트)
- 채널별 수익 현황 7열 그리드

### 데이터 페치
- `total_runs`, `hitl_pending` 추가를 위해 `fetchData()`에서 `/api/pipeline/status`, `/api/hitl-signals` 병렬 fetch 추가
- 기존 Supabase mock fallback 패턴 유지

---

## 3. 영향 범위

| 파일 | 변경 유형 |
|---|---|
| `web/components/sidebar-nav.tsx` | `navItems[]` → `NAV_GROUPS[]` 리팩터 |
| `web/app/page.tsx` | KPI 섹션 재구성, 불필요 섹션 제거 |

- `ChannelCard`, `TimelineNode`, `RunStateBadge` 함수: `page.tsx` 내부에서만 사용되므로 함께 제거
- `home-charts.tsx`의 `Sparkline`, `RadialGauge`, `ChannelDots`: KPI 카드에서 계속 사용 여부 확인 필요 → 달성률 카드에 `RadialGauge` 유지, 나머지 제거

---

## 4. 비기능 요건
- 기존 Red Light Glassmorphism 디자인 토큰(`G` 상수, `--c-*` CSS 변수) 그대로 사용
- 서버 컴포넌트(`page.tsx`) 유지 — 클라이언트 훅 추가 없음
- 모바일 반응형: KPI 그리드 `grid-cols-2 sm:grid-cols-3`, 채널 도트 `flex-wrap`
