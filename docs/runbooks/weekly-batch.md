# 런북: 주간 배치 (G2 파이프라인 v2.1)

**버전**: v2.1 | **최종 수정**: 2026-04-22  
**담당 에이전트**: sre-engineer (모니터링) · backend-engineer (수정)  
**SLA**: 42시간 (일요일 00:00 ~ 월요일 18:00)

---

## 1. 개요

주간 배치는 7채널 × 2 롱폼 = 14편을 병렬 제작한다. `weekly_batch.py`가 오케스트레이터 역할을 하며, 4 병렬 트랙(Narrative/Audio/Visual/Assembly)을 asyncio로 관리한다.

```
일요일 00:00 (cron / 작업 스케줄러)
   └─ python -m src.pipeline_v2.weekly_batch
         ├─ 주간 계획 파일 로드 (data/global/monthly_plan/{YYYY-MM}/week_{W}.json)
         ├─ EpisodeJob 14개 생성
         ├─ asyncio 세마포어 4 (최대 동시 4편)
         └─ 각 에피소드: Track A → B+C (병렬) → D → QC → 업로드
```

---

## 2. 사전 조건 체크

배치 실행 전 아래 항목을 확인한다:

```bash
# 환경 점검
python scripts/preflight_check.py

# 필수 환경변수 확인
python -c "
from src.core.config import settings
print('GEMINI_API_KEY:', bool(settings.GEMINI_API_KEY))
print('ELEVENLABS_API_KEY:', bool(settings.ELEVENLABS_API_KEY))
print('YOUTUBE_DATA_API_KEY:', bool(settings.YOUTUBE_API_KEY))
"

# 주간 계획 파일 존재 여부
python -c "
from datetime import date
d = date.today()
import json, pathlib
week = d.isocalendar()[1]
p = pathlib.Path(f'data/global/monthly_plan/{d.strftime(\"%Y-%m\")}/week_{week}.json')
print('계획 파일:', 'OK' if p.exists() else '없음 — 생성 필요')
"
```

### 주간 계획 파일 없는 경우 생성

`data/global/monthly_plan/{YYYY-MM}/week_{W}.json` 형식:

```json
{
  "week": 17,
  "episodes": [
    {"channel_id": "CH1", "topic": "금리와 부동산의 상관관계", "series_id": "금리_시리즈", "episode_index": 3},
    {"channel_id": "CH1", "topic": "연준 금리 인하 시나리오 분석", "series_id": "금리_시리즈", "episode_index": 4},
    {"channel_id": "CH2", "topic": "블랙홀 정보 역설", "series_id": "우주_시리즈", "episode_index": 1},
    {"channel_id": "CH2", "topic": "양자 얽힘의 실제 응용", "series_id": "양자역학_시리즈", "episode_index": 2}
  ]
}
```

---

## 3. 실행

```bash
# 전체 주간 배치 실행
python -m src.pipeline_v2.weekly_batch

# 특정 채널만 실행 (테스트 목적)
python -c "
import asyncio
from src.pipeline_v2.weekly_batch import run_weekly_batch
asyncio.run(run_weekly_batch(channel_filter='CH1'))
"

# 드라이런 (API 호출 없이 구조만 확인)
python -c "
import asyncio
from src.pipeline_v2.weekly_batch import run_weekly_batch
asyncio.run(run_weekly_batch(dry_run=True))
"
```

---

## 4. 모니터링

### 진행 상황 확인

```bash
# 배치 히스토리 확인
cat data/global/batch_history.json | python -m json.tool | head -50

# HITL 신호 확인 (알림 대기 항목)
cat data/global/notifications/hitl_signals.json

# 채널별 에피소드 메타 확인
ls data/episodes/CH1/$(date +%Y-%m)/
```

### 웹 대시보드

- **HITL Gate 1** (월 1회): `http://localhost:7002/hitl/series-approval`
- **HITL Gate 2** (편당 10초): `http://localhost:7002/hitl/thumbnail-veto`
- **HITL Gate 3** (업로드 전): `http://localhost:7002/hitl/final-preview`
- **외부 접근**: `https://cwstudio.ngrok.app/hitl/*` (ngrok 실행 중일 때)

---

## 5. 장애 대응 플레이북

### 5-1. Gemini API 쿼터 초과

**증상**: `ResourceExhausted: 429` 로그, Track C/D 스텝 실패

```bash
# 쿼터 현황 확인
cat data/global/quota/gemini_quota_daily.json

# Claude 폴백으로 전환 (LLM 이중화)
# src/core/llm_client.py의 FALLBACK_TO_CLAUDE=True 확인
python -c "from src.core import llm_client; print(llm_client.FALLBACK_TO_CLAUDE)"
```

**조치**: 다음날 쿼터 리셋(UTC 00:00)까지 대기 또는 `GEMINI_REQUESTS_PER_MINUTE` 환경변수를 줄여 재시도

### 5-2. QC Layer 1 반복 실패 (캐릭터 일관성)

**증상**: `hitl_signals.json`에 `type: qc_layer1_fail` 항목 3개 이상

```bash
# 실패한 씬 이미지 경인
cat data/global/notifications/hitl_signals.json | python -m json.tool

# 캐시 매니페스트에서 실패한 포즈 확인
cat assets/characters/cache_manifest.json | python -m json.tool
```

**조치**: 
1. 실패한 에피소드의 `scene_images` 디렉토리 비우기
2. `nano_banana.generate_poses_for_character(overwrite=True)` 호출
3. 에피소드 Track C부터 재실행

### 5-3. FFmpeg 오디오 싱크 오차 (Layer 3 실패)

**증상**: `sync_score < 0.80` 로그

```bash
# SRT 자막 파일 타임코드 확인
cat runs/CH1/{run_id}/step08/subtitles.srt | head -20

# Faster-Whisper 재전사
python -c "
from src.pipeline_v2.qc.layer3_sync import check_sync
print(check_sync('runs/CH1/{run_id}/step08/narration.wav', 'runs/CH1/{run_id}/step08/subtitles.srt'))
"
```

**조치**: Track D Assembly에서 `--fix_sync` 플래그 활성화 후 재합성

### 5-4. YouTube 업로드 실패

**증상**: `upload_result.json`에 `status: failed`

```bash
# OAuth 토큰 만료 확인
cat credentials/CH1_token.json | python -c "import json,sys,datetime; d=json.load(sys.stdin); print('만료:', d.get('expiry'))"

# 토큰 재발급
python scripts/generate_oauth_token.py --channel CH1
```

### 5-5. 42시간 SLA 초과 위험

**증상**: `batch_history.json`에 `elapsed_h > 38` 경고

```bash
# 현재 진행 중인 에피소드 수 확인
cat data/global/batch_history.json | python -m json.tool | grep -A2 "in_progress"
```

**조치**: `MAX_CONCURRENT_EPISODES` 환경변수를 4→6으로 임시 증가 (API 비용 상승 주의)

---

## 6. 정상 완료 확인

배치 종료 후 아래 항목이 모두 충족되어야 한다:

```bash
# 체크리스트 자동 검증
python -c "
from pathlib import Path
import json, datetime

week = datetime.date.today().isocalendar()[1]
log_path = Path(f'data/global/batch_history.json')
history = json.loads(log_path.read_text(encoding='utf-8'))
latest = history[-1] if isinstance(history, list) else history

print('완료 에피소드 수:', latest.get('completed', 0))
print('실패 에피소드 수:', latest.get('failed', 0))
print('소요 시간(h):', round(latest.get('elapsed_sec', 0) / 3600, 1))
print('SLA 충족:', latest.get('elapsed_sec', 0) < 42 * 3600)
"
```

**정상 기준**:
- [ ] 완료 에피소드 ≥ 12 (실패 허용 2편 이하)
- [ ] 소요 시간 ≤ 42h
- [ ] HITL Gate 2 미결 항목 없음 (`thumbnail_veto_queue.json` 비어있거나 모두 결정됨)
- [ ] 업로드 예약 완료 (`upload_queue.json` 항목 14개)

---

## 7. 쇼츠 자동 파생 확인

롱폼 완료 후 자동으로 쇼츠가 파생된다:

```bash
# 채널별 쇼츠 파생 결과 확인
python -c "
from pathlib import Path
import json

for ch in ['CH1','CH2','CH3','CH4','CH5','CH6','CH7']:
    runs = sorted(Path(f'runs/{ch}').glob('*/shorts_clips.json'))
    if runs:
        data = json.loads(runs[-1].read_text(encoding='utf-8'))
        print(f'{ch}: {len(data.get(\"clips\",[])} 개 쇼츠 파생')
"
```

---

## 8. 피드백 루프 확인 (48h 후)

롱폼 업로드 후 48시간이 지나면 KPI가 자동 수집된다:

```bash
# KPI 수집 상태 확인
cat data/global/learning_feedback.json | python -m json.tool | head -30
```

수집된 KPI는 다음 주 `L3 월간 기획`에 자동 반영되어 시리즈 방향을 조정한다.

---

## 9. 관련 파일

| 파일 | 역할 |
|---|---|
| `src/pipeline_v2/weekly_batch.py` | 배치 오케스트레이터 |
| `src/pipeline_v2/episode_schema.py` | EpisodeMeta Pydantic 스키마 |
| `data/global/batch_history.json` | 배치 실행 이력 |
| `data/global/notifications/hitl_signals.json` | HITL 알림 큐 |
| `data/episodes/CH{1-7}/{YYYY-MM}/` | 에피소드 메타데이터 SSOT |
| `runs/CH{1-7}/{run_id}/` | 실행 아티팩트 |
| `assets/characters/cache_manifest.json` | 포즈 캐시 인덱스 |
