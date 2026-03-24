"""STEP 14 — 수익 다각화 트래킹."""
import logging
from src.core.ssot import read_json, write_json, json_exists, now_iso
from src.core.config import CHANNELS_DIR, GLOBAL_DIR

logger = logging.getLogger(__name__)

def update_revenue_monthly(channel_id: str, month_str: str,
                            adsense_krw: float, affiliate_krw: float,
                            operating_cost: float) -> dict:
    ch_dir = CHANNELS_DIR/channel_id; ch_dir.mkdir(parents=True, exist_ok=True)
    path   = ch_dir/"revenue_monthly.json"
    data   = read_json(path) if json_exists(path) else {
        "schema_version":"1.0","channel_id":channel_id,"monthly_records":{},
    }
    net    = adsense_krw + affiliate_krw - operating_cost
    target = net >= 1_500_000
    total_rev = adsense_krw + affiliate_krw
    data["monthly_records"][month_str] = {
        "month":month_str,"adsense_krw":adsense_krw,"affiliate_krw":affiliate_krw,
        "operating_cost":operating_cost,"total_revenue":total_rev,"net_profit":net,
        "mix_ratio":{"adsense":round(adsense_krw/(total_rev+0.001),2),
                      "affiliate":round(affiliate_krw/(total_rev+0.001),2)},
        "policy_violation_flags": adsense_krw > total_rev * 0.70,
        "target_achieved": target,
        "target_1_5m_achieved": target,
        "updated_at": now_iso(),
    }
    data["net_profit"]=net; data["updated_at"]=now_iso()
    write_json(path, data)
    logger.info(f"[STEP14] {channel_id} {month_str} net={net:,.0f}원")
    return data

def get_total_revenue(month_str: str) -> dict:
    total_net=0.0; by_ch={}; channels_hit=0
    for ch in ["CH1","CH2","CH3","CH4","CH5"]:
        path = CHANNELS_DIR/ch/"revenue_monthly.json"
        if not json_exists(path):
            by_ch[ch]={"net_profit":0,"target_achieved":False,"rpm_stage":"INITIAL"}; continue
        rec  = read_json(path).get("monthly_records",{}).get(month_str,{})
        net  = rec.get("net_profit",0.0)
        hit=rec.get("target_achieved",False)
        by_ch[ch]={"net_profit":net,"target_achieved":hit,"rpm_stage":"INITIAL"}
        total_net+=net
        if hit: channels_hit+=1
    result = {
        "month_id":month_str,"revenue_target_per_channel":1_500_000,
        "revenue_target_total":7_500_000,"by_channel":by_ch,
        "channels_achieved_1_5m":channels_hit,"total_net_profit":total_net,
        "gap_to_total_target":max(0,7_500_000-total_net),
    }
    rev_dir = GLOBAL_DIR/"revenue"; rev_dir.mkdir(parents=True, exist_ok=True)
    write_json(rev_dir/f"revenue_aggregate_{month_str}.json", result)
    return result
