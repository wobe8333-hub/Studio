"""
실제 출력 텍스트 확인용 Export 기능

기능:
- plans JSON에서 대본/씬 데이터 추출
- verify 폴더에 텍스트 파일 생성
- script.txt, scenes.json, prompts.txt, chapters.txt 생성
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path


def export_verify_from_plan(
    plan_data: Dict[str, Any],
    run_id: str,
    output_dir: Path
) -> Dict[str, str]:
    """
    VideoPlanV1 JSON에서 verify 텍스트 파일 생성
    
    Args:
        plan_data: VideoPlanV1 JSON 데이터
        run_id: 실행 ID (job_id 또는 video_id)
        output_dir: 출력 디렉토리 (backend/output)
    
    Returns:
        Dict[str, str]: 생성된 파일 경로들
            - script_path
            - scenes_path
            - prompts_path
            - chapters_path (있는 경우)
    """
    verify_dir = output_dir / "verify" / run_id
    verify_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = {}
    
    try:
        # 1. script.txt 생성
        narration_script = plan_data.get("narration_script", "")
        if narration_script and narration_script.strip():
            script_path = verify_dir / "script.txt"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(narration_script)
            created_files["script_path"] = str(script_path)
            print(f"[VERIFY_EXPORT] script.txt 생성: {script_path}")
        else:
            print(f"[VERIFY_EXPORT] WARN: narration_script이 비어있습니다. script.txt를 생성하지 않습니다.")
        
        # 2. scenes.json 생성
        scenes = plan_data.get("scenes", [])
        if scenes:
            scenes_path = verify_dir / "scenes.json"
            with open(scenes_path, "w", encoding="utf-8") as f:
                json.dump(scenes, f, ensure_ascii=False, indent=2)
            created_files["scenes_path"] = str(scenes_path)
            print(f"[VERIFY_EXPORT] scenes.json 생성: {scenes_path} ({len(scenes)}개 씬)")
        else:
            print(f"[VERIFY_EXPORT] WARN: scenes가 비어있습니다. scenes.json을 생성하지 않습니다.")
        
        # 3. prompts.txt 생성
        if scenes:
            prompts_path = verify_dir / "prompts.txt"
            with open(prompts_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("씬별 이미지 프롬프트 요약\n")
                f.write("=" * 60 + "\n\n")
                
                for scene in sorted(scenes, key=lambda s: s.get("order", 0)):
                    order = scene.get("order", 0)
                    scene_id = scene.get("scene_id", "unknown")
                    narration = scene.get("narration", "")
                    shot_prompt = scene.get("shot_prompt_en", "")
                    
                    f.write(f"[씬 {order}] {scene_id}\n")
                    f.write(f"  내레이션: {narration[:100]}{'...' if len(narration) > 100 else ''}\n")
                    f.write(f"  프롬프트: {shot_prompt}\n")
                    f.write("\n" + "-" * 60 + "\n\n")
            
            created_files["prompts_path"] = str(prompts_path)
            print(f"[VERIFY_EXPORT] prompts.txt 생성: {prompts_path}")
        
        # 4. chapters.txt 생성 (있는 경우)
        chapters = plan_data.get("chapters", [])
        if chapters:
            chapters_path = verify_dir / "chapters.txt"
            with open(chapters_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("유튜브 챕터 목록\n")
                f.write("=" * 60 + "\n\n")
                
                for chapter in chapters:
                    title = chapter.get("title", "")
                    start_sec = chapter.get("start_sec", 0)
                    minutes = start_sec // 60
                    seconds = start_sec % 60
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    f.write(f"{time_str} {title}\n")
            
            created_files["chapters_path"] = str(chapters_path)
            print(f"[VERIFY_EXPORT] chapters.txt 생성: {chapters_path} ({len(chapters)}개 챕터)")
        else:
            print(f"[VERIFY_EXPORT] INFO: chapters가 없습니다. chapters.txt를 생성하지 않습니다.")
        
    except Exception as e:
        print(f"[VERIFY_EXPORT] ERROR: verify 파일 생성 중 오류 발생: {e}")
        raise
    
    return created_files


def export_verify_from_plan_file(
    plan_path: Path,
    run_id: str,
    output_dir: Path
) -> Dict[str, str]:
    """
    plan JSON 파일에서 verify 텍스트 파일 생성
    
    Args:
        plan_path: plan JSON 파일 경로
        run_id: 실행 ID
        output_dir: 출력 디렉토리
    
    Returns:
        Dict[str, str]: 생성된 파일 경로들
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"플랜 파일을 찾을 수 없습니다: {plan_path}")
    
    with open(plan_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    
    return export_verify_from_plan(plan_data, run_id, output_dir)


def export_verify_from_report(
    report_data: Dict[str, Any],
    output_dir: Path
) -> Optional[Dict[str, str]]:
    """
    report JSON에서 job_id를 추출하여 plan을 찾아 verify 파일 생성
    
    Args:
        report_data: report JSON 데이터
        output_dir: 출력 디렉토리
    
    Returns:
        Optional[Dict[str, str]]: 생성된 파일 경로들 또는 None
    """
    job_id = report_data.get("job_id")
    if not job_id:
        print(f"[VERIFY_EXPORT] WARN: report에 job_id가 없습니다.")
        return None
    
    # plan 파일 찾기 (video_id 또는 job_id로)
    plans_dir = output_dir / "plans"
    
    # video_id를 report의 meta에서 찾거나, job_id를 video_id로 사용
    # 또는 checkruns에서 찾기
    plan_path = None
    
    # 1. job_id가 video_id 형식인 경우
    plan_path = plans_dir / f"{job_id}.json"
    if not plan_path.exists():
        # 2. checkruns에서 찾기
        checkruns_dir = output_dir / "checkruns"
        for checkrun_dir in checkruns_dir.iterdir():
            if not checkrun_dir.is_dir():
                continue
            summary_path = checkrun_dir / "summary.json"
            if summary_path.exists():
                try:
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary = json.load(f)
                    for result in summary.get("results", []):
                        if result.get("job_id") == job_id:
                            # result에서 video_id 추출 시도
                            result_data = result.get("result", {})
                            if result_data:
                                video_id = result_data.get("video_id")
                                if video_id:
                                    plan_path = plans_dir / f"{video_id}.json"
                                    break
                except Exception:
                    continue
    
    if plan_path and plan_path.exists():
        return export_verify_from_plan_file(plan_path, job_id, output_dir)
    else:
        print(f"[VERIFY_EXPORT] WARN: job_id={job_id}에 해당하는 plan 파일을 찾을 수 없습니다.")
        return None
































