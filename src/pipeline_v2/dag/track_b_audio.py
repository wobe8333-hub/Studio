"""Track B — Audio: ElevenLabs TTS 화자별 스위칭 + Suno BGM 선곡 (최적화 ④)"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

VOICE_MAP_PATH = Path("data/config/voice_mapping.yaml")
AUDIO_ROOT = Path("runs/pipeline_v2")
PAUSE_BETWEEN_SPEAKERS_MS = 120
PAUSE_SENTENCE_MS = 80


def _load_voice_config(channel_id: str) -> dict:
    with open(VOICE_MAP_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ch = cfg["channels"].get(channel_id)
    if not ch:
        raise ValueError(f"voice_mapping.yaml에 채널 없음: {channel_id}")
    defaults = cfg.get("defaults", {})
    dialogue = cfg.get("dialogue", {})
    return {"channel": ch, "defaults": defaults, "dialogue": dialogue}


def _get_voice_id(channel_id: str, role: str) -> str:
    env_key = f"CH{channel_id[-1]}_{role.upper()}_VOICE_ID"
    voice_id = os.getenv(env_key, "")
    if not voice_id or "YOUR_" in voice_id:
        raise EnvironmentError(f"{env_key} 환경변수가 설정되지 않았습니다.")
    return voice_id


def _parse_script_segments(script_text: str) -> list[dict]:
    """스크립트를 화자 단위 세그먼트로 파싱.

    형식:
        [나레이터] 대사 내용
        [게스트] 대사 내용
    """
    segments = []
    pattern = re.compile(r"\[(나레이터|narrator|게스트|guest)\]\s*(.+?)(?=\[(?:나레이터|narrator|게스트|guest)\]|$)", re.DOTALL | re.IGNORECASE)
    for m in pattern.finditer(script_text):
        role_raw = m.group(1).lower()
        role = "narrator" if role_raw in ("나레이터", "narrator") else "guest"
        text = m.group(2).strip()
        if text:
            segments.append({"role": role, "text": text})

    if not segments:
        segments = [{"role": "narrator", "text": script_text.strip()}]
    return segments


async def _tts_segment(
    text: str,
    voice_id: str,
    stability: float,
    similarity_boost: float,
    style: float,
    output_path: Path,
) -> Path:
    """ElevenLabs TTS API 단일 세그먼트 호출."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx 설치 필요: pip install httpx")

    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    import asyncio
    loop = asyncio.get_event_loop()

    def _sync_call():
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)

    await loop.run_in_executor(None, _sync_call)
    return output_path


def _concat_segments_ffmpeg(segment_paths: list[Path], pause_ms: int, output_path: Path) -> Path:
    """FFmpeg로 세그먼트 파일들을 무음 삽입하여 연결."""
    silence_duration = pause_ms / 1000.0
    parts: list[str] = []
    for seg in segment_paths:
        # 절대 경로 사용 (작업 디렉토리 의존 제거)
        parts.append(f"file '{seg.resolve().as_posix()}'")
        parts.append(f"duration {silence_duration}")

    list_path = output_path.parent / "_seg_concat_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-ar", "44100", "-ac", "1",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat 실패: {result.stderr}")
    return output_path


async def run_track_b(job: "EpisodeJob") -> dict:
    """Track B: 나레이션 생성 + BGM 선곡.

    Returns: {"narration_path": str, "bgm_path": str, "segments": int}
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id
    script_text = job.track_a_result.output.get("script_text", "") if job.track_a_result else ""

    out_dir = AUDIO_ROOT / meta.episode_id / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    voice_cfg = _load_voice_config(channel_id)
    ch_voices = voice_cfg["channel"]
    defaults = voice_cfg["defaults"]
    dialogue = voice_cfg.get("dialogue", {})

    pause_ms = dialogue.get("pause_between_speakers_ms", PAUSE_BETWEEN_SPEAKERS_MS)

    # 스크립트 파싱
    segments = _parse_script_segments(script_text) if script_text else [
        {"role": "narrator", "text": "스크립트가 아직 준비되지 않았습니다."}
    ]
    logger.info(f"Track B: {len(segments)}개 세그먼트 감지 (채널={channel_id})")

    seg_paths: list[Path] = []
    for i, seg in enumerate(segments):
        role = seg["role"]
        voice_cfg_role = ch_voices.get(role, ch_voices["narrator"])
        voice_id = _get_voice_id(channel_id, role)

        role_defaults = defaults.get(role, defaults.get("narrator", {}))
        stability = voice_cfg_role.get("stability", role_defaults.get("stability", 0.75))
        similarity = voice_cfg_role.get("similarity_boost", role_defaults.get("similarity_boost", 0.80))
        style = voice_cfg_role.get("style", role_defaults.get("style", 0.20))

        seg_path = out_dir / f"seg_{i:03d}_{role}.mp3"
        await _tts_segment(seg["text"], voice_id, stability, similarity, style, seg_path)
        seg_paths.append(seg_path)

    narration_path = out_dir / "narration_full.mp3"
    if len(seg_paths) > 1:
        _concat_segments_ffmpeg(seg_paths, pause_ms, narration_path)
    elif seg_paths:
        import shutil
        shutil.copy(seg_paths[0], narration_path)

    narrator_vid = _get_voice_id(channel_id, "narrator")
    guest_vid = _get_voice_id(channel_id, "guest")
    meta.features.narrator_voice_id = narrator_vid
    meta.features.guest_voice_id = guest_vid
    meta.audio_path = str(narration_path)

    # BGM 선곡
    from src.adapters.suno import select_bgm_for_episode
    mood_tag = meta.features.bgm_mood_tag or "neutral_background"
    bgm_path = select_bgm_for_episode(channel_id, mood_tag)
    logger.info(f"Track B: BGM 선택 = {bgm_path}")

    return {
        "narration_path": str(narration_path),
        "bgm_path": bgm_path or "",
        "segments": len(segments),
    }
