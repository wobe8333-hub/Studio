"""채널별 캐릭터 일관성 점수를 집계하고 드리프트를 감지한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json

_DRIFT_THRESHOLD = 0.7


def check_character_drift(runs_dir: Path, channel_id: str) -> dict:
    """최근 10개 QA 결과에서 캐릭터 일관성 평균을 계산한다.

    Args:
        runs_dir: runs/ 루트 디렉토리
        channel_id: 채널 ID (예: "CH1")

    Returns:
        {"avg_score": float, "drift_detected": bool, "sample_count": int}
    """
    scores = []
    pattern = f"{channel_id}/*/step11/qa_result.json"
    for qa_path in sorted(runs_dir.glob(pattern))[-10:]:
        try:
            qa = read_json(qa_path)
            score = qa.get("vision_qa", {}).get("character_consistency_score", 1.0)
            scores.append(float(score))
        except Exception as e:
            logger.warning(f"QA 결과 읽기 실패: {qa_path} — {e}")

    if not scores:
        return {"avg_score": 1.0, "drift_detected": False, "sample_count": 0}

    avg = sum(scores) / len(scores)
    drift = avg < _DRIFT_THRESHOLD
    if drift:
        logger.warning(f"[{channel_id}] 캐릭터 드리프트 감지: avg={avg:.3f}")
    return {"avg_score": round(avg, 3), "drift_detected": drift, "sample_count": len(scores)}
