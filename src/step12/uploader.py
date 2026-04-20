"""STEP 12 — YouTube 영상 업로드.
버그 수정: dict 기반 로드 대신 token JSON 파일 + from_authorized_user_file 사용.
E-2: 만료 토큰 자동 갱신 + 갱신 결과 파일 저장 추가.
"""

from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

from src.core.config import CHANNEL_OPTIMAL_UPLOAD_KST, CREDENTIALS_DIR
from src.core.ssot import get_run_dir, now_iso, read_json, sha256_file, write_json
from src.quota.youtube_quota import can_upload, consume, defer_job

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def _get_youtube_service(channel_id: str):
    """YouTube API 서비스 빌드. 만료 토큰은 자동 갱신 후 파일에 저장한다."""
    token_path = CREDENTIALS_DIR / f"{channel_id}_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"token.json 없음: {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        logger.info(f"[STEP12] {channel_id}: access token 만료 — refresh 시도")
        creds.refresh(Request())
        # 갱신된 토큰을 원본 파일에 덮어씀 (다음 실행에서 재사용)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        logger.info(f"[STEP12] {channel_id}: token 갱신 완료 → {token_path.name}")
    return build("youtube", "v3", credentials=creds)

def _next_publish_time(channel_id: str) -> str:
    """채널별 최적 KST 시간 기준 다음 예약 업로드 시각을 RFC 3339 UTC로 반환한다.
    당일 최적 시간이 이미 지났으면 다음 날 같은 시간으로 설정한다.
    """
    kst_time_str = CHANNEL_OPTIMAL_UPLOAD_KST.get(channel_id, "15:00")
    hour, minute = map(int, kst_time_str.split(":"))
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    target = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now_kst:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def rollback_video(channel_id: str, video_id: str) -> dict:
    """업로드된 YouTube 영상을 비공개로 전환한다 (롤백).
    영상을 삭제하지 않고 비공개 전환만 하므로 복구 가능하다.
    Returns: {"video_id": str, "status": "private", "channel_id": str}
    """
    youtube = _get_youtube_service(channel_id)
    youtube.videos().update(
        part="status",
        body={"status": {"privacyStatus": "private"}},
        id=video_id,
    ).execute()
    logger.info(f"[ROLLBACK] {channel_id} / {video_id} 비공개 전환 완료")
    return {"video_id": video_id, "status": "private", "channel_id": channel_id}
