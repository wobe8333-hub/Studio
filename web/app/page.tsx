import { createClient } from '@/lib/supabase/server'
import type { Channel } from '@/lib/types'
import { readKasJson, getKasRoot } from '@/lib/fs-helpers'
import fs from 'fs/promises'
import path from 'path'
import type { HitlSignal } from '@/lib/fs-helpers'
import { KpiBanner } from '@/components/kpi-banner'
import HomeExecTab from './home-exec-tab'

const MOCK_CHANNELS: Channel[] = [
  { id: 'CH1', category: 'economy',     category_ko: '경제',    youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 7000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH2', category: 'realestate',  category_ko: '부동산',  youtube_channel_id: null, launch_phase: 1, status: 'active',  rpm_proxy: 6000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH3', category: 'psychology',  category_ko: '심리',    youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH4', category: 'mystery',     category_ko: '미스터리', youtube_channel_id: null, launch_phase: 2, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH5', category: 'war_history', category_ko: '전쟁사',  youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 3500, revenue_target_monthly: 2000000, monthly_longform_target: 12, monthly_shorts_target: 40, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH6', category: 'science',     category_ko: '과학',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
  { id: 'CH7', category: 'history',     category_ko: '역사',    youtube_channel_id: null, launch_phase: 3, status: 'pending', rpm_proxy: 4000, revenue_target_monthly: 2000000, monthly_longform_target: 10, monthly_shorts_target: 30, subscriber_count: 0, video_count: 0, algorithm_trust_level: 'PRE-ENTRY', updated_at: null },
]

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
        count += runs.filter((r) => r.startsWith('run_')).length
      } catch { /* 빈 채널 무시 */ }
    }
  } catch { /* runs/ 없음 */ }
  return count
}

async function countHitlPending(): Promise<number> {
  const signals = await readKasJson<HitlSignal[]>('data/global/notifications/hitl_signals.json')
  if (!Array.isArray(signals)) return 0
  return signals.filter((s) => !s.resolved).length
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

export default async function HomePage() {
  const { channels, totalRuns, hitlPending } = await fetchData()

  // launch_phase === 1 이 파이프라인 SSOT (pipeline.py get_active_channels 기준)
  const activeChannelCount = channels.filter((ch) => ch.launch_phase === 1).length
  const totalRevenue = 0   // Supabase revenue_monthly 미연동 시 mock 0
  const achievementRate = totalRevenue > 0 ? (totalRevenue / 14_000_000) * 100 : 0

  return (
    <div>
      {/* KPI 배너 — 항상 고정 */}
      <KpiBanner
        revenue={totalRevenue}
        achievementRate={achievementRate}
        activeChannels={activeChannelCount}
        totalChannels={channels.length}
        totalRuns={totalRuns}
        hitlPending={hitlPending}
      />

      {/* 탭 컨트롤러 + 탭 콘텐츠 (경영/운영) */}
      <HomeExecTab
        channels={channels}
        totalRuns={totalRuns}
        activeChannelCount={activeChannelCount}
      />
    </div>
  )
}
