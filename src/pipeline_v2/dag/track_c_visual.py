"""Track C — Visual: 스크립트 → 캐릭터 추출 → 이미지 생성 (에피소드 캐릭터 캐시 우선) → QC Layer1"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.core.llm_client import generate_text
from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

CHANNELS_ROOT = Path("assets/channels")
BASE_POSES_ROOT = Path("assets/shared/base_poses")
VISUAL_OUTPUT_ROOT = Path("runs/pipeline_v2")

# ── 캐릭터 추출 프롬프트 ─────────────────────────────────────────────────────
_CHARACTER_EXTRACT_PROMPT = """\
아래 스크립트에서 등장하는 모든 캐릭터를 분석하세요.
각 캐릭터마다 두들 애니메이션 스타일에 맞는 의상 묘사를 영어로 작성하세요.

출력 형식 (JSON 배열):
[
  {
    "name": "캐릭터 이름 (한국어 가능)",
    "costume": "OUTFIT: [의상]. ACCESSORIES: [소품]. [표정/특징]. (전부 영어)",
    "poses": ["neutral", "explaining", "surprised"]  ← 스크립트에서 해당 캐릭터가 사용할 포즈들
  }
]

포즈 목록 (가능한 값만 사용):
neutral, explaining, pointing, surprised, thinking, excited, sad, determined,
running, presenting, shocked, laughing, sneaking, commanding, reading

규칙:
- 의상은 구체적이고 시각적으로 명확하게 (색상 hex 포함 권장)
- 역사 인물은 시대 고증을 반영하되 두들 스타일 유지
- 포즈는 스크립트에서 해당 캐릭터가 실제로 필요한 것만 선택
- JSON만 출력, 설명 없음
"""

# ── 스토리보드 생성 프롬프트 ─────────────────────────────────────────────────
_STORYBOARD_PROMPT = """\
아래 스크립트를 씬(Scene) 단위로 분해하세요. 각 씬마다:
- scene_id: 순번 (0부터)
- duration_sec: 예상 길이(초)
- insert_type: "doodle" | "chart" | "formula" | "diagram"  ← CH1/CH2에서 차트/수식은 manim 사용
- character_name: 이 씬에 등장하는 캐릭터 이름 (없으면 null)
- pose_tag: 사용할 포즈 태그 (neutral/explaining/surprised 등, 캐릭터 없으면 null)
- image_prompt: 배경/소품 두들 이미지 프롬프트 (한국어)
- narration_text: 해당 씬 나레이션

JSON 배열로만 출력.
"""


async def _call_llm_async(system: str, user: str) -> str:
    """동기 generate_text를 executor에서 비동기 실행."""
    loop = asyncio.get_event_loop()
    prompt = f"{system}\n\n{user}"
    return await loop.run_in_executor(None, generate_text, prompt)


async def _extract_episode_characters(script_text: str, channel_id: str) -> list[dict]:
    """스크립트에서 스토리 캐릭터 목록과 의상 스펙 추출."""
    raw = await _call_llm_async(_CHARACTER_EXTRACT_PROMPT, f"채널: {channel_id}\n\n스크립트:\n{script_text}")
    try:
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning(f"캐릭터 추출 JSON 파싱 실패: {e}")
    return []


async def _generate_storyboard(script_text: str, channel_id: str, episode_id: str = "") -> list[dict]:
    """LLM Storyboard 생성 → 실패 시 rule-based fallback."""
    raw = await _call_llm_async(_STORYBOARD_PROMPT, f"채널: {channel_id}\n\n스크립트:\n{script_text}")
    try:
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning(f"Storyboard JSON 파싱 실패: {e} — rule-based fallback 사용")

    from src.pipeline_v2.storyboard import build_storyboard
    return build_storyboard(script_text, channel_id, episode_id or "unknown")


def _lookup_episode_character_pose(channel_id: str, episode_id: str, character_name: str, pose_tag: str) -> Path | None:
    """에피소드 캐릭터 캐시에서 특정 포즈 이미지 조회."""
    safe_name = character_name.replace(" ", "_").replace("/", "_")
    ep_dir = CHANNELS_ROOT / channel_id / "episode_cache" / episode_id

    # {character_name}_{pose_tag}.png 형식 우선 조회
    pose_path = ep_dir / f"{safe_name}_{pose_tag}.png"
    if pose_path.exists():
        return pose_path

    # 포즈 없으면 베이스 의상 이미지 반환 (neutral 대체)
    base_path = ep_dir / f"{safe_name}.png"
    if base_path.exists():
        return base_path

    return None


def _lookup_base_pose(pose_tag: str) -> Path | None:
    """베이스 포즈 라이브러리에서 포즈 이미지 조회 (배경 없는 씬용)."""
    # pose_tag → 파일명 매핑 (번호 없이도 찾기)
    for f in BASE_POSES_ROOT.glob("*.png"):
        # 파일명 예: 01_neutral.png, 09_determined.png
        if f.stem.split("_", 1)[-1] == pose_tag:
            return f
    return None


async def _generate_scene_image(
    scene: dict,
    channel_id: str,
    episode_id: str,
    out_dir: Path,
) -> Path:
    """씬 이미지 생성 — 에피소드 캐릭터 캐시 → 베이스 포즈 → Gemini 생성 순."""
    scene_id = scene.get("scene_id", 0)
    character_name: str | None = scene.get("character_name")
    pose_tag: str = scene.get("pose_tag") or "neutral"
    image_prompt: str = scene.get("image_prompt", "두들 장면")

    out_path = out_dir / f"scene_{scene_id:03d}.png"

    # 1. 에피소드 캐릭터 캐시 조회
    if character_name:
        cached = _lookup_episode_character_pose(channel_id, episode_id, character_name, pose_tag)
        if cached:
            logger.debug(f"에피소드 캐릭터 캐시 히트: {character_name}/{pose_tag} → {cached}")
            return cached

    # 2. 베이스 포즈 라이브러리 조회 (캐릭터 없는 씬)
    base_pose = _lookup_base_pose(pose_tag)
    if base_pose and not character_name:
        logger.debug(f"베이스 포즈 히트: {pose_tag} → {base_pose}")
        return base_pose

    # 3. Gemini 이미지 생성 (캐시 미스) — 배경 씬 전용
    try:
        import base64
        import os

        from google import genai
        from google.genai import types as gtypes
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        full_prompt = (
            "Flat 2D cartoon doodle style, white background, 2px black outline, "
            f"flat colors only: {image_prompt}"
        )
        loop = asyncio.get_event_loop()

        def _gen():
            resp = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=full_prompt,
                config=gtypes.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            for part in resp.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    raw = part.inline_data.data
                    if isinstance(raw, str):
                        raw = base64.b64decode(raw)
                    return raw
            return None

        img_bytes = await loop.run_in_executor(None, _gen)
        if img_bytes:
            out_path.write_bytes(img_bytes)
        else:
            out_path.touch()
    except Exception as e:
        logger.warning(f"이미지 생성 실패 scene_{scene_id}: {e}")
        out_path.touch()

    return out_path


async def run_track_c(job: "EpisodeJob") -> dict:
    """Track C: 캐릭터 추출 → 에피소드 캐릭터 생성 → Storyboard → 씬별 이미지 생성.

    Returns: {
        "characters": list[dict],          # 추출된 캐릭터 스펙
        "character_paths": dict,           # {character_name: {pose: path}}
        "storyboard": list[dict],
        "doodle_scenes": list[dict],
        "manim_scenes": list[dict],
        "scene_images": list[str],
        "scene_count": int,
    }
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id
    episode_id = meta.episode_id
    script_text = job.track_a_result.output.get("script_text", "") if job.track_a_result else ""

    out_dir = VISUAL_OUTPUT_ROOT / episode_id / "visual"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: 캐릭터 추출 + 스토리보드 병렬 생성 ─────────────────────────
    logger.info(f"Track C: 캐릭터 추출 + 스토리보드 생성 ({channel_id})")
    char_task = asyncio.create_task(_extract_episode_characters(script_text, channel_id))
    sb_task = asyncio.create_task(_generate_storyboard(script_text, channel_id, episode_id))

    characters, storyboard = await asyncio.gather(char_task, sb_task)
    logger.info(f"Track C: 캐릭터 {len(characters)}명, 씬 {len(storyboard)}개")

    # ── Step 2: 에피소드 캐릭터 이미지 생성 (캐릭터 있을 때만) ─────────────
    character_paths: dict = {}
    if characters:
        ep_spec = {
            "episode_id": episode_id,
            "channel_id": channel_id,
            "characters": characters,
        }
        try:
            # 동기 함수이므로 executor로 실행
            loop = asyncio.get_event_loop()
            from src.adapters.character_generator import generate_episode_characters
            character_paths = await loop.run_in_executor(
                None,
                lambda: generate_episode_characters(ep_spec, overwrite=False),
            )
            # Path 객체를 str로 직렬화
            character_paths = {
                name: {pose: str(path) for pose, path in poses.items()}
                for name, poses in character_paths.items()
            }
            logger.success(f"Track C: 에피소드 캐릭터 {len(character_paths)}명 생성 완료")
        except Exception as e:
            logger.warning(f"에피소드 캐릭터 생성 실패: {e} — 씬 이미지 생성 계속")

    # ── Step 3: Manim / Doodle 씬 분리 ─────────────────────────────────────
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

    # ── Step 4: 씬별 이미지 생성 (캐릭터 캐시 우선) ────────────────────────
    tasks = [
        _generate_scene_image(s, channel_id, episode_id, out_dir)
        for s in doodle_scenes
    ]
    scene_paths = await asyncio.gather(*tasks)

    return {
        "characters": characters,
        "character_paths": character_paths,
        "storyboard": storyboard,
        "doodle_scenes": doodle_scenes,
        "manim_scenes": manim_scenes,
        "scene_images": [str(p) for p in scene_paths],
        "scene_count": len(storyboard),
    }
