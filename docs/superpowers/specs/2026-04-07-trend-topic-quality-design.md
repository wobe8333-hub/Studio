# 트렌드 주제 품질 개선 설계

날짜: 2026-04-07

## 문제 요약

수집된 트렌드 주제 12/12개가 전부 "검토 필요" 상태로 표시됨. 실제 원인은 7가지 버그/설계 결함이 중첩된 것.

## 발견된 이슈

| # | 분류 | 문제 | 파일 | 심각도 |
|---|---|---|---|---|
| A | 버그 | `"reject"` ↔ `"rejected"` 문자열 불일치 → 거부 대상이 전부 "검토 필요"로 fallback | `scorer.py:115` | 높음 |
| B | 데이터 | YouTube raw 제목(`topics`) 대신 정제 키워드(`keywords`) 사용 안 함 | `trend_collector.py:_collect_layer2` | 높음 |
| C | 점수 | `news_scores`가 YouTube `scores`와 미연결 → interest_score 항상 0 → 최대 52.5점 | `trend_collector.py:collect_trends` | 높음 |
| D | 보안 | Supabase anon UPDATE 정책 없음 → 승인/거부 버튼 DB 저장 실패 | `supabase_schema.sql` | 높음 |
| E | 임계값 | auto 기준 80은 실제 데이터 없이 절대 달성 불가 → 70으로 재조정 | `scorer.py:110` | 중간 |
| F | UI | 점수 배지가 실제 구성요소가 아닌 비율 추정값 표시 | `trends/page.tsx:250` | 낮음 |
| G | 동기화 | 재동기화 시 이미 승인/거부된 grade 덮어씀 | `sync_to_supabase.py:205` | 중간 |

## 설계

### 1. Grade 문자열 통일 (A)

`scorer.py` 115번 줄:
```python
grade = "reject"  →  grade = "rejected"
```

로깅 문자열도 동일하게 수정. `trend_collector.py` log 통계 카운터도 `"reject"` → `"rejected"` 통일.

### 2. YouTube 소스 수정 (B + C)

`_collect_layer2()` 내 YouTube 처리:
```python
# 수정 전
topics.extend(result.get("topics", [])[:8])   # raw 영상 제목

# 수정 후
topics.extend(result.get("keywords", [])[:8]) # 정제된 키워드
news_scores.update(result.get("scores", {}))  # 빈도 점수 연결
```

효과:
- YouTube keywords("금리") + news_score 0.8 → interest_score 0.24 → 최종 ~62점 (review 통과)
- Google Trends 병행 시("금리" trends=0.8) → interest_score 0.64 → ~78점 (auto 통과)

### 3. 점수 임계값 재조정 (E)

`scorer.py`:
```python
# 수정 전
if final_score >= 80:  grade = "auto"
elif final_score >= 60: grade = "review"
else:                   grade = "rejected"

# 수정 후
if final_score >= 70:  grade = "auto"
elif final_score >= 55: grade = "review"
else:                   grade = "rejected"
```

근거: economy 채널에서 news_score=0.8이면 최종 62.1점 → 55+ → review 통과.
Google Trends 병행 시 78.1점 → 70+ → auto 통과.

### 4. Supabase service_role 클라이언트 (D)

신규 파일 `web/lib/supabase/server-admin.ts`:
```typescript
import { createClient } from '@supabase/supabase-js'

export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY!
  return createClient(url, key)
}
```

`web/app/trends/actions.ts`에서 `createClient()` → `createAdminClient()` 교체.

`web/.env.local.example`에 `SUPABASE_SERVICE_ROLE_KEY=` 항목 추가.

### 5. 동기화 grade 보호 (G)

`sync_to_supabase.py`의 `sync_trend_topics()`:
- upsert 전 기존 DB grade 일괄 조회
- grade ∈ {approved, rejected}인 항목은 row에서 grade 키 제거 후 upsert (기존 값 유지)

### 6. UI breakdown 실제값 표시 (F)

`supabase_schema.sql`에 `breakdown JSONB` 컬럼 추가:
```sql
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS breakdown JSONB;
```

`sync_to_supabase.py`에서 `rec.get("breakdown")` 저장.

`trends/page.tsx` Topic 인터페이스에 `breakdown?: {interest, fit, revenue, urgency}` 추가,
배지를 `breakdown?.interest ?? Math.round(score * 40 / 100)` 형태로 실제값 우선 표시.

## 구현 순서

1. `scorer.py` — grade 문자열 + 임계값
2. `trend_collector.py` — YouTube keywords 전환 + news_scores 연결
3. `sync_to_supabase.py` — grade 보호 + breakdown 저장
4. `web/lib/supabase/server-admin.ts` — admin 클라이언트 신규 생성
5. `web/app/trends/actions.ts` — admin 클라이언트 사용
6. `web/.env.local.example` — 환경변수 문서화
7. `supabase_schema.sql` — breakdown 컬럼 추가
8. `web/app/trends/page.tsx` — breakdown UI 표시

## 영향 범위

모든 7채널(CH1~CH7) 공통 코드이므로 일괄 적용됨.
기존 Supabase DB의 중복 데이터는 별도 정리 SQL로 처리.
