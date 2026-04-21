# [KAS-PROTECTED] step08 메인 오케스트레이터
# 이 파일은 run_step08 함수를 포함하는 핵심 파일이다.
# 절대 빈 파일로 교체하거나 내용을 삭제하지 않는다.
# 정리 스크립트(__init__.py 일괄 초기화 등) 적용 대상에서 반드시 제외한다.

import shutil
import time
from pathlib import Path

from loguru import logger

from src.core.config import CHANNEL_CATEGORY_KO, CHANNELS_DIR
from src.core.decision_trace import append_trace
from src.core.ssot import (
    get_run_dir,
    json_exists,
    now_iso,
    read_json,
    sha256_dict,
    sha256_file,
    write_json,
)
from src.step00.channel_registry import get_channel
from src.step08.ffmpeg_composer import add_narration, add_subtitles, concat_clips, image_to_clip
from src.step08.image_generator import generate_batch as gen_images
from src.step08.manim_generator import generate_and_run as manim_run
from src.step08.metadata_generator import generate_metadata
from src.step08.motion_engine import batch_create_motion_clips, create_motion_clip
from src.step08.narration_generator import generate_narration
from src.step08.scene_composer import compose_all_scenes
from src.step08.script_generator import generate_script
from src.step08.sd_generator import generate_scene_images as gen_sd_images
from src.step08.subtitle_generator import generate_subtitles


def run_step08(channel_id: str, topic: dict, style_policy: dict,
               revenue_policy: dict, algorithm_policy: dict) -> str:
    from src.core.config import BGM_DIR, GEMINI_API_KEY, GEMINI_TEXT_MODEL, RUNS_DIR
    run_id = f"run_{channel_id}_{int(time.time())}"
    run_dir = get_run_dir(channel_id, run_id)
    step08_dir = run_dir / "step08"
    clips_gemini = step08_dir / "clips" / "gemini"
    clips_manim = step08_dir / "clips" / "manim"
    images_ai = step08_dir / "images" / "assets_ai"
    images_kf = step08_dir / "images" / "keyframes"

    for d in [step08_dir, clips_gemini, clips_manim, images_ai, images_kf]:
        d.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "channel_id": channel_id,
        "schema_version": "1.0",
        "run_state": "RUNNING",
        "goal_ref": f"채널 {channel_id} 영상 자동 생성",
        "created_at": now_iso(),
        "topic": topic,
    }
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "decision_trace.json", {"events": []})
    write_json(run_dir / "observability.json", {"run_id": run_id, "start": now_iso()})
    write_json(run_dir / "reflection.json", {"run_id": run_id})

    cost_data = {
        "channel_id": channel_id, "run_id": run_id,
        "cost_recorded_at": now_iso(),
        "gemini_api": {
            "script_generation": {"input_tokens": 0, "output_tokens": 0, "cost_krw": 0.0},
            "image_generation": {"image_count": 0, "cost_krw": 0.0},
            "manim_code_generation": {"input_tokens": 0, "output_tokens": 0, "cost_krw": 0.0},
            "title_tag_generation": {"input_tokens": 0, "output_tokens": 0, "cost_krw": 0.0},
            "total_krw": 0.0,
        },
        "manim_render": {"method": "local", "compute_cost_krw": 0.0},
        "other_cost_krw": 0.0,
        "total_cost_krw": 0.0,
    }
    write_json(run_dir / "cost.json", cost_data)

    logger.info(f"[STEP08] {channel_id}/{run_id} script 생성 중...")
    script = generate_script(channel_id, run_id, topic, style_policy,
                              revenue_policy, algorithm_policy)
    write_json(step08_dir / "script.json", script)

    sections = script.get("sections", [])
    clip_paths = []

    # ── Phase 9: Gemini 배경 + 에셋 캐릭터 PNG 합성 파이프라인 ─────────────
    # SD XL / Manim 대신: Gemini로 배경 생성 → assets/ 캐릭터 PNG 오버레이
    from src.step08.character_manager import (
        get_character_asset_path,
        select_expression_for_section,
    )
    from src.step08.scene_composer import compose_scene

    logger.info(f"[STEP08] {channel_id}/{run_id} Gemini 배경 이미지 생성 중...")
    bg_results = gen_images(sections, images_ai)

    composed_dir = step08_dir / "images" / "composed"
    composed_dir.mkdir(parents=True, exist_ok=True)
    total_secs = len(sections)
    composed_frames: list[Path] = []

    for sec in sections:
        expression = select_expression_for_section(sec["id"], total_secs)
        char_png   = get_character_asset_path(channel_id, expression)
        bg_path    = bg_results.get(sec["id"])
        out_path   = composed_dir / f"composed_{sec['id']:03d}.png"

        ok = compose_scene(
            character_path=char_png,
            background_path=bg_path,
            narration_text=sec.get("narration_text", ""),
            output_path=out_path,
        )
        if ok and out_path.exists():
            composed_frames.append(out_path)
        elif bg_path and bg_path.exists():
            composed_frames.append(bg_path)   # 배경만이라도 사용
            logger.debug(f"[STEP08] section={sec['id']} 합성 실패 → 배경 단독 사용")

    # motion_engine: Ken Burns 팬/줌 효과
    motion_clips_dir = step08_dir / "clips" / "motion"
    motion_clips = batch_create_motion_clips(composed_frames, motion_clips_dir, duration_sec=6.0)
    for i, clip_path in enumerate(motion_clips):
        if clip_path and clip_path.exists():
            clip_paths.append((i, clip_path))

    # manim_stability_report — 호환성 유지 (Gemini+에셋 파이프라인으로 대체됨)
    manim_stability = {
        "run_id": run_id,
        "manim_sections_attempted": 0,
        "manim_sections_success": 0,
        "manim_sections_fallback": 0,
        "fallback_rate": 0.0,
        "hitl_required": False,
        "details": [],
        "note": "Phase 9: Gemini 배경 + 에셋 캐릭터 PNG 파이프라인으로 대체됨",
    }
    write_json(step08_dir / "manim_stability_report.json", manim_stability)

    clip_paths.sort(key=lambda x: x[0])
    ordered_clips = [p for _, p in clip_paths]

    if not ordered_clips:
        raise RuntimeError("STEP08_FAIL: 생성된 클립 없음")

    concat_path = step08_dir / "video_raw.mp4"
    if not concat_clips(ordered_clips, concat_path):
        raise RuntimeError(f"STEP08_FAIL: concat_clips 실패 — {channel_id}/{run_id}")
    if not concat_path.exists() or concat_path.stat().st_size == 0:
        raise RuntimeError(f"STEP08_FAIL: video_raw.mp4 생성 실패 — {channel_id}/{run_id}")

    logger.info(f"[STEP08] {channel_id}/{run_id} narration 생성 중...")
    narration_path = step08_dir / "narration.wav"
    generate_narration(script, narration_path, channel_id)

    with_narr = step08_dir / "video_narr.mp4"
    if not add_narration(concat_path, narration_path, with_narr):
        raise RuntimeError(f"STEP08_FAIL: add_narration 실패 — {channel_id}/{run_id}")
    if not with_narr.exists() or with_narr.stat().st_size == 0:
        raise RuntimeError(f"STEP08_FAIL: video_narr.mp4 생성 실패 — {channel_id}/{run_id}")

    srt_path = step08_dir / "subtitles.srt"
    generate_subtitles(script, narration_path, srt_path)

    with_subs = step08_dir / "video_subs.mp4"
    if not add_subtitles(with_narr, srt_path, with_subs):
        logger.warning(f"[STEP08] 자막 추가 실패 — narration 영상으로 진행: {channel_id}/{run_id}")
        with_subs = with_narr  # 자막 없이 진행 (업로드 차단 대신 경고)

    final_video = step08_dir / "video.mp4"
    shutil.copy2(with_subs, final_video)

    try:
        generate_metadata(channel_id, run_id, script, step08_dir, topic)
    except Exception as meta_err:
        logger.warning(f"[STEP08] 메타데이터 생성 실패 (영상은 유지): {meta_err}")

    needed = ["script.json", "narration.wav", "subtitles.srt", "video.mp4",
              "render_report.json"]
    hashes = {}
    for f in needed:
        fp = step08_dir / f
        if fp.exists():
            hashes[f] = sha256_file(fp)
    write_json(step08_dir / "artifact_hashes.json", hashes)

    manifest["run_state"] = "COMPLETED"
    manifest["completed_at"] = now_iso()
    write_json(run_dir / "manifest.json", manifest)

    logger.info(f"[STEP08] {channel_id}/{run_id} 완료 ✅")
    return run_id

