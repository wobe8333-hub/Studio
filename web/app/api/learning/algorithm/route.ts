import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export async function GET() {
  const kasRoot = getKasRoot()
  const channelsDir = path.join(kasRoot, 'data', 'channels')

  if (!fs.existsSync(channelsDir)) {
    return NextResponse.json({ channels: [] })
  }

  try {
    const channels = fs.readdirSync(channelsDir)
    const result = channels.map(ch => {
      const policyFile = path.join(channelsDir, ch, 'algorithm_policy.json')
      if (!fs.existsSync(policyFile)) return { channel_id: ch, policy: null }
      try {
        const raw = fs.readFileSync(policyFile, 'utf-8').replace(/^\uFEFF/, '')
        return { channel_id: ch, policy: JSON.parse(raw) }
      } catch {
        return { channel_id: ch, policy: null }
      }
    })
    return NextResponse.json({ channels: result })
  } catch {
    return NextResponse.json({ error: '알고리즘 정책 읽기 오류' }, { status: 500 })
  }
}
