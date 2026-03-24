"""
v6 Gate Record Utilities (NO run_manager import)

목적:
- 순환 import 방지
- v6 게이트 성공/실패 기록을 공통 유틸로 제공
- REQUIRED_* 상수도 여기서 제공 (run_manager/v6_gates 양쪽에서 사용)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from backend.utils.failure_taxonomy import classify_failure
from backend.utils.meaning_failure import classify_meaning_failure
from backend.schemas.failure_taxonomy import normalize_failure_taxonomy


REQUIRED_MANIFEST_KEYS = [
    "run_id",
    "schema_version",
    "run_state",
    "goal_ref",
    "constraint_ref",
    "repro_key",
    "env_snapshot",
]

REQUIRED_IDENTITY_KEYS = [
    "identity_profile_ref",
    "tone_profile_ref",
    "disallowed_content_rules_ref",
]

REQUIRED_DECISION_TRACE_KEYS = [
    "input_reference",
    "alternatives",
    "decision_reason",
    "final_choice",
]


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def record_failure(manifest: Dict[str, Any], step: str, error: str) -> None:
    """v6 게이트 실패 기록 (failure_taxonomy + meaning_failure 포함)"""
    taxonomy_result = classify_failure(step, error, manifest=manifest)
    meaning = classify_meaning_failure(error, manifest=manifest, step=step)
    
    # failure_taxonomy를 5개 값 중 하나로 normalize
    if isinstance(taxonomy_result, dict):
        primary_cat = taxonomy_result.get("primary_category") or taxonomy_result.get("primary_taxonomy") or "STRUCTURE"
    else:
        primary_cat = str(taxonomy_result)
    
    normalized_taxonomy = normalize_failure_taxonomy(primary_cat)
    failure_taxonomy_value = normalized_taxonomy.value
    
    # meaning_failure 보장
    meaning_value = getattr(meaning, "value", str(meaning)) if meaning else "LOW_SIGNAL"
    if not meaning_value or meaning_value == "":
        meaning_value = "LOW_SIGNAL"

    steps = manifest.setdefault("steps", {})
    step_obj = steps.setdefault(step, {"status": "pending", "artifacts": [], "errors": [], "warnings": []})
    step_obj.setdefault("errors", []).append(
        {
            "ts": _now_iso(),
            "error": error,
            "failure_taxonomy": failure_taxonomy_value,
            "meaning_failure": meaning_value,
        }
    )
    step_obj["status"] = "failed"
    manifest["run_state"] = "FAILED"


def mark_success(manifest: Dict[str, Any], step: str, artifact: Optional[Dict[str, Any]] = None) -> None:
    """v6 게이트 성공 기록"""
    steps = manifest.setdefault("steps", {})
    step_obj = steps.setdefault(step, {"status": "pending", "artifacts": [], "errors": [], "warnings": []})
    step_obj["status"] = "success"
    if artifact is not None:
        step_obj.setdefault("artifacts", []).append({"ts": _now_iso(), **artifact})

