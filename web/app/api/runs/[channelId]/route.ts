import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { validateChannelPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

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

  if (!fs.existsSync(channelRunsDir)) {
    return NextResponse.json({ runs: [] })
  }

  const entries = fs.readdirSync(channelRunsDir, { withFileTypes: true })
  const runs: RunSummary[] = []

  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith('run_')) continue

    const runDir = path.join(channelRunsDir, entry.name)
    const manifestPath = path.join(runDir, 'manifest.json')

    if (!fs.existsSync(manifestPath)) continue

    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))

      // QA 결과 (있으면 로드)
      let qa_pass: boolean | null = null
      const qaPath = path.join(runDir, 'step11', 'qa_result.json')
      if (fs.existsSync(qaPath)) {
        try {
          const qa = JSON.parse(fs.readFileSync(qaPath, 'utf-8'))
          qa_pass = qa.overall_pass ?? null
        } catch {
          // qa_result.json 파싱 실패 시 무시
        }
      }

      runs.push({
        run_id: manifest.run_id ?? entry.name,
        run_state: manifest.run_state ?? 'UNKNOWN',
        created_at: manifest.created_at ?? '',
        completed_at: manifest.completed_at,
        topic_title: manifest.topic?.reinterpreted_title ?? manifest.topic?.title,
        qa_pass,
      })
    } catch {
      // manifest.json 파싱 실패 시 스킵
    }
  }

  // 최신 Run이 먼저 오도록 정렬
  runs.sort((a, b) => b.created_at.localeCompare(a.created_at))

  return NextResponse.json({ runs, channel_id: channelId })
}
