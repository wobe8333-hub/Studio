# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**KAS (Knowledge Animation Studio)** — AI가 트렌드 주제를 자동 발굴하고, 스크립트/이미지/나레이션을 생성하여 YouTube에 업로드하는 7채널 풀 자동화 파이프라인. 채널당 월 200만원, 총 1,400만원/월 수익 목표.

7채널: CH1(경제) / CH2(부동산) / CH3(심리) / CH4(미스터리) / CH5(전쟁사) / CH6(과학) / CH7(역사)

## 주요 명령어

```bash
# 월간 파이프라인 실행 (month_number: 1~12)
python -m src.pipeline 1

# 전체 테스트
pytest tests/ -q

# 단일 테스트 파일
pytest tests/test_step05_scorer.py -v

# 단일 테스트 함수
pytest tests/test_step08_sd.py::TestSDGenerator::test_detect_gpu_returns_bool -v

# 대시보드 실행
streamlit run dashboard/app.py

# 환경 점검 (파일럿 전 필수)
python scripts/preflight_check.py

# 환경 설정
cp .env.example .env   # API 키 입력 후 사용
```

## 아키텍처

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

1. 스크립트 생성 (`script_generator.py` → Gemini API)
2. 이미지 생성: `sd_generator.py` (SD XL, GPU 우선) → 실패 시 `image_generator.py` (Gemini 폴백)
3. 나레이션 (`narration_generator.py`: ElevenLabs → gTTS 폴백)
4. 자막 (`subtitle_generator.py`: Faster-Whisper → 균등분배 폴백)
5. FFmpeg 합성 (`ffmpeg_composer.py`)

결과물은 `runs/{channel_id}/{run_id}/step08/` 에 저장.

**주의**: `src/step08/__init__.py`는 **KAS-PROTECTED** 파일이다. 248줄의 오케스트레이터이며 일반적인 `__init__.py`가 아니다. 내용을 비우거나 일괄 초기화 스크립트 대상에서 반드시 제외해야 한다.

### Step05 — 트렌드+지식 수집

**트렌드 수집** (`trend_collector.py`): 5계층 소스 오케스트레이션
- Layer 1~2: `sources/google_trends.py`, `sources/naver.py`, `sources/youtube_trending.py`
- Layer 3~4: `sources/reddit.py`, `sources/arxiv.py`, `sources/scholar.py`
- Layer 5: `sources/wikipedia.py`, `sources/curated.py`
- 점수화: `scorer.py` (관심도 40% + 적합도 25% + 수익성 20% + 긴급도 15%)

**지식 수집** (`knowledge/`): 3단계 파이프라인
- Stage 1: Tavily AI Search + Perplexity API + Gemini Deep Research
- Stage 2: Wikipedia + Semantic Scholar + Naver API 구조화
- Stage 3: Gemini/Claude 팩트체크 + 카테고리별 보강 (FRED, 실거래가, NASA 등)

### 데이터 흐름 — SSOT 원칙

모든 JSON I/O는 **반드시 `src/core/ssot.py`의 `read_json()` / `write_json()`을 사용**해야 한다.

- `write_json()`: `filelock` + **atomic write** (tempfile → `os.replace`) + `ensure_ascii=True` (PowerShell 5.1 호환용 `\uXXXX` 이스케이프)
- `read_json()`: `encoding="utf-8-sig"` (BOM 처리)

```
data/global/          — 채널 레지스트리, 쿼터 정책, 메모리 스토어
data/channels/CH*/    — 채널별 algorithm/revenue/style 정책 JSON
data/knowledge_store/ — KnowledgePackage JSON
runs/CH*/run_*/       — 실행별 결과물 (manifest.json, step08/, step09/ 등)
logs/                 — pipeline.log (loguru, 50MB rotation)
```

### 쿼터/캐시 시스템

- **`src/quota/gemini_quota.py`**: RPM 50 제한, 이미지 일 500장, 일간 자동 리셋. 상태 파일 `data/global/quota/gemini_quota_daily.json`.
- **`src/quota/youtube_quota.py`**: 일 10,000단위, 업로드 1건=1,700단위. 부족 시 `deferred_jobs`에 이연 → 다음 실행 시 자동 재시도.
- **`src/quota/ytdlp_quota.py`**: RPM 30, User-Agent 로테이션, 차단 감지 시 5분 대기.
- **`src/cache/gemini_cache.py`**: diskcache 기반, TTL 24h, 500MB. 특정 프롬프트 타입만 캐싱.

**주의**: `src/quota/__init__.py`는 23KB 레거시 파일로, yt-dlp 채널 수집 로직이 포함되어 있다. 일반적인 패키지 init이 아님.

## 테스트 핵심 패턴

### Gemini API 의존성 격리

`src/step08/__init__.py`가 `script_generator.py`를 임포트하고, `script_generator.py`가 `google.generativeai`를 임포트하기 때문에, `from src.step08.xxx import ...` 형태의 import가 테스트에서 실패할 수 있다.

**`conftest.py` 3단계 방어** (모든 테스트 전에 실행):
1. `google.generativeai`, `diskcache`, `sentry_sdk` 모듈-레벨 mock 사전 등록
2. `import src.step08` 선점 — 테스트 파일이 가짜 부모 모듈을 설치하는 것을 방지
3. `_restore_gemini_cache_after_test` autouse fixture — `importlib.reload()` 후 `_CACHE` 싱글턴 복원

**`google` 네임스페이스 패키지 오염 주의**: 반드시 `import google`로 실제 패키지를 먼저 확보한 뒤 `google.generativeai`만 가짜로 등록해야 한다. `sys.modules["google"]`을 덮어쓰면 `google.api_core` 등 다른 테스트가 실패한다.

```python
# 올바른 패턴
import google as _google_pkg          # 실제 패키지 확보
_genai_mock = types.ModuleType("google.generativeai")
sys.modules["google.generativeai"] = _genai_mock
setattr(_google_pkg, "generativeai", _genai_mock)
```

**`_load_and_register()` 패턴**: `test_step08_sd.py`, `test_step08_narration.py`에서 사용. `importlib.util.spec_from_file_location()`으로 개별 파일을 직접 로드하여 `__init__.py`를 우회.

### 모듈 바인딩 함정 (테스트에서 가장 흔한 실수)

`from X import Y`는 import 시점에 `Y`를 바인딩한다. `X.Y`를 나중에 patch해도 이미 바인딩된 참조는 변경되지 않는다.

```python
# 잘못된 패턴 — bgm_overlay.py가 이미 overlay_bgm을 바인딩했으므로 무효
@patch("src.step08.ffmpeg_composer.overlay_bgm")

# 올바른 패턴 — 타겟 모듈에서 patch
@patch("src.step09.bgm_overlay.overlay_bgm")
```

### utf-8-sig 인코딩

`ssot.write_json()`은 `utf-8-sig`(BOM 포함)으로 쓴다. 테스트에서 이 파일을 읽을 때 반드시 `encoding="utf-8-sig"`를 사용해야 한다. `utf-8`로 읽으면 `JSONDecodeError: Unexpected UTF-8 BOM` 발생.

## 핵심 규칙

- **로깅**: `import logging` 금지. 반드시 `from loguru import logger` 사용.
- **JSON I/O**: 직접 `open()` 금지. `ssot.read_json()` / `ssot.write_json()` 사용.
- **캐싱**: Gemini API 응답은 `src/cache/gemini_cache.py` (diskcache 기반, TTL 24h) 사용.
- **쿼터 관리**: Gemini/YouTube API 호출 전 `src/quota/` 모듈로 사용량 기록.
- **채널 설정 SSOT**: 채널 수/카테고리/RPM/목표값은 `src/core/config.py`가 단일 출처. JSON 파일들은 파생 데이터.
- **KPI 수집 지연**: Step12 업로드 후 즉시 수집하지 않고 48시간 pending 메커니즘 사용.

## 환경 변수

`.env.example` 참고. 최소 필수 키:
- `GEMINI_API_KEY` — 스크립트/이미지/QA 전반
- `YOUTUBE_API_KEY` — 업로드 및 KPI 수집
- `CH1_CHANNEL_ID` ~ `CH7_CHANNEL_ID` — 7개 채널 YouTube ID
- `KAS_ROOT` — 프로젝트 루트 절대 경로. **config.py 기본값이 다른 경로이므로 반드시 `.env`에 명시 필요.**

선택 키 (미설정 시 폴백 동작):
- `ELEVENLABS_API_KEY` — 미설정 시 gTTS 폴백
- `SERPAPI_KEY`, `REDDIT_*`, `NAVER_*` — 미설정 시 해당 소스 스킵
- `SENTRY_DSN` — 미설정 시 에러 추적 비활성화
