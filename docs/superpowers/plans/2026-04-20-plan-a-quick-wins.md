# Plan A — Quick Wins 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** T4(Step08 타임아웃) + B6(예약 업로드) + O4(Slack 에러 알림) 구현으로 58 → 68점 달성

**Architecture:** 세 기능은 서로 독립적이며 각각 1~2개 파일만 수정한다. 기존 파이프라인 로직 변경 없이 래핑(T4), 설정 추가(B6), 훅 추가(O4) 방식으로 구현한다.

**Tech Stack:** Python 3.11, concurrent.futures, requests, sentry_sdk, YouTube Data API v3

---

## 파일 맵

| 기능 | 수정 파일 | 역할 |
|------|----------|------|
| T4 | `src/pipeline.py` | Step08 호출을 30분 타임아웃 래퍼로 교체 |
| B6 | `src/core/config.py` | 채널별 최적 업로드 시간 상수 추가 |
| B6 | `src/step12/uploader.py` | `_next_publish_time()` 헬퍼 + 호출부 수정 |
| O4 | `src/pipeline.py` | Sentry `before_send` 훅으로 Slack 전송 |
| O4 | `.env.example` | `SLACK_WEBHOOK_URL` 항목 추가 |
| T4 테스트 | `tests/test_pipeline.py` | 타임아웃 시나리오 테스트 추가 |
| B6 테스트 | `tests/test_step12.py` | 예약 업로드 시각 계산 테스트 추가 |
| O4 테스트 | `tests/test_pipeline.py` | Slack 전송 훅 테스트 추가 |

---

## Task 1: T4 — Step08 전체 30분 타임아웃

**Files:**
- Modify: `src/pipeline.py` (라인 33 import 블록, 라인 332~349 Step08 호출 블록)
- Test: `tests/test_pipeline.py`

- [ ] **Step 1-1: 실패 테스트 작성**

`tests/test_pipeline.py` 파일에 아래 테스트를 추가한다.

```python
import concurrent.futures
from unittest.mock import patch, MagicMock

def test_step08_timeout_raises_after_30min():
    """run_step08가 1800초 초과하면 TimeoutError가 발생해야 한다"""
    from src.pipeline import _run_step08_timed

    def slow_step08(*args, **kwargs):
        import time; time.sleep(9999)

    with patch("src.pipeline.run_step08", side_effect=slow_step08):
        with pytest.raises(concurrent.futures.TimeoutError):
            _run_step08_timed("CH1", {}, {}, {}, {}, timeout_sec=1)
```

- [ ] **Step 1-2: 테스트 실패 확인**

```bash
cd C:/Users/조찬우/Desktop/ai_stuidio_claude
pytest tests/test_pipeline.py::test_step08_timeout_raises_after_30min -v
```

기대 결과: `FAILED — ImportError: cannot import name '_run_step08_timed'`

- [ ] **Step 1-3: `src/pipeline.py` 수정 — import 추가**

파일 상단 import 블록에 아래를 추가한다 (기존 `import concurrent.futures`가 없을 경우).

```python
import concurrent.futures
```

- [ ] **Step 1-4: `src/pipeline.py` 수정 — 타임아웃 래퍼 함수 추가**

`SENTRY_DSN = os.getenv(...)` 라인 아래에 다음 상수와 함수를 추가한다.

```python
STEP08_TIMEOUT_SEC = 1800  # 30분

def _run_step08_timed(
    channel_id: str,
    topic: dict,
    style_policy: dict,
    revenue_policy: dict,
    algorithm_policy: dict,
    timeout_sec: int = STEP08_TIMEOUT_SEC,
) -> str:
    """Step08을 별도 스레드에서 실행하고 timeout_sec 초과 시 TimeoutError를 발생시킨다."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            run_step08, channel_id, topic, style_policy, revenue_policy, algorithm_policy
        )
        return future.result(timeout=timeout_sec)
```

- [ ] **Step 1-5: `src/pipeline.py` 수정 — 호출부 교체**

라인 332~333의 `run_step08(...)` 호출을 `_run_step08_timed(...)` 로 교체한다.

기존:
```python
run_id = run_step08(channel_id, topic, style_policy,
                    revenue_policy, algorithm_policy)
```

변경 후:
```python
run_id = _run_step08_timed(channel_id, topic, style_policy,
                           revenue_policy, algorithm_policy)
```

- [ ] **Step 1-6: 타임아웃 예외 처리 추가**

라인 332~349 사이의 `except Exception as e8:` 블록을 찾아 `TimeoutError` 처리를 추가한다.

```python
except concurrent.futures.TimeoutError:
    logger.error(f"[PIPELINE] Step08 {STEP08_TIMEOUT_SEC}초 타임아웃 — {channel_id} 주제 건너뜀")
    mark_step_failed(channel_id, run_id if 'run_id' in dir() else "unknown",
                     "step08", "STEP08_TIMEOUT", f"{STEP08_TIMEOUT_SEC}s exceeded")
    continue
except Exception as e8:
    # 기존 예외 처리 유지
    ...
```

- [ ] **Step 1-7: 테스트 통과 확인**

```bash
pytest tests/test_pipeline.py::test_step08_timeout_raises_after_30min -v
```

기대 결과: `PASSED`

- [ ] **Step 1-8: 전체 테스트 회귀 확인**

```bash
pytest tests/ -q --ignore=tests/test_step08_integration.py -x
```

기대 결과: 기존 실패(FFmpeg concat 6개) 외 새 실패 없음

- [ ] **Step 1-9: 커밋**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): Step08 30분 전체 타임아웃 추가 — concurrent.futures 래퍼"
```

---

## Task 2: B6 — YouTube 예약 업로드

**Files:**
- Modify: `src/core/config.py` (끝 부분에 상수 추가)
- Modify: `src/step12/uploader.py` (헬퍼 함수 + 호출부)
- Test: `tests/test_step12.py`

- [ ] **Step 2-1: 실패 테스트 작성**

`tests/test_step12.py`에 아래 테스트를 추가한다.

```python
from datetime import datetime, timezone, timedelta

def test_next_publish_time_returns_future_utc():
    """_next_publish_time은 항상 현재 시각보다 미래인 UTC 문자열을 반환해야 한다"""
    from src.step12.uploader import _next_publish_time

    result = _next_publish_time("CH1")
    # RFC 3339 형식 확인
    assert result.endswith("Z"), f"UTC 형식이 아님: {result}"
    # 미래 시각 확인
    publish_dt = datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert publish_dt > datetime.now(timezone.utc), "예약 시각이 과거임"


def test_next_publish_time_unknown_channel_defaults():
    """알 수 없는 채널은 기본값(15:00 KST)을 사용해야 한다"""
    from src.step12.uploader import _next_publish_time
    result = _next_publish_time("CH_UNKNOWN")
    assert result.endswith("Z")
```

- [ ] **Step 2-2: 테스트 실패 확인**

```bash
pytest tests/test_step12.py::test_next_publish_time_returns_future_utc -v
```

기대 결과: `FAILED — ImportError: cannot import name '_next_publish_time'`

- [ ] **Step 2-3: `src/core/config.py` 수정 — 채널별 업로드 시간 추가**

파일 끝에 다음을 추가한다.

```python
# 채널별 최적 업로드 시간 (KST 24시간 형식)
# 근거: 직장인 유튜브 이용 패턴 (점심/퇴근/저녁)
CHANNEL_OPTIMAL_UPLOAD_KST: dict[str, str] = {
    "CH1": "14:00",  # 경제 — 점심 후 직장인
    "CH2": "19:00",  # 과학 — 저녁 여가
    "CH3": "12:00",  # 부동산 — 점심 탐색
    "CH4": "21:00",  # 심리 — 취침 전
    "CH5": "20:00",  # 미스터리 — 저녁
    "CH6": "18:00",  # 역사 — 퇴근 후
    "CH7": "17:00",  # 전쟁사 — 퇴근 직후
}
```

- [ ] **Step 2-4: `src/step12/uploader.py` 수정 — import 추가**

파일 상단 import 블록에 추가한다.

```python
from datetime import datetime, timezone, timedelta
from src.core.config import CHANNEL_OPTIMAL_UPLOAD_KST
```

- [ ] **Step 2-5: `src/step12/uploader.py` 수정 — 헬퍼 함수 추가**

`upload_video()` 함수 정의 바로 위에 추가한다.

```python
def _next_publish_time(channel_id: str) -> str:
    """채널별 최적 KST 시간 기준 다음 예약 업로드 시각을 RFC 3339 UTC로 반환한다.

    당일 최적 시간이 이미 지났으면 다음 날 같은 시간으로 설정한다.
    """
    kst_time_str = CHANNEL_OPTIMAL_UPLOAD_KST.get(channel_id, "15:00")
    hour, minute = map(int, kst_time_str.split(":"))
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    target = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now_kst:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 2-6: `src/step12/uploader.py` 수정 — `upload_video` 호출부 수정**

`upload_video(channel_id, run_id)` 를 호출하는 곳을 찾아 예약 시간을 주입한다.
`upload_video` 내부의 `body` 조립 부분(라인 70~72)은 이미 `publishAt`을 지원하므로,
외부 호출 시 `scheduled_time` 인자만 전달하면 된다.

`src/step12/__init__.py` 또는 `src/pipeline.py`에서 `upload_video(...)` 호출 부분을 찾아:

```python
# 기존
result = upload_video(channel_id, run_id)

# 변경 후
from src.step12.uploader import _next_publish_time
result = upload_video(channel_id, run_id,
                      scheduled_time=_next_publish_time(channel_id))
```

- [ ] **Step 2-7: 테스트 통과 확인**

```bash
pytest tests/test_step12.py::test_next_publish_time_returns_future_utc \
       tests/test_step12.py::test_next_publish_time_unknown_channel_defaults -v
```

기대 결과: `2 passed`

- [ ] **Step 2-8: 전체 테스트 회귀 확인**

```bash
pytest tests/test_step12.py -q
```

기대 결과: 기존 통과 테스트 유지

- [ ] **Step 2-9: 커밋**

```bash
git add src/core/config.py src/step12/uploader.py tests/test_step12.py
git commit -m "feat(step12): 채널별 최적 시간대 YouTube 예약 업로드 추가"
```

---

## Task 3: O4 — Sentry Slack 웹훅 에러 알림

**Files:**
- Modify: `src/pipeline.py` (Sentry init 블록 수정)
- Modify: `.env.example` (SLACK_WEBHOOK_URL 항목 추가)
- Test: `tests/test_pipeline.py`

- [ ] **Step 3-1: 실패 테스트 작성**

`tests/test_pipeline.py`에 추가한다.

```python
def test_sentry_before_send_posts_to_slack(requests_mock):
    """_sentry_before_send는 SLACK_WEBHOOK_URL이 있을 때 POST 요청을 보내야 한다"""
    import importlib, sys
    webhook_url = "https://hooks.slack.com/services/TEST/WEBHOOK"

    with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": webhook_url}):
        # requests_mock으로 실제 HTTP 차단
        requests_mock.post(webhook_url, json={"ok": True})

        from src.pipeline import _sentry_before_send
        fake_event = {
            "exception": {"values": [{"value": "테스트 오류 메시지"}]}
        }
        result = _sentry_before_send(fake_event, {})

        assert result == fake_event          # Sentry에도 전달
        assert requests_mock.called          # Slack에도 전송
        assert "테스트 오류 메시지" in requests_mock.last_request.json()["text"]
```

> `requests_mock` 픽스처는 `pytest-requests-mock` 패키지 필요:
> ```bash
> pip install requests-mock
> ```

- [ ] **Step 3-2: 테스트 실패 확인**

```bash
pytest tests/test_pipeline.py::test_sentry_before_send_posts_to_slack -v
```

기대 결과: `FAILED — ImportError: cannot import name '_sentry_before_send'`

- [ ] **Step 3-3: `src/pipeline.py` 수정 — import 추가**

상단 import 블록에 추가한다.

```python
import requests
```

- [ ] **Step 3-4: `src/pipeline.py` 수정 — 환경변수 읽기 추가**

`SENTRY_DSN = os.getenv(...)` 라인 아래에 추가한다.

```python
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
```

- [ ] **Step 3-5: `src/pipeline.py` 수정 — `_sentry_before_send` 함수 추가**

`_run_step08_timed` 함수 아래에 추가한다.

```python
def _sentry_before_send(event: dict, hint: dict) -> dict:
    """Sentry 이벤트 발생 시 Slack으로도 즉시 알림을 보낸다.

    Sentry 전송을 막지 않도록 항상 event를 반환한다.
    """
    if SLACK_WEBHOOK_URL:
        try:
            exc_values = event.get("exception", {}).get("values", [])
            error_msg = exc_values[0].get("value", "알 수 없는 오류") if exc_values else "알 수 없는 오류"
            requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": f":red_circle: *KAS 파이프라인 에러*\n```{error_msg}```"},
                timeout=5,
            )
        except Exception:
            pass  # Slack 전송 실패가 파이프라인을 멈추면 안 된다
    return event
```

- [ ] **Step 3-6: `src/pipeline.py` 수정 — Sentry init에 훅 연결**

기존 Sentry init 블록을 찾아 `before_send`를 추가한다.

기존:
```python
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)
```

변경 후:
```python
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        before_send=_sentry_before_send,
    )
```

- [ ] **Step 3-7: `.env.example` 수정 — Slack 웹훅 URL 항목 추가**

`.env.example` 파일에서 `SENTRY_DSN` 라인 아래에 추가한다.

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

- [ ] **Step 3-8: 테스트 통과 확인**

```bash
pip install requests-mock -q
pytest tests/test_pipeline.py::test_sentry_before_send_posts_to_slack -v
```

기대 결과: `PASSED`

- [ ] **Step 3-9: 전체 테스트 회귀 확인**

```bash
pytest tests/ -q --ignore=tests/test_step08_integration.py -x
```

기대 결과: 새 실패 없음

- [ ] **Step 3-10: 커밋**

```bash
git add src/pipeline.py .env.example tests/test_pipeline.py
git commit -m "feat(pipeline): Sentry before_send 훅으로 Slack 에러 즉시 알림 추가"
```

---

## 완료 확인

모든 Task 완료 후 최종 검증:

```bash
pytest tests/ -q --ignore=tests/test_step08_integration.py
```

기대 결과: 기존 FFmpeg concat 6개 실패 외 신규 실패 없음.

점수 변화: **58점 → 68점 (B급 진입)**
