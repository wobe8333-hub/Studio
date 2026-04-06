# KAS 대시보드 전면 재설계 + 검증 기능 통합 스펙

**작성일**: 2026-04-06  
**상태**: 승인됨  
**범위**: `web/` 전체 Next.js 대시보드

---

## 1. 목표

파이프라인이 실제로 원활하게 작동하는지 검증하기 위한 **테스트 런 검증 대시보드**를 구축한다. 실제 YouTube 업로드 없이 Step00~Step12까지 실행하고, 생성된 모든 아티팩트(스크립트·이미지·영상·썸네일·BGM·Shorts)를 대시보드에서 직접 검수할 수 있어야 한다.

동시에 전체 대시보드를 **Red Light Glassmorphism** 디자인 시스템으로 전면 재설계한다.

---

## 2. 디자인 시스템

### 2.1 색상 팔레트 (Red Light)

| 변수 | 값 | 용도 |
|---|---|---|
| `--c-dark` | `#900000` | 다크 레드 — 숫자 강조, 헤딩 |
| `--c-red` | `#ee2400` | 브라이트 레드 — 버튼, 배지, 포인트 |
| `--c-salmon` | `#ffb09c` | 살몬 — 보조 포인트, 채널 dot |
| `--c-blush` | `#fbd9d3` | 블러쉬 — 카드 배경, 태그 |
| `--c-cream` | `#ffefea` | 크림 — 페이지 배경 |

### 2.2 텍스트 색상

| 변수 | 값 | 용도 |
|---|---|---|
| `--t-primary` | `#1a0505` | 주요 텍스트 (딥 크림슨 블랙) |
| `--t-secondary` | `#5c1a1a` | 보조 텍스트 |
| `--t-muted` | `#9b6060` | 뮤트 텍스트, 레이블 |
| `--t-accent` | `#900000` | 수치 강조 |
| `--t-on-dark` | `#ffefea` | 다크 배경 위 텍스트 |

### 2.3 글래스모피즘

```css
background: rgba(255, 255, 255, 0.55);
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
border: 1px solid rgba(238, 36, 0, 0.12);
border-radius: 16px;
box-shadow: 0 8px 32px rgba(144, 0, 0, 0.08);
```

### 2.4 폰트 시스템

| 역할 | 폰트 | 용도 |
|---|---|---|
| 헤딩 | `Libre Baskerville` | 페이지 제목, KPI 숫자, 카드 타이틀 |
| 본문 | `M PLUS Rounded 1c` | 모든 본문 텍스트, 레이블, 버튼 |
| 모노 | `DM Mono` | 로그, API 경로, 코드, 수치 |

### 2.5 배경

```css
background: linear-gradient(135deg, #fbd9d3 0%, #ffefea 55%, #ffd9cc 100%);
```

사이드바: `rgba(144, 0, 0, 0.88)` + `backdrop-filter: blur(20px)`

---

## 3. 검증 항목 전체 목록 (23개)

### 기존 8개

| # | 항목 | 페이지 | Step |
|---|---|---|---|
| 1 | 지식 수집 내역 | `/knowledge` | Step 05~06 |
| 2 | 트렌드 수집 리스트 | `/trends` | Step 05 |
| 3 | 영상 프롬프트 + 도입부 후킹 | `/runs/[ch]/[id]` | Step 08 |
| 4 | 프롬프트별 이미지 갤러리 | `/runs/[ch]/[id]` | Step 08 |
| 5 | 영상 인라인 플레이어 | `/runs/[ch]/[id]` | Step 08 |
| 6 | 썸네일 3종 나란히 비교 | `/runs/[ch]/[id]` | Step 10 |
| 7 | 채널별 수익 현황 | `/` + `/revenue` | Step 14 |
| 8 | 실시간 반영 (Step 진행 상황) | `/monitor` | 전체 |

### 신규 추가 — 🔴 검증 필수 (6개)

| # | 항목 | 페이지 | Step |
|---|---|---|---|
| 9 | Shorts 결과물 검수 (3편 9:16 미리보기) | `/runs/[ch]/[id]` → Shorts 탭 | Step 08-S |
| 10 | BGM 오디오 플레이어 + 톤 정보 | `/runs/[ch]/[id]` → 오디오 탭 | Step 09 |
| 11 | 제목 배리언트 A/B/C 선택 UI | `/runs/[ch]/[id]` → 제목 선택 탭 | Step 10 |
| 12 | Vision QA 상세 (캐릭터 일관성·텍스트 가독성·콘텐츠 안전) | `/runs/[ch]/[id]` → QA 상세 탭 | Step 11 |
| 13 | Manim 애니메이션 안정성 + fallback_rate | `/monitor` → Manim 탭 | Step 08 |
| 14 | 비용 예측 vs 실제 비교 | `/cost` → 예측 vs 실제 탭 | Core/pre_cost_estimator |

### 신규 추가 — 🟡 운영 유용 (6개)

| # | 항목 | 페이지 | Step |
|---|---|---|---|
| 15 | 이연 업로드 대기 목록 + 재시도 | `/cost` → 이연 업로드 탭 | Step 12 |
| 16 | HITL 신호 대시보드 (미해결 신호 통합) | `/monitor` → HITL 탭 | Sub-Agent |
| 17 | KPI 48시간 수집 결과 | `/learning` → KPI 탭 | Step 12~13 |
| 18 | 알고리즘 단계 승격 현황 (4단계) | `/learning` → 알고리즘 탭 | Step 13 |
| 19 | SEO 메타데이터 검수 + 편집 | `/runs/[ch]/[id]` → SEO 탭 | Step 08 |
| 20 | Sub-Agent 실행 현황 (4종) | `/monitor` → Sub-Agent 탭 | agents/ |

### 신규 추가 — 🟢 장기 분석 (3개)

| # | 항목 | 페이지 | Step |
|---|---|---|---|
| 21 | 월별 수익 추세 그래프 | `/revenue` → 추세 탭 | Step 14 |
| 22 | 주제 지속성 분석 (topic_capacity, depletion_risk) | `/risk` → 지속성 탭 | Step 17 |
| 23 | 학습 바이어스 시각화 (레이더 차트) | `/learning` → 바이어스 탭 | Step 13 |

---

## 4. 실시간 반영 전략

### 4.1 A+B 하이브리드 검증 워크플로우

```
[① 트리거] 채널 선택 → "테스트 런" 버튼 클릭 (실제 업로드 없이 Step00~Step12 실행)
       ↓ 실행 중
[② 실시간 관찰] /monitor — Step 진행 트래커 + 이미지 실시간 미리보기 + 로그 스트림
       ↓ 완료 후
[③ 결과 검수] /runs/[ch]/[id] — 전체 아티팩트 종합 검수 (스크립트·이미지·영상·BGM·Shorts·썸네일·SEO)
```

### 4.2 실시간 기술 레이어

| 기술 | 대상 페이지 | 갱신 주기 |
|---|---|---|
| Supabase Realtime | `/` (홈) | 즉시 |
| Polling (fetch) | `/monitor` (Step 진행, 로그, Manim) | 3초 |
| On-demand fetch | `/knowledge`, `/trends`, `/runs`, `/cost` | 탭 전환 시 |

---

## 5. 페이지별 변경 상세

### 5.1 홈 대시보드 (`/`) — 강화

**기존 유지**: KPI 4개 카드, 파이프라인 타임라인  
**신규 추가**:
- 채널별 수익 현황 탭 전환 (CH1~CH4 → CH7)
- 현재 실행 중인 Run 실시간 표시 (Supabase Realtime)
- `▶ 테스트 런 실행` 버튼 → `/api/pipeline/trigger` POST

### 5.2 파이프라인 모니터 (`/monitor`) — 핵심 강화

**기존 유지**: Preflight 패널, 로그 뷰어  
**신규 추가 — 탭 구조**:
- **Step 진행 탭**: Step00~17 시각적 진행 트래커 (아이콘·상태·소요시간)
- **실시간 미리보기 탭**: Step08 실행 중 생성 이미지 즉시 표시 (3초 폴링)
- **Manim 탭**: fallback_rate, 렌더 성공/실패 현황
- **HITL 탭**: hitl_signals.json 미해결 신호 목록 + 해결 버튼
- **Sub-Agent 탭**: 4종 Sub-Agent 마지막 실행 결과 요약

### 5.3 Run 상세 — 검수 허브 (`/runs/[ch]/[id]`) — 핵심 강화

**탭 구조로 재설계**:

| 탭 | 내용 | 신규/기존 |
|---|---|---|
| 스크립트 | 전문 + 도입부 후킹 하이라이트 (빨간 밑줄) | 강화 |
| 이미지 갤러리 | 장면별 이미지 + 생성 프롬프트 매핑 | 강화 |
| 영상 | 인라인 비디오 플레이어 | 기존 |
| Shorts | 3편 9:16 세로 영상 미리보기 | **신규** |
| 오디오 | 나레이션 + BGM 오디오 플레이어, bgm_category_tone | **신규** |
| 썸네일 | 3종 나란히 비교 + 선택 | 기존 |
| 제목 선택 | authority / curiosity / benefit 3종 비교 + 선택 | **신규** |
| SEO | 설명문·태그 15개·해시태그 검수 + 편집 | **신규** |
| QA 상세 | Vision QA 프레임 분석 결과 상세 | **신규** |
| 비용 | 비용 예측 vs 실제 + Step별 분석 | 강화 |

### 5.4 지식 수집 뷰어 (`/knowledge`) — 강화

- 수집 단계별 표시: Tavily → Wikipedia → Gemini Deep Research
- KnowledgePackage 구조 트리 뷰어
- 팩트체크 결과 배지
- 채널별 탭 전환 (30초 폴링으로 Step05 완료 반영)

### 5.5 트렌드 관리 (`/trends`) — 강화

- 채널별 탭 → `/api/knowledge?channel=CHx` 자동 fetch
- 점수 구성 시각화: 관심도 40% + 적합도 25% + 수익성 20% + 긴급도 15%
- 소스별 수집 현황 배지 (구글 트렌드 / 네이버 / YouTube)

### 5.6 비용/쿼터 (`/cost`) — 강화

- **예측 vs 실제 탭**: pre_cost_estimator.py 결과 vs 실제 소비 비교
- **이연 업로드 탭**: deferred_jobs 목록, 잔여 쿼터, 재시도 버튼

### 5.7 학습 피드백 (`/learning`) — 강화

- **KPI 48h 탭**: 업로드 후 48시간 YouTube Analytics 결과
- **알고리즘 탭**: PRE-ENTRY → SEARCH → BROWSE → ACTIVE 단계 현황
- **바이어스 탭**: 학습 바이어스 레이더 차트

### 5.8 수익 추적 (`/revenue`) — 강화

- **추세 탭**: 월별 수익 꺾은선 그래프 (AdSense / Affiliate 구분)

### 5.9 리스크 (`/risk`) — 강화

- **지속성 탭**: topic_capacity, depletion_risk 채널별 시각화

### 5.10 나머지 페이지 — 스타일 전환만

`/qa`, `/settings`, `/channels/[id]`, `/login` → Red Light Glassmorphism 스타일 적용, 기능 변경 없음

---

## 6. 신규 API 라우트

| 라우트 | 메서드 | 용도 |
|---|---|---|
| `/api/pipeline/steps` | GET | Step별 진행 상태 + 소요시간 조회 |
| `/api/runs/[ch]/[id]/shorts` | GET | Shorts 3편 경로 + 메타데이터 |
| `/api/runs/[ch]/[id]/bgm` | GET | BGM 파일 경로 + tone 정보 |
| `/api/runs/[ch]/[id]/seo` | GET/PATCH | SEO 메타데이터 조회 + 편집 |
| `/api/cost/projection` | GET | pre_cost_estimator 결과 조회 |
| `/api/agents/status` | GET | Sub-Agent 4종 마지막 실행 결과 |
| `/api/learning/kpi` | GET | KPI 48h 수집 결과 |
| `/api/learning/algorithm` | GET | 알고리즘 단계 승격 이력 |
| `/api/sustainability` | GET | 주제 지속성 분석 결과 |

기존 `/api/artifacts/[...path]`를 통해 BGM, Shorts 영상 파일도 서빙 가능 (확장).

---

## 7. globals.css 변경

Tailwind v4 CSS-first 방식 유지. `@theme inline` 블록에 Red Light 팔레트 추가:

```css
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Mplus+Rounded+1c:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');

@theme inline {
  --color-primary: oklch(0.45 0.22 25);      /* #ee2400 근사 */
  --color-primary-dark: oklch(0.30 0.20 25); /* #900000 근사 */
  --color-blush: oklch(0.93 0.04 15);
  --color-cream: oklch(0.97 0.02 15);
  --font-heading: 'Libre Baskerville', Georgia, serif;
  --font-body: 'Mplus Rounded 1c', -apple-system, sans-serif;
  --font-mono: 'DM Mono', 'Consolas', monospace;
}
```

---

## 8. 구현 제약 및 주의사항

- **Step08-S Shorts API**: 현재 `/api/artifacts`가 mp4 서빙 지원하므로 경로 규칙만 추가하면 됨
- **BGM 파일 서빙**: `runs/{ch}/{run}/step09/bgm_overlay.mp3` 경로, artifacts API 확장
- **pre_cost_estimator**: `src/core/pre_cost_estimator.py`의 `load_cost_projection()` 결과를 읽는 API 신규 작성
- **Shorts 경로**: `src/step08_s/shorts_generator.py`가 `runs/{ch}/{run}/step08_s/` 에 저장
- **KAS_ROOT 환경변수**: 모든 파일시스템 API는 반드시 `KAS_ROOT` 기반 경로 사용
- **SSOT**: 모든 JSON 읽기는 `ssot.read_json()` 패턴 사용 (웹 API에서는 직접 fs.readFile 사용 가능)
- **Tailwind v4**: `tailwind.config.ts` 없음 — `globals.css`에서만 설정
- **다크모드**: 기존 `next-themes` 유지하되, Red Light 팔레트는 라이트 모드 기준으로 설계

---

## 9. 구현 순서 권장

1. **globals.css + layout.tsx** — Red Light 시스템 + K 폰트 적용 (전체 기반)
2. **사이드바 (`sidebar-nav.tsx`)** — Red Light 다크 사이드바
3. **홈 (`/`)** — KPI 카드 + 테스트 런 버튼 + 수익 탭
4. **파이프라인 모니터 (`/monitor`)** — Step 트래커 + 실시간 미리보기 + 탭 구조
5. **Run 상세 (`/runs/[ch]/[id]`)** — 탭 10개 재설계 (Shorts, BGM, 제목, SEO, Vision QA)
6. **신규 API 라우트** — steps, shorts, bgm, seo, projection, agents/status
7. **지식/트렌드 강화** — 채널 탭 + 점수 시각화
8. **비용/학습/수익/리스크 강화** — 추가 탭
9. **나머지 페이지 스타일 전환**
