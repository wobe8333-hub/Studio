import { ShieldAlert, AlertTriangle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { createClient } from '@/lib/supabase/server'
import type { Channel, RevenueMonthly } from '@/lib/types'
import { SustainabilitySection } from './sustainability-section'

type RiskMonthly = { channel_id: string | null; month: string | null; net_profit: number | null; target: number | null; risk_level: string | null; risks: string[] | null }

// 실행 시점 기준 자동 계산
const CURRENT_MONTH = new Date().toISOString().slice(0, 7)
const TARGET = 2_000_000

interface RiskRow {
  channel_id: string
  category_ko: string
  month: string
  net_profit: number
  target: number
  risk_level: 'HIGH' | 'LOW'
  risks: string[]
}

async function fetchRiskData(): Promise<RiskRow[]> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (supabaseUrl && supabaseKey && !supabaseUrl.includes('xxxxxxxxxxxx')) {
    try {
      const supabase = await createClient()

      // channels + risk_monthly join
      const [{ data: channels }, { data: riskData }] = await Promise.all([
        supabase.from('channels').select('id, category_ko').order('id'),
        supabase.from('risk_monthly').select('*').eq('month', CURRENT_MONTH),
      ])

      if (channels) {
        const chRows = channels as Channel[]
        const riskRows = (riskData ?? []) as RiskMonthly[]
        return chRows.map((ch) => {
          const risk = riskRows.find((r) => r.channel_id === ch.id)
          const netProfit = risk?.net_profit ?? 0
          const target = risk?.target ?? TARGET
          const isHigh = netProfit < target
          return {
            channel_id: ch.id,
            category_ko: ch.category_ko ?? '',
            month: CURRENT_MONTH,
            net_profit: netProfit,
            target,
            risk_level: (isHigh ? 'HIGH' : 'LOW') as 'HIGH' | 'LOW',
            risks: isHigh ? [`순이익 미달: ${netProfit.toLocaleString()}원 < ${target.toLocaleString()}원`] : [],
          }
        })
      }
    } catch {
      // fallthrough to mock
    }
  }

  // fallback mock — config.py CHANNEL_CATEGORY_KO 기준
  const MOCK_CHANNELS = [
    { id: 'CH1', category_ko: '경제' },
    { id: 'CH2', category_ko: '부동산' },
    { id: 'CH3', category_ko: '심리' },
    { id: 'CH4', category_ko: '미스터리' },
    { id: 'CH5', category_ko: '전쟁사' },
    { id: 'CH6', category_ko: '과학' },
    { id: 'CH7', category_ko: '역사' },
  ]
  return MOCK_CHANNELS.map((ch) => ({
    channel_id: ch.id,
    category_ko: ch.category_ko,
    month: CURRENT_MONTH,
    net_profit: 0,
    target: TARGET,
    risk_level: 'HIGH' as const,
    risks: [`순이익 미달: 0원 < ${TARGET.toLocaleString()}원`],
  }))
}

export default async function RiskPage() {
  const riskData = await fetchRiskData()
  const highRiskChannels = riskData.filter((r) => r.risk_level === 'HIGH')
  const lowRiskChannels = riskData.filter((r) => r.risk_level === 'LOW')
  const totalProfit = riskData.reduce((s, r) => s + r.net_profit, 0)
  const totalTarget = riskData.reduce((s, r) => s + r.target, 0)
  const achieveRate = totalTarget > 0 ? (totalProfit / totalTarget) * 100 : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>리스크 모니터링</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>채널별 월간 수익 리스크 평가</p>
      </div>

      {/* 경고 배너 — 활성 채널(Phase 1)만 */}
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
        <Card className="glow-danger">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">HIGH 리스크</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{highRiskChannels.length}</div>
            <p className="text-xs text-muted-foreground mt-1">즉각 조치 필요</p>
          </CardContent>
        </Card>

        <Card className="glow-success">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">LOW 리스크</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{lowRiskChannels.length}</div>
            <p className="text-xs text-muted-foreground mt-1">정상 범위</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">전체 달성률</CardTitle>
            <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{achieveRate.toFixed(0)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              총 순이익 ₩{(totalProfit / 10000).toFixed(0)}만 / 목표 ₩{(totalTarget / 10000).toFixed(0)}만
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 리스크 히트맵 */}
      <Card>
        <CardHeader>
          <CardTitle>7채널 리스크 현황</CardTitle>
          <CardDescription>{CURRENT_MONTH} 기준 — HIGH(빨강) / LOW(초록)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
            {riskData.map((r) => (
              <div
                key={r.channel_id}
                className={`rounded-lg p-4 text-center border ${
                  r.risk_level === 'HIGH'
                    ? 'bg-red-500/10 border-red-500/25 glow-danger text-red-300'
                    : 'bg-green-500/[0.08] border-green-500/20 glow-success text-green-300'
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
        {riskData.map((r) => (
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

      {/* 주제 지속성 분석 — 클라이언트 컴포넌트 (/api/sustainability 연동) */}
      <SustainabilitySection />
    </div>
  )
}
