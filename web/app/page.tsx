import Link from 'next/link'
import {
  Eye,
  MousePointerClick,
  DollarSign,
  Activity,
  CheckCircle,
  XCircle,
  TrendingUp,
  AlertTriangle,
  Clock,
  PlayCircle,
  Zap,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { createClient } from '@/lib/supabase/server'
import type { Channel, PipelineRun } from '@/lib/types'
import { Sparkline, RadialGauge, ChannelDots } from '@/components/home-charts'
import { StaggerContainer, StaggerItem, ScrollReveal, AnimatedCard } from '@/components/animated-sections'
import { cn } from '@/lib/utils'

// Supabase 미연동 시 사용할 fallback mock 데이터
// config.py SSOT 기준 채널 정보 (CH1~CH7)
const MOCK_CHANNELS: Channel[] = [
  { id: 'CH1', category: 'economy',     category_ko: '경제',    youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH2', category: 'realestate',  category_ko: '부동산',  youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH3', category: 'psychology',  category_ko: '심리',    youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH4', category: 'mystery',     category_ko: '미스터리', youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH5', category: 'war_history', category_ko: '전쟁사',  youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH6', category: 'science',     category_ko: '과학',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH7', category: 'history',     category_ko: '역사',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
]

const MOCK_RUNS: PipelineRun[] = [
  { id: 'run_001', channel_id: 'CH1', run_state: 'PENDING', topic_title: '금리 인상이 내 지갑을 얇게 만드는 5가지 방법', topic_category: 'economy', topic_score: 85, is_trending: true, created_at: '2026-04-02T09:00:00', completed_at: null },
  { id: 'run_002', channel_id: 'CH2', run_state: 'PENDING', topic_title: '양자컴퓨터가 현실이 된다면 우리 생활은?', topic_category: 'science', topic_score: 91, is_trending: true, created_at: '2026-04-02T09:05:00', completed_at: null },
]

async function fetchData() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) {
    return { channels: MOCK_CHANNELS, runs: MOCK_RUNS }
  }

  try {
    const supabase = await createClient()
    const [{ data: channels }, { data: runs }] = await Promise.all([
      supabase.from('channels').select('*').order('id'),
      supabase.from('pipeline_runs').select('*').order('created_at', { ascending: false }).limit(5),
    ])
    return {
      channels: (channels ?? MOCK_CHANNELS) as Channel[],
      runs: (runs ?? MOCK_RUNS) as PipelineRun[],
    }
  } catch {
    return { channels: MOCK_CHANNELS, runs: MOCK_RUNS }
  }
}

function formatKrw(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return `${value}`
}

function RunStateBadge({ state }: { state: string }) {
  if (state === 'COMPLETED') return <Badge className="bg-green-500 text-white text-xs">완료</Badge>
  if (state === 'FAILED') return <Badge variant="destructive" className="text-xs">실패</Badge>
  if (state === 'RUNNING') return <Badge className="bg-blue-500 text-white text-xs">실행중</Badge>
  return <Badge variant="secondary" className="text-xs">대기</Badge>
}

// 파이프라인 타임라인 노드 색상
function TimelineNode({ state }: { state: string }) {
  if (state === 'COMPLETED') return (
    <span className="relative z-10 mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border-2 border-green-500 bg-background">
      <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
    </span>
  )
  if (state === 'FAILED') return (
    <span className="relative z-10 mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border-2 border-destructive bg-background">
      <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
    </span>
  )
  if (state === 'RUNNING') return (
    <span className="relative z-10 mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border-2 border-blue-500 bg-background">
      <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
    </span>
  )
  return (
    <span className="relative z-10 mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border-2 border-yellow-500 bg-background">
      <span className="h-1.5 w-1.5 rounded-full bg-yellow-400" />
    </span>
  )
}

export default async function HomePage() {
  const { channels, runs } = await fetchData()

  const activeChannels = channels.filter((ch) => ch.launch_phase === 1)
  const runningCount = runs.filter((r) => r.run_state === 'RUNNING').length
  const pendingCount = runs.filter((r) => r.run_state === 'PENDING').length

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 배경 메시 그라데이션 */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-mesh-warm" />

      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-3xl font-heading font-bold tracking-tight">
          전체 KPI 대시보드
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          7채널 AI 자동화 파이프라인 현황 — 월 목표: 1,400만원
        </p>
      </div>

      {/* 총괄 요약 KPI 카드 — stagger 입장 애니메이션 */}
      <StaggerContainer className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {/* 월 총 목표 */}
        <StaggerItem>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">월 총 목표</CardTitle>
              <DollarSign className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-heading font-bold tabular-nums">₩14,000,000</div>
              <p className="text-xs text-muted-foreground mt-1">채널당 ₩2,000,000</p>
              <Sparkline data={[0, 0, 0, 0, 0, 0, 0]} color="var(--chart-1)" />
            </CardContent>
          </Card>
        </StaggerItem>

        {/* 활성 채널 */}
        <StaggerItem>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">활성 채널</CardTitle>
              <Activity className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-heading font-bold tabular-nums">
                {activeChannels.length} <span className="text-muted-foreground">/ {channels.length}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Phase 1 ({activeChannels.map((c) => c.id).join(', ')})
              </p>
              <ChannelDots activeIds={activeChannels.map((c) => c.id)} />
            </CardContent>
          </Card>
        </StaggerItem>

        {/* 달성률 */}
        <StaggerItem>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">이번달 달성률</CardTitle>
              <TrendingUp className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-heading font-bold tabular-nums">0%</div>
              <RadialGauge value={0} color="var(--chart-1)" />
            </CardContent>
          </Card>
        </StaggerItem>

        {/* 리스크 채널 */}
        <StaggerItem>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">리스크 채널</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-heading font-bold tabular-nums">
                0 <span className="text-muted-foreground">/ {channels.length}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">HIGH 리스크 없음</p>
              <div className="flex items-center gap-1 mt-2">
                <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                <span className="text-xs text-green-600 dark:text-green-400">모두 안전</span>
              </div>
            </CardContent>
          </Card>
        </StaggerItem>
      </StaggerContainer>

      {/* 파이프라인 현황 + 채널별 현황 */}
      <ScrollReveal className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 파이프라인 타임라인 */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <PlayCircle className="h-4 w-4 text-primary" />
                  {runningCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                  )}
                </div>
                <CardTitle className="text-base">파이프라인</CardTitle>
              </div>
              <div className="flex gap-1.5">
                {runningCount > 0 && (
                  <Badge className="bg-blue-500 text-white text-xs">{runningCount} 실행중</Badge>
                )}
                {pendingCount > 0 && (
                  <Badge variant="secondary" className="text-xs">{pendingCount} 대기</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {runs.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">실행 이력 없음</p>
            ) : (
              <div className="relative">
                {/* 수직 타임라인 연결선 */}
                <div className="absolute left-[6px] top-3 bottom-3 w-px bg-border" />
                <div className="space-y-4">
                  {runs.map((run) => (
                    <div key={run.id} className="flex gap-3">
                      <TimelineNode state={run.run_state ?? 'PENDING'} />
                      <div className="flex-1 min-w-0 pb-1">
                        <div className="flex items-center justify-between gap-2 mb-0.5">
                          <Link
                            href={`/channels/${run.channel_id}`}
                            className="text-xs font-heading font-semibold text-primary hover:underline"
                          >
                            {run.channel_id}
                          </Link>
                          <RunStateBadge state={run.run_state ?? 'PENDING'} />
                        </div>
                        <p className="text-xs text-muted-foreground truncate">
                          {run.topic_title ?? '주제 없음'}
                        </p>
                        {run.created_at && (
                          <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                            {new Date(run.created_at).toLocaleDateString('ko-KR', {
                              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 채널별 현황 카드 그리드 */}
        <div className="lg:col-span-2">
          <h2 className="text-base font-heading font-semibold mb-3">채널별 현황</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {channels.map((ch, i) => (
              <AnimatedCard key={ch.id} delay={i * 0.06}>
                <ChannelCard channel={ch} />
              </AnimatedCard>
            ))}
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}

function ChannelCard({ channel }: { channel: Channel }) {
  const isActive = channel.launch_phase === 1
  const target = channel.revenue_target_monthly ?? 2000000
  const revenue = 0
  const achieveRate = (revenue / target) * 100
  const channelColorVar = `var(--channel-${channel.id.toLowerCase()})`

  return (
    <Link href={`/channels/${channel.id}`}>
      <Card
        className={cn(
          'cursor-pointer border-l-[3px] transition-shadow',
          !isActive && 'opacity-55 hover:opacity-80'
        )}
        style={{ borderLeftColor: channelColorVar }}
      >
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* 채널 색상 dot */}
              <span
                className="h-2.5 w-2.5 rounded-full shrink-0 ring-1 ring-inset ring-black/10 dark:ring-white/10"
                style={{
                  backgroundColor: channelColorVar,
                  boxShadow: isActive ? `0 0 7px ${channelColorVar}` : 'none',
                }}
              />
              <div>
                <CardTitle className="text-base">{channel.category_ko}</CardTitle>
                <p className="text-[10px] text-muted-foreground font-mono">{channel.id}</p>
              </div>
            </div>
            <Badge
              variant={isActive ? 'default' : 'secondary'}
              className="text-[10px]"
            >
              {isActive ? 'LIVE' : `P${channel.launch_phase}`}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* 월 수익 Progress */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">월 수익</span>
              <span className="font-medium font-mono tabular-nums">
                ₩{formatKrw(revenue)} / ₩{formatKrw(target)}
              </span>
            </div>
            <Progress value={achieveRate} className="h-1.5" />
          </div>

          {/* 3열 KPI 메트릭 */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="flex items-center justify-center gap-1 text-muted-foreground">
                <Eye className="h-3 w-3" />
                <span className="text-xs">조회수</span>
              </div>
              <p className="text-sm font-heading font-semibold mt-0.5">—</p>
            </div>
            <div>
              <div className="flex items-center justify-center gap-1 text-muted-foreground">
                <MousePointerClick className="h-3 w-3" />
                <span className="text-xs">CTR</span>
              </div>
              <p className="text-sm font-heading font-semibold mt-0.5">—</p>
            </div>
            <div>
              <div className="flex items-center justify-center gap-1 text-muted-foreground">
                <Activity className="h-3 w-3" />
                <span className="text-xs">알고리즘</span>
              </div>
              <p className="text-xs font-semibold mt-0.5">
                {(channel.algorithm_trust_level ?? 'PRE-ENTRY').replace('PRE-ENTRY', 'PRE').replace('ENTRY', 'ENT')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
