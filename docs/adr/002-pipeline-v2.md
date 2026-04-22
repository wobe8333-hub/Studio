# ADR 002 — G2 Meta Pipeline v2.1 도입

**상태**: 확정 (2026-04-22)  
**결정자**: ceo, cto, backend-engineer  
**영향 범위**: 전체 KAS 파이프라인 — src/pipeline_v2/, web/app/hitl/, src/adapters/

---

## 문맥

KAS는 7채널 YouTube 자동화를 위해 Step00~17 선형 파이프라인을 운영 중이었다. 두들 애니메이션 YouTube 상위 1% 채널 데이터(100만+ 구독자, 73% 병행 전략 채택) 분석 결과 4가지 구조적 한계가 드러났다:

1. 썸네일·제목이 스크립트 전 단계에 위치 → 내용-썸네일 괴리 → 알고리즘 패널티
2. 나레이션 단계가 영상 합성과 분리 → 오디오-영상 싱크 오차 반복
3. 롱폼·쇼츠가 별도 파이프라인 → 자산 재활용률 저조, 제작비 ×10 낭비
4. KPI → 차기 영상 피드백 루프 부재 → 학습 효과 누적 실패

## 결정

**G2 Meta Pipeline v2.1**로 전환한다. 핵심 결정 사항:

| # | 결정 | 근거 |
|:-:|---|---|
| 1 | 4 병렬 트랙 DAG (A/B/C/D) | asyncio 기반, 42h SLA 내 주간 14편 달성 |
| 2 | 쇼츠 롱폼 자동 파생 | 쇼츠 편당 비용 $0.8 → $0.08 (-90%) |
| 3 | QC 5 레이어 자동 검증 | Vision+CLIP+ORB 다중 검증, 자동 통과율 ≥93% 목표 |
| 4 | HITL 3 게이트 웹 대시보드 | 유저 투입 시간 월 2h → 20분 (-83%) |
| 5 | Manim 인서트 CH1/CH2 전용 | 차트/수식 장면 CTR +15%p, AVD +11%p |
| 6 | YouTube Thumbnail Experiments | 썸네일 3종 자동 A/B, 72h 내 알고리즘 자동 채택 |
| 7 | 14 캐릭터 TTS 음성 매핑 | 채널별 Narrator/Guest 분리, 이탈률 -3%p |
| 8 | G3 호환 스키마 사전 설계 | Phase 2 전환 비용 2~3주 → 3일 (-90%) |
| 9 | nano-banana 포즈 캐시 | 초기 560장 생성, 이후 SHA-256 캐시 재활용 |
| 10 | Suno AI BGM 라이브러리 | 175곡, 저작권 100% 사용자 보유 |

## 트레이드오프

**채택한 방식의 장점**:
- 병렬 트랙으로 제작 시간 6~8h → 3~4h
- 피드백 루프로 KPI 데이터가 차기 시리즈에 자동 반영
- G3(PQS + Multi-Platform) 전환 시 schema 재설계 불필요

**포기한 대안**:
- Runway/Kling AI 영상 생성: 두들 스타일 일관성 97% 이하로 DB 98% 실패 패턴 확인 → 채택 불가
- Manim 전 채널 적용: CH3~7에서 CTR 개선 효과 미미, 렌더 타임 증가만 발생
- 선형 파이프라인 유지: KPI 루프 부재로 학습 효과 누적 불가

## 구현 현황 (2026-04-22)

### 완료된 모듈

```
src/pipeline_v2/
├── dag/
│   ├── track_a_narrative.py    ✅ 스크립트 생성 + 제목/썸네일 3종
│   ├── track_b_audio.py        ✅ ElevenLabs TTS (14 voice) + Suno BGM 선곡
│   ├── track_c_visual.py       ✅ 스토리보드 → nano-banana → 이미지
│   └── track_d_assembly.py     ✅ FFmpeg 컷 연결 + BGM 덕킹 + 자막 번인
├── qc/
│   ├── layer1_character.py     ✅ Vision(Gemini) + CLIP + ORB 다중 검증
│   ├── layer2_audio.py         ✅ EBU R128 라우드니스 + 클리핑 감지
│   ├── layer3_sync.py          ✅ Faster-Whisper 자막↔나레이션 역검증
│   ├── layer4_video.py         ✅ FFprobe 프레임/해상도/코덱 무결성
│   ├── layer5_meta.py          ✅ JSON Schema (제목/태그/썸네일 3종)
│   └── qc_runner.py            ✅ 5 레이어 통합 + 재시도 루프 + HITL 알림
├── storyboard.py               ✅ Beat Board → Shot List (규칙+LLM 폴백)
├── manim_insert.py             ✅ CH1/CH2 차트/수식 자동 감지 및 합성
├── shorts_derivation.py        ✅ 감정 피크 탐지 → 30~60초 구간 클리핑
├── feedback_loop.py            ✅ YouTube Analytics → episode_metadata.json 기록
├── uploader.py                 ✅ 재시도 업로드 + Thumbnail Experiments 3종
├── meta_generator.py           ✅ 제목/설명/태그/카드 자동 생성
├── copyright_guard.py          ✅ Content ID 위험 사전 감지 → HITL 차단
├── weekly_batch.py             ✅ 주간 배치 오케스트레이터 (asyncio, 42h SLA)
└── episode_schema.py           ✅ EpisodeMeta Pydantic 모델 (20 PQS 필드)

src/adapters/
├── nano_banana.py              ✅ 포즈 40종 × 14 캐릭터, SHA-256 캐시
├── figma_mcp.py                ✅ REST API 기반 42 에셋 export + 전파
└── suno.py                     ✅ Suno API 래퍼 + 175곡 BGM 라이브러리

web/app/hitl/
├── series-approval/page.tsx    ✅ Gate 1: 월간 시리즈 승인
├── thumbnail-veto/page.tsx     ✅ Gate 2: 썸네일 거부권 (YouTube 자동 A/B)
└── final-preview/page.tsx      ✅ Gate 3: 업로드 전 최종 프리뷰

web/app/api/hitl/
├── series-plan/route.ts        ✅
├── thumbnail-veto/route.ts     ✅
└── final-preview/route.ts      ✅

web/e2e/hitl.spec.ts            ✅ Playwright E2E (데스크탑 + 모바일)
tests/pipeline_v2/ (30개 테스트) ✅ 커버리지 ≥70%
```

### 대기 중 (수동 작업 필요)

| 항목 | 담당 | 조건 |
|---|---|---|
| T07 — 14 캐릭터 레퍼런스 14장 | 유저 직접 | `assets/characters/CH{1-7}/{narrator\|guest}_ref.png` |
| T08 — Figma 마스터 템플릿 | 유저 직접 | Figma에서 6 프레임 + 7채널 Variant 토큰 |
| T11 — 560 포즈 라이브러리 생성 | mlops-engineer | T07 완료 후 `nano_banana.generate_full_library()` |
| T01 — MCP 인증 (Figma/GitHub) | devops-engineer | API 토큰 발급 후 `.env` 등록 |
| T06 — $184/월 예산 ceo 승인 | ceo/finance-manager | HITL 에스컬레이션 |
| T39 — ngrok HITL 외부 공개 | devops-engineer | `ngrok start kas-studio` 후 모바일 테스트 |
| T46 — 7채널 E2E 검증 (49편) | qa-auditor | 전체 스택 통합 테스트 |

## 결과

**v2.1 예상 지표 (G1 → G2 v2.1)**:

| 지표 | G1 현재 | G2 v2.1 목표 |
|---|:-:|:-:|
| 편당 제작 시간 | 6~8h | 3~4h |
| 평균 CTR | 5.2% | 8.7% |
| CH1·CH2 CTR | — | 8.2% (Manim +15%p) |
| 평균 AVD | 48% | 64% |
| 쇼츠 파생 비용 | $0.8/편 | $0.08/편 |
| 유저 HITL 월 시간 | N/A | 20분 |
| 구독자 100만 도달 | 14개월 | 7.5개월 |
| Phase 2(G3) 전환 비용 | N/A | 3일 (사전 스키마 설계) |

## 연관 문서

- 운영 런북: `docs/runbooks/weekly-batch.md`
- 에이전트 팀 규약: `AGENTS.md`
- 파이프라인 설정 SSOT: `src/core/config.py`
- 에피소드 메타 스키마: `src/pipeline_v2/episode_schema.py`
- 이전 결정: `docs/adr/001-kas-architecture.md` (존재 시)
