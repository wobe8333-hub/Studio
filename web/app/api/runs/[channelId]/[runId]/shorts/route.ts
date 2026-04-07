import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import { validateRunPath, getKasRoot } from '@/lib/fs-helpers'

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

  let files: string[]
  try {
    files = await fs.readdir(shortsDir)
  } catch (e: unknown) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') {
      return NextResponse.json({ shorts: [] })
    }
    return NextResponse.json({ error: 'shorts 디렉토리 읽기 오류' }, { status: 500 })
  }

  const shorts = files
    .filter(f => f.endsWith('.mp4'))
    .map((f, i) => ({
      index: i + 1,
      filename: f,
      url: `/api/artifacts/${channelId}/${runId}/step08_s/${f}`,
    }))

  return NextResponse.json({ shorts })
}
