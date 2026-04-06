import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { getKasRoot } from '@/lib/fs-helpers'

/**
 * POST /api/pipeline/trigger
 * body: { month_number: number }
 *
 * Python 파이프라인을 백그라운드 서브프로세스로 실행한다.
 * 즉시 202 Accepted 반환 — 완료를 기다리지 않는다.
 */
export async function POST(req: NextRequest) {
  const body = (await req.json()) as { month_number: number }
  const monthNumber = Number(body.month_number)

  if (!Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) {
    return NextResponse.json(
      { ok: false, error: 'month_number는 1~12 사이 정수여야 합니다.' },
      { status: 400 },
    )
  }

  try {
    const kasRoot = getKasRoot()
    const child = spawn('python', ['-m', 'src.pipeline', String(monthNumber)], {
      cwd: kasRoot,
      detached: true,
      stdio: 'ignore',
      env: {
        ...process.env,
        PYTHONPATH: kasRoot,
        KAS_ROOT: kasRoot,
      },
    })
    child.unref()

    return NextResponse.json(
      {
        ok: true,
        message: `파이프라인 month=${monthNumber} 시작됨 (백그라운드 실행)`,
        pid: child.pid,
        started_at: new Date().toISOString(),
      },
      { status: 202 },
    )
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 })
  }
}
