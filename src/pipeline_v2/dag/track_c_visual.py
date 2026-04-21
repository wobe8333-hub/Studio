"""Track C — Visual: Storyboard → 이미지 생성 (포즈 캐시 우선) → QC Layer1"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.core.llm_client import call_llm
from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

POSES_ROOT = Path("assets/characters")
CACHE_MANIFEST = POSES_ROOT / "cache_manifest.json"
VISUAL_OUTPUT_ROOT = Path("runs/pipeline_v2")

_STORYBOARD_PROMPT = """\
아래 스크립트를 씬(Scene) 단위로 분해하세요. 각 씬마다:
- scene_id: 순번
- duration_sec: 예상 길이(초)
- insert_type: "doodle" | "chart" | "formula" | "diagram"  ← CH1/CH2에서 차트/수식은 manim 사용
- character_role: "narrator" | "guest" | "both" | "none"
- pose_tag: 사용할 포즈 (pointing_right, surprised, showing_board 등)
- image_prompt: 배경/소품 두들 이미지 프롬프트 (한국어)
- narration_text: 해당 씬 나레이션 (해당 부분만)

JSON 배열로만 출력.
"""


async def _generate_storyboard(script_text: str, channel_id: str) -> list[dict]:
    prompt = f"채널: {channel_id}\n\n스크립트:\n{script_text}"
    raw = await call_llm(system=_STORYBOARD_PROMPT, user=prompt, max_tokens=4000)
    try:
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning(f"Storyboard JSON 파싱 실패: {e}, 기본값 사용")
    return [{"scene_id": 0, "duration_sec": 5, "insert_type": "doodle",
             "character_role": "narrator", "pose_tag": "neutral_standing",
             "image_prompt": "두들 배경 장면", "narration_text": script_text[:100]}]


def _lookup_pose_cache(channel_id: str, role: str, pose_tag: str) -> Path | None:
    """캐시 매니페스트에서 포즈 이미지 경로 조회."""
    if not CACHE_MANIFEST.exists():
        return None
    try:
        manifest = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return None
    key = f"{channel_id}/{role}/{pose_tag}"
    path_str = manifest.get(key)
    if path_str and Path(path_str).exists():
        return Path(path_str)
    return None


async def _generate_scene_image(scene: dict, channel_id: str, out_dir: Path) -> Path:
    """씬 이미지 생성 — 포즈 캐시 우선, 없으면 Gemini nano-banana 호출."""
    scene_id = scene.get("scene_id", 0)
    role = scene.get("character_role", "narrator")
    pose_tag = scene.get("pose_tag", "neutral_standing")

    # 캐시 조회
    if role != "none":
        cached = _lookup_pose_cache(channel_id, role, pose_tag)
        if cached:
            logger.debug(f"포즈 캐시 히트: {channel_id}/{role}/{pose_tag}")
            return cached

    # nano-banana 생성 (Gemini)
    out_path = out_dir / f"scene_{scene_id:03d}.png"
    image_prompt = scene.get("image_prompt", "두들 장면")

    try:
        from src.core.llm_client import generate_image_gemini
        await generate_image_gemini(
            prompt=f"두들 애니메이션 스타일, 크래프트 페이퍼 배경, 2px 라인: {image_prompt}",
            output_path=out_path,
        )
    except Exception as e:
        logger.warning(f"이미지 생성 실패 scene_{scene_id}: {e}, placeholder 사용")
        out_path.touch()

    return out_path


async def run_track_c(job: "EpisodeJob") -> dict:
    """Track C: Storyboard 생성 + 씬별 이미지 생성.

    Returns: {"storyboard": list[dict], "scene_images": list[str], "scene_count": int}
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id
    script_text = job.track_a_result.output.get("script_text", "") if job.track_a_result else ""

    out_dir = VISUAL_OUTPUT_ROOT / meta.episode_id / "visual"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Track C: Storyboard 생성 ({channel_id})")
    storyboard = await _generate_storyboard(script_text, channel_id)
    logger.info(f"Track C: {len(storyboard)}개 씬 생성됨")

    # manim insert 씬 분리 (CH1/CH2 전용)
    manim_scenes = []
    doodle_scenes = []
    for scene in storyboard:
        if channel_id in ("CH1", "CH2") and scene.get("insert_type") in ("chart", "formula", "diagram"):
            manim_scenes.append(scene)
        else:
            scene["insert_type"] = "doodle"
            doodle_scenes.append(scene)

    meta.features.manim_inserts_count = len(manim_scenes)
    logger.info(f"Track C: doodle={len(doodle_scenes)}, manim={len(manim_scenes)}")

    # 두들 씬 이미지 생성
    import asyncio
    tasks = [_generate_scene_image(s, channel_id, out_dir) for s in doodle_scenes]
    scene_paths = await asyncio.gather(*tasks)

    return {
        "storyboard": storyboard,
        "doodle_scenes": doodle_scenes,
        "manim_scenes": manim_scenes,
        "scene_images": [str(p) for p in scene_paths],
        "scene_count": len(storyboard),
    }
