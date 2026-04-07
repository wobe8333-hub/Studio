import { Settings, Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// config.py SSOT 기준 채널 정보 (CH1~CH7)
const CHANNELS = [
  { id: 'CH1', category_ko: '경제',    launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target: 2000000, monthly_longform: 10, monthly_shorts: 30 },
  { id: 'CH2', category_ko: '부동산',  launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target: 2000000, monthly_longform: 10, monthly_shorts: 30 },
  { id: 'CH3', category_ko: '심리',    launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target: 2000000, monthly_longform: 10, monthly_shorts: 30 },
  { id: 'CH4', category_ko: '미스터리', launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target: 2000000, monthly_longform: 12, monthly_shorts: 40 },
  { id: 'CH5', category_ko: '전쟁사',  launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target: 2000000, monthly_longform: 12, monthly_shorts: 40 },
  { id: 'CH6', category_ko: '과학',    launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target: 2000000, monthly_longform: 10, monthly_shorts: 30 },
  { id: 'CH7', category_ko: '역사',    launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target: 2000000, monthly_longform: 10, monthly_shorts: 30 },
]

const QUOTA_POLICIES = [
  { service: 'Gemini API', limit: '이미지 500장/일', rpm: 'RPM 50', note: 'diskcache 24h TTL 캐시' },
  { service: 'YouTube API', limit: '10,000단위/일', rpm: '업로드 1,700단위', note: '부족 시 자동 이연 처리' },
  { service: 'yt-dlp', limit: '없음', rpm: 'RPM 30', note: '차단 감지 시 5분 대기' },
]

export default function SettingsPage() {
  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>설정</h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>채널 설정 및 API 쿼터 정책 — 현재 읽기 전용 (Supabase 연동 후 수정 가능)</p>
      </div>

      {/* 채널 설정 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            <CardTitle>7채널 설정</CardTitle>
          </div>
          <CardDescription>런치 단계별 활성화 정책 (config.py SSOT 기준)</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>채널</TableHead>
                <TableHead>카테고리</TableHead>
                <TableHead className="text-center">런치 단계</TableHead>
                <TableHead className="text-center">상태</TableHead>
                <TableHead className="text-center">RPM 기준</TableHead>
                <TableHead className="text-center">월 목표</TableHead>
                <TableHead className="text-center">롱폼/월</TableHead>
                <TableHead className="text-center">Shorts/월</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {CHANNELS.map((ch) => (
                <TableRow key={ch.id}>
                  <TableCell>
                    <span className="font-medium">{ch.id}</span>
                  </TableCell>
                  <TableCell>{ch.category_ko}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline">Phase {ch.launch_phase}</Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={ch.status === 'active' ? 'default' : 'secondary'}>
                      {ch.status === 'active' ? '활성' : '대기'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center text-sm">₩{ch.rpm_proxy.toLocaleString()}</TableCell>
                  <TableCell className="text-center text-sm">₩{(ch.revenue_target / 10000).toFixed(0)}만</TableCell>
                  <TableCell className="text-center text-sm">{ch.monthly_longform}편</TableCell>
                  <TableCell className="text-center text-sm">{ch.monthly_shorts}편</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 쿼터 정책 */}
      <Card>
        <CardHeader>
          <CardTitle>API 쿼터 정책</CardTitle>
          <CardDescription>src/quota/ 모듈 기준 — 변경 시 config.py 수정 필요</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>서비스</TableHead>
                <TableHead>일간 한도</TableHead>
                <TableHead>속도 제한</TableHead>
                <TableHead>비고</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {QUOTA_POLICIES.map((p, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">{p.service}</TableCell>
                  <TableCell className="text-sm">{p.limit}</TableCell>
                  <TableCell className="text-sm">{p.rpm}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.note}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 파이프라인 론치 단계 설명 */}
      <Card>
        <CardHeader>
          <CardTitle>채널 런치 단계 정책</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { phase: 'Phase 1', months: 'Month 1~2', channels: 'CH1 + CH2', desc: '경제·부동산 2채널로 파이프라인 검증' },
            { phase: 'Phase 2', months: 'Month 2~3', channels: 'CH1~CH4', desc: '심리·미스터리 추가, 4채널 운영' },
            { phase: 'Phase 3', months: 'Month 3+', channels: '전체 7채널', desc: '전쟁사·과학·역사 합류, 풀 운영' },
          ].map((p, i) => (
            <div key={i} className="flex items-start gap-4 p-3 rounded-lg border">
              <div className="min-w-[72px]">
                <Badge>{p.phase}</Badge>
              </div>
              <div>
                <p className="text-sm font-medium">{p.months} — {p.channels}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{p.desc}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 저장 안내 */}
      <div className="flex items-center gap-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        <Save className="h-4 w-4 shrink-0" />
        <p>설정 변경은 현재 <code className="text-xs bg-muted px-1 rounded">src/core/config.py</code>를 직접 수정해야 합니다. Supabase 연동 후 웹에서 수정 가능하도록 업데이트 예정.</p>
      </div>
    </div>
  )
}
