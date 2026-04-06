# KAS 대시보드 전면 재설계 + 검증 기능 통합 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KAS 파이프라인 테스트 검증을 위한 23개 항목 완전 커버 + Red Light Glassmorphism 대시보드 전면 재설계

**Architecture:** Red Light 팔레트(#900000~#ffefea) + 글래스모피즘 카드 + A+B 하이브리드 검증 워크플로우(실시간 관찰 → 완료 후 검수). globals.css CSS 변수 교체 → 사이드바/레이아웃 → 핵심 검증 페이지(/monitor, /runs) → 보조 강화 페이지 순서로 구현.

**Tech Stack:** Next.js 15 App Router, Tailwind CSS v4 (CSS-first), shadcn/ui v4, Supabase Realtime, Google Fonts (Libre Baskerville + M PLUS Rounded 1c), HTML5 audio/video

---

## 파일 구조

### 수정 파일
- `web/app/globals.css` — Red Light 팔레트 + 폰트 변수 교체
- `web/app/layout.tsx` — 폰트 적용 + 헤더 업데이트
- `web/components/sidebar-nav.tsx` — Red Light 다크 사이드바
- `web/app/page.tsx` — 홈 KPI + 테스트 런 버튼 + 채널 수익 탭
- `web/components/home-charts.tsx` — Red Light 색상 반영
- `web/app/monitor/page.tsx` — 5개 탭 구조 (Step/미리보기/Manim/HITL/Sub-Agent)
- `web/app/runs/[channelId]/[runId]/page.tsx` — 10개 탭 검수 허브
- `web/app/knowledge/page.tsx` — 수집 단계 + 팩트체크 강화
- `web/app/trends/page.tsx` — 점수 구성 시각화 + 소스 배지
- `web/app/cost/page.tsx` — 예측 vs 실제 탭 + 이연 업로드 탭
- `web/app/learning/page.tsx` — KPI 48h + 알고리즘 단계 + 바이어스 탭
- `web/app/revenue/page.tsx` — 월별 추세 탭
- `web/app/risk/page.tsx` — 지속성 분석 탭
- `web/app/qa/page.tsx` — 스타일 전환
- `web/app/settings/page.tsx` — 스타일 전환
- `web/app/channels/[id]/page.tsx` — 스타일 전환

### 신규 파일
- `web/app/api/pipeline/steps/route.ts` — Step별 진행 상태 + 소요시간
- `web/app/api/runs/[channelId]/[runId]/shorts/route.ts` — Shorts 3편 메타
- `web/app/api/runs/[channelId]/[runId]/bgm/route.ts` — BGM 경로 + tone
- `web/app/api/runs/[channelId]/[runId]/seo/route.ts` — SEO 메타 GET/PATCH
- `web/app/api/cost/projection/route.ts` — pre_cost_estimator 결과
- `web/app/api/agents/status/route.ts` — Sub-Agent 4종 실행 결과
- `web/app/api/learning/kpi/route.ts` — KPI 48h 수집 결과
- `web/app/api/learning/algorithm/route.ts` — 알고리즘 단계 승격 이력
- `web/app/api/sustainability/route.ts` — 주제 지속성 분석

---

## Task 1: globals.css — Red Light 팔레트 + 폰트 교체

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: Google Fonts import 추가 및 폰트 변수 교체**

`globals.css` 최상단 `@import "tailwindcss";` 바로 아래에 추가:

```css
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Mplus+Rounded+1c:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');
```

`@theme inline { }` 블록 내 폰트 관련 변수를 다음으로 교체:

```css
--font-sans: 'Mplus Rounded 1c', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'DM Mono', 'Consolas', monospace;
--font-heading: 'Libre Baskerville', Georgia, serif;
```

- [ ] **Step 2: @theme inline 블록에 Red Light 색상 변수 추가**

`@theme inline { }` 블록 내 기존 `--color-primary` 계열을 다음으로 교체:

```css
/* Red Light Palette */
--color-red-dark:   oklch(0.30 0.20 25);   /* #900000 */
--color-red-bright: oklch(0.55 0.25 25);   /* #ee2400 */
--color-salmon:     oklch(0.80 0.10 25);   /* #ffb09c */
--color-blush:      oklch(0.91 0.04 20);   /* #fbd9d3 */
--color-cream:      oklch(0.97 0.02 18);   /* #ffefea */

/* 텍스트 — 가독성 우선 */
--color-text-primary:   oklch(0.18 0.08 25);  /* #1a0505 */
--color-text-secondary: oklch(0.35 0.12 25);  /* #5c1a1a */
--color-text-muted:     oklch(0.60 0.07 25);  /* #9b6060 */

/* shadcn/ui 호환 — 라이트 모드 */
--color-background: oklch(0.97 0.02 18);   /* cream */
--color-foreground: oklch(0.18 0.08 25);   /* text-primary */
--color-primary:    oklch(0.55 0.25 25);   /* red-bright */
--color-primary-foreground: oklch(1 0 0);
--color-muted:      oklch(0.91 0.04 20);   /* blush */
--color-muted-foreground: oklch(0.60 0.07 25);
--color-border:     oklch(0.88 0.06 20);
--color-card:       oklch(0.98 0.01 18);
--color-card-foreground: oklch(0.18 0.08 25);
```

- [ ] **Step 3: :root 블록 업데이트**

기존 `:root { }` 블록을 다음으로 교체:

```css
:root {
  --background: oklch(0.97 0.02 18);
  --foreground: oklch(0.18 0.08 25);
  --card: rgba(255, 255, 255, 0.55);
  --card-foreground: oklch(0.18 0.08 25);
  --primary: oklch(0.55 0.25 25);
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.91 0.04 20);
  --secondary-foreground: oklch(0.35 0.12 25);
  --muted: oklch(0.93 0.03 18);
  --muted-foreground: oklch(0.60 0.07 25);
  --accent: oklch(0.80 0.10 25);
  --accent-foreground: oklch(0.18 0.08 25);
  --destructive: oklch(0.55 0.25 25);
  --border: rgba(238, 36, 0, 0.12);
  --input: rgba(238, 36, 0, 0.08);
  --ring: oklch(0.55 0.25 25);
  --radius: 0.75rem;
  --sidebar: rgba(144, 0, 0, 0.88);
  --sidebar-foreground: oklch(0.97 0.02 18);
  --sidebar-primary: oklch(0.55 0.25 25);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: rgba(255, 176, 156, 0.15);
  --sidebar-accent-foreground: oklch(0.97 0.02 18);
  --sidebar-border: rgba(255, 176, 156, 0.15);
  --sidebar-ring: oklch(0.80 0.10 25);
}
```

- [ ] **Step 4: body 배경 + 글래스 유틸리티 추가**

기존 `body { }` 블록 교체 및 `@layer utilities` 블록에 추가:

```css
body {
  background: linear-gradient(135deg, #fbd9d3 0%, #ffefea 55%, #ffd9cc 100%);
  background-attachment: fixed;
  font-family: var(--font-sans);
  color: var(--foreground);
}

@layer utilities {
  .glass-card {
    background: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(238, 36, 0, 0.12);
    border-radius: 1rem;
    box-shadow: 0 8px 32px rgba(144, 0, 0, 0.08);
  }
  .glass-card-hover {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .glass-card-hover:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 40px rgba(144, 0, 0, 0.12);
  }
  .heading-font {
    font-family: var(--font-heading);
  }
  .text-red-accent {
    color: oklch(0.30 0.20 25); /* #900000 */
  }
  .bg-red-glass {
    background: rgba(144, 0, 0, 0.88);
    backdrop-filter: blur(20px);
  }
}
```

- [ ] **Step 5: 개발 서버 확인**

```bash
cd web && npm run dev
```

브라우저에서 http://localhost:3000 열기. 배경이 크림색 그라디언트로 바뀌고 폰트가 변경되면 성공.

- [ ] **Step 6: 커밋**

```bash
cd web && git add app/globals.css
git commit -m "feat: Red Light 팔레트 + Libre Baskerville + M PLUS Rounded 1c 폰트 적용"
```

---

## Task 2: layout.tsx + 사이드바 Red Light 적용

**Files:**
- Modify: `web/app/layout.tsx`
- Modify: `web/components/sidebar-nav.tsx`

- [ ] **Step 1: layout.tsx — next/font 제거, 변수 적용**

`web/app/layout.tsx`에서 `Geist`, `Sora` 등 `next/font` import를 제거하고, `body` className을 단순화:

```tsx
// 폰트 import 제거 (Google Fonts는 globals.css에서 처리)
// 기존: const geist = Geist({ subsets: ['latin'] }) 등 제거

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const channels = await fetchChannels()

  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <SidebarProvider>
            <AppSidebar channels={channels} />
            <div className="flex flex-1 flex-col">
              <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b border-red-100/50 px-6"
                style={{ background: 'rgba(255,239,234,0.8)', backdropFilter: 'blur(12px)' }}>
                <SidebarTrigger className="text-[#5c1a1a]" />
                <div className="flex-1" />
                <ThemeToggle />
              </header>
              <main className="flex-1 p-6">{children}</main>
            </div>
          </SidebarProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: sidebar-nav.tsx — Red Light 사이드바 스타일 적용**

`web/components/sidebar-nav.tsx`의 `AppSidebar` 컴포넌트에서 shadcn `Sidebar` 관련 className을 업데이트:

```tsx
// SidebarHeader 영역 — 로고
<SidebarHeader className="border-b border-white/10 px-4 py-5">
  <div className="flex items-center gap-2">
    <div className="h-2 w-2 rounded-full bg-[#ffb09c] shadow-[0_0_8px_rgba(255,176,156,0.6)]" />
    <span className="heading-font text-xl font-bold text-[#ffefea]">KAS</span>
  </div>
  <p className="mt-1 text-[10px] uppercase tracking-widest text-[#ffb09c]/60">
    Knowledge Animation Studio
  </p>
</SidebarHeader>

// SidebarMenu 아이템 — active 상태
<SidebarMenuButton
  asChild
  isActive={pathname === item.url}
  className="text-[#ffefea]/70 hover:bg-white/10 hover:text-[#ffefea]
             data-[active=true]:bg-white/15 data-[active=true]:text-[#ffefea]
             data-[active=true]:font-semibold"
>
```

- [ ] **Step 3: 채널 dot 색상 Red Light 계열로 업데이트**

`CHANNEL_COLORS` 상수를 Red Light 팔레트 기반으로 업데이트:

```tsx
const CHANNEL_COLORS: Record<string, string> = {
  CH1: '#ee2400',  // 브라이트 레드
  CH2: '#ffb09c',  // 살몬
  CH3: '#fbd9d3',  // 블러쉬
  CH4: '#900000',  // 다크 레드
  CH5: '#d4464a',  // 미디엄 레드
  CH6: '#f07060',  // 코럴
  CH7: '#c03020',  // 딥 코럴
}
```

- [ ] **Step 4: 빌드 타입 체크**

```bash
cd web && npm run build 2>&1 | tail -20
```

TypeScript 에러 없으면 성공.

- [ ] **Step 5: 커밋**

```bash
git add app/layout.tsx components/sidebar-nav.tsx
git commit -m "feat: Red Light 사이드바 + 레이아웃 폰트 적용"
```

---

## Task 3: 홈 페이지 재설계

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/components/home-charts.tsx`

- [ ] **Step 1: page.tsx — 상단 헤더 + 테스트 런 버튼 추가**

`web/app/page.tsx` 최상단 서버 컴포넌트 부분에서 헤더 섹션 수정:

```tsx
// 페이지 헤더
<div className="mb-6 flex items-start justify-between">
  <div>
    <h1 className="heading-font text-2xl font-bold text-[#1a0505]">
      파이프라인 대시보드
    </h1>
    <p className="mt-1 text-sm text-[#9b6060]">
      {new Date().getFullYear()}년 {new Date().getMonth() + 1}월 · 7채널 자동화 현황
    </p>
  </div>
  <div className="flex gap-3">
    <a href="/monitor"
      className="glass-card glass-card-hover flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#5c1a1a]">
      📋 전체 Run 내역
    </a>
    <TestRunButton />
  </div>
</div>
```

- [ ] **Step 2: TestRunButton 클라이언트 컴포넌트 생성**

`web/components/test-run-button.tsx` 신규 파일 생성:

```tsx
'use client'
import { useState } from 'react'

export function TestRunButton() {
  const [loading, setLoading] = useState(false)
  const [channelId, setChannelId] = useState('CH1')

  async function handleClick() {
    setLoading(true)
    try {
      await fetch('/api/pipeline/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ month_number: 1 }),
      })
      window.location.href = '/monitor'
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={channelId}
        onChange={e => setChannelId(e.target.value)}
        className="glass-card rounded-lg px-3 py-2 text-sm text-[#5c1a1a] outline-none"
      >
        {['CH1','CH2','CH3','CH4','CH5','CH6','CH7'].map(ch => (
          <option key={ch} value={ch}>{ch}</option>
        ))}
      </select>
      <button
        onClick={handleClick}
        disabled={loading}
        className="flex items-center gap-2 rounded-xl bg-[#ee2400] px-5 py-2 text-sm font-bold text-white
                   shadow-[0_4px_14px_rgba(238,36,0,0.3)] transition hover:-translate-y-0.5
                   hover:bg-[#cc1e00] disabled:opacity-60"
      >
        {loading ? '실행 중...' : '▶ 테스트 런 실행'}
      </button>
    </div>
  )
}
```

- [ ] **Step 3: KPI 카드 glass-card 클래스 적용**

`page.tsx`의 KPI 카드 4개에 `glass-card glass-card-hover` className 추가. 수치는 `heading-font text-red-accent` 적용:

```tsx
<div className="glass-card glass-card-hover p-5">
  <p className="text-xs font-bold uppercase tracking-wider text-[#9b6060]">월 수익 목표</p>
  <p className="heading-font mt-2 text-3xl font-bold text-red-accent">
    ₩{(totalRevenue / 1_000_000).toFixed(1)}M
  </p>
  <p className="mt-1 text-xs text-[#9b6060]">목표 대비 {achievementRate}%</p>
  {/* 진행바 */}
  <div className="mt-3 h-1 rounded-full bg-red-100/50">
    <div className="h-1 rounded-full bg-gradient-to-r from-[#ee2400] to-[#ffb09c]"
         style={{ width: `${Math.min(achievementRate, 100)}%` }} />
  </div>
</div>
```

- [ ] **Step 4: 채널별 수익 탭 추가**

`page.tsx` 하단에 채널별 수익 섹션 추가 (shadcn Tabs 사용):

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// 채널별 수익 탭 — 클라이언트 컴포넌트로 분리
<ChannelRevenueTabs channels={channels} />
```

`web/components/channel-revenue-tabs.tsx` 신규:

```tsx
'use client'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface Channel { id: string; name: string; monthly_revenue?: number }

export function ChannelRevenueTabs({ channels }: { channels: Channel[] }) {
  const active = channels.filter(c => c.monthly_revenue != null)
  return (
    <div className="glass-card mt-4 overflow-hidden">
      <div className="border-b border-red-100/50 px-5 py-4">
        <h2 className="heading-font text-base font-bold text-[#1a0505]">채널별 수익 현황</h2>
      </div>
      <Tabs defaultValue={active[0]?.id ?? 'CH1'} className="p-4">
        <TabsList className="bg-red-50/50">
          {active.map(ch => (
            <TabsTrigger key={ch.id} value={ch.id}
              className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
              {ch.id}
            </TabsTrigger>
          ))}
        </TabsList>
        {active.map(ch => (
          <TabsContent key={ch.id} value={ch.id} className="mt-4">
            <p className="text-[#9b6060] text-xs">{ch.name}</p>
            <p className="heading-font text-2xl font-bold text-red-accent mt-1">
              ₩{((ch.monthly_revenue ?? 0) / 1_000_000).toFixed(1)}M
            </p>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
```

- [ ] **Step 5: 커밋**

```bash
git add app/page.tsx components/test-run-button.tsx components/channel-revenue-tabs.tsx components/home-charts.tsx
git commit -m "feat: 홈 페이지 Red Light 재설계 + 테스트 런 버튼 + 채널별 수익 탭"
```

---

## Task 4: API — /api/pipeline/steps (Step 진행 현황)

**Files:**
- Create: `web/app/api/pipeline/steps/route.ts`

- [ ] **Step 1: Step 상태 조회 API 작성**

`web/app/api/pipeline/steps/route.ts` 생성:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

interface StepInfo {
  step_id: string
  step_name: string
  status: 'done' | 'running' | 'pending' | 'failed' | 'skipped'
  started_at?: string
  finished_at?: string
  duration_ms?: number
  error?: string
}

interface StepProgressFile {
  run_id: string
  channel_id: string
  steps: StepInfo[]
  current_step?: string
  updated_at: string
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const channelId = searchParams.get('channel') ?? 'CH1'
  const runId = searchParams.get('run')

  const kasRoot = getKasRoot()

  // 진행 중인 Run 찾기
  let targetRunId = runId
  if (!targetRunId) {
    const manifestDir = path.join(kasRoot, 'runs', channelId)
    if (!fs.existsSync(manifestDir)) {
      return NextResponse.json({ steps: [], current_step: null })
    }
    const runs = fs.readdirSync(manifestDir)
      .filter(d => fs.existsSync(path.join(manifestDir, d, 'manifest.json')))
      .sort().reverse()

    for (const run of runs) {
      const manifest = JSON.parse(
        fs.readFileSync(path.join(manifestDir, run, 'manifest.json'), 'utf-8')
      )
      if (manifest.run_state === 'RUNNING') {
        targetRunId = run
        break
      }
    }
    if (!targetRunId) targetRunId = runs[0]
  }

  if (!targetRunId) return NextResponse.json({ steps: [], current_step: null })

  // step_progress.json 읽기 (파이프라인이 기록하는 파일)
  const progressPath = path.join(kasRoot, 'runs', channelId, targetRunId, 'step_progress.json')
  if (!fs.existsSync(progressPath)) {
    // step_progress.json 없으면 manifest에서 상태 추론
    const manifestPath = path.join(kasRoot, 'runs', channelId, targetRunId, 'manifest.json')
    if (!fs.existsSync(manifestPath)) return NextResponse.json({ steps: [], current_step: null })

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))
    const state = manifest.run_state ?? 'PENDING'

    // 기본 Step 목록 반환 (실제 진행 데이터 없을 때)
    const defaultSteps: StepInfo[] = [
      { step_id: 'step05', step_name: '트렌드 수집', status: state === 'COMPLETED' ? 'done' : 'pending' },
      { step_id: 'step06', step_name: '지식 수집', status: 'pending' },
      { step_id: 'step07', step_name: '알고리즘 정책', status: 'pending' },
      { step_id: 'step08', step_name: '영상 생성', status: 'pending' },
      { step_id: 'step08s', step_name: 'Shorts 생성', status: 'pending' },
      { step_id: 'step09', step_name: 'BGM 오버레이', status: 'pending' },
      { step_id: 'step10', step_name: '제목/썸네일', status: 'pending' },
      { step_id: 'step11', step_name: 'QA 검수', status: 'pending' },
      { step_id: 'step12', step_name: '업로드', status: 'pending' },
    ]
    return NextResponse.json({ steps: defaultSteps, run_id: targetRunId, current_step: null })
  }

  const progress: StepProgressFile = JSON.parse(fs.readFileSync(progressPath, 'utf-8'))
  return NextResponse.json({
    steps: progress.steps,
    run_id: targetRunId,
    current_step: progress.current_step ?? null,
    updated_at: progress.updated_at,
  })
}
```

- [ ] **Step 2: API 동작 확인**

개발 서버 실행 후:
```bash
curl "http://localhost:3000/api/pipeline/steps?channel=CH1"
```
Expected: `{ steps: [...], current_step: null, run_id: "..." }`

- [ ] **Step 3: 커밋**

```bash
git add app/api/pipeline/steps/route.ts
git commit -m "feat: Step 진행 현황 API 추가 (/api/pipeline/steps)"
```

---

## Task 5: API — Run 아티팩트 확장 (Shorts, BGM, SEO)

**Files:**
- Create: `web/app/api/runs/[channelId]/[runId]/shorts/route.ts`
- Create: `web/app/api/runs/[channelId]/[runId]/bgm/route.ts`
- Create: `web/app/api/runs/[channelId]/[runId]/seo/route.ts`

- [ ] **Step 1: Shorts API 작성**

`web/app/api/runs/[channelId]/[runId]/shorts/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()
  const shortsDir = path.join(kasRoot, 'runs', channelId, runId, 'step08_s')

  if (!fs.existsSync(shortsDir)) {
    return NextResponse.json({ shorts: [], available: false })
  }

  const mp4Files = fs.readdirSync(shortsDir)
    .filter(f => f.endsWith('.mp4'))
    .map((f, i) => ({
      index: i + 1,
      filename: f,
      url: `/api/artifacts/${channelId}/${runId}/step08_s/${f}`,
      duration_sec: 60,
    }))

  return NextResponse.json({ shorts: mp4Files, available: mp4Files.length > 0 })
}
```

- [ ] **Step 2: BGM API 작성**

`web/app/api/runs/[channelId]/[runId]/bgm/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()
  const step09Dir = path.join(kasRoot, 'runs', channelId, runId, 'step09')

  const bgmFiles = ['bgm_overlay.mp3', 'bgm.mp3', 'bgm_overlay.wav']
  let bgmUrl: string | null = null
  for (const f of bgmFiles) {
    if (fs.existsSync(path.join(step09Dir, f))) {
      bgmUrl = `/api/artifacts/${channelId}/${runId}/step09/${f}`
      break
    }
  }

  // render_report.json에서 BGM 메타데이터 읽기
  const reportPath = path.join(kasRoot, 'runs', channelId, runId, 'render_report.json')
  let meta: Record<string, unknown> = {}
  if (fs.existsSync(reportPath)) {
    const report = JSON.parse(fs.readFileSync(reportPath, 'utf-8'))
    meta = {
      bgm_used: report.bgm_used ?? false,
      bgm_source: report.bgm_source ?? null,
      bgm_category_tone: report.bgm_category_tone ?? null,
    }
  }

  return NextResponse.json({ bgm_url: bgmUrl, available: bgmUrl !== null, ...meta })
}
```

- [ ] **Step 3: SEO API 작성 (GET + PATCH)**

`web/app/api/runs/[channelId]/[runId]/seo/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }
function getSeoPath(kasRoot: string, channelId: string, runId: string) {
  return path.join(kasRoot, 'runs', channelId, runId, 'step08', 'metadata.json')
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const seoPath = getSeoPath(getKasRoot(), channelId, runId)
  if (!fs.existsSync(seoPath)) return NextResponse.json({ available: false })
  const data = JSON.parse(fs.readFileSync(seoPath, 'utf-8'))
  return NextResponse.json({ available: true, ...data })
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const seoPath = getSeoPath(getKasRoot(), channelId, runId)
  if (!fs.existsSync(seoPath)) return NextResponse.json({ ok: false, error: 'not found' }, { status: 404 })

  const body = await req.json()
  const existing = JSON.parse(fs.readFileSync(seoPath, 'utf-8'))
  const updated = { ...existing, ...body, updated_at: new Date().toISOString() }
  fs.writeFileSync(seoPath, JSON.stringify(updated, null, 2), 'utf-8')
  return NextResponse.json({ ok: true })
}
```

- [ ] **Step 4: 커밋**

```bash
git add app/api/runs/
git commit -m "feat: Shorts·BGM·SEO Run 아티팩트 API 추가"
```

---

## Task 6: API — 운영 데이터 (cost/projection, agents, learning, sustainability)

**Files:**
- Create: `web/app/api/cost/projection/route.ts`
- Create: `web/app/api/agents/status/route.ts`
- Create: `web/app/api/learning/kpi/route.ts`
- Create: `web/app/api/learning/algorithm/route.ts`
- Create: `web/app/api/sustainability/route.ts`

- [ ] **Step 1: 비용 예측 API**

`web/app/api/cost/projection/route.ts`:

```typescript
import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET() {
  const kasRoot = getKasRoot()
  // src/core/pre_cost_estimator.py가 저장하는 경로
  const projPath = path.join(kasRoot, 'data', 'global', 'cost_projection.json')
  if (!fs.existsSync(projPath)) return NextResponse.json({ available: false, projections: [] })

  const data = JSON.parse(fs.readFileSync(projPath, 'utf-8'))
  return NextResponse.json({ available: true, ...data })
}
```

- [ ] **Step 2: Sub-Agent 상태 API**

`web/app/api/agents/status/route.ts`:

```typescript
import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

const AGENT_LOGS = [
  { id: 'dev_maintenance', name: 'DevMaintenance', logFile: 'agent_dev_maintenance.json' },
  { id: 'analytics_learning', name: 'AnalyticsLearning', logFile: 'agent_analytics_learning.json' },
  { id: 'ui_ux', name: 'UiUx', logFile: 'agent_ui_ux.json' },
  { id: 'video_style', name: 'VideoStyle', logFile: 'agent_video_style.json' },
]

export async function GET() {
  const kasRoot = getKasRoot()
  const logsDir = path.join(kasRoot, 'data', 'global', 'agent_logs')

  const agents = AGENT_LOGS.map(agent => {
    const logPath = path.join(logsDir, agent.logFile)
    if (!fs.existsSync(logPath)) return { ...agent, available: false, last_run: null }
    const data = JSON.parse(fs.readFileSync(logPath, 'utf-8'))
    return { ...agent, available: true, last_run: data }
  })

  return NextResponse.json({ agents })
}
```

- [ ] **Step 3: KPI 48h + 알고리즘 단계 API**

`web/app/api/learning/kpi/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const channelId = searchParams.get('channel')
  const kasRoot = getKasRoot()

  const kpiDir = path.join(kasRoot, 'data', 'global', 'kpi_48h')
  if (!fs.existsSync(kpiDir)) return NextResponse.json({ records: [] })

  const files = fs.readdirSync(kpiDir)
    .filter(f => f.endsWith('.json') && (!channelId || f.includes(channelId)))
    .slice(-50) // 최근 50개

  const records = files.flatMap(f => {
    try { return [JSON.parse(fs.readFileSync(path.join(kpiDir, f), 'utf-8'))] }
    catch { return [] }
  })

  return NextResponse.json({ records })
}
```

`web/app/api/learning/algorithm/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const channelId = searchParams.get('channel') ?? 'CH1'
  const kasRoot = getKasRoot()

  const policyPath = path.join(kasRoot, 'data', 'channels', channelId, 'algorithm_policy.json')
  if (!fs.existsSync(policyPath)) return NextResponse.json({ available: false })

  const policy = JSON.parse(fs.readFileSync(policyPath, 'utf-8'))
  return NextResponse.json({
    available: true,
    current_stage: policy.algorithm_stage ?? 'PRE-ENTRY',
    stage_history: policy.stage_history ?? [],
    last_updated: policy.updated_at ?? null,
  })
}
```

`web/app/api/sustainability/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { glob } from 'glob'

function getKasRoot() { return process.env.KAS_ROOT ?? path.join(process.cwd(), '..') }

export async function GET(_req: NextRequest) {
  const kasRoot = getKasRoot()
  const pattern = path.join(kasRoot, 'data', 'global', 'sustainability_*.json')
  const files = glob.sync(pattern).sort().reverse()

  if (files.length === 0) return NextResponse.json({ available: false, channels: [] })

  const latest = JSON.parse(fs.readFileSync(files[0], 'utf-8'))
  return NextResponse.json({ available: true, ...latest })
}
```

- [ ] **Step 4: 커밋**

```bash
git add app/api/cost/ app/api/agents/ app/api/learning/ app/api/sustainability/
git commit -m "feat: 운영 데이터 API 5종 추가 (projection, agents, kpi, algorithm, sustainability)"
```

---

## Task 7: 파이프라인 모니터 재설계 (5개 탭)

**Files:**
- Modify: `web/app/monitor/page.tsx`

- [ ] **Step 1: 탭 구조로 리팩토링**

`web/app/monitor/page.tsx`를 5개 탭(Step 진행 / 실시간 미리보기 / Manim / HITL / Sub-Agent)으로 재구성:

```tsx
'use client'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function MonitorPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="heading-font text-2xl font-bold text-[#1a0505]">파이프라인 모니터</h1>
          <p className="mt-1 text-sm text-[#9b6060]">실시간 실행 현황 · 로그 · 검증 신호</p>
        </div>
      </div>

      {/* Preflight 패널 — 탭 위에 항상 표시 */}
      <PreflightPanel />

      <Tabs defaultValue="steps" className="space-y-4">
        <TabsList className="glass-card p-1">
          <TabsTrigger value="steps" className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
            📡 Step 진행
          </TabsTrigger>
          <TabsTrigger value="preview" className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
            🖼 실시간 미리보기
          </TabsTrigger>
          <TabsTrigger value="manim" className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
            🎞 Manim
          </TabsTrigger>
          <TabsTrigger value="hitl" className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
            🚨 HITL
          </TabsTrigger>
          <TabsTrigger value="agents" className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs">
            🤖 Sub-Agent
          </TabsTrigger>
        </TabsList>

        <TabsContent value="steps"><StepProgressPanel /></TabsContent>
        <TabsContent value="preview"><RealtimePreviewPanel /></TabsContent>
        <TabsContent value="manim"><ManímPanel /></TabsContent>
        <TabsContent value="hitl"><HitlPanel /></TabsContent>
        <TabsContent value="agents"><SubAgentPanel /></TabsContent>
      </Tabs>

      {/* 기존 로그 패널 하단에 유지 */}
      <LogPanel />
    </div>
  )
}
```

- [ ] **Step 2: StepProgressPanel 구현**

```tsx
function StepProgressPanel() {
  const [data, setData] = useState<{ steps: StepInfo[], current_step: string | null }>({
    steps: [], current_step: null
  })
  const [channel, setChannel] = useState('CH1')

  useEffect(() => {
    const load = () => fetch(`/api/pipeline/steps?channel=${channel}`)
      .then(r => r.json()).then(setData)
    load()
    const id = setInterval(load, 3000)
    return () => clearInterval(id)
  }, [channel])

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-red-100/50 px-5 py-4">
        <h2 className="heading-font text-sm font-bold text-[#1a0505]">Step 진행 현황</h2>
        <select value={channel} onChange={e => setChannel(e.target.value)}
          className="rounded-lg border border-red-100/50 bg-white/50 px-2 py-1 text-xs text-[#5c1a1a]">
          {['CH1','CH2','CH3','CH4'].map(c => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div className="divide-y divide-red-50/50">
        {data.steps.map(step => (
          <div key={step.step_id} className="flex items-center gap-3 px-5 py-3">
            <div className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs
              ${step.status === 'done' ? 'bg-green-100 text-green-700' :
                step.status === 'running' ? 'bg-red-100 text-[#ee2400] animate-pulse' :
                step.status === 'failed' ? 'bg-red-200 text-red-800' :
                'bg-gray-100 text-gray-400'}`}>
              {step.status === 'done' ? '✓' : step.status === 'running' ? '⚡' :
               step.status === 'failed' ? '✗' : '○'}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-[#1a0505]">{step.step_name}</p>
              {step.duration_ms && (
                <p className="text-xs text-[#9b6060]">{(step.duration_ms / 1000).toFixed(1)}s</p>
              )}
            </div>
            <span className={`rounded px-2 py-0.5 text-[10px] font-bold font-mono
              ${step.status === 'done' ? 'bg-green-100 text-green-700' :
                step.status === 'running' ? 'bg-red-100 text-[#ee2400]' :
                'bg-gray-100 text-gray-500'}`}>
              {step.status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: RealtimePreviewPanel 구현 (Step08 이미지 실시간)**

```tsx
function RealtimePreviewPanel() {
  const [images, setImages] = useState<string[]>([])
  const [channel, setChannel] = useState('CH1')

  useEffect(() => {
    const load = async () => {
      // /api/pipeline/status에서 실행중인 Run 찾아 이미지 목록 조회
      const status = await fetch('/api/pipeline/status').then(r => r.json())
      const running = status.recent?.find((r: any) => r.run_state === 'RUNNING')
      if (!running) return
      const res = await fetch(
        `/api/runs/${running.channel_id}/${running.run_id}`
      ).then(r => r.json())
      setImages(res.step08?.images ?? [])
    }
    load()
    const id = setInterval(load, 3000)
    return () => clearInterval(id)
  }, [channel])

  if (images.length === 0) {
    return (
      <div className="glass-card flex items-center justify-center py-16 text-[#9b6060] text-sm">
        실행 중인 Run이 없거나 이미지가 아직 생성되지 않았습니다
      </div>
    )
  }

  return (
    <div className="glass-card p-4">
      <p className="mb-3 text-xs font-bold text-[#9b6060]">Step08 생성 이미지 — 실시간 ({images.length}장)</p>
      <div className="grid grid-cols-4 gap-3">
        {images.map((url, i) => (
          <div key={i} className="aspect-video overflow-hidden rounded-lg bg-red-50/50">
            <img src={url} alt={`장면 ${i+1}`} className="h-full w-full object-cover" />
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: HitlPanel + SubAgentPanel 구현**

```tsx
function HitlPanel() {
  const [signals, setSignals] = useState<any[]>([])
  useEffect(() => {
    fetch('/api/hitl-signals').then(r => r.json()).then(d => setSignals(d ?? []))
  }, [])

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-red-100/50 px-5 py-4">
        <h2 className="heading-font text-sm font-bold text-[#1a0505]">
          HITL 신호 — 운영자 확인 필요 ({signals.length})
        </h2>
      </div>
      {signals.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-[#9b6060]">✓ 미해결 신호 없음</p>
      ) : (
        <div className="divide-y divide-red-50/50">
          {signals.map(s => (
            <div key={s.id} className="flex items-center gap-3 px-5 py-3">
              <span className="text-lg">{s.type === 'pipeline_failure' ? '🔴' : '⚠️'}</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-[#1a0505]">{s.type}</p>
                <p className="text-xs text-[#9b6060]">{s.message}</p>
              </div>
              <button
                onClick={() => fetch('/api/hitl-signals', {
                  method: 'PATCH', headers: {'Content-Type':'application/json'},
                  body: JSON.stringify({ id: s.id })
                }).then(() => setSignals(prev => prev.filter(x => x.id !== s.id)))}
                className="rounded-lg bg-green-100 px-3 py-1 text-xs font-bold text-green-700 hover:bg-green-200">
                해결
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SubAgentPanel() {
  const [agents, setAgents] = useState<any[]>([])
  useEffect(() => {
    fetch('/api/agents/status').then(r => r.json()).then(d => setAgents(d.agents ?? []))
  }, [])

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-red-100/50 px-5 py-4">
        <h2 className="heading-font text-sm font-bold text-[#1a0505]">Sub-Agent 실행 현황</h2>
      </div>
      <div className="divide-y divide-red-50/50">
        {agents.map(a => (
          <div key={a.id} className="px-5 py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-bold text-[#1a0505]">🤖 {a.name}</p>
              <span className={`rounded px-2 py-0.5 text-[10px] font-bold
                ${a.available ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {a.available ? '실행됨' : '미실행'}
              </span>
            </div>
            {a.last_run && (
              <p className="text-xs text-[#9b6060]">
                마지막 실행: {new Date(a.last_run.timestamp ?? '').toLocaleString('ko-KR')}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: ManímPanel 구현**

```tsx
function ManímPanel() {
  const [data, setData] = useState<any>(null)
  useEffect(() => {
    // 최근 Run의 manim_stability_report.json 읽기
    fetch('/api/pipeline/status').then(r => r.json()).then(async status => {
      const recent = status.recent?.[0]
      if (!recent) return
      const res = await fetch(`/api/runs/${recent.channel_id}/${recent.run_id}`)
        .then(r => r.json())
      setData(res.manim_stability ?? null)
    })
  }, [])

  const fallbackRate = data?.fallback_rate ?? 0
  const isWarning = fallbackRate > 0.5

  return (
    <div className="glass-card p-5">
      <h2 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">Manim 애니메이션 안정성</h2>
      {data ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[#5c1a1a]">Fallback Rate</span>
            <span className={`heading-font text-xl font-bold ${isWarning ? 'text-[#ee2400]' : 'text-green-700'}`}>
              {(fallbackRate * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-red-100">
            <div className={`h-2 rounded-full transition-all ${isWarning ? 'bg-[#ee2400]' : 'bg-green-500'}`}
                 style={{ width: `${fallbackRate * 100}%` }} />
          </div>
          {isWarning && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-[#ee2400] font-semibold">
              ⚠ fallback_rate 50% 초과 — HITL 플래그 발생
            </p>
          )}
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="glass-card p-3 text-center">
              <p className="heading-font text-2xl font-bold text-green-700">{data.success_count ?? 0}</p>
              <p className="text-xs text-[#9b6060]">성공</p>
            </div>
            <div className="glass-card p-3 text-center">
              <p className="heading-font text-2xl font-bold text-[#ee2400]">{data.fallback_count ?? 0}</p>
              <p className="text-xs text-[#9b6060]">폴백</p>
            </div>
            <div className="glass-card p-3 text-center">
              <p className="heading-font text-2xl font-bold text-[#900000]">{data.total_count ?? 0}</p>
              <p className="text-xs text-[#9b6060]">전체</p>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-[#9b6060]">Manim 데이터 없음 — 실행 후 확인 가능</p>
      )}
    </div>
  )
}
```

- [ ] **Step 6: 커밋**

```bash
git add app/monitor/page.tsx
git commit -m "feat: 파이프라인 모니터 5개 탭 재설계 (Step/미리보기/Manim/HITL/Sub-Agent)"
```

---

## Task 8: Run 상세 — 검수 허브 (10개 탭)

**Files:**
- Modify: `web/app/runs/[channelId]/[runId]/page.tsx`

- [ ] **Step 1: 10개 탭 기본 구조 설정**

`web/app/runs/[channelId]/[runId]/page.tsx` 전체를 탭 구조로 재작성:

```tsx
'use client'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function RunDetailPage() {
  const { channelId, runId } = useParams<{ channelId: string; runId: string }>()
  const [artifacts, setArtifacts] = useState<any>(null)

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}`)
      .then(r => r.json()).then(setArtifacts)
  }, [channelId, runId])

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="heading-font text-2xl font-bold text-[#1a0505]">
            {channelId} / {runId}
          </h1>
          <p className="mt-1 text-sm text-[#9b6060]">
            {artifacts?.manifest?.topic_title ?? '로딩 중...'}
          </p>
        </div>
        <RunStateBadge state={artifacts?.manifest?.run_state} />
      </div>

      <Tabs defaultValue="script" className="space-y-4">
        <TabsList className="glass-card flex-wrap p-1 h-auto gap-1">
          {[
            ['script','✍️ 스크립트'],['images','🖼 이미지'],['video','🎬 영상'],
            ['shorts','📱 Shorts'],['audio','🎵 오디오'],['thumbnail','🖼 썸네일'],
            ['title','📝 제목 선택'],['seo','🔍 SEO'],['qa','👁 QA'],['cost','💰 비용'],
          ].map(([v, label]) => (
            <TabsTrigger key={v} value={v}
              className="data-[state=active]:bg-[#ee2400] data-[state=active]:text-white text-xs px-3">
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="script"><ScriptTab channelId={channelId} runId={runId} /></TabsContent>
        <TabsContent value="images"><ImagesTab artifacts={artifacts} /></TabsContent>
        <TabsContent value="video"><VideoTab artifacts={artifacts} /></TabsContent>
        <TabsContent value="shorts"><ShortsTab channelId={channelId} runId={runId} /></TabsContent>
        <TabsContent value="audio"><AudioTab channelId={channelId} runId={runId} /></TabsContent>
        <TabsContent value="thumbnail"><ThumbnailTab artifacts={artifacts} /></TabsContent>
        <TabsContent value="title"><TitleTab artifacts={artifacts} /></TabsContent>
        <TabsContent value="seo"><SeoTab channelId={channelId} runId={runId} /></TabsContent>
        <TabsContent value="qa"><QaTab artifacts={artifacts} /></TabsContent>
        <TabsContent value="cost"><CostTab artifacts={artifacts} /></TabsContent>
      </Tabs>
    </div>
  )
}
```

- [ ] **Step 2: ScriptTab — 후킹 하이라이트 적용**

```tsx
function ScriptTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [script, setScript] = useState<string>('')
  useEffect(() => {
    fetch(`/api/artifacts/${channelId}/${runId}/step08/script.md`)
      .then(r => r.text()).then(setScript).catch(() => setScript('스크립트 없음'))
  }, [channelId, runId])

  // 도입부 첫 200자 하이라이트
  const intro = script.slice(0, 200)
  const rest = script.slice(200)

  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-3 text-sm font-bold text-[#1a0505]">스크립트 전문</h3>
      <div className="mb-3 rounded-lg border border-[#ee2400]/20 bg-red-50/50 p-4">
        <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ee2400]">
          ✦ 도입부 후킹 (첫 200자)
        </p>
        <p className="text-sm leading-relaxed text-[#1a0505] font-medium">{intro}</p>
      </div>
      <pre className="whitespace-pre-wrap text-xs leading-relaxed text-[#5c1a1a] font-mono max-h-96 overflow-y-auto">
        {rest}
      </pre>
    </div>
  )
}
```

- [ ] **Step 3: ShortsTab + AudioTab 구현**

```tsx
function ShortsTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [data, setData] = useState<any>({ shorts: [], available: false })
  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/shorts`).then(r => r.json()).then(setData)
  }, [channelId, runId])

  if (!data.available) return (
    <div className="glass-card flex items-center justify-center py-16 text-sm text-[#9b6060]">
      Shorts 파일이 없습니다 (Step08-S 실행 후 확인 가능)
    </div>
  )

  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">
        Shorts 결과물 ({data.shorts.length}편)
      </h3>
      <div className="grid grid-cols-3 gap-4">
        {data.shorts.map((s: any) => (
          <div key={s.index} className="space-y-2">
            <div className="aspect-[9/16] overflow-hidden rounded-xl bg-red-50/50">
              <video src={s.url} controls className="h-full w-full object-cover" />
            </div>
            <p className="text-center text-xs text-[#9b6060]">Shorts #{s.index} · {s.duration_sec}초</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function AudioTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [bgm, setBgm] = useState<any>({ available: false })
  const [narUrl, setNarUrl] = useState<string | null>(null)
  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/bgm`).then(r => r.json()).then(setBgm)
    setNarUrl(`/api/artifacts/${channelId}/${runId}/step08/narration.wav`)
  }, [channelId, runId])

  return (
    <div className="glass-card p-5 space-y-6">
      <div>
        <h3 className="heading-font mb-3 text-sm font-bold text-[#1a0505]">나레이션</h3>
        <audio controls src={narUrl ?? ''} className="w-full" />
      </div>
      <div>
        <h3 className="heading-font mb-3 text-sm font-bold text-[#1a0505]">BGM 오버레이</h3>
        {bgm.available ? (
          <>
            <audio controls src={bgm.bgm_url} className="w-full mb-3" />
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-red-50/50 p-3">
                <p className="text-xs text-[#9b6060]">BGM 소스</p>
                <p className="font-semibold text-[#1a0505]">{bgm.bgm_source ?? '—'}</p>
              </div>
              <div className="rounded-lg bg-red-50/50 p-3">
                <p className="text-xs text-[#9b6060]">톤 카테고리</p>
                <p className="font-semibold text-[#1a0505]">{bgm.bgm_category_tone ?? '—'}</p>
              </div>
            </div>
          </>
        ) : <p className="text-sm text-[#9b6060]">BGM 파일 없음</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: TitleTab — A/B/C 선택 UI**

```tsx
function TitleTab({ artifacts }: { artifacts: any }) {
  const variants = artifacts?.step08?.title_variants ?? []
  const [selected, setSelected] = useState<string | null>(null)

  if (variants.length === 0) return (
    <div className="glass-card flex items-center justify-center py-16 text-sm text-[#9b6060]">
      제목 배리언트 데이터 없음
    </div>
  )

  const labels: Record<string, string> = {
    authority: '권위형 (Authority)',
    curiosity: '호기심형 (Curiosity)',
    benefit: '혜택형 (Benefit)',
  }

  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">
        제목 배리언트 선택 — 업로드 전 최종 결정
      </h3>
      <div className="space-y-3">
        {variants.map((v: any) => (
          <button key={v.type}
            onClick={() => setSelected(v.type)}
            className={`w-full rounded-xl border-2 p-4 text-left transition
              ${selected === v.type
                ? 'border-[#ee2400] bg-red-50/80'
                : 'border-red-100/50 bg-white/40 hover:border-red-200'}`}>
            <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ee2400]">
              {labels[v.type] ?? v.type}
            </div>
            <p className="text-sm font-semibold text-[#1a0505]">{v.title}</p>
          </button>
        ))}
      </div>
      {selected && (
        <div className="mt-4 rounded-lg bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
          ✓ 선택됨: {labels[selected]} — 실제 적용은 업로드 시 반영됩니다
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: SeoTab 구현**

```tsx
function SeoTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [seo, setSeo] = useState<any>({ available: false })
  const [editing, setEditing] = useState(false)
  const [desc, setDesc] = useState('')

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/seo`)
      .then(r => r.json()).then(d => { setSeo(d); setDesc(d.description ?? '') })
  }, [channelId, runId])

  async function save() {
    await fetch(`/api/runs/${channelId}/${runId}/seo`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: desc }),
    })
    setEditing(false)
  }

  if (!seo.available) return (
    <div className="glass-card flex items-center justify-center py-16 text-sm text-[#9b6060]">
      SEO 메타데이터 없음
    </div>
  )

  return (
    <div className="glass-card p-5 space-y-4">
      <h3 className="heading-font text-sm font-bold text-[#1a0505]">SEO 메타데이터</h3>
      <div>
        <p className="mb-1 text-xs font-bold text-[#9b6060]">설명문</p>
        {editing ? (
          <div className="space-y-2">
            <textarea value={desc} onChange={e => setDesc(e.target.value)}
              className="w-full rounded-lg border border-red-100/50 bg-white/50 p-3 text-sm text-[#1a0505] outline-none"
              rows={4} />
            <div className="flex gap-2">
              <button onClick={save} className="rounded-lg bg-[#ee2400] px-4 py-1.5 text-xs font-bold text-white">저장</button>
              <button onClick={() => setEditing(false)} className="rounded-lg bg-gray-100 px-4 py-1.5 text-xs font-bold">취소</button>
            </div>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-3 rounded-lg bg-red-50/50 p-3">
            <p className="text-sm text-[#5c1a1a]">{desc}</p>
            <button onClick={() => setEditing(true)} className="text-[10px] font-bold text-[#ee2400] shrink-0">편집</button>
          </div>
        )}
      </div>
      <div>
        <p className="mb-2 text-xs font-bold text-[#9b6060]">태그 ({(seo.tags ?? []).length}개)</p>
        <div className="flex flex-wrap gap-2">
          {(seo.tags ?? []).map((tag: string, i: number) => (
            <span key={i} className="rounded-full bg-red-100/60 px-3 py-1 text-xs text-[#5c1a1a]">#{tag}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: QaTab — Vision QA 상세 구현**

```tsx
function QaTab({ artifacts }: { artifacts: any }) {
  const qa = artifacts?.step11 ?? {}
  const checks = [
    { key: 'animation_ok', label: '애니메이션 품질', icon: '🎞' },
    { key: 'script_ok', label: '스크립트 검증', icon: '✍️' },
    { key: 'policy_ok', label: '정책 준수', icon: '📋' },
    { key: 'character_consistency', label: '캐릭터 일관성', icon: '🎭' },
    { key: 'text_readability', label: '텍스트 가독성', icon: '👁' },
    { key: 'content_safe', label: '콘텐츠 안전', icon: '🛡' },
  ]

  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">QA 검수 상세</h3>
      <div className="grid grid-cols-3 gap-3">
        {checks.map(c => {
          const val = qa[c.key]
          const ok = val === true
          const na = val === null || val === undefined
          return (
            <div key={c.key} className={`rounded-xl p-4 text-center border
              ${ok ? 'border-green-200 bg-green-50' :
                na ? 'border-gray-200 bg-gray-50' :
                'border-red-200 bg-red-50'}`}>
              <div className="text-2xl mb-2">{c.icon}</div>
              <p className="text-xs font-bold text-[#1a0505] mb-1">{c.label}</p>
              <span className={`text-xs font-bold
                ${ok ? 'text-green-700' : na ? 'text-gray-500' : 'text-[#ee2400]'}`}>
                {ok ? '✓ 통과' : na ? '— 미검사' : '✗ 실패'}
              </span>
            </div>
          )
        })}
      </div>
      {qa.human_review_required && (
        <div className="mt-4 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800 font-semibold">
          ⚠ 수동 검수 필요 — QA 자동 판정 불확실
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 7: CostTab — 비용 예측 vs 실제**

```tsx
function CostTab({ artifacts }: { artifacts: any }) {
  const cost = artifacts?.cost_krw ?? 0
  const costJson = artifacts?.cost_detail ?? {}

  return (
    <div className="glass-card p-5 space-y-4">
      <h3 className="heading-font text-sm font-bold text-[#1a0505]">비용 분석</h3>
      <div className="flex items-center gap-4">
        <div className="flex-1 rounded-xl bg-red-50/50 p-4">
          <p className="text-xs text-[#9b6060]">이 Run 총 비용</p>
          <p className="heading-font text-3xl font-bold text-red-accent mt-1">
            ₩{cost.toLocaleString()}
          </p>
        </div>
      </div>
      {Object.entries(costJson).length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-[#9b6060]">Step별 비용</p>
          {Object.entries(costJson).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between py-2 border-b border-red-50/50">
              <span className="text-sm text-[#5c1a1a]">{k}</span>
              <span className="text-sm font-bold text-red-accent font-mono">
                ₩{Number(v).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 8: 남은 탭 — ImagesTab, VideoTab, ThumbnailTab**

```tsx
function ImagesTab({ artifacts }: { artifacts: any }) {
  const images: Array<{ url: string; prompt?: string }> = artifacts?.step08?.images ?? []
  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">
        장면별 이미지 ({images.length}장)
      </h3>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {images.map((img, i) => (
          <div key={i} className="space-y-1">
            <div className="aspect-video overflow-hidden rounded-lg bg-red-50/50">
              <img src={img.url} alt={`장면 ${i+1}`} className="h-full w-full object-cover" />
            </div>
            <p className="text-[10px] text-[#9b6060] truncate">장면 {i+1}</p>
            {img.prompt && (
              <p className="text-[9px] text-[#9b6060] line-clamp-2">{img.prompt}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function VideoTab({ artifacts }: { artifacts: any }) {
  const videoUrl = artifacts?.step08?.video_url
  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">완성 영상</h3>
      {videoUrl ? (
        <video controls src={videoUrl} className="w-full rounded-xl" />
      ) : (
        <div className="flex items-center justify-center py-16 text-sm text-[#9b6060]">
          영상 파일 없음
        </div>
      )}
    </div>
  )
}

function ThumbnailTab({ artifacts }: { artifacts: any }) {
  const thumbs: string[] = artifacts?.step08?.thumbnails ?? []
  const [selected, setSelected] = useState<number | null>(null)
  return (
    <div className="glass-card p-5">
      <h3 className="heading-font mb-4 text-sm font-bold text-[#1a0505]">썸네일 3종 비교</h3>
      <div className="grid grid-cols-3 gap-4">
        {thumbs.map((url, i) => (
          <button key={i} onClick={() => setSelected(i)}
            className={`overflow-hidden rounded-xl border-2 transition
              ${selected === i ? 'border-[#ee2400] shadow-lg' : 'border-red-100/50'}`}>
            <img src={url} alt={`썸네일 ${i+1}`} className="w-full aspect-video object-cover" />
            <p className={`py-2 text-center text-xs font-bold
              ${selected === i ? 'text-[#ee2400]' : 'text-[#9b6060]'}`}>
              배리언트 {i+1} {selected === i ? '✓ 선택됨' : ''}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}

function RunStateBadge({ state }: { state?: string }) {
  const map: Record<string, string> = {
    RUNNING: 'bg-red-100 text-[#ee2400] animate-pulse',
    COMPLETED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-200 text-red-800',
    PENDING: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold ${map[state ?? 'PENDING'] ?? map.PENDING}`}>
      {state ?? 'PENDING'}
    </span>
  )
}
```

- [ ] **Step 9: 커밋**

```bash
git add app/runs/
git commit -m "feat: Run 상세 검수 허브 — 10개 탭 재설계 (Shorts·BGM·제목·SEO·QA·비용 신규)"
```

---

## Task 9: 지식/트렌드 강화

**Files:**
- Modify: `web/app/knowledge/page.tsx`
- Modify: `web/app/trends/page.tsx`

- [ ] **Step 1: knowledge/page.tsx — 수집 단계 + 팩트체크 배지**

`web/app/knowledge/page.tsx`의 기존 토픽 목록에 수집 단계 표시 추가:

```tsx
// 수집 단계 배지 컴포넌트
function SourceBadge({ source }: { source?: string }) {
  const colors: Record<string, string> = {
    tavily: 'bg-blue-100 text-blue-700',
    wikipedia: 'bg-purple-100 text-purple-700',
    gemini: 'bg-red-100 text-[#ee2400]',
    naver: 'bg-green-100 text-green-700',
    scholar: 'bg-amber-100 text-amber-700',
  }
  const label = source?.toLowerCase() ?? 'unknown'
  return (
    <span className={`rounded px-2 py-0.5 text-[9px] font-bold ${colors[label] ?? 'bg-gray-100 text-gray-600'}`}>
      {source ?? '?'}
    </span>
  )
}

// 팩트체크 배지
function FactCheckBadge({ status }: { status?: string }) {
  if (!status) return null
  const ok = status === 'verified'
  return (
    <span className={`rounded px-2 py-0.5 text-[9px] font-bold
      ${ok ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
      {ok ? '✓ 팩트체크 완료' : '⚠ 미검증'}
    </span>
  )
}
```

- [ ] **Step 2: trends/page.tsx — 점수 구성 시각화 + 채널 탭**

기존 트렌드 페이지에 점수 구성 시각화 추가:

```tsx
// 점수 구성 막대 시각화
function ScoreBreakdown({ scores }: { scores?: {
  interest: number; relevance: number; revenue: number; urgency: number
}}) {
  if (!scores) return null
  const items = [
    { label: '관심도', value: scores.interest, weight: 40, color: '#ee2400' },
    { label: '적합도', value: scores.relevance, weight: 25, color: '#ffb09c' },
    { label: '수익성', value: scores.revenue, weight: 20, color: '#900000' },
    { label: '긴급도', value: scores.urgency, weight: 15, color: '#fbd9d3' },
  ]
  return (
    <div className="mt-2 space-y-1">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-[9px] text-[#9b6060] w-12 shrink-0">{item.label}</span>
          <div className="flex-1 h-1.5 rounded-full bg-red-100/50">
            <div className="h-1.5 rounded-full transition-all"
                 style={{ width: `${item.value}%`, background: item.color }} />
          </div>
          <span className="text-[9px] font-bold text-[#900000] w-6 text-right">{item.value}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: 커밋**

```bash
git add app/knowledge/page.tsx app/trends/page.tsx
git commit -m "feat: 지식 수집 단계 배지 + 트렌드 점수 구성 시각화"
```

---

## Task 10: 비용/학습/수익/리스크 강화

**Files:**
- Modify: `web/app/cost/page.tsx`
- Modify: `web/app/learning/page.tsx`
- Modify: `web/app/revenue/page.tsx`
- Modify: `web/app/risk/page.tsx`

- [ ] **Step 1: cost/page.tsx — 예측 vs 실제 탭 + 이연 업로드 탭 추가**

기존 cost 페이지를 Tabs로 감싸고 2개 탭 추가:

```tsx
// 기존 쿼터 현황을 첫 번째 탭으로, 다음 탭들 추가
<Tabs defaultValue="quota" className="space-y-4">
  <TabsList className="glass-card p-1">
    <TabsTrigger value="quota" ...>쿼터 현황</TabsTrigger>
    <TabsTrigger value="projection" ...>예측 vs 실제</TabsTrigger>
    <TabsTrigger value="deferred" ...>이연 업로드</TabsTrigger>
  </TabsList>
  <TabsContent value="quota">{/* 기존 내용 */}</TabsContent>
  <TabsContent value="projection"><CostProjectionTab /></TabsContent>
  <TabsContent value="deferred"><DeferredJobsTab /></TabsContent>
</Tabs>
```

```tsx
function CostProjectionTab() {
  const [data, setData] = useState<any>({ available: false })
  useEffect(() => {
    fetch('/api/cost/projection').then(r => r.json()).then(setData)
  }, [])

  if (!data.available) return (
    <div className="glass-card flex items-center justify-center py-12 text-sm text-[#9b6060]">
      비용 예측 데이터 없음 (파이프라인 실행 후 생성됨)
    </div>
  )

  const items: Array<{ topic: string; estimated: number; actual: number }> = data.projections ?? []
  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-red-100/50 px-5 py-4">
        <h3 className="heading-font text-sm font-bold text-[#1a0505]">주제별 예측 vs 실제 비용</h3>
      </div>
      <div className="divide-y divide-red-50/50">
        {items.map((item, i) => {
          const diff = item.actual - item.estimated
          const over = diff > 0
          return (
            <div key={i} className="px-5 py-3">
              <p className="text-sm font-semibold text-[#1a0505] mb-2">{item.topic}</p>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-[10px] text-[#9b6060]">예측</p>
                  <p className="heading-font font-bold text-[#900000]">₩{item.estimated.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#9b6060]">실제</p>
                  <p className="heading-font font-bold text-[#900000]">₩{item.actual.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#9b6060]">차이</p>
                  <p className={`heading-font font-bold ${over ? 'text-[#ee2400]' : 'text-green-700'}`}>
                    {over ? '+' : ''}₩{diff.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DeferredJobsTab() {
  const [data, setData] = useState<any>({ deferred_jobs: [], quota_remaining: 0 })
  useEffect(() => {
    fetch('/api/deferred-jobs').then(r => r.json()).then(setData)
  }, [])

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-red-100/50 px-5 py-4">
        <h3 className="heading-font text-sm font-bold text-[#1a0505]">
          이연 업로드 ({data.deferred_jobs?.length ?? 0}건)
        </h3>
        <span className="text-xs text-[#9b6060]">잔여 쿼터: {data.quota_remaining?.toLocaleString()}</span>
      </div>
      {(data.deferred_jobs ?? []).length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-[#9b6060]">✓ 이연 업로드 없음</p>
      ) : (
        <div className="divide-y divide-red-50/50">
          {data.deferred_jobs.map((job: any, i: number) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3">
              <div className="flex-1">
                <p className="text-sm font-semibold text-[#1a0505]">{job.title ?? job.run_id}</p>
                <p className="text-xs text-[#9b6060]">{job.channel_id} · {job.deferred_at}</p>
              </div>
              <button onClick={() => fetch('/api/deferred-jobs', { method: 'POST' })
                .then(() => setData((d: any) => ({ ...d, deferred_jobs: d.deferred_jobs.filter((_: any, j: number) => j !== i) })))}
                className="rounded-lg bg-[#ee2400] px-3 py-1 text-xs font-bold text-white">
                재시도
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: learning/page.tsx — KPI 48h + 알고리즘 단계 + 바이어스 탭**

기존 learning 페이지를 3개 탭으로 확장:

```tsx
<Tabs defaultValue="kpi" className="space-y-4">
  <TabsList className="glass-card p-1">
    <TabsTrigger value="kpi" ...>📉 KPI 48h</TabsTrigger>
    <TabsTrigger value="algorithm" ...>🧠 알고리즘 단계</TabsTrigger>
    <TabsTrigger value="bias" ...>🧬 학습 바이어스</TabsTrigger>
  </TabsList>
  <TabsContent value="kpi"><KpiTab /></TabsContent>
  <TabsContent value="algorithm"><AlgorithmStageTab /></TabsContent>
  <TabsContent value="bias">{/* 기존 학습 피드백 내용 유지 */}</TabsContent>
</Tabs>
```

```tsx
function AlgorithmStageTab() {
  const [data, setData] = useState<any>({ available: false })
  const [channel, setChannel] = useState('CH1')

  useEffect(() => {
    fetch(`/api/learning/algorithm?channel=${channel}`).then(r => r.json()).then(setData)
  }, [channel])

  const stages = ['PRE-ENTRY', 'SEARCH-ONLY', 'BROWSE-ENTRY', 'ALGORITHM-ACTIVE']
  const currentIdx = stages.indexOf(data.current_stage ?? 'PRE-ENTRY')

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="heading-font text-sm font-bold text-[#1a0505]">알고리즘 단계 승격 현황</h3>
        <select value={channel} onChange={e => setChannel(e.target.value)}
          className="rounded-lg border border-red-100/50 bg-white/50 px-2 py-1 text-xs text-[#5c1a1a]">
          {['CH1','CH2','CH3','CH4'].map(c => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div className="flex items-center justify-between gap-2">
        {stages.map((stage, i) => (
          <div key={stage} className="flex-1 text-center">
            <div className={`mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full text-xs font-bold
              ${i <= currentIdx ? 'bg-[#ee2400] text-white' : 'bg-red-100 text-[#9b6060]'}`}>
              {i + 1}
            </div>
            <p className={`text-[9px] font-bold ${i <= currentIdx ? 'text-[#900000]' : 'text-[#9b6060]'}`}>
              {stage}
            </p>
            {i < stages.length - 1 && (
              <div className={`absolute top-5 right-0 h-0.5 w-full ${i < currentIdx ? 'bg-[#ee2400]' : 'bg-red-100'}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: revenue/page.tsx — 월별 추세 탭 추가**

기존 revenue 페이지에 추세 탭 추가 (Recharts LineChart 사용):

```tsx
// 기존 내용을 첫 번째 탭으로, 추세 그래프를 두 번째 탭으로
<Tabs defaultValue="current">
  <TabsList className="glass-card p-1">
    <TabsTrigger value="current" ...>현황</TabsTrigger>
    <TabsTrigger value="trend" ...>📅 월별 추세</TabsTrigger>
  </TabsList>
  <TabsContent value="current">{/* 기존 내용 */}</TabsContent>
  <TabsContent value="trend">
    {/* Recharts LineChart — 서버 컴포넌트 불가, 'use client' 분리 파일로 */}
    <RevenueTrendChart />
  </TabsContent>
</Tabs>
```

- [ ] **Step 4: risk/page.tsx — 지속성 분석 탭 추가**

```tsx
// 기존 리스크 탭에 지속성 탭 추가
function SustainabilityTab() {
  const [data, setData] = useState<any>({ available: false })
  useEffect(() => {
    fetch('/api/sustainability').then(r => r.json()).then(setData)
  }, [])

  if (!data.available) return (
    <div className="glass-card flex items-center justify-center py-12 text-sm text-[#9b6060]">
      지속성 데이터 없음 (Step17 실행 후 생성됨)
    </div>
  )

  const channels: Array<{ channel_id: string; topic_capacity: number; depletion_risk: string }> =
    data.channels ?? []

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-red-100/50 px-5 py-4">
        <h3 className="heading-font text-sm font-bold text-[#1a0505]">주제 지속성 분석</h3>
      </div>
      <div className="divide-y divide-red-50/50">
        {channels.map(ch => {
          const isHigh = ch.depletion_risk === 'HIGH'
          return (
            <div key={ch.channel_id} className="px-5 py-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-bold text-[#1a0505]">{ch.channel_id}</p>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold
                  ${isHigh ? 'bg-red-100 text-[#ee2400]' : 'bg-green-100 text-green-700'}`}>
                  {ch.depletion_risk} RISK
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 rounded-full bg-red-100/50">
                  <div className="h-2 rounded-full bg-gradient-to-r from-[#ee2400] to-[#ffb09c]"
                       style={{ width: `${ch.topic_capacity}%` }} />
                </div>
                <span className="text-xs font-bold text-[#900000]">{ch.topic_capacity}%</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: 커밋**

```bash
git add app/cost/page.tsx app/learning/page.tsx app/revenue/page.tsx app/risk/page.tsx
git commit -m "feat: 비용·학습·수익·리스크 페이지 검증 탭 추가"
```

---

## Task 11: 나머지 페이지 스타일 전환

**Files:**
- Modify: `web/app/qa/page.tsx`
- Modify: `web/app/settings/page.tsx`
- Modify: `web/app/channels/[id]/page.tsx`

- [ ] **Step 1: qa/page.tsx — 글래스 카드 + Red Light 배지 적용**

기존 QA 페이지의 Card 컴포넌트에 `glass-card` 클래스 추가. 배지 색상을 Red Light 팔레트로:

```tsx
// 기존 shadcn Card → className에 glass-card 추가
<Card className="glass-card glass-card-hover">
  ...
</Card>

// 상태 배지 색상 교체
const STATUS_CLASS = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-[#ee2400]',
} as const
```

- [ ] **Step 2: settings/page.tsx + channels/[id]/page.tsx 스타일 전환**

각 페이지에서:
1. `<Card>` → `<Card className="glass-card">` 추가
2. 주요 수치 표시 부분에 `heading-font text-red-accent` 클래스 추가
3. 페이지 헤딩에 `heading-font` 클래스 추가

- [ ] **Step 3: 빌드 최종 확인**

```bash
cd web && npm run build
```

Expected: 오류 없이 빌드 완료. 경고는 무시 가능.

- [ ] **Step 4: 최종 커밋**

```bash
git add app/qa/page.tsx app/settings/page.tsx app/channels/
git commit -m "feat: 나머지 페이지 Red Light Glassmorphism 스타일 전환 완료"
```

---

## Task 12: 통합 검증

- [ ] **Step 1: 개발 서버 시작**

```bash
cd web && npm run dev
```

- [ ] **Step 2: 핵심 기능 체크리스트**

브라우저에서 순서대로 확인:

| 항목 | URL | 확인 방법 |
|---|---|---|
| 배경 그라디언트 | `/` | 크림~블러쉬 그라디언트 표시 |
| 폰트 적용 | `/` | KPI 숫자가 Libre Baskerville, 본문이 M PLUS Rounded 1c |
| 사이드바 | 모든 페이지 | 다크 레드(#900000) 사이드바 |
| 테스트 런 버튼 | `/` | 버튼 클릭 → `/monitor` 리디렉트 |
| Step 진행 탭 | `/monitor` | Step 진행 탭 표시, 3초 폴링 |
| HITL 탭 | `/monitor` | hitl-signals 데이터 표시 |
| Shorts 탭 | `/runs/CH1/[any]` | shorts 탭 표시 (데이터 없으면 "없음" 메시지) |
| BGM 탭 | `/runs/CH1/[any]` | 오디오 탭, audio 플레이어 |
| 제목 선택 탭 | `/runs/CH1/[any]` | A/B/C 선택 UI |
| SEO 탭 | `/runs/CH1/[any]` | 편집 버튼 동작 |
| QA 6항목 | `/runs/CH1/[any]` | 6개 체크 항목 표시 |
| 이연 업로드 | `/cost` | 이연 업로드 탭 표시 |
| 알고리즘 단계 | `/learning` | 4단계 진행 표시 |
| 지속성 분석 | `/risk` | 채널별 topic_capacity |

- [ ] **Step 3: 최종 커밋**

```bash
git add -A
git commit -m "feat: KAS 대시보드 전면 재설계 + 23개 검증 항목 통합 완료"
```

---

## 스펙 커버리지 체크

| 스펙 요구사항 | Task |
|---|---|
| Red Light 팔레트 (#900000~#ffefea) | Task 1 |
| Libre Baskerville + M PLUS Rounded 1c | Task 1~2 |
| 글래스모피즘 (.glass-card) | Task 1 |
| 테스트 런 버튼 (업로드 없이) | Task 3 |
| Step 진행 트래커 | Task 4+7 |
| 실시간 이미지 미리보기 | Task 7 |
| Manim 안정성 탭 | Task 7 |
| HITL 신호 탭 | Task 7 |
| Sub-Agent 현황 탭 | Task 6+7 |
| Shorts 3편 검수 | Task 5+8 |
| BGM 오디오 플레이어 | Task 5+8 |
| 제목 A/B/C 선택 | Task 8 |
| Vision QA 상세 | Task 8 |
| SEO 편집 | Task 5+8 |
| 비용 예측 vs 실제 | Task 6+10 |
| 이연 업로드 탭 | Task 10 |
| KPI 48h | Task 6+10 |
| 알고리즘 단계 | Task 6+10 |
| 학습 바이어스 | Task 10 |
| 월별 수익 추세 | Task 10 |
| 지속성 분석 | Task 6+10 |
| 채널별 트렌드 탭 | Task 9 |
| 지식 수집 단계 표시 | Task 9 |
