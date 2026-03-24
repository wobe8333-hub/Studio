"""
Step1-REAPPLY: 기존 runs 전체 manifest 백필 (v1.4 Step1 신규 메타 필드)

기능:
- runs 폴더의 모든 run_id 하위 manifest.json을 자동 탐색
- v1.4 Step1 신규 메타 필드 백필 (creation_mode, ui_scope, data_impact_scope, cost_caps, stop_conditions, decision_trace, governance, locks)
- 기존 키/값/구조는 절대 변경하지 않음 (신규 키 추가만)
- schema_version은 절대 변경하지 않음

실행:
    python -m backend.scripts.backfill_manifest_v1_4_step1
"""

import sys
from pathlib import Path
from typing import Tuple

# 프로젝트 루트 기준으로 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.utils.run_manager import get_runs_root, backfill_manifest_file_v1_4_step1


def main() -> int:
    """
    백필 메인 함수
    
    Returns:
        int: exit code (0=성공, 1=에러 있음)
    """
    print("BACKFILL START")
    
    # runs 디렉토리 경로
    runs_dir = get_runs_root(None)
    
    if not runs_dir.exists():
        print(f"ERROR: runs 디렉토리가 없습니다: {runs_dir}")
        return 1
    
    # 카운터
    total = 0
    updated = 0
    ok = 0
    error = 0
    
    # runs 디렉토리 하위의 모든 run_id 디렉토리 탐색
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        
        run_id = run_dir.name
        manifest_path = run_dir / "manifest.json"
        
        # manifest.json이 없으면 SKIP
        if not manifest_path.exists():
            continue
        
        total += 1
        
        try:
            # 백필 실행
            changed = backfill_manifest_file_v1_4_step1(manifest_path)
            
            if changed:
                print(f"UPDATED: {run_id}")
                updated += 1
            else:
                print(f"OK: {run_id}")
                ok += 1
        except Exception as e:
            print(f"ERROR: {run_id} :: {e}")
            error += 1
            # 에러가 있어도 계속 진행
    
    # 요약 출력
    print("BACKFILL DONE")
    print(f"TOTAL={total} UPDATED={updated} OK={ok} ERROR={error}")
    
    # error>0이면 exit code 1
    return 1 if error > 0 else 0


if __name__ == "__main__":
    sys.exit(main())


