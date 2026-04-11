import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

// DRY RUN 단계별 시뮬레이션 소요 시간 (ms)
const STEP_DURATIONS = [4000, 2000, 2000, 6000, 3000, 3000, 3000, 2000]

/** DELETE /api/pipeline/steps — step_progress.json 초기화 (모든 스텝 idle로 리셋) */
export async function DELETE() {
  const kasRoot = getKasRoot()
  const progressFile = path.join(kasRoot, 'data', 'global', 'step_progress.json')
  try {
    fs.writeFileSync(
      progressFile,
      JSON.stringify({ active: false, dry_run: false, steps: [], channel_id: null, run_id: null, updated_at: new Date().toISOString() }, null, 2),
      'utf-8'
    )
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: '초기화 실패' }, { status: 500 })
  }
}

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
              // manifest.json run_state → COMPLETED 업데이트
              if (data.run_id && data.channel_id) {
                try {
                  const manifestPath = path.join(kasRoot, 'runs', data.channel_id, data.run_id, 'manifest.json')
                  if (fs.existsSync(manifestPath)) {
                    const mRaw = fs.readFileSync(manifestPath, 'utf-8').replace(/^\uFEFF/, '')
                    const m = JSON.parse(mRaw)
                    m.run_state = 'COMPLETED'
                    m.completed_at = now.toISOString()
                    m.updated_at = now.toISOString()
                    fs.writeFileSync(manifestPath, JSON.stringify(m, null, 2), 'utf-8')
                  }
                } catch { /* manifest 업데이트 실패는 무시 */ }
              }
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
