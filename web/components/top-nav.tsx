'use client'

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
  BookOpen,
} from 'lucide-react'

const NAV_GROUPS = [
  {
    label: '경영',
    items: [
      { title: 'KPI',   url: '/',          icon: LayoutDashboard },
      { title: '트렌드', url: '/trends',    icon: TrendingUp },
      { title: '지식',   url: '/knowledge', icon: BookOpen },
      { title: '수익',   url: '/revenue',   icon: BarChart2 },
    ],
  },
  {
    label: '운영',
    items: [
      { title: 'QA',      url: '/qa',           icon: CheckSquare },
      { title: '런 목록', url: '/runs/CH1',     icon: List },
      { title: '파이프라인', url: '/monitor',   icon: Monitor },
      { title: '채널',    url: '/channels/CH1', icon: Tv },
      { title: '설정',    url: '/settings',     icon: Settings },
    ],
  },
]

export function TopNav() {
  const pathname = usePathname()

  return (
    <header
      className="kas-top-nav"
      style={{
        flexShrink: 0,
        background: 'var(--sidebar)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--sidebar-border)',
        position: 'sticky',
        top: 0,
        zIndex: 20,
      }}
    >
      {/* 로고 행 */}
      <div
        style={{
          height: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          borderBottom: '1px solid rgba(255,140,140,0.12)',
        }}
      >
        <span
          style={{
            fontWeight: 800,
            fontSize: 15,
            color: 'var(--sidebar-foreground)',
            letterSpacing: '-0.02em',
          }}
        >
          KAS Studio
        </span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: 99,
            background: 'rgba(255,160,160,0.25)',
            color: 'var(--sidebar-primary)',
            letterSpacing: '0.08em',
          }}
        >
          LIVE
        </span>
      </div>

      {/* 탭 행 */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          height: 40,
          overflowX: 'auto',
          scrollbarWidth: 'none',
          padding: '0 8px',
          gap: 2,
        }}
      >
        {NAV_GROUPS.map((group, gi) => (
          <div
            key={group.label}
            style={{ display: 'flex', alignItems: 'center', gap: 2 }}
          >
            {/* 그룹 구분선 */}
            {gi > 0 && (
              <div
                style={{
                  width: 1,
                  height: 20,
                  background: 'rgba(255,255,255,0.2)',
                  margin: '0 4px',
                  flexShrink: 0,
                }}
              />
            )}

            {group.items.map((item) => {
              const isActive =
                item.url === '/'
                  ? pathname === '/'
                  : pathname.startsWith(item.url)
              return (
                <Link
                  key={item.url}
                  href={item.url}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '4px 10px',
                    borderRadius: 6,
                    color: isActive ? '#ffffff' : 'rgba(255,255,255,0.65)',
                    background: isActive
                      ? 'rgba(255,255,255,0.18)'
                      : 'transparent',
                    textDecoration: 'none',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                    transition: 'background 0.15s ease',
                    fontSize: 12,
                    fontWeight: isActive ? 600 : 500,
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive)
                      e.currentTarget.style.background = 'rgba(255,255,255,0.10)'
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive)
                      e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <item.icon size={14} strokeWidth={1.8} style={{ flexShrink: 0 }} />
                  {item.title}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
    </header>
  )
}
