import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from 'next-themes'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CollapsibleSidebar } from '@/components/sidebar-nav'
import { BottomNav } from '@/components/bottom-nav'
import { ThemeToggle } from '@/components/theme-toggle'
import { createClient } from '@/lib/supabase/server'

export const metadata: Metadata = {
  title: 'KAS Studio — 7채널 AI 자동화 대시보드',
  description: 'Knowledge Animation Studio 파이프라인 모니터링 대시보드',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'KAS Studio',
  },
  other: {
    'mobile-web-app-capable': 'yes',
  },
}

async function fetchChannels() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return null

  try {
    const supabase = await createClient()
    const { data } = await supabase
      .from('channels')
      .select('id, category_ko')
      .order('id')
    return data
  } catch {
    return null
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const channels = await fetchChannels()

  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <TooltipProvider>
            <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
              {/* 접이식 사이드바 (데스크톱 전용) */}
              <CollapsibleSidebar channels={channels ?? undefined} />

              {/* 오른쪽 메인 영역 */}
              <div className="kas-main-col" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* 탑바 */}
                <header
                  style={{
                    height: 48,
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0 20px',
                    background: 'var(--sidebar)',
                    backdropFilter: 'blur(20px)',
                    WebkitBackdropFilter: 'blur(20px)',
                    borderBottom: '1px solid var(--sidebar-border)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 10,
                  }}
                >
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: 15,
                      color: 'var(--sidebar-foreground)',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    KAS Studio
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
                    <ThemeToggle />
                  </div>
                </header>

                {/* 페이지 콘텐츠 */}
                <main
                  className="kas-content"
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '16px 20px',
                  }}
                >
                  {children}
                </main>
              </div>
            </div>

            {/* 하단 탭 바 (모바일 전용) */}
            <BottomNav />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
