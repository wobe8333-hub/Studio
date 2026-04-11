'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  CheckCircle2, Circle, Loader2, XCircle,
  ChevronRight, RotateCcw, ClipboardCheck,
} from 'lucide-react'

// ─── 타입 ───────────────────────────────────────────────────────────────────

type StageStatus = 'pending' | 'in_progress' | 'done' | 'failed'

interface Stage {
  id: number
  status: StageStatus
  updated_at: string | null
  note: string
}

// ─── 단계 메타데이터 ──────────────────────────────────────────────────────────

const STAGE_META = [
  {
    id: 0,
    label: '0단계 · 사전 점검',
    shortLabel: '사전 점검',
    desc: 'API키 · 모듈 · Gemini 연결 · OAuth · FFmpeg',
    href: '/monitor',
    checkItems: ['GEMINI_API_KEY', 'YOUTUBE_API_KEY', '채널 파일', '모듈 import', 'Gemini API', 'FFmpeg'],
  },
  {
    id: 1,
    label: '1단계 · 파이프라인 실행',
    shortLabel: '파이프라인 실행',
    desc: 'DRY RUN 또는 실제 월간 파이프라인 실행',
    href: '/monitor',
    checkItems: ['트리거 실행', 'CH1+CH2 활성'],
  },
  {
    id: 2,
    label: '2단계 · 실시간 모니터링',
    shortLabel: '모니터링',
    desc: 'Step05~12 진행 상태 실시간 확인',
    href: '/monitor',
    checkItems: ['Step05 트렌드', 'Step08 영상생성', 'Step11 QA', 'Step12 업로드'],
  },
  {
    id: 3,
    label: '3단계 · 키워드·지식 수집',
    shortLabel: '키워드·지식',
    desc: '트렌드 grade(auto/review) + 지식 소스 확인',
    href: '/trends',
    checkItems: ['grade auto 존재', 'knowledge 데이터', '점수 구성 확인'],
  },
  {
    id: 4,
    label: '4단계 · Run 상세 검수',
    shortLabel: 'Run 검수',
    desc: '스크립트·이미지·영상·BGM·썸네일·제목',
    href: '/runs/CH1',
    checkItems: ['스크립트', '장면 이미지', '완성 영상', 'BGM', '썸네일 v1~v3', '제목 3종'],
  },
  {
    id: 5,
    label: '5단계 · QA 검수 승인',
    shortLabel: 'QA 승인',
    desc: '자동 QA 통과 + 수동 검수 승인 + 배리언트 선택',
    href: '/qa',
    checkItems: ['자동 QA 통과', '수동 검수 승인', '제목 선택', '썸네일 선택'],
  },
  {
    id: 6,
    label: '6단계 · 사후 분석',
    shortLabel: '사후 분석',
    desc: '48h KPI · 비용 · 수익 · 리스크 확인',
    href: '/learning',
    checkItems: ['CTR/AVP 확인', 'API 비용 적정', '수익 추적'],
  },
]

// ─── 스타일 헬퍼 ──────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<StageStatus, {
  bg: string; border: string; color: string; label: string; icon: React.ElementType
}> = {
  pending:     { bg: 'rgba(152,150,176,0.08)', border: 'rgba(152,150,176,0.18)', color: '#9896b0', label: '대기',    icon: Circle },
  in_progress: { bg: 'rgba(255,190,50,0.10)',  border: 'rgba(255,170,0,0.28)',   color: '#b47800', label: '진행 중', icon: Loader2 },
  done:        { bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.25)',   color: '#16a34a', label: '완료',    icon: CheckCircle2 },
  failed:      { bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)',   color: '#dc2626', label: '실패',    icon: XCircle },
}

// 클릭 시 다음 상태 순환
const NEXT_STATUS: Record<StageStatus, StageStatus> = {
  pending: 'in_progress',
  in_progress: 'done',
  done: 'failed',
  failed: 'pending',
}

// ─── 진행률 계산 ─────────────────────────────────────────────────────────────

function calcProgress(stages: Stage[]) {
  const done  = stages.filter(s => s.status === 'done').length
  const total = stages.length
  return { done, total, pct: Math.round((done / total) * 100) }
}

// ─── 메인 컴포넌트 ────────────────────────────────────────────────────────────

const CARD_BASE: React.CSSProperties = {
  background: 'var(--card)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid var(--border)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(180,40,40,0.07)',
}

export default function VerificationBoard() {
  const [stages, setStages] = useState<Stage[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState<number | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/verification')
      if (res.ok) {
        const data = await res.json()
        setStages(data.stages ?? [])
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  // 단계 상태 순환 업데이트
  const cycleStatus = async (stageId: number, currentStatus: StageStatus) => {
    const next = NEXT_STATUS[currentStatus]
    setUpdating(stageId)
    try {
      const res = await fetch('/api/verification', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: stageId, status: next }),
      })
      if (res.ok) {
        const data = await res.json()
        setStages(data.stages ?? [])
      }
    } finally {
      setUpdating(null)
    }
  }

  // 전체 초기화
  const resetAll = async () => {
    if (!confirm('모든 검증 단계를 초기화하시겠습니까?')) return
    setUpdating(-1)
    try {
      const res = await fetch('/api/verification', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset: true }),
      })
      if (res.ok) {
        const data = await res.json()
        setStages(data.stages ?? [])
      }
    } finally {
      setUpdating(null)
    }
  }

  if (loading) {
    return (
      <div style={{ ...CARD_BASE, padding: 16 }} className="flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" style={{ color: '#b06060' }} />
        <span style={{ fontSize: 12, color: '#9b6060' }}>검증 현황 로딩 중...</span>
      </div>
    )
  }

  const { done, total, pct } = calcProgress(stages)
  // 현재 진행 중인 첫 번째 단계 찾기
  const currentStage = stages.find(s => s.status === 'in_progress') ?? stages.find(s => s.status === 'pending')

  return (
    <div style={{ ...CARD_BASE, padding: 16 }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ClipboardCheck size={16} style={{ color: 'var(--p4)' }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--t1)' }}>검증 진행 현황</span>
          <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99,
            background: pct === 100 ? 'rgba(34,197,94,0.12)' : 'rgba(180,40,40,0.10)',
            color: pct === 100 ? '#16a34a' : 'var(--p4)',
          }}>
            {done}/{total} 완료
          </span>
        </div>
        <button
          onClick={resetAll}
          disabled={updating !== null}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 11, color: 'var(--t3)', background: 'transparent',
            border: 'none', cursor: 'pointer', padding: '2px 6px',
          }}
          title="전체 초기화"
        >
          <RotateCcw size={12} />
          초기화
        </button>
      </div>

      {/* 진행률 바 */}
      <div style={{ height: 6, borderRadius: 99, background: 'rgba(180,40,40,0.08)', marginBottom: 12, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          borderRadius: 99,
          background: pct === 100 ? '#22c55e' : 'linear-gradient(90deg, var(--p4) 0%, #e85555 100%)',
          transition: 'width 0.4s ease',
        }} />
      </div>

      {/* 현재 진행 중 안내 */}
      {currentStage && pct < 100 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10,
          padding: '6px 10px', borderRadius: 8,
          background: 'rgba(180,40,40,0.05)', border: '1px solid rgba(180,40,40,0.10)',
        }}>
          <ChevronRight size={12} style={{ color: 'var(--p4)', flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: 'var(--t2)' }}>
            현재: <strong>{STAGE_META[currentStage.id]?.shortLabel}</strong>
            {' '}—{' '}
            <Link href={STAGE_META[currentStage.id]?.href ?? '/'} style={{ color: 'var(--p4)', textDecoration: 'underline', fontSize: 11 }}>
              바로 가기
            </Link>
          </span>
        </div>
      )}
      {pct === 100 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10,
          padding: '6px 10px', borderRadius: 8,
          background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.20)',
        }}>
          <CheckCircle2 size={12} style={{ color: '#16a34a' }} />
          <span style={{ fontSize: 11, color: '#15803d', fontWeight: 600 }}>전체 검증 완료! 파이프라인 운영 준비됨</span>
        </div>
      )}

      {/* 단계 그리드 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 8,
      }}>
        {STAGE_META.map(meta => {
          const stage = stages.find(s => s.id === meta.id)
          const status: StageStatus = stage?.status ?? 'pending'
          const cfg = STATUS_CONFIG[status]
          const Icon = cfg.icon
          const isUpdating = updating === meta.id

          return (
            <div
              key={meta.id}
              style={{
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
                borderRadius: 10,
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              {/* 단계 헤더 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--t1)' }}>{meta.label}</span>
                {/* 상태 토글 버튼 */}
                <button
                  onClick={() => cycleStatus(meta.id, status)}
                  disabled={isUpdating || updating !== null}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 3,
                    fontSize: 10, fontWeight: 600, color: cfg.color,
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    padding: '2px 4px', borderRadius: 4,
                    opacity: (isUpdating || (updating !== null && updating !== meta.id)) ? 0.5 : 1,
                  }}
                  title="클릭하여 상태 변경"
                >
                  {isUpdating
                    ? <Loader2 size={12} className="animate-spin" />
                    : <Icon size={12} style={status === 'in_progress' ? { animation: 'spin 1s linear infinite' } : {}} />
                  }
                  {cfg.label}
                </button>
              </div>

              {/* 설명 */}
              <p style={{ fontSize: 10, color: 'var(--t3)', lineHeight: 1.4, margin: 0 }}>
                {meta.desc}
              </p>

              {/* 업데이트 시각 + 이동 링크 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 }}>
                {stage?.updated_at ? (
                  <span style={{ fontSize: 9, color: 'var(--t3)', fontFamily: 'monospace' }}>
                    {new Date(stage.updated_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                ) : <span />}
                <Link
                  href={meta.href}
                  style={{
                    fontSize: 9, fontWeight: 600, color: 'var(--p4)',
                    textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 2,
                  }}
                >
                  이동 <ChevronRight size={9} />
                </Link>
              </div>
            </div>
          )
        })}
      </div>

      {/* 도움말 */}
      <p style={{ fontSize: 10, color: 'var(--t3)', marginTop: 10, marginBottom: 0 }}>
        💡 각 단계 상태 버튼 클릭 → <strong>대기 → 진행 중 → 완료 → 실패</strong> 순환
      </p>
    </div>
  )
}
