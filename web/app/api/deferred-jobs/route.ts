import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { readKasJson, getKasRoot, YoutubeQuotaFile } from '@/lib/fs-helpers'

const QUOTA_PATH = 'data/global/quota/youtube_quota_daily.json'

/** GET /api/deferred-jobs — deferred_jobs 목록 반환 */
export async function GET() {
  const quota = await readKasJson<YoutubeQuotaFile>(QUOTA_PATH)
  return NextResponse.json({
    deferred_jobs: quota?.deferred_jobs ?? [],
    quota_remaining: quota?.quota_remaining ?? 0,
  })
}

/** POST /api/deferred-jobs — Python으로 _run_deferred_uploads() 실행 */
export async function POST() {
  try {
    const kasRoot = getKasRoot()
    const child = spawn(
      'python',
      ['-c', 'from src.pipeline import _run_deferred_uploads; _run_deferred_uploads()'],
      {
        cwd: kasRoot,
        detached: true,
        stdio: 'ignore',
        env: { ...process.env, PYTHONPATH: kasRoot, KAS_ROOT: kasRoot },
      },
    )
    child.unref()
    return NextResponse.json({ ok: true, message: '이연 업로드 재시도를 시작했습니다.' })
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 })
  }
}
