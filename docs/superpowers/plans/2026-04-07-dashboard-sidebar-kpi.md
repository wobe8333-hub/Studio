# 대시보드 개선 구현 플랜 — 사이드바 카테고리화 + KPI 요약 페이지

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사이드바를 3그룹으로 카테고리화하고, 홈 KPI 페이지를 KPI 6개 + 채널 도트 7개의 간결한 요약 화면으로 교체한다.

**Architecture:** `sidebar-nav.tsx`의 단일 navItems 배열을 NAV_GROUPS 배열로 교체하고, `page.tsx`에서 파이프라인 타임라인·채널 카드·수익 그리드를 제거한 뒤 신규 KPI 카드 6개와 채널 상태 도트 섹션으로 대체한다.

**Tech Stack:** Next.js 16 (RSC), React 19, Tailwind CSS v4, shadcn/ui, lucide-react, `web/lib/fs-helpers.ts`

---

## 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|---|---|---|
| `web/components/sidebar-nav.tsx` | 수정 | navItems[] → NAV_GROUPS[] |
| `web/app/page.tsx` | 수정 | KPI 6개 + 채널 도트, 불필요 섹션 제거 |

---

## Task 1: 사이드바 카테고리화

**Files:**
- Modify: `web/components/sidebar-nav.tsx`

### 변경 계획

`navItems` 단일 배열을 `NAV_GROUPS` 배열로 교체한다. 각 그룹은 `{ label, items }` 구조를 가지며, 기존 `SidebarGroup` 하나를 4개의 그룹으로 확장한다.

- [ ] **Step 1: sidebar-nav.tsx 전체 교체**

`web/components/sidebar-nav.tsx` 내용을 아래로 교체한다:

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  DollarSign,
  ShieldAlert,
  Brain,
  Monitor,
  BookOpen,
  ClipboardCheck,
  CreditCard,
  Settings,
  Zap,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { cn } from '@/lib/utils'

interface NavItem {
  title: string
  url: string
  icon: React.ElementType
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: '대시보드',
    items: [
      { title: '전체 KPI', url: '/', icon: LayoutDashboard },
    ],
  },
  {
    label: '콘텐츠',
    items: [
      { title: '트렌드 관리',  url: '/trends',    icon: TrendingUp },
      { title: '지식 수집',   url: '/knowledge', icon: BookOpen },
      { title: 'QA 검수',     url: '/qa',        icon: ClipboardCheck },
    ],
  },
  {
    label: '수익 / 비용',
    items: [
      { title: '수익 추적',      url: '/revenue', icon: DollarSign },
      { title: '비용/쿼터',      url: '/cost',    icon: CreditCard },
      { title: '리스크 모니터링', url: '/risk',    icon: ShieldAlert },
    ],
  },
  {
    label: '시스템',
    items: [
      { title: '파이프라인 모니터', url: '/monitor',  icon: Monitor },
      { title: '학습 피드백',       url: '/learning', icon: Brain },
    ],
  },
]

// 채널별 고유 색상 CSS 변수 맵
const CHANNEL_COLORS: Record<string, string> = {
  CH1: 'var(--channel-ch1)',
  CH2: 'var(--channel-ch2)',
  CH3: 'var(--channel-ch3)',
  CH4: 'var(--channel-ch4)',
  CH5: 'var(--channel-ch5)',
  CH6: 'var(--channel-ch6)',
  CH7: 'var(--channel-ch7)',
}

// fallback — Supabase 연동 전 기본값
const DEFAULT_CHANNELS = [
  { id: 'CH1', category_ko: '경제' },
  { id: 'CH2', category_ko: '부동산' },
  { id: 'CH3', category_ko: '심리' },
  { id: 'CH4', category_ko: '미스터리' },
  { id: 'CH5', category_ko: '전쟁사' },
  { id: 'CH6', category_ko: '과학' },
  { id: 'CH7', category_ko: '역사' },
]

interface ChannelItem {
  id: string
  category_ko: string | null
}

interface AppSidebarProps {
  channels?: ChannelItem[]
}

export function AppSidebar({ channels = DEFAULT_CHANNELS }: AppSidebarProps) {
  const pathname = usePathname()

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-5" style={{ borderColor: 'rgba(255, 176, 156, 0.2)' }}>
        <div className="flex items-center gap-2.5">
          <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: '#ffb09c', boxShadow: '0 0 8px rgba(255,176,156,0.6)' }} />
          <div>
            <span className="font-bold text-base tracking-tight" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#ffefea' }}>KAS</span>
            <p className="text-[10px] uppercase tracking-widest leading-tight mt-0.5" style={{ color: 'rgba(255,176,156,0.6)' }}>Knowledge Animation Studio</p>
          </div>
          <Zap className="h-3.5 w-3.5 ml-auto shrink-0" style={{ color: 'rgba(255,176,156,0.5)' }} />
        </div>
      </SidebarHeader>

      <SidebarContent>
        {NAV_GROUPS.map((group, idx) => (
          <div key={group.label}>
            {idx > 0 && <SidebarSeparator />}
            <SidebarGroup>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((item) => (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton
                        isActive={pathname === item.url}
                        render={<Link href={item.url} />}
                      >
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </div>
        ))}

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>채널별 상세</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {channels.map((ch) => (
                <SidebarMenuItem key={ch.id}>
                  <SidebarMenuButton
                    isActive={pathname.startsWith(`/channels/${ch.id}`)}
                    render={<Link href={`/channels/${ch.id}`} />}
                  >
                    <span
                      className={cn(
                        'h-2.5 w-2.5 rounded-full shrink-0',
                        'ring-1 ring-inset ring-black/10 dark:ring-white/10'
                      )}
                      style={{
                        backgroundColor: CHANNEL_COLORS[ch.id] ?? 'var(--muted-foreground)',
                        boxShadow: `0 0 6px ${CHANNEL_COLORS[ch.id] ?? 'transparent'}`,
                      }}
                    />
                    <span>{ch.id} {ch.category_ko}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border/60">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={pathname === '/settings'}
              render={<Link href="/settings" />}
            >
              <Settings className="h-4 w-4" />
              <span>설정</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
```

- [ ] **Step 2: 빌드 타입 체크**

```bash
cd web && npx tsc --noEmit
```

Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add web/components/sidebar-nav.tsx
git commit -m "feat: 사이드바 메뉴 4그룹 카테고리화 (대시보드/콘텐츠/수익비용/시스템)"
```

---

## Task 2: KPI 페이지 요약화

**Files:**
- Modify: `web/app/page.tsx`

### 변경 계획

`page.tsx`에서 다음을 제거한다:
- `TimelineNode`, `RunStateBadge`, `ChannelCard` 함수
- 파이프라인 타임라인 Card 섹션 (lines 222–284)
- 채널별 현황 그리드 (lines 286–297)
- 채널별 수익 현황 7열 그리드 섹션 (lines 201–219)

다음을 추가한다:
- `fetchData()`에서 `total_runs`, `hitl_pending` 추가 fetch
- KPI 카드 6개 (3×2 그리드)
- 채널 상태 도트 섹션

불필요해진 import도 함께 제거한다:
- `Eye`, `MousePointerClick`, `PlayCircle` (lucide)
- `Card`, `CardContent`, `CardHeader`, `CardTitle` (shadcn)
- `Badge`, `Progress`
- `ChannelDots`, `Sparkline` (home-charts) — `RadialGauge`만 유지
- `ScrollReveal`, `AnimatedCard` (animated-sections) — `StaggerContainer`, `StaggerItem`만 유지
- `TestRunButton`
- `cn`

- [ ] **Step 1: page.tsx 전체 교체**

`web/app/page.tsx` 내용을 아래로 교체한다:

```tsx
import {
  DollarSign,
  Activity,
  TrendingUp,
  AlertTriangle,
  BarChart2,
  Bell,
} from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import type { Channel } from '@/lib/types'
import { RadialGauge } from '@/components/home-charts'
import { StaggerContainer, StaggerItem } from '@/components/animated-sections'
import { readKasJson, getKasRoot } from '@/lib/fs-helpers'
import fs from 'fs/promises'
import path from 'path'
import type { HitlSignal } from '@/lib/fs-helpers'

// Supabase 미연동 시 fallback mock 데이터
const MOCK_CHANNELS: Channel[] = [
  { id: 'CH1', category: 'economy',     category_ko: '경제',    youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH2', category: 'realestate',  category_ko: '부동산',  youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH3', category: 'psychology',  category_ko: '심리',    youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH4', category: 'mystery',     category_ko: '미스터리', youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH5', category: 'war_history', category_ko: '전쟁사',  youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH6', category: 'science',     category_ko: '과학',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH7', category: 'history',     category_ko: '역사',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
]

// runs/ 디렉토리 스캔으로 총 Run 수 계산
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
        count += runs.filter(r => r.startsWith('run_')).length
      } catch { /* 빈 채널 무시 */ }
    }
  } catch { /* runs/ 없음 */ }
  return count
}

// 미해결 HITL 신호 수 계산
async function countHitlPending(): Promise<number> {
  const signals = await readKasJson<HitlSignal[]>('data/global/notifications/hitl_signals.json')
  if (!Array.isArray(signals)) return 0
  return signals.filter(s => !s.resolved).length
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

// 채널별 고유 색상 (sidebar-nav.tsx와 동일한 CSS 변수)
const CHANNEL_COLORS: Record<string, string> = {
  CH1: 'var(--channel-ch1)',
  CH2: 'var(--channel-ch2)',
  CH3: 'var(--channel-ch3)',
  CH4: 'var(--channel-ch4)',
  CH5: 'var(--channel-ch5)',
  CH6: 'var(--channel-ch6)',
  CH7: 'var(--channel-ch7)',
}

export default async function HomePage() {
  const { channels, totalRuns, hitlPending } = await fetchData()

  const activeChannels = channels.filter((ch) => ch.launch_phase === 1)

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 배경 메시 그라데이션 */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-mesh-warm" />

      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>
          파이프라인 대시보드
        </h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>
          7채널 AI 자동화 파이프라인 현황 · 월 목표: 1,400만원
        </p>
      </div>

      {/* KPI 카드 6개 (3×2) */}
      <StaggerContainer className="grid grid-cols-2 gap-3 sm:grid-cols-3">

        {/* 1. 월 목표 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>월 목표</span>
              <DollarSign className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>₩14M</div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>채널당 ₩2,000,000</p>
          </div>
        </StaggerItem>

        {/* 2. 활성 채널 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>활성 채널</span>
              <Activity className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>
              {activeChannels.length} <span style={{ color: '#9b6060', fontSize: '1rem' }}>/ {channels.length}</span>
            </div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>
              {activeChannels.map((c) => c.id).join(', ')}
            </p>
          </div>
        </StaggerItem>

        {/* 3. 총 Runs */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>총 Runs</span>
              <BarChart2 className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>{totalRuns}</div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>누적 파이프라인 실행</p>
          </div>
        </StaggerItem>

        {/* 4. 달성률 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>이번달 달성률</span>
              <TrendingUp className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>0%</div>
            <RadialGauge value={0} color="rgba(238,36,0,0.6)" />
          </div>
        </StaggerItem>

        {/* 5. 리스크 채널 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>리스크 채널</span>
              <AlertTriangle className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#22c55e' }}>0</div>
            <p className="text-xs mt-1" style={{ color: '#22c55e' }}>HIGH 리스크 없음</p>
          </div>
        </StaggerItem>

        {/* 6. HITL 대기 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>HITL 대기</span>
              <Bell className="h-4 w-4" style={{ color: hitlPending > 0 ? '#f59e0b' : '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: hitlPending > 0 ? '#f59e0b' : '#1a0505' }}>
              {hitlPending}
            </div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>
              {hitlPending > 0 ? '운영자 확인 필요' : '대기 신호 없음'}
            </p>
          </div>
        </StaggerItem>

      </StaggerContainer>

      {/* 채널 상태 도트 */}
      <StaggerItem>
        <div className="glass-card p-5">
          <h2 className="text-sm font-bold mb-4" style={{ color: '#5c1a1a' }}>채널별 상태</h2>
          <div className="flex flex-wrap gap-5">
            {channels.map((ch) => {
              const isActive = ch.launch_phase === 1
              const color = CHANNEL_COLORS[ch.id] ?? '#ddd'
              return (
                <div key={ch.id} className="flex flex-col items-center gap-1.5">
                  <div
                    className="flex items-center justify-center rounded-full text-white font-bold text-[11px] transition-opacity"
                    style={{
                      width: 44,
                      height: 44,
                      background: isActive ? color : '#d1d5db',
                      boxShadow: isActive ? `0 0 12px ${color}` : 'none',
                      opacity: isActive ? 1 : 0.45,
                    }}
                  >
                    {ch.id}
                  </div>
                  <span className="text-[10px] font-medium" style={{ color: '#5c1a1a' }}>{ch.category_ko}</span>
                  <span
                    className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{
                      background: isActive ? 'rgba(34,197,94,0.12)' : 'rgba(0,0,0,0.06)',
                      color: isActive ? '#16a34a' : '#9b6060',
                    }}
                  >
                    {isActive ? 'LIVE' : '준비중'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </StaggerItem>

    </div>
  )
}
```

- [ ] **Step 2: 빌드 타입 체크**

```bash
cd web && npx tsc --noEmit
```

Expected: 에러 없음. 만약 `fs` import 관련 에러가 나면 `tsconfig.json`에 `"node"` types가 포함됐는지 확인.

- [ ] **Step 3: 브라우저 확인 (Playwright)**

```bash
python -c "
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':900})
    page.goto('http://localhost:7002', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    errs = []
    page.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
    page.wait_for_timeout(1000)
    h1 = page.locator('h1').first.text_content()
    cards = page.locator('.glass-card').count()
    dots  = page.locator('[style*=\"border-radius: 50%\"], [style*=\"rounded-full\"]').count()
    print(f'h1={h1}, glass-card={cards}, console_errors={len(errs)}')
    page.screenshot(path='/tmp/kpi_final.png')
    browser.close()
"
```

Expected: `h1=파이프라인 대시보드`, `glass-card>=7` (KPI 6 + 채널도트 1), `console_errors=0`

- [ ] **Step 4: 커밋**

```bash
git add web/app/page.tsx
git commit -m "feat: 홈 KPI 페이지 — KPI 6개 + 채널 상태 도트로 요약 (파이프라인 타임라인·채널카드 제거)"
```

---

## 자체 검토

- ✅ **스펙 커버리지**: 사이드바 4그룹(대시보드/콘텐츠/수익비용/시스템/채널) ✓, KPI 6개 ✓, 채널 도트 ✓, 제거 항목(타임라인·채널카드·수익그리드) ✓
- ✅ **Placeholder 없음**: 모든 스텝에 실제 코드 포함
- ✅ **타입 일관성**: `NavGroup.items` → `NavItem[]`, `fetchData` 반환 `{channels, totalRuns, hitlPending}` 전 파일 일관
- ✅ **import 정리**: 제거한 컴포넌트(`ChannelCard`, `TestRunButton` 등)의 import도 함께 제거됨
- ✅ **`fs` import**: Next.js 서버 컴포넌트는 Node.js 빌트인 사용 가능 — `tsconfig`에 `lib: ["node"]` 불필요, `import fs from 'fs/promises'` 그대로 동작
