"""메타데이터 자동 생성기 — 스크립트 → 태그·설명·카드·종료화면 제안 (T42)"""
from __future__ import annotations

import re

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

CHANNEL_CATEGORY_MAP = {
    "CH1": "경제",
    "CH2": "과학",
    "CH3": "부동산",
    "CH4": "심리",
    "CH5": "미스터리",
    "CH6": "역사",
    "CH7": "전쟁사",
}

CHANNEL_YT_CATEGORY_ID = {
    "CH1": "22",
    "CH2": "28",
    "CH3": "22",
    "CH4": "22",
    "CH5": "22",
    "CH6": "22",
    "CH7": "22",
}

CHANNEL_SEO_TAGS = {
    "CH1": ["경제", "금융", "투자", "주식", "부동산", "금리", "인플레이션", "경제상식"],
    "CH2": ["과학", "우주", "물리", "화학", "생물", "과학상식", "양자역학", "블랙홀"],
    "CH3": ["부동산", "아파트", "청약", "전세", "월세", "부동산투자", "재테크", "집값"],
    "CH4": ["심리학", "심리", "인간관계", "행동심리", "자기계발", "동기부여", "마음"],
    "CH5": ["미스터리", "괴담", "불가사의", "음모론", "UFO", "초자연", "호러", "공포"],
    "CH6": ["역사", "한국사", "세계사", "역사상식", "역사이야기", "근현대사"],
    "CH7": ["전쟁사", "세계대전", "군사", "역사전쟁", "무기", "전략", "전술", "군사역사"],
}


def _extract_keywords(script: str, max_keywords: int = 10) -> list[str]:
    """스크립트에서 핵심 키워드 추출 (빈도 기반)."""
    words = re.findall(r"[가-힣a-zA-Z]{2,}", script)
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    stop_words = {"그리고", "하지만", "이것은", "그것은", "있습니다", "했습니다", "됩니다", "이런", "저런", "이렇게"}
    sorted_words = sorted(
        [(w, c) for w, c in freq.items() if w not in stop_words and len(w) >= 2],
        key=lambda x: x[1],
        reverse=True,
    )
    return [w for w, _ in sorted_words[:max_keywords]]


def _build_description(
    title: str,
    script: str,
    channel_id: str,
    series_name: str | None,
) -> str:
    """YouTube 설명란 자동 생성."""
    category = CHANNEL_CATEGORY_MAP.get(channel_id, "")
    script_preview = script[:300].replace("\n", " ").strip()
    if len(script) > 300:
        script_preview += "..."

    series_line = f"\n📚 시리즈: {series_name}" if series_name else ""
    description = f"""{title}

{script_preview}
{series_line}

━━━━━━━━━━━━━━━━━━━━
📌 이 채널은 {category} 주제를 두들 애니메이션으로 쉽고 재미있게 전달합니다.
🔔 구독과 좋아요는 더 좋은 콘텐츠를 만드는 데 큰 힘이 됩니다!

#두들애니메이션 #{category} #loomix
━━━━━━━━━━━━━━━━━━━━
"""
    return description.strip()


def generate_upload_meta(
    meta: EpisodeMeta,
    title: str,
    script: str,
    thumbnail_prompts: list[str],
) -> dict:
    """업로드 메타데이터 완전체 생성.

    Returns: {title, description, tags, thumbnail_prompts, category_id, card_timestamps}
    """
    channel_id = meta.channel_id
    keywords = _extract_keywords(script)
    channel_tags = CHANNEL_SEO_TAGS.get(channel_id, [])

    tags = list(dict.fromkeys(keywords + channel_tags))[:30]

    description = _build_description(title, script, channel_id, meta.series_id)
    category_id = CHANNEL_YT_CATEGORY_ID.get(channel_id, "22")

    duration = meta.features.duration_sec or 300
    card_timestamps = [
        int(duration * 0.3),
        int(duration * 0.6),
        int(duration * 0.85),
    ]

    upload_meta = {
        "title": title,
        "description": description,
        "tags": tags,
        "thumbnail_prompts": thumbnail_prompts,
        "category_id": category_id,
        "card_timestamps": card_timestamps,
        "default_language": "ko",
    }

    logger.info(f"메타 생성 완료: {meta.episode_id} title={title[:30]}... tags={len(tags)}개")
    return upload_meta
