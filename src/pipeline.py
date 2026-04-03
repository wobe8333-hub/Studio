"""KAS 전체 파이프라인 진입점.
버그 수정(BUG-2): can_upload dead import 제거.
버그 수정(BUG-2+3): KAS_ROOT 사용 + LOGS_DIR 사전 생성.
버그 수정(BUG-6): STEP 13 pending 메커니즘 연결 (48h 후 자동 실행).
python -m src.pipeline {month_number} 으로 실행.
"""
import time, sys
from datetime import datetime, timedelta
from loguru import logger
import sentry_sdk
from src.core.config import KAS_ROOT, CHANNEL_CATEGORIES, CHANNEL_MONTHLY_TARGET, SENTRY_DSN
from src.step00.channel_registry import get_active_channels
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge
from src.step06.style_policy import build_style_policy
from src.step07.revenue_policy import get_revenue_policy
from src.step03.algorithm_policy import get_algorithm_policy
from src.step08 import run_step08
from src.step09.bgm_overlay import run_step09
from src.step10.title_variant_builder import run_step10
from src.step11.qa_gate import run_step11
from src.core.manifest import mark_step_done, mark_step_failed
from src.core.pre_cost_estimator import estimate_pre_run_cost, check_cost_limit, save_cost_projection
from src.quota.youtube_quota import get_quota as get_youtube_quota

LOGS_DIR = KAS_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# loguru 파일 핸들러 설정
logger.add(
    str(LOGS_DIR / "pipeline.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {name}: {message}",
    encoding="utf-8",
    rotation="50 MB",
    retention="30 days",
    level="INFO",
)

# Sentry 에러 추적 초기화
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

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

def _ensure_initialized() -> None:
    """Step00~04 초기화 가드 — data/global/.initialized 플래그가 없을 때 1회 실행"""
    from src.core.config import GLOBAL_DIR, CHANNEL_CATEGORIES
    flag = GLOBAL_DIR / ".initialized"
    if flag.exists():
        return
    logger.info("[PIPELINE] 초기화 시작 (Step00~04)...")
    from src.step00.global_init import run_global_init
    run_global_init()
    all_channels = list(CHANNEL_CATEGORIES.keys())
    try:
        from src.step01.channel_baseline import run_step01
        run_step01(all_channels)
    except Exception as e:
        logger.warning(f"[PIPELINE] Step01 초기화 오류 (계속): {e}")
    try:
        from src.step02.revenue_structure import run_step02
        run_step02(all_channels)
    except Exception as e:
        logger.warning(f"[PIPELINE] Step02 초기화 오류 (계속): {e}")
    from src.step03.algorithm_policy import get_algorithm_policy
    for ch in all_channels:
        try:
            get_algorithm_policy(ch)
        except Exception:
            pass
    try:
        from src.step04.portfolio_plan import create_portfolio_plan
        create_portfolio_plan(1)
    except Exception as e:
        logger.warning(f"[PIPELINE] Step04 초기화 오류 (계속): {e}")
    flag.touch()
    logger.info("[PIPELINE] Step00~04 초기화 완료")


def _check_topic_cost(channel_id: str, topic_title: str) -> bool:
    """pre_cost_estimator로 주제당 비용 사전 검증 — 초과 시 False 반환"""
    try:
        est_calls = 15   # Gemini API 호출 수 추정 (스크립트+이미지+태그 등)
        est_tokens = 5000  # 평균 토큰 수 추정
        total_cost, breakdown = estimate_pre_run_cost(est_calls, est_tokens)
        allowed, msg = check_cost_limit(total_cost)
        save_cost_projection(
            {**breakdown, "channel_id": channel_id, "topic": topic_title[:80]}, KAS_ROOT
        )
        if not allowed:
            logger.error(f"[PIPELINE] 비용 초과 차단: {msg}")
        return allowed
    except Exception as e:
        logger.warning(f"[PIPELINE] pre_cost_estimator 오류 (실행 허용): {e}")
        return True  # 비용 추정 실패 시 실행 허용


def _run_deferred_uploads() -> None:
    """쿼터 부족으로 이연된 업로드 작업을 재처리한다.

    youtube_quota.json의 deferred_jobs 목록을 확인하여
    현재 쿼터 여유가 있을 때 업로드를 재시도한다.
    """
    try:
        quota_data = get_youtube_quota()
        deferred = quota_data.get("deferred_jobs", [])
        if not deferred:
            return
        logger.info(f"[PIPELINE] 이연된 업로드 {len(deferred)}건 재처리 시도")
        from src.step12.uploader import upload_video
        from src.quota.youtube_quota import can_upload, QUOTA_FILE
        from src.core.ssot import read_json, write_json
        still_deferred = []
        for job in deferred:
            ch = job.get("channel_id", "")
            rid = job.get("run_id", "")
            if not ch or not rid:
                continue
            if not can_upload():
                logger.info(f"[PIPELINE] 쿼터 부족 — 이연 유지: {ch}/{rid}")
                still_deferred.append(job)
                continue
            try:
                receipt = upload_video(ch, rid)
                mark_step_done(ch, rid, "step12")
                _mark_pending_step13(ch, rid, receipt.get("video_id", ""))
                logger.info(f"[PIPELINE] 이연 업로드 완료: {ch}/{rid}")
            except Exception as e:
                logger.error(f"[PIPELINE] 이연 업로드 재시도 실패 {ch}/{rid}: {e}")
                still_deferred.append(job)
        # 남은 이연 목록 업데이트
        q = read_json(QUOTA_FILE)
        q["deferred_jobs"] = still_deferred
        write_json(QUOTA_FILE, q)
    except Exception as e:
        logger.warning(f"[PIPELINE] _run_deferred_uploads 오류 (계속): {e}")


def _run_monthly_reports(month_str: str) -> None:
    """Step14, Step16, Step17 월말 집계 보고서 생성"""
    logger.info(f"[PIPELINE] 월말 보고서 생성 중 ({month_str})...")
    try:
        from src.step14.revenue_tracker import get_total_revenue
        rev = get_total_revenue(month_str)
        logger.info(f"[PIPELINE] Step14 완료: 총 순이익={rev.get('total_net_profit', 0):,.0f}원 "
                    f"(달성률={rev.get('achievement_rate', 0)}%)")
    except Exception as e:
        logger.error(f"[PIPELINE] Step14 실패: {e}")
    try:
        from src.step16.risk_control import run_step16
        risk = run_step16(month_str)
        logger.info(f"[PIPELINE] Step16 완료: total={risk.get('total_net_profit_month', 0):,.0f}원")
    except Exception as e:
        logger.error(f"[PIPELINE] Step16 실패: {e}")
    try:
        from src.step17.sustainability import run_step17
        run_step17()
        logger.info("[PIPELINE] Step17 완료: 지속성 분석 보고서 생성")
    except Exception as e:
        logger.error(f"[PIPELINE] Step17 실패: {e}")


def run_monthly_pipeline(month_number: int) -> dict:
    _ensure_initialized()  # C-1: Step00~04 최초 1회 초기화
    logger.info(f"=== 월간 파이프라인 시작 (월차={month_number}) ===")
    _run_deferred_uploads()   # E-4: 이연된 업로드 먼저 재처리
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
            topic_title = topic.get("reinterpreted_title", "")

            # C-5: 주제별 사전 비용 검증
            if not _check_topic_cost(channel_id, topic_title):
                logger.warning(f"[PIPELINE] {channel_id} 비용 초과 — 토픽 스킵: {topic_title[:40]}")
                continue

            run_id = None
            qa = {"overall_pass": False}
            try:
                style_policy     = build_style_policy(channel_id, topic, month_number)
                revenue_policy   = get_revenue_policy(channel_id)
                algorithm_policy = get_algorithm_policy(channel_id)

                # Step08: 영상 생성 (run_id 반환)
                run_id = run_step08(channel_id, topic, style_policy,
                                    revenue_policy, algorithm_policy)
                mark_step_done(channel_id, run_id, "step08")  # C-2

                # Step09: BGM 오버레이
                try:
                    run_step09(channel_id, run_id)
                    mark_step_done(channel_id, run_id, "step09")
                except Exception as e9:
                    mark_step_failed(channel_id, run_id, "step09", "STEP09_FAIL", str(e9)[:200])
                    logger.warning(f"[PIPELINE] Step09 실패 (계속): {e9}")

                # Step10: 제목/썸네일 배리언트
                try:
                    run_step10(channel_id, run_id)
                    mark_step_done(channel_id, run_id, "step10")
                except Exception as e10:
                    mark_step_failed(channel_id, run_id, "step10", "STEP10_FAIL", str(e10)[:200])
                    logger.warning(f"[PIPELINE] Step10 실패 (계속): {e10}")

                # Step11: QA 게이트
                try:
                    qa = run_step11(channel_id, run_id,
                                    human_review_completed=(channel_id not in {"CH1","CH2","CH4"}))
                    mark_step_done(channel_id, run_id, "step11")
                except Exception as e11:
                    mark_step_failed(channel_id, run_id, "step11", "STEP11_FAIL", str(e11)[:200])
                    logger.error(f"[PIPELINE] Step11 실패: {e11}")
                    qa = {"overall_pass": False}

                # Step12: 업로드 (QA 통과 + 수동 검수 불필요 채널)
                if qa.get("overall_pass") and channel_id not in {"CH1","CH2","CH4"}:
                    try:
                        from src.step12.uploader import upload_video
                        receipt = upload_video(channel_id, run_id)
                        mark_step_done(channel_id, run_id, "step12")
                        _mark_pending_step13(channel_id, run_id, receipt.get("video_id",""))
                    except Exception as upload_err:
                        mark_step_failed(channel_id, run_id, "step12",
                                         "STEP12_FAIL", str(upload_err)[:200])
                        logger.error(f"[PIPELINE] STEP12 실패 {channel_id}/{run_id}: {upload_err}")

                    # Shorts 파이프라인
                    try:
                        from src.step08_s.shorts_generator import run_step08s
                        from src.step12.shorts_uploader import run_shorts_upload
                        run_step08s(channel_id, run_id)
                        run_shorts_upload(channel_id, run_id)
                        logger.info(f"[PIPELINE] {channel_id}/{run_id} Shorts 생성/업로드 완료")
                    except Exception as shorts_err:
                        logger.warning(f"[PIPELINE] Shorts 파이프라인 실패 {channel_id}/{run_id}: {shorts_err}")

                channel_results.append({
                    "run_id":  run_id,
                    "topic":   topic_title,
                    "qa_pass": qa.get("overall_pass", False),
                    "human_review_required": qa.get("human_review", {}).get("required", False),
                })
                logger.info(f"[PIPELINE] {channel_id}/{run_id} 완료, QA={qa.get('overall_pass')}")

            except Exception as e:
                if run_id:
                    mark_step_failed(channel_id, run_id, "step08", "STEP08_FAIL", str(e)[:200])
                logger.error(f"[PIPELINE] {channel_id} 오류: {e}")
                continue

        results[channel_id] = channel_results
        time.sleep(2)

    # C-6: Step14/16/17 월말 집계 보고서
    month_str = datetime.utcnow().strftime("%Y-%m")
    _run_monthly_reports(month_str)

    logger.info("=== 월간 파이프라인 완료 ===")

    # C-7: Supabase 동기화 (SUPABASE_URL 설정된 경우에만)
    import os
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        try:
            import subprocess, sys as _sys
            sync_script = KAS_ROOT / "scripts" / "sync_to_supabase.py"
            subprocess.run(
                [_sys.executable, str(sync_script), "all"],
                check=False, timeout=60,
            )
            logger.info("[PIPELINE] Supabase 동기화 완료")
        except Exception as sync_err:
            logger.warning(f"[PIPELINE] Supabase 동기화 실패 (비치명): {sync_err}")

    return results

if __name__ == "__main__":
    month_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_monthly_pipeline(month_num)
