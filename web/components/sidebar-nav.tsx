'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  DollarSign,
  ShieldAlert,
  Brain,
  CreditCard,
  Settings,
  Zap,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from '@/components/ui/sidebar'
import { cn } from '@/lib/utils'

const navItems = [
  { title: '전체 KPI', url: '/', icon: LayoutDashboard },
  { title: '트렌드 관리', url: '/trends', icon: TrendingUp },
  { title: '수익 추적', url: '/revenue', icon: DollarSign },
  { title: '리스크 모니터링', url: '/risk', icon: ShieldAlert },
  { title: '학습 피드백', url: '/learning', icon: Brain },
  { title: '비용/쿼터', url: '/cost', icon: CreditCard },
]

// 채널별 고유 색상 CSS 변수 맵
const CHANNEL_COLORS: Record<string, string> = {
  CH1: 'var(--channel-ch1)',
  CH2: 'var(--channel-ch2)',
  CH3: 'var(--channel-ch3)',
  CH4: 'var(--channel-ch4)',
  CH5: 'var(--channel-ch5)',
  CH6: 'var(--channel-ch6)',
  CH7: 'var(--channel-ch7)',
}

// fallback — Supabase 연동 전 기본값 (config.py CHANNEL_CATEGORY_KO 기준)
const DEFAULT_CHANNELS = [
  { id: 'CH1', category_ko: '경제' },
  { id: 'CH2', category_ko: '부동산' },
  { id: 'CH3', category_ko: '심리' },
  { id: 'CH4', category_ko: '미스터리' },
  { id: 'CH5', category_ko: '전쟁사' },
  { id: 'CH6', category_ko: '과학' },
  { id: 'CH7', category_ko: '역사' },
]

interface ChannelItem {
  id: string
  category_ko: string | null
}

interface AppSidebarProps {
  channels?: ChannelItem[]
}

export function AppSidebar({ channels = DEFAULT_CHANNELS }: AppSidebarProps) {
  const pathname = usePathname()

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-white/[0.05] px-4 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shrink-0">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <span className="font-heading font-bold text-sm tracking-tight">KAS Studio</span>
            <p className="text-[10px] text-muted-foreground leading-tight">AI 자동화 파이프라인</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>대시보드</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton
                    isActive={pathname === item.url}
                    render={<Link href={item.url} />}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>채널별 상세</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {channels.map((ch) => (
                <SidebarMenuItem key={ch.id}>
                  <SidebarMenuButton
                    isActive={pathname.startsWith(`/channels/${ch.id}`)}
                    render={<Link href={`/channels/${ch.id}`} />}
                  >
                    {/* 채널 고유 색상 dot */}
                    <span
                      className={cn(
                        'h-2.5 w-2.5 rounded-full shrink-0',
                        'ring-1 ring-inset ring-black/10 dark:ring-white/10'
                      )}
                      style={{
                        backgroundColor: CHANNEL_COLORS[ch.id] ?? 'var(--muted-foreground)',
                        boxShadow: `0 0 6px ${CHANNEL_COLORS[ch.id] ?? 'transparent'}`,
                      }}
                    />
                    <span>{ch.id} {ch.category_ko}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border/60">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={pathname === '/settings'}
              render={<Link href="/settings" />}
            >
              <Settings className="h-4 w-4" />
              <span>설정</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
