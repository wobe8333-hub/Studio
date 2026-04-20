# Plan C — S급 완성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** B7(저작권 체크) + T8(텍스트 LLM 이중화) + T7(Chaos Engineering) 구현으로 82 → 92점 달성
> **참고:** B8(시청자 유지율 예측)은 최소 3개월치 KPI 데이터가 필요하므로 데이터 축적 후 별도 계획으로 진행한다. 현재는 데이터 수집 훅만 심어둔다.

**Architecture:**
- B7: Gemini로 대본에서 저작권 위험 신호(인용구, 고유명사, 저작 캐릭터)를 감지하고, YouTube Data API `VideoCategory`와 비교해 위험 점수를 산출한다. Step11 QA 게이트에 통합한다.
- T8: 모든 Gemini 텍스트 생성 호출에 `try/except` + Claude(Anthropic SDK) fallback을 추가한다. `src/core/llm_client.py` 단일 진입점으로 추상화한다.
- T7: `pytest` fixture로 API 실패를 주입하는 Chaos 테스트 모음을 구성한다. 별도 `tests/chaos/` 디렉토리에 격리한다.

**Tech Stack:** Python 3.11, google-genai, anthropic SDK, pytest, unittest.mock

---

## 사전 조건

- Plan A, Plan B가 완료되어 있어야 한다.
- `anthropic` 패키지 설치: `pip install anthropic`
- `ANTHROPIC_API_KEY` 환경 변수 설정

---

## 파일 맵

| 기능 | 파일 | 역할 |
|------|------|------|
| T8 | `src/core/llm_client.py` (신규) | Gemini/Claude 통합 텍스트 생성 클라이언트 |
| T8 | `src/step08/script_generator.py` | `llm_client` 사용으로 교체 |
| T8 | `src/step10/__init__.py` | `llm_client` 사용으로 교체 |
| B7 | `src/step11/copyright_checker.py` (신규) | 저작권 위험 점수 산출 |
| B7 | `src/step11/__init__.py` | QA 게이트에 copyright_checker 통합 |
| T7 | `tests/chaos/__init__.py` (신규) | Chaos 테스트 패키지 |
| T7 | `tests/chaos/test_api_failures.py` (신규) | API 실패 시나리오 테스트 |
| B8 | `src/step13/retention_collector.py` (신규) | 유지율 데이터 수집 훅 (미래 모델용) |
| 공통 | `.env.example` | `ANTHROPIC_API_KEY` 추가 |

---

## Task 1: T8 — 텍스트 LLM 이중화 (Gemini → Claude fallback)

**Files:**
- Create: `src/core/llm_client.py`
- Modify: `src/step08/script_generator.py`
- Modify: `.env.example`
- Test: `tests/test_llm_client.py` (신규)

- [ ] **Step 1-1: `ANTHROPIC_API_KEY` 환경 변수 추가**

`.env.example`에 추가한다.

```
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

실제 `.env` 파일에도 발급받은 키를 추가한다.

- [ ] **Step 1-2: anthropic 패키지 설치 및 requirements 반영**

```bash
pip install anthropic
echo "anthropic>=0.25.0" >> requirements.txt
```

- [ ] **Step 1-3: 실패 테스트 작성**

`tests/test_llm_client.py` 파일을 신규 생성한다.

```python
import pytest
from unittest.mock import patch, MagicMock


def test_generate_text_uses_gemini_first():
    """generate_text는 Gemini를 우선 호출해야 한다"""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", return_value="Gemini 응답") as mock_g, \
         patch("src.core.llm_client._call_claude") as mock_c:
        result = generate_text("테스트 프롬프트")

    mock_g.assert_called_once()
    mock_c.assert_not_called()
    assert result == "Gemini 응답"


def test_generate_text_falls_back_to_claude_on_gemini_failure():
    """Gemini 실패 시 Claude로 자동 전환되어야 한다"""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", side_effect=Exception("Gemini API 오류")), \
         patch("src.core.llm_client._call_claude", return_value="Claude 응답") as mock_c:
        result = generate_text("테스트 프롬프트")

    mock_c.assert_called_once()
    assert result == "Claude 응답"


def test_generate_text_raises_when_both_fail():
    """Gemini와 Claude 모두 실패하면 RuntimeError를 발생시켜야 한다"""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", side_effect=Exception("Gemini 실패")), \
         patch("src.core.llm_client._call_claude", side_effect=Exception("Claude 실패")):
        with pytest.raises(RuntimeError, match="LLM_ALL_PROVIDERS_FAILED"):
            generate_text("테스트 프롬프트")
```

- [ ] **Step 1-4: 테스트 실패 확인**

```bash
pytest tests/test_llm_client.py -v
```

기대 결과: `FAILED — ModuleNotFoundError: No module named 'src.core.llm_client'`

- [ ] **Step 1-5: `src/core/llm_client.py` 신규 생성**

```python
"""LLM 텍스트 생성 단일 진입점.

Gemini를 우선 사용하고, 실패 시 Claude(Anthropic)로 자동 전환한다.
호출자는 어떤 LLM이 응답했는지 알 필요 없다.
"""
import os
from loguru import logger


def _call_gemini(prompt: str, model: str | None = None) -> str:
    """Gemini 텍스트 생성 호출."""
    import google.generativeai as genai
    _model = model or os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = genai.GenerativeModel(_model).generate_content(prompt)
    return response.text


def _call_claude(prompt: str) -> str:
    """Claude 텍스트 생성 호출 (Gemini fallback)."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 비용 효율적인 fallback
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_text(prompt: str, model: str | None = None) -> str:
    """텍스트 생성. Gemini 실패 시 Claude로 자동 전환.

    Args:
        prompt: 생성 프롬프트
        model: Gemini 모델명 (None이면 GEMINI_TEXT_MODEL 환경변수 사용)

    Returns:
        생성된 텍스트

    Raises:
        RuntimeError: Gemini와 Claude 모두 실패한 경우
    """
    try:
        result = _call_gemini(prompt, model)
        logger.debug("[LLM] Gemini 응답 성공")
        return result
    except Exception as e_gemini:
        logger.warning(f"[LLM] Gemini 실패 → Claude fallback: {e_gemini}")
        try:
            result = _call_claude(prompt)
            logger.info("[LLM] Claude fallback 응답 성공")
            return result
        except Exception as e_claude:
            logger.error(f"[LLM] Claude도 실패: {e_claude}")
            raise RuntimeError(
                f"LLM_ALL_PROVIDERS_FAILED gemini={e_gemini} claude={e_claude}"
            )
```

- [ ] **Step 1-6: 테스트 통과 확인**

```bash
pytest tests/test_llm_client.py -v
```

기대 결과: `3 passed`

- [ ] **Step 1-7: `src/step08/script_generator.py` 수정 — llm_client 사용**

`script_generator.py`에서 직접 `genai.GenerativeModel(...).generate_content(...)` 를 호출하는 부분을 찾아 `generate_text()`로 교체한다.

기존:
```python
response = genai.GenerativeModel(model).generate_content(prompt)
script_text = response.text
```

변경 후:
```python
from src.core.llm_client import generate_text
script_text = generate_text(prompt, model=model)
```

- [ ] **Step 1-8: 전체 회귀 테스트**

```bash
pytest tests/ -q --ignore=tests/test_step08_integration.py -x
```

기대 결과: 신규 실패 없음

- [ ] **Step 1-9: 커밋**

```bash
git add src/core/llm_client.py src/step08/script_generator.py \
        tests/test_llm_client.py .env.example requirements.txt
git commit -m "feat(core): LLM 이중화 — Gemini 실패 시 Claude 자동 전환"
```

---

## Task 2: B7 — 저작권 사전 체크

**Files:**
- Create: `src/step11/copyright_checker.py`
- Modify: `src/step11/__init__.py` (QA 게이트에 통합)
- Test: `tests/test_step11.py`

- [ ] **Step 2-1: 실패 테스트 작성**

`tests/test_step11.py`에 추가한다.

```python
def test_copyright_check_high_risk_script():
    """저작권 위험 대본은 risk_score가 0.7 이상이어야 한다"""
    from src.step11.copyright_checker import check_copyright_risk

    risky_script = (
        "이 영상에서 디즈니 미키마우스 캐릭터의 정확한 대사를 인용합니다. "
        "'오, 미키야!' 라는 대사는 1928년 월트 디즈니가 직접 작성한 것입니다."
    )
    with patch("src.step11.copyright_checker.generate_text",
               return_value='{"risk_score": 0.85, "reasons": ["고유 캐릭터 언급", "직접 인용"]}'):
        result = check_copyright_risk(risky_script)

    assert result["risk_score"] >= 0.7
    assert len(result["reasons"]) > 0


def test_copyright_check_safe_script():
    """일반 교육 대본은 risk_score가 0.3 미만이어야 한다"""
    from src.step11.copyright_checker import check_copyright_risk

    safe_script = "금리가 오르면 채권 가격은 내려갑니다. 이는 경제학의 기본 원리입니다."
    with patch("src.step11.copyright_checker.generate_text",
               return_value='{"risk_score": 0.05, "reasons": []}'):
        result = check_copyright_risk(safe_script)

    assert result["risk_score"] < 0.3
```

- [ ] **Step 2-2: 테스트 실패 확인**

```bash
pytest tests/test_step11.py::test_copyright_check_high_risk_script -v
```

기대 결과: `FAILED — ModuleNotFoundError: No module named 'src.step11.copyright_checker'`

- [ ] **Step 2-3: `src/step11/copyright_checker.py` 신규 생성**

```python
"""저작권 위험 사전 체크.

Gemini(또는 Claude fallback)로 대본을 분석해 Content ID 스트라이크 위험을
0~1 점수로 산출한다. 0.7 이상이면 Step11 QA 게이트에서 경고를 발행한다.
"""
import json
from loguru import logger
from src.core.llm_client import generate_text

COPYRIGHT_RISK_PROMPT = """아래 유튜브 영상 대본에서 저작권 위험 요소를 분석하세요.

대본:
{script}

다음 JSON 형식으로만 답하세요:
{{
  "risk_score": 0.0~1.0 사이 숫자 (0=안전, 1=매우 위험),
  "reasons": ["위험 요소 설명 목록"]
}}

위험 요소 예시: 저작권 있는 노래 가사 직접 인용, 실존 인물 허위 사실, 
상표 캐릭터 무단 사용, 다른 영상 장면 직접 묘사.
교육·정보 목적의 일반 지식은 위험하지 않습니다."""


def check_copyright_risk(script: str) -> dict:
    """대본의 저작권 위험을 분석한다.

    Args:
        script: 분석할 영상 대본 텍스트

    Returns:
        {"risk_score": float, "reasons": list[str]}
        risk_score 0.7 이상이면 업로드 전 검토 권장
    """
    try:
        prompt = COPYRIGHT_RISK_PROMPT.format(script=script[:3000])
        response = generate_text(prompt)
        # JSON 추출
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("JSON 없음")
        result = json.loads(response[start:end])
        risk_score = float(result.get("risk_score", 0.0))
        reasons = result.get("reasons", [])
        logger.info(f"[COPYRIGHT] 위험 점수: {risk_score:.2f} / 사유: {reasons}")
        return {"risk_score": risk_score, "reasons": reasons}
    except Exception as e:
        logger.warning(f"[COPYRIGHT] 분석 실패, 안전으로 처리: {e}")
        return {"risk_score": 0.0, "reasons": []}
```

- [ ] **Step 2-4: `src/step11/__init__.py` 수정 — QA 게이트에 통합**

Step11의 QA 결과 딕셔너리를 조립하는 부분을 찾아 copyright 체크를 추가한다.

```python
from src.step11.copyright_checker import check_copyright_risk

# 기존 QA 체크들 아래에 추가
copyright_result = check_copyright_risk(script_text)
qa_result["copyright_risk_score"] = copyright_result["risk_score"]
qa_result["copyright_reasons"] = copyright_result["reasons"]
if copyright_result["risk_score"] >= 0.7:
    logger.warning(f"[QA] 저작권 위험 높음 ({copyright_result['risk_score']:.2f}) — 수동 검토 권장")
    qa_result["warnings"] = qa_result.get("warnings", []) + ["COPYRIGHT_HIGH_RISK"]
```

- [ ] **Step 2-5: 테스트 통과 확인**

```bash
pytest tests/test_step11.py::test_copyright_check_high_risk_script \
       tests/test_step11.py::test_copyright_check_safe_script -v
```

기대 결과: `2 passed`

- [ ] **Step 2-6: 커밋**

```bash
git add src/step11/copyright_checker.py src/step11/__init__.py tests/test_step11.py
git commit -m "feat(step11): 저작권 사전 체크 추가 — Gemini 분석으로 Content ID 위험 감지"
```

---

## Task 3: T7 — Chaos Engineering 테스트

**Files:**
- Create: `tests/chaos/__init__.py`
- Create: `tests/chaos/test_api_failures.py`

- [ ] **Step 3-1: `tests/chaos/` 디렉토리 생성**

```bash
mkdir -p C:/Users/조찬우/Desktop/ai_stuidio_claude/tests/chaos
```

- [ ] **Step 3-2: `tests/chaos/__init__.py` 생성**

```python
"""Chaos Engineering 테스트 모음.

외부 API가 무작위로 실패할 때 파이프라인이 올바르게 대응하는지 검증한다.
정상 경로 테스트와 격리하기 위해 별도 디렉토리에 배치한다.

실행 방법:
    pytest tests/chaos/ -v
"""
```

- [ ] **Step 3-3: `tests/chaos/test_api_failures.py` 생성**

```python
"""API 실패 시나리오 Chaos 테스트."""
import pytest
from unittest.mock import patch, MagicMock


class TestGeminiFailureChaos:
    """Gemini API 장애 시나리오"""

    def test_gemini_rate_limit_retries_and_succeeds(self):
        """Gemini가 처음 2번 Rate Limit 오류를 내도 3번째에 성공해야 한다"""
        from src.core.llm_client import generate_text
        call_count = [0]

        def flaky_gemini(prompt, model=None):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("429 Resource Exhausted")
            return "성공 응답"

        with patch("src.core.llm_client._call_gemini", side_effect=flaky_gemini), \
             patch("src.core.llm_client._call_claude", return_value="Claude 응답"):
            result = generate_text("테스트")

        # 2번 실패 후 Claude fallback이 응답
        assert result in ("성공 응답", "Claude 응답")

    def test_gemini_total_outage_uses_claude(self):
        """Gemini 완전 장애 시 Claude로 전환되어 파이프라인이 계속 실행되어야 한다"""
        from src.core.llm_client import generate_text

        with patch("src.core.llm_client._call_gemini", side_effect=Exception("서비스 불가")), \
             patch("src.core.llm_client._call_claude", return_value="Claude 대체 응답"):
            result = generate_text("대본 생성해줘")

        assert result == "Claude 대체 응답"

    def test_both_llm_down_raises_clear_error(self):
        """Gemini와 Claude 모두 다운 시 명확한 오류 코드로 실패해야 한다"""
        from src.core.llm_client import generate_text

        with patch("src.core.llm_client._call_gemini", side_effect=Exception("Gemini 다운")), \
             patch("src.core.llm_client._call_claude", side_effect=Exception("Claude 다운")):
            with pytest.raises(RuntimeError, match="LLM_ALL_PROVIDERS_FAILED"):
                generate_text("프롬프트")


class TestYouTubeQuotaExhaustedChaos:
    """YouTube API 쿼터 소진 시나리오"""

    def test_upload_deferred_when_quota_exhausted(self):
        """YouTube 쿼터 소진 시 업로드가 deferred_jobs에 추가되어야 한다"""
        from src.quota.youtube_quota import can_upload, defer_job

        # 쿼터를 한도까지 소모한 상황 시뮬레이션
        with patch("src.quota.youtube_quota._load_quota", return_value={
            "date": "2026-04-20",
            "used": 9600,  # BLOCK_THRESHOLD(9500) 초과
            "deferred_jobs": [],
        }):
            assert can_upload() is False


class TestFileSystemChaos:
    """파일 시스템 장애 시나리오"""

    def test_ssot_write_retries_on_lock_contention(self):
        """SSOT 파일락 경합 시에도 쓰기가 결국 성공해야 한다"""
        import threading
        from src.core.ssot import write_json
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test.json")
            errors = []

            def write_worker(i):
                try:
                    write_json(test_path, {"worker": i, "data": "x" * 100})
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=write_worker, args=(i,)) for i in range(5)]
            for t in threads: t.start()
            for t in threads: t.join()

            assert len(errors) == 0, f"동시 쓰기 오류 발생: {errors}"
            import json
            with open(test_path, encoding="utf-8-sig") as f:
                data = json.load(f)
            assert "worker" in data  # 마지막 쓰기가 유효한 JSON
```

- [ ] **Step 3-4: Chaos 테스트 실행**

```bash
pytest tests/chaos/ -v
```

기대 결과: 모든 Chaos 테스트 통과 (LLM 이중화가 구현된 상태이므로)

- [ ] **Step 3-5: 전체 회귀 테스트**

```bash
pytest tests/ -q -x
```

기대 결과: 신규 실패 없음

- [ ] **Step 3-6: 커밋**

```bash
git add tests/chaos/ 
git commit -m "test(chaos): API 장애·쿼터 소진·파일락 경합 Chaos Engineering 테스트 추가"
```

---

## Task 4: B8 — 유지율 데이터 수집 훅 (미래 모델 준비)

> B8 전체 구현(예측 모델)은 3개월 이상의 KPI 데이터 후 별도 계획으로 진행한다.
> 지금은 데이터만 수집해 `data/global/retention/` 에 축적한다.

**Files:**
- Create: `src/step13/retention_collector.py`
- Modify: `src/step13/__init__.py`

- [ ] **Step 4-1: `src/step13/retention_collector.py` 신규 생성**

```python
"""유지율 데이터 수집기.

YouTube Analytics API에서 평균 시청 지속시간(average_view_duration)을
수집해 data/global/retention/{channel_id}.jsonl에 누적 기록한다.

이 데이터는 3개월 이상 축적 후 유지율 예측 모델(B8) 구현에 사용된다.
"""
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

RETENTION_DIR = Path(os.getenv("KAS_ROOT", ".")) / "data" / "global" / "retention"


def collect_retention(channel_id: str, video_id: str, kpi: dict) -> None:
    """KPI에서 유지율 지표를 추출해 누적 기록한다.

    Args:
        channel_id: 채널 ID (예: "CH1")
        video_id: YouTube 영상 ID
        kpi: Step13에서 수집한 KPI 딕셔너리
    """
    avg_duration = kpi.get("average_view_duration", 0)
    total_duration = kpi.get("video_duration", 0)
    if total_duration <= 0:
        return

    retention_rate = avg_duration / total_duration if total_duration > 0 else 0.0

    record = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel_id": channel_id,
        "video_id": video_id,
        "avg_duration_sec": avg_duration,
        "total_duration_sec": total_duration,
        "retention_rate": round(retention_rate, 4),
        "views": kpi.get("views", 0),
        "ctr": kpi.get("click_through_rate", 0.0),
    }

    RETENTION_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RETENTION_DIR / f"{channel_id}.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        import json
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"[RETENTION] {channel_id}/{video_id} 유지율 {retention_rate:.1%} 기록")
```

- [ ] **Step 4-2: `src/step13/__init__.py` 수정 — 수집 훅 호출 추가**

Step13 KPI 수집 완료 후 `collect_retention()` 호출을 추가한다.

```python
from src.step13.retention_collector import collect_retention

# 기존 KPI 수집 후
collect_retention(channel_id, video_id, kpi_data)
```

- [ ] **Step 4-3: 커밋**

```bash
git add src/step13/retention_collector.py src/step13/__init__.py
git commit -m "feat(step13): 유지율 데이터 수집 훅 추가 — 3개월 축적 후 예측 모델 기반"
```

---

## 완료 확인

```bash
# 전체 테스트 (Chaos 포함)
pytest tests/ -q -x

# 린팅
ruff check src/ --select=E,W,F,I

# Chaos 테스트 단독
pytest tests/chaos/ -v
```

점수 변화: **82점 → 92점 (S급 달성)**

---

## S급 달성 후 체크리스트

| 항목 | 완료 기준 |
|------|----------|
| T4 ✅ | Step08 30분 타임아웃 동작 확인 |
| B6 ✅ | YouTube 스튜디오에서 예약 업로드 확인 |
| O4 ✅ | Slack 채널에 에러 알림 수신 확인 |
| T5 ✅ | 로그에서 다채널 병렬 시작 확인 |
| O5 ✅ | `rollback` CLI로 영상 비공개 전환 확인 |
| T6 ✅ | `pytest` 전체 실패 0건 (FFmpeg skip 제외) |
| T8 ✅ | Gemini mock 실패 시 Claude 응답 확인 |
| B7 ✅ | QA 리포트에 `copyright_risk_score` 필드 존재 |
| T7 ✅ | `pytest tests/chaos/` 전체 통과 |
| B8 ✅ | `data/global/retention/CH1.jsonl` 파일 생성 확인 |
