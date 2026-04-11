import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import { validateChannelPath, getKasRoot } from '@/lib/fs-helpers'

export interface RunSummary {
  run_id: string
  run_state: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TEST' | string
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
    const isRun = entry.name.startsWith('run_') || entry.name.startsWith('test_run_')
    if (!entry.isDirectory() || !isRun) continue

    const runDir = `${channelRunsDir}/${entry.name}`

    // QA 결과 (있으면 로드)
    let qa_pass: boolean | null = null
    let qaCreatedAt: string | undefined
    try {
      let qaText = await fs.readFile(`${runDir}/step11/qa_result.json`, 'utf-8')
      if (qaText.charCodeAt(0) === 0xFEFF) qaText = qaText.slice(1)
      const qa = JSON.parse(qaText)
      qa_pass = qa.overall_pass ?? null
      qaCreatedAt = qa.qa_timestamp
    } catch {
      // qa_result.json 없는 run 정상 처리
    }

    // manifest.json 로드 (없으면 qa_result.json 기반 폴백)
    let manifest: Record<string, unknown> | null = null
    try {
      let text = await fs.readFile(`${runDir}/manifest.json`, 'utf-8')
      if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1)
      manifest = JSON.parse(text)
    } catch {
      // manifest 없는 test_run_* 등 허용
    }

    // manifest 없으면 디렉토리 mtime을 created_at 대용으로 사용
    let fallbackCreatedAt = qaCreatedAt ?? ''
    if (!fallbackCreatedAt) {
      try {
        const stat = await fs.stat(runDir)
        fallbackCreatedAt = stat.birthtime.toISOString()
      } catch { /* ignore */ }
    }

    runs.push({
      run_id: (manifest?.run_id as string) ?? entry.name,
      run_state: (manifest?.run_state as string) ?? (entry.name.startsWith('test_run_') ? 'TEST' : 'UNKNOWN'),
      created_at: (manifest?.created_at as string) ?? fallbackCreatedAt,
      completed_at: manifest?.completed_at as string | undefined,
      topic_title: (manifest?.topic as Record<string, string> | undefined)?.reinterpreted_title
        ?? (manifest?.topic as Record<string, string> | undefined)?.title,
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
