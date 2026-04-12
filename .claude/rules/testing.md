---
paths:
  - tests/**/*.py
  - conftest.py
---

## 테스트 핵심 패턴

### 알려진 기존 실패

`tests/test_step08_integration.py` 6개 테스트는 FFmpeg concat 버그로 **항상 실패**. 코드 변경과 무관하므로 테스트 결과 검증 시 제외:
```bash
pytest tests/ --ignore=tests/test_step08_integration.py -q   # 186 passed 기준
```

**pytest-timeout 미설치**: `--timeout=60` 플래그 및 `pyproject.toml`의 `timeout = 60` 옵션 사용 금지 (`unrecognized arguments` 오류). 필요 시 `pip install pytest-timeout` 먼저 설치.

### Gemini API 의존성 격리

`src/step08/__init__.py`가 `script_generator.py` → `google.generativeai` 임포트 체인을 형성해 테스트에서 실패할 수 있다.

**`conftest.py` 3단계 방어** (모든 테스트 전에 실행):
1. `google.generativeai`, `diskcache`, `sentry_sdk` 모듈-레벨 mock 사전 등록
2. `import src.step08` 선점 — 가짜 부모 모듈 설치 방지
3. `_restore_gemini_cache_after_test` autouse fixture — `importlib.reload()` 후 `_CACHE` 싱글턴 복원

**`google` 네임스페이스 패키지 오염 주의**: 반드시 실제 `google` 패키지 먼저 확보 후 `google.generativeai`만 mock 등록.
```python
import google as _google_pkg
_genai_mock = types.ModuleType("google.generativeai")
sys.modules["google.generativeai"] = _genai_mock
setattr(_google_pkg, "generativeai", _genai_mock)
```

**`_load_and_register()` 패턴**: `test_step08_sd.py`, `test_step08_narration.py`에서 사용. `importlib.util.spec_from_file_location()`으로 `__init__.py`를 우회하여 개별 파일 직접 로드.

### 모듈 바인딩 함정

`from X import Y`는 import 시점에 바인딩된다. 타겟 모듈에서 patch해야 한다:
```python
# 잘못됨
@patch("src.step08.ffmpeg_composer.overlay_bgm")
# 올바름 — 실제 사용하는 모듈에서 patch
@patch("src.step09.bgm_overlay.overlay_bgm")
```

### utf-8-sig 인코딩

`ssot.write_json()`은 `utf-8-sig`(BOM 포함)으로 쓴다. 테스트에서 읽을 때 반드시 `encoding="utf-8-sig"` 사용.
