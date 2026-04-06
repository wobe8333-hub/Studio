import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const progressFile = path.join(kasRoot, 'data', 'global', 'step_progress.json')

  // 파일이 없으면 빈 상태 반환
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
    const raw = fs.readFileSync(progressFile, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'step_progress.json 파싱 오류' }, { status: 500 })
  }
}
