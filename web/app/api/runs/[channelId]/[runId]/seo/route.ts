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
  const metaFile = path.join(kasRoot, 'runs', channelId, runId, 'step10', 'metadata.json')

  if (!fs.existsSync(metaFile)) {
    return NextResponse.json({ seo: null })
  }

  try {
    const raw = fs.readFileSync(metaFile, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json({ seo: data })
  } catch {
    return NextResponse.json({ error: 'metadata.json 파싱 오류' }, { status: 500 })
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()
  const metaFile = path.join(kasRoot, 'runs', channelId, runId, 'step10', 'metadata.json')

  if (!fs.existsSync(metaFile)) {
    return NextResponse.json({ error: 'metadata.json 없음' }, { status: 404 })
  }

  try {
    const body = await req.json()
    const raw = fs.readFileSync(metaFile, 'utf-8')
    const current = JSON.parse(raw)
    const updated = { ...current, ...body, updated_at: new Date().toISOString() }
    fs.writeFileSync(metaFile, JSON.stringify(updated, null, 2), 'utf-8')
    return NextResponse.json({ ok: true, seo: updated })
  } catch {
    return NextResponse.json({ error: '저장 실패' }, { status: 500 })
  }
}
