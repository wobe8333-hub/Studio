import fs from 'fs/promises'
import path from 'path'

// process.cwd() in Next.js = {project}/web/ → parent = KAS 루트
const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')

export function getKasRoot(): string {
  return KAS_ROOT
}

/** KAS 루트 기준 상대 경로로 JSON 파일 읽기. 없으면 null 반환 */
export async function readKasJson<T = unknown>(relativePath: string): Promise<T | null> {
  try {
    const fullPath = path.join(KAS_ROOT, relativePath)
    const text = await fs.readFile(fullPath, 'utf-8')
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

/** KAS 루트 기준 상대 경로로 JSON 파일 원자적 쓰기 (tmp → rename) */
export async function writeKasJson(relativePath: string, data: unknown): Promise<void> {
  const fullPath = path.join(KAS_ROOT, relativePath)
  await fs.mkdir(path.dirname(fullPath), { recursive: true })
  const tmp = fullPath + '.tmp'
  await fs.writeFile(tmp, JSON.stringify(data, null, 2), 'utf-8')
  await fs.rename(tmp, fullPath)
}

// ─── 타입 정의 ──────────────────────────────────────────────────────────────

export interface HitlSignal {
  id: string
  type: 'pytest_failure' | 'pipeline_failure' | 'schema_mismatch'
  details: Record<string, unknown>
  timestamp: string
  resolved: boolean
}

export interface QaResult {
  channel_id: string
  run_id: string
  qa_timestamp: string
  animation_quality_check: { pass: boolean; vision_qa?: { pass: boolean; skipped?: boolean } }
  script_accuracy_check: { pass: boolean; disclaimer_key?: string }
  youtube_policy_check: { ai_label_placed: boolean; disclaimer_placed: boolean; pass: boolean }
  human_review: { required: boolean; completed: boolean; reviewer: string | null; sla_hours: number }
  affiliate_formula_check: { purchase_rate_applied: number; formula_correct: boolean }
  overall_pass: boolean
}

export interface QaPendingRun {
  channelId: string
  runId: string
  qaResult: QaResult
}

export interface TitleVariant {
  ref: string
  mode: 'authority' | 'curiosity' | 'benefit'
  title: string
  seo_keyword_included: boolean
}

export interface ThumbnailVariant {
  ref: string
  mode: string
  path: string
}

export interface VariantManifest {
  channel_id: string
  run_id: string
  title_variants: TitleVariant[]
  thumbnail_variants: ThumbnailVariant[]
  selected_title_ref?: string
  selected_thumbnail_ref?: string
}

export interface DeferredJob {
  channel_id: string
  run_id: string
  topic_title?: string
  created_at?: string
  video_path?: string
}

export interface YoutubeQuotaFile {
  date: string
  quota_used: number
  quota_limit: number
  quota_remaining: number
  deferred_jobs: DeferredJob[]
}

// ─── QA 스캔 ─────────────────────────────────────────────────────────────────

/** runs/{channelId}/[runId]/step11/qa_result.json 중 수동 검수 미완료 항목 반환 */
export async function scanPendingHumanReviews(): Promise<QaPendingRun[]> {
  const runsDir = path.join(KAS_ROOT, 'runs')
  const results: QaPendingRun[] = []
  try {
    const channels = await fs.readdir(runsDir)
    for (const channelId of channels) {
      const channelDir = path.join(runsDir, channelId)
      let stat: Awaited<ReturnType<typeof fs.stat>>
      try { stat = await fs.stat(channelDir) } catch { continue }
      if (!stat.isDirectory()) continue
      const runDirs = await fs.readdir(channelDir)
      for (const runId of runDirs) {
        const qaPath = path.join(channelDir, runId, 'step11', 'qa_result.json')
        try {
          const text = await fs.readFile(qaPath, 'utf-8')
          const qa = JSON.parse(text) as QaResult
          if (qa.human_review?.required && !qa.human_review?.completed) {
            results.push({ channelId, runId, qaResult: qa })
          }
        } catch { /* qa_result.json 없는 run 스킵 */ }
      }
    }
  } catch { /* runs/ 디렉토리 없음 */ }
  return results
}

/** runs/{channelId}/{runId}/step08/variants/variant_manifest.json 읽기 */
export async function readVariantManifest(
  channelId: string,
  runId: string,
): Promise<VariantManifest | null> {
  return readKasJson<VariantManifest>(
    `runs/${channelId}/${runId}/step08/variants/variant_manifest.json`,
  )
}
