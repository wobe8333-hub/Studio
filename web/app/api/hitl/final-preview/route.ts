import { NextRequest, NextResponse } from 'next/server'
import { readKasJson, writeKasJson } from '@/lib/fs-helpers'

const PREVIEW_QUEUE_PATH = 'data/global/notifications/final_preview_queue.json'
const UPLOAD_QUEUE_PATH = 'data/global/notifications/upload_queue.json'

interface PreviewItem {
  episode_id: string
  channel_id: string
  title: string
  video_url: string | null
  duration_sec: number
  tags: string[]
  thumbnail_url: string | null
  upload_ready: boolean
}

/** GET /api/hitl/final-preview — 업로드 직전 프리뷰 목록 */
export async function GET() {
  const queue = await readKasJson<PreviewItem[]>(PREVIEW_QUEUE_PATH)
  const ready = (queue ?? []).filter((i) => i.upload_ready)
  return NextResponse.json({ items: ready })
}

/** POST /api/hitl/final-preview — 업로드 승인 또는 Skip(자동 업로드) */
export async function POST(req: NextRequest) {
  const { episode_id, action } = (await req.json()) as {
    episode_id: string
    action: 'upload' | 'auto_upload'
  }

  // 업로드 큐에 추가
  const uploadQueue = (await readKasJson<object[]>(UPLOAD_QUEUE_PATH)) ?? []
  uploadQueue.push({
    episode_id,
    action,
    queued_at: new Date().toISOString(),
    status: 'queued',
  })
  await writeKasJson(UPLOAD_QUEUE_PATH, uploadQueue)

  // 프리뷰 큐에서 해당 아이템 제거
  const previewQueue = (await readKasJson<PreviewItem[]>(PREVIEW_QUEUE_PATH)) ?? []
  const remaining = previewQueue.filter((i) => i.episode_id !== episode_id)
  await writeKasJson(PREVIEW_QUEUE_PATH, remaining)

  return NextResponse.json({ ok: true, episode_id, action })
}
