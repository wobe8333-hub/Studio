"""STEP 16 — 월간 리스크 통제."""
import logging
from datetime import datetime
from src.core.ssot import read_json, write_json, json_exists, now_iso
from src.core.config import CHANNELS_DIR, GLOBAL_DIR

logger = logging.getLogger(__name__)

def _channel_risk(channel_id: str, month_str: str) -> dict:
    rev = CHANNELS_DIR/channel_id/"revenue_monthly.json"
    net = 0.0
    if json_exists(rev):
        net = read_json(rev).get("monthly_records",{}).get(month_str,{}).get("net_profit",0.0)
    risks = [] if net >= 1_500_000 else [f"순이익 미달: {net:,.0f}원 < 1,500,000원"]
    return {"channel_id":channel_id,"month":month_str,"net_profit":net,
             "target_achieved":net>=1_500_000,"risks":risks,
             "risk_level":"HIGH" if risks else "LOW"}

def run_step16(month_str: str = None) -> dict:
    if not month_str: month_str = datetime.utcnow().strftime("%Y-%m")
    ch_risks={}; total_net=0.0
    for ch in ["CH1","CH2","CH3","CH4","CH5"]:
        r=_channel_risk(ch,month_str); ch_risks[ch]=r; total_net+=r["net_profit"]
        risk_dir=CHANNELS_DIR/ch/"risk"; risk_dir.mkdir(parents=True, exist_ok=True)
        write_json(risk_dir/f"risk_dashboard_{month_str}.json", r)
    aggregate = {"schema_version":"1.0","month":month_str,
                  "total_net_profit_month":total_net,"target_total_achieved":total_net>=7_500_000,
                  "channels":ch_risks,"generated_at":now_iso()}
    risk_dir = GLOBAL_DIR/"risk"; risk_dir.mkdir(parents=True, exist_ok=True)
    write_json(risk_dir/f"risk_aggregate_{month_str}.json", aggregate)
    logger.info(f"[STEP16] {month_str} total={total_net:,.0f}원")
    return aggregate
