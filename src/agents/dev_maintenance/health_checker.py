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
