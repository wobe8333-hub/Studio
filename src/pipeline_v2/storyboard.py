"""Storyboard — Beat Board → Shot List 변환 (T19)

Track A의 스크립트 챕터를 씬 단위 Shot List로 분해.
각 Shot은 Track C 이미지 생성의 직접 입력값이 된다.
"""
from __future__ import annotations

import re

from loguru import logger

POSE_TAG_MAP: dict[str, str] = {
    "설명": "explaining_pointing_right",
    "질문": "thinking_chin_touch",
    "놀람": "surprised_hands_up",
    "강조": "explaining_arms_open",
    "결론": "presenting_gesture_board",
    "인사": "happy_waving",
    "감정": "happy_thumbs_up",
    "우려": "concerned_frowning",
    "default": "neutral_standing",
}

INSERT_KEYWORDS: dict[str, str] = {
    "차트": "chart",
    "그래프": "chart",
    "수식": "formula",
    "방정식": "formula",
    "다이어그램": "diagram",
    "구조": "diagram",
    "분자": "diagram",
    "궤도": "diagram",
}


def _detect_pose_tag(narration_text: str) -> str:
    """나레이션 텍스트로 적합한 포즈 태그 추정."""
    for keyword, tag in POSE_TAG_MAP.items():
        if keyword in narration_text:
            return tag
    return POSE_TAG_MAP["default"]


def _detect_insert_type(narration_text: str, chapter_title: str, channel_id: str) -> str:
    """CH1/CH2 전용 — Manim 인서트 타입 감지."""
    combined = narration_text + chapter_title
    for keyword, insert_type in INSERT_KEYWORDS.items():
        if keyword in combined:
            if channel_id in ("CH1", "CH2"):
                return insert_type
    return "doodle"


def _split_narration_to_beats(narration: str, max_words_per_beat: int = 60) -> list[str]:
    """나레이션을 Beat 단위(최대 60어절)로 분할."""
    sentences = re.split(r"(?<=[.!?。！？])\s+", narration.strip())
    beats: list[str] = []
    current = ""

    for sent in sentences:
        words = sent.split()
        if len(current.split()) + len(words) > max_words_per_beat and current:
            beats.append(current.strip())
            current = sent
        else:
            current = (current + " " + sent).strip()

    if current:
        beats.append(current.strip())

    return beats


def build_storyboard(
    script: str,
    channel_id: str,
    episode_id: str,
    duration_hint_sec: int = 480,
) -> list[dict]:
    """스크립트 → Shot List (Storyboard) 변환.

    Returns: [
        {
            "scene_id": int,
            "chapter": str,
            "narration_text": str,
            "duration_sec": float,
            "insert_type": "doodle" | "chart" | "formula" | "diagram",
            "character_role": "narrator" | "guest" | "none",
            "pose_tag": str,
            "image_prompt": str,
            "chart_type": str | None,
        },
        ...
    ]
    """
    lines = script.strip().splitlines()
    chapters: list[dict] = []
    current_chapter = {"title": "intro", "lines": []}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("##") or (line.isupper() and len(line) < 40):
            if current_chapter["lines"]:
                chapters.append(current_chapter)
            current_chapter = {"title": line.lstrip("#").strip(), "lines": []}
        else:
            current_chapter["lines"].append(line)

    if current_chapter["lines"]:
        chapters.append(current_chapter)

    if not chapters:
        chapters = [{"title": "전체", "lines": lines}]

    storyboard: list[dict] = []
    scene_id = 0
    sec_per_scene = max(4.0, duration_hint_sec / max(len(chapters) * 3, 1))

    for chapter in chapters:
        chapter_text = " ".join(chapter["lines"])
        beats = _split_narration_to_beats(chapter_text)

        for beat_idx, beat_text in enumerate(beats):
            insert_type = _detect_insert_type(beat_text, chapter["title"], channel_id)
            pose_tag = _detect_pose_tag(beat_text)

            role = "narrator"
            if beat_text.startswith("[게스트]") or beat_text.startswith("[guest]"):
                role = "guest"
                beat_text = re.sub(r"^\[게스트\]|\[guest\]", "", beat_text).strip()
            elif beat_text.startswith("[나레이터]") or beat_text.startswith("[narrator]"):
                beat_text = re.sub(r"^\[나레이터\]|\[narrator\]", "", beat_text).strip()

            chart_type = None
            if insert_type == "chart" and channel_id == "CH1":
                if "비교" in beat_text or "막대" in beat_text:
                    chart_type = "bar"
                elif "비율" in beat_text or "파이" in beat_text:
                    chart_type = "pie"
                else:
                    chart_type = "line"

            image_prompt = (
                f"{channel_id} 두들 채널 — {chapter['title']} 챕터 "
                f"— '{beat_text[:50]}' 장면. {role} 캐릭터 {pose_tag} 포즈."
            )

            storyboard.append({
                "scene_id": scene_id,
                "chapter": chapter["title"],
                "narration_text": beat_text,
                "duration_sec": round(sec_per_scene, 1),
                "insert_type": insert_type,
                "character_role": role,
                "pose_tag": pose_tag,
                "image_prompt": image_prompt,
                "chart_type": chart_type,
            })
            scene_id += 1

    logger.info(f"Storyboard 생성: {episode_id} — {len(storyboard)}씬 / {len(chapters)}챕터")
    return storyboard
