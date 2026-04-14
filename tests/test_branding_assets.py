# tests/test_branding_assets.py
"""브랜딩 에셋 파일 존재·유효성 검증"""
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS

# CH1: 레퍼런스 crop PNG 에셋 목록
CH1_PNG_FILES = [
    "logo/logo.png",
    "characters/character_explain.png",
    "characters/character_rich.png",
    "characters/character_money.png",
    "characters/character_lucky.png",
    "intro/intro_frame.png",
    "intro/intro_text.png",
    "intro/intro_character.png",
    "intro/intro_sparkle.png",
    "intro/intro.html",
    "outro/outro_background.png",
    "outro/outro_bill.png",
    "outro/outro_character.png",
    "outro/outro_cta.png",
    "outro/outro.html",
    "templates/thumbnail_sample_1.png",
    "templates/thumbnail_sample_2.png",
    "templates/thumbnail_sample_3.png",
    "templates/subtitle_bar_key.png",
    "templates/subtitle_bar_dialog.png",
    "templates/subtitle_bar_info.png",
    "templates/transition_paper.png",
    "templates/transition_ink.png",
    "templates/transition_zoom.png",
]

def test_channels_dir_exists():
    assert CHANNELS_DIR.exists(), f"assets/channels/ 폴더 없음: {CHANNELS_DIR}"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
@pytest.mark.parametrize("subdir", SUBDIRS)
def test_subdir_exists(ch_id, subdir):
    path = CHANNELS_DIR / ch_id / subdir
    assert path.is_dir(), f"{ch_id}/{subdir} 폴더 없음"

@pytest.mark.parametrize("ch_id", ["CH2","CH3","CH4","CH5","CH6","CH7"])
def test_logo_svg_exists_and_valid(ch_id):
    """CH2~7: SVG 로고 존재·유효성 확인 (CH1은 logo.png 사용)."""
    logo_path = CHANNELS_DIR / ch_id / "logo" / "logo.svg"
    assert logo_path.exists(), f"{ch_id}/logo/logo.svg 없음"
    content = logo_path.read_text(encoding="utf-8")
    assert "<svg" in content, f"{ch_id} 로고가 유효한 SVG가 아님"
    ET.fromstring(content)

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_intro_html_exists(ch_id):
    intro = CHANNELS_DIR / ch_id / "intro" / "intro.html"
    assert intro.exists(), f"{ch_id}/intro/intro.html 없음"
    content = intro.read_text(encoding="utf-8")
    assert "<!DOCTYPE html" in content or "<html" in content, f"{ch_id}/intro/intro.html이 유효한 HTML이 아님"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_outro_html_exists(ch_id):
    outro = CHANNELS_DIR / ch_id / "outro" / "outro.html"
    assert outro.exists(), f"{ch_id}/outro/outro.html 없음"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_icons_count(ch_id):
    icons_dir = CHANNELS_DIR / ch_id / "icons"
    svgs = list(icons_dir.glob("*.svg"))
    expected = len(CHANNELS[ch_id]["icons"])
    assert len(svgs) == expected, f"{ch_id} 아이콘 수 불일치: {len(svgs)} != {expected}"

@pytest.mark.parametrize("ch_id", ["CH2","CH3","CH4","CH5","CH6","CH7"])
def test_templates_exist(ch_id):
    """CH2~7: SVG 템플릿 존재 확인 (CH1은 PNG 템플릿 사용)."""
    tmpl_dir = CHANNELS_DIR / ch_id / "templates"
    required = ["subtitle_bar.svg","thumbnail_template.svg",
                "transition_wipe.svg","lower_third.svg"]
    for f in required:
        assert (tmpl_dir / f).exists(), f"{ch_id}/templates/{f} 없음"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_extras_exist(ch_id):
    extras_dir = CHANNELS_DIR / ch_id / "extras"
    for f in ["channel_art.svg", "profile_banner.svg"]:
        assert (extras_dir / f).exists(), f"{ch_id}/extras/{f} 없음"


# ── CH1 PNG 에셋 전용 검증 ───────────────────────────────────────────────────

@pytest.mark.parametrize("rel", CH1_PNG_FILES)
def test_ch1_asset_exists(rel):
    """CH1 레퍼런스 crop PNG 에셋 + HTML 존재·최소 크기 확인."""
    from PIL import Image
    p = Path("assets/channels/CH1") / rel
    assert p.exists(), f"missing: {p}"
    if p.suffix == ".png":
        img = Image.open(p)
        assert img.size[0] >= 60 and img.size[1] >= 60, f"{rel} too small: {img.size}"


@pytest.mark.parametrize("rel,expected_size", [
    ("logo/logo.png",                  (1024, 1024)),
    ("characters/character_explain.png",(1024, 1024)),
    ("characters/character_rich.png",  (1024, 1024)),
    ("characters/character_money.png", (1024, 1024)),
    ("characters/character_lucky.png", (1024, 1024)),
])
def test_ch1_character_logo_rgba(rel, expected_size):
    """CH1 로고·캐릭터: RGBA 1024×1024, 배경 투명 확인."""
    from PIL import Image
    img = Image.open(Path("assets/channels/CH1") / rel)
    assert img.mode == "RGBA", f"{rel} mode={img.mode}"
    assert img.size == expected_size, f"{rel} size={img.size}"


@pytest.mark.parametrize("rel", [
    "templates/thumbnail_sample_1.png",
    "templates/thumbnail_sample_2.png",
    "templates/thumbnail_sample_3.png",
])
def test_ch1_thumbnail_resolution(rel):
    """CH1 썸네일: 1920×1080 확인."""
    from PIL import Image
    img = Image.open(Path("assets/channels/CH1") / rel)
    assert img.size == (1920, 1080), f"{rel} size={img.size}"


def test_ch1_intro_html_uses_decomposed():
    """CH1 인트로 HTML: 분해 요소 4종 + @keyframes 포함 확인."""
    html = Path("assets/channels/CH1/intro/intro.html").read_text(encoding="utf-8")
    for ref in ["intro_frame.png", "intro_character.png", "intro_text.png", "intro_sparkle.png"]:
        assert ref in html, f"인트로 HTML 누락: {ref}"
    assert "@keyframes" in html, "인트로 HTML @keyframes 없음"


def test_ch1_outro_html_has_20_bills():
    """CH1 아웃트로 HTML: 지폐 20장 이상 + fly keyframe 확인."""
    html = Path("assets/channels/CH1/outro/outro.html").read_text(encoding="utf-8")
    bill_count = html.count('src="outro_bill.png"')
    assert bill_count >= 20, f"지폐 수 부족: {bill_count}"
    assert "@keyframes fly" in html, "아웃트로 HTML @keyframes fly 없음"


# ── CH1 레퍼런스 Crop 유효성 검증 ─────────────────────────────────────────────
def test_ch1_crop_regions_valid():
    from PIL import Image
    from config import CH1_CROP_REGIONS, CH1_POST_POLICY
    img = Image.open("essential_branding/CH1.png")
    W, H = img.size
    for name, (l, t, r, b) in CH1_CROP_REGIONS.items():
        assert 0 <= l < r <= W, f"{name}: bad x ({l},{r},W={W})"
        assert 0 <= t < b <= H, f"{name}: bad y ({t},{b},H={H})"
        assert (r - l) >= 30 and (b - t) >= 30, f"{name}: too small"
        assert name in CH1_POST_POLICY, f"{name}: policy missing"


def test_ch1_post_policy_keys_consistent():
    from config import CH1_CROP_REGIONS, CH1_POST_POLICY
    assert set(CH1_CROP_REGIONS) == set(CH1_POST_POLICY), (
        f"key mismatch: {set(CH1_CROP_REGIONS) ^ set(CH1_POST_POLICY)}"
    )


def test_ch1_cropper_pipeline(tmp_path):
    """reference_cropper가 CH1 에셋 23개를 올바르게 생성하는지 검증."""
    from PIL import Image
    import sys
    sys.path.insert(0, "scripts/generate_branding")
    import reference_cropper
    out = tmp_path / "CH1"
    reference_cropper.crop_channel("CH1", out)

    # 필수 파일 존재 확인
    expected = list(reference_cropper._CH1_OUTPUT_MAP.values())
    for rel in expected:
        p = out / rel
        assert p.exists(), f"missing: {rel}"
        assert p.stat().st_size > 200, f"too small: {rel}"

    # 로고·캐릭터는 RGBA (배경 투명)
    for rel in [
        "logo/logo.png",
        "characters/character_explain.png",
        "characters/character_rich.png",
    ]:
        img = Image.open(out / rel)
        assert img.mode == "RGBA", f"{rel} mode={img.mode}"
        assert img.size == (1024, 1024), f"{rel} size={img.size}"

    # 썸네일은 1920×1080 RGB
    for i in range(1, 4):
        img = Image.open(out / f"templates/thumbnail_sample_{i}.png")
        assert img.size == (1920, 1080), f"thumbnail_{i} size={img.size}"
