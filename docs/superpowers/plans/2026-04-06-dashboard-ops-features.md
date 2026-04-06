# KAS 대시보드 운영 기능 5종 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹 대시보드에서 Step11 QA 검수·HITL 알림·Step10 배리언트 선택·deferred_jobs 재시도·파이프라인 트리거 기능을 구현해 운영자가 CLI 없이 파이프라인을 관리할 수 있도록 한다.

**Architecture:** KAS 백엔드 JSON 파일을 Next.js API route/Server Action에서 Node.js `fs` 모듈로 직접 읽고 쓴다. 파이프라인 트리거는 `child_process.spawn()`으로 Python 서브프로세스를 비동기로 실행한다. 모든 파일 I/O는 `web/lib/fs-helpers.ts` 한 곳에서 처리한다.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 (CSS-first, globals.css) · shadcn/ui · Node.js `fs/promises` · `child_process.spawn` · 기존 glassmorphism dark 테마 유지

---

## 파일 구조 결정

**신규 파일:**
| 파일 | 역할 |
|------|------|
| `web/lib/fs-helpers.ts` | KAS_ROOT 해석, JSON 읽기/쓰기, QA 대기 run 스캔 |
| `web/app/api/hitl-signals/route.ts` | GET 미해결 신호 목록, PATCH 신호 해결 |
| `web/components/hitl-banner.tsx` | 미해결 HITL 신호 알림 배너 (클라이언트) |
| `web/app/qa/page.tsx` | QA 검수 + 배리언트 선택 통합 페이지 |
| `web/app/qa/actions.ts` | approveHumanReview, selectTitleVariant 서버 액션 |
| `web/app/api/artifacts/[...path]/route.ts` | 로컬 이미지 파일 프록시 (썸네일 표시) |
| `web/app/api/deferred-jobs/route.ts` | GET 이연 작업 목록, POST 재시도 |
| `web/app/api/pipeline/trigger/route.ts` | POST 파이프라인 트리거 (Python 서브프로세스) |
| `scripts/web_runner.py` | 웹에서 호출하는 Python 진입점 |

**수정 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `web/app/layout.tsx` | `<HitlBanner />` 헤더 아래 삽입 |
| `web/components/sidebar-nav.tsx` | QA 검수 메뉴 항목 추가 |
| `web/app/cost/page.tsx` | deferred jobs 섹션 추가 |
| `web/app/channels/[id]/page.tsx` | 파이프라인 트리거 카드 추가 |

---

## 컨텍스트 (서브에이전트용)

### 프로젝트 경로
- KAS 루트: `C:\Users\조찬우\Desktop\ai_stuidio_claude`
- 웹 루트: `C:\Users\조찬우\Desktop\ai_stuidio_claude\web`
- dev server: `localhost:3002`

### 중요 데이터 파일
- `data/global/notifications/hitl_signals.json` — HITL 신호 배열 (파일이 없을 수 있음, graceful 처리 필요)
- `data/global/quota/youtube_quota_daily.json` — `.deferred_jobs` 배열 포함
- `runs/{channelId}/{runId}/step11/qa_result.json` — QA 결과 (human_review.required/completed)
- `runs/{channelId}/{runId}/step08/variants/variant_manifest.json` — 배리언트 목록
- `runs/{channelId}/{runId}/step08/title.json` — 선택된 제목

### hitl_signals.json 스키마
```json
[
  {
    "id": "uuid-string",
    "type": "pytest_failure | pipeline_failure | schema_mismatch",
    "details": { "run_id": "...", "step": "...", "error": "..." },
    "timestamp": "2026-04-06T18:00:00+00:00",
    "resolved": false
  }
]
```

### qa_result.json 스키마
```json
{
  "channel_id": "CH1",
  "run_id": "test_run_001",
  "qa_timestamp": "2026-04-05T06:33:40Z",
  "animation_quality_check": { "pass": false, "vision_qa": { "pass": true, "skipped": true } },
  "script_accuracy_check": { "pass": false, "disclaimer_key": "financial_disclaimer" },
  "youtube_policy_check": { "ai_label_placed": false, "disclaimer_placed": false, "pass": false },
  "human_review": { "required": true, "completed": false, "reviewer": null, "sla_hours": 24 },
  "affiliate_formula_check": { "purchase_rate_applied": 0, "formula_correct": false },
  "overall_pass": false
}
```

### variant_manifest.json 스키마
```json
{
  "channel_id": "CH1",
  "run_id": "run_CH1_xxx",
  "title_variants": [
    { "ref": "01", "mode": "authority", "title": "...", "seo_keyword_included": true },
    { "ref": "02", "mode": "curiosity", "title": "...", "seo_keyword_included": true },
    { "ref": "03", "mode": "benefit",   "title": "...", "seo_keyword_included": false }
  ],
  "thumbnail_variants": [
    { "ref": "01", "mode": "style", "path": "runs/CH1/run_xxx/step08/variants/thumbnail_variant_01.png" },
    { "ref": "02", "mode": "data",  "path": "runs/CH1/run_xxx/step08/variants/thumbnail_variant_02.png" },
    { "ref": "03", "mode": "text",  "path": "runs/CH1/run_xxx/step08/variants/thumbnail_variant_03.png" }
  ]
}
```

### youtube_quota_daily.json 스키마
```json
{
  "date": "2026-04-05",
  "quota_used": 0,
  "quota_limit": 10000,
  "quota_remaining": 10000,
  "deferred_jobs": []
}
```

### 기존 패턴 참고
- Server Action 패턴: `web/app/trends/actions.ts` (use server, try/catch, revalidatePath)
- 클라이언트 fetch 패턴: `web/app/cost/page.tsx` (useEffect + supabase)
- 타입 정의: `web/lib/types.ts`
- 경로 별칭: `@/` = `web/` (tsconfig에서 설정됨)
- Tailwind 다크모드: `.dark .glass-card` 2-class 셀렉터, `globals.css`에서만 관리
- glassmorphism 클래스: `glass-card`, `glow-amber`, `glow-success`, `glow-danger`, `ambient-bg`

### KAS_ROOT 해석 원칙
Next.js dev 서버의 `process.cwd()` = `web/` 디렉토리이므로:
```typescript
const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')
// → C:\Users\조찬우\Desktop\ai_stuidio_claude
```

---

## Task 1: fs-helpers.ts — KAS 파일시스템 헬퍼

**Files:**
- Create: `web/lib/fs-helpers.ts`

- [ ] **Step 1: TypeScript 타입 에러 확인 (파일 없음 상태)**

```bash
cd web && npx tsc --noEmit 2>&1 | head -5
```

Expected: 0 errors 또는 기존 에러만 (fs-helpers.ts 관련 에러 없음)

- [ ] **Step 2: `web/lib/fs-helpers.ts` 작성**

```typescript
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

/** runs/{channelId}/*/step11/qa_result.json 중 수동 검수 미완료 항목 반환 */
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
```

- [ ] **Step 3: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep fs-helpers
```

Expected: 출력 없음 (에러 없음)

- [ ] **Step 4: 커밋**

```bash
cd web && git add lib/fs-helpers.ts
git commit -m "feat: KAS 파일시스템 헬퍼 추가 (fs-helpers.ts)"
```

---

## Task 2: HITL 신호 API route + 배너 컴포넌트

**Files:**
- Create: `web/app/api/hitl-signals/route.ts`
- Create: `web/components/hitl-banner.tsx`

- [ ] **Step 1: API route 작성 — `web/app/api/hitl-signals/route.ts`**

```typescript
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
```

- [ ] **Step 2: 배너 컴포넌트 작성 — `web/components/hitl-banner.tsx`**

```typescript
'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { HitlSignal } from '@/lib/fs-helpers'

const TYPE_LABEL: Record<string, string> = {
  pytest_failure:   'pytest 실패',
  pipeline_failure: '파이프라인 실패',
  schema_mismatch:  '스키마 불일치',
}

export function HitlBanner() {
  const [signals, setSignals] = useState<HitlSignal[]>([])

  useEffect(() => {
    fetch('/api/hitl-signals')
      .then((r) => r.json())
      .then((data: HitlSignal[]) => setSignals(data))
      .catch(() => {/* 조용히 실패 */})
  }, [])

  async function dismiss(id: string) {
    await fetch('/api/hitl-signals', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    })
    setSignals((prev) => prev.filter((s) => s.id !== id))
  }

  if (signals.length === 0) return null

  return (
    <div className="px-4 md:px-6 pt-2 space-y-1.5">
      {signals.map((signal) => (
        <div
          key={signal.id}
          className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm glow-danger"
        >
          <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-red-300">
              [{TYPE_LABEL[signal.type] ?? signal.type}]
            </span>{' '}
            <span className="text-red-200/80">
              {(signal.details as { error?: string; run_id?: string }).error
                ?? (signal.details as { run_id?: string }).run_id
                ?? '운영자 확인 필요'}
            </span>
            <span className="ml-2 text-red-400/60 text-xs">
              {signal.timestamp?.slice(0, 16).replace('T', ' ')}
            </span>
          </div>
          <button
            onClick={() => dismiss(signal.id)}
            className="shrink-0 text-red-400/60 hover:text-red-300 transition-colors"
            aria-label="닫기"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep -E "hitl|banner"
```

Expected: 출력 없음 (에러 없음)

- [ ] **Step 4: 커밋**

```bash
cd web && git add app/api/hitl-signals/route.ts components/hitl-banner.tsx
git commit -m "feat: HITL 신호 API route 및 배너 컴포넌트 추가"
```

---

## Task 3: layout.tsx에 HITL 배너 통합

**Files:**
- Modify: `web/app/layout.tsx`

현재 `web/app/layout.tsx`의 `<main>` 바로 위, `<header>` 닫히는 태그 직후에 `<HitlBanner />`를 삽입한다.

- [ ] **Step 1: layout.tsx 현재 구조 확인**

```bash
cd web && grep -n "HitlBanner\|<main\|</header\|<header" app/layout.tsx
```

Expected: `<header`, `</header`, `<main` 라인 번호 출력

- [ ] **Step 2: layout.tsx 수정**

`web/app/layout.tsx` 파일에서 다음 두 가지를 변경:

**import 추가** (기존 import 블록 끝에 추가):
```typescript
import { HitlBanner } from '@/components/hitl-banner'
```

**`</header>` 바로 뒤에 삽입**:
```tsx
</header>
<HitlBanner />
```

즉, 변경 전:
```tsx
              </header>
              <main className="flex-1 overflow-auto p-4 md:p-6">
```
변경 후:
```tsx
              </header>
              <HitlBanner />
              <main className="flex-1 overflow-auto p-4 md:p-6">
```

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npx tsc --noEmit 2>&1 | grep layout
```

Expected: 출력 없음

- [ ] **Step 4: 커밋**

```bash
cd web && git add app/layout.tsx
git commit -m "feat: layout.tsx에 HITL 배너 통합"
```

---

## Task 4: QA 검수 + 배리언트 선택 페이지

**Files:**
- Create: `web/app/qa/actions.ts`
- Create: `web/app/qa/page.tsx`

### Task 4a: actions.ts 작성

- [ ] **Step 1: `web/app/qa/actions.ts` 작성**

```typescript
'use server'

import { revalidatePath } from 'next/cache'
import { readKasJson, writeKasJson, QaResult, VariantManifest } from '@/lib/fs-helpers'

/**
 * Step11 QA 결과의 human_review.completed를 true로 업데이트
 * 이후 파이프라인이 Step12 업로드를 진행할 수 있게 된다
 */
export async function approveHumanReview(
  channelId: string,
  runId: string,
  reviewer: string = 'dashboard',
): Promise<{ ok: boolean; error?: string }> {
  const relPath = `runs/${channelId}/${runId}/step11/qa_result.json`
  const qa = await readKasJson<QaResult>(relPath)
  if (!qa) return { ok: false, error: 'qa_result.json 파일 없음' }

  const updated: QaResult = {
    ...qa,
    human_review: {
      ...qa.human_review,
      completed: true,
      reviewer,
    },
  }
  await writeKasJson(relPath, updated)
  revalidatePath('/qa')
  return { ok: true }
}

/**
 * Step10 배리언트 선택: variant_manifest.json의 selected_title_ref 업데이트
 * + step08/title.json의 selected 필드도 선택된 제목으로 업데이트
 */
export async function selectTitleVariant(
  channelId: string,
  runId: string,
  titleRef: string,
): Promise<{ ok: boolean; error?: string }> {
  const manifestPath = `runs/${channelId}/${runId}/step08/variants/variant_manifest.json`
  const manifest = await readKasJson<VariantManifest>(manifestPath)
  if (!manifest) return { ok: false, error: 'variant_manifest.json 파일 없음' }

  const selected = manifest.title_variants.find((v) => v.ref === titleRef)
  if (!selected) return { ok: false, error: `ref "${titleRef}" 없음` }

  // variant_manifest.json 업데이트
  const updatedManifest: VariantManifest = { ...manifest, selected_title_ref: titleRef }
  await writeKasJson(manifestPath, updatedManifest)

  // step08/title.json의 selected 업데이트
  const titlePath = `runs/${channelId}/${runId}/step08/title.json`
  const titleJson = await readKasJson<{ title_candidates: string[]; selected: string }>(titlePath)
  if (titleJson) {
    await writeKasJson(titlePath, { ...titleJson, selected: selected.title })
  }

  revalidatePath('/qa')
  return { ok: true }
}

/**
 * Step10 배리언트 선택: variant_manifest.json의 selected_thumbnail_ref 업데이트
 */
export async function selectThumbnailVariant(
  channelId: string,
  runId: string,
  thumbnailRef: string,
): Promise<{ ok: boolean; error?: string }> {
  const manifestPath = `runs/${channelId}/${runId}/step08/variants/variant_manifest.json`
  const manifest = await readKasJson<VariantManifest>(manifestPath)
  if (!manifest) return { ok: false, error: 'variant_manifest.json 파일 없음' }

  const updatedManifest: VariantManifest = { ...manifest, selected_thumbnail_ref: thumbnailRef }
  await writeKasJson(manifestPath, updatedManifest)
  revalidatePath('/qa')
  return { ok: true }
}
```

### Task 4b: page.tsx 작성

- [ ] **Step 2: `web/app/qa/page.tsx` 작성**

이 파일은 QA 검수 대기 목록과 배리언트 선택을 하나의 페이지에서 보여주는 클라이언트 컴포넌트다. 서버 액션을 호출해 파일을 업데이트한다.

```typescript
'use client'

import { useState, useEffect, useTransition } from 'react'
import {
  ClipboardCheck, CheckCircle2, XCircle, ChevronRight,
  Type, Image as ImageIcon, Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { approveHumanReview, selectTitleVariant, selectThumbnailVariant } from './actions'
import type { QaPendingRun, VariantManifest } from '@/lib/fs-helpers'

const MODE_LABEL: Record<string, string> = {
  authority: '권위형',
  curiosity: '호기심형',
  benefit: '이득형',
}

function QaCheckRow({ label, pass }: { label: string; pass: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {pass
        ? <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
        : <XCircle className="h-4 w-4 text-red-400 shrink-0" />}
      <span className={pass ? 'text-muted-foreground' : 'text-red-300'}>{label}</span>
    </div>
  )
}

function QaCard({ item, onApprove }: { item: QaPendingRun; onApprove: () => void }) {
  const [isPending, startTransition] = useTransition()
  const qa = item.qaResult

  function handleApprove() {
    startTransition(async () => {
      await approveHumanReview(item.channelId, item.runId)
      onApprove()
    })
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="font-mono text-amber-400">{item.channelId}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-normal text-muted-foreground truncate max-w-[240px]">
                {item.runId}
              </span>
            </CardTitle>
            <CardDescription className="mt-1 text-xs">
              QA 타임스탬프: {qa.qa_timestamp?.slice(0, 16).replace('T', ' ')}
            </CardDescription>
          </div>
          <Badge variant="outline" className="border-amber-500/40 text-amber-400 shrink-0">
            검수 대기
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* QA 체크 항목 */}
        <div className="space-y-1.5 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <QaCheckRow label="애니메이션 품질" pass={qa.animation_quality_check.pass} />
          <QaCheckRow label="스크립트 정확성" pass={qa.script_accuracy_check.pass} />
          <QaCheckRow label="YouTube 정책" pass={qa.youtube_policy_check.pass} />
          <QaCheckRow label="수익 공식" pass={qa.affiliate_formula_check.formula_correct} />
        </div>

        {/* 전체 통과 여부 */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            자동 QA: {qa.overall_pass ? '통과' : '미통과'} ·{' '}
            SLA {qa.human_review.sla_hours}시간
          </span>
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isPending}
            className="bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
            )}
            수동 검수 승인
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function VariantCard({ channelId, runId, manifest, onUpdate }: {
  channelId: string
  runId: string
  manifest: VariantManifest
  onUpdate: () => void
}) {
  const [isPending, startTransition] = useTransition()

  function handleSelectTitle(ref: string) {
    startTransition(async () => {
      await selectTitleVariant(channelId, runId, ref)
      onUpdate()
    })
  }

  function handleSelectThumbnail(ref: string) {
    startTransition(async () => {
      await selectThumbnailVariant(channelId, runId, ref)
      onUpdate()
    })
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <span className="font-mono text-blue-400">{channelId}</span>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-normal text-muted-foreground truncate max-w-[240px]">
            {runId}
          </span>
        </CardTitle>
        <CardDescription>Step10 배리언트 선택</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 제목 배리언트 */}
        <div>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
            <Type className="h-3.5 w-3.5" /> 제목 배리언트
          </p>
          <div className="space-y-2">
            {manifest.title_variants.map((v) => {
              const isSelected = manifest.selected_title_ref === v.ref
              return (
                <div
                  key={v.ref}
                  className={cn(
                    'flex items-start justify-between gap-3 p-2.5 rounded-lg border transition-colors cursor-pointer',
                    isSelected
                      ? 'border-amber-500/50 bg-amber-500/10 glow-amber'
                      : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]',
                  )}
                  onClick={() => !isPending && handleSelectTitle(v.ref)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-snug">{v.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {MODE_LABEL[v.mode] ?? v.mode}
                      {v.seo_keyword_included && ' · SEO ✓'}
                    </p>
                  </div>
                  {isSelected && (
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* 썸네일 배리언트 */}
        {manifest.thumbnail_variants.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
              <ImageIcon className="h-3.5 w-3.5" /> 썸네일 배리언트
            </p>
            <div className="flex gap-2">
              {manifest.thumbnail_variants.map((v) => {
                const isSelected = manifest.selected_thumbnail_ref === v.ref
                const proxyUrl = `/api/artifacts/${v.path.replace(/\\/g, '/')}`
                return (
                  <button
                    key={v.ref}
                    onClick={() => !isPending && handleSelectThumbnail(v.ref)}
                    className={cn(
                      'relative flex-1 aspect-video rounded-lg border overflow-hidden transition-all',
                      isSelected
                        ? 'border-amber-500/60 shadow-[0_0_12px_rgba(245,158,11,0.4)]'
                        : 'border-white/[0.08] hover:border-white/20',
                    )}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={proxyUrl}
                      alt={`썸네일 ${v.ref}`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                    <div className="absolute bottom-0 inset-x-0 bg-black/60 px-2 py-1 text-xs text-center">
                      {v.ref}
                    </div>
                    {isSelected && (
                      <div className="absolute top-1 right-1">
                        <CheckCircle2 className="h-4 w-4 text-amber-400" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// 클라이언트에서 /api/qa-data를 호출해 QA 대기 목록과 배리언트 목록을 가져온다
export default function QaPage() {
  const [pendingQa, setPendingQa] = useState<QaPendingRun[]>([])
  const [variants, setVariants] = useState<Array<{
    channelId: string; runId: string; manifest: VariantManifest
  }>>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const [qaRes, varRes] = await Promise.all([
        fetch('/api/qa-data?type=pending'),
        fetch('/api/qa-data?type=variants'),
      ])
      const qaData = await qaRes.json()
      const varData = await varRes.json()
      setPendingQa(qaData)
      setVariants(varData)
    } catch { /* 네트워크 에러 무시 */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <div className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5" />
          <h1 className="text-2xl font-bold tracking-tight">QA 검수</h1>
        </div>
        <p className="text-muted-foreground text-sm mt-1">수동 검수 승인 및 Step10 배리언트 선택</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          <span>로딩 중...</span>
        </div>
      ) : (
        <>
          {/* QA 검수 대기 섹션 */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              수동 검수 대기 ({pendingQa.length})
            </h2>
            {pendingQa.length === 0 ? (
              <Card className="glass-card">
                <CardContent className="py-10 text-center text-muted-foreground text-sm">
                  <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-400" />
                  검수 대기 항목 없음
                </CardContent>
              </Card>
            ) : (
              pendingQa.map((item) => (
                <QaCard key={`${item.channelId}-${item.runId}`} item={item} onApprove={load} />
              ))
            )}
          </section>

          {/* 배리언트 선택 섹션 */}
          {variants.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                배리언트 선택 ({variants.length})
              </h2>
              {variants.map((v) => (
                <VariantCard
                  key={`${v.channelId}-${v.runId}`}
                  channelId={v.channelId}
                  runId={v.runId}
                  manifest={v.manifest}
                  onUpdate={load}
                />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: `/api/qa-data` route 작성 — `web/app/api/qa-data/route.ts`**

```typescript
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
```

- [ ] **Step 4: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep -E "qa/"
```

Expected: 출력 없음

- [ ] **Step 5: 커밋**

```bash
cd web && git add app/qa/ app/api/qa-data/
git commit -m "feat: QA 검수 + 배리언트 선택 페이지 추가"
```

---

## Task 5: 이미지 프록시 API route

**Files:**
- Create: `web/app/api/artifacts/[...path]/route.ts`

썸네일 등 KAS 로컬 이미지를 브라우저에서 볼 수 있도록 파일을 스트리밍한다.

- [ ] **Step 1: `web/app/api/artifacts/[...path]/route.ts` 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')

const EXT_TO_MIME: Record<string, string> = {
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.mp4':  'video/mp4',
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path: segments } = await params
  // path 세그먼트를 결합해 KAS 루트 기준 절대경로 생성
  const relativePath = segments.join('/')
  const fullPath = path.join(KAS_ROOT, relativePath)

  // 경로 트래버설 방지: fullPath가 KAS_ROOT 하위인지 검증
  const resolved = path.resolve(fullPath)
  if (!resolved.startsWith(path.resolve(KAS_ROOT))) {
    return new NextResponse('Forbidden', { status: 403 })
  }

  try {
    const buffer = await fs.readFile(resolved)
    const ext = path.extname(resolved).toLowerCase()
    const contentType = EXT_TO_MIME[ext] ?? 'application/octet-stream'
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch {
    return new NextResponse('Not Found', { status: 404 })
  }
}
```

- [ ] **Step 2: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep "artifacts"
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd web && git add app/api/artifacts/
git commit -m "feat: KAS 로컬 파일 이미지 프록시 API route 추가"
```

---

## Task 6: deferred_jobs 재시도 UI

**Files:**
- Create: `web/app/api/deferred-jobs/route.ts`
- Modify: `web/app/cost/page.tsx`

### Task 6a: deferred-jobs API route

- [ ] **Step 1: `web/app/api/deferred-jobs/route.ts` 작성**

```typescript
import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import { readKasJson, YoutubeQuotaFile } from '@/lib/fs-helpers'

const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')
const QUOTA_PATH = 'data/global/quota/youtube_quota_daily.json'

/** GET /api/deferred-jobs — deferred_jobs 목록 반환 */
export async function GET() {
  const quota = await readKasJson<YoutubeQuotaFile>(QUOTA_PATH)
  return NextResponse.json({
    deferred_jobs: quota?.deferred_jobs ?? [],
    quota_remaining: quota?.quota_remaining ?? 0,
  })
}

/** POST /api/deferred-jobs — Python으로 _run_deferred_uploads() 실행 */
export async function POST() {
  try {
    const child = spawn(
      'python',
      ['-c', 'from src.pipeline import _run_deferred_uploads; _run_deferred_uploads()'],
      {
        cwd: KAS_ROOT,
        detached: true,
        stdio: 'ignore',
        env: { ...process.env, PYTHONPATH: KAS_ROOT },
      },
    )
    child.unref()
    return NextResponse.json({ ok: true, message: '이연 업로드 재시도를 시작했습니다.' })
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 })
  }
}
```

### Task 6b: cost/page.tsx에 deferred jobs 섹션 추가

- [ ] **Step 2: `web/app/cost/page.tsx` 읽기 확인**

```bash
cd web && grep -n "return\|export default\|<Card\|</Card" app/cost/page.tsx | tail -20
```

Expected: 파일 하단 구조 확인

- [ ] **Step 3: `web/app/cost/page.tsx` 하단에 deferred jobs 섹션 추가**

`app/cost/page.tsx` 파일의 기존 import 블록 끝에 다음을 추가:
```typescript
import { useState, useEffect, useTransition } from 'react'  // 이미 있으면 스킵
import { RefreshCw, Loader2, Clock } from 'lucide-react'     // 이미 있으면 개별 추가
```

그리고 파일 맨 끝의 `export default function CostPage()` 내부 `return` 직전에 다음 상태 추가:
```typescript
  const [deferredJobs, setDeferredJobs] = useState<Array<{
    channel_id: string; run_id: string; topic_title?: string
  }>>([])
  const [quotaRemaining, setQuotaRemaining] = useState(10000)
  const [retrying, startRetry] = useTransition()
  const [retryMsg, setRetryMsg] = useState('')

  useEffect(() => {
    fetch('/api/deferred-jobs')
      .then((r) => r.json())
      .then((d) => {
        setDeferredJobs(d.deferred_jobs ?? [])
        setQuotaRemaining(d.quota_remaining ?? 10000)
      })
      .catch(() => {})
  }, [])

  function handleRetry() {
    startRetry(async () => {
      const res = await fetch('/api/deferred-jobs', { method: 'POST' })
      const data = await res.json()
      setRetryMsg(data.message ?? (data.ok ? '시작됨' : '실패'))
    })
  }
```

그리고 `return` 블록의 마지막 `</div>` 바로 앞에 다음 섹션 추가:
```tsx
      {/* 이연된 YouTube 업로드 */}
      {deferredJobs.length > 0 && (
        <Card className={cn(deferredJobs.length > 0 && 'glow-amber')}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-400" />
                이연된 YouTube 업로드
              </CardTitle>
              <CardDescription className="mt-0.5">
                쿼터 초과로 대기 중 · 잔여 쿼터 {quotaRemaining.toLocaleString()} 단위
              </CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRetry}
              disabled={retrying}
              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              {retrying
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
              재시도
            </Button>
          </CardHeader>
          <CardContent>
            {retryMsg && (
              <p className="text-xs text-green-400 mb-3">{retryMsg}</p>
            )}
            <div className="space-y-1.5">
              {deferredJobs.map((job, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.06] text-sm"
                >
                  <span className="font-mono text-xs text-amber-400">{job.channel_id}</span>
                  <span className="flex-1 mx-3 truncate text-muted-foreground text-xs">
                    {job.topic_title ?? job.run_id}
                  </span>
                  <Badge variant="outline" className="text-xs border-amber-500/30 text-amber-400">
                    대기
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
```

**주의**: `cost/page.tsx`가 `'use client'`이므로 `useState`, `useTransition`은 이미 사용 가능하다. `cn` 유틸은 `@/lib/utils`에서 import.

- [ ] **Step 4: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep -E "deferred|cost/"
```

Expected: 출력 없음

- [ ] **Step 5: 커밋**

```bash
cd web && git add app/api/deferred-jobs/ app/cost/page.tsx
git commit -m "feat: deferred_jobs 재시도 API 및 비용 페이지 섹션 추가"
```

---

## Task 7: 파이프라인 트리거 API route + 채널 상세 UI

**Files:**
- Create: `web/app/api/pipeline/trigger/route.ts`
- Modify: `web/app/channels/[id]/page.tsx`

### Task 7a: 파이프라인 트리거 API route

- [ ] **Step 1: `web/app/api/pipeline/trigger/route.ts` 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

const KAS_ROOT = process.env.KAS_ROOT_DIR ?? path.resolve(process.cwd(), '..')

/**
 * POST /api/pipeline/trigger
 * body: { month_number: number; channel_id?: string }
 *
 * Python 파이프라인을 백그라운드 서브프로세스로 실행한다.
 * 즉시 202 Accepted 반환 — 완료를 기다리지 않는다.
 */
export async function POST(req: NextRequest) {
  const body = (await req.json()) as { month_number: number; channel_id?: string }
  const monthNumber = Number(body.month_number)

  if (!Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) {
    return NextResponse.json(
      { ok: false, error: 'month_number는 1~12 사이 정수여야 합니다.' },
      { status: 400 },
    )
  }

  try {
    // Windows: python -m src.pipeline {month_number}
    // PYTHONPATH를 KAS_ROOT로 설정해 src 패키지를 찾을 수 있게 한다
    const child = spawn('python', ['-m', 'src.pipeline', String(monthNumber)], {
      cwd: KAS_ROOT,
      detached: true,
      stdio: 'ignore',
      env: {
        ...process.env,
        PYTHONPATH: KAS_ROOT,
        KAS_ROOT: KAS_ROOT,
      },
    })
    child.unref() // 부모 프로세스가 종료돼도 자식은 계속 실행

    return NextResponse.json(
      {
        ok: true,
        message: `파이프라인 month=${monthNumber} 시작됨 (백그라운드 실행)`,
        pid: child.pid,
        started_at: new Date().toISOString(),
      },
      { status: 202 },
    )
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 })
  }
}
```

### Task 7b: 채널 상세 페이지에 트리거 카드 추가

- [ ] **Step 2: `web/app/channels/[id]/page.tsx` 수정**

`web/app/channels/[id]/page.tsx`에서:

**import 추가** (기존 import 블록에):
```typescript
import { Play, Loader2 } from 'lucide-react'
// useState, useEffect, useTransition 은 이미 있음
```

**컴포넌트 내부 상태 추가** (`const [kpiHistory, setKpiHistory] = useState` 다음에):
```typescript
  const [monthInput, setMonthInput] = useState(1)
  const [triggerMsg, setTriggerMsg] = useState('')
  const [isTriggerPending, startTrigger] = useTransition()
```

**handleTrigger 함수 추가** (`useEffect` 블록 아래에):
```typescript
  function handleTrigger() {
    startTrigger(async () => {
      const res = await fetch('/api/pipeline/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ month_number: monthInput, channel_id: channelId }),
      })
      const data = await res.json()
      setTriggerMsg(data.message ?? (data.ok ? '시작됨' : data.error ?? '실패'))
    })
  }
```

**파이프라인 트리거 카드 추가** (파이프라인 실행 이력 Card 바로 뒤, 닫는 `</div>` 바로 앞에):
```tsx
      {/* 파이프라인 트리거 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Play className="h-4 w-4 text-green-400" />
            파이프라인 실행
          </CardTitle>
          <CardDescription>
            월간 파이프라인을 백그라운드로 시작합니다. 완료까지 수분~수시간 소요될 수 있습니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="month-input" className="text-sm text-muted-foreground whitespace-nowrap">
                월 번호
              </label>
              <input
                id="month-input"
                type="number"
                min={1}
                max={12}
                value={monthInput}
                onChange={(e) => setMonthInput(Number(e.target.value))}
                className="w-16 rounded-md border border-input bg-background px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <Button
              onClick={handleTrigger}
              disabled={isTriggerPending}
              className="bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
            >
              {isTriggerPending
                ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                : <Play className="h-3.5 w-3.5 mr-1.5" />}
              실행
            </Button>
          </div>
          {triggerMsg && (
            <p className="mt-2 text-xs text-green-400">{triggerMsg}</p>
          )}
        </CardContent>
      </Card>
```

- [ ] **Step 3: TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1 | grep -E "trigger|channels/"
```

Expected: 출력 없음

- [ ] **Step 4: 커밋**

```bash
cd web && git add app/api/pipeline/ app/channels/
git commit -m "feat: 파이프라인 트리거 API route 및 채널 상세 트리거 UI 추가"
```

---

## Task 8: 사이드바 QA 메뉴 추가 + 최종 빌드 검증

**Files:**
- Modify: `web/components/sidebar-nav.tsx`

### Task 8a: 사이드바 수정

- [ ] **Step 1: `web/components/sidebar-nav.tsx` 읽기**

```bash
cd web && grep -n "navItems\|ClipboardCheck\|lucide" components/sidebar-nav.tsx | head -20
```

Expected: navItems 배열과 현재 아이콘 import 확인

- [ ] **Step 2: `web/components/sidebar-nav.tsx` 수정**

**import에 `ClipboardCheck` 추가** (기존 lucide-react import 라인에 추가):
```typescript
import { ..., ClipboardCheck } from 'lucide-react'
```

**navItems 배열에 QA 항목 추가** (`{ title: '비용/쿼터', ... }` 바로 앞에 삽입):
```typescript
  { title: 'QA 검수', url: '/qa', icon: ClipboardCheck },
```

즉, navItems는 다음과 같이 된다:
```typescript
const navItems = [
  { title: '전체 KPI',       url: '/',        icon: LayoutDashboard },
  { title: '트렌드 관리',    url: '/trends',   icon: TrendingUp },
  { title: '수익 추적',      url: '/revenue',  icon: DollarSign },
  { title: '리스크 모니터링', url: '/risk',    icon: ShieldAlert },
  { title: '학습 피드백',    url: '/learning', icon: Brain },
  { title: 'QA 검수',        url: '/qa',       icon: ClipboardCheck },
  { title: '비용/쿼터',      url: '/cost',     icon: CreditCard },
]
```

### Task 8b: 최종 빌드 검증

- [ ] **Step 3: 전체 TypeScript 타입 검사**

```bash
cd web && npx tsc --noEmit 2>&1
```

Expected: 에러 없음 (기존 에러만 허용)

- [ ] **Step 4: Next.js 빌드 검사**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` 또는 `Route (app)` 테이블 출력

- [ ] **Step 5: 커밋**

```bash
cd web && git add components/sidebar-nav.tsx
git commit -m "feat: 사이드바 QA 검수 메뉴 추가"
```

---

## 최종 확인 체크리스트

구현 완료 후 localhost:3002에서 수동 확인:

- [ ] `/` — HITL 배너: 신호가 없으면 배너 미표시, hitl_signals.json 있으면 빨간 배너 표시
- [ ] `/qa` — QA 검수 페이지 접근 가능, "검수 대기 항목 없음" 카드 표시
- [ ] `/qa` — `runs/CH1/test_run_001/step11/qa_result.json`의 human_review.completed 를 false로 변경 후 페이지 새로고침하면 검수 카드 표시
- [ ] `/cost` — deferred_jobs가 비어있으면 섹션 미표시
- [ ] `/channels/CH1` — 파이프라인 트리거 카드 표시, 월 번호 입력 가능
- [ ] 사이드바 — "QA 검수" 항목 표시

---

## Self-Review

**1. Spec 커버리지**
- Step11 QA 검수 UI → Task 4 (QaCard + approveHumanReview) ✅
- HITL 신호 배너 → Task 2 + Task 3 ✅
- Step10 배리언트 선택 → Task 4 (VariantCard + selectTitleVariant/selectThumbnailVariant) ✅
- deferred_jobs 재시도 → Task 6 ✅
- 파이프라인 트리거 → Task 7 ✅

**2. Placeholder 없음**: 모든 코드 블록에 완전한 구현 포함 ✅

**3. 타입 일관성**
- `HitlSignal`, `QaResult`, `QaPendingRun`, `VariantManifest`, `DeferredJob`, `YoutubeQuotaFile` — `fs-helpers.ts`에서 정의, 모든 task에서 import해 사용 ✅
- `approveHumanReview(channelId, runId, reviewer?)` — Task 4a와 Task 4b 모두 동일 시그니처 ✅
- `/api/qa-data?type=pending` — QaPendingRun[] 반환, page.tsx에서 동일 타입으로 수신 ✅
