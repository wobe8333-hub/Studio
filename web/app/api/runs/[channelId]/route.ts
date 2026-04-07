import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import { validateChannelPath, getKasRoot } from '@/lib/fs-helpers'

export interface RunSummary {
  run_id: string
  run_state: 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  created_at: string
  completed_at?: string
  topic_title?: string
  qa_pass?: boolean | null
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string }> }
) {
  const { channelId } = await params
  const kasRoot = getKasRoot()

  const channelRunsDir = validateChannelPath(kasRoot, channelId)
  if (!channelRunsDir) {
    return NextResponse.json({ error: '잘못된 채널 ID' }, { status: 400 })
  }

  // 채널 디렉토리 존재 여부 확인
  try {
    await fs.access(channelRunsDir)
  } catch {
    return NextResponse.json({ runs: [] })
  }

  const entries = await fs.readdir(channelRunsDir, { withFileTypes: true })
  const runs: RunSummary[] = []

  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith('run_')) continue

    const runDir = `${channelRunsDir}/${entry.name}`
    const manifestPath = `${runDir}/manifest.json`

    let manifest: Record<string, unknown>
    try {
      const text = await fs.readFile(manifestPath, 'utf-8')
      manifest = JSON.parse(text)
    } catch {
      continue
    }

    // QA 결과 (있으면 로드)
    let qa_pass: boolean | null = null
    try {
      const qaText = await fs.readFile(`${runDir}/step11/qa_result.json`, 'utf-8')
      const qa = JSON.parse(qaText)
      qa_pass = qa.overall_pass ?? null
    } catch {
      // qa_result.json 없는 run 정상 처리
    }

    runs.push({
      run_id: (manifest.run_id as string) ?? entry.name,
      run_state: (manifest.run_state as string) ?? 'UNKNOWN',
      created_at: (manifest.created_at as string) ?? '',
      completed_at: manifest.completed_at as string | undefined,
      topic_title: (manifest.topic as Record<string, string> | undefined)?.reinterpreted_title
        ?? (manifest.topic as Record<string, string> | undefined)?.title,
      qa_pass,
    })
  }

  // 최신 Run이 먼저 오도록 정렬 (created_at 없는 항목은 맨 뒤)
  runs.sort((a, b) => {
    if (!a.created_at && !b.created_at) return 0
    if (!a.created_at) return 1
    if (!b.created_at) return -1
    return b.created_at.localeCompare(a.created_at)
  })

  return NextResponse.json({ runs, channel_id: channelId })
}
