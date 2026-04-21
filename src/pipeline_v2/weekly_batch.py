"""주간 배치 스케줄러 — 일요일 00:00 cron 진입점 (T43)

Windows 작업 스케줄러 등록:
  python -m src.pipeline_v2.weekly_batch
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json, write_json
from src.pipeline_v2.dag.orchestrator import EpisodeJob, run_weekly_batch
from src.pipeline_v2.episode_schema import EpisodeMeta

PLAN_PATH = Path("data/global/monthly_plan")
BATCH_LOG_PATH = Path("logs/weekly_batch.log")
MAX_CONCURRENT = 4


def _load_weekly_plan(iso_week: str) -> list[dict]:
    """주간 영상 기획 목록 로드 (data/global/monthly_plan/{YYYY-MM}/week_{W}.json)."""
    year_month = iso_week[:7]
    week_num = datetime.now().isocalendar()[1]
    plan_file = PLAN_PATH / year_month / f"week_{week_num:02d}.json"

    if not plan_file.exists():
        logger.warning(f"주간 기획 파일 없음: {plan_file} — 빈 배치로 진행")
        return []

    data = read_json(plan_file)
    return data if isinstance(data, list) else []


def _build_jobs(plan_items: list[dict]) -> list[EpisodeJob]:
    """기획 아이템 → EpisodeJob 변환."""
    jobs = []
    now = datetime.now(timezone.utc)
    iso_week = now.strftime("%GW%V")

    for item in plan_items:
        channel_id = item.get("channel_id", "CH1")
        topic = item.get("topic", "")
        series_id = item.get("series_id", f"{channel_id}_default")
        episode_index = item.get("episode_index", 1)

        episode_id = f"{channel_id}_{iso_week}_{episode_index:03d}"
        meta = EpisodeMeta(
            episode_id=episode_id,
            channel_id=channel_id,
            series_id=series_id,
            episode_index=episode_index,
        )
        job = EpisodeJob(
            channel_id=channel_id,
            series_id=series_id,
            topic=topic,
            episode_meta=meta,
        )
        jobs.append(job)

    return jobs


async def _run_batch(jobs: list[EpisodeJob]) -> dict:
    """배치 실행 + 결과 저장."""
    start_time = datetime.now(timezone.utc)
    logger.info(f"주간 배치 시작: {len(jobs)}개 에피소드")

    results = await run_weekly_batch(jobs, max_concurrent=MAX_CONCURRENT)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    summary = {
        "batch_start": start_time.isoformat(),
        "elapsed_sec": int(elapsed),
        "total_jobs": len(jobs),
        "succeeded": sum(1 for r in results if not isinstance(r, Exception)),
        "failed": sum(1 for r in results if isinstance(r, Exception)),
    }

    log_path = Path("data/global/batch_history.json")
    existing = []
    if log_path.exists():
        try:
            existing = read_json(log_path)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    existing.append(summary)
    write_json(log_path, existing[-52:])

    logger.info(
        f"주간 배치 완료: {summary['succeeded']}/{summary['total_jobs']} 성공 "
        f"({elapsed:.0f}s / {elapsed/3600:.1f}h)"
    )
    if elapsed > 42 * 3600:
        logger.warning(f"SLA 초과: {elapsed/3600:.1f}h > 42h 한계")

    return summary


def main() -> None:
    """배치 진입점 (Windows 작업 스케줄러 / cron)."""
    now = datetime.now(timezone.utc)
    iso_week = now.strftime("%GW%V")

    logger.add(BATCH_LOG_PATH, rotation="50 MB", retention=10, encoding="utf-8")
    logger.info(f"=== 주간 배치 시작 {iso_week} ===")

    plan_items = _load_weekly_plan(iso_week)
    if not plan_items:
        logger.info("기획 없음 — 배치 종료")
        return

    jobs = _build_jobs(plan_items)
    asyncio.run(_run_batch(jobs))


if __name__ == "__main__":
    main()
