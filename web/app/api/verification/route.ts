import { NextRequest, NextResponse } from 'next/server'
import path from 'path'
import fs from 'fs'
import { getKasRoot } from '@/lib/fs-helpers'

export type StageStatus = 'pending' | 'in_progress' | 'done' | 'failed'

export interface VerificationStage {
  id: number
  status: StageStatus
  updated_at: string | null
  note: string
}

export interface VerificationState {
  stages: VerificationStage[]
  last_reset: string
}

const DEFAULT_STAGES: VerificationStage[] = [
  { id: 0, status: 'pending', updated_at: null, note: '' },
  { id: 1, status: 'pending', updated_at: null, note: '' },
  { id: 2, status: 'pending', updated_at: null, note: '' },
  { id: 3, status: 'pending', updated_at: null, note: '' },
  { id: 4, status: 'pending', updated_at: null, note: '' },
  { id: 5, status: 'pending', updated_at: null, note: '' },
  { id: 6, status: 'pending', updated_at: null, note: '' },
]

function getFilePath(): string {
  return path.join(getKasRoot(), 'data', 'global', 'verification_status.json')
}

function readState(): VerificationState {
  const filePath = getFilePath()
  if (!fs.existsSync(filePath)) {
    return { stages: DEFAULT_STAGES, last_reset: new Date().toISOString() }
  }
  try {
    const raw = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '')
    return JSON.parse(raw) as VerificationState
  } catch {
    return { stages: DEFAULT_STAGES, last_reset: new Date().toISOString() }
  }
}

function writeState(state: VerificationState): void {
  const filePath = getFilePath()
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, JSON.stringify(state, null, 2), 'utf-8')
}

/** GET /api/verification — 현재 검증 단계 상태 반환 */
export async function GET() {
  const state = readState()
  return NextResponse.json(state)
}

/** PATCH /api/verification — 특정 단계 상태 업데이트
 *  body: { id: number, status: StageStatus, note?: string }
 *  또는: { reset: true }
 */
export async function PATCH(req: NextRequest) {
  const body = await req.json().catch(() => ({})) as Record<string, unknown>

  if (body.reset) {
    const fresh: VerificationState = {
      stages: DEFAULT_STAGES.map(s => ({ ...s })),
      last_reset: new Date().toISOString(),
    }
    writeState(fresh)
    return NextResponse.json(fresh)
  }

  const { id, status, note } = body as { id: number; status: StageStatus; note?: string }
  if (id == null || !status) {
    return NextResponse.json({ error: 'id 와 status 필수' }, { status: 400 })
  }

  const state = readState()
  const stage = state.stages.find(s => s.id === id)
  if (!stage) {
    return NextResponse.json({ error: `id ${id} 없음` }, { status: 404 })
  }

  stage.status = status
  stage.updated_at = new Date().toISOString()
  if (note !== undefined) stage.note = note

  writeState(state)
  return NextResponse.json(state)
}
