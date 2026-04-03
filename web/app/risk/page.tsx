import { ShieldAlert, AlertTriangle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const CHANNELS = [
  { id: 'CH1', category_ko: '경제' },
  { id: 'CH2', category_ko: '과학' },
  { id: 'CH3', category_ko: '부동산' },
  { id: 'CH4', category_ko: '심리' },
  { id: 'CH5', category_ko: '미스터리' },
  { id: 'CH6', category_ko: '역사' },
  { id: 'CH7', category_ko: '전쟁사' },
]

// mock 데이터 (Supabase 연동 전)
const mockRisk = CHANNELS.map((ch) => ({
  channel_id: ch.id,
  category_ko: ch.category_ko,
  month: '2026-04',
  net_profit: 0,
  target: 2_000_000,
  risk_level: 'HIGH' as 'HIGH' | 'LOW',
  risks: ['순이익 미달: 0원 < 2,000,000원'],
}))

const highRiskChannels = mockRisk.filter((r) => r.risk_level === 'HIGH')

export default function RiskPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">리스크 모니터링</h1>
        <p className="text-muted-foreground text-sm">채널별 월간 수익 리스크 평가</p>
      </div>

      {/* 경고 배너 */}
      {highRiskChannels.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>HIGH 리스크 채널 {highRiskChannels.length}개</AlertTitle>
          <AlertDescription>
            {highRiskChannels.map((r) => r.channel_id).join(', ')} 채널이 월 목표 수익 미달 상태입니다.
          </AlertDescription>
        </Alert>
      )}

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">HIGH 리스크</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{highRiskChannels.length}</div>
            <p className="text-xs text-muted-foreground mt-1">즉각 조치 필요</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">LOW 리스크</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {mockRisk.filter((r) => r.risk_level === 'LOW').length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">정상 범위</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">전체 달성률</CardTitle>
            <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0%</div>
            <p className="text-xs text-muted-foreground mt-1">총 순이익 0원 / 목표 1,400만원</p>
          </CardContent>
        </Card>
      </div>

      {/* 리스크 히트맵 */}
      <Card>
        <CardHeader>
          <CardTitle>7채널 리스크 현황</CardTitle>
          <CardDescription>2026-04 기준 — HIGH(빨강) / LOW(초록)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
            {mockRisk.map((r) => (
              <div
                key={r.channel_id}
                className={`rounded-lg p-4 text-center text-white ${
                  r.risk_level === 'HIGH'
                    ? 'bg-red-500 dark:bg-red-600'
                    : 'bg-green-500 dark:bg-green-600'
                }`}
              >
                <p className="font-bold text-sm">{r.channel_id}</p>
                <p className="text-xs opacity-90">{r.category_ko}</p>
                <p className="text-xs font-semibold mt-1">{r.risk_level}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 채널별 리스크 상세 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {mockRisk.map((r) => (
          <Card key={r.channel_id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">
                  {r.channel_id} {r.category_ko}
                </CardTitle>
                <Badge variant={r.risk_level === 'HIGH' ? 'destructive' : 'default'}>
                  {r.risk_level}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">순이익</span>
                <span className="font-medium">₩{r.net_profit.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">목표</span>
                <span className="font-medium">₩{r.target.toLocaleString()}</span>
              </div>
              {r.risks.length > 0 && (
                <div className="pt-1">
                  {r.risks.map((risk, i) => (
                    <p key={i} className="text-xs text-destructive flex items-start gap-1">
                      <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                      {risk}
                    </p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
