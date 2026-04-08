'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  CheckSquare,
  List,
  Monitor,
  Tv,
  Settings,
  ChevronsRight,
} from 'lucide-react'

const NAV_GROUPS = [
  {
    label: '경영',
    items: [
      { title: 'KPI 대시보드', url: '/',        icon: LayoutDashboard },
      { title: '트렌드 관리',  url: '/trends',  icon: TrendingUp },
      { title: '수익 추적',   url: '/revenue', icon: BarChart2 },
    ],
  },
  {
    label: '운영',
    items: [
      { title: 'QA 검수',    url: '/qa',           icon: CheckSquare },
      { title: '런 목록',    url: '/runs/CH1',     icon: List },
      { title: '파이프라인', url: '/monitor',      icon: Monitor },
      { title: '채널 상세',  url: '/channels/CH1', icon: Tv },
      { title: '설정',       url: '/settings',     icon: Settings },
    ],
  },
]

interface ChannelItem {
  id: string
  category_ko: string | null
}

interface CollapsibleSidebarProps {
  channels?: ChannelItem[]
}

export function CollapsibleSidebar({ channels: _channels }: CollapsibleSidebarProps) {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  return (
    <div
      className="kas-sidebar"
      style={{
        width: open ? 160 : 44,
        height: '100vh',
        position: 'sticky',
        top: 0,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(180,40,40,0.92)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(255,140,140,0.2)',
        transition: 'width 0.25s ease',
        overflow: 'hidden',
        zIndex: 20,
      }}
    >
      {/* 토글 버튼 */}
      <button
        onClick={() => setOpen(!open)}
        aria-label={open ? '사이드바 닫기' : '사이드바 열기'}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 44,
          height: 44,
          flexShrink: 0,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'rgba(255,255,255,0.7)',
        }}
      >
        <ChevronsRight
          size={18}
          strokeWidth={1.8}
          style={{
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.25s ease',
          }}
        />
      </button>

      {/* 네비게이션 */}
      <nav style={{ flex: 1, paddingTop: 4, overflowY: 'auto', overflowX: 'hidden' }}>
        {NAV_GROUPS.map((group, gi) => (
          <div key={group.label}>
            {/* 그룹 구분선 + 레이블 */}
            {gi > 0 && (
              <div
                style={{
                  margin: '6px 8px',
                  height: 1,
                  background: 'rgba(255,255,255,0.15)',
                }}
              />
            )}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '2px 12px 2px',
                height: 20,
                overflow: 'hidden',
              }}
            >
              <span
                style={{
                  maxWidth: open ? 120 : 0,
                  overflow: 'hidden',
                  opacity: open ? 0.55 : 0,
                  transition: 'max-width 0.25s ease, opacity 0.2s ease',
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  color: 'rgba(255,255,255,0.9)',
                  whiteSpace: 'nowrap',
                  textTransform: 'uppercase',
                }}
              >
                {group.label}
              </span>
            </div>

            {/* 메뉴 아이템 */}
            {group.items.map((item) => {
              const isActive = item.url === '/'
                ? pathname === '/'
                : pathname.startsWith(item.url)
              return (
                <Link
                  key={item.url}
                  href={item.url}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    margin: '1px 4px',
                    borderRadius: 8,
                    color: isActive ? '#ffffff' : 'rgba(255,255,255,0.7)',
                    background: isActive ? 'rgba(255,255,255,0.18)' : 'transparent',
                    textDecoration: 'none',
                    whiteSpace: 'nowrap',
                    transition: 'background 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.10)'
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <item.icon size={18} strokeWidth={1.8} style={{ flexShrink: 0 }} />
                  <span
                    style={{
                      maxWidth: open ? 120 : 0,
                      overflow: 'hidden',
                      opacity: open ? 1 : 0,
                      transition: 'max-width 0.25s ease, opacity 0.2s ease',
                      fontSize: 13,
                      fontWeight: 500,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.title}
                  </span>
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
    </div>
  )
}

// AppSidebar alias — layout.tsx 교체 전 하위호환
export { CollapsibleSidebar as AppSidebar }
