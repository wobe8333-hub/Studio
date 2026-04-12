---
paths:
  - src/pipeline.py
  - src/step*/**/*.py
---

### 전체 데이터 흐름

```
파이프라인 실행 → runs/ JSON 파일
                → scripts/sync_to_supabase.py → Supabase PostgreSQL
                                                      ↓
                                              web/ Next.js 대시보드
                                              (https://cwstudio.ngrok.app)
```

### 파이프라인 오케스트레이션 (`src/pipeline.py`)

`run_monthly_pipeline(month_number)` 실행 흐름:

1. **`_ensure_initialized()`** — `data/global/.initialized` 플래그로 1회만 실행. Step00~04(채널 초기화, 베이스라인, 수익구조, 알고리즘 정책, 포트폴리오) 순차 실행. 개별 실패 허용.
2. **`_run_deferred_uploads()`** — YouTube 쿼터 부족으로 이연된 업로드 재시도 (`youtube_quota.json`의 `deferred_jobs` 배열).
3. **`_run_pending_step13()`** — `data/global/step13_pending/*.json`에서 48시간 경과 항목의 KPI 수집 + 학습 피드백.
4. **채널 루프** — `get_active_channels(month_number)`로 활성 채널 결정:
   - Step05 트렌드+지식 → Step06/07 정책 → Step08 영상 생성 → Step09 BGM → Step10 제목/썸네일 → Step11 QA → Step12 업로드 → Step13 pending 등록
5. **`_run_monthly_reports()`** — Step14(수익), Step16(리스크), Step17(지속성).

**채널 론칭 단계** (`CHANNEL_LAUNCH_PHASE` in config.py):
- month_number=1 → CH1+CH2만 활성
- month_number=2 → CH1~CH4
- month_number=3+ → 전체 7채널

**에러 전략**: fail-and-continue. Step09/10/11 실패는 경고 후 진행. Step08 실패만 해당 주제를 건너뜀.

**실시간 진행 추적** — 대시보드(운영 탭) 3초 폴링을 위해 두 가지 헬퍼를 사용한다:
- `_progress_init(channel_id, run_id)` — 파이프라인 시작 시 호출. `data/global/step_progress.json`에 전체 Step 목록(idle)과 `active: true` 기록.
- `_progress_step(index, status, started_at?)` — 각 Step 전/후에 호출. 단일 Step의 `status` + 타임스탬프를 업데이트. 마지막 Step(index=7) done 시 `active: false` 설정.
- 상태 파일: `data/global/step_progress.json` — `{ active, dry_run, channel_id, run_id, steps: [{index, name, status, started_at, done_at, elapsed_ms}] }`
