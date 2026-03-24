"""
체크프롬프트 CLI Runner

사용법:
    python backend/tools/run_checkprompts.py --names step1_basic step1_cache_hit --repeat 2
"""

import sys
import json
import argparse
from pathlib import Path

# 상위 디렉토리를 path에 추가
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from backend.checkprompts.runner import run_longform_script_pipeline


def main():
    parser = argparse.ArgumentParser(description="체크프롬프트 실행")
    parser.add_argument(
        "--names",
        nargs="+",
        required=True,
        help="실행할 체크프롬프트 이름 리스트"
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="반복 횟수 (기본: 1)"
    )
    
    args = parser.parse_args()
    
    # 레지스트리 로드
    registry_path = backend_dir / "checkprompts" / "registry.json"
    if not registry_path.exists():
        print(f"ERROR: 레지스트리를 찾을 수 없습니다: {registry_path}")
        sys.exit(1)
    
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    
    prompts = registry.get("prompts", {})
    
    # run_id 생성
    import uuid
    run_id = str(uuid.uuid4())
    checkruns_dir = backend_dir / "output" / "checkruns" / run_id
    checkruns_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    print(f"체크프롬프트 실행 시작: run_id={run_id}")
    print(f"체크프롬프트: {args.names}")
    print(f"반복 횟수: {args.repeat}")
    print("-" * 50)
    
    # 각 체크프롬프트 실행
    for name in args.names:
        if name not in prompts:
            print(f"ERROR: 체크프롬프트를 찾을 수 없습니다: {name}")
            results.append({
                "name": name,
                "status": "error",
                "error": f"체크프롬프트를 찾을 수 없습니다: {name}"
            })
            continue
        
        prompt_data = prompts[name]
        force_fail = prompt_data.get("force_fail", False)
        
        print(f"\n[{name}] 실행 중...")
        
        # 반복 실행
        for repeat_idx in range(args.repeat):
            import uuid
            job_id = str(uuid.uuid4())
            
            print(f"  반복 {repeat_idx + 1}/{args.repeat} (job_id={job_id})")
            
            try:
                success, result, error = run_longform_script_pipeline(
                    prompt_data,
                    job_id,
                    backend_dir,
                    force_fail=force_fail
                )
                
                if success:
                    status = "success"
                    cache_hit = result.get("cache_hit", False) if isinstance(result, dict) else False
                    print(f"    ✓ 성공 (cache_hit={cache_hit})")
                else:
                    status = "fail"
                    cache_hit = False
                    print(f"    ✗ 실패: {error}")
                
                # 결과 저장
                result_file = checkruns_dir / f"each_{name}_{repeat_idx}.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "name": name,
                        "repeat": repeat_idx,
                        "job_id": job_id,
                        "status": status,
                        "cache_hit": cache_hit,
                        "result": result if success else None,
                        "error": error
                    }, f, ensure_ascii=False, indent=2)
                
                # 리포트에서 로그/리포트 경로 가져오기
                logs_path = backend_dir / "output" / "logs" / f"{job_id}.log"
                reports_path = backend_dir / "output" / "reports" / f"{job_id}.json"
                
                results.append({
                    "name": name,
                    "repeat": repeat_idx,
                    "status": status,
                    "job_id": job_id,
                    "cache_hit": cache_hit,
                    "error": error,
                    "log_path": str(logs_path) if logs_path.exists() else None,
                    "report_path": str(reports_path) if reports_path.exists() else None
                })
                
            except Exception as e:
                # 예외 발생 시에도 서버는 정상 유지
                error_msg = str(e)
                print(f"    ✗ 예외 발생: {error_msg}")
                
                results.append({
                    "name": name,
                    "repeat": repeat_idx,
                    "status": "error",
                    "job_id": job_id,
                    "error": error_msg
                })
                
                # 에러 결과도 저장
                result_file = checkruns_dir / f"each_{name}_{repeat_idx}.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "name": name,
                        "repeat": repeat_idx,
                        "job_id": job_id,
                        "status": "error",
                        "error": error_msg
                    }, f, ensure_ascii=False, indent=2)
    
    # 요약 저장
    summary = {
        "run_id": run_id,
        "total": len(results),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "fail": sum(1 for r in results if r.get("status") == "fail"),
        "error": sum(1 for r in results if r.get("status") == "error"),
        "results": results
    }
    
    summary_path = checkruns_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print(f"실행 완료: run_id={run_id}")
    print(f"요약: 성공={summary['success']}, 실패={summary['fail']}, 에러={summary['error']}")
    print(f"결과 저장 위치: {checkruns_dir}")
    print(f"요약 파일: {summary_path}")


if __name__ == "__main__":
    main()








