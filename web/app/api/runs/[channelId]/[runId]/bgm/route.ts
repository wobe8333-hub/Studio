import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import { validateRunPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? require('path').join(process.cwd(), '..')
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const reportFile = validateRunPath(kasRoot, channelId, runId, 'step09', 'render_report.json')
  if (!reportFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(reportFile)) {
    return NextResponse.json({ bgm: null })
  }

  try {
    const raw = fs.readFileSync(reportFile, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json({ bgm: data })
  } catch {
    return NextResponse.json({ error: 'render_report.json 파싱 오류' }, { status: 500 })
  }
}
