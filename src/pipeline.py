"""KAS 전체 파이프라인 진입점.
버그 수정(BUG-2): can_upload dead import 제거.
버그 수정(BUG-2+3): KAS_ROOT 사용 + LOGS_DIR 사전 생성.
버그 수정(BUG-6): STEP 13 pending 메커니즘 연결 (48h 후 자동 실행).
python -m src.pipeline {month_number} 으로 실행.
"""
import time, logging, sys
from datetime import datetime, timedelta
from src.core.config import KAS_ROOT, CHANNEL_CATEGORIES, CHANNEL_MONTHLY_TARGET
from src.step00.channel_registry import get_active_channels
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge
from src.step06.style_policy import build_style_policy
from src.step07.revenue_policy import get_revenue_policy
from src.step03.algorithm_policy import get_algorithm_policy
from src.step08 import run_step08
from src.step09.bgm_overlay import run_step09
from src.step10.title_variant_builder import run_step10
from src.step11.qa_gate import run_step11

LOGS_DIR = KAS_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOGS_DIR / "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def _mark_pending_step13(channel_id: str, run_id: str, video_id: str) -> None:
    from src.core.ssot import write_json, now_iso
    from src.core.config import GLOBAL_DIR
    pending_dir = GLOBAL_DIR / "step13_pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    kpi_after = (datetime.utcnow() + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(pending_dir / f"{channel_id}_{run_id}.json", {
        "channel_id":channel_id,"run_id":run_id,"video_id":video_id,
        "upload_at":now_iso(),"kpi_collect_after":kpi_after,"step13_completed":False,
    })
    logger.info(f"[PIPELINE] STEP13 pending 등록: {channel_id}/{run_id} (48h 후)")

def _run_pending_step13() -> None:
    from src.core.config import GLOBAL_DIR
    from src.core.ssot import read_json, write_json
    from src.step12.kpi_collector import collect_kpi_48h
    from src.step13.learning_feedback import run_step13
    pending_dir = GLOBAL_DIR / "step13_pending"
    if not pending_dir.exists(): return
    now = datetime.utcnow()
    for pf in pending_dir.glob("*.json"):
        try:
            p = read_json(pf)
            if p.get("step13_completed"): continue
            kpi_time = datetime.fromisoformat(p["kpi_collect_after"].replace("Z",""))
            if now < kpi_time:
                logger.info(f"[PIPELINE] STEP13 대기: {pf.name} ({int((kpi_time-now).total_seconds()/3600)}h 남음)")
                continue
            ch=p["channel_id"]; rid=p["run_id"]; vid=p["video_id"]
            logger.info(f"[PIPELINE] STEP12~13 실행: {ch}/{rid}")
            collect_kpi_48h(ch, rid, vid)
            run_step13(ch, rid)
            p["step13_completed"]=True; write_json(pf, p)
            logger.info(f"[PIPELINE] STEP13 완료: {ch}/{rid}")
        except Exception as e:
            logger.error(f"[PIPELINE] pending STEP13 실패 {pf.name}: {e}")

def run_monthly_pipeline(month_number: int) -> dict:
    logger.info(f"=== 월간 파이프라인 시작 (월차={month_number}) ===")
    _run_pending_step13()
    results = {}
    active_channels = get_active_channels(month_number)
    logger.info(f"활성 채널: {active_channels}")

    for channel_id in active_channels:
        category = CHANNEL_CATEGORIES[channel_id]
        logger.info(f"--- {channel_id} ({category}) 처리 시작 ---")

        trends = collect_trends(channel_id, category, limit=5)
        topics = [reinterpret_trend(t, category, channel_id) for t in trends[:3]]
        save_knowledge(channel_id, topics)

        channel_results = []
        for topic in topics:
            try:
                style_policy     = build_style_policy(channel_id, topic, month_number)
                revenue_policy   = get_revenue_policy(channel_id)
                algorithm_policy = get_algorithm_policy(channel_id)
                run_id           = run_step08(channel_id, topic, style_policy,
                                              revenue_policy, algorithm_policy)
                run_step09(channel_id, run_id)
                run_step10(channel_id, run_id)
                qa = run_step11(channel_id, run_id,
                                 human_review_completed=(channel_id not in {"CH1","CH2","CH4"}))

                if qa.get("overall_pass") and channel_id not in {"CH1","CH2","CH4"}:
                    try:
                        from src.step12.uploader import upload_video
                        receipt = upload_video(channel_id, run_id)
                        _mark_pending_step13(channel_id, run_id, receipt.get("video_id",""))
                    except Exception as upload_err:
                        logger.error(f"[PIPELINE] STEP12 실패 {channel_id}/{run_id}: {upload_err}")

                channel_results.append({
                    "run_id":  run_id,
                    "topic":   topic.get("reinterpreted_title",""),
                    "qa_pass": qa.get("overall_pass",False),
                    "human_review_required": qa.get("human_review",{}).get("required",False),
                })
                logger.info(f"[PIPELINE] {channel_id}/{run_id} 완료, QA={qa['overall_pass']}")

            except Exception as e:
                logger.error(f"[PIPELINE] {channel_id} 오류: {e}")
                continue

        results[channel_id] = channel_results
        time.sleep(2)

    logger.info("=== 월간 파이프라인 완료 ===")
    return results

if __name__ == "__main__":
    month_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_monthly_pipeline(month_num)
