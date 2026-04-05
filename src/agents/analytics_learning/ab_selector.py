"""A/B 테스트(authority/curiosity/benefit) CTR 기반 승자를 선택한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

_DEFAULT_WINNER = "curiosity"
_MODES = ["authority", "curiosity", "benefit"]


def select_winner(variant_performance: dict) -> str:
    """3종 제목 변형 중 CTR이 가장 높은 모드를 반환한다."""
    ctrs = {m: variant_performance.get(f"{m}_ctr", 0.0) for m in _MODES}
    best = max(ctrs, key=ctrs.get)
    if ctrs[best] == 0.0:
        return _DEFAULT_WINNER
    return best


def update_bias(bias_path: Path, winner: str, channel_id: str) -> None:
    """topic_priority_bias.json의 선호 제목 모드를 업데이트한다."""
    try:
        bias = read_json(bias_path)
    except FileNotFoundError:
        bias = {}
    bias[channel_id] = {"preferred_title_mode": winner}
    write_json(bias_path, bias)
    logger.info(f"A/B 승자 업데이트: {channel_id} → {winner}")
