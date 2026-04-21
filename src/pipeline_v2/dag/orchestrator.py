"""4 병렬 트랙 DAG 오케스트레이터 (asyncio 기반)"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta, save_episode


class TrackStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TrackResult:
    track_name: str
    status: TrackStatus
    output: dict = field(default_factory=dict)
    error: Optional[str] = None
    elapsed_sec: float = 0.0


@dataclass
class EpisodeJob:
    channel_id: str
    series_id: str
    episode_index: int
    topic: str
    episode_meta: EpisodeMeta

    track_a_result: Optional[TrackResult] = None
    track_b_result: Optional[TrackResult] = None
    track_c_result: Optional[TrackResult] = None
    track_d_result: Optional[TrackResult] = None
    final_video_path: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


async def _run_track(name: str, coro) -> TrackResult:
    t0 = time.time()
    try:
        output = await coro
        elapsed = time.time() - t0
        logger.info(f"Track {name} 완료 ({elapsed:.1f}s)")
        return TrackResult(name, TrackStatus.DONE, output=output or {}, elapsed_sec=elapsed)
    except Exception as exc:
        elapsed = time.time() - t0
        logger.error(f"Track {name} 실패 ({elapsed:.1f}s): {exc}")
        return TrackResult(name, TrackStatus.FAILED, error=str(exc), elapsed_sec=elapsed)


async def run_episode_dag(job: EpisodeJob) -> EpisodeJob:
    """4 트랙을 가능한 병렬로 실행.

    흐름:
        A (Narrative) ─────────────────┐
        B (Audio)      ─── 병렬 A ─────┤
                                       ├─▶ D (Assembly) ─▶ 완료
        C (Visual)     ─── 병렬 A,B ───┘
    """
    from src.pipeline_v2.dag.track_a_narrative import run_track_a
    from src.pipeline_v2.dag.track_b_audio import run_track_b
    from src.pipeline_v2.dag.track_c_visual import run_track_c
    from src.pipeline_v2.dag.track_d_assembly import run_track_d

    meta = job.episode_meta
    logger.info(f"에피소드 DAG 시작: {meta.channel_id}/{meta.series_id}/{meta.episode_index}")

    # Track A, B, C 병렬 실행
    a_task = asyncio.create_task(_run_track("A-Narrative", run_track_a(job)))
    b_task = asyncio.create_task(_run_track("B-Audio", run_track_b(job)))
    c_task = asyncio.create_task(_run_track("C-Visual", run_track_c(job)))

    job.track_a_result, job.track_b_result, job.track_c_result = await asyncio.gather(
        a_task, b_task, c_task, return_exceptions=False
    )

    # 하나라도 실패하면 D 중단
    failed = [
        r for r in [job.track_a_result, job.track_b_result, job.track_c_result]
        if r and r.status == TrackStatus.FAILED
    ]
    if failed:
        logger.error(f"트랙 실패로 Assembly 중단: {[r.track_name for r in failed]}")
        job.completed_at = time.time()
        save_episode(meta)
        return job

    # Track D: 수렴 (A+B+C 결과 사용)
    job.track_d_result = await _run_track("D-Assembly", run_track_d(job))

    if job.track_d_result.status == TrackStatus.DONE:
        job.final_video_path = job.track_d_result.output.get("video_path")
        meta.video_path = job.final_video_path or ""

    job.completed_at = time.time()
    elapsed_total = job.completed_at - job.started_at
    logger.info(f"에피소드 DAG 완료: {meta.episode_id} ({elapsed_total:.1f}s)")

    meta.features.production_time_sec = int(elapsed_total)
    save_episode(meta)
    return job


async def run_weekly_batch(
    jobs: list[EpisodeJob],
    max_concurrent: int = 4,
) -> list[EpisodeJob]:
    """주간 배치 — 최대 max_concurrent 에피소드 동시 실행."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded(job: EpisodeJob) -> EpisodeJob:
        async with semaphore:
            return await run_episode_dag(job)

    results = await asyncio.gather(*[bounded(j) for j in jobs])
    done = sum(1 for j in results if j.final_video_path)
    logger.info(f"주간 배치 완료: {done}/{len(jobs)} 성공")
    return list(results)
