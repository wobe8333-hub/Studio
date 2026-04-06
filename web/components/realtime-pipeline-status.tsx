'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

/**
 * Supabase Realtime으로 pipeline_runs 테이블을 구독하여
 * 현재 실행 중인 파이프라인 수를 실시간으로 표시합니다.
 * Supabase 미연동 시 아무것도 렌더링하지 않습니다.
 */
export function RealtimePipelineStatus() {
  const [activeRuns, setActiveRuns] = useState(0)

  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()

    // 초기 실행중인 run 수 조회
    supabase
      .from('pipeline_runs')
      .select('id', { count: 'exact', head: true })
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .eq('run_state', 'RUNNING' as any)
      .then(({ count }) => setActiveRuns(count ?? 0))

    // Realtime: pipeline_runs 변경 구독
    const channel = supabase
      .channel('pipeline-runs-live')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'pipeline_runs' },
        (payload) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const newRow = payload.new as any
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const oldRow = payload.old as any
          const isNewRunning = newRow?.run_state === 'RUNNING'
          const wasRunning   = oldRow?.run_state === 'RUNNING'

          if (isNewRunning && !wasRunning) {
            setActiveRuns((prev) => prev + 1)
          } else if (!isNewRunning && wasRunning) {
            setActiveRuns((prev) => Math.max(0, prev - 1))
          }
        }
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [])

  if (activeRuns === 0) return null

  return (
    <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-green-600 dark:text-green-400">
      <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
      {activeRuns}건 실행중
    </span>
  )
}
