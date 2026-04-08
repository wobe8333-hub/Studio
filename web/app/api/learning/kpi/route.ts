import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const kpiDir = path.join(kasRoot, 'data', 'global', 'kpi_48h')

  if (!fs.existsSync(kpiDir)) {
    return NextResponse.json({ kpi_items: [] })
  }

  try {
    const files = fs.readdirSync(kpiDir).filter(f => f.endsWith('.json'))
    const items = files.flatMap(f => {
      try {
        const raw = fs.readFileSync(path.join(kpiDir, f), 'utf-8').replace(/^\uFEFF/, '')
        return [JSON.parse(raw)]
      } catch {
        return []
      }
    })
    return NextResponse.json({ kpi_items: items })
  } catch {
    return NextResponse.json({ error: 'kpi_48h 읽기 오류' }, { status: 500 })
  }
}
