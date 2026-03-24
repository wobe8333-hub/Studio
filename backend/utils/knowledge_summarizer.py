"""
Knowledge 요약 생성 유틸리티 (V3)

기능:
- manifest 기반 규칙 기반 요약 생성
- 외부 LLM 호출 금지 (템플릿 기반)
"""

from typing import Dict, List, Any, Optional
from pathlib import Path


def build_summary_from_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    manifest에서 규칙 기반 요약 생성
    
    Args:
        manifest: run manifest
    
    Returns:
        Dict: summary 데이터
        {
            "one_liner": str,
            "bullet_points": List[str],
            "keywords": List[str]
        }
    """
    run_id = manifest.get("run_id", "unknown")
    steps = manifest.get("steps", {})
    
    # Step3 정보
    step3 = steps.get("step3", {})
    scenes_fixed_path = ""
    scenes_count = 0
    
    # Step4 정보
    step4 = steps.get("step4", {})
    step4_status = step4.get("status", "unknown")
    step4_artifacts = step4.get("artifacts", [])
    final_video_path = ""
    
    # Step7 정보
    step7 = steps.get("step7", {})
    step7_artifacts = step7.get("artifacts", {})
    cached_scenes = step7_artifacts.get("cached_scenes", 0) if isinstance(step7_artifacts, dict) else 0
    
    # final_video_path 추출
    for artifact in step4_artifacts:
        artifact_str = str(artifact)
        if "final_" in artifact_str and artifact_str.endswith(".mp4"):
            final_video_path = artifact_str
            break
    
    # scenes_count 추출 (scenes_fixed.json 경로에서 추론하거나 manifest에서)
    # 간단히 step4 artifacts의 scene_videos 개수로 추정
    scene_videos = [a for a in step4_artifacts if "scene_" in str(a) and str(a).endswith(".mp4")]
    scenes_count = len(scene_videos)
    
    # one_liner 생성
    one_liner_parts = []
    one_liner_parts.append(f"Run {run_id}")
    if scenes_count > 0:
        one_liner_parts.append(f"{scenes_count} scenes")
    one_liner_parts.append(f"Step4: {step4_status}")
    if cached_scenes > 0:
        one_liner_parts.append(f"{cached_scenes} cached")
    if final_video_path:
        one_liner_parts.append("video generated")
    
    one_liner = " | ".join(one_liner_parts)
    
    # bullet_points 생성
    bullet_points = []
    bullet_points.append(f"Run ID: {run_id}")
    if scenes_count > 0:
        bullet_points.append(f"Scenes: {scenes_count}")
    bullet_points.append(f"Step4 Status: {step4_status}")
    if final_video_path:
        bullet_points.append(f"Final Video: {Path(final_video_path).name}")
    if cached_scenes > 0:
        bullet_points.append(f"Cached Scenes: {cached_scenes}")
    
    # keywords 생성
    keywords = []
    keywords.append(run_id)
    keywords.append(f"scenes_{scenes_count}")
    keywords.append(f"step4_{step4_status}")
    if cached_scenes > 0:
        keywords.append("cached")
    if final_video_path:
        keywords.append("video")
    
    # step statuses 추가
    for step_name in ["step1", "step2", "step3", "step4", "step6", "step7"]:
        step_data = steps.get(step_name, {})
        step_status = step_data.get("status")
        if step_status:
            keywords.append(f"{step_name}_{step_status}")
    
    return {
        "one_liner": one_liner,
        "bullet_points": bullet_points,
        "keywords": keywords
    }

