"""알고리즘 단계를 단방향으로 승격한다 (강등 없음)."""
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json, write_json

STAGE_ORDER = ["PRE-ENTRY", "SEARCH-ONLY", "BROWSE-ENTRY", "ALGORITHM-ACTIVE"]


def promote_if_eligible(policy_path: Path, new_stage: str) -> bool:
    """현재 단계보다 높은 stage인 경우에만 algorithm_policy.json을 업데이트한다."""
    if new_stage not in STAGE_ORDER:
        logger.warning(f"알 수 없는 stage 값 무시: {new_stage!r}")
        return False
    policy = read_json(policy_path)
    current = policy.get("algorithm_stage", "PRE-ENTRY")

    current_idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else 0
    new_idx = STAGE_ORDER.index(new_stage) if new_stage in STAGE_ORDER else 0

    if new_idx > current_idx:
        policy["algorithm_stage"] = new_stage
        write_json(policy_path, policy)
        logger.info(f"Phase 승격: {current} → {new_stage} ({policy_path.parent.name})")
        return True

    logger.debug(f"Phase 변경 없음: {current} (요청: {new_stage})")
    return False
