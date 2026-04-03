"""
STEP 12 — YouTube Shorts 업로더.

Phase 7 추가:
  9:16 Shorts 영상을 YouTube Shorts 전용 설정으로 업로드.
  해시태그 자동 생성, #Shorts 태그 삽입.
"""

from pathlib import Path
from loguru import logger

from src.core.ssot import write_json, now_iso
from src.core.config import CHANNEL_IDS, CHANNEL_CATEGORIES, CHANNEL_CATEGORY_KO

# 카테고리별 Shorts 해시태그
SHORTS_HASHTAGS = {
    "economy":     ["#경제", "#재테크", "#금융", "#Shorts", "#경제상식"],
    "realestate":  ["#부동산", "#아파트", "#투자", "#Shorts", "#부동산상식"],
    "psychology":  ["#심리학", "#자기개발", "#심리", "#Shorts", "#심리상식"],
    "mystery":     ["#미스터리", "#괴담", "#미해결사건", "#Shorts", "#미스터리쇼츠"],
    "war_history": ["#전쟁사", "#역사", "#세계대전", "#Shorts", "#역사쇼츠"],
    "science":     ["#과학", "#우주", "#과학상식", "#Shorts", "#과학쇼츠"],
    "history":     ["#역사", "#세계사", "#한국사", "#Shorts", "#역사쇼츠"],
}


def upload_shorts(
    channel_id: str,
    run_id: str,
    shorts_paths: list,
    script: dict,
) -> list:
    """
    Shorts 파일들을 YouTube에 업로드.

    Args:
        channel_id: CH1~CH7
        run_id: 실행 ID
        shorts_paths: Shorts 파일 경로 리스트
        script: step08 스크립트 dict

    Returns:
        업로드된 video_id 리스트
    """
    from src.quota.youtube_quota import check_quota, record_upload

    category = CHANNEL_CATEGORIES.get(channel_id, "")
    category_ko = CHANNEL_CATEGORY_KO.get(channel_id, "")
    hashtags = SHORTS_HASHTAGS.get(category, ["#Shorts"])

    # 제목 후보에서 첫 번째 선택
    title_candidates = script.get("title_candidates", [])
    base_title = title_candidates[0] if title_candidates else script.get("topic", "알아두면 유용한 상식")

    uploaded_ids = []

    for i, shorts_path in enumerate(shorts_paths):
        shorts_path = Path(shorts_path)
        if not shorts_path.exists():
            logger.warning(f"[ShortsUpload] 파일 없음: {shorts_path}")
            continue

        if not check_quota():
            logger.warning("[ShortsUpload] YouTube API 쿼터 초과 — 업로드 중단")
            break

        # Shorts 제목 (최대 100자)
        shorts_title = f"[{i+1}편] {base_title} {' '.join(hashtags[:2])}"
        if len(shorts_title) > 95:
            shorts_title = shorts_title[:92] + "..."

        # 설명 (해시태그 포함)
        description = (
            f"{script.get('promise', '')}\n\n"
            f"{' '.join(hashtags)}\n\n"
            f"🤖 AI 귀여운 애니메이션 지식 채널 — {category_ko}\n"
            f"{script.get(list({v: k for k, v in {'financial_disclaimer': 'CH1', 'investment_disclaimer': 'CH2', 'psychology_disclaimer': 'CH3', 'mystery_disclaimer': 'CH4', 'history_disclaimer': 'CH5', 'science_disclaimer': 'CH6'}.get(channel_id, '')}.items())[0] if False else 'ai_label', '')}"
        )

        try:
            video_id = _upload_to_youtube(
                channel_id=channel_id,
                video_path=shorts_path,
                title=shorts_title,
                description=description,
                tags=hashtags,
            )
            if video_id:
                record_upload()
                uploaded_ids.append(video_id)
                logger.info(f"[ShortsUpload] {channel_id} Shorts {i+1} 업로드: {video_id}")
        except Exception as e:
            logger.error(f"[ShortsUpload] {shorts_path.name} 업로드 실패: {e}")

    return uploaded_ids


def _upload_to_youtube(
    channel_id: str,
    video_path: Path,
    title: str,
    description: str,
    tags: list,
) -> str:
    """YouTube Data API v3로 Shorts 업로드."""
    from src.core.config import YOUTUBE_API_KEY

    if not YOUTUBE_API_KEY:
        logger.debug("[ShortsUpload] YouTube API 키 없음 — 시뮬레이션")
        return f"simulated_shorts_{channel_id}_{video_path.stem}"

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import json

        # credentials 파일로 인증 (OAuth2)
        creds_path = Path("credentials") / f"{channel_id}_oauth.json"
        if not creds_path.exists():
            logger.warning(f"[ShortsUpload] OAuth 크레덴셜 없음: {creds_path}")
            return ""

        from google.oauth2.credentials import Credentials
        with open(creds_path) as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)

        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": "ko",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = request.execute()
        return response.get("id", "")

    except Exception as e:
        logger.error(f"[ShortsUpload] API 업로드 오류: {e}")
        return ""


def run_shorts_upload(channel_id: str, run_id: str) -> dict:
    """pipeline.py에서 호출하는 Shorts 업로드 진입점."""
    from src.core.ssot import read_json, json_exists, get_run_dir

    run_dir = get_run_dir(channel_id, run_id)
    shorts_dir = run_dir / "step08s"
    s08 = run_dir / "step08"

    report_path = shorts_dir / "shorts_report.json"
    if not json_exists(report_path):
        logger.warning(f"[ShortsUpload] shorts_report.json 없음: {channel_id}/{run_id}")
        return {"ok": False, "reason": "no_shorts_report"}

    shorts_report = read_json(report_path)
    shorts_paths = shorts_report.get("paths", [])
    script = read_json(s08 / "script.json") if json_exists(s08 / "script.json") else {}

    uploaded = upload_shorts(channel_id, run_id, shorts_paths, script)
    result = {
        "channel_id": channel_id,
        "run_id": run_id,
        "uploaded_at": now_iso(),
        "uploaded_count": len(uploaded),
        "video_ids": uploaded,
        "ok": len(uploaded) > 0,
    }
    write_json(shorts_dir / "shorts_upload_result.json", result)
    return result
