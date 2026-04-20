"""유지율 데이터 수집기 (Plan C-4 B8).

YouTube Analytics에서 평균 시청 지속시간(average_view_duration)을
수집해 data/global/retention/{channel_id}.jsonl에 누적 기록한다.

이 데이터는 3개월 이상 축적 후 유지율 예측 모델(B8 전체 구현)에 사용된다.
지금은 데이터 수집 훅만 심어두는 단계다.

사용법:
    from src.step13.retention_collector import collect_retention

    collect_retention("CH1", "abc123", kpi_data)
"""
import json
import os
from datetime import datetime
from pathlib import Path

from loguru import logger

_RETENTION_DIR = Path(os.getenv("KAS_ROOT", ".")) / "data" / "global" / "retention"


def collect_retention(channel_id: str, video_id: str, kpi: dict) -> None:
    """KPI에서 유지율 지표를 추출해 채널별 JSONL 파일에 누적 기록한다.

    Args:
        channel_id: 채널 ID (예: "CH1")
        video_id: YouTube 영상 ID
        kpi: Step13에서 수집한 KPI 딕셔너리
              avg_view_percentage, average_view_duration, video_duration 등

    누적 파일: data/global/retention/{channel_id}.jsonl
    """
    avg_duration = kpi.get("average_view_duration", 0) or 0
    avg_pct = kpi.get("avg_view_percentage", 0) or 0
    total_duration = kpi.get("video_duration", 0) or 0

    # 데이터가 없으면 기록 불필요
    if avg_duration == 0 and avg_pct == 0:
        return

    # retention_rate: 평균 시청 지속시간 / 영상 총 길이
    if total_duration > 0:
        retention_rate = avg_duration / total_duration
    elif avg_pct > 0:
        retention_rate = avg_pct / 100.0  # avg_view_percentage(%) → ratio
    else:
        retention_rate = 0.0

    record = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel_id": channel_id,
        "video_id": video_id,
        "avg_duration_sec": avg_duration,
        "total_duration_sec": total_duration,
        "avg_view_pct": avg_pct,
        "retention_rate": round(retention_rate, 4),
        "views": kpi.get("views", 0),
        "ctr": kpi.get("ctr", 0.0),
    }

    _RETENTION_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _RETENTION_DIR / f"{channel_id}.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(
        f"[RETENTION] {channel_id}/{video_id} 유지율 {retention_rate:.1%} 기록 → {out_path.name}"
    )
