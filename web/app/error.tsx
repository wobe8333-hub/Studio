'use client'

// React 에러 경계는 클라이언트 컴포넌트여야 함
import { useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function GlobalError({ error, reset }: ErrorProps) {
  useEffect(() => {
    // 에러 로깅 (Sentry 연동 시 여기서 captureException 호출)
    console.error('[KAS Error]', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 p-8 text-center">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-destructive/10">
        <AlertTriangle className="w-8 h-8 text-destructive" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">페이지를 불러올 수 없습니다</h2>
        <p className="text-sm text-muted-foreground max-w-md">
          데이터를 가져오는 중 오류가 발생했습니다.
          {error.digest && (
            <span className="block mt-1 font-mono text-xs opacity-60">
              오류 코드: {error.digest}
            </span>
          )}
        </p>
      </div>
      <Button onClick={reset} variant="outline" size="sm">
        다시 시도
      </Button>
    </div>
  )
}
