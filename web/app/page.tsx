import {
  DollarSign,
  Activity,
  TrendingUp,
  AlertTriangle,
  BarChart2,
  Bell,
} from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import type { Channel } from '@/lib/types'
import { RadialGauge } from '@/components/home-charts'
import { StaggerContainer, StaggerItem, ScrollReveal } from '@/components/animated-sections'
import { readKasJson, getKasRoot } from '@/lib/fs-helpers'
import fs from 'fs/promises'
import path from 'path'
import type { HitlSignal } from '@/lib/fs-helpers'

// Supabase 미연동 시 fallback mock 데이터
const MOCK_CHANNELS: Channel[] = [
  { id: 'CH1', category: 'economy',     category_ko: '경제',    youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH2', category: 'realestate',  category_ko: '부동산',  youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH3', category: 'psychology',  category_ko: '심리',    youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH4', category: 'mystery',     category_ko: '미스터리', youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH5', category: 'war_history', category_ko: '전쟁사',  youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH6', category: 'science',     category_ko: '과학',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH7', category: 'history',     category_ko: '역사',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
]

// runs/ 디렉토리 스캔으로 총 Run 수 계산
async function countTotalRuns(): Promise<number> {
  const kasRoot = getKasRoot()
  const runsDir = path.join(kasRoot, 'runs')
  let count = 0
  try {
    const channels = await fs.readdir(runsDir)
    for (const ch of channels) {
      const chDir = path.join(runsDir, ch)
      try {
        const stat = await fs.stat(chDir)
        if (!stat.isDirectory()) continue
        const runs = await fs.readdir(chDir)
        count += runs.filter(r => r.startsWith('run_')).length
      } catch { /* 빈 채널 무시 */ }
    }
  } catch { /* runs/ 없음 */ }
  return count
}

// 미해결 HITL 신호 수 계산
async function countHitlPending(): Promise<number> {
  const signals = await readKasJson<HitlSignal[]>('data/global/notifications/hitl_signals.json')
  if (!Array.isArray(signals)) return 0
  return signals.filter(s => !s.resolved).length
}

async function fetchData() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  const [totalRuns, hitlPending] = await Promise.all([
    countTotalRuns(),
    countHitlPending(),
  ])

  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) {
    return { channels: MOCK_CHANNELS, totalRuns, hitlPending }
  }

  try {
    const supabase = await createClient()
    const { data: channels } = await supabase.from('channels').select('*').order('id')
    return {
      channels: (channels ?? MOCK_CHANNELS) as Channel[],
      totalRuns,
      hitlPending,
    }
  } catch {
    return { channels: MOCK_CHANNELS, totalRuns, hitlPending }
  }
}

// 채널별 고유 색상 (sidebar-nav.tsx와 동일한 CSS 변수)
const CHANNEL_COLORS: Record<string, string> = {
  CH1: 'var(--channel-ch1)',
  CH2: 'var(--channel-ch2)',
  CH3: 'var(--channel-ch3)',
  CH4: 'var(--channel-ch4)',
  CH5: 'var(--channel-ch5)',
  CH6: 'var(--channel-ch6)',
  CH7: 'var(--channel-ch7)',
}

export default async function HomePage() {
  const { channels, totalRuns, hitlPending } = await fetchData()

  const activeChannels = channels.filter((ch) => ch.status === 'active')

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 배경 메시 그라데이션 */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-mesh-warm" />

      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>
          파이프라인 대시보드
        </h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>
          7채널 AI 자동화 파이프라인 현황 · 월 목표: 1,400만원
        </p>
      </div>

      {/* KPI 카드 6개 (3×2) */}
      <StaggerContainer className="grid grid-cols-2 gap-3 sm:grid-cols-3">

        {/* 1. 월 목표 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>월 목표</span>
              <DollarSign className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>₩14M</div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>채널당 ₩2,000,000</p>
          </div>
        </StaggerItem>

        {/* 2. 활성 채널 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>활성 채널</span>
              <Activity className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>
              {activeChannels.length} <span style={{ color: '#9b6060', fontSize: '1rem' }}>/ {channels.length}</span>
            </div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>
              {activeChannels.map((c) => c.id).join(', ')}
            </p>
          </div>
        </StaggerItem>

        {/* 3. 총 Runs */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>총 Runs</span>
              <BarChart2 className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>{totalRuns}</div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>누적 파이프라인 실행</p>
          </div>
        </StaggerItem>

        {/* 4. 달성률 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>이번달 달성률</span>
              <TrendingUp className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#1a0505' }}>0%</div>
            <RadialGauge value={0} color="rgba(238,36,0,0.6)" />
          </div>
        </StaggerItem>

        {/* 5. 리스크 채널 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>리스크 채널</span>
              <AlertTriangle className="h-4 w-4" style={{ color: '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: '#22c55e' }}>0</div>
            <p className="text-xs mt-1" style={{ color: '#22c55e' }}>HIGH 리스크 없음</p>
          </div>
        </StaggerItem>

        {/* 6. HITL 대기 */}
        <StaggerItem>
          <div className="glass-card glass-card-hover p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: '#9b6060' }}>HITL 대기</span>
              <Bell className="h-4 w-4" style={{ color: hitlPending > 0 ? '#f59e0b' : '#ee2400' }} />
            </div>
            <div className="text-2xl font-bold tabular-nums" style={{ fontFamily: "'Libre Baskerville', Georgia, serif", color: hitlPending > 0 ? '#f59e0b' : '#1a0505' }}>
              {hitlPending}
            </div>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>
              {hitlPending > 0 ? '운영자 확인 필요' : '대기 신호 없음'}
            </p>
          </div>
        </StaggerItem>

      </StaggerContainer>

      {/* 채널 상태 도트 */}
      <ScrollReveal>
        <div className="glass-card p-5">
          <h2 className="text-sm font-bold mb-4" style={{ color: '#5c1a1a' }}>채널별 상태</h2>
          <div className="flex flex-wrap gap-5">
            {channels.map((ch) => {
              const isActive = ch.status === 'active'
              const color = CHANNEL_COLORS[ch.id] ?? '#ddd'
              return (
                <div key={ch.id} className="flex flex-col items-center gap-1.5">
                  <div
                    className="flex items-center justify-center rounded-full text-white font-bold text-[11px] transition-opacity"
                    style={{
                      width: 44,
                      height: 44,
                      background: isActive ? color : '#d1d5db',
                      boxShadow: isActive ? `0 0 12px ${color}` : 'none',
                      opacity: isActive ? 1 : 0.45,
                    }}
                  >
                    {ch.id}
                  </div>
                  <span className="text-[10px] font-medium" style={{ color: '#5c1a1a' }}>{ch.category_ko}</span>
                  <span
                    className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{
                      background: isActive ? 'rgba(34,197,94,0.12)' : 'rgba(0,0,0,0.06)',
                      color: isActive ? '#16a34a' : '#9b6060',
                    }}
                  >
                    {isActive ? 'LIVE' : '준비중'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </ScrollReveal>

    </div>
  )
}
