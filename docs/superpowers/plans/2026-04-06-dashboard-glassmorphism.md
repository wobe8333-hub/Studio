# KAS 대시보드 Glassmorphism Dark 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KAS 대시보드 전체(8페이지 + 공통 레이어 14개 파일)에 Glassmorphism Dark 디자인을 적용한다.

**Architecture:** `globals.css`에 글래스 CSS 토큰과 유틸리티 클래스를 먼저 정의(다른 모든 파일의 의존성)한 후, `card.tsx`에 자동 적용하여 8페이지가 동시에 변경되도록 하고, 페이지별 상태 기반 글로우(HIGH 리스크, 승리 패턴, 쿼터 경고)를 순차 추가한다. `:root`(라이트 모드) 토큰은 건드리지 않고 `.dark` 토큰만 수정한다.

**Tech Stack:** Next.js 16.2.2 · React 19 · Tailwind CSS v4 (CSS-first, `globals.css` 단일 설정) · shadcn/ui · motion/react · Recharts 3

---

### Task 1: globals.css — 다크 토큰 교체 + 글래스 유틸리티 추가

**Files:**
- Modify: `web/app/globals.css`

**주의:** `:root` 블록(라이트 모드)은 건드리지 않는다. `.dark` 블록과 `@layer utilities` 블록만 수정한다.

- [ ] **Step 1: `.dark` 배경·카드·사이드바 토큰 교체**

`globals.css`의 `.dark { ... }` 블록 상단을 다음으로 교체한다:

```css
.dark {
  /* 배경 — 딥 블루-블랙 (기존 0.14 → 0.07로 더 어둡게) */
  --background: oklch(0.07 0.01 240);
  --foreground: oklch(0.95 0.005 85);
  --card: oklch(0.10 0.01 240);
  --card-foreground: oklch(0.95 0.005 85);
  --popover: oklch(0.10 0.01 240);
  --popover-foreground: oklch(0.95 0.005 85);

  /* Primary — 밝은 앰버 (기존 유지) */
  --primary: oklch(0.72 0.17 65);
  --primary-foreground: oklch(0.15 0.02 55);

  --secondary: oklch(0.20 0.015 240);
  --secondary-foreground: oklch(0.92 0.005 85);

  --muted: oklch(0.18 0.015 240);
  --muted-foreground: oklch(0.65 0.02 80);

  --accent: oklch(0.20 0.03 190);
  --accent-foreground: oklch(0.90 0.02 190);

  --destructive: oklch(0.704 0.191 22.216);

  --border: oklch(1 0 0 / 8%);
  --input: oklch(1 0 0 / 12%);
  --ring: oklch(0.72 0.17 65);

  /* 차트 (기존 유지) */
  --chart-1: oklch(0.75 0.18 60);
  --chart-2: oklch(0.70 0.16 175);
  --chart-3: oklch(0.72 0.18 330);
  --chart-4: oklch(0.68 0.14 145);
  --chart-5: oklch(0.65 0.18 280);

  /* 사이드바 */
  --sidebar: oklch(0.09 0.01 240);
  --sidebar-foreground: oklch(0.95 0.005 85);
  --sidebar-primary: oklch(0.72 0.17 65);
  --sidebar-primary-foreground: oklch(0.15 0.02 55);
  --sidebar-accent: oklch(0.18 0.03 55);
  --sidebar-accent-foreground: oklch(0.92 0.03 55);
  --sidebar-border: oklch(1 0 0 / 5%);
  --sidebar-ring: oklch(0.72 0.17 65);

  /* 7채널 고유 색상 (기존 유지) */
  --channel-ch1: oklch(0.75 0.18 60);
  --channel-ch2: oklch(0.70 0.16 175);
  --channel-ch3: oklch(0.72 0.15 25);
  --channel-ch4: oklch(0.70 0.18 310);
  --channel-ch5: oklch(0.65 0.16 280);
  --channel-ch6: oklch(0.68 0.14 145);
  --channel-ch7: oklch(0.68 0.20 15);

  /* ── 글래스 토큰 (신규) ─────────────────────────────── */
  --glass-bg:     rgba(255 255 255 / 0.04);
  --glass-border: rgba(255 255 255 / 0.08);
  --glass-hover:  rgba(255 255 255 / 0.07);
  --glass-blur:   blur(16px) saturate(180%);

  /* ── 글로우 토큰 (신규) ─────────────────────────────── */
  --glow-primary: rgba(245 158 11 / 0.25);
  --glow-success: rgba(34 197 94 / 0.20);
  --glow-danger:  rgba(239 68 68 / 0.20);

  /* ── 헤더 그라데이션 바 (신규) ──────────────────────── */
  --gradient-bar: linear-gradient(90deg, #f59e0b 0%, #ef4444 25%, #8b5cf6 60%, #06b6d4 100%);
}
```

- [ ] **Step 2: `@layer utilities` 블록에 글래스 유틸리티 추가**

기존 `@layer utilities { ... }` 블록의 닫는 `}` 앞에 다음을 추가한다:

```css
  /* ─── 글래스 카드 (다크 모드만 활성) ─────────────────────────────────── */
  .dark .glass-card {
    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-color: var(--glass-border);
    box-shadow: 0 4px 24px rgba(0 0 0 / 0.35),
                inset 0 1px 0 rgba(255 255 255 / 0.06);
  }
  .dark .glass-card:hover {
    background: var(--glass-hover);
    border-color: rgba(255 255 255 / 0.12);
  }

  /* ─── 상태 기반 글로우 (다크 모드만 활성) ────────────────────────────── */
  .dark .glow-amber {
    box-shadow: 0 0 20px var(--glow-primary),
                0 0 0 1px rgba(245 158 11 / 0.15);
  }
  .dark .glow-success {
    box-shadow: 0 0 20px var(--glow-success),
                0 0 0 1px rgba(34 197 94 / 0.12);
  }
  .dark .glow-danger {
    box-shadow: 0 0 20px var(--glow-danger),
                0 0 0 1px rgba(239 68 68 / 0.15);
  }

  /* ─── 앰비언트 글로우 배경 (다크 모드만 활성) ───────────────────────── */
  .dark .ambient-bg::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 40% at 80% 15%, rgba(245 158 11 / 0.07) 0%, transparent 60%),
      radial-gradient(ellipse 50% 40% at 15% 80%, rgba(139 92 246 / 0.05) 0%, transparent 60%);
    pointer-events: none;
    z-index: -1;
  }

  /* ─── backdrop-filter 미지원 환경 폴백 ───────────────────────────────── */
  @supports not (backdrop-filter: blur(1px)) {
    .dark .glass-card {
      background: oklch(0.13 0.01 240);
      box-shadow: 0 4px 24px rgba(0 0 0 / 0.3);
    }
  }
```

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

Expected: `Route (app)` 목록 출력, TypeScript 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd web && cd .. && git add web/app/globals.css
git commit -m "style: 다크 배경 토큰 딥 다크 교체 + 글래스·글로우·앰비언트 유틸리티 추가"
```

---

### Task 2: ui/card.tsx — 글래스 카드 클래스 자동 적용

**Files:**
- Modify: `web/components/ui/card.tsx`

- [ ] **Step 1: Card 컴포넌트 기본 className에 `glass-card` 추가**

`web/components/ui/card.tsx`의 `Card` 함수에서 `cn(...)` 첫 번째 인자를 수정한다.

변경 전:
```tsx
"group/card flex flex-col gap-4 overflow-hidden rounded-xl bg-card py-4 text-sm text-card-foreground ring-1 ring-foreground/10 has-data-[slot=card-footer]:pb-0 ..."
```

변경 후 (첫 번째 인자 문자열에 `glass-card` 추가):
```tsx
function Card({
  className,
  size = "default",
  ...props
}: React.ComponentProps<"div"> & { size?: "default" | "sm" }) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        "group/card flex flex-col gap-4 overflow-hidden rounded-xl bg-card py-4 text-sm text-card-foreground ring-1 ring-foreground/10 glass-card has-data-[slot=card-footer]:pb-0 has-[>img:first-child]:pt-0 data-[size=sm]:gap-3 data-[size=sm]:py-3 data-[size=sm]:has-data-[slot=card-footer]:pb-0 *:[img:first-child]:rounded-t-xl *:[img:last-child]:rounded-b-xl",
        className
      )}
      {...props}
    />
  )
}
```

`glass-card`를 `ring-1 ring-foreground/10` 뒤에 추가했다. 다크 모드에서 `.dark .glass-card`가 `box-shadow`를 override하므로 ring이 글래스 그림자로 교체된다.

- [ ] **Step 2: 빌드 + 시각 확인**

```bash
cd web && npm run build
```

`npm run dev` 후 브라우저에서 다크 모드 전환 → 모든 카드에 blur + 반투명 배경 + 상단 인셋 하이라이트가 보여야 한다.

- [ ] **Step 3: 커밋**

```bash
git add web/components/ui/card.tsx
git commit -m "style: Card 컴포넌트에 glass-card 클래스 추가 — 전체 8페이지 자동 적용"
```

---

### Task 3: layout.tsx — 그라데이션 헤더 바 + 글래스 헤더

**Files:**
- Modify: `web/app/layout.tsx`

- [ ] **Step 1: SidebarInset 안에 그라데이션 바 삽입 + 헤더 강화**

`web/app/layout.tsx`의 `<SidebarInset>` 블록을 다음으로 교체한다:

```tsx
<SidebarInset>
  {/* 최상단 2px 멀티 그라데이션 바 */}
  <div
    className="h-[2px] w-full shrink-0"
    style={{ background: 'var(--gradient-bar)' }}
  />
  <header className="flex h-14 shrink-0 items-center gap-2 border-b border-white/[0.06] px-4 bg-background/70 backdrop-blur-xl sticky top-0 z-10">
    <SidebarTrigger className="-ml-1" />
    <Separator orientation="vertical" className="mr-2 h-4" />
    <div className="flex flex-1 items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-sm font-heading font-semibold text-foreground">
          KAS Studio
        </span>
        <Badge
          variant="outline"
          className="text-[10px] font-mono border-primary/30 text-primary px-1.5 py-0"
        >
          LIVE
        </Badge>
        <RealtimePipelineStatus />
      </div>
      <ThemeToggle />
    </div>
  </header>
  <main className="flex-1 overflow-auto p-4 md:p-6">
    {children}
  </main>
</SidebarInset>
```

변경 포인트:
- `<div className="h-[2px] ..." style={{ background: 'var(--gradient-bar)' }} />` 신규 추가
- `header` className: `border-border/60 bg-background/80 backdrop-blur-sm` → `border-white/[0.06] bg-background/70 backdrop-blur-xl`

- [ ] **Step 2: 빌드 확인**

```bash
cd web && npm run build
```

`npm run dev` 후 다크 모드에서 최상단에 앰버→빨강→바이올렛→시안 2px 그라데이션 바가 보여야 한다.

- [ ] **Step 3: 커밋**

```bash
git add web/app/layout.tsx
git commit -m "style: 헤더 상단 멀티 그라데이션 바 + backdrop-blur-xl 강화"
```

---

### Task 4: sidebar-nav.tsx — 사이드바 글래스 + 채널 dot 글로우

**Files:**
- Modify: `web/components/sidebar-nav.tsx`

- [ ] **Step 1: SidebarHeader에 backdrop-blur 추가**

`AppSidebar` 함수 내 `<SidebarHeader>` className 수정:

```tsx
<SidebarHeader className="border-b border-white/[0.05] px-4 py-3 backdrop-blur-xl">
```

기존: `"border-b border-sidebar-border/60 px-4 py-3"`

- [ ] **Step 2: 채널 dot에 글로우 box-shadow 추가**

`channels.map()` 내부 채널 dot `<span>` 요소의 `style` prop에 `boxShadow` 추가:

```tsx
<span
  className={cn(
    'h-2.5 w-2.5 rounded-full shrink-0',
    'ring-1 ring-inset ring-black/10 dark:ring-white/10'
  )}
  style={{
    backgroundColor: CHANNEL_COLORS[ch.id] ?? 'var(--muted-foreground)',
    boxShadow: `0 0 6px ${CHANNEL_COLORS[ch.id] ?? 'transparent'}`,
  }}
/>
```

기존 `style={{ backgroundColor: CHANNEL_COLORS[ch.id] ?? 'var(--muted-foreground)' }}`에 `boxShadow` 추가.

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add web/components/sidebar-nav.tsx
git commit -m "style: 사이드바 헤더 blur + 채널 dot 글로우 추가"
```

---

### Task 5: home-charts.tsx — 차트 글로우 효과

**Files:**
- Modify: `web/components/home-charts.tsx`

- [ ] **Step 1: Sparkline Area에 drop-shadow 필터 추가**

`Sparkline` 컴포넌트의 `<Area>` 요소에 `style` prop 추가:

```tsx
<Area
  type="monotone"
  dataKey="v"
  stroke={color}
  fill={`url(#sparkGrad-${color.replace(/[^a-zA-Z0-9]/g, '')})`}
  strokeWidth={1.5}
  dot={false}
  isAnimationActive={false}
  style={{ filter: `drop-shadow(0 0 4px ${color})` }}
/>
```

- [ ] **Step 2: RadialGauge 래퍼 div에 drop-shadow 추가**

`RadialGauge` 컴포넌트의 반환부 외부 `<div>` 수정:

```tsx
return (
  <div
    className="h-14 w-14 mx-auto mt-1"
    style={{ filter: `drop-shadow(0 0 6px ${color})` }}
  >
    <ResponsiveContainer width="100%" height="100%">
      <RadialBarChart
        cx="50%"
        cy="80%"
        innerRadius="65%"
        outerRadius="100%"
        startAngle={180}
        endAngle={0}
        data={data}
        barSize={6}
      >
        <RadialBar
          dataKey="value"
          cornerRadius={4}
          background={{ fill: 'var(--muted)' }}
          isAnimationActive={false}
        />
      </RadialBarChart>
    </ResponsiveContainer>
  </div>
)
```

기존 `<div className="h-14 w-14 mx-auto mt-1">`에 `style` prop 추가.

- [ ] **Step 3: ChannelDots 활성 dot 글로우 추가**

`ChannelDots` 컴포넌트의 `<span>` 요소 `style` prop 수정:

```tsx
<span
  key={id}
  title={id}
  className="h-2 w-2 rounded-full transition-opacity"
  style={{
    backgroundColor: isActive
      ? `var(--channel-${id.toLowerCase()})`
      : 'var(--muted-foreground)',
    opacity: isActive ? 1 : 0.3,
    boxShadow: isActive
      ? `0 0 5px var(--channel-${id.toLowerCase()})`
      : 'none',
  }}
/>
```

기존 `style`에 `boxShadow` 조건부 추가.

- [ ] **Step 4: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 5: 커밋**

```bash
git add web/components/home-charts.tsx
git commit -m "style: Sparkline·RadialGauge·ChannelDots drop-shadow 글로우 추가"
```

---

### Task 6: animated-sections.tsx — Spring 물리 전환

**Files:**
- Modify: `web/components/animated-sections.tsx`

- [ ] **Step 1: StaggerItem에 spring 전환 적용**

`StaggerItem` 함수를 다음으로 교체:

```tsx
export function StaggerItem({ children, className }: ContainerProps) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { type: 'spring', stiffness: 260, damping: 20 },
        },
      }}
    >
      {children}
    </motion.div>
  )
}
```

변경: `{ duration: 0.4, ease: 'easeOut' }` → `{ type: 'spring', stiffness: 260, damping: 20 }`

- [ ] **Step 2: AnimatedCard에 spring 전환 + 호버 강화**

`AnimatedCard` 함수를 다음으로 교체:

```tsx
export function AnimatedCard({ children, className, delay = 0 }: AnimatedCardProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 260, damping: 20, delay }}
      whileHover={{ y: -3, transition: { duration: 0.18 } }}
    >
      {children}
    </motion.div>
  )
}
```

변경: `{ duration: 0.4, delay, ease: 'easeOut' }` → spring, `y: -2` → `y: -3`.

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add web/components/animated-sections.tsx
git commit -m "style: StaggerItem·AnimatedCard spring 물리 진입 애니메이션 적용"
```

---

### Task 7: page.tsx (홈) — 앰비언트 배경 + dot 글로우

**Files:**
- Modify: `web/app/page.tsx`

**참고:** `ChannelCard`의 `border-l-[3px]`와 `borderLeftColor: channelColorVar`는 이미 구현되어 있다. 이 Task는 ambient 배경과 dot 글로우만 추가한다.

- [ ] **Step 1: 루트 div에 ambient-bg 클래스 추가**

`HomePage` 반환부 루트 `<div>` className 수정:

```tsx
<div className="relative space-y-6 ambient-bg overflow-hidden">
```

기존: `"relative space-y-6"`

- [ ] **Step 2: ChannelCard 내부 채널 dot span에 글로우 추가**

`ChannelCard` 함수 내 채널 dot `<span>` 요소 수정 (line 295~298):

```tsx
<span
  className="h-2.5 w-2.5 rounded-full shrink-0 ring-1 ring-inset ring-black/10 dark:ring-white/10"
  style={{
    backgroundColor: channelColorVar,
    boxShadow: isActive ? `0 0 7px ${channelColorVar}` : 'none',
  }}
/>
```

기존 `style={{ backgroundColor: channelColorVar }}`에 `boxShadow` 추가.

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add web/app/page.tsx
git commit -m "style: 홈 페이지 앰비언트 배경 + 채널 카드 dot 글로우 추가"
```

---

### Task 8: risk/page.tsx — 상태 기반 글로우 카드

**Files:**
- Modify: `web/app/risk/page.tsx`

- [ ] **Step 1: HIGH/LOW 요약 카드에 조건부 글로우 추가**

`RiskPage` 반환부 요약 카드 섹션에서 HIGH 카드와 LOW 카드 `className` 수정:

```tsx
{/* HIGH 리스크 카드 */}
<Card className="glow-danger">
  <CardHeader className="flex flex-row items-center justify-between pb-2">
    <CardTitle className="text-sm font-medium">HIGH 리스크</CardTitle>
    <AlertTriangle className="h-4 w-4 text-destructive" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold text-destructive">{highRiskChannels.length}</div>
    <p className="text-xs text-muted-foreground mt-1">즉각 조치 필요</p>
  </CardContent>
</Card>

{/* LOW 리스크 카드 */}
<Card className="glow-success">
  <CardHeader className="flex flex-row items-center justify-between pb-2">
    <CardTitle className="text-sm font-medium">LOW 리스크</CardTitle>
    <CheckCircle className="h-4 w-4 text-green-500" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold text-green-500">{lowRiskChannels.length}</div>
    <p className="text-xs text-muted-foreground mt-1">정상 범위</p>
  </CardContent>
</Card>
```

- [ ] **Step 2: 리스크 히트맵 셀에 글래스 스타일 적용**

`riskData.map()` 내부 `<div>` className에서 기존 단색 bg를 글래스 스타일로 교체:

```tsx
{riskData.map((r) => (
  <div
    key={r.channel_id}
    className={`rounded-lg p-4 text-center border ${
      r.risk_level === 'HIGH'
        ? 'bg-red-500/10 border-red-500/25 glow-danger text-red-300'
        : 'bg-green-500/[0.08] border-green-500/20 glow-success text-green-300'
    }`}
  >
    {/* 기존 내용 유지 */}
  </div>
))}
```

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add web/app/risk/page.tsx
git commit -m "style: 리스크 페이지 HIGH/LOW 조건부 글로우 카드 적용"
```

---

### Task 9: learning/page.tsx — 승리 패턴 앰버 글로우

**Files:**
- Modify: `web/app/learning/page.tsx`

- [ ] **Step 1: WIN_PATTERNS 카드에 앰버 글로우 추가**

`learning/page.tsx`에서 `WIN_PATTERNS`를 렌더링하는 `<Card>`를 찾아 className에 `glow-amber` 추가:

```tsx
<Card className="glow-amber">
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      <Brain className="h-5 w-5 text-primary" />
      승리 패턴 가이드라인
    </CardTitle>
    <CardDescription>누적 데이터 기반 최적화 지침</CardDescription>
  </CardHeader>
  <CardContent>
    {/* 기존 테이블/내용 유지 */}
  </CardContent>
</Card>
```

- [ ] **Step 2: 페이지 루트에 ambient-bg 추가**

최상위 `<div className="space-y-6">` 또는 `<div className="...">` 를 찾아:

```tsx
<div className="relative space-y-6 ambient-bg overflow-hidden">
```

- [ ] **Step 3: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add web/app/learning/page.tsx
git commit -m "style: 학습 페이지 승리 패턴 앰버 글로우 + 앰비언트 배경 추가"
```

---

### Task 10: cost/page.tsx — 쿼터 진행바 그라데이션 + 경고 글로우

**Files:**
- Modify: `web/app/cost/page.tsx`

- [ ] **Step 1: shadcn Progress를 커스텀 그라데이션 진행바로 교체하는 헬퍼 추가**

`CostPage` 함수 바깥(상단)에 헬퍼 컴포넌트 추가:

```tsx
function GradientProgress({
  value,
  max,
  gradient,
  glowColor,
}: {
  value: number
  max: number
  gradient: string
  glowColor: string
}) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="relative mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{
          width: `${pct}%`,
          background: gradient,
          boxShadow: `0 0 8px ${glowColor}`,
        }}
      />
    </div>
  )
}
```

- [ ] **Step 2: Gemini 쿼터 Progress를 GradientProgress로 교체**

`cost/page.tsx`에서 Gemini 쿼터를 표시하는 `<Progress ... />` 를 찾아 교체. `quota` 상태 배열에서 `gemini` 서비스를 찾아 사용:

```tsx
{(() => {
  const geminiQuota = quota.find((q) => q.service === 'gemini') ?? DEFAULT_QUOTA[0]
  return (
    <GradientProgress
      value={geminiQuota.quota_used}
      max={GEMINI_DAILY_IMAGE_LIMIT}
      gradient="linear-gradient(90deg, #818cf8, #a78bfa)"
      glowColor="rgba(139, 92, 246, 0.5)"
    />
  )
})()}
```

- [ ] **Step 3: YouTube 쿼터 카드에 경고 글로우 + 그라데이션 진행바 적용**

YouTube 쿼터를 표시하는 `<Card>` 의 className에 조건부 `glow-danger` 추가, `<Progress>` 를 `<GradientProgress>`로 교체:

```tsx
{(() => {
  const ytQuota = quota.find((q) => q.service === 'youtube')
  const ytUsed = ytQuota?.quota_used ?? 0
  const ytRate = ytUsed / YOUTUBE_DAILY_QUOTA
  return (
    <Card className={cn(ytRate >= 0.8 && 'glow-danger')}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">YouTube API</CardTitle>
        <PlayCircle
          className={cn('h-4 w-4', ytRate >= 0.8 ? 'text-destructive' : 'text-muted-foreground')}
        />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">{ytUsed.toLocaleString()}</div>
        <p className="text-xs text-muted-foreground mt-1">/ {YOUTUBE_DAILY_QUOTA.toLocaleString()} 단위</p>
        <GradientProgress
          value={ytUsed}
          max={YOUTUBE_DAILY_QUOTA}
          gradient={
            ytRate >= 0.8
              ? 'linear-gradient(90deg, #ef4444, #f87171)'
              : 'linear-gradient(90deg, #f59e0b, #fbbf24)'
          }
          glowColor={
            ytRate >= 0.8 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(245, 158, 11, 0.4)'
          }
        />
        {ytRate >= 0.8 && (
          <p className="text-xs text-destructive mt-1">⚠ 임계값 근접</p>
        )}
      </CardContent>
    </Card>
  )
})()}
```

- [ ] **Step 4: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 5: 커밋**

```bash
git add web/app/cost/page.tsx
git commit -m "style: 비용 페이지 쿼터 그라데이션 진행바 + YouTube 경고 글로우 추가"
```

---

### Task 11: trends/page.tsx — 승인/거부 버튼 글로우

**Files:**
- Modify: `web/app/trends/page.tsx`

- [ ] **Step 1: 승인 버튼에 초록 호버 글로우 추가**

`trends/page.tsx`에서 승인 버튼을 찾아 className에 호버 글로우 추가:

```tsx
{/* 승인 버튼 */}
<Button
  size="sm"
  className="bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
  onClick={() => handleApprove(topic.id)}
>
  승인
</Button>

{/* 거부 버튼 */}
<Button
  size="sm"
  variant="outline"
  className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:shadow-[0_0_12px_rgba(239,68,68,0.25)] transition-shadow"
  onClick={() => handleReject(topic.id)}
>
  거부
</Button>
```

- [ ] **Step 2: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 3: 커밋**

```bash
git add web/app/trends/page.tsx
git commit -m "style: 트렌드 페이지 승인/거부 버튼 글로우 호버 효과 추가"
```

---

### Task 12: revenue/page.tsx — 총계 카드 초록 tint

**Files:**
- Modify: `web/app/revenue/page.tsx`

- [ ] **Step 1: 총 수익 카드에 초록 tint + 글로우 추가**

`revenue/page.tsx`에서 총 수익(AdSense + 제휴마케팅 합산)을 표시하는 `<Card>`를 찾아 className 수정:

```tsx
<Card className="dark:bg-green-500/[0.07] dark:border-green-500/20 glow-success">
```

- [ ] **Step 2: 빌드 확인**

```bash
cd web && npm run build
```

- [ ] **Step 3: 커밋**

```bash
git add web/app/revenue/page.tsx
git commit -m "style: 수익 페이지 총계 카드 초록 tint + 글로우 적용"
```

---

### Task 13: settings/page.tsx + channels/[id]/page.tsx — 마무리

**Files:**
- Modify: `web/app/settings/page.tsx`
- Modify: `web/app/channels/[id]/page.tsx`

- [ ] **Step 1: settings 페이지 루트 div에 ambient-bg 추가**

`settings/page.tsx`의 최상위 `<div className="space-y-6">` 수정:

```tsx
<div className="relative space-y-6 ambient-bg overflow-hidden">
```

- [ ] **Step 2: channels/[id] 페이지 루트 div에 ambient-bg 추가**

`channels/[id]/page.tsx`의 최상위 `<div className="...">` 수정:

```tsx
<div className="relative space-y-6 ambient-bg overflow-hidden">
```

- [ ] **Step 3: 최종 빌드 확인**

```bash
cd web && npm run build
```

Expected: 빌드 성공, TypeScript 에러 없음. `npm run dev` 후 전체 8페이지 다크 모드에서 글래스 효과 확인.

- [ ] **Step 4: 최종 커밋**

```bash
git add web/app/settings/page.tsx "web/app/channels/[id]/page.tsx"
git commit -m "style: settings·채널 상세 페이지 앰비언트 배경 추가 — 글래스모피즘 리디자인 완료"
```

---

## 스펙 커버리지 체크

| 스펙 요구사항 | Task | 상태 |
|---|---|---|
| globals.css 딥 다크 배경 토큰 | Task 1 | ✓ |
| 글래스 CSS 변수 | Task 1 | ✓ |
| `.glass-card` 유틸리티 | Task 1 | ✓ |
| 글로우 유틸리티 클래스 | Task 1 | ✓ |
| `.ambient-bg` 유틸리티 | Task 1 | ✓ |
| `@supports` 폴백 | Task 1 | ✓ |
| card.tsx 글래스 자동 적용 | Task 2 | ✓ |
| layout.tsx 그라데이션 바 + 글래스 헤더 | Task 3 | ✓ |
| sidebar-nav.tsx 글래스 + dot 글로우 | Task 4 | ✓ |
| home-charts.tsx drop-shadow | Task 5 | ✓ |
| animated-sections.tsx spring | Task 6 | ✓ |
| page.tsx 앰비언트 bg + dot 글로우 | Task 7 | ✓ |
| risk/page.tsx 조건부 글로우 | Task 8 | ✓ |
| learning/page.tsx 승리 패턴 글로우 | Task 9 | ✓ |
| cost/page.tsx 진행바 그라데이션 + 경고 | Task 10 | ✓ |
| trends/page.tsx 버튼 호버 글로우 | Task 11 | ✓ |
| revenue/page.tsx 총계 카드 tint | Task 12 | ✓ |
| settings + channels/[id] ambient | Task 13 | ✓ |
| 라이트 모드 보존 (`:root` 미변경) | Task 1 | ✓ |
