'use client'

import { useState } from 'react'
import {
  LayoutDashboard,
  Monitor,
  DollarSign,
  TrendingUp,
  BarChart2,
  Activity,
} from 'lucide-react'
import HomeOpsTab from './home-ops-tab'
import type { Channel } from '@/lib/types'

const CH_COLORS: Record<string, string> = {
  CH1: '#e07070',
  CH2: '#c4a0d4',
  CH3: '#7ab3d4',
  CH4: '#8785A2',
  CH5: '#d47a7a',
  CH6: '#70a4d4',
  CH7: '#b4709c',
}

// 6개월 추이 — mock 데이터 (실 수익 데이터 미연동)
const MONTHLY_TREND = [
  { month: '11월', value: 0 },
  { month: '12월', value: 0 },
  { month: '1월',  value: 0 },
  { month: '2월',  value: 0 },
  { month: '3월',  value: 0 },
  { month: '4월',  value: 0 },
]

const CARD_BASE: React.CSSProperties = {
  background: 'rgba(255,255,255,0.60)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(220,80,80,0.18)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(180,40,40,0.07)',
}

interface KpiCardProps {
  label: string
  value: string
  sub: string
  Icon: React.ElementType
}

function KpiCard({ label, value, sub, Icon }: KpiCardProps) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      style={{
        ...CARD_BASE,
        padding: 16,
        transform: hovered ? 'translateY(-2px)' : 'none',
        boxShadow: hovered
          ? '0 12px 32px rgba(180,40,40,0.12)'
          : '0 4px 16px rgba(180,40,40,0.07)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: '#9b4040', fontWeight: 500 }}>{label}</span>
        <Icon size={16} strokeWidth={1.8} color="#c03030" />
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color: '#6b1a1a', lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: 11, color: '#b06060', marginTop: 4 }}>{sub}</div>
    </div>
  )
}

interface ChannelCardProps {
  ch: Channel
  isActive: boolean
}

function ChannelCard({ ch, isActive }: ChannelCardProps) {
  const [hovered, setHovered] = useState(false)
  const color = CH_COLORS[ch.id] ?? '#8785A2'
  return (
    <div
      style={{
        ...CARD_BASE,
        padding: 14,
        opacity: isActive ? 1 : 0.35,
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
        transform: hovered && isActive ? 'translateY(-2px)' : 'none',
        borderColor: hovered && isActive ? 'rgba(220,80,80,0.45)' : 'rgba(220,80,80,0.18)',
        boxShadow: hovered && isActive
          ? '0 8px 24px rgba(180,40,40,0.12)'
          : '0 4px 16px rgba(180,40,40,0.07)',
        cursor: isActive ? 'pointer' : 'default',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: isActive ? color : '#d1d5db',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 9,
            fontWeight: 700,
            boxShadow: isActive ? `0 0 8px ${color}80` : 'none',
            flexShrink: 0,
          }}
        >
          {ch.id}
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#4a1010' }}>{ch.category_ko}</div>
          <div style={{ fontSize: 10, color: isActive ? '#16a34a' : '#b06060' }}>
            {isActive ? 'LIVE' : '준비중'}
          </div>
        </div>
      </div>
      {/* 수익 진행 바 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: '#b06060' }}>이번달 수익</span>
          <span style={{ fontSize: 10, color: '#6b1a1a', fontWeight: 600 }}>0%</span>
        </div>
        <div style={{ height: 4, background: 'rgba(220,80,80,0.10)', borderRadius: 2, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: '0%',
              background: isActive ? color : '#d1d5db',
              borderRadius: 2,
            }}
          />
        </div>
      </div>
    </div>
  )
}

interface HomeExecTabProps {
  channels: Channel[]
  totalRuns: number
  activeChannelCount: number
}

export default function HomeExecTab({ channels, totalRuns, activeChannelCount }: HomeExecTabProps) {
  const [activeTab, setActiveTab] = useState<'exec' | 'ops'>('exec')

  const TABS = [
    { id: 'exec' as const, label: '경영', Icon: LayoutDashboard },
    { id: 'ops'  as const, label: '운영', Icon: Monitor },
  ]

  return (
    <div>
      {/* 탭 바 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 16px',
                borderRadius: 8,
                border: 'none',
                cursor: 'pointer',
                background: isActive ? 'rgba(180,40,40,0.88)' : 'transparent',
                color: isActive ? '#ffffff' : '#9b4040',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                transition: 'background 0.2s ease, color 0.2s ease',
              }}
            >
              <tab.Icon size={15} strokeWidth={1.8} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── 경영 탭 ── */}
      {activeTab === 'exec' && (
        <div>
          {/* KPI 카드 4개 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 12,
              marginBottom: 16,
            }}
          >
            <KpiCard label="이번달 수익"  value="₩0"                        sub="목표: ₩14,000,000" Icon={DollarSign} />
            <KpiCard label="달성률"       value="0%"                         sub="목표 대비"         Icon={TrendingUp} />
            <KpiCard label="총 Runs"      value={String(totalRuns)}          sub="누적 실행"         Icon={BarChart2}  />
            <KpiCard label="활성 채널"    value={`${activeChannelCount}/7`}  sub="launch_phase 1"   Icon={Activity}   />
          </div>

          {/* 채널 목표 진행 바 + 6개월 추이 차트 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 12,
              marginBottom: 16,
            }}
          >
            {/* 채널별 목표 진행 */}
            <div style={{ ...CARD_BASE, padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#4a1010', marginBottom: 12 }}>
                채널별 목표 진행
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {channels.map((ch) => {
                  const color = CH_COLORS[ch.id] ?? '#8785A2'
                  const isActive = ch.launch_phase === 1
                  return (
                    <div key={ch.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 11, color: '#7a3030', fontWeight: 500 }}>
                          {ch.id} {ch.category_ko}
                        </span>
                        <span style={{ fontSize: 11, color: '#b06060' }}>0%</span>
                      </div>
                      <div
                        style={{
                          height: 5,
                          background: 'rgba(220,80,80,0.10)',
                          borderRadius: 3,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: '0%',
                            background: isActive ? color : '#d1d5db',
                            borderRadius: 3,
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* 6개월 수익 추이 — CSS flex 바 차트 (mock) */}
            <div style={{ ...CARD_BASE, padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#4a1010', marginBottom: 12 }}>
                6개월 수익 추이
              </h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 80 }}>
                {MONTHLY_TREND.map((item) => (
                  <div
                    key={item.month}
                    style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
                  >
                    <div
                      style={{
                        width: '100%',
                        height: item.value > 0 ? `${(item.value / 14000000) * 64}px` : 4,
                        background: item.value > 0 ? '#e85555' : 'rgba(220,80,80,0.12)',
                        borderRadius: '3px 3px 0 0',
                        transition: 'height 0.6s ease',
                      }}
                    />
                    <span style={{ fontSize: 9, color: '#b06060' }}>{item.month}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 채널 카드 7개 그리드 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: 10,
            }}
          >
            {channels.map((ch) => (
              <ChannelCard key={ch.id} ch={ch} isActive={ch.launch_phase === 1} />
            ))}
          </div>
        </div>
      )}

      {/* ── 운영 탭 ── */}
      {activeTab === 'ops' && <HomeOpsTab />}
    </div>
  )
}
