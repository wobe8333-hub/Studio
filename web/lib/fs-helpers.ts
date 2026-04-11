import fs from 'fs/promises'
import path from 'path'

const CHANNEL_ID_RE = /^CH[1-7]$/
const RUN_ID_RE     = /^(run_CH[1-7]_\d{7,13}|test_run_\d{1,16}|test_run_\d{3})$/

/**
 * channelId / runId 형식 검증 후 허용된 kasRoot 하위 경로를 반환한다.
 * 형식 불일치 또는 경로 트래버설 시 null 반환.
 *
 * @param kasRoot  KAS_ROOT 환경변수 값
 * @param channelId URL 파라미터 (예: "CH1")
 * @param runId     URL 파라미터 (예: "run_CH1_1775143500")
 * @param ...sub    kasRoot/runs/{channelId}/{runId}/ 이후 경로 세그먼트
 * @returns         절대 경로 문자열, 또는 null (검증 실패)
 */
export function validateRunPath(
  kasRoot: string,
  channelId: string,
  runId: string,
  ...sub: string[]
): string | null {
  if (!CHANNEL_ID_RE.test(channelId)) return null
  if (!RUN_ID_RE.test(runId)) return null
  if (sub.some(s => s.includes('..') || path.isAbsolute(s))) return null

  const allowedRoot = path.resolve(kasRoot)
  const requestedPath = path.resolve(
    path.join(kasRoot, 'runs', channelId, runId, ...sub)
  )

  if (!requestedPath.startsWith(allowedRoot + path.sep) &&
      requestedPath !== allowedRoot) {
    return null
  }

  return requestedPath
}

/**
 * channelId만 검증 (runs 목록 등 runId 없는 경우용).
 */
export function validateChannelPath(
  kasRoot: string,
  channelId: string,
  ...sub: string[]
): string | null {
  if (!CHANNEL_ID_RE.test(channelId)) return null
  if (sub.some(s => s.includes('..') || path.isAbsolute(s))) return null

  const allowedRoot = path.resolve(kasRoot)
  const requestedPath = path.resolve(
    path.join(kasRoot, 'runs', channelId, ...sub)
  )

  if (!requestedPath.startsWith(allowedRoot + path.sep) &&
      requestedPath !== allowedRoot) {
    return null
  }

  return requestedPath
}

// process.cwd() in Next.js = {project}/web/ → parent = KAS 루트
const KAS_ROOT = process.env.KAS_ROOT ?? path.resolve(process.cwd(), '..')

/** KAS 루트 외부 경로 탈출 차단 */
function assertWithinRoot(fullPath: string): void {
  const rel = path.relative(KAS_ROOT, fullPath)
  if (rel.startsWith('..') || path.isAbsolute(rel)) {
    throw new Error(`경로 탈출 차단: ${fullPath}`)
  }
}

export function getKasRoot(): string {
  return KAS_ROOT
}

/**
 * 현재 환경에서 사용 가능한 Python 실행 파일 경로를 반환한다.
 *
 * 우선순위:
 *   1. PYTHON_EXECUTABLE 환경변수 (web/.env.local 에서 설정 가능)
 *   2. Windows: 'py'  (C:\Windows\py.exe — PATH 오염 없는 고정 시스템 경로)
 *   3. non-Windows: 'python3'
 *   4. 최종 폴백: 'python'
 *
 * Windows에서 'python' 직접 호출 시 WindowsApps 스텁(0xC0000142)을 선택할 수 있어
 * 'py' 런처를 우선 사용한다.
 */
export function getPythonExecutable(): string {
  if (process.env.PYTHON_EXECUTABLE) return process.env.PYTHON_EXECUTABLE
  if (process.platform === 'win32') return 'py'
  return 'python3'
}

/** KAS 루트 기준 상대 경로로 JSON 파일 읽기. 없으면 null 반환 */
export async function readKasJson<T = unknown>(relativePath: string): Promise<T | null> {
  try {
    const fullPath = path.join(KAS_ROOT, relativePath)
    assertWithinRoot(fullPath)   // 경로 탈출 차단
    let text = await fs.readFile(fullPath, 'utf-8')
    // ssot.write_json()이 utf-8-sig(BOM 포함)으로 쓰므로 BOM 제거
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1)
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

/** KAS 루트 기준 상대 경로로 JSON 파일 원자적 쓰기 (tmp → rename) */
export async function writeKasJson(relativePath: string, data: unknown): Promise<void> {
  const fullPath = path.join(KAS_ROOT, relativePath)
  assertWithinRoot(fullPath)   // 경로 탈출 차단
  await fs.mkdir(path.dirname(fullPath), { recursive: true })
  const tmp = fullPath + '.tmp'
  await fs.writeFile(tmp, JSON.stringify(data, null, 2), 'utf-8')
  try {
    await fs.rename(tmp, fullPath)
  } catch (e) {
    await fs.unlink(tmp).catch(() => {})
    throw e
  }
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
