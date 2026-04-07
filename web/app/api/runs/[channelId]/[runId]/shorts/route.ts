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

  const shortsDir = validateRunPath(kasRoot, channelId, runId, 'step08_s')
  if (!shortsDir) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(shortsDir)) {
    return NextResponse.json({ shorts: [] })
  }

  const files = fs.readdirSync(shortsDir).filter(f => f.endsWith('.mp4'))
  const shorts = files.map((f, i) => ({
    index: i + 1,
    filename: f,
    url: `/api/artifacts/${channelId}/${runId}/step08_s/${f}`,
  }))

  return NextResponse.json({ shorts })
}
