import { NextResponse } from 'next/server'
import { spawnSync } from 'child_process'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface PreflightResult {
  exit_code: number
  all_passed: boolean
  stdout: string
  failures: string[]
  duration_ms: number
}

/**
 * POST /api/pipeline/preflight
 * scripts/preflight_check.py를 동기 실행해 환경 검증 결과를 반환한다.
 * Gemini API 호출 포함으로 최대 60초 소요될 수 있다.
 */
export async function POST() {
  const kasRoot = getKasRoot()
  const scriptPath = path.join(kasRoot, 'scripts', 'preflight_check.py')
  const start = Date.now()

  const result = spawnSync('python', [scriptPath], {
    cwd: kasRoot,
    env: { ...process.env, PYTHONPATH: kasRoot, KAS_ROOT: kasRoot },
    encoding: 'utf-8',
    timeout: 60_000, // 60초 타임아웃 (Gemini API 포함)
  })

  const duration_ms = Date.now() - start
  const stdout = (result.stdout ?? '') + (result.stderr ?? '')
  const exit_code = result.status ?? 1

  // ❌ 접두사 라인만 failures로 추출
  const failures = stdout
    .split('\n')
    .filter((line) => line.includes('❌'))
    .map((line) => line.trim())

  const response: PreflightResult = {
    exit_code,
    all_passed: exit_code === 0,
    stdout,
    failures,
    duration_ms,
  }

  return NextResponse.json(response)
}
