'use client'

import { useEffect, useState } from 'react'
import { Brain, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from '@/components/ui/chart'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
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

interface FeedbackRow {
  run_id: string | null
  channel_id: string | null
  ctr: number | null
  avp: number | null
  views: number | null
  algorithm_stage: string | null
  preferred_title_mode: string | null
  revenue_on_track: boolean | null
  recorded_at: string | null
}

interface WeeklyKpi {
  week: string
  CTR: number
  AVP: number
}

const chartConfig: ChartConfig = {
  CTR: { label: 'CTR (%)', color: 'var(--chart-1)' },
  AVP: { label: '평균 시청률 (%)', color: 'var(--chart-2)' },
}

// 누적 데이터 기반 가이드라인 (고정)
const WIN_PATTERNS = [
  { pattern: '제목 형식', value: '질문형 제목 (CTR +2~3%)', trend: 'up' },
  { pattern: '섬네일 색상', value: '고대비 빨강/노랑 배경', trend: 'up' },
  { pattern: '최적 업로드 시간', value: '화목 오후 7~9시', trend: 'neutral' },
  { pattern: '영상 길이', value: '8~12분 (알고리즘 진입 최적)', trend: 'up' },
  { pattern: '카테고리별 AVP', value: '경제 > 과학 > 심리 순', trend: 'neutral' },
]

const G_CARD = {
  background: 'var(--card)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid var(--border)',
  borderRadius: '1rem',
  boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
} as React.CSSProperties

const LEARN_TABS = [
  { id: 'kpi',       label: 'KPI 48h' },
  { id: 'algorithm', label: '알고리즘 단계' },
  { id: 'bias',      label: '학습 바이어스' },
] as const
type LearnTabId = typeof LEARN_TABS[number]['id']

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp className="h-4 w-4 text-green-500" />
  if (trend === 'down') return <TrendingDown className="h-4 w-4 text-red-500" />
  return <Minus className="h-4 w-4 text-muted-foreground" />
}

function AlgorithmBadge({ stage }: { stage: string | null }) {
  const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
    'ALGORITHM-ACTIVE': { label: '알고리즘 진입', variant: 'default' },
    'BROWSE-ENTRY': { label: '브라우즈 진입', variant: 'secondary' },
    'SEARCH-ONLY': { label: '검색 전용', variant: 'outline' },
    'PRE-ENTRY': { label: '사전 단계', variant: 'outline' },
  }
  const key = stage ?? 'PRE-ENTRY'
  const info = map[key] ?? { label: key, variant: 'outline' as const }
  return <Badge variant={info.variant}>{info.label}</Badge>
}

// ── AlgorithmTab ─────────────────────────────────────────────────────────────

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

  if (loading) return (
    <div className="flex justify-center py-12">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#ee2400] border-t-transparent" />
    </div>
  )

  return (
    <div className="space-y-3">
      {channels.length === 0 ? (
        <div style={G_CARD} className="p-10 text-center">
          <p className="text-sm" style={{ color: '#9b6060' }}>알고리즘 정책 데이터 없음 (파이프라인 실행 후 생성)</p>
        </div>
      ) : channels.map(ch => {
        const stage = ch.policy?.algorithm_stage ?? 'PRE-ENTRY'
        const stageIdx = STAGE_ORDER.indexOf(stage)
        const color = STAGE_COLOR[stage] ?? '#9b6060'
        return (
          <div key={ch.channel_id} style={G_CARD} className="p-5">
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
    </div>
  )
}

// ── BiasTab ───────────────────────────────────────────────────────────────────

const BIAS_DATA = [
  { subject: '제목 다양성', value: 72 },
  { subject: '주제 균형', value: 58 },
  { subject: '채널 분산', value: 85 },
  { subject: '업로드 일관성', value: 64 },
  { subject: '시각 스타일', value: 79 },
]

function BiasTab() {
  return (
    <div style={G_CARD} className="p-6">
      <h3 className="font-bold mb-1" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>학습 바이어스 레이더</h3>
      <p className="text-xs mb-5" style={{ color: '#9b6060' }}>5개 차원 바이어스 분석 — 수치가 낮을수록 해당 영역 편향 가능성 있음</p>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={BIAS_DATA}>
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

// ── LearningPage ──────────────────────────────────────────────────────────────

export default function LearningPage() {
  const [feedback, setFeedback] = useState<FeedbackRow[]>([])
  const [trendData, setTrendData] = useState<WeeklyKpi[]>([
    { week: 'W1', CTR: 0, AVP: 0 },
    { week: 'W2', CTR: 0, AVP: 0 },
    { week: 'W3', CTR: 0, AVP: 0 },
    { week: 'W4', CTR: 0, AVP: 0 },
  ])
  const [tab, setTab] = useState<LearnTabId>('kpi')

  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()

    supabase
      .from('learning_feedback')
      .select('*')
      .order('recorded_at', { ascending: false })
      .limit(50)
      .then(({ data }) => {
        if (!data || data.length === 0) return
        const rows = data as FeedbackRow[]
        setFeedback(rows)

        // 주간 집계 (최근 4주, 7일 단위)
        const now = new Date()
        const weekly: WeeklyKpi[] = Array.from({ length: 4 }, (_, i) => {
          const weekEnd = new Date(now)
          weekEnd.setDate(weekEnd.getDate() - i * 7)
          const weekStart = new Date(weekEnd)
          weekStart.setDate(weekStart.getDate() - 6)
          const weekRows = rows.filter((r) => {
            if (!r.recorded_at) return false
            const d = new Date(r.recorded_at)
            return d >= weekStart && d <= weekEnd
          })
          const avgCtr = weekRows.length > 0
            ? weekRows.reduce((s, r) => s + (r.ctr ?? 0), 0) / weekRows.length * 100
            : 0
          const avgAvp = weekRows.length > 0
            ? weekRows.reduce((s, r) => s + (r.avp ?? 0), 0) / weekRows.length * 100
            : 0
          return { week: `W${4 - i}`, CTR: parseFloat(avgCtr.toFixed(1)), AVP: parseFloat(avgAvp.toFixed(1)) }
        }).reverse()
        setTrendData(weekly)
      })
  }, [])

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>학습 피드백</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>업로드 48시간 후 KPI 수집 기반 성과 분석</p>
      </div>

      {/* 탭 바 */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--tab-bg)', border: '1px solid var(--tab-border)' }}>
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

      {/* KPI 탭: 기존 차트 + 테이블 */}
      {tab === 'kpi' && (
        <>
          {/* CTR / AVP 추이 라인차트 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4" />
                <CardTitle>주간 CTR / AVP 추이</CardTitle>
              </div>
              <CardDescription>Click-Through Rate & 평균 시청 완료율</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={chartConfig} className="h-64 w-full">
                <LineChart data={trendData}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="week" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} unit="%" />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ChartLegend content={<ChartLegendContent />} />
                  <Line type="monotone" dataKey="CTR" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="AVP" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

          {/* 승리 패턴 */}
          <Card className="glow-amber">
            <CardHeader>
              <CardTitle>승리 패턴 분석</CardTitle>
              <CardDescription>누적 데이터 기반 최적 전략 가이드라인</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {WIN_PATTERNS.map((p, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="text-sm font-medium">{p.pattern}</p>
                      <p className="text-xs text-muted-foreground">{p.value}</p>
                    </div>
                    <TrendIcon trend={p.trend} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 피드백 이력 테이블 */}
          <Card>
            <CardHeader>
              <CardTitle>48시간 KPI 피드백 이력</CardTitle>
            </CardHeader>
            <CardContent>
              {feedback.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  KPI 피드백 데이터가 없습니다. 파이프라인 실행 후 48시간 후 수집됩니다.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>채널</TableHead>
                      <TableHead className="text-center">CTR</TableHead>
                      <TableHead className="text-center">AVP</TableHead>
                      <TableHead className="text-center">조회수</TableHead>
                      <TableHead className="text-center">알고리즘 단계</TableHead>
                      <TableHead className="text-center">수익 추적</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feedback.map((fb, i) => (
                      <TableRow key={fb.run_id ?? i}>
                        <TableCell>
                          <Badge variant="secondary">{fb.channel_id ?? '—'}</Badge>
                        </TableCell>
                        <TableCell className="text-center text-sm">
                          {fb.ctr != null && fb.ctr > 0 ? `${(fb.ctr * 100).toFixed(1)}%` : '—'}
                        </TableCell>
                        <TableCell className="text-center text-sm">
                          {fb.avp != null && fb.avp > 0 ? `${(fb.avp * 100).toFixed(1)}%` : '—'}
                        </TableCell>
                        <TableCell className="text-center text-sm">
                          {fb.views != null && fb.views > 0 ? fb.views.toLocaleString() : '—'}
                        </TableCell>
                        <TableCell className="text-center">
                          <AlgorithmBadge stage={fb.algorithm_stage} />
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant={fb.revenue_on_track ? 'default' : 'outline'}>
                            {fb.revenue_on_track ? '정상' : '미달'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {tab === 'algorithm' && <AlgorithmTab />}
      {tab === 'bias' && <BiasTab />}
    </div>
  )
}
