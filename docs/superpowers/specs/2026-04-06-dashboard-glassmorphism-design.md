# KAS 대시보드 Glassmorphism Dark 리디자인

**날짜**: 2026-04-06  
**범위**: 웹 대시보드 전체 (8페이지 + 공통 레이어)  
**디자인 방향**: Glassmorphism Dark (B안) — 기존 Amber Studio 시스템 위에 글래스 레이어 추가  

---

## 1. 개요

현재 Amber Studio 디자인 시스템(oklch 색공간, 7채널 고유 색상, motion 애니메이션)을 유지하면서, 2025 SaaS 트렌드인 Glassmorphism Dark를 입힌다. `backdrop-filter: blur()` + 반투명 배경 + 앰비언트 글로우를 통해 배경 레이어와 카드 레이어 사이에 시각적 깊이감을 만든다.

---

## 2. 변경 파일 목록 (14개)

### 디자인 시스템
| 파일 | 변경 내용 |
|---|---|
| `web/app/globals.css` | 배경 토큰 딥 다크 교체, 글래스 유틸리티 추가, 앰비언트 글로우, 헤더 그라데이션 바 |
| `web/app/layout.tsx` | 최상단 2px 멀티 그라데이션 바 추가, 헤더 글래스 처리 |

### 공통 컴포넌트
| 파일 | 변경 내용 |
|---|---|
| `web/components/ui/card.tsx` | 글래스 카드 스타일 적용 |
| `web/components/sidebar-nav.tsx` | 사이드바 전체 글래스 처리, 활성 항목 글래스 배경 |
| `web/components/home-charts.tsx` | Recharts 차트 색상 채널 oklch 색상으로 교체, 글로우 필터 추가 |
| `web/components/animated-sections.tsx` | 진입 애니메이션 강화 (spring 물리, stagger 딜레이) |

### 페이지
| 파일 | 변경 내용 |
|---|---|
| `web/app/page.tsx` | KPI 카드 4개 글래스, 채널 카드 좌측 컬러 바 |
| `web/app/channels/[id]/page.tsx` | 채널 상세 카드 글래스 |
| `web/app/trends/page.tsx` | 필터 탭 글래스, 주제 카드 글래스, 승인/거부 버튼 글로우 |
| `web/app/revenue/page.tsx` | 차트 컨테이너 글래스, 월별 달성 카드 글래스 |
| `web/app/risk/page.tsx` | HIGH 리스크 빨간 글로우 카드, LOW 초록 글로우 카드 |
| `web/app/learning/page.tsx` | 승리 패턴 앰버 글로우 강조, 일반 패턴 희미한 글래스 |
| `web/app/cost/page.tsx` | 쿼터 진행바 그라데이션, 임계값 경고 빨간 글로우 |
| `web/app/settings/page.tsx` | 설정 섹션 카드 글래스 |

---

## 3. 디자인 시스템 스펙 (globals.css)

### 3-1. 배경 토큰 교체 (다크 모드)

```css
/* 기존 → 신규 */
--background:  oklch(0.14 0.01 55)
           →  oklch(0.07 0.01 240);   /* 딥 블루-블랙 */

--card:        oklch(0.17 0.01 55)
           →  rgba(255 255 255 / 0.04);  /* 반투명 글래스 */
```

### 3-2. 새 글래스 토큰

```css
:root {
  --glass-bg:      rgba(255 255 255 / 0.04);
  --glass-border:  rgba(255 255 255 / 0.08);
  --glass-hover:   rgba(255 255 255 / 0.07);
  --glass-blur:    blur(16px) saturate(180%);

  --glow-primary:  rgba(245 158 11 / 0.25);   /* 앰버 */
  --glow-success:  rgba(34 197 94 / 0.20);    /* 초록 */
  --glow-danger:   rgba(239 68 68 / 0.20);    /* 빨강 */

  --gradient-bar: linear-gradient(90deg, #f59e0b 0%, #ef4444 25%, #8b5cf6 60%, #06b6d4 100%);
}
```

### 3-3. 유틸리티 클래스

```css
@layer utilities {
  .glass-card {
    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur);
    border: 1px solid var(--glass-border);
    box-shadow: 0 4px 24px rgba(0 0 0 / 0.3),
                inset 0 1px 0 rgba(255 255 255 / 0.06);
  }

  .glass-card:hover {
    background: var(--glass-hover);
    border-color: rgba(255 255 255 / 0.12);
  }

  .glow-amber  { box-shadow: 0 0 20px var(--glow-primary); }
  .glow-success { box-shadow: 0 0 20px var(--glow-success); }
  .glow-danger  { box-shadow: 0 0 20px var(--glow-danger); }

  /* 채널 카드 좌측 컬러 바 */
  .channel-bar-left {
    border-left-width: 2px;
    border-left-style: solid;
  }

  /* 배경 앰비언트 글로우 */
  .ambient-bg::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 40% at 80% 20%, rgba(245 158 11 / 0.08) 0%, transparent 60%),
      radial-gradient(ellipse 50% 40% at 20% 80%, rgba(139 92 246 / 0.06) 0%, transparent 60%);
    pointer-events: none;
  }
}
```

---

## 4. 컴포넌트 스펙

### 4-1. card.tsx

기존 `cn()` 기반 className 합성 방식을 유지하면서, `Card` 컴포넌트의 기본 클래스에 글래스 스타일을 추가한다.

```tsx
// 변경 전
"rounded-xl border bg-card text-card-foreground shadow"

// 변경 후
"rounded-xl border bg-card text-card-foreground shadow glass-card"
```

`backdrop-filter`를 지원하지 않는 환경을 위한 폴백: `@supports not (backdrop-filter: blur(1px))` 조건으로 단색 배경 유지.

### 4-2. sidebar-nav.tsx

```tsx
// SidebarContent에 적용
className="... bg-transparent backdrop-blur-xl border-r border-white/5"

// 활성 메뉴 아이템
className="... bg-white/[0.06] border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"

// 채널 점 (이미 구현됨) — 글로우 box-shadow 추가
style={{ boxShadow: `0 0 6px ${channelColor}99` }}
```

### 4-3. layout.tsx (헤더)

헤더 최상단에 2px 그라데이션 바 추가:

```tsx
// SidebarInset 내부 header 위에 추가
<div className="h-[2px] w-full shrink-0"
     style={{ background: 'var(--gradient-bar)' }} />
```

헤더 자체에 `backdrop-blur-xl bg-background/60` 적용.

### 4-4. home-charts.tsx (Recharts)

- **Sparkline**: `stroke` 색상을 채널 oklch 변수로 교체. `style="filter: drop-shadow(0 0 4px {color})"` 추가.
- **RadialGauge**: `<feGaussianBlur>` SVG 필터로 원호에 글로우 효과.
- **BarChart**: `fill`에 `<linearGradient>` 추가 (하단 채널색 → 상단 밝은 버전).

### 4-5. animated-sections.tsx

기존 `StaggerContainer` / `StaggerItem` 유지. `AnimatedCard`에 spring 물리 적용:

```tsx
// 기존 ease
transition={{ duration: 0.4, ease: "easeOut" }}

// 신규 spring
transition={{ type: "spring", stiffness: 260, damping: 20, delay: i * 0.06 }}
```

---

## 5. 페이지별 스펙

### 5-1. 홈 (`page.tsx`)

- KPI 카드 4개: `.glass-card` + 각 카드의 primary 색상 tint (`rgba(channel-color / 0.07)`)
- 채널 카드 7개: `.channel-bar-left` + `border-left-color: var(--channel-chN)` + 좌측 글로우 `box-shadow: -2px 0 12px rgba(channel-color / 0.2)`
- 비활성 채널(Phase 미시작): `opacity-40`, 컬러 바 없음
- 페이지 래퍼: `relative overflow-hidden ambient-bg`

### 5-2. 트렌드 (`trends/page.tsx`)

- 필터 탭(`전체` / `검토 대기` / `자동 승인`): `.glass-card` + 활성 탭 앰버 tint
- 주제 카드: `.glass-card` + 호버 시 `border-color: rgba(255,255,255,0.12)` 전환
- 승인 버튼: `bg-[rgba(34,197,94,0.12)] border-[rgba(34,197,94,0.3)] text-green-400` + 호버 글로우
- 거부 버튼: `bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.2)] text-red-400`

### 5-3. 수익 (`revenue/page.tsx`)

- 차트 컨테이너 `Card`: `.glass-card`
- BarChart: 채널별 `<linearGradient>` fill + `drop-shadow` 필터
- 총계 카드: `bg-[rgba(34,197,94,0.07)] border-[rgba(34,197,94,0.2)]` + 수치 text-shadow 글로우

### 5-4. 리스크 (`risk/page.tsx`)

- HIGH 리스크 카드: `bg-[rgba(239,68,68,0.10)] border-[rgba(239,68,68,0.25)] .glow-danger`
- LOW 리스크 카드: `bg-[rgba(34,197,94,0.06)] border-[rgba(34,197,94,0.18)] .glow-success`
- 배지: HIGH = 빨간 채움, LOW = 초록 채움

### 5-5. 학습 (`learning/page.tsx`)

- 승리 패턴 카드(`is_winning: true`): `bg-[rgba(245,158,11,0.08)] border-[rgba(245,158,11,0.22)] .glow-amber`
- 일반 패턴 카드: `.glass-card` (기본)
- CTR/AVP 뱃지: 앰버 tint 배경

### 5-6. 비용 (`cost/page.tsx`)

- 쿼터 카드: `.glass-card`
- 진행바: `background: linear-gradient(90deg, channelColor, lighterVersion)` + 글로우 box-shadow
- 임계값 근접(≥80%): 카드 전체 `.glow-danger` + 경고 텍스트 빨간색

### 5-7. 설정 (`settings/page.tsx`)

- 섹션 카드: `.glass-card` (읽기 전용이므로 인터랙션 없음)

### 5-8. 채널 상세 (`channels/[id]/page.tsx`)

- 모든 카드: `.glass-card`
- 페이지 헤더: 해당 채널 고유색 앰비언트 글로우

---

## 6. 라이트 모드 처리

기존 라이트 모드(C 옵션 Warm Minimal)는 그대로 유지한다. `globals.css`의 `:root` (라이트) 토큰은 변경하지 않고, `.dark` 토큰만 업데이트한다. 글래스 유틸리티 클래스는 다크 모드에서만 `backdrop-filter`를 활성화한다:

```css
.glass-card {
  background: hsl(var(--card));  /* 라이트: 기존 단색 */
}
.dark .glass-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border-color: var(--glass-border);
}
```

---

## 7. 구현 순서

1. `globals.css` — 토큰·유틸리티 먼저 정의 (다른 모든 파일의 의존성)
2. `ui/card.tsx` — 글래스 기본 카드 (전체 페이지 자동 반영)
3. `layout.tsx` — 헤더 그라데이션 바 + 글래스 헤더
4. `sidebar-nav.tsx` — 사이드바 글래스
5. `page.tsx` (홈) — 채널 컬러 바 + KPI 카드
6. `home-charts.tsx` — Recharts 글로우
7. `animated-sections.tsx` — spring 전환
8. 운영 페이지 5개 (trends → revenue → risk → learning → cost) — 순서대로
9. `settings/page.tsx`, `channels/[id]/page.tsx` — 마지막
