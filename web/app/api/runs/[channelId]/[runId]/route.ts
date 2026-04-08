import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot, validateRunPath } from '@/lib/fs-helpers'

export interface RunArtifacts {
  manifest: {
    run_id: string
    channel_id: string
    run_state: string
    created_at: string
    topic_title: string
    topic_score: number
    topic_category: string
  }
  step08: {
    has_script: boolean
    section_count: number
    title_candidates: string[]
    selected_title: string | null
    has_narration: boolean
    has_video: boolean
    image_paths: string[]   // /api/artifacts/ 호출용 상대 경로
    manim: {
      attempted: number
      success: number
      fallback: number
      fallback_rate: number
    } | null
  } | null
  step11: {
    overall_pass: boolean
    animation_ok: boolean
    script_ok: boolean
    policy_ok: boolean
    human_review_required: boolean
    human_review_completed: boolean
  } | null
  cost_krw: number | null
}

async function tryReadJson<T>(filePath: string): Promise<T | null> {
  try {
    let text = await fs.readFile(filePath, 'utf-8')
    // ssot.write_json()이 utf-8-sig(BOM 포함)으로 쓰므로 BOM 제거
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1)
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

async function fileExists(p: string): Promise<boolean> {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

/**
 * GET /api/runs/[channelId]/[runId]
 * Run 디렉토리의 아티팩트를 집계해 반환한다.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> },
) {
  const { channelId, runId } = await params

  const kasRoot = getKasRoot()

  // channelId/runId 형식 검증 + 경로 탈출 방지
  const runDir = validateRunPath(kasRoot, channelId, runId)
  if (!runDir) {
    return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
  }

  // manifest
  const raw = await tryReadJson<Record<string, unknown>>(path.join(runDir, 'manifest.json'))
  if (!raw) {
    return NextResponse.json({ error: 'Run not found' }, { status: 404 })
  }
  const topic = (raw.topic ?? {}) as Record<string, unknown>
  const manifest = {
    run_id:         String(raw.run_id ?? ''),
    channel_id:     String(raw.channel_id ?? channelId),
    run_state:      String(raw.run_state ?? 'UNKNOWN'),
    created_at:     String(raw.created_at ?? ''),
    topic_title:    String(
      (topic.reinterpreted_title as string) ??
      ((topic.original_trend as Record<string, unknown>)?.topic as string) ??
      '—'
    ),
    topic_score:    Number(topic.score ?? 0),
    topic_category: String(topic.category ?? ''),
  }

  // step08
  const step08Dir = path.join(runDir, 'step08')
  const scriptData = await tryReadJson<Record<string, unknown>>(path.join(step08Dir, 'script.json'))
  const titleData  = await tryReadJson<Record<string, unknown>>(path.join(step08Dir, 'title.json'))
  const manimData  = await tryReadJson<Record<string, unknown>>(
    path.join(step08Dir, 'manim_stability_report.json')
  )

  let step08: RunArtifacts['step08'] = null
  if (scriptData || titleData) {
    // assets_ai/*.png 이미지 목록
    const imgDir = path.join(step08Dir, 'images', 'assets_ai')
    let imageFiles: string[] = []
    try {
      const entries = await fs.readdir(imgDir)
      imageFiles = entries
        .filter((f) => /\.(png|jpg|jpeg|webp)$/i.test(f))
        .sort()
        .map((f) => `runs/${channelId}/${runId}/step08/images/assets_ai/${f}`)
    } catch { /* 이미지 없음 */ }

    const sections = Array.isArray(scriptData?.sections) ? scriptData.sections as unknown[] : []
    const titleCandidates = Array.isArray(titleData?.title_candidates)
      ? (titleData.title_candidates as string[])
      : Array.isArray(scriptData?.title_candidates)
        ? (scriptData.title_candidates as string[])
        : []

    step08 = {
      has_script:      !!scriptData,
      section_count:   sections.length,
      title_candidates: titleCandidates,
      selected_title:  titleData?.selected ? String(titleData.selected) : null,
      has_narration:   await fileExists(path.join(step08Dir, 'narration.wav')),
      has_video:       await fileExists(path.join(step08Dir, 'video.mp4')),
      image_paths:     imageFiles,
      manim: manimData ? {
        attempted:    Number(manimData.manim_sections_attempted ?? 0),
        success:      Number(manimData.manim_sections_success ?? 0),
        fallback:     Number(manimData.manim_sections_fallback ?? 0),
        fallback_rate: Number(manimData.fallback_rate ?? 0),
      } : null,
    }
  }

  // step11
  const qaData = await tryReadJson<Record<string, unknown>>(
    path.join(runDir, 'step11', 'qa_result.json')
  )
  const step11: RunArtifacts['step11'] = qaData ? {
    overall_pass:            Boolean(qaData.overall_pass),
    animation_ok:            Boolean((qaData.animation_quality_check as Record<string, unknown>)?.pass),
    script_ok:               Boolean((qaData.script_accuracy_check as Record<string, unknown>)?.pass),
    policy_ok:               Boolean((qaData.youtube_policy_check as Record<string, unknown>)?.pass),
    human_review_required:   Boolean((qaData.human_review as Record<string, unknown>)?.required),
    human_review_completed:  Boolean((qaData.human_review as Record<string, unknown>)?.completed),
  } : null

  // cost
  const costData = await tryReadJson<Record<string, unknown>>(path.join(runDir, 'cost.json'))
  const cost_krw = costData?.total_cost_krw != null ? Number(costData.total_cost_krw) : null

  return NextResponse.json({ manifest, step08, step11, cost_krw } satisfies RunArtifacts)
}
