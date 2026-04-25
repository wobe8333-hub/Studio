"""에피소드별 스토리 캐릭터 생성 어댑터.

베이스 플레인 캐릭터(민머리 3.5등신)에 스토리 의상을 입혀
에피소드마다 다양한 인물을 생성한다. 바디/얼굴은 항상 동일.
"""
import base64
import hashlib
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from loguru import logger

ROOT            = Path(__file__).parent.parent.parent
BASE_IMAGE_PATH = ROOT / "assets" / "shared" / "base_plain.png"
CHANNELS_ROOT   = ROOT / "assets" / "channels"
MODEL           = "gemini-2.5-flash-image"

# 채널별 색상 톤 가이드 (의상에 미묘하게 반영)
CHANNEL_COLOR_GUIDE: dict[str, str] = {
    "CH1": "Prefer gold (#E8A44C) and navy (#1A237E) tones in the costume design.",
    "CH2": "Prefer teal (#00CED1) and white tones in the costume design.",
    "CH3": "Prefer orange (#FF8C42) and sage green (#52B788) tones in the costume design.",
    "CH4": "Prefer lavender (#9B59B6) and soft coral tones in the costume design.",
    "CH5": "Prefer dark navy (#1F3A5F) and purple tones in the costume design.",
    "CH6": "Prefer golden brown (#8B6914) and burgundy tones in the costume design.",
    "CH7": "Prefer forest green (#2E5B3C) and warm amber tones in the costume design.",
}

STYLE_PREFIX = (
    "Keep the EXACT same body as shown in the reference image: "
    "3.5-head-tall doodle character, completely bald round head, same round face with "
    "black dot eyes, tiny smile, pink blush cheeks, same body proportions and medium-length legs. "
    "Pure white background. Flat 2D cartoon doodle style. Clean 2px black outline. "
    "Flat colors only, no gradients, no shadows. Full body visible head to feet. "
    "ONLY change the outfit, accessories, and expression as described. "
)

POSE_PREFIX = (
    "Using the exact same character shown in the reference image (same bald head, "
    "same face, same outfit), change ONLY the pose and expression as described. "
    "Keep all outfit details and colors identical. "
    "Pure white background. Flat 2D cartoon doodle style. Clean 2px black outline. "
)


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def _load_base() -> bytes:
    if not BASE_IMAGE_PATH.exists():
        raise FileNotFoundError(f"베이스 이미지 없음: {BASE_IMAGE_PATH}")
    return BASE_IMAGE_PATH.read_bytes()


def _call_gemini(client: genai.Client, image_bytes: bytes, prompt: str) -> bytes:
    response = client.models.generate_content(
        model=MODEL,
        contents=types.Content(parts=[
            types.Part(inline_data=types.Blob(data=image_bytes, mime_type="image/png")),
            types.Part(text=prompt),
        ]),
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            raw = part.inline_data.data
            if isinstance(raw, str):
                raw = base64.b64decode(raw)
            return raw
    raise ValueError("응답에서 이미지 데이터를 찾을 수 없음")


def generate_costume(
    character_name: str,
    costume_description: str,
    channel_id: str,
    episode_id: str,
    overwrite: bool = False,
) -> Path:
    """베이스 + 의상 설명 → 스토리 캐릭터 이미지 생성.

    Args:
        character_name: 인물명 (예: "나폴레옹", "아인슈타인")
        costume_description: 의상/소품 묘사 (영문 프롬프트)
        channel_id: 채널 ID (색상 가이드 적용)
        episode_id: 에피소드 ID (캐시 폴더 구분)
        overwrite: 기존 캐시 무시하고 재생성

    Returns:
        생성된 이미지 경로
    """
    safe_name = character_name.replace(" ", "_").replace("/", "_")
    cache_path = CHANNELS_ROOT / channel_id / "episode_cache" / episode_id / f"{safe_name}.png"

    if cache_path.exists() and not overwrite:
        logger.info(f"[{episode_id}] {character_name} 캐시 히트 → {cache_path}")
        return cache_path

    color_guide = CHANNEL_COLOR_GUIDE.get(channel_id, "")
    prompt = STYLE_PREFIX + costume_description + " " + color_guide

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    base_bytes = _load_base()

    for attempt in range(1, 4):
        try:
            logger.info(f"[{episode_id}] {character_name} 생성 시도 {attempt}/3 ...")
            img_bytes = _call_gemini(client, base_bytes, prompt)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(img_bytes)
            logger.success(f"[{episode_id}] {character_name} 저장 → {cache_path} ({len(img_bytes)//1024}KB)")
            return cache_path
        except Exception as e:
            logger.warning(f"[{episode_id}] {character_name} 시도 {attempt} 실패: {e}")
            if attempt < 3:
                time.sleep(8 * attempt)

    raise RuntimeError(f"{character_name} 생성 실패 (3회)")


def generate_pose(
    character_image_path: Path,
    pose_description: str,
    pose_name: str,
    episode_id: str,
    overwrite: bool = False,
) -> Path:
    """의상 입은 캐릭터 → 특정 포즈 이미지 생성.

    Args:
        character_image_path: generate_costume() 결과 경로
        pose_description: 포즈 묘사 (예: "pointing right arm forward with excited face")
        pose_name: 파일명용 포즈 키 (예: "pointing", "surprised")
        episode_id: 에피소드 ID
        overwrite: 재생성 여부

    Returns:
        생성된 포즈 이미지 경로
    """
    stem = character_image_path.stem
    pose_path = character_image_path.parent / f"{stem}_{pose_name}.png"

    if pose_path.exists() and not overwrite:
        logger.info(f"[{episode_id}] 포즈 캐시 히트 → {pose_path}")
        return pose_path

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    char_bytes = character_image_path.read_bytes()
    prompt = POSE_PREFIX + pose_description

    for attempt in range(1, 4):
        try:
            logger.info(f"[{episode_id}] {stem}/{pose_name} 포즈 생성 시도 {attempt}/3 ...")
            img_bytes = _call_gemini(client, char_bytes, prompt)
            pose_path.write_bytes(img_bytes)
            logger.success(f"[{episode_id}] {stem}/{pose_name} 저장 → {pose_path}")
            return pose_path
        except Exception as e:
            logger.warning(f"시도 {attempt} 실패: {e}")
            if attempt < 3:
                time.sleep(8 * attempt)

    raise RuntimeError(f"{stem}/{pose_name} 포즈 생성 실패 (3회)")


def generate_episode_characters(episode_spec: dict, overwrite: bool = False) -> dict[str, Path]:
    """에피소드 스펙에서 캐릭터 전체 일괄 생성.

    Args:
        episode_spec: {
            "episode_id": "CH6_2026W17_001",
            "channel_id": "CH6",
            "characters": [
                {
                    "name": "나폴레옹",
                    "costume": "...",
                    "poses": ["neutral", "pointing", "determined"]
                },
                ...
            ]
        }
        overwrite: 재생성 여부

    Returns:
        {character_name: {pose_name: Path}} 형태 딕셔너리
    """
    episode_id  = episode_spec["episode_id"]
    channel_id  = episode_spec["channel_id"]
    characters  = episode_spec["characters"]
    results: dict[str, dict] = {}

    for char in characters:
        name    = char["name"]
        costume = char["costume"]
        poses   = char.get("poses", ["neutral"])

        char_path = generate_costume(name, costume, channel_id, episode_id, overwrite)
        results[name] = {"_base": char_path}

        for pose_key in poses:
            pose_desc = POSE_DESCRIPTIONS.get(pose_key, pose_key)
            pose_path = generate_pose(char_path, pose_desc, pose_key, episode_id, overwrite)
            results[name][pose_key] = pose_path

        time.sleep(3)

    manifest_path = CHANNELS_ROOT / channel_id / "episode_cache" / episode_id / "manifest.json"
    manifest_data = {k: {p: str(v) for p, v in poses.items()} for k, poses in results.items()}
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.success(f"에피소드 캐릭터 생성 완료 → {manifest_path}")

    return results


# ── 기본 포즈 설명 사전 ────────────────────────────────────────────────────────
POSE_DESCRIPTIONS: dict[str, str] = {
    "neutral":    "Standing upright facing forward, arms relaxed at sides, calm neutral expression.",
    "explaining": "Right arm raised with index finger pointing up, left arm down, mouth slightly open in explaining expression.",
    "pointing":   "Right arm extended forward pointing finger at viewer, leaning slightly forward, confident expression.",
    "surprised":  "Both arms raised up and outward, eyes wide open, mouth in a surprised O shape.",
    "thinking":   "Right hand on chin, eyes looking up-left, thoughtful pondering expression.",
    "excited":    "Both arms raised high in the air celebrating, big open happy smile, eyes sparkling.",
    "sad":        "Head slightly bowed, arms hanging down, eyes downcast, small worried frown.",
    "determined": "Right fist raised heroically upward, left arm at side, strong confident determined smile.",
    "running":    "Leaning forward, arms pumping, one leg lifted, speed lines around body.",
    "presenting": "Both arms open outward palms up, warm welcoming smile, presenting gesture.",
    "shocked":    "Both hands on cheeks, eyes huge and wide, mouth wide open in shock.",
    "laughing":   "One hand on belly, other arm up, head slightly tilted back, big laughing smile.",
    "sneaking":   "Body crouched low, arms pulled in, wide cautious eyes, tiptoeing pose.",
    "commanding": "One arm raised forward commanding, standing tall, authoritative expression.",
    "reading":    "Holding an open book in both hands at chest level, eyes looking down at it.",
}
