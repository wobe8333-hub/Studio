import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()
  const reportFile = path.join(kasRoot, 'runs', channelId, runId, 'step09', 'render_report.json')

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
