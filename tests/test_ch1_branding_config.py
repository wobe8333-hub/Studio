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
