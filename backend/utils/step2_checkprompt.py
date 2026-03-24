"""
Step2 결과 자동 검증 모듈

기능:
- Step2 실행 결과에 대한 자동 검증
- checkruns 폴더에 검증 결과 저장
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


def load_default_checkprompt(backend_dir: Path) -> Dict[str, Any]:
    """
    기본 검증 설정 로드 (파일 기반)
    
    Args:
        backend_dir: 백엔드 디렉토리 (Path 객체)
    
    Returns:
        Dict: 기본 검증 설정 데이터
    """
    # 파일에서 로드 시도
    prompt_file = backend_dir / "resources" / "checkprompt" / "step2_checkprompt.txt"
    
    if prompt_file.exists():
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        except Exception as e:
            print(f"[STEP2_VALIDATION] WARN: 검증 설정 파일 로드 실패, 기본값 사용: {e}")
            prompt_text = None
    else:
        prompt_text = None
    
    # 기본 검증 설정 구조
    default_prompt = {
        "version": "v2",
        "description": "Step2 기본 검증 설정",
        "source": str(prompt_file) if prompt_file.exists() else "built-in",
        "checks": [
            {
                "id": "file_generation",
                "name": "파일 생성 확인",
                "description": "필수 파일 4개가 모두 생성되었는지 확인",
                "required": True
            },
            {
                "id": "encoding_utf8",
                "name": "UTF-8 인코딩 확인",
                "description": "모든 파일이 UTF-8로 저장되었는지 확인",
                "required": True
            },
            {
                "id": "korean_content",
                "name": "한글 내용 확인",
                "description": "한글이 정상적으로 포함되어 있는지 확인",
                "required": True
            },
            {
                "id": "scene_structure",
                "name": "씬 구조 확인",
                "description": "씬 구조가 올바르게 생성되었는지 확인 (intro/body/conclusion)",
                "required": True
            },
            {
                "id": "placeholder_check",
                "name": "Placeholder 검증",
                "description": "'string' placeholder가 존재하지 않는지 확인",
                "required": True
            },
            {
                "id": "sentence_count",
                "name": "문장 수 확인",
                "description": "문장 수가 최소 3개 이상인지 확인 (권장: 20개 이상)",
                "required": False
            }
        ]
    }
    
    # 파일 내용이 있으면 추가
    if prompt_text:
        default_prompt["file_content"] = prompt_text
    
    return default_prompt


def verify_step2_outputs(
    run_id: str,
    output_dir: Path,
    created_files: Dict[str, str],
    parsed_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step2 출력 파일 검증
    
    Args:
        run_id: 실행 ID
        output_dir: 출력 디렉토리
        created_files: 생성된 파일 경로 딕셔너리
        parsed_data: 파싱된 데이터
    
    Returns:
        Dict: 검증 결과
    """
    check_results = []
    all_passed = True
    
    # 1. 파일 생성 확인
    file_check = {
        "id": "file_generation",
        "name": "파일 생성 확인",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    required_files = ["script_path", "sentences_path", "scenes_path", "report_path"]
    missing_files = []
    
    for file_key in required_files:
        file_path_str = created_files.get(file_key)
        if file_path_str:
            file_path = Path(file_path_str)
            if file_path.exists():
                file_check["details"][file_key] = {
                    "exists": True,
                    "size": file_path.stat().st_size,
                    "path": str(file_path)
                }
            else:
                file_check["details"][file_key] = {"exists": False, "path": file_path_str}
                missing_files.append(file_key)
        else:
            file_check["details"][file_key] = {"exists": False, "path": None}
            missing_files.append(file_key)
    
    if missing_files:
        file_check["status"] = "FAIL"
        file_check["message"] = f"누락된 파일: {', '.join(missing_files)}"
        all_passed = False
    else:
        file_check["message"] = "모든 필수 파일이 생성되었습니다."
    
    check_results.append(file_check)
    
    # 2. UTF-8 인코딩 확인 (한글 깨짐 포함)
    encoding_check = {
        "id": "encoding_utf8",
        "name": "UTF-8 인코딩 확인",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    encoding_errors = []
    corruption_warnings = []
    
    for file_key, file_path_str in created_files.items():
        if file_key == "_timings":
            continue
        if file_path_str and Path(file_path_str).exists():
            try:
                with open(file_path_str, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 한글 깨짐 문자 체크 (, ??)
                    has_corruption = '' in content or '??' in content
                    # 한글이 포함되어 있는지 확인
                    has_korean = any('\uAC00' <= char <= '\uD7A3' for char in content)
                    
                    encoding_check["details"][file_key] = {
                        "readable": True,
                        "has_korean": has_korean,
                        "has_corruption": has_corruption,
                        "size": len(content)
                    }
                    
                    if has_corruption:
                        corruption_warnings.append(file_key)
            except UnicodeDecodeError as e:
                encoding_check["details"][file_key] = {
                    "readable": False,
                    "error": str(e)
                }
                encoding_errors.append(file_key)
            except Exception as e:
                encoding_check["details"][file_key] = {
                    "readable": False,
                    "error": str(e)
                }
                encoding_errors.append(file_key)
    
    if encoding_errors:
        encoding_check["status"] = "FAIL"
        encoding_check["message"] = f"인코딩 오류 파일: {', '.join(encoding_errors)}"
        all_passed = False
    elif corruption_warnings:
        encoding_check["status"] = "WARN"
        encoding_check["message"] = f"한글 깨짐 문자 발견 (경고): {', '.join(corruption_warnings)}"
    else:
        encoding_check["message"] = "모든 파일이 UTF-8로 정상 저장되었습니다."
    
    check_results.append(encoding_check)
    
    # 3. 한글 내용 확인
    korean_check = {
        "id": "korean_content",
        "name": "한글 내용 확인",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    script_path_str = created_files.get("script_path")
    if script_path_str and Path(script_path_str).exists():
        try:
            with open(script_path_str, "r", encoding="utf-8") as f:
                script_content = f.read()
                korean_chars = [char for char in script_content if '\uAC00' <= char <= '\uD7A3']
                korean_check["details"]["script"] = {
                    "has_korean": len(korean_chars) > 0,
                    "korean_count": len(korean_chars),
                    "total_chars": len(script_content)
                }
                
                if len(korean_chars) == 0:
                    korean_check["status"] = "FAIL"
                    korean_check["message"] = "스크립트에 한글이 포함되어 있지 않습니다."
                    all_passed = False
                else:
                    korean_check["message"] = f"한글 {len(korean_chars)}자가 정상적으로 포함되어 있습니다."
        except Exception as e:
            korean_check["status"] = "FAIL"
            korean_check["message"] = f"스크립트 파일 읽기 실패: {str(e)}"
            all_passed = False
    else:
        korean_check["status"] = "FAIL"
        korean_check["message"] = "스크립트 파일이 없습니다."
        all_passed = False
    
    check_results.append(korean_check)
    
    # 4. 씬 구조 확인
    scene_check = {
        "id": "scene_structure",
        "name": "씬 구조 확인",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    scenes = parsed_data.get("scenes", [])
    structure = parsed_data.get("structure", {})
    
    if len(scenes) == 0:
        scene_check["status"] = "FAIL"
        scene_check["message"] = "씬이 생성되지 않았습니다."
        all_passed = False
    else:
        scene_check["details"]["scene_count"] = len(scenes)
        scene_check["details"]["scenes"] = []
        
        # intro/body/conclusion 구조 확인
        intro_count = len(structure.get("intro", []))
        body_count = len(structure.get("body", []))
        conclusion_count = len(structure.get("conclusion", []))
        
        scene_check["details"]["structure"] = {
            "intro": intro_count,
            "body": body_count,
            "conclusion": conclusion_count
        }
        
        # 구조가 없으면 경고
        if intro_count == 0 and body_count == 0 and conclusion_count == 0:
            scene_check["status"] = "WARN"
            scene_check["message"] = "씬은 생성되었지만 intro/body/conclusion 구조가 없습니다."
        else:
            scene_check["message"] = f"{len(scenes)}개 씬이 정상적으로 생성되었습니다. (intro: {intro_count}, body: {body_count}, conclusion: {conclusion_count})"
        
        for scene in scenes[:5]:  # 최대 5개만
            scene_info = {
                "scene_index": scene.get("scene_index", 0),
                "type": scene.get("type", "unknown"),
                "has_narration": bool(scene.get("narration") or scene.get("text")),
                "has_visual_prompt": bool(scene.get("visual_prompt")),
                "duration_sec": scene.get("duration_sec", 0)
            }
            scene_check["details"]["scenes"].append(scene_info)
    
    check_results.append(scene_check)
    
    # 5. Placeholder 검증
    placeholder_check = {
        "id": "placeholder_check",
        "name": "Placeholder 검증",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    placeholder_found = []
    
    # script.txt에서 placeholder 체크
    script_path_str = created_files.get("script_path")
    if script_path_str and Path(script_path_str).exists():
        try:
            with open(script_path_str, "r", encoding="utf-8") as f:
                script_content = f.read()
                if '"string"' in script_content or script_content.strip().lower() == "string":
                    placeholder_found.append("script.txt")
        except Exception:
            pass
    
    # scenes.json에서 placeholder 체크
    scenes_path_str = created_files.get("scenes_path")
    if scenes_path_str and Path(scenes_path_str).exists():
        try:
            with open(scenes_path_str, "r", encoding="utf-8") as f:
                scenes_data = json.load(f)
                scenes = scenes_data.get("scenes", [])
                for scene in scenes:
                    narration = scene.get("narration", "") or scene.get("text", "")
                    overlay_text = scene.get("overlay_text", "")
                    visual_prompt = scene.get("visual_prompt", "")
                    
                    if '"string"' in narration or narration.strip().lower() == "string":
                        placeholder_found.append(f"scenes.json scene_{scene.get('scene_index', 0)} narration")
                    if overlay_text and ('"string"' in overlay_text or overlay_text.strip().lower() == "string"):
                        placeholder_found.append(f"scenes.json scene_{scene.get('scene_index', 0)} overlay_text")
                    if '"string"' in visual_prompt or visual_prompt.strip().lower() == "string":
                        placeholder_found.append(f"scenes.json scene_{scene.get('scene_index', 0)} visual_prompt")
        except Exception:
            pass
    
    if placeholder_found:
        placeholder_check["status"] = "FAIL"
        placeholder_check["message"] = f"Placeholder 'string' 발견: {', '.join(placeholder_found)}"
        all_passed = False
    else:
        placeholder_check["message"] = "Placeholder가 발견되지 않았습니다."
    
    placeholder_check["details"]["placeholder_found"] = placeholder_found
    check_results.append(placeholder_check)
    
    # 6. 문장 수 확인 (선택)
    sentence_check = {
        "id": "sentence_count",
        "name": "문장 수 확인",
        "status": "PASS",
        "message": "",
        "details": {}
    }
    
    sentences = parsed_data.get("sentences", [])
    sentence_check["details"]["sentence_count"] = len(sentences)
    
    if len(sentences) < 3:
        sentence_check["status"] = "FAIL"
        sentence_check["message"] = f"문장 수가 부족합니다 ({len(sentences)}개). 최소 3개 필요."
        all_passed = False
    elif len(sentences) < 20:
        sentence_check["status"] = "WARN"
        sentence_check["message"] = f"문장 수가 적습니다 ({len(sentences)}개). 권장: 20개 이상."
    else:
        sentence_check["message"] = f"문장 수가 충분합니다 ({len(sentences)}개)."
    
    check_results.append(sentence_check)
    
    # 전체 상태 결정 (OK/WARN/FAIL)
    has_fail = any(check.get("status") == "FAIL" for check in check_results)
    has_warn = any(check.get("status") == "WARN" for check in check_results)
    
    if has_fail:
        overall_status = "FAIL"
    elif has_warn:
        overall_status = "WARN"
    else:
        overall_status = "OK"
    
    return {
        "run_id": run_id,
        "check_time": datetime.now().isoformat(),
        "overall_status": overall_status,
        "checks": check_results
    }


def save_checkprompt_results(
    run_id: str,
    output_dir: Path,
    check_prompt: Dict[str, Any],
    check_results: Dict[str, Any]
) -> Dict[str, str]:
    """
    검증 결과를 checkruns 폴더에 저장
    
    Args:
        run_id: 실행 ID
        output_dir: 출력 디렉토리
        check_prompt: 사용된 검증 설정
        check_results: 검증 결과
    
    Returns:
        Dict[str, str]: 생성된 파일 경로들
    """
    checkruns_dir = output_dir / "checkruns" / run_id
    checkruns_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = {}
    
    # 1. validation_config_used.txt 저장
    prompt_path = checkruns_dir / "validation_config_used.txt"
    with open(prompt_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("=" * 60 + "\n")
        f.write("사용된 검증 설정\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"버전: {check_prompt.get('version', 'unknown')}\n")
        f.write(f"설명: {check_prompt.get('description', '')}\n\n")
        f.write("체크 항목:\n")
        for check in check_prompt.get("checks", []):
            f.write(f"  - [{check.get('id')}] {check.get('name')}\n")
            f.write(f"    설명: {check.get('description', '')}\n")
            f.write(f"    필수: {'예' if check.get('required', False) else '아니오'}\n\n")
    
    created_files["prompt_path"] = str(prompt_path.resolve())
    
    # 2. check_results.json 저장
    results_json_path = checkruns_dir / "check_results.json"
    with open(results_json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(check_results, f, ensure_ascii=False, indent=2)
    
    created_files["results_json_path"] = str(results_json_path.resolve())
    
    # 3. check_results.txt 저장 (사람이 읽기 좋은 형태)
    results_txt_path = checkruns_dir / "check_results.txt"
    with open(results_txt_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("=" * 60 + "\n")
        f.write("Step2 결과 검증\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"실행 ID: {run_id}\n")
        f.write(f"검증 시간: {check_results.get('check_time', '')}\n")
        f.write(f"전체 상태: {check_results.get('overall_status', 'UNKNOWN')}\n\n")
        
        f.write("-" * 60 + "\n")
        f.write("체크 항목별 결과\n")
        f.write("-" * 60 + "\n\n")
        
        for check in check_results.get("checks", []):
            status = check.get("status", "UNKNOWN")
            status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
            
            f.write(f"{status_symbol} [{check.get('id')}] {check.get('name')}\n")
            f.write(f"   상태: {status}\n")
            f.write(f"   메시지: {check.get('message', '')}\n")
            
            details = check.get("details", {})
            if details:
                f.write(f"   상세:\n")
                for key, value in details.items():
                    if isinstance(value, dict):
                        f.write(f"     - {key}:\n")
                        for k, v in value.items():
                            f.write(f"       {k}: {v}\n")
                    else:
                        f.write(f"     - {key}: {value}\n")
            
            f.write("\n")
    
    created_files["results_txt_path"] = str(results_txt_path.resolve())
    
    return created_files
