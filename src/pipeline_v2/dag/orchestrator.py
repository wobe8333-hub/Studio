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
    """4 트랙을 최적 순서로 실행.

    흐름:
        A (Narrative) ──────────────────────────┐
                                                 ├─ B (Audio) ─┐
                                                 │              ├─▶ D (Assembly) ─▶ 완료
                                                 └─ C (Visual) ─┘

    A가 먼저 완료되어야 B(BGM 감정 분석)·C(스크립트 기반 캐릭터 추출) 가능.
    B와 C는 A 완료 후 병렬 실행.
    """
    from src.pipeline_v2.dag.track_a_narrative import run_track_a
    from src.pipeline_v2.dag.track_b_audio import run_track_b
    from src.pipeline_v2.dag.track_c_visual import run_track_c
    from src.pipeline_v2.dag.track_d_assembly import run_track_d

    meta = job.episode_meta
    logger.info(f"에피소드 DAG 시작: {meta.channel_id}/{meta.series_id}/{meta.episode_index}")

    # Step 1: Track A 먼저 실행 (스크립트가 B·C의 입력)
    job.track_a_result = await _run_track("A-Narrative", run_track_a(job))
    if job.track_a_result.status == TrackStatus.FAILED:
        logger.error(f"Track A 실패 — 전체 중단: {job.track_a_result.error}")
        job.completed_at = time.time()
        save_episode(meta)
        return job

    # Track A 결과를 job에 즉시 반영 (B·C가 참조 가능하도록)
    if job.track_a_result.output:
        meta.title = job.track_a_result.output.get("titles", [meta.title])[0] or meta.title

    # HITL Gate 1: 시리즈 승인 — Track A 완료 직후 신규 시리즈 첫 에피소드에만 트리거
    if job.episode_index == 1:
        await _trigger_series_approval(job)

    # Step 2: Track B + C 병렬 실행 (둘 다 A의 스크립트 사용)
    b_task = asyncio.create_task(_run_track("B-Audio", run_track_b(job)))
    c_task = asyncio.create_task(_run_track("C-Visual", run_track_c(job)))
    job.track_b_result, job.track_c_result = await asyncio.gather(b_task, c_task)

    # HITL Gate 2: 썸네일 거부권 — Track C 완료 후 썸네일이 생성된 경우 트리거
    if job.track_c_result and job.track_c_result.status == TrackStatus.DONE:
        await _trigger_thumbnail_veto(job)

    # 하나라도 실패하면 D 중단
    failed = [
        r for r in [job.track_b_result, job.track_c_result]
        if r and r.status == TrackStatus.FAILED
    ]
    if failed:
        logger.error(f"트랙 실패로 Assembly 중단: {[r.track_name for r in failed]}")
        job.completed_at = time.time()
        save_episode(meta)
        return job

    # Step 3: Track D: 수렴 (A+B+C 결과 사용)
    job.track_d_result = await _run_track("D-Assembly", run_track_d(job))

    if job.track_d_result.status == TrackStatus.DONE:
        job.final_video_path = job.track_d_result.output.get("video_path")
        meta.video_path = job.final_video_path or ""

    # Step 4: QC 5 레이어 자동 실행 (Track D 성공 시)
    if job.track_d_result and job.track_d_result.status == TrackStatus.DONE:
        await _run_qc(job)

    # HITL Gate 3: 최종 프리뷰 — QC 통과 후 업로드 직전 트리거
    if (
        job.track_d_result
        and job.track_d_result.status == TrackStatus.DONE
        and job.final_video_path
    ):
        await _trigger_final_preview(job)

    job.completed_at = time.time()
    elapsed_total = job.completed_at - job.started_at
    logger.info(f"에피소드 DAG 완료: {meta.episode_id} ({elapsed_total:.1f}s)")

    meta.features.production_time_sec = int(elapsed_total)
    save_episode(meta)
    return job


async def _trigger_series_approval(job: "EpisodeJob") -> None:
    """HITL Gate 1: 시리즈 승인 신호 발송."""
    from src.pipeline_v2.hitl_gate import trigger_series_approval
    meta = job.episode_meta
    titles: list[str] = []
    if job.track_a_result and job.track_a_result.output:
        raw = job.track_a_result.output.get("titles", [])
        titles = raw if isinstance(raw, list) else [str(raw)]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: trigger_series_approval(meta.channel_id, job.series_id, titles),
    )


async def _trigger_thumbnail_veto(job: "EpisodeJob") -> None:
    """HITL Gate 2: 썸네일 거부권 신호 발송."""
    from src.pipeline_v2.hitl_gate import trigger_thumbnail_veto
    meta = job.episode_meta
    thumbnails: list[str] = meta.thumbnail_paths or []
    if not thumbnails and job.track_c_result:
        thumbnails = job.track_c_result.output.get("thumbnail_paths", [])
    if not thumbnails:
        logger.debug(f"썸네일 없음 — thumbnail_veto 게이트 스킵: {meta.episode_id}")
        return
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: trigger_thumbnail_veto(meta.channel_id, meta.episode_id, thumbnails),
    )


async def _trigger_final_preview(job: "EpisodeJob") -> None:
    """HITL Gate 3: 최종 프리뷰 신호 발송."""
    from src.pipeline_v2.hitl_gate import trigger_final_preview
    meta = job.episode_meta
    description = ""
    if job.track_a_result and job.track_a_result.output:
        description = job.track_a_result.output.get("script_text", "")[:200]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: trigger_final_preview(
            meta.channel_id,
            meta.episode_id,
            job.final_video_path or "",
            meta.title,
            description,
        ),
    )


async def _run_qc(job: "EpisodeJob") -> None:
    """QC 5 레이어를 executor에서 비동기 실행."""
    from src.pipeline_v2.qc.qc_runner import run_all_layers

    meta = job.episode_meta
    video_path = job.final_video_path or ""
    scene_images = (
        job.track_c_result.output.get("scene_images", []) if job.track_c_result else []
    )
    # Layer5 검증용 메타데이터 (제목/태그/설명)
    track_a_output = job.track_a_result.output if job.track_a_result else {}
    upload_meta = {
        "title": meta.title,
        "tags": track_a_output.get("titles", []),
        "description": track_a_output.get("script_text", "")[:200],
        "thumbnail_paths": meta.thumbnail_paths,
    }

    loop = asyncio.get_event_loop()
    try:
        qc_result = await loop.run_in_executor(
            None,
            lambda: run_all_layers(meta, video_path, scene_images, upload_meta),
        )
        passed = qc_result.get("all_passed", False)
        failed = qc_result.get("failed_layers", [])
        logger.info(f"QC 완료: {'전체 통과' if passed else f'실패 레이어={failed}'} — {meta.episode_id}")
    except Exception as e:
        logger.error(f"QC 실행 오류: {e} — {meta.episode_id}")


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
