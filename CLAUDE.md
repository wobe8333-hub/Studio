# CLAUDE.md

@AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**KAS (Knowledge Animation Studio)** — AI가 트렌드 주제를 자동 발굴하고, 스크립트/이미지/나레이션을 생성하여 YouTube에 업로드하는 7채널 풀 자동화 파이프라인. 채널당 월 200만원, 총 1,400만원/월 수익 목표.

GitHub: `https://github.com/wobe8333-hub/Studio`

7채널: CH1(경제) / CH2(부동산) / CH3(심리) / CH4(미스터리) / CH5(전쟁사) / CH6(과학) / CH7(역사)

## 주요 명령어

```bash
# ── 파이썬 백엔드 ──────────────────────────────────
# 월간 파이프라인 실행 (month_number: 1~12)
python -m src.pipeline 1

# Windows 작업 스케줄러 등록 (1회 실행, 이후 자동 기동)
# 파이프라인 자동 실행: 매일 06:00  python -m src.pipeline (KAS_Daily_Pipeline)
.\scripts\register_daily_task.ps1
# Mission-Controller 자율 감지: 매일 17:00  claude --print '/mission autorun'
.\scripts\register_autonomous_task.ps1

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
python -c "from src.agents.cost_optimizer import CostOptimizerAgent; print(CostOptimizerAgent().run())"
python -c "from src.agents.script_quality import ScriptQualityAgent; print(ScriptQualityAgent().run())"

# Sub-Agent 테스트만 실행
pytest tests/test_agents/ -q

# GPU 패키지 설치 (GPU 환경 한정 — CPU-only/CI 환경에서는 실행 금지)
pip install torch diffusers transformers accelerate safetensors

# ── 코드 품질 ─────────────────────────────────────
ruff check src/                                          # Python 린팅
ruff check src/ --fix --select=E,W,F,I                  # 자동 수정
cd web && npx prettier --check "app/**/*.{ts,tsx}"       # TS 포맷 체크
cd web && npx prettier --write "app/**/*.{ts,tsx}"       # TS 포맷 적용

# ── 웹 프론트엔드 (web/) ───────────────────────────
cd web
npm run dev          # 개발 서버 (localhost:7002)
npm run build        # 프로덕션 빌드 (TypeScript 타입 검사 포함)
npm run lint         # ESLint

# ── ngrok 외부 공개 ────────────────────────────────
# 고정 도메인: https://cwstudio.ngrok.app → localhost:7002
ngrok start kas-studio
```

## 아키텍처 핵심

### 데이터 흐름 — SSOT 원칙

모든 JSON I/O는 **반드시 `src/core/ssot.py`의 `read_json()` / `write_json()`을 사용**해야 한다.

- `write_json()`: `filelock` + **atomic write** (tempfile → `os.replace`) + `ensure_ascii=True` (PowerShell 5.1 호환용 `\uXXXX` 이스케이프)
- `read_json()`: `encoding="utf-8-sig"` (BOM 처리)

```
data/global/                        — 채널 레지스트리, 쿼터 정책, 메모리 스토어
data/global/notifications/          — Sub-Agent 알림 (notifications.json, hitl_signals.json)
data/global/step_progress.json      — 파이프라인 실시간 진행 상태 (웹 3초 폴링 대상)
data/channels/CH*/                  — 채널별 algorithm/revenue/style 정책 JSON
data/knowledge_store/               — KnowledgePackage JSON
runs/CH*/run_*/                     — 실제 파이프라인 실행 결과물 (manifest.json, step08/, step09/ 등)
runs/CH*/test_run_*/                — DRY RUN 결과물 (manifest.json만 생성, dry_run: true)
logs/                               — pipeline.log (loguru, 50MB rotation)
```

> 상세 아키텍처는 `.claude/rules/` 파일에서 on-demand 로드: `pipeline.md` | `steps.md` | `sub-agents-system.md` | `quota.md` | `web.md` | `testing.md`

## 핵심 규칙

- **로깅**: `import logging` 금지. 반드시 `from loguru import logger` 사용.
- **JSON I/O**: 직접 `open()` 금지. `ssot.read_json()` / `ssot.write_json()` 사용.
- **캐싱**: Gemini API 응답은 `src/cache/gemini_cache.py` (diskcache 기반, TTL 24h) 사용.
- **쿼터 관리**: Gemini/YouTube API 호출 전 `src/quota/` 모듈로 사용량 기록.
- **채널 설정 SSOT**: 채널 수/카테고리/RPM/목표값은 `src/core/config.py`가 단일 출처.
- **KPI 수집 지연**: Step12 업로드 후 즉시 수집하지 않고 48시간 pending 메커니즘 사용.
- **Sub-Agent 비침습**: `src/agents/` 코드는 기존 파이프라인(Step00~17) 로직을 변경하지 않는다.
- **Sub-Agent BaseAgent**: `if root:` 대신 `if root is not None:` 사용 (Path는 항상 truthy).
- **type_syncer SQL 타입**: `_SQL_TO_TS` 매핑에 없는 타입은 `"unknown"`. 새 SQL 타입 추가 시 업데이트 필수.
- **`assets/` 디렉토리**: `characters/`, `lora/`, `thumbnails/` 3개 하위 디렉토리. 런타임 읽기 전용.

> 웹 관련 규칙: `.claude/rules/web.md` (on-demand) | 영상·Step 규칙: `.claude/rules/steps.md` (on-demand)
- **대용량 파일 쓰기**: 한국어 비율이 높거나 300줄 이상인 파일은 Write 도구 대신 Python 스크립트로 작성. 성공 여부는 `grep` 또는 `wc -l`로 즉시 검증.
- **settings.local.json Write 주의**: 직전 Bash 실행이 훅을 트리거해 파일이 변경될 수 있음. Write/Edit 전 반드시 Read 먼저 실행.
- **Python 스크립트 Windows 인코딩**: stdout이 cp949 — em dash·이모지 출력 시 `UnicodeEncodeError`. 스크립트 상단에 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")` 추가.
- **PowerShell 5.1 `?.` 미지원**: PS 7+만 지원. 기본 PS 5.1에서는 `$cmd = Get-Command x -ErrorAction SilentlyContinue; $cmd.Source`로 분리.
- **CronCreate 세션 한계**: Windows에서 cron은 항상 세션 한정. 대안: Windows 작업 스케줄러로 `claude --print '/mission'` 등록.
- **SessionStart 자동 감지**: `settings.local.json`의 `SessionStart` 훅이 매 세션 시작 시 `scripts/mission_probe.py`를 비차단 실행.

---

## 환경 변수

**백엔드 (`.env`)**: `.env.example` 참고.
- `GEMINI_API_KEY` — 스크립트/이미지/QA 전반
- `YOUTUBE_API_KEY` — 업로드 및 KPI 수집
- `CH1_CHANNEL_ID` ~ `CH7_CHANNEL_ID` — 7개 채널 YouTube ID
- `KAS_ROOT` — 프로젝트 루트 절대 경로. **config.py 기본값이 다른 경로이므로 반드시 `.env`에 명시 필요.**
- `ELEVENLABS_API_KEY` — 미설정 시 gTTS 폴백
- `CH1_VOICE_ID` ~ `CH7_VOICE_ID` — ElevenLabs 채널별 보이스 ID (미설정 시 gTTS 폴백)
- `GEMINI_TEXT_MODEL` — 기본값 `gemini-2.5-flash`
- `GEMINI_IMAGE_MODEL` — 기본값 `gemini-2.0-flash-preview-image-generation`
- `MANIM_QUALITY` — 기본값 `l` (low, 빠름). 프로덕션 시 `h` (high) 사용
- `USD_TO_KRW` — 기본값 `1350`
- `SERPAPI_KEY`, `REDDIT_*`, `NAVER_*`, `TAVILY_API_KEY`, `PERPLEXITY_API_KEY` — 미설정 시 해당 소스 스킵
- `SENTRY_DSN` — 미설정 시 에러 추적 비활성화

**웹 (`web/.env.local`)**: `web/.env.local.example` 참고.
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase 프로젝트 URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase anon 공개 키
- `SUPABASE_SERVICE_ROLE_KEY` — **서버 전용** service_role 키. `createAdminClient()`에서만 사용.
- `DASHBOARD_PASSWORD` — 웹 대시보드 비밀번호. 미설정 시 인증 자동 통과
- `PYTHON_EXECUTABLE` — Python 실행 파일 경로. 미설정 시 Windows는 `py`, 기타 환경은 `python3`

**YouTube OAuth 토큰**: `credentials/{CH}_token.json`이 채널당 존재해야 한다. 만료 토큰은 자동 갱신. 초기 발급: `python scripts/generate_oauth_token.py --channel CH1`.

---

## Agent Teams 설정

Claude Code Agent Teams v5가 활성화되어 있다 (**experimental**: `.claude/settings.local.json`의 `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요, Claude Code v2.1.32+). 팀 운영 가이드는 `AGENTS.md` 참고.

### 4-Layer 구조 (14개)

| Layer | 팀원 | 모델 | maxTurns | 역할 |
|-------|------|------|:--------:|------|
| L0 | `mission-controller` | Opus | 30 | 자율 이슈 감지 + 팀 편성 |
| L1 | `python-dev` | Sonnet | 30 | src/+tests/+scripts/ (worktree) |
| L1 | `web-dev` | Sonnet | 30 | web/ (globals.css 제외, worktree) |
| L1 | `design-dev` | Sonnet | 25 | globals.css+public/+thumbnails/ |
| L2 | `quality-security` | Sonnet | 25 | 보안+품질 통합 감사 (background) |
| L2 | `ops-monitor` | Sonnet | 25 | 인프라+문서+비용 운영 |
| L3 | `db-architect` | **Opus** | 25 | DB 스키마/마이그레이션 (worktree) |
| L3 | `refactoring-surgeon` | Sonnet | 30 | God Module 분해 (worktree) |
| L3 | `pipeline-debugger` | Sonnet | 25 | 파이프라인+지식 품질 디버깅 (read-only) |
| L3 | `performance-profiler` | **Haiku** | 25 | 성능 병목 분석 (read-only) |
| L3 | `ux-a11y` | **Haiku** | 20 | WCAG+UX 통합 리뷰 (read-only) |
| L3 | `release-manager` | Haiku | 15 | 릴리스 관리 |
| L3 | `video-specialist` | Sonnet | 25 | 스크립트·썸네일·영상QA·SEO (read-only) |
| L3 | `revenue-strategist` | Sonnet | 25 | 수익 주제 선별 전략 감사 (read-only) |

### Agent Teams 핵심 규칙
- **파일 교차 수정 금지**: python-dev는 web/ 금지, web-dev는 src/ 금지 (per-agent hook 물리적 차단)
- **Read-only 에이전트**: quality-security, performance-profiler, ux-a11y, video-specialist, revenue-strategist, pipeline-debugger는 Write/Edit 금지
- **worktree 에이전트**: python-dev, web-dev, db-architect, refactoring-surgeon, performance-profiler, video-specialist
- **평시**: L0 + L2 = 3개 / **미션**: L1 1~2개 + L3 1~2개 = **최대 5~6개** (공식 권장 3~5 준수). Critical 이슈 시 7개까지 허용. 8개+ 소환은 mission-controller 사전 근거 명시 필수.

### Opus 동시 소환 제약 (2026-04-12)
- mission-controller + db-architect 동시 활성화 시: mission-controller는 팀 편성 직후 종료
- 그 외 Opus 2개 동시 활성 조합은 Anti-Pattern (비용 폭주)

### TaskCompleted 훅 (자동 품질 게이트)
태스크 완료 시마다 **비차단(async)** 자동 실행: pytest → ruff → npm build. (단일 책임 — python-dev·web-dev SubagentStop 훅에서 중복 실행 금지)

```bash
claude agents  # 14개 subagent 목록 확인
```
