"""Step08 서브모듈 — YouTube 메타데이터 생성 (제목 후보 / 설명 / 태그).

run_step08 오케스트레이터에서 분리된 순수 메타데이터 생성 책임을 담당한다.
"""
import shutil
from pathlib import Path

from loguru import logger

from src.core.config import CHANNEL_CATEGORY_KO, CHANNELS_DIR
from src.core.ssot import now_iso, write_json


def generate_metadata(channel_id: str, run_id: str, script: dict,
                      step08_dir: Path, topic: dict) -> None:
    """YouTube 업로드용 메타데이터 파일들을 생성한다.

    생성 파일:
    - step08/title.json          — 제목 후보 목록
    - step08/description.txt     — 업로드 설명 (면책조항 + 제휴링크 포함)
    - step08/tags.json            — SEO 태그 15개
    - step08/render_report.json  — 렌더링 요약
    - step08/style_policy.json   — 채널 스타일 정책 스냅샷
    """
    from google import genai
    from google.genai import types as genai_types

    from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
    from src.quota.gemini_quota import record_request, throttle_if_needed

    _client = genai.Client(api_key=GEMINI_API_KEY)

    # 제목 후보
    title_candidates = script.get("title_candidates", [topic.get("title", "제목 없음")])
    write_json(step08_dir / "title.json", {
        "title_candidates": title_candidates,
        "selected": title_candidates[0] if title_candidates else "",
    })

    # 설명
    seo = script.get("seo", {})
    desc_first = seo.get("description_first_2lines", "")

    # chapter_markers 포맷: [{"time": "00:00", "title": "인트로"}, ...] 또는 ["00:00 인트로", ...]
    chapters = seo.get("chapter_markers", [])
    chapter_block = ""
    if chapters:
        lines = []
        for c in chapters:
            if isinstance(c, dict):
                lines.append(f"{c.get('time', '00:00')} {c.get('title', '')}")
            else:
                lines.append(str(c))
        chapter_block = "\n\n" + "\n".join(lines)

    description = (
        f"{desc_first}"
        f"{chapter_block}\n\n"
        f"▼ 관련 링크\n"
        f"─────────────────────────────\n"
        f"🔗 {script.get('affiliate_insert', {}).get('text', '')}\n\n"
        f"⚠️ {script.get('financial_disclaimer', '') or script.get('medical_disclaimer', '') or ''}\n\n"
        f"{script.get('ai_label', '이 영상은 AI가 제작에 참여했습니다.')}"
    )
    (step08_dir / "description.txt").write_text(description, encoding="utf-8")

    # 태그 (Gemini API 호출)
    throttle_if_needed()
    record_request()
    category_ko = CHANNEL_CATEGORY_KO.get(channel_id, channel_id)
    tag_prompt = (
        f"YouTube 영상 태그 15개를 한국어와 영어로 섞어 콤마로 구분하여 나열하시오. "
        f"주제: {topic.get('title', '')} 카테고리: {category_ko}"
    )
    tag_response = _client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=tag_prompt,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=2000,
        ),
    )
    # Thinking 모델 대응 — parts 순회하여 텍스트 추출
    try:
        raw_tags = tag_response.text
    except (ValueError, AttributeError):
        parts = tag_response.candidates[0].content.parts if tag_response.candidates else []
        texts = [p.text for p in parts if hasattr(p, "text") and p.text]
        raw_tags = texts[-1] if texts else ""
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()][:15]
    write_json(step08_dir / "tags.json", {"tags": tags})
    logger.debug(f"[METADATA] {channel_id}/{run_id} 태그 {len(tags)}개 생성 완료")

    # 렌더링 요약
    write_json(step08_dir / "render_report.json", {
        "run_id": run_id,
        "channel_id": channel_id,
        "render_completed_at": now_iso(),
        "bgm_used": False,
        "bgm_category_tone": "",
        "video_spec": script.get("video_spec", {}),
        "target_duration_sec": script.get("target_duration_sec", 720),
        "sections_count": len(script.get("sections", [])),
        "manim_sections": len(
            [s for s in script.get("sections", []) if s.get("render_tool") == "manim"]
        ),
    })

    # 채널 스타일 정책 스냅샷
    style_src = CHANNELS_DIR / channel_id / "style_policy_master.json"
    if style_src.exists():
        shutil.copy2(style_src, step08_dir / "style_policy.json")
