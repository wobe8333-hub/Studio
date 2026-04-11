import { NextResponse } from 'next/server'
import { spawnSync } from 'child_process'
import path from 'path'
import { getKasRoot, getPythonExecutable } from '@/lib/fs-helpers'

export interface PreflightResult {
  exit_code: number
  all_passed: boolean
  stdout: string
  failures: string[]
  duration_ms: number
  python_version?: string
  python_error?: string
}

/**
 * Python 실행 가능 여부를 먼저 확인하고 버전을 반환한다.
 * Windows Store 스텁(0xC0000142) vs 실제 Python을 구분한다.
 */
function checkPythonVersion(pyExe: string, cwd: string): { ok: boolean; version: string; error?: string } {
  const r = spawnSync(pyExe, ['--version'], {
    cwd,
    shell: true,
    encoding: 'utf-8',
    timeout: 10_000,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  })
  if (r.error) {
    return { ok: false, version: '', error: `'${pyExe}' 실행 불가: ${r.error.message}` }
  }
  const ver = (r.stdout || r.stderr || '').trim()
  if (r.status !== 0 || !ver) {
    const hex = `0x${(r.status ?? 0).toString(16).toUpperCase()}`
    return { ok: false, version: '', error: `'${pyExe} --version' exit ${r.status} (${hex})` }
  }
  return { ok: true, version: ver }
}

/**
 * POST /api/pipeline/preflight
 * scripts/preflight_check.py를 동기 실행해 환경 검증 결과를 반환한다.
 *
 * Python 실행 파일 우선순위:
 *   PYTHON_EXECUTABLE 환경변수 → py (Windows 런처) → python
 */
export async function POST() {
  const kasRoot = getKasRoot()
  const scriptPath = path.join(kasRoot, 'scripts', 'preflight_check.py')
  const pyExe = getPythonExecutable()
  const start = Date.now()

  // ─ Step 0: Python 자체 실행 가능 여부 먼저 확인 ─
  const pyCheck = checkPythonVersion(pyExe, kasRoot)
  if (!pyCheck.ok) {
    return NextResponse.json({
      exit_code: 1,
      all_passed: false,
      stdout: '',
      failures: [`❌ Python 실행 오류: ${pyCheck.error}`],
      duration_ms: Date.now() - start,
      python_error: pyCheck.error,
    } satisfies PreflightResult)
  }

  // ─ Step 1: preflight_check.py 실행 ─
  const result = spawnSync(pyExe, [scriptPath], {
    cwd: kasRoot,
    shell: true,
    env: {
      ...process.env,
      PYTHONPATH: kasRoot,
      KAS_ROOT: kasRoot,
      PYTHONIOENCODING: 'utf-8',   // Windows cp949에서 ✅/❌ 이모지 UnicodeEncodeError 방지
      PYTHONUTF8: '1',             // Python 3.7+ UTF-8 모드 (추가 보험)
    },
    encoding: 'utf-8',
    timeout: 60_000,
  })

  const duration_ms = Date.now() - start

  // 타임아웃 또는 프로세스 실행 오류 처리
  if (result.error) {
    const isTimeout = result.signal === 'SIGTERM' || result.error.message.includes('ETIMEDOUT')
    return NextResponse.json({
      exit_code: 1,
      all_passed: false,
      stdout: '',
      failures: [isTimeout ? `❌ 타임아웃 (${duration_ms}ms 경과)` : `❌ ${result.error.message}`],
      duration_ms,
      python_version: pyCheck.version,
    } satisfies PreflightResult)
  }

  const exit_code = result.status ?? 1
  const stdout = (result.stdout ?? '') + (result.stderr ?? '')

  // 스크립트가 아무것도 출력하지 않고 크래시한 경우 (DLL 오류 등)
  if (!stdout.trim() && exit_code !== 0) {
    const hexCode = `0x${exit_code.toString(16).toUpperCase()}`
    return NextResponse.json({
      exit_code,
      all_passed: false,
      stdout: '',
      failures: [
        `❌ Python 프로세스 비정상 종료 (exit ${exit_code} / ${hexCode})`,
        exit_code === 3221225794
          ? '❌ 0xC0000142: DLL 초기화 실패 — pip install -r requirements.txt 또는 Python 재설치 필요'
          : `❌ Windows 오류 코드: ${hexCode}`,
      ],
      duration_ms,
      python_version: pyCheck.version,
      python_error: `exit ${exit_code} (${hexCode}) — stdout 없음`,
    } satisfies PreflightResult)
  }

  // ❌ 접두사 라인만 failures로 추출
  const failures = stdout
    .split('\n')
    .filter((line) => line.includes('❌'))
    .map((line) => line.trim())

  return NextResponse.json({
    exit_code,
    all_passed: exit_code === 0,
    stdout,
    failures,
    duration_ms,
    python_version: pyCheck.version,
  } satisfies PreflightResult)
}
