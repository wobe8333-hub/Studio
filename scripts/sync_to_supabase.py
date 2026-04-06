"""
KAS JSON → Supabase DB 동기화 스크립트

파이프라인 완료 후 자동 호출되거나 수동으로 실행 가능.

사용법:
    python scripts/sync_to_supabase.py          # 전체 동기화
    python scripts/sync_to_supabase.py channels  # 채널 레지스트리만
    python scripts/sync_to_supabase.py revenue   # 수익 데이터만
"""

import sys
import os
import json
import glob
from pathlib import Path
from datetime import datetime

from loguru import logger

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.config import KAS_ROOT, CHANNEL_IDS
from src.core.ssot import read_json

# Supabase 클라이언트 초기화
try:
    from supabase import create_client, Client

    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase 클라이언트 초기화 완료")

except ImportError:
    logger.error("supabase 패키지가 설치되지 않았습니다: pip install supabase")
    sys.exit(1)


def sync_channels() -> int:
    """채널 레지스트리 동기화"""
    registry_path = KAS_ROOT / "data" / "global" / "channel_registry.json"
    if not registry_path.exists():
        logger.warning(f"채널 레지스트리 파일 없음: {registry_path}")
        return 0

    data = read_json(registry_path)
    channels = data.get("channels", []) if isinstance(data, dict) else data

    upserted = 0
    for ch in channels:
        row = {
            "id": ch.get("id") or ch.get("channel_id"),
            "category": ch.get("category", ""),
            "category_ko": ch.get("category_ko", ""),
            "youtube_channel_id": ch.get("youtube_channel_id"),
            "launch_phase": ch.get("launch_phase", 1),
            "status": ch.get("status", "active"),
            "rpm_proxy": ch.get("rpm_proxy", 2),
            "revenue_target_monthly": ch.get("revenue_target_monthly", 2000000),
            "monthly_longform_target": ch.get("monthly_longform_target"),
            "monthly_shorts_target": ch.get("monthly_shorts_target"),
            "subscriber_count": ch.get("subscriber_count", 0),
            "video_count": ch.get("video_count", 0),
            "algorithm_trust_level": ch.get("algorithm_trust_level", "PRE-ENTRY"),
            "updated_at": datetime.utcnow().isoformat(),
        }
        supabase.table("channels").upsert(row).execute()
        upserted += 1

    logger.info(f"채널 레지스트리 동기화 완료: {upserted}건")
    return upserted


def sync_pipeline_runs() -> int:
    """파이프라인 실행 이력 동기화"""
    total = 0
    for ch_id in CHANNEL_IDS:
        manifest_paths = list(
            (KAS_ROOT / "runs" / ch_id).glob("run_*/manifest.json")
        )
        for mp in manifest_paths:
            try:
                data = read_json(mp)
                run_id = data.get("run_id", mp.parent.name)
                row = {
                    "id": run_id,
                    "channel_id": ch_id,
                    "run_state": data.get("run_state", "UNKNOWN"),
                    "topic_title": data.get("topic", {}).get("reinterpreted_title"),
                    "topic_category": data.get("topic", {}).get("category"),
                    "topic_score": data.get("topic", {}).get("score"),
                    "is_trending": data.get("topic", {}).get("is_trending", False),
                    "created_at": data.get("created_at"),
                    "completed_at": data.get("completed_at"),
                }
                supabase.table("pipeline_runs").upsert(row).execute()
                total += 1
            except Exception as e:
                logger.warning(f"실행 이력 파싱 실패 {mp}: {e}")

    logger.info(f"파이프라인 실행 이력 동기화 완료: {total}건")
    return total


def sync_revenue() -> int:
    """월별 수익 데이터 동기화"""
    total = 0
    for ch_id in CHANNEL_IDS:
        revenue_path = KAS_ROOT / "data" / "channels" / ch_id / "revenue_monthly.json"
        if not revenue_path.exists():
            continue
        data = read_json(revenue_path)
        records = data if isinstance(data, list) else [data]
        for rec in records:
            row = {
                "channel_id": ch_id,
                "month": rec.get("month"),
                "adsense_krw": rec.get("adsense_krw", 0),
                "affiliate_krw": rec.get("affiliate_krw", 0),
                "operating_cost": rec.get("operating_cost", 0),
                "net_profit": rec.get("net_profit", 0),
                "target_achieved": rec.get("target_achieved", False),
                "mix_ratio_adsense": rec.get("mix_ratio_adsense"),
                "mix_ratio_affiliate": rec.get("mix_ratio_affiliate"),
                "updated_at": datetime.utcnow().isoformat(),
            }
            supabase.table("revenue_monthly").upsert(
                row, on_conflict="channel_id,month"
            ).execute()
            total += 1

    logger.info(f"수익 데이터 동기화 완료: {total}건")
    return total


def sync_risk() -> int:
    """리스크 데이터 동기화"""
    risk_files = list(
        (KAS_ROOT / "data" / "global" / "risk").glob("risk_aggregate_*.json")
    )
    total = 0
    for rf in risk_files:
        try:
            data = read_json(rf)
            channels_raw = data.get("channels", []) if isinstance(data, dict) else data
            # channels가 dict(키=채널ID)인 경우 values()로 변환
            records = list(channels_raw.values()) if isinstance(channels_raw, dict) else channels_raw
            month = data.get("month") if isinstance(data, dict) else None
            for rec in records:
                row = {
                    "channel_id": rec.get("channel_id"),
                    "month": rec.get("month") or month,
                    "net_profit": rec.get("net_profit", 0),
                    "target": rec.get("target", 2000000),
                    "risk_level": "HIGH" if not rec.get("target_achieved", False) else "LOW",
                    "risks": rec.get("risks", []),
                    "generated_at": datetime.utcnow().isoformat(),
                }
                supabase.table("risk_monthly").upsert(
                    row, on_conflict="channel_id,month"
                ).execute()
                total += 1
        except Exception as e:
            logger.warning(f"리스크 파일 파싱 실패 {rf}: {e}")

    logger.info(f"리스크 데이터 동기화 완료: {total}건")
    return total


def sync_trend_topics() -> int:
    """트렌드 주제 동기화 (knowledge store)"""
    total = 0
    for ch_id in CHANNEL_IDS:
        assets_path = (
            KAS_ROOT
            / "data"
            / "knowledge_store"
            / ch_id
            / "discovery"
            / "raw"
            / "assets.jsonl"
        )
        if not assets_path.exists():
            continue
        with open(assets_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    row = {
                        "channel_id": ch_id,
                        "original_topic": rec.get("original_topic"),
                        "reinterpreted_title": rec.get("reinterpreted_title"),
                        "score": rec.get("score"),
                        "grade": rec.get("grade", "review"),
                        "is_trending": rec.get("is_trending", False),
                        "topic_type": rec.get("topic_type"),
                        "collected_at": rec.get("collected_at", datetime.utcnow().isoformat()),
                    }
                    supabase.table("trend_topics").upsert(
                        row, on_conflict="channel_id,reinterpreted_title"
                    ).execute()
                    total += 1
                except Exception as e:
                    logger.warning(f"트렌드 주제 파싱 실패: {e}")

    logger.info(f"트렌드 주제 동기화 완료: {total}건")
    return total


def sync_quota() -> int:
    """API 쿼터/비용 동기화"""
    quota_files = list(
        (KAS_ROOT / "data" / "global" / "quota").glob("*_daily.json")
    )
    total = 0
    for qf in quota_files:
        try:
            service = qf.stem.replace("_quota_daily", "").replace("_daily", "")
            data = read_json(qf)
            row = {
                "date": data.get("date", str(datetime.utcnow().date())),
                "service": service,
                "total_requests": data.get("total_requests", 0),
                "images_generated": data.get("images_generated", 0),
                "cache_hit_rate": data.get("cache_hit_rate", 0),
                "quota_used": data.get("quota_used", 0),
                "quota_remaining": data.get("quota_remaining", 0),
                "cost_krw": data.get("cost_krw", 0),
            }
            supabase.table("quota_daily").upsert(
                row, on_conflict="date,service"
            ).execute()
            total += 1
        except Exception as e:
            logger.warning(f"쿼터 파일 파싱 실패 {qf}: {e}")

    logger.info(f"쿼터 데이터 동기화 완료: {total}건")
    return total


def sync_learning_feedback() -> int:
    """Step13 학습 피드백 동기화"""
    total = 0
    for ch_id in CHANNEL_IDS:
        for run_dir in sorted((KAS_ROOT / "runs" / ch_id).glob("run_*")):
            s13 = run_dir / "step13" / "variant_performance.json"
            s12 = run_dir / "step12" / "kpi_48h.json"
            if not s13.exists() or not s12.exists():
                continue
            try:
                perf = read_json(s13)
                kpi  = read_json(s12)
                row = {
                    "run_id":               perf.get("run_id"),
                    "channel_id":           ch_id,
                    "ctr":                  kpi.get("ctr"),
                    "avp":                  kpi.get("avg_view_percentage"),
                    "views":                kpi.get("views"),
                    "algorithm_stage":      perf.get("algorithm_stage"),
                    "preferred_title_mode": "curiosity",
                    "revenue_on_track":     bool(perf.get("revenue_on_track", False)),
                    "recorded_at":          perf.get("recorded_at"),
                }
                if not row["run_id"]:
                    continue
                supabase.table("learning_feedback").upsert(
                    row, on_conflict="run_id"
                ).execute()
                total += 1
            except Exception as e:
                logger.warning(f"학습 피드백 파싱 실패 {run_dir}: {e}")

    logger.info(f"학습 피드백 동기화 완료: {total}건")
    return total


SYNC_MAP = {
    "channels":  sync_channels,
    "runs":      sync_pipeline_runs,
    "revenue":   sync_revenue,
    "risk":      sync_risk,
    "trends":    sync_trend_topics,
    "quota":     sync_quota,
    "learning":  sync_learning_feedback,
}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        tasks = list(SYNC_MAP.values())
    elif target in SYNC_MAP:
        tasks = [SYNC_MAP[target]]
    else:
        logger.error(f"알 수 없는 동기화 대상: {target}. 사용 가능: {list(SYNC_MAP.keys())}")
        sys.exit(1)

    logger.info(f"동기화 시작: {target}")
    total = sum(fn() for fn in tasks)
    logger.info(f"전체 동기화 완료: {total}건")


if __name__ == "__main__":
    main()
