"""
VideoPlanV1 백필 스크립트 (Step6/10 검증 404 해결)

기능:
- 기존 run_id에 대해 scenes_fixed.json을 기반으로 VideoPlanV1 플랜 생성
- backend/output/plans/{run_id}.json 저장

실행:
    python -m backend.scripts.backfill_video_plan_v1 --run-id <run_id>
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# 프로젝트 루트 기준으로 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.utils.run_manager import get_runs_root, get_run_dir
from backend.schemas.longform_scene_v1 import VideoPlanV1, SceneV1
from backend.ai_engine.longform_scene_splitter import save_video_plan


def create_plan_from_scenes_fixed(run_id: str) -> Optional[Path]:
    """
    scenes_fixed.json을 기반으로 VideoPlanV1 생성 및 저장
    
    Args:
        run_id: 실행 ID
    
    Returns:
        Optional[Path]: 저장된 플랜 파일 경로 (실패 시 None)
    """
    run_dir = get_run_dir(run_id, None)
    
    # 입력 소스 1: scenes_fixed.json (필수)
    scenes_fixed_path = run_dir / "step3" / "scenes_fixed.json"
    if not scenes_fixed_path.exists():
        print(f"ERROR: scenes_fixed.json이 없습니다: {scenes_fixed_path}")
        return None
    
    # 입력 소스 2: script.txt (없으면 빈 문자열 허용)
    script_path = run_dir / "step2" / "script.txt"
    narration_script = ""
    if script_path.exists():
        try:
            narration_script = script_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            pass
    
    # scenes_fixed.json 로드
    try:
        with open(scenes_fixed_path, "r", encoding="utf-8") as f:
            scenes_fixed_data = json.load(f)
    except Exception as e:
        print(f"ERROR: scenes_fixed.json 로드 실패: {e}")
        return None
    
    scenes_list = scenes_fixed_data.get("scenes", [])
    if not scenes_list:
        print(f"ERROR: scenes_fixed.json에 씬이 없습니다")
        return None
    
    # topic 추출 (script.txt의 첫 번째 non-empty 라인, 최대 60자)
    topic = "Untitled"
    if narration_script:
        lines = narration_script.splitlines()
        for line in lines:
            line = line.strip()
            if line:
                topic = line[:60]
                break
    
    # scenes 배열 생성
    scenes = []
    for i, scene_fixed in enumerate(scenes_list):
        # order: scene_index + 1 (없으면 i+1)
        scene_index = scene_fixed.get("scene_index", i)
        order = scene_index + 1 if scene_index > 0 else i + 1
        
        # scene_id
        scene_id = f"scene_{order:03d}"
        
        # narration
        narration = scene_fixed.get("narration", "")
        
        # shot_prompt_en (visual_prompt 사용)
        shot_prompt_en = scene_fixed.get("visual_prompt", "")
        
        # duration_sec (1~60 범위로 clamp)
        duration_sec = scene_fixed.get("duration_sec", 6)
        duration_sec = max(1, min(60, int(duration_sec)))
        
        # SceneV1 생성
        scene = SceneV1(
            scene_id=scene_id,
            order=order,
            narration=narration,
            shot_prompt_en=shot_prompt_en,
            image_asset=None,
            duration_sec=duration_sec,
            overlay_text=None,
            bgm=None,
            status="pending",
            render_status="PENDING",
            render_attempts=0,
            last_error=None,
            output_video_path=None
        )
        scenes.append(scene)
    
    # VideoPlanV1 생성
    video_plan = VideoPlanV1(
        video_id=run_id,
        topic=topic,
        style_profile_id="longform-default",
        narration_script=narration_script,
        scenes=scenes,
        chapters=[],
        meta={
            "source": "backfill_video_plan_v1",
            "from": f"runs/{run_id}/step3/scenes_fixed.json"
        }
    )
    
    # 저장
    backend_dir = Path(__file__).resolve().parents[1]
    plans_dir = backend_dir / "output" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / f"{run_id}.json"
    
    try:
        save_video_plan(video_plan, plan_path)
        return plan_path
    except Exception as e:
        print(f"ERROR: 플랜 저장 실패: {e}")
        return None


def main() -> int:
    """
    메인 함수
    
    Returns:
        int: exit code (0=성공, 1=실패)
    """
    parser = argparse.ArgumentParser(description="VideoPlanV1 백필")
    parser.add_argument("--run-id", type=str, required=True, help="Run ID")
    args = parser.parse_args()
    
    print("BACKFILL_PLAN START")
    print(f"RUN_ID={args.run_id}")
    
    run_dir = get_run_dir(args.run_id, None)
    print(f"RUN_DIR={run_dir.resolve()}")
    
    # 플랜 생성
    plan_path = create_plan_from_scenes_fixed(args.run_id)
    
    if plan_path:
        print(f"OUT_PLAN={plan_path.resolve()}")
        print("DONE")
        return 0
    else:
        print("FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

