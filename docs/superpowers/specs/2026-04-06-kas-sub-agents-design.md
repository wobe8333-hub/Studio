# KAS Sub-Agent 시스템 설계

> **버전**: 1.0.0 | **작성일**: 2026-04-06  
> **상태**: 설계 완료 — 구현 계획 수립 대기

---

## 1. 설계 철학

### 핵심 원칙: 기존 파이프라인은 건드리지 않는다

`src/pipeline.py`의 18-Step 파이프라인은 이미 잘 작동한다.  
Sub Agent는 **현재 1인 운영자가 수동으로 처리하는 고통점만 자동화**한다.

```
❌ 하지 않는 것: 잘 작동하는 Step들을 Agent로 감싸기
✓  하는 것:      수동 작업, 실패 대응, 학습 루프, 대시보드 정비 자동화
```

### 기존 파이프라인 유지 범위

다음은 Sub Agent 없이 기존 그대로 유지한다:

| 컴포넌트 | 이유 |
|---------|------|
| `src/pipeline.py` (Orchestrator) | 이미 정상 작동 |
| `src/step05/` (Trend & Research) | 이미 정상 작동 |
| `src/step06~11/` (Content Generation) | 이미 정상 작동 |
| `src/step12/` (Publishing) | 이미 정상 작동 |

---

## 2. 현재 시스템의 고통점 분석

| 고통점 | 현재 방식 | 해결 Agent |
|--------|----------|-----------|
| 파이프라인 실패 시 로그 수동 분석 | 운영자가 직접 로그 뒤짐 | **Dev & Maintenance** |
| Manim fallback rate 파악 불가 | 수동으로 `manim_stability_report.json` 확인 | **Dev & Maintenance** |
| CTR/KPI 결과 → 정책 반영 수동 | 운영자가 직접 분석 후 JSON 수정 | **Analytics & Learning** |
| A/B 테스트 승자 선택 수동 | `variant_performance.json` 직접 확인 | **Analytics & Learning** |
| 대시보드 컴포넌트 수정 수동 | 운영자가 직접 코드 작성 | **UI/UX** |
| Supabase 스키마 변경 시 `types.ts` 수동 동기화 | 운영자가 직접 업데이트 | **UI/UX** |
| 채널별 스타일 A/B 최적화 없음 | 스타일 정책 고정 | **Video Style & Character** |

---

## 3. 전체 아키텍처

```
기존 파이프라인 (변경 없음)
─────────────────────────────────────────────────────
pipeline.py → Step05 → Step06~11 → Step12 → Step13~17
─────────────────────────────────────────────────────
                    ↕ JSON 파일 (SSOT)
─────────────────────────────────────────────────────
Sub Agent 레이어 (신규)

  [Phase 1 — 즉시 가치]
  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────┐
  │  Dev & Maintenance  │  │ Analytics & Learning │  │   UI/UX      │
  │  실패 자동 진단/수정  │  │  CTR/KPI 자동 학습   │  │ 대시보드 정비  │
  └─────────────────────┘  └─────────────────────┘  └──────────────┘

  [Phase 2 — 품질 향상]
  ┌───────────────────────────┐
  │  Video Style & Character  │
  │  스타일 A/B 자동화         │
  └───────────────────────────┘
```

---

## 4. Agent 상세 설계

---

### Agent 1: Dev & Maintenance

**목적**: 파이프라인 실패를 운영자 개입 없이 자동 진단하고 수정한다.

| 항목 | 내용 |
|------|------|
| **트리거** | `runs/*/manifest.json`의 `run_state: FAILED` 감지 / 주간 정기 실행 / 수동 |
| **읽는 파일** | `logs/pipeline.log`, `runs/*/manifest.json`, `runs/*/decision_trace.json` |
| **수정 대상** | `src/` 전체 (KAS-PROTECTED 제외) |

**담당 작업**:

```
1. 실패 진단
   - loguru 에러 로그에서 스택 트레이스 추출
   - 원인 파일/라인 특정
   - 패치 생성 및 적용

2. Manim 안정성 모니터링
   - manim_stability_report.json 주간 집계
   - fallback_rate > 50% 시 HITL 신호 발생
   - LaTeX 패턴 감지 규칙 개선

3. 의존성 정비
   - requirements.txt 버전 충돌 감지
   - 보안 취약점 스캔

4. 스키마 동기화 검증
   - scripts/supabase_schema.sql ↔ web/lib/types.ts 일치 여부 확인
   - 불일치 시 Dev Agent가 직접 수정 또는 UI/UX Agent에 위임

5. 주간 Health Check
   - python scripts/preflight_check.py 실행
   - pytest tests/ -q 실행 → 회귀 감지
```

**금지 사항**:
- `src/step08/__init__.py` 내용 비우기 금지 (KAS-PROTECTED)
- `src/quota/__init__.py` (23KB 레거시) 무단 수정 금지
- `--no-verify` 플래그 사용 금지

---

### Agent 2: Analytics & Learning

**목적**: KPI 수집 결과를 자동으로 분석하고 파이프라인 정책에 반영한다.

| 항목 | 내용 |
|------|------|
| **트리거** | `data/global/step13_pending/` 파일 감지 (48h 경과) / 월말 |
| **읽는 파일** | `runs/*/step12/kpi_48h.json`, `runs/*/step13/variant_performance.json` |
| **쓰는 파일** | `data/global/memory_store/`, `data/channels/*/algorithm_policy.json` |

**담당 작업**:

```
1. 48h KPI 자동 수집 및 분석
   - YouTube Analytics API: views/CTR/AVP/AVD/revenue
   - 알고리즘 단계 판정: PRE-ENTRY → SEARCH-ONLY → BROWSE-ENTRY → ALGORITHM-ACTIVE

2. 승리 패턴 자동 추출
   - 조건: CTR ≥ 6.0% AND AVP ≥ 50.0%
   - winning_animation_patterns 업데이트 (최근 50건 유지)

3. A/B 테스트 자동 승자 선택
   - authority / curiosity / benefit 3종 CTR 비교
   - 승자를 topic_priority_bias.json에 자동 반영
   - 초기 가중치: authority 35% / curiosity 45% / benefit 20%

4. Phase 승격 자동 판정
   - 단방향만 허용 (강등 없음)
   - algorithm_policy.json 자동 업데이트

5. 월간 보고 자동화 (Step14~17)
   - 채널별 순이익 집계
   - 리스크 채널 감지 (net_profit < 2,000,000원 → HIGH)
   - 주제 고갈 리스크 평가 (분기 1회)
```

**피드백 루프**:
```
Analytics Agent 결과
  → winning_animation_patterns → Content Generation 정책 개선
  → A/B 승자 제목 모드 → 다음 Step10 title_variant에 반영
  → algorithm_policy → Step03 정책 업데이트
```

---

### Agent 3: UI/UX

**목적**: 웹 대시보드(`web/`)를 운영자 개입 없이 정비하고 개선한다.

| 항목 | 내용 |
|------|------|
| **트리거** | 수동 요청 / Supabase 스키마 변경 감지 / 신규 페이지 요청 |
| **읽는 파일** | `web/` 전체, `scripts/supabase_schema.sql` |
| **쓰는 파일** | `web/` 전체 |
| **검증 도구** | Playwright MCP (`cwstudio.ngrok.app` 스크린샷) |

**담당 작업**:

```
1. 컴포넌트 생성/수정
   - Amber Studio 디자인 시스템 준수
   - oklch 색공간, 7채널 고유 색상 변수 유지
   - Sora(heading) / Geist Sans(body) 폰트 일관성

2. Tailwind v4 토큰 관리
   - globals.css CSS-first 방식 (tailwind.config.ts 없음)
   - @layer utilities {} 블록에 신규 유틸리티 추가

3. Supabase 타입 자동 동기화
   - supabase_schema.sql 변경 감지
   - web/lib/types.ts 자동 업데이트

4. 시각 QA (Playwright)
   - 라이트/다크 모드 스크린샷 비교
   - 모바일 반응형 검증
   - next-themes 패턴 준수 확인

5. 성능 및 접근성
   - 서버/클라이언트 컴포넌트 분리 유지
   - Recharts는 반드시 'use client' 파일에 격리
   - hydration mismatch 방지 (mounted 패턴)
```

**준수 규칙**:
- `document.documentElement.classList` 직접 조작 금지 → `next-themes` 사용
- Supabase 쿼리 결과 `never` 타입 → `as any[]` 캐스팅
- 서버 컴포넌트에서 Recharts 직접 사용 금지

---

### Agent 4: Video Style & Character _(Phase 2)_

**목적**: 채널별 시각 아이덴티티를 유지하고, CTR 피드백을 통해 스타일 정책을 자동 개선한다.

| 항목 | 내용 |
|------|------|
| **트리거** | Analytics Agent의 CTR 피드백 수신 / 수동 / Manim fallback rate 경고 |
| **읽는 파일** | `runs/*/step13/variant_performance.json`, `data/channels/*/style_policy_master.json` |
| **쓰는 파일** | `data/channels/*/style_policy_master.json`, `src/step08/character_manager.py` (파라미터만) |

**담당 작업**:

```
1. 캐릭터 일관성 유지
   - SD XL LoRA seed/negative_prompt 파라미터 관리
   - 7채널 캐릭터 (까미/도리/루나/셜/마루/스텔라/구루) 시각 드리프트 감지

2. 오프닝 시각 후킹 최적화
   - 첫 10초 애니메이션 임팩트 평가
   - CTR이 낮은 채널 → 오프닝 스타일 변경 제안

3. Manim 템플릿 개선
   - fallback_rate > 50% 시 LaTeX-free 코드 패턴 보강
   - 채널별 Manim 스타일 최적화

4. 썸네일 스타일 A/B 자동화
   - CTR 기반 채널별 최적 썸네일 스타일 학습
   - style_policy_master.json 자동 업데이트

5. 스타일 매핑 최적화
   CH1/CH2: comparison → Manim
   CH3: metaphor → Gemini
   CH4: hybrid → Manim + Gemini
   CH5/CH7: timeline → Manim
   CH6: process → Manim
```

---

## 5. 핵심 원칙 요약

```
1. SSOT 준수
   모든 파일 I/O는 ssot.read_json() / ssot.write_json() 사용

2. KAS-PROTECTED 존중
   src/step08/__init__.py 수정 금지 (어떤 Agent도)

3. 쿼터 공유 인식
   Gemini RPM 50 / YouTube 10,000유닛/일 — Agent 간 공유
   작업 전 src/quota/ 모듈로 잔여 확인 필수

4. 비침습적 원칙
   기존 파이프라인(Step00~17) 로직을 바꾸지 않고
   그 결과물(JSON 파일)을 읽어 분석하고 정책만 업데이트
```

---

## 6. 구현 순서

```
Phase 1 (즉시 시작):
  1. Dev & Maintenance  — 실패 자동 대응 (가장 즉각적인 고통 해소)
  2. Analytics & Learning — CTR 피드백 자동화
  3. UI/UX              — 대시보드 자동 정비

Phase 2 (안정화 후):
  4. Video Style & Character — 스타일 최적화
```

---

## 7. 미결 사항

- [ ] Dev & Maintenance의 자동 커밋 범위 확정 (자동 vs 운영자 확인 후 커밋)
- [ ] Analytics Agent의 Phase 승격 알림 채널 결정 (이메일 / 대시보드 알림)
- [ ] UI/UX Agent의 Playwright 실행 환경 (로컬 vs GitHub Actions)
- [ ] Video Style Agent의 LoRA 파라미터 변경 권한 범위 확정
