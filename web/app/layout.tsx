import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from 'next-themes'
import { TooltipProvider } from '@/components/ui/tooltip'
import { TopNav } from '@/components/top-nav'
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
  await fetchChannels()

  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <TooltipProvider>
            <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
              {/* 상단 탭 네비게이션 */}
              <TopNav />

              {/* ThemeToggle — 탑바 우측 고정 */}
              <div
                style={{
                  position: 'fixed',
                  top: 8,
                  right: 16,
                  zIndex: 30,
                }}
              >
                <ThemeToggle />
              </div>

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

            {/* 하단 탭 바 (모바일 전용) */}
            <BottomNav />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
