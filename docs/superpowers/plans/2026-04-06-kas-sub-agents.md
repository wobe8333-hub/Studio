# KAS Sub-Agent 시스템 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KAS 파이프라인의 수동 고통점(실패 진단, KPI 학습, 대시보드 정비, 스타일 최적화)을 자동화하는 4개 Sub-Agent를 구현한다.

**Architecture:** 기존 18-Step 파이프라인은 수정하지 않는다. 각 Agent는 파이프라인이 생성한 JSON 파일(SSOT)을 읽고 정책 파일만 업데이트하는 비침습적 레이어다. 모든 파일 I/O는 `src/core/ssot.py`의 `read_json/write_json`을 통한다.

**Tech Stack:** Python 3.8+, loguru, pathlib, subprocess, pytest, Playwright MCP (UI/UX Agent)

---

## 파일 구조

```
신규 생성:
src/agents/
  __init__.py                          ← 패키지 init
  base_agent.py                        ← 공통 기반 클래스
  dev_maintenance/
    __init__.py                        ← Agent 진입점 (run() 함수)
    log_monitor.py                     ← FAILED 실행 감지
    health_checker.py                  ← preflight + pytest 실행
    schema_validator.py                ← SQL ↔ types.ts 불일치 감지
  analytics_learning/
    __init__.py                        ← Agent 진입점
    kpi_analyzer.py                    ← 48h KPI 수집 및 단계 판정
    pattern_extractor.py               ← 승리 패턴 추출 (CTR/AVP)
    ab_selector.py                     ← A/B 테스트 승자 선택
    phase_promoter.py                  ← 알고리즘 Phase 단방향 승격
  ui_ux/
    __init__.py                        ← Agent 진입점
    schema_watcher.py                  ← 스키마 변경 해시 감지
    type_syncer.py                     ← SQL 컬럼 → TypeScript 타입 변환
  video_style/
    __init__.py                        ← Agent 진입점 (Phase 2)
    character_monitor.py               ← 캐릭터 일관성 점수 집계
    style_optimizer.py                 ← style_policy 업데이트 + Manim fallback 감지

tests/test_agents/
  __init__.py
  test_dev_maintenance.py
  test_analytics_learning.py
  test_ui_ux.py
  test_video_style.py                  ← Phase 2
```

---

## Phase 1

---

### Task 1: 기반 구조 생성

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/base_agent.py`
- Create: `tests/test_agents/__init__.py`

- [ ] **Step 1: 디렉토리 및 빈 파일 생성**

```bash
mkdir -p src/agents/dev_maintenance
mkdir -p src/agents/analytics_learning
mkdir -p src/agents/ui_ux
mkdir -p src/agents/video_style
mkdir -p tests/test_agents
touch src/agents/__init__.py
touch src/agents/dev_maintenance/__init__.py
touch src/agents/analytics_learning/__init__.py
touch src/agents/ui_ux/__init__.py
touch src/agents/video_style/__init__.py
touch tests/test_agents/__init__.py
```

- [ ] **Step 2: base_agent.py 작성**

`src/agents/base_agent.py`:
```python
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
```

- [ ] **Step 3: base_agent 임포트 검증**

```bash
python -c "from src.agents.base_agent import BaseAgent; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/agents/ tests/test_agents/__init__.py
git commit -m "feat: Sub-Agent 기반 구조 생성"
```

---

### Task 2: Dev & Maintenance — 실패 감지 (log_monitor)

**Files:**
- Create: `src/agents/dev_maintenance/log_monitor.py`
- Create: `tests/test_agents/test_dev_maintenance.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_agents/test_dev_maintenance.py`:
```python
"""Dev & Maintenance Agent 테스트."""
import json
from pathlib import Path
import pytest


def _write_manifest(path: Path, run_state: str) -> None:
    """테스트용 manifest.json을 utf-8-sig 인코딩으로 생성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": path.parent.name,
        "channel_id": "CH1",
        "run_state": run_state,
        "error": "테스트 에러" if run_state == "FAILED" else ""
    }
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8-sig")


def test_find_failed_runs_returns_only_failed(tmp_path):
    """FAILED 상태 manifest만 반환하고 COMPLETED는 무시한다."""
    _write_manifest(tmp_path / "CH1" / "run_001" / "manifest.json", "FAILED")
    _write_manifest(tmp_path / "CH1" / "run_002" / "manifest.json", "COMPLETED")

    from src.agents.dev_maintenance.log_monitor import find_failed_runs
    result = find_failed_runs(tmp_path)

    assert len(result) == 1
    assert result[0]["run_id"] == "run_001"
    assert result[0]["run_state"] == "FAILED"


def test_find_failed_runs_empty_when_no_runs(tmp_path):
    """runs 디렉토리가 비어있으면 빈 리스트를 반환한다."""
    from src.agents.dev_maintenance.log_monitor import find_failed_runs
    result = find_failed_runs(tmp_path)
    assert result == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py -v
```
Expected: `ImportError` 또는 `ModuleNotFoundError`

- [ ] **Step 3: log_monitor.py 구현**

`src/agents/dev_maintenance/log_monitor.py`:
```python
"""FAILED 상태의 파이프라인 실행을 감지한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json


def find_failed_runs(runs_dir: Path) -> list:
    """runs/ 하위 모든 manifest.json을 스캔해 FAILED 항목을 반환한다.

    Args:
        runs_dir: runs/ 루트 디렉토리 경로

    Returns:
        FAILED 상태 manifest 딕셔너리 리스트.
        각 항목: {run_id, channel_id, run_state, error, manifest_path}
    """
    failed = []
    for manifest_path in runs_dir.glob("*/*/manifest.json"):
        try:
            manifest = read_json(manifest_path)
            if manifest.get("run_state") == "FAILED":
                failed.append({
                    "run_id": manifest.get("run_id", manifest_path.parent.name),
                    "channel_id": manifest.get("channel_id", "UNKNOWN"),
                    "run_state": "FAILED",
                    "error": manifest.get("error", ""),
                    "manifest_path": str(manifest_path),
                })
        except Exception as e:
            logger.warning(f"manifest 읽기 실패: {manifest_path} — {e}")
    return failed
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py -v
```
Expected: `PASSED` 2개

- [ ] **Step 5: Commit**

```bash
git add src/agents/dev_maintenance/log_monitor.py tests/test_agents/test_dev_maintenance.py
git commit -m "feat: Dev Agent — FAILED 실행 감지 (log_monitor)"
```

---

### Task 3: Dev & Maintenance — Health Check

**Files:**
- Modify: `src/agents/dev_maintenance/health_checker.py` (신규)
- Modify: `tests/test_agents/test_dev_maintenance.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가**

`tests/test_agents/test_dev_maintenance.py` 하단에 추가:
```python
def test_run_tests_returns_passed_on_success(tmp_path, monkeypatch):
    """pytest가 0으로 종료되면 passed=True를 반환한다."""
    import subprocess

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "2 passed", "stderr": ""})()
    )
    from src.agents.dev_maintenance.health_checker import run_tests
    result = run_tests(tmp_path)
    assert result["passed"] is True
    assert "passed" in result["output"]


def test_run_tests_returns_failed_on_error(tmp_path, monkeypatch):
    """pytest가 1로 종료되면 passed=False를 반환한다."""
    import subprocess

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "1 failed"})()
    )
    from src.agents.dev_maintenance.health_checker import run_tests
    result = run_tests(tmp_path)
    assert result["passed"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py::test_run_tests_returns_passed_on_success -v
```
Expected: `ImportError`

- [ ] **Step 3: health_checker.py 구현**

`src/agents/dev_maintenance/health_checker.py`:
```python
"""preflight 검사 및 pytest 실행으로 시스템 건강 상태를 확인한다."""
import subprocess
from pathlib import Path
from loguru import logger


def run_preflight(root: Path) -> dict:
    """scripts/preflight_check.py를 실행하고 결과를 반환한다.

    Returns:
        {"passed": bool, "stdout": str, "stderr": str}
    """
    try:
        result = subprocess.run(
            ["python", "scripts/preflight_check.py"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        logger.error("preflight_check.py 타임아웃 (60초)")
        return {"passed": False, "stdout": "", "stderr": "TIMEOUT"}


def run_tests(root: Path) -> dict:
    """pytest tests/ -q --tb=short를 실행하고 결과를 반환한다.

    Returns:
        {"passed": bool, "output": str}
    """
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-q", "--tb=short"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "passed": result.returncode == 0,
            "output": result.stdout + result.stderr,
        }
    except subprocess.TimeoutExpired:
        logger.error("pytest 타임아웃 (300초)")
        return {"passed": False, "output": "TIMEOUT"}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py -v
```
Expected: `PASSED` 4개

- [ ] **Step 5: Commit**

```bash
git add src/agents/dev_maintenance/health_checker.py tests/test_agents/test_dev_maintenance.py
git commit -m "feat: Dev Agent — Health Check (preflight + pytest)"
```

---

### Task 4: Dev & Maintenance — 스키마 검증 (schema_validator)

**Files:**
- Create: `src/agents/dev_maintenance/schema_validator.py`
- Modify: `tests/test_agents/test_dev_maintenance.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가**

`tests/test_agents/test_dev_maintenance.py` 하단에 추가:
```python
def test_find_missing_types_detects_new_table(tmp_path):
    """SQL에 추가된 테이블이 types.ts에 없으면 반환한다."""
    sql = tmp_path / "schema.sql"
    sql.write_text(
        "CREATE TABLE channels (id TEXT);\nCREATE TABLE new_table (col INT);",
        encoding="utf-8"
    )
    types_ts = tmp_path / "types.ts"
    types_ts.write_text("export type Database = { channels: { id: string } }", encoding="utf-8")

    from src.agents.dev_maintenance.schema_validator import find_missing_types
    missing = find_missing_types(sql, types_ts)

    assert "new_table" in missing
    assert "channels" not in missing


def test_find_missing_types_returns_empty_when_in_sync(tmp_path):
    """SQL과 types.ts가 일치하면 빈 리스트를 반환한다."""
    sql = tmp_path / "schema.sql"
    sql.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    types_ts = tmp_path / "types.ts"
    types_ts.write_text("export type Database = { channels: { id: string } }", encoding="utf-8")

    from src.agents.dev_maintenance.schema_validator import find_missing_types
    assert find_missing_types(sql, types_ts) == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py::test_find_missing_types_detects_new_table -v
```
Expected: `ImportError`

- [ ] **Step 3: schema_validator.py 구현**

`src/agents/dev_maintenance/schema_validator.py`:
```python
"""supabase_schema.sql ↔ web/lib/types.ts 불일치를 감지한다."""
import re
from pathlib import Path


def extract_table_names_from_sql(sql_path: Path) -> set:
    """SQL 파일에서 CREATE TABLE 문의 테이블명을 추출한다."""
    content = sql_path.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", content, re.IGNORECASE))


def extract_identifiers_from_types(types_path: Path) -> set:
    """types.ts에서 최상위 키 식별자를 추출한다."""
    content = types_path.read_text(encoding="utf-8")
    # "identifier: {" 패턴 추출 (테이블명 대응)
    return set(re.findall(r"(\w+)\s*:", content))


def find_missing_types(sql_path: Path, types_path: Path) -> list:
    """SQL에는 있지만 types.ts에 정의가 없는 테이블 이름을 반환한다.

    Returns:
        정렬된 테이블명 리스트. 동기화 완료 시 빈 리스트.
    """
    sql_tables = extract_table_names_from_sql(sql_path)
    ts_identifiers = extract_identifiers_from_types(types_path)
    return sorted(sql_tables - ts_identifiers)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py -v
```
Expected: `PASSED` 6개

- [ ] **Step 5: Commit**

```bash
git add src/agents/dev_maintenance/schema_validator.py tests/test_agents/test_dev_maintenance.py
git commit -m "feat: Dev Agent — 스키마 불일치 감지 (schema_validator)"
```

---

### Task 5: Dev & Maintenance — Agent 진입점

**Files:**
- Modify: `src/agents/dev_maintenance/__init__.py`
- Modify: `tests/test_agents/test_dev_maintenance.py` (통합 테스트 추가)

- [ ] **Step 1: 통합 테스트 추가**

`tests/test_agents/test_dev_maintenance.py` 하단에 추가:
```python
def test_dev_agent_run_returns_report(tmp_path, monkeypatch):
    """run()이 실패 수, health 결과, 스키마 불일치 수를 포함한 리포트를 반환한다."""
    import subprocess

    # FAILED 실행 1개 생성 — DevMaintenanceAgent.runs_dir = root/"runs" 이므로 runs/ 하위에 생성
    _write_manifest(tmp_path / "runs" / "CH1" / "run_001" / "manifest.json", "FAILED")

    # subprocess.run mock (pytest 성공)
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()
    )

    # schema/types 파일 생성 (동기화 상태)
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    types_path.write_text("channels: { id: string }", encoding="utf-8")

    from src.agents.dev_maintenance import DevMaintenanceAgent
    agent = DevMaintenanceAgent(root=tmp_path)
    report = agent.run()

    assert "failed_runs" in report
    assert len(report["failed_runs"]) == 1
    assert "health" in report
    assert "schema_missing" in report
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py::test_dev_agent_run_returns_report -v
```
Expected: `ImportError`

- [ ] **Step 3: __init__.py 구현**

`src/agents/dev_maintenance/__init__.py`:
```python
"""Dev & Maintenance Agent — 파이프라인 실패 자동 진단 및 시스템 건강 점검."""
from pathlib import Path
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.dev_maintenance.log_monitor import find_failed_runs
from src.agents.dev_maintenance.health_checker import run_tests
from src.agents.dev_maintenance.schema_validator import find_missing_types


class DevMaintenanceAgent(BaseAgent):
    """파이프라인 실패 감지, 테스트 실행, 스키마 동기화 검증을 담당한다."""

    def __init__(self, root: Path = None):
        super().__init__("DevMaintenance")
        if root:
            self.root = root
            self.runs_dir = root / "runs"

    def run(self) -> dict:
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
        schema_missing = []
        if sql_path.exists() and types_path.exists():
            schema_missing = find_missing_types(sql_path, types_path)
            if schema_missing:
                logger.warning(f"[{self.name}] types.ts 누락 테이블: {schema_missing}")

        report = {
            "failed_runs": failed_runs,
            "health": health,
            "schema_missing": schema_missing,
        }
        self._log_done({"failed": len(failed_runs), "tests_ok": health["passed"]})
        return report
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_dev_maintenance.py -v
```
Expected: `PASSED` 7개

- [ ] **Step 5: Commit**

```bash
git add src/agents/dev_maintenance/__init__.py tests/test_agents/test_dev_maintenance.py
git commit -m "feat: Dev & Maintenance Agent 진입점 완성"
```

---

### Task 6: Analytics & Learning — KPI 분석 (kpi_analyzer)

**Files:**
- Create: `src/agents/analytics_learning/kpi_analyzer.py`
- Create: `tests/test_agents/test_analytics_learning.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_agents/test_analytics_learning.py`:
```python
"""Analytics & Learning Agent 테스트."""
import pytest


def test_compute_algorithm_stage_algorithm_active():
    """views >= 100,000 이면 ALGORITHM-ACTIVE를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 150_000, "ctr": 4.0, "avg_view_percentage": 40.0, "browse_feed_percentage": 10.0}
    assert compute_algorithm_stage(kpi) == "ALGORITHM-ACTIVE"


def test_compute_algorithm_stage_browse_entry():
    """CTR>=5.5, AVP>=45, browse>=20 이면 BROWSE-ENTRY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 5_000, "ctr": 5.8, "avg_view_percentage": 47.0, "browse_feed_percentage": 22.0}
    assert compute_algorithm_stage(kpi) == "BROWSE-ENTRY"


def test_compute_algorithm_stage_search_only():
    """CTR 4~5.5 이면 SEARCH-ONLY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 1_000, "ctr": 4.5, "avg_view_percentage": 38.0, "browse_feed_percentage": 5.0}
    assert compute_algorithm_stage(kpi) == "SEARCH-ONLY"


def test_compute_algorithm_stage_pre_entry():
    """CTR < 4 이면 PRE-ENTRY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 200, "ctr": 2.1, "avg_view_percentage": 30.0, "browse_feed_percentage": 0.0}
    assert compute_algorithm_stage(kpi) == "PRE-ENTRY"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py -v
```
Expected: `ImportError`

- [ ] **Step 3: kpi_analyzer.py 구현**

`src/agents/analytics_learning/kpi_analyzer.py`:
```python
"""48h KPI 데이터를 분석하고 알고리즘 단계를 판정한다."""
import time
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json


def load_pending_kpis(pending_dir: Path) -> list:
    """step13_pending/ 디렉토리에서 48시간 경과 항목을 로드한다.

    Returns:
        {"path": str, ...kpi 데이터} 딕셔너리 리스트
    """
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

    Returns:
        "ALGORITHM-ACTIVE" | "BROWSE-ENTRY" | "SEARCH-ONLY" | "PRE-ENTRY"
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py -v
```
Expected: `PASSED` 4개

- [ ] **Step 5: Commit**

```bash
git add src/agents/analytics_learning/kpi_analyzer.py tests/test_agents/test_analytics_learning.py
git commit -m "feat: Analytics Agent — KPI 분석 및 알고리즘 단계 판정"
```

---

### Task 7: Analytics & Learning — 승리 패턴 추출 및 Phase 승격

**Files:**
- Create: `src/agents/analytics_learning/pattern_extractor.py`
- Create: `src/agents/analytics_learning/phase_promoter.py`
- Modify: `tests/test_agents/test_analytics_learning.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가**

`tests/test_agents/test_analytics_learning.py` 하단에 추가:
```python
def test_is_winning_true_when_both_criteria_met():
    """CTR >= 6.0 AND AVP >= 50.0 이면 True를 반환한다."""
    from src.agents.analytics_learning.pattern_extractor import is_winning
    assert is_winning({"ctr": 6.5, "avg_view_percentage": 52.0}) is True


def test_is_winning_false_when_only_one_criterion_met():
    """CTR 또는 AVP 중 하나만 충족하면 False를 반환한다."""
    from src.agents.analytics_learning.pattern_extractor import is_winning
    assert is_winning({"ctr": 7.0, "avg_view_percentage": 45.0}) is False
    assert is_winning({"ctr": 5.0, "avg_view_percentage": 55.0}) is False


def test_update_winning_patterns_keeps_last_50(tmp_path):
    """winning_animation_patterns는 최근 50건만 유지한다."""
    import json
    memory_path = tmp_path / "memory.json"
    # 기존 50건 생성
    existing = [{"run_id": f"run_{i:03d}", "ctr": 6.0, "avp": 51.0} for i in range(50)]
    memory_path.write_text(
        json.dumps({"winning_animation_patterns": existing}, ensure_ascii=True),
        encoding="utf-8-sig"
    )

    from src.agents.analytics_learning.pattern_extractor import update_winning_patterns
    update_winning_patterns(memory_path, {
        "run_id": "run_new", "channel_id": "CH1",
        "animation_style": "comparison", "ctr": 7.0, "avp": 55.0
    })

    from src.core.ssot import read_json
    updated = read_json(memory_path)
    patterns = updated["winning_animation_patterns"]
    assert len(patterns) == 50
    assert patterns[-1]["run_id"] == "run_new"


def test_promote_if_eligible_advances_stage(tmp_path):
    """현재 단계보다 높은 stage를 받으면 승격한다."""
    import json
    policy_path = tmp_path / "algorithm_policy.json"
    policy_path.write_text(
        json.dumps({"algorithm_stage": "PRE-ENTRY"}, ensure_ascii=True),
        encoding="utf-8-sig"
    )

    from src.agents.analytics_learning.phase_promoter import promote_if_eligible
    promoted = promote_if_eligible(policy_path, "SEARCH-ONLY")

    assert promoted is True
    from src.core.ssot import read_json
    assert read_json(policy_path)["algorithm_stage"] == "SEARCH-ONLY"


def test_promote_if_eligible_blocks_demotion(tmp_path):
    """현재 단계보다 낮은 stage를 받으면 변경하지 않는다."""
    import json
    policy_path = tmp_path / "algorithm_policy.json"
    policy_path.write_text(
        json.dumps({"algorithm_stage": "BROWSE-ENTRY"}, ensure_ascii=True),
        encoding="utf-8-sig"
    )

    from src.agents.analytics_learning.phase_promoter import promote_if_eligible
    promoted = promote_if_eligible(policy_path, "SEARCH-ONLY")

    assert promoted is False
    from src.core.ssot import read_json
    assert read_json(policy_path)["algorithm_stage"] == "BROWSE-ENTRY"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py -v
```
Expected: `ImportError` 다수

- [ ] **Step 3: pattern_extractor.py 구현**

`src/agents/analytics_learning/pattern_extractor.py`:
```python
"""승리 패턴(CTR/AVP 기준)을 추출하고 memory_store에 누적한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json


def is_winning(kpi: dict) -> bool:
    """CTR >= 6.0% AND AVP >= 50.0% 이면 승리 패턴으로 분류한다."""
    return kpi.get("ctr", 0.0) >= 6.0 and kpi.get("avg_view_percentage", 0.0) >= 50.0


def update_winning_patterns(memory_path: Path, run_data: dict) -> None:
    """winning_animation_patterns에 새 패턴을 추가하고 최근 50건만 유지한다.

    Args:
        memory_path: memory_store JSON 파일 경로
        run_data: {run_id, channel_id, animation_style, ctr, avp} 딕셔너리
    """
    try:
        memory = read_json(memory_path)
    except FileNotFoundError:
        memory = {"winning_animation_patterns": []}

    patterns = memory.get("winning_animation_patterns", [])
    patterns.append({
        "run_id": run_data.get("run_id"),
        "channel_id": run_data.get("channel_id"),
        "animation_style": run_data.get("animation_style"),
        "ctr": run_data.get("ctr"),
        "avp": run_data.get("avp"),
    })
    memory["winning_animation_patterns"] = patterns[-50:]
    write_json(memory_path, memory)
    logger.info(f"winning_patterns 업데이트: {len(memory['winning_animation_patterns'])}건")
```

- [ ] **Step 4: phase_promoter.py 구현**

`src/agents/analytics_learning/phase_promoter.py`:
```python
"""알고리즘 단계를 단방향으로 승격한다 (강등 없음)."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

STAGE_ORDER = ["PRE-ENTRY", "SEARCH-ONLY", "BROWSE-ENTRY", "ALGORITHM-ACTIVE"]


def promote_if_eligible(policy_path: Path, new_stage: str) -> bool:
    """현재 단계보다 높은 stage인 경우에만 algorithm_policy.json을 업데이트한다.

    Args:
        policy_path: data/channels/{CH}/algorithm_policy.json 경로
        new_stage: 새로 판정된 알고리즘 단계

    Returns:
        True if 승격됨, False if 변경 없음
    """
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
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py -v
```
Expected: `PASSED` 9개

- [ ] **Step 6: Commit**

```bash
git add src/agents/analytics_learning/pattern_extractor.py src/agents/analytics_learning/phase_promoter.py tests/test_agents/test_analytics_learning.py
git commit -m "feat: Analytics Agent — 승리 패턴 추출 + Phase 단방향 승격"
```

---

### Task 8: Analytics & Learning — A/B 선택 + Agent 진입점

**Files:**
- Create: `src/agents/analytics_learning/ab_selector.py`
- Modify: `src/agents/analytics_learning/__init__.py`
- Modify: `tests/test_agents/test_analytics_learning.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가**

`tests/test_agents/test_analytics_learning.py` 하단에 추가:
```python
def test_select_winner_returns_highest_ctr_mode():
    """3종 중 CTR이 가장 높은 제목 모드를 반환한다."""
    from src.agents.analytics_learning.ab_selector import select_winner
    variant = {"authority_ctr": 4.2, "curiosity_ctr": 6.8, "benefit_ctr": 3.5}
    assert select_winner(variant) == "curiosity"


def test_select_winner_defaults_to_curiosity_when_all_zero():
    """모든 CTR이 0이면 초기 가중치가 가장 높은 curiosity를 반환한다."""
    from src.agents.analytics_learning.ab_selector import select_winner
    variant = {"authority_ctr": 0.0, "curiosity_ctr": 0.0, "benefit_ctr": 0.0}
    assert select_winner(variant) == "curiosity"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py::test_select_winner_returns_highest_ctr_mode -v
```
Expected: `ImportError`

- [ ] **Step 3: ab_selector.py 구현**

`src/agents/analytics_learning/ab_selector.py`:
```python
"""A/B 테스트(authority/curiosity/benefit) CTR 기반 승자를 선택한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

# 초기 가중치: authority 35% / curiosity 45% / benefit 20%
_DEFAULT_WINNER = "curiosity"
_MODES = ["authority", "curiosity", "benefit"]


def select_winner(variant_performance: dict) -> str:
    """3종 제목 변형 중 CTR이 가장 높은 모드를 반환한다.

    Args:
        variant_performance: {authority_ctr, curiosity_ctr, benefit_ctr} 딕셔너리

    Returns:
        "authority" | "curiosity" | "benefit"
    """
    ctrs = {m: variant_performance.get(f"{m}_ctr", 0.0) for m in _MODES}
    best = max(ctrs, key=ctrs.get)
    # 동점(모두 0)이면 초기 가중치 기준 기본값 반환
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
```

- [ ] **Step 4: Analytics Agent 진입점 구현**

`src/agents/analytics_learning/__init__.py`:
```python
"""Analytics & Learning Agent — KPI 자동 분석 및 파이프라인 정책 반영."""
from pathlib import Path
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.analytics_learning.kpi_analyzer import load_pending_kpis, compute_algorithm_stage
from src.agents.analytics_learning.pattern_extractor import is_winning, update_winning_patterns
from src.agents.analytics_learning.phase_promoter import promote_if_eligible
from src.agents.analytics_learning.ab_selector import select_winner, update_bias


class AnalyticsLearningAgent(BaseAgent):
    """48h KPI 분석, 승리 패턴 추출, Phase 승격, A/B 승자 반영을 담당한다."""

    def __init__(self, root: Path = None):
        super().__init__("AnalyticsLearning")
        if root:
            self.root = root
            self.data_dir = root / "data"
            self.runs_dir = root / "runs"

    def run(self) -> dict:
        """모든 pending KPI를 처리하고 결과 리포트를 반환한다.

        Returns:
            {
                "processed": int,   # 처리된 KPI 건수
                "promoted": int,    # Phase 승격 건수
                "patterns_added": int,  # 승리 패턴 추가 건수
            }
        """
        self._log_start()
        pending_dir = self.data_dir / "global" / "step13_pending"
        pending_kpis = load_pending_kpis(pending_dir) if pending_dir.exists() else []

        promoted_count = 0
        patterns_added = 0

        for item in pending_kpis:
            channel_id = item.get("channel_id", "")
            kpi = item.get("kpi", item)

            stage = compute_algorithm_stage(kpi)
            policy_path = self.data_dir / "channels" / channel_id / "algorithm_policy.json"
            if policy_path.exists():
                if promote_if_eligible(policy_path, stage):
                    promoted_count += 1

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

        report = {
            "processed": len(pending_kpis),
            "promoted": promoted_count,
            "patterns_added": patterns_added,
        }
        self._log_done(report)
        return report
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_analytics_learning.py -v
```
Expected: `PASSED` 11개

- [ ] **Step 6: Commit**

```bash
git add src/agents/analytics_learning/ tests/test_agents/test_analytics_learning.py
git commit -m "feat: Analytics & Learning Agent 완성"
```

---

### Task 9: UI/UX — 스키마 감시 + 타입 동기화

**Files:**
- Create: `src/agents/ui_ux/schema_watcher.py`
- Create: `src/agents/ui_ux/type_syncer.py`
- Create: `tests/test_agents/test_ui_ux.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_agents/test_ui_ux.py`:
```python
"""UI/UX Agent 테스트."""
import json
from pathlib import Path
import pytest


def test_has_schema_changed_true_when_first_run(tmp_path):
    """상태 파일이 없으면 항상 변경됨으로 판정한다."""
    sql_path = tmp_path / "schema.sql"
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    state_path = tmp_path / "schema_state.json"

    from src.agents.ui_ux.schema_watcher import has_schema_changed
    assert has_schema_changed(sql_path, state_path) is True


def test_has_schema_changed_false_when_unchanged(tmp_path):
    """이전과 동일한 SQL이면 변경 없음으로 판정한다."""
    sql_path = tmp_path / "schema.sql"
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    from src.agents.ui_ux.schema_watcher import get_schema_hash, save_schema_hash, has_schema_changed
    state_path = tmp_path / "schema_state.json"
    save_schema_hash(sql_path, state_path)

    assert has_schema_changed(sql_path, state_path) is False


def test_extract_columns_from_sql_parses_types(tmp_path):
    """SQL CREATE TABLE에서 컬럼명과 타입을 올바르게 파싱한다."""
    sql_content = """
    CREATE TABLE channels (
        id TEXT,
        subscriber_count INT,
        is_active BOOL,
        created_at TIMESTAMPTZ
    );
    """
    from src.agents.ui_ux.type_syncer import extract_columns_from_sql
    columns = extract_columns_from_sql(sql_content, "channels")

    names = [c["name"] for c in columns]
    assert "id" in names
    assert "subscriber_count" in names
    assert "is_active" in names


def test_sql_type_to_ts_converts_correctly():
    """SQL 타입을 TypeScript 타입으로 올바르게 변환한다."""
    from src.agents.ui_ux.type_syncer import sql_type_to_ts
    assert sql_type_to_ts("TEXT") == "string"
    assert sql_type_to_ts("INT") == "number"
    assert sql_type_to_ts("BOOL") == "boolean"
    assert sql_type_to_ts("TIMESTAMPTZ") == "string"
    assert sql_type_to_ts("TEXT[]") == "string[]"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_ui_ux.py -v
```
Expected: `ImportError`

- [ ] **Step 3: schema_watcher.py 구현**

`src/agents/ui_ux/schema_watcher.py`:
```python
"""supabase_schema.sql의 변경 여부를 SHA-256 해시로 감지한다."""
import hashlib
from pathlib import Path
from src.core.ssot import read_json, write_json


def get_schema_hash(sql_path: Path) -> str:
    """SQL 파일의 SHA-256 해시를 반환한다."""
    return hashlib.sha256(sql_path.read_bytes()).hexdigest()


def has_schema_changed(sql_path: Path, state_path: Path) -> bool:
    """이전 실행 대비 스키마 변경 여부를 확인한다.

    Returns:
        True if 변경됨 또는 최초 실행, False if 동일
    """
    current_hash = get_schema_hash(sql_path)
    try:
        state = read_json(state_path)
        return state.get("schema_hash") != current_hash
    except FileNotFoundError:
        return True


def save_schema_hash(sql_path: Path, state_path: Path) -> None:
    """현재 스키마 해시를 상태 파일에 저장한다."""
    write_json(state_path, {"schema_hash": get_schema_hash(sql_path)})
```

- [ ] **Step 4: type_syncer.py 구현**

`src/agents/ui_ux/type_syncer.py`:
```python
"""supabase_schema.sql 컬럼 정보를 TypeScript 타입으로 변환한다."""
import re
from pathlib import Path
from loguru import logger

_SQL_TO_TS: dict = {
    "TEXT": "string",
    "VARCHAR": "string",
    "INT": "number",
    "INTEGER": "number",
    "BIGINT": "number",
    "REAL": "number",
    "FLOAT": "number",
    "BOOL": "boolean",
    "BOOLEAN": "boolean",
    "TIMESTAMPTZ": "string",
    "TIMESTAMP": "string",
    "TEXT[]": "string[]",
    "INT[]": "number[]",
}


def extract_columns_from_sql(sql_content: str, table_name: str) -> list:
    """SQL에서 특정 테이블의 컬럼 정보를 추출한다.

    Returns:
        [{"name": str, "sql_type": str}] 리스트
    """
    pattern = rf"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+{re.escape(table_name)}\s*\((.*?)\);"
    match = re.search(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    columns = []
    _skip = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
    for line in match.group(1).split("\n"):
        line = line.strip().rstrip(",")
        if not line or any(line.upper().startswith(s) for s in _skip):
            continue
        col_match = re.match(r"(\w+)\s+([\w\[\]]+)", line)
        if col_match:
            columns.append({
                "name": col_match.group(1),
                "sql_type": col_match.group(2).upper(),
            })
    return columns


def sql_type_to_ts(sql_type: str) -> str:
    """SQL 데이터 타입을 TypeScript 타입 문자열로 변환한다."""
    return _SQL_TO_TS.get(sql_type.upper(), "unknown")


def generate_ts_interface(table_name: str, columns: list) -> str:
    """컬럼 목록으로 TypeScript interface 문자열을 생성한다."""
    lines = [f"export interface {table_name.capitalize()} {{"]
    for col in columns:
        ts_type = sql_type_to_ts(col["sql_type"])
        lines.append(f"  {col['name']}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_ui_ux.py -v
```
Expected: `PASSED` 4개

- [ ] **Step 6: Commit**

```bash
git add src/agents/ui_ux/schema_watcher.py src/agents/ui_ux/type_syncer.py tests/test_agents/test_ui_ux.py
git commit -m "feat: UI/UX Agent — 스키마 감시 + TypeScript 타입 변환"
```

---

### Task 10: UI/UX — Agent 진입점

**Files:**
- Modify: `src/agents/ui_ux/__init__.py`
- Modify: `tests/test_agents/test_ui_ux.py` (통합 테스트 추가)

- [ ] **Step 1: 통합 테스트 추가**

`tests/test_agents/test_ui_ux.py` 하단에 추가:
```python
def test_uiux_agent_run_detects_schema_change(tmp_path):
    """스키마가 변경됐을 때 changed=True를 포함한 리포트를 반환한다."""
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    types_path.write_text("export interface Channels { id: string; }", encoding="utf-8")

    from src.agents.ui_ux import UiUxAgent
    agent = UiUxAgent(root=tmp_path)
    report = agent.run()

    assert "schema_changed" in report
    assert report["schema_changed"] is True


def test_uiux_agent_run_no_change_after_save(tmp_path):
    """동일한 스키마로 두 번 실행하면 두 번째는 changed=False를 반환한다."""
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    types_path.write_text("export interface Channels { id: string; }", encoding="utf-8")

    from src.agents.ui_ux import UiUxAgent
    agent = UiUxAgent(root=tmp_path)
    agent.run()        # 첫 번째 실행 — 해시 저장
    report = agent.run()  # 두 번째 실행 — 변경 없음

    assert report["schema_changed"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_ui_ux.py::test_uiux_agent_run_detects_schema_change -v
```
Expected: `ImportError`

- [ ] **Step 3: __init__.py 구현**

`src/agents/ui_ux/__init__.py`:
```python
"""UI/UX Agent — 대시보드 스키마 변경 감지 및 TypeScript 타입 자동 동기화."""
from pathlib import Path
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.ui_ux.schema_watcher import has_schema_changed, save_schema_hash
from src.agents.ui_ux.type_syncer import extract_columns_from_sql, generate_ts_interface


class UiUxAgent(BaseAgent):
    """스키마 변경을 감지하고 web/lib/types.ts를 자동 동기화한다."""

    def __init__(self, root: Path = None):
        super().__init__("UiUx")
        if root:
            self.root = root

    def run(self) -> dict:
        """스키마 변경 여부를 확인하고 변경 시 타입 동기화를 수행한다.

        Returns:
            {
                "schema_changed": bool,
                "synced_tables": list,   # 동기화된 테이블 목록
            }
        """
        self._log_start()

        sql_path = self.root / "scripts" / "supabase_schema.sql"
        types_path = self.root / "web" / "lib" / "types.ts"
        state_path = self.root / "data" / "global" / ".ui_schema_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        if not sql_path.exists():
            logger.warning(f"[{self.name}] {sql_path} 없음 — 스킵")
            return {"schema_changed": False, "synced_tables": []}

        changed = has_schema_changed(sql_path, state_path)
        synced_tables = []

        if changed:
            logger.info(f"[{self.name}] 스키마 변경 감지 — 타입 동기화 시작")
            sql_content = sql_path.read_text(encoding="utf-8")
            import re
            tables = re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", sql_content, re.IGNORECASE)

            new_interfaces = []
            for table in tables:
                columns = extract_columns_from_sql(sql_content, table)
                if columns:
                    new_interfaces.append(generate_ts_interface(table, columns))
                    synced_tables.append(table)

            if new_interfaces and types_path.exists():
                # 기존 파일 하단에 자동 생성 블록으로 추가
                existing = types_path.read_text(encoding="utf-8")
                marker = "// AUTO-GENERATED by UiUxAgent — DO NOT EDIT BELOW"
                base = existing.split(marker)[0].rstrip()
                updated = base + f"\n\n{marker}\n" + "\n\n".join(new_interfaces) + "\n"
                types_path.write_text(updated, encoding="utf-8")
                logger.info(f"[{self.name}] types.ts 업데이트: {synced_tables}")

            save_schema_hash(sql_path, state_path)

        report = {"schema_changed": changed, "synced_tables": synced_tables}
        self._log_done(report)
        return report
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_ui_ux.py -v
```
Expected: `PASSED` 6개

- [ ] **Step 5: 전체 Phase 1 테스트 실행**

```bash
pytest tests/test_agents/ -v
```
Expected: 모든 테스트 `PASSED`

- [ ] **Step 6: Commit**

```bash
git add src/agents/ui_ux/__init__.py tests/test_agents/test_ui_ux.py
git commit -m "feat: UI/UX Agent 완성 — 스키마 변경 감지 및 types.ts 자동 동기화"
```

---

## Phase 2

---

### Task 11: Video Style & Character — 캐릭터 모니터링

**Files:**
- Create: `src/agents/video_style/character_monitor.py`
- Create: `src/agents/video_style/style_optimizer.py`
- Create: `tests/test_agents/test_video_style.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_agents/test_video_style.py`:
```python
"""Video Style & Character Agent 테스트."""
import json
from pathlib import Path
import pytest


def _write_qa_result(path: Path, consistency_score: float) -> None:
    """테스트용 qa_result.json을 생성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "vision_qa": {"character_consistency_score": consistency_score},
        "overall_pass": consistency_score >= 0.7
    }
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8-sig")


def test_check_character_drift_detects_low_score(tmp_path):
    """평균 일관성 점수 < 0.7 이면 drift_detected=True를 반환한다."""
    for i in range(5):
        _write_qa_result(
            tmp_path / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.5
        )
    from src.agents.video_style.character_monitor import check_character_drift
    result = check_character_drift(tmp_path, "CH1")
    assert result["drift_detected"] is True
    assert result["avg_score"] < 0.7


def test_check_character_drift_no_drift_when_consistent(tmp_path):
    """평균 일관성 점수 >= 0.7 이면 drift_detected=False를 반환한다."""
    for i in range(5):
        _write_qa_result(
            tmp_path / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.9
        )
    from src.agents.video_style.character_monitor import check_character_drift
    result = check_character_drift(tmp_path, "CH1")
    assert result["drift_detected"] is False


def test_check_manim_fallback_rate_calculates_average(tmp_path):
    """최근 10개 실행의 평균 Manim fallback_rate를 반환한다."""
    for i in range(5):
        report_path = tmp_path / "CH1" / f"run_{i:03d}" / "step08" / "manim_stability_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"fallback_rate": 0.6}, ensure_ascii=True), encoding="utf-8-sig"
        )
    from src.agents.video_style.style_optimizer import check_manim_fallback_rate
    rate = check_manim_fallback_rate(tmp_path, "CH1")
    assert abs(rate - 0.6) < 0.01
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_video_style.py -v
```
Expected: `ImportError`

- [ ] **Step 3: character_monitor.py 구현**

`src/agents/video_style/character_monitor.py`:
```python
"""채널별 캐릭터 일관성 점수를 집계하고 드리프트를 감지한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json

_DRIFT_THRESHOLD = 0.7  # 평균 일관성 점수 기준


def check_character_drift(runs_dir: Path, channel_id: str) -> dict:
    """최근 10개 QA 결과에서 캐릭터 일관성 평균을 계산한다.

    Args:
        runs_dir: runs/ 루트 디렉토리
        channel_id: 채널 ID (예: "CH1")

    Returns:
        {"avg_score": float, "drift_detected": bool, "sample_count": int}
    """
    scores = []
    pattern = f"{channel_id}/*/step11/qa_result.json"
    for qa_path in sorted(runs_dir.glob(pattern))[-10:]:
        try:
            qa = read_json(qa_path)
            score = qa.get("vision_qa", {}).get("character_consistency_score", 1.0)
            scores.append(float(score))
        except Exception as e:
            logger.warning(f"QA 결과 읽기 실패: {qa_path} — {e}")

    if not scores:
        return {"avg_score": 1.0, "drift_detected": False, "sample_count": 0}

    avg = sum(scores) / len(scores)
    drift = avg < _DRIFT_THRESHOLD
    if drift:
        logger.warning(f"[{channel_id}] 캐릭터 드리프트 감지: avg={avg:.3f}")
    return {"avg_score": round(avg, 3), "drift_detected": drift, "sample_count": len(scores)}
```

- [ ] **Step 4: style_optimizer.py 구현**

`src/agents/video_style/style_optimizer.py`:
```python
"""CTR 피드백 기반으로 스타일 정책을 업데이트하고 Manim 안정성을 감시한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json, write_json

_MANIM_ALERT_THRESHOLD = 0.5  # fallback_rate 경고 기준


def check_manim_fallback_rate(runs_dir: Path, channel_id: str) -> float:
    """최근 10개 실행의 평균 Manim fallback_rate를 계산한다.

    Returns:
        0.0~1.0 사이의 평균 fallback rate. 데이터 없으면 0.0.
    """
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
    """style_policy_master.json에 부분 업데이트를 적용한다.

    Args:
        policy_path: data/channels/{CH}/style_policy_master.json 경로
        updates: 업데이트할 키-값 딕셔너리
    """
    try:
        policy = read_json(policy_path)
    except FileNotFoundError:
        policy = {}
    policy.update(updates)
    policy["last_updated_by"] = "video_style_agent"
    write_json(policy_path, policy)
    logger.info(f"스타일 정책 업데이트: {policy_path.parent.name} — {list(updates.keys())}")
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_agents/test_video_style.py -v
```
Expected: `PASSED` 3개

- [ ] **Step 6: Commit**

```bash
git add src/agents/video_style/character_monitor.py src/agents/video_style/style_optimizer.py tests/test_agents/test_video_style.py
git commit -m "feat: Video Style Agent — 캐릭터 드리프트 감지 + Manim fallback 모니터링"
```

---

### Task 12: Video Style & Character — Agent 진입점

**Files:**
- Modify: `src/agents/video_style/__init__.py`
- Modify: `tests/test_agents/test_video_style.py` (통합 테스트 추가)

- [ ] **Step 1: 통합 테스트 추가**

`tests/test_agents/test_video_style.py` 하단에 추가:
```python
def test_video_style_agent_run_returns_report(tmp_path):
    """run()이 모든 채널의 드리프트 및 Manim 상태를 포함한 리포트를 반환한다."""
    # CH1 QA 결과 생성 — VideoStyleAgent.runs_dir = root/"runs" 이므로 runs/ 하위에 생성
    for i in range(3):
        _write_qa_result(
            tmp_path / "runs" / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.85
        )

    # 채널 목록 상태 파일 생성
    registry_path = tmp_path / "data" / "global" / "channel_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps([{"id": "CH1", "status": "active"}], ensure_ascii=True),
        encoding="utf-8-sig"
    )

    from src.agents.video_style import VideoStyleAgent
    agent = VideoStyleAgent(root=tmp_path)
    report = agent.run()

    assert "channels" in report
    assert "CH1" in report["channels"]
    assert "drift_detected" in report["channels"]["CH1"]
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_agents/test_video_style.py::test_video_style_agent_run_returns_report -v
```
Expected: `ImportError`

- [ ] **Step 3: __init__.py 구현**

`src/agents/video_style/__init__.py`:
```python
"""Video Style & Character Agent — 채널별 시각 아이덴티티 유지 및 스타일 최적화."""
from pathlib import Path
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.agents.video_style.character_monitor import check_character_drift
from src.agents.video_style.style_optimizer import check_manim_fallback_rate
from src.core.ssot import read_json


class VideoStyleAgent(BaseAgent):
    """캐릭터 일관성 드리프트 감지, Manim fallback 모니터링, 스타일 정책 최적화를 담당한다."""

    def __init__(self, root: Path = None):
        super().__init__("VideoStyle")
        if root:
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

    def run(self) -> dict:
        """모든 활성 채널의 스타일 상태를 점검하고 리포트를 반환한다.

        Returns:
            {
                "channels": {
                    "CH1": {"drift_detected": bool, "avg_score": float, "manim_fallback_rate": float},
                    ...
                }
            }
        """
        self._log_start()
        channels = self._get_active_channels()
        channel_reports = {}

        for ch_id in channels:
            drift_info = check_character_drift(self.runs_dir, ch_id)
            manim_rate = check_manim_fallback_rate(self.runs_dir, ch_id)
            channel_reports[ch_id] = {
                "drift_detected": drift_info["drift_detected"],
                "avg_score": drift_info["avg_score"],
                "manim_fallback_rate": manim_rate,
            }

        report = {"channels": channel_reports}
        self._log_done({"channels_checked": len(channels)})
        return report
```

- [ ] **Step 4: 전체 테스트 실행**

```bash
pytest tests/test_agents/ -v
```
Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 최종 Commit**

```bash
git add src/agents/video_style/__init__.py tests/test_agents/test_video_style.py
git commit -m "feat: Video Style & Character Agent 완성 (Phase 2)"
```

---

## 완료 검증

- [ ] **전체 테스트 실행**

```bash
pytest tests/test_agents/ -v --tb=short
```
Expected: `PASSED` 전체 (실패 0건)

- [ ] **기존 테스트 회귀 없음 확인**

```bash
pytest tests/ -q --ignore=tests/test_agents/
```
Expected: 기존 테스트 모두 `PASSED` (신규 Agent 코드로 인한 회귀 없음)

- [ ] **임포트 검증**

```bash
python -c "
from src.agents.dev_maintenance import DevMaintenanceAgent
from src.agents.analytics_learning import AnalyticsLearningAgent
from src.agents.ui_ux import UiUxAgent
from src.agents.video_style import VideoStyleAgent
print('모든 Agent 임포트 OK')
"
```
Expected: `모든 Agent 임포트 OK`
