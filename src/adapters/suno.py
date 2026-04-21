"""Suno AI BGM 생성 어댑터 (pipeline_v2 Track B)"""
import hashlib
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from src.core.ssot import write_json

SUNO_API_BASE = "https://studio-api.suno.ai/api"
SUNO_CLIP_API = "https://studio-api.suno.ai/api/gen"
BGM_PROMPTS_PATH = Path("data/config/bgm_prompts.yaml")
BGM_ASSETS_ROOT = Path("assets/bgm")
BGM_META_PATH = Path("data/config/bgm_manifest.json")

_SUPPORTED_CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]


def _get_api_key() -> str:
    key = os.getenv("SUNO_API_KEY", "")
    if not key or key == "YOUR_SUNO_API_KEY_HERE":
        raise EnvironmentError("SUNO_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return key


def _clip_id_from_prompt(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def generate_song(
    prompt: str,
    channel_id: str,
    mood_id: str,
    duration_sec: int = 120,
    output_dir: Optional[Path] = None,
) -> dict:
    """Suno API로 BGM 1곡 생성 후 로컬 저장.

    Returns:
        {"mood_id": str, "file_path": str, "bpm": int, "duration_sec": int,
         "mood_tag": str, "channel_id": str, "status": "ok"|"error"}
    """
    api_key = _get_api_key()
    if output_dir is None:
        output_dir = BGM_ASSETS_ROOT / channel_id
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"{mood_id}.mp3"
    if out_path.exists():
        logger.info(f"캐시 히트 — {out_path} 이미 존재, 생성 스킵")
        return {
            "mood_id": mood_id, "file_path": str(out_path),
            "status": "cached", "channel_id": channel_id,
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "make_instrumental": True,
        "model": "chirp-v3-5",
        "duration": duration_sec,
    }

    logger.info(f"Suno 곡 생성 시작: {channel_id}/{mood_id}")
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{SUNO_CLIP_API}", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        clip_ids = [item["id"] for item in data.get("clips", [])]
        if not clip_ids:
            raise ValueError(f"Suno API 응답에 clip ID가 없음: {data}")

        clip_id = clip_ids[0]
        audio_url = _poll_clip_url(clip_id, api_key)

        with httpx.Client(timeout=180) as client:
            audio_resp = client.get(audio_url)
            audio_resp.raise_for_status()
            out_path.write_bytes(audio_resp.content)

        logger.info(f"BGM 저장 완료: {out_path}")
        return {
            "mood_id": mood_id, "file_path": str(out_path),
            "status": "ok", "channel_id": channel_id,
        }
    except Exception as exc:
        logger.error(f"Suno 생성 실패 [{channel_id}/{mood_id}]: {exc}")
        return {"mood_id": mood_id, "status": "error", "error": str(exc), "channel_id": channel_id}


def _poll_clip_url(clip_id: str, api_key: str, max_wait_sec: int = 300) -> str:
    """생성 완료될 때까지 폴링, audio_url 반환."""
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{SUNO_API_BASE}/clip/{clip_id}", headers=headers)
            r.raise_for_status()
            clip = r.json()
        status = clip.get("status", "")
        if status == "complete" and clip.get("audio_url"):
            return clip["audio_url"]
        if status in ("error", "failed"):
            raise RuntimeError(f"Suno clip 생성 실패: {clip}")
        time.sleep(10)
    raise TimeoutError(f"Suno clip {clip_id} 생성 타임아웃 ({max_wait_sec}s)")


def select_bgm_for_episode(
    channel_id: str,
    mood_tag: str,
    fallback_mood: str = "neutral_background",
) -> Optional[str]:
    """에피소드 분위기에 맞는 BGM 파일 경로 반환.

    mood_tag가 없으면 fallback_mood 사용.
    """
    if channel_id not in _SUPPORTED_CHANNELS:
        raise ValueError(f"지원하지 않는 채널: {channel_id}")

    bgm_dir = BGM_ASSETS_ROOT / channel_id
    if not bgm_dir.exists():
        logger.warning(f"BGM 디렉토리 없음: {bgm_dir}")
        return None

    target = bgm_dir / f"{channel_id}_{mood_tag}.mp3"
    if target.exists():
        return str(target)

    fallback = bgm_dir / f"{channel_id}_{fallback_mood}.mp3"
    if fallback.exists():
        logger.warning(f"mood '{mood_tag}' 없음, fallback '{fallback_mood}' 사용")
        return str(fallback)

    all_mp3 = list(bgm_dir.glob("*.mp3"))
    if all_mp3:
        chosen = all_mp3[0]
        logger.warning(f"fallback도 없음, 첫 번째 파일 사용: {chosen}")
        return str(chosen)

    return None


def build_full_library(dry_run: bool = False) -> dict:
    """bgm_prompts.yaml을 읽어 175곡 전체 일괄 생성.

    dry_run=True이면 API 호출 없이 계획만 반환.
    """
    import yaml  # PyYAML

    with open(BGM_PROMPTS_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    results = {"total": 0, "success": 0, "cached": 0, "error": 0, "details": []}

    for ch_key, ch_data in config.get("channels", {}).items():
        for variation in ch_data.get("variations", []):
            results["total"] += 1
            mood_id = variation["id"]
            prompt = variation["prompt"]

            if dry_run:
                logger.info(f"[DRY RUN] {mood_id}: {prompt[:60]}...")
                results["details"].append({"mood_id": mood_id, "status": "dry_run"})
                continue

            result = generate_song(
                prompt=prompt,
                channel_id=ch_key,
                mood_id=mood_id,
            )
            results["details"].append(result)
            if result["status"] == "ok":
                results["success"] += 1
            elif result["status"] == "cached":
                results["cached"] += 1
            else:
                results["error"] += 1
            time.sleep(2)

    write_json(BGM_META_PATH, results)
    logger.info(f"BGM 라이브러리 생성 완료: {results['success']}성공 {results['cached']}캐시 {results['error']}실패")
    return results
