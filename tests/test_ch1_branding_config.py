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


def test_wonee_base_has_no_text_constraint():
    """_WONEE_BASE 공유 베이스에 NO text 규칙 직접 확인."""
    from config import _WONEE_BASE
    assert "NO text" in _WONEE_BASE, "_WONEE_BASE에 'NO text' 규칙 없음"


def test_ch1_prompts_all_contain_wonee_base():
    """각 포즈 프롬프트가 _WONEE_BASE 핵심 문구를 포함하는지 확인."""
    from config import CHANNELS, _WONEE_BASE
    fragment = "minimalist cute round character"
    for pose, prompt in CHANNELS["CH1"]["character_prompts"].items():
        assert fragment in prompt, f"포즈 '{pose}' 프롬프트가 _WONEE_BASE를 포함하지 않음"


def test_subdirs_has_transitions():
    from config import SUBDIRS
    assert "transitions" in SUBDIRS, "SUBDIRS에 'transitions' 없음"


def _ensure_google_genai_mocked():
    """google.genai 및 google.genai.types를 테스트용으로 모킹한다."""
    import sys, types as _types
    import google as _g
    if "google.genai" not in sys.modules:
        _mock = _types.ModuleType("google.genai")
        _mock.Client = object
        _mock_types = _types.ModuleType("google.genai.types")
        _mock.types = _mock_types
        sys.modules["google.genai"] = _mock
        sys.modules["google.genai.types"] = _mock_types
        setattr(_g, "genai", _mock)


def test_model_is_pro():
    import sys
    from pathlib import Path
    import importlib
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    _ensure_google_genai_mocked()
    # 모듈이 이미 캐시되어 있으면 reload, 아니면 새로 import
    if "nano_banana_helper" in sys.modules:
        nbh = sys.modules["nano_banana_helper"]
    else:
        nbh = importlib.import_module("nano_banana_helper")
    assert nbh.MODEL_MULTIMODAL == "gemini-3-pro-image-preview", \
        f"모델이 Pro가 아님: {nbh.MODEL_MULTIMODAL}"


def test_budget_limit_is_sufficient():
    import sys
    from pathlib import Path
    import importlib
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    _ensure_google_genai_mocked()
    if "nano_banana_helper" in sys.modules:
        nbh = sys.modules["nano_banana_helper"]
    else:
        nbh = importlib.import_module("nano_banana_helper")
    assert nbh.BUDGET_LIMIT >= 200, f"예산 부족: {nbh.BUDGET_LIMIT}"


def test_generate_character_sheet_callable():
    """generate_character_sheet 함수가 존재하고 호출 가능한지 확인."""
    import sys
    from pathlib import Path
    import importlib
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    _ensure_google_genai_mocked()
    if "nano_banana_helper" in sys.modules:
        nbh = sys.modules["nano_banana_helper"]
    else:
        nbh = importlib.import_module("nano_banana_helper")
    assert hasattr(nbh, "generate_character_sheet"), "generate_character_sheet 함수 없음"
    assert callable(nbh.generate_character_sheet)


def test_generate_wonee_character_sheet_in_character_gen():
    """character_gen에 generate_wonee_character_sheet 함수가 있는지 확인."""
    import sys, types as _t
    from pathlib import Path
    import importlib
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
    _ensure_google_genai_mocked()
    if "character_gen" not in sys.modules:
        importlib.import_module("character_gen")
    cg = sys.modules["character_gen"]
    assert hasattr(cg, "generate_wonee_character_sheet"), \
        "character_gen에 generate_wonee_character_sheet 없음"
    assert callable(cg.generate_wonee_character_sheet)


def test_ch1_characters_are_10_poses():
    """config 기반 CH1 캐릭터 목록이 10개인지 재확인."""
    from config import CHANNELS
    assert len(CHANNELS["CH1"]["characters"]) == 10
