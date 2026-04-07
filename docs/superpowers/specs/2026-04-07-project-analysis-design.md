# KAS 프로젝트 종합 분석 — 개선/강화/추가 설계서

> **날짜**: 2026-04-07 | **버전**: 1.0 | **상태**: 승인됨 | **분석 범위**: 전체 시스템 (9개 영역, 55개 항목)

## Context

KAS(Knowledge Animation Studio)는 AI 기반 7채널 YouTube 자동화 파이프라인이다. 현재 개발 단계이며 실제 YouTube 업로드 전이다. 35개 Python 모듈(4,728줄), 14개 웹 페이지, 4개 Sub-Agent, CI/CD 기본 구성을 갖추고 있으나, 프로덕션 론칭을 위해 안정성/보안/품질/운영 자동화 전반에서 개선이 필요하다.

이 문서는 **7개 영역, 40+ 항목**의 개선/강화/추가 사항을 영역별로 상세 분석한다.

---

## 영역 1: 백엔드 파이프라인 (`src/`)

### 개선점 (기존 문제 수정)

#### 1.1 [P0] Step08 Resume 메커니즘
- **현재**: `src/step08/__init__.py`의 `run_step08()`이 모놀리식. 중간 실패(예: FFmpeg concat) 시 스크립트 생성부터 전부 재시작. 10-20분의 Gemini API 호출과 비용 낭비
- **제안**: `step08_progress.json` 체크포인트 도입. 각 하위 단계(script, images, manim, narration, subtitles, compose) 완료 시 기록. 재시작 시 완료된 단계 스킵
- **영향도**: High — API 비용 절감 + 안정성 향상
- **파일**: `src/step08/__init__.py`, 신규 `src/step08/checkpoint.py`

#### 1.2 [P0] FFmpeg 반환값 검증
- **현재**: `src/step08/__init__.py` L162, 169, 175에서 `concat_clips`, `add_narration`, `add_subtitles` 반환값(bool) 미검증. False 반환 시에도 다음 단계 진행 → 빈/손상 영상이 QA로 전달
- **제안**: 각 FFmpeg 호출 후 반환값 + 출력 파일 존재/크기 검증. 실패 시 `RuntimeError` 발생
- **영향도**: High — 손상 영상 업로드 방지
- **파일**: `src/step08/__init__.py` (L162-178)

#### 1.3 [P1] days_since_trending 실제값 반영
- **현재**: `src/step05/trend_collector.py` L263에서 `score_topic()` 호출 시 `days_since_trending` 미전달. `scorer.py` L52 기본값 0 → 긴급도 점수 항상 1.0 (15% 가중치 무의미화)
- **제안**: 주제 최초 발견 시점을 `knowledge_store/{channel}/first_seen.json`에 기록. 수집 시 경과 일수 계산하여 `score_topic()`에 전달
- **영향도**: Medium
- **파일**: `src/step05/trend_collector.py`, `src/step05/scorer.py`

#### 1.4 [P1] SD Gemini 폴백 쿼터 카운팅
- **현재**: `src/step08/sd_generator.py` L96-126 `_generate_gemini_image()`가 `record_image()` 호출 없이 Gemini API 사용. 일 500장 한도 카운팅 누락
- **제안**: `from src.quota.gemini_quota import record_image, record_request` 추가 및 호출
- **영향도**: Medium
- **파일**: `src/step08/sd_generator.py`

#### 1.5 [P1] YouTube 쿼터 리셋 타임존 수정
- **현재**: `src/quota/youtube_quota.py` L32에서 UTC 기준 날짜 비교. YouTube API는 PST 기준 리셋 → 최대 7-8시간 불일치
- **제안**: `datetime.now(ZoneInfo("America/Los_Angeles"))` 사용
- **영향도**: Medium
- **파일**: `src/quota/youtube_quota.py`

#### 1.6 [P1] deferred_jobs 만료/최대 재시도
- **현재**: `src/pipeline.py` L132-170 `_run_deferred_uploads()`가 무한 재시도. 실패 job이 `still_deferred`에 재추가되며 무한 성장
- **제안**: `max_retries: 3`, `retry_count`, `expires_at`(72시간) 필드 추가. 만료/초과 시 스킵
- **영향도**: Medium
- **파일**: `src/quota/youtube_quota.py`, `src/pipeline.py`

### 강화점 (기존 기능 향상)

#### 1.7 [P1] 이미지/Manim/모션 병렬 처리
- **현재**: `sd_generator.py` L154-188 섹션별 순차 이미지 생성, `motion_engine.py` L160-169 순차 Ken Burns, `__init__.py` L119-136 순차 Manim 렌더링. 6섹션 기준 12-18분 소요
- **제안**: `concurrent.futures.ThreadPoolExecutor` (I/O-bound) + `ProcessPoolExecutor` (CPU-bound Manim) 적용. 3-4배 가속 기대
- **영향도**: High — Step08 소요 시간 18분→5분
- **파일**: `src/step08/__init__.py`, `src/step08/sd_generator.py`, `src/step08/motion_engine.py`

#### 1.8 [P2] 트렌드 수집 Layer 1-4 병렬화
- **현재**: `src/step05/trend_collector.py` L220-224에서 Layer 1-4 순차 실행. 각 소스 10초 타임아웃 누적
- **제안**: `ThreadPoolExecutor`로 4개 레이어 동시 수집 (독립적)
- **영향도**: Medium — Step05 소요 30s→10s
- **파일**: `src/step05/trend_collector.py`

#### 1.9 [P2] genai.configure 중앙화
- **현재**: 7개 파일에서 `genai.configure(api_key=GEMINI_API_KEY)` 반복 호출
- **제안**: `src/core/gemini_client.py` 싱글턴 생성. 모든 모듈이 여기서 import
- **영향도**: Low — 코드 품질
- **파일**: 신규 `src/core/gemini_client.py`, 기존 7개 파일

### 추가점 (신규 기능)

#### 1.10 [P1] knowledge_store 3단계 지식 수집 연동
- **현재**: `src/step05/knowledge_store.py`의 `collect_knowledge()` (Tavily+Perplexity+Gemini 리서치, Wikipedia+Scholar 보강, 팩트체크)가 구현되어 있으나 `pipeline.py`에서 호출하지 않음. `script_generator.py`에 `knowledge_pkg=None`으로 전달
- **제안**: 파이프라인에서 `reinterpret_trend()` 후 `collect_knowledge()` 호출, 결과를 `generate_script()`에 전달 → 팩트 기반 스크립트 생성 활성화
- **영향도**: High — 콘텐츠 품질 근본적 향상
- **파일**: `src/pipeline.py`, `src/step05/knowledge_store.py`, `src/step08/script_generator.py`

#### 1.11 [P1] 자동 스케줄링 시스템
- **현재**: `python -m src.pipeline {month}` 수동 실행. `register_daily_task.ps1`은 Windows 전용
- **제안**: `src/scheduler.py` (schedule 라이브러리 또는 시스템 cron) 도입. 일간/주간/월간 트리거 + Sub-Agent 통합
- **영향도**: High — 진정한 자동화
- **파일**: 신규 `src/scheduler.py`

---

## 영역 2: 웹 대시보드 — 기능/데이터 (`web/`)

### 개선점

#### 2.1 [P1] settings 페이지 동적 데이터 연동
- **현재**: `web/app/settings/page.tsx`가 완전 하드코딩. RPM 값이 config.py와 불일치 (CH2: 6000 vs 7000)
- **제안**: `/api/settings/channels` 엔드포인트 생성, config.py 또는 Supabase에서 동적 로드
- **영향도**: Medium
- **파일**: `web/app/settings/page.tsx`, 신규 `web/app/api/settings/channels/route.ts`

#### 2.2 [P2] learning 바이어스 탭 실제 데이터 연동
- **현재**: 바이어스 레이더 차트가 하드코딩 `[72, 58, 85, 64, 79]` → "분석 결과"처럼 보여 잘못된 의사결정 위험
- **제안**: Supabase `learning_feedback` 기반 실제 분석값 표시. 미연동 시 "데이터 미수집" 명시
- **영향도**: Medium
- **파일**: `web/app/learning/page.tsx`, `web/app/api/learning/kpi/route.ts`

#### 2.3 [P2] monitor 폴링 조건부 전환
- **현재**: 3초 polling이 파이프라인 미실행 시에도 계속. 불필요한 네트워크/서버 부하
- **제안**: `active === true` → 3초, `active === false` → 30초 또는 정지. `visibilityState` 기반 탭 비활성 시 정지
- **영향도**: Low
- **파일**: `web/app/monitor/page.tsx`

### 강화점

#### 2.4 [P2] 인라인 스타일 → CSS 변수/Tailwind 통합
- **현재**: 14개 tsx 파일에서 254회 `style={` 사용. `#1a0505`, `#9b6060` 등 30+ 곳 반복
- **제안**: `globals.css`에 semantic 토큰 추가 (`--kas-text-primary` 등). Tailwind 유틸리티 클래스로 교체
- **영향도**: Medium — 유지보수성
- **파일**: `web/app/globals.css`, 14개 tsx 파일

#### 2.5 [P3] 공유 Tab 컴포넌트 추출
- **현재**: 5+ 페이지에서 동일 패턴의 커스텀 탭 바를 인라인 구현
- **제안**: `web/components/ui/kas-tabs.tsx` 공유 컴포넌트 생성. ARIA 접근성 포함
- **영향도**: Low — DRY
- **파일**: 신규 `web/components/ui/kas-tabs.tsx`, 5개 페이지

#### 2.6 [P3] 서버 컴포넌트 최적화
- **현재**: 12개 페이지가 `'use client'`. settings, risk 등 정적 페이지도 클라이언트 렌더링
- **제안**: 인터랙션 없는 페이지를 서버 컴포넌트로 전환, 인터랙티브 섹션만 분리
- **영향도**: Medium — 초기 로드 속도
- **파일**: 해당 페이지들

### 추가점

#### 2.7 [P2] ARIA 접근성 보강
- **현재**: 커스텀 탭에 `role="tablist"`, `aria-selected` 없음. `<div onClick>` 키보드 접근 불가. 색상 대비 WCAG AA 미달 가능
- **제안**: WAI-ARIA 1.2 tab 패턴 적용, 키보드 내비게이션, 포커스 관리
- **영향도**: Medium
- **파일**: 모든 탭 사용 페이지, 공유 Tab 컴포넌트

#### 2.8 [P1] 알림(notifications) UI + API
- **현재**: `notifier.py`가 `notifications.json`에 기록하지만, 이를 읽는 웹 UI/API 없음. Phase 승격 등 알림이 사용자에게 전달되지 않음
- **제안**: `/api/notifications` 엔드포인트 + 사이드바 알림 벨 컴포넌트 + 미읽음 카운트
- **영향도**: High — 운영 인지도 향상
- **파일**: 신규 `web/app/api/notifications/route.ts`, 신규 `web/components/notification-bell.tsx`

---

## 영역 3: 대시보드 UX 재구성

### 개선점 (사용자 여정 단절 해소)

#### 3.1 [P0] `/runs/{channelId}` 목록 페이지 신규 생성
- **현재**: 홈 채널 카드가 `/runs/{channelId}`로 링크하지만 해당 페이지 미존재 → 404. Run 상세의 "뒤로가기"도 동일 404
- **제안**: `web/app/runs/[channelId]/page.tsx` 생성. 채널별 전체 Run 목록 (상태, 주제, 날짜, QA 통과 여부) + 각 Run으로의 링크
- **영향도**: Critical — 핵심 네비게이션 체인 복원
- **파일**: 신규 `web/app/runs/[channelId]/page.tsx`

#### 3.2 [P1] 페이지 간 상호 링크 강화
- **현재**: 대부분 페이지가 사이드바로만 이동 가능. 관련 정보 교차 확인에 항상 사이드바 경유
- **제안**: 다음 링크 추가:
  - `/trends` → 주제별 해당 Run 링크 (주제가 실행되었을 경우)
  - `/qa` → Run 상세 직접 링크 (`/runs/{channelId}/{runId}`)
  - `/channels/{id}` → 실행 이력 테이블의 각 Run ID를 클릭 가능 링크로
  - `/revenue`, `/risk` → 채널명 클릭 시 `/channels/{id}`로 이동
  - `/learning` KPI 테이블 → 채널 링크
- **영향도**: High — 자연스러운 사용자 흐름 회복
- **파일**: 해당 5개+ 페이지

#### 3.3 [P1] 하드코딩 데이터 명확한 표시 또는 제거
- **현재**: 학습 바이어스 레이더 차트(고정값), 승리 패턴 5개(고정 가이드라인)이 실제 분석 결과처럼 표시 → 잘못된 의사결정 위험
- **제안**: 
  - 실제 데이터 미연동 시 "분석 데이터 미수집 — 파이프라인 실행 후 표시됩니다" 플레이스홀더 표시
  - 또는 "참고 가이드라인 (고정값)" 라벨 명시
- **영향도**: Medium — 의사결정 정확성
- **파일**: `web/app/learning/page.tsx`

### 강화점 (화면 재배치/재구성)

#### 3.4 [P1] 홈 대시보드 정보 계층 재구성
- **현재**: 홈에 KPI 4개 + 수익 7열 그리드 + 파이프라인 타임라인 + 채널 카드 7개가 혼재. 같은 페이지에서 "채널별 수익 현황 그리드"와 "채널 카드의 수익 Progress"가 중복
- **제안**:
  - **1단: 오늘의 상태** — HITL 대기 건수, 실행 중 파이프라인, 긴급 리스크 (액션 필요 요약)
  - **2단: 핵심 KPI** — 월 달성률, 활성 채널, 총수익 (현재와 유사하되 간소화)
  - **3단: 채널 카드** — 7채널 각각의 상태/수익/최근Run (수익 그리드 중복 제거)
  - **4단: 최근 활동** — 파이프라인 타임라인 + 최근 HITL 이벤트
- **영향도**: High — 운영자 일일 워크플로우 효율화
- **파일**: `web/app/page.tsx`

#### 3.5 [P1] 사이드바 네비게이션 그룹 재구성
- **현재**: "대시보드" 그룹에 9개 메뉴가 플랫하게 나열. 운영자 워크플로우와 메뉴 순서가 불일치
- **제안**: 워크플로우 기반 3단 그룹핑:
  - **📊 운영 현황**: 전체 KPI, 파이프라인 모니터, QA 검수
  - **📈 콘텐츠 관리**: 트렌드 관리, 지식 수집, 학습 피드백
  - **💰 비즈니스**: 수익 추적, 비용/쿼터, 리스크
  - **📺 채널별** (기존 유지)
  - **⚙️ 설정** (기존 유지)
- **영향도**: Medium — 인지 부하 감소
- **파일**: `web/components/sidebar-nav.tsx`

#### 3.6 [P2] 빈 상태(Empty State) 가이드 강화
- **현재**: Supabase 미연동 시 대부분 페이지가 all-zero 숫자나 빈 차트만 표시. 사용자에게 "다음에 무엇을 해야 하는지" 안내 부재
- **제안**: 각 빈 상태에 가이드 메시지 추가:
  - "파이프라인을 실행하면 여기에 데이터가 표시됩니다 → [테스트 런 시작]"
  - "Supabase를 연동하면 실시간 대시보드가 활성화됩니다 → [설정 가이드]"
- **영향도**: Medium — 온보딩 경험 향상
- **파일**: 해당 페이지들

### 추가점

#### 3.7 [P2] 통합 검색 / 빠른 이동
- **현재**: Run ID, 주제명, 채널명으로 특정 페이지를 찾으려면 사이드바를 하나씩 탐색
- **제안**: 헤더에 `Cmd+K` 스타일 커맨드 팔레트. Run ID, 주제명, 채널명 검색 → 해당 페이지로 즉시 이동
- **영향도**: Medium — 파워 유저 생산성
- **파일**: 신규 `web/components/command-palette.tsx`, `web/app/layout.tsx`

---

## 영역 4: 보안/인프라

### 개선점

#### 4.1 [P0] API 인증 미들웨어 — **CRITICAL**
- **현재**: `web/proxy.ts`에 인증 로직이 있으나 **미사용** (import 없음). `middleware.ts` 부재. 모든 19개 API 라우트가 인증 없이 공개. `/api/pipeline/trigger`로 인증 없이 파이프라인 실행 가능
- **제안**: `web/middleware.ts` 생성, `proxy.ts` 로직 활용. 모든 `/api/*` 라우트에 세션 토큰 검증 적용
- **영향도**: Critical
- **파일**: 신규 `web/middleware.ts`, `web/proxy.ts`

#### 4.2 [P0] 경로 트래버설 방지 — **HIGH**
- **현재**: `web/app/api/runs/[channelId]/[runId]/seo/route.ts`, `shorts/route.ts`, `bgm/route.ts`에서 URL 파라미터를 검증 없이 `path.join`에 사용. `../../etc/passwd` 공격 가능
- **제안**: `artifacts/[...path]/route.ts`의 `path.resolve` + `startsWith` 패턴을 모든 파일 서빙 라우트에 적용. 공유 `validatePath()` 유틸리티 생성
- **영향도**: High
- **파일**: 해당 3개 라우트, 신규 `web/lib/fs-helpers.ts`

#### 4.3 [P0] SEO PATCH 입력 검증 — **HIGH**
- **현재**: `/api/runs/{ch}/{runId}/seo` PATCH가 임의 JSON body를 검증 없이 `fs.writeFileSync`로 저장
- **제안**: `channelId`/`runId` 정규식 검증 (`/^CH\d+$/`, `/^run_CH\d+_\d+$/`), JSON 스키마 검증, 경로 트래버설 체크
- **영향도**: High
- **파일**: `web/app/api/runs/[channelId]/[runId]/seo/route.ts`

#### 4.4 [P1] 세션 토큰 전환
- **현재**: `login/actions.ts` L27에서 쿠키에 평문 비밀번호 저장
- **제안**: `crypto.randomUUID()` 기반 세션 토큰 발급. 서버 사이드 세션 검증
- **영향도**: Medium
- **파일**: `web/app/login/actions.ts`, `web/proxy.ts`

#### 4.5 [P1] DASHBOARD_PASSWORD 프로덕션 필수화
- **현재**: 미설정 시 인증 완전 bypass (개발 편의)
- **제안**: `NODE_ENV === 'production'`에서 미설정 시 503 반환 또는 기동 차단
- **영향도**: Medium
- **파일**: `web/app/login/actions.ts`, `web/proxy.ts`

### 추가점

#### 4.6 [P1] 데이터 백업/복구 시스템
- **현재**: 로컬 단일 머신에 모든 데이터 존재. 백업/복구 메커니즘 전무
- **제안**: 일간 백업 스크립트 — `data/`, `config/`, `runs/`(manifest.json만) → 클라우드 스토리지 (S3/Supabase Storage)
- **영향도**: High — 비즈니스 연속성
- **파일**: 신규 `scripts/backup.py`, `scripts/restore.py`

#### 4.7 [P1] 외부 알림 채널 (Slack/Discord)
- **현재**: 알림이 로컬 JSON 파일에만 기록. 외부 전달 경로 없음
- **제안**: Slack Webhook 연동. 파이프라인 실패, 쿼터 경고, HITL 신호, Phase 승격 시 자동 발송
- **영향도**: High — 실시간 운영 인지
- **파일**: `src/agents/analytics_learning/notifier.py`, `src/core/config.py` (SLACK_WEBHOOK_URL 추가)

---

## 영역 5: 테스트/품질

### 개선점

#### 5.1 [P1] 핵심 모듈 테스트 추가
- **현재**: `config.py`, `ssot.py`, `script_generator.py`, `ffmpeg_composer.py`, `uploader.py` 등 파이프라인 핵심부 미테스트
- **제안**: 각 모듈의 단위 테스트 작성 (mock Gemini, mock subprocess, mock YouTube API)
- **영향도**: High — 회귀 방지
- **파일**: 신규 `tests/test_config.py`, `tests/test_ssot.py` 등 5개

#### 5.2 [P1] requirements 버전 고정 + lock 파일
- **현재**: `requirements.txt`에 `>=` 하한만 지정. lock 파일 없음. 빌드 재현 불가
- **제안**: `pip-compile` (pip-tools)로 `requirements.lock` 생성. CI에서 `pip install -r requirements.lock` 사용
- **영향도**: High — 재현 가능 빌드
- **파일**: `requirements.txt`, 신규 `requirements.lock`

#### 5.3 [P1] CI lint/format/coverage 추가
- **현재**: CI가 `pytest`와 `npm run build`만 실행
- **제안**: `ruff check`, `ruff format --check`, `pytest --cov=src`, `pip-audit`, `npm run lint` 추가
- **영향도**: Medium — 코드 품질 게이트
- **파일**: `.github/workflows/ci.yml`

### 강화점

#### 5.4 [P2] 프론트엔드 테스트 (Vitest + Playwright)
- **현재**: 프론트엔드 테스트 전무. Jest/Vitest/Playwright 없음
- **제안**: Vitest (컴포넌트 단위) + Playwright (E2E: 로그인, 트렌드 승인, 파이프라인 트리거)
- **영향도**: Medium
- **파일**: `web/package.json`, 신규 `web/vitest.config.ts`, `web/tests/`

#### 5.5 [P2] 보안 스캔 (Dependabot, pip-audit)
- **현재**: 의존성 취약점 자동 탐지 미구성
- **제안**: `.github/dependabot.yml` + CI에 `pip-audit`, `npm audit` 추가
- **영향도**: Medium
- **파일**: 신규 `.github/dependabot.yml`, `.github/workflows/ci.yml`

### 추가점

#### 5.6 [P2] 레거시 문서 업데이트
- **현재**: `RUNBOOK.md`가 `backend.scripts.verify_repo_health`, `REPRODUCIBLE_BUILD.md`가 `cd backend` 참조 — 현재 구조(`src/`, `web/`)와 불일치
- **제안**: 현재 프로젝트 구조 반영하여 업데이트
- **영향도**: Low
- **파일**: `docs/RUNBOOK.md`, `docs/REPRODUCIBLE_BUILD.md`

---

## 영역 6: 운영/모니터링

### 개선점

#### 6.1 [P1] Sub-Agent 자동 실행 오케스트레이터
- **현재**: 4개 Sub-Agent 모듈이 구현되어 있으나 자동 실행 메커니즘 없음. 웹의 "실행" 버튼도 `/api/agents/run` 엔드포인트 미존재로 404
- **제안**: `src/agents/orchestrator.py` 생성. 파이프라인 완료 후 자동 실행 또는 스케줄 기반 주기 실행. 웹 API 엔드포인트도 연동
- **영향도**: High — Sub-Agent 시스템 전체 활성화
- **파일**: 신규 `src/agents/orchestrator.py`, 신규 `web/app/api/agents/run/route.ts`

### 강화점

#### 6.2 [P2] runs/ 디렉토리 TTL/아카이빙
- **현재**: runs/ 디렉토리가 무한 증가. 영상 파일 포함 시 Run당 50-200MB
- **제안**: 30일 초과 Run을 자동 압축. manifest.json + cost.json만 보존, 영상/이미지 삭제 또는 tar.gz
- **영향도**: Medium — 디스크 관리
- **파일**: 신규 `src/core/runs_archiver.py`

#### 6.3 [P2] 구조적 파이프라인 관측성
- **현재**: loguru 텍스트 로그만 존재. 스텝별 소요 시간, 토큰 수, 비용 등의 구조화된 메트릭 없음
- **제안**: `observability.json`에 per-step 타이밍, 토큰 카운트, 에러 카운트 기록. `/api/pipeline/observability` 대시보드 연동
- **영향도**: Medium
- **파일**: `src/step08/__init__.py`, `src/pipeline.py`, 신규 API

### 추가점

#### 6.4 [P2] 헬스체크 엔드포인트
- **현재**: 외부 모니터링 도구(UptimeRobot 등)가 시스템 상태를 확인할 방법 없음
- **제안**: `/api/health` — 디스크 공간, 쿼터 상태, 마지막 성공 Run, Supabase 연결, 자격증명 유효성 확인
- **영향도**: Medium
- **파일**: 신규 `web/app/api/health/route.ts`

#### 6.5 [P2] 클라우드 배포 준비 (Docker Compose)
- **현재**: 전체 시스템이 단일 로컬 Windows 머신 의존. `web/Dockerfile`만 존재
- **제안**: Python 파이프라인 `Dockerfile` + `docker-compose.yml` (web + pipeline + ngrok)
- **영향도**: High — 스케일링/이중화 기반
- **파일**: 신규 root `Dockerfile`, `docker-compose.yml`

---

## 영역 7: 수익화 전략

### 개선점 (기존 수익 로직 버그/누락)

#### 7.1 [P0] QA Vision 프레임 추출 시간 계산 버그
- **현재**: `src/step11/qa_gate.py` L56에서 `"ss", str(pct * 1.2)`로 프레임 추출. 영상 길이를 120초로 가정하지만 실제 영상은 660-780초. 따라서 5%, 25%, 50% 위치 대신 영상 초반 6-108초에서만 프레임이 추출되어 **영상 후반부의 품질 문제를 전혀 감지하지 못함**
- **제안**: 실제 영상 길이를 `ffprobe`로 측정 후 `pct * actual_duration`으로 계산
- **영향도**: Critical — QA 무결성
- **파일**: `src/step11/qa_gate.py` (L56)

#### 7.2 [P0] chapter_markers가 description에 미삽입
- **현재**: `src/step03/algorithm_policy.py`에서 `chapter_markers_required: True`, `chapter_min_count: 5`를 요구. `script_generator.py`에서 챕터 마커를 스크립트에 포함시키지만, `metadata_generator.py`가 description 생성 시 `seo.description_first_2lines`만 사용하고 `seo.chapter_markers`를 삽입하지 않음
- **제안**: `metadata_generator.py`에서 description 끝에 chapter_markers 자동 추가 (`00:00 인트로` 형식)
- **영향도**: High — YouTube 알고리즘이 챕터 마커를 Browse Feed 추천 시그널로 사용
- **파일**: `src/step08/metadata_generator.py`

#### 7.3 [P1] 업로드 카테고리 ID 채널별 분화
- **현재**: `src/step12/uploader.py` L68에서 `categoryId: "27"` (Education) 하드코딩. Shorts는 `"22"` (People & Blogs). CH4(미스터리)는 Entertainment(24), CH5(전쟁사)는 People & Blogs(22)가 더 적합할 수 있음
- **제안**: `config.py`에 채널별 `YOUTUBE_CATEGORY_ID` 매핑 추가. uploader에서 동적 참조
- **영향도**: Medium — 카테고리별 추천 알고리즘 최적화
- **파일**: `src/step12/uploader.py`, `src/core/config.py`

#### 7.4 [P1] rpm_stage 하드코딩 해소
- **현재**: `src/step14/revenue_tracker.py` L66에서 `rpm_stage`가 항상 `"INITIAL"`. `config.py`의 `CHANNEL_RPM_ACTUAL`도 모두 `None`
- **제안**: KPI 수집 시 실측 RPM을 자동 업데이트 → `revenue_policy.py`와 `scorer.py`로 피드백하는 루프 구축
- **영향도**: Medium — 수익 예측 정확도
- **파일**: `src/step14/revenue_tracker.py`, `src/core/config.py`, `src/step07/revenue_policy.py`

### 강화점

#### 7.5 [P1] 업로드 타이밍 자동 최적화
- **현재**: `algorithm_policy.py`에 `preferred_hours_kst` (채널별 피크 시간대)가 정의되어 있으나, `uploader.py`가 이를 참조하지 않음. `scheduled_time` 파라미터가 존재하지만 외부에서 수동 전달 필요
- **제안**: 업로드 시 `algorithm_policy.json`의 `preferred_hours_kst`를 읽어 YouTube `publishAt` 자동 설정. KPI 학습 데이터로 최적 시간대 갱신
- **영향도**: High — 초기 노출량 극대화
- **파일**: `src/step12/uploader.py`, `src/step03/algorithm_policy.py`

#### 7.6 [P1] A/B 제목/썸네일 48시간 자동 교체
- **현재**: `ab_selector.py`가 CTR 기반 승자를 선택하고 채널 단위 bias만 저장 (`bias[channel_id] = {"preferred_title_mode": winner}`). 업로드 후 제목/썸네일 자동 교체 미구현
- **제안**: Step13(48h KPI 수집) 후 CTR이 목표 미달이면 YouTube `videos.update` API로 차선 배리언트로 자동 교체. A/B 학습을 주제 유형별로 세분화 (경제 위기→authority, 재테크 팁→benefit 등)
- **영향도**: High — CTR 최적화 자동화
- **파일**: `src/step12/uploader.py`, `src/agents/analytics_learning/ab_selector.py`, `src/agents/analytics_learning/pattern_extractor.py`

#### 7.7 [P2] SEO 태그 검색량 기반 고도화
- **현재**: `metadata_generator.py`가 Gemini로 태그 15개 생성. 실제 검색량/경쟁도 미반영
- **제안**: SerpAPI (키 이미 설정됨) 또는 YouTube Search Suggest API로 고검색량 키워드 발굴 → 태그 우선순위 재배치
- **영향도**: Medium — 검색 유입 증가
- **파일**: `src/step08/metadata_generator.py`, `src/core/config.py` (SERPAPI_KEY 활용)

### 추가점

#### 7.8 [P1] 핀 댓글 자동 생성
- **현재**: `algorithm_policy.py`에 `pinned_comment_required: True` 정의. `uploader.py` receipt에 `pinned_comment_posted: False` 기록. 그러나 **실제 댓글 작성 로직 미구현**
- **제안**: YouTube `commentThreads.insert` API로 영상별 맞춤 핀 댓글 자동 생성. 콘텐츠 관련 질문 형식으로 댓글 유도 → 커뮤니티 신호 증폭
- **영향도**: High — 알고리즘 점수 직접 영향 (댓글 수 = engagement signal)
- **파일**: `src/step12/uploader.py`, 신규 `src/step12/comment_manager.py`

#### 7.9 [P2] End Screen / Cards API 연동
- **현재**: 미구현. YouTube Data API의 `endScreen`과 `cards` 리소스 미활용
- **제안**: 영상 종료 20초 전에 다음 영상 추천 카드 + 구독 버튼 자동 설정. Session Watch Time 향상
- **영향도**: Medium — 세션 시청 시간 증가
- **파일**: 신규 `src/step12/endscreen_manager.py`

#### 7.10 [P2] UTM 파라미터 기반 Affiliate 추적
- **현재**: `script_generator.py` L218에서 `"utm": ""` 빈 문자열. affiliate 링크 클릭/전환 추적 미구현
- **제안**: 채널/영상/주제별 고유 UTM 파라미터 생성. description에 추적 가능한 affiliate 링크 삽입
- **영향도**: Medium — 수익원 다각화 측정
- **파일**: `src/step08/script_generator.py`, `src/step08/metadata_generator.py`

#### 7.11 [P3] 스폰서십/멤버십 수익 필드 확장
- **현재**: `revenue_tracker.py`에 AdSense + Affiliate 2개 수익원만 존재
- **제안**: 스폰서십, 멤버십, 슈퍼챗 필드 추가. 채널 성장에 따라 수익 다각화 추적
- **영향도**: Low (장기)
- **파일**: `src/step14/revenue_tracker.py`, `web/lib/types.ts`

---

## 영역 8: 영상 품질 강화

### 개선점 (품질 저하 버그/설정 문제)

#### 8.1 [P0] FFmpeg CRF/비트레이트 통합 설정 부재
- **현재**: `src/step08/ffmpeg_composer.py`의 `image_to_clip`에서 `-c:v libx264 -pix_fmt yuv420p`만 설정. **CRF 미지정 → ffmpeg 기본 CRF=23 적용**. YouTube 권장 CRF 18-20. Shorts도 CRF=23 (저화질)
- **제안**: `config.py`에 `VIDEO_CRF=18`, `VIDEO_PRESET="medium"`, `VIDEO_FPS=30` 통합 설정. 모든 ffmpeg 명령에서 참조. Shorts는 CRF=20
- **영향도**: High — 전체 영상 화질 직접 영향
- **파일**: `src/step08/ffmpeg_composer.py`, `src/step08_s/shorts_generator.py`, `src/core/config.py`

#### 8.2 [P1] 자막 정확도 향상 (Whisper 모델 + 글자 수)
- **현재**: Faster-Whisper 모델 `"base"` 사용 (L31). `MAX_CHARS=40` (L43). 한국어 YouTube 표준 20-25자 대비 과다. 균등분배 폴백의 pydub에서는 80자까지 허용 (L136)
- **제안**: 모델을 `"small"` 이상으로 변경 (한국어 정확도 대폭 향상). `MAX_CHARS=25`로 축소. 폴백도 동일 기준 적용
- **영향도**: High — 시청자 경험 직접 영향
- **파일**: `src/step08/subtitle_generator.py`

#### 8.3 [P1] scene_composer 배경 연동 + 캐릭터 위치 다양성
- **현재**: `scene_composer.py`에서 `background_path=None` 고정 (L111). 모든 장면이 `#1E1E32` 단색 배경. 캐릭터도 항상 오른쪽 하단 고정 (L54-55)
- **제안**: SD/Gemini 이미지를 배경으로 활용. 캐릭터 위치를 섹션별 로테이션 (좌하단, 우하단, 좌상단 등)
- **영향도**: High — 시각적 단조로움 해소
- **파일**: `src/step08/scene_composer.py`, `src/step08/__init__.py`

#### 8.4 [P1] motion_engine 클립 나레이션 동기화
- **현재**: `motion_engine.py`에서 기본 `duration_sec=6.0` (L37). 실제 섹션별 나레이션 길이와 무관. 나레이션이 8초인데 클립이 6초면 영상/음성 불일치
- **제안**: 나레이션 생성 후 각 섹션의 실제 오디오 길이를 측정하여 `create_motion_clips()`에 전달
- **영향도**: High — 영상-음성 동기화
- **파일**: `src/step08/motion_engine.py`, `src/step08/__init__.py`

#### 8.5 [P1] 자막 없는 영상 전달 방지
- **현재**: `ffmpeg_composer.py`의 `add_subtitles` 실패 시 `shutil.copy2(video_path, output_path)` (L38) → 자막 없는 영상이 QA로 전달. QA에 자막 존재 여부 검증 없음
- **제안**: 자막 추가 실패 시 fallback SRT 재생성 시도. QA 게이트에 "자막 파일 존재 + 최소 10개 엔트리" 검증 추가
- **영향도**: Medium
- **파일**: `src/step08/ffmpeg_composer.py`, `src/step11/qa_gate.py`

#### 8.6 [P1] Manim 품질 설정 업그레이드
- **현재**: `MANIM_QUALITY="l"` (low). 프로덕션 영상에 부적합한 저해상도 렌더링
- **제안**: 환경변수 `MANIM_QUALITY`를 기본 `"m"` (medium, 720p) 이상으로 변경. 최종 빌드 시 `"h"` (1080p)
- **영향도**: Medium
- **파일**: `.env`, `src/core/config.py`

### 강화점

#### 8.7 [P1] 스크립트 프롬프트 구조화 + 후킹 검증
- **현재**: `script_generator.py`의 시스템 프롬프트가 채널별 2줄 수준으로 매우 짧고 일반적. narrative arc, 감정 곡선, 섹션 전환 패턴 등 구조 지침 없음. 첫 30초 후킹에 대한 체계적 검증 없음
- **제안**: 
  - 프롬프트에 "4막 구조" (Hook→Setup→Conflict→Resolution) 명시
  - `narration_text` 최소 400자 + **최대 800자** 제한 추가
  - QA 게이트에 "첫 섹션 narration_text가 질문/통계/반전으로 시작하는지" 체크
  - `algorithm_policy.py`의 `hook_max_sec: 25` 설정을 스크립트 생성에 실제 반영
- **영향도**: High — AVP(평균 시청률) 직접 영향
- **파일**: `src/step08/script_generator.py`, `src/step11/qa_gate.py`

#### 8.8 [P2] 나레이션 섹션별 감정 분리
- **현재**: `narration_generator.py`가 전체 나레이션을 하나의 텍스트로 합쳐 단일 TTS 호출. 캐릭터 감정(happy/surprised/thinking/sad)이 4종뿐이며, ElevenLabs `stability=0.5`로 변동성이 높음
- **제안**: 섹션별 개별 TTS 호출. 스크립트의 `character_directions.expression`에 따라 ElevenLabs `voice_settings` 동적 조절 (thinking→stability 0.7, surprised→style 0.6). 감정 종류를 `excited`, `curious`, `serious` 등 확대
- **영향도**: Medium — 콘텐츠 몰입도
- **파일**: `src/step08/narration_generator.py`, `src/step08/character_manager.py`

#### 8.9 [P2] Ken Burns 모션 프리셋 확대
- **현재**: 4개 프리셋만 순환 (zoom_in/zoom_out/pan_left/pan_right). 6+ 섹션 영상에서 반복감 발생
- **제안**: 8-12개 프리셋 (대각선 팬, zoom+pan 복합, 회전, drift 등). 장면 키워드에 따른 동적 프리셋 선택 (데이터→zoom_in, 인물→pan, 풍경→wide_pan)
- **영향도**: Medium — 시각적 다양성
- **파일**: `src/step08/motion_engine.py`

#### 8.10 [P2] SD XL 이미지 품질 최적화
- **현재**: `num_inference_steps=25` (일반 30-50이 고품질). 해상도 1920x1080 직접 생성 (SDXL에서 메모리 과부하). LoRA scale factor 미제어 (기본 1.0). `enable_vae_tiling()` 미적용
- **제안**: `num_inference_steps=35`, 1024x576 생성 후 upscale, LoRA scale 0.7-0.8, `enable_vae_tiling()` + `enable_model_cpu_offload()` 추가
- **영향도**: Medium — 이미지 품질 + 안정성
- **파일**: `src/step08/sd_generator.py`

### 추가점

#### 8.11 [P2] Manim 검증 템플릿 라이브러리
- **현재**: Gemini가 매번 Manim 코드를 새로 생성 → LaTeX 사용 등으로 높은 fallback rate. max_retries=2로 3번 모두 실패하면 정적 이미지로 대체
- **제안**: 카테고리별 검증된 Manim 템플릿 (경제: BarChart, 과학: MathTex-free 다이어그램, 역사: Timeline) 라이브러리 구축. Gemini에 템플릿 기반 코드 생성 지시
- **영향도**: Medium — Manim 성공률 향상
- **파일**: 신규 `src/step08/manim_templates/`, `src/step08/manim_generator.py`

#### 8.12 [P2] BGM 반복 경계 크로스페이드
- **현재**: Suno AI BGM 최대 240초. 영상 660-780초이므로 `aloop=-1`로 무한 반복. 반복 경계에서 부자연스러운 끊김 가능. `bgm_volume=0.08`로 매우 낮음
- **제안**: BGM 루프 경계에 3초 크로스페이드 적용. 볼륨 0.10-0.12로 조정. 또는 2-3개 BGM 생성하여 이어붙이기
- **영향도**: Low-Medium
- **파일**: `src/step09/bgm_overlay.py`, `src/step08/ffmpeg_composer.py`

#### 8.13 [P3] Shorts 스마트 하이라이트 추출
- **현재**: 1920x1080→608x1080 중앙 크롭 → 1080x1920 확대. 섹션 시작 시간 균등 분배 (실제 하이라이트와 무관)
- **제안**: Gemini Vision으로 "가장 임팩트 있는 3개 구간" 분석. 크롭 시 피사체 위치 감지(face detection 등)로 동적 크롭 영역 결정
- **영향도**: Medium — Shorts 노출/조회수
- **파일**: `src/step08_s/shorts_generator.py`

---

## 영역 9: 자료 수집 강화

### 개선점 (수집 품질 버그/누락)

#### 9.1 [P0] dedup.py knowledge packages 미탐색
- **현재**: `src/step05/dedup.py` L29에서 `store_dir.glob("*.json")`으로 루트만 탐색. `knowledge_package.py`의 `save_package()`는 `packages/` 하위 디렉토리에 저장. **기존 knowledge package가 중복 검사에 포함되지 않아 동일 주제 반복 생성 가능**
- **제안**: `store_dir.glob("**/*.json")`으로 재귀 탐색. 또는 `packages/` 경로를 명시적으로 추가
- **영향도**: High — 콘텐츠 중복 방지
- **파일**: `src/step05/dedup.py` (L29)

#### 9.2 [P1] scorer.py fit_score/revenue_score 동적화
- **현재**: `fit_score`가 카테고리별 상수 (economy=0.7, mystery=0.95). "인플레이션의 원리"(애니메이션 적합)와 "FOMC 회의 결과"(데이터 중심)가 동일 점수. `revenue_score`도 RPM 상수 기반
- **제안**: fit_score에 키워드 특성 분석 추가 (시각화 가능성, 스토리텔링 적합도 등 Gemini 평가). revenue_score에 SerpAPI 키워드 광고 단가 데이터 반영
- **영향도**: Medium — 주제 선별 정밀도
- **파일**: `src/step05/scorer.py`

#### 9.3 [P1] 에버그린 혼합 비율 보장
- **현재**: `trend_collector.py` L238-245에서 에버그린이 `all_raw_topics < limit`일 때만 보충. 트렌드가 충분하면 에버그린 0개. 한편 `knowledge_store.py`에서 별도로 에버그린 추가 (이중 로직)
- **제안**: 항상 에버그린 20-30% 혼합 보장. `limit` 파라미터와 별개로 `evergreen_ratio=0.25` 설정. knowledge_store의 중복 로직 통합
- **영향도**: Medium — 콘텐츠 다양성 + 장기 트래픽
- **파일**: `src/step05/trend_collector.py`, `src/step05/knowledge_store.py`

### 강화점

#### 9.4 [P1] 5계층 수집 비동기 병렬화
- **현재**: Layer 1-4가 순차 실행 (L220-224). 각 소스의 네트워크 I/O 타임아웃이 누적되어 채널당 30초+ 소요
- **제안**: `asyncio` 또는 `ThreadPoolExecutor`로 L1-L4 동시 수집. L5(에버그린)는 결과 기반 조건부 유지
- **영향도**: Medium — 수집 시간 30s→10s
- **파일**: `src/step05/trend_collector.py`

#### 9.5 [P1] Stage 2 다국어 Wikipedia 확장
- **현재**: `stage2_enrich.py`에서 한국어 Wikipedia만 검색. CH5(전쟁사), CH6(과학), CH4(미스터리) 등은 영어 Wikipedia가 훨씬 풍부
- **제안**: 한국어 → 영어 → 일본어 순으로 다국어 Wikipedia 검색. 핵심 정보를 한국어로 요약
- **영향도**: Medium — 지식 깊이 향상
- **파일**: `src/step05/knowledge/stage2_enrich.py`

#### 9.6 [P2] 중복 검사 의미적 유사도 도입
- **현재**: 2-gram Jaccard 유사도 (임계값 0.75). "블랙홀이란 무엇인가" vs "블랙홀의 비밀"처럼 의미적으로 유사하지만 문자적으로 다른 주제를 놓침
- **제안**: Gemini embedding API 또는 sentence-transformers로 의미적 유사도 추가. Jaccard + semantic 복합 점수로 판단
- **영향도**: Medium — 콘텐츠 중복 방지 정밀도
- **파일**: `src/step05/dedup.py`

#### 9.7 [P2] Stage 3 circular validation 해소
- **현재**: Gemini로 Gemini가 수집한 정보를 교차 검증 → circular validation 위험. 팩트 부족 시 Gemini 보충 팩트에 대한 추가 검증 없음
- **제안**: 교차 검증 시 최소 1개 외부 소스(Wikipedia/Scholar) 확인을 필수화. Gemini 보충 팩트에 `source: "ai_generated"` 태그 + 낮은 confidence 부여
- **영향도**: Medium — 팩트 신뢰도
- **파일**: `src/step05/knowledge/stage3_factcheck.py`

### 추가점

#### 9.8 [P1] SerpAPI 트렌드 소스 활성화
- **현재**: `config.py`에 `SERPAPI_KEY` 환경변수가 정의되어 있으나, 11개 소스 모듈 **어디에서도 사용하지 않음**
- **제안**: `sources/serpapi.py` 신규 모듈 생성. Google 실시간 검색 트렌드 + 관련 질문(People Also Ask) 수집. Layer 1에 추가
- **영향도**: High — 가장 정확한 실시간 검색 트렌드
- **파일**: 신규 `src/step05/sources/serpapi.py`, `src/step05/trend_collector.py`

#### 9.9 [P2] 카테고리별 전문 API 실제 연동
- **현재**: `category_enricher.py`가 출처 URL만 추가하고 실제 데이터를 파싱하지 않음. FRED API 미구현. 한국은행 ECOS API 미사용. 국토교통부 실거래가 API 미사용
- **제안**:
  - CH1(경제): FRED API + 한국은행 ECOS Open API로 실시간 금리/환율/물가 데이터
  - CH2(부동산): 국토교통부 공공데이터 API로 실거래가/전세가
  - CH6(과학): NASA Open API 실제 데이터 파싱 (현재 sources/nasa.py는 URL만 수집)
- **영향도**: Medium — 데이터 기반 콘텐츠 차별화
- **파일**: `src/step05/knowledge/category_enricher.py`, 신규 API 클라이언트 모듈들

#### 9.10 [P2] 커뮤니티 소스 확대
- **현재**: `community.py`에서 카테고리당 1개 사이트만 크롤링. Reddit도 서브레딧 1-2개만
- **제안**: 에펨코리아, 뽐뿌, 루리웹, 블라인드(직장인), 클리앙 등 추가. Reddit에 r/hanguk, r/Korean 추가
- **영향도**: Low-Medium
- **파일**: `src/step05/sources/community.py`, `src/step05/sources/reddit.py`

#### 9.11 [P3] 시리즈 콘텐츠 자동 기획
- **현재**: `knowledge_store.py` L18에 "나머지 15%는 시리즈 (Step15에서 관리)" 주석만 존재. 시리즈 기획 로직 미구현
- **제안**: 관련 주제 클러스터링 (semantic similarity) → 3-5편 시리즈 자동 기획. 에피소드 간 스토리 연결 지시를 script_generator에 전달
- **영향도**: Medium (장기) — 구독자 유지율 향상
- **파일**: 신규 `src/step05/series_planner.py`, `src/step08/script_generator.py`

---

## 우선순위 실행 요약

| 우선순위 | 항목 수 | 핵심 내용 |
|----------|---------|-----------|
| **P0** (즉시) | 8 | API 인증 미들웨어, 경로 트래버설, SEO 입력 검증, FFmpeg 반환값 검증, runs 목록 페이지, QA Vision 프레임 버그, chapter_markers 미삽입, dedup 경로 버그, FFmpeg CRF 설정 |
| **P1** (스프린트 1-2) | 24 | Resume 메커니즘, 병렬 처리, knowledge 연동, 스케줄링, 백업, 인증 강화, 핵심 테스트, CI, 알림 UI, Sub-Agent 오케스트레이터, 페이지 링크, 사이드바/홈 재구성, 업로드 타이밍, A/B 자동교체, 핀 댓글, 스크립트 후킹, 자막 정확도, 배경/캐릭터, 모션 동기화, SerpAPI, 에버그린 비율, Wikipedia 다국어, 5계층 병렬화 |
| **P2** (스프린트 3-4) | 19 | 트렌드 병렬화, 인라인 스타일, 접근성, 프론트엔드 테스트, 보안 스캔, 아카이빙, 관측성, 헬스체크, Docker, Empty State, 검색, SEO 고도화, 나레이션 감정, Manim 템플릿, 모션 다양성, SD XL 최적화, BGM 크로스페이드, 카테고리 API, 의미적 중복검사, circular validation 해소, End Screen, UTM 추적, 커뮤니티 확대 |
| **P3** (백로그) | 4 | 공유 Tab 컴포넌트, 서버 컴포넌트 최적화, Shorts 스마트 추출, 시리즈 자동 기획, 수익 필드 확장 |

## 검증 계획

### 보안 검증
1. `/api/pipeline/trigger`에 인증 없이 POST → 401 반환 확인
2. `channelId=../../etc/passwd`로 API 호출 → 400 반환 확인
3. SEO PATCH에 잘못된 JSON 스키마 → 400 반환 확인

### 파이프라인 검증
1. Step08 중간 실패 후 재실행 → 이전 완료 단계 스킵 확인
2. FFmpeg 실패 시뮬레이션 → RuntimeError 발생 확인
3. 이미지 병렬 생성 → 소요 시간 50%+ 감소 확인
4. CRF=18로 인코딩 → 영상 파일 크기/화질 비교

### 영상 품질 검증
1. 자막 MAX_CHARS=25 → 한 줄 가독성 확인
2. Whisper "small" 모델 → 한국어 정확도 비교 (WER 측정)
3. QA Vision 프레임 → 5%, 25%, 50%, 75%, 95% 위치 정확히 추출 확인
4. chapter_markers → YouTube description에 올바른 타임스탬프 형식 확인

### 수익화 검증
1. 업로드 시 publishAt → algorithm_policy의 preferred_hours_kst 범위 내 확인
2. 핀 댓글 → YouTube API로 정상 생성 + 고정 확인
3. A/B 교체 → 48시간 후 CTR 미달 시 자동 제목 변경 확인

### 자료 수집 검증
1. dedup → `packages/` 하위 JSON도 기존 주제로 인식 확인
2. SerpAPI → 실시간 트렌드 키워드 최소 5개 수집 확인
3. 에버그린 비율 → limit=10일 때 에버그린 2-3개 항상 포함 확인
4. 5계층 병렬 → 수집 시간 30s→10s 이내 확인

### 대시보드 검증
1. Playwright로 홈 → 채널 카드 클릭 → Run 목록 → Run 상세 전체 흐름 E2E
2. 트렌드 승인 → 해당 Run 링크 확인
3. 빈 상태 가이드 메시지 표시 확인
