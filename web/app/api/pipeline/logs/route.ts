import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

/**
 * GET /api/pipeline/logs?lines=N
 * logs/pipeline.log의 마지막 N줄을 반환한다. 기본 100줄, 최대 500줄.
 * 파일이 없으면 빈 배열 반환.
 */
export async function GET(req: NextRequest) {
  const linesParam = req.nextUrl.searchParams.get('lines')
  const n = Math.min(Math.max(parseInt(linesParam ?? '100', 10) || 100, 1), 500)

  const logPath = path.join(getKasRoot(), 'logs', 'pipeline.log')

  try {
    const text = await fs.readFile(logPath, 'utf-8')
    const lines = text.split('\n').filter(Boolean) // 빈 줄 제거
    const tail = lines.slice(-n)
    return NextResponse.json({
      lines: tail,
      total_lines: lines.length,
      log_path: 'logs/pipeline.log',
    })
  } catch {
    return NextResponse.json({
      lines: [],
      total_lines: 0,
      log_path: 'logs/pipeline.log',
    })
  }
}
