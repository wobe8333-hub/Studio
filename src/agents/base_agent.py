"""KAS Sub-Agent 공통 기반 클래스."""
from pathlib import Path
from loguru import logger


class BaseAgent:
    """모든 Sub-Agent의 공통 기반. root 경로와 로깅을 제공한다."""

    def __init__(self, name: str):
        self.name = name
        self.root = Path(__file__).parent.parent.parent
        self.runs_dir = self.root / "runs"
        self.data_dir = self.root / "data"
        self.logs_dir = self.root / "logs"

    def run(self) -> dict:
        raise NotImplementedError(f"{self.name}.run() 미구현")

    def _log_start(self) -> None:
        logger.info(f"[{self.name}] Agent 시작")

    def _log_done(self, result: dict) -> None:
        logger.info(f"[{self.name}] 완료: {result}")
