---
paths:
  - src/step05/**
  - src/step08/**
  - src/step08_s/**
  - src/step10/**
---

# Loomix Pipeline Steps — Step00~17 운영 참조

> 각 Step: 입력(Input) · 출력(Output) · 실패 모드(Failure) · 담당 에이전트 · SSOT 경로

---

## Step00 — 글로벌 초기화

- **Input**: 없음 (시스템 시작)
- **Output**: `data/global/step_progress.json`, 7채널 디렉토리 구조 생성
- **Failure**: KAS_ROOT 미설정 → `src/step00/global_init.py` `RuntimeError`
- **담당**: devops-engineer (환경), backend-engineer (로직)
- **SSOT**: `data/global/`, `src/core/config.py`

## Step00p — 파일럿 진단 (Manim + 속도)

- **Input**: Manim 설치 여부 + GPU 가용성
- **Output**: `data/global/pilot_results.json` (Manim OK/FAIL, 렌더 속도 benchmark)
- **Failure**: Manim import 오류 → `src/step00p/diagnose_manim.py` fallback 경로 제안
- **담당**: mlops-engineer
- **SSOT**: `data/global/pilot_results.json`

## Step01 — 채널 베이스라인

- **Input**: `src/core/config.py` 채널 설정
- **Output**: `data/{CH}/baseline.json` (채널별 RPM·목표·설정 스냅샷)
- **Failure**: 채널 설정 불일치 → `config.py` SSOT 재확인
- **담당**: backend-engineer
- **SSOT**: `src/core/config.py`, `data/{CH}/baseline.json`

## Step02 — 수익 구조 분석

- **Input**: `data/{CH}/baseline.json`
- **Output**: `data/{CH}/revenue_structure.json` (광고·멤버십·쇼핑 수익 분해)
- **Failure**: RPM 데이터 없음 → 기본값 사용 (`CH{N}_DEFAULT_RPM`)
- **담당**: revenue-strategist (감사), backend-engineer (구현)
- **SSOT**: `data/{CH}/revenue_structure.json`

## Step03 — 알고리즘 정책

- **Input**: YouTube API (채널 통계)
- **Output**: `data/{CH}/algorithm_policy.json` (SEO 정책·태그·카테고리 설정)
- **Failure**: YouTube API 쿼터 초과 → `data/global/quota/youtube_quota_daily.json` 확인
- **담당**: content-director (감사), backend-engineer (수집)
- **SSOT**: `data/{CH}/algorithm_policy.json`

## Step04 — 월간 포트폴리오 계획

- **Input**: `data/{CH}/revenue_structure.json`, 이전 월 KPI
- **Output**: `data/global/monthly_plan/{yyyy-mm}/portfolio_plan.json`
- **Failure**: 이전 KPI 없음 → 기본 4편/월 계획 사용
- **담당**: revenue-strategist, data-analyst
- **SSOT**: `data/global/monthly_plan/{yyyy-mm}/portfolio_plan.json`

## Step05 — 트렌드 + 지식 수집

- **Input**: 채널별 카테고리, `data/global/quota/` 쿼터 상태
- **Output**: `data/knowledge_store/{CH}/` (트렌드 토픽 + 지식 청크)
- **Failure**: Google Trends 429 → `_KEYWORD_BASELINES` 자동 폴백; YouTube search `relevanceLanguage` 금지
- **담당**: data-engineer (ETL), pipeline-debugger (장애 분석)
- **SSOT**: `data/knowledge_store/{CH}/`

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
python -c "
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge
for ch, cat in [('CH1','economy'),('CH2','realestate')]:
    scored = collect_trends(ch, cat, limit=10)
    topics = [reinterpret_trend(s, cat, ch) for s in scored if s['grade'] in ('auto','review')]
    save_knowledge(ch, topics)
"
python scripts/sync_to_supabase.py
```

**지식 수집** (`knowledge/`): 3단계 파이프라인
- Stage 1: Tavily AI Search + Perplexity API + Gemini Deep Research
- Stage 2: Wikipedia + Semantic Scholar + Naver API 구조화
- Stage 3: Gemini/Claude 팩트체크 + 카테고리별 보강 (FRED, 실거래가, NASA 등)

## Step06 — 주제 선별

- **Input**: `data/knowledge_store/{CH}/`, Step04 포트폴리오 계획
- **Output**: `data/{CH}/selected_topics.json` (grade auto/review 토픽 최종 선별)
- **Failure**: 자동 선별 0건 → HITL 요청 또는 review 토픽 수동 승인
- **담당**: revenue-strategist (감사), content-director (최종 승인)
- **SSOT**: `data/{CH}/selected_topics.json`

## Step07 — 스크립트 초안

- **Input**: `data/{CH}/selected_topics.json`, `data/knowledge_store/{CH}/`
- **Output**: `runs/{CH}/{run_id}/step07/script_draft.json`
- **Failure**: Gemini API 오류 → 재시도 3회 후 `data/global/quota/gemini_quota_daily.json` 확인
- **담당**: backend-engineer (생성), content-director (감사)
- **SSOT**: `runs/{CH}/{run_id}/step07/`

## Step08 — 핵심 영상 생성 오케스트레이터 (**KAS-PROTECTED**)

- **Input**: `runs/{CH}/{run_id}/step07/script_draft.json`, 채널 설정
- **Output**: `runs/{CH}/{run_id}/step08/` (video.mp4, narration.wav, subtitles.srt 등)
- **Failure**: FFmpeg 오류 → `ffmpeg_composer.py` 로그; Manim 타임아웃 → 120초 후 건너뜀
- **담당**: backend-engineer (구현), pipeline-debugger (장애 분석)
- **SSOT**: `runs/{CH}/{run_id}/step08/`, `artifact_hashes.json`

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

캐릭터는 `character_manager.py`에서 채널별 프로파일(base_prompt, seed, LoRA) 관리.

**⚠️ PROTECTED**: `src/step08/__init__.py` 248줄 오케스트레이터 — 비우거나 초기화 스크립트 대상 제외 필수.

## Step08s — Shorts 자동 추출

- **Input**: `runs/{CH}/{run_id}/step08/video_narr.mp4`
- **Output**: `runs/{CH}/{run_id}/step08s/shorts_{1-3}.mp4` (9:16, 60초)
- **Failure**: 원본 영상 없음 → Step08 재실행 필요
- **담당**: backend-engineer, media-engineer (인코딩 품질)
- **SSOT**: `runs/{CH}/{run_id}/step08s/`

`src/step08_s/shorts_generator.py`: Long-form 1편에서 60초 Shorts 3편 자동 추출. FFmpeg 중앙 크롭 1920×1080 → 1080×1920 (9:16).

## Step09 — 영상 QA

- **Input**: `runs/{CH}/{run_id}/step08/` 전체
- **Output**: `runs/{CH}/{run_id}/step09/qa_result.json` (pass/fail + 항목별 점수)
- **Failure**: QA 실패 → `qa_result.json`의 `failed_checks` 항목 확인 후 Step08 재실행
- **담당**: qa-auditor (감사), backend-engineer (수정)
- **SSOT**: `runs/{CH}/{run_id}/step09/qa_result.json`

## Step10 — 썸네일 생성 (PIL 합성)

- **Input**: `assets/thumbnails/CH{N}_base.png`, `runs/{CH}/{run_id}/step07/script_draft.json`
- **Output**: `runs/{CH}/{run_id}/step10/thumbnail_v{1|2|3}.png`
- **Failure**: `CH{N}_base.png` 없음 → `_generate_placeholder()` 단색 대체
- **담당**: ui-designer (디자인), backend-engineer (구현)
- **SSOT**: `runs/{CH}/{run_id}/step10/`, `assets/thumbnails/`

`src/step10/thumbnail_generator.py`는 Gemini 이미지 생성을 **완전히 제거**하고 PIL 4레이어 합성으로 교체됐다.

**베이스 템플릿**: `assets/thumbnails/CH{1-7}_base.png` (1920×1080, HTML+Playwright 스크린샷으로 생성)

**PIL 합성 레이어**:
1. `CH{N}_base.png` 로드 (마스코트 + 아이콘 상단 62%)
2. 하단 38% 반투명 오버레이 (`CHANNEL_COLORS[ch_id]["overlay"]` RGBA)
3. 채널명 소형 텍스트 (primary색)
4. 제목 텍스트 (mode별 변형)

**mode별 출력**: `01` 원문 흰색 · `02` 숫자 2× 강조 · `03` 마지막 어절 질문형 + primary색

**⚠️ 금지**: `thumbnail_generator.py`에 `genai` / `google.generativeai` 임포트 추가 금지.

## Step11 — 최종 QA

- **Input**: step09 QA 결과, step10 썸네일
- **Output**: `runs/{CH}/{run_id}/step11/qa_result.json` (업로드 승인 여부)
- **Failure**: 2회 연속 FAIL → HITL 요청 (ceo 판단)
- **담당**: qa-auditor
- **SSOT**: `runs/{CH}/{run_id}/step11/qa_result.json`

## Step12 — YouTube 업로드

- **Input**: step11 승인 완료, OAuth 토큰 (`data/{CH}/oauth_token.json`)
- **Output**: `runs/{CH}/{run_id}/step12/upload_result.json` (video_id, upload_time)
- **Failure**: OAuth 만료 → `scripts/generate_oauth_token.py --channel {CH}` 재발급; 쿼터 초과 → 익일 재시도
- **담당**: backend-engineer, devops-engineer (OAuth 관리)
- **SSOT**: `runs/{CH}/{run_id}/step12/upload_result.json`, `data/global/quota/youtube_quota_daily.json`

## Step13 — 업로드 후 메타데이터 최적화

- **Input**: `runs/{CH}/{run_id}/step12/upload_result.json` (video_id)
- **Output**: `runs/{CH}/{run_id}/step13/metadata_update.json` (카드·최종화면·자막 업로드)
- **Failure**: video_id 없음 → Step12 재확인; YouTube API 오류 → 재시도 3회
- **담당**: backend-engineer, content-director (SEO 감사)
- **SSOT**: `runs/{CH}/{run_id}/step13/`

## Step14 — 초기 KPI 수집 (48h pending)

- **Input**: `runs/{CH}/{run_id}/step12/upload_result.json`, 업로드 후 48시간
- **Output**: `runs/{CH}/{run_id}/step14/initial_kpi.json` (조회수·좋아요·댓글)
- **Failure**: 48시간 미경과 → `pending` 상태 유지 (강제 수집 금지)
- **담당**: data-analyst (수집), data-engineer (저장)
- **SSOT**: `runs/{CH}/{run_id}/step14/initial_kpi.json`

**⚠️ KPI 수집 지연**: Step12 업로드 후 48시간 pending 메커니즘 — 강제 수집 시 불완전 데이터.

## Step15 — Supabase 동기화

- **Input**: Step14 KPI, 전체 run 메타데이터
- **Output**: Supabase `videos` 테이블 upsert
- **Failure**: Supabase 연결 오류 → `scripts/sync_to_supabase.py` 재실행; RLS 오류 → db-architect 확인
- **담당**: data-engineer, db-architect (스키마)
- **SSOT**: Supabase `videos`, `channels` 테이블

## Step16 — 학습 피드백 수집

- **Input**: Step14~15 KPI 데이터
- **Output**: `data/global/learning_feedback.json` (성공/실패 패턴)
- **Failure**: 피드백 저장 실패 → 세션 교훈 누실. `save_reflection.py` 확인
- **담당**: data-analyst (분석), backend-engineer (저장)
- **SSOT**: `data/global/learning_feedback.json`

## Step17 — 월간 리포트

- **Input**: 전월 전체 run KPI, Supabase BI
- **Output**: `data/global/monthly_report/{yyyy-mm}.json` + Slack 전송
- **Failure**: KPI 부족 (run 0건) → 빈 리포트 생성 후 HITL
- **담당**: data-analyst (생성), finance-manager (P&L), ceo (검토)
- **SSOT**: `data/global/monthly_report/`

---

## 핵심 규칙

- **FFmpeg 인코딩 표준**: `ffmpeg_composer.py`는 `-crf 22 -preset medium` 기본값.
- **영상 파일 우선순위**: `video_narr.mp4 > video.mp4 > video_subs.mp4`. `final.mp4` 하드코딩 금지.
- **나레이션 파일 확장자**: `narration.wav` 우선, `narration.mp3` 폴백. `.mp3` 고정 하드코딩 금지.
- **Run 이미지 경로**: step08 디렉토리 기준 상대경로. `/api/artifacts/{ch}/{run}/step08/` prefix 조합.
- **DRY RUN 런 식별**: `manifest.json`의 `dry_run: true` 필드로 구분.
- **썸네일 베이스 PNG**: `assets/thumbnails/CH{N}_base.png` 7개가 Step10의 입력이다.
