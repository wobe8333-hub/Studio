---
paths:
  - web/**/*
---

### 웹 대시보드 (`web/`)

> **`web/CLAUDE.md`** — 웹 전용 상세 가이드. Route Handler params 패턴, TypeScript null 좁히기, Supabase fallback, Docker/Capacitor 빌드, 미들웨어 제약 등이 기록돼 있다. 웹 작업 시 반드시 읽을 것.

**스택**: Next.js 16.2.2 + React 19 + **Tailwind CSS v4** + shadcn/ui v4 (base-nova) + Recharts 3 + Supabase + **motion** + **next-themes** + **react-intersection-observer**

#### Tailwind CSS v4 주의사항
`tailwind.config.ts` 파일이 **없다** — v4의 CSS-first 방식으로 `app/globals.css`에서 모든 설정 관리.
```css
/* globals.css 구조 */
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@custom-variant dark (&:is(.dark *));   /* class 기반 다크모드 */
@theme inline { /* 디자인 토큰 */ }
:root { /* 라이트 테마 */ }
.dark { /* 다크 테마 */ }
```
새 Tailwind 유틸리티 추가 시 `@layer utilities {}` 블록 사용. PostCSS는 `@tailwindcss/postcss` 단일 플러그인.

#### 디자인 시스템 — Red Light Glassmorphism

`globals.css`에 정의된 현재 팔레트 CSS 변수:
```css
--p1: #FFB0B0;   /* 살구레드 — 강조 */
--p2: #FFD5D5;   /* 연핑크레드 — 배너 배경 */
--p4: #B42828;   /* 딥레드 — 탑바, 사이드바, 버튼 */
--t1: #4a1010;   /* 진한 텍스트 */
--t2: #7a3030;   /* 서브 텍스트 */
--t3: #b06060;   /* 뮤트 텍스트 */
/* 하위 호환 alias: --c-dark(#B42828), --c-red(#e85555) 등 */
```
폰트: **Noto Sans KR** (400/500/600/700/800) — Google Fonts.
페이지 배경: `linear-gradient(135deg, #fff0f0 0%, #ffe0e0 40%, #f8f4f4 100%)`.

클라이언트 컴포넌트에서는 `tailwind` 클래스 대신 인라인 `style` + `CARD_BASE` 상수를 사용한다. **반드시 CSS 변수를 사용**해야 다크모드가 자동 적용된다:
```tsx
const CARD_BASE: React.CSSProperties = {
  background: 'var(--card)',            // 라이트: rgba(255,255,255,0.60) / 다크: rgba(42,16,16,0.80)
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid var(--border)',    // 라이트: rgba(220,80,80,0.18) / 다크: rgba(255,100,100,0.20)
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(180,40,40,0.07)',
}
```
탭/필터 컨테이너 배경: `background: 'var(--tab-bg)', border: '1px solid var(--tab-border)'` 사용.
사이드바/탑바: `background: var(--sidebar)` + `backdropFilter: blur(20px)`. 탑바 텍스트/배지: `color: var(--sidebar-foreground/primary)`.
탭 버튼 활성: `rgba(180,40,40,0.88)` 배경 + 흰 텍스트 / 비활성: `transparent`, `#9b4040`.

#### 다크모드 — Crimson Night 팔레트

`ThemeProvider`는 `defaultTheme="light"`, `enableSystem={false}`. 헤더 우측 `<ThemeToggle />` 버튼으로 전환.

`.dark` 주요 변수 (Crimson Night):
```css
--background: #1a0808;           /* 딥레드 블랙 배경 */
--foreground: #ffdede;           /* 연핑크 텍스트 */
--card:        rgba(42,16,16,0.80);  /* 글래스카드 */
--primary:     #e85555;          /* 버튼/강조 */
--sidebar:     rgba(61,15,15,0.95);  /* 사이드바/탑바 */
--tab-bg:      rgba(42,16,16,0.55);  /* 탭 컨테이너 */
--tab-border:  rgba(255,100,100,0.15);
```
body 다크 그라디언트: `.dark body { background: linear-gradient(135deg, #1a0808 0%, #250d0d 40%, #1e0a0a 100%); }`

#### 모바일 반응형

`web/hooks/use-is-mobile.ts`의 `useIsMobile(breakpoint=768)` 훅으로 클라이언트 컴포넌트 내부 레이아웃 분기. 레이아웃 수준(사이드바 숨김·하단 탭)은 CSS 클래스 + `globals.css` 미디어 쿼리로 처리:
```css
/* globals.css */
.kas-bottom-nav { display: none; }
@media (max-width: 767px) {
  .kas-sidebar { display: none !important; }
  .kas-bottom-nav { display: flex !important; }
  .kas-content { padding-bottom: 68px !important; }
}
```
`web/components/bottom-nav.tsx` — 모바일 전용 하단 탭 바 (홈·트렌드·수익·QA·런 5개 항목).
`web/capacitor.config.ts` — Capacitor 모바일 앱 설정 파일 존재. `appId: com.kas.studio`, `webDir: out`.

**`web/next.config.ts` output 모드 전환**: 배포 대상에 따라 `output` 값이 달라진다.
- `'standalone'` (현재 기본값) — Docker 배포용
- 없음(삭제) — Vercel 배포용 (`web/vercel.json` regions: `icn1` 설정됨)
- `'export'` — Capacitor 모바일 앱 빌드용 (`npx cap sync` 전 필수)

#### 디렉토리 구조

```
web/
├── app/
│   ├── layout.tsx          — CollapsibleSidebar + 탑바(var(--sidebar) glass) + ThemeToggle + BottomNav + ThemeProvider
│   ├── page.tsx            — 서버 컴포넌트: KpiBanner + HomeExecTab(경영/운영 탭 컨트롤러)
│   ├── home-exec-tab.tsx   — 경영 탭 (KPI 카드 4개, 채널 목표 진행 바, 6개월 차트, 채널 카드 7개)
│   ├── home-ops-tab.tsx    — 운영 탭 (파이프라인 스텝 현황, HITL 신호, 파이프라인 제어 버튼)
│   ├── globals.css         — Tailwind v4 설정 + Red Light Glassmorphism 팔레트 + 모바일 미디어 쿼리
│   ├── channels/[id]/      — 채널 상세 (클라이언트)
│   ├── trends/             — 트렌드 주제 관리 (클라이언트, 채널탭 + 승인/거부/필터)
│   ├── revenue/            — 수익 추적 (클라이언트, 이번달/월별추세 2탭)
│   ├── risk/               — 리스크 모니터링 (서버 컴포넌트)
│   │   └── sustainability-section.tsx  — 클라이언트 컴포넌트 분리 예시 (서버 페이지 내 클라이언트 탭)
│   ├── learning/           — 학습 피드백 (KPI/알고리즘/바이어스 3탭)
│   ├── cost/               — 비용/쿼터 추적 (쿼터현황/예측vs실제/이연업로드 3탭)
│   ├── monitor/            — 파이프라인 실시간 모니터링 (폴링 기반)
│   ├── runs/[channelId]/[runId]/ — Run 상세 (10탭: 이미지/영상/Shorts/나레이션/BGM/썸네일/제목/QA/메타/로그)
│   ├── runs/[channelId]/   — 채널별 Run 목록 (클라이언트, 홈 채널 카드 링크 대상)
│   ├── qa/                 — QA 결과 관리
│   ├── knowledge/          — 지식 수집 현황 (단계별 배지)
│   └── settings/           — 설정 (읽기 전용)
├── components/
│   ├── kpi-banner.tsx        — KPI 배너 (이번달 수익/달성률/활성채널/총Runs/HITL 대기, 항상 고정)
│   ├── bottom-nav.tsx        — 모바일 전용 하단 탭 바 (홈·트렌드·수익·QA·런)
│   ├── sidebar-nav.tsx       — CollapsibleSidebar: 44px↔160px 토글, 경영/운영 섹션 분류, kas-sidebar 클래스
│   ├── animated-sections.tsx — motion 래퍼: StaggerContainer/StaggerItem/ScrollReveal/AnimatedCard
│   ├── home-charts.tsx       — Recharts 클라이언트 컴포넌트: Sparkline/RadialGauge/ChannelDots
│   ├── theme-toggle.tsx      — next-themes useTheme (mounted 패턴으로 hydration mismatch 방지)
│   ├── realtime-pipeline-status.tsx — Supabase Realtime 구독으로 파이프라인 상태 자동 갱신 (폴링 없음)
│   └── ui/                   — shadcn/ui 컴포넌트 (16개)
├── hooks/
│   └── use-is-mobile.ts      — useIsMobile(breakpoint=768): SSR-safe 모바일 감지 훅
└── lib/
    ├── supabase/
    │   ├── client.ts         — 브라우저용 (createBrowserClient)
    │   ├── server.ts         — 서버용 (createServerClient + cookies)
    │   └── server-admin.ts   — service_role 전용 (RLS 우회, 서버에서만 사용)
    ├── fs-helpers.ts         — 경로 보안 유틸리티: validateRunPath / validateChannelPath / getKasRoot / readKasJson / writeKasJson. `RUN_ID_RE`는 `run_CH[1-7]_\d{7,13}` 및 `test_run_\d{1,16}|test_run_\d{3}` 패턴 허용.
    └── types.ts              — Supabase DB 전체 타입 (Database, Channel, PipelineRun 등)
```

**홈 페이지 구조**: `page.tsx`(서버) → `KpiBanner`(항상 고정) + `HomeExecTab`(탭 컨트롤러). `HomeExecTab`은 활성 탭에 따라 자체 콘텐츠(경영) 또는 `<HomeOpsTab />`(운영)을 렌더링.

**운영 탭 API 형식**: `/api/pipeline/steps`는 `{ active: boolean, steps: [{ index: 0, name: string, status: 'idle'|'running'|'done'|'error'|'skipped', elapsed_ms?: number }] }` 반환. `index` 0~7이 Step05~12에 대응.

**운영 탭 파이프라인 제어 버튼** (`home-ops-tab.tsx`):
- 실제 파이프라인 실행 (`dry_run: false`) — `window.confirm()` 경고 후 실행. `python -m src.pipeline 1`과 동일하며 Gemini API 크레딧 소모.
- DRY RUN (`dry_run: true`) — 시뮬레이션. 실제 API 호출 없이 스텝 시뮬레이션. `runs/{chId}/{runId}/manifest.json` 생성 → 런 목록에 즉시 표시됨.
- 스텝 초기화 — `DELETE /api/pipeline/steps` → `step_progress.json` 초기화 + frozen 해제.

**DRY RUN 트리거 동작** (`/api/pipeline/trigger`): `dry_run: true` 요청 시 `runs/{chId}/{runId}/manifest.json` 파일을 실제로 생성한다(run_state: RUNNING). Step 완료 시 run_state가 COMPLETED로 갱신됨.

**Run 상세 `RunArtifacts` 인터페이스** (`/api/runs/[ch]/[id]`):
- `manifest.dry_run?: boolean` — DRY RUN 여부
- `step08.hook_text: string | null` — `script.json`의 `hook` 필드. 문자열 또는 `{text: string}` 객체 모두 파싱.
- `step08.narration_ext: 'wav' | 'mp3'` — `.wav` 우선, 없으면 `.mp3` 폴백.
- `step08.video_filename: string` — 우선순위: `video_narr.mp4 > video.mp4 > video_subs.mp4`. `final.mp4`는 존재하지 않음.
- `step08.image_paths: string[]` — **step08 디렉토리 기준 상대경로** (`images/assets_ai/xxx.png`). 프론트엔드에서 `/api/artifacts/{ch}/{run}/step08/${img}` 형태로 조합.

**채널별 Run 목록 API** (`/api/runs/[channelId]`): `run_*` 및 `test_run_*` 두 패턴 모두 포함. `manifest.json`이 없는 `test_run_*`은 `qa_result.json` 타임스탬프 또는 디렉토리 생성 시간을 `created_at`으로 사용.

**API 라우트** (`app/api/`): `artifacts/[...path]`(파일 서빙), `agents/status`, `agents/run`, `cost/projection`, `deferred-jobs`, `hitl-signals`, `knowledge`, `learning/algorithm|kpi`, `pipeline/logs|preflight|preview|status|steps|trigger`, `qa-data`, `runs/[ch]`(채널별 Run 목록), `runs/[ch]/[id]`, `runs/[ch]/[id]/bgm|seo|shorts`, `sustainability`

**서버 컴포넌트 내 클라이언트 탭 분리 패턴**: 서버 컴포넌트 페이지에 `'use client'`를 붙일 수 없을 때, 클라이언트 로직이 필요한 섹션을 별도 파일로 분리 후 import. `risk/sustainability-section.tsx`가 참조 구현이다.

#### 애니메이션 패턴 (`animated-sections.tsx`)

`page.tsx`는 서버 컴포넌트라 motion 직접 사용 불가 → 클라이언트 래퍼 import:
```tsx
import { StaggerContainer, StaggerItem, AnimatedCard } from '@/components/animated-sections'

// KPI 카드 순차 등장
<StaggerContainer className="grid grid-cols-4 gap-3">
  <StaggerItem><Card>...</Card></StaggerItem>
</StaggerContainer>

// 채널 카드 hover lift + 지연 등장
<AnimatedCard delay={i * 0.06}>
  <ChannelCard />
</AnimatedCard>
```

#### Supabase 연동 패턴

서버 컴포넌트: `lib/supabase/server.ts`의 `createClient()` (async)
```typescript
const supabase = await createClient()
const { data } = await supabase.from('channels').select('*')
```

클라이언트 컴포넌트: `lib/supabase/client.ts`의 `createClient()` (sync, useEffect 내부)

**fallback 패턴**: `NEXT_PUBLIC_SUPABASE_URL`에 `xxxxxxxxxxxx` 포함 시 mock 데이터 사용. Supabase 쿼리 결과가 `never` 타입으로 추론되는 경우 `as any[]` 캐스팅 필요 (알려진 타입 추론 한계).

**사이드바 채널 동기화**: `app/layout.tsx`(서버)에서 Supabase `channels` 조회 → `CollapsibleSidebar` props → 실제 DB 채널명 표시. 미연동 시 폴백.

**Supabase 테이블**: `channels`, `pipeline_runs`, `kpi_48h`, `revenue_monthly`, `risk_monthly`, `sustainability`, `learning_feedback`, `quota_daily`, `trend_topics`. 스키마는 `scripts/supabase_schema.sql` 참고.

`trend_topics` 테이블 주요 컬럼: `channel_id`, `reinterpreted_title`(UNIQUE 복합키), `score`, `grade`(`auto`/`review`/`rejected`/`approved`), `breakdown`(JSONB — `{interest, fit, revenue, urgency}`). UNIQUE 제약은 `(channel_id, reinterpreted_title)` 조합.

**Supabase 클라이언트 선택 규칙**:
- 읽기 전용 서버 컴포넌트 → `lib/supabase/server.ts`의 `createClient()` (anon key, RLS 적용)
- 트렌드 grade 업데이트 등 RLS 우회 필요 → `lib/supabase/server-admin.ts`의 `createAdminClient()` (service_role key, **절대 클라이언트 컴포넌트에서 사용 금지**)

#### 웹 핵심 규칙

- **Recharts**: `page.tsx`는 서버 컴포넌트이므로 Recharts 직접 사용 불가. `home-charts.tsx` 또는 별도 `'use client'` 파일에 격리.
- **다크모드**: `document.documentElement.classList`를 직접 조작하지 말 것. `next-themes`의 `useTheme`/`ThemeProvider` 사용.
- **인라인 스타일**: 색상은 `CARD_BASE` 상수 + CSS 변수(`--p1~4`, `--t1~3`)로 표현. 하드코딩된 `rgba(255,255,255,...)` 사용 금지 — 다크모드에서 흰색 박스가 나타난다.
- **파일 서빙**: `runs/` 결과물은 반드시 `/api/artifacts/[channelId]/[runId]/...` 경로 사용.
- **Supabase 쓰기 작업**: `createAdminClient()` (service_role) 사용. `web/app/trends/actions.ts`가 참조 구현이다.
- **API 경로 보안**: `channelId`/`runId` URL 파라미터를 파일 경로에 사용하는 모든 API 라우트는 반드시 `web/lib/fs-helpers.ts`의 `validateRunPath()` 또는 `validateChannelPath()`를 사용해야 한다.
- **getKasRoot 싱글턴**: 반드시 `import { getKasRoot } from '@/lib/fs-helpers'`로 가져온다. 로컬 정의 금지.
- **Next.js 16 미들웨어**: `web/proxy.ts`가 미들웨어 파일이다. `web/middleware.ts`를 별도로 생성하면 빌드 오류 발생.
- **Next.js 16 params**: `{ params }: { params: Promise<{ channelId: string }> }` 패턴 — 반드시 `await params`로 구조분해.
- **RUN_ID_RE 허용 패턴**: `run_CH[1-7]_\d{7,13}` + `test_run_\d{1,16}` + `test_run_\d{3}`. 새 run 유형 추가 시 `web/lib/fs-helpers.ts`의 `RUN_ID_RE` 업데이트 필수.
- **모바일 반응형**: 레이아웃 수준 변경은 `globals.css` 미디어 쿼리 (`kas-sidebar`, `kas-bottom-nav`, `kas-content` 클래스)로 처리. 컴포넌트 내부 분기는 `useIsMobile()` 훅 사용.
