"""
Step5 검증 규칙 (Step6/v3 진입 Gate)

검증 기준:
- manifest.json 단일 진실만 사용
- 파일 존재 여부로 PASS/FAIL 판정 금지
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from backend.utils.run_manager import get_run_dir, load_run_manifest, _atomic_write_json
from backend.utils.failure_taxonomy import classify_failure
from backend.schemas.failure_taxonomy import FailureTaxonomy, normalize_failure_taxonomy
from backend.utils.meaning_failure import classify_meaning_failure


def verify_step5(
    run_id: str,
    base_dir: Optional[Path] = None
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Step5 검증 (Step6/v3 진입 Gate)
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Tuple[bool, List[str], Dict[str, Any]]: (PASS 여부, 실패 사유 리스트, 상세 정보)
    """
    failures: List[str] = []
    details: Dict[str, Any] = {
        "run_id": run_id,
        "step1_status": None,
        "step2_status": None,
        "step3_status": None,
        "step4_status": None,
        "scenes_count": 0,
        "step4_artifacts": [],
        "failed_at": None
    }
    
    # 1) manifest.json 존재 확인
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        failures.append("manifest_missing")
        details["failed_at"] = {"step": "manifest", "reason": "manifest_missing"}
        return False, failures, details
    
    steps = manifest.get("steps", {})
    
    # 2) Step1~Step4 상태 검증
    step1_status = steps.get("step1", {}).get("status")
    step2_status = steps.get("step2", {}).get("status")
    step3_status = steps.get("step3", {}).get("status")
    step4_status = steps.get("step4", {}).get("status")
    
    details["step1_status"] = step1_status
    details["step2_status"] = step2_status
    details["step3_status"] = step3_status
    details["step4_status"] = step4_status
    
    if step1_status != "success":
        failures.append(f"step1_status_not_success: {step1_status}")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step1", "reason": f"status={step1_status}"}
    
    if step2_status != "success":
        failures.append(f"step2_status_not_success: {step2_status}")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step2", "reason": f"status={step2_status}"}
    
    if step3_status != "success":
        failures.append(f"step3_status_not_success: {step3_status}")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step3", "reason": f"status={step3_status}"}
    
    if step4_status != "success":
        failures.append(f"step4_status_not_success: {step4_status}")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step4", "reason": f"status={step4_status}"}
    
    # Step1~4 중 하나라도 실패하면 여기서 종료
    if failures:
        return False, failures, details
    
    # 3) Step3 산출물 검증
    run_dir = get_run_dir(run_id, base_dir)
    scenes_fixed_path = run_dir / "step3" / "scenes_fixed.json"
    
    # scenes_fixed.json 존재 확인 (참고용, 판정에는 사용 안 함)
    if not scenes_fixed_path.exists():
        # 참고 로그만 남기고 판정에는 영향 없음
        pass
    
    # scenes_fixed.json 로드 (manifest에 기록된 정보 사용)
    try:
        with open(scenes_fixed_path, "r", encoding="utf-8") as f:
            scenes_fixed_data = json.load(f)
        
        scenes = scenes_fixed_data.get("scenes", [])
        scenes_count = len(scenes)
        details["scenes_count"] = scenes_count
        
        # scene 개수 >= 1
        if scenes_count < 1:
            failures.append("scenes_count_less_than_1")
            if details["failed_at"] is None:
                details["failed_at"] = {"step": "step3", "reason": "scenes_count < 1"}
        else:
            # scene id 연속성 검증 (1..N)
            scene_indices = []
            for scene in scenes:
                scene_index = scene.get("scene_index")
                if scene_index is not None:
                    scene_indices.append(scene_index)
            
            scene_indices.sort()
            expected_indices = list(range(1, scenes_count + 1))
            
            if scene_indices != expected_indices:
                failures.append(f"scene_indices_not_continuous: got {scene_indices}, expected {expected_indices}")
                if details["failed_at"] is None:
                    details["failed_at"] = {"step": "step3", "reason": "scene_indices_not_continuous"}
    
    except Exception as e:
        failures.append(f"scenes_fixed_json_load_error: {str(e)}")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step3", "reason": f"json_load_error: {str(e)}"}
    
    # 4) Step4 산출물 정합성 검증
    step4 = steps.get("step4", {})
    step4_artifacts = step4.get("artifacts", [])
    details["step4_artifacts"] = step4_artifacts
    
    # final_video 존재 확인
    final_video_found = False
    scene_videos_count = 0
    
    # scene_video 패턴: scene_001.mp4, scene_002.mp4 등
    scene_video_pattern = re.compile(r'scene_\d+\.mp4$', re.IGNORECASE)
    
    for artifact in step4_artifacts:
        artifact_str = str(artifact)
        if "final_" in artifact_str and artifact_str.endswith(".mp4"):
            final_video_found = True
        elif scene_video_pattern.search(artifact_str):
            scene_videos_count += 1
    
    if not final_video_found:
        failures.append("step4_final_video_missing")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "step4", "reason": "final_video_missing"}
    
    # final_video 경로 문자열이 비어있지 않은지 확인
    final_video_paths = [a for a in step4_artifacts if "final_" in str(a) and str(a).endswith(".mp4")]
    if final_video_paths:
        final_video_path = str(final_video_paths[0])
        if not final_video_path or final_video_path.strip() == "":
            failures.append("step4_final_video_path_empty")
            if details["failed_at"] is None:
                details["failed_at"] = {"step": "step4", "reason": "final_video_path_empty"}
    
    # scene 개수 == step4.artifacts.scene_videos 개수
    if scenes_count > 0:
        if scene_videos_count != scenes_count:
            failures.append(f"scene_videos_count_mismatch: expected {scenes_count}, got {scene_videos_count}")
            if details["failed_at"] is None:
                details["failed_at"] = {"step": "step4", "reason": f"scene_videos_count_mismatch: {scene_videos_count} != {scenes_count}"}
    
    # 5) repro/environment 필수 필드 확인 (처음문서_v1.2)
    if "repro" not in manifest or not manifest.get("repro", {}).get("repro_key"):
        failures.append("repro_missing")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "manifest", "reason": "repro_missing"}
    
    if "environment" not in manifest or not manifest.get("environment", {}).get("python_version"):
        failures.append("environment_missing")
        if details["failed_at"] is None:
            details["failed_at"] = {"step": "manifest", "reason": "environment_missing"}
    
    # v1.4 확장: data_signals 추가 (피드백8 반영)
    # Silence Signal 규칙: Step3 결과(scene 리스트)가 존재하지만 모든 scene의 narration/shot_prompt 등이 빈 문자열이거나 극단적으로 짧은 경우
    data_signals = {
        "silence_detected": False,
        "silence_reason": None
    }
    
    try:
        scenes_count = details.get("scenes_count", 0)
        if scenes_fixed_path.exists() and scenes_count > 0:
            with open(scenes_fixed_path, "r", encoding="utf-8") as f:
                scenes_fixed_data = json.load(f)
            
            scenes = scenes_fixed_data.get("scenes", [])
            if scenes:
                # 모든 scene의 narration/shot_prompt 등이 빈 문자열이거나 1~2자인 경우 감지
                all_silent = True
                for scene in scenes:
                    narration = scene.get("narration", "") or scene.get("text", "")
                    visual_prompt = scene.get("visual_prompt", "") or scene.get("shot_prompt", "")
                    
                    narration_len = len(narration.strip()) if narration else 0
                    visual_prompt_len = len(visual_prompt.strip()) if visual_prompt else 0
                    
                    # 극단적으로 짧은 경우 (1~2자) 또는 빈 문자열
                    if narration_len > 2 and visual_prompt_len > 2:
                        all_silent = False
                        break
                
                if all_silent:
                    data_signals["silence_detected"] = True
                    data_signals["silence_reason"] = "모든 scene의 narration/visual_prompt가 빈 문자열이거나 극단적으로 짧음"
    except Exception:
        # silence detection 실패는 무시 (판정에는 영향 없음)
        pass
    
    details["data_signals"] = data_signals
    
    # 6) failure_summary 생성 (처음문서_v1.2, v1.4 확장)
    failure_summary = None
    if failures:
        # 첫 번째 실패를 기준으로 분류 (details 전달하여 확장 태깅)
        first_failure = failures[0]
        failed_at = (details or {}).get("failed_at", {}) or {}
        failed_step = failed_at.get("step", "unknown") if isinstance(failed_at, dict) else "unknown"
        failure_summary = classify_failure(failed_step, first_failure, manifest, details)
    else:
        # 성공 시에도 기본 failure_summary 생성 (정책 입력으로서)
        failure_summary = {
            "primary_category": "NO_FAILURES",
            "severity": "soft",
            "policy_hint": "no_failures",
            "failed_step": None,
            "secondary_tags": [],
            "valuable_failure": False,
            "valuable_reason": None
        }
    
    # failure_summary 값 보장 (절대 공백/None 금지, v1.4 확장 필드 포함)
    if not failure_summary.get("primary_category"):
        failure_summary["primary_category"] = FailureTaxonomy.STRUCTURE.value
    else:
        # primary_category를 Enum으로 정규화
        taxonomy = normalize_failure_taxonomy(failure_summary["primary_category"])
        failure_summary["primary_taxonomy"] = taxonomy.value
        failure_summary["primary_category"] = taxonomy.value  # 하위 호환 유지
    
    if not failure_summary.get("severity"):
        failure_summary["severity"] = "hard"
    if not failure_summary.get("policy_hint"):
        failure_summary["policy_hint"] = "unknown_failure"
    if "failed_step" not in failure_summary:
        failure_summary["failed_step"] = None
    if "secondary_tags" not in failure_summary:
        failure_summary["secondary_tags"] = []
    if "valuable_failure" not in failure_summary:
        failure_summary["valuable_failure"] = False
    if "valuable_reason" not in failure_summary:
        failure_summary["valuable_reason"] = None
    
    # primary_taxonomy 필드 보장 (Enum 기반)
    if "primary_taxonomy" not in failure_summary:
        taxonomy = normalize_failure_taxonomy(failure_summary.get("primary_category", FailureTaxonomy.STRUCTURE.value))
        failure_summary["primary_taxonomy"] = taxonomy.value
    
    # v6-Step5: meaning_failure 추가 (항상 포함)
    first_failure = failures[0] if failures else ""
    failed_at = (details or {}).get("failed_at", {}) or {}
    step_name = failed_at.get("step") if isinstance(failed_at, dict) else None
    
    # 에러가 없어도 meaning_failure는 항상 존재해야 함 (기본값: LOW_SIGNAL)
    if not first_failure:
        # 에러가 없는 경우 기본값으로 LOW_SIGNAL 설정
        meaning_failure_value = "LOW_SIGNAL"
    else:
        meaning_failure = classify_meaning_failure(first_failure, manifest=manifest, step=step_name)
        meaning_failure_value = getattr(meaning_failure, "value", str(meaning_failure))
    
    failure_summary["meaning_failure"] = meaning_failure_value
    details["failure_summary"] = failure_summary
    
    # 최종 판정
    is_pass = len(failures) == 0
    
    # v6-Step5: manifest에 meaning_failure 기록 (항상)
    try:
        from datetime import datetime
        
        run_dir = get_run_dir(run_id, base_dir)
        manifest_path = run_dir / "manifest.json"
        
        if manifest_path.exists():
            # manifest 재로드 (최신 상태)
            current_manifest = load_run_manifest(run_id, base_dir)
            if current_manifest:
                steps = current_manifest.setdefault("steps", {})
                step_obj = steps.setdefault("v6_step5_meaning_failure_taxonomy", {
                    "status": "pending",
                    "artifacts": [],
                    "errors": [],
                    "warnings": []
                })
                
                # status 설정
                step_obj["status"] = "success" if is_pass else "failed"
                
                # artifact 추가 (항상)
                artifact = {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "meaning_failure": meaning_failure_value,
                    "source": "verify_step5_rules"
                }
                step_obj.setdefault("artifacts", []).append(artifact)
                
                # manifest 저장
                _atomic_write_json(manifest_path, current_manifest)
    except Exception as e:
        # manifest 기록 실패는 경고만 (검증 자체는 계속 진행)
        pass
    
    return is_pass, failures, details

