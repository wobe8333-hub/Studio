import { NextRequest, NextResponse } from 'next/server'
import { scanPendingHumanReviews, readVariantManifest } from '@/lib/fs-helpers'
import fs from 'fs/promises'
import path from 'path'

const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')

/** GET /api/qa-data?type=pending — QA 검수 대기 목록 */
/** GET /api/qa-data?type=variants — 배리언트 선택 대기 목록 */
export async function GET(req: NextRequest) {
  const type = req.nextUrl.searchParams.get('type')

  if (type === 'pending') {
    const pending = await scanPendingHumanReviews()
    return NextResponse.json(pending)
  }

  if (type === 'variants') {
    const runsDir = path.join(KAS_ROOT, 'runs')
    const results: Array<{ channelId: string; runId: string; manifest: unknown }> = []
    try {
      const channels = await fs.readdir(runsDir)
      for (const channelId of channels) {
        const channelDir = path.join(runsDir, channelId)
        let stat: Awaited<ReturnType<typeof fs.stat>>
        try { stat = await fs.stat(channelDir) } catch { continue }
        if (!stat.isDirectory()) continue
        const runDirs = await fs.readdir(channelDir)
        for (const runId of runDirs) {
          const manifest = await readVariantManifest(channelId, runId)
          if (manifest && manifest.title_variants?.length > 0) {
            results.push({ channelId, runId, manifest })
          }
        }
      }
    } catch { /* runs/ 없음 */ }
    return NextResponse.json(results)
  }

  return NextResponse.json({ error: 'type 파라미터 필요 (pending | variants)' }, { status: 400 })
}
