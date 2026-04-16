# tests/test_branding_assets.py
"""브랜딩 에셋 파일 존재·유효성 검증"""
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS

# CH1 PIL 전용 에셋 (Gemini API 불필요 — 항상 존재해야 함)
CH1_PIL_FILES = [
    "intro/intro.html",
    "intro/intro_frame.png",
    "intro/intro_text.png",
    "intro/intro_sparkle.png",
    "outro/outro.html",
    "outro/outro_bill.png",
    "outro/outro_background.png",
    "outro/outro_cta.png",
    "logo/logo.png",
]

# CH1 Gemini 의존 에셋 (캐릭터 PNG — API 호출 없으면 생성 안 됨)
CH1_GEMINI_FILES = [
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
    "intro/intro_character.png",   # character_explain.png 재사용
    "outro/outro_character.png",   # character_victory.png 재사용
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

@pytest.mark.parametrize("rel", CH1_PIL_FILES)
def test_ch1_pil_asset_exists(rel):
    """CH1 PIL 생성 에셋: 존재·최소 크기 확인 (Gemini API 불필요)."""
    from PIL import Image
    p = Path("assets/channels/CH1") / rel
    assert p.exists(), f"missing: {p}"
    if p.suffix == ".png":
        img = Image.open(p)
        assert img.size[0] >= 60 and img.size[1] >= 60, f"{rel} too small: {img.size}"


@pytest.mark.parametrize("rel", CH1_GEMINI_FILES)
def test_ch1_gemini_asset_exists(rel):
    """CH1 Gemini 생성 에셋: 존재 확인 (API 미실행 시 skip)."""
    from PIL import Image
    p = Path("assets/channels/CH1") / rel
    if not p.exists():
        pytest.skip(f"Gemini 캐릭터 PNG 미생성: {rel}")
    img = Image.open(p)
    assert img.size[0] >= 60 and img.size[1] >= 60, f"{rel} too small: {img.size}"


def test_ch1_logo_png_size():
    """CH1 로고 PNG: 512×512 이상 확인."""
    from PIL import Image
    path = Path("assets/channels/CH1/logo/logo.png")
    assert path.exists(), "logo/logo.png 없음"
    img = Image.open(path)
    assert img.size[0] >= 512 and img.size[1] >= 512, f"logo.png size={img.size}"


@pytest.mark.parametrize("rel,min_size", [
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
    """CH1 캐릭터 10종: 최소 크기 확인 (Gemini API 미실행 시 skip)."""
    from PIL import Image
    p = Path("assets/channels/CH1") / rel
    if not p.exists():
        pytest.skip(f"Gemini 캐릭터 PNG 미생성: {rel}")
    img = Image.open(p)
    assert img.size[0] >= min_size[0] and img.size[1] >= min_size[1], \
        f"{rel} size={img.size} < min={min_size}"


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


# ──────────────────────────────────────────────────────────────────────────────
# CH1 Imagen 2K 품질 강화 (v2.0) 테스트
# ──────────────────────────────────────────────────────────────────────────────

# 크림 배경 확인 대상 (좌상단 픽셀 기준)
CH1_CREAM_SURFACES = [
    "outro/outro_background.png",
    "templates/transition_ink.png",
    # transition_zoom은 어두운 배경 디자인 — 크림 검사 제외
]

@pytest.mark.parametrize("rel", CH1_CREAM_SURFACES)
def test_ch1_imagen_surface_is_cream(rel):
    """Imagen 생성 표면: 좌상단 픽셀이 warm cream 범위(R≥230, G≥200, B≥170) 확인.

    Imagen은 #FFFDF5 정확 재현이 아닌 warm cream 계열 근사값을 생성하므로
    넓은 허용 범위 적용 (실측: R≥251, G≥238, B≥202).
    """
    from PIL import Image
    path = Path("assets/channels/CH1") / rel
    if not path.exists():
        pytest.skip(f"{rel} 없음")
    img = Image.open(path).convert("RGB")
    r, g, b = img.getpixel((5, 5))
    assert r >= 230 and g >= 200 and b >= 170, \
        f"{rel} 좌상단 크림 계열 아님: RGB=({r},{g},{b})"


CH1_SVG_SOURCES = [
    # 새 파이프라인에서 logo.svg만 SVG로 생성 (나머지는 PIL PNG로 전환)
    "logo/logo.svg",
]

@pytest.mark.parametrize("rel", CH1_SVG_SOURCES)
def test_ch1_svg_source_valid_xml(rel):
    """CH1 SVG 소스 파일: 존재 + XML 유효성 확인."""
    import xml.etree.ElementTree as ET
    path = Path("assets/channels/CH1") / rel
    assert path.exists(), f"{rel} SVG 파일 없음"
    try:
        ET.parse(path)
    except ET.ParseError as e:
        pytest.fail(f"{rel} XML 파싱 오류: {e}")


CH1_IMAGEN_FILES = [
    "outro/outro_background.png",
    "templates/transition_paper.png",
    "templates/transition_ink.png",
    "templates/transition_zoom.png",
    "templates/thumbnail_sample_1.png",
    "templates/thumbnail_sample_2.png",
    "templates/thumbnail_sample_3.png",
]

@pytest.mark.parametrize("rel", CH1_IMAGEN_FILES)
def test_ch1_imagen_file_min_size(rel):
    """PIL/Gemini 생성 파일: 10KB 이상 (빈 파일 차단)."""
    path = Path("assets/channels/CH1") / rel
    if not path.exists():
        pytest.skip(f"{rel} 없음")
    size = path.stat().st_size
    assert size >= 10_000, f"{rel} 파일 크기 부족: {size:,} bytes"


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
    """CH1 캐릭터 (Gemini Pro 생성): 200KB 이상 확인 (API 미실행 시 skip)."""
    path = Path("assets/channels/CH1") / rel
    if not path.exists():
        pytest.skip(f"Gemini 캐릭터 PNG 미생성: {rel}")
    size = path.stat().st_size
    assert size >= 200_000, f"{rel} 크기 부족: {size:,} bytes"


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
