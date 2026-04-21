import { NextRequest, NextResponse } from 'next/server'
import { readKasJson, writeKasJson } from '@/lib/fs-helpers'

const PLAN_PATH = 'data/global/monthly_plan/hitl_series_plan.json'
const APPROVAL_PATH = 'data/global/monthly_plan/series_approvals.json'

/** GET /api/hitl/series-plan — 이번 달 시리즈 기획 목록 반환 */
export async function GET() {
  const data = await readKasJson<{ series: unknown[] }>(PLAN_PATH)
  return NextResponse.json({ series: data?.series ?? [] })
}

/** POST /api/hitl/series-plan — 승인 결과 저장 */
export async function POST(req: NextRequest) {
  const { approvals } = (await req.json()) as { approvals: Record<string, string> }
  const existing = (await readKasJson<unknown[]>(APPROVAL_PATH)) ?? []
  const record = {
    approved_at: new Date().toISOString(),
    approvals,
  }
  await writeKasJson(APPROVAL_PATH, [...(existing as object[]), record])
  return NextResponse.json({ ok: true })
}
