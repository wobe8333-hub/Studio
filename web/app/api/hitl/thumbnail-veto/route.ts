import { NextRequest, NextResponse } from 'next/server'
import { readKasJson, writeKasJson } from '@/lib/fs-helpers'

const QUEUE_PATH = 'data/global/notifications/thumbnail_veto_queue.json'
const DECISION_PATH = 'data/global/notifications/thumbnail_decisions.json'

interface ThumbnailVetoItem {
  episode_id: string
  channel_id: string
  title: string
  thumbnail_urls: string[]
  status: 'pending' | 'ok' | 'blocked'
}

/** GET /api/hitl/thumbnail-veto — 검토 대기 썸네일 목록 */
export async function GET() {
  const queue = await readKasJson<ThumbnailVetoItem[]>(QUEUE_PATH)
  const pending = (queue ?? []).filter((i) => i.status === 'pending')
  return NextResponse.json({ sets: pending })
}

/** POST /api/hitl/thumbnail-veto — 거부권 결정 저장 */
export async function POST(req: NextRequest) {
  const { decisions } = (await req.json()) as { decisions: Record<string, 'ok' | 'blocked'> }

  // 큐 업데이트
  const queue = (await readKasJson<ThumbnailVetoItem[]>(QUEUE_PATH)) ?? []
  const updated = queue.map((item) =>
    decisions[item.episode_id]
      ? { ...item, status: decisions[item.episode_id] }
      : item,
  )
  await writeKasJson(QUEUE_PATH, updated)

  // 결정 이력 저장
  const history = (await readKasJson<object[]>(DECISION_PATH)) ?? []
  history.push({ decided_at: new Date().toISOString(), decisions })
  await writeKasJson(DECISION_PATH, history.slice(-200))

  return NextResponse.json({ ok: true })
}
