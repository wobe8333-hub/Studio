'use client'

import { use, useState, useEffect, useTransition } from 'react'
import { notFound } from 'next/navigation'
import {
  Tv, Activity, CheckCircle, XCircle, Clock,
  DollarSign, Users, Video, TrendingUp, MousePointerClick,
  Play, Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { createClient } from '@/lib/supabase/client'

// config.py CHANNEL_CATEGORY_KO 기준 fallback
const CHANNEL_DEFAULTS: Record<string, { category_ko: string; launch_phase: number }> = {
  CH1: { category_ko: '경제', launch_phase: 1 },
  CH2: { category_ko: '부동산', launch_phase: 1 },
  CH3: { category_ko: '심리', launch_phase: 2 },
  CH4: { category_ko: '미스터리', launch_phase: 2 },
  CH5: { category_ko: '전쟁사', launch_phase: 3 },
  CH6: { category_ko: '과학', launch_phase: 3 },
  CH7: { category_ko: '역사', launch_phase: 3 },
}

interface ChannelData {
  id: string
  category_ko: string
  algorithm_trust_level: string
  launch_phase: number
  subscriber_count: number
  video_count: number
  revenue_target: number
  net_profit: number
  ctr: number | null
  avp: number | null
}

interface RunRow {
  id: string
  topic_title: string | null
  run_state: string | null
  created_at: string | null
  completed_at: string | null
}

interface KpiPoint {
  date: string
  ctr: number
  avp: number
}

const chartConfig: ChartConfig = {
  ctr: { label: 'CTR (%)', color: 'var(--chart-1)' },
  avp: { label: 'AVP (%)', color: 'var(--chart-2)' },
}

function RunStateBadge({ state }: { state: string | null }) {
  if (state === 'COMPLETED') return <Badge className="bg-green-500 text-white">완료</Badge>
  if (state === 'FAILED') return <Badge variant="destructive">실패</Badge>
  if (state === 'RUNNING') return <Badge className="bg-blue-500 text-white">실행중</Badge>
  return <Badge variant="secondary">대기</Badge>
}

function formatKrw(value: number) {
  if (value >= 1_000_000) return `₩${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `₩${(value / 1_000).toFixed(0)}K`
  return `₩${value}`
}

export default function ChannelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const channelId = id.toUpperCase()
  const defaults = CHANNEL_DEFAULTS[channelId]

  if (!defaults) notFound()

  const [channel, setChannel] = useState<ChannelData>({
    id: channelId,
    category_ko: defaults.category_ko,
    algorithm_trust_level: 'PRE-ENTRY',
    launch_phase: defaults.launch_phase,
    subscriber_count: 0,
    video_count: 0,
    revenue_target: 2_000_000,
    net_profit: 0,
    ctr: null,
    avp: null,
  })
  const [runs, setRuns] = useState<RunRow[]>([])
  const [kpiHistory, setKpiHistory] = useState<KpiPoint[]>([])
  const [monthInput, setMonthInput] = useState(1)
  const [triggerMsg, setTriggerMsg] = useState('')
  const [isTriggerPending, startTrigger] = useTransition()

  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()
    const currentMonth = new Date().toISOString().slice(0, 7)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Promise.all([
      supabase.from('channels').select('*').eq('id', channelId).single() as any,
      supabase.from('revenue_monthly').select('net_profit').eq('channel_id', channelId).eq('month', currentMonth).single() as any,
      supabase.from('pipeline_runs').select('id, topic_title, run_state, created_at, completed_at').eq('channel_id', channelId).order('created_at', { ascending: false }).limit(10) as any,
      supabase.from('kpi_48h').select('ctr, avg_view_percentage, collected_at').eq('channel_id', channelId).order('collected_at', { ascending: true }).limit(7) as any,
    ]).then(([chRes, revRes, runsRes, kpiRes]: [any, any, any, any]) => {
      if (chRes.data) {
        const ch = chRes.data
        setChannel((prev) => ({
          ...prev,
          category_ko: ch.category_ko ?? prev.category_ko,
          algorithm_trust_level: ch.algorithm_trust_level ?? 'PRE-ENTRY',
          launch_phase: ch.launch_phase ?? prev.launch_phase,
          subscriber_count: ch.subscriber_count ?? 0,
          video_count: ch.video_count ?? 0,
          revenue_target: ch.revenue_target_monthly ?? 2_000_000,
          net_profit: (revRes.data?.net_profit as number | null) ?? 0,
        }))
      }
      if (runsRes.data) {
        setRuns(runsRes.data as RunRow[])
      }
      if (kpiRes.data && kpiRes.data.length > 0) {
        setKpiHistory(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          kpiRes.data.map((k: any) => ({
            date: k.collected_at?.slice(5, 10) ?? '',
            ctr: ((k.ctr ?? 0) * 100),
            avp: ((k.avg_view_percentage ?? 0) * 100),
          }))
        )
      }
    })
  }, [channelId])

  function handleTrigger() {
    startTrigger(async () => {
      const res = await fetch('/api/pipeline/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ month_number: monthInput }),
      })
      const data: { ok: boolean; message?: string; error?: string } = await res.json()
      setTriggerMsg(data.message ?? (data.ok ? '시작됨' : data.error ?? '실패'))
    })
  }

  const isActive = channel.launch_phase === 1
  const achieveRate = channel.revenue_target > 0
    ? Math.min((channel.net_profit / channel.revenue_target) * 100, 100)
    : 0

  // KPI 히스토리: 데이터 없으면 기본 0 플레이스홀더
  const chartData = kpiHistory.length > 0 ? kpiHistory : [{ date: '—', ctr: 0, avp: 0 }]

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Tv className="h-5 w-5" style={{ color: '#ee2400' }} />
            <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>{channel.id} — {channel.category_ko}</h1>
          </div>
          <p className="text-sm mt-1" style={{ color: '#9b6060' }}>채널 상세 현황 및 KPI 이력</p>
        </div>
        <Badge variant={isActive ? 'default' : 'secondary'} className="mt-1">
          {isActive ? '활성' : '대기'}
        </Badge>
      </div>

      {/* 주요 KPI 카드 */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="col-span-2 sm:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">월 수익 달성률</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">{formatKrw(channel.net_profit)}</div>
              <div className="text-sm text-muted-foreground">/ {formatKrw(channel.revenue_target)}</div>
            </div>
            <Progress value={achieveRate} className="h-2" />
            <p className="text-xs text-muted-foreground">{achieveRate.toFixed(0)}% 달성</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">평균 CTR</CardTitle>
            <MousePointerClick className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {channel.ctr != null ? `${channel.ctr.toFixed(1)}%` : '—'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">목표: 4% 이상</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">평균 시청률</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {channel.avp != null ? `${channel.avp.toFixed(1)}%` : '—'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">AVP (시청 완료율)</p>
          </CardContent>
        </Card>
      </div>

      {/* 채널 메타 카드 */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">알고리즘 단계</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1.5">
              <Activity className="h-4 w-4 text-blue-500" />
              <span className="font-semibold text-sm">{channel.algorithm_trust_level}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">구독자</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1.5">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-xl font-bold">
                {channel.subscriber_count > 0 ? channel.subscriber_count.toLocaleString() : '—'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">업로드 영상</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1.5">
              <Video className="h-4 w-4 text-muted-foreground" />
              <span className="text-xl font-bold">{channel.video_count}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">런치 단계</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">Phase {channel.launch_phase}</Badge>
          </CardContent>
        </Card>
      </div>

      {/* KPI 히스토리 라인차트 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI 히스토리</CardTitle>
          <CardDescription>일별 CTR · AVP 추이 (업로드 후 48h 수집)</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-56 w-full">
            <LineChart data={chartData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} unit="%" />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line type="monotone" dataKey="ctr" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="avp" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
            </LineChart>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* 파이프라인 실행 이력 */}
      <Card>
        <CardHeader>
          <CardTitle>파이프라인 실행 이력</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">실행 이력이 없습니다.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>실행 ID</TableHead>
                  <TableHead>주제</TableHead>
                  <TableHead className="text-center">상태</TableHead>
                  <TableHead className="text-center">시작</TableHead>
                  <TableHead className="text-center">완료</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {run.id.slice(0, 20)}
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <p className="truncate text-sm">{run.topic_title ?? '—'}</p>
                    </TableCell>
                    <TableCell className="text-center">
                      <RunStateBadge state={run.run_state} />
                    </TableCell>
                    <TableCell className="text-center text-xs text-muted-foreground">
                      <div className="flex items-center justify-center gap-1">
                        <Clock className="h-3 w-3" />
                        {run.created_at?.slice(0, 10) ?? '—'}
                      </div>
                    </TableCell>
                    <TableCell className="text-center text-xs">
                      {run.completed_at ? (
                        <div className="flex items-center justify-center gap-1 text-green-600">
                          <CheckCircle className="h-3 w-3" />
                          {run.completed_at.slice(0, 10)}
                        </div>
                      ) : (
                        <div className="flex items-center justify-center gap-1 text-muted-foreground">
                          <XCircle className="h-3 w-3" />
                          미완료
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 파이프라인 트리거 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Play className="h-4 w-4 text-green-400" />
            파이프라인 실행
          </CardTitle>
          <CardDescription>
            월간 파이프라인을 백그라운드로 시작합니다. 완료까지 수분~수시간 소요될 수 있습니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="month-input" className="text-sm text-muted-foreground whitespace-nowrap">
                월 번호
              </label>
              <input
                id="month-input"
                type="number"
                min={1}
                max={12}
                value={monthInput}
                onChange={(e) => setMonthInput(Number(e.target.value))}
                className="w-16 rounded-md border border-input bg-background px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <Button
              onClick={handleTrigger}
              disabled={isTriggerPending}
              className="bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
            >
              {isTriggerPending
                ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                : <Play className="h-3.5 w-3.5 mr-1.5" />}
              실행
            </Button>
          </div>
          {triggerMsg && (
            <p className="mt-2 text-xs text-green-400">{triggerMsg}</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
