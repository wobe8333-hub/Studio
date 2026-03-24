"""
Run Manager - Run Manifest 및 단일 구조 관리

기능:
- Run Manifest 생성 및 업데이트
- Checkpoint 관리
- 재개 (Resume) 로직
- Idempotent 실행 지원
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from backend.utils.repro import ensure_repro, generate_repro_seed, generate_repro_key
from backend.utils.env_snapshot import ensure_environment
from backend.utils.failure_taxonomy import classify_failure
from backend.utils.meaning_failure import classify_meaning_failure
from backend.schemas.failure_taxonomy import normalize_failure_taxonomy, FailureTaxonomy
from backend.utils.v6_gate_record import (
    REQUIRED_MANIFEST_KEYS,
    REQUIRED_IDENTITY_KEYS,
    REQUIRED_DECISION_TRACE_KEYS,
    record_failure as v6_record_failure,
    mark_success as v6_mark_success,
)

try:
    import orjson  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    orjson = None


class RunStatus(str, Enum):
    """Run 상태"""
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class RunStep(str, Enum):
    """Run 단계"""
    STEP1 = "step1"
    STEP2 = "step2"
    STEP3 = "step3"
    STEP4 = "step4"


def _now_iso() -> str:
    """UTC ISO8601 형식 현재 시간 반환"""
    return datetime.utcnow().isoformat() + "Z"


def _v6_normalize_errors(errors: Any, manifest: Dict[str, Any], step_name: str) -> List[Dict[str, Any]]:
    """
    v6-Step4/5: errors 정규화 (string을 dict로 변환, failure_taxonomy/meaning_failure 추가)
    
    Args:
        errors: errors 리스트 (None, str, dict, list 등 가능)
        manifest: manifest dict
        step_name: step 이름
    
    Returns:
        List[Dict]: 정규화된 errors 리스트
    """
    if errors is None:
        return []
    
    if not isinstance(errors, list):
        errors = [errors]
    
    normalized = []
    
    for e in errors:
        if isinstance(e, str):
            # string을 dict로 변환
            error_str = e
            taxonomy_result = classify_failure(step_name, error_str, manifest=manifest)
            meaning = classify_meaning_failure(error_str, manifest=manifest, step=step_name)
            
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
            
            normalized.append({
                "ts": _now_iso(),
                "error": error_str,
                "failure_taxonomy": failure_taxonomy_value,
                "meaning_failure": meaning_value
            })
        elif isinstance(e, dict):
            # dict인 경우 필수 키 보장
            error_dict = dict(e)
            
            if "error" not in error_dict or not error_dict.get("error"):
                error_dict["error"] = str(e)
            
            error_str = str(error_dict.get("error", ""))
            
            if "failure_taxonomy" not in error_dict or not error_dict.get("failure_taxonomy"):
                taxonomy_result = classify_failure(step_name, error_str, manifest=manifest)
                if isinstance(taxonomy_result, dict):
                    primary_cat = taxonomy_result.get("primary_category") or taxonomy_result.get("primary_taxonomy") or "STRUCTURE"
                else:
                    primary_cat = str(taxonomy_result)
                normalized_taxonomy = normalize_failure_taxonomy(primary_cat)
                error_dict["failure_taxonomy"] = normalized_taxonomy.value
            else:
                # 기존 값이 있어도 5개 값 중 하나로 normalize
                existing_tax = error_dict.get("failure_taxonomy", "")
                normalized_taxonomy = normalize_failure_taxonomy(existing_tax)
                error_dict["failure_taxonomy"] = normalized_taxonomy.value
            
            if "meaning_failure" not in error_dict or not error_dict.get("meaning_failure"):
                meaning = classify_meaning_failure(error_str, manifest=manifest, step=step_name)
                meaning_value = getattr(meaning, "value", str(meaning)) if meaning else "LOW_SIGNAL"
                if not meaning_value or meaning_value == "":
                    meaning_value = "LOW_SIGNAL"
                error_dict["meaning_failure"] = meaning_value
            
            if "ts" not in error_dict or not error_dict.get("ts"):
                error_dict["ts"] = _now_iso()
            
            normalized.append(error_dict)
        else:
            # 그 외 타입은 str()로 변환 후 dict로 처리
            error_str = str(e)
            taxonomy_result = classify_failure(step_name, error_str, manifest=manifest)
            meaning = classify_meaning_failure(error_str, manifest=manifest, step=step_name)
            
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
            
            normalized.append({
                "ts": _now_iso(),
                "error": error_str,
                "failure_taxonomy": failure_taxonomy_value,
                "meaning_failure": meaning_value
            })
    
    return normalized


def _v6_normalize_decision_trace(manifest: Dict[str, Any]) -> bool:
    """
    v6-Step12: decision_trace 정규화 (필수 키 보장)
    
    Args:
        manifest: manifest dict
    
    Returns:
        bool: 변경 여부
    """
    dt = manifest.get("decision_trace")
    if not dt:
        return False
    
    if not isinstance(dt, list):
        return False
    
    changed = False
    
    for i, item in enumerate(dt):
        if not isinstance(item, dict):
            # dict가 아니면 dict로 변환
            item = {"backfilled_item": str(item)}
            dt[i] = item
            changed = True
        
        # input_reference 보장
        if "input_reference" not in item or not item.get("input_reference"):
            # 후보 키에서 찾기
            candidates = ["input_ref", "input", "source", "reference"]
            found = None
            for c in candidates:
                if c in item and item[c]:
                    found = str(item[c])
                    break
            item["input_reference"] = found if found else "backfilled:unknown"
            changed = True
        
        # alternatives 보장
        if "alternatives" not in item or not isinstance(item.get("alternatives"), list):
            item["alternatives"] = [
                {"option": "keep_current", "description": "backfilled placeholder"},
                {"option": "rollback", "description": "backfilled placeholder"}
            ]
            changed = True
        elif len(item["alternatives"]) < 2:
            # 길이가 2 미만이면 placeholder 추가
            while len(item["alternatives"]) < 2:
                item["alternatives"].append({
                    "option": f"backfilled_option_{len(item['alternatives'])}",
                    "description": "backfilled placeholder"
                })
            changed = True
        
        # decision_reason 보장
        if "decision_reason" not in item or not item.get("decision_reason"):
            item["decision_reason"] = "backfilled_for_v6_schema"
            changed = True
        
        # final_choice 보장
        if "final_choice" not in item or not item.get("final_choice"):
            item["final_choice"] = "backfilled"
            changed = True
        
        # ts 보장
        if "ts" not in item or not item.get("ts"):
            item["ts"] = _now_iso()
            changed = True
    
    return changed


def get_project_root() -> Path:
    """
    프로젝트 루트 디렉토리 경로 반환 (단일 진실)
    
    Returns:
        Path: 프로젝트 루트 경로 (backend의 상위 2단계)
    """
    # backend/utils/run_manager.py -> backend -> 프로젝트 루트
    return Path(__file__).resolve().parents[2]


def get_runs_root(base_dir: Optional[Path] = None) -> Path:
    """
    runs 루트 디렉토리 경로 반환 (단일 진실)
    
    Args:
        base_dir: 기본 디렉토리 (None이면 프로젝트 루트 기준으로 backend/output/runs 계산)
    
    Returns:
        Path: backend/output/runs 경로
    """
    if base_dir is None:
        project_root = get_project_root()
        runs_root = project_root / "backend" / "output" / "runs"
    else:
        # base_dir이 제공되면 그 기준으로 계산 (하위 호환)
        if base_dir.name == "backend":
            output_root = base_dir / "output"
        else:
            # base_dir이 이미 output이거나 다른 경로인 경우
            output_root = base_dir / "output" if (base_dir / "output").exists() else base_dir
        runs_root = output_root / "runs"
    
    return runs_root


def get_run_dir(run_id: str, base_dir: Optional[Path] = None) -> Path:
    """
    Run 디렉토리 경로 반환
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리 (None이면 backend 디렉토리 기준)
    
    Returns:
        Path: output/runs/{run_id} 경로
    """
    runs_root = get_runs_root(base_dir)
    run_dir = runs_root / run_id
    return run_dir


def get_run_subdirs(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Run 하위 디렉토리 구조 생성 및 반환 (요구사항 스펙)
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 디렉토리 경로 딕셔너리
            - root: runs/<run_id>
            - step1: runs/<run_id>/step1 (입력 백업)
            - step2: runs/<run_id>/step2
            - step3: runs/<run_id>/step3
            - logs/reports/plans/verify/renders/artifacts: 보조 저장소
    """
    run_dir = get_run_dir(run_id, base_dir)
    
    dirs = {
        "root": run_dir,
        "step1": run_dir / "step1",
        "input": run_dir / "step1",  # 하위 호환 별칭
        "step2": run_dir / "step2",
        "step3": run_dir / "step3",
        "logs": run_dir / "logs",
        "reports": run_dir / "reports",
        "plans": run_dir / "plans",
        "verify": run_dir / "verify",
        "renders": run_dir / "renders",
        "artifacts": run_dir / "artifacts"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


def _atomic_write_json(path: Path, data: Any) -> None:
    """
    JSON 파일을 원자적으로 저장한다.
    임시 파일에 먼저 쓰고 rename으로 치환하여 부분 쓰기/손상 방지.
    manifest 저장 시 JSON-safe 정규화를 자동 적용.
    """
    from backend.utils.json_sanitize import sanitize_json_obj
    
    # manifest 저장 시 JSON-safe 정규화
    data = sanitize_json_obj(data)
    
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    if orjson is not None:
        # orjson은 bytes를 반환하므로 그대로 기록
        content = orjson.dumps(data, option=orjson.OPT_INDENT_2)
        tmp_path.write_bytes(content)
    else:
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _save_manifest(run_id: str, manifest: Dict[str, Any], base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Manifest 구조를 단일 책임으로 저장하는 헬퍼.
    """
    manifest["last_updated"] = datetime.now().isoformat()
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    return manifest


def calculate_input_hash(input_data: str) -> str:
    """
    입력 데이터의 해시 계산
    
    Args:
        input_data: 입력 데이터 (텍스트)
    
    Returns:
        str: SHA256 해시 (16진수)
    """
    return hashlib.sha256(input_data.encode("utf-8")).hexdigest()[:16]


def create_run_manifest(
    run_id: str,
    input_hash: Optional[str] = None,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Run Manifest 생성
    
    Args:
        run_id: 실행 ID
        input_hash: 입력 데이터 해시 (없으면 None)
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: Manifest 데이터
    """
    dirs = get_run_subdirs(run_id, base_dir)
    manifest_path = dirs["root"] / "manifest.json"
    
    # 기존 output 디렉토리 경로 계산
    if base_dir is None:
        backend_dir = Path(__file__).resolve().parent.parent
        output_root = backend_dir / "output"
    else:
        output_root = base_dir / "output"
    
    verify_dir = output_root / "verify"
    plans_dir = output_root / "plans"
    reports_dir = output_root / "reports"
    
    now_str = datetime.now().isoformat()
    
    # schema_version 및 run_state 설정
    schema_version = "v2_manifest_1_2"
    run_state = "CREATED"
    
    # repro 생성
    repro = ensure_repro({}, run_id)
    
    # environment 캡처
    environment = ensure_environment({})
    
    manifest = {
        "run_id": run_id,
        "schema_version": schema_version,
        "input_hash": input_hash or "",
        "created_at": now_str,
        "last_updated": now_str,
        "status": RunStatus.RUNNING.value,  # 하위 호환 유지
        "run_state": run_state,  # 새 필드
        "current_step": RunStep.STEP1.value,
        "completed_steps": [RunStep.STEP1.value],
        "files_generated": [],
        "last_error": None,
        "goal_ref": None,  # 읽기 전용 슬롯
        "constraint_ref": None,  # 읽기 전용 슬롯
        "baseline_ref": None,  # 읽기 전용 슬롯
        "experiment_id": None,
        "policy_version_id": None,
        "repro": repro,
        "environment": environment,
        # v1.4 피드백 반영: 운영 콘솔/권한 모드/데이터 영향경계/비용·중단 상한 필드 추가
        "creation_mode": "REVIEW",
        "ui_scope": "OPS_CONSOLE",
        "data_impact_scope": "RUN_ONLY",
        "cost_caps": {
            "max_seconds": 0,
            "max_usd": 0.0
        },
        "stop_conditions": {
            "max_failures": 0,
            "max_retries": 0
        },
        "decision_trace": [],
        "governance": {
            "auto_select_enabled": False,
            "recommendation_enabled": False
        },
        # v6 필수 필드
        "execution_mode": "REVIEW",
        "identity_profile_ref": "backend/config/identity_profiles/v6_default.json",
        "tone_profile_ref": "backend/config/tone_profiles/v6_default.json",
        "disallowed_content_rules_ref": "backend/config/disallowed_rules/v6_default.json",
        "cost_state": "NORMAL",
        "hitl_rules": {
            "retry_count_threshold": 3,
            "cost_usd_threshold": 0.0
        },
        "steps": {
            "step1": {
                "status": "success",
                "artifacts": []
            },
            "step2": {
                "status": "pending",
                "artifacts": [],
                "errors": [],
                "warnings": []
            },
            "step3": {
                "status": "pending",
                "artifacts": [],
                "errors": [],
                "warnings": []
            }
        },
        "paths": {
            "runs_dir": dirs["root"].resolve().as_posix(),
            "legacy_outputs": {
                "verify_dir": verify_dir.resolve().as_posix(),
                "plans_dir": plans_dir.resolve().as_posix(),
                "reports_dir": reports_dir.resolve().as_posix()
            }
        }
    }
    
    _atomic_write_json(manifest_path, manifest)
    return manifest


def load_run_manifest(run_id: str, base_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Run Manifest 로드 및 백필
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: Manifest 데이터 (없으면 None, 백필 적용됨)
    """
    from backend.utils.manifest_repair import load_manifest_with_repair
    
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    
    if not manifest_path.exists():
        return None
    
    # 복구 가능한 로더 사용
    manifest = load_manifest_with_repair(manifest_path)
    
    if manifest is None:
        return None
    
    # 백필 적용
    manifest = _backfill_manifest(manifest, run_id)
    
    return manifest


def _backfill_manifest(manifest: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    manifest 백필 (처음문서_v1.2 기준)
    
    Args:
        manifest: 기존 manifest
        run_id: 실행 ID
    
    Returns:
        Dict: 백필된 manifest
    """
    needs_save = False
    
    # schema_version 백필
    if "schema_version" not in manifest:
        manifest["schema_version"] = "v2_manifest_1_2"
        needs_save = True
    
    # run_state 백필 (기존 status에서 변환)
    if "run_state" not in manifest:
        old_status = manifest.get("status", "unknown")
        run_state_map = {
            "running": "RUNNING",
            "failed": "FAILED",
            "success": "SUCCESS",
            "completed": "SUCCESS"
        }
        manifest["run_state"] = run_state_map.get(old_status, "CREATED")
        needs_save = True
    
    # goal_ref, constraint_ref 백필 (v6 필수)
    if "goal_ref" not in manifest or not manifest.get("goal_ref"):
        manifest["goal_ref"] = "backend/config/goals/v6_default.json"
        needs_save = True
    
    if "constraint_ref" not in manifest or not manifest.get("constraint_ref"):
        manifest["constraint_ref"] = "backend/config/constraints/v6_default.json"
        needs_save = True
    
    # baseline_ref 백필 (기존 로직 유지)
    if "baseline_ref" not in manifest:
        manifest["baseline_ref"] = None
        needs_save = True
    
    # experiment_id, policy_version_id 백필
    for id_field in ["experiment_id", "policy_version_id"]:
        if id_field not in manifest:
            manifest[id_field] = None
            needs_save = True
    
    # repro 백필
    if "repro" not in manifest or not manifest.get("repro", {}).get("repro_key"):
        manifest["repro"] = ensure_repro(manifest, run_id)
        needs_save = True
    
    # environment 백필
    if "environment" not in manifest or not manifest.get("environment", {}).get("python_version"):
        manifest["environment"] = ensure_environment(manifest)
        needs_save = True
    
    # v1.4 피드백 반영: 운영 콘솔/권한 모드/데이터 영향경계/비용·중단 상한 필드 백필
    if "creation_mode" not in manifest:
        manifest["creation_mode"] = "REVIEW"
        needs_save = True
    
    if "ui_scope" not in manifest:
        manifest["ui_scope"] = "OPS_CONSOLE"
        needs_save = True
    
    if "data_impact_scope" not in manifest:
        manifest["data_impact_scope"] = "RUN_ONLY"
        needs_save = True
    
    if "cost_caps" not in manifest:
        manifest["cost_caps"] = {
            "max_seconds": 0,
            "max_usd": 0.0
        }
        needs_save = True
    
    if "stop_conditions" not in manifest:
        manifest["stop_conditions"] = {
            "max_failures": 0,
            "max_retries": 0
        }
        needs_save = True
    
    if "decision_trace" not in manifest:
        manifest["decision_trace"] = []
        needs_save = True
    
    # v6 필수 필드 백필
    if "execution_mode" not in manifest:
        manifest["execution_mode"] = "REVIEW"
        needs_save = True
    
    if "identity_profile_ref" not in manifest:
        manifest["identity_profile_ref"] = "backend/config/identity_profiles/v6_default.json"
        needs_save = True
    
    if "tone_profile_ref" not in manifest:
        manifest["tone_profile_ref"] = "backend/config/tone_profiles/v6_default.json"
        needs_save = True
    
    if "disallowed_content_rules_ref" not in manifest:
        manifest["disallowed_content_rules_ref"] = "backend/config/disallowed_rules/v6_default.json"
        needs_save = True
    
    if "cost_state" not in manifest:
        manifest["cost_state"] = "NORMAL"
        needs_save = True
    
    if "hitl_rules" not in manifest:
        manifest["hitl_rules"] = {
            "retry_count_threshold": 3,
            "cost_usd_threshold": 0.0
        }
        needs_save = True
    
    # v1.4 Step10: locks 백필
    if "locks" not in manifest:
        manifest["locks"] = {"scenes": {}}
        needs_save = True
    else:
        if "scenes" not in manifest["locks"]:
            manifest["locks"]["scenes"] = {}
            needs_save = True
    
    if "governance" not in manifest:
        manifest["governance"] = {
            "auto_select_enabled": False,
            "recommendation_enabled": False
        }
        needs_save = True
    else:
        # governance 내부 필드도 백필
        governance = manifest["governance"]
        if not isinstance(governance, dict):
            governance = {}
            manifest["governance"] = governance
            needs_save = True
        
        if "auto_select_enabled" not in governance:
            governance["auto_select_enabled"] = False
            needs_save = True
        
        if "recommendation_enabled" not in governance:
            governance["recommendation_enabled"] = False
            needs_save = True
    
    # v6 필수: repro_key (repro.repro_key와 동일 또는 별도 보장)
    if "repro_key" not in manifest:
        repro = manifest.get("repro", {})
        if isinstance(repro, dict) and repro.get("repro_key"):
            manifest["repro_key"] = repro["repro_key"]
        else:
            manifest["repro_key"] = ""
        needs_save = True
    
    # v6 필수: env_snapshot (environment와 동일 또는 별도 보장)
    if "env_snapshot" not in manifest:
        env = manifest.get("environment", {})
        if isinstance(env, dict) and env:
            manifest["env_snapshot"] = env
        else:
            manifest["env_snapshot"] = {}
        needs_save = True
    
    # v6-Step4/5: errors 정규화
    steps = manifest.get("steps", {}) or {}
    for step_name, step_obj in steps.items():
        if isinstance(step_obj, dict):
            original_errors = step_obj.get("errors")
            normalized_errors = _v6_normalize_errors(original_errors, manifest, step_name)
            # 정규화 결과가 원본과 다르면 저장 필요
            if normalized_errors != original_errors:
                step_obj["errors"] = normalized_errors
                needs_save = True
    
    # v6-Step12: decision_trace 정규화
    if _v6_normalize_decision_trace(manifest):
        needs_save = True
    
    # v6 게이트 step 기록 생성 (감사 가능한 기록)
    steps = manifest.setdefault("steps", {})
    
    # v6-Step2: Manifest Gate 기록
    step2_name = "v6_step2_manifest_gate"
    if step2_name not in steps:
        missing = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest or manifest.get(k) in (None, "", {})]
        if not missing:
            v6_mark_success(manifest, step2_name, {"note": "backfill_success"})
            needs_save = True
        else:
            error_msg = f"manifest_missing_required_keys: {missing}"
            v6_record_failure(manifest, step2_name, error_msg)
            needs_save = True
    
    # v6-Step3: Identity Guardrail 기록
    step3_name = "v6_step3_identity_guardrail"
    if step3_name not in steps:
        missing = [k for k in REQUIRED_IDENTITY_KEYS if k not in manifest or manifest.get(k) in (None, "", {})]
        if not missing:
            v6_mark_success(manifest, step3_name, {"note": "backfill_success"})
            needs_save = True
        else:
            error_msg = f"identity_guardrail_missing_keys: {missing}"
            v6_record_failure(manifest, step3_name, error_msg)
            needs_save = True
    
    # v6-Step12: Decision Trace 기록
    step12_name = "v6_step12_decision_trace"
    if step12_name not in steps:
        dt = manifest.get("decision_trace", [])
        if dt and isinstance(dt, list):
            all_valid = True
            for item in dt:
                if not isinstance(item, dict):
                    all_valid = False
                    break
                missing = [k for k in REQUIRED_DECISION_TRACE_KEYS if k not in item or not item.get(k)]
                if missing:
                    all_valid = False
                    break
                alternatives = item.get("alternatives", [])
                if not isinstance(alternatives, list) or len(alternatives) < 2:
                    all_valid = False
                    break
            
            if all_valid:
                v6_mark_success(manifest, step12_name, {"note": "backfill_success"})
                needs_save = True
            else:
                error_msg = "decision_trace_structure_invalid"
                v6_record_failure(manifest, step12_name, error_msg)
                needs_save = True
        else:
            # decision_trace가 없거나 빈 리스트면 success로 기록 (NOT_TRIGGERED)
            v6_mark_success(manifest, step12_name, {"note": "backfill_success_not_triggered"})
            needs_save = True
    
    # 백필 후 저장
    if needs_save:
        run_dir = get_run_dir(run_id, None)
        manifest_path = run_dir / "manifest.json"
        _atomic_write_json(manifest_path, manifest)
    
    return manifest


def ensure_manifest_v1_4_step1_fields(manifest: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    """
    manifest에 v1.4 Step1 신규 메타 필드 백필 (안전)
    
    Args:
        manifest: manifest dict
    
    Returns:
        tuple[Dict[str, Any], bool]: (수정된 manifest, changed 여부)
    
    규칙:
    - 기존 키/값/구조는 절대 변경하지 않음
    - 신규 키는 없을 때만 추가
    - schema_version은 절대 변경하지 않음
    """
    changed = False
    
    # (1) creation_mode
    if "creation_mode" not in manifest:
        manifest["creation_mode"] = "REVIEW"
        changed = True
    
    # (2) ui_scope
    if "ui_scope" not in manifest:
        manifest["ui_scope"] = "OPS_CONSOLE"
        changed = True
    
    # (3) data_impact_scope
    if "data_impact_scope" not in manifest:
        manifest["data_impact_scope"] = "RUN_ONLY"
        changed = True
    
    # (4) cost_caps
    if "cost_caps" not in manifest:
        manifest["cost_caps"] = {
            "max_seconds": 0,
            "max_usd": 0.0
        }
        changed = True
    
    # (5) stop_conditions
    if "stop_conditions" not in manifest:
        manifest["stop_conditions"] = {
            "max_failures": 0,
            "max_retries": 0
        }
        changed = True
    
    # (6) decision_trace
    if "decision_trace" not in manifest:
        manifest["decision_trace"] = []
        changed = True
    
    # (7) governance
    if "governance" not in manifest:
        manifest["governance"] = {
            "auto_select_enabled": False,
            "recommendation_enabled": False
        }
        changed = True
    else:
        # governance가 이미 있으면 내부 필드만 백필 (덮어쓰기 금지)
        governance = manifest["governance"]
        if not isinstance(governance, dict):
            governance = {}
            manifest["governance"] = governance
            changed = True
        
        if "auto_select_enabled" not in governance:
            governance["auto_select_enabled"] = False
            changed = True
        
        if "recommendation_enabled" not in governance:
            governance["recommendation_enabled"] = False
            changed = True
    
    # (8) locks
    if "locks" not in manifest:
        manifest["locks"] = {"scenes": {}}
        changed = True
    else:
        # locks가 이미 있으면 scenes 필드만 백필 (덮어쓰기 금지)
        locks = manifest["locks"]
        if not isinstance(locks, dict):
            locks = {}
            manifest["locks"] = locks
            changed = True
        
        if "scenes" not in locks:
            locks["scenes"] = {}
            changed = True
    
    return manifest, changed


def backfill_manifest_file_v1_4_step1(manifest_path: Path) -> bool:
    """
    manifest.json 파일에 v1.4 Step1 신규 메타 필드 백필 (안전)
    
    Args:
        manifest_path: manifest.json 경로
    
    Returns:
        bool: 변경 여부 (changed=True면 저장됨, False면 변경 없음)
    
    규칙:
    - 기존 키/값/구조는 절대 변경하지 않음
    - 신규 키는 없을 때만 추가
    - schema_version은 절대 변경하지 않음
    - 원자적 저장 사용
    """
    if not manifest_path.exists():
        return False
    
    try:
        # JSON 로드
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        # 백필
        manifest, changed = ensure_manifest_v1_4_step1_fields(manifest)
        
        # changed=True일 때만 저장
        if changed:
            _atomic_write_json(manifest_path, manifest)
            return True
        
        return False
    except Exception as e:
        # 에러 발생 시 예외를 다시 던져서 호출자가 처리할 수 있도록
        raise RuntimeError(f"백필 실패: {manifest_path}: {e}") from e


def append_decision_trace(run_id: str, entry: Dict[str, Any], base_dir: Optional[Path] = None) -> None:
    """
    decision_trace에 엔트리 추가 (v1.4 Step6)
    
    Args:
        run_id: 실행 ID (video_id 가능)
        entry: 추가할 엔트리 데이터
        base_dir: 기본 디렉토리
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Manifest not found for run_id: {run_id}")
    
    # decision_trace 백필
    if "decision_trace" not in manifest:
        manifest["decision_trace"] = []
    
    # entry에 타임스탬프 및 메타데이터 추가
    trace_entry = {
        "timestamp": datetime.now().isoformat(),
        "actor": entry.get("actor", "human"),
        "channel": entry.get("channel", "ops_console"),
        "run_state": manifest.get("run_state"),
        "current_step": manifest.get("current_step"),
        **entry
    }
    
    manifest["decision_trace"].append(trace_entry)
    manifest["last_updated"] = datetime.now().isoformat()
    
    # atomic 저장
    manifest_path = get_run_dir(run_id, base_dir) / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    
    # v1.4 Step7: decision_trace_count 자동 동기화 (순환 import 방지)
    try:
        from backend.utils.observability import update_metrics, ensure_metrics
        metrics = ensure_metrics(run_id, base_dir)
        metrics["human_intervention_count"] = metrics.get("human_intervention_count", 0) + 1
        metrics["decision_trace_count"] = len(manifest["decision_trace"])
        update_metrics(run_id, metrics, base_dir)
    except Exception:
        # observability 업데이트 실패는 무시 (메인 로직에 영향 없음)
        pass


def update_run_manifest(
    run_id: str,
    updates: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Run Manifest 업데이트
    
    Args:
        run_id: 실행 ID
        updates: 업데이트할 필드 딕셔너리
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: 업데이트된 Manifest 데이터
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Run manifest not found: {run_id}")
    
    # 업데이트 적용
    manifest.update(updates)
    
    # 단일 저장 헬퍼 사용
    return _save_manifest(run_id, manifest, base_dir)


def _update_run_state_from_status(manifest: Dict[str, Any]) -> None:
    """
    기존 status에서 run_state 업데이트 (처음문서_v1.2)
    
    Args:
        manifest: run manifest
    """
    if "run_state" in manifest:
        return  # 이미 있으면 업데이트 안 함
    
    old_status = manifest.get("status", "unknown")
    run_state_map = {
        "running": "RUNNING",
        "failed": "FAILED",
        "success": "SUCCESS",
        "completed": "SUCCESS"
    }
    manifest["run_state"] = run_state_map.get(old_status, "CREATED")


def mark_step_completed(
    run_id: str,
    step: RunStep,
    files_generated: List[str],
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Step 완료 표시
    
    Args:
        run_id: 실행 ID
        step: 완료된 단계
        files_generated: 생성된 파일 목록
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: 업데이트된 Manifest 데이터
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Run manifest not found: {run_id}")
    
    step_str = step.value
    steps = manifest.setdefault("steps", {})
    if step_str not in steps:
        steps[step_str] = {"status": "pending", "artifacts": []}
    
    steps[step_str]["status"] = "success"
    if files_generated:
        # artifacts는 파일 경로 문자열 배열
        artifacts = steps[step_str].get("artifacts", [])
        artifacts.extend([str(p) for p in files_generated])
        steps[step_str]["artifacts"] = list(dict.fromkeys(artifacts))
    
    # completed_steps 업데이트 (호환용)
    completed = manifest.get("completed_steps", [])
    if step_str not in completed:
        completed.append(step_str)
    manifest["completed_steps"] = completed
    
    manifest["files_generated"] = list(dict.fromkeys(manifest.get("files_generated", []) + files_generated))
    manifest["current_step"] = step_str
    
    # 모든 필수 step 성공 여부로 전체 상태 결정 (step1~step3)
    required_steps = ["step1", "step2", "step3"]
    if all(steps.get(s, {}).get("status") == "success" for s in required_steps):
        manifest["status"] = "success"
        manifest["run_state"] = "SUCCESS"  # 처음문서_v1.2
    else:
        manifest["status"] = RunStatus.RUNNING.value
        manifest["run_state"] = "RUNNING"  # 처음문서_v1.2
    
    return _save_manifest(run_id, manifest, base_dir)


def mark_step_failed(
    run_id: str,
    step: RunStep,
    error_message: str,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Step 실패 표시
    
    Args:
        run_id: 실행 ID
        step: 실패한 단계
        error_message: 에러 메시지
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: 업데이트된 Manifest 데이터
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Run manifest not found: {run_id}")
    
    step_str = step.value
    steps = manifest.setdefault("steps", {})
    if step_str not in steps:
        steps[step_str] = {"status": "pending", "artifacts": []}
    steps[step_str]["status"] = "fail"
    
    manifest["current_step"] = step_str
    manifest["status"] = RunStatus.FAILED.value
    manifest["run_state"] = "FAILED"  # 처음문서_v1.2
    manifest["last_error"] = {
        "step": step_str,
        "message": error_message,
        "timestamp": datetime.now().isoformat()
    }
    
    return _save_manifest(run_id, manifest, base_dir)


def find_run_by_input_hash(input_hash: str, base_dir: Optional[Path] = None) -> Optional[str]:
    """
    입력 해시로 기존 Run 찾기
    
    Args:
        input_hash: 입력 데이터 해시
        base_dir: 기본 디렉토리
    
    Returns:
        str: run_id (없으면 None)
    """
    if base_dir is None:
        backend_dir = Path(__file__).resolve().parent.parent
        output_root = backend_dir / "output"
    else:
        output_root = base_dir / "output"
    
    runs_dir = get_runs_root(base_dir)
    if not runs_dir.exists():
        return None
    
    # 모든 run 디렉토리 검색
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        
        manifest = load_run_manifest(run_dir.name, base_dir)
        if manifest and manifest.get("input_hash") == input_hash:
            # 완료된 run은 재사용하지 않음 (새 run 생성)
            if manifest.get("status") == RunStatus.COMPLETED.value:
                continue
            return run_dir.name
    
    return None


def is_step_completed(run_id: str, step: RunStep, base_dir: Optional[Path] = None) -> bool:
    """
    Step 완료 여부 확인
    
    Args:
        run_id: 실행 ID
        step: 확인할 단계
        base_dir: 기본 디렉토리
    
    Returns:
        bool: 완료 여부
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        return False
    
    return manifest.get("steps", {}).get(step.value, {}).get("status") == "success"


def get_resume_step(run_id: str, base_dir: Optional[Path] = None) -> Optional[RunStep]:
    """
    재개할 Step 확인
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        RunStep: 재개할 단계 (없으면 None)
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        return None
    
    if manifest.get("status") in [RunStatus.COMPLETED.value, "success"]:
        return None
    
    steps_info = manifest.get("steps", {})
    order = [RunStep.STEP2, RunStep.STEP3]
    for step in order:
        if steps_info.get(step.value, {}).get("status") != "success":
            return step
    
    return None

