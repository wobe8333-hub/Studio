"""STEP 08 — 스크립트 생성기.
버그 수정(BUG-5): generate_script 전체를 @retry로 감쌈.
                  json.loads JSONDecodeError도 재시도 대상에 포함.
"""
import json, logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
from src.core.config import GEMINI_API_KEY, CHANNEL_CATEGORIES, GEMINI_TEXT_MODEL
from src.quota.gemini_quota import throttle_if_needed, record_request
from src.cache.gemini_cache import get as cache_get, set as cache_set

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPTS = {
    "CH1": "당신은 경제 재테크 지식 애니메이션 스크립트 작가입니다. 톤: authoritative_accessible. 훅: 경제적 손실 공포 후 기회 제시. 반드시 포함: financial_disclaimer.",
    "CH2": "당신은 건강 의학 지식 애니메이션 스크립트 작가입니다. 톤: scientific_caring. 훅: 건강 위협 사실 후 해결책 예고. 반드시 포함: medical_disclaimer.",
    "CH3": "당신은 심리 행동과학 지식 애니메이션 스크립트 작가입니다. 톤: curious_empathetic. 훅: 행동 패턴 충격 사실 후 변화 약속.",
    "CH4": "당신은 부동산 경매 지식 애니메이션 스크립트 작가입니다. 톤: practical_urgent. 훅: 부동산 손실 위험 후 기회 포착 방법. 반드시 포함: financial_disclaimer.",
    "CH5": "당신은 AI 테크 지식 애니메이션 스크립트 작가입니다. 톤: wonder_accessible. 훅: AI 충격 사실 후 활용 방법 약속.",
}

def _get_system_prompt(channel_id: str, style_policy: dict) -> str:
    base      = SCRIPT_SYSTEM_PROMPTS.get(channel_id, "")
    cache_key = f"system_{channel_id}_{style_policy.get('animation_style','')}"
    cached    = cache_get("system_prompt", cache_key)
    if cached: return cached
    cache_set("system_prompt", cache_key, base, cost_krw=5.0)
    return base

def _call_gemini_raw(model, prompt: str, max_tokens: int = 4000) -> str:
    throttle_if_needed()
    record_request()
    return model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    ).text

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=60),
       retry=retry_if_exception_type(Exception))
def generate_script(channel_id: str, run_id: str, topic: dict,
                    style_policy: dict, revenue_policy: dict,
                    algorithm_policy: dict) -> dict:
    model = genai.GenerativeModel(
        GEMINI_TEXT_MODEL,
        system_instruction=_get_system_prompt(channel_id, style_policy),
    )
    category      = CHANNEL_CATEGORIES[channel_id]
    anim_style    = style_policy.get("animation_style","process")
    is_trending   = style_policy.get("is_trending", False)
    trend_note    = style_policy.get("trend_reinterpretation","")
    affiliate     = style_policy.get("affiliate_product_ref","")
    dur_range     = revenue_policy.get("target_duration_range_sec",[660,780])
    dur_min, dur_max = dur_range[0]//60, dur_range[1]//60
    midroll       = revenue_policy.get("midroll_positions_ratio",[0.35,0.65,0.85])
    hook_dir      = style_policy.get("hook_direction","")
    click_rate    = style_policy.get("affiliate_click_rate_applied",0.003)
    purchase_rate = style_policy.get("affiliate_purchase_rate_applied",0.0)
    render_tool   = "manim" if anim_style in ["process","comparison","timeline"] else "gemini"
    med_disc  = "null" if channel_id != "CH2" else '"본 영상은 의학적 조언을 대체하지 않습니다."'
    fin_disc  = "null" if channel_id not in ["CH1","CH4"] else '"본 영상은 투자/법적 조언을 대체하지 않습니다."'

    prompt = f"""다음 주제에 대해 YouTube 지식 애니메이션 영상 스크립트를 JSON 형식으로 작성하시오.
주제: {topic.get('reinterpreted_title', topic.get('title',''))}
카테고리: {category}
{"트렌드 재해석: " + trend_note if is_trending else ""}
애니메이션 스타일: {anim_style} / 훅 방향: {hook_dir}
영상 길이: {dur_min}~{dur_max}분 / 미드롤 위치: {midroll}

반드시 다음 JSON 구조로만 응답 (다른 텍스트 없이):
{{
  "title_candidates":["제목1","제목2","제목3"],
  "hook":{{"text":"훅 텍스트","duration_estimate_sec":20,"hook_type":"충격사실","hook_direction":"{hook_dir}","animation_preview_at_sec":8}},
  "promise":"이 영상에서 배울 내용 한 문장",
  "sections":[{{"id":0,"heading":"섹션 제목","narration_text":"나레이션(400자 이상)","animation_prompt":"영문 애니메이션 설명","animation_style":"{anim_style}","render_tool":"{render_tool}","manim_code":null,"manim_fallback_used":false,"chapter_title":"챕터 제목"}}],
  "affiliate_insert":{{"text":"Affiliate 문구","position_ratio":0.70,"product_ref":"{affiliate}","utm":"","click_rate_applied":{click_rate},"purchase_rate_applied":{purchase_rate},"expected_revenue_per_1000_views":0.0}},
  "seo":{{"primary_keyword":"키워드","secondary_keywords":["k2","k3"],"description_first_2lines":"설명 첫 2줄","chapter_markers":["00:00 인트로","01:30 설명"]}},
  "cta":{{"text":"구독/좋아요 CTA","like_cta_at_sec":55}},
  "target_duration_sec":720,"midroll_plan":{midroll},
  "video_spec":{{"width":1920,"height":1080,"fps":30}},
  "ai_label":"이 영상은 AI가 제작에 참여했습니다.",
  "medical_disclaimer":{med_disc},
  "financial_disclaimer":{fin_disc}
}}
sections 6개 이상. chapter_markers 5개 이상."""

    raw = _call_gemini_raw(model, prompt, max_tokens=4000).strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]).strip()
    script = json.loads(raw)
    script.update({
        "channel_id": channel_id, "run_id": run_id,
        "is_trending": is_trending,
        "trend_reinterpretation_note": trend_note if is_trending else None,
        "step07_policy_version": revenue_policy.get("policy_version","v1.0"),
        "animation_style": anim_style,
        "render_tool": style_policy.get("render_tool","manim"),
    })
    return script
