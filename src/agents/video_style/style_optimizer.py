"""CTR 피드백 기반으로 스타일 정책을 업데이트하고 Manim 안정성을 감시한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

_MANIM_ALERT_THRESHOLD = 0.5


def check_manim_fallback_rate(runs_dir: Path, channel_id: str) -> float:
    """최근 10개 실행의 평균 Manim fallback_rate를 계산한다."""
    rates = []
    pattern = f"{channel_id}/*/step08/manim_stability_report.json"
    for report_path in sorted(runs_dir.glob(pattern))[-10:]:
        try:
            report = read_json(report_path)
            rates.append(float(report.get("fallback_rate", 0.0)))
        except Exception as e:
            logger.warning(f"Manim 리포트 읽기 실패: {report_path} — {e}")

    if not rates:
        return 0.0
    avg = sum(rates) / len(rates)
    if avg > _MANIM_ALERT_THRESHOLD:
        logger.warning(f"[{channel_id}] Manim fallback_rate 경고: {avg:.1%} — HITL 필요")
    return round(avg, 3)


def update_style_policy(policy_path: Path, updates: dict) -> None:
    """style_policy_master.json에 부분 업데이트를 적용한다."""
    try:
        policy = read_json(policy_path)
    except FileNotFoundError:
        policy = {}
    policy.update(updates)
    policy["last_updated_by"] = "video_style_agent"
    write_json(policy_path, policy)
    logger.info(f"스타일 정책 업데이트: {policy_path.parent.name} — {list(updates.keys())}")
