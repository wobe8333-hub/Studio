"""7채널 심플 배너 생성 — 채널 컬러 도화지 + 채널명 + 소제목.

컨셉: 채널 메인 컬러 도화지에 낙서하는 스타일.
구성: 채널명(크게, 중앙) + 소제목(작게, 중앙) — 텍스트만, 아이콘 없음.
레퍼런스 없음: 단색 배경 + 텍스트 구조라 텍스트 프롬프트만으로 충분.

사용법:
    python scripts/generate_branding/gen_banner_simple.py
    python scripts/generate_branding/gen_banner_simple.py --channels CH1 CH2
    python scripts/generate_branding/gen_banner_simple.py --count 10

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

# ─── 채널 정보 ────────────────────────────────────────────────────────────────
CHANNEL_INFO = {
    "CH1": {
        "name": "머니그래픽",
        "subtitle": "돈의 언어를 배울 시간",
        "bg_color": "#F4C420",
        "bg_desc": "golden yellow",
        "text_color": "#1A1A2E",
        "text_desc": "dark navy",
    },
    "CH2": {
        "name": "가설낙서",
        "subtitle": "왜라고 물어본 적 있나요",
        "bg_color": "#00E5FF",
        "bg_desc": "bright cyan",
        "text_color": "#1A1A2E",
        "text_desc": "dark navy",
    },
    "CH3": {
        "name": "홈팔레트",
        "subtitle": "당신의 다음 집을 위한 채널",
        "bg_color": "#E67E22",
        "bg_desc": "warm orange",
        "text_color": "#FFFFFF",
        "text_desc": "white",
    },
    "CH4": {
        "name": "오묘한심리",
        "subtitle": "행동 뒤에 숨겨진 이유들",
        "bg_color": "#9B59B6",
        "bg_desc": "purple",
        "text_color": "#FFFFFF",
        "text_desc": "white",
    },
    "CH5": {
        "name": "검은물음표",
        "subtitle": "믿을 것인가, 의심할 것인가",
        "bg_color": "#1C2833",
        "bg_desc": "dark charcoal",
        "text_color": "#FFFFFF",
        "text_desc": "white",
    },
    "CH6": {
        "name": "오래된두루마리",
        "subtitle": "우리가 배우지 못한 역사",
        "bg_color": "#A0522D",
        "bg_desc": "warm brown",
        "text_color": "#F5F0E0",
        "text_desc": "cream beige",
    },
    "CH7": {
        "name": "워메이징",
        "subtitle": "이긴 쪽도 진 쪽도 몰랐던 진실",
        "bg_color": "#3D4A2E",
        "bg_desc": "ranger green",
        "text_color": "#F5F0E0",
        "text_desc": "cream beige",
    },
}

# ─── 컴포지션 변형 20가지 (텍스트 스타일·장식 변화) ──────────────────────────
VARIATIONS = [
    "channel name with thick bold marker strokes, subtitle in thin casual handwriting",
    "channel name in slightly tilted hand-lettered style, subtitle perfectly horizontal",
    "channel name with double underline doodle beneath it, subtitle below",
    "channel name in large brushstroke style, subtitle with small arrow doodle pointing to it",
    "channel name enclosed in a rough hand-drawn rectangle frame, subtitle below",
    "channel name with star doodles on each side, subtitle in neat handwriting",
    "channel name in all-caps bold doodle font, subtitle in lowercase cursive",
    "channel name with wavy underline, subtitle with small dot decorations",
    "channel name in chunky bubble letters outline style, subtitle clean",
    "channel name with hand-drawn shadow effect, subtitle in lighter weight",
    "channel name in casual graffiti-inspired doodle lettering, subtitle minimal",
    "channel name with small heart doodle accent, subtitle in italic style",
    "channel name in stacked two-line layout if long, subtitle single line below",
    "channel name with zigzag underline doodle, subtitle with dash separators",
    "channel name in retro hand-lettered style, subtitle in modern minimal",
    "channel name with corner bracket doodles, subtitle centered below",
    "channel name in playful uneven baseline lettering, subtitle aligned center",
    "channel name with small lightning bolt doodle accent, subtitle below",
    "channel name surrounded by minimal dot grid pattern, subtitle below",
    "channel name in clean bold print style with hand-drawn feel, subtitle in script",
]

BASE_PROMPT = (
    "Create a YouTube channel art banner (2560×1440, 16:9). "

    "BACKGROUND: Fill the entire banner with solid {bg_color} ({bg_desc}) — "
    "like a sheet of colored construction paper or sketchbook page. "
    "Add very subtle paper texture (slight grain, natural imperfections) for hand-crafted feel. "
    "NO gradients. NO patterns. NO icons. NO decorative elements anywhere in the background. "
    "The background must be clean and flat — only the colored paper. "

    "CENTER CONTENT — place everything at the absolute center of the banner "
    "(center 48% width × center 24% height — the YouTube mobile safe zone): "
    "① Korean channel name '{name}' in LARGE bold hand-drawn doodle lettering, color {text_color} ({text_desc}). "
    "   Natural hand-written feel with slight wobble — like drawn with a thick marker on paper. "
    "② Korean subtitle '{subtitle}' in smaller hand-drawn text, same color {text_color}. "
    "   Placed just below the channel name, clearly readable. "

    "COMPOSITION STYLE: {variation}. "

    "CRITICAL RULES: "
    "Both texts centered horizontally and vertically in the banner. "
    "NO text outside the center area. "
    "NO background icons or decorations. "
    "LANGUAGE: Write ONLY in Korean (한국어). "
    "NO English letters, NO romanization, NO Latin alphabet anywhere in the image. "
    "The overall aesthetic: someone casually hand-lettering on a colored paper — "
    "minimal, authentic, clean, and confident."
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
                bg_color=info["bg_color"],
                bg_desc=info["bg_desc"],
                text_color=info["text_color"],
                text_desc=info["text_desc"],
                name=info["name"],
                subtitle=info["subtitle"],
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
    parser = argparse.ArgumentParser(description="심플 배너 생성 — 채널 컬러 도화지 + 채널명 + 소제목")
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
