"""KAS 전체 파이프라인 진입점.
버그 수정(BUG-2): can_upload dead import 제거.
버그 수정(BUG-2+3): KAS_ROOT 사용 + LOGS_DIR 사전 생성.
버그 수정(BUG-6): STEP 13 pending 메커니즘 연결 (48h 후 자동 실행).
python -m src.pipeline {month_number} 으로 실행.
"""
import concurrent.futures
import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests
import sentry_sdk
from loguru import logger

from src.core.config import CHANNEL_CATEGORIES, KAS_ROOT, SENTRY_DSN
from src.core.hitl_gate import (
    approve_review,
    reject_review,
    write_review_request,
)
from src.core.manifest import mark_step_done, mark_step_failed
from src.core.pre_cost_estimator import (
    check_cost_limit,
    estimate_pre_run_cost,
    save_cost_projection,
)
from src.quota.youtube_quota import get_quota as get_youtube_quota
from src.step00.channel_registry import get_active_channels
from src.step03.algorithm_policy import get_algorithm_policy
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge
from src.step06.style_policy import build_style_policy
from src.step07.revenue_policy import get_revenue_policy
from src.step08 import run_step08
from src.step09.bgm_overlay import run_step09
from src.step10.thumbnail_generator import generate_thumbnail_from_topic
from src.step10.title_variant_builder import run_step10
from src.step11.qa_gate import run_step11
from src.step_final import run_intro_outro

LOGS_DIR = KAS_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Slack 웹훅 URL (설정하면 Sentry 에러가 Slack으로도 즉시 전송됨)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# loguru 파일 핸들러 설정
logger.add(
    str(LOGS_DIR / "pipeline.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {name}: {message}",
    encoding="utf-8",
    rotation="50 MB",
    retention="30 days",
    level="INFO",
)

STEP08_TIMEOUT_SEC = 1800  # 30분


def _run_step08_timed(
    channel_id: str,
    topic: dict,
    style_policy: dict,
    revenue_policy: dict,
    algorithm_policy: dict,
    timeout_sec: int = STEP08_TIMEOUT_SEC,
) -> str:
    """Step08을 별도 스레드에서 실행하고 timeout_sec 초과 시 TimeoutError를 발생시킨다.

    ThreadPoolExecutor를 cancel_futures=True로 종료하여
    타임아웃 시 블록되지 않도록 한다.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            run_step08, channel_id, topic, style_policy, revenue_policy, algorithm_policy
        )
        return future.result(timeout=timeout_sec)
    finally:
        # wait=False: 실행 중인 스레드 완료를 기다리지 않고 즉시 반환
        executor.shutdown(wait=False)


def _sentry_before_send(event: dict, hint: dict) -> dict:
    """Sentry 이벤트 발생 시 Slack으로도 즉시 알림을 보낸다.
    Sentry 전송을 막지 않도록 항상 event를 반환한다.
    """
    if SLACK_WEBHOOK_URL:
        try:
            exc_values = event.get("exception", {}).get("values", [])
            error_msg = exc_values[0].get("value", "알 수 없는 오류") if exc_values else "알 수 없는 오류"
            requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": f":red_circle: *KAS 파이프라인 에러*\n```{error_msg}```"},
                timeout=5,
            )
        except Exception:
            pass  # Slack 전송 실패가 파이프라인을 멈추면 안 된다
    return event


# Sentry 에러 추적 초기화
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        before_send=_sentry_before_send,
    )

# ── 대시보드 실시간 진행 상태 추적 ────────────────────────────────────────────
_PROGRESS_FILE = KAS_ROOT / "data" / "global" / "step_progress.json"
_STEP_NAMES = [
    "Step05 트렌드+지식 수집",
    "Step06 시나리오 정책",
    "Step07 알고리즘 정책",
    "Step08 영상 생성",
    "Step09 BGM",
    "Step10 제목+썸네일",
    "Step11 QA 검수",
    "Step12 업로드",
]

def _progress_init(channel_id: str, run_id: str) -> None:
    """파이프라인 시작 시 step_progress.json 초기화"""
    data = {
        "active": True,
        "dry_run": False,
        "channel_id": channel_id,
        "run_id": run_id,
        "month_number": 1,
        "steps": [
            {"index": i, "name": name, "status": "idle",
             "started_at": None, "completed_at": None, "elapsed_ms": None}
            for i, name in enumerate(_STEP_NAMES)
        ],
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        _PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[PROGRESS] 초기화 실패: {e}")

def _progress_step(index: int, status: str, started_at: str | None = None) -> None:
    """특정 Step 상태를 업데이트 (running / done / error)"""
    try:
        raw = _PROGRESS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        now = datetime.utcnow().isoformat() + "Z"
        steps = data.get("steps", [])
        for s in steps:
            if s.get("index") == index:
                s["status"] = status
                if status == "running":
                    s["started_at"] = now
                elif status in ("done", "error"):
                    s["completed_at"] = now
                    if s.get("started_at"):
                        try:
                            start = datetime.fromisoformat(s["started_at"].replace("Z", ""))
                            s["elapsed_ms"] = int((datetime.utcnow() - start).total_seconds() * 1000)
                        except Exception:
                            pass
                break
        # 마지막 step 완료 시 active=False
        if status == "done" and index == len(_STEP_NAMES) - 1:
            data["active"] = False
        data["updated_at"] = now
        _PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[PROGRESS] step{index} 업데이트 실패: {e}")

def _mark_pending_step13(channel_id: str, run_id: str, video_id: str) -> None:
    from src.core.config import GLOBAL_DIR
    from src.core.ssot import now_iso, write_json
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
    from src.core.config import CHANNEL_CATEGORIES, GLOBAL_DIR
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
        from src.core.ssot import read_json, write_json
        from src.quota.youtube_quota import QUOTA_FILE, can_upload
        from src.step12.uploader import upload_video
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

        # Step05: 트렌드+지식 수집
        _progress_init(channel_id, f"run_{channel_id}_{int(time.time())}")  # 임시 run_id (Step08 전)
        _progress_step(0, "running")
        trends = collect_trends(channel_id, category, limit=5)
        topics = [reinterpret_trend(t, category, channel_id) for t in trends[:3]]
        save_knowledge(channel_id, topics)
        _progress_step(0, "done")

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
                # Step06: 시나리오 정책
                _progress_step(1, "running")
                style_policy = build_style_policy(channel_id, topic, month_number)
                _progress_step(1, "done")

                # Step07: 알고리즘/수익 정책
                _progress_step(2, "running")
                revenue_policy   = get_revenue_policy(channel_id)
                algorithm_policy = get_algorithm_policy(channel_id)
                _progress_step(2, "done")

                # ── 새 워크플로우 ─────────────────────────────────────────

                # [2] 썸네일 초안 (script 없이 주제만으로 생성)
                import time as _t
                preview_run_id = f"run_{channel_id}_{int(_t.time())}"
                try:
                    generate_thumbnail_from_topic(channel_id, preview_run_id, topic)
                    logger.info(f"[PIPELINE] {channel_id} 썸네일 초안 생성 완료")
                except Exception as eth:
                    logger.warning(f"[PIPELINE] 썸네일 초안 실패 (계속): {eth}")

                # [3-5] Step08: 대본 → 이미지 생성 → 모션 → 나레이션 → 영상 조합
                _progress_step(3, "running")
                run_id = _run_step08_timed(channel_id, topic, style_policy,
                                           revenue_policy, algorithm_policy)
                _progress_init(channel_id, run_id)
                for i in range(3): _progress_step(i, "done")
                _progress_step(3, "running")
                mark_step_done(channel_id, run_id, "step08")
                _progress_step(3, "done")

                # Step09: BGM 오버레이
                _progress_step(4, "running")
                try:
                    run_step09(channel_id, run_id)
                    mark_step_done(channel_id, run_id, "step09")
                    _progress_step(4, "done")
                except Exception as e9:
                    mark_step_failed(channel_id, run_id, "step09", "STEP09_FAIL", str(e9)[:200])
                    _progress_step(4, "error")
                    logger.warning(f"[PIPELINE] Step09 실패 (계속): {e9}")

                # Step10: 썸네일 배리언트 (script 기반 최종본)
                _progress_step(5, "running")
                try:
                    run_step10(channel_id, run_id)
                    mark_step_done(channel_id, run_id, "step10")
                    _progress_step(5, "done")
                except Exception as e10:
                    mark_step_failed(channel_id, run_id, "step10", "STEP10_FAIL", str(e10)[:200])
                    _progress_step(5, "error")
                    logger.warning(f"[PIPELINE] Step10 실패 (계속): {e10}")

                # Step11: 자동 QA
                _progress_step(6, "running")
                try:
                    qa = run_step11(channel_id, run_id,
                                    human_review_completed=False)  # HITL 전 단계
                    mark_step_done(channel_id, run_id, "step11")
                    _progress_step(6, "done")
                except Exception as e11:
                    mark_step_failed(channel_id, run_id, "step11", "STEP11_FAIL", str(e11)[:200])
                    _progress_step(6, "error")
                    logger.error(f"[PIPELINE] Step11 실패: {e11}")
                    qa = {"overall_pass": False}

                # ── [HITL] 사용자 검토 요청 ──────────────────────────────
                from src.core.ssot import get_run_dir as _get_run_dir
                _run_dir  = _get_run_dir(channel_id, run_id)
                _vid_path = _run_dir / "step08" / "video_narr.mp4"
                if not _vid_path.exists():
                    _vid_path = _run_dir / "step08" / "video.mp4"

                write_review_request(channel_id, run_id, _vid_path)
                _progress_step(7, "running")  # 검토 대기 상태

                channel_results.append({
                    "run_id":  run_id,
                    "topic":   topic_title,
                    "qa_pass": qa.get("overall_pass", False),
                    "human_review_required": True,
                    "status": "pending_review",
                })
                logger.info(
                    f"[PIPELINE] {channel_id}/{run_id} 영상 생성 완료 — 검토 대기 중\n"
                    f"  영상: {_vid_path}\n"
                    f"  썸네일: {_run_dir / 'step10'}\n"
                    f"  승인: python -m src.pipeline approve {channel_id} {run_id}\n"
                    f"  거부: python -m src.pipeline reject  {channel_id} {run_id}"
                )
                # 이 토픽은 HITL 대기 → 다음 토픽으로 진행하지 않음
                break

            except concurrent.futures.TimeoutError:
                logger.error(f"[PIPELINE] Step08 {STEP08_TIMEOUT_SEC}초 타임아웃 — {channel_id} 주제 건너뜀")
                continue
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
            import subprocess
            import sys as _sys
            sync_script = KAS_ROOT / "scripts" / "sync_to_supabase.py"
            subprocess.run(
                [_sys.executable, str(sync_script), "all"],
                check=False, timeout=60,
            )
            logger.info("[PIPELINE] Supabase 동기화 완료")
        except Exception as sync_err:
            logger.warning(f"[PIPELINE] Supabase 동기화 실패 (비치명): {sync_err}")

    return results

def _cmd_approve(channel_id: str, run_id: str) -> None:
    """승인 → 인트로/아웃트로 추가 → video_final.mp4 생성."""
    approve_review(channel_id, run_id)
    final_path = run_intro_outro(channel_id, run_id)
    if final_path:
        logger.info(f"[PIPELINE] 최종 영상 완성: {final_path}")
        print(f"\n✅ 최종 영상: {final_path}")
    else:
        logger.error("[PIPELINE] 최종 영상 생성 실패")
        print("\n❌ 최종 영상 생성 실패 — 로그 확인 필요")


def _cmd_reject(channel_id: str, run_id: str) -> None:
    """거부 → 해당 run 거부 표시. 재생성은 pipeline 재실행으로."""
    reject_review(channel_id, run_id)
    print(
        f"\n🔄 {channel_id}/{run_id} 거부됨.\n"
        f"   재생성: python -m src.pipeline {1}"
    )


if __name__ == "__main__":
    # ── CLI 명령 분기 ─────────────────────────────────────────────
    # python -m src.pipeline 1                          → 월간 파이프라인
    # python -m src.pipeline approve CH1 run_CH1_XXX   → 승인 + 최종 영상
    # python -m src.pipeline reject  CH1 run_CH1_XXX   → 거부 (재생성 필요)
    if len(sys.argv) >= 4 and sys.argv[1] in ("approve", "reject"):
        cmd        = sys.argv[1]
        ch_id      = sys.argv[2]
        r_id       = sys.argv[3]
        if cmd == "approve":
            _cmd_approve(ch_id, r_id)
        else:
            _cmd_reject(ch_id, r_id)
    else:
        month_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        run_monthly_pipeline(month_num)
