import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const projFile = path.join(kasRoot, 'data', 'global', 'cost_projection.json')

  if (!fs.existsSync(projFile)) {
    return NextResponse.json({ projection: null })
  }

  try {
    const raw = fs.readFileSync(projFile, 'utf-8').replace(/^\uFEFF/, '')
    return NextResponse.json({ projection: JSON.parse(raw) })
  } catch {
    return NextResponse.json({ error: 'cost_projection.json 파싱 오류' }, { status: 500 })
  }
}
