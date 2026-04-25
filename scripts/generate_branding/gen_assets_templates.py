"""자막바·장면전환·로워서드·썸네일 템플릿 10장×7채널 — 스타일 레퍼런스 4장 + 로고.

사용법:
    python scripts/generate_branding/gen_assets_templates.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"
from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference, _make_client

STYLE_REFS = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

CHANNEL_THEMES = {
    "CH1": ("economics, money", "#F4C420", "#333333"),
    "CH2": ("science, experiments", "#00E5FF", "#1A1A2E"),
    "CH3": ("real estate, housing", "#E67E22", "#FFFFFF"),
    "CH4": ("psychology, mind", "#9B59B6", "#FFFFFF"),
    "CH5": ("mystery, enigma", "#1C2833", "#F0F0F0"),
    "CH6": ("history, ancient", "#A0522D", "#F5F0E0"),
    "CH7": ("war history, military", "#C0392B", "#FFFFFF"),
}

SUBTITLE_VARIATIONS = [
    "solid dark background bar with channel color left accent stripe",
    "channel color background bar with bold text area",
    "minimal design, only bottom border line in channel color",
    "rounded pill shape in channel color",
    "double border frame in channel color",
    "gradient fade from channel color to transparent",
    "doodle-decorated edges on both sides of the text area",
    "speech bubble / dialogue box shape",
    "bold thick border frame with corner doodle accents",
    "split two-tone bar, channel color left half and dark right half",
]

TRANSITION_VARIATIONS = [
    "smooth horizontal wipe from left in channel color doodle style",
    "radial ink blot expanding from center in channel color",
    "vertical split curtain effect in channel color",
    "diagonal sweep from top-left corner in channel color",
    "circular zoom burst from center with doodle elements",
    "paper fold effect with channel color and doodle texture",
    "scattered doodle icons filling the screen as transition",
    "horizontal stripe blinds effect in channel color",
    "starburst explosion pattern from center in channel color",
    "bottom-to-top wipe with doodle elements rising up",
]

LOWER_THIRD_VARIATIONS = [
    "clean horizontal bar with left accent line and name/title text area",
    "channel color background bar with white text zones",
    "minimal design with just a thin colored line and floating text",
    "box style with rounded corners and doodle border",
    "split design: channel color left block + dark right block",
    "transparent overlay bar with doodle frame decoration",
    "stacked name and title with channel color highlight",
    "wide full-width bar with channel name watermark on right",
    "bold impact style with thick colored borders top and bottom",
    "doodle-decorated lower third with small icon accent",
]

THUMBNAIL_VARIATIONS = [
    "standard layout: large left area for character, right area for title text",
    "impact style: full dark background with large centered title area",
    "comparison layout: left vs right split with channel color divider",
    "question mark emphasis: large ? watermark, title box on right",
    "urgent/breaking style: red top banner, main content below",
    "minimal clean: white background, channel color frame border",
    "doodle frame: hand-drawn border with channel theme icons as decoration",
    "gradient background from channel color to white, title centered",
    "channel mascot placeholder left, three key points listed right",
    "bold number/stat emphasis: large number left, explanation right",
]


def gen_type(ch_id: str, asset_type: str, variations: list,
             theme: str, main_color: str, bg_color: str,
             refs: list, client, output_dir: Path):

    type_prompts = {
        "subtitle_bar": (
            "The first four references show flat doodle illustration style. "
            "The LAST reference is the channel logo — match its exact colors and theme. "
            f"Create a SUBTITLE BAR for a {theme} YouTube channel. "
            "Wide horizontal format (approx 1280×120px ratio). "
            f"Channel main color: {main_color}. Background: {bg_color}. "
            "CRITICAL: Same flat doodle style as references — simple outlines, flat colors. "
            "Include small doodle icons from the channel theme as accents. "
            "Clean central text area. No actual text. "
            "Style: {variation}."
        ),
        "transition": (
            "The first four references show flat doodle illustration style. "
            "The LAST reference is the channel logo — match its exact colors and theme. "
            f"Create a SCENE TRANSITION FRAME for a {theme} YouTube channel. "
            "Full screen 16:9 format. "
            f"Channel main color: {main_color}. "
            "CRITICAL: Same flat doodle style as references — simple outlines, flat colors. "
            "Incorporate doodle icons from the channel theme into the transition design. "
            "Style: {variation}."
        ),
        "lower_third": (
            "The first four references show flat doodle illustration style. "
            "The LAST reference is the channel logo — match its exact colors and theme. "
            f"Create a LOWER THIRD / NAME PLATE for a {theme} YouTube channel. "
            "Wide horizontal format, positioned at bottom of screen. "
            f"Channel main color: {main_color}. Background: {bg_color}. "
            "CRITICAL: Same flat doodle style as references — simple outlines, flat colors. "
            "Small doodle accents from channel theme. Text zones for name and title. "
            "Style: {variation}."
        ),
        "thumbnail": (
            "The first four references show flat doodle illustration style. "
            "The LAST reference is the channel logo — match its exact colors and theme. "
            f"Create a THUMBNAIL TEMPLATE FRAME for a {theme} YouTube channel. "
            "16:9 format (1280×720). "
            f"Channel main color: {main_color}. Background: {bg_color}. "
            "CRITICAL: Same flat doodle style as references — simple outlines, flat colors. "
            "Doodle border decoration and channel theme icons as frame elements. "
            "Clear zones for title text and character/image. No actual text. "
            "Style: {variation}."
        ),
    }

    base = type_prompts[asset_type]
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = 0

    for i, variation in enumerate(variations, 1):
        prompt = base.format(variation=variation)
        ok = generate_with_multi_reference(refs, prompt, output_dir / f"variant_{i}.png", client=client)
        if ok:
            saved += 1
        else:
            print(f"  [{ch_id}/{asset_type}] variant_{i} [FAIL]")

    print(f"  [{ch_id}] {asset_type}: {saved}/10장")
    return saved


def main():
    client = _make_client()
    print("=== 템플릿 생성 시작 (자막바·장면전환·로워서드·썸네일) ===\n")

    asset_types = [
        ("subtitle_bar",  SUBTITLE_VARIATIONS),
        ("transition",    TRANSITION_VARIATIONS),
        ("lower_third",   LOWER_THIRD_VARIATIONS),
        ("thumbnail",     THUMBNAIL_VARIATIONS),
    ]

    for ch_id, (theme, main_color, bg_color) in CHANNEL_THEMES.items():
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        refs = STYLE_REFS + [logo_path]
        print(f"[{ch_id}] 템플릿 4종 × 10장 생성 중...")

        for asset_type, variations in asset_types:
            output_dir = Path(f"assets/channels/{ch_id}/_candidates/{asset_type}")
            gen_type(ch_id, asset_type, variations, theme, main_color, bg_color, refs, client, output_dir)

        print(f"[{ch_id}] 완료\n")

    print("=== 템플릿 생성 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/{subtitle_bar|transition|lower_third|thumbnail}/")


if __name__ == "__main__":
    main()
