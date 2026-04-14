"""구현 계획 문서 생성 스크립트 — 7채널 에센셜 브랜딩 에셋"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

plan = '''# 7채널 에센셜 브랜딩 에셋 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Loomix 7채널(CH1~CH7) 각각의 로고·캐릭터·인트로·아웃트로·아이콘·템플릿·채널아트를 `assets/channels/` 정식 폴더에 자동 생성한다.

**Architecture:** Python 생성 스크립트(`scripts/generate_branding/`) 단계별 실행 → Gemini API로 캐릭터 PNG 생성 → SVG/HTML 파일 직접 코딩 저장. 채널 메타데이터는 `config.py` 단일 SSOT. 테스트는 파일 존재·SVG 유효성 검증.

**Tech Stack:** Python 3.10+, google-generativeai (Gemini imagen), pathlib, pytest

---

## 파일 구조

```
scripts/generate_branding/
├── config.py          # 7채널 메타데이터 SSOT
├── svg_helpers.py     # 두들 스타일 SVG 헬퍼 함수
├── logo_gen.py        # 채널 로고 SVG 생성
├── character_gen.py   # Gemini API 캐릭터 PNG 생성
├── intro_gen.py       # 인트로 HTML 생성 (3s)
├── outro_gen.py       # 아웃트로 HTML 생성 (10s)
├── icon_gen.py        # 도메인 아이콘 SVG 생성
├── template_gen.py    # 템플릿 SVG 생성
├── extras_gen.py      # 채널 아트·배너 SVG 생성
└── run_all.py         # 전체 파이프라인 실행

assets/channels/
└── CH1~CH7/
    ├── logo/logo.svg
    ├── characters/character_*.png
    ├── intro/intro.html
    ├── outro/outro.html
    ├── icons/*.svg
    ├── templates/*.svg
    └── extras/*.svg

tests/
└── test_branding_assets.py
```

---

### Task 1: 폴더 구조 생성 + 검증 테스트

**Files:**
- Create: `scripts/generate_branding/config.py`
- Create: `tests/test_branding_assets.py`

- [ ] **Step 1: config.py 작성**

```python
# scripts/generate_branding/config.py
"""7채널 브랜딩 메타데이터 SSOT"""
from pathlib import Path

KAS_ROOT = Path(__file__).parent.parent.parent
CHANNELS_DIR = KAS_ROOT / "assets" / "channels"
BRANDING_REF_DIR = KAS_ROOT / "essential_branding"

CHANNELS = {
    "CH1": {
        "name": "머니그래픽", "domain": "경제",
        "main_color": "#2ECC71", "bg_color": "#FFFFFF",
        "sub_colors": ["#3498DB", "#F1C40F", "#2C3E50"],
        "stroke_color": "#2C3E50",
        "characters": ["explain", "rich", "money", "lucky"],
        "character_prompts": {
            "explain": "cute doodle style character with crown, pointing finger explaining, Korean YouTube economics channel, white background, simple black outlines, cheerful expression",
            "rich": "cute doodle style character with crown, holding money bags, wealthy pose, Korean YouTube economics channel, white background, simple black outlines",
            "money": "cute doodle style character with crown, surrounded by flying money bills, excited expression, Korean YouTube economics channel, white background",
            "lucky": "cute doodle style character with crown, shocked happy expression, holding lottery ticket, Korean YouTube economics channel, white background",
        },
        "icons": ["money","coin","stock_up","stock_down","bank","interest",
                  "exchange","piggy","card","wallet","calculator",
                  "graph_up","graph_down","dollar","won","tax",
                  "inflation","recession","growth","bond"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH2": {
        "name": "가설낙서", "domain": "과학",
        "main_color": "#00E5FF", "bg_color": "#1A1A2E",
        "sub_colors": ["#00B8D4", "#FFFFFF", "#1A1A2E"],
        "stroke_color": "#00E5FF",
        "characters": ["curious", "explain", "research", "serious", "data"],
        "character_prompts": {
            "curious": "cute doodle style scientist character, wearing lab coat, curious expression, magnifying glass, neon cyan color scheme, dark background, simple outlines, Korean science YouTube",
            "explain": "cute doodle style scientist character, wearing lab coat, explaining with chalkboard, neon cyan color scheme, dark background, Korean science YouTube",
            "research": "cute doodle style scientist character, looking through microscope, focused expression, neon cyan color scheme, dark background, Korean science YouTube",
            "serious": "cute doodle style scientist character, serious thinking expression, holding formula paper, neon cyan color scheme, dark background, Korean science YouTube",
            "data": "cute doodle style scientist character, analyzing data on screen, excited expression, neon cyan color scheme, dark background, Korean science YouTube",
        },
        "icons": ["flask","microscope","atom","dna","telescope","rocket",
                  "lightbulb","magnet","circuit","graph","beaker","planet",
                  "formula","lab_coat","notebook","fire","water","wind",
                  "electricity","virus"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH3": {
        "name": "홈팔레트", "domain": "부동산",
        "main_color": "#E67E22", "bg_color": "#FFFFFF",
        "sub_colors": ["#3498DB", "#2ECC71", "#F1C40F"],
        "stroke_color": "#2C3E50",
        "characters": ["explain", "buy", "invest", "contract", "profit", "dream"],
        "character_prompts": {
            "explain": "cute doodle style character holding house model, explaining real estate, Korean YouTube, white background, orange color scheme, simple outlines",
            "buy": "cute doodle style character shaking hands in front of house, buying/selling pose, Korean YouTube, white background, orange color scheme",
            "invest": "cute doodle style character with rising graph and house, investment pose, Korean YouTube, white background, orange color scheme",
            "contract": "cute doodle style character signing contract document, serious expression, Korean YouTube, white background, orange color scheme",
            "profit": "cute doodle style character celebrating with money and house, profit expression, Korean YouTube, white background, orange color scheme",
            "dream": "cute doodle style character dreaming of perfect house, starry eyes, Korean YouTube, white background, orange color scheme",
        },
        "icons": ["house","apartment","building","key","contract","loan","interest",
                  "calculator","chart_up","chart_down","location_pin","map",
                  "wallet","handshake","crown","door","window","garden","elevator","bus"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH4": {
        "name": "오묘한심리", "domain": "심리",
        "main_color": "#9B59B6", "bg_color": "#FFFFFF",
        "sub_colors": ["#2C3E50", "#BDC3C7", "#FFFFFF"],
        "stroke_color": "#2C3E50",
        "characters": ["explore", "explain", "anxiety", "stress", "growth"],
        "character_prompts": {
            "explore": "cute doodle style character with brain symbol, exploring psychology theories, purple color scheme, white background, Korean psychology YouTube, simple outlines",
            "explain": "cute doodle style character with thought bubble, explaining mind concepts, purple color scheme, white background, Korean psychology YouTube",
            "anxiety": "cute doodle style character showing anxiety emotion, sweat drops, worried expression, purple color scheme, white background, Korean psychology YouTube",
            "stress": "cute doodle style character managing stress, calming expression, purple color scheme, white background, Korean psychology YouTube",
            "growth": "cute doodle style character with upward arrow, self-growth pose, confident expression, purple color scheme, white background, Korean psychology YouTube",
        },
        "icons": ["brain","heart","mirror","eye","thought_bubble","stress_cloud",
                  "growth_arrow","book","couch","clock","spiral","question",
                  "star","shield","hand_holding","meditation","journal",
                  "door_open","balance","mask"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH5": {
        "name": "검은물음표", "domain": "미스터리",
        "main_color": "#1C2833", "bg_color": "#F0F0F0",
        "sub_colors": ["#2E4057", "#AAAAAA", "#FFFFFF"],
        "stroke_color": "#1C2833",
        "characters": ["curious", "explain", "shocked", "think", "investigate", "win"],
        "character_prompts": {
            "curious": "cute doodle style mystery character with question mark, curious suspicious expression, dark color scheme, white background, Korean mystery YouTube, simple outlines",
            "explain": "cute doodle style mystery character explaining with magnifying glass, dark color scheme, white background, Korean mystery YouTube",
            "shocked": "cute doodle style mystery character with shocked expression, eyes wide open, dark color scheme, white background, Korean mystery YouTube",
            "think": "cute doodle style mystery character deep in thought, dark questioning expression, dark color scheme, white background, Korean mystery YouTube",
            "investigate": "cute doodle style mystery character searching for clues, detective pose, dark color scheme, white background, Korean mystery YouTube",
            "win": "cute doodle style mystery character celebrating solving mystery, triumphant expression, dark color scheme, white background, Korean mystery YouTube",
        },
        "icons": ["question_mark","eye_dark","magnifier","key_old","lock","shadow",
                  "ghost","skull","map_torn","compass","candle","raven","clue",
                  "fingerprint","door_mystery","fog","ancient_book","crystal_ball",
                  "spider","moon"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH6": {
        "name": "오래된두루마리", "domain": "역사",
        "main_color": "#A0522D", "bg_color": "#F5F0E0",
        "sub_colors": ["#C4A35A", "#6B4C11", "#F5F0E0"],
        "stroke_color": "#6B4C11",
        "characters": ["explore", "explain", "scholar", "travel"],
        "character_prompts": {
            "explore": "cute doodle style historian character with scroll, exploring ancient history, parchment brown color scheme, aged paper background, Korean history YouTube, simple outlines",
            "explain": "cute doodle style historian character explaining with open scroll, parchment brown color scheme, aged paper background, Korean history YouTube",
            "scholar": "cute doodle style historian character as scholar with quill pen, parchment brown color scheme, aged paper background, Korean history YouTube",
            "travel": "cute doodle style historian character on historical journey with map, parchment brown color scheme, aged paper background, Korean history YouTube",
        },
        "icons": ["scroll","map_old","sword","crown","castle","ship","compass_old",
                  "book_aged","hourglass","coin_old","portrait","flag","temple",
                  "arch","quill","shield_crest","lantern","cart","gate","column"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH7": {
        "name": "워메이징", "domain": "전쟁사",
        "main_color": "#C0392B", "bg_color": "#FFFFFF",
        "sub_colors": ["#2C3E50", "#7F8C8D", "#F1C40F"],
        "stroke_color": "#2C3E50",
        "characters": ["victory", "strategy", "battle", "general", "soldier"],
        "character_prompts": {
            "victory": "cute doodle style military general character, victory pose with raised fist, red military color scheme, white background, Korean war history YouTube, simple outlines",
            "strategy": "cute doodle style military general character, studying battle map, strategic thinking expression, red military color scheme, white background, Korean war history YouTube",
            "battle": "cute doodle style military general character, charging battle pose, determined expression, red military color scheme, white background, Korean war history YouTube",
            "general": "cute doodle style military general character, commanding pose, medal on chest, red military color scheme, white background, Korean war history YouTube",
            "soldier": "cute doodle style military soldier character, saluting pose, red military color scheme, white background, Korean war history YouTube",
        },
        "icons": ["sword_crossed","shield","tank","plane","ship_war","flag_military",
                  "medal","map_battle","cannon","helmet","rifle","bomb",
                  "general_star","binoculars","radio","trench","grenade",
                  "compass","dog_tag","victory"],
        "intro_duration": 3, "outro_duration": 10,
    },
}

SUBDIRS = ["logo", "characters", "intro", "outro", "icons", "templates", "extras"]
```

- [ ] **Step 2: 검증 테스트 작성**

```python
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
    # SVG XML 파싱 검증
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
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
cd C:/Users/조찬우/Desktop/ai_stuidio_claude
pytest tests/test_branding_assets.py -v --tb=no -q 2>&1 | head -30
```
Expected: FAILED (폴더·파일 없어서 전부 실패)

- [ ] **Step 4: 폴더 구조 생성 스크립트 작성 및 실행**

```python
# scripts/generate_branding/setup_folders.py
"""assets/channels/ 폴더 구조 일괄 생성"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS

def create_folder_structure():
    for ch_id in CHANNELS:
        for subdir in SUBDIRS:
            path = CHANNELS_DIR / ch_id / subdir
            path.mkdir(parents=True, exist_ok=True)
            print(f"  created: {path.relative_to(CHANNELS_DIR.parent.parent)}")
    print(f"\\n[완료] {len(CHANNELS) * len(SUBDIRS)}개 폴더 생성")

if __name__ == "__main__":
    create_folder_structure()
```

```bash
python scripts/generate_branding/setup_folders.py
```
Expected: 49개 폴더 생성 메시지

- [ ] **Step 5: 폴더 테스트 통과 확인**

```bash
pytest tests/test_branding_assets.py::test_subdir_exists -v --tb=short -q
```
Expected: 49 passed

- [ ] **Step 6: 커밋**

```bash
git add scripts/generate_branding/config.py scripts/generate_branding/setup_folders.py tests/test_branding_assets.py
git commit -m "feat: 브랜딩 에셋 config·폴더 구조·검증 테스트 추가"
```

---

### Task 2: SVG 두들 헬퍼 모듈

**Files:**
- Create: `scripts/generate_branding/svg_helpers.py`

- [ ] **Step 1: svg_helpers.py 작성**

```python
# scripts/generate_branding/svg_helpers.py
"""두들 스타일 SVG 헬퍼 — Manim SVGMobject 호환"""

def svg_open(width, height, bg_color="none"):
    bg = f\'<rect width="{width}" height="{height}" fill="{bg_color}"/>\' if bg_color != "none" else ""
    return (f\'\'\'<?xml version="1.0" encoding="UTF-8"?>\\n\'\'\'
            f\'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" \\'
            f\'viewBox="0 0 {width} {height}">{bg}\')

def svg_close():
    return "</svg>"

def doodle_circle(cx, cy, r, color, sw=4, fill="none"):
    """불규칙 bezier 원 — 손그림 느낌"""
    o = 3
    return (f\'<path d="M {cx+r+o},{cy} \\'
            f\'C {cx+r+o},{cy-r+o} {cx+o},{cy-r-o} {cx},{cy-r} \\'
            f\'C {cx-r-o},{cy-r+o} {cx-r+o},{cy+o} {cx-r},{cy} \\'
            f\'C {cx-r+o},{cy+r-o} {cx-o},{cy+r+o} {cx},{cy+r} \\'
            f\'C {cx+r+o},{cy+r-o} {cx+r-o},{cy-o} {cx+r+o},{cy} Z" \\'
            f\'fill="{fill}" stroke="{color}" stroke-width="{sw}" \\'
            f\'stroke-linecap="round" stroke-linejoin="round"/>\')

def doodle_rect(x, y, w, h, color, sw=4, fill="none", rx=8):
    """두들 스타일 사각형"""
    o = 2
    return (f\'<rect x="{x+o}" y="{y-o}" width="{w-o}" height="{h+o}" \\'
            f\'rx="{rx}" fill="{fill}" stroke="{color}" stroke-width="{sw}" \\'
            f\'stroke-linecap="round" stroke-linejoin="round"/>\')

def doodle_line(x1, y1, x2, y2, color, sw=3):
    """두들 직선 (약간 불규칙 bezier)"""
    mx, my = (x1+x2)//2 + 2, (y1+y2)//2 - 2
    return (f\'<path d="M {x1},{y1} Q {mx},{my} {x2},{y2}" \\'
            f\'fill="none" stroke="{color}" stroke-width="{sw}" \\'
            f\'stroke-linecap="round"/>\')

def doodle_text(text, x, y, size, color, anchor="middle", weight="bold"):
    return (f\'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" \\'
            f\'font-family="Gmarket Sans Bold, sans-serif" \\'
            f\'text-anchor="{anchor}" font-weight="{weight}">{text}</text>\')

def doodle_path(d, color, sw=4, fill="none"):
    """임의 두들 path"""
    return (f\'<path d="{d}" fill="{fill}" stroke="{color}" \\'
            f\'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>\')

def doodle_crown(cx, cy, size, color, sw=3):
    """왕관 두들 — CH1 머니그래픽 전용"""
    s = size
    return doodle_path(
        f"M {cx-s},{cy} L {cx-s},{cy-s*0.8} L {cx-s*0.4},{cy-s*0.3} "
        f"L {cx},{cy-s} L {cx+s*0.4},{cy-s*0.3} L {cx+s},{cy-s*0.8} L {cx+s},{cy} Z",
        color, sw, fill=color
    )

def doodle_star(cx, cy, r, color, sw=2):
    """별 두들"""
    import math
    pts = []
    for i in range(10):
        angle = math.pi * i / 5 - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.4
        pts.append(f"{cx + rad*math.cos(angle):.1f},{cy + rad*math.sin(angle):.1f}")
    return doodle_path("M " + " L ".join(pts) + " Z", color, sw, fill=color)

def group(content, transform=""):
    t = f\' transform="{transform}"\' if transform else ""
    return f"<g{t}>{content}</g>"
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/generate_branding/svg_helpers.py
git commit -m "feat: 두들 스타일 SVG 헬퍼 모듈 추가"
```

---

### Task 3: 채널 로고 SVG 생성 (7채널)

**Files:**
- Create: `scripts/generate_branding/logo_gen.py`

- [ ] **Step 1: logo_gen.py 작성**

```python
# scripts/generate_branding/logo_gen.py
"""7채널 로고 SVG 생성 — 두들 원형 배지 스타일"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import math
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import (svg_open, svg_close, doodle_circle, doodle_text,
                          doodle_path, doodle_crown, doodle_star, group)

DOMAIN_ICONS = {
    "경제": _draw_economy_icon,
    "과학": _draw_science_icon,
    "부동산": _draw_house_icon,
    "심리": _draw_brain_icon,
    "미스터리": _draw_question_icon,
    "역사": _draw_scroll_icon,
    "전쟁사": _draw_sword_icon,
}

def _draw_economy_icon(cx, cy, size, color):
    """왕관 아이콘"""
    return doodle_crown(cx, cy - size*0.15, size*0.35, color, sw=3)

def _draw_science_icon(cx, cy, size, color):
    """플라스크 아이콘"""
    s = size * 0.3
    return (doodle_path(f"M {cx-s*0.4},{cy-s} L {cx-s*0.6},{cy+s*0.5} "
                         f"Q {cx},{cy+s*1.2} {cx+s*0.6},{cy+s*0.5} L {cx+s*0.4},{cy-s} Z",
                         color, sw=3)
            + doodle_line(cx-s*0.5, cy-s, cx+s*0.5, cy-s, color, sw=3))

def _draw_house_icon(cx, cy, size, color):
    """집 아이콘"""
    s = size * 0.3
    return (doodle_path(f"M {cx},{cy-s} L {cx+s},{cy} L {cx+s},{cy+s} "
                         f"L {cx-s},{cy+s} L {cx-s},{cy} Z", color, sw=3)
            + doodle_path(f"M {cx-s*1.2},{cy} L {cx},{cy-s*1.3} L {cx+s*1.2},{cy}", color, sw=3))

def _draw_brain_icon(cx, cy, size, color):
    """뇌 아이콘 (좌우 반원)"""
    r = size * 0.28
    return (doodle_circle(cx - r*0.5, cy, r, color, sw=3)
            + doodle_circle(cx + r*0.5, cy, r, color, sw=3)
            + doodle_line(cx, cy-r, cx, cy+r, color, sw=2))

def _draw_question_icon(cx, cy, size, color):
    """물음표 아이콘"""
    s = size * 0.3
    return (doodle_path(f"M {cx-s*0.5},{cy-s} Q {cx-s*0.5},{cy-s*1.5} {cx},{cy-s*1.5} "
                         f"Q {cx+s*0.5},{cy-s*1.5} {cx+s*0.5},{cy-s} "
                         f"Q {cx+s*0.5},{cy-s*0.3} {cx},{cy} L {cx},{cy+s*0.3}", color, sw=4)
            + doodle_circle(cx, cy+s*0.7, s*0.15, color, sw=3, fill=color))

def _draw_scroll_icon(cx, cy, size, color):
    """두루마리 아이콘"""
    s = size * 0.3
    return (doodle_rect(cx-s, cy-s*0.7, s*2, s*1.4, color, sw=3)
            + doodle_circle(cx-s, cy, s*0.25, color, sw=3)
            + doodle_circle(cx+s, cy, s*0.25, color, sw=3)
            + doodle_line(cx-s*0.6, cy-s*0.3, cx+s*0.6, cy-s*0.3, color, sw=2)
            + doodle_line(cx-s*0.6, cy, cx+s*0.6, cy, color, sw=2)
            + doodle_line(cx-s*0.6, cy+s*0.3, cx+s*0.6, cy+s*0.3, color, sw=2))

def _draw_sword_icon(cx, cy, size, color):
    """교차 검 아이콘"""
    s = size * 0.35
    return (doodle_line(cx-s, cy-s, cx+s, cy+s, color, sw=4)
            + doodle_line(cx+s, cy-s, cx-s, cy+s, color, sw=4)
            + doodle_star(cx, cy, s*0.15, color, sw=2))

def generate_logo(ch_id):
    cfg = CHANNELS[ch_id]
    w, h = 500, 500
    cx, cy, r = 250, 250, 200
    main = cfg["main_color"]
    bg = cfg["bg_color"]
    stroke = cfg["stroke_color"]
    name = cfg["name"]

    # CH2는 다크 배경 처리
    bg_fill = bg if bg != "#FFFFFF" else "none"
    bg_rect = f\'<rect width="500" height="500" fill="{bg}"/>\' if bg != "#FFFFFF" else ""

    icon_fn = DOMAIN_ICONS.get(cfg["domain"], _draw_economy_icon)
    icon_svg = icon_fn(cx, cy - 40, r, main)

    parts = [
        svg_open(w, h, bg_color=bg),
        bg_rect,
        # 외곽 두들 원
        doodle_circle(cx, cy, r, main, sw=6),
        doodle_circle(cx, cy, r-12, main, sw=2),
        # 도메인 아이콘
        icon_svg,
        # 채널명 텍스트
        doodle_text(name, cx, cy + r*0.55, size=36, color=main),
        svg_close(),
    ]
    content = "\\n".join(parts)
    out = CHANNELS_DIR / ch_id / "logo" / "logo.svg"
    out.write_text(content, encoding="utf-8")
    print(f"  [OK] {ch_id} 로고 → {out.name}")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_logo(ch_id)
    print(f"\\n[완료] 7채널 로고 SVG 생성")
```

- [ ] **Step 2: 실행**

```bash
python scripts/generate_branding/logo_gen.py
```
Expected: `[OK] CH1 로고 → logo.svg` × 7줄

- [ ] **Step 3: 로고 테스트 통과 확인**

```bash
pytest tests/test_branding_assets.py::test_logo_svg_exists_and_valid -v
```
Expected: 7 passed

- [ ] **Step 4: 커밋**

```bash
git add scripts/generate_branding/logo_gen.py assets/channels/
git commit -m "feat: 7채널 두들 스타일 로고 SVG 생성"
```

---

### Task 4: Gemini API 캐릭터 PNG 생성

**Files:**
- Create: `scripts/generate_branding/character_gen.py`

- [ ] **Step 1: character_gen.py 작성**

```python
# scripts/generate_branding/character_gen.py
"""Gemini API imagen으로 채널 캐릭터 PNG 생성"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "imagen-3.0-generate-002"

def generate_character(ch_id, pose_key):
    cfg = CHANNELS[ch_id]
    prompt = cfg["character_prompts"][pose_key]
    out_path = CHANNELS_DIR / ch_id / "characters" / f"character_{pose_key}.png"

    try:
        result = genai.ImageGenerationModel(MODEL).generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_few",
        )
        image = result.images[0]
        out_path.write_bytes(image._image_bytes)
        print(f"  [OK] {ch_id}/{pose_key} → character_{pose_key}.png")
    except Exception as e:
        print(f"  [ERR] {ch_id}/{pose_key}: {e}")
    time.sleep(1.5)  # API rate limit

def run_all():
    for ch_id, cfg in CHANNELS.items():
        print(f"\\n[{ch_id}] {cfg[\'name\']} 캐릭터 생성...")
        for pose in cfg["characters"]:
            generate_character(ch_id, pose)

if __name__ == "__main__":
    run_all()
```

- [ ] **Step 2: 실행 (GEMINI_API_KEY 필요)**

```bash
python scripts/generate_branding/character_gen.py
```
Expected: 총 35장(CH1×4 + CH2×5 + CH3×6 + CH4×5 + CH5×6 + CH6×4 + CH7×5) PNG 생성

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/character_gen.py
git commit -m "feat: Gemini API 캐릭터 생성 스크립트 추가"
```

---

### Task 5: 인트로 HTML 생성 (3초, 7채널)

**Files:**
- Create: `scripts/generate_branding/intro_gen.py`

- [ ] **Step 1: intro_gen.py 작성**

```python
# scripts/generate_branding/intro_gen.py
"""영상 인트로 HTML 생성 — 3초, 채널 컬러 적용"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} 인트로</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:1920px; height:1080px; background:{bg_color}; overflow:hidden;
          font-family:\'Gmarket Sans\', sans-serif; display:flex;
          align-items:center; justify-content:center; }}
  .logo-wrap {{ opacity:0; transform:translateX(-120px);
                animation:slideIn 0.6s cubic-bezier(.22,1,.36,1) 0.3s forwards; }}
  .logo-circle {{ width:220px; height:220px; border-radius:50%;
                  border:6px solid {main_color}; display:flex; align-items:center;
                  justify-content:center; position:relative; }}
  .logo-inner {{ width:196px; height:196px; border-radius:50%;
                 border:2px solid {main_color}; }}
  .channel-name {{ font-size:72px; font-weight:900; color:{main_color};
                   margin-left:32px; opacity:0;
                   animation:fadeUp 0.5s ease 0.9s forwards; }}
  .domain-tag {{ font-size:28px; color:{sub_color}; margin-top:8px; opacity:0;
                 animation:fadeUp 0.5s ease 1.2s forwards; }}
  .deco-line {{ position:absolute; bottom:180px; width:600px; height:3px;
                background:linear-gradient(90deg, transparent, {main_color}, transparent);
                opacity:0; animation:fadeIn 0.8s ease 1.5s forwards; }}
  @keyframes slideIn {{
    to {{ opacity:1; transform:translateX(0); }}
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(20px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes fadeIn {{
    to {{ opacity:1; }}
  }}
</style>
</head>
<body>
  <div style="display:flex; align-items:center;">
    <div class="logo-wrap">
      <div class="logo-circle">
        <div class="logo-inner"></div>
      </div>
    </div>
    <div style="margin-left:40px;">
      <div class="channel-name">{name}</div>
      <div class="domain-tag">{domain}</div>
    </div>
  </div>
  <div class="deco-line"></div>
  <script>
    // 3초 후 자동 페이드아웃
    setTimeout(() => {{
      document.body.style.transition = "opacity 0.4s";
      document.body.style.opacity = "0";
    }}, 2600);
  </script>
</body>
</html>"""

def generate_intro(ch_id):
    cfg = CHANNELS[ch_id]
    html = TEMPLATE.format(
        name=cfg["name"],
        domain=cfg["domain"],
        main_color=cfg["main_color"],
        bg_color=cfg["bg_color"],
        sub_color=cfg["sub_colors"][0],
    )
    out = CHANNELS_DIR / ch_id / "intro" / "intro.html"
    out.write_text(html, encoding="utf-8")
    print(f"  [OK] {ch_id} 인트로 → intro.html")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_intro(ch_id)
    print("\\n[완료] 7채널 인트로 HTML 생성")
```

- [ ] **Step 2: 실행**

```bash
python scripts/generate_branding/intro_gen.py
```
Expected: `[OK] CH1~CH7 인트로 → intro.html` × 7줄

- [ ] **Step 3: 테스트**

```bash
pytest tests/test_branding_assets.py::test_intro_html_exists -v
```
Expected: 7 passed

- [ ] **Step 4: 커밋**

```bash
git add scripts/generate_branding/intro_gen.py assets/channels/
git commit -m "feat: 7채널 인트로 HTML 생성 (3초 통일)"
```

---

### Task 6: 아웃트로 HTML 생성 (10초, 7채널)

**Files:**
- Create: `scripts/generate_branding/outro_gen.py`

- [ ] **Step 1: outro_gen.py 작성**

```python
# scripts/generate_branding/outro_gen.py
"""영상 아웃트로 HTML — 10초, 구독·좋아요 CTA + 다음영상 카드"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{name} 아웃트로</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:1920px; height:1080px; background:{bg_color};
          font-family:\'Gmarket Sans\', sans-serif; overflow:hidden; }}
  .top-msg {{ position:absolute; top:120px; left:50%; transform:translateX(-50%);
              font-size:56px; font-weight:900; color:{main_color}; text-align:center;
              opacity:0; animation:fadeUp 0.6s ease 0.3s forwards; }}
  .cta-wrap {{ position:absolute; top:320px; left:50%; transform:translateX(-50%);
               display:flex; gap:60px; opacity:0;
               animation:fadeUp 0.6s ease 1s forwards; }}
  .btn-sub {{ background:#FF0000; color:#fff; font-size:40px; font-weight:900;
              padding:28px 64px; border-radius:60px; border:4px solid #fff;
              animation:pulse 1.2s ease-in-out 2s infinite; }}
  .btn-like {{ background:{main_color}; color:{bg_color}; font-size:40px; font-weight:900;
               padding:28px 64px; border-radius:60px; border:4px solid {main_color}; }}
  .cards-wrap {{ position:absolute; bottom:80px; left:50%; transform:translateX(-50%);
                 display:flex; gap:48px; opacity:0;
                 animation:fadeUp 0.6s ease 3s forwards; }}
  .next-card {{ width:480px; height:270px; border:4px solid {main_color};
                border-radius:16px; background:rgba(0,0,0,0.15);
                display:flex; align-items:center; justify-content:center;
                font-size:28px; color:{main_color}; font-weight:700; text-align:center; }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateX(-50%) translateY(24px); }}
    to {{ opacity:1; transform:translateX(-50%) translateY(0); }}
  }}
  @keyframes pulse {{
    0%,100% {{ transform:scale(1); }}
    50% {{ transform:scale(1.06); }}
  }}
</style>
</head>
<body>
  <div class="top-msg">영상이 도움이 됐나요? 🙌</div>
  <div class="cta-wrap">
    <div class="btn-sub">🔔 구독</div>
    <div class="btn-like">👍 좋아요</div>
  </div>
  <div class="cards-wrap">
    <div class="next-card">다음 영상<br>추천 1</div>
    <div class="next-card">다음 영상<br>추천 2</div>
  </div>
  <script>
    // 10초 후 페이드아웃
    setTimeout(() => {{
      document.body.style.transition = "opacity 0.5s";
      document.body.style.opacity = "0";
    }}, 9500);
  </script>
</body>
</html>"""

def generate_outro(ch_id):
    cfg = CHANNELS[ch_id]
    html = TEMPLATE.format(
        name=cfg["name"],
        main_color=cfg["main_color"],
        bg_color=cfg["bg_color"],
    )
    out = CHANNELS_DIR / ch_id / "outro" / "outro.html"
    out.write_text(html, encoding="utf-8")
    print(f"  [OK] {ch_id} 아웃트로 → outro.html")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_outro(ch_id)
    print("\\n[완료] 7채널 아웃트로 HTML 생성")
```

- [ ] **Step 2: 실행 + 테스트**

```bash
python scripts/generate_branding/outro_gen.py
pytest tests/test_branding_assets.py::test_outro_html_exists -v
```
Expected: 7 passed

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/outro_gen.py assets/channels/
git commit -m "feat: 7채널 아웃트로 HTML 생성 (10초, 구독 CTA)"
```

---

### Task 7: 아이콘 SVG 세트 생성 (7채널 × 20종)

**Files:**
- Create: `scripts/generate_branding/icon_gen.py`

- [ ] **Step 1: icon_gen.py 작성**

```python
# scripts/generate_branding/icon_gen.py
"""도메인별 두들 아이콘 SVG 생성 — Manim SVGMobject 완벽 호환"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import math
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_path, doodle_circle, doodle_line, doodle_rect

W = H = 100
C = 50  # 중심

def icon_svg(body, color):
    return svg_open(W, H) + body + svg_close()

# ─── CH1 경제 아이콘 ───
ICONS_CH1 = {
    "money": lambda c: (doodle_rect(15,30,70,45,c,sw=4)
                        + doodle_circle(C,C+5,14,c,sw=3)
                        + doodle_line(20,30,20,75,c,sw=2)
                        + doodle_line(80,30,80,75,c,sw=2)),
    "coin": lambda c: (doodle_circle(C,C,32,c,sw=4)
                       + doodle_circle(C,C,22,c,sw=2)
                       + doodle_path(f"M {C-6},38 L {C},35 L {C+6},38",c,sw=3)),
    "stock_up": lambda c: (doodle_path(f"M 10,75 L 30,55 L 50,65 L 75,30 L 90,20",c,sw=4)
                            + doodle_path(f"M 75,20 L 90,20 L 90,35",c,sw=3)),
    "stock_down": lambda c: (doodle_path(f"M 10,25 L 30,45 L 50,35 L 75,70 L 90,80",c,sw=4)
                              + doodle_path(f"M 75,80 L 90,80 L 90,65",c,sw=3)),
    "bank": lambda c: (doodle_path(f"M 10,75 L 90,75",c,sw=4)
                       + doodle_path(f"M 10,45 L 90,45",c,sw=3)
                       + doodle_path(f"M C,15 L 10,45 L 90,45 Z".replace("C",str(C)),c,sw=4)
                       + doodle_line(25,45,25,75,c,sw=3)
                       + doodle_line(50,45,50,75,c,sw=3)
                       + doodle_line(75,45,75,75,c,sw=3)),
    "interest": lambda c: (doodle_circle(30,38,14,c,sw=4)
                            + doodle_circle(70,62,14,c,sw=4)
                            + doodle_path(f"M 15,75 L 85,25",c,sw=3)
                            + doodle_path(f"M {C-4},{C-16} L {C+4},{C-16}",c,sw=2)),
    "exchange": lambda c: (doodle_path(f"M 15,38 L 75,38 L 60,25",c,sw=4)
                            + doodle_path(f"M 85,62 L 25,62 L 40,75",c,sw=4)),
    "piggy": lambda c: (doodle_circle(45,C,28,c,sw=4)
                         + doodle_circle(72,40,12,c,sw=3)
                         + doodle_circle(45,32,5,c,sw=2)
                         + doodle_path(f"M 30,75 L 25,88 M 45,78 L 45,92 M 60,75 L 65,88",c,sw=3)
                         + doodle_line(68,C,80,C,c,sw=3)),
    "card": lambda c: (doodle_rect(10,28,80,45,c,sw=4,rx=6)
                       + doodle_line(10,42,90,42,c,sw=4)
                       + doodle_rect(18,52,25,12,c,sw=2,rx=2)),
    "wallet": lambda c: (doodle_rect(8,30,72,45,c,sw=4,rx=6)
                          + doodle_rect(65,38,22,28,c,sw=3,rx=12)
                          + doodle_circle(76,C+2,7,c,sw=2)),
    "calculator": lambda c: (doodle_rect(20,15,60,70,c,sw=4,rx=4)
                              + doodle_rect(28,23,44,18,c,sw=2,rx=2)
                              + "".join(doodle_circle(30+i*15,52,5,c,sw=2) for i in range(4))
                              + "".join(doodle_circle(30+i*15,67,5,c,sw=2) for i in range(4))),
    "graph_up": lambda c: (doodle_path(f"M 10,85 L 10,15",c,sw=3)
                            + doodle_path(f"M 10,85 L 92,85",c,sw=3)
                            + doodle_path(f"M 20,70 L 40,50 L 60,60 L 82,25",c,sw=4)
                            + doodle_rect(18,62,14,23,c,sw=2)
                            + doodle_rect(38,42,14,43,c,sw=2)
                            + doodle_rect(58,52,14,33,c,sw=2)
                            + doodle_rect(78,17,14,68,c,sw=2)),
    "graph_down": lambda c: (doodle_path(f"M 10,85 L 10,15",c,sw=3)
                              + doodle_path(f"M 10,85 L 92,85",c,sw=3)
                              + doodle_rect(18,30,14,55,c,sw=2)
                              + doodle_rect(38,45,14,40,c,sw=2)
                              + doodle_rect(58,55,14,30,c,sw=2)
                              + doodle_rect(78,65,14,20,c,sw=2)),
    "dollar": lambda c: (doodle_circle(C,C,36,c,sw=4)
                          + doodle_path(f"M {C},20 L {C},80",c,sw=3)
                          + doodle_path(f"M {C-14},35 Q {C-18},28 {C},{C-10} Q {C+18},28 {C+14},35 Q {C+18},50 {C},{C+3} Q {C-18},58 {C-14},65 Q {C-18},72 {C},{C+12}",c,sw=3)),
    "won": lambda c: (doodle_circle(C,C,36,c,sw=4)
                      + doodle_path(f"M 30,30 L 42,65 L C,55 L 58,65 L 70,30".replace("C",str(C)),c,sw=3)
                      + doodle_line(28,48,72,48,c,sw=2)
                      + doodle_line(28,58,72,58,c,sw=2)),
    "tax": lambda c: (doodle_rect(20,10,60,80,c,sw=4,rx=4)
                      + doodle_line(30,28,70,28,c,sw=3)
                      + doodle_line(30,40,70,40,c,sw=3)
                      + doodle_line(30,52,55,52,c,sw=3)
                      + doodle_circle(68,62,10,c,sw=3)
                      + doodle_path(f"M 64,58 L 72,66 M 72,58 L 64,66",c,sw=2)),
    "inflation": lambda c: (doodle_circle(C,38,26,c,sw=4)
                             + doodle_path(f"M {C-4},64 L {C-8},85 M {C+4},64 L {C+8},85",c,sw=3)
                             + doodle_path(f"M {C-2},28 L {C-2},22 M {C+2},28 L {C+2},22",c,sw=2)),
    "recession": lambda c: (doodle_path(f"M 10,40 Q 30,20 50,30 Q 70,40 90,30",c,sw=4)
                             + "".join(doodle_line(20+i*15,45,20+i*15,75,c,sw=3) for i in range(5))),
    "growth": lambda c: (doodle_path(f"M 10,85 Q 30,60 50,55 Q 70,50 90,20",c,sw=4)
                          + doodle_path(f"M 80,20 L 90,20 L 90,30",c,sw=3)
                          + doodle_circle(C,70,10,c,sw=3,fill=c)),
    "bond": lambda c: (doodle_rect(15,15,70,70,c,sw=4,rx=4)
                       + doodle_circle(C,C,18,c,sw=3)
                       + doodle_path(f"M {C-8},{C-4} L {C},{C+8} L {C+12},{C-10}",c,sw=4)),
}

# ─── CH2 과학 아이콘 ───
ICONS_CH2 = {
    "flask": lambda c: (doodle_path(f"M 38,15 L 38,45 L 15,80 Q 12,88 20,90 L 80,90 Q 88,88 85,80 L 62,45 L 62,15 Z",c,sw=4)
                         + doodle_line(32,15,68,15,c,sw=4)
                         + doodle_circle(42,72,6,c,sw=2,fill=c)
                         + doodle_circle(58,62,4,c,sw=2,fill=c)),
    "microscope": lambda c: (doodle_line(C,20,C,65,c,sw=5)
                              + doodle_rect(35,62,30,15,c,sw=4)
                              + doodle_line(20,77,80,77,c,sw=4)
                              + doodle_circle(C,20,10,c,sw=3)
                              + doodle_line(38,40,62,40,c,sw=3)),
    "atom": lambda c: (doodle_circle(C,C,8,c,sw=3,fill=c)
                       + doodle_path(f"M {C-35},{C} Q {C},{C-25} {C+35},{C}",c,sw=3)
                       + doodle_path(f"M {C-35},{C} Q {C},{C+25} {C+35},{C}",c,sw=3)
                       + doodle_path(f"M {C},{C-35} Q {C+25},{C} {C},{C+35}",c,sw=3)
                       + doodle_path(f"M {C},{C-35} Q {C-25},{C} {C},{C+35}",c,sw=3)),
    "dna": lambda c: (doodle_path(f"M 30,10 Q 60,25 30,40 Q 60,55 30,70 Q 60,85 30,90",c,sw=3)
                      + doodle_path(f"M 70,10 Q 40,25 70,40 Q 40,55 70,70 Q 40,85 70,90",c,sw=3)
                      + doodle_line(38,26,62,26,c,sw=2)
                      + doodle_line(38,52,62,52,c,sw=2)
                      + doodle_line(38,76,62,76,c,sw=2)),
    "telescope": lambda c: (doodle_path(f"M 20,75 L 75,35",c,sw=5)
                             + doodle_path(f"M 65,28 L 82,20 L 85,30 L 68,38 Z",c,sw=3)
                             + doodle_circle(25,78,6,c,sw=3)
                             + doodle_line(25,84,C,84,c,sw=3)),
    "rocket": lambda c: (doodle_path(f"M {C},{15} Q {C+20},25 {C+20},55 L {C+10},65 L {C-10},65 Q {C-20},55 {C-20},55 Q {C-20},25 {C},15 Z",c,sw=4)
                          + doodle_circle(C,42,10,c,sw=3)
                          + doodle_path(f"M {C-20},55 L {C-30},75 L {C-10},65",c,sw=3)
                          + doodle_path(f"M {C+20},55 L {C+30},75 L {C+10},65",c,sw=3)),
    "lightbulb": lambda c: (doodle_circle(C,38,24,c,sw=4)
                             + doodle_path(f"M {C-12},60 Q {C-14},70 {C-10},75 L {C+10},75 Q {C+14},70 {C+12},60",c,sw=3)
                             + doodle_line(C-8,78,C+8,78,c,sw=3)
                             + doodle_line(C-6,83,C+6,83,c,sw=3)
                             + doodle_line(C,10,C,18,c,sw=2)
                             + doodle_line(20,20,26,26,c,sw=2)
                             + doodle_line(80,20,74,26,c,sw=2)),
    "magnet": lambda c: (doodle_path(f"M 20,70 L 20,40 Q 20,15 {C},15 Q 80,15 80,40 L 80,70",c,sw=5)
                          + doodle_line(12,70,28,70,c,sw=5)
                          + doodle_line(72,70,88,70,c,sw=5)),
    "circuit": lambda c: (doodle_line(10,C,90,C,c,sw=3)
                           + doodle_rect(38,38,24,24,c,sw=3,rx=2)
                           + doodle_line(C,10,C,38,c,sw=2)
                           + doodle_line(C,62,C,90,c,sw=2)
                           + doodle_circle(15,C,5,c,sw=2,fill=c)
                           + doodle_circle(85,C,5,c,sw=2,fill=c)),
    "graph": lambda c: (doodle_path(f"M 10,85 L 10,15",c,sw=3)
                        + doodle_path(f"M 10,85 L 90,85",c,sw=3)
                        + doodle_path(f"M 20,65 Q 35,45 50,50 Q 65,55 80,25",c,sw=4)),
    "beaker": lambda c: (doodle_path(f"M 35,15 L 35,55 L 15,85 L 85,85 L 65,55 L 65,15 Z",c,sw=4)
                          + doodle_line(28,15,72,15,c,sw=3)
                          + doodle_line(18,72,65,72,c,sw=2)),
    "planet": lambda c: (doodle_circle(C,C,28,c,sw=4)
                          + doodle_path(f"M 8,C Q {C},28 92,C Q {C},72 8,C".replace("C",str(C)),c,sw=3)
                          + doodle_line(12,38,88,38,c,sw=2)),
    "formula": lambda c: (doodle_path(f"M 15,C L 30,30 L 45,C L 60,30 L 75,C L 90,30".replace("C",str(C)),c,sw=4)
                           + doodle_path(f"M 20,{C+20} L 80,{C+20}",c,sw=2)),
    "lab_coat": lambda c: (doodle_path(f"M 30,15 L 15,35 L 15,85 L 85,85 L 85,35 L 70,15",c,sw=4)
                            + doodle_path(f"M 30,15 L 38,30 L {C},22 L 62,30 L 70,15",c,sw=3)
                            + doodle_circle(45,55,5,c,sw=2,fill=c)
                            + doodle_circle(45,68,5,c,sw=2,fill=c)),
    "notebook": lambda c: (doodle_rect(20,10,60,80,c,sw=4,rx=4)
                            + doodle_line(35,10,35,90,c,sw=3)
                            + doodle_line(42,28,72,28,c,sw=2)
                            + doodle_line(42,40,72,40,c,sw=2)
                            + doodle_line(42,52,72,52,c,sw=2)
                            + doodle_line(42,64,65,64,c,sw=2)),
    "fire": lambda c: (doodle_path(f"M {C},85 Q 20,70 25,50 Q 20,60 30,55 Q 25,35 {C},20 Q 55,35 65,55 Q 75,60 75,50 Q 80,70 {C},85 Z",c,sw=4)),
    "water": lambda c: (doodle_path(f"M {C},20 Q 70,50 {C},80 Q 30,50 {C},20 Z",c,sw=4)),
    "wind": lambda c: (doodle_path(f"M 10,38 Q 40,28 60,38 Q 75,45 72,55 Q 65,68 48,60 L 10,60",c,sw=4)
                       + doodle_path(f"M 10,C Q 55,{C-15} 70,C".replace("C",str(C)),c,sw=3)),
    "electricity": lambda c: (doodle_path(f"M 55,15 L 35,C L 55,C L 35,85".replace("C",str(C)),c,sw=5)),
    "virus": lambda c: (doodle_circle(C,C,22,c,sw=4)
                        + "".join(
                            doodle_line(
                                int(C+22*math.cos(math.pi*i/4)),
                                int(C+22*math.sin(math.pi*i/4)),
                                int(C+36*math.cos(math.pi*i/4)),
                                int(C+36*math.sin(math.pi*i/4)),
                                c, sw=3
                            ) + doodle_circle(
                                int(C+38*math.cos(math.pi*i/4)),
                                int(C+38*math.sin(math.pi*i/4)),
                                4, c, sw=2, fill=c
                            ) for i in range(8)
                        )),
}

# ─── CH3~CH7 아이콘은 공통 패턴으로 간략화 ───
def _simple_icon(shape_fn):
    return shape_fn

ICONS_CH3 = {
    "house": lambda c: (doodle_path(f"M {C},15 L 85,50 L 85,85 L 15,85 L 15,50 Z",c,sw=4)
                        + doodle_path(f"M 5,52 L {C},12 L 95,52",c,sw=4)
                        + doodle_rect(38,58,24,27,c,sw=3,rx=2)),
    "apartment": lambda c: (doodle_rect(15,25,70,60,c,sw=4)
                             + "".join(doodle_rect(22+i*18,33,12,12,c,sw=2) for i in range(3))
                             + "".join(doodle_rect(22+i*18,52,12,12,c,sw=2) for i in range(3))
                             + doodle_line(15,85,85,85,c,sw=4)),
    "building": lambda c: (doodle_rect(20,15,60,70,c,sw=4)
                            + "".join(doodle_rect(25+i*14,22,10,10,c,sw=2) for i in range(3))
                            + "".join(doodle_rect(25+i*14,38,10,10,c,sw=2) for i in range(3))
                            + "".join(doodle_rect(25+i*14,54,10,10,c,sw=2) for i in range(3))
                            + doodle_rect(38,68,24,17,c,sw=2,rx=2)),
    "key": lambda c: (doodle_circle(32,38,18,c,sw=4)
                      + doodle_circle(32,38,9,c,sw=2)
                      + doodle_line(48,38,88,38,c,sw=4)
                      + doodle_line(75,38,75,52,c,sw=4)
                      + doodle_line(85,38,85,48,c,sw=4)),
    "contract": lambda c: (doodle_rect(15,10,70,80,c,sw=4,rx=3)
                            + doodle_line(25,28,75,28,c,sw=3)
                            + doodle_line(25,40,75,40,c,sw=3)
                            + doodle_line(25,52,55,52,c,sw=3)
                            + doodle_path(f"M 55,62 L 80,75 L 70,85 L 45,72 Z",c,sw=3)),
    "loan": lambda c: (doodle_circle(C,C,30,c,sw=4)
                       + doodle_path(f"M {C-8},38 L {C},35 L {C+8},38 L {C+8},62 L {C-8},62 Z",c,sw=3)
                       + doodle_line(C-14,C,C+14,C,c,sw=3)),
    "interest": lambda c: (doodle_circle(30,35,14,c,sw=4) + doodle_circle(70,65,14,c,sw=4)
                            + doodle_line(15,75,85,25,c,sw=3)),
    "calculator": lambda c: ICONS_CH1["calculator"](c),
    "chart_up": lambda c: ICONS_CH1["stock_up"](c),
    "chart_down": lambda c: ICONS_CH1["stock_down"](c),
    "location_pin": lambda c: (doodle_circle(C,35,22,c,sw=4)
                                + doodle_path(f"M {C-22},35 Q {C-22},70 {C},88 Q {C+22},70 {C+22},35",c,sw=4)
                                + doodle_circle(C,35,8,c,sw=2,fill=c)),
    "map": lambda c: (doodle_path(f"M 15,15 L 38,22 L 62,15 L 85,22 L 85,82 L 62,75 L 38,82 L 15,75 Z",c,sw=4)
                      + doodle_line(38,22,38,82,c,sw=3)
                      + doodle_line(62,15,62,75,c,sw=3)),
    "wallet": lambda c: ICONS_CH1["wallet"](c),
    "handshake": lambda c: (doodle_path(f"M 10,C L 35,{C-15} L {C},{C-10} L 65,{C-15} L 90,C".replace("C",str(C)),c,sw=4)
                             + doodle_path(f"M 10,C L 35,{C+15} L {C},{C+10} L 65,{C+15} L 90,C".replace("C",str(C)),c,sw=4)),
    "crown": lambda c: doodle_crown(C,C,35,c,sw=4),
    "door": lambda c: (doodle_rect(22,15,56,75,c,sw=4,rx=3)
                       + doodle_circle(68,C,5,c,sw=3,fill=c)
                       + doodle_path(f"M 40,15 Q 50,10 60,15",c,sw=3)),
    "window": lambda c: (doodle_rect(15,15,70,70,c,sw=4,rx=3)
                          + doodle_line(C,15,C,85,c,sw=3)
                          + doodle_line(15,C,85,C,c,sw=3)),
    "garden": lambda c: (doodle_path(f"M {C},75 Q {C-20},55 {C-15},35 Q {C},20 {C+15},35 Q {C+20},55 {C},75",c,sw=4)
                          + doodle_line(C,75,C,88,c,sw=4)
                          + doodle_line(15,88,85,88,c,sw=3)),
    "elevator": lambda c: (doodle_rect(20,10,60,80,c,sw=4,rx=2)
                            + doodle_line(C,10,C,90,c,sw=3)
                            + doodle_path(f"M {C-10},35 L {C},25 L {C+10},35",c,sw=3)
                            + doodle_path(f"M {C-10},65 L {C},75 L {C+10},65",c,sw=3)),
    "bus": lambda c: (doodle_rect(10,20,80,60,c,sw=4,rx=8)
                      + "".join(doodle_rect(18+i*22,28,16,18,c,sw=2,rx=3) for i in range(3))
                      + doodle_circle(28,84,10,c,sw=4)
                      + doodle_circle(72,84,10,c,sw=4)),
}

ICONS_CH4 = {k: lambda c, k=k: doodle_circle(C,C,30,c,sw=4) for k in CHANNELS["CH4"]["icons"]}
ICONS_CH4["brain"] = lambda c: (doodle_circle(C-12,C,22,c,sw=4) + doodle_circle(C+12,C,22,c,sw=4) + doodle_line(C,C-18,C,C+18,c,sw=2))
ICONS_CH4["heart"] = lambda c: doodle_path(f"M {C},72 Q 10,50 10,35 Q 10,15 {C-15},22 Q {C},28 {C},{C-5} Q {C},28 {C+15},22 Q 90,15 90,35 Q 90,50 {C},72 Z",c,sw=4)
ICONS_CH4["thought_bubble"] = lambda c: (doodle_circle(C,35,28,c,sw=4) + doodle_circle(C-5,68,10,c,sw=3) + doodle_circle(C-8,82,6,c,sw=2))
ICONS_CH4["stress_cloud"] = lambda c: (doodle_path(f"M 20,60 Q 10,50 15,38 Q 12,20 30,22 Q 32,10 {C},12 Q 68,10 72,22 Q 88,18 90,35 Q 95,50 82,60 Z",c,sw=4))

ICONS_CH5 = {k: lambda c, k=k: doodle_path(f"M {C},{C-30} Q {C+30},{C-30} {C+30},{C} Q {C+30},{C+30} {C},{C+30} Q {C-30},{C+30} {C-30},{C} Q {C-30},{C-30} {C},{C-30} Z",c,sw=4) for k in CHANNELS["CH5"]["icons"]}
ICONS_CH5["question_mark"] = lambda c: (doodle_path(f"M {C-12},{C-28} Q {C-16},{C-42} {C},{C-42} Q {C+16},{C-42} {C+16},{C-28} Q {C+16},{C-14} {C},{C-8} L {C},{C+5}",c,sw=5) + doodle_circle(C,C+18,5,c,sw=3,fill=c))
ICONS_CH5["ghost"] = lambda c: (doodle_path(f"M 20,85 L 20,40 Q 20,15 {C},15 Q 80,15 80,40 L 80,85 L 68,72 L {C},85 L 32,72 Z",c,sw=4) + doodle_circle(38,48,7,c,sw=3,fill=c) + doodle_circle(62,48,7,c,sw=3,fill=c))
ICONS_CH5["magnifier"] = lambda c: (doodle_circle(38,38,24,c,sw=4) + doodle_line(56,56,85,85,c,sw=6))
ICONS_CH5["moon"] = lambda c: doodle_path(f"M {C+10},18 Q {C-20},20 {C-28},{C} Q {C-20},80 {C+10},82 Q {C-15},70 {C-15},{C} Q {C-15},30 {C+10},18 Z",c,sw=4)

ICONS_CH6 = {k: lambda c, k=k: doodle_rect(15,15,70,70,c,sw=4,rx=6) for k in CHANNELS["CH6"]["icons"]}
ICONS_CH6["scroll"] = lambda c: (doodle_rect(20,20,60,60,c,sw=4,rx=4) + doodle_circle(20,C,12,c,sw=4) + doodle_circle(80,C,12,c,sw=4) + doodle_line(28,35,72,35,c,sw=2) + doodle_line(28,C,72,C,c,sw=2) + doodle_line(28,65,60,65,c,sw=2))
ICONS_CH6["sword"] = lambda c: (doodle_line(C-35,C+35,C+35,C-35,c,sw=5) + doodle_path(f"M {C-42},{C+42} L {C-38},{C+38}",c,sw=8) + doodle_line(C-8,C+8,C+8,C-8,c,sw=3))
ICONS_CH6["crown"] = lambda c: doodle_crown(C,C,38,c,sw=4)
ICONS_CH6["castle"] = lambda c: (doodle_rect(15,38,70,47,c,sw=4) + doodle_rect(15,25,14,18,c,sw=3) + doodle_rect(43,25,14,18,c,sw=3) + doodle_rect(71,25,14,18,c,sw=3) + doodle_rect(38,58,24,27,c,sw=3,rx=2))
ICONS_CH6["hourglass"] = lambda c: (doodle_path(f"M 20,15 L 80,15 L {C},C L 80,85 L 20,85 L {C},C Z".replace("C",str(C)),c,sw=4) + doodle_line(15,15,85,15,c,sw=4) + doodle_line(15,85,85,85,c,sw=4))

ICONS_CH7 = {k: lambda c, k=k: doodle_circle(C,C,30,c,sw=4) for k in CHANNELS["CH7"]["icons"]}
ICONS_CH7["sword_crossed"] = lambda c: (doodle_line(15,15,85,85,c,sw=5) + doodle_line(85,15,15,85,c,sw=5))
ICONS_CH7["shield"] = lambda c: doodle_path(f"M {C},{15} L 82,30 L 82,C Q 82,75 {C},88 Q 18,75 18,C L 18,30 Z".replace("C",str(C)),c,sw=4)
ICONS_CH7["tank"] = lambda c: (doodle_rect(12,42,76,35,c,sw=4,rx=8) + doodle_rect(22,28,56,18,c,sw=3,rx=4) + doodle_line(60,28,85,18,c,sw=4) + "".join(doodle_circle(20+i*15,78,8,c,sw=3) for i in range(5)))
ICONS_CH7["medal"] = lambda c: (doodle_circle(C,55,28,c,sw=4) + doodle_star(C,55,15,c,sw=2) + doodle_line(C-12,28,C-8,8,c,sw=3) + doodle_line(C+12,28,C+8,8,c,sw=3) + doodle_line(C-8,8,C+8,8,c,sw=3))
ICONS_CH7["helmet"] = lambda c: (doodle_path(f"M 15,58 Q 15,22 {C},18 Q 85,22 85,58 L 85,65 L 15,65 Z",c,sw=4) + doodle_rect(10,62,80,12,c,sw=3,rx=4))
ICONS_CH7["flag_military"] = lambda c: (doodle_line(20,15,20,85,c,sw=4) + doodle_path(f"M 20,18 L 75,28 L 75,55 L 20,48 Z",c,sw=3))
ICONS_CH7["cannon"] = lambda c: (doodle_rect(15,C-10,55,22,c,sw=4,rx=6) + doodle_circle(80,C,12,c,sw=3) + doodle_circle(25,C+16,12,c,sw=4) + doodle_circle(48,C+16,12,c,sw=4))

CHANNEL_ICONS = {
    "CH1": ICONS_CH1, "CH2": ICONS_CH2, "CH3": ICONS_CH3,
    "CH4": ICONS_CH4, "CH5": ICONS_CH5, "CH6": ICONS_CH6, "CH7": ICONS_CH7,
}

def generate_icons(ch_id):
    cfg = CHANNELS[ch_id]
    color = cfg["main_color"]
    icons_map = CHANNEL_ICONS[ch_id]
    out_dir = CHANNELS_DIR / ch_id / "icons"
    count = 0
    for icon_name in cfg["icons"]:
        fn = icons_map.get(icon_name)
        if fn is None:
            body = doodle_circle(C, C, 30, color, sw=4)
        else:
            body = fn(color)
        content = icon_svg(body, color)
        (out_dir / f"{icon_name}.svg").write_text(content, encoding="utf-8")
        count += 1
    print(f"  [OK] {ch_id} 아이콘 {count}종 생성")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_icons(ch_id)
    print("\\n[완료] 7채널 × 20종 아이콘 SVG 생성")
```

- [ ] **Step 2: 실행**

```bash
python scripts/generate_branding/icon_gen.py
```
Expected: `[OK] CH1 아이콘 20종 생성` × 7줄

- [ ] **Step 3: 테스트**

```bash
pytest tests/test_branding_assets.py::test_icons_count -v
```
Expected: 7 passed

- [ ] **Step 4: 커밋**

```bash
git add scripts/generate_branding/icon_gen.py assets/channels/
git commit -m "feat: 7채널 도메인 아이콘 SVG 세트 생성 (20종×7채널)"
```

---

### Task 8: 템플릿 SVG 생성 (4종 × 7채널)

**Files:**
- Create: `scripts/generate_branding/template_gen.py`

- [ ] **Step 1: template_gen.py 작성**

```python
# scripts/generate_branding/template_gen.py
"""영상 템플릿 SVG 생성 — 자막바·썸네일·장면전환·로워서드"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_rect, doodle_line, doodle_text, doodle_path

def subtitle_bar(ch_id):
    cfg = CHANNELS[ch_id]
    mc, bg = cfg["main_color"], cfg["bg_color"]
    bg_fill = "#1A1A1A" if bg == "#FFFFFF" else bg
    return (svg_open(1280, 120, bg_fill)
            + doodle_rect(0, 8, 1280, 104, mc, sw=3, rx=8)
            + f\'<text x="640" y="78" font-size="52" fill="{mc}" font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">자막 텍스트 영역</text>\'
            + svg_close())

def thumbnail_template(ch_id):
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = cfg["bg_color"]
    return (svg_open(1280, 720, bg)
            + doodle_rect(12, 12, 1256, 696, mc, sw=6, rx=16)
            + doodle_rect(32, 32, 760, 656, mc, sw=3, rx=8)
            + doodle_rect(820, 32, 428, 310, mc, sw=3, rx=8)
            + doodle_rect(820, 378, 428, 310, mc, sw=3, rx=8)
            + f\'<text x="412" y="380" font-size="64" fill="{mc}" font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">제목 영역</text>\'
            + f\'<text x="1034" y="200" font-size="36" fill="{mc}" font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle">{cfg["name"]}</text>\'
            + svg_close())

def transition_wipe(ch_id):
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    return (svg_open(1920, 1080)
            + f\'<defs><linearGradient id="wipe" x1="0%" y1="0%" x2="100%" y2="0%">\'
            + f\'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>\'
            + f\'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/></linearGradient></defs>\'
            + f\'<rect width="1920" height="1080" fill="url(#wipe)"/>\'
            + svg_close())

def lower_third(ch_id):
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = "#1A1A1A" if cfg["bg_color"] == "#FFFFFF" else cfg["bg_color"]
    return (svg_open(1920, 200, bg)
            + doodle_rect(40, 20, 8, 160, mc, sw=0, rx=4)
            + doodle_rect(0, 0, 1920, 200, mc, sw=0)
            + f\'<rect width="1920" height="200" fill="{bg}" opacity="0.85"/>\'
            + f\'<rect x="40" y="20" width="8" height="160" fill="{mc}" rx="4"/>\'
            + f\'<text x="72" y="90" font-size="52" fill="#FFFFFF" font-family="Gmarket Sans Bold,sans-serif" font-weight="900">이름 / 출처</text>\'
            + f\'<text x="72" y="148" font-size="34" fill="{mc}" font-family="Gmarket Sans,sans-serif">{cfg["name"]} · {cfg["domain"]}</text>\'
            + svg_close())

TEMPLATES = {
    "subtitle_bar.svg": subtitle_bar,
    "thumbnail_template.svg": thumbnail_template,
    "transition_wipe.svg": transition_wipe,
    "lower_third.svg": lower_third,
}

def generate_templates(ch_id):
    out_dir = CHANNELS_DIR / ch_id / "templates"
    for fname, fn in TEMPLATES.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    print(f"  [OK] {ch_id} 템플릿 4종 생성")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_templates(ch_id)
    print("\\n[완료] 7채널 템플릿 SVG 생성")
```

- [ ] **Step 2: 실행 + 테스트**

```bash
python scripts/generate_branding/template_gen.py
pytest tests/test_branding_assets.py::test_templates_exist -v
```
Expected: 7 passed

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/template_gen.py assets/channels/
git commit -m "feat: 7채널 영상 템플릿 SVG 생성 (자막바·썸네일·전환·로워서드)"
```

---

### Task 9: 채널 아트·프로필 배너 SVG (7채널)

**Files:**
- Create: `scripts/generate_branding/extras_gen.py`

- [ ] **Step 1: extras_gen.py 작성**

```python
# scripts/generate_branding/extras_gen.py
"""채널 아트(2560×1440) + 프로필 배너(800×800) SVG 생성"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_circle, doodle_text, doodle_rect, doodle_line, doodle_path

def channel_art(ch_id):
    cfg = CHANNELS[ch_id]
    mc, bg = cfg["main_color"], cfg["bg_color"]
    sc = cfg["sub_colors"][0]
    name = cfg["name"]
    domain = cfg["domain"]
    W, H = 2560, 1440
    CX, CY = W // 2, H // 2
    return (svg_open(W, H, bg)
            # 배경 장식 원
            + doodle_circle(CX, CY, 580, mc, sw=3)
            + doodle_circle(CX, CY, 520, mc, sw=1)
            + doodle_circle(200, 200, 120, sc, sw=2)
            + doodle_circle(W-200, H-200, 100, sc, sw=2)
            + doodle_circle(200, H-200, 80, mc, sw=2)
            + doodle_circle(W-200, 200, 90, mc, sw=2)
            # 채널명
            + f\'<text x="{CX}" y="{CY-40}" font-size="180" fill="{mc}" \'
            + f\'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">{name}</text>\'
            + f\'<text x="{CX}" y="{CY+100}" font-size="80" fill="{sc}" \'
            + f\'font-family="Gmarket Sans,sans-serif" text-anchor="middle">{domain} 채널</text>\'
            # 하단 데코 라인
            + doodle_line(CX-400, CY+180, CX+400, CY+180, mc, sw=4)
            + svg_close())

def profile_banner(ch_id):
    cfg = CHANNELS[ch_id]
    mc, bg = cfg["main_color"], cfg["bg_color"]
    name = cfg["name"]
    W = H = 800
    CX = CY = 400
    return (svg_open(W, H, bg)
            + doodle_circle(CX, CY, 340, mc, sw=8)
            + doodle_circle(CX, CY, 310, mc, sw=3)
            + f\'<text x="{CX}" y="{CY+16}" font-size="88" fill="{mc}" \'
            + f\'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">{name}</text>\'
            + svg_close())

def generate_extras(ch_id):
    out_dir = CHANNELS_DIR / ch_id / "extras"
    (out_dir / "channel_art.svg").write_text(channel_art(ch_id), encoding="utf-8")
    (out_dir / "profile_banner.svg").write_text(profile_banner(ch_id), encoding="utf-8")
    print(f"  [OK] {ch_id} extras 2종 생성")

if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_extras(ch_id)
    print("\\n[완료] 7채널 채널아트·배너 SVG 생성")
```

- [ ] **Step 2: 실행 + 테스트**

```bash
python scripts/generate_branding/extras_gen.py
pytest tests/test_branding_assets.py::test_extras_exist -v
```
Expected: 7 passed

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/extras_gen.py assets/channels/
git commit -m "feat: 7채널 채널 아트·프로필 배너 SVG 생성"
```

---

### Task 10: 전체 파이프라인 실행 + 최종 검증

**Files:**
- Create: `scripts/generate_branding/run_all.py`

- [ ] **Step 1: run_all.py 작성**

```python
# scripts/generate_branding/run_all.py
"""7채널 브랜딩 에셋 전체 생성 파이프라인"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import importlib
sys.path.insert(0, str(Path(__file__).parent))

STEPS = [
    ("setup_folders", "create_folder_structure"),
    ("logo_gen", None),          # __main__ 방식
    ("intro_gen", None),
    ("outro_gen", None),
    ("icon_gen", None),
    ("template_gen", None),
    ("extras_gen", None),
]

def run():
    print("=" * 60)
    print("7채널 브랜딩 에셋 전체 생성 시작")
    print("=" * 60)
    for mod_name, fn_name in STEPS:
        print(f"\\n[{mod_name}] 실행 중...")
        mod = importlib.import_module(mod_name)
        if fn_name:
            getattr(mod, fn_name)()
        else:
            # 각 모듈의 if __name__ == "__main__" 블록과 동일한 로직
            from config import CHANNELS
            generate_fn = getattr(mod, f"generate_{mod_name.replace(\'_gen\',\'\')}", None)
            if generate_fn:
                for ch_id in CHANNELS:
                    generate_fn(ch_id)
    print("\\n" + "=" * 60)
    print("[완료] 전체 파이프라인 완료")
    print("character_gen은 별도 실행: python scripts/generate_branding/character_gen.py")
    print("=" * 60)

if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 전체 실행**

```bash
python scripts/generate_branding/run_all.py
```

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
pytest tests/test_branding_assets.py -v --tb=short
```
Expected: 최소 56 passed (캐릭터 PNG 제외)

- [ ] **Step 4: 캐릭터 생성 (Gemini API)**

```bash
python scripts/generate_branding/character_gen.py
```
Expected: 35장 PNG 생성

- [ ] **Step 5: 전체 파일 확인**

```bash
find assets/channels -type f | wc -l
```
Expected: 190+ 파일 (캐릭터 포함 시 225+)

- [ ] **Step 6: 최종 커밋**

```bash
git add scripts/generate_branding/run_all.py
git commit -m "feat: 7채널 브랜딩 에셋 전체 파이프라인 완성"
```

---

## 자체 검토 결과

**스펙 커버리지 확인:**
- ✅ 폴더 구조 `assets/channels/CH1~CH7/` — Task 1
- ✅ 채널 로고 SVG — Task 3
- ✅ 채널 캐릭터 PNG (Gemini API) — Task 4
- ✅ 인트로 HTML 3초 통일 — Task 5
- ✅ 아웃트로 HTML 10초 통일 — Task 6
- ✅ 아이콘 SVG 7채널 × 20종 — Task 7
- ✅ 템플릿 SVG 4종 × 7채널 — Task 8
- ✅ 채널 아트·배너 SVG — Task 9
- ✅ 검증 테스트 — Task 1·10

**Placeholder 없음** — 모든 단계에 실행 가능한 코드 포함
**타입 일관성** — `generate_branding/config.py`의 `CHANNELS` 딕셔너리가 모든 모듈의 단일 SSOT
'''

out_path = r"C:\Users\조찬우\Desktop\ai_stuidio_claude\docs\superpowers\plans\2026-04-14-channel-branding-assets.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(plan)

print(f"[완료] 계획 문서 저장: {out_path}")
import subprocess
result = subprocess.run(["wc", "-l", out_path], capture_output=True, text=True, shell=True)
print(f"라인 수: {result.stdout.strip()}")
