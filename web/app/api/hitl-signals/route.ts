import { NextRequest, NextResponse } from 'next/server'
import { readKasJson, writeKasJson, HitlSignal } from '@/lib/fs-helpers'

const SIGNALS_PATH = 'data/global/notifications/hitl_signals.json'

/** GET /api/hitl-signals — 미해결 신호 목록 반환 */
export async function GET() {
  const signals = await readKasJson<HitlSignal[]>(SIGNALS_PATH)
  const unresolved = (signals ?? []).filter((s) => !s.resolved)
  return NextResponse.json(unresolved)
}

/** PATCH /api/hitl-signals — body: { id: string } → 해당 신호 resolved=true */
export async function PATCH(req: NextRequest) {
  const { id } = (await req.json()) as { id: string }
  const signals = await readKasJson<HitlSignal[]>(SIGNALS_PATH)
  if (!signals) return NextResponse.json({ ok: false, error: '파일 없음' }, { status: 404 })

  const updated = signals.map((s) => (s.id === id ? { ...s, resolved: true } : s))
  await writeKasJson(SIGNALS_PATH, updated)
  return NextResponse.json({ ok: true })
}
