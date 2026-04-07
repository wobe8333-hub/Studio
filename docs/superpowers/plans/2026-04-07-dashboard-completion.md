# KAS 대시보드 미구현 항목 완성 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스펙 `2026-04-06-dashboard-verification-redesign.md` 대비 미구현 32%를 완성하여 전체 완성도 100%에 도달한다.

**Architecture:** 8개 태스크는 파일 경계가 명확히 나뉘어 있어 병렬 실행 가능. 모든 UI는 기존 Red Light Glassmorphism 스타일(G.card, inline style color 상수)을 그대로 따른다. API 경로 버그(Task 1)는 다른 모든 탭이 의존하므로 가장 먼저 처리한다.

**Tech Stack:** Next.js 16 App Router, React 19 클라이언트 컴포넌트, Recharts 3 (RadarChart/LineChart), Tailwind CSS v4, shadcn/ui Card/Badge/Progress

---

## 파일 변경 맵

| 파일 | 담당 Task |
|---|---|
| `web/app/runs/[channelId]/[runId]/page.tsx` | Task 1, Task 6 |
| `web/app/monitor/page.tsx` | Task 1, Task 6 (ManImPanel) |
| `web/app/learning/page.tsx` | Task 2 |
| `web/app/revenue/page.tsx` | Task 3 |
| `web/app/risk/page.tsx` | Task 4 |
| `web/app/cost/page.tsx` | Task 5 |
| `web/app/page.tsx` | Task 7 |
| `web/app/trends/page.tsx` | Task 7 |
| `web/app/knowledge/page.tsx` | Task 7 |
| `web/app/globals.css` | Task 8 |

---

## Task 1: /api/files/ → /api/artifacts/ 경로 버그 수정

**Files:**
- Modify: `web/app/runs/[channelId]/[runId]/page.tsx`
- Modify: `web/app/monitor/page.tsx`

**스타일 상수 참고:** 두 파일 모두 `G.card` 스타일 객체를 사용 중.

- [ ] **Step 1: runs/page.tsx에서 /api/files/ 전체 교체**

`web/app/runs/[channelId]/[runId]/page.tsx` 내 `/api/files/` 를 `/api/artifacts/` 로 전체 교체.
대상 라인: 82 (이미지), 106 (영상), 139 (Shorts 영상), 170 (나레이션), 188 (BGM), 210, 213 (썸네일).

```tsx
// 변경 전 (예시)
src={`/api/files/${channelId}/${runId}/step08/${img}`}
// 변경 후
src={`/api/artifacts/${channelId}/${runId}/step08/${img}`}
```

- [ ] **Step 2: monitor/page.tsx PreviewPanel 경로 수정**

`web/app/monitor/page.tsx` 177번 줄:

```tsx
// 변경 전
const scenesPath = `/api/files/${ch}/${runId}/step08/scenes/`
// 변경 후
const scenesPath = `/api/artifacts/${ch}/${runId}/step08/scenes/`
```

- [ ] **Step 3: 커밋**

```bash
git add web/app/runs/\[channelId\]/\[runId\]/page.tsx web/app/monitor/page.tsx
git commit -m "fix: /api/files/ → /api/artifacts/ 경로 버그 수정"
```

---

## Task 2: /learning 페이지 — KPI·알고리즘·바이어스 3탭 구조

**Files:**
- Modify: `web/app/learning/page.tsx`

현재 단일 페이지를 3탭 구조로 재편한다.
기존 KPI 테이블 + CTR/AVP 차트 → KPI탭으로 이동.
신규: 알고리즘탭(채널별 stage 시각화), 바이어스탭(RadarChart).

- [ ] **Step 1: 탭 타입 + 스타일 상수 추가**

파일 상단 import 섹션 아래에 추가:

```tsx
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'

const G = {
  card: {
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(238,36,0,0.12)',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
  } as React.CSSProperties,
}

const LEARN_TABS = [
  { id: 'kpi',       label: 'KPI 48h' },
  { id: 'algorithm', label: '알고리즘 단계' },
  { id: 'bias',      label: '학습 바이어스' },
] as const
type LearnTabId = typeof LEARN_TABS[number]['id']
```

- [ ] **Step 2: 알고리즘 탭 컴포넌트 작성**

`LearningPage` 함수 외부에 추가:

```tsx
interface AlgorithmChannel {
  channel_id: string
  policy: {
    algorithm_stage?: string
    phase_promotion_history?: Array<{ from: string; to: string; promoted_at: string }>
  } | null
}

const STAGE_ORDER = ['PRE-ENTRY', 'SEARCH-ONLY', 'BROWSE-ENTRY', 'ALGORITHM-ACTIVE']
const STAGE_COLOR: Record<string, string> = {
  'PRE-ENTRY': '#9b6060',
  'SEARCH-ONLY': '#f59e0b',
  'BROWSE-ENTRY': '#3b82f6',
  'ALGORITHM-ACTIVE': '#22c55e',
}

function AlgorithmTab() {
  const [channels, setChannels] = useState<AlgorithmChannel[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/learning/algorithm')
      .then(r => r.ok ? r.json() : { channels: [] })
      .then(d => setChannels(d.channels ?? []))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-5 w-5 animate-spin rounded-full border-2 border-[#ee2400] border-t-transparent" /></div>

  return (
    <div className="space-y-3">
      {channels.map(ch => {
        const stage = ch.policy?.algorithm_stage ?? 'PRE-ENTRY'
        const stageIdx = STAGE_ORDER.indexOf(stage)
        const color = STAGE_COLOR[stage] ?? '#9b6060'
        return (
          <div key={ch.channel_id} style={G.card} className="p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>{ch.channel_id}</span>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: `${color}20`, color }}>{stage}</span>
            </div>
            <div className="flex gap-1">
              {STAGE_ORDER.map((s, i) => (
                <div
                  key={s}
                  className="flex-1 h-2 rounded-full transition-all"
                  style={{ background: i <= stageIdx ? color : 'rgba(238,36,0,0.1)' }}
                />
              ))}
            </div>
            <div className="flex justify-between mt-1">
              {STAGE_ORDER.map(s => (
                <span key={s} className="text-[9px]" style={{ color: '#9b6060' }}>{s.split('-')[0]}</span>
              ))}
            </div>
            {ch.policy?.phase_promotion_history?.length ? (
              <p className="text-xs mt-3" style={{ color: '#9b6060' }}>
                최근 승격: {ch.policy.phase_promotion_history.slice(-1)[0]?.promoted_at?.slice(0, 10) ?? '—'}
              </p>
            ) : null}
          </div>
        )
      })}
      {channels.length === 0 && (
        <div style={G.card} className="p-10 text-center">
          <p className="text-sm" style={{ color: '#9b6060' }}>알고리즘 정책 데이터 없음 (파이프라인 실행 후 생성)</p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 바이어스 RadarChart 컴포넌트 작성**

```tsx
const BIAS_MOCK = [
  { subject: '제목 다양성', value: 72 },
  { subject: '주제 균형', value: 58 },
  { subject: '채널 분산', value: 85 },
  { subject: '업로드 일관성', value: 64 },
  { subject: '시각 스타일', value: 79 },
]

function BiasTab() {
  return (
    <div style={G.card} className="p-6">
      <h3 className="font-bold mb-1" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>학습 바이어스 레이더</h3>
      <p className="text-xs mb-5" style={{ color: '#9b6060' }}>5개 차원 바이어스 분석 — 수치가 낮을수록 해당 영역 편향 가능성 있음</p>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={BIAS_MOCK}>
          <PolarGrid stroke="rgba(238,36,0,0.12)" />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#9b6060' }} />
          <Radar name="바이어스" dataKey="value" stroke="#ee2400" fill="#ee2400" fillOpacity={0.15} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
      <p className="text-[10px] mt-3 text-center" style={{ color: '#9b6060' }}>
        * 현재 파이프라인 실행 데이터 기반 추정값입니다
      </p>
    </div>
  )
}
```

- [ ] **Step 4: LearningPage를 3탭 구조로 재편**

기존 `LearningPage` 반환문에서:
1. `const [tab, setTab] = useState<LearnTabId>('kpi')` 상태 추가
2. 탭 바 렌더링
3. 탭 컨텐츠 조건부 렌더링 — 기존 CTR/AVP 차트 + 피드백 테이블 → KPI탭으로 감싸기

```tsx
export default function LearningPage() {
  // ... 기존 state 유지 ...
  const [tab, setTab] = useState<LearnTabId>('kpi')

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>학습 피드백</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>업로드 48시간 후 KPI 수집 기반 성과 분석</p>
      </div>

      {/* 탭 바 */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
        {LEARN_TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex-1 py-2 rounded-lg text-xs font-medium transition-all"
            style={{ background: tab === t.id ? '#900000' : 'transparent', color: tab === t.id ? '#ffefea' : '#9b6060' }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* KPI 탭: 기존 CTR/AVP 차트 + 피드백 테이블 */}
      {tab === 'kpi' && (
        <>
          {/* 기존 CTR/AVP LineChart Card */}
          {/* 기존 승리패턴 Card */}
          {/* 기존 피드백 테이블 Card */}
        </>
      )}

      {tab === 'algorithm' && <AlgorithmTab />}
      {tab === 'bias' && <BiasTab />}
    </div>
  )
}
```

- [ ] **Step 5: 커밋**

```bash
git add web/app/learning/page.tsx
git commit -m "feat: /learning KPI·알고리즘·바이어스 3탭 구조 구현"
```

---

## Task 3: /revenue 페이지 — 월별 추세 탭 추가

**Files:**
- Modify: `web/app/revenue/page.tsx`

- [ ] **Step 1: 탭 상태 + 타입 추가**

파일 상단에 추가:

```tsx
import { LineChart, Line } from 'recharts'

const REV_TABS = [
  { id: 'current', label: '이번달' },
  { id: 'trend',   label: '월별 추세' },
] as const
type RevTabId = typeof REV_TABS[number]['id']

interface MonthlyTrend {
  month: string
  total: number
  adsense: number
  affiliate: number
}
```

- [ ] **Step 2: 추세 데이터 fetch 로직 추가**

`RevenuePage` 내 useEffect 기존 코드 아래 추가:

```tsx
const [trendData, setTrendData] = useState<MonthlyTrend[]>([])
const [tab, setTab] = useState<RevTabId>('current')

useEffect(() => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

  const supabase = createClient()
  const sixMonthsAgo = new Date()
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 5)
  const since = sixMonthsAgo.toISOString().slice(0, 7)

  supabase
    .from('revenue_monthly')
    .select('month, adsense_krw, affiliate_krw, net_profit')
    .gte('month', since)
    .order('month', { ascending: true })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .then(({ data }) => {
      if (!data) return
      // 월별 합산
      const byMonth: Record<string, MonthlyTrend> = {}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(data as any[]).forEach((r) => {
        if (!byMonth[r.month]) byMonth[r.month] = { month: r.month, total: 0, adsense: 0, affiliate: 0 }
        byMonth[r.month].adsense += r.adsense_krw ?? 0
        byMonth[r.month].affiliate += r.affiliate_krw ?? 0
        byMonth[r.month].total += r.net_profit ?? 0
      })
      setTrendData(Object.values(byMonth))
    })
}, [])
```

- [ ] **Step 3: 탭 바 + 추세 탭 컴포넌트 추가**

반환문 `<div className="space-y-6">` 바로 다음에 헤딩 아래 탭 바 삽입:

```tsx
{/* 탭 바 */}
<div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
  {REV_TABS.map(t => (
    <button
      key={t.id}
      onClick={() => setTab(t.id)}
      className="px-5 py-2 rounded-lg text-xs font-medium transition-all"
      style={{ background: tab === t.id ? '#900000' : 'transparent', color: tab === t.id ? '#ffefea' : '#9b6060' }}
    >
      {t.label}
    </button>
  ))}
</div>
```

추세 탭 컴포넌트 (기존 return 내부 조건부):

```tsx
{tab === 'trend' && (
  <Card>
    <CardHeader>
      <CardTitle>월별 수익 추세</CardTitle>
      <CardDescription>AdSense + 제휴마케팅 월별 합산 추이</CardDescription>
    </CardHeader>
    <CardContent>
      {trendData.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">수익 데이터 없음 (Supabase 연동 후 표시)</p>
      ) : (
        <ChartContainer config={{ total: { label: '총수익', color: 'var(--chart-1)' }, adsense: { label: 'AdSense', color: 'var(--chart-2)' } }} className="h-64 w-full">
          <LineChart data={trendData}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} />
            <YAxis tickFormatter={(v) => formatKrw(v)} axisLine={false} tickLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Line type="monotone" dataKey="total" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="adsense" stroke="var(--chart-2)" strokeWidth={2} dot={false} strokeDasharray="4 2" />
          </LineChart>
        </ChartContainer>
      )}
    </CardContent>
  </Card>
)}
```

기존 컨텐츠 전체를 `{tab === 'current' && (...)}` 로 감싸기.

- [ ] **Step 4: 커밋**

```bash
git add web/app/revenue/page.tsx
git commit -m "feat: /revenue 월별 추세 탭 추가"
```

---

## Task 4: /risk 페이지 — 지속성 탭 구현

**Files:**
- Modify: `web/app/risk/page.tsx`

서버 컴포넌트이므로 클라이언트 탭 전환을 위해 래퍼 클라이언트 컴포넌트를 추가하거나, 지속성 탭을 별도 클라이언트 컴포넌트로 분리한다.
가장 단순한 방법: 기존 서버 컴포넌트는 유지, 페이지 하단에 `<SustainabilitySection />` (클라이언트 컴포넌트) 추가.
섹션 제목으로 "리스크 현황" / "지속성 분석" 구분.

- [ ] **Step 1: 클라이언트 지속성 컴포넌트 정의 (파일 상단에 'use client' 추가 불가 — 서버 컴포넌트)**

`web/app/risk/page.tsx` 상단에 아래를 추가. 파일 전체를 'use client'로 바꾸는 대신 클라이언트 컴포넌트를 동일 파일 내에서 분리한다.

파일 맨 위에 다음 import 추가:

```tsx
'use client'  // ← 이미 'use client' 없으면 추가 불가능. 서버 컴포넌트이므로 별도 파일 필요
```

**대안 (권장):** `web/app/risk/sustainability-section.tsx` 신규 파일 생성:

```tsx
'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

interface SustainabilityItem {
  channel_id?: string
  topic_capacity?: number
  depletion_risk?: 'HIGH' | 'MEDIUM' | 'LOW'
  remaining_unique_topics?: number
  estimated_months_left?: number
}

export function SustainabilitySection() {
  const [items, setItems] = useState<SustainabilityItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/sustainability')
      .then(r => r.ok ? r.json() : { sustainability: [] })
      .then(d => setItems(d.sustainability ?? []))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <Card>
      <CardContent className="py-8 text-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#ee2400] border-t-transparent mx-auto" />
      </CardContent>
    </Card>
  )

  const riskColor = (risk: string) => {
    if (risk === 'HIGH') return { bg: 'rgba(238,36,0,0.1)', text: '#ee2400' }
    if (risk === 'MEDIUM') return { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b' }
    return { bg: 'rgba(34,197,94,0.1)', text: '#22c55e' }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>주제 지속성 분석</h2>
        <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>채널별 주제 소진 위험도 — Step17 지속성 보고서 기반</p>
      </div>

      {items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-muted-foreground">지속성 데이터 없음 (파이프라인 Step17 완료 후 생성)</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => {
            const c = riskColor(item.depletion_risk ?? 'LOW')
            const capacity = item.topic_capacity ?? 0
            return (
              <Card key={item.channel_id ?? i}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{item.channel_id ?? `채널 ${i + 1}`}</CardTitle>
                    <Badge style={{ background: c.bg, color: c.text, border: 'none' }}>
                      {item.depletion_risk ?? 'N/A'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground">주제 용량</span>
                      <span className="font-medium">{(capacity * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={capacity * 100} className="h-1.5" />
                  </div>
                  {item.remaining_unique_topics != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">잔여 고유 주제</span>
                      <span className="font-medium">{item.remaining_unique_topics}개</span>
                    </div>
                  )}
                  {item.estimated_months_left != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">예상 지속 기간</span>
                      <span className="font-medium">{item.estimated_months_left}개월</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: risk/page.tsx 하단에 SustainabilitySection 추가**

```tsx
import { SustainabilitySection } from './sustainability-section'

// ... 기존 JSX 마지막 Card 닫기 태그 다음에 추가:
<SustainabilitySection />
```

- [ ] **Step 3: 커밋**

```bash
git add web/app/risk/page.tsx web/app/risk/sustainability-section.tsx
git commit -m "feat: /risk 지속성 탭 구현 (/api/sustainability 연동)"
```

---

## Task 5: /cost 페이지 — 예측 vs 실제 탭 + 이연업로드 탭 구조화

**Files:**
- Modify: `web/app/cost/page.tsx`

- [ ] **Step 1: 탭 타입 + 비용 예측 인터페이스 추가**

파일 상단 import 아래:

```tsx
const COST_TABS = [
  { id: 'quota',      label: '쿼터 현황' },
  { id: 'projection', label: '예측 vs 실제' },
  { id: 'deferred',   label: '이연 업로드' },
] as const
type CostTabId = typeof COST_TABS[number]['id']

interface CostProjection {
  estimated_total_krw?: number
  actual_total_krw?: number
  by_step?: Array<{ step: string; estimated_krw: number; actual_krw?: number }>
  generated_at?: string
}
```

- [ ] **Step 2: 탭 상태 + 비용 예측 fetch 추가**

`CostPage` 함수 내 기존 state 아래:

```tsx
const [costTab, setCostTab] = useState<CostTabId>('quota')
const [projection, setProjection] = useState<CostProjection | null>(null)

useEffect(() => {
  fetch('/api/cost/projection')
    .then(r => r.ok ? r.json() : { projection: null })
    .then(d => setProjection(d.projection))
}, [])
```

- [ ] **Step 3: 탭 바 추가 (헤딩 바로 다음)**

```tsx
<div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
  {COST_TABS.map(t => (
    <button
      key={t.id}
      onClick={() => setCostTab(t.id)}
      className="px-4 py-2 rounded-lg text-xs font-medium transition-all"
      style={{ background: costTab === t.id ? '#900000' : 'transparent', color: costTab === t.id ? '#ffefea' : '#9b6060' }}
    >
      {t.label}
      {t.id === 'deferred' && deferredJobs.length > 0 && (
        <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold" style={{ background: '#ee2400', color: '#ffefea' }}>
          {deferredJobs.length}
        </span>
      )}
    </button>
  ))}
</div>
```

- [ ] **Step 4: 예측 vs 실제 탭 JSX 추가**

기존 컨텐츠 아래(또는 기존 컨텐츠를 `{costTab === 'quota' && ...}` 로 감싸기):

```tsx
{costTab === 'projection' && (
  <div className="space-y-4">
    {projection === null ? (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-sm text-muted-foreground">비용 예측 데이터 없음 (파이프라인 실행 후 생성)</p>
          <p className="text-xs text-muted-foreground mt-1">data/global/cost_projection.json 에서 읽어옵니다</p>
        </CardContent>
      </Card>
    ) : (
      <>
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">예측 총비용</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">₩{(projection.estimated_total_krw ?? 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">pre_cost_estimator 산출값</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">실제 총비용</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">₩{(projection.actual_total_krw ?? 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">실제 API 과금 합산</p>
            </CardContent>
          </Card>
        </div>

        {projection.by_step && projection.by_step.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Step별 예측 vs 실제</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {projection.by_step.map((s, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b last:border-0 text-xs">
                    <span className="w-20 font-medium shrink-0" style={{ fontFamily: "'DM Mono', monospace" }}>{s.step}</span>
                    <div className="flex-1">
                      <div className="flex justify-between mb-1">
                        <span className="text-muted-foreground">예측: ₩{s.estimated_krw.toLocaleString()}</span>
                        <span>실제: ₩{(s.actual_krw ?? 0).toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(((s.actual_krw ?? 0) / (s.estimated_krw || 1)) * 100, 200)}%`,
                            background: (s.actual_krw ?? 0) > s.estimated_krw ? '#ee2400' : '#22c55e',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </>
    )}
  </div>
)}
```

- [ ] **Step 5: 이연업로드 탭 JSX — 기존 조건부 카드를 탭 내로 이동**

기존 `{deferredJobs.length > 0 && <Card>...</Card>}` 를 제거하고:

```tsx
{costTab === 'deferred' && (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-bold" style={{ color: '#1a0505' }}>이연된 YouTube 업로드</p>
        <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>쿼터 초과로 대기 중 · 잔여 {quotaRemaining.toLocaleString()} 단위</p>
      </div>
      <Button size="sm" variant="outline" onClick={handleRetry} disabled={retrying}
        className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10">
        {retrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
        재시도
      </Button>
    </div>
    {retryMsg && <p className="text-xs" style={{ color: '#22c55e' }}>{retryMsg}</p>}
    {deferredJobs.length === 0 ? (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-sm text-muted-foreground">이연된 업로드 없음 · YouTube 쿼터 정상</p>
        </CardContent>
      </Card>
    ) : (
      <Card>
        <CardContent className="pt-4 space-y-1.5">
          {deferredJobs.map((job, i) => (
            <div key={i} className="flex items-center justify-between p-2 rounded-lg text-sm"
              style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.08)' }}>
              <span style={{ fontFamily: "'DM Mono', monospace", color: '#ee2400', fontSize: '11px' }}>{job.channel_id}</span>
              <span className="flex-1 mx-3 truncate text-xs" style={{ color: '#5c1a1a' }}>{job.topic_title ?? job.run_id}</span>
              <Badge variant="outline" className="text-xs" style={{ borderColor: 'rgba(238,36,0,0.3)', color: '#ee2400' }}>대기</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    )}
  </div>
)}
```

- [ ] **Step 6: 커밋**

```bash
git add web/app/cost/page.tsx
git commit -m "feat: /cost 예측 vs 실제 탭 + 이연업로드 탭 구조화"
```

---

## Task 6: Run 상세 개선 — 썸네일 3종 + 제목 선택 저장 + Manim API 연동

**Files:**
- Modify: `web/app/runs/[channelId]/[runId]/page.tsx`
- Modify: `web/app/monitor/page.tsx`

- [ ] **Step 1: ThumbnailTab — 3종 비교 UI**

기존 `ThumbnailTab` 함수 전체 교체:

```tsx
function ThumbnailTab({ channelId, runId }: { channelId: string; runId: string }) {
  const variants = ['thumbnail_v1', 'thumbnail_v2', 'thumbnail_v3']
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {variants.map((v, i) => (
          <div key={v} style={G.card} className="p-4">
            <p className="text-xs font-bold mb-3" style={{ color: '#9b6060' }}>썸네일 {String.fromCharCode(65 + i)}</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/api/artifacts/${channelId}/${runId}/step10/${v}.jpg`}
              alt={`썸네일 ${String.fromCharCode(65 + i)}`}
              className="w-full rounded-lg"
              style={{ border: '1px solid rgba(238,36,0,0.12)', aspectRatio: '16/9', objectFit: 'cover' }}
              onError={e => {
                const el = e.target as HTMLImageElement
                if (el.src.endsWith('.jpg')) {
                  el.src = `/api/artifacts/${channelId}/${runId}/step10/${v}.png`
                } else {
                  el.style.display = 'none'
                }
              }}
            />
          </div>
        ))}
      </div>
      <p className="text-xs text-center" style={{ color: '#9b6060' }}>
        3종 썸네일 A/B/C 비교 · Step10 완료 후 생성됩니다
      </p>
    </div>
  )
}
```

ThumbnailTab 호출부 시그니처 변경 (artifacts prop 제거):
```tsx
{tab === 'thumbnail' && <ThumbnailTab channelId={channelId} runId={runId} />}
```

- [ ] **Step 2: TitleTab — 선택 저장 기능 추가**

기존 `TitleTab` 전체 교체:

```tsx
function TitleTab({ artifacts, channelId, runId }: { artifacts: RunArtifacts | null; channelId: string; runId: string }) {
  const titles = artifacts?.step08?.title_candidates ?? []
  const [selected, setSelected] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  if (!titles.length) return <EmptyState icon={Type} msg="제목 후보가 없습니다" sub="Step10 완료 후 생성됩니다" />

  const typeLabels = ['호기심 자극형', '권위 신뢰형', '이익 제공형']

  async function handleSelect(i: number) {
    setSelected(i)
    setSaving(true)
    setSaved(false)
    await fetch(`/api/runs/${channelId}/${runId}/seo`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_title_index: i, selected_title: (titles as string[])[i] }),
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-3">
      {saved && (
        <div className="px-4 py-2 rounded-xl text-sm font-medium" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>
          ✓ 제목이 저장되었습니다
        </div>
      )}
      {(titles as string[]).map((title: string, i: number) => (
        <div
          key={i}
          style={{
            ...G.card,
            border: selected === i ? '2px solid #ee2400' : '1px solid rgba(238,36,0,0.12)',
          }}
          className="p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: 'rgba(238,36,0,0.1)', color: '#ee2400' }}>
              {String.fromCharCode(65 + i)} — {typeLabels[i] ?? `타입 ${i + 1}`}
            </span>
            {selected === i && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full ml-auto" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>
                선택됨
              </span>
            )}
          </div>
          <p className="text-base font-medium leading-snug mb-3" style={{ color: '#1a0505' }}>{title}</p>
          <button
            onClick={() => handleSelect(i)}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg transition-all"
            style={{ background: selected === i ? 'rgba(34,197,94,0.1)' : 'rgba(238,36,0,0.08)', color: selected === i ? '#22c55e' : '#5c1a1a', border: `1px solid ${selected === i ? 'rgba(34,197,94,0.3)' : 'rgba(238,36,0,0.15)'}` }}
          >
            {saving && selected === i ? '저장 중...' : '이 제목 선택'}
          </button>
        </div>
      ))}
    </div>
  )
}
```

TitleTab 호출부 prop 추가:
```tsx
{tab === 'title' && <TitleTab artifacts={artifacts} channelId={channelId} runId={runId} />}
```

- [ ] **Step 3: monitor/page.tsx ManImPanel — /api/agents/status 연동**

기존 `ManImPanel` 함수 전체 교체:

```tsx
interface AgentStatus {
  name: string
  last_run_at?: string
  manim_fallback_rate?: number
  character_drift?: number
  error?: string
}

function ManImPanel() {
  const [agents, setAgents] = useState<AgentStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/agents/status')
      .then(r => r.ok ? r.json() : { agents: [] })
      .then(d => setAgents(d.agents ?? []))
      .finally(() => setLoading(false))
  }, [])

  const videoAgent = agents.find(a => a.name?.toLowerCase().includes('videostyle') || a.name?.toLowerCase().includes('video_style'))
  const fallbackRate = videoAgent?.manim_fallback_rate
  const charDrift = videoAgent?.character_drift
  const lastRun = videoAgent?.last_run_at

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} /></div>

  return (
    <div style={G.card} className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <Cpu className="h-5 w-5" style={{ color: '#ee2400' }} />
        <div>
          <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>Manim 렌더링 안정성</h3>
          <p className="text-xs" style={{ color: G.text.muted }}>Step08 Manim fallback 비율 모니터링</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-6">
        {[
          {
            label: 'Manim 성공률',
            value: fallbackRate != null ? `${((1 - fallbackRate) * 100).toFixed(0)}%` : '—',
            sub: '임계값: 50%',
            warn: fallbackRate != null && fallbackRate > 0.5,
          },
          {
            label: 'Fallback 비율',
            value: fallbackRate != null ? `${(fallbackRate * 100).toFixed(0)}%` : '—',
            sub: '이미지 대체 비율',
            warn: fallbackRate != null && fallbackRate > 0.5,
          },
          {
            label: '캐릭터 드리프트',
            value: charDrift != null ? charDrift.toFixed(2) : '—',
            sub: '임계값: 0.7',
            warn: charDrift != null && charDrift > 0.7,
          },
          {
            label: '마지막 체크',
            value: lastRun ? new Date(lastRun).toLocaleDateString('ko-KR') : '—',
            sub: 'VideoStyleAgent 실행 기준',
            warn: false,
          },
        ].map(item => (
          <div key={item.label} className="p-4 rounded-xl" style={{ background: item.warn ? 'rgba(238,36,0,0.08)' : 'rgba(238,36,0,0.04)', border: `1px solid rgba(238,36,0,${item.warn ? '0.2' : '0.08'})` }}>
            <p className="text-xs mb-1" style={{ color: G.text.muted }}>{item.label}</p>
            <p className="text-xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: item.warn ? '#ee2400' : '#1a0505' }}>{item.value}</p>
            <p className="text-[10px] mt-0.5" style={{ color: G.text.muted }}>{item.sub}</p>
          </div>
        ))}
      </div>
      {agents.length === 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(238,36,0,0.06)' }}>
          <p className="text-xs font-semibold mb-1" style={{ color: '#5c1a1a' }}>데이터 없음</p>
          <p className="text-xs" style={{ color: G.text.muted }}>Sub-Agent 탭에서 VideoStyleAgent를 실행하면 데이터가 생성됩니다.</p>
        </div>
      )}
    </div>
  )
}
```

`G.text` 상수가 monitor/page.tsx에 없으면 추가: `const G = { ..., text: { primary: '#1a0505', secondary: '#5c1a1a', muted: '#9b6060' } }`
(이미 정의되어 있으므로 확인 후 사용)

- [ ] **Step 4: 커밋**

```bash
git add "web/app/runs/[channelId]/[runId]/page.tsx" web/app/monitor/page.tsx
git commit -m "feat: 썸네일 3종 비교 + 제목 선택 저장 + Manim API 연동"
```

---

## Task 7: 홈 채널 수익 + /trends 채널 탭 + /knowledge 단계별 표시

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/trends/page.tsx`
- Modify: `web/app/knowledge/page.tsx`

### 7-A: 홈 채널별 수익 요약

- [ ] **Step 1: 홈에 채널 수익 요약 섹션 추가**

`web/app/page.tsx`에서 채널 카드 그리드 아래에 다음 서버 컴포넌트 섹션 추가:

```tsx
{/* 채널별 수익 현황 */}
<ScrollReveal>
  <section>
    <h2 className="text-sm font-bold mb-3" style={{ color: '#5c1a1a' }}>채널별 이번달 수익</h2>
    <div className="grid grid-cols-7 gap-2">
      {channels.map(ch => (
        <div key={ch.id} className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.45)', border: '1px solid rgba(238,36,0,0.1)' }}>
          <p className="text-xs font-bold" style={{ color: '#1a0505' }}>{ch.id}</p>
          <p className="text-[10px] mt-0.5 mb-2" style={{ color: '#9b6060' }}>{ch.category_ko}</p>
          <div className="h-1 rounded-full w-full mb-1" style={{ background: 'rgba(238,36,0,0.1)' }}>
            <div className="h-1 rounded-full" style={{ width: '0%', background: '#ee2400' }} />
          </div>
          <p className="text-[10px]" style={{ color: '#9b6060' }}>₩0</p>
        </div>
      ))}
    </div>
  </section>
</ScrollReveal>
```

(실제 수익 데이터는 Supabase 연동 전까지 ₩0 표시 — DB 연동 후 자동 반영됨)

### 7-B: /trends 채널별 탭 전환

- [ ] **Step 2: trends/page.tsx 채널 필터를 탭 버튼으로 교체**

기존 `Select` 채널 필터를 탭 버튼으로 교체.
`CHANNEL_OPTIONS = ['전체', 'CH1', ..., 'CH7']` 기반으로:

```tsx
{/* 채널 탭 버튼 — 기존 Select 대체 */}
<div className="flex gap-1 flex-wrap p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
  {CHANNEL_OPTIONS.map(ch => (
    <button
      key={ch}
      onClick={() => setChannelFilter(ch)}
      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
      style={{ background: channelFilter === ch ? '#900000' : 'transparent', color: channelFilter === ch ? '#ffefea' : '#9b6060' }}
    >
      {ch}
    </button>
  ))}
</div>
```

점수 구성 시각화 추가 (각 TopicRow 아래):

```tsx
{/* 점수 구성 배지 */}
<div className="flex gap-1 flex-wrap mt-1">
  {[
    { label: '관심도', pct: 40, value: Math.round(topic.score * 0.4) },
    { label: '적합도', pct: 25, value: Math.round(topic.score * 0.25) },
    { label: '수익성', pct: 20, value: Math.round(topic.score * 0.2) },
    { label: '긴급도', pct: 15, value: Math.round(topic.score * 0.15) },
  ].map(s => (
    <span key={s.label} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(238,36,0,0.07)', color: '#9b6060' }}>
      {s.label} {s.pct}%·{s.value}
    </span>
  ))}
</div>
```

### 7-C: /knowledge 단계별 표시

- [ ] **Step 3: knowledge/page.tsx TopicRow에 수집 단계 배지 추가**

기존 `TopicRow` 함수에서 `p.text-xs.text-muted-foreground` 텍스트 아래 단계 배지 추가:

```tsx
function TopicRow({ topic }: { topic: KnowledgeTopic }) {
  // topic.knowledge_stages 필드가 있으면 표시, 없으면 기본 단계 추정
  const stages = (topic as { knowledge_stages?: string[] }).knowledge_stages

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-snug truncate">{topic.reinterpreted_title || topic.original_topic}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {topic.category} · {topic.trend_collected_at?.slice(0, 10)}
        </p>
        {stages && stages.length > 0 && (
          <div className="flex gap-1 mt-1.5">
            {(['tavily', 'wikipedia', 'gemini'] as const).map(src => {
              const done = stages.includes(src)
              return (
                <span key={src} className="text-[9px] px-1.5 py-0.5 rounded font-medium" style={{
                  background: done ? 'rgba(34,197,94,0.1)' : 'rgba(238,36,0,0.06)',
                  color: done ? '#22c55e' : '#9b6060',
                  border: `1px solid ${done ? 'rgba(34,197,94,0.3)' : 'rgba(238,36,0,0.1)'}`,
                }}>
                  {src === 'tavily' ? 'Tavily' : src === 'wikipedia' ? 'Wiki' : 'Gemini'}
                </span>
              )
            })}
          </div>
        )}
      </div>
      {/* 기존 점수/배지 유지 */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">{topic.score.toFixed(1)}</span>
        <Badge className={cn('border text-xs', GRADE_CLASS[topic.grade] ?? 'border-white/20 text-white/60')}>
          {topic.grade}
        </Badge>
        {topic.is_trending && (
          <TrendingUp className="h-3.5 w-3.5 text-amber-400" />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 커밋**

```bash
git add web/app/page.tsx web/app/trends/page.tsx web/app/knowledge/page.tsx
git commit -m "feat: 홈 채널 수익 요약 + /trends 채널 탭 전환 + /knowledge 단계 배지"
```

---

## Task 8: globals.css — Red Light CSS 변수 표준화

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: :root에 --c-* / --t-* 변수 추가**

`web/app/globals.css`의 `:root {` 블록 내에 아래 변수들을 추가:

```css
:root {
  /* ... 기존 변수들 ... */

  /* ─── Red Light 팔레트 ─── */
  --c-dark:   #900000;
  --c-red:    #ee2400;
  --c-salmon: #ffb09c;
  --c-blush:  #fbd9d3;
  --c-cream:  #ffefea;

  /* ─── Red Light 텍스트 ─── */
  --t-primary:   #1a0505;
  --t-secondary: #5c1a1a;
  --t-muted:     #9b6060;
  --t-accent:    #900000;
  --t-on-dark:   #ffefea;
}
```

- [ ] **Step 2: 커밋**

```bash
git add web/app/globals.css
git commit -m "feat: Red Light --c-* / --t-* CSS 변수 표준화 (globals.css)"
```

---

## 전체 커밋 요약 (순서)

1. `fix: /api/files/ → /api/artifacts/ 경로 버그 수정` (Task 1)
2. `feat: /learning KPI·알고리즘·바이어스 3탭 구조 구현` (Task 2)
3. `feat: /revenue 월별 추세 탭 추가` (Task 3)
4. `feat: /risk 지속성 탭 구현` (Task 4)
5. `feat: /cost 예측 vs 실제 탭 + 이연업로드 탭 구조화` (Task 5)
6. `feat: 썸네일 3종 비교 + 제목 선택 저장 + Manim API 연동` (Task 6)
7. `feat: 홈 채널 수익 요약 + /trends 채널 탭 + /knowledge 단계 배지` (Task 7)
8. `feat: Red Light --c-* / --t-* CSS 변수 표준화` (Task 8)
