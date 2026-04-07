'use client'

import { useEffect, useState, useTransition } from 'react'
import { CreditCard, Zap, PlayCircle, RefreshCw, Clock, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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

// 탭 정의
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
  const [deferredJobs, setDeferredJobs] = useState<Array<{
    channel_id: string; run_id: string; topic_title?: string
  }>>([])
  const [quotaRemaining, setQuotaRemaining] = useState(10000)
  const [retrying, startRetry] = useTransition()
  const [retryMsg, setRetryMsg] = useState('')
  const [costTab, setCostTab] = useState<CostTabId>('quota')
  const [projection, setProjection] = useState<CostProjection | null>(null)

  useEffect(() => {
    fetch('/api/cost/projection')
      .then(r => r.ok ? r.json() : { projection: null })
      .then(d => setProjection(d?.projection ?? null))
      .catch(() => setProjection(null))
  }, [])

  useEffect(() => {
    fetch('/api/deferred-jobs')
      .then((r) => r.json())
      .then((d: { deferred_jobs: Array<{ channel_id: string; run_id: string; topic_title?: string }>; quota_remaining: number }) => {
        setDeferredJobs(d.deferred_jobs ?? [])
        setQuotaRemaining(d.quota_remaining ?? 10000)
      })
      .catch(() => {})
  }, [])

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

  function handleRetry() {
    startRetry(async () => {
      const res = await fetch('/api/deferred-jobs', { method: 'POST' })
      const data: { ok: boolean; message?: string; error?: string } = await res.json()
      setRetryMsg(data.message ?? (data.ok ? '시작됨' : data.error ?? '실패'))
    })
  }

  const geminiQuota = quota.find((q) => q.service === 'gemini') ?? DEFAULT_QUOTA[0]
  const youtubeQuota = quota.find((q) => q.service === 'youtube') ?? DEFAULT_QUOTA[1]
  const geminiImageRate = (geminiQuota.images_generated / GEMINI_DAILY_IMAGE_LIMIT) * 100
  const uploadsRemaining = Math.floor(youtubeQuota.quota_remaining / YOUTUBE_UPLOAD_COST)
  const totalCostKrw = quota.reduce((s, q) => s + q.cost_krw, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>비용 / 쿼터 추적</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>Gemini & YouTube API 일간 사용량 및 비용</p>
      </div>

      {/* 탭 바 */}
      <div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
        {COST_TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setCostTab(t.id)}
            className="px-4 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5"
            style={{ background: costTab === t.id ? '#900000' : 'transparent', color: costTab === t.id ? '#ffefea' : '#9b6060' }}
          >
            {t.label}
            {t.id === 'deferred' && deferredJobs.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold" style={{ background: '#ee2400', color: '#ffefea' }}>
                {deferredJobs.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 쿼터 현황 탭 */}
      {costTab === 'quota' && (
        <div className="space-y-6">

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
      )}{/* 쿼터 현황 탭 끝 */}

      {/* 예측 vs 실제 탭 */}
      {costTab === 'projection' && (
        <div className="space-y-4">
          {projection === null ? (
            <Card>
              <CardContent className="py-10 text-center">
                <p className="text-sm text-muted-foreground">비용 예측 데이터 없음</p>
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
                    <CardTitle className="text-sm">Step별 예측 vs 실제</CardTitle>
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

      {/* 이연 업로드 탭 */}
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
    </div>
  )
}
