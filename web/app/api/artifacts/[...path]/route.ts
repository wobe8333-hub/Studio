import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

const EXT_TO_MIME: Record<string, string> = {
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.mp4':  'video/mp4',
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path: segments } = await params
  const relativePath = segments.join('/')
  // 실행 결과물은 KAS 루트 하위 runs/ 에 저장됨
  const fullPath = path.join(getKasRoot(), 'runs', relativePath)

  // 경로 트래버설 방지
  const resolved = path.resolve(fullPath)
  if (!resolved.startsWith(path.resolve(getKasRoot()))) {
    return new NextResponse('Forbidden', { status: 403 })
  }

  try {
    const buffer = await fs.readFile(resolved)
    const ext = path.extname(resolved).toLowerCase()
    const contentType = EXT_TO_MIME[ext] ?? 'application/octet-stream'
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch {
    return new NextResponse('Not Found', { status: 404 })
  }
}
