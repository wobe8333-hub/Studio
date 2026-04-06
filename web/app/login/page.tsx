'use client'

import { useActionState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Zap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { login, type LoginState } from './actions'

function LoginForm() {
  const searchParams = useSearchParams()
  const from = searchParams.get('from') ?? '/'

  const [state, formAction, isPending] = useActionState<LoginState, FormData>(login, null)

  return (
    <form action={formAction} className="space-y-4">
      {/* 리다이렉트 원본 경로 전달 */}
      <input type="hidden" name="from" value={from} />

      <div className="space-y-1.5">
        <label htmlFor="password" className="text-sm font-medium text-foreground">
          비밀번호
        </label>
        <Input
          id="password"
          name="password"
          type="password"
          placeholder="••••••••"
          autoFocus
          required
          className="h-10"
        />
      </div>

      {state?.error && (
        <p className="text-sm text-destructive">{state.error}</p>
      )}

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? '확인 중...' : '로그인'}
      </Button>
    </form>
  )
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center pb-4">
          <div className="flex justify-center mb-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Zap className="h-5 w-5" />
            </div>
          </div>
          <CardTitle className="font-heading text-xl">KAS Studio</CardTitle>
          <CardDescription>대시보드 접근 비밀번호를 입력하세요</CardDescription>
        </CardHeader>
        <CardContent>
          {/* useSearchParams는 Suspense 경계 필요 */}
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  )
}
