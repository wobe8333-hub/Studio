"""48h KPI 데이터를 분석하고 알고리즘 단계를 판정한다."""
import time
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json


def load_pending_kpis(pending_dir: Path) -> list:
    """step13_pending/ 디렉토리에서 48시간 경과 항목을 로드한다."""
    now = time.time()
    pending = []
    for f in pending_dir.glob("*.json"):
        try:
            data = read_json(f)
            created_ts = data.get("created_at_ts", 0)
            if now - created_ts >= 48 * 3600:
                pending.append({"path": str(f), **data})
        except Exception as e:
            logger.warning(f"pending KPI 읽기 실패: {f} — {e}")
    return pending


def compute_algorithm_stage(kpi: dict) -> str:
    """KPI 수치로 YouTube 알고리즘 진입 단계를 판정한다.

    판정 기준 (우선순위 순):
      ALGORITHM-ACTIVE: views >= 100,000 OR ctr >= 8.0
      BROWSE-ENTRY:     ctr >= 5.5 AND avp >= 45.0 AND browse_feed_pct >= 20.0
      SEARCH-ONLY:      ctr >= 4.0
      PRE-ENTRY:        그 외
    """
    views = kpi.get("views", 0)
    ctr = kpi.get("ctr", 0.0)
    avp = kpi.get("avg_view_percentage", 0.0)
    browse_pct = kpi.get("browse_feed_percentage", 0.0)

    if views >= 100_000 or ctr >= 8.0:
        return "ALGORITHM-ACTIVE"
    if ctr >= 5.5 and avp >= 45.0 and browse_pct >= 20.0:
        return "BROWSE-ENTRY"
    if ctr >= 4.0:
        return "SEARCH-ONLY"
    return "PRE-ENTRY"
