'use client'

import { useEffect, useState } from 'react'
import { DollarSign, TrendingUp, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from '@/components/ui/chart'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
} from 'recharts'
import { createClient } from '@/lib/supabase/client'

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

const CHANNEL_IDS = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7']
const TARGET = 2_000_000
const TOTAL_TARGET = 14_000_000
// 매달 수동 변경 불필요 — 실행 시점 기준 자동 계산
const CURRENT_MONTH = new Date().toISOString().slice(0, 7)

interface RevenueRow {
  channel_id: string
  month: string
  adsense_krw: number
  affiliate_krw: number
  net_profit: number
  target_achieved: boolean
}

const DEFAULT_REVENUE: RevenueRow[] = CHANNEL_IDS.map((id) => ({
  channel_id: id,
  month: CURRENT_MONTH,
  adsense_krw: 0,
  affiliate_krw: 0,
  net_profit: 0,
  target_achieved: false,
}))

const chartConfig: ChartConfig = {
  애드센스: { label: 'AdSense', color: 'var(--chart-1)' },
  제휴: { label: '제휴마케팅', color: 'var(--chart-2)' },
}

function formatKrw(v: number) {
  if (v >= 10000) return `₩${(v / 10000).toFixed(0)}만`
  return `₩${v.toLocaleString()}`
}

export default function RevenuePage() {
  const [revenue, setRevenue] = useState<RevenueRow[]>(DEFAULT_REVENUE)
  const [trendData, setTrendData] = useState<MonthlyTrend[]>([])
  const [tab, setTab] = useState<RevTabId>('current')

  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()
    supabase
      .from('revenue_monthly')
      .select('*')
      .eq('month', CURRENT_MONTH)
      .then(({ data }) => {
        if (!data || data.length === 0) return
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const rows = data as any[]
        setRevenue(
          CHANNEL_IDS.map((id) => {
            const row = rows.find((r) => r.channel_id === id)
            return {
              channel_id: id,
              month: CURRENT_MONTH,
              adsense_krw: row?.adsense_krw ?? 0,
              affiliate_krw: row?.affiliate_krw ?? 0,
              net_profit: row?.net_profit ?? 0,
              target_achieved: row?.target_achieved ?? false,
            }
          })
        )
      })
  }, [])

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
      .then(({ data }) => {
        if (!data) return
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

  const totalRevenue = revenue.reduce((s, r) => s + r.net_profit, 0)
  const achieveRate = (totalRevenue / TOTAL_TARGET) * 100
  const achievedCount = revenue.filter((r) => r.target_achieved).length

  const chartData = revenue.map((r) => ({
    channel: r.channel_id,
    애드센스: r.adsense_krw,
    제휴: r.affiliate_krw,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>수익 추적</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>월 목표: 채널당 200만원 / 전체 1,400만원</p>
      </div>

      {/* 탭 바 */}
      <div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: 'var(--tab-bg)', border: '1px solid var(--tab-border)' }}>
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

      {tab === 'current' && (<>
      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="dark:bg-green-500/[0.07] dark:border-green-500/20 glow-success">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">총 순이익</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₩{totalRevenue.toLocaleString()}</div>
            <div className="mt-2">
              <Progress value={achieveRate} className="h-1.5" />
              <p className="text-xs text-muted-foreground mt-1">{achieveRate.toFixed(1)}% / 목표 ₩14,000,000</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">목표 달성 채널</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{achievedCount} / 7</div>
            <p className="text-xs text-muted-foreground mt-1">이번달 목표 달성 채널 수</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">이번달</CardTitle>
            <Badge variant="outline">{CURRENT_MONTH}</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{achieveRate.toFixed(0)}%</div>
            <p className="text-xs text-muted-foreground mt-1">전체 달성률</p>
          </CardContent>
        </Card>
      </div>

      {/* 스택 바 차트 */}
      <Card>
        <CardHeader>
          <CardTitle>채널별 수익 구성</CardTitle>
          <CardDescription>AdSense + 제휴마케팅 수익 분포</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <BarChart data={chartData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="channel" tickLine={false} axisLine={false} />
              <YAxis tickFormatter={(v) => formatKrw(v)} axisLine={false} tickLine={false} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="애드센스" stackId="a" fill="var(--chart-1)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="제휴" stackId="a" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* 채널별 달성률 */}
      <Card>
        <CardHeader>
          <CardTitle>채널별 목표 달성률</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {revenue.map((r) => {
            const rate = Math.min((r.net_profit / TARGET) * 100, 100)
            return (
              <div key={r.channel_id} className="flex items-center gap-3">
                <span className="w-10 text-sm font-medium">{r.channel_id}</span>
                <Progress value={rate} className="flex-1 h-2" />
                <span className="w-20 text-right text-xs text-muted-foreground">
                  ₩{r.net_profit.toLocaleString()}
                </span>
                {r.target_achieved ? (
                  <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
      </>)}

      {tab === 'trend' && (
        <Card>
          <CardHeader>
            <CardTitle>월별 수익 추세</CardTitle>
            <CardDescription>AdSense + 제휴마케팅 월별 합산 추이</CardDescription>
          </CardHeader>
          <CardContent>
            {trendData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                수익 데이터 없음 (Supabase 연동 후 표시)
              </p>
            ) : (
              <ChartContainer
                config={{
                  total: { label: '총수익', color: 'var(--chart-1)' },
                  adsense: { label: 'AdSense', color: 'var(--chart-2)' },
                }}
                className="h-64 w-full"
              >
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
    </div>
  )
}
