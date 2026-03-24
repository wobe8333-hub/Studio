"""
3단계: Scene JSON 고정 스펙 변환

기능:
- Step 2 결과(구형 스키마)를 Step 3 완전 고정 스펙으로 변환
- scenes_fixed.json 생성
- 고정 스펙 검증
- Step 3 리포트 생성
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from backend.utils.output_paths import (
    get_output_dirs,
    get_step3_file_paths
)


def convert_scenes_to_fixed(
    input_scenes_path: str,
    output_scenes_fixed_path: str,
    style_profile: str = "default"
) -> Dict[str, Any]:
    """
    구형 scenes.json을 고정 스펙 scenes_fixed.json으로 변환
    
    Args:
        input_scenes_path: 입력 파일 경로 (구형 scenes.json)
        output_scenes_fixed_path: 출력 파일 경로 (scenes_fixed.json)
        style_profile: 스타일 프로필 이름 (기본: "default")
    
    Returns:
        Dict: 변환된 고정 스펙 데이터
    """
    # 입력 파일 로드
    input_path = Path(input_scenes_path)
    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_scenes_path}")
    
    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    
    # run_id 추출 (파일명 또는 데이터에서)
    run_id = input_data.get("run_id")
    if not run_id:
        # 파일명에서 추출 시도
        filename = input_path.stem
        if "_scenes" in filename:
            run_id = filename.replace("_scenes", "")
        else:
            raise ValueError("run_id를 찾을 수 없습니다")
    
    scenes_raw = input_data.get("scenes", [])
    scenes_converted = []
    
    for scene in scenes_raw:
        # scene_index
        scene_index = scene.get("scene_index", 0)
        
        # scene_type (type 필드에서 변환)
        scene_type_raw = scene.get("type", "body")
        scene_type_map = {
            "intro": "intro",
            "body": "body",
            "transition": "transition",
            "conclusion": "conclusion"
        }
        scene_type = scene_type_map.get(scene_type_raw, "body")
        
        # narration (narration 우선, 없으면 text)
        narration = scene.get("narration") or scene.get("text", "")
        if not narration:
            narration = ""
        
        # visual_prompt
        visual_prompt = scene.get("visual_prompt", "cinematic, professional, calm, informative, high quality, detailed, 4k")
        
        # duration_sec
        duration_sec = scene.get("duration_sec", 6)
        
        # source_range (source_index_range에서 변환, start/end 형식)
        source_index_range = scene.get("source_index_range", {})
        start = source_index_range.get("start", 0)
        end = source_index_range.get("end", 0)
        
        # sentence_indices가 있으면 그것을 사용하여 범위 계산
        sentence_indices = scene.get("sentence_indices", [])
        if sentence_indices and len(sentence_indices) > 0:
            start = min(sentence_indices)
            end = max(sentence_indices)
        
        source_range = {
            "start": start,
            "end": end
        }
        
        # Step 3 완전 고정 스펙 형식으로 변환 (7개 필드만)
        scene_converted = {
            "scene_index": scene_index,
            "scene_type": scene_type,
            "narration": narration,
            "visual_prompt": visual_prompt,
            "duration_sec": duration_sec,
            "source_range": source_range,
            "style_profile": style_profile
        }
        
        scenes_converted.append(scene_converted)
    
    # Step 3 완전 고정 스펙 형식의 최종 데이터
    result = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "spec_version": "fixed_v1",
        "scenes": scenes_converted
    }
    
    # 파일 저장
    output_path = Path(output_scenes_fixed_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


def validate_fixed_spec(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    고정 스펙 검증
    
    Args:
        data: 검증할 데이터
    
    Returns:
        Tuple[bool, List[str], List[str]]: (검증 통과 여부, missing_required, forbidden_found)
    """
    errors = []
    missing_required = []
    forbidden_found = []
    
    # 최상위 필드 검증
    if "run_id" not in data:
        errors.append("run_id 필드가 없습니다")
    if "scenes" not in data:
        errors.append("scenes 필드가 없습니다")
        return False, missing_required, forbidden_found
    
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        errors.append("scenes는 리스트여야 합니다")
        return False, missing_required, forbidden_found
    
    if len(scenes) == 0:
        errors.append("scenes가 비어있습니다")
        return False, missing_required, forbidden_found
    
    # 고정 스펙 필드만 허용 (7개)
    allowed_fields = {
        "scene_index",
        "scene_type",
        "narration",
        "visual_prompt",
        "duration_sec",
        "source_range",
        "style_profile"
    }
    
    # 금지 필드
    forbidden_fields_set = {
        "scene_number",
        "type",
        "text",
        "approx_chars",
        "sentence_count",
        "sentence_indices",
        "source_index_range",
        "structure"
    }
    
    valid_scene_types = ["intro", "body", "transition", "conclusion"]
    
    for idx, scene in enumerate(scenes):
        scene_num = idx + 1
        
        # 허용되지 않은 필드 검사
        scene_fields = set(scene.keys())
        forbidden_in_scene = scene_fields & forbidden_fields_set
        if forbidden_in_scene:
            forbidden_found.extend([f"씬 {scene_num}: {field}" for field in forbidden_in_scene])
        
        # 필수 필드 검증 (7개)
        required_fields = [
            "scene_index",
            "scene_type",
            "narration",
            "visual_prompt",
            "duration_sec",
            "source_range",
            "style_profile"
        ]
        
        for field in required_fields:
            if field not in scene:
                missing_required.append(f"씬 {scene_num}: {field}")
                errors.append(f"씬 {scene_num}: {field} 필드가 없습니다")
        
        # scene_index 검증 (1부터 순차 증가)
        scene_index = scene.get("scene_index")
        if scene_index != scene_num:
            errors.append(f"씬 {scene_num}: scene_index가 {scene_index}입니다 (예상: {scene_num})")
        
        # scene_type 검증
        scene_type = scene.get("scene_type")
        if scene_type not in valid_scene_types:
            errors.append(f"씬 {scene_num}: scene_type이 유효하지 않습니다 ({scene_type})")
        
        # narration 검증 (빈 문자열이 아닌지)
        narration = scene.get("narration", "")
        if not narration or not narration.strip():
            errors.append(f"씬 {scene_num}: narration이 비어있습니다")
        
        # source_range 검증
        source_range = scene.get("source_range")
        if not isinstance(source_range, dict):
            errors.append(f"씬 {scene_num}: source_range는 객체여야 합니다")
        else:
            if "start" not in source_range or "end" not in source_range:
                errors.append(f"씬 {scene_num}: source_range에 start 또는 end가 없습니다")
            else:
                start = source_range.get("start")
                end = source_range.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    errors.append(f"씬 {scene_num}: source_range의 start와 end는 정수여야 합니다")
                elif start > end:
                    errors.append(f"씬 {scene_num}: source_range의 start({start})가 end({end})보다 큽니다")
        
        # duration_sec 검증
        duration_sec = scene.get("duration_sec")
        if not isinstance(duration_sec, (int, float)) or duration_sec <= 0:
            errors.append(f"씬 {scene_num}: duration_sec는 양수여야 합니다")
        
        # UTF-8 검증 (narration과 visual_prompt)
        try:
            narration.encode("utf-8")
            visual_prompt = scene.get("visual_prompt", "")
            visual_prompt.encode("utf-8")
        except UnicodeEncodeError as e:
            errors.append(f"씬 {scene_num}: UTF-8 인코딩 오류: {str(e)}")
    
    return len(errors) == 0, missing_required, forbidden_found


def check_utf8_encoding(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    파일이 UTF-8로 읽히는지 확인
    
    Args:
        file_path: 파일 경로
    
    Returns:
        Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read()
        return True, None
    except UnicodeDecodeError as e:
        return False, f"UTF-8 디코딩 실패: {str(e)}"
    except Exception as e:
        return False, f"파일 읽기 실패: {str(e)}"


def generate_step3_report(
    input_file: str,
    output_file: str,
    fixed_data: Dict[str, Any],
    validation_result: Tuple[bool, List[str], List[str]],
    encoding_check: Tuple[bool, Optional[str]],
    run_id: str,
    output_dir: Path
) -> Path:
    """
    Step 3 검증 리포트 생성
    
    Args:
        input_file: 입력 파일 경로 (구형 scenes.json)
        output_file: 출력 파일 경로 (scenes_fixed.json)
        fixed_data: 고정 스펙 데이터
        validation_result: 검증 결과 (is_valid, missing_required, forbidden_found)
        encoding_check: UTF-8 인코딩 검증 결과
        run_id: 실행 ID
        output_dir: 출력 디렉토리 (backend/output)
    
    Returns:
        Path: 저장된 리포트 파일 경로
    """
    # 통합 유틸 사용
    file_paths = get_step3_file_paths(run_id, output_dir.parent if output_dir.name == "output" else output_dir)
    report_path = file_paths["report_json"]
    
    is_valid, missing_required, forbidden_found = validation_result
    encoding_valid, encoding_error = encoding_check
    scenes = fixed_data.get("scenes", [])
    
    # 전체 상태 결정
    overall_status = "success" if (is_valid and encoding_valid) else "fail"
    
    report = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "step": 3,
        "status": overall_status,
        "input_file": str(input_file),
        "output_file": str(output_file),
        "counts": {
            "scenes_count": len(scenes)
        },
        "schema_check": {
            "missing_required": missing_required,
            "forbidden_found": forbidden_found,
            "passed": is_valid
        },
        "encoding_check": {
            "utf8_readable": encoding_valid,
            "error": encoding_error
        },
        "summary": {
            "scene_types": {
                "intro": sum(1 for s in scenes if s.get("scene_type") == "intro"),
                "body": sum(1 for s in scenes if s.get("scene_type") == "body"),
                "transition": sum(1 for s in scenes if s.get("scene_type") == "transition"),
                "conclusion": sum(1 for s in scenes if s.get("scene_type") == "conclusion")
            },
            "total_duration_sec": sum(s.get("duration_sec", 0) for s in scenes)
        },
        "errors": [] if overall_status == "success" else [
            f"스키마 검증 실패: {len(missing_required)}개 필수 필드 누락, {len(forbidden_found)}개 금지 필드 발견" if not is_valid else "",
            encoding_error if not encoding_valid else ""
        ]
    }
    
    # 파일 저장 (UTF-8, BOM 없음)
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_path


# 하위 호환성을 위한 기존 함수들 (기존 코드 유지)
def convert_step2_to_step3_spec(
    step2_data: Dict[str, Any],
    run_id: str
) -> Dict[str, Any]:
    """기존 함수 (하위 호환성 유지)"""
    scenes_raw = step2_data.get("scenes", [])
    scenes_converted = []
    
    for scene in scenes_raw:
        scene_index = scene.get("scene_index", 0)
        scene_type_raw = scene.get("type", "body")
        scene_type_map = {
            "intro": "intro",
            "body": "body",
            "transition": "transition",
            "conclusion": "conclusion"
        }
        scene_type = scene_type_map.get(scene_type_raw, "body")
        narration = scene.get("narration") or scene.get("text", "")
        visual_prompt = scene.get("visual_prompt", "cinematic, professional, calm, informative, high quality, detailed, 4k")
        duration_sec = scene.get("duration_sec", 6)
        
        source_index_range = scene.get("source_index_range", {})
        start = source_index_range.get("start", 0)
        end = source_index_range.get("end", 0)
        
        sentence_indices = scene.get("sentence_indices", [])
        if sentence_indices and len(sentence_indices) > 0:
            start = min(sentence_indices)
            end = max(sentence_indices)
        
        source_range = {"start": start, "end": end}
        
        scene_converted = {
            "scene_index": scene_index,
            "scene_type": scene_type,
            "narration": narration,
            "visual_prompt": visual_prompt,
            "duration_sec": duration_sec,
            "source_range": source_range,
            "style_profile": "default"
        }
        scenes_converted.append(scene_converted)
    
    result = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "spec_version": "fixed_v1",
        "scenes": scenes_converted
    }
    
    return result


def load_step2_result(run_id: str, output_dir: Path) -> Optional[Dict[str, Any]]:
    """기존 함수 (하위 호환성 유지)"""
    plans_dir = output_dir / "plans"
    scenes_path = plans_dir / f"{run_id}_scenes.json"
    
    if not scenes_path.exists():
        return None
    
    try:
        with open(scenes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Step 2 결과 파일 로드 실패: {str(e)}")
