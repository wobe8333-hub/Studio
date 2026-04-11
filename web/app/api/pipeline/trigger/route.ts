import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'
import { getKasRoot, getPythonExecutable } from '@/lib/fs-helpers'

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

    const chId = channel_id ?? 'CH1'
    const runId = `test_run_${Date.now()}`
    const now = new Date().toISOString()

    const progressData = {
      active: true,
      dry_run: true,
      channel_id: chId,
      run_id: runId,
      month_number,
      steps: STEPS.map((name, i) => ({
        index: i,
        name,
        status: i === 0 ? 'running' : 'pending',
        started_at: i === 0 ? now : null,
        completed_at: null,
        elapsed_ms: null,
      })),
      updated_at: now,
    }

    fs.writeFileSync(progressFile, JSON.stringify(progressData, null, 2), 'utf-8')

    // 런 목록에 표시되도록 최소 디렉토리 + manifest.json 생성
    const runDir = path.join(kasRoot, 'runs', chId, runId)
    fs.mkdirSync(runDir, { recursive: true })
    const manifest = {
      run_id: runId,
      channel_id: chId,
      run_state: 'RUNNING',
      dry_run: true,
      month_number,
      created_at: now,
      updated_at: now,
      topic: { reinterpreted_title: `[DRY RUN] ${chId} 테스트 실행` },
    }
    fs.writeFileSync(path.join(runDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8')

    return NextResponse.json({ ok: true, dry_run: true, run_id: runId })
  }

  const child = spawn(getPythonExecutable(), ['-m', 'src.pipeline', String(month_number)], {
    cwd: kasRoot,
    shell: true,
    detached: true,
    stdio: 'ignore',
  })
  child.unref()

  return NextResponse.json({ ok: true, dry_run: false, pid: child.pid })
}
