import type { Metadata } from 'next'
import { Geist, Geist_Mono, Sora } from 'next/font/google'
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

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })
const sora = Sora({
  variable: '--font-display',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
})

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
      <body className={`${geistSans.variable} ${geistMono.variable} ${sora.variable} antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <TooltipProvider>
            <SidebarProvider>
              <AppSidebar channels={channels ?? undefined} />
              <SidebarInset>
                {/* 최상단 2px 멀티 그라데이션 바 */}
                <div
                  className="h-[2px] w-full shrink-0"
                  style={{ background: 'var(--gradient-bar)' }}
                />
                <header className="flex h-14 shrink-0 items-center gap-2 border-b border-white/[0.06] px-4 bg-background/70 backdrop-blur-xl sticky top-0 z-10">
                  <SidebarTrigger className="-ml-1" />
                  <Separator orientation="vertical" className="mr-2 h-4" />
                  <div className="flex flex-1 items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-heading font-semibold text-foreground">
                        KAS Studio
                      </span>
                      <Badge
                        variant="outline"
                        className="text-[10px] font-mono border-primary/30 text-primary px-1.5 py-0"
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
