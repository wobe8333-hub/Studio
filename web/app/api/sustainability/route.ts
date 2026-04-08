import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const globalDir = path.join(kasRoot, 'data', 'global')

  if (!fs.existsSync(globalDir)) {
    return NextResponse.json({ sustainability: [] })
  }

  try {
    const files = fs.readdirSync(globalDir).filter(f => f.startsWith('sustainability_') && f.endsWith('.json'))
    const items = files.flatMap(f => {
      try {
        const raw = fs.readFileSync(path.join(globalDir, f), 'utf-8').replace(/^\uFEFF/, '')
        return [JSON.parse(raw)]
      } catch {
        return []
      }
    })
    return NextResponse.json({ sustainability: items })
  } catch {
    return NextResponse.json({ error: '지속성 데이터 읽기 오류' }, { status: 500 })
  }
}
