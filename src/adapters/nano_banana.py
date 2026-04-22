"""nano-banana 포즈 증폭 어댑터 (T10)

유저 레퍼런스 1장 → Gemini로 40 포즈 자동 생성 + cache_manifest.json 해시 관리.
포즈 40종 × 14 캐릭터 = 560장 (T11 배치 생성 기반).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from loguru import logger

CHARACTERS_ROOT = Path("assets/characters")
CACHE_MANIFEST_PATH = CHARACTERS_ROOT / "cache_manifest.json"

POSE_CATEGORIES: dict[str, list[str]] = {
    "neutral": ["standing", "sitting", "leaning"],
    "explaining": ["pointing_right", "pointing_left", "pointing_up", "arms_open"],
    "thinking": ["chin_touch", "arms_crossed", "looking_up"],
    "surprised": ["hands_up", "mouth_open", "step_back"],
    "happy": ["thumbs_up", "clapping", "jumping", "waving"],
    "concerned": ["frowning", "head_tilt", "hands_clasped"],
    "presenting": ["gesture_board", "holding_paper", "side_profile"],
    "walking": ["walk_left", "walk_right"],
    "action": ["writing", "typing", "phone_call"],
    "special": ["bow", "celebrate"],
}

ALL_POSES: list[str] = [
    f"{cat}_{pose}" for cat, poses in POSE_CATEGORIES.items() for pose in poses
][:40]

DOODLE_STYLE_PREFIX = (
    "두들 애니메이션 스타일, 크래프트 페이퍼 배경, 2px 검정 라인 아트, "
    "5등신 비율, 흰색 배경, 정면 또는 3/4뷰, 단색 의상, "
)


def _file_hash(path: Path) -> str:
    """파일 SHA-256 해시 (캐시 키)."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _load_manifest() -> dict:
    if not CACHE_MANIFEST_PATH.exists():
        return {}
    try:
        with open(CACHE_MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_manifest(manifest: dict) -> None:
    CACHE_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def get_pose_path(channel_id: str, role: str, pose_tag: str) -> Path:
    """포즈 파일 경로 반환 (존재 여부 무관)."""
    return CHARACTERS_ROOT / channel_id / "poses" / f"{role}_{pose_tag}.png"


def lookup_cached_pose(channel_id: str, role: str, pose_tag: str) -> Path | None:
    """캐시 매니페스트 + 파일 존재 확인 후 경로 반환."""
    pose_path = get_pose_path(channel_id, role, pose_tag)
    if not pose_path.exists():
        return None

    manifest = _load_manifest()
    cache_key = f"{channel_id}/{role}/{pose_tag}"
    if cache_key not in manifest:
        return None

    return pose_path


async def _generate_pose(
    ref_path: Path,
    channel_id: str,
    role: str,
    pose_tag: str,
    out_path: Path,
) -> bool:
    """Gemini nano-banana 편집으로 단일 포즈 생성."""
    pose_description = pose_tag.replace("_", " ")
    prompt = (
        f"{DOODLE_STYLE_PREFIX}"
        f"캐릭터가 '{pose_description}' 포즈를 취하고 있는 모습. "
        f"레퍼런스 캐릭터와 동일한 의상, 헤어스타일, 얼굴 특징 유지."
    )

    try:
        from src.core.llm_client import generate_image_gemini
        await generate_image_gemini(
            prompt=prompt,
            output_path=out_path,
            reference_image_path=str(ref_path),
        )
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        logger.warning(f"포즈 생성 실패 {channel_id}/{role}/{pose_tag}: {e}")
        return False


async def generate_poses_for_character(
    channel_id: str,
    role: str,
    pose_tags: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    """캐릭터 1명의 포즈 라이브러리 생성.

    Args:
        channel_id: CH1~CH7
        role: narrator | guest
        pose_tags: None이면 ALL_POSES(40종) 전체
        overwrite: True면 기존 파일 덮어쓰기

    Returns: {"generated": int, "skipped": int, "failed": int}
    """
    ref_path = CHARACTERS_ROOT / channel_id / f"{role}_ref.png"
    if not ref_path.exists():
        logger.error(f"레퍼런스 없음: {ref_path} — 포즈 생성 불가")
        return {"generated": 0, "skipped": 0, "failed": 0, "error": "ref_missing"}

    poses = pose_tags or ALL_POSES
    out_dir = CHARACTERS_ROOT / channel_id / "poses"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    ref_hash = _file_hash(ref_path)

    generated = skipped = failed = 0

    for pose_tag in poses:
        out_path = out_dir / f"{role}_{pose_tag}.png"
        cache_key = f"{channel_id}/{role}/{pose_tag}"

        if not overwrite and out_path.exists() and cache_key in manifest:
            logger.debug(f"포즈 캐시 존재, 스킵: {cache_key}")
            skipped += 1
            continue

        success = await _generate_pose(ref_path, channel_id, role, pose_tag, out_path)
        if success:
            manifest[cache_key] = {
                "file": str(out_path),
                "ref_hash": ref_hash,
                "pose_tag": pose_tag,
            }
            generated += 1
            logger.info(f"포즈 생성: {cache_key}")
        else:
            failed += 1

    _save_manifest(manifest)
    logger.info(f"포즈 생성 완료 {channel_id}/{role}: 생성={generated} 스킵={skipped} 실패={failed}")
    return {"generated": generated, "skipped": skipped, "failed": failed}


async def generate_full_library(
    channel_ids: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    """14 캐릭터 × 40 포즈 = 560장 전체 생성 (T11).

    channel_ids: None이면 CH1~CH7 전체
    """
    if channel_ids is None:
        channel_ids = [f"CH{i}" for i in range(1, 8)]

    total = {"generated": 0, "skipped": 0, "failed": 0}
    for channel_id in channel_ids:
        for role in ("narrator", "guest"):
            result = await generate_poses_for_character(channel_id, role, overwrite=overwrite)
            for k in total:
                total[k] += result.get(k, 0)

    logger.info(f"전체 포즈 라이브러리 완료: {total}")
    return total
