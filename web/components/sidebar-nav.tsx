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
  Tv,
  Activity,
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

const navItems = [
  { title: '전체 KPI', url: '/', icon: LayoutDashboard },
  { title: '트렌드 관리', url: '/trends', icon: TrendingUp },
  { title: '수익 추적', url: '/revenue', icon: DollarSign },
  { title: '리스크 모니터링', url: '/risk', icon: ShieldAlert },
  { title: '학습 피드백', url: '/learning', icon: Brain },
  { title: '비용/쿼터', url: '/cost', icon: CreditCard },
]

const channelItems = [
  { title: 'CH1 경제', url: '/channels/CH1' },
  { title: 'CH2 과학', url: '/channels/CH2' },
  { title: 'CH3 부동산', url: '/channels/CH3' },
  { title: 'CH4 심리', url: '/channels/CH4' },
  { title: 'CH5 미스터리', url: '/channels/CH5' },
  { title: 'CH6 역사', url: '/channels/CH6' },
  { title: 'CH7 전쟁사', url: '/channels/CH7' },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-primary" />
          <span className="font-bold text-base">KAS Studio</span>
        </div>
        <p className="text-xs text-muted-foreground">AI 자동화 파이프라인</p>
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
              {channelItems.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton
                    isActive={pathname.startsWith(item.url)}
                    render={<Link href={item.url} />}
                  >
                    <Activity className="h-4 w-4" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t">
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
