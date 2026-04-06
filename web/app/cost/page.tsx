'use client'

import { useEffect, useState } from 'react'
import { CreditCard, Zap, PlayCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
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
import { createClient } from '@/lib/supabase/client'

// 쿼터 상수 (config.py 기준)
const GEMINI_DAILY_IMAGE_LIMIT = 500
const YOUTUBE_DAILY_QUOTA = 10000
const YOUTUBE_UPLOAD_COST = 1700

const chartConfig: ChartConfig = {
  gemini: { label: 'Gemini API', color: 'var(--chart-1)' },
  youtube: { label: 'YouTube API', color: 'var(--chart-3)' },
}

interface QuotaRow {
  date: string
  service: string
  total_requests: number
  images_generated: number
  cache_hit_rate: number
  quota_used: number
  quota_remaining: number
  cost_krw: number
}

const today = new Date().toISOString().slice(0, 10)

const DEFAULT_QUOTA: QuotaRow[] = [
  { date: today, service: 'gemini', total_requests: 0, images_generated: 0, cache_hit_rate: 0, quota_used: 0, quota_remaining: GEMINI_DAILY_IMAGE_LIMIT, cost_krw: 0 },
  { date: today, service: 'youtube', total_requests: 0, images_generated: 0, cache_hit_rate: 0, quota_used: 0, quota_remaining: YOUTUBE_DAILY_QUOTA, cost_krw: 0 },
]

// 최근 7일 날짜 배열 생성
function getLast7Days(): string[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    return d.toISOString().slice(5, 10)
  })
}

function GradientProgress({
  value,
  max,
  gradient,
  glowColor,
}: {
  value: number
  max: number
  gradient: string
  glowColor: string
}) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="relative mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{
          width: `${pct}%`,
          background: gradient,
          boxShadow: `0 0 8px ${glowColor}`,
        }}
      />
    </div>
  )
}

export default function CostPage() {
  const [quota, setQuota] = useState<QuotaRow[]>(DEFAULT_QUOTA)
  const [weeklyData, setWeeklyData] = useState(
    getLast7Days().map((d) => ({ date: d, gemini: 0, youtube: 0 }))
  )

  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6)
    const sinceDate = sevenDaysAgo.toISOString().slice(0, 10)

    supabase
      .from('quota_daily')
      .select('*')
      .gte('date', sinceDate)
      .order('date', { ascending: true })
      .then(({ data }) => {
        if (!data || data.length === 0) return
        const rows = data as QuotaRow[]

        // 오늘 데이터
        const todayRows = rows.filter((r) => r.date === today)
        if (todayRows.length > 0) setQuota(todayRows)

        // 주간 바차트 데이터
        const days = getLast7Days()
        setWeeklyData(
          days.map((d) => {
            const fullDate = `${new Date().getFullYear()}-${d}`
            const gemini = rows.find((r) => r.service === 'gemini' && r.date.slice(5, 10) === d)
            const youtube = rows.find((r) => r.service === 'youtube' && r.date.slice(5, 10) === d)
            return {
              date: d,
              gemini: gemini?.total_requests ?? 0,
              youtube: youtube?.total_requests ?? 0,
              _fullDate: fullDate,
            }
          })
        )
      })
  }, [])

  const geminiQuota = quota.find((q) => q.service === 'gemini') ?? DEFAULT_QUOTA[0]
  const youtubeQuota = quota.find((q) => q.service === 'youtube') ?? DEFAULT_QUOTA[1]
  const geminiImageRate = (geminiQuota.images_generated / GEMINI_DAILY_IMAGE_LIMIT) * 100
  const youtubeUsedRate = (youtubeQuota.quota_used / YOUTUBE_DAILY_QUOTA) * 100
  const uploadsRemaining = Math.floor(youtubeQuota.quota_remaining / YOUTUBE_UPLOAD_COST)
  const totalCostKrw = quota.reduce((s, q) => s + q.cost_krw, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">비용 / 쿼터 추적</h1>
        <p className="text-muted-foreground text-sm">Gemini & YouTube API 일간 사용량 및 비용</p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">오늘 총 비용</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₩{totalCostKrw.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">{today} 기준</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Gemini 이미지</CardTitle>
            <Zap className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {geminiQuota.images_generated} / {GEMINI_DAILY_IMAGE_LIMIT}
            </div>
            {(() => {
              const geminiQuotaData = quota.find((q) => q.service === 'gemini') ?? DEFAULT_QUOTA[0]
              return (
                <GradientProgress
                  value={geminiQuotaData.quota_used}
                  max={GEMINI_DAILY_IMAGE_LIMIT}
                  gradient="linear-gradient(90deg, #818cf8, #a78bfa)"
                  glowColor="rgba(139, 92, 246, 0.5)"
                />
              )
            })()}
            <p className="text-xs text-muted-foreground mt-1">
              {geminiImageRate.toFixed(1)}% 사용 · 캐시 히트율 {(geminiQuota.cache_hit_rate * 100).toFixed(0)}%
            </p>
          </CardContent>
        </Card>

        {(() => {
          const ytQuota = quota.find((q) => q.service === 'youtube')
          const ytUsed = ytQuota?.quota_used ?? 0
          const ytRate = ytUsed / YOUTUBE_DAILY_QUOTA
          return (
            <Card className={cn(ytRate >= 0.8 && 'glow-danger')}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">YouTube API</CardTitle>
                <PlayCircle
                  className={cn('h-4 w-4', ytRate >= 0.8 ? 'text-destructive' : 'text-muted-foreground')}
                />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{ytUsed.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">/ {YOUTUBE_DAILY_QUOTA.toLocaleString()} 단위</p>
                <GradientProgress
                  value={ytUsed}
                  max={YOUTUBE_DAILY_QUOTA}
                  gradient={
                    ytRate >= 0.8
                      ? 'linear-gradient(90deg, #ef4444, #f87171)'
                      : 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                  }
                  glowColor={
                    ytRate >= 0.8 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(245, 158, 11, 0.4)'
                  }
                />
                {ytRate >= 0.8 && (
                  <p className="text-xs text-destructive mt-1">⚠ 임계값 근접</p>
                )}
              </CardContent>
            </Card>
          )
        })()}
      </div>

      {/* 주간 사용량 바차트 */}
      <Card>
        <CardHeader>
          <CardTitle>주간 API 요청 추이</CardTitle>
          <CardDescription>Gemini + YouTube API 일별 요청 수</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <BarChart data={weeklyData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="gemini" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="youtube" fill="var(--chart-3)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* 서비스별 상세 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              <CardTitle className="text-sm">Gemini API 상세</CardTitle>
              <Badge variant="outline" className="ml-auto">일 500장</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">총 요청</span>
              <span className="font-medium">{geminiQuota.total_requests.toLocaleString()}건</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">이미지 생성</span>
              <span className="font-medium">{geminiQuota.images_generated}장</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">캐시 히트율</span>
              <span className="font-medium">{(geminiQuota.cache_hit_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">오늘 비용</span>
              <span className="font-medium text-green-600">₩{geminiQuota.cost_krw.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-red-500" />
              <CardTitle className="text-sm">YouTube API 상세</CardTitle>
              <Badge variant="outline" className="ml-auto">일 10,000단위</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">사용 쿼터</span>
              <span className="font-medium">{youtubeQuota.quota_used.toLocaleString()}단위</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">잔여 쿼터</span>
              <span className="font-medium">{youtubeQuota.quota_remaining.toLocaleString()}단위</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">업로드 가능</span>
              <span className="font-medium">{uploadsRemaining}건</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">오늘 비용</span>
              <span className="font-medium text-green-600">₩{youtubeQuota.cost_krw.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
