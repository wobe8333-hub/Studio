'use client'

interface KpiBannerProps {
  revenue: number
  achievementRate: number
  activeChannels: number
  totalChannels: number
  totalRuns: number
  hitlPending: number
}

interface KpiItemProps {
  label: string
  value: string
  sub?: string
  highlight?: boolean
  isLast?: boolean
}

function KpiItem({ label, value, sub, highlight, isLast }: KpiItemProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        padding: '0 24px',
        borderRight: isLast ? 'none' : '1px solid rgba(255,199,199,0.25)',
        minWidth: 130,
        flex: 1,
      }}
    >
      <span
        style={{
          fontSize: 11,
          color: '#9896b0',
          fontWeight: 500,
          letterSpacing: '0.04em',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: highlight ? '#dc3545' : '#2d2b3d',
          letterSpacing: '-0.02em',
          lineHeight: 1.2,
          whiteSpace: 'nowrap',
        }}
      >
        {value}
      </span>
      {sub && (
        <span style={{ fontSize: 10, color: '#9896b0', whiteSpace: 'nowrap' }}>{sub}</span>
      )}
    </div>
  )
}

export function KpiBanner({
  revenue,
  achievementRate,
  activeChannels,
  totalChannels,
  totalRuns,
  hitlPending,
}: KpiBannerProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255,226,226,0.62)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,199,199,0.3)',
        borderRadius: '0.75rem',
        boxShadow: '0 4px 16px rgba(135,133,162,0.08)',
        padding: '14px 0',
        marginBottom: 16,
        overflowX: 'auto',
      }}
    >
      <KpiItem
        label="이번달 수익"
        value={`₩${revenue.toLocaleString()}`}
        sub="목표: ₩14,000,000"
      />
      <KpiItem
        label="달성률"
        value={`${achievementRate.toFixed(1)}%`}
        sub="목표 대비"
      />
      <KpiItem
        label="활성 채널"
        value={`${activeChannels}/${totalChannels}`}
        sub="launch_phase 1"
      />
      <KpiItem
        label="총 Runs"
        value={String(totalRuns)}
        sub="누적 실행"
      />
      <KpiItem
        label="HITL 대기"
        value={`${hitlPending}건`}
        highlight={hitlPending > 0}
        sub={hitlPending > 0 ? '확인 필요' : '정상'}
        isLast
      />
    </div>
  )
}
