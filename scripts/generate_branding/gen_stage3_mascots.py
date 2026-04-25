"""3단계: 마스코트 40장 × 7채널 Gemini 생성.

사용법:
    python scripts/generate_branding/gen_stage3_mascots.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import (
    generate_best_of_n_multi_reference,
    _make_client,
)
from scripts.generate_branding.config import CHANNEL_COLOR_GUIDE, MASCOT_COSTUME

BASE_PLAIN = Path("assets/shared/base_plain.png")

# ─── 채널별 마스코트 테마 ─────────────────────────────────────────────────────
CHANNEL_THEMES = {
    "CH1": {
        "theme": "economics and money — balance scales, gold coins, currency symbols ($,€,¥,₩), stock charts, briefcase",
        "accessories": [
            "holding a large gold coin",
            "holding a mini stock chart graph",
            "holding a briefcase with money symbols",
            "holding balance scales",
            "holding a stack of bills",
            "with coins scattered around feet",
            "holding a calculator",
            "holding a bar graph",
            "wearing a tie with $ pattern",
            "holding a golden trophy",
        ],
    },
    "CH2": {
        "theme": "science — lab flask, atom symbol, DNA helix, microscope, test tubes, equations",
        "accessories": [
            "holding a glowing flask",
            "holding an atom model",
            "holding a test tube",
            "wearing safety goggles on forehead",
            "holding a clipboard with equations",
            "with DNA helix floating beside",
            "holding a magnifying glass",
            "holding a rocket",
            "with bubbles around",
            "holding a lightbulb",
        ],
    },
    "CH3": {
        "theme": "real estate — house model, key, location pin, blueprint, city building",
        "accessories": [
            "holding a miniature house",
            "holding a large key",
            "holding a location pin",
            "holding a blueprint roll",
            "holding a sold sign",
            "with tiny buildings around",
            "holding a contract document",
            "holding a hammer",
            "wearing a hard hat",
            "holding city building model",
        ],
    },
    "CH4": {
        "theme": "psychology — brain, thought bubble, mirror, spiral, emotions, mind symbols",
        "accessories": [
            "holding a glowing brain",
            "with large thought bubble above",
            "holding a hand mirror",
            "with spiral pattern background",
            "holding an open book on psychology",
            "with emotion symbols floating",
            "holding a heart",
            "with question marks around head",
            "holding a compass (metaphorical)",
            "with stars and moon decoration",
        ],
    },
    "CH5": {
        "theme": "mystery — question mark, magnifying glass, keyhole, shadow, clue cards",
        "accessories": [
            "holding a large question mark",
            "holding a magnifying glass",
            "peering through a keyhole shape",
            "holding a clue card",
            "with shadow silhouette effect",
            "holding an old key",
            "with exclamation marks around",
            "holding a mystery box",
            "with fog/mist around feet",
            "holding a flashlight",
        ],
    },
    "CH6": {
        "theme": "history — scroll, hourglass, ancient map, quill pen, crown, artifacts",
        "accessories": [
            "holding an ancient scroll",
            "holding an hourglass",
            "holding a quill pen",
            "holding an old map",
            "wearing a small crown",
            "holding a lantern",
            "holding ancient coins",
            "with archaeological artifacts",
            "holding a compass",
            "with feather plume hat",
        ],
    },
    "CH7": {
        "theme": "war history — sword, shield, battle flag, medal, strategy map, helmet",
        "accessories": [
            "holding a small sword",
            "holding a shield",
            "holding a battle flag",
            "wearing a medal",
            "holding a strategy map",
            "saluting pose",
            "holding binoculars",
            "with military star badge",
            "holding a compass",
            "holding a horn/bugle",
        ],
    },
}

# ─── 표정 변형 (4종 반복) ────────────────────────────────────────────────────
EXPRESSIONS = [
    "friendly smile, looking forward",
    "excited happy expression, slight open mouth",
    "confident determined expression",
    "curious tilted head expression",
]

# ─── 포즈 변형 (4종 반복) ────────────────────────────────────────────────────
POSES = [
    "standing straight, front-facing",
    "slight lean to one side, casual pose",
    "one arm raised slightly",
    "both arms slightly out, welcoming pose",
]


def build_prompt(ch_id: str, variant_idx: int) -> str:
    info = CHANNEL_THEMES[ch_id]
    costume = MASCOT_COSTUME[ch_id]
    color_guide = CHANNEL_COLOR_GUIDE[ch_id]
    accessories = info["accessories"]
    theme = info["theme"]

    acc = accessories[variant_idx % len(accessories)]
    expr = EXPRESSIONS[variant_idx % len(EXPRESSIONS)]
    pose = POSES[variant_idx % len(POSES)]

    return (
        "Create a cute chibi mascot character based on these TWO reference images. "

        "From the FIRST reference (character): "
        "inherit the exact body proportions (3.5-head chibi ratio), "
        "bald round head, chubby round face with rosy cheeks, "
        "simple 2px black doodle outline style, flat colors, no gradients. "

        "From the SECOND reference (logo): "
        f"inherit the color palette and {theme} theme elements. "
        f"{color_guide} "

        f"Costume: {costume}. "
        f"Accessory/prop: {acc}. "
        f"Expression: {expr}. "
        f"Pose: {pose}. "

        "Style rules: pure white background, full body visible head to feet, "
        "same kawaii doodle illustration style as the first reference, "
        "flat coloring only, no text, no logo, character only. "
        "Make each variant creative and slightly different."
    )


def main():
    client = _make_client()

    print("=== 3단계: 마스코트 생성 시작 ===\n")

    for ch_id in CHANNEL_THEMES:
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/mascot")
        output_dir.mkdir(parents=True, exist_ok=True)

        if not BASE_PLAIN.exists():
            print(f"[{ch_id}] base_plain.png 없음 — 스킵")
            continue
        if not logo_path.exists():
            print(f"[{ch_id}] 로고 없음 — 스킵")
            continue

        refs = [BASE_PLAIN, logo_path]
        print(f"[{ch_id}] 마스코트 40장 생성 중...")
        saved_count = 0

        for i in range(1, 41):
            prompt = build_prompt(ch_id, i - 1)
            output_path = output_dir / f"variant_{i}.png"

            from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference
            success = generate_with_multi_reference(refs, prompt, output_path, client=client)
            if success:
                saved_count += 1
                if i % 10 == 0:
                    print(f"  [{ch_id}] {i}/40장 완료...")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")

        print(f"[{ch_id}] 완료: {saved_count}/40장\n")

    print("=== 3단계 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/mascot/")


if __name__ == "__main__":
    main()
