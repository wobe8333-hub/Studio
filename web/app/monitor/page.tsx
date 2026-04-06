'use client'

import { useState, useEffect, useRef, useTransition, useCallback } from 'react'
import Link from 'next/link'
import {
  Activity, CheckCircle2,
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

function RunRow({ run, compact = false }: { run: ManifestSummary; compact?: boolean }) {
  return (
    <Link href={`/runs/${run.channel_id}/${run.run_id}`} className="block hover:opacity-80 transition-opacity">
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
    </Link>
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
    const id = setInterval(load, 10_000)
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

// ─── Log Viewer Panel ─────────────────────────────────────────────────────────

function LogPanel() {
  const [lines, setLines] = useState<string[]>([])
  const [totalLines, setTotalLines] = useState(0)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

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

  useEffect(() => {
    if (autoRefresh && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [lines, autoRefresh])

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
          <div ref={containerRef} className="rounded-lg bg-black/40 border border-white/[0.06] p-3 font-mono text-xs leading-5 h-80 overflow-y-auto">
            {lines.map((line, i) => (
              <div key={i} className={lineColor(line)}>
                {line}
              </div>
            ))}
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
