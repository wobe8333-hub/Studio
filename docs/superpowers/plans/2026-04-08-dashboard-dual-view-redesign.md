# KAS 대시보드 Dual-View 재구성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈(`/`) 페이지를 KPI 배너 고정 + 경영/운영 탭 전환 구조로 재구성하고, Glassmorphism Pink 디자인 시스템을 전체 대시보드에 적용한다.

**Architecture:** `page.tsx`(서버 컴포넌트)에서 데이터를 fetch해 `KpiBanner`와 `HomeExecTab`에 props로 전달한다. `HomeExecTab`('use client')이 탭 상태를 관리하고 경영 콘텐츠 or `HomeOpsTab`을 조건부 렌더링한다. `layout.tsx`의 shadcn SidebarProvider를 제거하고 커스텀 `CollapsibleSidebar`로 교체한다.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 · Lucide React · Noto Sans KR · Glassmorphism (backdrop-filter)

---

## 파일 맵

**신규 생성:**
| 파일 | 역할 |
|---|---|
| `web/app/home-exec-tab.tsx` | 탭 컨트롤러 + 경영 탭 콘텐츠 (채널 카드 포함) |
| `web/app/home-ops-tab.tsx` | 운영 탭 콘텐츠 (3초 폴링) |
| `web/components/kpi-banner.tsx` | KPI 배너 클라이언트 컴포넌트 |

**수정:**
| 파일 | 변경 내용 |
|---|---|
| `web/app/globals.css` | Pink Glassmorphism 팔레트 + Noto Sans KR |
| `web/app/layout.tsx` | SidebarProvider 제거, 새 CollapsibleSidebar + 탑바 |
| `web/app/page.tsx` | KPI 배너 + 탭 구조로 재작성 |
| `web/components/sidebar-nav.tsx` | 접이식 사이드바 재작성 |

---

## Task 1: globals.css — 팔레트 & 폰트 교체

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: globals.css 전체를 아래 내용으로 교체**

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'Noto Sans KR', 'Consolas', monospace;
  --font-heading: 'Noto Sans KR', sans-serif;
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
  --radius-3xl: calc(var(--radius) * 2.2);
  --radius-4xl: calc(var(--radius) * 2.6);
  --color-channel-ch1: var(--channel-ch1);
  --color-channel-ch2: var(--channel-ch2);
  --color-channel-ch3: var(--channel-ch3);
  --color-channel-ch4: var(--channel-ch4);
  --color-channel-ch5: var(--channel-ch5);
  --color-channel-ch6: var(--channel-ch6);
  --color-channel-ch7: var(--channel-ch7);
}

:root {
  /* ─── Pink Glassmorphism 팔레트 ─── */
  --p1: #FFC7C7;   /* 살구핑크 — 프로그레스 바, 강조 */
  --p2: #FFE2E2;   /* 연핑크 — KPI 배너 배경 */
  --p3: #F6F6F6;   /* 라이트그레이 — 페이지 배경 */
  --p4: #8785A2;   /* 뮤트 퍼플 — 탑바, 사이드바, 버튼 */
  --t1: #2d2b3d;   /* 진한 텍스트 */
  --t2: #5c5a74;   /* 서브 텍스트 */
  --t3: #9896b0;   /* 뮤트 텍스트 */

  /* shadcn 호환 토큰 */
  --background: #F6F6F6;
  --foreground: #2d2b3d;
  --card: rgba(255,255,255,0.55);
  --card-foreground: #2d2b3d;
  --popover: #ffffff;
  --popover-foreground: #2d2b3d;
  --primary: #8785A2;
  --primary-foreground: #ffffff;
  --secondary: #FFE2E2;
  --secondary-foreground: #2d2b3d;
  --muted: #F6F6F6;
  --muted-foreground: #9896b0;
  --accent: #FFC7C7;
  --accent-foreground: #2d2b3d;
  --destructive: oklch(0.55 0.25 25);
  --border: rgba(255,199,199,0.3);
  --input: rgba(255,199,199,0.15);
  --ring: #8785A2;
  --chart-1: #8785A2;
  --chart-2: #FFC7C7;
  --chart-3: #2d2b3d;
  --chart-4: #FFE2E2;
  --chart-5: #5c5a74;
  --radius: 0.75rem;

  /* 사이드바 */
  --sidebar: rgba(135,133,162,0.92);
  --sidebar-foreground: #ffffff;
  --sidebar-primary: #FFC7C7;
  --sidebar-primary-foreground: #2d2b3d;
  --sidebar-accent: rgba(255,255,255,0.12);
  --sidebar-accent-foreground: #ffffff;
  --sidebar-border: rgba(255,199,199,0.2);
  --sidebar-ring: #FFC7C7;

  /* 7채널 고유 색상 */
  --channel-ch1: #e07070;
  --channel-ch2: #c4a0d4;
  --channel-ch3: #7ab3d4;
  --channel-ch4: #8785A2;
  --channel-ch5: #d47a7a;
  --channel-ch6: #70a4d4;
  --channel-ch7: #b4709c;

  /* 하위 호환 alias — 기존 --c-dark 등 참조 페이지용 */
  --c-dark:      #8785A2;
  --c-red:       #FFC7C7;
  --c-salmon:    #FFE2E2;
  --c-blush:     #FFE2E2;
  --c-cream:     #F6F6F6;
  --t-primary:   #2d2b3d;
  --t-secondary: #5c5a74;
  --t-muted:     #9896b0;
  --t-accent:    #8785A2;
  --t-on-dark:   #ffffff;
}

.dark {
  --background: #1a192b;
  --foreground: #f0ecff;
  --card: rgba(135,133,162,0.15);
  --card-foreground: #f0ecff;
  --popover: #22203a;
  --popover-foreground: #f0ecff;
  --primary: #FFC7C7;
  --primary-foreground: #2d2b3d;
  --secondary: rgba(135,133,162,0.25);
  --secondary-foreground: #FFE2E2;
  --muted: rgba(135,133,162,0.20);
  --muted-foreground: #9896b0;
  --accent: rgba(135,133,162,0.30);
  --accent-foreground: #FFE2E2;
  --destructive: oklch(0.70 0.20 25);
  --border: rgba(255,199,199,0.15);
  --input: rgba(255,199,199,0.10);
  --ring: #FFC7C7;
  --chart-1: #FFC7C7;
  --chart-2: #8785A2;
  --chart-3: #5c5a74;
  --chart-4: #FFE2E2;
  --chart-5: #9896b0;
  --sidebar: rgba(30,28,50,0.95);
  --sidebar-foreground: #f0ecff;
  --sidebar-primary: #FFC7C7;
  --sidebar-primary-foreground: #2d2b3d;
  --sidebar-accent: rgba(255,255,255,0.08);
  --sidebar-accent-foreground: #f0ecff;
  --sidebar-border: rgba(255,199,199,0.10);
  --sidebar-ring: #FFC7C7;
  --channel-ch1: #f09090;
  --channel-ch2: #d4b0e4;
  --channel-ch3: #90c3e4;
  --channel-ch4: #9896b0;
  --channel-ch5: #e49090;
  --channel-ch6: #80b4e4;
  --channel-ch7: #c480ac;
  --c-dark:      #9896b0;
  --c-red:       #FFC7C7;
  --t-primary:   #f0ecff;
  --t-secondary: #c8c6e0;
  --t-muted:     #9896b0;
  --glass-bg:     rgba(135,133,162,0.15);
  --glass-border: rgba(255,199,199,0.15);
  --glass-hover:  rgba(135,133,162,0.25);
  --glass-blur:   blur(16px) saturate(180%);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    background: linear-gradient(135deg, #f0ecff 0%, #ffe8e8 45%, #f6f6f6 100%);
    background-attachment: fixed;
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--foreground);
  }
  html {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: 'Noto Sans KR', sans-serif;
  }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(135,133,162,0.3); }
  50%       { box-shadow: 0 0 12px 4px rgba(135,133,162,0.12); }
}

@layer utilities {
  .bg-mesh-warm {
    background:
      radial-gradient(ellipse at 20% 50%, rgba(135,133,162,0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(255,199,199,0.05) 0%, transparent 50%),
      radial-gradient(ellipse at 60% 80%, rgba(255,226,226,0.04) 0%, transparent 50%);
  }

  .glass-card {
    background: rgba(255,255,255,0.55);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,199,199,0.3);
    border-radius: 0.75rem;
    box-shadow: 0 4px 16px rgba(135,133,162,0.08);
  }
  .glass-card-hover {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .glass-card-hover:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(135,133,162,0.14);
  }
  .dark .glass-card {
    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-color: var(--glass-border);
    box-shadow: 0 4px 24px rgba(0,0,0,0.35),
                inset 0 1px 0 rgba(255,199,199,0.06);
  }
  .dark .glass-card:hover {
    background: var(--glass-hover);
    border-color: rgba(255,199,199,0.20);
  }

  .heading-font {
    font-family: 'Noto Sans KR', sans-serif;
  }
  .mono-font {
    font-family: 'Noto Sans KR', 'Consolas', monospace;
  }

  .text-purple-accent {
    color: #8785A2;
  }
  .bg-purple-glass {
    background: rgba(135,133,162,0.88);
    backdrop-filter: blur(20px);
  }

  .animate-pulse-glow {
    animation: pulse-glow 2s ease-in-out infinite;
  }
  .glow-primary {
    box-shadow: 0 0 20px rgba(135,133,162,0.25),
                0 0 0 1px rgba(135,133,162,0.15);
  }
  .glow-success {
    box-shadow: 0 0 20px rgba(34,197,94,0.20),
                0 0 0 1px rgba(34,197,94,0.12);
  }
  .glow-danger {
    box-shadow: 0 0 20px rgba(239,68,68,0.20),
                0 0 0 1px rgba(239,68,68,0.15);
  }

  @supports not (backdrop-filter: blur(1px)) {
    .glass-card {
      background: rgba(246,246,246,0.95);
    }
    .dark .glass-card {
      background: #22203a;
    }
  }
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` (0 errors)

- [ ] **Step 3: commit**

```bash
git add web/app/globals.css
git commit -m "design: Pink Glassmorphism 팔레트 + Noto Sans KR 폰트 전환"
```

---

## Task 2: sidebar-nav.tsx — 접이식 사이드바 재작성

**Files:**
- Modify: `web/components/sidebar-nav.tsx`

- [ ] **Step 1: sidebar-nav.tsx 전체를 아래 내용으로 교체**

shadcn Sidebar 의존성 전체 제거. `useState` 기반 CSS 트랜지션 접이식 사이드바로 교체. 아이콘 전용(44px) ↔ 아이콘+라벨(160px) 토글.

```tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  CheckSquare,
  List,
  Monitor,
  Tv,
  Settings,
  ChevronsRight,
} from 'lucide-react'

const NAV_ITEMS = [
  { title: 'KPI 대시보드', url: '/',          icon: LayoutDashboard },
  { title: '트렌드 관리',  url: '/trends',    icon: TrendingUp },
  { title: '수익 추적',   url: '/revenue',   icon: BarChart2 },
  { title: 'QA 검수',     url: '/qa',        icon: CheckSquare },
  { title: '런 목록',     url: '/runs/CH1',  icon: List },
  { title: '파이프라인',  url: '/monitor',   icon: Monitor },
  { title: '채널 상세',   url: '/channels/CH1', icon: Tv },
  { title: '설정',        url: '/settings',  icon: Settings },
]

interface ChannelItem {
  id: string
  category_ko: string | null
}

interface CollapsibleSidebarProps {
  channels?: ChannelItem[]
}

export function CollapsibleSidebar({ channels: _channels }: CollapsibleSidebarProps) {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  return (
    <div
      style={{
        width: open ? 160 : 44,
        height: '100vh',
        position: 'sticky',
        top: 0,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(135,133,162,0.92)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(255,199,199,0.2)',
        transition: 'width 0.25s ease',
        overflow: 'hidden',
        zIndex: 20,
      }}
    >
      {/* 토글 버튼 */}
      <button
        onClick={() => setOpen(!open)}
        aria-label={open ? '사이드바 닫기' : '사이드바 열기'}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 44,
          height: 44,
          flexShrink: 0,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'rgba(255,255,255,0.7)',
        }}
      >
        <ChevronsRight
          size={18}
          strokeWidth={1.8}
          style={{
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.25s ease',
          }}
        />
      </button>

      {/* 네비게이션 */}
      <nav style={{ flex: 1, paddingTop: 4, overflowY: 'auto', overflowX: 'hidden' }}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.url === '/'
            ? pathname === '/'
            : pathname.startsWith(item.url)
          return (
            <Link
              key={item.url}
              href={item.url}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                margin: '1px 4px',
                borderRadius: 8,
                color: isActive ? '#ffffff' : 'rgba(255,255,255,0.7)',
                background: isActive ? 'rgba(255,255,255,0.18)' : 'transparent',
                textDecoration: 'none',
                whiteSpace: 'nowrap',
                transition: 'background 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.10)'
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent'
              }}
            >
              <item.icon size={18} strokeWidth={1.8} style={{ flexShrink: 0 }} />
              <span
                style={{
                  maxWidth: open ? 120 : 0,
                  overflow: 'hidden',
                  opacity: open ? 1 : 0,
                  transition: 'max-width 0.25s ease, opacity 0.2s ease',
                  fontSize: 13,
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                }}
              >
                {item.title}
              </span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

// AppSidebar alias — layout.tsx 교체 전 하위호환
export { CollapsibleSidebar as AppSidebar }
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 빌드 성공

- [ ] **Step 3: commit**

```bash
git add web/components/sidebar-nav.tsx
git commit -m "feat: 접이식 사이드바 (아이콘 44px ↔ 라벨+아이콘 160px 토글)"
```

---

## Task 3: layout.tsx — 탑바 & 레이아웃 구조 교체

**Files:**
- Modify: `web/app/layout.tsx`

- [ ] **Step 1: layout.tsx 전체를 아래 내용으로 교체**

`SidebarProvider / SidebarInset / SidebarTrigger` 제거. Noto Sans KR 추가. Pink Glassmorphism 탑바. `RealtimePipelineStatus`, `HitlBanner`는 홈 탭 구조로 이전됐으므로 제거.

```tsx
import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from 'next-themes'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CollapsibleSidebar } from '@/components/sidebar-nav'
import { createClient } from '@/lib/supabase/server'

export const metadata: Metadata = {
  title: 'KAS Studio — 7채널 AI 자동화 대시보드',
  description: 'Knowledge Animation Studio 파이프라인 모니터링 대시보드',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'KAS Studio',
  },
  other: {
    'mobile-web-app-capable': 'yes',
  },
}

async function fetchChannels() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return null

  try {
    const supabase = await createClient()
    const { data } = await supabase
      .from('channels')
      .select('id, category_ko')
      .order('id')
    return data
  } catch {
    return null
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const channels = await fetchChannels()

  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <TooltipProvider>
            <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
              {/* 접이식 사이드바 */}
              <CollapsibleSidebar channels={channels ?? undefined} />

              {/* 오른쪽 메인 영역 */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* 탑바 */}
                <header
                  style={{
                    height: 48,
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0 20px',
                    background: 'rgba(135,133,162,0.82)',
                    backdropFilter: 'blur(20px)',
                    WebkitBackdropFilter: 'blur(20px)',
                    borderBottom: '1px solid rgba(255,199,199,0.2)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 10,
                  }}
                >
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: 15,
                      color: '#ffffff',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    KAS Studio
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 99,
                      background: 'rgba(255,199,199,0.25)',
                      color: '#FFC7C7',
                      letterSpacing: '0.08em',
                    }}
                  >
                    LIVE
                  </span>
                </header>

                {/* 페이지 콘텐츠 */}
                <main
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '16px 20px',
                  }}
                >
                  {children}
                </main>
              </div>
            </div>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 빌드 성공. `RealtimePipelineStatus`, `HitlBanner`, `SidebarProvider` 등 참조 제거됐으므로 미사용 import 경고 없음.

- [ ] **Step 3: commit**

```bash
git add web/app/layout.tsx
git commit -m "feat: Pink Glassmorphism 탑바 + 접이식 사이드바 레이아웃 전환"
```

---

## Task 4: kpi-banner.tsx — KPI 배너 신규 생성

**Files:**
- Create: `web/components/kpi-banner.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client'

interface KpiBannerProps {
  revenue: number
  achievementRate: number
  activeChannels: number
  totalChannels: number
  totalRuns: number
  hitlPending: number
}

interface KpiItemProps {
  label: string
  value: string
  sub?: string
  highlight?: boolean
  isLast?: boolean
}

function KpiItem({ label, value, sub, highlight, isLast }: KpiItemProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        padding: '0 24px',
        borderRight: isLast ? 'none' : '1px solid rgba(255,199,199,0.25)',
        minWidth: 130,
        flex: 1,
      }}
    >
      <span
        style={{
          fontSize: 11,
          color: '#9896b0',
          fontWeight: 500,
          letterSpacing: '0.04em',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: highlight ? '#dc3545' : '#2d2b3d',
          letterSpacing: '-0.02em',
          lineHeight: 1.2,
          whiteSpace: 'nowrap',
        }}
      >
        {value}
      </span>
      {sub && (
        <span style={{ fontSize: 10, color: '#9896b0', whiteSpace: 'nowrap' }}>{sub}</span>
      )}
    </div>
  )
}

export function KpiBanner({
  revenue,
  achievementRate,
  activeChannels,
  totalChannels,
  totalRuns,
  hitlPending,
}: KpiBannerProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255,226,226,0.62)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,199,199,0.3)',
        borderRadius: '0.75rem',
        boxShadow: '0 4px 16px rgba(135,133,162,0.08)',
        padding: '14px 0',
        marginBottom: 16,
        overflowX: 'auto',
      }}
    >
      <KpiItem
        label="이번달 수익"
        value={`₩${revenue.toLocaleString()}`}
        sub="목표: ₩14,000,000"
      />
      <KpiItem
        label="달성률"
        value={`${achievementRate.toFixed(1)}%`}
        sub="목표 대비"
      />
      <KpiItem
        label="활성 채널"
        value={`${activeChannels}/${totalChannels}`}
        sub="launch_phase 1"
      />
      <KpiItem
        label="총 Runs"
        value={String(totalRuns)}
        sub="누적 실행"
      />
      <KpiItem
        label="HITL 대기"
        value={`${hitlPending}건`}
        highlight={hitlPending > 0}
        sub={hitlPending > 0 ? '확인 필요' : '정상'}
        isLast
      />
    </div>
  )
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 빌드 성공

- [ ] **Step 3: commit**

```bash
git add web/components/kpi-banner.tsx
git commit -m "feat: KPI 배너 컴포넌트 신규 생성 (Pink Glassmorphism)"
```

---

## Task 5: home-exec-tab.tsx — 경영 탭 + 탭 컨트롤러

**Files:**
- Create: `web/app/home-exec-tab.tsx`

- [ ] **Step 1: 파일 생성**

탭 상태(경영/운영) 관리 + 경영 탭 콘텐츠. 운영 탭 선택 시 `HomeOpsTab` 렌더링.

```tsx
'use client'

import { useState } from 'react'
import {
  LayoutDashboard,
  Monitor,
  DollarSign,
  TrendingUp,
  BarChart2,
  Activity,
} from 'lucide-react'
import HomeOpsTab from './home-ops-tab'
import type { Channel } from '@/lib/types'

const CH_COLORS: Record<string, string> = {
  CH1: '#e07070',
  CH2: '#c4a0d4',
  CH3: '#7ab3d4',
  CH4: '#8785A2',
  CH5: '#d47a7a',
  CH6: '#70a4d4',
  CH7: '#b4709c',
}

// 6개월 추이 — mock 데이터 (실 수익 데이터 미연동)
const MONTHLY_TREND = [
  { month: '11월', value: 0 },
  { month: '12월', value: 0 },
  { month: '1월',  value: 0 },
  { month: '2월',  value: 0 },
  { month: '3월',  value: 0 },
  { month: '4월',  value: 0 },
]

const CARD_BASE: React.CSSProperties = {
  background: 'rgba(255,255,255,0.55)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,199,199,0.3)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(135,133,162,0.08)',
}

interface KpiCardProps {
  label: string
  value: string
  sub: string
  Icon: React.ElementType
}

function KpiCard({ label, value, sub, Icon }: KpiCardProps) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      style={{
        ...CARD_BASE,
        padding: 16,
        transform: hovered ? 'translateY(-2px)' : 'none',
        boxShadow: hovered
          ? '0 12px 32px rgba(135,133,162,0.14)'
          : '0 4px 16px rgba(135,133,162,0.08)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: '#9896b0', fontWeight: 500 }}>{label}</span>
        <Icon size={16} strokeWidth={1.8} color="#8785A2" />
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color: '#2d2b3d', lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: 11, color: '#9896b0', marginTop: 4 }}>{sub}</div>
    </div>
  )
}

interface ChannelCardProps {
  ch: Channel
  isActive: boolean
}

function ChannelCard({ ch, isActive }: ChannelCardProps) {
  const [hovered, setHovered] = useState(false)
  const color = CH_COLORS[ch.id] ?? '#8785A2'
  return (
    <div
      style={{
        ...CARD_BASE,
        padding: 14,
        opacity: isActive ? 1 : 0.35,
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
        transform: hovered && isActive ? 'translateY(-2px)' : 'none',
        borderColor: hovered && isActive ? 'rgba(255,199,199,0.7)' : 'rgba(255,199,199,0.3)',
        boxShadow: hovered && isActive
          ? '0 8px 24px rgba(135,133,162,0.14)'
          : '0 4px 16px rgba(135,133,162,0.08)',
        cursor: isActive ? 'pointer' : 'default',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: isActive ? color : '#d1d5db',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 9,
            fontWeight: 700,
            boxShadow: isActive ? `0 0 8px ${color}80` : 'none',
            flexShrink: 0,
          }}
        >
          {ch.id}
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#2d2b3d' }}>{ch.category_ko}</div>
          <div style={{ fontSize: 10, color: isActive ? '#16a34a' : '#9896b0' }}>
            {isActive ? 'LIVE' : '준비중'}
          </div>
        </div>
      </div>
      {/* 수익 진행 바 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: '#9896b0' }}>이번달 수익</span>
          <span style={{ fontSize: 10, color: '#2d2b3d', fontWeight: 600 }}>0%</span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,199,199,0.2)', borderRadius: 2, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: '0%',
              background: isActive ? color : '#d1d5db',
              borderRadius: 2,
            }}
          />
        </div>
      </div>
    </div>
  )
}

interface HomeExecTabProps {
  channels: Channel[]
  totalRuns: number
  activeChannelCount: number
}

export default function HomeExecTab({ channels, totalRuns, activeChannelCount }: HomeExecTabProps) {
  const [activeTab, setActiveTab] = useState<'exec' | 'ops'>('exec')

  const TABS = [
    { id: 'exec' as const, label: '경영', Icon: LayoutDashboard },
    { id: 'ops'  as const, label: '운영', Icon: Monitor },
  ]

  return (
    <div>
      {/* 탭 바 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 16px',
                borderRadius: 8,
                border: 'none',
                cursor: 'pointer',
                background: isActive ? '#8785A2' : 'transparent',
                color: isActive ? '#ffffff' : '#9896b0',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                transition: 'background 0.2s ease, color 0.2s ease',
              }}
            >
              <tab.Icon size={15} strokeWidth={1.8} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── 경영 탭 ── */}
      {activeTab === 'exec' && (
        <div>
          {/* KPI 카드 4개 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 12,
              marginBottom: 16,
            }}
          >
            <KpiCard label="이번달 수익"  value="₩0"                        sub="목표: ₩14,000,000" Icon={DollarSign} />
            <KpiCard label="달성률"       value="0%"                         sub="목표 대비"         Icon={TrendingUp} />
            <KpiCard label="총 Runs"      value={String(totalRuns)}          sub="누적 실행"         Icon={BarChart2}  />
            <KpiCard label="활성 채널"    value={`${activeChannelCount}/7`}  sub="launch_phase 1"   Icon={Activity}   />
          </div>

          {/* 채널 목표 진행 바 + 6개월 추이 차트 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 12,
              marginBottom: 16,
            }}
          >
            {/* 채널별 목표 진행 */}
            <div style={{ ...CARD_BASE, padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#2d2b3d', marginBottom: 12 }}>
                채널별 목표 진행
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {channels.map((ch) => {
                  const color = CH_COLORS[ch.id] ?? '#8785A2'
                  const isActive = ch.launch_phase === 1
                  return (
                    <div key={ch.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 11, color: '#5c5a74', fontWeight: 500 }}>
                          {ch.id} {ch.category_ko}
                        </span>
                        <span style={{ fontSize: 11, color: '#9896b0' }}>0%</span>
                      </div>
                      <div
                        style={{
                          height: 5,
                          background: 'rgba(255,199,199,0.2)',
                          borderRadius: 3,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: '0%',
                            background: isActive ? color : '#d1d5db',
                            borderRadius: 3,
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* 6개월 수익 추이 — CSS flex 바 차트 (mock) */}
            <div style={{ ...CARD_BASE, padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#2d2b3d', marginBottom: 12 }}>
                6개월 수익 추이
              </h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 80 }}>
                {MONTHLY_TREND.map((item) => (
                  <div
                    key={item.month}
                    style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
                  >
                    <div
                      style={{
                        width: '100%',
                        height: item.value > 0 ? `${(item.value / 14000000) * 64}px` : 4,
                        background: item.value > 0 ? '#FFC7C7' : 'rgba(255,199,199,0.2)',
                        borderRadius: '3px 3px 0 0',
                        transition: 'height 0.6s ease',
                      }}
                    />
                    <span style={{ fontSize: 9, color: '#9896b0' }}>{item.month}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 채널 카드 7개 그리드 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: 10,
            }}
          >
            {channels.map((ch) => (
              <ChannelCard key={ch.id} ch={ch} isActive={ch.launch_phase === 1} />
            ))}
          </div>
        </div>
      )}

      {/* ── 운영 탭 ── */}
      {activeTab === 'ops' && <HomeOpsTab />}
    </div>
  )
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -30
```

Expected: 빌드 성공. TypeScript 타입 오류 없음.

- [ ] **Step 3: commit**

```bash
git add web/app/home-exec-tab.tsx
git commit -m "feat: 경영 탭 — KPI 카드·진행 바·채널 카드 그리드 + 탭 컨트롤러"
```

---

## Task 6: home-ops-tab.tsx — 운영 탭

**Files:**
- Create: `web/app/home-ops-tab.tsx`

- [ ] **Step 1: 파일 생성**

`/api/pipeline/steps`, `/api/hitl-signals` 3초 폴링. 파이프라인 스텝 Step05~12 현황 + HITL 신호 + 파이프라인 제어.

```tsx
'use client'

import { useState, useEffect, useCallback } from 'react'

interface StepStatus {
  step: string
  status: 'idle' | 'running' | 'done' | 'error' | 'skipped'
}

interface HitlSignal {
  id: string
  type: string
  message: string
  resolved: boolean
}

const STEP_LABELS: Record<string, string> = {
  step05: 'Step05 · 트렌드 수집',
  step06: 'Step06 · 정책 적용',
  step07: 'Step07 · 콘텐츠 계획',
  step08: 'Step08 · 영상 생성',
  step09: 'Step09 · BGM 합성',
  step10: 'Step10 · 제목/썸네일',
  step11: 'Step11 · QA 검수',
  step12: 'Step12 · YouTube 업로드',
}

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  idle:    { bg: 'rgba(152,150,176,0.10)', color: '#9896b0', label: 'IDLE' },
  running: { bg: 'rgba(255,199,100,0.15)', color: '#c4860f', label: 'RUNNING' },
  done:    { bg: 'rgba(34,197,94,0.12)',   color: '#16a34a', label: 'DONE' },
  error:   { bg: 'rgba(239,68,68,0.12)',   color: '#dc2626', label: 'ERROR' },
  skipped: { bg: 'rgba(152,150,176,0.06)', color: '#c0bdd8', label: 'SKIPPED' },
}

const CARD_BASE: React.CSSProperties = {
  background: 'rgba(255,255,255,0.55)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,199,199,0.3)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(135,133,162,0.08)',
  padding: 16,
}

export default function HomeOpsTab() {
  const [steps, setSteps] = useState<StepStatus[]>([])
  const [hitlSignals, setHitlSignals] = useState<HitlSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)

  const fetchAll = useCallback(async () => {
    try {
      const [stepsRes, hitlRes] = await Promise.all([
        fetch('/api/pipeline/steps').then((r) => (r.ok ? r.json() : { steps: [] })),
        fetch('/api/hitl-signals').then((r) => (r.ok ? r.json() : [])),
      ])
      setSteps(stepsRes.steps ?? [])
      setHitlSignals(
        Array.isArray(hitlRes) ? hitlRes.filter((s: HitlSignal) => !s.resolved) : []
      )
    } catch {
      /* 네트워크 오류 무시 */
    } finally {
      setLoading(false)
    }
  }, [])

  // 탭이 활성일 때만 폴링
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 3000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const triggerRun = async () => {
    setTriggering(true)
    try {
      await fetch('/api/pipeline/trigger', { method: 'POST' })
      await fetchAll()
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      {/* 파이프라인 스텝 현황 */}
      <div style={CARD_BASE}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#2d2b3d', marginBottom: 12 }}>
          파이프라인 스텝 현황
        </h3>
        {loading ? (
          <div style={{ color: '#9896b0', fontSize: 12 }}>불러오는 중...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {Object.entries(STEP_LABELS).map(([stepId, label]) => {
              const stepData = steps.find((s) => s.step === stepId)
              const status = stepData?.status ?? 'idle'
              const style = STATUS_STYLE[status] ?? STATUS_STYLE.idle
              return (
                <div
                  key={stepId}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '7px 10px',
                    borderRadius: 8,
                    background: style.bg,
                  }}
                >
                  <span style={{ fontSize: 12, color: '#5c5a74', fontWeight: 500 }}>{label}</span>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: style.color,
                      letterSpacing: '0.05em',
                    }}
                  >
                    {style.label}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 오른쪽 패널: HITL + 파이프라인 제어 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* HITL 신호 */}
        <div style={CARD_BASE}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#2d2b3d', marginBottom: 12 }}>
            HITL 대기 신호
            {hitlSignals.length > 0 && (
              <span
                style={{
                  marginLeft: 8,
                  background: 'rgba(239,68,68,0.12)',
                  color: '#dc2626',
                  fontSize: 10,
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: 99,
                }}
              >
                {hitlSignals.length}
              </span>
            )}
          </h3>
          {hitlSignals.length === 0 ? (
            <div style={{ color: '#16a34a', fontSize: 12 }}>대기 신호 없음 ✓</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {hitlSignals.slice(0, 4).map((sig) => (
                <div
                  key={sig.id}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 8,
                    background: 'rgba(239,68,68,0.06)',
                    border: '1px solid rgba(239,68,68,0.15)',
                  }}
                >
                  <div style={{ fontSize: 11, color: '#dc2626', fontWeight: 600 }}>
                    {sig.type}
                  </div>
                  <div style={{ fontSize: 11, color: '#5c5a74', marginTop: 2 }}>
                    {sig.message}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 파이프라인 제어 */}
        <div style={CARD_BASE}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#2d2b3d', marginBottom: 12 }}>
            파이프라인 제어
          </h3>
          <button
            onClick={triggerRun}
            disabled={triggering}
            style={{
              width: '100%',
              padding: '9px 16px',
              borderRadius: 8,
              border: 'none',
              background: triggering ? '#c0bdd8' : '#8785A2',
              color: '#ffffff',
              fontSize: 13,
              fontWeight: 600,
              cursor: triggering ? 'not-allowed' : 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!triggering) {
                e.currentTarget.style.transform = 'translateY(-1px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(135,133,162,0.35)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            {triggering ? '실행 중...' : '테스트 런 실행'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 빌드 성공

- [ ] **Step 3: commit**

```bash
git add web/app/home-ops-tab.tsx
git commit -m "feat: 운영 탭 — 파이프라인 스텝 현황 + HITL 신호 3초 폴링"
```

---

## Task 7: page.tsx — KPI 배너 + 탭 구조 재작성

**Files:**
- Modify: `web/app/page.tsx`

- [ ] **Step 1: page.tsx 전체를 아래 내용으로 교체**

기존 KPI 카드 6개 + 채널 도트 레이아웃을 제거. KpiBanner + HomeExecTab 구조로 교체. `fetchData()`, `countTotalRuns()`, `countHitlPending()`, `MOCK_CHANNELS`는 동일하게 유지.

```tsx
import { createClient } from '@/lib/supabase/server'
import type { Channel } from '@/lib/types'
import { readKasJson, getKasRoot } from '@/lib/fs-helpers'
import fs from 'fs/promises'
import path from 'path'
import type { HitlSignal } from '@/lib/fs-helpers'
import { KpiBanner } from '@/components/kpi-banner'
import HomeExecTab from './home-exec-tab'

const MOCK_CHANNELS: Channel[] = [
  { id: 'CH1', category: 'economy',     category_ko: '경제',    youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH2', category: 'realestate',  category_ko: '부동산',  youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH3', category: 'psychology',  category_ko: '심리',    youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH4', category: 'mystery',     category_ko: '미스터리', youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH5', category: 'war_history', category_ko: '전쟁사',  youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH6', category: 'science',     category_ko: '과학',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH7', category: 'history',     category_ko: '역사',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
]

async function countTotalRuns(): Promise<number> {
  const kasRoot = getKasRoot()
  const runsDir = path.join(kasRoot, 'runs')
  let count = 0
  try {
    const channels = await fs.readdir(runsDir)
    for (const ch of channels) {
      const chDir = path.join(runsDir, ch)
      try {
        const stat = await fs.stat(chDir)
        if (!stat.isDirectory()) continue
        const runs = await fs.readdir(chDir)
        count += runs.filter((r) => r.startsWith('run_')).length
      } catch { /* 빈 채널 무시 */ }
    }
  } catch { /* runs/ 없음 */ }
  return count
}

async function countHitlPending(): Promise<number> {
  const signals = await readKasJson<HitlSignal[]>('data/global/notifications/hitl_signals.json')
  if (!Array.isArray(signals)) return 0
  return signals.filter((s) => !s.resolved).length
}

async function fetchData() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  const [totalRuns, hitlPending] = await Promise.all([
    countTotalRuns(),
    countHitlPending(),
  ])

  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) {
    return { channels: MOCK_CHANNELS, totalRuns, hitlPending }
  }

  try {
    const supabase = await createClient()
    const { data: channels } = await supabase.from('channels').select('*').order('id')
    return {
      channels: (channels ?? MOCK_CHANNELS) as Channel[],
      totalRuns,
      hitlPending,
    }
  } catch {
    return { channels: MOCK_CHANNELS, totalRuns, hitlPending }
  }
}

export default async function HomePage() {
  const { channels, totalRuns, hitlPending } = await fetchData()

  // launch_phase === 1 이 파이프라인 SSOT (pipeline.py get_active_channels 기준)
  const activeChannelCount = channels.filter((ch) => ch.launch_phase === 1).length
  const totalRevenue = 0   // Supabase revenue_monthly 미연동 시 mock 0
  const achievementRate = totalRevenue > 0 ? (totalRevenue / 14_000_000) * 100 : 0

  return (
    <div>
      {/* KPI 배너 — 항상 고정 */}
      <KpiBanner
        revenue={totalRevenue}
        achievementRate={achievementRate}
        activeChannels={activeChannelCount}
        totalChannels={channels.length}
        totalRuns={totalRuns}
        hitlPending={hitlPending}
      />

      {/* 탭 컨트롤러 + 탭 콘텐츠 (경영/운영) */}
      <HomeExecTab
        channels={channels}
        totalRuns={totalRuns}
        activeChannelCount={activeChannelCount}
      />
    </div>
  )
}
```

- [ ] **Step 2: 빌드 검증**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` (0 errors, 0 TypeScript 오류)

- [ ] **Step 3: 개발 서버 기능 확인**

```bash
cd web && npm run dev
```

http://localhost:7002 접속 후 체크리스트:
- [ ] 배경: 라일락→연핑크→라이트그레이 그라디언트
- [ ] 왼쪽 사이드바: 44px 아이콘 전용 → 토글 버튼 클릭 시 160px로 확장 + 라벨 나타남
- [ ] 상단 탑바: 퍼플 글래스모피즘 "KAS Studio · LIVE 뱃지"
- [ ] KPI 배너: 연핑크 글래스 배경, 이번달 수익/달성률/활성 채널/총 Runs/HITL 5개 항목
- [ ] 경영/운영 탭 버튼: 아이콘+라벨, 활성 시 퍼플 배경
- [ ] 경영 탭: KPI 카드 4개 (호버 시 lift), 진행 바, 6개월 바 차트, 채널 카드 7개 (CH1/CH2 활성, 나머지 35% opacity)
- [ ] 운영 탭: Step05~12 현황, HITL 신호, 테스트 런 버튼

- [ ] **Step 4: commit**

```bash
git add web/app/page.tsx
git commit -m "feat: 홈 페이지 KPI 배너 + 경영/운영 듀얼 뷰 탭 구조 완성"
```

---

## 셀프 리뷰 체크리스트

스펙(`2026-04-08-dashboard-dual-view-redesign.md`)과의 커버리지:

| 스펙 요구사항 | 구현 태스크 |
|---|---|
| Pink Glassmorphism 팔레트 (--p1~--p4, --t1~--t3) | Task 1 |
| Noto Sans KR 폰트 교체 | Task 1, 3 |
| 접이식 사이드바 (44px ↔ 160px) | Task 2 |
| ChevronsRight 토글 버튼 | Task 2 |
| 탑바 퍼플 글래스모피즘 | Task 3 |
| KPI 배너 (연핑크 배경, 5개 항목) | Task 4 |
| 경영 탭 KPI 카드 4개 | Task 5 |
| 채널별 목표 진행 바 | Task 5 |
| 6개월 추이 차트 (CSS flex, mock) | Task 5 |
| 채널 카드 7개 그리드 (활성/비활성) | Task 5 |
| 운영 탭 Step05~12 스텝 현황 | Task 6 |
| HITL 신호 표시 | Task 6 |
| 3초 폴링 (탭 활성 시만) | Task 6 |
| 테스트 런 버튼 → /api/pipeline/trigger | Task 6 |
| page.tsx 서버 컴포넌트 유지 | Task 7 |
| launch_phase === 1 SSOT | Task 7 |
| backdrop-filter 폴백 | Task 1 (`@supports not`) |
| 하위 호환 alias (--c-dark 등) | Task 1 |
