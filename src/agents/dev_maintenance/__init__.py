"""Dev & Maintenance Agent — 파이프라인 실패 자동 진단 및 시스템 건강 점검."""
from pathlib import Path
from typing import Any, Optional
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.dev_maintenance.log_monitor import find_failed_runs
from src.agents.dev_maintenance.health_checker import run_tests
from src.agents.dev_maintenance.schema_validator import find_missing_types


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

        failed_runs = find_failed_runs(self.runs_dir)
        if failed_runs:
            logger.warning(f"[{self.name}] FAILED 실행 {len(failed_runs)}건 감지")

        health = run_tests(self.root)
        if not health["passed"]:
            logger.error(f"[{self.name}] pytest 실패 — 출력:\n{health['output'][:500]}")

        sql_path = self.root / "scripts" / "supabase_schema.sql"
        types_path = self.root / "web" / "lib" / "types.ts"
        schema_missing: list = []
        if sql_path.exists() and types_path.exists():
            schema_missing = find_missing_types(sql_path, types_path)
            if schema_missing:
                logger.warning(f"[{self.name}] types.ts 누락 테이블: {schema_missing}")

        report: dict[str, Any] = {
            "failed_runs": failed_runs,
            "health": health,
            "schema_missing": schema_missing,
        }
        self._log_done(report)
        return report
