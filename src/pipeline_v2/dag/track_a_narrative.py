"""Track A — Narrative: 주제 → 훅 추출 → 스크립트 → 제목/썸네일 3 변형 (최적화 ③ 자동 A/B)"""
from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING

from loguru import logger

from src.core.llm_client import generate_text
from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

# 채널별 특화 훅 스타일 (법칙 5)
_CHANNEL_TONE = {
    "CH1": "숫자·비율로 신뢰 구축. 예: '연 8% 복리면 10년 후 2.16배입니다. 지금 이 숫자를 기억하세요.'",
    "CH2": "역설·상식 파괴로 시작. 예: '사실 지구는 태양 주위를 돌지 않습니다. 정확히는 두 천체가 공통 무게중심을 함께 돕니다.'",
    "CH3": "손실 회피 심리 자극. 예: '지금 이 정보를 모르면 3년 후 2억을 잃을 수 있습니다.'",
    "CH4": "2인칭 공감 질문으로 끌어들임. 예: '왜 당신은 알면서도 반복할까요? 의지 부족이 아닙니다.'",
    "CH5": "스포일러 역행. 결론을 먼저 공개하고 이유를 미스터리로 남김. 예: '그는 결국 사라졌습니다. 하지만 그 이유는 아직 아무도 모릅니다.'",
    "CH6": "현재형 역사 투영. 시청자를 현장으로 데려감. 예: '지금 1592년 임진왜란 한복판입니다. 포성이 울립니다.'",
    "CH7": "극한 긴장 현재형. 생존 긴박감으로 몰입. 예: '지금 전선은 무너지고 있습니다. 10분 안에 결정해야 합니다.'",
}

_SCRIPT_SYSTEM_PROMPT = """\
당신은 두들 애니메이션 YouTube 상위 1% 채널 전문 스크립트 작가입니다.
{channel_name} 채널({genre})용 롱폼 스크립트를 작성하세요.

━━━ 6대 인기 영상 대사 법칙 (반드시 준수) ━━━

[법칙 1] 첫 12초 훅 — 아래 이 채널 전용 스타일로 시작
  {channel_tone}
  (숫자충격 CTR +18% | 역설선언 AVD +12% | 2인칭질문 댓글 +40% | 스포일러역행 이탈률 -15%)

[법칙 2] 현재형 시제
  · 핵심 장면·감정적 클라이맥스는 반드시 현재형: "그는 달립니다", "총이 발사됩니다"
  · 과거형은 배경 설명에만 허용 (상위 채널 92% 공통 패턴)

[법칙 3] 3분마다 감정 피크 1회
  · 0~3분 구간: 긴장 또는 충격
  · 3~6분 구간: 슬픔 또는 반전
  · 6분~끝: 희망·교훈·감동으로 마무리

[법칙 4] 60초 정보 밀도 + 전환 문구
  · 60초마다 새로운 핵심 정보 1개 배치
  · 챕터 연결부에 반드시 전환 문구 삽입:
    "그런데 여기서 반전이 있습니다" / "그 선택이 모든 것을 바꿨습니다"
    "아무도 몰랐던 사실이 밝혀집니다" / "바로 그 순간이 결정적이었습니다"

[법칙 5] 채널별 특화 톤 (법칙 1과 연결)
  · {channel_name} 채널은 위 훅 스타일을 전편에 일관되게 유지

[법칙 6] 문장 길이 황금비율 — 짧은 문장 : 긴 문장 = 3 : 1
  · 짧은 문장 예: "그는 멈췄습니다." / "결과는 충격이었습니다."
  · 긴 문장은 핵심 설명·수치·배경에만 사용

━━━ 구조 규칙 ━━━
- 등장인물: 실제 또는 가상 인물 2~4명 (이름·역할 명확히)
- 챕터 구분: ## 챕터명 형식으로 3~5개
- 총 분량: 7~10분 (약 1,400~2,000자)
- 마지막: 구독 유도 문구로 마무리
"""

_TITLE_SYSTEM_PROMPT = """\
당신은 YouTube CTR 최적화 전문가입니다.
아래 스크립트를 기반으로 훅 타입이 각각 다른 제목 3가지를 생성하세요.

훅 타입 선택 기준:
  - curiosity_gap(궁금증): "~의 진짜 이유", "아무도 몰랐던 ~"
  - shocking(충격): 숫자·비율 포함, "단 ~만에", "~% 차이"
  - question(질문): "왜 ~일까?", "당신은 ~를 알고 있나요?"

규칙:
- 각 제목은 서로 다른 훅 타입 사용
- 30자 이내, 한국어
- JSON 배열로만 출력 (설명 없이)
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


async def _llm(system: str, user: str) -> str:
    """동기 generate_text를 executor에서 비동기 실행."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_text, f"{system}\n\n{user}")


async def run_track_a(job: "EpisodeJob") -> dict:
    """Track A: 스크립트 + 제목 3변형 + 썸네일 프롬프트 생성.

    Returns: {"script_text": str, "titles": list[str], "thumbnail_prompts": list[str],
              "hook_type": str, "opening_hook_sec": int}
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id
    ch_name, genre = CHANNEL_GENRES.get(channel_id, ("채널", "일반"))

    logger.info(f"Track A 시작: {channel_id} / {job.topic}")

    channel_tone = _CHANNEL_TONE.get(channel_id, "스토리 형식으로 서사적 전개, 핵심 궁금증 유발")
    system = _SCRIPT_SYSTEM_PROMPT.format(channel_name=ch_name, genre=genre, channel_tone=channel_tone)
    script_text = await _llm(system, f"주제: {job.topic}\n채널: {ch_name} ({genre})")
    logger.info(f"Track A: 스크립트 생성 완료 ({len(script_text)}자)")

    title_raw = await _llm(
        _TITLE_SYSTEM_PROMPT,
        f"스크립트:\n{script_text[:500]}...\n\n제목 3가지 JSON 배열로만 출력:",
    )

    titles: list[str] = []
    try:
        m = re.search(r'\[.*?\]', title_raw, re.DOTALL)
        if m:
            titles = json.loads(m.group())
    except Exception:
        pass
    if not titles:
        titles = [
            f"{job.topic} — 당신이 몰랐던 진실",
            f"충격! {job.topic}의 비밀",
            f"왜 {job.topic}가 중요한가?",
        ]

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
    """썸네일 3 변형 이미지 프롬프트 생성."""
    base = f"두들 애니메이션 스타일, 크래프트 페이퍼 배경, 2px 라인, 3.5등신 캐릭터, {ch_name} 채널"
    t0 = titles[0][:15] if titles else topic[:15]
    return [
        f"{base}, 놀란 표정 캐릭터가 '{t0}' 텍스트를 가리키는 구도, 강렬한 빨간 포인트 텍스트",
        f"{base}, 캐릭터가 차트/그래프를 설명하는 구도, '{topic}' 핵심 키워드 강조, 궁금증 유발",
        f"{base}, 질문형 구도 — 캐릭터가 물음표를 들고 있음, 깔끔한 흰 배경 강조, 클릭 유도",
    ]
