'use client'

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
} from 'recharts'

const CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7']
const TARGET = 2_000_000
const TOTAL_TARGET = 14_000_000

// Supabase 연동 전 mock 데이터
const mockRevenue = CHANNELS.map((id) => ({
  channel_id: id,
  month: '2026-04',
  adsense_krw: 0,
  affiliate_krw: 0,
  net_profit: 0,
  target_achieved: false,
}))

const chartData = CHANNELS.map((id) => {
  const r = mockRevenue.find((r) => r.channel_id === id)
  return {
    channel: id,
    애드센스: r?.adsense_krw ?? 0,
    제휴: r?.affiliate_krw ?? 0,
  }
})

const chartConfig: ChartConfig = {
  애드센스: { label: 'AdSense', color: 'var(--chart-1)' },
  제휴: { label: '제휴마케팅', color: 'var(--chart-2)' },
}

function formatKrw(v: number) {
  return `₩${(v / 10000).toFixed(0)}만`
}

export default function RevenuePage() {
  const totalRevenue = mockRevenue.reduce((s, r) => s + r.net_profit, 0)
  const achieveRate = (totalRevenue / TOTAL_TARGET) * 100
  const achievedCount = mockRevenue.filter((r) => r.target_achieved).length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">수익 추적</h1>
        <p className="text-muted-foreground text-sm">월 목표: 채널당 200만원 / 전체 1,400만원</p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
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
            <Badge variant="outline">2026-04</Badge>
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

      {/* 채널별 달성률 테이블 */}
      <Card>
        <CardHeader>
          <CardTitle>채널별 목표 달성률</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {mockRevenue.map((r) => {
            const rate = (r.net_profit / TARGET) * 100
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
    </div>
  )
}
