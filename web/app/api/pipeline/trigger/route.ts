import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const { month_number = 1, channel_id, dry_run = true } = body

  const kasRoot = getKasRoot()

  if (dry_run) {
    const progressFile = path.join(kasRoot, 'data', 'global', 'step_progress.json')
    const dataDir = path.dirname(progressFile)
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true })
    }

    const STEPS = [
      'Step05 트렌드+지식 수집',
      'Step06 시나리오 정책',
      'Step07 알고리즘 정책',
      'Step08 영상 생성',
      'Step09 BGM',
      'Step10 제목+썸네일',
      'Step11 QA 검수',
      'Step12 업로드',
    ]

    const progressData = {
      active: true,
      dry_run: true,
      channel_id: channel_id ?? 'CH1',
      run_id: `test_run_${Date.now()}`,
      month_number,
      steps: STEPS.map((name, i) => ({
        index: i,
        name,
        status: i === 0 ? 'running' : 'pending',
        started_at: i === 0 ? new Date().toISOString() : null,
        completed_at: null,
        elapsed_ms: null,
      })),
      updated_at: new Date().toISOString(),
    }

    fs.writeFileSync(progressFile, JSON.stringify(progressData, null, 2), 'utf-8')
    return NextResponse.json({ ok: true, dry_run: true, run_id: progressData.run_id })
  }

  const python = process.platform === 'win32' ? 'python' : 'python3'
  const child = spawn(python, ['-m', 'src.pipeline', String(month_number)], {
    cwd: kasRoot,
    detached: true,
    stdio: 'ignore',
  })
  child.unref()

  return NextResponse.json({ ok: true, dry_run: false, pid: child.pid })
}
