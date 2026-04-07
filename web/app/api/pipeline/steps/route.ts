import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

// DRY RUN 단계별 시뮬레이션 소요 시간 (ms)
const STEP_DURATIONS = [4000, 2000, 2000, 6000, 3000, 3000, 3000, 2000]

export async function GET() {
  const kasRoot = getKasRoot()
  const progressFile = path.join(kasRoot, 'data', 'global', 'step_progress.json')

  if (!fs.existsSync(progressFile)) {
    return NextResponse.json({
      active: false,
      steps: [],
      channel_id: null,
      run_id: null,
      updated_at: null,
    })
  }

  try {
    const raw = fs.readFileSync(progressFile, 'utf-8').replace(/^\uFEFF/, '')
    const data = JSON.parse(raw)

    // DRY RUN 시뮬레이션: 폴링할 때마다 완료된 단계를 자동 진행
    if (data.dry_run && data.active) {
      const now = new Date()
      let changed = false

      for (let i = 0; i < data.steps.length; i++) {
        const step = data.steps[i]
        if (step.status === 'running' && step.started_at) {
          const elapsed = now.getTime() - new Date(step.started_at).getTime()
          const duration = STEP_DURATIONS[i] ?? 3000

          if (elapsed >= duration) {
            // 현재 단계 완료
            data.steps[i] = {
              ...step,
              status: 'done',
              completed_at: now.toISOString(),
              elapsed_ms: elapsed,
            }
            // 다음 단계 시작 또는 전체 완료
            if (i + 1 < data.steps.length) {
              data.steps[i + 1] = {
                ...data.steps[i + 1],
                status: 'running',
                started_at: now.toISOString(),
              }
            } else {
              data.active = false
            }
            data.updated_at = now.toISOString()
            changed = true
            break
          }
        }
      }

      if (changed) {
        fs.writeFileSync(progressFile, JSON.stringify(data, null, 2), 'utf-8')
      }
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'step_progress.json 파싱 오류' }, { status: 500 })
  }
}
