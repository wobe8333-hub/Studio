'use client'

import { useState, useEffect, useCallback } from 'react'
import { useIsMobile } from '@/hooks/use-is-mobile'

interface StepStatus {
  index: number
  name: string
  status: 'idle' | 'running' | 'done' | 'error' | 'skipped'
  elapsed_ms?: number
}

interface HitlSignal {
  id: string
  type: string
  message: string
  resolved: boolean
}

// API index(0~7) → 표시 레이블 매핑
const STEP_LABELS: Record<number, string> = {
  0: 'Step05 · 트렌드 수집',
  1: 'Step06 · 정책 적용',
  2: 'Step07 · 콘텐츠 계획',
  3: 'Step08 · 영상 생성',
  4: 'Step09 · BGM 합성',
  5: 'Step10 · 제목/썸네일',
  6: 'Step11 · QA 검수',
  7: 'Step12 · YouTube 업로드',
}

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  idle:    { bg: 'rgba(152,150,176,0.10)', color: '#9896b0', label: 'IDLE' },
  running: { bg: 'rgba(255,199,100,0.15)', color: '#c4860f', label: 'RUNNING' },
  done:    { bg: 'rgba(34,197,94,0.12)',   color: '#16a34a', label: 'DONE' },
  error:   { bg: 'rgba(239,68,68,0.12)',   color: '#dc2626', label: 'ERROR' },
  skipped: { bg: 'rgba(152,150,176,0.06)', color: '#c0bdd8', label: 'SKIPPED' },
}

const CARD_BASE: React.CSSProperties = {
  background: 'rgba(255,255,255,0.60)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(220,80,80,0.18)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(180,40,40,0.07)',
  padding: 16,
}

export default function HomeOpsTab() {
  const [steps, setSteps] = useState<StepStatus[]>([])
  const [hitlSignals, setHitlSignals] = useState<HitlSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const isMobile = useIsMobile()

  const fetchAll = useCallback(async () => {
    try {
      const [stepsRes, hitlRes] = await Promise.all([
        fetch('/api/pipeline/steps').then((r) => (r.ok ? r.json() : { steps: [] })),
        fetch('/api/hitl-signals').then((r) => (r.ok ? r.json() : [])),
      ])
      setSteps(stepsRes.steps ?? [])
      setHitlSignals(
        Array.isArray(hitlRes) ? hitlRes.filter((s: HitlSignal) => !s.resolved) : []
      )
    } catch {
      /* 네트워크 오류 무시 */
    } finally {
      setLoading(false)
    }
  }, [])

  // 탭이 활성일 때만 폴링 (cleanup으로 interval 해제)
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 3000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const triggerRun = async () => {
    setTriggering(true)
    try {
      await fetch('/api/pipeline/trigger', { method: 'POST' })
      await fetchAll()
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: isMobile ? 8 : 12 }}>
      {/* 파이프라인 스텝 현황 */}
      <div style={CARD_BASE}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#4a1010', marginBottom: 12 }}>
          파이프라인 스텝 현황
        </h3>
        {loading ? (
          <div style={{ color: '#9896b0', fontSize: 12 }}>불러오는 중...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {Object.entries(STEP_LABELS).map(([idxStr, label]) => {
              const idx = Number(idxStr)
              const stepData = steps.find((s) => s.index === idx)
              const status = stepData?.status ?? 'idle'
              const style = STATUS_STYLE[status] ?? STATUS_STYLE.idle
              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '7px 10px',
                    borderRadius: 8,
                    background: style.bg,
                  }}
                >
                  <span style={{ fontSize: 12, color: '#7a3030', fontWeight: 500 }}>{label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {stepData?.elapsed_ms && (
                      <span style={{ fontSize: 10, color: '#b06060' }}>
                        {(stepData.elapsed_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: style.color,
                        letterSpacing: '0.05em',
                      }}
                    >
                      {style.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 오른쪽 패널: HITL + 파이프라인 제어 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* HITL 신호 */}
        <div style={CARD_BASE}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#4a1010', marginBottom: 12 }}>
            HITL 대기 신호
            {hitlSignals.length > 0 && (
              <span
                style={{
                  marginLeft: 8,
                  background: 'rgba(239,68,68,0.12)',
                  color: '#dc2626',
                  fontSize: 10,
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: 99,
                }}
              >
                {hitlSignals.length}
              </span>
            )}
          </h3>
          {hitlSignals.length === 0 ? (
            <div style={{ color: '#16a34a', fontSize: 12 }}>대기 신호 없음 ✓</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {hitlSignals.slice(0, 4).map((sig) => (
                <div
                  key={sig.id}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 8,
                    background: 'rgba(239,68,68,0.06)',
                    border: '1px solid rgba(239,68,68,0.15)',
                  }}
                >
                  <div style={{ fontSize: 11, color: '#dc2626', fontWeight: 600 }}>
                    {sig.type}
                  </div>
                  <div style={{ fontSize: 11, color: '#5c5a74', marginTop: 2 }}>
                    {sig.message}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 파이프라인 제어 */}
        <div style={CARD_BASE}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#4a1010', marginBottom: 12 }}>
            파이프라인 제어
          </h3>
          <button
            onClick={triggerRun}
            disabled={triggering}
            style={{
              width: '100%',
              padding: '9px 16px',
              borderRadius: 8,
              border: 'none',
              background: triggering ? 'rgba(180,40,40,0.38)' : 'rgba(180,40,40,0.88)',
              color: '#ffffff',
              fontSize: 13,
              fontWeight: 600,
              cursor: triggering ? 'not-allowed' : 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!triggering) {
                e.currentTarget.style.transform = 'translateY(-1px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(180,40,40,0.30)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            {triggering ? '실행 중...' : '테스트 런 실행'}
          </button>
        </div>
      </div>
    </div>
  )
}
