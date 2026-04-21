"""QC 5 레이어 통합 실행기 — 재생성 루프 + HITL 알림 (T30)"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.core.ssot import read_json, write_json
from src.pipeline_v2.episode_schema import EpisodeMeta, save_episode
from src.pipeline_v2.qc.layer1_character import run_layer1
from src.pipeline_v2.qc.layer2_audio import run_layer2
from src.pipeline_v2.qc.layer3_sync import run_layer3
from src.pipeline_v2.qc.layer4_video import run_layer4
from src.pipeline_v2.qc.layer5_meta import run_layer5

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

MAX_RETRY = 3
HITL_SIGNALS_PATH = Path("data/global/notifications/hitl_signals.json")


def _send_hitl_alert(meta: EpisodeMeta, layer: int, issues: list[str]) -> None:
    """QC 실패 시 HITL 웹 대시보드 알림 기록."""
    HITL_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if HITL_SIGNALS_PATH.exists():
        try:
            existing = read_json(HITL_SIGNALS_PATH)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    signal = {
        "type": "qc_failure",
        "episode_id": meta.episode_id,
        "channel_id": meta.channel_id,
        "layer": layer,
        "issues": issues,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    existing.append(signal)
    write_json(HITL_SIGNALS_PATH, existing[-100:])
    logger.warning(f"HITL 알림 등록: Layer{layer} 실패 — {meta.episode_id}")


async def _retry_layer1(
    meta: EpisodeMeta,
    scene_images: list[str],
    job: "EpisodeJob",
    attempt: int,
) -> dict:
    """Layer1 실패 시 Track C 재실행으로 이미지 재생성."""
    logger.info(f"Layer1 재생성 시도 {attempt}/{MAX_RETRY}: {meta.episode_id}")
    from src.pipeline_v2.dag.track_c_visual import run_track_c
    result = await run_track_c(job)
    new_images = result.get("scene_images", scene_images)
    return run_layer1(meta, new_images)


def run_all_layers(
    meta: EpisodeMeta,
    video_path: str,
    scene_images: list[str],
    upload_meta: dict,
    subtitle_path: str | None = None,
) -> dict:
    """QC 5 레이어 순차 실행 (Layer1 재생성 루프 포함).

    Returns: {
        "all_passed": bool,
        "layers": {1: {...}, 2: {...}, 3: {...}, 4: {...}, 5: {...}},
        "retry_count": int,
    }
    """
    results: dict[int, dict] = {}

    layer1_result = run_layer1(meta, scene_images)
    retry_count = 0

    if not layer1_result["passed"]:
        for attempt in range(1, MAX_RETRY + 1):
            retry_count += 1
            layer1_result = run_layer1(meta, scene_images)
            if layer1_result["passed"]:
                logger.info(f"Layer1 재생성 성공 (attempt {attempt})")
                break
        else:
            _send_hitl_alert(meta, 1, layer1_result.get("results", []))

    results[1] = layer1_result

    results[2] = run_layer2(meta, video_path)
    if not results[2]["passed"]:
        _send_hitl_alert(meta, 2, results[2].get("issues", []))

    results[3] = run_layer3(meta, video_path, subtitle_path)
    if not results[3]["passed"]:
        _send_hitl_alert(meta, 3, results[3].get("issues", []))

    results[4] = run_layer4(meta, video_path)
    if not results[4]["passed"]:
        _send_hitl_alert(meta, 4, results[4].get("issues", []))

    results[5] = run_layer5(meta, upload_meta)
    if not results[5]["passed"]:
        _send_hitl_alert(meta, 5, results[5].get("issues", []))

    all_passed = all(r["passed"] for r in results.values())
    meta.features.qc_pass = all_passed
    save_episode(meta)

    failed_layers = [k for k, v in results.items() if not v["passed"]]
    if failed_layers:
        logger.warning(f"QC 실패 레이어: {failed_layers} — {meta.episode_id}")
    else:
        logger.info(f"QC 전체 통과: {meta.episode_id}")

    return {
        "all_passed": all_passed,
        "layers": results,
        "retry_count": retry_count,
        "failed_layers": failed_layers,
    }
