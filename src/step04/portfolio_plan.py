"""STEP 04 — 월간 포트폴리오 계획.
버그 수정(BUG-1): 중복 로직 제거. channel_registry.get_active_channels 재사용.
"""
from datetime import datetime
from src.core.config import GLOBAL_DIR, CHANNEL_MONTHLY_TARGET
from src.core.ssot import write_json, now_iso
from src.step00.channel_registry import get_active_channels

TRENDING_RATIO  = 0.60
EVERGREEN_RATIO = 0.25
SERIES_RATIO    = 0.15

def create_portfolio_plan(month_number: int) -> dict:
    ym       = datetime.utcnow().strftime("%Y-%m")
    active   = get_active_channels(month_number)
    plan_dir = GLOBAL_DIR / "monthly_plan" / ym
    plan_dir.mkdir(parents=True, exist_ok=True)
    ch_plans, total = {}, 0
    for ch in active:
        mv = CHANNEL_MONTHLY_TARGET[ch]; total += mv
        ch_plans[ch] = {
            "monthly_video_target": mv,
            "trending_count":  int(mv * TRENDING_RATIO),
            "evergreen_count": int(mv * EVERGREEN_RATIO),
            "series_count":    mv - int(mv * TRENDING_RATIO) - int(mv * EVERGREEN_RATIO),
        }
    plan = {
        "schema_version": "1.0", "month_number": month_number, "year_month": ym,
        "created_at": now_iso(), "active_channels": active, "total_video_target": total,
        "content_ratio": {"trending": TRENDING_RATIO, "evergreen": EVERGREEN_RATIO, "series": SERIES_RATIO},
        "channel_plans": ch_plans,
    }
    write_json(plan_dir / "portfolio_plan.json", plan)
    return plan

if __name__ == "__main__":
    import sys
    p = create_portfolio_plan(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    print(f"[STEP04] total={p['total_video_target']} active={p['active_channels']}")
