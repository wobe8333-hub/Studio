"""
2단계: 롱폼 스크립트 구조화 결과 Export

기능:
- 구조화된 스크립트 데이터를 파일로 저장
- scripts, plans, reports 폴더에 파일 생성
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from backend.utils.encoding_utils import (
    ensure_utf8_string,
    validate_before_save,
    log_encoding_step,
    has_korean,
    detect_mojibox
)
from backend.utils.output_paths import (
    get_output_dirs,
    get_step2_file_paths,
    get_encoding_log_path
)

# UTF-8 런타임 강제 설정
def _force_utf8_runtime():
    """Python 런타임 UTF-8 강제 설정"""
    # PYTHONUTF8 환경변수 설정
    if "PYTHONUTF8" not in os.environ:
        os.environ["PYTHONUTF8"] = "1"
    
    # stdout/stderr 인코딩 재설정 (가능할 때)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        # reconfigure가 지원되지 않는 경우 무시
        pass

# 모듈 로드 시 UTF-8 강제
_force_utf8_runtime()


def export_step2_results(
    parsed_data: Dict[str, Any],
    run_id: str,
    output_dir: Path,
    start_time: Optional[datetime] = None,
    encoding_warnings: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    2단계 결과를 파일로 저장
    
    Args:
        parsed_data: parse_longform_script()의 반환값
        run_id: 실행 ID
        output_dir: 출력 디렉토리 (backend/output)
        start_time: 시작 시간 (선택)
    
    Returns:
        Dict[str, str]: 생성된 파일 경로들
    """
    created_files = {}
    timings = {}
    
    if start_time:
        timings["start_time"] = start_time.isoformat()
    
    step_start = datetime.now()
    
    try:
        # 출력 디렉토리 구조 생성 (통합 유틸 사용)
        dirs = get_output_dirs(output_dir.parent if output_dir.name == "output" else output_dir)
        verify_dir = dirs["verify"]
        plans_dir = dirs["plans"]
        reports_dir = dirs["reports"]
        
        # 파일 경로 생성 (통합 유틸 사용)
        file_paths = get_step2_file_paths(run_id, output_dir.parent if output_dir.name == "output" else output_dir)
        script_path = file_paths["script_txt"]
        sentences_path = file_paths["sentences_txt"]
        scenes_path = file_paths["scenes_json"]
        report_path = file_paths["report_json"]
        
        # 경로를 문자열로 변환 (UTF-8 보장)
        script_path_str = str(script_path.resolve())
        sentences_path_str = str(sentences_path.resolve())
        scenes_path_str = str(scenes_path.resolve())
        report_path_str = str(report_path.resolve())
        
        # 상대경로 계산 (output_dir 기준)
        try:
            script_path_rel = str(script_path.relative_to(output_dir))
            sentences_path_rel = str(sentences_path.relative_to(output_dir))
            scenes_path_rel = str(scenes_path.relative_to(output_dir))
            report_path_rel = str(report_path.relative_to(output_dir))
        except ValueError:
            # 상대경로 계산 실패 시 절대경로만 사용
            script_path_rel = script_path_str
            sentences_path_rel = sentences_path_str
            scenes_path_rel = scenes_path_str
            report_path_rel = report_path_str
        
        print(f"[STEP2_SCRIPT] 생성 예정 파일:")
        print(f"[STEP2_SCRIPT]   1. {script_path_str}")
        print(f"[STEP2_SCRIPT]   2. {sentences_path_str}")
        print(f"[STEP2_SCRIPT]   3. {scenes_path_str}")
        print(f"[STEP2_SCRIPT]   4. {report_path_str}")
        
        # 인코딩 추적 로그 파일 경로 생성 (통합 유틸 사용)
        encoding_log_path = get_encoding_log_path(run_id, output_dir.parent if output_dir.name == "output" else output_dir)
        
        # 원본 스크립트 인코딩 검증 및 복구
        original_script = parsed_data.get("original_script", "")
        log_encoding_step("INPUT_ORIGINAL_SCRIPT", original_script, encoding_log_path)
        
        # 인코딩 보장 처리
        original_script_fixed, script_diagnostic = ensure_utf8_string(original_script, "original_script")
        if script_diagnostic.get("encoding_fallback_used"):
            print(f"[STEP2_SCRIPT] WARN: 원본 스크립트 인코딩 복구 사용됨: {script_diagnostic.get('encoding_fallback_used')}")
        
        # 저장 전 검증
        is_valid, error_msg = validate_before_save(original_script_fixed, "original_script")
        if not is_valid:
            raise ValueError(f"원본 스크립트 저장 전 검증 실패: {error_msg}")
        
        # 1. verify/{run_id}_script.txt 생성
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        script_path.write_text(
            original_script_fixed,
            encoding="utf-8",
            newline="\n"
        )
        
        log_encoding_step("SAVED_SCRIPT_TXT", original_script_fixed, encoding_log_path)
        
        # 파일 생성 후 경로 저장 (exists 체크 불필요 - write_text가 성공하면 파일 존재)
        created_files["script_path"] = script_path_str
        file_size = script_path.stat().st_size
        print(f"[STEP2_SCRIPT] ✓ script.txt 생성 완료: {script_path_str} (크기: {file_size} bytes)")
        
        # 2. verify/{run_id}_sentences.txt 생성 (한 줄 = 한 단위)
        sentences_path.parent.mkdir(parents=True, exist_ok=True)
        
        sentences = parsed_data.get("sentences", [])
        paragraphs = parsed_data.get("paragraphs", [])
        
        # 문장이 너무 적으면 (20줄 미만) 분해 규칙 보완
        if len(sentences) < 20:
            print(f"[STEP2_SCRIPT] WARN: 문장 수가 적습니다 ({len(sentences)}개). 분해 규칙을 보완합니다.")
            # 문장을 더 세밀하게 분해 (쉼표 기준 추가 분해)
            enhanced_sentences = []
            for sent in sentences:
                text = sent["text"]
                # 쉼표로 추가 분해
                parts = text.split("，")  # 한글 쉼표
                if len(parts) == 1:
                    parts = text.split(",")  # 영문 쉼표
                
                for idx, part in enumerate(parts):
                    part = part.strip()
                    if part:
                        enhanced_sentences.append({
                            "index": len(enhanced_sentences),
                            "text": part,
                            "length": len(part)
                        })
            
            if len(enhanced_sentences) > len(sentences):
                sentences = enhanced_sentences
                print(f"[STEP2_SCRIPT] 문장 수 보완: {len(sentences)}개")
        
        # 문장 인코딩 검증 및 복구
        sentences_fixed = []
        for sent in sentences:
            sent_text = sent.get("text", "")
            log_encoding_step(f"SENTENCE_{sent.get('index', 0)}", sent_text, encoding_log_path)
            
            # 인코딩 보장 처리
            sent_text_fixed, sent_diagnostic = ensure_utf8_string(sent_text, f"sentence_{sent.get('index', 0)}")
            if sent_diagnostic.get("encoding_fallback_used"):
                print(f"[STEP2_SCRIPT] WARN: 문장 {sent.get('index', 0)} 인코딩 복구 사용됨")
            
            # 저장 전 검증
            is_valid, error_msg = validate_before_save(sent_text_fixed, f"sentence_{sent.get('index', 0)}")
            if not is_valid:
                raise ValueError(f"문장 {sent.get('index', 0)} 저장 전 검증 실패: {error_msg}")
            
            sentences_fixed.append({
                "index": sent.get("index", 0),
                "text": sent_text_fixed,
                "length": len(sent_text_fixed)
            })
        
        # 한 줄 = 한 단위 형식으로 저장
        with open(sentences_path, "w", encoding="utf-8", newline="\n") as f:
            # 문장 단위 (한 줄에 하나씩)
            for sent in sentences_fixed:
                f.write(f"{sent['text']}\n")
        
        log_encoding_step("SAVED_SENTENCES_TXT", "\n".join(s["text"] for s in sentences_fixed[:5]), encoding_log_path)
        
        # 파일 생성 후 경로 저장
        created_files["sentences_path"] = sentences_path_str
        file_size = sentences_path.stat().st_size
        print(f"[STEP2_SCRIPT] ✓ sentences.txt 생성 완료: {sentences_path_str} (크기: {file_size} bytes)")
        
        # 3. plans/{run_id}_scenes.json 생성 (Step 3 완전 고정 스펙으로 직접 생성)
        scenes_path.parent.mkdir(parents=True, exist_ok=True)
        
        # scenes 데이터 준비 (Step 3 완전 고정 스펙 형식으로 직접 생성)
        scenes_raw = parsed_data.get("scenes", [])
        scenes_processed = []
        for scene in scenes_raw:
            # Step 3 완전 고정 스펙 형식으로 변환
            scene_index = scene.get("scene_index", 0)
            scene_type_raw = scene.get("type", "body")
            
            # scene_type 변환
            scene_type_map = {
                "intro": "intro",
                "body": "body",
                "transition": "transition",
                "conclusion": "conclusion"
            }
            scene_type = scene_type_map.get(scene_type_raw, "body")
            
            # narration (narration 우선, 없으면 text)
            narration_raw = scene.get("narration") or scene.get("text", "")
            log_encoding_step(f"SCENE_{scene_index}_NARRATION_RAW", narration_raw, encoding_log_path)
            
            # 인코딩 보장 처리
            narration, narration_diagnostic = ensure_utf8_string(narration_raw, f"scene_{scene_index}_narration")
            if narration_diagnostic.get("encoding_fallback_used"):
                print(f"[STEP2_SCRIPT] WARN: 씬 {scene_index} narration 인코딩 복구 사용됨")
            
            # 저장 전 검증
            is_valid, error_msg = validate_before_save(narration, f"scene_{scene_index}_narration")
            if not is_valid:
                raise ValueError(f"씬 {scene_index} narration 저장 전 검증 실패: {error_msg}")
            
            log_encoding_step(f"SCENE_{scene_index}_NARRATION_FIXED", narration, encoding_log_path)
            
            # visual_prompt
            visual_prompt = scene.get("visual_prompt", "cinematic, professional, calm, informative, high quality, detailed, 4k")
            
            # duration_sec
            duration_sec = scene.get("duration_sec", max(6, min(12, scene.get("approx_chars", scene.get("length", 100)) // 20)))
            
            # source_range (source_index_range에서 변환)
            source_index_range = scene.get("source_index_range", {})
            start_sentence = source_index_range.get("start", 0)
            end_sentence = source_index_range.get("end", 0)
            
            # sentence_indices가 있으면 그것을 사용하여 범위 계산
            sentence_indices = scene.get("sentence_indices", [])
            if sentence_indices and len(sentence_indices) > 0:
                start_sentence = min(sentence_indices)
                end_sentence = max(sentence_indices)
            
            source_range = {
                "start_sentence": start_sentence,
                "end_sentence": end_sentence
            }
            
            # Step 3 완전 고정 스펙 형식으로 생성
            scene_processed = {
                "scene_index": scene_index,
                "scene_type": scene_type,
                "narration": narration,
                "visual_prompt": visual_prompt,
                "duration_sec": duration_sec,
                "source_range": source_range,
                "style_profile": "longform-default"
            }
            scenes_processed.append(scene_processed)
        
        # Step 3 완전 고정 스펙 형식 (structure 제거)
        scenes_data = {
            "run_id": run_id,
            "generated_at": datetime.now().isoformat(),
            "scenes": scenes_processed
        }
        with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)
        
        # 파일 생성 후 경로 저장
        created_files["scenes_path"] = scenes_path_str
        file_size = scenes_path.stat().st_size
        scene_count = len(scenes_data['scenes'])
        print(f"[STEP2_SCRIPT] ✓ scenes.json 생성 완료: {scenes_path_str} ({scene_count}개 씬, 크기: {file_size} bytes)")
        
        # Step 3 변환 자동 실행 (scenes_fixed.json 생성)
        try:
            from backend.utils.step3_converter import (
                convert_scenes_to_fixed,
                validate_fixed_spec,
                check_utf8_encoding,
                generate_step3_report
            )
            
            # scenes_fixed.json 경로
            scenes_fixed_path = plans_dir / f"{run_id}_scenes_fixed.json"
            
            # Step 3 변환 실행
            fixed_data = convert_scenes_to_fixed(
                str(scenes_path),
                str(scenes_fixed_path),
                style_profile="default"
            )
            
            print(f"[STEP2_SCRIPT] ✓ Step 3 변환 완료: scenes_fixed.json 생성 ({len(fixed_data.get('scenes', []))}개 씬)")
            
            # 검증
            validation_result = validate_fixed_spec(fixed_data)
            is_valid, missing_required, forbidden_found = validation_result
            
            # UTF-8 인코딩 검증
            encoding_check = check_utf8_encoding(str(scenes_fixed_path))
            
            # 리포트 생성
            step3_report_path = generate_step3_report(
                str(scenes_path),
                str(scenes_fixed_path),
                fixed_data,
                validation_result,
                encoding_check,
                run_id,
                output_dir
            )
            
            print(f"[STEP2_SCRIPT] ✓ Step 3 리포트 생성 완료: {step3_report_path}")
            created_files["scenes_fixed_path"] = str(scenes_fixed_path)
            created_files["step3_report_path"] = str(step3_report_path)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[STEP2_SCRIPT] ⚠ Step 3 변환 실패 (무시): {str(e)}\n{error_trace}")
        
        # 4. reports/{run_id}_step2_report.json 생성
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 이미 위에서 가져온 데이터 재사용 (중복 접근 제거)
        # sentences는 위에서 이미 가져왔고, scenes는 scenes_raw로 가져왔으므로 재사용
        structure = parsed_data.get("structure", {})
        paragraphs = parsed_data.get("paragraphs", [])
        
        # 파일 존재 여부는 이미 생성했으므로 모두 True (중복 체크 제거)
        file_status = {
            "script_txt": True,
            "sentences_txt": True,
            "scenes_json": True
        }
        
        # 타이밍 계산 (리포트에 포함)
        step_end = datetime.now()
        timings["end_time"] = step_end.isoformat()
        if start_time:
            timings["duration_ms"] = round((step_end - start_time).total_seconds() * 1000, 2)
        
        # 구조 정보 미리 계산 (중복 접근 제거)
        # scenes는 scenes_raw를 사용, sentences는 위에서 이미 가져옴
        intro_count = len(structure.get("intro", []))
        body_count = len(structure.get("body", []))
        transition_count = len(structure.get("transitions", []))
        conclusion_count = len(structure.get("conclusion", []))
        sentence_count = len(sentences)
        paragraph_count = len(paragraphs)
        scene_count = len(scenes_processed)  # scenes_raw 대신 scenes_processed 사용
        
        report_data = {
            "run_id": run_id,
            "step": 2,
            "status": "success",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "sentence_count": sentence_count,
                "paragraph_count": paragraph_count,
                "scene_count": scene_count,
                "structure": {
                    "intro_count": intro_count,
                    "body_count": body_count,
                    "transition_count": transition_count,
                    "conclusion_count": conclusion_count
                }
            },
            "generated_files": [
                script_path_str,
                sentences_path_str,
                scenes_path_str,
                report_path_str
            ],
            "generated_files_relative": [
                script_path_rel,
                sentences_path_rel,
                scenes_path_rel,
                report_path_rel
            ],
            "file_status": file_status,
            "counts": {
                "sentences": sentence_count,
                "paragraphs": paragraph_count,
                "scenes": scene_count
            },
            "timings": timings,
            "warnings": encoding_warnings if encoding_warnings else [],
            "errors": []
        }
        
        # 문장 수가 적으면 경고 추가 (sentence_count 재사용)
        if sentence_count < 3:
            report_data["warnings"].append(f"문장 수가 매우 적습니다 ({sentence_count}개). 최소 3개 이상 권장.")
        elif sentence_count < 20:
            report_data["warnings"].append(f"문장 수가 적습니다 ({sentence_count}개). 분해 규칙을 보완했습니다.")
        
        # timings를 created_files에 추가 (리포트에서 사용)
        created_files["_timings"] = timings
        
        # 생성된 파일 검증 (한글 포함 확인)
        _verify_generated_files(created_files, parsed_data)
        
        # 리포트 저장
        with open(report_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 파일 생성 후 경로 저장
        created_files["report_path"] = report_path_str
        file_size = report_path.stat().st_size
        print(f"[STEP2_SCRIPT] ✓ step2_report.json 생성 완료: {report_path_str} (크기: {file_size} bytes)")
        
        # 생성 완료 로그 (상대경로 사용하여 인코딩 문제 방지)
        print(f"[STEP2_SCRIPT] ===== 생성 완료 - 파일 목록 =====")
        file_mapping = [
            ("script_path", script_path_rel),
            ("sentences_path", sentences_path_rel),
            ("scenes_path", scenes_path_rel),
            ("report_path", report_path_rel)
        ]
        for key, rel_path in file_mapping:
            full_path = output_dir / rel_path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"[STEP2_SCRIPT]   {key}: {rel_path} (크기: {size} bytes)")
        print(f"[STEP2_SCRIPT] =====================================")
        
    except Exception as e:
        print(f"[STEP2_SCRIPT] ERROR: 파일 생성 중 오류 발생: {e}")
        import traceback
        print(f"[STEP2_SCRIPT] ERROR traceback: {traceback.format_exc()}")
        raise
    
    return created_files


def _verify_generated_files(created_files: Dict[str, str], parsed_data: Dict[str, Any]) -> None:
    """
    생성된 파일 검증 (한글 포함 확인)
    
    Args:
        created_files: 생성된 파일 경로 딕셔너리
        parsed_data: 파싱된 데이터
    """
    try:
        # script.txt 검증
        script_path_str = created_files.get("script_path")
        if script_path_str:
            script_path = Path(script_path_str)
            if script_path.exists():
                with open(script_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 한글 포함 확인
                    has_korean = any('\uAC00' <= char <= '\uD7A3' for char in content)
                    if not has_korean:
                        print(f"[STEP2_SCRIPT] WARN: script.txt에 한글이 포함되어 있지 않습니다.")
                    else:
                        korean_count = sum(1 for char in content if '\uAC00' <= char <= '\uD7A3')
                        print(f"[STEP2_SCRIPT] ✓ script.txt 한글 검증: {korean_count}자 포함")
        
        # sentences.txt 검증
        sentences_path_str = created_files.get("sentences_path")
        if sentences_path_str:
            sentences_path = Path(sentences_path_str)
            if sentences_path.exists():
                with open(sentences_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    has_korean = any(any('\uAC00' <= char <= '\uD7A3' for char in line) for line in lines)
                    if not has_korean:
                        print(f"[STEP2_SCRIPT] WARN: sentences.txt에 한글이 포함되어 있지 않습니다.")
                    else:
                        print(f"[STEP2_SCRIPT] ✓ sentences.txt 한글 검증: {len(lines)}줄 중 한글 포함")
        
        # scenes.json 검증
        scenes_path_str = created_files.get("scenes_path")
        if scenes_path_str:
            scenes_path = Path(scenes_path_str)
            if scenes_path.exists():
                with open(scenes_path, "r", encoding="utf-8") as f:
                    scenes_data = json.load(f)
                    scenes = scenes_data.get("scenes", [])
                    has_korean = False
                    for scene in scenes:
                        narration = scene.get("narration", "") or scene.get("text", "")
                        if any('\uAC00' <= char <= '\uD7A3' for char in narration):
                            has_korean = True
                            break
                    
                    if not has_korean:
                        print(f"[STEP2_SCRIPT] WARN: scenes.json에 한글이 포함되어 있지 않습니다.")
                    else:
                        print(f"[STEP2_SCRIPT] ✓ scenes.json 한글 검증: {len(scenes)}개 씬 중 한글 포함")
    except Exception as e:
        print(f"[STEP2_SCRIPT] WARN: 파일 검증 중 오류 발생 (무시): {e}")


def export_step2_error(
    run_id: str,
    output_dir: Path,
    error_message: str
) -> Dict[str, str]:
    """
    2단계 에러 리포트 생성
    
    Args:
        run_id: 실행 ID
        output_dir: 출력 디렉토리
        error_message: 에러 메시지
    
    Returns:
        Dict[str, str]: 생성된 리포트 경로
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / f"{run_id}_step2_report.json"
    report_path_abs = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        "run_id": run_id,
        "step": 2,
        "status": "error",
        "generated_at": datetime.now().isoformat(),
        "error_message": error_message,
        "summary": {
            "sentence_count": 0,
            "paragraph_count": 0,
            "scene_count": 0,
            "structure": {
                "intro_count": 0,
                "body_count": 0,
                "transition_count": 0,
                "conclusion_count": 0
            }
        },
        "counts": {
            "sentences": 0,
            "paragraphs": 0,
            "scenes": 0
        },
        "file_status": {
            "script_txt": False,
            "sentences_txt": False,
            "scenes_json": False
        },
        "generated_files": []
    }
    
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    report_path_str = str(report_path_abs)
    print(f"[STEP2_SCRIPT] step2_report.json (에러) 생성: {report_path_str}")
    
    return {"report_path": report_path_str}




