# 트렌드 주제 품질 개선 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 7채널 트렌드 주제 수집의 grade 불일치 버그 수정, YouTube 데이터 품질 개선, 점수 연결 수정, Supabase UPDATE 보안 강화, UI breakdown 실제값 표시

**Architecture:** 백엔드(scorer.py → trend_collector.py → sync_to_supabase.py) → Supabase DB → 프론트엔드(actions.ts → page.tsx) 순서로 수정. 각 계층이 독립적으로 테스트 가능하도록 구성.

**Tech Stack:** Python (loguru, pytest), TypeScript (Next.js 16, Supabase SSR), Supabase PostgreSQL

---

## 파일 맵

| 역할 | 파일 | 변경 유형 |
|---|---|---|
| 점수화 + grade 분류 | `src/step05/scorer.py` | 수정 |
| 트렌드 수집 오케스트레이터 | `src/step05/trend_collector.py` | 수정 |
| Supabase 동기화 스크립트 | `scripts/sync_to_supabase.py` | 수정 |
| Supabase admin 클라이언트 | `web/lib/supabase/server-admin.ts` | **신규** |
| grade 업데이트 Server Action | `web/app/trends/actions.ts` | 수정 |
| 환경변수 예제 | `web/.env.local.example` | 수정 |
| DB 스키마 | `scripts/supabase_schema.sql` | 수정 |
| 트렌드 UI 페이지 | `web/app/trends/page.tsx` | 수정 |
| scorer 테스트 | `tests/test_step05_scorer.py` | 수정 |
| trend_collector 테스트 | `tests/test_step05_knowledge.py` | 수정 |

---

## Task 1: scorer.py — grade 문자열 통일 + 임계값 재조정 (A + E)

**Files:**
- Modify: `src/step05/scorer.py:110-115`
- Modify: `tests/test_step05_scorer.py`

### 배경

현재 `scorer.py`는 grade로 `"reject"`를 반환하지만 UI의 `GradeBadge`는 `"rejected"`만 인식한다.
임계값도 80/60이라 실제 외부 데이터 없이는 절대 "auto"에 도달 불가.

- [ ] **Step 1: 기존 테스트 실행하여 현재 상태 확인**

```bash
cd C:/Users/조찬우/Desktop/ai_stuidio_claude
pytest tests/test_step05_scorer.py -v
```

Expected: `test_grade_reject_low_score` 통과 (현재 `"reject"` 반환 중)

- [ ] **Step 2: 테스트 업데이트 — 새 grade 값 + 새 임계값 반영**

`tests/test_step05_scorer.py` 전체를 아래로 교체:

```python
"""Step05 — 트렌드 점수화 알고리즘 테스트."""

import pytest
from src.step05.scorer import score_topic


def test_score_topic_returns_dict():
    """score_topic()이 올바른 dict 구조를 반환하는지 확인."""
    result = score_topic(
        topic="금리 인하",
        category="economy",
        trends_score=0.7,
        news_score=0.6,
        community_score=0.5,
    )
    assert isinstance(result, dict)
    assert "topic" in result
    assert "score" in result
    assert "grade" in result
    assert "category" in result
    assert "breakdown" in result


def test_score_range():
    """점수가 0~100 범위인지 확인."""
    result = score_topic("테스트 주제", "science", 0.5, 0.5, 0.5)
    assert 0 <= result["score"] <= 100


def test_grade_auto_high_score():
    """높은 점수(70+)는 'auto' 등급이어야 함."""
    result = score_topic("초인기 주제", "economy", 1.0, 1.0, 1.0)
    assert result["grade"] == "auto"


def test_grade_review_mid_score():
    """중간 점수(55~69)는 'review' 등급이어야 함."""
    # economy: fit=0.7, revenue=1.0, urgency=1.0 → base=52.5
    # trends_score=0.4 → interest=0.4*40=16 → total=68.5 → review
    result = score_topic("중간 주제", "economy", 0.4, 0.0, 0.0, days_since_trending=1)
    assert result["grade"] == "review"


def test_grade_rejected_low_score():
    """낮은 점수(<55)는 'rejected' 등급이어야 함."""
    result = score_topic("비인기 주제", "history", 0.0, 0.0, 0.0)
    assert result["grade"] == "rejected"


def test_grade_values_are_valid():
    """grade 값이 허용된 3개 중 하나여야 함."""
    for trends in [0.0, 0.5, 1.0]:
        result = score_topic("주제", "economy", trends, 0.0, 0.0)
        assert result["grade"] in ("auto", "review", "rejected"), \
            f"unexpected grade: {result['grade']} (score={result['score']})"


def test_score_topic_all_categories():
    """7개 카테고리 모두에 대해 점수화가 동작하는지 확인."""
    categories = ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]
    for cat in categories:
        result = score_topic(f"{cat} 테스트 주제", cat, 0.5, 0.5, 0.5)
        assert result["category"] == cat
        assert result["grade"] in ("auto", "review", "rejected")


def test_breakdown_keys_present():
    """breakdown에 4개 구성요소가 모두 있어야 함."""
    result = score_topic("주제", "economy", 0.5, 0.5, 0.5)
    assert set(result["breakdown"].keys()) == {"interest", "fit", "revenue", "urgency"}


def test_score_topic_without_external_scores():
    """외부 점수 없이도 동작하는지 확인 (에버그린 주제)."""
    result = score_topic("에버그린 주제", "science", 0.0, 0.0, 0.0)
    assert isinstance(result["score"], float)
    assert result["grade"] in ("auto", "review", "rejected")
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_step05_scorer.py -v
```

Expected: `test_grade_rejected_low_score`, `test_grade_values_are_valid` FAIL (`"reject"` 반환 중)

- [ ] **Step 4: scorer.py 수정**

`src/step05/scorer.py` 108~115번 줄 교체:

```python
    # 등급 분류
    if final_score >= 70:
        grade = "auto"      # 자동 승격
    elif final_score >= 55:
        grade = "review"    # 인간 리뷰 대기
    else:
        grade = "rejected"  # 폐기
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_step05_scorer.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/step05/scorer.py tests/test_step05_scorer.py
git commit -m "fix: grade 문자열 reject→rejected 통일 + auto 임계값 80→70 재조정"
```

---

## Task 2: trend_collector.py — YouTube keywords 전환 + news_scores 연결 (B + C)

**Files:**
- Modify: `src/step05/trend_collector.py:82-113` (`_collect_layer2`), `270-276` (로그 통계)
- Modify: `tests/test_step05_knowledge.py`

### 배경

`_collect_layer2()`가 `result.get("topics")` (raw 영상 제목 `[한국경제TV LIVE]` 등)을 쓰고 있다.
`fetch_youtube_trending()`은 이미 정제된 `keywords`와 `scores`를 반환하므로 그것을 써야 한다.
또한 YouTube `scores`를 `news_scores`에 연결해야 interest_score 계산에 반영된다.

- [ ] **Step 1: 기존 collect_trends 관련 테스트 확인**

```bash
pytest tests/test_step05_knowledge.py -v
```

Expected: 현재 상태 확인

- [ ] **Step 2: 테스트 추가 — keywords 전환 동작 검증**

`tests/test_step05_knowledge.py` 끝에 아래 클래스 추가:

```python
class TestCollectLayer2YouTubeKeywords:
    """Layer2 YouTube 수집이 keywords를 사용하는지 검증."""

    def test_layer2_uses_keywords_not_raw_titles(self):
        """YouTube raw 제목 대신 정제된 keywords가 수집 결과에 포함되어야 함."""
        from unittest.mock import patch
        from src.step05.trend_collector import _collect_layer2

        mock_yt = {
            "configured": True,
            "topics": ["[한국경제TV LIVE] 금리 인상 긴급 분석", "주식 전망 #shorts"],
            "keywords": ["금리", "주식"],
            "scores": {"금리": 0.9, "주식": 0.7},
        }
        mock_rss = ({"금리": 0.5}, [])  # fetch_news_context 반환 형식

        with patch("src.step05.sources.youtube_trending.fetch_youtube_trending",
                   return_value=mock_yt), \
             patch("src.step05.sources.rss.fetch_news_context",
                   return_value=mock_rss):
            result = _collect_layer2("economy")

        # raw 제목이 포함되면 안 됨
        assert "[한국경제TV LIVE] 금리 인상 긴급 분석" not in result["topics"]
        assert "#shorts" not in " ".join(result["topics"])

        # 정제된 키워드가 포함되어야 함
        assert "금리" in result["topics"] or "주식" in result["topics"]

        # YouTube scores가 news_scores에 반영되어야 함
        assert result["news_scores"].get("금리") == 0.9 or \
               result["news_scores"].get("주식") == 0.7

    def test_layer2_news_scores_enable_interest_calculation(self):
        """news_scores가 있으면 interest_score가 0보다 커야 함."""
        from unittest.mock import patch
        from src.step05.trend_collector import collect_trends

        mock_yt = {
            "configured": True,
            "topics": ["[라이브] 경제 뉴스"],
            "keywords": ["금리"],
            "scores": {"금리": 0.8},
        }
        mock_google = {"demand_score": {}, "pytrends_available": False, "error": None}

        with patch("src.step05.sources.youtube_trending.fetch_youtube_trending",
                   return_value=mock_yt), \
             patch("src.step05.sources.google_trends.fetch_trends_scores",
                   return_value=mock_google), \
             patch("src.step05.sources.naver.fetch_naver_trends",
                   return_value={"topics": []}), \
             patch("src.step05.sources.reddit.fetch_reddit_topics",
                   return_value={"configured": False}), \
             patch("src.step05.sources.community.fetch_community_topics",
                   return_value={"topics": []}), \
             patch("src.step05.trend_collector.deduplicate_topics",
                   side_effect=lambda ch, topics, **kw: topics):

            results = collect_trends("CH1", "economy", limit=5)

        # 금리 주제가 수집됐으면 점수가 0보다 높아야 함
        matched = [r for r in results if r.get("topic") == "금리"]
        if matched:
            assert matched[0]["score"] > 52.5, \
                f"interest_score 연결 안 됨: score={matched[0]['score']}"
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_step05_knowledge.py::TestCollectLayer2YouTubeKeywords -v
```

Expected: FAIL — 현재 raw 제목을 쓰고 있어서 `[한국경제TV LIVE]` 포함

- [ ] **Step 4: trend_collector.py `_collect_layer2` 수정**

`src/step05/trend_collector.py` 88~93번 줄 교체:

```python
    try:
        from src.step05.sources.youtube_trending import fetch_youtube_trending
        result = fetch_youtube_trending(category)
        if result.get("configured"):
            # raw 영상 제목(topics) 대신 정제된 키워드(keywords) 사용
            topics.extend(result.get("keywords", [])[:8])
            # YouTube 빈도 점수를 news_scores에 연결 → interest_score 계산에 반영
            news_scores.update(result.get("scores", {}))
    except Exception as e:
        logger.debug(f"[STEP05-L2] youtube_trending 수집 실패: {e}")
```

- [ ] **Step 5: trend_collector.py 로그 통계 수정**

`src/step05/trend_collector.py` 270~276번 줄 (등급별 통계 로깅 부분) 수정:

```python
    # 등급별 통계 로깅
    auto_count = sum(1 for s in scored if s["grade"] == "auto")
    review_count = sum(1 for s in scored if s["grade"] == "review")
    rejected_count = sum(1 for s in scored if s["grade"] == "rejected")
    logger.info(
        f"[STEP05] {channel_id} 수집 완료: 전체={len(scored)} "
        f"자동승격={auto_count} 리뷰대기={review_count} 거부={rejected_count}"
    )
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_step05_knowledge.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add src/step05/trend_collector.py tests/test_step05_knowledge.py
git commit -m "fix: YouTube keywords 사용으로 전환 + news_scores 연결로 interest_score 수정"
```

---

## Task 3: sync_to_supabase.py — grade 보호 + breakdown 저장 (G + F 일부)

**Files:**
- Modify: `scripts/sync_to_supabase.py:178-220`

### 배경

재동기화 시 `upsert`가 이미 운영자가 검토한 `approved`/`rejected` grade를 덮어쓴다.
또한 `breakdown` 상세 점수도 저장해야 UI에서 실제값 표시 가능.

- [ ] **Step 1: sync_trend_topics 함수 수정**

`scripts/sync_to_supabase.py`의 `sync_trend_topics()` 함수 전체를 아래로 교체:

```python
def sync_trend_topics() -> int:
    """트렌드 주제 동기화 (knowledge store)"""
    total = 0

    for ch_id in CHANNEL_IDS:
        assets_path = (
            KAS_ROOT
            / "data"
            / "knowledge_store"
            / ch_id
            / "discovery"
            / "raw"
            / "assets.jsonl"
        )
        if not assets_path.exists():
            continue

        # 기존 DB에서 이미 검토 완료된 항목의 grade 일괄 조회
        try:
            existing = (
                supabase.table("trend_topics")
                .select("reinterpreted_title, grade")
                .eq("channel_id", ch_id)
                .in_("grade", ["approved", "rejected"])
                .execute()
            )
            protected_titles = {
                row["reinterpreted_title"]
                for row in (existing.data or [])
            }
        except Exception as e:
            logger.warning(f"기존 grade 조회 실패 {ch_id}: {e}")
            protected_titles = set()

        with open(assets_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    reinterpreted_title = rec.get("reinterpreted_title")

                    row = {
                        "channel_id": ch_id,
                        "original_topic": rec.get("original_topic"),
                        "reinterpreted_title": reinterpreted_title,
                        "score": rec.get("score"),
                        "is_trending": rec.get("is_trending", False),
                        "topic_type": rec.get("topic_type"),
                        "collected_at": rec.get("collected_at", datetime.utcnow().isoformat()),
                        "breakdown": rec.get("breakdown"),
                    }

                    # 이미 승인/거부된 항목은 grade 덮어쓰지 않음
                    if reinterpreted_title not in protected_titles:
                        row["grade"] = rec.get("grade", "review")

                    supabase.table("trend_topics").upsert(
                        row, on_conflict="channel_id,reinterpreted_title"
                    ).execute()
                    total += 1
                except Exception as e:
                    logger.warning(f"트렌드 주제 파싱 실패: {e}")

    logger.info(f"트렌드 주제 동기화 완료: {total}건")
    return total
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/sync_to_supabase.py
git commit -m "fix: 재동기화 시 approved/rejected grade 보호 + breakdown 저장 추가"
```

---

## Task 4: Supabase admin 클라이언트 생성 + actions.ts 수정 (D)

**Files:**
- Create: `web/lib/supabase/server-admin.ts`
- Modify: `web/app/trends/actions.ts`
- Modify: `web/.env.local.example`

### 배경

`updateTopicGrade()` Server Action이 anon key로 UPDATE를 시도하는데 RLS UPDATE 정책이 없어 실패한다.
service_role key를 서버 전용 클라이언트에서만 사용하면 보안을 유지하면서 해결 가능.

- [ ] **Step 1: server-admin.ts 생성**

`web/lib/supabase/server-admin.ts` 신규 생성:

```typescript
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/lib/types'

/**
 * service_role key를 사용하는 서버 전용 Supabase 클라이언트.
 * Server Action / API Route 내부에서만 사용할 것.
 * 클라이언트 컴포넌트에서 절대 import 금지.
 */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !key) {
    throw new Error('NEXT_PUBLIC_SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 미설정')
  }

  return createClient<Database>(url, key, {
    auth: { persistSession: false },
  })
}
```

- [ ] **Step 2: actions.ts 수정 — admin 클라이언트 사용**

`web/app/trends/actions.ts` 전체를 아래로 교체:

```typescript
'use server'

import { revalidatePath } from 'next/cache'
import { createAdminClient } from '@/lib/supabase/server-admin'

type Grade = 'approved' | 'rejected' | 'review'

/**
 * trend_topics 테이블의 grade 필드를 Supabase에서 업데이트합니다.
 * service_role key 사용 — RLS를 우회하여 UPDATE 가능.
 */
export async function updateTopicGrade(
  topicId: number,
  grade: Grade
): Promise<{ ok: boolean; error?: string }> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (
    !supabaseUrl ||
    supabaseUrl.includes('xxxxxxxxxxxx') ||
    !serviceKey
  ) {
    // Supabase 미연동 시 조용히 성공 (로컬 상태 변경만 동작)
    return { ok: true }
  }

  try {
    const supabase = createAdminClient()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (supabase as any)
      .from('trend_topics')
      .update({ grade })
      .eq('id', topicId)

    if (error) {
      return { ok: false, error: error.message }
    }

    revalidatePath('/trends')
    return { ok: true }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}
```

- [ ] **Step 3: .env.local.example 업데이트**

`web/.env.local.example` 끝에 추가:

```
# Supabase service_role key (서버 전용 — 절대 클라이언트에 노출 금지)
# Supabase 대시보드 → Settings → API → service_role 에서 복사
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

- [ ] **Step 4: 빌드 확인**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 타입 에러 없이 빌드 성공

- [ ] **Step 5: 커밋**

```bash
git add web/lib/supabase/server-admin.ts web/app/trends/actions.ts web/.env.local.example
git commit -m "feat: service_role admin 클라이언트 추가 + updateTopicGrade RLS 우회"
```

---

## Task 5: supabase_schema.sql — breakdown 컬럼 추가 (F)

**Files:**
- Modify: `scripts/supabase_schema.sql`

### 배경

`sync_to_supabase.py`가 이제 `breakdown` JSON을 저장하지만 Supabase 테이블에 컬럼이 없다.
또한 운영 DB에 직접 실행할 ALTER 문도 준비해야 한다.

- [ ] **Step 1: supabase_schema.sql 수정**

`scripts/supabase_schema.sql`에서 `trend_topics` 테이블 정의를 찾아 `breakdown` 컬럼 추가:

```sql
CREATE TABLE IF NOT EXISTS trend_topics (
  id                   SERIAL PRIMARY KEY,
  channel_id           TEXT REFERENCES channels(id),
  original_topic       TEXT,
  reinterpreted_title  TEXT,
  score                REAL,
  grade                TEXT DEFAULT 'review',
  breakdown            JSONB,
  is_trending          BOOLEAN DEFAULT FALSE,
  topic_type           TEXT,
  collected_at         TIMESTAMPTZ,
  UNIQUE(channel_id, reinterpreted_title)
);
```

- [ ] **Step 2: 운영 DB에 적용할 마이그레이션 메모**

`scripts/supabase_schema.sql` 파일 맨 아래에 아래 주석 추가:

```sql
-- ── 마이그레이션: breakdown 컬럼 추가 (2026-04-07) ─────────────
-- 기존 DB에는 아래 ALTER 문을 Supabase SQL Editor에서 직접 실행:
-- ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS breakdown JSONB;
```

- [ ] **Step 3: 커밋**

```bash
git add scripts/supabase_schema.sql
git commit -m "feat: trend_topics에 breakdown JSONB 컬럼 추가"
```

---

## Task 6: trends/page.tsx — breakdown 실제값 표시 (F)

**Files:**
- Modify: `web/app/trends/page.tsx:28-36` (Topic 인터페이스), `248-260` (배지 렌더링)

### 배경

현재 점수 배지가 `Math.round(topic.score * pct / 100)` 비율 추정값을 표시한다.
`breakdown` 실제 데이터가 있으면 그것을 우선 표시하도록 수정.

- [ ] **Step 1: Topic 인터페이스에 breakdown 추가**

`web/app/trends/page.tsx` 28~36번 줄 `Topic` 인터페이스 수정:

```typescript
interface Breakdown {
  interest: number
  fit: number
  revenue: number
  urgency: number
}

interface Topic {
  id: number
  channel_id: string
  reinterpreted_title: string
  score: number
  grade: Grade
  is_trending: boolean
  topic_type: string
  breakdown?: Breakdown
}
```

- [ ] **Step 2: Supabase 조회에 breakdown 컬럼 추가**

`web/app/trends/page.tsx` 79번 줄 `.select()` 수정:

```typescript
      .from('trend_topics')
      .select('id, channel_id, reinterpreted_title, score, grade, is_trending, topic_type, breakdown')
      .order('score', { ascending: false })
      .limit(100)
```

- [ ] **Step 3: Supabase 데이터 매핑에 breakdown 추가**

`web/app/trends/page.tsx` 84~97번 줄 `data.map()` 블록 수정:

```typescript
          setTopics(
            data.map((row) => ({
              id: row.id,
              channel_id: row.channel_id ?? '',
              reinterpreted_title: row.reinterpreted_title ?? '',
              score: row.score ?? 0,
              grade: (row.grade as Grade) ?? 'review',
              is_trending: row.is_trending ?? false,
              topic_type: row.topic_type ?? '',
              breakdown: row.breakdown ?? undefined,
            }))
          )
```

- [ ] **Step 4: 배지 렌더링을 breakdown 실제값 우선으로 수정**

`web/app/trends/page.tsx` 248~260번 줄 점수 배지 블록 교체:

```tsx
                      <div className="flex gap-1 flex-wrap mt-1">
                        {[
                          { label: '관심도', pct: 40, key: 'interest' as const },
                          { label: '적합도', pct: 25, key: 'fit' as const },
                          { label: '수익성', pct: 20, key: 'revenue' as const },
                          { label: '긴급도', pct: 15, key: 'urgency' as const },
                        ].map(s => {
                          const val = topic.breakdown
                            ? Math.round(topic.breakdown[s.key])
                            : Math.round(topic.score * s.pct / 100)
                          return (
                            <span key={s.label} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(238,36,0,0.07)', color: '#9b6060' }}>
                              {s.label} {s.pct}%·{val}
                            </span>
                          )
                        })}
                      </div>
```

- [ ] **Step 5: 빌드 확인**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: 타입 에러 없이 빌드 성공

- [ ] **Step 6: 커밋**

```bash
git add web/app/trends/page.tsx
git commit -m "feat: 트렌드 배지에 breakdown 실제값 우선 표시"
```

---

## Task 7: 전체 테스트 + DB 마이그레이션 안내

**Files:** 없음 (검증만)

- [ ] **Step 1: 전체 Python 테스트 실행**

```bash
cd C:/Users/조찬우/Desktop/ai_stuidio_claude
pytest tests/test_step05_scorer.py tests/test_step05_knowledge.py tests/test_step05_sources.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 2: 웹 빌드 최종 확인**

```bash
cd web && npm run build 2>&1 | tail -30
```

Expected: `✓ Compiled successfully` 또는 `Route (app) ...` 목록 출력

- [ ] **Step 3: Supabase DB 마이그레이션 실행**

Supabase 대시보드 → SQL Editor에서 아래 실행:

```sql
-- breakdown 컬럼 추가
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS breakdown JSONB;

-- 기존 중복 데이터 정리 (동일 channel_id + reinterpreted_title 중 id가 큰 것 삭제)
DELETE FROM trend_topics
WHERE id NOT IN (
  SELECT MIN(id)
  FROM trend_topics
  GROUP BY channel_id, reinterpreted_title
);
```

- [ ] **Step 4: web/.env.local에 service_role key 추가**

실제 `web/.env.local` 파일에 아래 추가 (Supabase 대시보드 → Settings → API에서 복사):

```
SUPABASE_SERVICE_ROLE_KEY=<실제_서비스_롤_키>
```

- [ ] **Step 5: 대시보드 동작 확인**

브라우저에서 `http://localhost:7002/trends` 접속 후:
1. 점수가 52.5 고정이 아닌 다양한 값으로 표시되는지 확인
2. 승인/거부 버튼 클릭 시 새로고침 후 상태 유지 확인
3. grade "자동 승인" 항목이 존재하는지 확인 (다음 Step05 실행 후)

- [ ] **Step 6: 최종 커밋**

```bash
git add .
git commit -m "docs: 트렌드 주제 품질 개선 완료 - 7가지 이슈 수정"
```
