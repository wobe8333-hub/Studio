"""Track A — Narrative: 주제 → 훅 추출 → 스크립트 → 제목/썸네일 3 변형 (최적화 ③ 자동 A/B)"""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.core.llm_client import call_llm
from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

_SCRIPT_SYSTEM_PROMPT = """\
당신은 두들 애니메이션 YouTube 채널 전문 스크립트 작가입니다.
{channel_name} 채널({genre})용 롱폼 스크립트를 작성하세요.

규칙:
- 형식: [나레이터] 대사 / [게스트] 대사 번갈아 작성
- 오프닝 훅: 처음 12초 안에 핵심 궁금증 유발
- 총 분량: 7~10분 (약 1,400~2,000자)
- 챕터 구분: ## 챕터명 형식으로 3~5개
- 마지막은 구독 유도 문구로 마무리
"""

_TITLE_SYSTEM_PROMPT = """\
당신은 YouTube CTR 최적화 전문가입니다.
아래 스크립트를 기반으로 제목 3가지를 생성하세요. (각각 다른 훅 타입 사용)
훅 타입: curiosity_gap(궁금증), shocking(충격), list(목록), how_to(방법), question(질문)
각 제목은 30자 이내, 한국어.
"""

CHANNEL_GENRES = {
    "CH1": ("경제", "경제/재테크"),
    "CH2": ("과학", "과학/자연"),
    "CH3": ("부동산", "부동산/투자"),
    "CH4": ("심리", "심리/마음"),
    "CH5": ("미스터리", "미스터리/초자연"),
    "CH6": ("역사", "역사/문화"),
    "CH7": ("전쟁사", "전쟁/군사"),
}


async def run_track_a(job: "EpisodeJob") -> dict:
    """Track A: 스크립트 + 제목 3변형 + 썸네일 프롬프트 생성.

    Returns: {"script_text": str, "titles": list[str], "thumbnail_prompts": list[str],
              "hook_type": str, "opening_hook_sec": int}
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id
    ch_name, genre = CHANNEL_GENRES.get(channel_id, ("채널", "일반"))

    logger.info(f"Track A 시작: {channel_id} / {job.topic}")

    script_prompt = f"주제: {job.topic}\n채널: {ch_name} ({genre})"
    system = _SCRIPT_SYSTEM_PROMPT.format(channel_name=ch_name, genre=genre)

    script_text = await call_llm(system=system, user=script_prompt, max_tokens=3000)
    logger.info(f"Track A: 스크립트 생성 완료 ({len(script_text)}자)")

    title_prompt = f"스크립트:\n{script_text[:500]}...\n\n제목 3가지 JSON 배열로만 출력:"
    title_raw = await call_llm(system=_TITLE_SYSTEM_PROMPT, user=title_prompt, max_tokens=200)

    import json
    import re
    titles: list[str] = []
    try:
        m = re.search(r'\[.*?\]', title_raw, re.DOTALL)
        if m:
            titles = json.loads(m.group())
    except Exception:
        pass
    if not titles:
        titles = [f"{job.topic} — 당신이 몰랐던 진실", f"충격! {job.topic}의 비밀", f"왜 {job.topic}가 중요한가?"]

    hook_type = _detect_hook_type(titles[0] if titles else "")
    meta.features.title_hook_type = hook_type
    meta.features.opening_hook_sec = 12

    thumbnail_prompts = _generate_thumbnail_prompts(job.topic, ch_name, titles)

    meta.title = titles[0] if titles else job.topic

    logger.info(f"Track A 완료: {len(titles)}개 제목, hook_type={hook_type}")
    return {
        "script_text": script_text,
        "titles": titles,
        "thumbnail_prompts": thumbnail_prompts,
        "hook_type": hook_type,
        "opening_hook_sec": 12,
    }


def _detect_hook_type(title: str) -> str:
    if "?" in title:
        return "question"
    if any(w in title for w in ["충격", "놀라운", "믿기지", "비밀"]):
        return "shocking"
    if any(c.isdigit() for c in title):
        return "list"
    if any(w in title for w in ["방법", "하는 법", "하는 방법"]):
        return "how_to"
    return "curiosity_gap"


def _generate_thumbnail_prompts(topic: str, ch_name: str, titles: list[str]) -> list[str]:
    """썸네일 3 변형 이미지 프롬프트 생성 — Gemini nano-banana에 전달용."""
    base = f"두들 애니메이션 스타일, 크래프트 페이퍼 배경, 2px 라인, 5등신 캐릭터, {ch_name} 채널"
    prompts = [
        f"{base}, 놀란 표정 캐릭터가 '{titles[0][:15]}' 텍스트를 가리키는 구도, 강렬한 빨간 포인트 텍스트",
        f"{base}, 캐릭터가 차트/그래프를 설명하는 구도, '{topic}' 핵심 키워드 강조, 궁금증 유발",
        f"{base}, 질문형 구도 — 캐릭터가 물음표를 들고 있음, 깔끔한 흰 배경 강조, 클릭 유도",
    ]
    return prompts[:3]
