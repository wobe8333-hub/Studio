"""
캐릭터 매니저 — 채널별 캐릭터 에셋/LoRA 관리.

Phase 5 추가:
  채널별 LoRA 경로 매핑, 캐릭터 프롬프트 템플릿, 일관성 시드 관리.
Phase 9 추가:
  assets/channels/{CH}/characters/ PNG 에셋 직접 로드 함수 추가.
  섹션 번호 기반 표정 자동 선택.
"""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from src.core.config import KAS_ROOT

# 표정 → 파일명 매핑 (assets/channels/{CH}/characters/ 기준)
# 단일 포즈 확인된 4개만 사용:
#   character_surprised.png — 팔 벌린 깜짝
#   character_victory.png   — 엄지 척/윙크
#   character_run.png       — 달리기 (활동적)
#   character_sit.png       — 앉은 자세 (차분)
CHARACTER_EXPRESSION_FILES: Dict[str, str] = {
    "happy":      "character_victory",    # 기쁨 → victory
    "surprised":  "character_surprised",  # 충격 ✅
    "thinking":   "character_sit",        # 사고 → sit (차분)
    "sad":        "character_sit",        # 슬픔 → sit (차분)
    "excited":    "character_run",        # 흥분 → run (활동적)
    "curious":    "character_sit",        # 호기심 → sit (사색)
    "explaining": "character_run",        # 설명 → run (역동적)
    "victory":    "character_victory",    # 승리 ✅
    "warn":       "character_surprised",  # 경고 → surprised (강조)
    "run":        "character_run",        # 달리기 ✅
    "sit":        "character_sit",        # 앉기 ✅
    "default":    "character_surprised",  # 기본 → surprised
}

# 섹션 인덱스 → 표정 순환 패턴 (0=훅, last=마무리)
# 검증된 단일 포즈 4종 교대 사용
_SECTION_EXPRESSION_CYCLE = [
    "surprised",  # 0: 훅 — 강렬한 첫인상
    "run",        # 1: 본론1 — 활발하게
    "sit",        # 2: 본론2 — 차분하게
    "run",        # 3: 본론3 — 역동적으로
    "sit",        # 4: 심화 — 사색
]


def get_character_asset_path(channel_id: str, expression: str = "default") -> Optional[Path]:
    """
    assets/channels/{channel_id}/characters/ 에서 표정 PNG 경로 반환.
    파일 없으면 default → explain → happy 순으로 폴백.
    """
    char_dir = KAS_ROOT / "assets" / "channels" / channel_id / "characters"
    filename = CHARACTER_EXPRESSION_FILES.get(expression, "character_default")
    path = char_dir / f"{filename}.png"
    if path.exists():
        return path
    # 폴백 순서 (검증된 단일 포즈만)
    for fallback in ["character_surprised", "character_run", "character_sit", "character_victory"]:
        fp = char_dir / f"{fallback}.png"
        if fp.exists():
            logger.debug(f"[Character] {expression} 없음 → {fallback} 사용")
            return fp
    logger.warning(f"[Character] {channel_id} 캐릭터 에셋 없음: {char_dir}")
    return None


def select_expression_for_section(section_id: int, total_sections: int) -> str:
    """섹션 번호 기반 표정 선택. 마지막 섹션은 항상 victory."""
    if section_id == 0:
        return "surprised"
    if section_id >= total_sections - 1:
        return "victory"
    return _SECTION_EXPRESSION_CYCLE[section_id % len(_SECTION_EXPRESSION_CYCLE)]

# 채널별 캐릭터 기본 설정
CHARACTER_PROFILES: Dict[str, Dict] = {
    "CH1": {
        "name": "머니그래픽",
        "gender": "neutral",
        "style": "doodle_simple",
        # 브랜딩 SSOT: scripts/generate_branding/config.py CH1 character_prompts와 동기화
        # 기준 스타일 — 두들 왕관 캐릭터, 흰 배경, 심플 아웃라인
        "base_prompt": (
            "cute doodle style character with crown W on head, simple black outlines, "
            "white background, Korean YouTube economics channel, consistent character design, "
            "no text, no labels, isolated character"
        ),
        "lora_name": "ch1_moneygraphic",
        "seed": 42001,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic, complex background, labels, text, watermark",
    },
    "CH2": {
        "name": "가설낙서",
        "gender": "neutral",
        "style": "cute_scientist",
        "base_prompt": "cute doodle style scientist character, wearing lab coat, curious expression, magnifying glass, neon cyan color scheme, dark background, simple outlines, Korean science YouTube",
        "lora_name": "ch2_science_character",
        "seed": 42002,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH3": {
        "name": "홈팔레트",
        "gender": "neutral",
        "style": "cute_simple",
        "base_prompt": "cute doodle style character holding house model, explaining real estate, Korean YouTube, white background, orange color scheme, simple outlines",
        "lora_name": "ch3_realestate_character",
        "seed": 42003,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH4": {
        "name": "오묘한심리",
        "gender": "neutral",
        "style": "cute_dreamy",
        "base_prompt": "cute doodle style character with brain symbol, exploring psychology theories, purple color scheme, white background, Korean psychology YouTube, simple outlines",
        "lora_name": "ch4_psychology_character",
        "seed": 42004,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH5": {
        "name": "검은물음표",
        "gender": "neutral",
        "style": "cute_mysterious",
        "base_prompt": "cute doodle style mystery character with question mark, curious suspicious expression, dark color scheme, white background, Korean mystery YouTube, simple outlines",
        "lora_name": "ch5_mystery_character",
        "seed": 42005,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH6": {
        "name": "오래된두루마리",
        "gender": "neutral",
        "style": "cute_wise",
        "base_prompt": "cute doodle style historian character with scroll, exploring ancient history, parchment brown color scheme, aged paper background, Korean history YouTube, simple outlines",
        "lora_name": "ch6_history_character",
        "seed": 42006,
        "negative_prompt": "ugly, deformed, nsfw, violence, realistic",
    },
    "CH7": {
        "name": "워메이징",
        "gender": "male",
        "style": "cute_brave",
        "base_prompt": "cute doodle style military general character, victory pose with raised fist, red military color scheme, white background, Korean war history YouTube, simple outlines",
        "lora_name": "ch7_warhistory_character",
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
