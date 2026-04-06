import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from 'next-themes'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppSidebar } from '@/components/sidebar-nav'
import { ThemeToggle } from '@/components/theme-toggle'
import { RealtimePipelineStatus } from '@/components/realtime-pipeline-status'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { createClient } from '@/lib/supabase/server'
import { HitlBanner } from '@/components/hitl-banner'

// 폰트는 globals.css Google Fonts import로 처리

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
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <TooltipProvider>
            <SidebarProvider>
              <AppSidebar channels={channels ?? undefined} />
              <SidebarInset>
                {/* Red Light 상단 그라디언트 바 */}
                <div
                  className="h-[2px] w-full shrink-0"
                  style={{ background: 'linear-gradient(90deg, #900000 0%, #ee2400 40%, #ffb09c 100%)' }}
                />
                <header
                  className="flex h-14 shrink-0 items-center gap-2 border-b px-4 sticky top-0 z-10"
                  style={{
                    background: 'rgba(255, 239, 234, 0.85)',
                    backdropFilter: 'blur(12px)',
                    borderColor: 'rgba(238, 36, 0, 0.12)',
                  }}
                >
                  <SidebarTrigger className="-ml-1 text-[#5c1a1a]" />
                  <Separator orientation="vertical" className="mr-2 h-4 bg-red-200/50" />
                  <div className="flex flex-1 items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#1a0505]" style={{ fontFamily: "'Libre Baskerville', Georgia, serif" }}>
                        KAS Studio
                      </span>
                      <Badge
                        variant="outline"
                        className="text-[10px] border-[rgba(238,36,0,0.3)] text-[#ee2400] px-1.5 py-0"
                        style={{ fontFamily: "'DM Mono', monospace" }}
                      >
                        LIVE
                      </Badge>
                      <RealtimePipelineStatus />
                    </div>
                    <ThemeToggle />
                  </div>
                </header>
                <HitlBanner />
                <main className="flex-1 overflow-auto p-4 md:p-6">
                  {children}
                </main>
              </SidebarInset>
            </SidebarProvider>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
