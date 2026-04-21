"""Analytics & Learning Agent — KPI 자동 분석 및 파이프라인 정책 반영."""
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.agents.analytics_learning.ab_selector import select_winner, update_bias
from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage, load_pending_kpis
from src.agents.analytics_learning.notifier import record_phase_promotion
from src.agents.analytics_learning.pattern_extractor import is_winning, update_winning_patterns
from src.agents.analytics_learning.phase_promoter import promote_if_eligible
from src.agents.base_agent import BaseAgent
from src.core.ssot import read_json


class AnalyticsLearningAgent(BaseAgent):
    """48h KPI 분석, 승리 패턴 추출, Phase 승격, A/B 승자 반영을 담당한다."""

    def __init__(self, root: Optional[Path] = None):
        super().__init__("AnalyticsLearning")
        # root=None 이면 BaseAgent 기본값(프로젝트 루트)을 사용한다
        if root is not None:
            self.root = root
            self.data_dir = root / "data"
            self.runs_dir = root / "runs"

    def run(self) -> dict[str, Any]:
        """모든 pending KPI를 처리하고 결과 리포트를 반환한다."""
        self._log_start()
        pending_dir = self.data_dir / "global" / "step13_pending"
        pending_kpis = load_pending_kpis(pending_dir) if pending_dir.exists() else []

        promoted_count = 0
        patterns_added = 0
        notifications_dir = self.data_dir / "global" / "notifications"

        for item in pending_kpis:
            channel_id = item.get("channel_id", "")
            kpi = item.get("kpi", item)

            stage = compute_algorithm_stage(kpi)
            policy_path = self.data_dir / "channels" / channel_id / "algorithm_policy.json"
            if policy_path.exists():
                # 승격 전 현재 단계를 읽어 알림에 기록한다
                current_policy = read_json(policy_path)
                current_stage = current_policy.get("algorithm_stage", "PRE-ENTRY")
                if promote_if_eligible(policy_path, stage):
                    promoted_count += 1
                    record_phase_promotion(notifications_dir, channel_id, current_stage, stage)

            if is_winning(kpi):
                memory_path = self.data_dir / "global" / "memory_store" / f"{channel_id}_memory.json"
                memory_path.parent.mkdir(parents=True, exist_ok=True)
                update_winning_patterns(memory_path, {**kpi, "channel_id": channel_id})
                patterns_added += 1

            variant = item.get("variant_performance", {})
            if variant:
                winner = select_winner(variant)
                bias_path = self.data_dir / "global" / "memory_store" / "topic_priority_bias.json"
                bias_path.parent.mkdir(parents=True, exist_ok=True)
                update_bias(bias_path, winner, channel_id)

            # 처리 완료된 pending 파일 삭제 (재실행 시 중복 처리 방지)
            pending_file = Path(item.get("path", ""))
            if pending_file.exists():
                pending_file.unlink()
                logger.debug(f"pending 파일 삭제: {pending_file.name}")

        report: dict[str, Any] = {
            "processed": len(pending_kpis),
            "promoted": promoted_count,
            "patterns_added": patterns_added,
            "notifications_created": promoted_count,
        }
        self._log_done(report)
        return report
