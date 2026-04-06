# Run 상세 페이지 + 지식 수집 뷰어 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹 대시보드에서 각 파이프라인 Run의 Step08 아티팩트(스크립트·이미지·나레이션·Manim·QA)를 확인하고, 채널별 지식 수집 결과(트렌드 토픽·시리즈)를 탐색할 수 있도록 한다.

**Architecture:** Next.js API routes 2개(`/api/runs/[ch]/[runId]`, `/api/knowledge`)가 KAS 로컬 파일시스템을 읽어 JSON 반환. 클라이언트 컴포넌트 2개(`/runs/[ch]/[runId]/page.tsx`, `/knowledge/page.tsx`)가 각 데이터를 표시. `/monitor` Status 패널의 Run 카드에 `/runs/` 링크를 추가해 드릴다운 지원.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 · shadcn/ui · glassmorphism dark · `web/lib/fs-helpers.ts` · `/api/artifacts/` (기존 이미지 스트리밍)

---

## 파일 구조

**신규 파일:**
| 파일 | 역할 |
|------|------|
| `web/app/api/runs/[channelId]/[runId]/route.ts` | GET: Run 아티팩트 집계 반환 |
| `web/app/runs/[channelId]/[runId]/page.tsx` | Run 상세 페이지 (Step08~11 체크리스트 + 이미지 갤러리) |
| `web/app/api/knowledge/route.ts` | GET: 채널별 KnowledgePackage + 시리즈 목록 반환 |
| `web/app/knowledge/page.tsx` | 지식 수집 뷰어 페이지 |

**수정 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `web/components/sidebar-nav.tsx` | "지식 수집" 메뉴 추가 |
| `web/app/monitor/page.tsx` | RunRow에 `/runs/[ch]/[id]` Link 추가 |

---

## 컨텍스트 (서브에이전트용)

### 실제 데이터 경로 (KAS 루트 기준)

**Run 아티팩트** (`runs/{channelId}/{runId}/`):
```
manifest.json          — run_id, channel_id, run_state, created_at, topic.*
step08/script.json     — title_candidates[], sections[{id, heading, narration_text, render_tool, manim_fallback_used}]
step08/title.json      — title_candidates[], selected (string)
step08/manim_stability_report.json — manim_sections_attempted, success, fallback, fallback_rate
step08/images/assets_ai/*.png      — AI 생성 이미지 (실제 PNG 파일)
step08/narration.wav               — 나레이션 오디오
step08/video.mp4                   — 최종 영상
step11/qa_result.json  — animation_quality_check.pass, script_accuracy_check.pass,
                          youtube_policy_check.pass, human_review.{required,completed},
                          overall_pass
cost.json              — total_cost_krw, gemini_api.total_krw
```

**지식 수집** (`data/knowledge_store/{channelId}/`):
```
discovery/raw/assets.jsonl  — JSONL (줄당 1 JSON):
  { original_trend: {topic}, reinterpreted_title, category, score, grade,
    is_trending, trend_collected_at, topic_type }
series/series_*.json        — { channel_id, base_topic, episode_count,
                                 episodes: [{episode, title, created_at}] }
```

### 기존 코드 패턴
- `getKasRoot()` → `web/lib/fs-helpers.ts`
- 이미지 스트리밍 → `/api/artifacts/{relative-path}` (기존 구현)
  - 예: `/api/artifacts/runs/CH1/run_CH1_xxx/step08/images/assets_ai/section_001.png`
- `glass-card`, `glow-amber`, `glow-success`, `glow-danger`, `ambient-bg` CSS 클래스
- shadcn 컴포넌트: `Card`, `CardContent`, `CardHeader`, `CardTitle`, `CardDescription`, `Badge`, `Button`
- `web/app/api/pipeline/status/route.ts` — API route 패턴 참조

---

## Task 1: Run Detail API route

**Files:**
- Create: `web/app/api/runs/[channelId]/[runId]/route.ts`

- [ ] **Step 1: 파일 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

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
    return JSON.parse(await fs.readFile(filePath, 'utf-8')) as T
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

  // 경로 탈출 방지
  if (channelId.includes('..') || runId.includes('..') ||
      path.isAbsolute(channelId) || path.isAbsolute(runId)) {
    return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
  }

  const kasRoot = getKasRoot()
  const runDir = path.join(kasRoot, 'runs', channelId, runId)

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
  const maninData  = await tryReadJson<Record<string, unknown>>(
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
      manim: maninData ? {
        attempted:    Number(maninData.manim_sections_attempted ?? 0),
        success:      Number(maninData.manim_sections_success ?? 0),
        fallback:     Number(maninData.manim_sections_fallback ?? 0),
        fallback_rate: Number(maninData.fallback_rate ?? 0),
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
  const cost_krw = costData ? Number(costData.total_cost_krw ?? 0) : null

  return NextResponse.json({ manifest, step08, step11, cost_krw } satisfies RunArtifacts)
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep "runs"
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude && git add web/app/api/runs/ && git commit -m "feat: Run 상세 아티팩트 API route 추가"
```

---

## Task 2: Run 상세 페이지

**Files:**
- Create: `web/app/runs/[channelId]/[runId]/page.tsx`

- [ ] **Step 1: 파일 작성**

```typescript
'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, FileText, Image as ImageIcon, Mic, Video,
  CheckCircle2, XCircle, AlertTriangle, Loader2, Clapperboard,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { RunArtifacts } from '@/app/api/runs/[channelId]/[runId]/route'

// 상태 배지
const STATE_CLASS: Record<string, string> = {
  RUNNING:   'bg-blue-500/15 border-blue-500/30 text-blue-400',
  COMPLETED: 'bg-green-500/15 border-green-500/30 text-green-400',
  FAILED:    'bg-red-500/15 border-red-500/30 text-red-400',
  PENDING:   'bg-amber-500/15 border-amber-500/30 text-amber-400',
}

function ArtifactRow({
  icon: Icon,
  label,
  ok,
  detail,
}: {
  icon: React.ElementType
  label: string
  ok: boolean | null
  detail?: string
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/[0.04] last:border-0">
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="flex-1 text-sm">{label}</span>
      {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
      {ok === null ? (
        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
      ) : ok ? (
        <CheckCircle2 className="h-4 w-4 text-green-400" />
      ) : (
        <XCircle className="h-4 w-4 text-red-400" />
      )}
    </div>
  )
}

export default function RunDetailPage() {
  const { channelId, runId } = useParams<{ channelId: string; runId: string }>()
  const [data, setData] = useState<RunArtifacts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImg, setSelectedImg] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/runs/${channelId}/${runId}`)
      if (!res.ok) throw new Error(`${res.status}`)
      setData(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [channelId, runId])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link href="/monitor">
          <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />모니터로</Button>
        </Link>
        <p className="text-sm text-red-400">Run을 찾을 수 없습니다: {error}</p>
      </div>
    )
  }

  const { manifest, step08, step11, cost_krw } = data

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 헤더 */}
      <div>
        <Link href="/monitor">
          <Button variant="ghost" size="sm" className="mb-3 -ml-2">
            <ArrowLeft className="h-4 w-4 mr-1" />모니터로
          </Button>
        </Link>
        <div className="flex items-start gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-sm text-amber-400">{manifest.channel_id}</span>
              <Badge className={cn('border text-xs', STATE_CLASS[manifest.run_state] ?? 'border-white/20 text-white/60')}>
                {manifest.run_state}
              </Badge>
              {cost_krw !== null && cost_krw > 0 && (
                <span className="text-xs text-muted-foreground">₩{cost_krw.toLocaleString()}</span>
              )}
            </div>
            <h1 className="text-xl font-bold tracking-tight leading-snug">{manifest.topic_title}</h1>
            <p className="text-xs text-muted-foreground mt-1">
              {manifest.run_id} · {manifest.created_at?.slice(0, 10)}
              {manifest.topic_score > 0 && ` · 점수 ${manifest.topic_score}`}
            </p>
          </div>
        </div>
      </div>

      {/* Step08 아티팩트 */}
      <Card className="glass-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Clapperboard className="h-4 w-4 text-amber-400" />
            Step08 — 영상 제작
          </CardTitle>
          {step08 ? (
            <CardDescription>
              {step08.section_count}개 섹션 ·
              이미지 {step08.image_paths.length}장 ·
              {step08.manim ? ` Manim 성공 ${step08.manim.success}/${step08.manim.attempted}` : ''}
            </CardDescription>
          ) : (
            <CardDescription>Step08 아직 미실행</CardDescription>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {step08 ? (
            <>
              {/* 아티팩트 체크리스트 */}
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-1">
                <ArtifactRow icon={FileText} label="스크립트" ok={step08.has_script} detail={`${step08.section_count}섹션`} />
                <ArtifactRow icon={Mic} label="나레이션" ok={step08.has_narration} />
                <ArtifactRow icon={Video} label="최종 영상 (video.mp4)" ok={step08.has_video} />
                <ArtifactRow
                  icon={ImageIcon}
                  label="AI 이미지"
                  ok={step08.image_paths.length > 0}
                  detail={`${step08.image_paths.length}장`}
                />
                {step08.manim && (
                  <ArtifactRow
                    icon={Clapperboard}
                    label="Manim 애니메이션"
                    ok={step08.manim.fallback_rate < 0.5}
                    detail={`fallback ${Math.round(step08.manim.fallback_rate * 100)}%`}
                  />
                )}
              </div>

              {/* 제목 후보 */}
              {step08.title_candidates.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">제목 후보</p>
                  <div className="space-y-1">
                    {step08.title_candidates.map((t, i) => (
                      <div
                        key={i}
                        className={cn(
                          'rounded-lg px-3 py-2 text-sm border',
                          step08.selected_title === t
                            ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                            : 'border-white/[0.06] bg-white/[0.02] text-muted-foreground',
                        )}
                      >
                        {step08.selected_title === t && <span className="text-amber-400 mr-1.5">✓</span>}
                        {t}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 이미지 갤러리 */}
              {step08.image_paths.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">이미지 갤러리</p>
                  <div className="grid grid-cols-3 gap-2">
                    {step08.image_paths.map((imgPath, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedImg(imgPath)}
                        className="rounded-lg overflow-hidden border border-white/[0.06] hover:border-amber-500/30 transition-colors aspect-video bg-white/[0.02]"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`/api/artifacts/${imgPath}`}
                          alt={`scene ${i + 1}`}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">아직 영상 제작이 시작되지 않았습니다.</p>
          )}
        </CardContent>
      </Card>

      {/* Step11 QA */}
      <Card className={cn('glass-card', step11 ? (step11.overall_pass ? 'glow-success' : 'glow-danger') : '')}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-400" />
            Step11 — QA 검수
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step11 ? (
            <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-1">
              <ArtifactRow icon={CheckCircle2} label="애니메이션 품질" ok={step11.animation_ok} />
              <ArtifactRow icon={CheckCircle2} label="스크립트 정확도" ok={step11.script_ok} />
              <ArtifactRow icon={CheckCircle2} label="YouTube 정책" ok={step11.policy_ok} />
              <ArtifactRow
                icon={CheckCircle2}
                label="휴먼 리뷰"
                ok={!step11.human_review_required || step11.human_review_completed}
                detail={step11.human_review_required ? (step11.human_review_completed ? '완료' : '대기') : '불필요'}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Step11 QA 미실행</p>
          )}
        </CardContent>
      </Card>

      {/* 이미지 라이트박스 */}
      {selectedImg && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedImg(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/artifacts/${selectedImg}`}
            alt="확대 보기"
            className="max-w-full max-h-full rounded-xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep -E "runs|RunDetail"
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude && git add web/app/runs/ && git commit -m "feat: Run 상세 페이지 추가 (Step08 아티팩트·이미지·QA)"
```

---

## Task 3: Knowledge API route

**Files:**
- Create: `web/app/api/knowledge/route.ts`

- [ ] **Step 1: 파일 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface KnowledgeTopic {
  original_topic: string
  reinterpreted_title: string
  category: string
  score: number
  grade: string
  is_trending: boolean
  trend_collected_at: string
  topic_type: string
}

export interface SeriesEntry {
  series_name: string
  episode_count: number
  episodes: { episode: number; title: string }[]
}

export interface ChannelKnowledge {
  channel_id: string
  topics: KnowledgeTopic[]
  series: SeriesEntry[]
}

/** assets.jsonl을 파싱해 KnowledgeTopic[] 반환 */
async function readTopics(channelId: string, kasRoot: string): Promise<KnowledgeTopic[]> {
  const jsonlPath = path.join(kasRoot, 'data', 'knowledge_store', channelId, 'discovery', 'raw', 'assets.jsonl')
  try {
    const text = await fs.readFile(jsonlPath, 'utf-8')
    const topics: KnowledgeTopic[] = []
    for (const line of text.split('\n')) {
      if (!line.trim()) continue
      try {
        const m = JSON.parse(line) as Record<string, unknown>
        const ot = (m.original_trend ?? {}) as Record<string, unknown>
        topics.push({
          original_topic:    String(ot.topic ?? m.reinterpreted_title ?? ''),
          reinterpreted_title: String(m.reinterpreted_title ?? ''),
          category:          String(m.category ?? ''),
          score:             Number(m.score ?? 0),
          grade:             String(m.grade ?? ''),
          is_trending:       Boolean(m.is_trending),
          trend_collected_at: String(m.trend_collected_at ?? ''),
          topic_type:        String(m.topic_type ?? 'trending'),
        })
      } catch { /* 잘못된 줄 무시 */ }
    }
    return topics
  } catch {
    return []
  }
}

/** series/*.json 목록 반환 */
async function readSeries(channelId: string, kasRoot: string): Promise<SeriesEntry[]> {
  const seriesDir = path.join(kasRoot, 'data', 'knowledge_store', channelId, 'series')
  const result: SeriesEntry[] = []
  try {
    const files = await fs.readdir(seriesDir)
    for (const file of files) {
      if (!file.endsWith('.json')) continue
      try {
        const raw = JSON.parse(
          await fs.readFile(path.join(seriesDir, file), 'utf-8')
        ) as Record<string, unknown>
        const eps = Array.isArray(raw.episodes) ? (raw.episodes as Record<string, unknown>[]) : []
        result.push({
          series_name:   String(raw.base_topic ?? file.replace('.json', '')),
          episode_count: Number(raw.episode_count ?? eps.length),
          episodes:      eps.map((e) => ({
            episode: Number(e.episode ?? 0),
            title:   String(e.title ?? ''),
          })),
        })
      } catch { /* 파일 읽기 실패 무시 */ }
    }
  } catch { /* series/ 없음 */ }
  return result
}

/**
 * GET /api/knowledge?channel=CH1
 * channel 파라미터 없으면 CH1~CH7 전체 반환.
 */
export async function GET(req: NextRequest) {
  const kasRoot = getKasRoot()
  const channelParam = req.nextUrl.searchParams.get('channel')

  const knowledgeRoot = path.join(kasRoot, 'data', 'knowledge_store')
  let channelIds: string[]

  if (channelParam) {
    // 경로 탈출 방지
    if (channelParam.includes('..') || path.isAbsolute(channelParam)) {
      return NextResponse.json({ error: 'Invalid channel' }, { status: 400 })
    }
    channelIds = [channelParam]
  } else {
    try {
      const entries = await fs.readdir(knowledgeRoot)
      channelIds = entries.filter((e) => /^CH\d+$/.test(e))
    } catch {
      channelIds = []
    }
  }

  const channels: ChannelKnowledge[] = await Promise.all(
    channelIds.map(async (ch) => ({
      channel_id: ch,
      topics:     await readTopics(ch, kasRoot),
      series:     await readSeries(ch, kasRoot),
    }))
  )

  return NextResponse.json({ channels })
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep knowledge
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude && git add web/app/api/knowledge/ && git commit -m "feat: 지식 수집 API route 추가 (JSONL + 시리즈 파싱)"
```

---

## Task 4: 지식 수집 뷰어 페이지

**Files:**
- Create: `web/app/knowledge/page.tsx`

- [ ] **Step 1: 파일 작성**

```typescript
'use client'

import { useState, useEffect, useCallback } from 'react'
import { BookOpen, TrendingUp, Layers, Loader2, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ChannelKnowledge, KnowledgeTopic, SeriesEntry } from '@/app/api/knowledge/route'

const CHANNEL_LABELS: Record<string, string> = {
  CH1: '경제', CH2: '부동산', CH3: '심리',
  CH4: '미스터리', CH5: '전쟁사', CH6: '과학', CH7: '역사',
}

const GRADE_CLASS: Record<string, string> = {
  approved: 'bg-green-500/15 border-green-500/30 text-green-400',
  reject:   'bg-red-500/15 border-red-500/30 text-red-400',
}

function TopicRow({ topic }: { topic: KnowledgeTopic }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-snug truncate">{topic.reinterpreted_title || topic.original_topic}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {topic.category} · {topic.trend_collected_at?.slice(0, 10)}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">{topic.score.toFixed(1)}</span>
        <Badge className={cn('border text-xs', GRADE_CLASS[topic.grade] ?? 'border-white/20 text-white/60')}>
          {topic.grade}
        </Badge>
        {topic.is_trending && (
          <TrendingUp className="h-3.5 w-3.5 text-amber-400" />
        )}
      </div>
    </div>
  )
}

function SeriesCard({ series }: { series: SeriesEntry }) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium">{series.series_name}</p>
        <Badge className="border border-amber-500/30 bg-amber-500/10 text-amber-400 text-xs">
          {series.episode_count}편
        </Badge>
      </div>
      <div className="space-y-1">
        {series.episodes.map((ep) => (
          <p key={ep.episode} className="text-xs text-muted-foreground">
            EP{ep.episode} — {ep.title}
          </p>
        ))}
      </div>
    </div>
  )
}

function ChannelKnowledgePanel({ ck }: { ck: ChannelKnowledge }) {
  const [tab, setTab] = useState<'topics' | 'series'>('topics')

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-amber-400" />
              {ck.channel_id} — {CHANNEL_LABELS[ck.channel_id] ?? ck.channel_id}
            </CardTitle>
            <CardDescription>
              트렌드 {ck.topics.length}개 · 시리즈 {ck.series.length}개
            </CardDescription>
          </div>
          <div className="flex gap-1">
            <Button
              size="sm"
              variant={tab === 'topics' ? 'default' : 'ghost'}
              onClick={() => setTab('topics')}
              className={cn('text-xs h-7', tab === 'topics' && 'bg-amber-500/15 border border-amber-500/30 text-amber-400')}
            >
              <TrendingUp className="h-3 w-3 mr-1" />트렌드
            </Button>
            <Button
              size="sm"
              variant={tab === 'series' ? 'default' : 'ghost'}
              onClick={() => setTab('series')}
              className={cn('text-xs h-7', tab === 'series' && 'bg-blue-500/15 border border-blue-500/30 text-blue-400')}
            >
              <Layers className="h-3 w-3 mr-1" />시리즈
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {tab === 'topics' && (
          ck.topics.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">수집된 트렌드 없음</p>
          ) : (
            <div className="max-h-64 overflow-y-auto">
              {ck.topics.map((t, i) => <TopicRow key={i} topic={t} />)}
            </div>
          )
        )}
        {tab === 'series' && (
          ck.series.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">등록된 시리즈 없음</p>
          ) : (
            <div className="space-y-3">
              {ck.series.map((s, i) => <SeriesCard key={i} series={s} />)}
            </div>
          )
        )}
      </CardContent>
    </Card>
  )
}

export default function KnowledgePage() {
  const [channels, setChannels] = useState<ChannelKnowledge[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/knowledge')
      const data: { channels: ChannelKnowledge[] } = await res.json()
      // 토픽 있는 채널만 필터링
      setChannels(data.channels.filter((c) => c.topics.length > 0 || c.series.length > 0))
    } catch { /* 무시 */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            <h1 className="text-2xl font-bold tracking-tight">지식 수집</h1>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            채널별 트렌드 토픽 및 시리즈 계획
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={load}
          disabled={loading}
          className="text-muted-foreground"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : channels.length === 0 ? (
        <Card className="glass-card">
          <CardContent className="py-12 text-center text-muted-foreground text-sm">
            지식 수집 데이터가 없습니다. 파이프라인을 실행하면 데이터가 표시됩니다.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {channels.map((ck) => (
            <ChannelKnowledgePanel key={ck.channel_id} ck={ck} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep knowledge
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude && git add web/app/knowledge/ && git commit -m "feat: 지식 수집 뷰어 페이지 추가 (트렌드·시리즈)"
```

---

## Task 5: 사이드바 + Monitor RunRow 링크 + 빌드 검증

**Files:**
- Modify: `web/components/sidebar-nav.tsx`
- Modify: `web/app/monitor/page.tsx`

- [ ] **Step 1: `sidebar-nav.tsx` 읽기 및 현재 import 확인**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && grep -n "lucide\|navItems\|Monitor" components/sidebar-nav.tsx | head -20
```

Expected: 현재 `Monitor` 아이콘 import + navItems 배열 확인

- [ ] **Step 2: 사이드바에 `BookOpen` import + "지식 수집" 메뉴 추가**

`sidebar-nav.tsx` lucide import에 `BookOpen` 추가:
```typescript
import {
  LayoutDashboard, TrendingUp, DollarSign, ShieldAlert,
  Brain, Monitor, ClipboardCheck, CreditCard,
  Settings, Zap, BookOpen,
} from 'lucide-react'
```

navItems에 "파이프라인 모니터" 바로 뒤에 삽입:
```typescript
const navItems = [
  { title: '전체 KPI',          url: '/',         icon: LayoutDashboard },
  { title: '트렌드 관리',       url: '/trends',   icon: TrendingUp },
  { title: '수익 추적',         url: '/revenue',  icon: DollarSign },
  { title: '리스크 모니터링',   url: '/risk',     icon: ShieldAlert },
  { title: '학습 피드백',       url: '/learning', icon: Brain },
  { title: '파이프라인 모니터', url: '/monitor',  icon: Monitor },
  { title: '지식 수집',         url: '/knowledge', icon: BookOpen },
  { title: 'QA 검수',           url: '/qa',       icon: ClipboardCheck },
  { title: '비용/쿼터',         url: '/cost',     icon: CreditCard },
]
```

- [ ] **Step 3: `monitor/page.tsx`의 RunRow에 Link 추가**

`web/app/monitor/page.tsx`를 읽어 `RunRow` 컴포넌트를 찾고, 아래와 같이 `Link`를 추가한다.

현재 RunRow:
```typescript
function RunRow({ run, compact = false }: { run: ManifestSummary; compact?: boolean }) {
  return (
    <div className={cn(
      'flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02]',
      compact ? 'px-3 py-1.5' : 'px-3 py-2.5',
    )}>
```

변경 후 RunRow (Link로 감싸기):
```typescript
import Link from 'next/link'

function RunRow({ run, compact = false }: { run: ManifestSummary; compact?: boolean }) {
  return (
    <Link href={`/runs/${run.channel_id}/${run.run_id}`} className="block hover:opacity-80 transition-opacity">
      <div className={cn(
        'flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02]',
        compact ? 'px-3 py-1.5' : 'px-3 py-2.5',
      )}>
```

닫는 `</div>` 다음에 `</Link>` 추가:
```typescript
      </div>
    </Link>
  )
}
```

- [ ] **Step 4: TypeScript 전체 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1
```

Expected: 0 errors

- [ ] **Step 5: Next.js 빌드 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npm run build 2>&1 | tail -30
```

Expected: 성공 빌드, `/knowledge`, `/runs/[channelId]/[runId]`, `/api/knowledge`, `/api/runs/[channelId]/[runId]` 라우트 포함

- [ ] **Step 6: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude && git add web/components/sidebar-nav.tsx web/app/monitor/ && git commit -m "feat: 사이드바 지식수집 메뉴 + 모니터 RunRow 링크 추가"
```

---

## Self-Review

**1. 스펙 커버리지**
- Run 상세 (Step08 체크리스트) → Task 1 + 2 ✅
- 이미지 갤러리 → Task 2 (image_paths + `/api/artifacts/`) ✅
- Step09~11 상태 → Task 2 (Step11 QA 표시, narration/video has_ 체크) ✅
- Monitor RunRow 링크 → Task 5 ✅
- 지식 수집 KnowledgePackage 목록 → Task 3 + 4 (topics, JSONL 파싱) ✅
- 시리즈 목록 → Task 3 + 4 ✅
- 사이드바 "지식 수집" 메뉴 → Task 5 ✅

**2. Placeholder 없음**: 모든 코드 완전 구현 ✅

**3. 타입 일관성**
- `RunArtifacts` — Task 1 export → Task 2 `import type` ✅
- `ChannelKnowledge`, `KnowledgeTopic`, `SeriesEntry` — Task 3 export → Task 4 `import type` ✅
- `ManifestSummary` — `@/app/api/pipeline/status/route` (기존 export) → Task 5에서 사용 ✅
