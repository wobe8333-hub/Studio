'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, CheckCircle2, XCircle, Loader2, Clock, PlayCircle, RefreshCw, FlaskConical } from 'lucide-react'
import type { RunSummary } from '@/app/api/runs/[channelId]/route'

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

function StateIcon({ state }: { state: string }) {
  if (state === 'COMPLETED') return <CheckCircle2 size={16} style={{ color: '#16a34a' }} />
  if (state === 'FAILED') return <XCircle size={16} style={{ color: '#dc2626' }} />
  if (state === 'RUNNING') return <Loader2 size={16} style={{ color: '#ca8a04' }} className="animate-spin" />
  if (state === 'TEST') return <FlaskConical size={16} style={{ color: '#7c3aed' }} />
  return <Clock size={16} style={{ color: G.text.muted }} />
}

function QaBadge({ pass }: { pass: boolean | null | undefined }) {
  if (pass === null || pass === undefined) return <span style={{ color: G.text.muted, fontSize: '0.75rem' }}>QA 미실행</span>
  if (pass) return <span style={{ color: '#16a34a', fontSize: '0.75rem', fontWeight: 600 }}>QA 통과</span>
  return <span style={{ color: '#dc2626', fontSize: '0.75rem', fontWeight: 600 }}>QA 실패</span>
}

export default function ChannelRunsPage() {
  const params = useParams()
  const channelId = params.channelId as string
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchRuns = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true)
    try {
      const data = await fetch(`/api/runs/${channelId}`).then(r => r.json())
      if (data.error) throw new Error(data.error)
      setRuns(data.runs ?? [])
      setLastUpdated(new Date())
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
      if (isManual) setRefreshing(false)
    }
  }, [channelId])

  // 최초 로드 + 5초 폴링 (파이프라인 실행 중 신규 Run 자동 감지)
  useEffect(() => {
    fetchRuns()
    const interval = setInterval(() => fetchRuns(), 5000)
    return () => clearInterval(interval)
  }, [fetchRuns])

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <Link href="/" style={{ color: G.text.muted, display: 'flex', alignItems: 'center', gap: '0.25rem', textDecoration: 'none' }}>
          <ArrowLeft size={16} />
          <span style={{ fontSize: '0.875rem' }}>홈</span>
        </Link>
        <h1 style={{ margin: 0, color: G.text.primary, fontSize: '1.5rem', fontFamily: 'var(--font-baskerville)', flex: 1 }}>
          {channelId} 실행 이력
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {lastUpdated && (
            <span style={{ fontSize: '0.7rem', color: G.text.muted }}>
              {lastUpdated.toLocaleTimeString('ko-KR')} 갱신
            </span>
          )}
          <button
            onClick={() => fetchRuns(true)}
            disabled={refreshing}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.375rem',
              padding: '0.375rem 0.75rem', borderRadius: '0.5rem',
              border: '1px solid rgba(180,40,40,0.25)', background: 'transparent',
              color: '#7a3030', fontSize: '0.75rem', fontWeight: 600,
              cursor: refreshing ? 'not-allowed' : 'pointer',
            }}
          >
            <RefreshCw size={12} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            새로고침
          </button>
        </div>
      </div>

      {/* 로딩 */}
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <Loader2 size={32} style={{ color: '#900000' }} className="animate-spin" />
        </div>
      )}

      {/* 오류 */}
      {error && (
        <div style={{ ...G.card, padding: '1.5rem', color: '#dc2626' }}>
          오류: {error}
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && !error && runs.length === 0 && (
        <div style={{ ...G.card, padding: '3rem', textAlign: 'center' }}>
          <PlayCircle size={48} style={{ color: G.text.muted, margin: '0 auto 1rem' }} />
          <p style={{ color: G.text.primary, fontWeight: 600, margin: '0 0 0.5rem' }}>아직 실행 이력이 없습니다</p>
          <p style={{ color: G.text.muted, fontSize: '0.875rem', margin: 0 }}>
            파이프라인 실행 후 여기에 Run 목록이 표시됩니다.
          </p>
        </div>
      )}

      {/* Run 목록 */}
      {!loading && runs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {runs.map(run => (
            <Link
              key={run.run_id}
              href={`/runs/${channelId}/${run.run_id}`}
              style={{ textDecoration: 'none' }}
            >
              <div
                style={{ ...G.card, padding: '1.25rem 1.5rem', cursor: 'pointer' }}
                onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 12px 40px rgba(144,0,0,0.14)')}
                onMouseLeave={e => (e.currentTarget.style.boxShadow = G.card.boxShadow as string)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  {/* 좌측: Run 정보 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                      <StateIcon state={run.run_state} />
                      <span style={{ color: G.text.primary, fontWeight: 600, fontSize: '0.9rem',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {run.topic_title ?? run.run_id}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: G.text.muted }}>
                      {run.run_id} · {run.created_at ? new Date(run.created_at).toLocaleString('ko-KR') : '-'}
                    </div>
                  </div>

                  {/* 우측: QA 배지 */}
                  <div style={{ marginLeft: '1rem', flexShrink: 0 }}>
                    <QaBadge pass={run.qa_pass} />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
