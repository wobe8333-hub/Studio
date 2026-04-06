'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export type LoginState = { error: string } | null

/**
 * 대시보드 로그인 서버 액션.
 * DASHBOARD_PASSWORD 환경 변수와 일치하면 httpOnly 쿠키를 설정합니다.
 */
export async function login(prevState: LoginState, formData: FormData): Promise<LoginState> {
  const password = formData.get('password') as string
  const expected = process.env.DASHBOARD_PASSWORD

  // 패스워드 미설정 시 항상 허용 (개발 환경)
  if (!expected) {
    const from = (formData.get('from') as string) ?? '/'
    redirect(from)
  }

  if (!password || password !== expected) {
    return { error: '비밀번호가 올바르지 않습니다.' }
  }

  const cookieStore = await cookies()
  cookieStore.set('kas_access', expected, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 24 * 7, // 7일
    path: '/',
  })

  const from = (formData.get('from') as string) ?? '/'
  redirect(from)
}
