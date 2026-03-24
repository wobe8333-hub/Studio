"""
Quality Gate - 각 Step 종료 시 품질 검사

기능:
- Step2 품질 게이트
- Step3 품질 게이트
- Step4 품질 게이트
"""

from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


def check_step2_quality(
    parsed_data: Dict[str, Any],
    report_data: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    Step2 품질 게이트 검사
    
    요구사항:
    - sentences >= 5
    - scenes >= 3
    
    Args:
        parsed_data: parse_longform_script()의 반환값
        report_data: Step2 리포트 데이터 (선택)
    
    Returns:
        Tuple[bool, List[str]]: (통과 여부, 실패 사유 목록)
    """
    errors = []
    
    sentences = parsed_data.get("sentences", [])
    scenes = parsed_data.get("scenes", [])
    
    # sentences >= 5
    if len(sentences) < 5:
        errors.append(f"문장 수가 부족합니다 (요구: 5개 이상, 실제: {len(sentences)}개)")
    
    # scenes >= 3
    if len(scenes) < 3:
        errors.append(f"씬 수가 부족합니다 (요구: 3개 이상, 실제: {len(scenes)}개)")
    
    return len(errors) == 0, errors


def check_step3_quality(
    fixed_data: Dict[str, Any],
    validation_result: Tuple[bool, List[str], List[str]],
    encoding_check: Tuple[bool, Optional[str]]
) -> Tuple[bool, List[str]]:
    """
    Step3 품질 게이트 검사
    
    요구사항:
    - scenes_fixed.json 존재
    - 고정 Scene JSON 스펙 100% 통과
    
    Args:
        fixed_data: 고정 스펙 데이터
        validation_result: 검증 결과 (is_valid, missing_required, forbidden_found)
        encoding_check: UTF-8 인코딩 검증 결과
    
    Returns:
        Tuple[bool, List[str]]: (통과 여부, 실패 사유 목록)
    """
    errors = []
    
    is_valid, missing_required, forbidden_found = validation_result
    encoding_valid, encoding_error = encoding_check
    
    # scenes_fixed.json 존재 확인
    scenes = fixed_data.get("scenes", [])
    if not scenes:
        errors.append("scenes_fixed.json에 씬이 없습니다")
    
    # 고정 스펙 검증 통과 확인
    if not is_valid:
        if missing_required:
            errors.append(f"필수 필드 누락: {', '.join(missing_required)}")
        if forbidden_found:
            errors.append(f"금지 필드 발견: {', '.join(forbidden_found)}")
    
    # UTF-8 인코딩 확인
    if not encoding_valid:
        errors.append(f"UTF-8 인코딩 검증 실패: {encoding_error}")
    
    return len(errors) == 0, errors


def check_step4_quality(
    final_video_path: Path,
    scenes: Any
) -> Tuple[bool, List[str]]:
    """
    Step4 품질 게이트 검사
    
    요구사항:
    - final video duration >= sum(scene.duration_sec) * 0.9
    
    Args:
        final_video_path: 최종 비디오 파일 경로
        scenes: 씬 리스트 또는 dict (타입 안전하게 처리)
    
    Returns:
        Tuple[bool, List[str]]: (통과 여부, 실패 사유 목록)
    """
    errors = []
    
    # 비디오 파일 존재 확인
    if not final_video_path.exists():
        errors.append("최종 비디오 파일이 생성되지 않았습니다")
        return False, errors
    
    # scenes 입력 정규화
    scenes_normalized = None
    
    if isinstance(scenes, dict):
        # dict인 경우 list로 변환
        try:
            scenes_normalized = list(scenes.values())
        except Exception as e:
            errors.append(f"scenes dict 변환 실패: {str(e)}")
            return False, errors
    elif isinstance(scenes, (list, tuple)):
        # list/tuple인 경우 그대로 사용
        scenes_normalized = list(scenes)
    else:
        # 그 외 타입이면 오류
        scenes_type = type(scenes).__name__
        errors.append(f"scenes 타입 오류: 예상 타입은 list/dict/tuple, 실제 타입은 {scenes_type}")
        return False, errors
    
    # scenes_normalized가 비어있으면 오류
    if not scenes_normalized:
        errors.append("scenes가 비어있습니다")
        return False, errors
    
    # 각 요소가 dict인지 확인하고 expected_duration 계산
    expected_duration = 0.0
    valid_scenes = []
    
    for idx, scene in enumerate(scenes_normalized):
        if not isinstance(scene, dict):
            scene_type = type(scene).__name__
            errors.append(f"scenes 요소 타입 오류: index={idx}, type={scene_type}")
            continue
        
        # duration_sec 안전하게 float 변환
        duration_sec = scene.get("duration_sec")
        try:
            if duration_sec is None or duration_sec == "":
                duration_sec = 0.0
            else:
                duration_sec = float(duration_sec)
        except (ValueError, TypeError):
            duration_sec = 0.0
        
        expected_duration += duration_sec
        valid_scenes.append(scene)
    
    # scenes 타입 오류/요소 타입 오류가 1개라도 있으면 FAIL
    if errors:
        return False, errors
    
    # valid_scenes가 없으면 오류
    if not valid_scenes:
        errors.append("유효한 scene이 없습니다")
        return False, errors
    
    # 실제 비디오 길이 확인 (ffprobe 사용) - 예외 금지
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(final_video_path)
            ],
            capture_output=True,
            text=True,
            check=False  # check=False로 변경하여 예외 방지
        )
        
        if result.returncode != 0:
            # ffprobe 실패 시 에러 추가 (예외는 던지지 않음)
            stderr_msg = result.stderr.strip() if result.stderr else "unknown error"
            errors.append(f"비디오 길이 검증 실패 (ffprobe 오류): {stderr_msg}")
        else:
            try:
                actual_duration = float(result.stdout.strip())
                
                # 최소 길이 확인 (90% 이상)
                min_duration = expected_duration * 0.9
                if actual_duration < min_duration:
                    errors.append(
                        f"비디오 길이가 부족합니다 "
                        f"(요구: {min_duration:.2f}초 이상, 실제: {actual_duration:.2f}초)"
                    )
            except (ValueError, TypeError) as e:
                errors.append(f"비디오 길이 파싱 실패: {str(e)}")
    
    except Exception as e:
        # 예외를 던지지 않고 에러 메시지만 추가
        errors.append(f"비디오 길이 검증 중 예외 발생: {str(e)}")
    
    return len(errors) == 0, errors

