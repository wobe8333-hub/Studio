'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, TrendingUp, BarChart2, CheckSquare, List } from 'lucide-react'

const BOTTOM_ITEMS = [
  { title: '홈',    url: '/',         icon: LayoutDashboard },
  { title: '트렌드', url: '/trends',  icon: TrendingUp },
  { title: '수익',  url: '/revenue',  icon: BarChart2 },
  { title: 'QA',   url: '/qa',        icon: CheckSquare },
  { title: '런',   url: '/runs/CH1',  icon: List },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className="kas-bottom-nav"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 56,
        background: 'rgba(180,40,40,0.94)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(255,140,140,0.2)',
        zIndex: 50,
        alignItems: 'stretch',
      }}
    >
      {BOTTOM_ITEMS.map((item) => {
        const isActive =
          item.url === '/' ? pathname === '/' : pathname.startsWith(item.url)
        return (
          <Link
            key={item.url}
            href={item.url}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 3,
              color: isActive ? '#ffffff' : 'rgba(255,255,255,0.50)',
              textDecoration: 'none',
              background: isActive ? 'rgba(255,255,255,0.12)' : 'transparent',
              transition: 'background 0.2s',
            }}
          >
            <item.icon size={20} strokeWidth={1.8} />
            <span
              style={{
                fontSize: 9,
                fontWeight: isActive ? 700 : 500,
                letterSpacing: '0.02em',
              }}
            >
              {item.title}
            </span>
          </Link>
        )
      })}
    </nav>
  )
}
