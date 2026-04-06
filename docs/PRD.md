# KAS (Knowledge Animation Studio) — Product Requirements Document

> **버전**: 1.0.0 | **작성일**: 2026-04-05 | **작성자**: KAS Team  
> **소스 기준**: `src/core/config.py`, `src/pipeline.py`, `web/app/**`, `scripts/supabase_schema.sql`

---

## 목차

1. [Executive Summary (경영 요약)](#1-executive-summary)
2. [Product Vision & Mission (비전 및 미션)](#2-product-vision--mission)
3. [Problem Statement (해결하고자 하는 문제)](#3-problem-statement)
4. [Target Users (대상 사용자)](#4-target-users)
5. [Product Overview (제품 개요)](#5-product-overview)
6. [Content Strategy (콘텐츠 전략)](#6-content-strategy)
7. [Character System (캐릭터 시스템)](#7-character-system)
8. [System Architecture (시스템 아키텍처)](#8-system-architecture)
9. [Feature Requirements — Backend Pipeline](#9-feature-requirements--backend-pipeline)
10. [Feature Requirements — Web Dashboard](#10-feature-requirements--web-dashboard)
11. [Business Model & Revenue (비즈니스 모델)](#11-business-model--revenue)
12. [Data Model (데이터 모델)](#12-data-model)
13. [Quality Assurance (품질 보증)](#13-quality-assurance)
14. [Success Metrics & KPIs (성공 지표)](#14-success-metrics--kpis)
15. [Risk Management (리스크 관리)](#15-risk-management)
16. [Non-Functional Requirements (비기능 요구사항)](#16-non-functional-requirements)
17. [Monitoring & Observability (모니터링)](#17-monitoring--observability)
18. [Deployment & Infrastructure (배포 및 인프라)](#18-deployment--infrastructure)
19. [Glossary (용어집)](#19-glossary)

---

## 1. Executive Summary

**KAS(Knowledge Animation Studio)**는 AI가 트렌드 주제 발굴부터 스크립트 생성, 애니메이션 영상 제작, YouTube 업로드까지 전 과정을 자동화하는 7채널 풀 파이프라인 시스템이다.

### 핵심 가치 제안

| 항목 | 내용 |
|------|------|
| **수익 목표** | 채널당 월 **200만원**, 7채널 합산 **월 1,400만원** |
| **자동화 범위** | 트렌드 수집 → 지식 조사 → 영상 생성 → QA → 업로드 → KPI 수집 → 학습 피드백 |
| **채널 수** | 7개 (경제/부동산/심리/미스터리/전쟁사/과학/역사) |
| **월간 생산량** | Long-form 74편 + Shorts 230편 = **총 304편** |
| **운영 인원** | **1인** (파이프라인 모니터링 + 선택적 QA 리뷰) |

### 기술 스택 한눈에 보기

| 레이어 | 기술 |
|--------|------|
| **AI 생성** | Google Gemini 2.5 Flash (텍스트), Gemini 2.0 Flash (이미지), Stable Diffusion XL + LoRA |
| **영상 합성** | FFmpeg, Manim (LaTeX-free), Faster-Whisper |
| **음성** | ElevenLabs Multilingual v2 → gTTS (폴백) |
| **백엔드** | Python 3.8+, loguru, tenacity, diskcache, filelock |
| **프론트엔드** | Next.js 16.2.2 + React 19 + Tailwind CSS v4 + shadcn/ui + Recharts 3 |
| **데이터베이스** | Supabase PostgreSQL (9개 테이블, RLS, Realtime) |
| **배포** | Docker (멀티 스테이지), GitHub Actions CI/CD, ngrok 고정 도메인 |

### 현재 상태 (2026-04-05 기준)

- **Phase 1 운영 중**: CH1(경제) + CH2(부동산) 활성화
- **월 20편 목표** (CH1: 10편, CH2: 10편)
- **알고리즘 단계**: 전 채널 PRE-ENTRY (초기 단계, 진입 전략 집중)
- **웹 대시보드**: `https://cwstudio.ngrok.app` (Supabase 연동 완료)

---

## 2. Product Vision & Mission

### Vision
> 1인 크리에이터가 7개 YouTube 채널을 동시 운영하며 월 1,400만원의 수익을 창출하는 AI 기반 지식 콘텐츠 공장

### Mission
> AI가 트렌드를 발굴하고, 지식을 검증하며, 애니메이션 영상을 생성하고, YouTube에 업로드하고, KPI를 수집하여 다음 영상을 더 잘 만들 수 있도록 자동 학습한다.

### 장기 비전 (3년)

1. **Year 1**: 7채널 안정화, 채널당 월 200만원 달성
2. **Year 2**: 법률/세금/환경 채널 추가 (최대 10채널), 월 2,000만원
3. **Year 3**: 멀티 언어 확장 (영어/일본어), 글로벌 콘텐츠 배포

---

## 3. Problem Statement

### 문제 1: YouTube 콘텐츠 제작의 높은 진입 장벽

| 작업 | 수동 시간 | KAS 자동화 시간 |
|------|----------|----------------|
| 트렌드 조사 | 2~4시간/편 | **~5분** (5계층 자동 수집) |
| 스크립트 작성 | 4~8시간/편 | **~2분** (Gemini 생성) |
| 영상 편집 | 8~16시간/편 | **~30분** (FFmpeg 합성) |
| 썸네일 제작 | 1~2시간/편 | **~3분** (AI 이미지 생성) |
| 업로드 및 최적화 | 30분/편 | **~5분** (자동 업로드) |
| **합계** | **약 20시간/편** | **약 45분/편** |

### 문제 2: 7채널 동시 수동 운영의 비현실성

- 7채널 × 10~12편/월 = 월 74편 Long-form 생성 필요
- 수동 운영 시 필요 인력: 최소 **3~5명** (시나리오 작가, 편집자, 업로드 담당 등)
- KAS: **1인** 운영 (모니터링 및 선택적 리뷰만)

### 문제 3: 트렌드 대응 속도의 한계

- YouTube 알고리즘은 트렌드 발생 **72시간 이내** 대응 시 노출 극대화
- 수동 제작 파이프라인은 물리적으로 72시간 대응 불가능
- KAS: 트렌드 감지 후 **약 45분** 내 영상 업로드 가능

---

## 4. Target Users

### 4.1 시스템 운영자 (주요 사용자)

| 항목 | 내용 |
|------|------|
| **인원** | 1인 |
| **주요 업무** | 파이프라인 실행/모니터링, 선택적 QA 리뷰, 정책 조정 |
| **필수 리뷰 채널** | CH1(경제), CH2(부동산), CH4(미스터리) — 업로드 전 수동 승인 필수 |
| **대시보드 접근** | `https://cwstudio.ngrok.app` (비밀번호 인증) |
| **리뷰 용량** | 일 3건, 월 최대 90건 (SLA: 트렌드 24시간, 일반 48시간) |

### 4.2 최종 시청자 (채널별 타겟)

| 채널 | 주요 타겟 | 시청 피크 시간 |
|------|----------|--------------|
| **CH1** 경제 | 30~50대 남성 | 화/목/토 19~21시 KST |
| **CH2** 부동산 | 30~50대 남녀 | 화/목/토 20~22시 KST |
| **CH3** 심리 | 20~40대 전반 | 토/일 14~17시 KST |
| **CH4** 미스터리 | 20~40대 남녀 | 금/토/일 21~23시 KST |
| **CH5** 전쟁사 | 25~45대 남성 | 토/일/화 14~15시, 21시 KST |
| **CH6** 과학 | 15~35대 남녀 | 화/목/토 19~21시 KST |
| **CH7** 역사 | 25~50대 남녀 | 화/목/토 20~22시 KST |

---

## 5. Product Overview

### 5.1 7채널 구성

| 채널 ID | 카테고리 | 론칭 Phase | Long-form/월 | Shorts/월 | RPM 목표 |
|---------|----------|-----------|-------------|----------|---------|
| **CH1** | 경제 | Phase 1 (month 1~) | 10편 | 30편 | 7,000원 |
| **CH2** | 부동산 | Phase 1 (month 1~) | 10편 | 30편 | 6,000원 |
| **CH3** | 심리 | Phase 2 (month 2~) | 10편 | 30편 | 4,000원 |
| **CH4** | 미스터리 | Phase 2 (month 2~) | 12편 | 40편 | 3,500원 |
| **CH5** | 전쟁사 | Phase 3 (month 3~) | 12편 | 40편 | 3,500원 |
| **CH6** | 과학 | Phase 3 (month 3~) | 10편 | 30편 | 4,000원 |
| **CH7** | 역사 | Phase 3 (month 3~) | 10편 | 30편 | 4,000원 |
| **합계** | 7채널 | — | **74편** | **230편** | — |

> **소스**: `src/core/config.py` CHANNELS 상수 (line 66~85)

### 5.2 전체 시스템 구성도

```
[트렌드 소스 5계층]  →  [Step05 수집/점수화]  →  [Step06~07 정책]
                                                           ↓
[Gemini API]        →  [Step08 영상 생성]    →  [Step09~10 BGM/썸네일]
[SD XL + LoRA]                                             ↓
[ElevenLabs/gTTS]                               [Step11 QA 게이트]
[Manim]                                                    ↓
                                                [Step12 YouTube 업로드]
                                                           ↓
                                                [Step13 48h KPI 수집]
                                                           ↓
                    [JSON 파일 (SSOT)]          [Step14~17 월간 보고]
                           ↓
              [scripts/sync_to_supabase.py]
                           ↓
                 [Supabase PostgreSQL]
                           ↓
            [web/ Next.js 대시보드]  →  [cwstudio.ngrok.app]
```

---

## 6. Content Strategy

### 6.1 5계층 트렌드 수집 아키텍처

> **소스**: `src/step05/trend_collector.py`, `src/step05/sources/`

| Layer | 갱신 주기 | 데이터 소스 | 특징 |
|-------|----------|-----------|------|
| **L1** 실시간 | 6시간 | Google Trends, Naver Search API | KR 지역, YouTube 검색 필터, 12개월 관심도 평균 |
| **L2** 일간 | 24시간 | YouTube Trending, Google News RSS | 경쟁 채널 인기 영상 키워드, feedparser 기반 |
| **L3** 주간 | 7일 | Reddit (PRAW), 클리앙/DC인사이드 | 카테고리별 서브레딧 3개, 업보트 기반 점수 |
| **L4** 월간 | 30일 | arXiv, Semantic Scholar, NASA | 학술/전문 소스 (카테고리 제한적) |
| **L5** 에버그린 | 상시 | Wikipedia, 수동 큐레이션 | 채널당 25개 에버그린 주제 풀 |

**수집 흐름**:
1. L1~L4 순차 수집
2. 2-gram Jaccard 유사도 0.75 이상 → 중복 제거 (`src/step05/dedup.py`)
3. 공급 부족 시 L5 에버그린 보충
4. 점수화 엔진 통과

### 6.2 점수화 엔진

> **소스**: `src/step05/scorer.py`

```
최종 점수 = 관심도(40%) + 적합도(25%) + 수익성(20%) + 긴급도(15%)
```

| 요소 | 계산 방법 | 비중 |
|------|----------|------|
| **관심도** | trends×0.5 + news×0.3 + community×0.2 | 40% |
| **적합도** | 채널별 애니메이션 변환 적합도 (mystery 0.95, economy 0.7) | 25% |
| **수익성** | 채널 RPM / 7,000 정규화 | 20% |
| **긴급도** | 트렌딩 3일 이내 1.0 → 14일 초과 0.2, 에버그린 0.3 | 15% |

**등급 분류**:
- **auto** (80점+): 자동 승인, 즉시 파이프라인 투입
- **review** (60~79점): 운영자 수동 승인 필요
- **reject** (60점 미만): 자동 폐기

### 6.3 3단계 지식 수집 파이프라인

> **소스**: `src/step05/knowledge/`, `src/step05/knowledge_store.py`

| Stage | 이름 | 도구 | 수집 항목 |
|-------|------|------|----------|
| **Stage 1** | AI 초벌 리서치 | Tavily AI Search + Perplexity API + Gemini Deep Research | core_facts 5~7개 + 출처 URL |
| **Stage 2** | 구조화 보강 | Wikipedia API + Semantic Scholar + Naver Search | timeline, statistics, expert_quotes, counterpoints |
| **Stage 3** | 팩트체크 | Gemini 교차 검증 + 출처 신뢰도 평가 + 카테고리 전문 보강 | confidence_score, verified facts |

**KnowledgePackage 스키마** (`src/step05/knowledge/knowledge_package.py`):

```
KnowledgePackage {
  topic, category, channel_id
  core_facts: List[str]       # 5~7개 핵심 사실
  timeline: List[Dict]        # 연대표
  statistics: List[Dict]      # 수치/통계
  expert_quotes: List[str]    # 전문가 인용
  counterpoints: List[str]    # 반론/다른 시각
  sources: List[SourceEntry]  # 출처 (url, title, type, reliability)
  confidence_score: float     # 0.0~1.0
  stage1_ok, stage2_ok, stage3_ok: bool
}
```

**카테고리 전문 보강 소스** (`src/step05/knowledge/category_enricher.py`):

| 채널 | 전문 데이터 소스 |
|------|----------------|
| CH1 경제 | 한국은행 경제통계 |
| CH2 부동산 | 국토교통부 실거래가, KB부동산 |
| CH3 심리 | APA (American Psychological Association) |
| CH4 미스터리 | Wikipedia 미해결 사건 목록 |
| CH5 전쟁사 | 전쟁기념관 |
| CH6 과학 | arXiv, NASA |
| CH7 역사 | 국사편찬위원회 |

### 6.4 콘텐츠 믹스 전략

| 유형 | 비율 | 설명 |
|------|------|------|
| **트렌딩** | 60% | 트렌드 발생 72시간 이내 대응 (CH4 미스터리는 48시간) |
| **에버그린** | 25% | 장기 검색 유입 유도, 시간이 지나도 가치 있는 주제 |
| **시리즈** | 15% | 기초편/심화편/실전편 3편 구성 (Step15 세션 체인) |

---

## 7. Character System

### 7.1 채널별 AI 캐릭터 프로파일

> **소스**: `src/step08/character_manager.py`

| 채널 | 캐릭터명 | 컨셉 | 특징 |
|------|---------|------|------|
| **CH1** | 경제요정 **까미** | 친근한 경제 멘토 | 골드/네이비 의상, 안경 착용 |
| **CH2** | 집찾기 **도리** | 부동산 전문 안내자 | 청록 의상, 집 모양 액세서리 |
| **CH3** | 마음탐험가 **루나** | 심리 탐구 가이드 | 보라/라벤더 의상, 온화한 표정 |
| **CH4** | 미스터리 탐정 **셜** | 수수께끼 해결사 | 다크 그린 코트, 돋보기 |
| **CH5** | 역사특공대 **마루** | 전쟁사 해설자 | 밀리터리 카키, 진지한 표정 |
| **CH6** | 과학박사 **스텔라** | 우주/과학 탐험가 | 흰 실험복, 별 장식 |
| **CH7** | 역사학자 **구루** | 역사 스토리텔러 | 전통 한복/클래식 의상 |

### 7.2 캐릭터 생성 기술 스택

```
캐릭터 생성 우선순위:
1순위: Stable Diffusion XL Base 1.0 + 채널별 LoRA (.safetensors)
2순위: Gemini Image Model (gemini-2.0-flash-preview-image-generation)
3순위: ffmpeg drawtext 플레이스홀더 → 최소 PNG (폴백)
```

**GPU 감지** (`src/step08/sd_generator.py`): `torch.cuda.is_available()` 확인 후 GPU 가용 시에만 SD XL 사용, 미가용 시 자동으로 Gemini 이미지 API 전환

**일관성 보장**: 캐릭터별 고정 seed + negative_prompt + base_prompt로 동일 캐릭터 반복 생성

### 7.3 채널별 면책조항 자동 삽입

> **소스**: `src/step11/qa_gate.py`, `src/step08/script_generator.py`

| 채널 | 면책조항 유형 |
|------|-------------|
| CH1 | `financial_disclaimer` — 투자 판단은 개인 책임 |
| CH2 | `investment_disclaimer` — 부동산 정보는 참고용 |
| CH3 | `psychology_disclaimer` — 전문 심리 치료 대체 불가 |
| CH4 | `mystery_disclaimer` — 미확인 정보 포함 가능 |
| CH5/CH7 | `history_disclaimer` — 역사적 해석 차이 존재 |
| CH6 | `science_disclaimer` — 최신 연구 반영 노력, 오류 가능 |

QA 게이트(Step11)에서 면책조항 키 존재 + AI 라벨 존재 여부를 필수 검증한다.

---

## 8. System Architecture

### 8.1 백엔드 파이프라인 18-Step 흐름

> **소스**: `src/pipeline.py` `run_monthly_pipeline(month_number)`

```
실행: python -m src.pipeline {month_number}

┌─ 초기화 (최초 1회, .initialized 플래그로 중복 방지) ──────────┐
│  Step00  전역 초기화 (채널 디렉토리, 레지스트리, 쿼터 정책)      │
│  Step00p Manim 파일럿 & 진단 (선택적)                          │
│  Step01  채널 베이스라인 (YouTube API 채널 통계 수집)            │
│  Step02  수익 구조 정책 (RPM 초기화, AdSense/제휴 믹스)         │
│  Step03  알고리즘 정책 (CTR/AVP 임계값, SEO 규칙, 업로드 타이밍) │
│  Step04  포트폴리오 계획 (월간 콘텐츠 비율 계획)                 │
└────────────────────────────────────────────────────────────────┘
         ↓
┌─ 이연 처리 ──────────────────────────────────────────────────┐
│  _run_deferred_uploads()  YouTube 쿼터 부족 이연 업로드 재처리  │
│  _run_pending_step13()    48시간 경과 KPI 수집 실행            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌─ 채널 루프 (활성 채널 × 주제 루프) ─────────────────────────────┐
│  Step05  트렌드 수집 + 지식 수집 (5계층 + 3단계)                │
│  Step06  스타일 정책 빌드 (애니메이션 스타일, 재해석)             │
│  Step07  수익 정책 로드 (미드롤 위치, RPM floor)                │
│                                                                │
│  Step08  영상 생성 오케스트레이터 ←── 핵심, 가장 복잡           │
│    ├── script_generator.py  (Gemini → 스크립트 JSON)           │
│    ├── sd_generator.py      (SD XL + LoRA → 캐릭터 이미지)     │
│    ├── image_generator.py   (Gemini 이미지 → 섹션 배경)        │
│    ├── scene_composer.py    (PIL → 캐릭터+배경+자막 합성)       │
│    ├── motion_engine.py     (FFmpeg Ken Burns → MP4 클립)      │
│    ├── manim_generator.py   (Gemini → Manim 코드 → 애니메이션) │
│    ├── narration_generator.py (ElevenLabs → gTTS 폴백)        │
│    ├── subtitle_generator.py  (Faster-Whisper → pydub 폴백)   │
│    ├── ffmpeg_composer.py   (클립 concat → 나레이션 합성 → SRT) │
│    └── metadata_generator.py (Gemini → SEO 태그 15개)         │
│                                                                │
│  Step09  BGM 오버레이 (Suno AI → 로컬 WAV → 없음)              │
│  Step10  제목/썸네일 변형 3종 (authority/curiosity/benefit)     │
│  Step11  QA 게이트 (5개 검증, 수동 리뷰 요청)                   │
│  Step12  YouTube 업로드 + 썸네일 + 48h KPI 등록                │
│  Step08s Shorts 생성 (Long-form에서 60초 × 3편)               │
│  Step13  학습 피드백 + Phase 승격 판정 (48h 후 실행)            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌─ 월간 보고 ─────────────────────────────────────────────────────┐
│  Step14  수익 추적 (AdSense + 제휴 - 운영비 = 순이익)           │
│  Step15  시리즈 체인 (기초편/심화편/실전편 계획)                 │
│  Step16  리스크 통제 (순이익 미달 채널 감지)                    │
│  Step17  지속가능성 평가 (주제 고갈 리스크, 분기 1회)            │
└────────────────────────────────────────────────────────────────┘
```

### 8.2 SSOT 데이터 흐름 원칙

> **소스**: `src/core/ssot.py`

모든 JSON I/O는 반드시 `ssot.read_json()` / `ssot.write_json()`을 통해야 한다.

```python
# write_json 보장 사항:
# 1. filelock.FileLock → 동시 접근 방지
# 2. tempfile → os.replace → 원자적 쓰기 (중단 시 파일 손상 없음)
# 3. ensure_ascii=True → PowerShell 5.1 호환 (\uXXXX 이스케이프)

# read_json 보장 사항:
# 1. encoding="utf-8-sig" → BOM 처리
```

### 8.3 캐시 전략

> **소스**: `src/cache/gemini_cache.py`

| 항목 | 값 |
|------|---|
| **구현** | diskcache 라이브러리 |
| **저장 경로** | `data/global/cache/diskcache/` |
| **크기 한도** | 500MB |
| **TTL** | 24시간 자동 만료 |
| **캐싱 대상** | `system_prompt`, `style_template`, `affiliate_insert_template` |
| **키 생성** | SHA-256(prompt_type::content) 앞 16자 |
| **쿼터 연동** | hit 시 `record_cache_hit(cost_saved_krw)` 자동 호출 |

### 8.4 외부 API 의존성 맵

| API | 사용 Step | 목적 | 폴백 |
|-----|----------|------|------|
| **Gemini 2.5 Flash** (텍스트) | Step05, Step08, Step10, Step11 | 스크립트, Manim 코드, SEO 태그, Vision QA | 없음 (핵심 의존) |
| **Gemini 2.0 Flash** (이미지) | Step08, Step10 | 섹션 이미지, 썸네일 | ffmpeg 플레이스홀더 |
| **YouTube Data API v3** | Step01, Step05, Step12 | 채널 통계, 트렌딩, 업로드 | 기본값, 이연 |
| **YouTube Analytics API v2** | Step12 KPI | 48h 조회수/CTR/AVP/수익 | 예측값 |
| **ElevenLabs** | Step08 | 채널별 TTS 나레이션 | gTTS |
| **Tavily AI Search** | Step05 Stage1 | 실시간 웹 검색 | 다른 소스 보충 |
| **Perplexity API** | Step05 Stage1 | AI 심층 요약 | 다른 소스 보충 |
| **Naver Search API** | Step05 L1, Stage2 | 한국어 트렌드/뉴스 | 다른 소스 보충 |
| **Google Trends** (pytrends) | Step05 L1 | 검색 트렌드 점수 | 0점 부여 |
| **Reddit** (PRAW) | Step05 L3 | 커뮤니티 토픽 | 건너뜀 |
| **Suno AI API** | Step09 | AI BGM 생성 | 로컬 WAV → 없음 |
| **Stable Diffusion XL** | Step08 | 캐릭터 이미지 (GPU) | Gemini 이미지 |
| **Sentry** | pipeline.py | 에러 추적 | 없어도 동작 |
| **Supabase** | 파이프라인 완료 후 | 대시보드 데이터 동기화 | 건너뜀 |

### 8.5 에러 처리 4계층 방어

```
계층 1 — 사전 차단 (실행 전)
  └── pre_cost_estimator: 실행당 $5 한도 초과 시 토픽 차단
  └── youtube_quota.can_upload(): 잔여 유닛 < 1,700 시 이연 등록

계층 2 — 재시도 (실행 중)
  └── @retry(stop_after_attempt(3), wait=wait_exponential(2, 60))
  └── 대상: script_generator, image_generator, manim_generator,
             title_variant_builder, thumbnail_generator

계층 3 — 폴백 체인 (대안 실행)
  └── SD XL → Gemini Image → ffmpeg placeholder → 최소 PNG
  └── ElevenLabs → gTTS
  └── Faster-Whisper → pydub 균등분배
  └── Manim → Gemini Image + motion clip
  └── Ken Burns → 정적 클립

계층 4 — 이연 메커니즘 (다음 실행에 재처리)
  └── YouTube 쿼터 부족 → deferred_jobs 배열 등록
  └── 48h KPI → step13_pending/ 디렉토리에 pending 파일 생성
```

---

## 9. Feature Requirements — Backend Pipeline

### Step00: 전역 초기화

> **소스**: `src/step00/global_init.py`, `src/step00/channel_registry.py`

| 항목 | 내용 |
|------|------|
| **기능** | 7채널 디렉토리 구조 생성, 채널 레지스트리 초기화, 쿼터/리뷰 정책 생성 |
| **실행 조건** | `data/global/.initialized` 플래그 없을 시 최초 1회만 실행 |
| **출력** | `data/global/channel_registry.json`, `data/global/api_quota_policy.json`, `data/global/review_capacity_policy.json` |
| **외부 API** | 없음 |

**채널 레지스트리 주요 필드**: `id`, `category`, `category_ko`, `launch_phase`, `rpm_tier(HIGH/MID/LOW)`, `monthly_longform_target`, `monthly_shorts_target`, `affiliate`

---

### Step00p: Manim 파일럿 & 진단

> **소스**: `src/step00p/diagnose_manim.py`, `src/step00p/manim_pilot.py`

| 항목 | 내용 |
|------|------|
| **기능** | Manim 렌더링 환경 진단, 비용/속도 측정 유틸리티 |
| **실행 조건** | 파이프라인 첫 실행 전 수동 실행 권장 |
| **외부 API** | 없음 |

---

### Step01: 채널 베이스라인

> **소스**: `src/step01/channel_baseline.py`

| 항목 | 내용 |
|------|------|
| **기능** | YouTube API로 채널 통계 수집 → 알고리즘 신뢰 레벨 판정 → 캐시플로우 계획 생성 |
| **입력** | CH1~CH7 YouTube Channel ID (환경 변수), OAuth2 토큰 |
| **출력** | `data/channels/{CH}/channel_baseline.json`, `data/channels/{CH}/cashflow_plan.json` |
| **외부 API** | YouTube Data API v3 `channels.list` (쿼터 1단위) |
| **알고리즘 레벨** | ACTIVE / WARMING / COLD 판정 |

---

### Step02: 수익 구조 정책

> **소스**: `src/step02/revenue_structure.py`

| 항목 | 내용 |
|------|------|
| **기능** | RPM 초기값 설정, 수익 구조 정책 생성 (AdSense 75% + 제휴 25%) |
| **입력** | `config.py` 상수 (RPM, 제휴 상품 정의) |
| **출력** | `data/channels/{CH}/rpm_reality.json`, `data/channels/{CH}/revenue_structure_policy.json` |
| **외부 API** | 없음 |

---

### Step03: 알고리즘 정책

> **소스**: `src/step03/algorithm_policy.py`

| 항목 | 내용 |
|------|------|
| **기능** | 채널별 YouTube 알고리즘 최적화 정책 생성 |
| **주요 파라미터** | CTR 임계값 5.5%, AVP 임계값 45%, AVD 임계값 280초, 트렌드 대응 72시간 |
| **출력** | `data/channels/{CH}/algorithm_policy.json` |
| **외부 API** | 없음 |

---

### Step04: 월간 포트폴리오 계획

> **소스**: `src/step04/portfolio_plan.py`

| 항목 | 내용 |
|------|------|
| **기능** | 활성 채널의 월간 콘텐츠 비율 계획 |
| **콘텐츠 믹스** | 트렌딩 60% / 에버그린 25% / 시리즈 15% |
| **출력** | `data/global/monthly_plan/{YYYY-MM}/portfolio_plan.json` |

---

### Step05: 트렌드 수집 + 지식 수집

> **소스**: `src/step05/trend_collector.py`, `src/step05/knowledge_store.py`

*(상세 내용은 [섹션 6](#6-content-strategy) 참조)*

| 항목 | 내용 |
|------|------|
| **기능** | 5계층 트렌드 수집, 점수화, 등급 분류, 3단계 지식 패키지 생성 |
| **출력** | `data/knowledge_store/{CH}/discovery/raw/assets.jsonl`, `data/knowledge_store/{CH}/packages/{topic}.json` |

---

### Step06: 스타일 정책

> **소스**: `src/step06/style_policy.py`

| 항목 | 내용 |
|------|------|
| **기능** | 채널별 영상 제작 스타일 정책 빌드 (애니메이션 스타일, 렌더 도구) |
| **출력** | `data/channels/{CH}/style_policy_master.json` (SHA-256 fingerprint 포함) |

**애니메이션 스타일 매핑**:

| 채널 | 스타일 | 렌더 도구 |
|------|--------|---------|
| CH1, CH2 | comparison (비교) | Manim |
| CH3 | metaphor (은유) | Gemini |
| CH4 | hybrid (혼합) | Manim + Gemini |
| CH5, CH7 | timeline (연대표) | Manim |
| CH6 | process (과정) | Manim |

---

### Step07: 수익 정책

> **소스**: `src/step07/revenue_policy.py`

| 항목 | 내용 |
|------|------|
| **기능** | 채널별 수익 정책 관리 (영상 길이, 미드롤 위치, RPM floor) |
| **출력** | `data/channels/{CH}/revenue_policy.json` |

---

### Step08: 영상 생성 오케스트레이터 (핵심)

> **소스**: `src/step08/__init__.py` (KAS-PROTECTED, 248줄 오케스트레이터)

**⚠️ 주의**: `src/step08/__init__.py`는 일반 `__init__.py`가 아닌 핵심 오케스트레이터다. 내용을 비우거나 초기화 스크립트 대상에서 반드시 제외해야 한다.

**`run_step08()` 처리 순서**:

```
1. run_id 생성 (run_{CH}_{timestamp})
2. 실행 디렉토리 구조 생성
3. manifest.json, decision_trace.json, cost.json 초기화
4. 스크립트 생성 (Gemini + KnowledgePackage 연동)
5. 섹션 분류 (manim_sections / gemini_sections)
6. 이미지 생성:
   ├── SD XL + LoRA (GPU 우선)
   ├── scene_composer.py: 캐릭터+배경+자막바 합성
   └── motion_engine.py: Ken Burns 팬/줌 효과 → MP4 클립
7. Manim 클립 생성:
   ├── Gemini로 LaTeX-free Manim 코드 생성
   ├── AST 검증 + LaTeX 패턴 탐지 + 자동 수정
   ├── subprocess 실행 (타임아웃 120초)
   └── 실패 시 이미지 폴백 + manim_stability_report.json 생성
8. 클립 concat (ffmpeg_composer.py)
9. 나레이션 생성 (ElevenLabs → gTTS)
10. 나레이션 합성
11. 자막 생성 (Faster-Whisper → pydub 균등분배)
12. 자막 합성 (한 줄 40자 제한)
13. 메타데이터 생성 (SEO 태그 15개)
14. SHA-256 무결성 검증 (artifact_hashes.json)
15. manifest.json → COMPLETED
```

**Manim LaTeX-free 강제 규칙**: `MathTex`, `Tex`, `BarChart`, `DecimalNumber` 사용 절대 금지 (pdflatex 미설치 환경)

**출력 경로**: `runs/{CH}/{run_id}/step08/`

---

### Step08s: Shorts 생성

> **소스**: `src/step08_s/shorts_generator.py`

| 항목 | 내용 |
|------|------|
| **기능** | Long-form 1편 → 60초 Shorts 3편 자동 생성 |
| **처리** | FFmpeg 중앙 크롭 1920×1080 → 1080×1920 (9:16 세로) + 자막 오버레이 |
| **추출 구간** | hook + 핵심 섹션 2개 |

---

### Step09: BGM 오버레이

> **소스**: `src/step09/bgm_overlay.py`, `src/step09/bgm_generator.py`

| 항목 | 내용 |
|------|------|
| **기능** | 채널별 BGM 생성 + 영상 오버레이 |
| **BGM 우선순위** | 로컬 WAV (`bgm/{CH}_bgm.wav`) → Suno AI API → 없음 |
| **오버레이** | FFmpeg amix (volume 0.08) |
| **실패 시** | 경고 후 진행 (비치명적) |

---

### Step10: 제목/썸네일 변형

> **소스**: `src/step10/title_variant_builder.py`, `src/step10/thumbnail_generator.py`

| 항목 | 내용 |
|------|------|
| **기능** | 제목 3종 + 썸네일 3종 생성 |
| **제목 모드** | authority(권위)/curiosity(호기심)/benefit(혜택) |
| **썸네일** | Gemini Image API, 채널별 스타일, 실패 시 플레이스홀더 |

---

### Step11: QA 게이트

> **소스**: `src/step11/qa_gate.py`

| 검증 항목 | 내용 | 채널별 예외 |
|----------|------|-----------|
| **애니메이션 품질** | video.mp4 존재 + 크기 > 0 + hook ≤ 10초 | 없음 |
| **Gemini Vision QA** | 5프레임 샘플링 → 캐릭터 일관성/텍스트 가독성/부적절 콘텐츠 | 없음 |
| **면책조항** | 채널별 disclaimer 키 + ai_label 존재 | 없음 |
| **수익 공식** | `affiliate purchase_rate_applied > 0` | 없음 |
| **수동 리뷰** | REVIEW_REQUIRED 상태 → 운영자 승인 대기 | CH1/CH2/CH4 필수, CH3 조건부, CH5~7 자동 |

`overall_pass`: 모든 항목 AND → 자동 채널만 자동 업로드

---

### Step12: YouTube 업로드 + KPI 수집

> **소스**: `src/step12/uploader.py`, `src/step12/kpi_collector.py`, `src/step12/experiment_manager.py`

**업로드 프로세스**:

| 단계 | 처리 | 쿼터 비용 |
|------|------|----------|
| 쿼터 확인 | `can_upload()`: 잔여 ≥ 1,700 유닛 확인 | — |
| 영상 업로드 | YouTube Data API v3 `videos.insert` (resumable) | 1,600 유닛 |
| 썸네일 설정 | `thumbnails.set` | 50 유닛 |
| 이연 등록 | 쿼터 부족 시 `deferred_jobs` 배열에 추가 | — |

**KPI 수집 (48시간 후)**:

수집 메트릭: `views`, `watchTime`, `avgViewDuration`, `avgViewPercentage`, `impressions`, `CTR`, `revenue(USD)`, `RPM`

알고리즘 단계 판정: `PRE-ENTRY → SEARCH-ONLY → BROWSE-ENTRY → ALGORITHM-ACTIVE`

---

### Step13: 학습 피드백

> **소스**: `src/step13/learning_feedback.py`

| 항목 | 내용 |
|------|------|
| **기능** | KPI 결과를 메모리 스토어에 반영, Phase 승격 판정 |
| **승리 패턴 기준** | CTR ≥ 6.0% AND AVP ≥ 50.0% → `winning_animation_patterns` 추가 |
| **Phase 승격** | 단방향만 허용 (강등 없음) |
| **Pending 메커니즘** | 업로드 후 48시간 후 실행 등록 (`data/global/step13_pending/`) |

---

### Step14~17: 월간 보고

| Step | 소스 | 기능 | 주기 |
|------|------|------|------|
| **Step14** | `src/step14/revenue_tracker.py` | 채널별 순이익 계산 및 집계 | 월간 |
| **Step15** | `src/step15/session_chain.py` | 시리즈 콘텐츠 계획 (기초/심화/실전) | 필요 시 |
| **Step16** | `src/step16/risk_control.py` | 수익 미달 채널 리스크 대시보드 | 월간 |
| **Step17** | `src/step17/sustainability.py` | 주제 고갈 리스크 평가 | 분기 |

---

## 10. Feature Requirements — Web Dashboard

> **소스**: `web/app/`, **스택**: Next.js 16.2.2 + Tailwind CSS v4 + shadcn/ui + Supabase

### 10.1 메인 대시보드 (`/`)

| 항목 | 내용 |
|------|------|
| **렌더링** | 서버 컴포넌트 (SSR) |
| **데이터** | `channels` 전체 + `pipeline_runs` 최신 5건 |
| **KPI 카드 4종** | 월 총 목표(14,000,000원) / 활성 채널 수 / 달성률(RadialGauge) / 리스크 채널 수 |
| **파이프라인 타임라인** | 수직 타임라인, 상태별 컬러 노드 (COMPLETED/FAILED/RUNNING/PENDING) |
| **채널 그리드** | 7채널 카드, 채널 고유 색상, 수익 Progress 바, KPI 3종 |
| **Fallback** | Supabase 미연동 시 MOCK_CHANNELS(7채널) + MOCK_RUNS(2건) |

### 10.2 트렌드 관리 (`/trends`)

| 항목 | 내용 |
|------|------|
| **렌더링** | 클라이언트 컴포넌트 (CSR) |
| **데이터** | `trend_topics` score 내림차순 100건 |
| **기능** | 채널/상태 필터링, 승인/거부/되돌리기 버튼 |
| **낙관적 업데이트** | UI 즉시 반영 → Server Action `updateTopicGrade` → 실패 시 롤백 |
| **쓰기 작업** | `trend_topics.grade` UPDATE + `revalidatePath('/trends')` |

### 10.3 수익 추적 (`/revenue`)

| 항목 | 내용 |
|------|------|
| **렌더링** | CSR |
| **데이터** | `revenue_monthly` 현재 월 |
| **차트** | Recharts BarChart (AdSense + 제휴 스택 바) |
| **요약** | 총 순이익 / 목표 달성 채널 수 / 전체 달성률 |

### 10.4 리스크 모니터링 (`/risk`)

| 항목 | 내용 |
|------|------|
| **렌더링** | SSR |
| **데이터** | `channels` + `risk_monthly` 현재 월 조인 |
| **리스크 판정** | `net_profit < 2,000,000` → HIGH |
| **UI** | 경고 배너 (HIGH 시) + 리스크 히트맵 + 채널별 상세 |

### 10.5 비용/쿼터 (`/cost`)

| 항목 | 내용 |
|------|------|
| **렌더링** | CSR |
| **데이터** | `quota_daily` 최근 7일 |
| **차트** | Recharts BarChart (Gemini + YouTube 일별 요청 추이) |
| **요약** | 오늘 총 비용 / Gemini 이미지 사용률 / YouTube 쿼터 사용률 |

### 10.6 학습 피드백 (`/learning`)

| 항목 | 내용 |
|------|------|
| **렌더링** | CSR |
| **데이터** | `learning_feedback` 최신 50건 |
| **차트** | 주간 CTR/AVP 추이 라인 차트 |
| **테이블** | 채널/CTR/AVP/조회수/알고리즘 단계/수익 추적 상태 |

### 10.7 채널 상세 (`/channels/[id]`)

| 항목 | 내용 |
|------|------|
| **렌더링** | CSR (React `use()` hook) |
| **데이터** | Promise.all 병렬: channels + revenue_monthly + pipeline_runs(10건) + kpi_48h(7건) |
| **차트** | KPI 히스토리 라인 차트 (CTR + AVP 추이) |
| **테이블** | 파이프라인 실행 이력 (ID/주제/상태/시간) |

### 10.8 설정 (`/settings`)

| 항목 | 내용 |
|------|------|
| **렌더링** | SSR (정적 데이터만) |
| **현재 상태** | 읽기 전용 |
| **표시 내용** | 7채널 설정 테이블 + API 쿼터 정책 테이블 + 런치 단계 정책 |

### 10.9 로그인 (`/login`)

| 항목 | 내용 |
|------|------|
| **렌더링** | CSR |
| **인증 방식** | 단일 비밀번호 (`DASHBOARD_PASSWORD` 환경 변수) |
| **쿠키** | `kas_access` httpOnly, secure, sameSite:strict, 7일 유효 |
| **개발 환경** | 비밀번호 미설정 시 항상 통과 |

### 10.10 공통 컴포넌트

| 컴포넌트 | 파일 | 기능 |
|---------|------|------|
| **AppSidebar** | `components/sidebar-nav.tsx` | 채널 고유 색상 dot, 현재 경로 하이라이트 |
| **RealtimePipelineStatus** | `components/realtime-pipeline-status.tsx` | Supabase Realtime 구독, RUNNING 상태 실시간 표시 |
| **AnimatedCard** | `components/animated-sections.tsx` | hover lift + viewport fade-in (motion/react) |
| **ThemeToggle** | `components/theme-toggle.tsx` | next-themes, hydration mismatch 방지 (mounted 패턴) |
| **Sparkline** | `components/home-charts.tsx` | KPI 카드 내 미니 AreaChart |
| **RadialGauge** | `components/home-charts.tsx` | 달성률 반원형 게이지 |

### 10.11 디자인 시스템 — Amber Studio

```css
/* 7채널 고유 색상 (oklch 색공간) */
--channel-ch1: oklch(0.65 0.19 55)   /* 경제: 골드 */
--channel-ch2: oklch(0.60 0.18 175)  /* 부동산: 틸 */
--channel-ch3: oklch(0.62 0.16 25)   /* 심리: 테라코타 */
--channel-ch4: oklch(0.65 0.18 310)  /* 미스터리: 퍼플 */
--channel-ch5: oklch(0.60 0.17 145)  /* 전쟁사: 올리브 그린 */
--channel-ch6: oklch(0.62 0.19 230)  /* 과학: 스카이 블루 */
--channel-ch7: oklch(0.62 0.15 60)   /* 역사: 브론즈 */

/* Primary (앰버 골드) */
라이트: oklch(0.55 0.16 55)
다크:   oklch(0.72 0.17 65)
```

**폰트**: Sora (heading), Geist Sans (body), Geist Mono (code)

**Tailwind v4**: `tailwind.config.ts` 없음 → `globals.css`에서 CSS-first 방식으로 전체 설정 관리

---

## 11. Business Model & Revenue

### 11.1 수익 목표 로드맵

> **소스**: `src/core/config.py` (line 154~165)

| Phase | 기간 | 채널당 월 순이익 목표 | 전략 |
|-------|------|-------------------|------|
| Phase 0 | month 1~2 | **0원** | 알고리즘 진입 집중, 콘텐츠 품질 최적화 |
| Phase 1 | month 3~5 | **500,000원** | SEARCH-ONLY 진입, CTR/AVP 개선 |
| Phase 2 | month 6+ | **2,000,000원** | ALGORITHM-ACTIVE, 수익화 최적화 |

### 11.2 RPM 3단계 체계

> **소스**: `src/step02/revenue_structure.py` (line 38~40)

| 채널 | RPM Initial (0.5x) | RPM Floor | RPM Proxy (안정화) |
|------|-------------------|-----------|--------------------|
| CH1 경제 | 3,500원 | 5,000원 | **7,000원** |
| CH2 부동산 | 3,000원 | 4,000원 | **6,000원** |
| CH3 심리 | 2,000원 | 2,800원 | **4,000원** |
| CH4 미스터리 | 1,750원 | 2,500원 | **3,500원** |
| CH5 전쟁사 | 1,750원 | 2,500원 | **3,500원** |
| CH6 과학 | 2,000원 | 2,800원 | **4,000원** |
| CH7 역사 | 2,000원 | 2,800원 | **4,000원** |

### 11.3 수익 다각화: AdSense + 제휴 마케팅

> **소스**: `src/step02/revenue_structure.py` (line 8~67)

**수익 믹스 목표**: AdSense **75%** : 제휴 마케팅 **25%**

| 채널 | 제휴 상품 | 유형 | 단가 | 클릭률(초기/성장) | 전환율 |
|------|----------|------|------|-----------------|-------|
| CH1 | 증권사 계좌 개설 | CPA | 15,000원 | 0.3%/0.8% | 20% |
| CH2 | 부동산 강의/청약 앱 | CPA | 20,000원 | 0.4%/0.9% | 15% |
| CH3 | 심리학 도서 | CPS | 20,000원 × 5% | 0.3%/0.8% | 10% |
| CH4 | 미스터리 도서/공포 OTT | CPA | 8,000원 | 0.5%/1.2% | 10% |
| CH5 | 밀리터리 도서/전쟁 게임 | CPS | 25,000원 × 5% | 0.4%/1.0% | 12% |
| CH6 | 과학 키트/온라인 강의 | CPA | 12,000원 | 0.4%/1.0% | 15% |
| CH7 | 역사 도서/역사 여행 | CPS | 18,000원 × 5% | 0.4%/1.0% | 15% |

**제휴 수익 공식**: `views × click_rate × purchase_conversion_rate × price × commission`

### 11.4 영상별 수익 극대화 정책

> **소스**: `data/channels/{CH}/revenue_policy.json`

| 채널 | 목표 영상 길이 | 미드롤 수 | 미드롤 위치 |
|------|--------------|----------|-----------|
| CH1, CH2, CH3 | 660~780초 (11~13분) | 3개 | 35% / 65% / 85% |
| CH4 | 600~720초 (10~12분) | 3개 | 30% / 60% / 85% |
| CH5 | 660~840초 (11~14분) | 3개 | 33% / 62% / 85% |
| CH6, CH7 | 600~780초 (10~13분) | 3개 | 33% / 62% / 85% |

모든 채널: `midroll_buffer_before_sec: 30` (미드롤 전 30초 버퍼)

### 11.5 운영 비용 구조

| 채널 | 월간 운영비 |
|------|-----------|
| CH1 | 80,000원 |
| CH2~CH7 | 각 100,000원 |
| **7채널 합산** | **680,000원/월** |

### 11.6 수익 시뮬레이션 (안정화 Phase 기준)

| 채널 | RPM | 월 편수 | 편당 필요 조회수 | 월 AdSense(추정) | 월 제휴 합산 |
|------|-----|---------|----------------|----------------|------------|
| CH1 | 7,000원 | 10편 | ~28,600회 | ~2,000,000원 | + 500,000원 |
| CH2 | 6,000원 | 10편 | ~33,300회 | ~2,000,000원 | + 600,000원 |
| CH3 | 4,000원 | 10편 | ~50,000회 | ~2,000,000원 | + 300,000원 |
| CH4 | 3,500원 | 12편 | ~47,600회 | ~2,000,000원 | + 400,000원 |
| CH5 | 3,500원 | 12편 | ~47,600회 | ~2,000,000원 | + 350,000원 |
| CH6 | 4,000원 | 10편 | ~50,000회 | ~2,000,000원 | + 350,000원 |
| CH7 | 4,000원 | 10편 | ~50,000회 | ~2,000,000원 | + 350,000원 |

*(AdSense 75% 기준 역산, 잔여 25%는 제휴 수익으로 보완)*

---

## 12. Data Model

### 12.1 Supabase 테이블 스키마 (9개)

> **소스**: `scripts/supabase_schema.sql`

#### `channels` — 채널 마스터

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | TEXT (PK) | CH1~CH7 |
| `category` | TEXT | economy/realestate/psychology 등 |
| `category_ko` | TEXT | 경제/부동산/심리 등 |
| `youtube_channel_id` | TEXT | YouTube 채널 ID |
| `launch_phase` | INT | 1~3 |
| `status` | TEXT | active/inactive |
| `rpm_proxy` | INT | RPM 안정화 목표값 (원) |
| `revenue_target_monthly` | INT | 월 순이익 목표 (원) |
| `monthly_longform_target` | INT | 월간 Long-form 목표 편수 |
| `monthly_shorts_target` | INT | 월간 Shorts 목표 편수 |
| `subscriber_count` | INT | 구독자 수 |
| `algorithm_trust_level` | TEXT | COLD/WARMING/ACTIVE |

#### `pipeline_runs` — 파이프라인 실행 기록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | TEXT (PK) | run_{CH}_{timestamp} |
| `channel_id` | TEXT (FK → channels) | 채널 ID |
| `run_state` | TEXT | PENDING/RUNNING/COMPLETED/FAILED |
| `topic_title` | TEXT | 재해석된 주제 제목 |
| `topic_score` | REAL | 트렌드 점수 (0~100) |
| `is_trending` | BOOL | 트렌딩 여부 |
| `created_at` | TIMESTAMPTZ | 시작 시각 |
| `completed_at` | TIMESTAMPTZ | 완료 시각 |

#### `kpi_48h` — 48시간 KPI

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `run_id` | TEXT (FK) | 파이프라인 실행 ID |
| `views` | INT | 조회수 |
| `ctr` | REAL | 클릭률 (%) |
| `avg_view_percentage` | REAL | 평균 시청률 (%) |
| `avg_view_duration_sec` | INT | 평균 시청 시간 (초) |
| `algorithm_stage` | TEXT | PRE-ENTRY/SEARCH-ONLY/BROWSE-ENTRY/ALGORITHM-ACTIVE |

#### `revenue_monthly` — 월간 수익

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `channel_id` + `month` | — | UNIQUE 조합 |
| `adsense_krw` | INT | AdSense 수익 (원) |
| `affiliate_krw` | INT | 제휴 수익 (원) |
| `operating_cost` | INT | 운영비 (원) |
| `net_profit` | INT | 순이익 (원) |
| `target_achieved` | BOOL | 200만원 달성 여부 |

#### `risk_monthly` — 월간 리스크

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `risk_level` | TEXT | HIGH/LOW |
| `risks` | TEXT[] | 위험 요소 배열 |
| `target` | INT | 목표 (default 2,000,000) |

#### `sustainability` — 지속가능성

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `topics_remaining_estimate` | INT | 잔여 주제 추정치 |
| `depletion_risk` | TEXT | HIGH/MEDIUM/LOW |

#### `learning_feedback` — 학습 피드백

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `ctr` | REAL | CTR |
| `avp` | REAL | 평균 시청률 |
| `algorithm_stage` | TEXT | 알고리즘 단계 |
| `preferred_title_mode` | TEXT | authority/curiosity/benefit |
| `revenue_on_track` | BOOL | 수익 목표 달성 추세 |

#### `quota_daily` — 일간 쿼터

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `date` + `service` | — | UNIQUE 조합 |
| `images_generated` | INT | 이미지 생성 수 |
| `cache_hit_rate` | REAL | 캐시 히트율 |
| `quota_used` | INT | 사용 쿼터 |
| `cost_krw` | INT | 비용 (원) |

#### `trend_topics` — 트렌드 주제

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `reinterpreted_title` | TEXT | 채널에 맞게 재해석된 제목 |
| `score` | REAL | 트렌드 점수 |
| `grade` | TEXT | auto/review/rejected (default: review) |
| `is_trending` | BOOL | 트렌딩 여부 |
| `topic_type` | TEXT | trending/evergreen/series |

**Realtime 활성화**: `pipeline_runs`, `kpi_48h`, `revenue_monthly`

**RLS 정책**:
- `anon` 역할: SELECT만 허용 (읽기 전용)
- `service_role` 키: 전체 CRUD (백엔드 파이프라인 전용)

### 12.2 로컬 JSON 파일 구조

```
data/
├── global/
│   ├── channel_registry.json          ← Step00 (채널 마스터)
│   ├── api_quota_policy.json          ← 쿼터 정책
│   ├── review_capacity_policy.json    ← 리뷰 용량 정책
│   ├── monthly_plan/{YYYY-MM}/        ← Step04 (포트폴리오)
│   ├── quota/                         ← 일간 쿼터 추적
│   ├── cache/diskcache/               ← Gemini 응답 캐시
│   ├── memory_store/                  ← Step13 학습 메모리
│   ├── revenue/                       ← Step14 수익 집계
│   ├── risk/                          ← Step16 리스크
│   ├── sustainability/                ← Step17 지속성
│   └── step13_pending/               ← 48h KPI 대기 큐
├── channels/{CH}/
│   ├── channel_baseline.json          ← Step01
│   ├── cashflow_plan.json             ← Step01
│   ├── rpm_reality.json               ← Step02
│   ├── revenue_structure_policy.json  ← Step02
│   ├── algorithm_policy.json          ← Step03
│   ├── style_policy_master.json       ← Step06
│   └── revenue_policy.json            ← Step07
└── knowledge_store/{CH}/
    ├── discovery/raw/assets.jsonl     ← Step05 트렌드 원본
    ├── reports/gate_stats.json        ← Step05 통계
    ├── packages/{topic}.json          ← KnowledgePackage
    └── series/series_{topic}.json     ← Step15 시리즈

runs/{CH}/{run_id}/
├── manifest.json                      ← 실행 상태/이력
├── decision_trace.json                ← 의사결정 추적
├── observability.json                 ← 관측성 데이터
├── reflection.json                    ← 실행 후 회고
├── cost.json                          ← 비용 기록
├── step08/
│   ├── script.json                    ← 스크립트
│   ├── video.mp4                      ← 최종 영상
│   ├── narration.wav                  ← 나레이션
│   ├── subtitles.srt                  ← 자막
│   ├── images/                        ← 생성 이미지
│   ├── clips/                         ← 섹션별 MP4
│   ├── title.json, description.txt, tags.json
│   ├── render_report.json             ← 렌더 리포트
│   ├── artifact_hashes.json           ← SHA-256 무결성
│   └── manim_stability_report.json    ← Manim 안정성
├── step08s/                           ← Shorts (3편)
├── step11/qa_result.json              ← QA 결과
├── step12/
│   ├── publish_receipt.json           ← 업로드 영수증
│   ├── kpi_48h.json                   ← KPI 결과
│   └── algorithm_stage_assessment.json
└── step13/
    ├── variant_performance.json       ← A/B 테스트 결과
    └── next_policy_update.json        ← 다음 정책 업데이트
```

---

## 13. Quality Assurance

### 13.1 QA 게이트 5개 검증 항목

> **소스**: `src/step11/qa_gate.py`

```
QA 통과 조건: 아래 5개 항목 모두 AND

1. 애니메이션 품질
   ✓ video.mp4 존재
   ✓ 파일 크기 > 0
   ✓ hook 애니메이션이 10초 이내 위치

2. Gemini Vision QA (5프레임 샘플링: 5%/25%/50%/75%/90%)
   ✓ 캐릭터 일관성 (일관된 외형)
   ✓ 텍스트 가독성 (자막/제목 명확)
   ✓ 부적절 콘텐츠 없음
   ✓ 전반적 품질 기준 충족

3. YouTube 정책 준수
   ✓ 채널별 면책조항 키 존재
   ✓ ai_label 존재

4. 제휴 수익 공식
   ✓ affiliate.purchase_rate_applied > 0

5. 수동 리뷰 (채널별 차별화)
   CH1/CH2/CH4: REVIEW_REQUIRED (SLA 24시간 내 승인 필요)
   CH3: REVIEW_CONDITIONAL (조건부)
   CH5/CH6/CH7: 자동 통과
```

### 13.2 학습 피드백 루프

> **소스**: `src/step13/learning_feedback.py`

```
YouTube Analytics KPI (48h 후 수집)
          ↓
승리 패턴 추출 (CTR ≥ 6.0% AND AVP ≥ 50.0%)
          ↓
winning_animation_patterns 업데이트 (최근 50건 유지)
          ↓
topic_priority_bias.json 갱신
          ↓
algorithm_policy.json Phase 승격 검토
(단방향, 강등 없음)
```

### 13.3 A/B 테스트 (제목 3종)

| 변형 | 전략 | 목적 |
|------|------|------|
| **authority** | "전문가/연구 결과 기반 제목" | 신뢰도 기반 클릭 유도 |
| **curiosity** | "~의 충격적인 진실" 형식 | 호기심 기반 클릭 유도 |
| **benefit** | "~하는 방법/알면 달라지는~" | 실용성 기반 클릭 유도 |

CTR 기준 승자 선택 → `variant_performance.json` 기록 → 다음 영상 정책에 반영

초기 가중치: authority 35% / curiosity 45% / benefit 20%

### 13.4 Manim 안정성 모니터링

`manim_stability_report.json`에서 `fallback_rate > 50%`이면 HITL(Human-In-The-Loop) 필요 신호 발생 → `decision_trace.json`에 기록

---

## 14. Success Metrics & KPIs

### 14.1 수익 지표

| 지표 | 측정 기준 | 목표값 |
|------|----------|--------|
| 채널당 월 순이익 | `net_profit = adsense + affiliate - operating_cost` | **2,000,000원** |
| 전체 월 순이익 | 7채널 합산 | **14,000,000원** |
| RPM 실측값 | YouTube Analytics revenue / views × 1000 | 채널별 Proxy값 달성 |

### 14.2 알고리즘 지표

| 지표 | 측정 방법 | 목표 임계값 |
|------|----------|-----------|
| **CTR** (클릭률) | impressions 대비 clicks | **5.5%** 이상 (BROWSE-ENTRY 진입) |
| **AVP** (평균 시청률) | avg_view_percentage | **45%** 이상 |
| **AVD** (평균 시청 시간) | avg_view_duration_sec | **280초** 이상 |

**알고리즘 4단계 진입 조건**:

| 단계 | 달성 조건 |
|------|---------|
| PRE-ENTRY | 기본 (신채널) |
| SEARCH-ONLY | CTR 4~5.5%, 검색 유입 위주 |
| BROWSE-ENTRY | CTR ≥ 5.5%, AVP ≥ 45%, Browse 피드 ≥ 20% |
| ALGORITHM-ACTIVE | Views ≥ 100,000 또는 CTR ≥ 8% |

### 14.3 생산성 지표

| 지표 | 목표 |
|------|------|
| Long-form 월 생산량 | **74편** (7채널 합산) |
| Shorts 월 생산량 | **230편** (Long-form에서 자동 추출) |
| 총 콘텐츠 | **304편/월** |
| 트렌드 대응 시간 | **72시간 이내** (CH4: 48시간 이내) |

### 14.4 비용 효율 지표

| 지표 | 목표 |
|------|------|
| 실행당 API 비용 | **$5.00 이하** |
| Gemini 캐시 히트율 | 최대화 (비용 절감) |
| YouTube 쿼터 사용률 | **95% 이하** (9,500 유닛/일 이내) |
| Gemini 이미지 사용률 | **80% 이하** (400장/일 이내) |

### 14.5 품질 지표

| 지표 | 목표 |
|------|------|
| QA 게이트 통과율 | **80%** 이상 |
| Manim fallback rate | **50% 미만** |
| 수동 리뷰 SLA 준수 | 트렌드 24시간, 일반 48시간 이내 |

---

## 15. Risk Management

### 15.1 수익 리스크

| 리스크 | 감지 조건 | 대응 전략 |
|--------|----------|---------|
| RPM 하락 | `rpm_actual < rpm_floor` | 트렌드 콘텐츠 비중 +10%p |
| 조회수 부진 | `views < target_per_video` | Shorts 편수 +10편 증가 |
| 알고리즘 진입 실패 | 3개월 경과 후 PRE-ENTRY 유지 | 썸네일/제목 A/B 테스트 강화 |
| 채널 리스크 HIGH | `net_profit < 2,000,000원` | Step16 리스크 대시보드 경보 |

### 15.2 주제 고갈 리스크

> **소스**: `src/step17/sustainability.py`

| 채널 | 예상 총 주제 | 고갈 리스크 기본값 |
|------|------------|-----------------|
| CH1 경제 | 1,000개 | LOW |
| CH2 부동산 | 800개 | LOW |
| CH3 심리 | 600개 | LOW |
| CH4 미스터리 | 800개 | LOW |
| CH5 전쟁사 | **2,000개** | LOW |
| CH6 과학 | **1,500개** | LOW |
| CH7 역사 | **2,000개** | LOW |

**고갈 판정**: 잔여 < 50개 → HIGH, 잔여 < 150개 → MEDIUM

**확장 후보 채널** (분기별 평가):

| 카테고리 | 예상 RPM | 이유 |
|---------|---------|------|
| 법률/생활법률 | 5,500원 | 고RPM, 실용적 수요 |
| 세금/절세 | 6,000원 | 최고 RPM, 재테크 관심 |
| 환경/에너지 | 3,500원 | 글로벌 트렌드 |

### 15.3 API 쿼터 리스크

| API | 일일 한도 | 경고 임계값 | 차단 임계값 | 대응 |
|-----|---------|-----------|-----------|------|
| **Gemini 이미지** | 500장 | 400장 | 500장 | SD XL 폴백 또는 중단 |
| **YouTube** | 10,000 유닛 | 8,000 유닛 | 9,500 유닛 | 이연 등록 |
| **yt-dlp** | RPM 30 | — | 차단 감지 | 5분 대기 후 재시도 |

### 15.4 비용 통제 메커니즘

```
실행 전: pre_cost_estimator.check_cost_limit()
  → 주제당 예상 비용 > $5.00 시 차단 (skip)
  → 기준: API 15회($0.015) + 토큰 5,000개($0.01) = ~$0.025/주제
```

### 15.5 기술 리스크

| 리스크 | 감지 방법 | 대응 |
|--------|---------|------|
| GPU 미가용 | `torch.cuda.is_available()` | Gemini 이미지 API 자동 전환 |
| Manim LaTeX 오류 | AST 분석 + regex | 코드 자동 수정 후 재시도 2회 |
| Manim 과다 fallback | `fallback_rate > 50%` | HITL 트리거, decision_trace 기록 |
| 수동 리뷰 백로그 | `backlog > 7건` | 트렌딩 비율 자동 축소 |

---

## 16. Non-Functional Requirements

### 16.1 성능

| 항목 | 요구사항 |
|------|---------|
| Gemini RPM | 자동 쓰로틀링, 목표 상한 **50 RPM** |
| Gemini 이미지 배치 | 3장씩 처리, 배치 간 2초 딜레이 |
| Manim 실행 타임아웃 | **120초** |
| YouTube 업로드 | Resumable Upload API (대용량 안전) |
| 일 최대 업로드 | **5~6건** (9,500 유닛 / 1,700 유닛) |
| yt-dlp 딜레이 | 10회마다 2초 슬립, 차단 시 5분 대기 |

### 16.2 확장성

- **채널 추가**: `config.py` CHANNELS 상수에 항목 추가만으로 가능
- **Launch Phase**: `month_number` 기반 점진적 채널 활성화
- **캐시 자동 정리**: diskcache TTL 24h 자동 만료, 500MB 상한
- **Step 독립성**: 각 Step이 파일 기반으로 통신 → 독립 테스트/재실행 가능

### 16.3 보안

| 항목 | 구현 |
|------|------|
| **API 키 관리** | `.env` 파일 전용, 소스코드 하드코딩 금지 |
| **Supabase RLS** | anon 키: SELECT only, service_role: 전체 CRUD |
| **웹 인증** | httpOnly 쿠키, secure, sameSite:strict, 7일 유효 |
| **파일 잠금** | `filelock.FileLock` (동시 접근 방지) |
| **OAuth2** | YouTube 업로드용 토큰 `credentials/{CH}_token.json` 분리 관리 |

### 16.4 가용성 & 복원력

| 전략 | 구현 |
|------|------|
| **fail-and-continue** | 각 Step 독립 try/except, 실패해도 다음 Step 진행 |
| **폴백 체인** | 모든 핵심 기능에 1~2개 대안 |
| **이연 메커니즘** | YouTube 쿼터 소진 시 다음 실행으로 자동 이연 |
| **Supabase 미연동 대비** | MOCK 데이터 자동 fallback (URL에 'xxxxxxxxxxxx' 포함 시) |
| **개발/프로덕션 분리** | 비밀번호 미설정 시 인증 자동 통과 (개발 환경) |

### 16.5 데이터 무결성

| 항목 | 구현 |
|------|------|
| **원자적 쓰기** | `tempfile → os.replace` (쓰기 중단 시 파일 손상 방지) |
| **동시성 제어** | `filelock.FileLock` (프로세스간 경쟁 방지) |
| **인코딩 통일** | `utf-8-sig` 쓰기 + `utf-8-sig` 읽기 (BOM 처리) |
| **SHA-256 해싱** | `artifact_hashes.json` (영상/나레이션/자막 무결성) |
| **volatile 키 제외** | `sha256_dict()`에서 `created_at`, `updated_at` 제거 후 해싱 |

---

## 17. Monitoring & Observability

### 17.1 로깅 시스템

> **규칙**: `from loguru import logger` 사용, `import logging` 절대 금지

| 항목 | 내용 |
|------|------|
| **로거** | loguru |
| **로그 파일** | `logs/pipeline.log` |
| **로테이션** | 50MB 초과 시 자동 순환 |
| **레벨** | DEBUG/INFO/WARNING/ERROR/CRITICAL |

### 17.2 파이프라인 5중 추적

각 실행(`run_{CH}_{timestamp}`)마다 생성되는 추적 파일:

| 파일 | 추적 내용 |
|------|---------|
| `manifest.json` | 실행 상태, 완료/실패 Step 목록, resume_from 포인트 |
| `decision_trace.json` | 주요 의사결정 이벤트 + 타임스탬프 (HITL 트리거 등) |
| `observability.json` | 시스템 관측 데이터 |
| `reflection.json` | 실행 후 회고/평가 |
| `cost.json` | API 호출 수, 토큰 수, 비용 (USD + KRW) |

### 17.3 에러 추적

| 도구 | 설정 | 비고 |
|------|------|------|
| **Sentry** | `SENTRY_DSN` 환경 변수 | 미설정 시 비활성화 (선택적) |
| **manifest.steps_failed** | 로컬 실패 기록 | 항상 동작 |

### 17.4 실시간 웹 모니터링

| 기능 | 구현 | 트리거 |
|------|------|--------|
| **파이프라인 실시간 상태** | Supabase Realtime (`pipeline_runs` 구독) | RUNNING 상태 변경 |
| **쿼터 대시보드** | `/cost` 페이지, `quota_daily` 테이블 | 수동 조회 |
| **리스크 경보** | `/risk` 페이지 경고 배너 | `risk_level = HIGH` |

### 17.5 Manim 안정성 모니터링

```
마다 영상 생성 후: manim_stability_report.json 생성
  → fallback_rate = 실패 섹션 수 / 전체 Manim 섹션 수
  → fallback_rate > 0.5 (50%) → HITL 필요 플래그
  → decision_trace에 "MANIM_HITL_REQUIRED" 이벤트 기록
```

---

## 18. Deployment & Infrastructure

### 18.1 Docker 배포

> **소스**: `web/Dockerfile`, `web/next.config.ts`

```dockerfile
# 3단계 멀티 스테이지 빌드
Stage 1 (deps):    node:20-alpine + npm ci
Stage 2 (builder): Supabase 환경 변수 ARG 주입 + npm run build
Stage 3 (runner):  standalone 결과물만 복사, 비루트 사용자(nextjs:nodejs), PORT 3000
```

**`next.config.ts` 설정**: `output: 'standalone'`, `NEXT_TELEMETRY_DISABLED=1`

### 18.2 CI/CD

> **소스**: `.github/workflows/ci.yml`

| Job | 트리거 | 내용 |
|-----|--------|------|
| **test-python** | push/PR → main | Python 3.11, GPU 패키지 제외 설치, pytest 실행 |
| **build-web** | push/PR → main | Node.js 20, `npm ci` + `npm run build`, mock Supabase URL |

### 18.3 외부 공개 (ngrok)

```bash
# 고정 도메인: https://cwstudio.ngrok.app → localhost:3000
ngrok start kas-studio
```

설정 파일: `config/ngrok.yml` (고정 도메인 `kas-studio` 터널)

### 18.4 환경 변수 관리

**백엔드 (`.env`)**:

| 변수 | 필수 | 설명 |
|------|------|------|
| `GEMINI_API_KEY` | ✅ | Gemini 텍스트/이미지 생성 |
| `YOUTUBE_API_KEY` | ✅ | YouTube 업로드 및 KPI 수집 |
| `KAS_ROOT` | ✅ | 프로젝트 루트 절대 경로 (config.py 기본값 다름) |
| `CH1_CHANNEL_ID` ~ `CH7_CHANNEL_ID` | ✅ | 7개 채널 YouTube ID |
| `ELEVENLABS_API_KEY` | ❌ | 미설정 시 gTTS 폴백 |
| `SERPAPI_KEY` | ❌ | 미설정 시 해당 소스 스킵 |
| `REDDIT_*` | ❌ | 미설정 시 Reddit 소스 스킵 |
| `NAVER_CLIENT_ID/SECRET` | ❌ | 미설정 시 Naver 소스 스킵 |
| `SENTRY_DSN` | ❌ | 미설정 시 에러 추적 비활성화 |
| `TAVILY_API_KEY` | ❌ | 미설정 시 해당 소스 스킵 |
| `PERPLEXITY_API_KEY` | ❌ | 미설정 시 해당 소스 스킵 |

**웹 (`web/.env.local`)**:

| 변수 | 필수 | 설명 |
|------|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | ❌ | 미설정 시 MOCK 데이터 fallback |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ❌ | 미설정 시 MOCK 데이터 fallback |
| `DASHBOARD_PASSWORD` | ❌ | 미설정 시 인증 자동 통과 (개발 환경) |

### 18.5 Supabase 동기화

```bash
# 전체 동기화 (파이프라인 완료 후)
python scripts/sync_to_supabase.py

# 채널 레지스트리만
python scripts/sync_to_supabase.py channels

# 수익 데이터만
python scripts/sync_to_supabase.py revenue
```

---

## 19. Glossary

| 용어 | 설명 |
|------|------|
| **RPM** | Revenue Per Mille — 조회 1,000회당 수익 (원) |
| **CTR** | Click-Through Rate — 노출 대비 클릭률 (%) |
| **AVP** | Average View Percentage — 영상 평균 시청률 (%) |
| **AVD** | Average View Duration — 평균 시청 시간 (초) |
| **SSOT** | Single Source of Truth — 데이터 단일 출처 원칙. 모든 JSON I/O는 `ssot.read_json()` / `ssot.write_json()`만 사용 |
| **HITL** | Human-In-The-Loop — AI 실패 시 사람이 개입하는 메커니즘 |
| **CPA** | Cost Per Action — 전환(가입/설치)당 제휴 수수료 지급 방식 |
| **CPS** | Cost Per Sale — 판매당 제휴 수수료 지급 방식 (가격 × 수수료율) |
| **RLS** | Row Level Security — Supabase 테이블 행 단위 접근 제어 |
| **Long-form** | 10~14분 길이의 일반 YouTube 영상 |
| **Shorts** | 60초 이하의 YouTube 세로형 짧은 영상 (9:16 비율) |
| **에버그린** | 시간이 지나도 검색 수요가 유지되는 주제 (트렌드와 반대) |
| **KnowledgePackage** | Step05에서 생성하는 구조화된 지식 데이터 단위 (facts, timeline, statistics, sources 포함) |
| **Proxy RPM** | 실측 전 추정 RPM 값. Initial = Proxy × 0.5 |
| **Run ID** | 파이프라인 1회 실행 단위 식별자 (`run_{CH}_{timestamp}`) |
| **Launch Phase** | 채널 점진적 활성화 단계 (1: CH1+CH2, 2: +CH3+CH4, 3: 전체) |
| **Manim** | Python 기반 수학 애니메이션 라이브러리. KAS에서 LaTeX 없이 사용 (pdflatex 미설치 환경) |
| **SD XL** | Stable Diffusion XL — 고해상도 이미지 생성 AI 모델 |
| **LoRA** | Low-Rank Adaptation — SD XL에 채널별 캐릭터를 추가 학습한 어댑터 |
| **diskcache** | Python 디스크 기반 캐시 라이브러리. Gemini API 응답 캐싱에 사용 |
| **Pending 메커니즘** | 업로드 후 48시간을 기다려 KPI를 수집하는 비동기 처리 방식 |
| **deferred_jobs** | YouTube 쿼터 부족으로 이번 실행에 처리 못한 업로드를 다음 실행에 처리하는 큐 |
| **fallback_rate** | Manim 렌더링 실패율. 50% 초과 시 HITL 필요 |
| **PRE-ENTRY** | YouTube 알고리즘 미진입 단계 (신채널 기본 상태) |
| **BROWSE-ENTRY** | YouTube 탐색 피드에 노출되는 알고리즘 진입 단계 |
| **ALGORITHM-ACTIVE** | YouTube 추천 알고리즘이 적극적으로 영상을 배포하는 최상위 단계 |
| **Amber Studio** | KAS 웹 대시보드의 디자인 시스템명. oklch 색공간 + 앰버 골드 primary 색상 |

---

*이 문서는 KAS 프로젝트의 실제 코드(`src/`, `web/`, `data/`, `scripts/`)에서 확인된 사실만을 기반으로 작성되었습니다.*  
*문서 업데이트 시: `git log`, `src/core/config.py`, `scripts/supabase_schema.sql`을 먼저 확인하세요.*
