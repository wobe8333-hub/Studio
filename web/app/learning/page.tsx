'use client'

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
} from 'recharts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// mock 데이터 (Supabase 연동 전)
const mockFeedback = [
  { run_id: 'run_CH1_001', channel_id: 'CH1', ctr: 0, avp: 0, views: 0, algorithm_stage: 'PRE-ENTRY', preferred_title_mode: 'question', revenue_on_track: false },
  { run_id: 'run_CH2_001', channel_id: 'CH2', ctr: 0, avp: 0, views: 0, algorithm_stage: 'PRE-ENTRY', preferred_title_mode: 'hook', revenue_on_track: false },
]

// CTR/AVP 추이 차트 데이터 (mock)
const trendData = [
  { week: 'W1', CTR: 0, AVP: 0 },
  { week: 'W2', CTR: 0, AVP: 0 },
  { week: 'W3', CTR: 0, AVP: 0 },
  { week: 'W4', CTR: 0, AVP: 0 },
]

const chartConfig: ChartConfig = {
  CTR: { label: 'CTR (%)', color: 'var(--chart-1)' },
  AVP: { label: '평균 시청률 (%)', color: 'var(--chart-2)' },
}

// 승리 패턴 (하드코딩 가이드라인)
const WIN_PATTERNS = [
  { pattern: '제목 형식', value: '질문형 제목 (CTR +2~3%)', trend: 'up' },
  { pattern: '섬네일 색상', value: '고대비 빨강/노랑 배경', trend: 'up' },
  { pattern: '최적 업로드 시간', value: '화목 오후 7~9시', trend: 'neutral' },
  { pattern: '영상 길이', value: '8~12분 (알고리즘 진입 최적)', trend: 'up' },
  { pattern: '카테고리별 AVP', value: '경제 > 과학 > 심리 순', trend: 'neutral' },
]

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp className="h-4 w-4 text-green-500" />
  if (trend === 'down') return <TrendingDown className="h-4 w-4 text-red-500" />
  return <Minus className="h-4 w-4 text-muted-foreground" />
}

function AlgorithmBadge({ stage }: { stage: string }) {
  const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
    'ALGORITHM-ACTIVE': { label: '알고리즘 진입', variant: 'default' },
    'BROWSE-ENTRY': { label: '브라우즈 진입', variant: 'secondary' },
    'SEARCH-ONLY': { label: '검색 전용', variant: 'outline' },
    'PRE-ENTRY': { label: '사전 단계', variant: 'outline' },
  }
  const info = map[stage] ?? { label: stage, variant: 'outline' as const }
  return <Badge variant={info.variant}>{info.label}</Badge>
}

export default function LearningPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">학습 피드백</h1>
        <p className="text-muted-foreground text-sm">업로드 48시간 후 KPI 수집 기반 성과 분석</p>
      </div>

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
      <Card>
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
              {mockFeedback.map((fb) => (
                <TableRow key={fb.run_id}>
                  <TableCell>
                    <Badge variant="secondary">{fb.channel_id}</Badge>
                  </TableCell>
                  <TableCell className="text-center text-sm">
                    {fb.ctr > 0 ? `${(fb.ctr * 100).toFixed(1)}%` : '—'}
                  </TableCell>
                  <TableCell className="text-center text-sm">
                    {fb.avp > 0 ? `${(fb.avp * 100).toFixed(1)}%` : '—'}
                  </TableCell>
                  <TableCell className="text-center text-sm">
                    {fb.views > 0 ? fb.views.toLocaleString() : '—'}
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
        </CardContent>
      </Card>
    </div>
  )
}
