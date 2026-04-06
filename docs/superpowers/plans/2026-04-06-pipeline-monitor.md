# 파이프라인 완전 테스트 (Monitor) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹 대시보드에서 파이프라인 사전 검증(Preflight)·실행 상태(Status)·실시간 로그(Logs) 3종을 제공하는 `/monitor` 페이지를 구현해 CLI 없이 전체 파이프라인을 테스트할 수 있도록 한다.

**Architecture:** Next.js API routes 3개(`/api/pipeline/preflight`, `/api/pipeline/status`, `/api/pipeline/logs`)가 KAS 로컬 파일시스템(manifest.json, pipeline.log)과 Python 서브프로세스를 읽어 JSON으로 반환하고, 클라이언트 컴포넌트 `/monitor/page.tsx`가 3개 패널(Preflight·Status·Log Viewer)을 보여준다. 로그는 SSE 대신 3초 폴링으로 구현한다.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 · shadcn/ui · glassmorphism dark · Node.js `child_process.spawnSync` (preflight) · Node.js `fs/promises` · `web/lib/fs-helpers.ts` (기존 getKasRoot)

---

## 파일 구조

**신규 파일:**
| 파일 | 역할 |
|------|------|
| `web/app/api/pipeline/preflight/route.ts` | POST: preflight_check.py 동기 실행, { exit_code, stdout, all_passed, failures } 반환 |
| `web/app/api/pipeline/status/route.ts` | GET: runs/*/manifest.json 스캔, { running, recent, initialized } 반환 |
| `web/app/api/pipeline/logs/route.ts` | GET ?lines=N: pipeline.log 마지막 N줄 반환 |
| `web/app/monitor/page.tsx` | 파이프라인 모니터 페이지 (Preflight + Status + Log Viewer 3패널) |

**수정 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `web/components/sidebar-nav.tsx` | "파이프라인 모니터" 메뉴 항목 추가 |

---

## 컨텍스트 (서브에이전트용)

### 프로젝트 경로
- KAS 루트: `C:\Users\조찬우\Desktop\ai_stuidio_claude` (env: `KAS_ROOT_DIR`, fallback: `path.resolve(process.cwd(), '..')`)
- 웹 루트: `C:\Users\조찬우\Desktop\ai_stuidio_claude\web`
- `getKasRoot()` 함수: `web/lib/fs-helpers.ts`에서 import

### 핵심 데이터 경로
- preflight 스크립트: `{KAS_ROOT}/scripts/preflight_check.py`
- 로그 파일: `{KAS_ROOT}/logs/pipeline.log`
- 초기화 플래그: `{KAS_ROOT}/data/global/.initialized`
- Run manifest: `{KAS_ROOT}/runs/{channelId}/{runId}/manifest.json`

### preflight_check.py 출력 형식
```
[1] 필수 환경 변수
✅ GEMINI_API_KEY  (설정됨)
❌ YOUTUBE_API_KEY  (미설정)
⚠️  ELEVENLABS_API_KEY  (미설정 — 폴백 동작)
...
[2] 채널 데이터 파일
✅ CH1 정책 파일  (dir=True algo=True rev=True style=True)
...
============================================================
❌ 2개 항목 실패:
   ❌ YOUTUBE_API_KEY  (미설정)
   ...
```
- exit code 0 = 모든 체크 통과, exit code 1 = 실패 있음
- `✅` / `❌` / `⚠️` 접두사로 각 라인 판별

### manifest.json 스키마
```json
{
  "run_id": "run_CH1_1775143500",
  "channel_id": "CH1",
  "run_state": "RUNNING",
  "created_at": "2026-04-02T15:25:00Z",
  "topic": {
    "reinterpreted_title": "주식지표 PER 완벽이해...",
    "category": "economy",
    "score": 52.5
  }
}
```
- `run_state`: `"RUNNING"` | `"COMPLETED"` | `"FAILED"` | `"PENDING"`

### 기존 코드 패턴
- `fs-helpers.ts`: `getKasRoot()`, `readKasJson<T>()` 사용
- API route 패턴: `web/app/api/pipeline/trigger/route.ts` 참조
- glassmorphism 클래스: `glass-card`, `glow-amber`, `glow-success`, `glow-danger`, `ambient-bg`
- shadcn 컴포넌트: `Card`, `CardContent`, `CardHeader`, `CardTitle`, `CardDescription`, `Badge`, `Button`
- Tailwind 다크모드: globals.css CSS-first, `.dark .glass-card` 셀렉터

---

## Task 1: Preflight API route

**Files:**
- Create: `web/app/api/pipeline/preflight/route.ts`

- [ ] **Step 1: `web/app/api/pipeline/preflight/route.ts` 작성**

```typescript
import { NextResponse } from 'next/server'
import { spawnSync } from 'child_process'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface PreflightResult {
  exit_code: number
  all_passed: boolean
  stdout: string
  failures: string[]
  duration_ms: number
}

/**
 * POST /api/pipeline/preflight
 * scripts/preflight_check.py를 동기 실행해 환경 검증 결과를 반환한다.
 * Gemini API 호출 포함으로 최대 30초 소요될 수 있다.
 */
export async function POST() {
  const kasRoot = getKasRoot()
  const scriptPath = path.join(kasRoot, 'scripts', 'preflight_check.py')
  const start = Date.now()

  const result = spawnSync('python', [scriptPath], {
    cwd: kasRoot,
    env: { ...process.env, PYTHONPATH: kasRoot, KAS_ROOT: kasRoot },
    encoding: 'utf-8',
    timeout: 60_000, // 60초 타임아웃 (Gemini API 포함)
  })

  const duration_ms = Date.now() - start
  const stdout = (result.stdout ?? '') + (result.stderr ?? '')
  const exit_code = result.status ?? 1

  // ❌ 접두사 라인만 failures로 추출
  const failures = stdout
    .split('\n')
    .filter((line) => line.includes('❌'))
    .map((line) => line.trim())

  const response: PreflightResult = {
    exit_code,
    all_passed: exit_code === 0,
    stdout,
    failures,
    duration_ms,
  }

  return NextResponse.json(response)
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep preflight
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && git add app/api/pipeline/preflight/ && git commit -m "feat: 파이프라인 preflight API route 추가"
```

---

## Task 2: Pipeline Status API route

**Files:**
- Create: `web/app/api/pipeline/status/route.ts`

- [ ] **Step 1: `web/app/api/pipeline/status/route.ts` 작성**

```typescript
import { NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface ManifestSummary {
  run_id: string
  channel_id: string
  run_state: string
  created_at: string
  topic_title: string
  topic_score: number
}

export interface PipelineStatusResult {
  initialized: boolean
  running: ManifestSummary[]
  recent: ManifestSummary[]   // 최근 20개, 생성시간 내림차순
  total_runs: number
}

async function readManifest(filePath: string): Promise<ManifestSummary | null> {
  try {
    const text = await fs.readFile(filePath, 'utf-8')
    const m = JSON.parse(text)
    return {
      run_id:      m.run_id      ?? '',
      channel_id:  m.channel_id  ?? '',
      run_state:   m.run_state   ?? 'UNKNOWN',
      created_at:  m.created_at  ?? '',
      topic_title: m.topic?.reinterpreted_title ?? m.topic?.original_trend?.topic ?? '—',
      topic_score: m.topic?.score ?? 0,
    }
  } catch {
    return null
  }
}

/**
 * GET /api/pipeline/status
 * runs/*/manifest.json 전체 스캔 + .initialized 플래그 확인
 */
export async function GET() {
  const kasRoot = getKasRoot()
  const runsDir = path.join(kasRoot, 'runs')
  const initializedFlag = path.join(kasRoot, 'data', 'global', '.initialized')

  // .initialized 플래그 확인
  let initialized = false
  try {
    await fs.access(initializedFlag)
    initialized = true
  } catch { /* 미초기화 */ }

  // manifest.json 스캔
  const all: ManifestSummary[] = []
  try {
    const channels = await fs.readdir(runsDir)
    for (const channelId of channels) {
      const channelDir = path.join(runsDir, channelId)
      try {
        const stat = await fs.stat(channelDir)
        if (!stat.isDirectory()) continue
      } catch { continue }

      const runDirs = await fs.readdir(channelDir)
      for (const runId of runDirs) {
        const manifestPath = path.join(channelDir, runId, 'manifest.json')
        const summary = await readManifest(manifestPath)
        if (summary) all.push(summary)
      }
    }
  } catch { /* runs/ 없음 */ }

  // 생성시간 내림차순 정렬
  all.sort((a, b) => (b.created_at > a.created_at ? 1 : -1))

  const running = all.filter((r) => r.run_state === 'RUNNING')
  const recent  = all.slice(0, 20)

  const result: PipelineStatusResult = {
    initialized,
    running,
    recent,
    total_runs: all.length,
  }

  return NextResponse.json(result)
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep "pipeline/status"
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && git add app/api/pipeline/status/ && git commit -m "feat: 파이프라인 status API route 추가 (manifest.json 스캔)"
```

---

## Task 3: Pipeline Logs API route

**Files:**
- Create: `web/app/api/pipeline/logs/route.ts`

- [ ] **Step 1: `web/app/api/pipeline/logs/route.ts` 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

/**
 * GET /api/pipeline/logs?lines=N
 * logs/pipeline.log의 마지막 N줄을 반환한다. 기본 100줄.
 * 파일이 없으면 빈 배열 반환.
 */
export async function GET(req: NextRequest) {
  const linesParam = req.nextUrl.searchParams.get('lines')
  const n = Math.min(Math.max(parseInt(linesParam ?? '100', 10) || 100, 1), 500)

  const logPath = path.join(getKasRoot(), 'logs', 'pipeline.log')

  try {
    const text = await fs.readFile(logPath, 'utf-8')
    const lines = text.split('\n').filter(Boolean) // 빈 줄 제거
    const tail = lines.slice(-n)
    return NextResponse.json({
      lines: tail,
      total_lines: lines.length,
      log_path: 'logs/pipeline.log',
    })
  } catch {
    return NextResponse.json({
      lines: [],
      total_lines: 0,
      log_path: 'logs/pipeline.log',
    })
  }
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep "pipeline/logs"
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && git add app/api/pipeline/logs/ && git commit -m "feat: 파이프라인 로그 API route 추가"
```

---

## Task 4: Pipeline Monitor 페이지

**Files:**
- Create: `web/app/monitor/page.tsx`

이 페이지는 3개 섹션으로 구성된다:
1. **Preflight Check** — POST 버튼, 터미널 스타일 결과 표시
2. **Pipeline Status** — 실행 중 run 카드 + 최근 실행 이력 테이블
3. **Log Viewer** — 마지막 100줄, 3초 자동 새로고침

- [ ] **Step 1: `web/app/monitor/page.tsx` 작성**

```typescript
'use client'

import { useState, useEffect, useRef, useTransition, useCallback } from 'react'
import {
  Activity, CheckCircle2, XCircle, AlertTriangle,
  RefreshCw, Play, Loader2, Terminal, Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { PreflightResult } from '@/app/api/pipeline/preflight/route'
import type { PipelineStatusResult, ManifestSummary } from '@/app/api/pipeline/status/route'

// ─── Preflight Panel ─────────────────────────────────────────────────────────

function PreflightPanel() {
  const [result, setResult] = useState<PreflightResult | null>(null)
  const [isPending, startTransition] = useTransition()

  function runPreflight() {
    startTransition(async () => {
      const res = await fetch('/api/pipeline/preflight', { method: 'POST' })
      const data: PreflightResult = await res.json()
      setResult(data)
    })
  }

  // stdout 라인에 색상 클래스 적용
  function colorLine(line: string): string {
    if (line.includes('✅')) return 'text-green-400'
    if (line.includes('❌')) return 'text-red-400'
    if (line.includes('⚠')) return 'text-amber-400'
    if (line.startsWith('[')) return 'text-blue-400 font-semibold mt-2'
    if (line.startsWith('===')) return 'text-white/40'
    return 'text-white/70'
  }

  return (
    <Card className="glass-card">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-400" />
            Preflight 체크
          </CardTitle>
          <CardDescription>실행 전 환경 검증 (API 키·OAuth 토큰·FFmpeg 등 6항목)</CardDescription>
        </div>
        <Button
          size="sm"
          onClick={runPreflight}
          disabled={isPending}
          className="bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 transition-colors shrink-0"
        >
          {isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Play className="h-3.5 w-3.5 mr-1.5" />}
          {isPending ? '실행 중...' : '검사 실행'}
        </Button>
      </CardHeader>
      <CardContent>
        {!result && !isPending && (
          <p className="text-sm text-muted-foreground text-center py-6">
            "검사 실행" 버튼을 눌러 환경을 점검하세요. (Gemini API 호출 포함, 최대 60초)
          </p>
        )}
        {isPending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
            <Loader2 className="h-4 w-4 animate-spin" />
            preflight_check.py 실행 중...
          </div>
        )}
        {result && (
          <div className="space-y-3">
            {/* 요약 배지 */}
            <div className="flex items-center gap-3">
              <Badge
                className={cn(
                  'text-sm px-3 py-1',
                  result.all_passed
                    ? 'bg-green-500/15 border border-green-500/30 text-green-400'
                    : 'bg-red-500/15 border border-red-500/30 text-red-400',
                )}
              >
                {result.all_passed ? '✅ 모든 체크 통과' : `❌ ${result.failures.length}개 실패`}
              </Badge>
              <span className="text-xs text-muted-foreground">{result.duration_ms}ms</span>
            </div>

            {/* 터미널 출력 */}
            <div className="rounded-lg bg-black/40 border border-white/[0.06] p-3 font-mono text-xs leading-5 max-h-72 overflow-y-auto">
              {result.stdout.split('\n').map((line, i) => (
                <div key={i} className={colorLine(line)}>
                  {line || '\u00A0'}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Status Panel ─────────────────────────────────────────────────────────────

const STATE_BADGE: Record<string, { label: string; className: string }> = {
  RUNNING:   { label: '실행중',  className: 'bg-blue-500/15 border-blue-500/30 text-blue-400' },
  COMPLETED: { label: '완료',    className: 'bg-green-500/15 border-green-500/30 text-green-400' },
  FAILED:    { label: '실패',    className: 'bg-red-500/15 border-red-500/30 text-red-400' },
  PENDING:   { label: '대기',    className: 'bg-amber-500/15 border-amber-500/30 text-amber-400' },
}

function RunBadge({ state }: { state: string }) {
  const s = STATE_BADGE[state] ?? { label: state, className: 'border-white/20 text-white/60' }
  return (
    <Badge className={cn('border text-xs', s.className)}>{s.label}</Badge>
  )
}

function StatusPanel() {
  const [status, setStatus] = useState<PipelineStatusResult | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/pipeline/status')
      setStatus(await res.json())
    } catch { /* 무시 */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 10_000) // 10초마다 갱신
    return () => clearInterval(id)
  }, [load])

  return (
    <Card className={cn('glass-card', status?.running.length ? 'glow-amber' : '')}>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-amber-400" />
            파이프라인 상태
          </CardTitle>
          <CardDescription>
            {status
              ? `총 ${status.total_runs}개 run · 초기화: ${status.initialized ? '완료' : '미완료'}`
              : '로딩 중...'}
          </CardDescription>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={load}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 실행 중 runs */}
        {status && (
          <>
            <div>
              <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">
                실행 중 ({status.running.length})
              </p>
              {status.running.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-3">실행 중인 파이프라인 없음</p>
              ) : (
                <div className="space-y-2">
                  {status.running.map((run) => (
                    <RunRow key={run.run_id} run={run} />
                  ))}
                </div>
              )}
            </div>

            {/* 최근 실행 이력 */}
            <div>
              <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">
                최근 실행 이력 (최대 20개)
              </p>
              <div className="space-y-1">
                {status.recent.map((run) => (
                  <RunRow key={run.run_id} run={run} compact />
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function RunRow({ run, compact = false }: { run: ManifestSummary; compact?: boolean }) {
  return (
    <div className={cn(
      'flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02]',
      compact ? 'px-3 py-1.5' : 'px-3 py-2.5',
    )}>
      <span className="font-mono text-xs text-amber-400 shrink-0 w-8">{run.channel_id}</span>
      <span className="flex-1 text-xs text-muted-foreground truncate">{run.topic_title}</span>
      {!compact && (
        <span className="text-xs text-muted-foreground shrink-0">
          {run.created_at?.slice(0, 10)}
        </span>
      )}
      <RunBadge state={run.run_state} />
    </div>
  )
}

// ─── Log Viewer Panel ─────────────────────────────────────────────────────────

function LogPanel() {
  const [lines, setLines] = useState<string[]>([])
  const [totalLines, setTotalLines] = useState(0)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/pipeline/logs?lines=100')
      const data: { lines: string[]; total_lines: number } = await res.json()
      setLines(data.lines)
      setTotalLines(data.total_lines)
    } catch { /* 무시 */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(fetchLogs, 3_000)
    return () => clearInterval(id)
  }, [autoRefresh, fetchLogs])

  // 새 로그 도착 시 자동 스크롤
  useEffect(() => {
    if (autoRefresh) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines, autoRefresh])

  // 로그 라인 색상
  function lineColor(line: string): string {
    if (line.includes('ERROR') || line.includes('❌')) return 'text-red-400'
    if (line.includes('WARNING') || line.includes('⚠')) return 'text-amber-400'
    if (line.includes('✅') || line.includes('COMPLETED')) return 'text-green-400'
    if (line.includes('RUNNING') || line.includes('INFO')) return 'text-white/80'
    return 'text-white/50'
  }

  return (
    <Card className="glass-card">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-green-400" />
            파이프라인 로그
          </CardTitle>
          <CardDescription>
            logs/pipeline.log 마지막 100줄 · 전체 {totalLines.toLocaleString()}줄
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
          <Button
            size="sm"
            variant={autoRefresh ? 'default' : 'outline'}
            onClick={() => setAutoRefresh((v) => !v)}
            className={cn(
              'text-xs',
              autoRefresh
                ? 'bg-green-500/15 border border-green-500/30 text-green-400 hover:bg-green-500/20'
                : 'border-white/20 text-muted-foreground',
            )}
          >
            <Clock className="h-3 w-3 mr-1" />
            {autoRefresh ? '자동갱신 ON' : '자동갱신 OFF'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={fetchLogs}
            className="text-muted-foreground"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {lines.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            로그 없음 — 파이프라인을 실행하면 여기에 표시됩니다.
          </p>
        ) : (
          <div className="rounded-lg bg-black/40 border border-white/[0.06] p-3 font-mono text-xs leading-5 h-80 overflow-y-auto">
            {lines.map((line, i) => (
              <div key={i} className={lineColor(line)}>
                {line}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Monitor Page ─────────────────────────────────────────────────────────────

export default function MonitorPage() {
  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          <h1 className="text-2xl font-bold tracking-tight">파이프라인 모니터</h1>
        </div>
        <p className="text-muted-foreground text-sm mt-1">
          Preflight 검증 · 실행 상태 · 실시간 로그
        </p>
      </div>

      <PreflightPanel />
      <StatusPanel />
      <LogPanel />
    </div>
  )
}
```

- [ ] **Step 2: TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1 | grep monitor
```

Expected: 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && git add app/monitor/ && git commit -m "feat: 파이프라인 모니터 페이지 추가 (Preflight·Status·Log 3패널)"
```

---

## Task 5: 사이드바 메뉴 추가 + 최종 빌드 검증

**Files:**
- Modify: `web/components/sidebar-nav.tsx`

- [ ] **Step 1: `web/components/sidebar-nav.tsx` 읽기**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && grep -n "navItems\|lucide" components/sidebar-nav.tsx | head -15
```

Expected: 현재 navItems 배열과 lucide import 확인

- [ ] **Step 2: `Monitor` 아이콘 import 추가**

기존 lucide-react import 라인에 `Monitor` 추가:
```typescript
import { ..., Monitor } from 'lucide-react'
```

- [ ] **Step 3: navItems에 파이프라인 모니터 추가**

`{ title: 'QA 검수', ... }` 바로 앞에 삽입:
```typescript
  { title: '파이프라인 모니터', url: '/monitor', icon: Monitor },
```

최종 navItems:
```typescript
const navItems = [
  { title: '전체 KPI',           url: '/',        icon: LayoutDashboard },
  { title: '트렌드 관리',        url: '/trends',   icon: TrendingUp },
  { title: '수익 추적',          url: '/revenue',  icon: DollarSign },
  { title: '리스크 모니터링',    url: '/risk',     icon: ShieldAlert },
  { title: '학습 피드백',        url: '/learning', icon: Brain },
  { title: '파이프라인 모니터',  url: '/monitor',  icon: Monitor },
  { title: 'QA 검수',            url: '/qa',       icon: ClipboardCheck },
  { title: '비용/쿼터',          url: '/cost',     icon: CreditCard },
]
```

- [ ] **Step 4: 전체 TypeScript 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npx tsc --noEmit 2>&1
```

Expected: 0 errors

- [ ] **Step 5: Next.js 빌드 검사**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && npm run build 2>&1 | tail -25
```

Expected: 성공 빌드, `/monitor` 라우트 포함, `/api/pipeline/preflight`, `/api/pipeline/status`, `/api/pipeline/logs` 라우트 포함

- [ ] **Step 6: 커밋**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude\web && git add components/sidebar-nav.tsx && git commit -m "feat: 사이드바 파이프라인 모니터 메뉴 추가"
```

---

## Self-Review

**1. Spec 커버리지**
- `/api/pipeline/preflight` → Task 1 ✅
- `/api/pipeline/status` → Task 2 ✅
- `/api/pipeline/logs` → Task 3 ✅
- Preflight 패널 (버튼 + 터미널 결과) → Task 4 PreflightPanel ✅
- Status 패널 (실행 중 + 최근 이력) → Task 4 StatusPanel ✅
- Log Viewer (자동 새로고침 + 스크롤) → Task 4 LogPanel ✅
- 사이드바 메뉴 → Task 5 ✅

**2. Placeholder 없음**: 모든 코드 완전 구현 ✅

**3. 타입 일관성**
- `PreflightResult` — Task 1에서 export, Task 4에서 `import type` ✅
- `PipelineStatusResult`, `ManifestSummary` — Task 2에서 export, Task 4에서 `import type` ✅
- `readManifest()` 반환 타입 `ManifestSummary | null` — Task 2 내부 일관 ✅
