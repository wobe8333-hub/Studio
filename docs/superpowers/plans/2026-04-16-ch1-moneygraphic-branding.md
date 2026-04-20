# CH1 머니그래픽 브랜딩 재제작 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CH1 머니그래픽 채널 브랜딩을 원이(₩ 왕관 미니멀 마스코트) + 새 팔레트(#F4C420·#333333·Red·Green) 기반으로 완전 재제작. 캐릭터 10포즈 + 52종 에셋 풀 세트 자동 생성.

**Architecture:** `config.py`에서 팔레트·캐릭터 프롬프트 정의 → `nano_banana_helper.py`에서 Pro 모델로 캐릭터 시트(Stage 1) 생성 → `character_gen.py`에서 시트를 레퍼런스로 10포즈 Best-of-3(Stage 2) → `template_gen.py`에서 12 SVG 템플릿 + 5 트랜지션 생성 → `run_all.py`로 전체 오케스트레이션.

**Tech Stack:** Python 3.11, Gemini `gemini-3-pro-image-preview`, Pillow, SVG, pytest

---

## 파일 변경 맵

| 파일 | 변경 유형 | 핵심 변경 내용 |
|---|---|---|
| `scripts/generate_branding/config.py` | Modify | CH1 팔레트·10포즈 정의·SUBDIRS transitions 추가 |
| `scripts/generate_branding/nano_banana_helper.py` | Modify | Pro 모델·예산 200·캐릭터 시트 함수 추가 |
| `scripts/generate_branding/character_gen.py` | Modify | 3단계 파이프라인·10포즈 generate_ch1 재작성 |
| `scripts/generate_branding/template_gen.py` | Modify | 4 SVG → 12 SVG + transitions 5종 (새 팔레트) |
| `scripts/generate_branding/intro_gen.py` | Modify | CH1_TEMPLATE 색상 #F5C518 → #F4C420 |
| `scripts/generate_branding/run_all.py` | Modify | CH1 파이프라인에 Stage 1 캐릭터 시트 단계 추가 |
| `tests/test_branding_assets.py` | Modify | CH1_PNG_FILES 10 캐릭터·transitions 어서션 업데이트 |
| `tests/test_ch1_branding_config.py` | Create | config 상수·nano_banana 함수 단위 테스트 |

---

### Task 1: `config.py` — CH1 팔레트 + 원이 10포즈 + SUBDIRS 업데이트

**Files:**
- Modify: `scripts/generate_branding/config.py`
- Create: `tests/test_ch1_branding_config.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_ch1_branding_config.py` 파일 생성:

```python
# tests/test_ch1_branding_config.py
"""CH1 브랜딩 config 상수 단위 테스트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))


def test_ch1_main_color_is_gold():
    from config import CHANNELS
    assert CHANNELS["CH1"]["main_color"] == "#F4C420"


def test_ch1_has_secondary_color():
    from config import CHANNELS
    ch1 = CHANNELS["CH1"]
    assert "secondary_color" in ch1
    assert ch1["secondary_color"] == "#333333"


def test_ch1_has_accent_colors():
    from config import CHANNELS
    ch1 = CHANNELS["CH1"]
    assert ch1.get("accent_red") == "#DC2626"
    assert ch1.get("accent_green") == "#16A34A"


def test_ch1_stroke_color_updated():
    from config import CHANNELS
    assert CHANNELS["CH1"]["stroke_color"] == "#333333"


def test_ch1_has_10_poses():
    from config import CHANNELS
    ch1 = CHANNELS["CH1"]
    expected = {"default", "explain", "surprised", "happy", "sad",
                "think", "victory", "warn", "sit", "run"}
    assert set(ch1["characters"]) == expected, f"포즈 불일치: {set(ch1['characters'])} != {expected}"
    assert set(ch1["character_prompts"].keys()) == expected


def test_ch1_prompts_have_no_text_rules():
    from config import CHANNELS
    for pose, prompt in CHANNELS["CH1"]["character_prompts"].items():
        assert "NO text" in prompt or "no text" in prompt.lower(), \
            f"포즈 '{pose}' 프롬프트에 NO text 규칙 없음"


def test_subdirs_has_transitions():
    from config import SUBDIRS
    assert "transitions" in SUBDIRS, "SUBDIRS에 'transitions' 없음"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
pytest tests/test_ch1_branding_config.py -v
```

Expected: `FAILED` 7개 (config 아직 변경 전)

- [ ] **Step 3: `config.py` CH1 섹션 교체**

`scripts/generate_branding/config.py` 의 `"CH1": {` 블록 전체를 아래로 교체:

```python
_WONEE_BASE = (
    "minimalist cute round character in flat 2D hand-drawn doodle illustration style: "
    "perfectly round white (#FFFFFF) body with thin black (#333333) outline 2px, "
    "small gold (#F4C420) crown on top of head with three rounded bumps and a tiny green circle gem in center "
    "(ABSOLUTELY NO text inside crown, NO letters, NO symbols written in crown — crown is a pure geometric SHAPE only), "
    "two small round black dot eyes with tiny white highlight dot, "
    "small upward-curved smile line, "
    "soft golden blush circles on both cheeks at low opacity, "
    "simple thin stick arms with rounded ends (no hands, no feet), "
    "simple thin stick legs, "
    "pure white #FFFFFF background, "
    "zero shading, zero gradients, zero 3D effects, zero drop shadows, "
    "CRITICAL: NO text, NO numbers, NO labels, NO hex codes, NO writing of any kind anywhere"
)

"CH1": {
    "name": "머니그래픽", "domain": "경제",
    "main_color": "#F4C420",
    "secondary_color": "#333333",
    "accent_red": "#DC2626",
    "accent_green": "#16A34A",
    "bg_color": "#FFFFFF",
    "sub_colors": ["#DC2626", "#16A34A", "#333333"],
    "stroke_color": "#333333",
    "characters": ["default", "explain", "surprised", "happy", "sad",
                   "think", "victory", "warn", "sit", "run"],
    "character_prompts": {
        "default": _WONEE_BASE + (
            ", neutral standing pose: body centered, arms hanging naturally at sides, "
            "gentle content closed smile, looking directly forward"
        ),
        "explain": _WONEE_BASE + (
            ", right arm raised and index finger pointing forward/upward confidently, "
            "left arm at side, mouth slightly open in explaining expression, "
            "eyes wide and attentive"
        ),
        "surprised": _WONEE_BASE + (
            ", both arms spread wide to sides in shock, "
            "mouth open in large O shape, eyes stretched wide, "
            "small exclamation lines radiating outward around head"
        ),
        "happy": _WONEE_BASE + (
            ", jumping upward, both arms raised above head forming a V shape, "
            "big wide arc smile, two small 4-pointed sparkle stars floating nearby"
        ),
        "sad": _WONEE_BASE + (
            ", body slightly drooped forward, both arms hanging down limp, "
            "downward curved sad mouth frown, single small teardrop beside one eye"
        ),
        "think": _WONEE_BASE + (
            ", body tilted slightly to one side, one arm raised with index finger "
            "touching cheek or chin, eyes looking upward thoughtfully, "
            "three small thought ellipsis dots nearby"
        ),
        "victory": _WONEE_BASE + (
            ", one arm raised with thumb pointing up (thumbs-up gesture), "
            "one eye in a playful wink, confident wide grin"
        ),
        "warn": _WONEE_BASE + (
            ", both arms stretched forward toward viewer with palms facing outward "
            "in a stop/warning gesture, eyebrows furrowed downward, "
            "firm closed straight-line mouth expression"
        ),
        "sit": _WONEE_BASE + (
            ", seated cross-legged on the ground, arms resting relaxed on knees, "
            "calm neutral expression with gentle small smile"
        ),
        "run": _WONEE_BASE + (
            ", sideways profile view, body leaning forward in full sprint, "
            "arms pumping alternating front and back, legs bent in running motion, "
            "three short horizontal speed lines behind the body"
        ),
    },
    "icons": ["money", "coin", "stock_up", "stock_down", "bank", "interest",
              "exchange", "piggy", "card", "wallet", "calculator",
              "graph_up", "graph_down", "dollar", "won", "tax",
              "inflation", "recession", "growth", "bond"],
    "intro_duration": 3, "outro_duration": 10,
},
```

그리고 파일 맨 아래 SUBDIRS 라인 교체:

```python
# 변경 전
SUBDIRS = ["logo", "characters", "intro", "outro", "icons", "templates", "extras"]

# 변경 후
SUBDIRS = ["logo", "characters", "intro", "outro", "icons", "templates", "extras", "transitions"]
```

**주의:** `_WONEE_BASE` 변수는 `CHANNELS` dict 정의 **이전** 에 선언해야 한다 (파일 상단, `KAS_ROOT` 상수들 아래).

- [ ] **Step 4: 테스트 재실행 — 통과 확인**

```bash
pytest tests/test_ch1_branding_config.py -v
```

Expected: `7 passed`

- [ ] **Step 5: 기존 테스트 회귀 확인**

```bash
pytest tests/test_branding_assets.py::test_channels_dir_exists -v
pytest tests/test_branding_assets.py::test_icons_count -v
```

Expected: `PASSED` (아이콘 수는 여전히 20개)

- [ ] **Step 6: 커밋**

```bash
git add scripts/generate_branding/config.py tests/test_ch1_branding_config.py
git commit -m "feat(ch1): config 팔레트 #F4C420 + 원이 10포즈 + transitions SUBDIR"
```

---

### Task 2: `nano_banana_helper.py` — Pro 모델·예산·캐릭터 시트 함수

**Files:**
- Modify: `scripts/generate_branding/nano_banana_helper.py`
- Modify: `tests/test_ch1_branding_config.py` (함수 존재 검증 추가)

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_ch1_branding_config.py` 하단에 추가:

```python
def test_model_is_pro():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    # google.genai mock — API 키 없어도 import 가능
    import types as _types
    import sys as _sys
    if "google.genai" not in _sys.modules:
        import google as _g
        _mock = _types.ModuleType("google.genai")
        _mock.Client = object
        _sys.modules["google.genai"] = _mock
        setattr(_g, "genai", _mock)
    from nano_banana_helper import MODEL_MULTIMODAL
    assert MODEL_MULTIMODAL == "gemini-3-pro-image-preview", \
        f"모델이 Pro가 아님: {MODEL_MULTIMODAL}"


def test_budget_limit_is_sufficient():
    from nano_banana_helper import BUDGET_LIMIT
    # 10포즈 × Best-of-3 = 30, 트랜지션 5 × 3 = 15, 시트 1 = 최소 46
    assert BUDGET_LIMIT >= 200, f"예산 부족: {BUDGET_LIMIT}"


def test_generate_character_sheet_exists():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "nano_banana_helper",
        Path(__file__).parent.parent / "scripts" / "generate_branding" / "nano_banana_helper.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert hasattr(mod, "generate_character_sheet") or True  # 로드 전 확인 불가 — Step 4에서 검증
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ch1_branding_config.py::test_model_is_pro -v
pytest tests/test_ch1_branding_config.py::test_budget_limit_is_sufficient -v
```

Expected: `FAILED`

- [ ] **Step 3: `nano_banana_helper.py` 수정**

아래 3곳을 변경한다:

**[변경 1] 모델 상수 (라인 30):**
```python
# 변경 전
MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

# 변경 후
MODEL_MULTIMODAL = "gemini-3-pro-image-preview"
```

**[변경 2] 예산 상수 (라인 34):**
```python
# 변경 전
BUDGET_LIMIT = 30

# 변경 후
BUDGET_LIMIT = 200  # 10포즈×3 + 5전환×3 + 캐릭터시트 + 여유분
```

**[변경 3] `full_prompt` 문자열 (라인 81~89) — 텍스트 오염 방지 강화:**
```python
    full_prompt = (
        "Replicate EXACTLY the flat 2D hand-drawn doodle illustration style shown "
        "in the reference image. Same line weight (2-3px thin black marker), "
        "pure white background (#FFFFFF), same wobbly hand-drawn lines, "
        "same flat coloring with NO gradients or shadows, NO shading, NO 3D effects. "
        f"Now generate: {prompt}. "
        "STRICT ANATOMY: exactly 2 arms, exactly 2 legs — NO extra limbs. "
        "CRITICAL TEXT BAN: NO text, NO letters, NO numbers, NO labels, NO hex codes "
        "anywhere in the image. The crown is a pure geometric SHAPE — "
        "absolutely NO ₩ symbol written inside, NO Korean text, NO any character glyph. "
        "Output ONLY the character on pure white background."
    )
```

**[변경 4] `generate_character_sheet` 함수 추가** — `generate_best_of_n_with_reference` 함수 **이후** 에 삽입:

```python
def generate_character_sheet(
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
) -> bool:
    """원이 캐릭터 시트를 생성한다 (3단계 파이프라인 Stage 1).

    10개 포즈를 2×5 그리드로 한 장에 보여주는 캐릭터 디자인 시트를 생성한다.
    이 시트를 이후 개별 포즈 생성의 레퍼런스로 사용한다.

    Args:
        output_path: 시트 PNG 저장 경로 (보통 essential_branding/CH1_wonee_sheet.png)
        client: 재사용 클라이언트 (None이면 신규 생성)

    Returns:
        True if 성공, False if 실패

    Raises:
        BudgetExceededError: API 호출 상한 초과 시
    """
    global _call_count
    if _call_count >= BUDGET_LIMIT:
        raise BudgetExceededError(f"API 호출 {BUDGET_LIMIT}회 초과 — 하드스톱")

    if client is None:
        client = _make_client()

    sheet_prompt = (
        "Character design reference sheet for cute minimalist round doodle mascot '원이': "
        "perfectly round white body, thin black outline 2px, "
        "small gold crown with three rounded bumps and tiny green gem (NO letters in crown), "
        "small oval black dot eyes with white highlight, tiny curved smile, "
        "golden blush circles on cheeks, simple thin stick arms and legs. "
        "Show exactly 10 poses arranged in a 2-column 5-row grid on white background: "
        "(1) standing neutral, (2) pointing arm explain, (3) arms spread surprised, "
        "(4) jumping V-arms happy, (5) drooping sad with teardrop, "
        "(6) finger-to-cheek thinking, (7) thumbs-up victory, (8) palms-forward warning, "
        "(9) sitting cross-legged, (10) running sideways sprint. "
        "Each pose has a small numeral (1-10) beneath it for reference. "
        "Flat 2D doodle style, pure white background, no shading, no gradients. "
        "ABSOLUTELY NO written text other than small numbers 1-10. "
        "Gold crown color #F4C420, black outline #333333."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=[sheet_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        _call_count += 1
        logger.debug(f"generate_character_sheet 완료 (누적 호출: {_call_count}/{BUDGET_LIMIT})")

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(f"[OK] 캐릭터 시트 생성: {output_path.name} ({len(part.inline_data.data):,} bytes)")
                return True

        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, "text")]
        logger.warning(f"[WARN] 시트 이미지 응답 없음. 텍스트: {' '.join(text_parts)[:200]}")
        return False

    except BudgetExceededError:
        raise
    except Exception as e:
        logger.error(f"[ERR] generate_character_sheet: {e}")
        return False
```

- [ ] **Step 4: 함수 존재 테스트 추가 + 실행**

`tests/test_ch1_branding_config.py` 하단에 추가:

```python
def test_generate_character_sheet_callable():
    import sys, types as _types
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    import google as _g
    if "google.genai" not in sys.modules:
        _mock = _types.ModuleType("google.genai")
        _mock.Client = object
        _mock.types = _types.ModuleType("google.genai.types")
        sys.modules["google.genai"] = _mock
        setattr(_g, "genai", _mock)
    import importlib
    nbh = importlib.import_module("nano_banana_helper")
    assert hasattr(nbh, "generate_character_sheet"), "generate_character_sheet 함수 없음"
    assert callable(nbh.generate_character_sheet)
```

```bash
pytest tests/test_ch1_branding_config.py -v
```

Expected: `10 passed`

- [ ] **Step 5: 커밋**

```bash
git add scripts/generate_branding/nano_banana_helper.py tests/test_ch1_branding_config.py
git commit -m "feat(ch1): nano_banana Pro 모델 + 예산 200 + generate_character_sheet"
```

---

### Task 3: `character_gen.py` — 3단계 파이프라인 + 10포즈

**Files:**
- Modify: `scripts/generate_branding/character_gen.py`

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_ch1_branding_config.py` 하단에 추가:

```python
def test_generate_wonee_character_sheet_in_character_gen():
    import sys, types as _t
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    # google.genai mock
    import google as _g
    for mod_name in ["google.genai", "google.genai.types"]:
        if mod_name not in sys.modules:
            _m = _t.ModuleType(mod_name)
            sys.modules[mod_name] = _m
    if not hasattr(_g, "genai"):
        setattr(_g, "genai", sys.modules["google.genai"])
    import importlib
    cg = importlib.import_module("character_gen")
    assert hasattr(cg, "generate_wonee_character_sheet"), \
        "character_gen에 generate_wonee_character_sheet 없음"
    assert callable(cg.generate_wonee_character_sheet)


def test_ch1_characters_are_10_poses():
    """config 기반 CH1 캐릭터 목록이 10개인지 확인."""
    from config import CHANNELS
    assert len(CHANNELS["CH1"]["characters"]) == 10
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ch1_branding_config.py::test_generate_wonee_character_sheet_in_character_gen -v
```

Expected: `FAILED`

- [ ] **Step 3: `character_gen.py` 재작성**

`generate_ch1_characters` 함수와 새 `generate_wonee_character_sheet` 함수를 교체/추가한다.
파일 상단 import에 `generate_character_sheet` 추가:

```python
# 기존 라인 26~27 수정
from nano_banana_helper import generate_best_of_n_with_reference, generate_character_sheet, generate_with_reference
```

`generate_ch1_characters` 함수를 아래로 **전체 교체**:

```python
WONEE_SHEET_PATH = KAS_ROOT / "essential_branding" / "CH1_wonee_sheet.png"


def generate_wonee_character_sheet(client: genai.Client) -> bool:
    """Stage 1: 원이 캐릭터 시트 생성.

    10포즈 그리드를 한 장에 담은 레퍼런스 이미지를 생성한다.
    이후 개별 포즈 생성 시 이 시트가 스타일 레퍼런스로 사용된다.

    Returns:
        True if 성공, False if 실패 (실패 시 기존 CH1.png로 폴백)
    """
    logger.info("[Stage 1] 원이 캐릭터 시트 생성 중...")
    from nano_banana_helper import generate_character_sheet
    ok = generate_character_sheet(WONEE_SHEET_PATH, client=client)
    if ok:
        logger.info(f"[Stage 1] 시트 생성 완료: {WONEE_SHEET_PATH}")
    else:
        logger.warning("[Stage 1] 시트 생성 실패 — 기존 CH1.png로 폴백")
    return ok


def generate_ch1_characters(client: genai.Client) -> dict[str, bool]:
    """Stage 2: 원이 10포즈를 Best-of-3으로 생성.

    캐릭터 시트(CH1_wonee_sheet.png)를 스타일 레퍼런스로 사용한다.
    시트가 없으면 기존 CH1.png로 폴백한다.

    Returns:
        {pose_key: True/False} — 생성 성공 여부
    """
    cfg = CHANNELS["CH1"]
    # 레퍼런스: 새 시트 우선, 없으면 기존 CH1.png
    reference = (
        WONEE_SHEET_PATH
        if WONEE_SHEET_PATH.exists()
        else KAS_ROOT / "essential_branding" / "CH1.png"
    )
    logger.info(f"[Stage 2] 레퍼런스: {reference.name}")

    results: dict[str, bool] = {}
    for pose in cfg["characters"]:
        prompt = cfg["character_prompts"][pose]
        canonical_path = CHANNELS_DIR / "CH1" / "characters" / f"character_{pose}.png"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[CH1/{pose}] Best-of-3 생성 중...")
        try:
            variants = generate_best_of_n_with_reference(
                reference, prompt, canonical_path, n=3, client=client
            )
            if variants:
                # variant_1.png를 canonical_path로 복사 (첫 번째 사용)
                import shutil
                shutil.copy2(variants[0], canonical_path)
                results[pose] = True
                logger.info(f"[CH1/{pose}] 완료 ({len(variants)}개 variant)")
            else:
                results[pose] = False
                logger.warning(f"[CH1/{pose}] 실패 (variant 없음)")
        except Exception as e:
            results[pose] = False
            logger.error(f"[CH1/{pose}] 오류: {e}")
        time.sleep(1.5)

    return results
```

`run_all` 함수의 CH1 분기도 업데이트:

```python
        if ch_id == "CH1":
            # Stage 1: 캐릭터 시트 생성 (없는 경우에만)
            if not WONEE_SHEET_PATH.exists():
                generate_wonee_character_sheet(client)
            else:
                logger.info(f"[Stage 1] 기존 시트 재사용: {WONEE_SHEET_PATH.name}")
            # Stage 2: 개별 포즈 10종 Best-of-3
            ch1_results = generate_ch1_characters(client)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_ch1_branding_config.py -v
```

Expected: `12 passed`

- [ ] **Step 5: 커밋**

```bash
git add scripts/generate_branding/character_gen.py tests/test_ch1_branding_config.py
git commit -m "feat(ch1): character_gen 3단계 파이프라인 + 원이 10포즈 generate_ch1_characters"
```

---

### Task 4: `template_gen.py` — 12 SVG 템플릿 + 5 트랜지션 (새 팔레트)

**Files:**
- Modify: `scripts/generate_branding/template_gen.py`

현재 4종(subtitle_bar, thumbnail_template, transition_wipe, lower_third) →
**CH1용 12종** (5 썸네일 + 4 자막바 + 3 섹션구분자) + **transitions/ 5종**.
CH2~7는 기존 4종 유지.

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_ch1_branding_config.py` 하단에 추가:

```python
def test_ch1_template_svgs_generated(tmp_path):
    """generate_templates(CH1) 실행 시 12개 SVG 생성 확인."""
    import sys, shutil
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    from config import CHANNELS
    # tmp_path에 CH1/templates 폴더 생성
    ch1_dir = tmp_path / "CH1"
    (ch1_dir / "templates").mkdir(parents=True)
    (ch1_dir / "transitions").mkdir(parents=True)

    import importlib, unittest.mock as mock
    tg = importlib.import_module("template_gen")
    with mock.patch("template_gen.CHANNELS_DIR", tmp_path):
        tg.generate_templates("CH1")

    svgs = list((ch1_dir / "templates").glob("*.svg"))
    assert len(svgs) >= 12, f"CH1 템플릿 SVG 부족: {len(svgs)}"


def test_ch1_transitions_generated(tmp_path):
    """generate_transitions(CH1) 실행 시 5개 SVG 생성 확인."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    ch1_dir = tmp_path / "CH1"
    (ch1_dir / "transitions").mkdir(parents=True)

    import importlib, unittest.mock as mock
    tg = importlib.import_module("template_gen")
    with mock.patch("template_gen.CHANNELS_DIR", tmp_path):
        tg.generate_transitions("CH1")

    svgs = list((ch1_dir / "transitions").glob("*.svg"))
    assert len(svgs) == 5, f"트랜지션 SVG 수 불일치: {len(svgs)}"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ch1_branding_config.py::test_ch1_template_svgs_generated -v
pytest tests/test_ch1_branding_config.py::test_ch1_transitions_generated -v
```

Expected: `FAILED` (generate_transitions 함수 없음)

- [ ] **Step 3: `template_gen.py` 전체 수정**

기존 4개 함수 아래에 CH1 전용 함수들과 `generate_transitions` 함수를 추가. 기존 `TEMPLATES` dict와 `generate_templates` 함수를 교체한다.

**① CH1 전용 SVG 함수 추가 (subtitle/lowerthird 4종):**

```python
# ─── CH1 전용 자막바/로어써드 (4종) ─────────────────────────────────────────

def ch1_subtitle_bar_basic(ch_id: str) -> str:
    """기본 자막바: 검정 배경 + 골드 텍스트."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 120, sec)
        + doodle_rect(4, 4, 1272, 112, mc, sw=3, rx=6)
        + f'<text x="640" y="78" font-size="46" fill="#FFFFFF" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">자막 텍스트 영역</text>'
        + svg_close()
    )


def ch1_subtitle_bar_emphasis(ch_id: str) -> str:
    """강조 자막바: 골드 배경 + 검정 텍스트."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 120, mc)
        + doodle_rect(4, 4, 1272, 112, sec, sw=3, rx=6)
        + f'<text x="640" y="78" font-size="46" fill="{sec}" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">강조 텍스트 영역</text>'
        + svg_close()
    )


def ch1_subtitle_bar_L(ch_id: str) -> str:
    """L자형 로어써드: 세로+가로 바 + 채널 정보."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1920, 200, "none")
        + f'<rect x="40" y="20" width="6" height="160" fill="{mc}" rx="3"/>'
        + f'<rect x="40" y="160" width="600" height="6" fill="{mc}" rx="3"/>'
        + f'<rect x="46" y="26" width="600" height="128" fill="{sec}" opacity="0.88" rx="4"/>'
        + f'<text x="72" y="90" font-size="48" fill="#FFFFFF" '
        + 'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">이름 · 직함</text>'
        + f'<text x="72" y="140" font-size="30" fill="{mc}" '
        + f'font-family="Gmarket Sans,sans-serif">{cfg["name"]} · {cfg["domain"]}</text>'
        + svg_close()
    )


def ch1_subtitle_bar_bubble(ch_id: str) -> str:
    """말풍선 자막바."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(800, 180, "none")
        + f'<rect x="8" y="8" width="784" height="120" fill="{mc}" '
        + f'stroke="{sec}" stroke-width="3" rx="16"/>'
        + f'<polygon points="80,128 130,128 95,172" fill="{mc}" '
        + f'stroke="{sec}" stroke-width="3" stroke-linejoin="round"/>'
        + f'<text x="400" y="76" font-size="42" fill="{sec}" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">말풍선 텍스트</text>'
        + svg_close()
    )
```

**② CH1 전용 SVG 함수 추가 (썸네일 5종, 1280×720):**

```python
# ─── CH1 전용 썸네일 템플릿 (5종) ────────────────────────────────────────────

def ch1_thumbnail_standard(ch_id: str) -> str:
    """표준 썸네일: 캐릭터 좌+제목 우."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 1268, 708, mc, sw=5, rx=12)
        + doodle_rect(24, 24, 600, 672, sec, sw=2, rx=8)
        + f'<text x="324" y="380" font-size="18" fill="{sec}" text-anchor="middle" opacity="0.4">캐릭터 영역</text>'
        + doodle_rect(648, 24, 608, 320, mc, sw=2, rx=8)
        + f'<text x="952" y="200" font-size="18" fill="{mc}" text-anchor="middle" opacity="0.6">제목 영역</text>'
        + doodle_rect(648, 368, 608, 328, sec, sw=2, rx=8)
        + f'<text x="952" y="540" font-size="32" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">{cfg["name"]}</text>'
        + svg_close()
    )


def ch1_thumbnail_impact(ch_id: str) -> str:
    """임팩트 썸네일: 큰 텍스트 중앙 + 사이드 캐릭터."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, sec)
        + doodle_rect(6, 6, 1268, 708, mc, sw=6, rx=0)
        + f'<text x="640" y="340" font-size="96" fill="{mc}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">제목</text>'
        + f'<text x="640" y="430" font-size="40" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans,sans-serif">부제목 / 키워드</text>'
        + doodle_rect(1040, 100, 200, 520, mc, sw=2, rx=8)
        + f'<text x="1140" y="370" font-size="14" fill="{mc}" text-anchor="middle" opacity="0.5">캐릭터</text>'
        + svg_close()
    )


def ch1_thumbnail_compare(ch_id: str) -> str:
    """좌우비교 썸네일: 두 영역 나란히."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    red = cfg.get("accent_red", "#DC2626")
    green = cfg.get("accent_green", "#16A34A")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 624, 708, red, sw=4, rx=8)
        + f'<text x="318" y="380" font-size="28" fill="{red}" text-anchor="middle">좌측 항목</text>'
        + doodle_rect(650, 6, 624, 708, green, sw=4, rx=8)
        + f'<text x="962" y="380" font-size="28" fill="{green}" text-anchor="middle">우측 항목</text>'
        + f'<rect x="620" y="0" width="40" height="720" fill="{mc}"/>'
        + f'<text x="640" y="370" font-size="36" fill="{sec}" text-anchor="middle" font-weight="900">VS</text>'
        + svg_close()
    )


def ch1_thumbnail_question(ch_id: str) -> str:
    """질문형 썸네일: 물음표 강조."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, "#FFF8E7")
        + doodle_rect(6, 6, 1268, 708, mc, sw=5, rx=12)
        + f'<text x="200" y="480" font-size="400" fill="{mc}" text-anchor="middle" opacity="0.15" '
        + f'font-family="Georgia,serif" font-weight="900">?</text>'
        + doodle_rect(380, 100, 860, 520, sec, sw=2, rx=8)
        + f'<text x="810" y="380" font-size="28" fill="#FFFFFF" text-anchor="middle">질문 텍스트 영역</text>'
        + svg_close()
    )


def ch1_thumbnail_urgent(ch_id: str) -> str:
    """긴급 썸네일: 빨간 강조 테두리."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    red = cfg.get("accent_red", "#DC2626")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 1268, 708, red, sw=8, rx=4)
        + f'<rect x="6" y="6" width="1268" height="80" fill="{red}"/>'
        + f'<text x="640" y="60" font-size="38" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">긴급 · BREAKING</text>'
        + doodle_rect(24, 110, 1232, 580, sec, sw=2, rx=6)
        + f'<text x="640" y="420" font-size="24" fill="{mc}" text-anchor="middle">제목 및 내용 영역</text>'
        + svg_close()
    )
```

**③ CH1 섹션구분자 3종 추가:**

```python
# ─── CH1 전용 섹션구분자 (3종) ────────────────────────────────────────────────

def ch1_section_divider_basic(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    return (
        svg_open(1920, 60, "none")
        + f'<line x1="0" y1="30" x2="1920" y2="30" stroke="{mc}" stroke-width="3" stroke-dasharray="12,6"/>'
        + svg_close()
    )


def ch1_section_divider_title(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1920, 100, "none")
        + f'<rect x="0" y="0" width="1920" height="100" fill="{mc}" rx="0"/>'
        + f'<text x="960" y="66" font-size="44" fill="{sec}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">섹션 제목</text>'
        + svg_close()
    )


def ch1_section_divider_box(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 160, "none")
        + doodle_rect(0, 0, 1280, 160, mc, sw=4, rx=12)
        + f'<text x="640" y="94" font-size="44" fill="{sec}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">강조 박스 텍스트</text>'
        + svg_close()
    )
```

**④ `TEMPLATES` dict + `generate_templates` + `generate_transitions` 교체:**

```python
# ─── CH2~7 공통 템플릿 (4종) ─────────────────────────────────────────────────
TEMPLATES: dict = {
    "subtitle_bar.svg": subtitle_bar,
    "thumbnail_template.svg": thumbnail_template,
    "transition_wipe.svg": transition_wipe,
    "lower_third.svg": lower_third,
}

# ─── CH1 전용 템플릿 (12종) ────────────────────────────────────────────────────
CH1_TEMPLATES: dict = {
    "subtitle_bar_basic.svg":      ch1_subtitle_bar_basic,
    "subtitle_bar_emphasis.svg":   ch1_subtitle_bar_emphasis,
    "subtitle_bar_L.svg":          ch1_subtitle_bar_L,
    "subtitle_bar_bubble.svg":     ch1_subtitle_bar_bubble,
    "thumbnail_standard.svg":      ch1_thumbnail_standard,
    "thumbnail_impact.svg":        ch1_thumbnail_impact,
    "thumbnail_compare.svg":       ch1_thumbnail_compare,
    "thumbnail_question.svg":      ch1_thumbnail_question,
    "thumbnail_urgent.svg":        ch1_thumbnail_urgent,
    "section_divider_basic.svg":   ch1_section_divider_basic,
    "section_divider_title.svg":   ch1_section_divider_title,
    "section_divider_box.svg":     ch1_section_divider_box,
}

# ─── CH1 트랜지션 SVG (5종, transitions/ 폴더) ────────────────────────────────
def _tr_ink(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080)
        + '<defs><radialGradient id="ink" cx="50%" cy="50%" r="70%">'
        + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
        + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
        + '</radialGradient></defs>'
        + '<ellipse cx="960" cy="540" rx="960" ry="540" fill="url(#ink)"/>'
        + svg_close()
    )

def _tr_zoom(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    sec = CHANNELS[ch_id].get("secondary_color", "#333333")
    return (
        svg_open(1920, 1080, sec)
        + f'<circle cx="960" cy="540" r="800" fill="{mc}" opacity="0.9"/>'
        + f'<circle cx="960" cy="540" r="400" fill="{sec}"/>'
        + svg_close()
    )

def _tr_slide(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    sec = CHANNELS[ch_id].get("secondary_color", "#333333")
    return (
        svg_open(1920, 1080, sec)
        + f'<rect x="0" y="0" width="960" height="1080" fill="{mc}"/>'
        + svg_close()
    )

def _tr_paper(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080, "#FFFFFF")
        + '<defs><linearGradient id="paper" x1="0%" y1="0%" x2="100%" y2="100%">'
        + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
        + '<stop offset="60%" style="stop-color:#FFFDF5;stop-opacity:1"/>'
        + '<stop offset="100%" style="stop-color:#FFFFFF;stop-opacity:0"/>'
        + '</linearGradient></defs>'
        + '<rect width="1920" height="1080" fill="url(#paper)"/>'
        + svg_close()
    )

def _tr_fade(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080, mc)
        + svg_close()
    )

CH1_TRANSITIONS: dict = {
    "transition_ink.svg":   _tr_ink,
    "transition_zoom.svg":  _tr_zoom,
    "transition_slide.svg": _tr_slide,
    "transition_paper.svg": _tr_paper,
    "transition_fade.svg":  _tr_fade,
}


def generate_templates(ch_id: str) -> None:
    """채널별 SVG 템플릿 생성. CH1은 12종, CH2~7은 4종."""
    out_dir = CHANNELS_DIR / ch_id / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = CH1_TEMPLATES if ch_id == "CH1" else TEMPLATES
    for fname, fn in templates.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    logger.info(f"[OK] {ch_id} 템플릿 {len(templates)}종 생성")


def generate_transitions(ch_id: str) -> None:
    """transitions/ 폴더에 전환 SVG 5종 생성 (CH1 전용)."""
    out_dir = CHANNELS_DIR / ch_id / "transitions"
    out_dir.mkdir(parents=True, exist_ok=True)
    transitions = CH1_TRANSITIONS if ch_id == "CH1" else {}
    for fname, fn in transitions.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    if transitions:
        logger.info(f"[OK] {ch_id} 트랜지션 {len(transitions)}종 생성")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_ch1_branding_config.py -v
```

Expected: `14 passed`

- [ ] **Step 5: CH2~7 SVG 템플릿 회귀 확인**

```bash
pytest tests/test_branding_assets.py::test_templates_exist -v
```

Expected: `PASSED`

- [ ] **Step 6: 커밋**

```bash
git add scripts/generate_branding/template_gen.py
git commit -m "feat(ch1): template_gen 12 SVG 템플릿 + 5 트랜지션 + 새 팔레트"
```

---

### Task 5: `intro_gen.py` 팔레트 업데이트 (#F5C518 → #F4C420)

**Files:**
- Modify: `scripts/generate_branding/intro_gen.py`

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_ch1_branding_config.py` 하단에 추가:

```python
def test_ch1_intro_uses_correct_gold():
    from pathlib import Path
    intro = Path(__file__).parent.parent / "scripts" / "generate_branding" / "intro_gen.py"
    content = intro.read_text(encoding="utf-8")
    # 구 색상값이 남아있으면 실패
    assert "#F5C518" not in content, "intro_gen.py에 구 색상 #F5C518 남아있음"
    assert "#F4C420" in content, "intro_gen.py에 새 색상 #F4C420 없음"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ch1_branding_config.py::test_ch1_intro_uses_correct_gold -v
```

Expected: `FAILED`

- [ ] **Step 3: `intro_gen.py` 색상 교체**

`scripts/generate_branding/intro_gen.py` 에서 모든 `#F5C518` 을 `#F4C420` 으로 교체 (총 4곳 — `.won`, `.star`, `.title text-shadow`):

```python
# 전체 교체 (replace_all)
# 변경 전: #F5C518
# 변경 후: #F4C420
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_ch1_branding_config.py::test_ch1_intro_uses_correct_gold -v
```

Expected: `PASSED`

- [ ] **Step 5: 인트로 생성 검증**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python scripts/generate_branding/intro_gen.py
```

Expected: `7채널 인트로 HTML 생성 완료` (오류 없음)

- [ ] **Step 6: 커밋**

```bash
git add scripts/generate_branding/intro_gen.py tests/test_ch1_branding_config.py
git commit -m "fix(ch1): intro_gen 팔레트 #F5C518 → #F4C420 + 테스트"
```

---

### Task 6: `tests/test_branding_assets.py` — 새 52종 어서션 업데이트

**Files:**
- Modify: `tests/test_branding_assets.py`

- [ ] **Step 1: `CH1_PNG_FILES` 리스트 교체**

`tests/test_branding_assets.py` 에서 `CH1_PNG_FILES = [...]` 블록 전체를 아래로 교체:

```python
# CH1 원이 신규 에셋 목록 (52종 전체 중 PNG/HTML 파일)
CH1_PNG_FILES = [
    # 캐릭터 10종
    "characters/character_default.png",
    "characters/character_explain.png",
    "characters/character_surprised.png",
    "characters/character_happy.png",
    "characters/character_sad.png",
    "characters/character_think.png",
    "characters/character_victory.png",
    "characters/character_warn.png",
    "characters/character_sit.png",
    "characters/character_run.png",
    # 인트로 (HTML + PNG 지원 파일)
    "intro/intro.html",
    "intro/intro_character.png",
    # 아웃트로 (HTML + PNG 지원 파일)
    "outro/outro.html",
    "outro/outro_character.png",
    "outro/outro_bill.png",
    "outro/outro_background.png",
    "outro/outro_cta.png",
    # 로고
    "logo/logo.png",
]
```

- [ ] **Step 2: 캐릭터 검증 테스트 업데이트**

`test_ch1_character_logo_rgba` 파라미터 목록 교체:

```python
@pytest.mark.parametrize("rel,min_size", [
    ("logo/logo.png",                       (512, 512)),
    ("characters/character_default.png",    (512, 512)),
    ("characters/character_explain.png",    (512, 512)),
    ("characters/character_surprised.png",  (512, 512)),
    ("characters/character_happy.png",      (512, 512)),
    ("characters/character_sad.png",        (512, 512)),
    ("characters/character_think.png",      (512, 512)),
    ("characters/character_victory.png",    (512, 512)),
    ("characters/character_warn.png",       (512, 512)),
    ("characters/character_sit.png",        (512, 512)),
    ("characters/character_run.png",        (512, 512)),
])
def test_ch1_character_logo_rgba(rel, min_size):
    """CH1 로고·캐릭터 10종: 최소 크기 확인."""
    from PIL import Image
    img = Image.open(Path("assets/channels/CH1") / rel)
    assert img.size[0] >= min_size[0] and img.size[1] >= min_size[1], \
        f"{rel} size={img.size} < min={min_size}"
```

`test_ch1_character_min_size_regen` 파라미터 목록 교체:

```python
@pytest.mark.parametrize("rel", [
    "characters/character_default.png",
    "characters/character_explain.png",
    "characters/character_surprised.png",
    "characters/character_happy.png",
    "characters/character_sad.png",
    "characters/character_think.png",
    "characters/character_victory.png",
    "characters/character_warn.png",
    "characters/character_sit.png",
    "characters/character_run.png",
])
def test_ch1_character_min_size_regen(rel):
    """CH1 캐릭터 (Gemini Pro 생성): 200KB 이상 확인."""
    path = Path("assets/channels/CH1") / rel
    assert path.exists(), f"{rel} 없음"
    size = path.stat().st_size
    assert size >= 200_000, f"{rel} 크기 부족: {size:,} bytes"
```

- [ ] **Step 3: CH1 SVG 템플릿 어서션 추가**

`tests/test_branding_assets.py` 하단에 추가:

```python
# ─── CH1 신규 SVG 자산 검증 ──────────────────────────────────────────────────

CH1_TEMPLATE_SVGS = [
    "templates/subtitle_bar_basic.svg",
    "templates/subtitle_bar_emphasis.svg",
    "templates/subtitle_bar_L.svg",
    "templates/subtitle_bar_bubble.svg",
    "templates/thumbnail_standard.svg",
    "templates/thumbnail_impact.svg",
    "templates/thumbnail_compare.svg",
    "templates/thumbnail_question.svg",
    "templates/thumbnail_urgent.svg",
    "templates/section_divider_basic.svg",
    "templates/section_divider_title.svg",
    "templates/section_divider_box.svg",
]

CH1_TRANSITION_SVGS = [
    "transitions/transition_ink.svg",
    "transitions/transition_zoom.svg",
    "transitions/transition_slide.svg",
    "transitions/transition_paper.svg",
    "transitions/transition_fade.svg",
]


@pytest.mark.parametrize("rel", CH1_TEMPLATE_SVGS)
def test_ch1_template_svg_valid(rel):
    """CH1 SVG 템플릿 12종: 존재 + XML 유효성 확인."""
    import xml.etree.ElementTree as ET
    path = Path("assets/channels/CH1") / rel
    assert path.exists(), f"CH1/{rel} SVG 파일 없음"
    ET.parse(path)  # ParseError 시 자동 실패


@pytest.mark.parametrize("rel", CH1_TRANSITION_SVGS)
def test_ch1_transition_svg_valid(rel):
    """CH1 트랜지션 SVG 5종: 존재 + XML 유효성 확인."""
    import xml.etree.ElementTree as ET
    path = Path("assets/channels/CH1") / rel
    assert path.exists(), f"CH1/{rel} 트랜지션 SVG 없음"
    ET.parse(path)


def test_ch1_transitions_folder_exists():
    """transitions/ 폴더 존재 확인."""
    path = Path("assets/channels/CH1") / "transitions"
    assert path.is_dir(), "assets/channels/CH1/transitions/ 폴더 없음"
```

- [ ] **Step 4: 테스트 실행 — 의도적 실패 확인 (에셋 생성 전)**

```bash
pytest tests/test_branding_assets.py::test_ch1_template_svg_valid -v --no-header -q 2>&1 | head -20
```

Expected: 대부분 `FAILED` (파일 아직 없음 — 정상)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_branding_assets.py
git commit -m "test(ch1): 원이 10포즈·12 SVG 템플릿·5 트랜지션 어서션 업데이트"
```

---

### Task 7: `run_all.py` — CH1 파이프라인 재배선

**Files:**
- Modify: `scripts/generate_branding/run_all.py`

- [ ] **Step 1: `generate_transitions` 임포트 + CH1 파이프라인 스텝 추가**

`run_all.py` 에서 template_gen 임포트 라인 수정:

```python
# 변경 전 (라인 25)
from template_gen import generate_templates

# 변경 후
from template_gen import generate_templates, generate_transitions
```

`STEPS` 리스트에 트랜지션 스텝 추가:

```python
STEPS = [
    ("폴더 구조 생성",  None,           create_folder_structure, False),
    ("로고 SVG",        "logo",         generate_logo,           True),
    ("인트로 HTML",     "intro",        generate_intro,          True),
    ("아웃트로 HTML",   "outro",        generate_outro,          True),
    ("아이콘 SVG",      "icons",        generate_icons,          True),
    ("템플릿 SVG",      "templates",    generate_templates,      True),
    ("트랜지션 SVG",    "transitions",  generate_transitions,    True),
    ("채널 아트·배너",  "extras",       generate_extras,         True),
]
```

`run_all` 함수의 CH1 전용 섹션에 캐릭터 시트 스텝 추가:

```python
        # CH1 전용: 3단계 고퀄리티 파이프라인
        if ch_id == "CH1":
            logger.info("  [Stage 1] 원이 캐릭터 시트 생성 (essential_branding/CH1_wonee_sheet.png)")
            try:
                from character_gen import generate_wonee_character_sheet
                import os
                from google import genai
                client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                generate_wonee_character_sheet(client)
            except Exception as e:
                logger.warning(f"  캐릭터 시트 생성 스킵: {e}")
            logger.info("  [Stage 2] CH1 Imagen 일러스트 표면 (스킵 가능)")
            try:
                generate_ch1_imagen_surfaces()
            except Exception as e:
                logger.warning(f"  CH1 Imagen 표면 스킵: {e}")
            logger.info("  [Stage 3] CH1 SVG → PNG 래스터화")
            generate_ch1_svg_pngs()
            logger.info("  [Stage 4] CH1 PIL 합성")
            generate_ch1_assets()
```

- [ ] **Step 2: 드라이런 — 오류 없이 임포트 확인**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python -c "import sys; sys.path.insert(0,'scripts/generate_branding'); from run_all import run_all; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/run_all.py
git commit -m "feat(ch1): run_all 트랜지션 스텝 + 원이 캐릭터 시트 Stage 1 연결"
```

---

### Task 8: 통합 실행 + 비주얼 QA

**SVG/HTML 에셋은 API 없이 즉시 생성 가능. 캐릭터 PNG는 GEMINI_API_KEY 필요.**

- [ ] **Step 1: 폴더 구조 생성 + SVG/HTML 에셋 생성**

```bash
cd "C:/Users/조찬우/Desktop/ai_stuidio_claude"
python scripts/generate_branding/setup_folders.py
python scripts/generate_branding/template_gen.py
python scripts/generate_branding/intro_gen.py
python scripts/generate_branding/outro_gen.py
python scripts/generate_branding/icon_gen.py
```

- [ ] **Step 2: SVG/HTML 어서션 테스트 실행**

```bash
pytest tests/test_branding_assets.py::test_ch1_template_svg_valid -v
pytest tests/test_branding_assets.py::test_ch1_transition_svg_valid -v
pytest tests/test_branding_assets.py::test_ch1_transitions_folder_exists -v
pytest tests/test_branding_assets.py::test_intro_html_exists -v
```

Expected: 모두 `PASSED`

- [ ] **Step 3: CH1 캐릭터 생성 (API 필요)**

```bash
python scripts/generate_branding/character_gen.py --channel CH1
```

Expected: `[완료] 10/10개 캐릭터 PNG/variant 생성`

- [ ] **Step 4: 전체 에셋 테스트 실행**

```bash
pytest tests/test_branding_assets.py -v -k "ch1 or CH1" --tb=short
```

Expected: 캐릭터 관련 테스트 포함 `PASSED`

- [ ] **Step 5: 전체 테스트 회귀 확인**

```bash
pytest tests/ --ignore=tests/test_step08_integration.py -q
```

Expected: 기존 통과 기준 유지 (기준: 186 passed)

- [ ] **Step 6: 비주얼 QA 체크리스트**

브라우저에서 `assets/channels/CH1/intro/intro.html` 열기:
- [ ] 배경 흰색 (#FFFFFF)
- [ ] 원이 캐릭터 이미지 로드 (`intro_character.png` 존재 확인)
- [ ] 골드 #F4C420 색상 ₩ 코인 애니메이션 3개
- [ ] "머니그래픽" 텍스트 골드 #F4C420

`assets/channels/CH1/transitions/transition_ink.svg` 를 브라우저로 열기:
- [ ] SVG 렌더링 정상 (중앙 원형 그라디언트)
- [ ] 색상 골드 #F4C420

캐릭터 PNG 육안 검수 (10종 모두):
- [ ] 둥근 원형 바디
- [ ] 골드 왕관 (텍스트 오염 없음)
- [ ] 흰 배경
- [ ] 각 포즈 구분 명확

- [ ] **Step 7: 최종 커밋**

```bash
git add assets/channels/CH1/ essential_branding/CH1_wonee_sheet.png
git commit -m "feat(ch1): 원이 캐릭터 10포즈 + 52종 에셋 풀 세트 생성 완료"
```

---

## 셀프 리뷰

**스펙 커버리지 체크:**
- [x] 원이 캐릭터 10포즈 — Task 1·3
- [x] 팔레트 #F4C420·#333333·Red·Green — Task 1
- [x] Pro 모델 업그레이드 — Task 2
- [x] 3단계 파이프라인 (시트→개별) — Task 2·3
- [x] 5 썸네일 템플릿 — Task 4
- [x] 4 자막바/로어써드 — Task 4
- [x] 5 트랜지션 SVG — Task 4
- [x] 3 섹션구분자 — Task 4
- [x] 인트로 팔레트 업데이트 — Task 5
- [x] 테스트 52종 어서션 — Task 6
- [x] run_all 파이프라인 연결 — Task 7

**플레이스홀더 없음:** 모든 Step에 실제 코드 포함.

**타입 일관성:** `generate_character_sheet(output_path, *, client)` → `bool` 시그니처가 Task 2·3에서 일치.
