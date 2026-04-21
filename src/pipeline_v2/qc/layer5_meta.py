"""QC Layer 5 — 메타데이터 JSON Schema 검증 (제목·태그·설명·썸네일 필수값)"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

TITLE_MIN_LEN = 10
TITLE_MAX_LEN = 100
DESCRIPTION_MIN_LEN = 100
TAG_MIN_COUNT = 5
TAG_MAX_COUNT = 500
TAG_TOTAL_MAX_LEN = 500


def _check_title(title: str) -> list[str]:
    issues = []
    if not title or not title.strip():
        issues.append("제목 없음")
        return issues
    if len(title) < TITLE_MIN_LEN:
        issues.append(f"제목 너무 짧음: {len(title)}자 (최소 {TITLE_MIN_LEN}자)")
    if len(title) > TITLE_MAX_LEN:
        issues.append(f"제목 너무 김: {len(title)}자 (최대 {TITLE_MAX_LEN}자)")
    return issues


def _check_description(description: str) -> list[str]:
    issues = []
    if not description or not description.strip():
        issues.append("설명 없음")
        return issues
    if len(description) < DESCRIPTION_MIN_LEN:
        issues.append(f"설명 너무 짧음: {len(description)}자 (최소 {DESCRIPTION_MIN_LEN}자)")
    return issues


def _check_tags(tags: list[str]) -> list[str]:
    issues = []
    if not tags:
        issues.append("태그 없음")
        return issues
    if len(tags) < TAG_MIN_COUNT:
        issues.append(f"태그 부족: {len(tags)}개 (최소 {TAG_MIN_COUNT}개)")
    total_len = sum(len(t) for t in tags)
    if total_len > TAG_TOTAL_MAX_LEN:
        issues.append(f"태그 총 길이 초과: {total_len}자 (최대 {TAG_TOTAL_MAX_LEN}자)")
    return issues


def _check_thumbnails(thumbnail_prompts: list[str] | None, channel_id: str, episode_id: str) -> list[str]:
    issues = []
    if not thumbnail_prompts or len(thumbnail_prompts) < 3:
        count = len(thumbnail_prompts) if thumbnail_prompts else 0
        issues.append(f"썸네일 변형 부족: {count}개 (최소 3개 — Thumbnail Experiments용)")

    thumb_dir = Path(f"runs/pipeline_v2/{episode_id}/thumbnails")
    if thumb_dir.exists():
        thumb_files = list(thumb_dir.glob("thumbnail_*.png"))
        if len(thumb_files) < 3:
            issues.append(f"썸네일 파일 부족: {len(thumb_files)}개 (최소 3개)")
    return issues


def run_layer5(meta: EpisodeMeta, upload_meta: dict) -> dict:
    """QC Layer 5: 업로드 메타데이터 전체 검증.

    upload_meta 기대 구조:
    {
        "title": str,
        "description": str,
        "tags": [str],
        "thumbnail_prompts": [str],  # 3종 필수
        "category_id": str,
    }

    Returns: {"passed": bool, "issues": [str], "meta_summary": dict}
    """
    issues: list[str] = []

    title = upload_meta.get("title", "")
    issues.extend(_check_title(title))

    description = upload_meta.get("description", "")
    issues.extend(_check_description(description))

    tags = upload_meta.get("tags", [])
    issues.extend(_check_tags(tags))

    thumbnail_prompts = upload_meta.get("thumbnail_prompts")
    issues.extend(_check_thumbnails(thumbnail_prompts, meta.channel_id, meta.episode_id))

    if not upload_meta.get("category_id"):
        issues.append("카테고리 ID 없음")

    meta.features.meta_validation_passed = len(issues) == 0

    passed = len(issues) == 0
    result = {
        "passed": passed,
        "issues": issues,
        "meta_summary": {
            "title_len": len(title),
            "description_len": len(description),
            "tag_count": len(tags),
            "thumbnail_variants": len(thumbnail_prompts) if thumbnail_prompts else 0,
        },
    }
    logger.info(f"QC Layer5: passed={passed} title={len(title)}자 tags={len(tags)}개 ({meta.episode_id})")
    return result
