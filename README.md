# KAS Studio — Knowledge Animation Studio

**AI 기반 YouTube 7채널 영상 자동화 파이프라인**

채널당 월 200만원(총 1,400만원/월) 수익을 목표로 하는 AI 콘텐츠 자동화 시스템.  
트렌드 발굴 → 스크립트/이미지/나레이션 생성 → YouTube 업로드까지 완전 자동화.

---

## 채널 구성

| 채널 | 카테고리 | 론칭 단계 |
|------|----------|-----------|
| CH1  | 경제      | Phase 1   |
| CH2  | 부동산    | Phase 1   |
| CH3  | 심리      | Phase 2   |
| CH4  | 미스터리  | Phase 2   |
| CH5  | 전쟁사    | Phase 3   |
| CH6  | 과학      | Phase 3   |
| CH7  | 역사      | Phase 3   |

---

## 프로젝트 구조

```
ai_stuidio_claude/
├── src/                      # Python 파이프라인 (핵심)
│   ├── pipeline.py           # 월간 파이프라인 진입점
│   ├── core/
│   │   ├── config.py         # 채널/API/경로 SSOT 설정
│   │   ├── ssot.py           # JSON I/O (filelock + atomic write)
│   │   └── pre_cost_estimator.py
│   ├── step00/               # 채널 레지스트리 초기화
│   ├── step01~04/            # 베이스라인·수익·알고리즘·포트폴리오 정책
│   ├── step05/               # 트렌드+지식 수집 (5계층 소스)
│   ├── step06~07/            # 스타일·수익 정책
│   ├── step08/               # 영상 생성 오케스트레이터 [KAS-PROTECTED]
│   │   ├── __init__.py       # run_step08() 메인 오케스트레이터
│   │   ├── script_generator.py
│   │   ├── image_generator.py
│   │   ├── sd_generator.py   # SD XL + LoRA (GPU)
│   │   ├── narration_generator.py
│   │   ├── subtitle_generator.py
│   │   ├── ffmpeg_composer.py
│   │   ├── motion_engine.py
│   │   ├── scene_composer.py
│   │   └── metadata_generator.py  # 제목/설명/태그 생성
│   ├── step09/               # BGM 오버레이
│   ├── step10/               # 제목/썸네일 배리언트
│   ├── step11/               # QA 게이트
│   ├── step12/               # YouTube 업로드 + 48h KPI 수집
│   ├── step13/               # 학습 피드백 + Phase 승격 판정
│   ├── step14/               # 수익 추적
│   ├── step16/               # 리스크 제어
│   └── step17/               # 지속성 분석
│
├── web/                      # Next.js 웹 대시보드
│   ├── app/
│   │   ├── page.tsx          # KPI 홈 (서버 컴포넌트)
│   │   ├── trends/           # 트렌드 주제 관리 (승인/거부)
│   │   ├── revenue/          # 수익 추적
│   │   ├── risk/             # 리스크 모니터링
│   │   ├── learning/         # 학습 피드백
│   │   ├── cost/             # API 비용/쿼터
│   │   ├── channels/[id]/    # 채널 상세 + KPI 히스토리
│   │   └── login/            # 패스워드 보호 로그인
│   ├── components/
│   │   ├── sidebar-nav.tsx
│   │   ├── realtime-pipeline-status.tsx  # Supabase Realtime
│   │   └── ui/               # shadcn/ui 컴포넌트
│   ├── Dockerfile            # Docker standalone 빌드
│   └── proxy.ts              # 패스워드 미들웨어 (Next.js 16)
│
├── scripts/
│   ├── sync_to_supabase.py   # JSON → Supabase DB 동기화
│   ├── supabase_schema.sql   # DB 스키마 (RLS 포함)
│   └── preflight_check.py   # 환경 점검
│
├── tests/                    # pytest 테스트 (140개+)
├── .github/workflows/ci.yml  # GitHub Actions CI
└── requirements.txt          # Python 의존성
```

---

## 빠른 시작

### 환경 설정

```bash
# 1. 의존성 설치 (GPU 패키지 제외)
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력:
# GEMINI_API_KEY, YOUTUBE_API_KEY, CH1_CHANNEL_ID ~ CH7_CHANNEL_ID
# KAS_ROOT (프로젝트 절대 경로)
```

### 파이프라인 실행

```bash
# 월간 파이프라인 (month_number: 1~12)
python -m src.pipeline 1

# 환경 점검
python scripts/preflight_check.py

# Supabase 동기화
python scripts/sync_to_supabase.py          # 전체
python scripts/sync_to_supabase.py channels # 채널만
```

### 웹 대시보드

```bash
cd web

# 개발 서버
npm run dev       # http://localhost:3000

# 프로덕션 빌드
npm run build

# Docker 빌드 & 실행
docker build \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=your-url \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key \
  -t kas-studio .

docker run -p 3000:3000 \
  -e DASHBOARD_PASSWORD=your-password \
  -e NEXT_PUBLIC_SUPABASE_URL=your-url \
  -e NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key \
  kas-studio
```

---

## 주요 명령

```bash
# 테스트
pytest tests/ -q            # 전체
pytest tests/ -q --tb=short # 실패 시 상세

# ngrok 외부 공개 (고정 도메인)
ngrok start kas-studio      # https://cwstudio.ngrok.app → localhost:3000
```

---

## 환경 변수

### 백엔드 (`.env`)

| 변수 | 설명 |
|------|------|
| `KAS_ROOT` | 프로젝트 절대 경로 |
| `GEMINI_API_KEY` | Gemini API (스크립트/이미지) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 |
| `CH1_CHANNEL_ID` ~ `CH7_CHANNEL_ID` | 채널별 YouTube ID |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase service_role 키 (백엔드 쓰기용) |
| `ELEVENLABS_API_KEY` | 나레이션 (미설정 시 gTTS 폴백) |
| `SENTRY_DSN` | 에러 추적 (선택) |

### 웹 (`web/.env.local`)

| 변수 | 설명 |
|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키 (읽기 전용) |
| `DASHBOARD_PASSWORD` | 대시보드 접근 패스워드 (미설정 시 공개) |

---

## 아키텍처

```
파이프라인 실행
    │
    ├── runs/ JSON 파일 (SSOT)
    │
    └── scripts/sync_to_supabase.py
              │
              ▼
        Supabase PostgreSQL (9개 테이블, RLS 적용)
              │
              ▼
        web/ Next.js 대시보드
        (Supabase Realtime 구독으로 자동 갱신)
```

### 데이터 흐름 규칙

- **모든 JSON I/O**: `ssot.read_json()` / `ssot.write_json()` 사용 (filelock + atomic write)
- **로깅**: `from loguru import logger` (표준 `logging` 금지)
- **채널 설정 SSOT**: `src/core/config.py`가 단일 출처
- **KPI 수집 지연**: 업로드 후 즉시 수집 금지, 48시간 pending 메커니즘 사용

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 파이프라인 | Python 3.11, Google Gemini, YouTube Data API |
| 영상 생성 | Manim, FFmpeg, SD XL + LoRA, ElevenLabs |
| 웹 대시보드 | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui |
| 데이터베이스 | Supabase PostgreSQL (RLS, Realtime) |
| 모니터링 | Loguru, Sentry SDK |
| CI/CD | GitHub Actions (pytest + npm build) |
| 배포 | Docker standalone, ngrok, Vercel |
