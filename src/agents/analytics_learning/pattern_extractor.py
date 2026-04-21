"""승리 패턴(CTR/AVP 기준)을 추출하고 memory_store에 누적한다."""
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json, write_json


def is_winning(kpi: dict) -> bool:
    """CTR >= 6.0% AND AVP >= 50.0% 이면 승리 패턴으로 분류한다."""
    return kpi.get("ctr", 0.0) >= 6.0 and kpi.get("avg_view_percentage", 0.0) >= 50.0


def update_winning_patterns(memory_path: Path, run_data: dict) -> None:
    """winning_animation_patterns에 새 패턴을 추가하고 최근 50건만 유지한다."""
    try:
        memory = read_json(memory_path)
    except FileNotFoundError:
        memory = {"winning_animation_patterns": []}

    patterns = memory.get("winning_animation_patterns", [])
    patterns.append({
        "run_id": run_data.get("run_id"),
        "channel_id": run_data.get("channel_id"),
        "animation_style": run_data.get("animation_style"),
        "ctr": run_data.get("ctr"),
        "avp": run_data.get("avg_view_percentage"),
    })
    memory["winning_animation_patterns"] = patterns[-50:]
    write_json(memory_path, memory)
    logger.info(f"winning_patterns 업데이트: {len(memory['winning_animation_patterns'])}건")
