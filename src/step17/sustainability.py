"""STEP 17 — 콘텐츠 지속성 관리. 분기 1회."""
from loguru import logger
from src.core.ssot import read_json, write_json, json_exists, now_iso
from src.core.config import GLOBAL_DIR, KNOWLEDGE_DIR, CHANNEL_CATEGORIES

# 채널별 주제 총 용량 추정
TOPIC_CAPACITY = {
    "CH1": {"total": 1000, "depletion_risk": "LOW"},
    "CH2": {"total": 800,  "depletion_risk": "LOW"},
    "CH3": {"total": 600,  "depletion_risk": "LOW"},
    "CH4": {"total": 800,  "depletion_risk": "LOW"},
    "CH5": {"total": 2000, "depletion_risk": "LOW"},
    "CH6": {"total": 1500, "depletion_risk": "LOW"},
    "CH7": {"total": 2000, "depletion_risk": "LOW"},
}


def run_step17() -> dict:
    by_ch = {}
    for ch, cat in CHANNEL_CATEGORIES.items():
        stats = KNOWLEDGE_DIR / ch / "reports" / "gate_stats.json"
        produced = read_json(stats).get("total_topics", 0) if json_exists(stats) else 0
        cap = TOPIC_CAPACITY.get(ch, {"total": 500, "depletion_risk": "LOW"})
        total = cap["total"]
        remain = max(0, total - produced)
        depl = "HIGH" if remain < 50 else ("MEDIUM" if remain < 150 else cap["depletion_risk"])
        by_ch[ch] = {
            "category": cat,
            "topics_produced": produced,
            "topics_remaining_estimate": remain,
            "depletion_risk": depl,
            "refresh_eligible": produced > 10,
        }

    report = {
        "schema_version": "2.0",
        "quarter": now_iso()[:7],
        "generated_at": now_iso(),
        "total_channels": 7,
        "by_channel": by_ch,
        "expansion_candidates": [
            {"category": "법률_생활법률", "rpm_est": 5500},
            {"category": "세금_절세",    "rpm_est": 6000},
            {"category": "환경_에너지",  "rpm_est": 3500},
        ],
    }
    sust_dir = GLOBAL_DIR / "sustainability"
    sust_dir.mkdir(parents=True, exist_ok=True)
    write_json(sust_dir / f"sustainability_{now_iso()[:7]}.json", report)
    logger.info("[STEP17] 지속성 리포트 생성 (7채널)")
    return report
