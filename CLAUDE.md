# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**KAS (Knowledge Animation Studio)** — AI가 트렌드 주제를 자동 발굴하고, 스크립트/이미지/나레이션을 생성하여 YouTube에 업로드하는 7채널 풀 자동화 파이프라인. 채널당 월 200만원, 총 1,400만원/월 수익 목표.

GitHub: `https://github.com/wobe8333-hub/Studio`

7채널: CH1(경제) / CH2(부동산) / CH3(심리) / CH4(미스터리) / CH5(전쟁사) / CH6(과학) / CH7(역사)

## 주요 명령어

```bash
# ── 파이썬 백엔드 ──────────────────────────────────
# 월간 파이프라인 실행 (month_number: 1~12)
python -m src.pipeline 1

# 전체 테스트
pytest tests/ -q

# 단일 테스트 파일 / 함수
pytest tests/test_step05_scorer.py -v
pytest tests/test_step08_sd.py::TestSDGenerator::test_detect_gpu_returns_bool -v

# 환경 점검 (파일럿 전 필수) — API 키, OAuth 토큰, FFmpeg, Gemini 연결 6가지 체크
python scripts/preflight_check.py

# YouTube OAuth 토큰 최초 발급 (채널당 1회, credentials/{CH}_token.json 생성)
python scripts/generate_oauth_token.py --channel CH1

# Supabase 동기화 (파이프라인 완료 후 또는 수동)
python scripts/sync_to_supabase.py           # 전체
python scripts/sync_to_supabase.py channels  # 채널 레지스트리만
python scripts/sync_to_supabase.py revenue   # 수익 데이터만

# ── Sub-Agent 수동 실행 ────────────────────────────
python -c "from src.agents.dev_maintenance import DevMaintenanceAgent; print(DevMaintenanceAgent().run())"
python -c "from src.agents.analytics_learning import AnalyticsLearningAgent; print(AnalyticsLearningAgent().run())"
python -c "from src.agents.ui_ux import UiUxAgent; print(UiUxAgent().run())"
python -c "from src.agents.video_style import VideoStyleAgent; print(VideoStyleAgent().run())"

# Sub-Agent 테스트만 실행
pytest tests/test_agents/ -q

# GPU 패키지 설치 (GPU 환경 한정 — CPU-only/CI 환경에서는 실행 금지)
pip install torch diffusers transformers accelerate safetensors

# ── 웹 프론트엔드 (web/) ───────────────────────────
cd web
npm run dev          # 개발 서버 (localhost:7002)
npm run build        # 프로덕션 빌드 (TypeScript 타입 검사 포함)

# ── ngrok 외부 공개 ────────────────────────────────
# 고정 도메인: https://cwstudio.ngrok.app → localhost:7002
ngrok start kas-studio
```

## 아키텍처

### 전체 데이터 흐름

```
파이프라인 실행 → runs/ JSON 파일
                → scripts/sync_to_supabase.py → Supabase PostgreSQL
                                                      ↓
                                              web/ Next.js 대시보드
                                              (https://cwstudio.ngrok.app)
```

### 파이프라인 오케스트레이션 (`src/pipeline.py`)

`run_monthly_pipeline(month_number)` 실행 흐름:

1. **`_ensure_initialized()`** — `data/global/.initialized` 플래그로 1회만 실행. Step00~04(채널 초기화, 베이스라인, 수익구조, 알고리즘 정책, 포트폴리오) 순차 실행. 개별 실패 허용.
2. **`_run_deferred_uploads()`** — YouTube 쿼터 부족으로 이연된 업로드 재시도 (`youtube_quota.json`의 `deferred_jobs` 배열).
3. **`_run_pending_step13()`** — `data/global/step13_pending/*.json`에서 48시간 경과 항목의 KPI 수집 + 학습 피드백.
4. **채널 루프** — `get_active_channels(month_number)`로 활성 채널 결정:
   - Step05 트렌드+지식 → Step06/07 정책 → Step08 영상 생성 → Step09 BGM → Step10 제목/썸네일 → Step11 QA → Step12 업로드 → Step13 pending 등록
5. **`_run_monthly_reports()`** — Step14(수익), Step16(리스크), Step17(지속성).

**채널 론칭 단계** (`CHANNEL_LAUNCH_PHASE` in config.py):
- month_number=1 → CH1+CH2만 활성
- month_number=2 → CH1~CH4
- month_number=3+ → 전체 7채널

**에러 전략**: fail-and-continue. Step09/10/11 실패는 경고 후 진행. Step08 실패만 해당 주제를 건너뜀.

### Step08 — 핵심 영상 생성 오케스트레이터

`src/step08/__init__.py`의 `run_step08()`이 하나의 영상을 처음부터 끝까지 생성:

1. 스크립트 생성 (`script_generator.py` → Gemini API, KnowledgePackage 연동)
2. 이미지 생성: `sd_generator.py` (SD XL + LoRA, GPU 우선) → 실패 시 `image_generator.py` (Gemini 폴백)
3. 장면 합성: `scene_composer.py` (PIL — 캐릭터+배경+자막바 레이어 합성)
4. 모션 효과: `motion_engine.py` (FFmpeg Ken Burns 팬/줌 → MP4 클립)
5. Manim 애니메이션: `manim_generator.py` (Gemini → LaTeX-free 코드 생성 → subprocess 실행, 타임아웃 120초)
6. 나레이션 (`narration_generator.py`: ElevenLabs → gTTS 폴백)
7. 자막 (`subtitle_generator.py`: Faster-Whisper → 균등분배 폴백, 한 줄 40자 제한)
8. FFmpeg 합성 (`ffmpeg_composer.py`: 클립 concat → 나레이션 → 자막)
9. 메타데이터 생성 (`metadata_generator.py`: Gemini → SEO 태그 15개)
10. SHA-256 무결성 검증 → `artifact_hashes.json`

캐릭터는 `character_manager.py`에서 채널별 프로파일(base_prompt, seed, LoRA) 관리. 결과물은 `runs/{channel_id}/{run_id}/step08/` 에 저장.

**Step08s** (`src/step08_s/shorts_generator.py`): Long-form 1편에서 60초 Shorts 3편 자동 추출. FFmpeg 중앙 크롭 1920×1080 → 1080×1920 (9:16).

**주의**: `src/step08/__init__.py`는 **KAS-PROTECTED** 파일이다. 248줄의 오케스트레이터이며 일반적인 `__init__.py`가 아니다. 내용을 비우거나 일괄 초기화 스크립트 대상에서 반드시 제외해야 한다.

### Step05 — 트렌드+지식 수집

**트렌드 수집** (`trend_collector.py`): 5계층 소스 오케스트레이션
- Layer 1~2: `sources/google_trends.py`, `sources/naver.py`, `sources/youtube_trending.py`
- Layer 3~4: `sources/reddit.py`, `sources/arxiv.py`, `sources/scholar.py`
- Layer 5: `sources/wikipedia.py`, `sources/curated.py`
- 점수화: `scorer.py` (관심도 40% + 적합도 25% + 수익성 20% + 긴급도 15%)
- **grade 임계값**: 80점+ → `auto`, 60~79 → `review`, <60 → `rejected`

**소스별 fallback 동작** (API 미설정/오류 시):
- Google Trends 429 Rate Limit → `sources/google_trends.py`의 `_KEYWORD_BASELINES` 딕셔너리에서 키워드별 베이스라인 점수(0.55~0.92) 자동 사용
- YouTube search.list `relevanceLanguage` 파라미터 사용 금지 — 400 오류 발생함
- Reddit(`praw`) 미설치 시 → `news_score * 0.6`을 community_score proxy로 사용

**수동 트렌드 재수집 워크플로우**:
```bash
# 1. 수집 + knowledge_store 저장
python -c "
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge
for ch, cat in [('CH1','economy'),('CH2','realestate')]:
    scored = collect_trends(ch, cat, limit=10)
    topics = [reinterpret_trend(s, cat, ch) for s in scored if s['grade'] in ('auto','review')]
    save_knowledge(ch, topics)
"
# 2. Supabase 동기화
python scripts/sync_to_supabase.py
```

**지식 수집** (`knowledge/`): 3단계 파이프라인
- Stage 1: Tavily AI Search + Perplexity API + Gemini Deep Research
- Stage 2: Wikipedia + Semantic Scholar + Naver API 구조화
- Stage 3: Gemini/Claude 팩트체크 + 카테고리별 보강 (FRED, 실거래가, NASA 등)

### 데이터 흐름 — SSOT 원칙

모든 JSON I/O는 **반드시 `src/core/ssot.py`의 `read_json()` / `write_json()`을 사용**해야 한다.

- `write_json()`: `filelock` + **atomic write** (tempfile → `os.replace`) + `ensure_ascii=True` (PowerShell 5.1 호환용 `\uXXXX` 이스케이프)
- `read_json()`: `encoding="utf-8-sig"` (BOM 처리)

```
data/global/                        — 채널 레지스트리, 쿼터 정책, 메모리 스토어
data/global/notifications/          — Sub-Agent 알림 (notifications.json, hitl_signals.json)
data/channels/CH*/                  — 채널별 algorithm/revenue/style 정책 JSON
data/knowledge_store/               — KnowledgePackage JSON
runs/CH*/run_*/                     — 실행별 결과물 (manifest.json, step08/, step09/ 등)
logs/                               — pipeline.log (loguru, 50MB rotation)
```

### Sub-Agent 시스템 (`src/agents/`)

**원칙**: 기존 파이프라인(Step00~17)을 수정하지 않고, 수동 고통점만 자동화. JSON 결과물을 읽어 정책만 업데이트하는 비침습적 설계.

```
src/agents/
  base_agent.py                  — BaseAgent: root/runs_dir/data_dir 경로 초기화, _log_start/_log_done
  dev_maintenance/
    __init__.py                  — DevMaintenanceAgent: 파이프라인 실패 감지 + 헬스체크 + HITL 신호
    log_monitor.py               — find_failed_runs(): runs/*/manifest.json FAILED 스캔
    health_checker.py            — run_tests(): pytest subprocess 실행
    schema_validator.py          — find_missing_types(): SQL↔types.ts 불일치 감지
    hitl_signal.py               — emit_hitl_signal(): hitl_signals.json 기록
  analytics_learning/
    __init__.py                  — AnalyticsLearningAgent: KPI 분석 + 패턴 추출 + Phase 승격 + A/B
    kpi_analyzer.py              — compute_algorithm_stage(): 4단계 판정
    pattern_extractor.py         — is_winning() (CTR≥6.0% AND AVP≥50.0%), update_winning_patterns()
    phase_promoter.py            — promote_if_eligible(): 단방향 승격만 허용
    ab_selector.py               — select_winner(): curiosity→authority→benefit 우선순위
    notifier.py                  — record_phase_promotion(): notifications.json 기록
  ui_ux/
    __init__.py                  — UiUxAgent: 스키마 변경 감지 → types.ts 자동 동기화
    schema_watcher.py            — has_schema_changed(): SHA-256 해시 비교
    type_syncer.py               — generate_ts_interface(): SQL→TypeScript 변환 (_to_pascal_case)
  video_style/
    __init__.py                  — VideoStyleAgent: 캐릭터 드리프트 감지 + Manim fallback 모니터링
    character_monitor.py         — check_character_drift(): 드리프트 임계값 0.7
    style_optimizer.py           — check_manim_fallback_rate(): 경고 임계값 0.5
```

**BaseAgent 패턴** — 모든 Agent가 따라야 하는 규칙:
```python
class MyAgent(BaseAgent):
    def __init__(self, root: Optional[Path] = None):
        super().__init__("AgentName")
        if root is not None:   # if root: 금지 — Path는 항상 truthy
            self.root = root
            self.data_dir = root / "data"

    def run(self) -> dict[str, Any]:   # 반드시 dict[str, Any] 반환
        ...
```

**알림/HITL 신호 파일**:
- `data/global/notifications/notifications.json` — Phase 승격 알림 (`type: "phase_promotion"`, `read: false`)
- `data/global/notifications/hitl_signals.json` — 운영자 확인 필요 신호 (`type: "pipeline_failure"|"pytest_failure"`, `resolved: false`)

**HITL 자동/수동 분기**:
- 자동 처리: 스키마 불일치 → UiUxAgent 위임, Phase 승격 → 알림만 기록
- 운영자 확인: FAILED 실행 1건 이상, pytest 실패

### Step10 — 썸네일 생성 (PIL 합성)

`src/step10/thumbnail_generator.py`는 Gemini 이미지 생성을 **완전히 제거**하고 PIL 4레이어 합성으로 교체됐다.

**베이스 템플릿**: `assets/thumbnails/CH{1-7}_base.png` (1920×1080, HTML+Playwright 스크린샷으로 생성)
- 재생성이 필요하면 `.superpowers/brainstorm/*/content/ch{N}_thumbnail.html` → Playwright 스크린샷

**PIL 합성 레이어**:
1. `CH{N}_base.png` 로드 (마스코트 + 아이콘 상단 62%)
2. 하단 38% 반투명 오버레이 (`CHANNEL_COLORS[ch_id]["overlay"]` RGBA)
3. 채널명 소형 텍스트 (primary색)
4. 제목 텍스트 (mode별 변형)

**mode별 출력 파일** (`step10/thumbnail_v1~3.png`):
- `01`: 제목 원문 흰색 텍스트
- `02`: 제목 내 아라비아 숫자 2× 크기 강조 (없으면 mode01과 동일)
- `03`: 마지막 어절 + "?" 질문형, 마지막 어절 채널 primary색

**폴백**: `CH{N}_base.png` 없거나 PIL 실패 시 `_generate_placeholder()` (단색 배경 + 텍스트)

**웹 경로**: `/api/artifacts/{channelId}/{runId}/step10/thumbnail_v{1|2|3}.png` — `runs/` prefix 포함

### 쿼터/캐시 시스템

- **`src/quota/gemini_quota.py`**: RPM 50 제한, 이미지 일 500장, 일간 자동 리셋. 상태 파일 `data/global/quota/gemini_quota_daily.json`.
- **`src/quota/youtube_quota.py`**: 일 10,000단위, 업로드 1건=1,700단위. 부족 시 `deferred_jobs`에 이연 → 다음 실행 시 자동 재시도.
- **`src/quota/ytdlp_quota.py`**: RPM 30, User-Agent 로테이션, 차단 감지 시 5분 대기.
- **`src/cache/gemini_cache.py`**: diskcache 기반, TTL 24h, 500MB. 특정 프롬프트 타입만 캐싱.

**주의**: `src/quota/__init__.py`는 23KB 레거시 파일로, yt-dlp 채널 수집 로직이 포함되어 있다. 일반적인 패키지 init이 아님.

### 웹 대시보드 (`web/`)

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

클라이언트 컴포넌트에서는 `tailwind` 클래스 대신 인라인 `style` + `CARD_BASE` 상수를 사용한다:
```tsx
const CARD_BASE: React.CSSProperties = {
  background: 'rgba(255,255,255,0.60)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(220,80,80,0.18)',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 16px rgba(180,40,40,0.07)',
}
```
사이드바/탑바: `background: rgba(180,40,40,0.82/0.92)` + `backdropFilter: blur(20px)`.
탭 버튼 활성: `rgba(180,40,40,0.88)` 배경 + 흰 텍스트 / 비활성: `transparent`, `#9b4040`.

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

#### 디렉토리 구조

```
web/
├── app/
│   ├── layout.tsx          — CollapsibleSidebar + 탑바(딥레드 glass) + BottomNav + ThemeProvider
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
│   └── ui/                   — shadcn/ui 컴포넌트 (16개)
├── hooks/
│   └── use-is-mobile.ts      — useIsMobile(breakpoint=768): SSR-safe 모바일 감지 훅
└── lib/
    ├── supabase/
    │   ├── client.ts         — 브라우저용 (createBrowserClient)
    │   ├── server.ts         — 서버용 (createServerClient + cookies)
    │   └── server-admin.ts   — service_role 전용 (RLS 우회, 서버에서만 사용)
    ├── fs-helpers.ts         — 경로 보안 유틸리티: validateRunPath / validateChannelPath / getKasRoot / readKasJson / writeKasJson
    └── types.ts              — Supabase DB 전체 타입 (Database, Channel, PipelineRun 등)
```

**홈 페이지 구조**: `page.tsx`(서버) → `KpiBanner`(항상 고정) + `HomeExecTab`(탭 컨트롤러). `HomeExecTab`은 활성 탭에 따라 자체 콘텐츠(경영) 또는 `<HomeOpsTab />`(운영)을 렌더링.

**운영 탭 API 형식**: `/api/pipeline/steps`는 `{ steps: [{ index: 0, name: string, status: 'idle'|'running'|'done'|'error'|'skipped', elapsed_ms?: number }] }` 반환. `index` 0~7이 Step05~12에 대응.

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

## 테스트 핵심 패턴

### Gemini API 의존성 격리

`src/step08/__init__.py`가 `script_generator.py` → `google.generativeai` 임포트 체인을 형성해 테스트에서 실패할 수 있다.

**`conftest.py` 3단계 방어** (모든 테스트 전에 실행):
1. `google.generativeai`, `diskcache`, `sentry_sdk` 모듈-레벨 mock 사전 등록
2. `import src.step08` 선점 — 가짜 부모 모듈 설치 방지
3. `_restore_gemini_cache_after_test` autouse fixture — `importlib.reload()` 후 `_CACHE` 싱글턴 복원

**`google` 네임스페이스 패키지 오염 주의**: 반드시 실제 `google` 패키지 먼저 확보 후 `google.generativeai`만 mock 등록.
```python
import google as _google_pkg
_genai_mock = types.ModuleType("google.generativeai")
sys.modules["google.generativeai"] = _genai_mock
setattr(_google_pkg, "generativeai", _genai_mock)
```

**`_load_and_register()` 패턴**: `test_step08_sd.py`, `test_step08_narration.py`에서 사용. `importlib.util.spec_from_file_location()`으로 `__init__.py`를 우회하여 개별 파일 직접 로드.

### 모듈 바인딩 함정

`from X import Y`는 import 시점에 바인딩된다. 타겟 모듈에서 patch해야 한다:
```python
# 잘못됨
@patch("src.step08.ffmpeg_composer.overlay_bgm")
# 올바름 — 실제 사용하는 모듈에서 patch
@patch("src.step09.bgm_overlay.overlay_bgm")
```

### utf-8-sig 인코딩

`ssot.write_json()`은 `utf-8-sig`(BOM 포함)으로 쓴다. 테스트에서 읽을 때 반드시 `encoding="utf-8-sig"` 사용.

## 핵심 규칙

- **로깅**: `import logging` 금지. 반드시 `from loguru import logger` 사용.
- **JSON I/O**: 직접 `open()` 금지. `ssot.read_json()` / `ssot.write_json()` 사용.
- **캐싱**: Gemini API 응답은 `src/cache/gemini_cache.py` (diskcache 기반, TTL 24h) 사용.
- **쿼터 관리**: Gemini/YouTube API 호출 전 `src/quota/` 모듈로 사용량 기록.
- **채널 설정 SSOT**: 채널 수/카테고리/RPM/목표값은 `src/core/config.py`가 단일 출처.
- **KPI 수집 지연**: Step12 업로드 후 즉시 수집하지 않고 48시간 pending 메커니즘 사용.
- **웹 채널 데이터**: 웹에서 채널 정보 하드코딩 금지. 항상 Supabase `channels` 테이블 또는 fallback 상수 사용.
- **웹 Recharts**: `page.tsx`는 서버 컴포넌트이므로 Recharts 직접 사용 불가. `home-charts.tsx` 또는 별도 `'use client'` 파일에 격리.
- **웹 다크모드**: `document.documentElement.classList`를 직접 조작하지 말 것. `next-themes`의 `useTheme`/`ThemeProvider` 사용.
- **웹 인라인 스타일**: 클라이언트 컴포넌트에서 색상은 Tailwind 클래스 대신 `CARD_BASE` 상수(각 파일 상단 정의) + CSS 변수(`--p1~4`, `--t1~3`)로 표현. 새 홈 탭 컴포넌트 작성 시 `home-exec-tab.tsx`의 `CARD_BASE` 패턴을 복사한다.
- **웹 모바일 반응형**: 레이아웃 수준 변경은 `globals.css` 미디어 쿼리(`kas-sidebar`, `kas-bottom-nav`, `kas-content` 클래스)로 처리. 컴포넌트 내부 그리드/폰트 분기는 `hooks/use-is-mobile.ts`의 `useIsMobile()` 훅 사용.
- **웹 파일 서빙**: `runs/` 결과물은 반드시 `/api/artifacts/[channelId]/[runId]/...` 경로 사용. `/api/files/` 경로는 존재하지 않는다.
- **Supabase 쓰기 작업**: anon key + RLS가 아닌 `createAdminClient()` (service_role) 사용. `web/app/trends/actions.ts`가 참조 구현이다.
- **Sub-Agent 비침습**: `src/agents/` 코드는 기존 파이프라인(Step00~17) 로직을 변경하지 않는다. JSON 결과물 읽기 + 정책 파일 쓰기만 허용.
- **Sub-Agent BaseAgent**: `if root:` 대신 `if root is not None:` 사용. Path 객체는 항상 truthy이므로 None 체크를 명시적으로 작성.
- **type_syncer SQL 타입**: `_SQL_TO_TS` 매핑에 없는 타입은 `"unknown"` 반환. 새 SQL 타입 추가 시 `type_syncer.py`의 `_SQL_TO_TS` dict를 업데이트.
- **썸네일 베이스 PNG**: `assets/thumbnails/CH{N}_base.png` 7개가 Step10의 입력이다. 채널 마스코트 디자인 변경 시 `.superpowers/brainstorm/*/content/ch{N}_thumbnail.html`을 수정 후 Playwright로 재스크린샷.
- **Step10 Gemini 금지**: `thumbnail_generator.py`에 `genai` / `google.generativeai` 임포트를 추가하지 말 것. PIL 합성만 사용한다.
- **`assets/` 디렉토리**: `characters/`(캐릭터 이미지), `lora/`(SD LoRA 가중치), `thumbnails/`(CH 베이스 PNG) 3개 하위 디렉토리. 파이프라인 런타임에 읽기 전용으로만 사용.
- **웹 API 경로 보안**: `channelId`/`runId` URL 파라미터를 파일 경로에 사용하는 모든 API 라우트는 반드시 `web/lib/fs-helpers.ts`의 `validateRunPath()` 또는 `validateChannelPath()`를 사용해야 한다. 직접 `path.join(kasRoot, channelId, ...)` 패턴은 경로 트래버설 취약점이므로 금지.
- **웹 getKasRoot 싱글턴**: API 라우트에서 KAS 루트 경로가 필요하면 로컬 `getKasRoot()` 함수를 직접 정의하지 말고 반드시 `import { getKasRoot } from '@/lib/fs-helpers'`로 가져온다. 로컬 정의 시 `path.join` vs `path.resolve` 불일치로 경계 검사가 실패할 수 있다.
- **Next.js 16 미들웨어**: `web/proxy.ts`가 Next.js 16.2.2의 미들웨어 파일이다. `web/middleware.ts`를 별도로 생성하면 빌드 오류("Both middleware file and proxy file detected")가 발생한다. 인증 로직 수정 시 `proxy.ts`만 편집할 것.
- **웹 Next.js 16 params**: Route handler의 params는 `Promise<{...}>` 타입이므로 반드시 `await params`로 구조분해해야 한다. `{ params }: { params: Promise<{ channelId: string }> }` 패턴.
- **chapter_markers 형식**: `step10/metadata.json`의 `chapter_markers` 키 값은 `[{"time": "00:00", "title": "인트로"}, ...]` 배열. `metadata_generator.py`가 description에 자동 삽입하며 `time` 필드는 `MM:SS` 또는 `H:MM:SS` 형식.
- **FFmpeg 인코딩 표준**: `ffmpeg_composer.py`의 모든 영상 인코딩은 `-crf 22 -preset medium`을 기본값으로 사용. YouTube 권장(18-20)과 처리 속도의 절충점.

## 환경 변수

**백엔드 (`.env`)**: `.env.example` 참고.
- `GEMINI_API_KEY` — 스크립트/이미지/QA 전반
- `YOUTUBE_API_KEY` — 업로드 및 KPI 수집
- `CH1_CHANNEL_ID` ~ `CH7_CHANNEL_ID` — 7개 채널 YouTube ID
- `KAS_ROOT` — 프로젝트 루트 절대 경로. **config.py 기본값이 다른 경로이므로 반드시 `.env`에 명시 필요.**
- `ELEVENLABS_API_KEY` — 미설정 시 gTTS 폴백
- `CH1_VOICE_ID` ~ `CH7_VOICE_ID` — ElevenLabs 채널별 보이스 ID (미설정 시 gTTS 폴백)
- `GEMINI_TEXT_MODEL` — 기본값 `gemini-2.5-flash` (오버라이드 가능)
- `GEMINI_IMAGE_MODEL` — 기본값 `gemini-2.0-flash-preview-image-generation`
- `MANIM_QUALITY` — 기본값 `l` (low, 빠름). 프로덕션 시 `h` (high) 사용
- `USD_TO_KRW` — 기본값 `1350` (YouTube 수익 USD → KRW 환산)
- `SERPAPI_KEY`, `REDDIT_*`, `NAVER_*`, `TAVILY_API_KEY`, `PERPLEXITY_API_KEY` — 미설정 시 해당 소스 스킵
- `SENTRY_DSN` — 미설정 시 에러 추적 비활성화

**웹 (`web/.env.local`)**: `web/.env.local.example` 참고.
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase 프로젝트 URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase anon 공개 키
- `SUPABASE_SERVICE_ROLE_KEY` — **서버 전용** service_role 키. 트렌드 주제 승인/거부 등 RLS를 우회하는 쓰기 작업에 필요. `web/lib/supabase/server-admin.ts`의 `createAdminClient()`에서만 사용.
- `DASHBOARD_PASSWORD` — 웹 대시보드 비밀번호. 미설정 시 인증 자동 통과 (개발 환경)

**YouTube OAuth 토큰**: 업로드/KPI 수집은 API 키가 아닌 OAuth2 인증이 필요하다. `credentials/{CH}_token.json`이 채널당 존재해야 한다. 만료 토큰은 자동 갱신 후 파일에 저장된다. 초기 발급: `python scripts/generate_oauth_token.py --channel CH1`.
