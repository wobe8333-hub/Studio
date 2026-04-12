---
paths:
  - src/step05/**
  - src/step08/**
  - src/step08_s/**
  - src/step10/**
---

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

**Step10 Gemini 금지**: `thumbnail_generator.py`에 `genai` / `google.generativeai` 임포트 추가 금지. PIL 합성만 사용한다.

### 핵심 규칙

- **FFmpeg 인코딩 표준**: `ffmpeg_composer.py`는 `-crf 22 -preset medium` 기본값.
- **영상 파일 우선순위**: `video_narr.mp4 > video.mp4 > video_subs.mp4`. `final.mp4` 하드코딩 금지.
- **나레이션 파일 확장자**: `narration.wav` 우선, `narration.mp3` 폴백. `.mp3` 고정 하드코딩 금지.
- **Run 이미지 경로**: step08 디렉토리 기준 상대경로. `/api/artifacts/{ch}/{run}/step08/` prefix 조합.
- **DRY RUN 런 식별**: `manifest.json`의 `dry_run: true` 필드로 구분.
- **썸네일 베이스 PNG**: `assets/thumbnails/CH{N}_base.png` 7개가 Step10의 입력이다.
