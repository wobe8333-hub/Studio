# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 이 파일은 `web/` 디렉토리 전용이다. 전체 프로젝트 아키텍처, 디자인 시스템, API 계약, Supabase 패턴은 상위 `/CLAUDE.md`를 참고하라.

---

## 명령어

```bash
# 개발 서버 (localhost:7002)
npm run dev

# 프로덕션 빌드 (TypeScript 타입 검사 포함)
npm run build

# 린팅
npm run lint

# Docker 빌드
docker build -t kas-web .
docker run -p 7002:7002 --env-file .env.local kas-web

# Capacitor — 모바일 앱 빌드 (정적 export 필요: next.config.ts output: 'export')
npx cap sync
npx cap run android
npx cap run ios
```

---

## 아키텍처

### 요청 흐름

```
브라우저 → proxy.ts (미들웨어, 패스워드 인증) → App Router
                                                    ├── 서버 컴포넌트 (page.tsx)
                                                    │     └── Supabase 직접 조회 (lib/supabase/server.ts)
                                                    ├── 클라이언트 컴포넌트 ('use client')
                                                    │     └── /api/* 폴링 or Supabase realtime
                                                    └── API Route (app/api/*/route.ts)
                                                          └── lib/fs-helpers.ts → KAS_ROOT 파일시스템
```

### 데이터 소스 2가지

| 소스 | 용도 | 접근 방법 |
|------|------|----------|
| **파일시스템** (`KAS_ROOT`) | 파이프라인 실행 결과 (`runs/`), 진행 상태, 쿼터 | `lib/fs-helpers.ts` — `readKasJson()`, `validateRunPath()` |
| **Supabase** | 채널 레지스트리, 수익/KPI, 트렌드 주제 | `lib/supabase/{server,client,server-admin}.ts` |

`KAS_ROOT`는 `process.env.KAS_ROOT` 또는 `process.cwd()/..` (web/의 부모 = 프로젝트 루트). 서버 컴포넌트·API 라우트에서만 접근.

### 미들웨어 — proxy.ts

`web/proxy.ts`가 Next.js 16.2.2의 미들웨어다. **`web/middleware.ts`를 별도 생성하면 빌드 오류**("Both middleware file and proxy file detected") 발생. 인증/리다이렉트 수정 시 `proxy.ts`만 편집.

`DASHBOARD_PASSWORD` 미설정 시 인증 전체 비활성화 (개발 기본값).

### Route Handler params

Next.js 16에서 `params`는 `Promise` 타입 — 반드시 `await` 필요:

```typescript
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string }> }
) {
  const { channelId } = await params
  // ...
}
```

### Tailwind CSS v4

`tailwind.config.ts` **파일 없음** — v4 CSS-first 방식. `globals.css`의 `@theme inline {}` 블록에서 모든 토큰 관리. 새 유틸리티는 `@layer utilities {}` 블록에 추가.

### 서버 컴포넌트에서 Recharts 사용 금지

`page.tsx`가 서버 컴포넌트인 경우 Recharts를 직접 import하면 빌드 오류. `'use client'`를 붙인 별도 파일로 분리 (참조: `components/home-charts.tsx`).

### Supabase fallback

`NEXT_PUBLIC_SUPABASE_URL`에 `xxxxxxxxxxxx` 포함 시 mock 데이터 모드. 쿼리 결과가 `never`로 추론될 경우 `as any[]` 캐스팅 필요 (알려진 타입 추론 한계).

### TypeScript null 좁히기

optional chaining으로 조건을 만든 뒤 블록 이후에도 타입이 좁혀지지 않음:

```typescript
// ❌ return 이후에도 data가 null로 추론됨
const hasItems = (data?.items?.length ?? 0) > 0
if (!hasItems) return <Empty />
data.field  // Type error: 'data' is possibly 'null'

// ✅ null을 조건에 명시적으로 포함
if (!data || !hasItems) return <Empty />
data.field  // OK
```

### 파일 서빙 경로

`runs/` 산출물은 `/api/artifacts/[channelId]/[runId]/...` 경로만 사용. `/api/files/` 경로는 존재하지 않음.

---

## 환경 변수 (`web/.env.local`)

| 변수 | 설명 |
|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키 |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role 키 — **서버 전용**, RLS 우회 쓰기 작업용 |
| `DASHBOARD_PASSWORD` | 미설정 시 인증 비활성화 |
| `KAS_ROOT` | 프로젝트 루트 절대 경로 (미설정 시 `process.cwd()/..`) |
| `PYTHON_EXECUTABLE` | Python 실행 파일 경로 (미설정 시 Windows: `py`, 기타: `python3`) |

---

## 배포

- **로컬**: `npm run dev` → `localhost:7002`
- **ngrok 고정 도메인**: `ngrok start kas-studio` → `https://cwstudio.ngrok.app`
- **Docker**: `next.config.ts`의 `output: 'standalone'` 필요
- **Vercel**: `output: 'standalone'` 제거, `vercel.json`의 `icn1` 리전 설정됨
- **Capacitor**: `output: 'export'`로 변경 후 `npx cap sync`
