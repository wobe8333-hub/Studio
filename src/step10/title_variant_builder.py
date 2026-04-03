"""STEP 10 — 제목 3종 + 썸네일 3종 변형 빌더."""
import json
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from src.core.ssot import read_json, write_json, json_exists, sha256_dict, now_iso, get_run_dir
from src.core.config import GEMINI_API_KEY, MEMORY_DIR, GEMINI_TEXT_MODEL
from src.quota.gemini_quota import throttle_if_needed, record_request
from src.step10.thumbnail_generator import generate_thumbnail

genai.configure(api_key=GEMINI_API_KEY)
def _get_preferred_mode(channel_id: str) -> str:
    bias = MEMORY_DIR / "topic_priority_bias.json"
    if not json_exists(bias): return "curiosity"
    w = read_json(bias).get("title_mode_weights",{})
    return max(w, key=w.get) if w else "curiosity"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _generate_titles(channel_id: str, base_title: str, keyword: str) -> list:
    model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
    throttle_if_needed(); record_request()
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
    raw = model.generate_content(
        prompt, generation_config=genai.GenerationConfig(max_output_tokens=300),
    ).text.strip()
    if raw.startswith("```"): raw = "\n".join(raw.split("\n")[1:-1])
    variants = json.loads(raw)
    for v in variants: v["seo_keyword_included"] = keyword in v.get("title","")
    return variants

def run_step10(channel_id: str, run_id: str) -> bool:
    run_dir      = get_run_dir(channel_id, run_id)
    s08          = run_dir / "step08"
    var_dir      = s08 / "variants"
    var_dir.mkdir(parents=True, exist_ok=True)
    script_path  = s08 / "script.json"
    if not json_exists(script_path): logger.error("[STEP10] script.json 없음"); return False
    script   = read_json(script_path)
    tc       = script.get("title_candidates",["제목 없음"])
    base     = tc[0] if tc else "제목 없음"
    keyword  = script.get("seo",{}).get("primary_keyword","")
    variants = _generate_titles(channel_id, base, keyword)
    for mode in ["01","02","03"]:
        generate_thumbnail(channel_id, base, mode, var_dir/f"thumbnail_variant_{mode}.png")
    sp  = s08/"style_policy.json"
    fp  = sha256_dict(read_json(sp)) if json_exists(sp) else ""
    write_json(var_dir/"title_variants.json", {
        "run_id":run_id,"channel_id":channel_id,"style_policy_fingerprint":fp,
        "title_variant_count":3,"thumbnail_variant_count":3,
        "variants":variants,"preferred_mode":_get_preferred_mode(channel_id),
        "created_at":now_iso(),
    })
    write_json(var_dir/"variant_manifest.json", {
        "variant_version":"v1.0","run_id":run_id,"channel_id":channel_id,
        "title_variants_path":str(var_dir/"title_variants.json"),
        "thumbnail_variants":[str(var_dir/f"thumbnail_variant_{n}.png") for n in ["01","02","03"]],
        "style_policy_fingerprint":fp,"title_variant_count":3,"thumbnail_variant_count":3,
        "created_at":now_iso(),
    })
    logger.info(f"[STEP10] {channel_id}/{run_id} 완료")
    return True
