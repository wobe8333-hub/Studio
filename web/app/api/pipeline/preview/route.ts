import { NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot, readKasJson } from '@/lib/fs-helpers'

interface Section {
  id?: string
  heading?: string
  narration_text?: string
  animation_prompt?: string
  image_prompt?: string
}

interface HookObject {
  text?: string
  [key: string]: unknown
}

interface Script {
  title_candidates?: string[]
  sections?: Section[]
  hook?: string | HookObject
  channel_id?: string
}

/** hook 필드가 string 또는 { text: string } 객체 모두 처리 */
function extractHookText(hook: string | HookObject | undefined | null): string | null {
  if (!hook) return null
  if (typeof hook === 'string') return hook
  return hook.text ?? null
}

export async function GET() {
  const kasRoot = getKasRoot()
  const runsDir = path.join(kasRoot, 'runs')

  // 가장 최근 실제 run 탐색 (test_run_ 제외, run_CH*_* 형식)
  let latestRun: { channel: string; runId: string; mtime: number } | null = null

  try {
    const channels = await fs.readdir(runsDir)
    for (const ch of channels) {
      const chDir = path.join(runsDir, ch)
      const chStat = await fs.stat(chDir).catch(() => null)
      if (!chStat?.isDirectory()) continue

      const runs = await fs.readdir(chDir)
      for (const runId of runs) {
        if (!runId.startsWith('run_')) continue
        const runDir = path.join(chDir, runId)
        const s = await fs.stat(runDir).catch(() => null)
        if (!s?.isDirectory()) continue
        if (!latestRun || s.mtimeMs > latestRun.mtime) {
          latestRun = { channel: ch, runId, mtime: s.mtimeMs }
        }
      }
    }
  } catch {
    return NextResponse.json({ error: 'runs 디렉토리 접근 실패' }, { status: 500 })
  }

  if (!latestRun) {
    return NextResponse.json({ error: '실행 결과 없음' }, { status: 404 })
  }

  const { channel, runId } = latestRun
  const step08Dir = path.join(runsDir, channel, runId, 'step08')

  // script.json 읽기
  const script = await readKasJson<Script>(`runs/${channel}/${runId}/step08/script.json`)
  const sections = script?.sections ?? []

  // assets_ai 전체 이미지 목록 (갤러리용)
  let allImages: string[] = []
  try {
    const imgDir = path.join(step08Dir, 'images', 'assets_ai')
    const files = await fs.readdir(imgDir)
    allImages = files
      .filter(f => f.match(/\.(png|jpg|jpeg|webp)$/i))
      .sort()
      .map(f => `/api/artifacts/${channel}/${runId}/step08/images/assets_ai/${f}`)
  } catch { /* 이미지 없음 */ }

  // 섹션별 미리보기 (최대 3개, 이미지 매핑 포함)
  const previews = sections.slice(0, 3).map((s, i) => ({
    index: i + 1,
    heading: s.heading ?? `섹션 ${i + 1}`,
    narration: s.narration_text ?? '',
    prompt: s.animation_prompt ?? s.image_prompt ?? '',
    image: allImages[i] ?? null,
  }))

  return NextResponse.json({
    channel,
    runId,
    title: script?.title_candidates?.[0] ?? null,
    hook: extractHookText(script?.hook),
    previews,
    allImages,           // 전체 이미지 갤러리용
    totalSections: sections.length,
  })
}
