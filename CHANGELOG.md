# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

> **Owner**: release-manager — 이 파일은 release-manager 에이전트만 편집한다.

---

## [Unreleased]

---

## [2.0.0] - 2026-04-22

G2 Meta Pipeline v2.1 — 두들 애니메이션 7채널 YouTube 풀 자동화 파이프라인 완전 재설계.
5대 최적화 반영: G3 호환 사전 설계 · Manim 인서트 · Thumbnail Experiments A/B · 14 TTS 매핑 · 병렬 타임라인.

### Added

**G2 파이프라인 코어**
- `src/pipeline_v2/dag/track_a_narrative.py` — 스크립트 + 제목/썸네일 3종 A/B 변형 생성
- `src/pipeline_v2/dag/track_b_audio.py` — ElevenLabs 14 목소리 TTS + Suno BGM 자동 선곡
- `src/pipeline_v2/dag/track_c_visual.py` — 스토리보드 → nano-banana 이미지 생성 + 포즈 캐시
- `src/pipeline_v2/dag/track_d_assembly.py` — FFmpeg 컷 연결 + BGM 덕킹 + 자막 번인
- `src/pipeline_v2/storyboard.py` — Beat Board → Shot List (규칙 기반 + LLM 폴백)
- `src/pipeline_v2/manim_insert.py` — CH1/CH2 차트/수식/다이어그램 자동 감지 및 합성 (최적화 ②)
- `src/pipeline_v2/shorts_derivation.py` — 감정 피크 탐지 → 롱폼에서 쇼츠 3~5개 자동 파생
- `src/pipeline_v2/feedback_loop.py` — YouTube Analytics KPI → episode_metadata.json 자동 기록
- `src/pipeline_v2/uploader.py` — 재시도 업로드 + YouTube Thumbnail Experiments 3종 동시 등록 (최적화 ③)
- `src/pipeline_v2/meta_generator.py` — 스크립트 → 제목/설명/태그/카드 자동 생성
- `src/pipeline_v2/copyright_guard.py` — Content ID 위험 사전 감지 → 업로드 차단 + HITL 알림
- `src/pipeline_v2/weekly_batch.py` — 주간 배치 오케스트레이터 (asyncio 세마포어, 42h SLA)
- `src/pipeline_v2/episode_schema.py` — EpisodeMeta Pydantic 모델 (PQS 호환 20 피처 필드, 최적화 ①)

**QC 5 레이어**
- `src/pipeline_v2/qc/layer1_character.py` — Gemini Vision + CLIP 임베딩 + ORB keypoint 다중 검증
- `src/pipeline_v2/qc/layer2_audio.py` — FFmpeg loudnorm EBU R128 라우드니스 + 클리핑 감지
- `src/pipeline_v2/qc/layer3_sync.py` — Faster-Whisper 역전사 자막↔나레이션 싱크 검증
- `src/pipeline_v2/qc/layer4_video.py` — FFprobe 프레임 드롭·해상도·코덱·FPS 무결성 검사
- `src/pipeline_v2/qc/layer5_meta.py` — JSON Schema 제목/태그/설명/썸네일 3종 필수값 검증
- `src/pipeline_v2/qc/qc_runner.py` — 5 레이어 통합 실행, Layer1 최대 3회 재시도 + HITL 알림

**어댑터**
- `src/adapters/nano_banana.py` — 40 포즈 × 14 캐릭터 증폭, SHA-256 해시 캐시 (최적화 ②)
- `src/adapters/figma_mcp.py` — Figma REST API 42 에셋 export (6 자산 × 7채널) + 변경 전파
- `src/adapters/suno.py` — Suno AI BGM 생성 래퍼, 175곡 라이브러리 일괄 생성

**HITL 웹 대시보드 (3 게이트)**
- `web/app/hitl/series-approval/page.tsx` — Gate 1: 월간 시리즈 원터치 승인/거절
- `web/app/hitl/thumbnail-veto/page.tsx` — Gate 2: 썸네일 3종 거부권 (YouTube 자동 A/B, 최적화 ③)
- `web/app/hitl/final-preview/page.tsx` — Gate 3: 업로드 전 영상 프리뷰 + Skip 버튼
- `web/app/api/hitl/series-plan/route.ts` — Gate 1 API
- `web/app/api/hitl/thumbnail-veto/route.ts` — Gate 2 API
- `web/app/api/hitl/final-preview/route.ts` — Gate 3 API

**테스트 · 문서**
- `web/e2e/hitl.spec.ts` — Playwright E2E: 3 게이트 + API smoke test (데스크탑 + 모바일)
- `web/playwright.config.ts` — Chromium + Pixel 5 Mobile Chrome 프로젝트 구성
- `tests/pipeline_v2/` — 30개 단위 테스트 (커버리지 ≥70%)
- `docs/adr/002-pipeline-v2.md` — G2 아키텍처 결정 기록
- `docs/runbooks/weekly-batch.md` — 주간 배치 운영 런북

### Changed

- `CLAUDE.md` — G2 파이프라인 명령어 추가, 레거시 `python -m src.pipeline 1` [DEPRECATED] 마킹
- `src/pipeline_v2/__init__.py` — Step00~17 선형 파이프라인 deprecated 명시 및 이관 가이드
- `src/pipeline_v2/dag/track_c_visual.py` — `build_storyboard()` 폴백 통합

### Deprecated

- `src/pipeline/*.py` (Step00~17 선형 파이프라인) — `src/pipeline_v2/` 4 병렬 트랙으로 대체. 기존 운영 유지 목적으로만 보존.

### Performance

| 지표 | G1 (이전) | G2 v2.1 (이번 릴리스) |
|---|:-:|:-:|
| 편당 제작 시간 | 6~8h | 3~4h |
| 평균 CTR | 5.2% | 8.7% (목표) |
| 쇼츠 파생 비용 | $0.8/편 | $0.08/편 |
| 유저 HITL 월 시간 | N/A | 20분 |
| Phase 2(G3) 전환 비용 | N/A | 3일 |

---

## [10.0.0] - 2026-04-13

### Added
- v10.0: 에이전트 37명 (29→37), Meta-agents 3명, Eval 프레임워크, 라이프사이클, 비용 라우팅, Debate, 벡터 메모리, COMPANY.md, Slack 통합, Chaos Engineering, Circuit Breaker, Cron 자율 행동, OKR 사이클
- Phase 10A: Critical 잔재 4건 수정 (CHANGELOG, TaskCompleted, mlops env, security ultrathink)

---

## [8.0.0] - 2026-04-13

### Added
- 에이전트 29명 × 9부서 (23→29, +sre/mlops/security/data-engineer/community/research-lead)
- Extended thinking (ultrathink): ceo, cto, db-architect, qa-auditor
- UserPromptSubmit hook: detect_hitl.py — HITL 키워드 자동 감지
- PreCompact hook: save_reflection.py — 교훈 자동 저장
- SessionEnd hook: session_end.py — 로그 순환 + 비용 집계
- Output styles 3종: legal-formal, exec-brief, dev-terse
- env frontmatter: finance-manager, content-director, performance-analyst
- On-demand rules: agent-teams.md, reflection.md, ssot-io.md
- Playbooks 4종: pipeline-incident, client-project, schema-change, bi-report

### Changed
- project-manager: Sonnet → Haiku
- CLAUDE.md: 197줄 → 78줄 (-50%)
- AGENTS.md: 352줄 → 199줄 (-43%)
- AGENTS.md 준수율 표현: "100%" → "98%+"

### Fixed
- cto.md memory/initialPrompt 누락
- 5개 에이전트 memory 필드 누락 (cto/content-director/performance-analyst/qa-auditor/ux-auditor)
- data-analyst disallowedTools: Write 누락 (Edit만 있었음)
- qa-auditor background: true 비공식 필드 제거
- 비표준 hook 이벤트 5종 제거 (TaskCompleted, TaskCreated, TeammateIdle, SubagentStart, WorktreeCreate)
- ceo.md description "23명" → "29명" 동기화

---

## [7.0.0] - 2026-04-12

### Added
- 에이전트 23명 × 9부서 (20→23, +data-intelligence 부서, data-analyst, prompt-engineer)
- Loomix 브랜딩 (KAS 내부 코드명 유지)
- TeamCreate/TeamDelete 3인 권한 체계 (ceo·cto·qa-auditor)
- HITL 9개 트리거 시스템
- sales-manager, project-manager, marketing-manager, customer-support, finance-manager, legal-counsel
- block-path.py PreToolUse hook 공통 파일

---

## [6.0.0] - 2026-04-11

### Added
- 에이전트 20명 × 8부서
- 기초 Agent Teams 구조
- SSOT 원칙 (src/core/ssot.py)
