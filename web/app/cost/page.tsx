'use client'

import { CreditCard, Zap, PlayCircle } from 'lucide-react'
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

// 쿼터 상수 (config.py 기준)
const GEMINI_DAILY_IMAGE_LIMIT = 500
const YOUTUBE_DAILY_QUOTA = 10000
const YOUTUBE_UPLOAD_COST = 1700

// mock 데이터 (Supabase 연동 전)
const today = '2026-04-02'
const mockQuota = [
  {
    date: today,
    service: 'gemini',
    total_requests: 0,
    images_generated: 0,
    cache_hit_rate: 0,
    quota_used: 0,
    quota_remaining: GEMINI_DAILY_IMAGE_LIMIT,
    cost_krw: 0,
  },
  {
    date: today,
    service: 'youtube',
    total_requests: 0,
    images_generated: 0,
    cache_hit_rate: 0,
    quota_used: 0,
    quota_remaining: YOUTUBE_DAILY_QUOTA,
    cost_krw: 0,
  },
]

// 주간 사용량 차트 데이터 (mock)
const weeklyData = ['03-27', '03-28', '03-29', '03-30', '03-31', '04-01', '04-02'].map((d) => ({
  date: d,
  gemini: 0,
  youtube: 0,
}))

const chartConfig: ChartConfig = {
  gemini: { label: 'Gemini API', color: 'var(--chart-1)' },
  youtube: { label: 'YouTube API', color: 'var(--chart-3)' },
}

const geminiQuota = mockQuota.find((q) => q.service === 'gemini')!
const youtubeQuota = mockQuota.find((q) => q.service === 'youtube')!

const geminiImageRate = ((geminiQuota.images_generated / GEMINI_DAILY_IMAGE_LIMIT) * 100)
const youtubeUsedRate = ((youtubeQuota.quota_used / YOUTUBE_DAILY_QUOTA) * 100)
const uploadsRemaining = Math.floor(youtubeQuota.quota_remaining / YOUTUBE_UPLOAD_COST)

export default function CostPage() {
  const totalCostKrw = mockQuota.reduce((s, q) => s + q.cost_krw, 0)

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
            <Progress value={geminiImageRate} className="mt-2 h-1.5" />
            <p className="text-xs text-muted-foreground mt-1">
              {geminiImageRate.toFixed(1)}% 사용 · 캐시 히트율 {(geminiQuota.cache_hit_rate * 100).toFixed(0)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">YouTube 쿼터</CardTitle>
            <PlayCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {youtubeQuota.quota_used.toLocaleString()} / {YOUTUBE_DAILY_QUOTA.toLocaleString()}
            </div>
            <Progress value={youtubeUsedRate} className="mt-2 h-1.5" />
            <p className="text-xs text-muted-foreground mt-1">
              업로드 가능 잔여: {uploadsRemaining}건 (건당 {YOUTUBE_UPLOAD_COST.toLocaleString()}단위)
            </p>
          </CardContent>
        </Card>
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
