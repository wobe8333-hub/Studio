"""Video Style & Character Agent — 채널별 시각 아이덴티티 유지 및 스타일 최적화."""
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.agents.video_style.character_monitor import check_character_drift
from src.agents.video_style.style_optimizer import check_manim_fallback_rate
from src.core.ssot import read_json


class VideoStyleAgent(BaseAgent):
    """캐릭터 일관성 드리프트 감지, Manim fallback 모니터링, 스타일 정책 최적화를 담당한다."""

    def __init__(self, root: Optional[Path] = None):
        super().__init__("VideoStyle")
        # root=None 이면 BaseAgent 기본값(프로젝트 루트)을 사용한다
        if root is not None:
            self.root = root
            self.runs_dir = root / "runs"
            self.data_dir = root / "data"

    def _get_active_channels(self) -> list:
        """channel_registry.json에서 활성 채널 ID 목록을 반환한다."""
        registry_path = self.data_dir / "global" / "channel_registry.json"
        try:
            registry = read_json(registry_path)
            if isinstance(registry, list):
                return [ch["id"] for ch in registry if ch.get("status") == "active"]
            return []
        except Exception:
            return ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]

    def run(self) -> dict[str, Any]:
        """모든 활성 채널의 스타일 상태를 점검하고 리포트를 반환한다."""
        self._log_start()
        channels = self._get_active_channels()
        channel_reports: dict[str, Any] = {}

        for ch_id in channels:
            drift_info = check_character_drift(self.runs_dir, ch_id)
            manim_rate = check_manim_fallback_rate(self.runs_dir, ch_id)
            channel_reports[ch_id] = {
                "drift_detected": drift_info["drift_detected"],
                "avg_score": drift_info["avg_score"],
                "manim_fallback_rate": manim_rate,
            }

        report: dict[str, Any] = {"channels": channel_reports}
        self._log_done(report)
        return report
