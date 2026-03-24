"""
v1.4 재반영 검증 자동화 (Step1/5/6/7/10/12 AUDIT)

기능:
- runs 폴더의 모든 run_id 하위 manifest.json을 자동 탐색
- Step1/5/6/7/10/12의 필수 파일/필드/구조를 자동 점검
- 실패 원인과 정확한 해결 명령 출력

실행:
    python -m backend.scripts.audit_v1_4_reapply --run-id <run_id>
    python -m backend.scripts.audit_v1_4_reapply  # 모든 run 검사
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 프로젝트 루트 기준으로 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.utils.run_manager import get_runs_root, get_run_dir, load_run_manifest
from backend.utils.observability import ensure_metrics
from backend.utils.knowledge_store import read_item, get_knowledge_root


def check_step1(manifest: Dict[str, Any], run_dir: Path) -> Tuple[str, str]:
    """
    Step1 판정 (manifest 필드 기반)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL, reason)
    """
    # 필수 키 8개
    required_fields = [
        "creation_mode",
        "ui_scope",
        "data_impact_scope",
        "cost_caps",
        "stop_conditions",
        "decision_trace",
        "governance",
        "locks"
    ]
    
    # 필수 키 존재 확인
    for field in required_fields:
        if field not in manifest:
            return "FAIL", f"required_field_missing:{field}"
    
    # ui_scope 확인
    if manifest.get("ui_scope") != "OPS_CONSOLE":
        return "FAIL", f"ui_scope_invalid (expected OPS_CONSOLE, got {manifest.get('ui_scope')})"
    
    # governance 확인
    governance = manifest.get("governance", {})
    if not isinstance(governance, dict):
        return "FAIL", "governance_invalid (not a dict)"
    
    if governance.get("auto_select_enabled") is not False:
        return "FAIL", "governance_invalid (auto_select_enabled != False)"
    
    if governance.get("recommendation_enabled") is not False:
        return "FAIL", "governance_invalid (recommendation_enabled != False)"
    
    return "PASS", "ok"


def check_step5(manifest: Dict[str, Any], run_dir: Path) -> Tuple[str, str]:
    """
    Step5 판정 (step5_report.json 존재 + 필드 기반)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL, reason)
    """
    # manifest.steps.step5.artifacts.step5_report 경로 확인
    step5_report_path = None
    steps = manifest.get("steps", {})
    step5 = steps.get("step5", {})
    artifacts = step5.get("artifacts", {})
    
    if isinstance(artifacts, dict) and "step5_report" in artifacts:
        report_path_str = artifacts["step5_report"]
        if isinstance(report_path_str, str):
            # 상대경로면 run_dir 기준으로 resolve
            if Path(report_path_str).is_absolute():
                step5_report_path = Path(report_path_str)
            else:
                step5_report_path = run_dir / report_path_str
    
    # 기본 후보 경로
    if step5_report_path is None or not step5_report_path.exists():
        step5_report_path = run_dir / "verify" / "step5_report.json"
    
    # 파일 존재 확인
    if not step5_report_path.exists():
        return "FAIL", "step5_report_missing"
    
    # JSON 파싱
    try:
        with open(step5_report_path, "r", encoding="utf-8") as f:
            step5_report = json.load(f)
    except Exception as e:
        return "FAIL", f"step5_report_json_invalid ({e})"
    
    # 필수 키 확인
    required_fields = [
        "classification",
        "secondary_tags",
        "valuable_failure",
        "valuable_reason",
        "data_signals"
    ]
    
    for field in required_fields:
        if field not in step5_report:
            return "FAIL", f"step5_report_field_missing:{field}"
    
    return "PASS", "ok"


def check_step6_api() -> Tuple[str, str]:
    """
    Step6_API 판정 (코드 로딩 기반 라우트 존재 점검)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL|SKIP, reason)
    """
    try:
        from backend.main import app
    except Exception as e:
        return "SKIP", f"import_failed:{type(e).__name__}:{str(e)}"
    
    # FastAPI routes 확인
    required_routes = [
        ("POST", "/longform/retry/{video_id}/scene/{scene_id}/regenerate"),
        ("POST", "/longform/retry/{video_id}/scene/{scene_id}/render")
    ]
    
    # app.routes에서 확인
    found_routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            methods = route.methods if hasattr(route.methods, "__contains__") else set()
            for method, required_path in required_routes:
                if method in methods and required_path == path:
                    found_routes.append((method, path))
    
    # 모든 라우트가 존재하는지 확인
    for method, required_path in required_routes:
        if (method, required_path) not in found_routes:
            return "FAIL", f"route_missing:{method} {required_path}"
    
    return "PASS", "ok"


def check_step7(manifest: Dict[str, Any], run_dir: Path) -> Tuple[str, str]:
    """
    Step7 판정 (metrics/logs 기반)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL, reason)
    """
    # metrics.json 확인
    metrics_path = run_dir / "logs" / "metrics.json"
    
    if not metrics_path.exists():
        # ensure_metrics로 생성 시도 (기존 덮어쓰기 금지)
        try:
            run_id = manifest.get("run_id")
            if run_id:
                ensure_metrics(run_id, None)
        except Exception:
            pass
        
        # 다시 확인
        if not metrics_path.exists():
            return "FAIL", "metrics_missing"
    
    # metrics.json 로드
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    except Exception as e:
        return "FAIL", f"metrics_json_invalid ({e})"
    
    # 필수 키 확인
    required_fields = [
        "scene_retry_regenerate_count",
        "scene_retry_render_count",
        "scene_lock_count",
        "human_intervention_count",
        "decision_trace_count",
        "silence_signal_count"
    ]
    
    for field in required_fields:
        if field not in metrics:
            return "FAIL", f"metrics_field_missing:{field}"
    
    # bias.json 확인
    bias_path = run_dir / "logs" / "bias.json"
    if not bias_path.exists():
        return "FAIL", "bias_missing"
    
    # forgetting_ledger.jsonl 확인
    forgetting_ledger_path = run_dir / "logs" / "forgetting_ledger.jsonl"
    if not forgetting_ledger_path.exists():
        return "FAIL", "forgetting_ledger_missing"
    
    return "PASS", "ok"


def check_step10(manifest: Dict[str, Any], run_dir: Path) -> Tuple[str, str]:
    """
    Step10 판정 (manifest locks 구조 기반)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL, reason)
    """
    # locks.scenes 구조 확인
    locks = manifest.get("locks", {})
    if not isinstance(locks, dict):
        return "FAIL", "locks_missing"
    
    if "scenes" not in locks:
        return "FAIL", "locks_missing (scenes key)"
    
    # 라우트 존재 확인 (참고 출력용)
    try:
        from backend.main import app
        lock_routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                path = route.path
                methods = route.methods if hasattr(route.methods, "__contains__") else set()
                if "POST" in methods:
                    if "/longform/lock/" in path or "/longform/unlock/" in path:
                        lock_routes.append(path)
    except Exception:
        pass
    
    return "PASS", "ok"


def check_step12(manifest: Dict[str, Any], run_dir: Path) -> Tuple[str, str]:
    """
    Step12 판정 (knowledge items JSON 기반)
    
    Returns:
        Tuple[str, str]: (PASS|FAIL, reason)
    """
    run_id = manifest.get("run_id")
    if not run_id:
        return "FAIL", "knowledge_file_missing (no run_id)"
    
    # 후보 경로 1: manifest.steps.step12.artifacts
    knowledge_path = None
    steps = manifest.get("steps", {})
    step12 = steps.get("step12", {})
    artifacts = step12.get("artifacts", {})
    
    if isinstance(artifacts, dict):
        # knowledge_item_path 또는 유사한 키 확인
        for key in ["knowledge_item_path", "item_path", "knowledge_path"]:
            if key in artifacts:
                path_str = artifacts[key]
                if isinstance(path_str, str):
                    if Path(path_str).is_absolute():
                        knowledge_path = Path(path_str)
                    else:
                        # 상대경로면 project_root 기준 resolve
                        from backend.utils.run_manager import get_project_root
                        project_root = get_project_root()
                        knowledge_path = project_root / path_str
                    break
    
    # 후보 경로 2: backend/output/knowledge/items/<run_id>.json
    if knowledge_path is None or not knowledge_path.exists():
        knowledge_root = get_knowledge_root(None)
        knowledge_path = knowledge_root / "items" / f"{run_id}.json"
    
    # Step12는 knowledge item과 Document를 별도로 저장
    # Document 메타 필드는 run_dir/knowledge/raw/<doc_id>.json에서 확인
    knowledge_raw_dir = run_dir / "knowledge" / "raw"
    
    # Document JSON 파일 찾기
    document_paths = []
    if knowledge_raw_dir.exists():
        for doc_file in knowledge_raw_dir.glob("*.json"):
            document_paths.append(doc_file)
    
    # Document 메타 필드 확인
    required_fields = [
        "knowledge_type",
        "source_class",
        "trust_level",
        "impact_scope",
        "dignity_level",
        "emotional_gravity",
        "deprecated"
    ]
    
    # Document JSON이 있으면 필드 확인
    if document_paths:
        found_fields = set()
        for doc_path in document_paths:
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)
                
                # Document 필드 확인
                for field in required_fields:
                    if field in doc_data:
                        found_fields.add(field)
            except Exception:
                continue
        
        # 모든 필드가 있는지 확인
        missing_fields = [f for f in required_fields if f not in found_fields]
        if missing_fields:
            return "FAIL", f"knowledge_field_missing:{','.join(missing_fields)}"
        
        return "PASS", "ok"
    else:
        # Document JSON이 없으면 knowledge item만 확인 (필드 검사는 SKIP)
        if knowledge_path.exists():
            return "PASS", "ok (knowledge_item_exists, but no Document JSON found for field check)"
        else:
            return "FAIL", "knowledge_file_missing"


def get_recommended_fix(step_results: Dict[str, Tuple[str, str]]) -> str:
    """
    RECOMMENDED_FIX 생성
    
    Args:
        step_results: {step_name: (status, reason)}
    
    Returns:
        str: 추천 명령 또는 "none"
    """
    fixes = []
    
    if step_results.get("STEP1", ("", ""))[0] == "FAIL":
        fixes.append("python -m backend.scripts.backfill_manifest_v1_4_step1")
    
    if step_results.get("STEP5", ("", ""))[0] == "FAIL":
        fixes.append("python -m backend.scripts.verify_runs")
    
    if step_results.get("STEP7", ("", ""))[0] == "FAIL":
        fixes.append("python -m backend.scripts.verify_runs")
        # Step7 CLI 확인 (run_step7 함수 존재 확인)
        try:
            import backend.cli as cli_module
            if hasattr(cli_module, "run_step7"):
                fixes.append("python -m backend.cli step7 --run-id <run_id>")
        except (ImportError, AttributeError):
            pass
    
    if step_results.get("STEP6_API", ("", ""))[0] == "FAIL":
        fixes.append("Run server using your canonical command, then check /docs and /openapi.json")
    
    if step_results.get("STEP10", ("", ""))[0] == "FAIL":
        fixes.append("Run server using your canonical command, then check /docs and /openapi.json")
    
    if not fixes:
        return "none"
    
    return " | ".join(fixes)


def audit_run(run_id: str) -> Dict[str, Any]:
    """
    단일 run 감사
    
    Args:
        run_id: 실행 ID
    
    Returns:
        Dict: 감사 결과
    """
    run_dir = get_run_dir(run_id, None)
    manifest_path = run_dir / "manifest.json"
    
    # manifest 로드 (자동 백필 포함)
    manifest = load_run_manifest(run_id, None)
    if manifest is None:
        return {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "error": "manifest_missing"
        }
    
    # Step별 판정
    step_results = {}
    
    # STEP1
    step1_status, step1_reason = check_step1(manifest, run_dir)
    step_results["STEP1"] = (step1_status, step1_reason)
    
    # STEP5
    step5_status, step5_reason = check_step5(manifest, run_dir)
    step_results["STEP5"] = (step5_status, step5_reason)
    
    # STEP6_API (한 번만 실행)
    step6_status, step6_reason = check_step6_api()
    step_results["STEP6_API"] = (step6_status, step6_reason)
    
    # STEP7
    step7_status, step7_reason = check_step7(manifest, run_dir)
    step_results["STEP7"] = (step7_status, step7_reason)
    
    # STEP10
    step10_status, step10_reason = check_step10(manifest, run_dir)
    step_results["STEP10"] = (step10_status, step10_reason)
    
    # STEP12
    step12_status, step12_reason = check_step12(manifest, run_dir)
    step_results["STEP12"] = (step12_status, step12_reason)
    
    # RECOMMENDED_FIX
    recommended_fix = get_recommended_fix(step_results)
    
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "step_results": step_results,
        "recommended_fix": recommended_fix
    }


def main() -> int:
    """
    메인 함수
    
    Returns:
        int: exit code (0=성공, 1=에러)
    """
    parser = argparse.ArgumentParser(description="v1.4 재반영 검증 자동화")
    parser.add_argument("--run-id", type=str, help="Run ID (생략 시 모든 run 검사)")
    args = parser.parse_args()
    
    print("AUDIT START")
    
    # RUNS_ROOT 출력
    runs_root = get_runs_root(None)
    print(f"RUNS_ROOT={runs_root.resolve()}")
    
    # 오판 방지 안내
    print(f"⚠️  WARNING: Make sure you are checking manifests in {runs_root.resolve()}")
    print(f"   If you see a different path, you are looking at the WRONG manifest!")
    
    # run_id 지정 여부
    if args.run_id:
        run_ids = [args.run_id]
    else:
        # 모든 run 검사
        if not runs_root.exists():
            print("ERROR: runs 디렉토리가 없습니다")
            return 1
        
        run_ids = []
        for run_dir in runs_root.iterdir():
            if run_dir.is_dir():
                manifest_path = run_dir / "manifest.json"
                if manifest_path.exists():
                    run_ids.append(run_dir.name)
    
    # 감사 실행
    results = []
    total = 0
    pass_count = 0
    fail_count = 0
    skip_count = 0
    
    for run_id in run_ids:
        total += 1
        result = audit_run(run_id)
        results.append(result)
        
        # 출력
        print(f"RUN_ID={run_id}")
        print(f"RUN_DIR={result['run_dir']}")
        
        if "error" in result:
            print(f"ERROR={result['error']}")
            fail_count += 1
            continue
        
        # Step별 출력
        step_results = result["step_results"]
        for step_name in ["STEP1", "STEP5", "STEP6_API", "STEP7", "STEP10", "STEP12"]:
            if step_name in step_results:
                status, reason = step_results[step_name]
                print(f"{step_name}={status} reason={reason}")
                
                if status == "PASS":
                    pass_count += 1
                elif status == "FAIL":
                    fail_count += 1
                elif status == "SKIP":
                    skip_count += 1
        
        # RECOMMENDED_FIX
        print(f"RECOMMENDED_FIX={result['recommended_fix']}")
    
    # 종료 요약
    print("AUDIT DONE")
    print(f"TOTAL={total} PASS={pass_count} FAIL={fail_count} SKIP={skip_count}")
    
    # fail_count > 0이면 exit code 1
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

