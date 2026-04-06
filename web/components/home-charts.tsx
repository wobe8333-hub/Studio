'use client'

import {
  AreaChart,
  Area,
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
} from 'recharts'

// ─── Sparkline ─────────────────────────────────────────────────────────────
// KPI 카드 내 미니 추이 그래프 (axes 없음)
interface SparklineProps {
  data: number[]
  color?: string
}

export function Sparkline({ data, color = 'var(--chart-1)' }: SparklineProps) {
  const chartData = data.map((v, i) => ({ i, v }))
  return (
    <div className="h-10 w-full mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`sparkGrad-${color.replace(/[^a-zA-Z0-9]/g, '')}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="v"
            stroke={color}
            fill={`url(#sparkGrad-${color.replace(/[^a-zA-Z0-9]/g, '')})`}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            style={{ filter: `drop-shadow(0 0 4px ${color})` }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── RadialGauge ────────────────────────────────────────────────────────────
// 달성률 반원형 게이지
interface RadialGaugeProps {
  value: number
  color?: string
}

export function RadialGauge({ value, color = 'var(--chart-1)' }: RadialGaugeProps) {
  const data = [{ value: Math.min(Math.max(value, 0), 100), fill: color }]
  return (
    <div className="h-14 w-14 mx-auto mt-1" style={{ filter: `drop-shadow(0 0 6px ${color})` }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="80%"
          innerRadius="65%"
          outerRadius="100%"
          startAngle={180}
          endAngle={0}
          data={data}
          barSize={6}
        >
          <RadialBar
            dataKey="value"
            cornerRadius={4}
            background={{ fill: 'var(--muted)' }}
            isAnimationActive={false}
          />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── ChannelDots ────────────────────────────────────────────────────────────
// 7채널 상태 표시 도트
interface ChannelDotsProps {
  activeIds: string[]
}

const ALL_CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7']

export function ChannelDots({ activeIds }: ChannelDotsProps) {
  return (
    <div className="flex gap-1.5 mt-2">
      {ALL_CHANNELS.map((id) => {
        const isActive = activeIds.includes(id)
        return (
          <span
            key={id}
            title={id}
            className="h-2 w-2 rounded-full transition-opacity"
            style={{
              backgroundColor: isActive
                ? `var(--channel-${id.toLowerCase()})`
                : 'var(--muted-foreground)',
              opacity: isActive ? 1 : 0.3,
              boxShadow: isActive
                ? `0 0 5px var(--channel-${id.toLowerCase()})`
                : 'none',
            }}
          />
        )
      })}
    </div>
  )
}
