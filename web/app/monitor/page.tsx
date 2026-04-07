'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  Activity, CheckCircle2, AlertTriangle, Bot,
  RefreshCw, Play, Loader2, Terminal, Clock,
  Image as ImageIcon, Cpu, Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── 탭 정의 ─────────────────────────────────────────────────────────────────

const TABS = [
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
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(238,36,0,0.12)',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
  } as React.CSSProperties,
  text: { primary: '#1a0505', secondary: '#5c1a1a', muted: '#9b6060' },
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

  if (!data?.active || !data.steps?.length) {
    return (
      <div style={G.card} className="p-8 text-center">
        <Activity className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.3)' }} />
        <p className="text-lg font-bold mb-2" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>파이프라인 대기 중</p>
        <p className="text-sm mb-6" style={{ color: '#9b6060' }}>홈에서 '테스트 런' 버튼을 눌러 파이프라인을 시작하세요</p>
        <Link href="/" className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold" style={{ background: '#900000', color: '#ffefea' }}>
          ▶ 테스트 런 시작
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div style={G.card} className="px-5 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#ee2400] animate-pulse" />
            <span className="font-bold" style={{ color: '#1a0505' }}>{data.channel_id}</span>
            {data.dry_run && <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(238,36,0,0.12)', color: '#ee2400' }}>DRY RUN</span>}
          </div>
          <p className="text-xs mt-0.5" style={{ fontFamily: "'DM Mono', monospace", color: '#9b6060' }}>{data.run_id}</p>
        </div>
        <div className="text-right text-xs" style={{ color: '#9b6060' }}>
          {data.updated_at && <p>마지막 업데이트: {new Date(data.updated_at).toLocaleTimeString('ko-KR')}</p>}
          <p className="text-[10px] mt-0.5">3초마다 자동 새로고침</p>
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

function PreviewPanel() {
  const [data, setData] = useState<StepProgress | null>(null)

  useEffect(() => {
    const poll = async () => {
      const res = await fetch('/api/pipeline/steps')
      if (res.ok) setData(await res.json())
    }
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [])

  if (!data?.active || !data.channel_id || !data.run_id) {
    return (
      <div style={G.card} className="p-8 text-center">
        <ImageIcon className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.3)' }} />
        <p className="text-sm" style={{ color: '#9b6060' }}>파이프라인 실행 중일 때 이미지가 실시간으로 표시됩니다</p>
      </div>
    )
  }

  const ch = data.channel_id
  const runId = data.run_id
  const scenesPath = `/api/artifacts/${ch}/${runId}/step08/scenes/`

  return (
    <div className="space-y-4">
      <div style={G.card} className="p-5">
        <h3 className="font-bold mb-1" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>생성 이미지 미리보기</h3>
        <p className="text-xs mb-4" style={{ color: '#9b6060' }}>Step08 실행 중 생성되는 장면 이미지가 여기에 표시됩니다 · 3초 폴링</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6].map(n => (
            <div key={n} className="aspect-video rounded-lg overflow-hidden flex items-center justify-center" style={{ background: 'rgba(238,36,0,0.06)', border: '1px solid rgba(238,36,0,0.1)' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${scenesPath}scene_${String(n).padStart(3, '0')}.jpg`}
                alt={`장면 ${n}`}
                className="w-full h-full object-cover"
                onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
              <span className="text-xs absolute" style={{ color: '#9b6060' }}>장면 {n}</span>
            </div>
          ))}
        </div>
      </div>
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

function SubAgentPanel() {
  const [agents, setAgents] = useState<{ name: string; status?: string; error?: string }[]>([])
  const [running, setRunning] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/agents/status').then(r => r.ok ? r.json() : null).then(d => {
      if (d?.agents) setAgents(d.agents)
    })
  }, [])

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
          return (
            <div key={agent.id} className="flex items-center gap-4 p-4 rounded-xl" style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.08)' }}>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold" style={{ color: '#1a0505' }}>{agent.name}</p>
                <p className="text-xs" style={{ color: '#9b6060' }}>{agent.desc}</p>
                {status?.error && <p className="text-xs mt-1 text-red-500">{status.error}</p>}
              </div>
              <button
                disabled={running === agent.id}
                onClick={async () => {
                  setRunning(agent.id)
                  await fetch('/api/agents/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ agent_id: agent.id }),
                  }).catch(() => {})
                  setRunning(null)
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
                style={{ background: 'rgba(144,0,0,0.1)', color: '#900000', border: '1px solid rgba(144,0,0,0.2)' }}
              >
                {running === agent.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                실행
              </button>
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

      {/* 탭 */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
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
      {tab === 'steps'    && <StepProgressPanel />}
      {tab === 'preview'  && <PreviewPanel />}
      {tab === 'manim'    && <ManImPanel />}
      {tab === 'hitl'     && <HitlPanel />}
      {tab === 'subagent' && <SubAgentPanel />}
    </div>
  )
}
