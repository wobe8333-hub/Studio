"""STEP 02 — 수익 구조 정책."""
from src.core.config import (
    CHANNEL_MONTHLY_TARGET,
    CHANNEL_RPM_INITIAL,
    CHANNEL_RPM_PROXY,
    CHANNELS_DIR,
    REVENUE_TARGET_PER_CHANNEL,
)
from src.core.ssot import now_iso, write_json

AFFILIATE_FULL = {
    "CH1": {"product":"증권사 계좌 개설 CPA","type":"CPA","cpa_amount":15000,
            "click_rate_initial":0.003,"click_rate_growth":0.008,"purchase_conversion_rate":0.20},
    "CH2": {"product":"과학 키트 / 온라인 강의 CPA","type":"CPA","cpa_amount":12000,
            "click_rate_initial":0.004,"click_rate_growth":0.010,"purchase_conversion_rate":0.15},
    "CH3": {"product":"부동산 강의 / 청약 앱 CPA","type":"CPA","cpa_amount":20000,
            "click_rate_initial":0.004,"click_rate_growth":0.009,"purchase_conversion_rate":0.15},
    "CH4": {"product":"심리학 도서 CPS","type":"CPS","product_price":20000,
            "commission_rate":0.05,"click_rate_initial":0.003,"click_rate_growth":0.008,
            "purchase_conversion_rate":0.10},
    "CH5": {"product":"미스터리 도서 / 공포 OTT CPA","type":"CPA","cpa_amount":8000,
            "click_rate_initial":0.005,"click_rate_growth":0.012,"purchase_conversion_rate":0.10},
    "CH6": {"product":"역사 도서 / 역사 여행 CPS","type":"CPS","product_price":18000,
            "commission_rate":0.05,"click_rate_initial":0.004,"click_rate_growth":0.010,
            "purchase_conversion_rate":0.15},
    "CH7": {"product":"밀리터리 도서 / 전쟁사 게임 CPS","type":"CPS","product_price":25000,
            "commission_rate":0.05,"click_rate_initial":0.004,"click_rate_growth":0.010,
            "purchase_conversion_rate":0.12},
}
OPERATING_COST = {
    "CH1": 80000, "CH2": 100000, "CH3": 100000,
    "CH4": 100000, "CH5": 100000, "CH6": 100000, "CH7": 100000,
}

def create_rpm_reality(channel_id: str) -> dict:
    ch_dir = CHANNELS_DIR / channel_id
    ch_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version":"1.0","channel_id":channel_id,"updated_at":now_iso()[:10],
        "rpm_proxy":CHANNEL_RPM_PROXY[channel_id],
        "rpm_initial":CHANNEL_RPM_INITIAL[channel_id],
        "rpm_actual":None,"rpm_stage":"INITIAL","rpm_initial_multiplier":0.5,
        "rpm_effective":CHANNEL_RPM_INITIAL[channel_id],"data_source":"proxy",
        "note":"실측 RPM 미수집. rpm_actual 수집 후 갱신 필요.",
    }
    write_json(ch_dir / "rpm_reality.json", data)
    return data

def create_revenue_structure_policy(channel_id: str) -> dict:
    ch_dir = CHANNELS_DIR / channel_id
    aff    = AFFILIATE_FULL[channel_id]
    op     = OPERATING_COST[channel_id]
    mv     = CHANNEL_MONTHLY_TARGET[channel_id]
    policy = {
        "schema_version":"1.0","channel_id":channel_id,"effective_from":now_iso()[:7],
        "revenue_target_net":REVENUE_TARGET_PER_CHANNEL,
        "operating_cost_monthly":op,"monthly_video_target":mv,
        "adsense":{
            "rpm_proxy":CHANNEL_RPM_PROXY[channel_id],
            "rpm_initial":CHANNEL_RPM_INITIAL[channel_id],"rpm_floor":3000,
            "rpm_stage_rules":{"initial_months":3,"initial_multiplier":0.5,
                                "stable_source":"rpm_actual_or_proxy"},
        },
        "affiliate":aff,
        "affiliate_formula":{
            "description":"views x click_rate x purchase_conversion_rate x price x commission",
            "formula_version":"v2.0",
        },
        "revenue_mix_target":{"adsense_pct":75,"affiliate_pct":25},
    }
    write_json(ch_dir / "revenue_structure_policy.json", policy)
    return policy

def run_step02(channel_ids: list) -> dict:
    results = {}
    for ch in channel_ids:
        rpm = create_rpm_reality(ch)
        pol = create_revenue_structure_policy(ch)
        results[ch] = {"rpm_reality":rpm,"revenue_structure_policy":pol}
        print(f"[STEP02] {ch}: rpm_proxy={rpm['rpm_proxy']}")
    return results

if __name__ == "__main__":
    import sys
    run_step02(sys.argv[1:] if len(sys.argv)>1 else ["CH1","CH2"])
