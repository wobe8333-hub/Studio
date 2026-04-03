# [KAS-PROTECTED] step08 메인 오케스트레이터
# 이 파일은 run_step08 함수를 포함하는 핵심 파일이다.
# 절대 빈 파일로 교체하거나 내용을 삭제하지 않는다.
# 정리 스크립트(__init__.py 일괄 초기화 등) 적용 대상에서 반드시 제외한다.

from loguru import logger
import time
import shutil
from pathlib import Path
from src.core.ssot import (write_json, read_json, json_exists, sha256_file,
                             sha256_dict, now_iso, get_run_dir)
from src.core.config import CHANNELS_DIR, CHANNEL_CATEGORY_KO
from src.core.decision_trace import append_trace
from src.step00.channel_registry import get_channel
from src.step08.script_generator import generate_script
from src.step08.image_generator import generate_batch as gen_images
from src.step08.sd_generator import generate_scene_images as gen_sd_images
from src.step08.manim_generator import generate_and_run as manim_run
from src.step08.narration_generator import generate_narration
from src.step08.subtitle_generator import generate_subtitles
from src.step08.ffmpeg_composer import (image_to_clip, concat_clips,
                                         add_narration, add_subtitles)
from src.step08.motion_engine import batch_create_motion_clips, create_motion_clip
from src.step08.scene_composer import compose_all_scenes

def run_step08(channel_id: str, topic: dict, style_policy: dict,
               revenue_policy: dict, algorithm_policy: dict) -> str:
    import google.generativeai as genai
    from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, BGM_DIR, RUNS_DIR
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
    manim_sections = [s for s in sections if s.get("render_tool") == "manim"]
    gemini_sections = [s for s in sections if s.get("render_tool") != "manim"]

    clip_paths = []
    manim_fallback_count = 0

    logger.info(f"[STEP08] {channel_id}/{run_id} 이미지 생성 중 (SD XL → Gemini 폴백)...")
    # SD XL + LoRA 우선 시도, 실패 섹션은 Gemini 폴백
    sd_paths = gen_sd_images(channel_id, gemini_sections, images_ai)
    img_results = {
        sec["id"]: p
        for sec, p in zip(gemini_sections, sd_paths)
        if p and p.exists()
    }
    missing_sections = [s for s in gemini_sections if s["id"] not in img_results]
    if missing_sections:
        fallback_results = gen_images(missing_sections, images_ai)
        img_results.update(fallback_results)
    # scene_composer: 캐릭터 이미지 + 텍스트 오버레이 합성
    composed_dir = step08_dir / "images" / "composed"
    char_paths_ordered = []
    sections_for_compose = []
    for sec in gemini_sections:
        img_path = img_results.get(sec["id"])
        if img_path and img_path.exists():
            char_paths_ordered.append(img_path)
            sections_for_compose.append(sec)

    composed_paths = compose_all_scenes(char_paths_ordered, sections_for_compose, composed_dir)
    # 합성 실패 시 원본 이미지 폴백
    final_img_paths = composed_paths if composed_paths else char_paths_ordered

    # motion_engine: Ken Burns 팬/줌 효과 적용
    motion_clips_dir = step08_dir / "clips" / "motion"
    motion_clips = batch_create_motion_clips(final_img_paths, motion_clips_dir, duration_sec=6.0)

    for sec, clip_path in zip(sections_for_compose, motion_clips):
        if clip_path and clip_path.exists():
            clip_paths.append((sec["id"], clip_path))

    logger.info(f"[STEP08] {channel_id}/{run_id} Manim 클립 생성 중...")
    stability_log = []
    for sec in manim_sections:
        success, clip_path, fallback = manim_run(sec, clips_manim)
        if success and clip_path:
            clip_paths.append((sec["id"], clip_path))
            stability_log.append({"section_id": sec["id"], "success": True, "fallback": False})
        else:
            manim_fallback_count += 1
            stability_log.append({"section_id": sec["id"], "success": False, "fallback": True})
            img_desc = sec.get("animation_prompt", "")
            img_path = images_ai / f"section_{sec['id']:03d}_fallback.png"
            from src.step08.image_generator import generate_single_image
            generate_single_image(img_desc, img_path)
            if img_path.exists():
                clip_path_fb = clips_gemini / f"section_{sec['id']:03d}_fallback.mp4"
                create_motion_clip(img_path, clip_path_fb, duration_sec=6.0)
                if clip_path_fb.exists():
                    clip_paths.append((sec["id"], clip_path_fb))

    fallback_rate = manim_fallback_count / max(len(manim_sections), 1)
    manim_stability = {
        "run_id": run_id,
        "manim_sections_attempted": len(manim_sections),
        "manim_sections_success": len(manim_sections) - manim_fallback_count,
        "manim_sections_fallback": manim_fallback_count,
        "fallback_rate": round(fallback_rate, 3),
        "hitl_required": fallback_rate > 0.50,
        "details": stability_log,
    }
    write_json(step08_dir / "manim_stability_report.json", manim_stability)

    if fallback_rate > 0.50:
        logger.error(f"MANIM_HITL_REQUIRED: fallback_rate={fallback_rate}")
        append_trace(run_dir / "decision_trace.json", "MANIM_HITL",
                     {"fallback_rate": fallback_rate, "action": "인간 점검 필요"})

    clip_paths.sort(key=lambda x: x[0])
    ordered_clips = [p for _, p in clip_paths]

    if not ordered_clips:
        raise RuntimeError("STEP08_FAIL: 생성된 클립 없음")

    concat_path = step08_dir / "video_raw.mp4"
    concat_clips(ordered_clips, concat_path)

    logger.info(f"[STEP08] {channel_id}/{run_id} narration 생성 중...")
    narration_path = step08_dir / "narration.wav"
    generate_narration(script, narration_path, channel_id)

    with_narr = step08_dir / "video_narr.mp4"
    add_narration(concat_path, narration_path, with_narr)

    srt_path = step08_dir / "subtitles.srt"
    generate_subtitles(script, narration_path, srt_path)

    with_subs = step08_dir / "video_subs.mp4"
    add_subtitles(with_narr, srt_path, with_subs)

    final_video = step08_dir / "video.mp4"
    shutil.copy2(with_subs, final_video)

    _generate_metadata_files(channel_id, run_id, script, step08_dir, topic)

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

def _generate_metadata_files(channel_id: str, run_id: str, script: dict,
                               step08_dir: Path, topic: dict) -> None:
    import google.generativeai as genai
    from src.core.config import GEMINI_API_KEY
    from src.quota.gemini_quota import throttle_if_needed, record_request

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    title_candidates = script.get("title_candidates", [topic.get("title", "제목 없음")])
    write_json(step08_dir / "title.json", {
        "title_candidates": title_candidates,
        "selected": title_candidates[0] if title_candidates else "",
    })

    seo = script.get("seo", {})
    desc_first = seo.get("description_first_2lines", "")
    description = (
        f"{desc_first}\n\n"
        f"▼ 관련 링크\n"
        f"─────────────────────────────\n"
        f"🔗 {script.get('affiliate_insert', {}).get('text', '')}\n\n"
        f"⚠️ {script.get('financial_disclaimer', '') or script.get('medical_disclaimer', '') or ''}\n\n"
        f"{script.get('ai_label', '이 영상은 AI가 제작에 참여했습니다.')}"
    )
    (step08_dir / "description.txt").write_text(description, encoding="utf-8")

    throttle_if_needed()
    record_request()
    tag_prompt = f"YouTube 영상 태그 15개를 한국어와 영어로 섞어 콤마로 구분하여 나열하시오. 주제: {topic.get('title', '')} 카테고리: {CHANNEL_CATEGORY_KO.get(channel_id, channel_id)}"
    tag_response = model.generate_content(tag_prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=200))
    tags = [t.strip() for t in tag_response.text.split(",")][:15]
    write_json(step08_dir / "tags.json", {"tags": tags})

    render_report = {
        "run_id": run_id,
        "channel_id": channel_id,
        "render_completed_at": now_iso(),
        "bgm_used": False,
        "bgm_category_tone": "",
        "video_spec": script.get("video_spec", {}),
        "target_duration_sec": script.get("target_duration_sec", 720),
        "sections_count": len(script.get("sections", [])),
        "manim_sections": len([s for s in script.get("sections", []) if s.get("render_tool") == "manim"]),
    }
    write_json(step08_dir / "render_report.json", render_report)

    style_src = CHANNELS_DIR / channel_id / "style_policy_master.json"
    if style_src.exists():
        shutil.copy2(style_src, step08_dir / "style_policy.json")
