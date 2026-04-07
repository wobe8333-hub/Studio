import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import { validateRunPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? require('path').join(process.cwd(), '..')
}

// SEO PATCH에서 허용할 최상위 키 목록 (임의 키 삽입 방지)
const ALLOWED_SEO_KEYS = new Set([
  'title', 'description', 'tags', 'category', 'thumbnail_url',
  'chapter_markers', 'selected_title', 'ab_variant',
])

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const metaFile = validateRunPath(kasRoot, channelId, runId, 'step10', 'metadata.json')
  if (!metaFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

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

  const metaFile = validateRunPath(kasRoot, channelId, runId, 'step10', 'metadata.json')
  if (!metaFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(metaFile)) {
    return NextResponse.json({ error: 'metadata.json 없음' }, { status: 404 })
  }

  try {
    const body = await req.json()

    // 허용된 키만 필터링
    const safeBody: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(body)) {
      if (ALLOWED_SEO_KEYS.has(k)) {
        safeBody[k] = v
      }
    }
    if (Object.keys(safeBody).length === 0) {
      return NextResponse.json({ error: '수정 가능한 필드가 없습니다' }, { status: 400 })
    }

    const raw = fs.readFileSync(metaFile, 'utf-8')
    const current = JSON.parse(raw)
    const updated = { ...current, ...safeBody, updated_at: new Date().toISOString() }
    fs.writeFileSync(metaFile, JSON.stringify(updated, null, 2), 'utf-8')
    return NextResponse.json({ ok: true, seo: updated })
  } catch {
    return NextResponse.json({ error: '저장 실패' }, { status: 500 })
  }
}
