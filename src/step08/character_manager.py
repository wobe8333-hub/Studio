"""
캐릭터 매니저 — 채널별 캐릭터 에셋/LoRA 관리.

Phase 5 추가:
  채널별 LoRA 경로 매핑, 캐릭터 프롬프트 템플릿, 일관성 시드 관리.
"""

from pathlib import Path
from typing import Dict, Optional
from loguru import logger

from src.core.config import KAS_ROOT

# 채널별 캐릭터 기본 설정
CHARACTER_PROFILES: Dict[str, Dict] = {
    "CH1": {
        "name": "경제요정 까미",
        "gender": "female",
        "style": "cute_simple",
        "base_prompt": "cute chibi female character, short bob hair, business casual outfit, big eyes, pastel colors",
        "lora_name": "ch1_economy_character",
        "seed": 42001,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH2": {
        "name": "집찾기 도리",
        "gender": "neutral",
        "style": "cute_simple",
        "base_prompt": "cute chibi character, casual outfit, hard hat accessory, friendly expression, warm colors",
        "lora_name": "ch2_realestate_character",
        "seed": 42002,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH3": {
        "name": "마음탐험가 루나",
        "gender": "female",
        "style": "cute_dreamy",
        "base_prompt": "cute chibi female character, long flowing hair, soft pastel dress, warm gentle expression, dreamy colors",
        "lora_name": "ch3_psychology_character",
        "seed": 42003,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH4": {
        "name": "미스터리 탐정 셜",
        "gender": "male",
        "style": "cute_mysterious",
        "base_prompt": "cute chibi detective character, magnifying glass, trench coat, curious expression, dark mysterious colors",
        "lora_name": "ch4_mystery_character",
        "seed": 42004,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH5": {
        "name": "역사특공대 마루",
        "gender": "male",
        "style": "cute_brave",
        "base_prompt": "cute chibi soldier character, historical uniform, brave expression, bold colors",
        "lora_name": "ch5_warhistory_character",
        "seed": 42005,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH6": {
        "name": "과학박사 스텔라",
        "gender": "female",
        "style": "cute_scientist",
        "base_prompt": "cute chibi female scientist character, lab coat, glasses, beaker accessory, curious excited expression, blue tech colors",
        "lora_name": "ch6_science_character",
        "seed": 42006,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH7": {
        "name": "역사학자 구루",
        "gender": "neutral",
        "style": "cute_wise",
        "base_prompt": "cute chibi scholar character, ancient scroll, wise gentle expression, earthy warm colors",
        "lora_name": "ch7_history_character",
        "seed": 42007,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
}

# 표정별 프롬프트 수식어
EXPRESSION_MODIFIERS: Dict[str, str] = {
    "happy":     "happy smiling expression, bright eyes",
    "surprised": "surprised wide eyes, open mouth",
    "thinking":  "thinking expression, finger on chin, tilted head",
    "sad":       "slightly sad gentle expression, downcast eyes",
    "excited":   "very excited expression, raised arms",
    "curious":   "curious expression, tilted head, raised eyebrow",
    "explaining": "explaining gesture, pointing finger, confident expression",
}

# 포즈별 프롬프트 수식어
POSE_MODIFIERS: Dict[str, str] = {
    "standing":  "standing upright, neutral pose",
    "pointing":  "pointing forward with finger",
    "explaining": "both hands gesturing, explaining pose",
    "sitting":   "sitting cross-legged",
    "running":   "dynamic running pose",
    "waving":    "waving hand, friendly pose",
}


def get_lora_path(channel_id: str) -> Optional[Path]:
    """채널별 LoRA .safetensors 경로 반환 (없으면 None)"""
    profile = CHARACTER_PROFILES.get(channel_id, {})
    lora_name = profile.get("lora_name", "")
    lora_dir = KAS_ROOT / "assets" / "lora"
    lora_path = lora_dir / f"{lora_name}.safetensors"
    if lora_path.exists():
        return lora_path
    logger.debug(f"[Character] LoRA 없음: {lora_path} — 기본 프롬프트 사용")
    return None


def build_character_prompt(
    channel_id: str,
    expression: str = "happy",
    pose: str = "standing",
    scene_context: str = "",
) -> Dict[str, str]:
    """
    캐릭터 이미지 생성용 프롬프트 빌드.

    Returns:
        {"positive": str, "negative": str, "seed": int}
    """
    profile = CHARACTER_PROFILES.get(channel_id, CHARACTER_PROFILES["CH1"])
    base = profile["base_prompt"]
    expr_mod = EXPRESSION_MODIFIERS.get(expression, "")
    pose_mod = POSE_MODIFIERS.get(pose, "")

    positive = ", ".join(filter(None, [
        base,
        expr_mod,
        pose_mod,
        scene_context,
        "masterpiece, best quality, high detail, anime style",
    ]))

    return {
        "positive": positive,
        "negative": profile.get("negative_prompt", "ugly, deformed, nsfw"),
        "seed": profile.get("seed", 42),
    }


def get_character_name(channel_id: str) -> str:
    """채널 캐릭터 이름 반환"""
    return CHARACTER_PROFILES.get(channel_id, {}).get("name", "캐릭터")
