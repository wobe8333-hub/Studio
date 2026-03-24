"""STEP 05 — 트렌드 topic 수집."""
import json, logging
from src.core.ssot import write_json, now_iso, sha256_dict
from src.core.config import KNOWLEDGE_DIR
from src.quota.ytdlp_quota import throttle, get_ytdlp_opts, on_block_detected
import yt_dlp

logger = logging.getLogger(__name__)

TRENDING_RATIO  = 0.60
EVERGREEN_RATIO = 0.25
SERIES_RATIO    = 0.15
TREND_VALIDITY_DAYS = 7

CATEGORY_KEYWORDS = {
    "경제_재테크":["금리","주식","경제","투자","재테크","인플레이션","부동산","ETF"],
    "건강_의학":  ["건강","질병","의학","암","바이러스","면역","뇌","심장"],
    "심리_행동":  ["심리","뇌","행동","감정","스트레스","도파민","중독","인간관계"],
    "부동산_경매":["부동산","경매","전세","아파트","집값","금리","청약"],
    "AI_테크":    ["AI","인공지능","ChatGPT","GPT","딥러닝","로봇","테크"],
}

def collect_trends(channel_id: str, category: str, limit: int = 10) -> list:
    throttle()
    opts = get_ytdlp_opts(channel_id)
    opts["playlistend"] = 50
    results = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/feed/trending", download=False)
            if not info or "entries" not in info: return results
            keywords = CATEGORY_KEYWORDS.get(category, [])
            for entry in info.get("entries", []):
                if not entry: continue
                title    = entry.get("title", "")
                combined = (title + " " + entry.get("description", "")).lower()
                for kw in keywords:
                    if kw.lower() in combined:
                        results.append({
                            "video_id":        entry.get("id",""),
                            "title":           title,
                            "view_count":      entry.get("view_count",0),
                            "upload_date":     entry.get("upload_date",""),
                            "channel":         entry.get("channel",""),
                            "matched_keyword": kw,
                            "collected_at":    now_iso(),
                        })
                        break
                if len(results) >= limit: break
    except Exception as e:
        if "429" in str(e) or "blocked" in str(e).lower(): on_block_detected()
        logger.error(f"[STEP05] TREND_COLLECT_ERROR {channel_id}: {e}")
    return results

def reinterpret_trend(trend: dict, category: str, channel_id: str) -> dict:
    fns = {
        "경제_재테크": lambda t: f"{t}의 작동 원리와 내 돈에 미치는 영향",
        "건강_의학":   lambda t: f"{t}이 우리 몸에서 일어나는 과정",
        "심리_행동":   lambda t: f"{t}이 뇌에서 작동하는 방식",
        "부동산_경매": lambda t: f"{t}의 원리와 투자에 미치는 영향",
        "AI_테크":     lambda t: f"{t}이 작동하는 방식",
    }
    fn = fns.get(category, lambda t: f"{t}의 원리")
    kw = trend.get("matched_keyword", trend.get("title",""))
    return {
        "original_trend":      trend,
        "reinterpreted_title": fn(kw),
        "category":            category,
        "channel_id":          channel_id,
        "is_trending":         True,
        "trend_collected_at":  trend.get("collected_at", now_iso()),
        "trend_validity_days": TREND_VALIDITY_DAYS,
    }

def save_knowledge(channel_id: str, topics: list) -> None:
    raw_dir = KNOWLEDGE_DIR / channel_id / "discovery" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=True: assets.jsonl 직접 쓰기 — PowerShell 5.1 파싱 안정성 보장
    with open(raw_dir / "assets.jsonl", "w", encoding="utf-8") as f:
        for t in topics:
            f.write(json.dumps(t, ensure_ascii=True) + "\n")
    report_dir = KNOWLEDGE_DIR / channel_id / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json(report_dir / "gate_stats.json", {
        "collected_at": now_iso(), "channel_id": channel_id,
        "total_topics": len(topics),
        "trending_count": sum(1 for t in topics if t.get("is_trending")),
        "assets_sha256": sha256_dict({"topics": topics}),
    })
    logger.info(f"[STEP05] {channel_id}: {len(topics)}개 topic 저장")
