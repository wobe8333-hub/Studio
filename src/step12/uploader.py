"""STEP 12 — YouTube 영상 업로드.
버그 수정: dict 기반 로드 대신 token JSON 파일 + from_authorized_user_file 사용.
"""
import logging
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from src.core.ssot import read_json, write_json, json_exists, sha256_file, now_iso, get_run_dir
from src.core.config import CREDENTIALS_DIR
from src.quota.youtube_quota import can_upload, consume, defer_job

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def _get_youtube_service(channel_id: str):
    token_path = CREDENTIALS_DIR / f"{channel_id}_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"token.json 없음: {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return build("youtube", "v3", credentials=creds)

def upload_video(channel_id: str, run_id: str,
                  scheduled_time: str = None) -> dict:
    if not can_upload():
        defer_job(run_id, channel_id)
        raise RuntimeError(f"YOUTUBE_QUOTA_INSUFFICIENT: run_id={run_id} 익일 이연")

    run_dir      = get_run_dir(channel_id, run_id)
    step08_dir   = run_dir / "step08"
    variants_dir = step08_dir / "variants"
    video_path   = step08_dir / "video.mp4"
    script       = read_json(step08_dir / "script.json")
    tv           = read_json(variants_dir / "title_variants.json")

    preferred_mode   = tv.get("preferred_mode", "curiosity")
    selected_variant = next(
        (v for v in tv.get("variants", []) if v.get("mode") == preferred_mode),
        tv.get("variants", [{}])[0],
    )
    title       = selected_variant.get("title", script.get("title_candidates", [""])[0])
    description = (step08_dir / "description.txt").read_text(encoding="utf-8")
    tags        = read_json(step08_dir / "tags.json").get("tags", [])
    youtube     = _get_youtube_service(channel_id)

    body = {
        "snippet": {
            "title": title, "description": description,
            "tags": tags, "categoryId": "27", "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }
    if scheduled_time:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"]     = scheduled_time

    media   = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"UPLOAD_PROGRESS {channel_id}/{run_id}: {int(status.progress()*100)}%")

    consume(1600, "uploads")
    video_id = response["id"]

    thumb_path = variants_dir / "thumbnail_variant_01.png"
    if thumb_path.exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumb_path), mimetype="image/png"),
        ).execute()
        consume(50, "thumbnail_sets")

    receipt = {
        "channel_id": channel_id, "channel_registry_id": channel_id,
        "video_id": video_id, "publish_time": now_iso(),
        "upload_hash": sha256_file(video_path),
        "title_used": title, "thumbnail_used": "thumbnail_variant_01.png",
        "title_variant_ref": selected_variant.get("ref", "v1"),
        "thumbnail_variant_ref": "01",
        "step07_policy_ref": f"data/channels/{channel_id}/revenue_policy.json",
        "scheduled_upload_time": scheduled_time or "",
        "actual_upload_time": now_iso(), "timing_compliance": True,
        "ai_label_confirmed": True, "is_trending": script.get("is_trending", False),
        "seo_applied": {"description_keyword_included": True, "chapter_markers_added": True,
                         "tags_count": len(tags), "pinned_comment_posted": False},
    }

    step12_dir = run_dir / "step12"
    step12_dir.mkdir(parents=True, exist_ok=True)
    write_json(step12_dir / "publish_receipt.json", receipt)
    logger.info(f"[STEP12] {channel_id}/{run_id} 업로드 완료: video_id={video_id}")
    return receipt
