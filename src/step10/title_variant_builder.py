"""STEP 10 — 제목 3종 + 썸네일 3종 변형 빌더."""
import json

from google import genai as _genai
from google.genai import types as genai_types
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, MEMORY_DIR
from src.core.ssot import get_run_dir, json_exists, now_iso, read_json, sha256_dict, write_json
from src.quota.gemini_quota import record_request, throttle_if_needed
from src.step10.thumbnail_generator import generate_thumbnail

_client: _genai.Client | None = None


def _get_client() -> _genai.Client:
    global _client
    if _client is None:
        _client = _genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _get_preferred_mode(channel_id: str) -> str:
    bias = MEMORY_DIR / "topic_priority_bias.json"
    if not json_exists(bias): return "curiosity"
    w = read_json(bias).get("title_mode_weights", {})
    return max(w, key=w.get) if w else "curiosity"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _generate_titles(channel_id: str, base_title: str, keyword: str) -> list:
    throttle_if_needed()
    record_request()
    json_example = (
        '[{"ref":"v1","mode":"authority","title":"제목1"},'
        '{"ref":"v2","mode":"curiosity","title":"제목2"},'
        '{"ref":"v3","mode":"benefit","title":"제목3"}]'
    )
    prompt = (
        f"YouTube 제목 3가지를 JSON 배열로.\n기본 주제: {base_title}\n키워드: {keyword}\n"
        f"규칙: 각 20~40자, 키워드 포함, 한국어\n"
        f"JSON만:{json_example}"
    )
    response = _get_client().models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=4000,
        ),
    )
    # Thinking 모델 대응 — parts 순회
    try:
        raw = response.text.strip()
    except (ValueError, AttributeError):
        parts = response.candidates[0].content.parts if response.candidates else []
        texts = [p.text for p in parts if hasattr(p, "text") and p.text]
        raw = texts[-1].strip() if texts else ""
    if not raw:
        raise ValueError("응답 텍스트 없음")
    # 마크다운 코드 펜스 제거
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    # 앞뒤 설명 텍스트 제거 — 첫 [ ~ 마지막 ] 추출
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    variants = json.loads(raw)
    for v in variants:
        v["seo_keyword_included"] = keyword in v.get("title", "")
    return variants


def run_step10(channel_id: str, run_id: str) -> bool:
    run_dir  = get_run_dir(channel_id, run_id)
    s08      = run_dir / "step08"
    var_dir  = s08 / "variants"
    var_dir.mkdir(parents=True, exist_ok=True)
    script_path = s08 / "script.json"
    if not json_exists(script_path):
        logger.error("[STEP10] script.json 없음")
        return False
    script  = read_json(script_path)
    tc      = script.get("title_candidates", ["제목 없음"])
    base    = tc[0] if tc else "제목 없음"
    keyword = script.get("seo", {}).get("primary_keyword", "")
    try:
        variants = _generate_titles(channel_id, base, keyword)
    except Exception as e:
        logger.warning(f"[STEP10] 제목 생성 실패 (폴백 사용): {e}")
        variants = [
            {"ref": "v1", "mode": "authority", "title": base, "seo_keyword_included": keyword in base},
            {"ref": "v2", "mode": "curiosity", "title": base, "seo_keyword_included": keyword in base},
            {"ref": "v3", "mode": "benefit",   "title": base, "seo_keyword_included": keyword in base},
        ]
    # 썸네일은 step10/ 에 저장
    step10_dir = run_dir / "step10"
    step10_dir.mkdir(parents=True, exist_ok=True)
    _mode_to_variant = {"01": "thumbnail_v1", "02": "thumbnail_v2", "03": "thumbnail_v3"}
    for mode in ["01", "02", "03"]:
        generate_thumbnail(channel_id, base, mode, step10_dir / f"{_mode_to_variant[mode]}.png")
    sp = s08 / "style_policy.json"
    fp = sha256_dict(read_json(sp)) if json_exists(sp) else ""
    write_json(var_dir / "title_variants.json", {
        "run_id": run_id, "channel_id": channel_id, "style_policy_fingerprint": fp,
        "title_variant_count": 3, "thumbnail_variant_count": 3,
        "variants": variants, "preferred_mode": _get_preferred_mode(channel_id),
        "created_at": now_iso(),
    })
    write_json(var_dir / "variant_manifest.json", {
        "variant_version": "v1.0", "run_id": run_id, "channel_id": channel_id,
        "title_variants_path": str(var_dir / "title_variants.json"),
        "thumbnail_variants": [str(step10_dir / f"thumbnail_v{n}.png") for n in ["1", "2", "3"]],
        "style_policy_fingerprint": fp, "title_variant_count": 3, "thumbnail_variant_count": 3,
        "created_at": now_iso(),
    })
    logger.info(f"[STEP10] {channel_id}/{run_id} 완료")
    return True
