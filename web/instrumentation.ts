/**
 * Next.js 15+ 계측(instrumentation) 진입점.
 * 서버 사이드 초기화 (Sentry 등)에 사용됩니다.
 *
 * Sentry 통합 시 활성화 방법:
 * 1. `npm install @sentry/nextjs` 실행
 * 2. 아래 주석을 해제
 * 3. NEXT_PUBLIC_SENTRY_DSN 환경 변수 설정
 */
export async function register() {
  // Sentry 설치 후 활성화:
  // if (process.env.NEXT_RUNTIME === 'nodejs') {
  //   await import('./sentry.server.config')
  // }
}

// 요청 에러 캡처 (Sentry 설치 후 활성화)
// export const onRequestError = async (
//   err: unknown,
//   request: { path: string; method: string },
//   context: { routerKind: string; routePath: string; routeType: string }
// ) => {
//   const { captureRequestError } = await import('@sentry/nextjs')
//   captureRequestError(err, request, context)
// }
