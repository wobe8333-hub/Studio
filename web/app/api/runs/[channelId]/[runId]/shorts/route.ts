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
  const shortsDir = path.join(kasRoot, 'runs', channelId, runId, 'step08_s')

  if (!fs.existsSync(shortsDir)) {
    return NextResponse.json({ shorts: [] })
  }

  const files = fs.readdirSync(shortsDir).filter(f => f.endsWith('.mp4'))
  const shorts = files.map((f, i) => ({
    index: i + 1,
    filename: f,
    url: `/api/files/${channelId}/${runId}/step08_s/${f}`,
  }))

  return NextResponse.json({ shorts })
}
