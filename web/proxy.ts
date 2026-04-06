import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const COOKIE_NAME = 'kas_access'

// 인증 없이 접근 허용할 경로 prefix
const PUBLIC_PREFIXES = [
  '/login',
  '/_next',
  '/favicon',
  '/manifest',
  '/icons',
  '/apple-touch',
]

/**
 * 대시보드 패스워드 보호 프록시 (Next.js 16+).
 * DASHBOARD_PASSWORD 환경 변수가 설정된 경우에만 활성화됩니다.
 * 미설정 시 전체 공개 (개발 환경 기본값).
 */
export function proxy(request: NextRequest) {
  const password = process.env.DASHBOARD_PASSWORD
  if (!password) return NextResponse.next()

  const { pathname } = request.nextUrl

  // 공개 경로는 인증 없이 통과
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // 쿠키에 저장된 접근 토큰 검증
  const session = request.cookies.get(COOKIE_NAME)
  if (session?.value === password) {
    return NextResponse.next()
  }

  // 인증 실패 → 로그인 페이지로 리다이렉트
  const loginUrl = new URL('/login', request.url)
  loginUrl.searchParams.set('from', pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  // 정적 자산과 이미지 최적화 경로는 미들웨어 제외
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
