from __future__ import annotations

import json
import os
import shutil
import time
import hashlib
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.utils import run_manager
from backend.v8 import (
    V8Stage,
    V8ValidationError,
    V8FFmpegNotFound,
    V8GeminiError,
    V8ThumbnailPolicyError,
    update_render_state,
)
from backend.v8.channel import load_channel, resolve_content_id, get_upload_dir, ChannelConfig
from backend.v8.style import create_style_snapshot_and_lock, StyleContext
from backend.v8.gemini_image import generate_section_image
from backend.v8.render_ffmpeg import render_video
from backend.v8 import text_prompt as text_prompt_module
from backend.v8 import stickman_overlay
from backend.v8 import simple_character_overlay
from backend.v8.thumbnail_ffmpeg import build_thumbnail
from backend.v8.wav_utils import generate_sine_wav, get_wav_duration
from backend.v8.srt_utils import write_srt_for_sections, validate_srt_format, get_srt_last_end_time
from backend.v8.hash_utils import build_hash_map, sha256_bytes
from backend.v8.content_registry import upsert_content_entry
from backend.v8.variant_builders import run_variant_builder_builder
from backend.style.style_policy_engine import (
    load_style_registries,
    build_style_policy,
    save_style_policy,
    validate_style_policy,
    ensure_style_policy_for_v8,
)


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_v8_dirs(run_root: Path) -> Dict[str, Path]:
    v8_root = run_root / "v8"
    images_root = v8_root / "images"
    assets_ai = images_root / "assets_ai"
    response_raw = images_root / "response_raw"
    state_dir = v8_root / "state"

    for d in [v8_root, images_root, assets_ai, response_raw, state_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        "v8_root": v8_root,
        "images_root": images_root,
        "assets_ai": assets_ai,
        "response_raw": response_raw,
        "state_dir": state_dir,
    }


def _get_channel_raw(channel_id: str) -> Dict[str, Any]:
    """channels.json에서 해당 채널의 원본 dict 반환 (선택 필드용)."""
    project_root = run_manager.get_project_root()
    config_path = project_root / "config" / "channels.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    for ch in data.get("channels") or []:
        if ch.get("channel_id") == channel_id:
            return ch
    return {}


def _build_script_json(
    channel: ChannelConfig,
    style_ctx: StyleContext,
    topic: str,
    content_id: str,
) -> Dict[str, Any]:
    tmpl = style_ctx.templates_profile
    hook = str(tmpl.get("hook_template", "")).format(topic=topic)
    promise = str(tmpl.get("promise_template", "")).format(topic=topic)

    sections: List[Dict[str, Any]] = []
    for idx in range(1, channel.sections + 1):
        heading = str(tmpl.get("section_heading_template", "")).format(
            topic=topic, index=idx
        )
        narration_text = str(tmpl.get("section_narration_template", "")).format(
            topic=topic, index=idx
        )
        asset_prompt = str(tmpl.get("asset_prompt_template", "")).format(
            topic=topic, index=idx
        )
        sections.append(
            {
                "id": f"section_{idx:03d}",
                "heading": heading,
                "narration_text": narration_text,
                "asset_prompt": asset_prompt,
            }
        )

    if not hook.strip() or not promise.strip():
        raise V8ValidationError("hook/promise must be non-empty")
    if len(sections) != channel.sections:
        raise V8ValidationError("sections length must equal channel.sections")

    # 간단하지만 결정적인 제목 후보 3개 생성
    base_topic = topic if topic and topic != "DEFAULT_TOPIC" else channel.niche
    title_candidates = [
        f"{base_topic} 완전 정리",
        f"{base_topic} 모르면 손해보는 핵심 5가지",
        f"지금 바로 써먹는 {base_topic} 실전 가이드",
    ]

    script = {
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "style_profile": channel.style_profile,
        "format_id": channel.format_id,
        "topic": topic,
        "title_candidates": title_candidates,
        "hook": hook,
        "promise": promise,
        "sections": sections,
        "target_duration_sec": channel.target_duration_sec,
        "midroll_plan": [0.35, 0.65, 0.85],
        "video_spec": {"width": 1920, "height": 1080, "fps": 30},
        "created_at_utc": _now_utc_iso(),
    }
    return script


def _build_script_json_stickman(
    channel: ChannelConfig,
    topic: str,
    content_id: str,
    channel_raw: Dict[str, Any],
) -> Dict[str, Any]:
    """스틱맨 채널: Gemini 3 Flash 1회 호출로 스토리 패키지 생성."""
    text_model_id = str(channel_raw.get("text_model_id") or "gemini-3-flash").strip()
    package = text_prompt_module.generate_story_package(
        topic=topic,
        style_profile=channel.style_profile,
        sections=channel.sections,
        model_id=text_model_id,
    )
    sections: List[Dict[str, Any]] = []
    for s in package.get("sections") or []:
        sec = dict(s)
        sec["asset_prompt"] = sec.get("background_prompt") or sec.get("asset_prompt") or ""
        sections.append(sec)
    script = {
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "style_profile": channel.style_profile,
        "format_id": channel.format_id,
        "topic": topic,
        "title_candidates": list(package.get("title_candidates") or [])[:3],
        "hook": str(package.get("hook") or ""),
        "promise": str(package.get("promise") or ""),
        "sections": sections,
        "target_duration_sec": channel.target_duration_sec,
        "midroll_plan": [0.35, 0.65, 0.85],
        "video_spec": {"width": 1920, "height": 1080, "fps": 30},
        "created_at_utc": _now_utc_iso(),
    }
    return script


def _build_script_json_simple_character(
    channel: ChannelConfig,
    topic: str,
    content_id: str,
    channel_raw: Dict[str, Any],
) -> Dict[str, Any]:
    """simple_character 채널: Gemini 3 Flash 1회 호출로 스토리 패키지 생성. section에 character_layout 포함."""
    text_model_id = str(channel_raw.get("text_model_id") or "gemini-3-flash").strip()
    package = text_prompt_module.generate_story_package(
        topic=topic,
        style_profile=channel.style_profile,
        sections=channel.sections,
        model_id=text_model_id,
    )
    sections: List[Dict[str, Any]] = []
    for s in package.get("sections") or []:
        sec = dict(s)
        sec["asset_prompt"] = sec.get("background_prompt") or sec.get("asset_prompt") or ""
        if "character_layout" not in sec:
            sec["character_layout"] = "right"
        sections.append(sec)
    script = {
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "style_profile": channel.style_profile,
        "format_id": channel.format_id,
        "topic": topic,
        "title_candidates": list(package.get("title_candidates") or [])[:3],
        "hook": str(package.get("hook") or ""),
        "promise": str(package.get("promise") or ""),
        "sections": sections,
        "target_duration_sec": channel.target_duration_sec,
        "midroll_plan": [0.35, 0.65, 0.85],
        "video_spec": {"width": 1920, "height": 1080, "fps": 30},
        "created_at_utc": _now_utc_iso(),
    }
    return script


def _build_ctr_package(
    v8_root: Path,
    script: Dict[str, Any],
    style_ctx: StyleContext,
    channel: ChannelConfig,
    content_id: str,
    topic: str,
) -> Dict[str, Path]:
    title_path = v8_root / "title.json"
    desc_path = v8_root / "description.txt"
    tags_path = v8_root / "tags.json"

    title_candidates = list(script.get("title_candidates") or [])
    if len(title_candidates) != 3:
        raise V8ValidationError("title_candidates must have length 3")
    selected_title = title_candidates[0]

    title_style = str(style_ctx.resolved_style.get("title_style", ""))
    title_obj = {
        "selected_title": selected_title,
        "title_candidates": title_candidates,
        "title_style": title_style,
        "topic": topic,
        "channel_id": channel.channel_id,
        "content_id": content_id,
    }
    title_path.write_text(json.dumps(title_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8~12줄 설명 생성 (결정적 텍스트, 외부검색 금지)
    lines: List[str] = []
    lines.append(f"이 영상에서는 {channel.niche} 관점에서 '{topic}'을(를) 정리합니다.")
    lines.append(script.get("hook", ""))
    lines.append(script.get("promise", ""))

    sections = script.get("sections") or []
    for s in sections:
        heading = s.get("heading") or s.get("id")
        lines.append(f"- {heading}")
        if len(lines) >= 7:
            break

    lines.append("영상이 도움이 되었다면 구독과 좋아요로 다음 콘텐츠를 함께 만들어 주세요.")
    while len(lines) < 8:
        lines.append("")

    desc_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    # 태그: 스타일 기본 태그 + topic 토큰
    import re

    base_tags = list(style_ctx.resolved_style.get("tags_base") or [])
    topic_tokens = [
        t.lower()
        for t in re.split(r"[^\w]+", topic)
        if t and t.lower() not in {b.lower() for b in base_tags}
    ]
    tags_combined: List[str] = []
    for t in base_tags + topic_tokens:
        if t and t not in tags_combined:
            tags_combined.append(t)
        if len(tags_combined) >= 20:
            break

    tags_obj = {"tags": tags_combined}
    tags_path.write_text(json.dumps(tags_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "title": title_path,
        "description": desc_path,
        "tags": tags_path,
    }


def _generate_images_stickman(
    channel: ChannelConfig,
    script: Dict[str, Any],
    run_id: str,
    content_id: str,
    images_root: Path,
    assets_ai_dir: Path,
    raw_dir: Path,
    channel_raw: Dict[str, Any],
) -> None:
    """스틱맨 채널: 배경만 Gemini(캐시 사용) → 로컬 캐릭터 오버레이 → assets_ai."""
    sections = script.get("sections") or []
    if len(sections) != channel.sections:
        raise V8ValidationError("sections length mismatch during image generation")

    backgrounds_dir = images_root / "backgrounds"
    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    cache_enabled = bool(channel_raw.get("image_cache_enabled", True))
    image_jobs: List[Dict[str, Any]] = []
    receipts: List[Dict[str, Any]] = []

    for idx, section in enumerate(sections, start=1):
        section_id = f"section_{idx:03d}"
        background_prompt = section.get("background_prompt") or section.get("asset_prompt") or ""
        pose = str(section.get("character_pose") or "idle")
        expression = str(section.get("character_expression") or "neutral")

        receipt = generate_section_image(
            model_id=channel.image_model_id,
            prompt_text=background_prompt,
            aspect_ratio=channel.image_aspect_ratio,
            image_size=channel.image_size,
            channel_id=channel.channel_id,
            content_id=content_id,
            run_id=run_id,
            section_id=section_id,
            assets_dir=backgrounds_dir,
            raw_dir=raw_dir,
            cache_enabled=cache_enabled,
            background_only=True,
        )
        receipts.append(receipt)

        bg_path = backgrounds_dir / f"{section_id}.png"
        out_path = assets_ai_dir / f"{section_id}.png"
        stickman_overlay.compose_stickman_frame(
            background_path=bg_path,
            output_path=out_path,
            pose=pose,
            expression=expression,
            position="right",
        )
        receipt["out_path"] = out_path.as_posix()
        receipt["image_sha256"] = sha256_bytes(out_path.read_bytes())

        image_jobs.append(
            {
                "section_id": section_id,
                "prompt_text": background_prompt,
                "model_id": channel.image_model_id,
                "aspect_ratio": channel.image_aspect_ratio,
                "image_size": channel.image_size,
                "out_path": out_path.as_posix(),
            }
        )

    image_jobs_path = images_root / "image_jobs.json"
    jobs_obj = {
        "schema_version": "v1",
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "run_id": run_id,
        "sections_count": len(sections),
        "jobs": image_jobs,
    }
    image_jobs_path.write_text(json.dumps(jobs_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    receipts_path = images_root / "image_receipts.jsonl"
    with receipts_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in receipts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _generate_images_simple_character(
    channel: ChannelConfig,
    script: Dict[str, Any],
    run_id: str,
    content_id: str,
    images_root: Path,
    assets_ai_dir: Path,
    raw_dir: Path,
    channel_raw: Dict[str, Any],
    project_root: Path,
) -> None:
    """simple_character 채널: 배경만 Gemini(캐시) → simple_character 오버레이 → assets_ai."""
    sections = script.get("sections") or []
    if len(sections) != channel.sections:
        raise V8ValidationError("sections length mismatch during image generation")

    backgrounds_dir = images_root / "backgrounds"
    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    cache_enabled = bool(channel_raw.get("image_cache_enabled", True))
    image_jobs: List[Dict[str, Any]] = []
    receipts: List[Dict[str, Any]] = []

    for idx, section in enumerate(sections, start=1):
        section_id = f"section_{idx:03d}"
        background_prompt = section.get("background_prompt") or section.get("asset_prompt") or ""
        pose = str(section.get("character_pose") or "idle")
        expression = str(section.get("character_expression") or "neutral")
        layout = str(section.get("character_layout") or "right")
        if layout not in ("left", "right", "center"):
            layout = "right"

        receipt = generate_section_image(
            model_id=channel.image_model_id,
            prompt_text=background_prompt,
            aspect_ratio=channel.image_aspect_ratio,
            image_size=channel.image_size,
            channel_id=channel.channel_id,
            content_id=content_id,
            run_id=run_id,
            section_id=section_id,
            assets_dir=backgrounds_dir,
            raw_dir=raw_dir,
            cache_enabled=cache_enabled,
            background_only=True,
        )
        receipts.append(receipt)

        bg_path = backgrounds_dir / f"{section_id}.png"
        out_path = assets_ai_dir / f"{section_id}.png"
        simple_character_overlay.compose_simple_character_frame(
            background_path=bg_path,
            output_path=out_path,
            pose=pose,
            expression=expression,
            layout=layout,
            project_root=project_root,
        )
        receipt["out_path"] = out_path.as_posix()
        receipt["image_sha256"] = sha256_bytes(out_path.read_bytes())

        image_jobs.append(
            {
                "section_id": section_id,
                "prompt_text": background_prompt,
                "model_id": channel.image_model_id,
                "aspect_ratio": channel.image_aspect_ratio,
                "image_size": channel.image_size,
                "out_path": out_path.as_posix(),
            }
        )

    image_jobs_path = images_root / "image_jobs.json"
    jobs_obj = {
        "schema_version": "v1",
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "run_id": run_id,
        "sections_count": len(sections),
        "jobs": image_jobs,
    }
    image_jobs_path.write_text(json.dumps(jobs_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    receipts_path = images_root / "image_receipts.jsonl"
    with receipts_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in receipts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _generate_images(
    channel: ChannelConfig,
    style_ctx: StyleContext,
    script: Dict[str, Any],
    run_id: str,
    content_id: str,
    images_root: Path,
    assets_ai_dir: Path,
    raw_dir: Path,
    channel_raw: Optional[Dict[str, Any]] = None,
) -> None:
    sections = script.get("sections") or []
    if len(sections) != channel.sections:
        raise V8ValidationError("sections length mismatch during image generation")

    if (channel_raw or {}).get("channel_type") == "simple_character_story":
        _generate_images_simple_character(
            channel=channel,
            script=script,
            run_id=run_id,
            content_id=content_id,
            images_root=images_root,
            assets_ai_dir=assets_ai_dir,
            raw_dir=raw_dir,
            channel_raw=channel_raw or {},
            project_root=run_manager.get_project_root(),
        )
        return
    if (channel_raw or {}).get("channel_type") == "stickman_story":
        _generate_images_stickman(
            channel=channel,
            script=script,
            run_id=run_id,
            content_id=content_id,
            images_root=images_root,
            assets_ai_dir=assets_ai_dir,
            raw_dir=raw_dir,
            channel_raw=channel_raw or {},
        )
        return

    image_jobs: List[Dict[str, Any]] = []
    receipts: List[Dict[str, Any]] = []

    for idx, section in enumerate(sections, start=1):
        section_id = f"section_{idx:03d}"
        asset_prompt = section.get("asset_prompt", "")
        prefix = str(style_ctx.resolved_style.get("image_prompt_prefix", ""))
        negative = str(style_ctx.resolved_style.get("image_negative_prompt", ""))
        prompt_text = prefix + asset_prompt
        if negative:
            prompt_text += f" Avoid: {negative}"

        receipt = generate_section_image(
            model_id=channel.image_model_id,
            prompt_text=prompt_text,
            aspect_ratio=channel.image_aspect_ratio,
            image_size=channel.image_size,
            channel_id=channel.channel_id,
            content_id=content_id,
            run_id=run_id,
            section_id=section_id,
            assets_dir=assets_ai_dir,
            raw_dir=raw_dir,
        )
        receipts.append(receipt)
        image_jobs.append(
            {
                "section_id": section_id,
                "prompt_text": prompt_text,
                "model_id": channel.image_model_id,
                "aspect_ratio": channel.image_aspect_ratio,
                "image_size": channel.image_size,
                "out_path": receipt["out_path"],
            }
        )

    image_jobs_path = images_root / "image_jobs.json"
    jobs_obj = {
        "schema_version": "v1",
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "run_id": run_id,
        "sections_count": len(sections),
        "jobs": image_jobs,
    }
    image_jobs_path.write_text(json.dumps(jobs_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    receipts_path = images_root / "image_receipts.jsonl"
    with receipts_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in receipts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _build_tts_cache_key(
    voice_id: str,
    model: str,
    text: str,
    speed: str,
    language: str,
) -> str:
    raw = f"{voice_id}|{model}|{text}|{speed}|{language}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _generate_audio_and_subtitles(
    v8_root: Path,
    script: Dict[str, Any],
    target_duration_sec: float,
) -> Tuple[Dict[str, Path], Dict[str, float]]:
    """
    오디오/자막 파이프라인 (실제 활성 경로).
    - narration: section 단위 synthetic TTS + 캐시 + ffmpeg concat (copy codec)
    - bgm: 경량 reference WAV (전체 길이와 동일할 필요 없음)
    - subtitles: script 섹션 기반 균등 타임라인 (audio reanalysis 금지)
    """
    narration_path = v8_root / "narration.wav"
    bgm_path = v8_root / "bgm.wav"
    srt_path = v8_root / "subtitles.srt"
    perf_log_path = v8_root / "perf_report.log"

    def perf(message: str) -> None:
        # stdout + perf_report.log 양쪽에 PERF 로그를 남긴다.
        print(message)
        try:
            perf_log_path.parent.mkdir(parents=True, exist_ok=True)
            with perf_log_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(message + "\n")
        except Exception:
            # PERF 로깅 실패는 본 파이프라인을 막지 않는다.
            pass

    sections = script.get("sections") or []
    if not sections:
        raise V8ValidationError("script.sections must be non-empty for audio generation")

    # PERF: narration (section TTS + concat)
    perf("[PERF] narration_start")
    t_narr_start = time.monotonic()

    project_root = run_manager.get_project_root()
    cache_dir = project_root / "backend" / "cache" / "tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    n_sections = len(sections)
    per_sec = float(target_duration_sec) / float(n_sections)

    tts_cache_hits = 0
    tts_cache_misses = 0

    section_paths: List[Path] = []
    for idx, section in enumerate(sections, start=1):
        section_id = f"section_{idx:03d}"
        text = str(section.get("narration_text") or section.get("heading") or section_id)
        # 단순 synthetic TTS 파라미터 (deterministic)
        voice_id = "default_voice"
        model = "synthetic_sine"
        speed = "1.0"
        language = "ko"
        cache_key = _build_tts_cache_key(voice_id, model, text, speed, language)
        section_wav = cache_dir / f"{cache_key}.wav"

        perf(f"[PERF] narration_section_start section_id={section_id}")
        t_sec_start = time.monotonic()

        cache_hit = False
        if section_wav.is_file():
            cache_hit = True
            tts_cache_hits += 1
        else:
            # section 단위 synthetic TTS (sine) 생성
            generate_sine_wav(section_wav, per_sec, freq_hz=440.0, volume=0.25)
            tts_cache_misses += 1

        t_sec_end = time.monotonic()
        elapsed_section = t_sec_end - t_sec_start
        perf(
            f"[PERF] narration_section_done section_id={section_id} "
            f"elapsed_sec={elapsed_section:.3f} cache_hit={str(cache_hit).lower()}"
        )
        section_paths.append(section_wav)

    # ffmpeg concat demuxer로 section WAV를 단일 narration.wav로 합치기 (copy codec)
    concat_list = v8_root / "v8_narration_concat.txt"
    lines: List[str] = []
    for p in section_paths:
        p_abs = p.resolve()
        p_norm = str(p_abs).replace("\\", "/")
        lines.append(f"file '{p_norm}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    from backend.v8.render_ffmpeg import _find_ffmpeg  # type: ignore
    import subprocess

    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(narration_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    t_narr_end = time.monotonic()
    narration_duration_sec = t_narr_end - t_narr_start
    perf(f"[PERF] narration_done elapsed_sec={narration_duration_sec:.3f}")

    # PERF: bgm (경량 reference 파일)
    perf("[PERF] bgm_start")
    t_bgm_start = time.monotonic()
    # 짧은 bgm 레퍼런스 (예: 15초) - narration 전체 길이와 동일할 필요 없음
    bgm_ref_duration = min(15.0, float(target_duration_sec))
    generate_sine_wav(bgm_path, bgm_ref_duration, freq_hz=220.0, volume=0.15)
    t_bgm_end = time.monotonic()
    bgm_duration_sec = t_bgm_end - t_bgm_start
    # V8.1 BGM Activation Layer: bgm은 최종 ffmpeg 렌더에서 실제로 믹스된다.
    perf(f"[PERF] bgm_done elapsed_sec={bgm_duration_sec:.3f} bgm_used=true")

    # PERF: subtitles (script 기반 균등 timeline)
    perf("[PERF] subtitle_start")
    t_sub_start = time.monotonic()
    write_srt_for_sections(srt_path, sections, target_duration_sec)

    # 기본적인 내부 검증
    narr_dur = get_wav_duration(narration_path)
    last_end = get_srt_last_end_time(srt_path)
    if abs(narr_dur - target_duration_sec) > 2.0:
        raise V8ValidationError("narration.wav duration far from target_duration_sec")
    if not validate_srt_format(srt_path):
        raise V8ValidationError("subtitles.srt format invalid")
    if abs(last_end - target_duration_sec) > 2.0:
        raise V8ValidationError("SRT last end time far from target_duration_sec")

    t_sub_end = time.monotonic()
    subtitle_duration_sec = t_sub_end - t_sub_start
    perf(f"[PERF] subtitle_done elapsed_sec={subtitle_duration_sec:.3f}")

    paths = {
        "narration": narration_path,
        "bgm": bgm_path,
        "srt": srt_path,
    }
    stats: Dict[str, float] = {
        "narration_duration_sec": narration_duration_sec,
        "bgm_duration_sec": bgm_duration_sec,
        "subtitle_duration_sec": subtitle_duration_sec,
        "tts_cache_hits": float(tts_cache_hits),
        "tts_cache_misses": float(tts_cache_misses),
        # ffmpeg concat 1회 + 최종 렌더 1회 (render_ffmpeg에서)
        "ffmpeg_call_count": 2.0,
    }
    return paths, stats


def _build_hashes(
    run_root: Path,
    v8_root: Path,
    images_root: Path,
    assets_ai_dir: Path,
    raw_dir: Path,
) -> None:
    import glob

    # images/assets_ai_hashes.json
    assets_paths = [Path(p) for p in glob.glob(str(assets_ai_dir / "*.png"))]
    assets_hashes = build_hash_map(run_root, assets_paths)
    assets_hashes_obj = {
        "schema_version": "v1",
        "root": run_root.as_posix(),
        "files": assets_hashes,
    }
    (images_root / "assets_ai_hashes.json").write_text(
        json.dumps(assets_hashes_obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # artifact_hashes.json (V8 필수 + images/receipt/raw 전수)
    required: List[Path] = []
    required.extend(
        [
            v8_root / "script.json",
            v8_root / "narration.wav",
            v8_root / "bgm.wav",
            v8_root / "subtitles.srt",
            v8_root / "video.mp4",
            v8_root / "thumbnail.png",
            v8_root / "render_report.json",
            images_root / "image_jobs.json",
            images_root / "image_receipts.jsonl",
            images_root / "assets_ai_hashes.json",
        ]
    )
    required.extend(assets_paths)
    required.extend(Path(p) for p in glob.glob(str(raw_dir / "*.json")))

    artifact_hashes = build_hash_map(run_root, required)
    artifact_obj = {
        "schema_version": "v1",
        "root": run_root.as_posix(),
        "files": artifact_hashes,
    }
    (v8_root / "artifact_hashes.json").write_text(
        json.dumps(artifact_obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _sync_upload_package(
    channel: ChannelConfig,
    content_id: str,
    run_id: str,
    run_root: Path,
    v8_root: Path,
    style_ctx: StyleContext,
) -> Path:
    upload_dir = get_upload_dir(channel, content_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    def _copy(src_name: str, dst_name: str) -> Path:
        src = v8_root / src_name
        dst = upload_dir / dst_name
        shutil.copy2(str(src), str(dst))
        return dst

    video_dst = _copy("video.mp4", "video.mp4")
    thumb_dst = _copy("thumbnail.png", "thumbnail.png")
    script_dst = _copy("script.json", "script.json")
    title_dst = _copy("title.json", "title.json")
    desc_dst = _copy("description.txt", "description.txt")
    tags_dst = _copy("tags.json", "tags.json")

    metadata = {
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "run_id": run_id,
        "style_profile": channel.style_profile,
        "format_id": channel.format_id,
        "topic": "",
        "created_at_utc": _now_utc_iso(),
        "run_root": run_root.as_posix(),
        "upload_dir": upload_dir.as_posix(),
        "image_model_id": channel.image_model_id,
        "style_fingerprint_sha256": style_ctx.style_fingerprint_sha256,
    }
    # topic은 script.json에서 가져온다
    try:
        script = json.loads((v8_root / "script.json").read_text(encoding="utf-8"))
        metadata["topic"] = script.get("topic", "")
    except Exception:
        pass

    (upload_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    content_status = {
        "channel_id": channel.channel_id,
        "content_id": content_id,
        "status": "uploaded_pending",
        "run_id": run_id,
        "upload_dir": upload_dir.as_posix(),
        "updated_at_utc": _now_utc_iso(),
    }
    (upload_dir / "content_status.json").write_text(
        json.dumps(content_status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # content_registry 갱신 (uploaded_pending)
    artifacts = {
        "video": video_dst.as_posix(),
        "thumbnail": thumb_dst.as_posix(),
        "title": title_dst.as_posix(),
    }
    upsert_content_entry(
        channel_id=channel.channel_id,
        content_id=content_id,
        topic=metadata.get("topic", ""),
        run_id=run_id,
        upload_dir=upload_dir.as_posix(),
        status="uploaded_pending",
        artifacts=artifacts,
    )

    return upload_dir


def run_v8_pipeline(
    channel_id: str,
    content_id: Optional[str],
    topic: str,
    run_id: Optional[str],
) -> Dict[str, str]:
    """
    단일 Run에 대해 V8 전체 파이프라인 실행.
    PERF 계측은 이 함수 진입부터 완료까지의 wall-clock을 기록한다.
    """
    # v8 전체 파이프라인 PERF 시작 (stdout에 반드시 남긴다).
    print("[PERF] v8_start")
    t_v8_start = time.monotonic()

    channel = load_channel(channel_id)

    if not run_id:
        run_id = "auto_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    run_root = run_manager.get_run_dir(run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    dirs = _ensure_v8_dirs(run_root)
    v8_root = dirs["v8_root"]
    images_root = dirs["images_root"]
    assets_ai = dirs["assets_ai"]
    raw_dir = dirs["response_raw"]

    # perf_report.log 경로 (V8 run 산출물 로그)
    perf_log_path = v8_root / "perf_report.log"

    def perf(message: str) -> None:
        # stdout + perf_report.log 양쪽에 PERF 로그를 남긴다.
        print(message)
        try:
            perf_log_path.parent.mkdir(parents=True, exist_ok=True)
            with perf_log_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(message + "\n")
        except Exception:
            # PERF 로깅 실패는 본 파이프라인을 막지 않는다.
            pass

    # V7.5 Style Policy Layer: build and save style_policy.json before V8 execution
    audience = getattr(channel, "niche", "") or ""
    t_script_start = time.monotonic()
    try:
        print("[STEP06] loading registries")
        load_style_registries()
        print("[STEP06] registries loaded")
        print("[STEP06] building style policy")
        policy = build_style_policy(topic=topic, keyword=topic, audience=audience or None)
        print(f"[STEP06] selected channel_style_id={policy['channel_style_id']}")
        print(f"[STEP06] selected image_style_id={policy['image_style_id']}")
        print(f"[STEP06] selected thumbnail_style_id={policy['thumbnail_style_id']}")
        print(f"[STEP06] selected prompt_system_id={policy['prompt_system_id']}")
        print(f"[STEP06] policy_fingerprint={policy['policy_fingerprint']}")
        style_policy_path = v8_root / "style_policy.json"
        save_style_policy(policy, str(style_policy_path))
        print(f"[STEP06] style policy saved path={style_policy_path}")
    except Exception as e:
        policy = ensure_style_policy_for_v8(v8_root, topic, topic, audience)
    t_script_end = time.monotonic()
    script_duration_sec = t_script_end - t_script_start
    perf(f"[PERF] script_done elapsed_sec={script_duration_sec:.3f}")

    update_render_state(run_root, run_id, V8Stage.INIT)

    # 스타일 스냅샷/락 생성
    style_ctx = create_style_snapshot_and_lock(run_root, channel.style_profile)

    # content_id 확정
    content_id_final = resolve_content_id(channel, content_id)
    channel_raw = _get_channel_raw(channel.channel_id)

    # script.json 생성 (simple_character / 스틱맨 채널은 Gemini 3 Flash 1회 호출로 스토리 패키지 생성)
    if channel_raw.get("channel_type") == "simple_character_story":
        script = _build_script_json_simple_character(
            channel=channel,
            topic=topic,
            content_id=content_id_final,
            channel_raw=channel_raw,
        )
    elif channel_raw.get("channel_type") == "stickman_story":
        script = _build_script_json_stickman(
            channel=channel,
            topic=topic,
            content_id=content_id_final,
            channel_raw=channel_raw,
        )
    else:
        script = _build_script_json(channel, style_ctx, topic, content_id_final)
    script_path = v8_root / "script.json"
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    update_render_state(run_root, run_id, V8Stage.SCRIPT_BUILT)

    # 이미지 생성 (Gemini; 스틱맨은 배경만 Gemini + 캐시 + 스틱맨 오버레이)
    t_images_start = time.monotonic()
    _generate_images(
        channel=channel,
        style_ctx=style_ctx,
        script=script,
        run_id=run_id,
        content_id=content_id_final,
        images_root=images_root,
        assets_ai_dir=assets_ai,
        raw_dir=raw_dir,
        channel_raw=channel_raw,
    )
    t_images_end = time.monotonic()
    image_duration_sec = t_images_end - t_images_start
    perf(f"[PERF] images_done elapsed_sec={image_duration_sec:.3f}")
    update_render_state(run_root, run_id, V8Stage.IMAGES_GENERATED)

    # 오디오/자막 생성
    # (_generate_audio_and_subtitles 내부에서 section 단위 PERF 로그 및 perf_report.log를 남긴다.)
    audio_paths, audio_stats = _generate_audio_and_subtitles(
        v8_root=v8_root,
        script=script,
        target_duration_sec=channel.target_duration_sec,
    )
    update_render_state(run_root, run_id, V8Stage.AUDIO_GENERATED)
    update_render_state(run_root, run_id, V8Stage.SUBTITLES_GENERATED)

    # 비디오 렌더
    image_files = sorted(list(assets_ai.glob("*.png")))
    if len(image_files) != len(script.get("sections") or []):
        raise V8ValidationError("assets_ai image count mismatch with sections_count")
    video_path = v8_root / "video.mp4"
    render_report_path = v8_root / "render_report.json"
    perf("[PERF] render_start")
    t_render_start = time.monotonic()
    try:
        # V8.1 BGM Activation Layer: narration + bgm를 함께 mix하여 최종 렌더를 수행한다.
        render_video(
            channel_id=channel_id,
            images=image_files,
            narration_wav=audio_paths["narration"],
            target_duration_sec=channel.target_duration_sec,
            output_path=video_path,
            report_path=render_report_path,
            bgm_wav=audio_paths.get("bgm"),
        )
    except FileNotFoundError as e:
        # ffmpeg 미발견은 상위에서 exit 71로 변환
        raise V8FFmpegNotFound(str(e)) from e
    t_render_end = time.monotonic()
    render_duration_sec = t_render_end - t_render_start
    perf(f"[PERF] render_done elapsed_sec={render_duration_sec:.3f}")
    update_render_state(run_root, run_id, V8Stage.VIDEO_RENDERED)

    # 썸네일 생성
    # 섹션_001 이미지를 기준으로 사용
    base_image = assets_ai / "section_001.png"
    title_json = json.loads((v8_root / "title.json").read_text(encoding="utf-8")) if (v8_root / "title.json").exists() else None
    if title_json:
        selected_title = title_json.get("selected_title", "")
    else:
        selected_title = script.get("title_candidates", [""])[0]

    # CTR 패키지 먼저 생성 (title.json이 썸네일 텍스트 소스)
    ctr_paths = _build_ctr_package(
        v8_root=v8_root,
        script=script,
        style_ctx=style_ctx,
        channel=channel,
        content_id=content_id_final,
        topic=topic,
    )
    selected_title = json.loads(
        ctr_paths["title"].read_text(encoding="utf-8")
    ).get("selected_title", selected_title)

    thumb_path = v8_root / "thumbnail.png"
    try:
        build_thumbnail(
            channel_id=channel_id,
            base_image=base_image,
            title_text=selected_title,
            channel_config={
                "thumbnail_text_enabled": channel.thumbnail_text_enabled,
                "thumbnail_text_policy": channel.thumbnail_text_policy,
                "thumbnail_font_candidates": channel.thumbnail_font_candidates,
            },
            output_path=thumb_path,
        )
    except FileNotFoundError as e:
        raise V8ValidationError(str(e)) from e
    update_render_state(run_root, run_id, V8Stage.THUMBNAIL_BUILT)

    # V8.5: Thumbnail/Title Variant Builder (thin overlay layer)
    # Keep existing core outputs unchanged; only generate variants/.
    run_variant_builder_builder(channel_id=channel_id, v8_root=v8_root, run_id=run_id)

    # 해시 집합 생성
    perf("[PERF] hashes_start")
    t_hashes_start = time.monotonic()
    _build_hashes(
        run_root=run_root,
        v8_root=v8_root,
        images_root=images_root,
        assets_ai_dir=assets_ai,
        raw_dir=raw_dir,
    )
    t_hashes_end = time.monotonic()
    hashes_duration_sec = t_hashes_end - t_hashes_start
    perf(f"[PERF] hashes_done elapsed_sec={hashes_duration_sec:.3f}")

    update_render_state(run_root, run_id, V8Stage.PACKAGE_BUILT)

    # 업로드 패키지 동기화 + content_registry 기록
    upload_dir = _sync_upload_package(
        channel=channel,
        content_id=content_id_final,
        run_id=run_id,
        run_root=run_root,
        v8_root=v8_root,
        style_ctx=style_ctx,
    )
    update_render_state(run_root, run_id, V8Stage.UPLOAD_SYNCED)

    t_v8_end = time.monotonic()
    total_duration_sec = t_v8_end - t_v8_start
    perf(f"[PERF] tts_cache_hits={int(audio_stats.get('tts_cache_hits', 0.0))} "
         f"tts_cache_misses={int(audio_stats.get('tts_cache_misses', 0.0))}")
    perf(f"[PERF] ffmpeg_call_count={int(audio_stats.get('ffmpeg_call_count', 0.0))}")
    perf(f"[PERF] v8_total elapsed_sec={total_duration_sec:.3f}")

    # render_report.json에 PERF 요약 필드 추가
    try:
        if render_report_path.is_file():
            report = json.loads(render_report_path.read_text(encoding="utf-8"))
        else:
            report = {}
    except Exception:
        report = {}

    report["perf_enabled"] = True
    report["total_duration_sec"] = total_duration_sec
    report["script_duration_sec"] = script_duration_sec
    report["image_duration_sec"] = image_duration_sec
    report["narration_duration_sec"] = float(audio_stats.get("narration_duration_sec", 0.0))
    report["bgm_duration_sec"] = float(audio_stats.get("bgm_duration_sec", 0.0))
    report["subtitle_duration_sec"] = float(audio_stats.get("subtitle_duration_sec", 0.0))
    report["render_duration_sec"] = render_duration_sec
    report["hashes_duration_sec"] = hashes_duration_sec
    report["tts_cache_hits"] = int(audio_stats.get("tts_cache_hits", 0.0))
    report["tts_cache_misses"] = int(audio_stats.get("tts_cache_misses", 0.0))
    report["ffmpeg_call_count"] = int(audio_stats.get("ffmpeg_call_count", 0.0))
    # V8.1 BGM Activation Layer: bgm은 최종 ffmpeg 렌더에서 실제로 사용된다.
    report["bgm_used"] = True
    # PERF 텍스트 로그가 perf_report.log 및 stdout에 모두 기록되었음을 나타내는 플래그
    report["perf_log_emitted"] = True

    render_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "channel_id": channel.channel_id,
        "content_id": content_id_final,
        "run_id": run_id,
        "run_root": run_root.as_posix(),
        "v8_dir": v8_root.as_posix(),
        "upload_dir": upload_dir.as_posix(),
    }


