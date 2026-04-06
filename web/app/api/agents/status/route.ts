import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const logsDir = path.join(kasRoot, 'data', 'global', 'agent_logs')

  if (!fs.existsSync(logsDir)) {
    return NextResponse.json({ agents: [] })
  }

  try {
    const files = fs.readdirSync(logsDir).filter(f => f.endsWith('.json'))
    const agents = files.map(f => {
      try {
        const raw = fs.readFileSync(path.join(logsDir, f), 'utf-8')
        return JSON.parse(raw)
      } catch {
        return { name: f.replace('.json', ''), error: '파싱 오류' }
      }
    })
    return NextResponse.json({ agents })
  } catch {
    return NextResponse.json({ error: 'agent_logs 읽기 오류' }, { status: 500 })
  }
}
