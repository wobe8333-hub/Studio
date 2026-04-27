"""7채널 심플 배너 생성 — 채널 컬러 도화지 + 채널명 + 소제목 + 채널 특색 액센트.

컨셉: 채널 메인 컬러 도화지에 낙서하는 스타일.
구성: 채널명(중앙) + 소제목 + 채널 테마를 암시하는 아주 작은 손그림 액센트.

사용법:
    python scripts/generate_branding/gen_banner_simple.py
    python scripts/generate_branding/gen_banner_simple.py --channels CH1 CH2
    python scripts/generate_branding/gen_banner_simple.py --count 20

저장 위치: assets/channels/CH{N}/_candidates/banner_simple/variant_{N}.png
"""
import sys
import io
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import generate_image, _make_client

# ─── 채널 정보 + 테마 액센트 ──────────────────────────────────────────────────
CHANNEL_INFO = {
    "CH1": {
        "name": "머니그래픽",
        "subtitle": "돈의 언어를 배울 시간",
        "bg_color": "#F4C420",
        "bg_desc": "golden yellow",
        "text_color": "#1A1A2E",
        "text_desc": "dark navy",
        "theme_accent": "2~3 tiny hand-drawn ₩ coin symbols or a small minimalist rising graph line",
        "theme_desc": "economics and money channel",
    },
    "CH2": {
        "name": "가설낙서",
        "subtitle": "왜라고 물어본 적 있나요",
        "bg_color": "#00E5FF",
        "bg_desc": "bright cyan",
        "text_color": "#1A1A2E",
        "text_desc": "dark navy",
        "theme_accent": "2~3 tiny hand-drawn atom rings or a small flask/beaker silhouette",
        "theme_desc": "science and hypothesis channel",
    },
    "CH3": {
        "name": "홈팔레트",
        "subtitle": "당신의 다음 집을 위한 채널",
        "bg_color": "#E67E22",
        "bg_desc": "warm orange",
        "text_color": "#FFFFFF",
        "text_desc": "white",
        "theme_accent": "2~3 tiny hand-drawn house outlines or a small key silhouette",
        "theme_desc": "real estate channel",
    },
    "CH4": {
        "name": "오묘한심리",
        "subtitle": "행동 뒤에 숨겨진 이유들",
        "bg_color": "#9B59B6",
        "bg_desc": "purple",
        "text_color": "#FFFFFF",
        "text_desc": "white",
        "theme_accent": "2~3 tiny hand-drawn spiral or thought bubble doodles",
        "theme_desc": "psychology channel",
    },
    "CH5": {
        "name": "검은물음표",
        "subtitle": "믿을 것인가, 의심할 것인가",
        "bg_color": "#1C2833",
        "bg_desc": "dark charcoal",
        "text_color": "#FFFFFF",
        "text_desc": "white",
        "theme_accent": "2~3 tiny hand-drawn question marks or a small magnifying glass silhouette",
        "theme_desc": "mystery channel",
    },
    "CH6": {
        "name": "오래된두루마리",
        "subtitle": "우리가 배우지 못한 역사",
        "bg_color": "#A0522D",
        "bg_desc": "warm brown",
        "text_color": "#F5F0E0",
        "text_desc": "cream beige",
        "theme_accent": "a small hand-drawn scroll edge or quill pen silhouette, or tiny hourglass",
        "theme_desc": "history channel",
    },
    "CH7": {
        "name": "워메이징",
        "subtitle": "이긴 쪽도 진 쪽도 몰랐던 진실",
        "bg_color": "#3D4A2E",
        "bg_desc": "ranger green",
        "text_color": "#F5F0E0",
        "text_desc": "cream beige",
        "theme_accent": "a tiny hand-drawn compass rose or star insignia, or crossed swords silhouette",
        "theme_desc": "war history channel",
    },
}

# ─── 변형 20가지 — 텍스트 스타일 × 액센트 배치 조합 ─────────────────────────
VARIATIONS = [
    "channel name in bold marker style; accent elements placed symmetrically above the channel name",
    "channel name slightly tilted; accent elements on the left side of the text block",
    "channel name with double underline doodle; accent elements on the right side of text",
    "channel name in brushstroke style; accent elements scattered above and below text",
    "channel name in rough hand-drawn rectangle frame; accent elements outside the frame corners",
    "channel name in clean bold lettering; accent elements in a small cluster below the subtitle",
    "channel name with wavy underline; accent element centered above the channel name",
    "channel name in chunky outline style; accent elements flanking both sides of the subtitle",
    "channel name with hand-drawn shadow; accent element placed top-right of text block",
    "channel name in casual doodle lettering; accent elements scattered loosely around text",
    "channel name with zigzag underline; accent element placed bottom-left of text block",
    "channel name in stacked layout; accent elements as a small row above the name",
    "channel name with corner bracket doodles; accent element centered below the subtitle",
    "channel name in retro hand-lettered style; accent elements on both sides of channel name",
    "channel name with uneven baseline; accent element placed to the far right of text",
    "channel name in bold print with hand-drawn feel; accent elements in diagonal arrangement",
    "channel name with minimal dot decorations; accent element as a single centered icon above",
    "channel name with thin elegant strokes; accent elements as a small horizontal row below",
    "channel name in compact centered block; accent elements at four corners of the text area",
    "channel name with small dash separators; accent element placed to the far left of text",
]

BASE_PROMPT = (
    "Create a YouTube channel art banner, exactly 2560 pixels wide × 1440 pixels tall (16:9). "
    "This is a {theme_desc}. "

    "BACKGROUND: The entire 2560×1440 canvas is filled with solid {bg_color} ({bg_desc}). "
    "Slight paper/sketchbook texture only. NO gradients — pure flat color canvas. "

    "TEXT — centered horizontally and vertically on the canvas: "
    "① Channel name '{name}' in Korean hand-drawn lettering, color {text_color} ({text_desc}). "
    "   TEXT HEIGHT: approximately 70 pixels tall (in the 2560×1440 image). "
    "   TEXT WIDTH: no wider than 380 pixels total. "
    "② Subtitle '{subtitle}' in Korean hand-drawn lettering, same color {text_color}. "
    "   TEXT HEIGHT: approximately 39 pixels tall. "
    "   Placed 17px below the channel name. "

    "CHANNEL ACCENT — this is what makes the channel unique: {theme_accent}. "
    "Draw 2~3 of these tiny accent elements near the text block (NOT overlapping the text). "
    "Each accent element: approximately 25~35 pixels in size. "
    "Color: same {text_color} ({text_desc}), hand-drawn doodle style, very light and delicate. "
    "The accent is a whisper of the channel theme — subtle, not dominant. "

    "COMPOSITION STYLE: {variation}. "

    "SIZE RULES: "
    "The entire text block (channel name + subtitle + accent elements combined) must stay "
    "within a 450×180 pixel area centered on the 2560×1440 canvas. "
    "Vast empty colored space must surround this center area on all sides. "

    "STRICT RULES: "
    "Korean characters only — NO English, NO romanization, NO Latin letters anywhere. "
    "The beauty is the large empty color canvas with a small, characterful center label."
)


def main(channels: list[str] | None = None, count: int = 20) -> None:
    client = _make_client()
    target_channels = channels or list(CHANNEL_INFO.keys())

    print(f"=== 심플 배너 생성 ({len(target_channels)}채널 × {count}장) ===\n")

    for ch_id in target_channels:
        info = CHANNEL_INFO[ch_id]
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/banner_simple")
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{ch_id}] '{info['name']}' — {info['bg_desc']} 배경, {count}장 생성 중...")
        saved = 0

        for i in range(1, count + 1):
            out_path = output_dir / f"variant_{i}.png"
            if out_path.exists():
                print(f"  [{ch_id}] variant_{i} [SKIP]")
                saved += 1
                continue

            variation = VARIATIONS[(i - 1) % len(VARIATIONS)]
            prompt = BASE_PROMPT.format(
                theme_desc=info["theme_desc"],
                bg_color=info["bg_color"],
                bg_desc=info["bg_desc"],
                text_color=info["text_color"],
                text_desc=info["text_desc"],
                name=info["name"],
                subtitle=info["subtitle"],
                theme_accent=info["theme_accent"],
                variation=variation,
            )

            ok = generate_image(prompt, out_path, client=client)
            if ok:
                saved += 1
                print(f"  [{ch_id}] variant_{i} [OK]")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")

        print(f"[{ch_id}] 완료: {saved}/{count}장\n")

    print("=== 생성 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/banner_simple/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="심플 배너 생성 — 채널 특색 액센트 포함")
    parser.add_argument(
        "--channels",
        nargs="+",
        choices=list(CHANNEL_INFO.keys()),
        help="특정 채널만 생성 (기본: 전체 7채널)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="채널당 생성 장수 (기본: 20)",
    )
    args = parser.parse_args()
    main(args.channels, args.count)
