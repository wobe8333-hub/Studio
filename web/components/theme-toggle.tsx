'use client'

import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // hydration mismatch 방지 — 마운트 후에만 렌더링
  useEffect(() => setMounted(true), [])

  if (!mounted) {
    return <Button variant="ghost" size="icon" className="h-8 w-8" />
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      style={{ color: 'var(--sidebar-primary)', opacity: 0.85 }}
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      title={resolvedTheme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
    >
      {resolvedTheme === 'dark' ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
      <span className="sr-only">테마 전환</span>
    </Button>
  )
}
