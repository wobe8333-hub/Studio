# tests/test_branding_assets.py
"""브랜딩 에셋 파일 존재·유효성 검증"""
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "generate_branding"))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS

def test_channels_dir_exists():
    assert CHANNELS_DIR.exists(), f"assets/channels/ 폴더 없음: {CHANNELS_DIR}"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
@pytest.mark.parametrize("subdir", SUBDIRS)
def test_subdir_exists(ch_id, subdir):
    path = CHANNELS_DIR / ch_id / subdir
    assert path.is_dir(), f"{ch_id}/{subdir} 폴더 없음"

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_logo_svg_exists_and_valid(ch_id):
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
    assert "<!DOCTYPE html" in content or "<html" in content

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

@pytest.mark.parametrize("ch_id", list(CHANNELS.keys()))
def test_templates_exist(ch_id):
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
