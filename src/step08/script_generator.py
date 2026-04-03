"""STEP 08 — 스크립트 생성기.

Phase 2 수정: 7채널 프롬프트 갱신 (CH2 부동산, CH4 미스터리, CH5 전쟁사)
Phase 4 연동: knowledge_package의 core_facts/statistics/counterpoints 활용
Phase 8 추가: 7채널 카테고리별 면책조항 자동 삽입 + character_directions 필드
"""

import json
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
from src.core.config import GEMINI_API_KEY, CHANNEL_CATEGORIES, GEMINI_TEXT_MODEL
from src.quota.gemini_quota import throttle_if_needed, record_request
from src.cache.gemini_cache import get as cache_get, set as cache_set

genai.configure(api_key=GEMINI_API_KEY)

# ── 7채널 시스템 프롬프트 ────────────────────────────────────────
SCRIPT_SYSTEM_PROMPTS = {
    "CH1": (
        "당신은 경제 재테크 지식 애니메이션 스크립트 작가입니다. "
        "톤: authoritative_accessible. "
        "훅: 경제적 손실 공포 후 기회 제시. "
        "반드시 포함: financial_disclaimer, character_directions(각 섹션별 귀여운 캐릭터 표정/동작)."
    ),
    "CH2": (
        "당신은 부동산 지식 애니메이션 스크립트 작가입니다. "
        "톤: practical_urgent. "
        "훅: 부동산 손실 위험 후 기회 포착 방법. "
        "반드시 포함: investment_disclaimer, character_directions."
    ),
    "CH3": (
        "당신은 심리 행동과학 지식 애니메이션 스크립트 작가입니다. "
        "톤: curious_empathetic. "
        "훅: 행동 패턴 충격 사실 후 변화 약속. "
        "반드시 포함: psychology_disclaimer, character_directions."
    ),
    "CH4": (
        "당신은 미스터리 탐구 지식 애니메이션 스크립트 작가입니다. "
        "톤: suspense_curious. "
        "훅: 미스터리 서스펜스 후 미해결 의문 제기. "
        "반드시 포함: mystery_disclaimer, character_directions."
    ),
    "CH5": (
        "당신은 전쟁사 지식 애니메이션 스크립트 작가입니다. "
        "톤: dramatic_educational. "
        "훅: 충격적 전황 후 숨겨진 역사적 사실 제시. "
        "반드시 포함: history_disclaimer, character_directions."
    ),
    "CH6": (
        "당신은 과학 지식 애니메이션 스크립트 작가입니다. "
        "톤: wonder_accessible. "
        "훅: 과학적 충격 사실 후 원리 해설 약속. "
        "반드시 포함: science_disclaimer, character_directions."
    ),
    "CH7": (
        "당신은 역사 지식 애니메이션 스크립트 작가입니다. "
        "톤: storytelling_educational. "
        "훅: 숨겨진 역사적 진실 후 교훈 제시. "
        "반드시 포함: history_disclaimer, character_directions."
    ),
}

# ── 카테고리별 면책조항 템플릿 ────────────────────────────────────
CHANNEL_DISCLAIMERS = {
    "CH1": {
        "key": "financial_disclaimer",
        "text": "본 영상은 교육 목적으로 제작되었으며, 투자 권유나 법적 조언을 대체하지 않습니다. 투자는 개인의 판단과 책임 하에 이루어져야 합니다.",
    },
    "CH2": {
        "key": "investment_disclaimer",
        "text": "본 영상은 부동산 시장 정보를 제공하며, 법적·투자 조언을 대체하지 않습니다. 부동산 거래 전 반드시 전문가와 상담하세요.",
    },
    "CH3": {
        "key": "psychology_disclaimer",
        "text": "본 영상은 심리학 교육 목적으로 제작되었으며, 전문적인 심리상담이나 치료를 대체하지 않습니다. 정신건강 문제는 전문가와 상담하세요.",
    },
    "CH4": {
        "key": "mystery_disclaimer",
        "text": "본 영상의 미스터리 내용은 교육·엔터테인먼트 목적이며, 일부 내용은 확인되지 않은 설이 포함될 수 있습니다.",
    },
    "CH5": {
        "key": "history_disclaimer",
        "text": "본 영상은 역사적 사실을 기반으로 제작되었으며, 특정 국가·집단에 대한 차별이나 혐오를 조장하지 않습니다.",
    },
    "CH6": {
        "key": "science_disclaimer",
        "text": "본 영상의 과학 내용은 공개된 연구를 기반으로 하며, 최신 연구 결과와 다를 수 있습니다. 중요한 결정에는 전문가 자문을 구하세요.",
    },
    "CH7": {
        "key": "history_disclaimer",
        "text": "본 영상은 역사적 사실을 기반으로 제작되었으며, 특정 국가·집단에 대한 차별이나 혐오를 조장하지 않습니다.",
    },
}


def _get_system_prompt(channel_id: str, style_policy: dict) -> str:
    base = SCRIPT_SYSTEM_PROMPTS.get(channel_id, "")
    cache_key = f"system_{channel_id}_{style_policy.get('animation_style','')}"
    cached = cache_get("system_prompt", cache_key)
    if cached:
        return cached
    cache_set("system_prompt", cache_key, base, cost_krw=5.0)
    return base


def _call_gemini_raw(model, prompt: str, max_tokens: int = 4000) -> str:
    throttle_if_needed()
    record_request()
    return model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    ).text


def _build_knowledge_context(knowledge_pkg: dict) -> str:
    """knowledge_package dict에서 스크립트 생성용 컨텍스트 문자열 생성"""
    if not knowledge_pkg:
        return ""

    lines = []
    facts = knowledge_pkg.get("core_facts", [])
    if facts:
        lines.append("【핵심 팩트 (반드시 활용)】")
        for i, f in enumerate(facts[:7], 1):
            lines.append(f"  {i}. {f}")

    stats = knowledge_pkg.get("statistics", [])
    if stats:
        lines.append("【수치/통계】")
        for s in stats[:3]:
            lines.append(f"  - {s.get('value', s)}")

    quotes = knowledge_pkg.get("expert_quotes", [])
    if quotes:
        lines.append("【전문가 인용】")
        for q in quotes[:2]:
            lines.append(f"  - {q[:150]}")

    counterpoints = knowledge_pkg.get("counterpoints", [])
    if counterpoints:
        lines.append("【다른 시각/반론】")
        for c in counterpoints[:2]:
            lines.append(f"  - {c}")

    confidence = knowledge_pkg.get("confidence_score", 0)
    if confidence:
        lines.append(f"【신뢰도 점수: {confidence:.2f}】")

    return "\n".join(lines)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=60),
    retry=retry_if_exception_type(Exception),
)
def generate_script(
    channel_id: str,
    run_id: str,
    topic: dict,
    style_policy: dict,
    revenue_policy: dict,
    algorithm_policy: dict,
    knowledge_pkg: dict = None,
) -> dict:
    model = genai.GenerativeModel(
        GEMINI_TEXT_MODEL,
        system_instruction=_get_system_prompt(channel_id, style_policy),
    )
    category     = CHANNEL_CATEGORIES[channel_id]
    anim_style   = style_policy.get("animation_style", "process")
    is_trending  = style_policy.get("is_trending", False)
    trend_note   = style_policy.get("trend_reinterpretation", "")
    affiliate    = style_policy.get("affiliate_product_ref", "")
    dur_range    = revenue_policy.get("target_duration_range_sec", [660, 780])
    dur_min, dur_max = dur_range[0] // 60, dur_range[1] // 60
    midroll      = revenue_policy.get("midroll_positions_ratio", [0.35, 0.65, 0.85])
    hook_dir     = style_policy.get("hook_direction", "")
    click_rate   = style_policy.get("affiliate_click_rate_applied", 0.003)
    purchase_rate = style_policy.get("affiliate_purchase_rate_applied", 0.0)
    render_tool  = "manim" if anim_style in ["process", "comparison", "timeline"] else "gemini"

    # 카테고리별 면책조항 설정
    disclaimer_cfg = CHANNEL_DISCLAIMERS.get(channel_id, {})
    disc_key  = disclaimer_cfg.get("key", "general_disclaimer")
    disc_text = disclaimer_cfg.get("text", "본 영상은 교육 목적으로 제작되었습니다.")

    # knowledge_package 컨텍스트 (Phase 4 연동)
    knowledge_ctx = _build_knowledge_context(knowledge_pkg or {})
    knowledge_block = f"\n\n【지식 패키지 (팩트 기반 스크립트 작성)】\n{knowledge_ctx}" if knowledge_ctx else ""

    prompt = f"""다음 주제에 대해 YouTube 귀여운 애니메이션 지식 영상 스크립트를 JSON 형식으로 작성하시오.
주제: {topic.get('reinterpreted_title', topic.get('title', ''))}
카테고리: {category}
{"트렌드 재해석: " + trend_note if is_trending else ""}
애니메이션 스타일: {anim_style} / 훅 방향: {hook_dir}
영상 길이: {dur_min}~{dur_max}분 / 미드롤 위치: {midroll}
{knowledge_block}

반드시 다음 JSON 구조로만 응답 (다른 텍스트 없이):
{{
  "title_candidates": ["제목1", "제목2", "제목3"],
  "hook": {{"text": "훅 텍스트", "duration_estimate_sec": 20, "hook_type": "충격사실", "hook_direction": "{hook_dir}", "animation_preview_at_sec": 8}},
  "promise": "이 영상에서 배울 내용 한 문장",
  "sections": [{{
    "id": 0,
    "heading": "섹션 제목",
    "narration_text": "나레이션(400자 이상)",
    "animation_prompt": "영문 애니메이션 설명",
    "animation_style": "{anim_style}",
    "render_tool": "{render_tool}",
    "manim_code": null,
    "manim_fallback_used": false,
    "chapter_title": "챕터 제목",
    "character_directions": {{"expression": "happy/surprised/thinking/sad", "pose": "standing/pointing/explaining", "action": "귀여운 동작 설명"}}
  }}],
  "affiliate_insert": {{"text": "Affiliate 문구", "position_ratio": 0.70, "product_ref": "{affiliate}", "utm": "", "click_rate_applied": {click_rate}, "purchase_rate_applied": {purchase_rate}, "expected_revenue_per_1000_views": 0.0}},
  "seo": {{"primary_keyword": "키워드", "secondary_keywords": ["k2", "k3"], "description_first_2lines": "설명 첫 2줄", "chapter_markers": ["00:00 인트로", "01:30 설명"]}},
  "cta": {{"text": "구독/좋아요 CTA", "like_cta_at_sec": 55}},
  "target_duration_sec": 720,
  "midroll_plan": {midroll},
  "video_spec": {{"width": 1920, "height": 1080, "fps": 30}},
  "ai_label": "이 영상은 AI가 제작에 참여했습니다.",
  "{disc_key}": "{disc_text}"
}}
sections 6개 이상. chapter_markers 5개 이상. character_directions는 모든 섹션에 포함."""

    raw = _call_gemini_raw(model, prompt, max_tokens=8192).strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]).strip()
    script = json.loads(raw)

    # 면책조항 강제 삽입 (Gemini가 누락한 경우 대비)
    if disc_key not in script:
        script[disc_key] = disc_text
        logger.debug(f"[Script] {channel_id}: {disc_key} 강제 삽입")

    script.update({
        "channel_id": channel_id,
        "run_id": run_id,
        "is_trending": is_trending,
        "trend_reinterpretation_note": trend_note if is_trending else None,
        "step07_policy_version": revenue_policy.get("policy_version", "v1.0"),
        "animation_style": anim_style,
        "render_tool": style_policy.get("render_tool", "manim"),
        "knowledge_confidence": (knowledge_pkg or {}).get("confidence_score", None),
    })
    return script
