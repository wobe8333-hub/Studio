"""KAS Sub-Agent 공통 기반 클래스."""
from pathlib import Path
from typing import Any

from loguru import logger


class BaseAgent:
    """모든 Sub-Agent의 공통 기반. root 경로와 로깅을 제공한다."""

    def __init__(self, name: str):
        self.name = name
        self.root: Path = Path(__file__).parent.parent.parent
        self.runs_dir: Path = self.root / "runs"
        self.data_dir: Path = self.root / "data"
        self.logs_dir: Path = self.root / "logs"

    def run(self) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__}.run() 미구현")

    def _log_start(self) -> None:
        logger.info(f"[{self.name}] Agent 시작")

    def _log_done(self, result: dict[str, Any]) -> None:
        logger.info(f"[{self.name}] 완료: keys={list(result.keys())}")
