import {
  Eye,
  MousePointerClick,
  DollarSign,
  Activity,
  CheckCircle,
  XCircle,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

// 채널 정보 (Supabase 연동 전 mock 데이터)
const CHANNELS = [
  { id: 'CH1', name: '경제', category_ko: '경제', target: 2000000 },
  { id: 'CH2', name: '과학', category_ko: '과학', target: 2000000 },
  { id: 'CH3', name: '부동산', category_ko: '부동산', target: 2000000 },
  { id: 'CH4', name: '심리', category_ko: '심리', target: 2000000 },
  { id: 'CH5', name: '미스터리', category_ko: '미스터리', target: 2000000 },
  { id: 'CH6', name: '역사', category_ko: '역사', target: 2000000 },
  { id: 'CH7', name: '전쟁사', category_ko: '전쟁사', target: 2000000 },
]

function formatKrw(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return `${value}`
}

export default function HomePage() {
  const totalTarget = 14_000_000

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">전체 KPI 대시보드</h1>
        <p className="text-muted-foreground text-sm">
          7채널 AI 자동화 파이프라인 현황 — 월 목표: 1,400만원
        </p>
      </div>

      {/* 총괄 수익 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">월 총 목표</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₩14,000,000</div>
            <p className="text-xs text-muted-foreground mt-1">채널당 ₩2,000,000</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">활성 채널</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2 / 7</div>
            <p className="text-xs text-muted-foreground mt-1">Phase 1 (CH1, CH2)</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">이번달 달성률</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0%</div>
            <Progress value={0} className="mt-2 h-1" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">리스크 채널</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0 / 7</div>
            <p className="text-xs text-muted-foreground mt-1">HIGH 리스크 없음</p>
          </CardContent>
        </Card>
      </div>

      {/* 7채널 카드 그리드 */}
      <div>
        <h2 className="text-lg font-semibold mb-3">채널별 현황</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {CHANNELS.map((ch) => (
            <ChannelCard key={ch.id} channel={ch} />
          ))}
        </div>
      </div>
    </div>
  )
}

function ChannelCard({ channel }: { channel: typeof CHANNELS[0] }) {
  // Supabase 연동 전 더미 데이터
  const isActive = channel.id === 'CH1' || channel.id === 'CH2'
  const revenue = 0
  const achieveRate = (revenue / channel.target) * 100

  return (
    <Card className={!isActive ? 'opacity-50' : ''}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{channel.id}</CardTitle>
            <p className="text-xs text-muted-foreground">{channel.category_ko}</p>
          </div>
          <Badge variant={isActive ? 'default' : 'secondary'}>
            {isActive ? '활성' : '대기'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 수익 진행률 */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">월 수익</span>
            <span className="font-medium">₩{formatKrw(revenue)} / ₩{formatKrw(channel.target)}</span>
          </div>
          <Progress value={achieveRate} className="h-1.5" />
        </div>

        {/* KPI 지표 */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="flex items-center justify-center gap-1 text-muted-foreground">
              <Eye className="h-3 w-3" />
              <span className="text-xs">조회수</span>
            </div>
            <p className="text-sm font-semibold mt-0.5">—</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-1 text-muted-foreground">
              <MousePointerClick className="h-3 w-3" />
              <span className="text-xs">CTR</span>
            </div>
            <p className="text-sm font-semibold mt-0.5">—</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-1 text-muted-foreground">
              <Activity className="h-3 w-3" />
              <span className="text-xs">알고리즘</span>
            </div>
            <p className="text-xs font-semibold mt-0.5 truncate">PRE</p>
          </div>
        </div>

        {/* 목표 달성 여부 */}
        <div className="flex items-center gap-1.5 text-xs">
          {achieveRate >= 100 ? (
            <>
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
              <span className="text-green-600 dark:text-green-400">목표 달성</span>
            </>
          ) : (
            <>
              <XCircle className="h-3.5 w-3.5 text-red-400" />
              <span className="text-muted-foreground">미달성 ({achieveRate.toFixed(0)}%)</span>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
