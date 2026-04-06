/**
 * Sentry 클라이언트(브라우저) 설정 파일.
 *
 * 활성화 방법:
 * 1. npm install @sentry/nextjs
 * 2. .env.local에 NEXT_PUBLIC_SENTRY_DSN 추가
 * 3. 아래 주석 해제
 *
 * import * as Sentry from '@sentry/nextjs'
 *
 * Sentry.init({
 *   dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
 *   tracesSampleRate: 0.1,
 *   enabled: process.env.NODE_ENV === 'production',
 *   release: process.env.NEXT_PUBLIC_APP_VERSION,
 *   integrations: [],
 * })
 */
