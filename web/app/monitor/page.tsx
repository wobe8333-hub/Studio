'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  Activity, CheckCircle2, AlertTriangle, Bot,
  RefreshCw, Play, Loader2, Terminal, Clock,
  Image as ImageIcon, Cpu, Shield, ClipboardCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import VerificationBoard from '@/components/verification-board'

// ─── 탭 정의 ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'preflight', label: '사전 점검',       icon: ClipboardCheck },
  { id: 'steps',    label: 'Step 진행',       icon: Activity },
  { id: 'preview',  label: '실시간 미리보기', icon: ImageIcon },
  { id: 'manim',    label: 'Manim 안정성',    icon: Cpu },
  { id: 'hitl',     label: 'HITL 신호',       icon: Shield },
  { id: 'subagent', label: 'Sub-Agent',       icon: Bot },
] as const

type TabId = typeof TABS[number]['id']

// ─── 공통 스타일 ──────────────────────────────────────────────────────────────

const G = {
  card: {
    background: 'var(--card)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid var(--border)',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
  } as React.CSSProperties,
  text: { primary: '#1a0505', secondary: '#5c1a1a', muted: '#9b6060' },
}

// ─── 사전 점검 탭 ────────────────────────────────────────────────────────────

interface PreflightResult {
  exit_code: number
  all_passed: boolean
  stdout: string
  failures: string[]
  duration_ms: number
  python_version?: string
  python_error?: string
}

// stdout 라인을 파싱해 ✅/❌/⚠️ 항목별로 분류
function parsePreflightLines(stdout: string) {
  return stdout
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.startsWith('✅') || l.startsWith('❌') || l.startsWith('⚠️') || l.startsWith('=='))
}

function PreflightPanel() {
  const [result, setResult] = useState<PreflightResult | null>(null)
  const [running, setRunning] = useState(false)

  const run = async () => {
    setRunning(true)
    setResult(null)
    try {
      const res = await fetch('/api/pipeline/preflight', { method: 'POST' })
      if (res.ok) setResult(await res.json())
    } finally {
      setRunning(false)
    }
  }

  const lines = result ? parsePreflightLines(result.stdout) : []
  const checkLines = lines.filter(l => l.startsWith('✅') || l.startsWith('❌') || l.startsWith('⚠️'))

  return (
    <div className="space-y-4">
      {/* 헤더 카드 */}
      <div style={G.card} className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ClipboardCheck className="h-5 w-5 shrink-0" style={{ color: '#ee2400' }} />
            <div>
              <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
                사전 점검 (Preflight Check)
              </h3>
              <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>
                API 키 · 채널 파일 · 모듈 import · Gemini 연결 · OAuth 토큰 · FFmpeg 총 6항목 검증
              </p>
              <p className="text-[10px] mt-1" style={{ color: '#b06060' }}>
                Gemini API 실제 호출로 인해 최대 60초 소요될 수 있습니다
              </p>
            </div>
          </div>
          <button
            onClick={run}
            disabled={running}
            className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
            style={{ background: '#900000', color: '#ffefea', border: 'none' }}
          >
            {running
              ? <><Loader2 className="h-4 w-4 animate-spin" />검증 중...</>
              : <><Play className="h-4 w-4" />검증 실행</>
            }
          </button>
        </div>

        {/* 실행 중 안내 */}
        {running && (
          <div className="mt-4 rounded-lg p-3 flex items-center gap-3"
            style={{ background: 'rgba(238,36,0,0.05)', border: '1px solid rgba(238,36,0,0.12)' }}>
            <Loader2 className="h-4 w-4 animate-spin shrink-0" style={{ color: '#ee2400' }} />
            <div>
              <p className="text-sm font-medium" style={{ color: '#1a0505' }}>Gemini API 연결 테스트 중...</p>
              <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>완료까지 최대 60초 기다려 주세요</p>
            </div>
          </div>
        )}
      </div>

      {/* 결과 카드 */}
      {result && (
        <>
          {/* Python 버전 표시 */}
          {result.python_version && (
            <div className="flex items-center gap-2 px-1">
              <span className="text-[11px]" style={{ color: '#9b6060' }}>Python:</span>
              <span className="text-[11px] font-mono" style={{ color: '#22c55e' }}>{result.python_version}</span>
            </div>
          )}

          {/* Python 크래시 (stdout 없음 + 비정상 종료) */}
          {result.python_error && (
            <div className="rounded-xl p-4" style={{ background: 'rgba(180,0,0,0.08)', border: '1px solid rgba(180,0,0,0.25)' }}>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 shrink-0" style={{ color: '#dc2626' }} />
                <p className="font-bold" style={{ color: '#dc2626' }}>Python 프로세스 크래시</p>
              </div>
              <p className="text-sm mb-2" style={{ color: '#5c1a1a' }}>{result.python_error}</p>
              <div className="rounded-lg p-3 mt-2" style={{ background: 'rgba(0,0,0,0.04)' }}>
                <p className="text-xs font-semibold mb-2" style={{ color: '#9b6060' }}>해결 방법 (순서대로 시도)</p>
                <ol className="space-y-1 text-xs" style={{ color: '#5c1a1a' }}>
                  <li className="flex gap-2"><span style={{ color: '#900000' }}>1.</span>
                    <code style={{ fontFamily: 'monospace' }}>pip install -r requirements.txt</code>
                  </li>
                  <li className="flex gap-2"><span style={{ color: '#900000' }}>2.</span>
                    <span>Visual C++ 재배포 패키지 설치 (Microsoft 공식 사이트)</span>
                  </li>
                  <li className="flex gap-2"><span style={{ color: '#900000' }}>3.</span>
                    <span>웹 서버를 Python 가상환경 활성화 후 재시작</span>
                  </li>
                  <li className="flex gap-2"><span style={{ color: '#900000' }}>4.</span>
                    <code style={{ fontFamily: 'monospace' }}>python --version</code> 터미널에서 직접 확인
                  </li>
                </ol>
              </div>
            </div>
          )}

          {/* 종합 결과 배너 (정상 실행된 경우만) */}
          {!result.python_error && (
            <div className="rounded-xl p-4 flex items-center gap-3" style={{
              background: result.all_passed ? 'rgba(34,197,94,0.08)' : 'rgba(238,36,0,0.08)',
              border: `1px solid ${result.all_passed ? 'rgba(34,197,94,0.25)' : 'rgba(238,36,0,0.25)'}`,
            }}>
              {result.all_passed
                ? <CheckCircle2 className="h-6 w-6 shrink-0" style={{ color: '#22c55e' }} />
                : <AlertTriangle className="h-6 w-6 shrink-0" style={{ color: '#ee2400' }} />
              }
              <div className="flex-1">
                <p className="font-bold" style={{ color: result.all_passed ? '#15803d' : '#dc2626' }}>
                  {result.all_passed
                    ? '모든 항목 통과 — 파이프라인 실행 가능'
                    : `${result.failures.length}개 항목 실패 — 해결 후 재실행 필요`}
                </p>
                <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>
                  소요 시간: {(result.duration_ms / 1000).toFixed(1)}s · exit code: {result.exit_code}
                </p>
              </div>
            </div>
          )}

          {/* 항목별 결과 */}
          {checkLines.length > 0 && (
          <div style={G.card} className="p-5">
            <p className="text-xs font-bold mb-3 uppercase" style={{ color: '#9b6060', letterSpacing: '0.08em' }}>
              점검 결과 ({checkLines.length}개 항목)
            </p>
            <div className="space-y-2">
              {checkLines.map((line, i) => {
                const isPass = line.startsWith('✅')
                const isWarn = line.startsWith('⚠️')
                const text = line.replace(/^[✅❌⚠️]\s*/, '')
                return (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{
                    background: isPass
                      ? 'rgba(34,197,94,0.05)'
                      : isWarn
                        ? 'rgba(234,179,8,0.06)'
                        : 'rgba(238,36,0,0.06)',
                    border: `1px solid ${isPass ? 'rgba(34,197,94,0.15)' : isWarn ? 'rgba(234,179,8,0.20)' : 'rgba(238,36,0,0.15)'}`,
                  }}>
                    <span className="text-base leading-none mt-0.5 shrink-0">
                      {isPass ? '✅' : isWarn ? '⚠️' : '❌'}
                    </span>
                    <span className="text-sm" style={{
                      color: isPass ? '#15803d' : isWarn ? '#92400e' : '#dc2626',
                    }}>
                      {text}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
          )}

          {/* 실패 항목 해결 가이드 */}
          {result.failures.length > 0 && (
            <div style={G.card} className="p-5">
              <p className="text-xs font-bold mb-3" style={{ color: '#dc2626' }}>
                ❌ 실패 항목 해결 방법
              </p>
              <div className="space-y-2 text-xs" style={{ color: '#5c1a1a' }}>
                {result.failures.some(f => f.includes('GEMINI_API_KEY') || f.includes('YOUTUBE_API_KEY')) && (
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.10)' }}>
                    <p className="font-semibold mb-1">API 키 미설정</p>
                    <code className="text-[11px]" style={{ fontFamily: "'DM Mono', monospace", color: '#900000' }}>
                      .env 파일에 GEMINI_API_KEY / YOUTUBE_API_KEY 추가
                    </code>
                  </div>
                )}
                {result.failures.some(f => f.includes('token') || f.includes('OAuth')) && (
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.10)' }}>
                    <p className="font-semibold mb-1">YouTube OAuth 토큰 없음</p>
                    <code className="text-[11px]" style={{ fontFamily: "'DM Mono', monospace", color: '#900000' }}>
                      python scripts/generate_oauth_token.py --channel CH1
                    </code>
                  </div>
                )}
                {result.failures.some(f => f.includes('ffmpeg') || f.includes('FFmpeg')) && (
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.10)' }}>
                    <p className="font-semibold mb-1">FFmpeg 미설치</p>
                    <code className="text-[11px]" style={{ fontFamily: "'DM Mono', monospace", color: '#900000' }}>
                      winget install ffmpeg  (또는 공식 사이트에서 설치)
                    </code>
                  </div>
                )}
                {result.failures.some(f => f.includes('import') || f.includes('module')) && (
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.10)' }}>
                    <p className="font-semibold mb-1">Python 패키지 누락</p>
                    <code className="text-[11px]" style={{ fontFamily: "'DM Mono', monospace", color: '#900000' }}>
                      pip install -r requirements.txt
                    </code>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 전체 로그 (접을 수 있는 raw 출력) */}
          <details style={G.card} className="p-4">
            <summary className="cursor-pointer text-xs font-semibold select-none" style={{ color: '#9b6060' }}>
              전체 로그 보기 (raw stdout)
            </summary>
            <pre className="mt-3 text-[10px] leading-relaxed whitespace-pre-wrap break-all max-h-60 overflow-y-auto"
              style={{ color: '#5c1a1a', fontFamily: "'DM Mono', monospace" }}>
              {result.stdout || '(출력 없음)'}
            </pre>
          </details>
        </>
      )}

      {/* 결과 없을 때 안내 */}
      {!result && !running && (
        <div style={G.card} className="p-8 text-center">
          <ClipboardCheck className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.25)' }} />
          <p className="text-sm" style={{ color: '#9b6060' }}>
            "검증 실행" 버튼을 눌러 파이프라인 실행 전 환경을 점검하세요
          </p>
        </div>
      )}
    </div>
  )
}

// ─── Step 진행 탭 ─────────────────────────────────────────────────────────────

interface StepItem {
  index: number
  name: string
  status: 'pending' | 'running' | 'done' | 'failed'
  started_at: string | null
  completed_at: string | null
  elapsed_ms: number | null
}

interface StepProgress {
  active: boolean
  dry_run?: boolean
  channel_id: string | null
  run_id: string | null
  steps: StepItem[]
  updated_at: string | null
}

function StepProgressPanel() {
  const [data, setData] = useState<StepProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [resetting, setResetting] = useState(false)

  const poll = useCallback(async () => {
    try {
      const res = await fetch('/api/pipeline/steps')
      if (res.ok) setData(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [poll])

  const startDryRun = async () => {
    setTriggering(true)
    try {
      const res = await fetch('/api/pipeline/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: true, channel_id: 'CH1', month_number: 1 }),
      })
      if (res.ok) await poll()
    } finally {
      setTriggering(false)
    }
  }

  const resetSteps = async () => {
    setResetting(true)
    try {
      await fetch('/api/pipeline/steps', { method: 'DELETE' })
      await poll()
    } finally {
      setResetting(false)
    }
  }

  const statusColor = (s: string) => {
    if (s === 'done') return '#22c55e'
    if (s === 'running') return '#ee2400'
    if (s === 'failed') return '#ef4444'
    return '#d1d5db'
  }
  const statusLabel = (s: string) => {
    if (s === 'done') return '완료'
    if (s === 'running') return '실행중'
    if (s === 'failed') return '실패'
    return '대기'
  }

  if (loading) return <div className="flex items-center justify-center py-20" style={{ color: '#9b6060' }}><Loader2 className="h-6 w-6 animate-spin" /></div>

  // 실행 이력 없음 (파일 없거나 steps 비어있음) → 대기 화면
  const hasSteps = (data?.steps?.length ?? 0) > 0
  if (!data || !hasSteps) {
    return (
      <div style={G.card} className="p-8 text-center">
        <Activity className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.3)' }} />
        <p className="text-lg font-bold mb-2" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>파이프라인 대기 중</p>
        <p className="text-sm mb-6" style={{ color: '#9b6060' }}>버튼을 눌러 DRY RUN 시뮬레이션을 시작하세요</p>
        <button
          onClick={startDryRun}
          disabled={triggering}
          className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
          style={{ background: '#900000', color: '#ffefea', cursor: triggering ? 'not-allowed' : 'pointer' }}
        >
          {triggering ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {triggering ? '시작 중...' : '테스트 런 시작'}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div style={G.card} className="px-5 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            {data.active
              ? <span className="h-2 w-2 rounded-full bg-[#ee2400] animate-pulse" />
              : <span className="h-2 w-2 rounded-full" style={{ background: '#22c55e' }} />
            }
            <span className="font-bold" style={{ color: '#1a0505' }}>{data.channel_id}</span>
            {data.dry_run && <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(238,36,0,0.12)', color: '#ee2400' }}>DRY RUN</span>}
            {!data.active && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-bold" style={{ background: 'rgba(34,197,94,0.12)', color: '#16a34a' }}>완료됨</span>
            )}
          </div>
          <p className="text-xs mt-0.5" style={{ fontFamily: "'DM Mono', monospace", color: '#9b6060' }}>{data.run_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-right text-xs" style={{ color: '#9b6060' }}>
            {data.updated_at && <p>마지막 업데이트: {new Date(data.updated_at).toLocaleTimeString('ko-KR')}</p>}
            {data.active && <p className="text-[10px] mt-0.5">3초마다 자동 새로고침</p>}
          </div>
          {!data.active && (
            <button
              onClick={resetSteps}
              disabled={resetting}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold disabled:opacity-50"
              style={{ border: '1px solid rgba(180,40,40,0.25)', background: 'transparent', color: '#7a3030', cursor: resetting ? 'not-allowed' : 'pointer' }}
            >
              {resetting ? '초기화 중...' : '초기화'}
            </button>
          )}
          {data.active && (
            <button
              onClick={startDryRun}
              disabled={triggering}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold disabled:opacity-50 inline-flex items-center gap-1"
              style={{ background: '#900000', color: '#ffefea', cursor: triggering ? 'not-allowed' : 'pointer' }}
            >
              {triggering ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              {triggering ? '시작 중...' : '새 런'}
            </button>
          )}
        </div>
      </div>

      {/* Step 리스트 */}
      <div style={G.card} className="p-5">
        <div className="space-y-1">
          {data.steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3 py-3 border-b last:border-0" style={{ borderColor: 'rgba(238,36,0,0.08)' }}>
              <div className="flex-none flex items-center justify-center h-7 w-7 rounded-full text-xs font-bold" style={{ background: `${statusColor(step.status)}20`, color: statusColor(step.status) }}>
                {step.status === 'running' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: '#1a0505' }}>{step.name}</p>
                {step.started_at && (
                  <p className="text-xs" style={{ color: '#9b6060', fontFamily: "'DM Mono', monospace" }}>
                    시작: {new Date(step.started_at).toLocaleTimeString('ko-KR')}
                    {step.elapsed_ms && ` · ${(step.elapsed_ms / 1000).toFixed(1)}s`}
                  </p>
                )}
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: `${statusColor(step.status)}15`, color: statusColor(step.status) }}>
                {statusLabel(step.status)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── 실시간 미리보기 탭 ──────────────────────────────────────────────────────

interface PreviewItem {
  index: number
  heading: string
  narration: string
  prompt: string
  image: string | null
}

interface PreviewData {
  channel: string
  runId: string
  title: string | null
  hook: string | null
  previews: PreviewItem[]
  allImages: string[]
  totalSections: number
}

function PreviewPanel() {
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImg, setSelectedImg] = useState<string | null>(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/pipeline/preview')
        if (res.ok) {
          setPreview(await res.json())
          setError(null)
        } else {
          setError('실행 결과 없음')
        }
      } catch {
        setError('API 오류')
      } finally {
        setLoading(false)
      }
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => clearInterval(id)
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center py-20" style={{ color: '#9b6060' }}>
      <Loader2 className="h-6 w-6 animate-spin" />
    </div>
  )

  if (error || !preview) return (
    <div style={G.card} className="p-8 text-center">
      <ImageIcon className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.3)' }} />
      <p className="text-sm" style={{ color: '#9b6060' }}>완료된 파이프라인 Run이 없습니다</p>
    </div>
  )

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div style={G.card} className="px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold" style={{ color: '#1a0505' }}>
            {preview.channel} · {preview.runId}
          </p>
          {preview.title && (
            <p className="text-xs mt-0.5" style={{ color: '#5c1a1a' }}>
              제목: {preview.title}
            </p>
          )}
          <p className="text-[10px] mt-0.5" style={{ color: '#9b6060' }}>
            섹션 {preview.totalSections}개 · 이미지 {preview.allImages.length}장 · 5초 자동 갱신
          </p>
        </div>
        <Link href={`/runs/${preview.channel}/${preview.runId}`}
          className="kas-btn text-[11px] px-2 py-1 rounded"
          style={{ background: 'rgba(144,0,0,0.08)', color: '#900000' }}>
          상세보기 →
        </Link>
      </div>

      {/* Hook */}
      {preview.hook && (
        <div style={G.card} className="px-4 py-3">
          <p className="text-[10px] font-bold uppercase mb-1" style={{ color: '#9b6060' }}>Hook</p>
          <p className="text-sm leading-relaxed" style={{ color: '#1a0505' }}>{preview.hook}</p>
        </div>
      )}

      {/* 이미지 갤러리 (전체) */}
      {preview.allImages.length > 0 && (
        <div style={G.card} className="p-4">
          <p className="text-xs font-bold mb-3" style={{ color: '#5c1a1a' }}>
            장면 이미지 갤러리
            <span className="ml-2 font-normal" style={{ color: '#9b6060' }}>
              {preview.allImages.length}장 · 클릭하면 확대
            </span>
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {preview.allImages.map((src, i) => (
              <button
                key={src}
                onClick={() => setSelectedImg(src)}
                className="relative rounded-lg overflow-hidden aspect-video block w-full"
                style={{ background: 'rgba(238,36,0,0.06)', border: '1px solid rgba(238,36,0,0.1)', cursor: 'pointer', padding: 0 }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt={`장면 ${i + 1}`}
                  className="w-full h-full object-cover"
                />
                <span className="absolute bottom-1 left-1 text-[9px] font-bold px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(0,0,0,0.55)', color: '#fff' }}>
                  {i + 1}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 이미지 없을 때 안내 */}
      {preview.allImages.length === 0 && (
        <div style={G.card} className="p-6 text-center">
          <ImageIcon className="h-8 w-8 mx-auto mb-2" style={{ color: 'rgba(238,36,0,0.25)' }} />
          <p className="text-xs" style={{ color: '#9b6060' }}>Step08 실행 중 이미지 자동 표시됩니다</p>
        </div>
      )}

      {/* 섹션별 나레이션 */}
      {preview.previews.length > 0 && (
        <div style={G.card} className="p-4">
          <p className="text-xs font-bold mb-3" style={{ color: '#5c1a1a' }}>나레이션 미리보기</p>
          <div className="space-y-3">
            {preview.previews.map((item) => (
              <div key={item.index} className="rounded-lg p-3" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.08)' }}>
                <p className="text-[10px] font-bold mb-1" style={{ color: '#9b6060' }}>
                  섹션 {item.index} · {item.heading}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: '#1a0505' }}>
                  {item.narration || '(나레이션 없음)'}
                </p>
                {item.prompt && (
                  <p className="text-[10px] mt-1 leading-relaxed" style={{ color: '#9b6060', fontFamily: "'DM Mono', monospace" }}>
                    {item.prompt}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 이미지 확대 모달 */}
      {selectedImg && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.80)' }}
          onClick={() => setSelectedImg(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={selectedImg}
            alt="확대 이미지"
            className="max-w-full max-h-full rounded-xl"
            style={{ boxShadow: '0 8px 40px rgba(0,0,0,0.6)' }}
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setSelectedImg(null)}
            className="absolute top-4 right-4 text-white text-2xl font-bold"
            style={{ background: 'rgba(0,0,0,0.5)', borderRadius: '50%', width: 36, height: 36, border: 'none', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Manim 안정성 탭 ─────────────────────────────────────────────────────────

interface ManImAgentStatus {
  name: string
  last_run_at?: string
  manim_fallback_rate?: number
  character_drift?: number
  error?: string
}

function ManImPanel() {
  const [agents, setAgents] = useState<ManImAgentStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/agents/status')
      .then(r => r.ok ? r.json() : { agents: [] })
      .then(d => setAgents(d.agents ?? []))
      .finally(() => setLoading(false))
  }, [])

  const videoAgent = agents.find(a =>
    a.name?.toLowerCase().includes('videostyle') ||
    a.name?.toLowerCase().includes('video_style')
  )
  const fallbackRate = videoAgent?.manim_fallback_rate
  const charDrift = videoAgent?.character_drift
  const lastRun = videoAgent?.last_run_at

  if (loading) return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} />
    </div>
  )

  return (
    <div style={G.card} className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <Cpu className="h-5 w-5" style={{ color: '#ee2400' }} />
        <div>
          <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>Manim 렌더링 안정성</h3>
          <p className="text-xs" style={{ color: G.text.muted }}>Step08 Manim fallback 비율 모니터링</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-6">
        {[
          {
            label: 'Manim 성공률',
            value: fallbackRate != null ? `${((1 - fallbackRate) * 100).toFixed(0)}%` : '—',
            sub: '임계값: 50%',
            warn: fallbackRate != null && fallbackRate > 0.5,
          },
          {
            label: 'Fallback 비율',
            value: fallbackRate != null ? `${(fallbackRate * 100).toFixed(0)}%` : '—',
            sub: '이미지 대체 비율',
            warn: fallbackRate != null && fallbackRate > 0.5,
          },
          {
            label: '캐릭터 드리프트',
            value: charDrift != null ? charDrift.toFixed(2) : '—',
            sub: '임계값: 0.7',
            warn: charDrift != null && charDrift > 0.7,
          },
          {
            label: '마지막 체크',
            value: lastRun ? new Date(lastRun).toLocaleDateString('ko-KR') : '—',
            sub: 'VideoStyleAgent 실행 기준',
            warn: false,
          },
        ].map(item => (
          <div key={item.label} className="p-4 rounded-xl" style={{
            background: item.warn ? 'rgba(238,36,0,0.08)' : 'rgba(238,36,0,0.04)',
            border: `1px solid rgba(238,36,0,${item.warn ? '0.2' : '0.08'})`,
          }}>
            <p className="text-xs mb-1" style={{ color: G.text.muted }}>{item.label}</p>
            <p className="text-xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: item.warn ? '#ee2400' : '#1a0505' }}>{item.value}</p>
            <p className="text-[10px] mt-0.5" style={{ color: G.text.muted }}>{item.sub}</p>
          </div>
        ))}
      </div>
      {agents.length === 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(238,36,0,0.06)' }}>
          <p className="text-xs font-semibold mb-1" style={{ color: '#5c1a1a' }}>데이터 없음</p>
          <p className="text-xs" style={{ color: G.text.muted }}>Sub-Agent 탭에서 VideoStyleAgent를 실행하면 데이터가 생성됩니다.</p>
        </div>
      )}
    </div>
  )
}

// ─── HITL 신호 탭 ────────────────────────────────────────────────────────────

interface HitlSignal {
  type: string
  message: string
  resolved: boolean
  created_at: string
}

function HitlPanel() {
  const [signals, setSignals] = useState<HitlSignal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/pipeline/status')
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.hitl_signals) setSignals(d.hitl_signals)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} /></div>

  const unresolved = signals.filter(s => !s.resolved)

  return (
    <div className="space-y-3">
      <div style={G.card} className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="h-5 w-5" style={{ color: '#ee2400' }} />
          <div>
            <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>HITL 신호</h3>
            <p className="text-xs" style={{ color: '#9b6060' }}>운영자 확인이 필요한 자동 감지 신호</p>
          </div>
          {unresolved.length > 0 && (
            <span className="ml-auto text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: 'rgba(238,36,0,0.12)', color: '#ee2400' }}>
              {unresolved.length}개 미해결
            </span>
          )}
        </div>

        {signals.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle2 className="h-10 w-10 mx-auto mb-3" style={{ color: '#22c55e' }} />
            <p className="text-sm font-medium" style={{ color: '#1a0505' }}>모든 신호 해결됨</p>
            <p className="text-xs mt-1" style={{ color: '#9b6060' }}>DevMaintenanceAgent가 이상 없음을 확인했습니다</p>
          </div>
        ) : (
          <div className="space-y-2">
            {signals.map((sig, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: sig.resolved ? 'rgba(34,197,94,0.05)' : 'rgba(238,36,0,0.06)', border: `1px solid ${sig.resolved ? 'rgba(34,197,94,0.2)' : 'rgba(238,36,0,0.15)'}` }}>
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" style={{ color: sig.resolved ? '#22c55e' : '#ee2400' }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium" style={{ color: '#1a0505' }}>{sig.type}</p>
                  <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>{sig.message}</p>
                  <p className="text-[10px] mt-1" style={{ color: '#9b6060', fontFamily: "'DM Mono', monospace" }}>
                    {new Date(sig.created_at).toLocaleString('ko-KR')}
                  </p>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: sig.resolved ? 'rgba(34,197,94,0.15)' : 'rgba(238,36,0,0.12)', color: sig.resolved ? '#22c55e' : '#ee2400' }}>
                  {sig.resolved ? '해결됨' : '미해결'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sub-Agent 탭 ────────────────────────────────────────────────────────────

const AGENTS = [
  { id: 'dev_maintenance', name: 'DevMaintenanceAgent', desc: '파이프라인 실패 감지 + 헬스체크' },
  { id: 'analytics_learning', name: 'AnalyticsLearningAgent', desc: 'KPI 분석 + Phase 승격' },
  { id: 'ui_ux', name: 'UiUxAgent', desc: '스키마 변경 감지 → TS 동기화' },
  { id: 'video_style', name: 'VideoStyleAgent', desc: '캐릭터 드리프트 + Manim 모니터링' },
]

interface AgentResult {
  ok: boolean
  agent_id: string
  exit_code: number
  result: unknown
  error?: string
}

function SubAgentPanel() {
  const [agents, setAgents] = useState<{ name: string; status?: string; error?: string }[]>([])
  const [running, setRunning] = useState<string | null>(null)
  // 에이전트별 실행 결과 저장
  const [results, setResults] = useState<Record<string, AgentResult>>({})

  useEffect(() => {
    fetch('/api/agents/status').then(r => r.ok ? r.json() : null).then(d => {
      if (d?.agents) setAgents(d.agents)
    })
  }, [])

  const runAgent = async (agentId: string) => {
    setRunning(agentId)
    // 이전 결과 초기화
    setResults(prev => { const next = { ...prev }; delete next[agentId]; return next })
    try {
      const res = await fetch('/api/agents/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      })
      const data: AgentResult = await res.json()
      setResults(prev => ({ ...prev, [agentId]: data }))
    } catch (e) {
      setResults(prev => ({ ...prev, [agentId]: { ok: false, agent_id: agentId, exit_code: -1, result: null, error: String(e) } }))
    } finally {
      setRunning(null)
    }
  }

  return (
    <div style={G.card} className="p-5">
      <div className="flex items-center gap-3 mb-5">
        <Bot className="h-5 w-5" style={{ color: '#ee2400' }} />
        <div>
          <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>Sub-Agent 현황</h3>
          <p className="text-xs" style={{ color: '#9b6060' }}>4개 자율 운영 에이전트</p>
        </div>
      </div>
      <div className="space-y-3">
        {AGENTS.map(agent => {
          const status = agents.find(a => a.name === agent.name)
          const result = results[agent.id]
          return (
            <div key={agent.id} className="rounded-xl" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.08)' }}>
              {/* 에이전트 헤더 */}
              <div className="flex items-center gap-4 p-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold" style={{ color: '#1a0505' }}>{agent.name}</p>
                  <p className="text-xs" style={{ color: '#9b6060' }}>{agent.desc}</p>
                  {status?.error && <p className="text-xs mt-1" style={{ color: '#ef4444' }}>{status.error}</p>}
                </div>
                <button
                  disabled={running !== null}
                  onClick={() => runAgent(agent.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
                  style={{ background: 'rgba(144,0,0,0.1)', color: '#900000', border: '1px solid rgba(144,0,0,0.2)' }}
                >
                  {running === agent.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                  {running === agent.id ? '실행 중...' : '실행'}
                </button>
              </div>
              {/* 실행 결과 표시 */}
              {result && (
                <div className="px-4 pb-4">
                  {/* exit_code 0만 성공, Windows 오류코드(0xC0000xxx) 포함 비정상 종료는 오류 */}
                  {(() => {
                    const isSuccess = result.exit_code === 0
                    const hasOutput = result.result && JSON.stringify(result.result) !== '{"raw":""}'
                    return (
                  <div className="rounded-lg p-3" style={{
                    background: isSuccess ? 'rgba(34,197,94,0.06)' : 'rgba(238,36,0,0.06)',
                    border: `1px solid ${isSuccess ? 'rgba(34,197,94,0.2)' : 'rgba(238,36,0,0.2)'}`,
                  }}>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{
                        background: isSuccess ? 'rgba(34,197,94,0.15)' : 'rgba(238,36,0,0.12)',
                        color: isSuccess ? '#22c55e' : '#ee2400',
                      }}>
                        {isSuccess ? '성공' : '오류'} · exit {result.exit_code}
                      </span>
                      {!isSuccess && result.exit_code === 3221225794 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(238,36,0,0.10)', color: '#ee2400' }}>
                          0xC0000142 — Python DLL 초기화 실패
                        </span>
                      )}
                      {!hasOutput && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(180,100,0,0.10)', color: '#b46000' }}>
                          출력 없음
                        </span>
                      )}
                    </div>
                    {result.error && (
                      <p className="text-xs mb-2" style={{ color: '#ef4444' }}>{result.error}</p>
                    )}
                    <pre className="text-[10px] leading-relaxed whitespace-pre-wrap break-all max-h-40 overflow-y-auto"
                      style={{ color: '#5c1a1a', fontFamily: "'DM Mono', monospace" }}>
                      {JSON.stringify(result.result, null, 2)}
                    </pre>
                  </div>
                    )
                  })()}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── 메인 페이지 ──────────────────────────────────────────────────────────────

export default function MonitorPage() {
  const [tab, setTab] = useState<TabId>('steps')

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
          파이프라인 모니터
        </h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>실시간 Step 관찰 · 검증 결과 확인</p>
      </div>

      {/* 검증 진행 현황 */}
      <VerificationBoard />

      {/* 탭 */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--tab-bg)', border: '1px solid var(--tab-border)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
            )}
            style={{
              background: tab === t.id ? '#900000' : 'transparent',
              color: tab === t.id ? '#ffefea' : '#9b6060',
            }}
          >
            <t.icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      {tab === 'preflight' && <PreflightPanel />}
      {tab === 'steps'    && <StepProgressPanel />}
      {tab === 'preview'  && <PreviewPanel />}
      {tab === 'manim'    && <ManImPanel />}
      {tab === 'hitl'     && <HitlPanel />}
      {tab === 'subagent' && <SubAgentPanel />}
    </div>
  )
}
