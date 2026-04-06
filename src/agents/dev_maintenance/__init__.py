"""Dev & Maintenance Agent — 파이프라인 실패 자동 진단 및 시스템 건강 점검."""
from pathlib import Path
from typing import Any, Optional
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.dev_maintenance.log_monitor import find_failed_runs
from src.agents.dev_maintenance.health_checker import run_tests
from src.agents.dev_maintenance.schema_validator import find_missing_types
from src.agents.dev_maintenance.hitl_signal import emit_hitl_signal, FAILED_RUNS_THRESHOLD


class DevMaintenanceAgent(BaseAgent):
    """파이프라인 실패 감지, 테스트 실행, 스키마 동기화 검증을 담당한다."""

    def __init__(self, root: Optional[Path] = None):
        super().__init__("DevMaintenance")
        # root=None 이면 BaseAgent 기본값(프로젝트 루트)을 사용한다
        if root is not None:
            self.root = root
            self.runs_dir = root / "runs"
            self.data_dir = root / "data"

    def run(self) -> dict[str, Any]:
        """Agent 전체 점검을 실행하고 결과 리포트를 반환한다.

        Returns:
            {
                "failed_runs": list,     # FAILED 상태 실행 목록
                "health": dict,          # pytest 결과
                "schema_missing": list,  # types.ts 누락 테이블
            }
        """
        self._log_start()
        signals_dir = self.data_dir / "global" / "notifications"
        hitl_signals: list[str] = []

        # ── 파이프라인 실패 감지 ──────────────────────────────────────
        failed_runs = find_failed_runs(self.runs_dir)
        if len(failed_runs) >= FAILED_RUNS_THRESHOLD:
            logger.warning(f"[{self.name}] FAILED 실행 {len(failed_runs)}건 감지")
            emit_hitl_signal(signals_dir, "pipeline_failure", {
                "count": len(failed_runs),
                "runs": [r.get("run_id", "") for r in failed_runs[:5]],
            })
            hitl_signals.append("pipeline_failure")

        # ── 테스트 건강 점검 ─────────────────────────────────────────
        health = run_tests(self.root)
        if not health["passed"]:
            logger.error(f"[{self.name}] pytest 실패 — 출력:\n{health['output'][:500]}")
            emit_hitl_signal(signals_dir, "pytest_failure", {
                "output_snippet": health["output"][:300],
            })
            hitl_signals.append("pytest_failure")

        # ── 스키마 동기화 검증 (UiUxAgent 위임 알림) ─────────────────
        sql_path = self.root / "scripts" / "supabase_schema.sql"
        types_path = self.root / "web" / "lib" / "types.ts"
        schema_missing: list = []
        if sql_path.exists() and types_path.exists():
            schema_missing = find_missing_types(sql_path, types_path)
            if schema_missing:
                # 스키마 불일치는 UiUxAgent가 자동 처리 — HITL 불필요
                logger.info(f"[{self.name}] types.ts 누락 테이블 {schema_missing} → UiUxAgent 위임")

        report: dict[str, Any] = {
            "failed_runs": failed_runs,
            "health": health,
            "schema_missing": schema_missing,
            "hitl_signals": hitl_signals,
        }
        self._log_done(report)
        return report
