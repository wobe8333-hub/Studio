"""YouTube Data API v3 업로드 자동화 + Thumbnail Experiments (T41)"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from src.core.ssot import read_json, write_json
from src.pipeline_v2.episode_schema import EpisodeMeta, save_episode

if TYPE_CHECKING:
    pass

YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YT_THUMBNAIL_URL = "https://www.googleapis.com/youtube/v3/thumbnails"
YT_EXPERIMENT_URL = "https://www.googleapis.com/youtube/v3/thumbnailExperiments"

UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_TIMEOUT_SEC = 3600


def _get_oauth_token(channel_id: str) -> str:
    token_path = Path(f"credentials/{channel_id}_token.json")
    if not token_path.exists():
        raise FileNotFoundError(f"OAuth 토큰 없음: {token_path}")
    token_data = read_json(token_path)
    return token_data.get("access_token", "")


def _channel_id_for(channel_code: str) -> str:
    """CH1 → 실제 YouTube 채널 ID (환경변수에서 로드)."""
    env_key = f"{channel_code}_CHANNEL_ID"
    val = os.environ.get(env_key, "")
    if not val:
        raise ValueError(f"환경변수 없음: {env_key}")
    return val


def upload_video(
    meta: EpisodeMeta,
    video_path: str,
    upload_meta: dict,
) -> str:
    """YouTube Data API v3 resumable upload.

    upload_meta 필수 키: title, description, tags, category_id
    Returns: YouTube video_id
    """
    token = _get_oauth_token(meta.channel_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(Path(video_path).stat().st_size),
    }

    snippet = {
        "title": upload_meta["title"],
        "description": upload_meta.get("description", ""),
        "tags": upload_meta.get("tags", []),
        "categoryId": upload_meta.get("category_id", "22"),
        "defaultLanguage": "ko",
        "defaultAudioLanguage": "ko",
    }
    body = {
        "snippet": snippet,
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    with httpx.Client(timeout=60) as client:
        init_resp = client.post(
            f"{YT_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers=headers,
            json=body,
        )
        init_resp.raise_for_status()
        upload_url = init_resp.headers.get("Location", "")

    if not upload_url:
        raise RuntimeError("업로드 URL을 얻지 못했습니다.")

    video_id = _upload_chunks(video_path, upload_url, token)
    logger.info(f"YouTube 업로드 완료: {meta.episode_id} → video_id={video_id}")
    return video_id


def _upload_chunks(video_path: str, upload_url: str, token: str) -> str:
    """청크 단위 업로드 → video_id 반환."""
    file_size = Path(video_path).stat().st_size
    uploaded = 0

    with open(video_path, "rb") as f, httpx.Client(timeout=UPLOAD_TIMEOUT_SEC) as client:
        while uploaded < file_size:
            chunk = f.read(UPLOAD_CHUNK_SIZE)
            end_byte = uploaded + len(chunk) - 1
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {uploaded}-{end_byte}/{file_size}",
            }
            resp = client.put(upload_url, headers=headers, content=chunk)

            if resp.status_code in (200, 201):
                video_id = resp.json().get("id", "")
                return video_id
            elif resp.status_code == 308:
                uploaded = end_byte + 1
                logger.debug(f"업로드 진행: {uploaded}/{file_size} bytes")
            else:
                raise RuntimeError(f"업로드 청크 실패: {resp.status_code} {resp.text[:200]}")

    raise RuntimeError("파일 업로드 완료 응답 없음")


def upload_thumbnail_experiments(
    video_id: str,
    channel_id: str,
    thumbnail_paths: list[str],
) -> bool:
    """YouTube Thumbnail Experiments API — 3종 썸네일 동시 등록.

    YouTube가 72h 내 최고 CTR 변형 자동 채택.
    Returns: True if all thumbnails registered successfully
    """
    if len(thumbnail_paths) < 3:
        logger.warning(f"썸네일 변형 부족: {len(thumbnail_paths)}개 (최소 3개 필요)")
        return False

    token = _get_oauth_token(channel_id)
    success_count = 0

    for i, thumb_path in enumerate(thumbnail_paths[:3], 1):
        if not Path(thumb_path).exists():
            logger.warning(f"썸네일 파일 없음: {thumb_path}")
            continue
        try:
            _upload_single_thumbnail(video_id, thumb_path, token, variant_index=i)
            success_count += 1
            logger.info(f"썸네일 변형 {i} 등록: video_id={video_id}")
        except Exception as e:
            logger.warning(f"썸네일 변형 {i} 등록 실패: {e}")

    return success_count >= 1


def _upload_single_thumbnail(video_id: str, thumb_path: str, token: str, variant_index: int) -> None:
    """단일 썸네일 업로드 (Thumbnail Experiments)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png",
    }
    params = {"videoId": video_id}

    with open(thumb_path, "rb") as f:
        data = f.read()

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{YT_THUMBNAIL_URL}?part=snippet",
            headers=headers,
            params=params,
            content=data,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"썸네일 업로드 실패: {resp.status_code}")


def upload_episode(
    meta: EpisodeMeta,
    video_path: str,
    upload_meta: dict,
    thumbnail_paths: list[str] | None = None,
) -> dict:
    """에피소드 업로드 전체 플로우: 영상 업로드 → 썸네일 실험 등록.

    Returns: {"video_id": str, "thumbnails_registered": bool}
    """
    video_id = upload_video(meta, video_path, upload_meta)

    thumbnails_registered = False
    if thumbnail_paths:
        thumbnails_registered = upload_thumbnail_experiments(video_id, meta.channel_id, thumbnail_paths)

    meta.features.platform_tag = "youtube_longform"
    upload_record = {
        "video_id": video_id,
        "platforms_uploaded": ["youtube_longform"],
        "platforms_ready": ["youtube_shorts", "tiktok", "ig_reels", "x"],
        "thumbnails_registered": thumbnails_registered,
        "upload_meta": {k: v for k, v in upload_meta.items() if k != "description"},
    }
    save_episode(meta)

    result_path = Path(f"runs/pipeline_v2/{meta.episode_id}/upload_result.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(result_path, upload_record)

    logger.info(f"에피소드 업로드 완료: {meta.episode_id} video_id={video_id} thumbnails={thumbnails_registered}")
    return {"video_id": video_id, "thumbnails_registered": thumbnails_registered}
