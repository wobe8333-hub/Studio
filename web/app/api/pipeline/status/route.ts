import { NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface ManifestSummary {
  run_id: string
  channel_id: string
  run_state: string
  created_at: string
  topic_title: string
  topic_score: number
}

export interface PipelineStatusResult {
  initialized: boolean
  running: ManifestSummary[]
  recent: ManifestSummary[]   // 최근 20개, 생성시간 내림차순
  total_runs: number
}

async function readManifest(filePath: string): Promise<ManifestSummary | null> {
  try {
    const text = (await fs.readFile(filePath, 'utf-8')).replace(/^\uFEFF/, '')
    const m = JSON.parse(text)
    return {
      run_id:      m.run_id      ?? '',
      channel_id:  m.channel_id  ?? '',
      run_state:   m.run_state   ?? 'UNKNOWN',
      created_at:  m.created_at  ?? '',
      topic_title: m.topic?.reinterpreted_title ?? m.topic?.original_trend?.topic ?? '—',
      topic_score: m.topic?.score ?? 0,
    }
  } catch {
    return null
  }
}

/**
 * GET /api/pipeline/status
 * runs/{channel}/{run}/manifest.json 전체 스캔 + .initialized 플래그 확인
 */
export async function GET() {
  const kasRoot = getKasRoot()
  const runsDir = path.join(kasRoot, 'runs')
  const initializedFlag = path.join(kasRoot, 'data', 'global', '.initialized')

  // .initialized 플래그 확인
  let initialized = false
  try {
    await fs.access(initializedFlag)
    initialized = true
  } catch { /* 미초기화 */ }

  // manifest.json 스캔
  const all: ManifestSummary[] = []
  try {
    const channels = await fs.readdir(runsDir)
    for (const channelId of channels) {
      const channelDir = path.join(runsDir, channelId)
      try {
        const stat = await fs.stat(channelDir)
        if (!stat.isDirectory()) continue
      } catch { continue }

      const runDirs = await fs.readdir(channelDir)
      for (const runId of runDirs) {
        // 경로 탈출 방지: .. 또는 절대경로 포함 항목 건너뜀
        if (runId.includes('..') || path.isAbsolute(runId)) continue
        const manifestPath = path.join(channelDir, runId, 'manifest.json')
        const summary = await readManifest(manifestPath)
        if (summary) all.push(summary)
      }
    }
  } catch { /* runs/ 없음 */ }

  // 생성시간 내림차순 정렬 (created_at 없는 항목은 뒤로)
  all.sort((a, b) => {
    if (!a.created_at && !b.created_at) return 0
    if (!a.created_at) return 1
    if (!b.created_at) return -1
    return b.created_at > a.created_at ? 1 : b.created_at < a.created_at ? -1 : 0
  })

  const running = all.filter((r) => r.run_state === 'RUNNING')
  const recent  = all.slice(0, 20)

  const result: PipelineStatusResult = {
    initialized,
    running,
    recent,
    total_runs: all.length,
  }

  return NextResponse.json(result)
}
