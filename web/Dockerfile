# KAS Studio — Next.js 웹 대시보드 Docker 이미지
# 멀티 스테이지 빌드: 의존성 설치 → 빌드 → 최소 런타임 이미지

FROM node:20-alpine AS base

# ── 1단계: 의존성 설치 ────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ── 2단계: 프로덕션 빌드 ─────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 빌드 시 필요한 환경 변수 (ARG로 전달, 이미지에 포함되지 않음)
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── 3단계: 최소 런타임 이미지 ────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 비루트 사용자 생성 (보안)
RUN addgroup --system --gid 1001 nodejs
RUN adduser  --system --uid 1001 nextjs

# standalone 빌드 결과물 복사
COPY --from=builder /app/public                          ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static     ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# standalone 모드: node server.js로 직접 실행
CMD ["node", "server.js"]
