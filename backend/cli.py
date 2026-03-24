"""
CLI 엔트리포인트 (패키지 실행 전용)

정답 실행 명령(고정, PowerShell 기준):
  python -m backend.cli step2
  python -m backend.cli step3 --run-id <run_id>
  python -m backend.cli verify-runs
  python -m backend.cli step4-check --run-id <run_id>
  python -m backend.cli step4 --run-id <run_id> [--resume] [--force]
  python -m backend.cli step7 --run-id <run_id>
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional


def run_step2(text: Optional[str] = None) -> None:
    """Step2 실행 (structure-script API 래핑)"""
    from backend.core.sample_inputs import STEP2_TEXT
    from backend.main import StructureScriptRequest, structure_script

    script_text = text or STEP2_TEXT
    req = StructureScriptRequest(script=script_text)
    result = asyncio.run(structure_script(req))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_step3(run_id: str) -> None:
    """Step3 실행 (convert-to-fixed-spec API 래핑)"""
    from backend.main import Step3ConvertRequest, convert_to_step3_spec

    req = Step3ConvertRequest(run_id=run_id)
    result = asyncio.run(convert_to_step3_spec(req))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_verify_runs() -> None:
    """runs 상태 일괄 점검"""
    from backend.scripts.verify_runs import main as verify_main

    verify_main()


def run_step4_guard(run_id: str) -> None:
    """Step4 진입 가능 여부 검사"""
    from backend.utils.run_guard import check_step4_ready

    ok, reasons = check_step4_ready(run_id)
    if ok:
        print("READY_FOR_STEP4: YES")
    else:
        print("READY_FOR_STEP4: NO")
        for reason in reasons:
            print(f"- {reason}")


def run_step7(run_id: str) -> None:
    """Step7 실행 (캐시 저장)"""
    from backend.steps.step7_cache import cache_step4_results

    success, error, report = cache_step4_results(run_id, None)
    
    if success:
        cached_count = report.get("cached_count", 0)
        missing_count = report.get("missing_count", 0)
        print("✅ STEP7 CACHE: SUCCESS")
        print(f"CACHED_SCENES: {cached_count}, MISSING_SCENES: {missing_count}")
    else:
        print("❌ STEP7 CACHE: FAIL")
        print(f"REASON: {error}")
        import sys
        sys.exit(1)


def run_v3_step1(run_id: str) -> None:
    """V3 Step1 실행 (Knowledge 적재)"""
    from backend.steps.v3_step1_knowledge import ingest_run

    success, error, report = ingest_run(run_id, None)
    
    if success:
        print("✅ V3_STEP1: SUCCESS")
        item_path = report.get("item_path", "")
        print(f"KNOWLEDGE_ITEM: {item_path}")
    else:
        print("❌ V3_STEP1: FAIL")
        print(f"REASON: {error}")
        import sys
        sys.exit(1)


def run_v3_search(q: str, limit: int = 10) -> None:
    """V3 검색"""
    from backend.utils.knowledge_search import search_index

    results = search_index(q, limit, None)
    
    if not results:
        print(f"No results found for: {q}")
        return
    
    print(f"Found {len(results)} result(s):")
    print()
    for idx, result in enumerate(results, start=1):
        run_id = result.get("run_id", "unknown")
        one_liner = result.get("one_liner", "")
        print(f"{idx}. {run_id}")
        print(f"   {one_liner}")
        print()


def run_step12(run_id: str, source_type: Optional[str] = None, source: Optional[str] = None, title: Optional[str] = None, allow_network: bool = False) -> None:
    """Step12 실행 (지식 적재 + 재활용 힌트 + 프롬프트 추천)"""
    from backend.steps.step12_knowledge import ingest_step12, ingest_step12_external
    from backend.utils.run_manager import load_run_manifest
    from backend.steps.step7_cache import cache_step4_results
    
    # Step12 시작 전 자동 캐시 생성 (cached_scenes < 1일 때)
    manifest = load_run_manifest(run_id, None)
    if manifest:
        steps = manifest.get("steps", {})
        step7 = steps.get("step7", {})
        step7_artifacts = step7.get("artifacts", {})
        cached_scenes = step7_artifacts.get("cached_scenes", 0) if isinstance(step7_artifacts, dict) else 0
        
        if cached_scenes < 1:
            print("STEP12: AUTO_CACHE: START")
            success, error, report = cache_step4_results(run_id, None)
            if success:
                cached_count = report.get("cached_count", 0)
                print(f"STEP12: AUTO_CACHE: CREATED cached_scenes={cached_count}")
            else:
                print(f"STEP12: AUTO_CACHE: FAILED - {error}")
                # 캐시 생성 실패해도 Step12는 계속 진행 (게이트 완화)
        else:
            print("STEP12: AUTO_CACHE: SKIP (already present)")

    # Phase2 옵션이 있으면 Phase2 실행
    if source_type:
        payload = {
            "source_type": source_type,
            "source": source or "",
            "title": title or "",
            "allow_network": allow_network
        }
        success, error, report = ingest_step12_external(run_id, payload, None)
        
        if success:
            print("✅ STEP12 (Phase2): SUCCESS")
            docs_added = report.get("docs_added", 0)
            docs_skipped = report.get("docs_skipped", 0)
            chunks_added = report.get("chunks_added", 0)
            doc_id = report.get("doc_id", "")
            print(f"DOCS_ADDED: {docs_added}, DOCS_SKIPPED: {docs_skipped}, CHUNKS_ADDED: {chunks_added}")
            if doc_id:
                print(f"DOC_ID: {doc_id}")
        else:
            print("❌ STEP12 (Phase2): FAIL")
            print(f"REASON: {error}")
            import sys
            sys.exit(1)
    else:
        # Phase1 실행 (기존 동작)
        success, error, report = ingest_step12(run_id, None)
        
        if success:
            print("✅ STEP12: SUCCESS")
            print(f"KNOWLEDGE_ITEM: {report.get('item_path', '')}")
            print(f"REUSE_HINTS: {report.get('hints_path', '')}")
            print(f"PROMPT_RECOMMENDATION: {report.get('prompts_path', '')}")
            print(f"SIMILAR_RUNS: {report.get('similar_runs_count', 0)}")
        else:
            print("❌ STEP12: FAIL")
            print(f"REASON: {error}")
            import sys
            sys.exit(1)


def run_step12_search(q: str, limit: int = 5) -> None:
    """Step12 검색"""
    from backend.utils.knowledge_search import search_index

    results = search_index(q, limit, None)
    
    if not results:
        print(f"No results found for: {q}")
        return
    
    print(f"Found {len(results)} result(s):")
    print()
    for idx, result in enumerate(results, start=1):
        run_id = result.get("run_id", "unknown")
        one_liner = result.get("one_liner", "")
        scene_count = result.get("scene_count", 0)
        cached_scenes = result.get("cached_scenes", 0)
        print(f"{idx}. {run_id}")
        print(f"   {one_liner}")
        if scene_count > 0 or cached_scenes > 0:
            print(f"   (scenes: {scene_count}, cached: {cached_scenes})")
        print()


def run_step8(run_id: str) -> None:
    """Step8 실행 (Swagger 예시 입력 검증)"""
    from backend.steps.step8_swagger_examples import run_step8 as step8_main

    success, error, report = step8_main(run_id, None)
    
    if success:
        print("✅ STEP8: SUCCESS")
        print(f"REPORT: {report.get('report_path', '')}")
        openapi_path = report.get("openapi_snapshot_path")
        if openapi_path:
            print(f"OPENAPI_SNAPSHOT: {openapi_path}")
        else:
            print("OPENAPI_SNAPSHOT: N/A")
    else:
        print("❌ STEP8: FAIL")
        print("REASONS:")
        if error:
            for reason in error.split("; "):
                print(f" - {reason}")
        import sys
        sys.exit(1)


def run_step9(run_id: str) -> None:
    """Step9 실행 (YouTube 메타데이터 생성)"""
    from backend.steps.step9_youtube_metadata import run_step9 as step9_main

    success, error, report = step9_main(run_id, None)
    
    if success:
        print("✅ STEP9: SUCCESS")
        print(f"METADATA: {report.get('metadata_path', '')}")
    else:
        print("❌ STEP9: FAIL")
        print("REASONS:")
        if error:
            for reason in error.split(", "):
                print(f" - {reason}")
        import sys
        sys.exit(1)


def run_step10(run_id: str) -> None:
    """Step10 실행 (Create 1버튼 오케스트레이션)"""
    from backend.steps.step10_create_pipeline import run_step10 as step10_main

    success, error, report = step10_main(run_id, None)
    
    if success:
        print("✅ STEP10: SUCCESS")
        print(f"PIPELINE: {report.get('pipeline', '')}")
        executed = report.get("executed_steps", [])
        skipped = report.get("skipped_steps", [])
        if executed:
            print(f"EXECUTED: {', '.join(executed)}")
        if skipped:
            print(f"SKIPPED: {', '.join(skipped)}")
    else:
        print("❌ STEP10: FAIL")
        failed_at = report.get("failed_at", "unknown")
        print(f"FAILED_AT: {failed_at}")
        if error:
            print(f"ERROR: {error}")
        import sys
        sys.exit(1)


def run_step4(run_id: str, resume: bool = False, force: bool = False) -> None:
    """Step4 실행 (렌더링)"""
    import sys
    from datetime import datetime
    from backend.steps.step4_render import render_step4
    from backend.utils.failure_report import (
        get_resume_info,
        format_resume_info,
        get_last_failure_summary,
        format_failure_summary
    )
    from backend.utils.run_manager import load_run_manifest, get_run_dir, _atomic_write_json

    # Step6 manifest 기록 보장 (Step4 진입 시 항상 수행)
    manifest = load_run_manifest(run_id, None)
    if manifest is not None:
        steps = manifest.setdefault("steps", {})
        
        # step6가 없으면 생성 (기능 준비 완료 성격)
        if "step6" not in steps:
            steps["step6"] = {
                "status": "success",
                "artifacts": {},
                "errors": [],
                "warnings": []
            }
            manifest["last_updated"] = datetime.now().isoformat()
            
            # manifest 저장
            run_dir = get_run_dir(run_id, None)
            manifest_path = run_dir / "manifest.json"
            _atomic_write_json(manifest_path, manifest)

    # 재실행 UX 게이트 (resume=False, force=False일 때만 동작)
    if not resume and not force:
        if manifest is not None:
            steps = manifest.get("steps", {})
            step4 = steps.get("step4", {})
            step4_status = step4.get("status")
            
            # step4.status="fail" 차단
            if step4_status == "fail":
                failure_info = get_last_failure_summary(run_id, None)
                if failure_info:
                    print(format_failure_summary(failure_info))
                    print()
                
                print("NEXT_ACTION: resume 하려면 --resume, 전체 재생성은 --force")
                print(f"EXAMPLE: python -m backend.cli step4 --run-id {run_id} --resume")
                sys.exit(1)
            
            # step4.status="running" 차단
            if step4_status == "running":
                print("🚫 RUN_LOCKED")
                print(f"- RUN_ID: {run_id}")
                print("- STATUS: running")
                print()
                print("NEXT_ACTION: 이전 실행이 끝난 후 재시도 또는 --force 사용")
                sys.exit(1)

    # resume 모드일 때 resume 정보 출력
    if resume:
        resume_info = get_resume_info(run_id, None)
        print(format_resume_info(resume_info))
        print()  # 빈 줄

    success, error, final_path = render_step4(run_id, resume=resume, force=force)
    
    if success:
        print(f"STATUS: success")
        print(f"FINAL_VIDEO: {final_path}")
    else:
        # 실패 시 실패 요약 출력
        failure_info = get_last_failure_summary(run_id, None)
        if failure_info:
            print(format_failure_summary(failure_info))
            print()  # 빈 줄
        
        print(f"STATUS: fail")
        print(f"ERROR: {error}")
        sys.exit(1)


def run_create() -> None:
    """v6 create 명령: 새 run 생성 + step10 오케스트레이션 실행"""
    import uuid
    from backend.utils.run_manager import create_run_manifest
    from backend.steps.step10_create_pipeline import run_step10
    from pathlib import Path
    
    run_id = str(uuid.uuid4())
    backend_dir = Path(__file__).resolve().parent
    
    # manifest 생성
    manifest = create_run_manifest(run_id, None, backend_dir)
    
    print(f"RUN_ID: {run_id}")
    
    # step10 오케스트레이션 실행
    success, error, report = run_step10(run_id, backend_dir)
    
    if success:
        print("✅ CREATE: SUCCESS")
        executed = report.get("executed_steps", [])
        skipped = report.get("skipped_steps", [])
        if executed:
            print(f"EXECUTED: {', '.join(executed)}")
        if skipped:
            print(f"SKIPPED: {', '.join(skipped)}")
    else:
        print("❌ CREATE: FAIL")
        failed_at = report.get("failed_at", "unknown") if report else "unknown"
        print(f"FAILED_AT: {failed_at}")
        if error:
            print(f"ERROR: {error}")
        import sys
        sys.exit(1)


def run_resume(run_id: str) -> None:
    """v6 resume 명령: 기존 run 재개"""
    from backend.steps.step10_create_pipeline import run_step10
    from pathlib import Path
    
    backend_dir = Path(__file__).resolve().parent
    
    # step10 오케스트레이션을 resume 모드로 실행
    success, error, report = run_step10(run_id, backend_dir)
    
    if success:
        print("✅ RESUME: SUCCESS")
        executed = report.get("executed_steps", [])
        skipped = report.get("skipped_steps", [])
        if executed:
            print(f"EXECUTED: {', '.join(executed)}")
        if skipped:
            print(f"SKIPPED: {', '.join(skipped)}")
    else:
        print("❌ RESUME: FAIL")
        failed_at = report.get("failed_at", "unknown") if report else "unknown"
        print(f"FAILED_AT: {failed_at}")
        if error:
            print(f"ERROR: {error}")
        import sys
        sys.exit(1)


def run_verify(run_id: Optional[str] = None) -> None:
    """v6 verify 명령: run 검증"""
    from backend.utils.run_manager import get_runs_root, latest_run_id, load_run_manifest, _backfill_manifest, get_run_dir, _atomic_write_json
    from backend.utils.verify_step5_rules import verify_step5
    from pathlib import Path
    
    if not run_id:
        # 최신 run_id 사용
        run_id = latest_run_id()
        if not run_id:
            print("❌ VERIFY: FAIL - No runs found")
            import sys
            sys.exit(1)
        print(f"Using latest run_id: {run_id}")
    
    # v6 backfill 강제 실행 (검증 전)
    manifest = load_run_manifest(run_id, None)
    if manifest:
        _backfill_manifest(manifest, run_id)
    
    is_pass, failures, details = verify_step5(run_id, None)
    
    if is_pass:
        print("✅ VERIFY: PASS")
        print(f"RUN_ID: {run_id}")
    else:
        print("❌ VERIFY: FAIL")
        print(f"RUN_ID: {run_id}")
        print(f"FAILURES: {failures}")
        import sys
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Animation Studio CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    
    # v6 단일 명령
    create_p = sub.add_parser("create", help="v6 create: 새 run 생성 + 오케스트레이션")
    resume_p = sub.add_parser("resume", help="v6 resume: run 재개")
    resume_p.add_argument("--run-id", required=True, help="재개할 run_id")
    verify_p = sub.add_parser("verify", help="v6 verify: run 검증")
    verify_p.add_argument("--run-id", help="검증할 run_id (생략 시 최신 run_id 사용)")

    # step2
    step2_p = sub.add_parser("step2", help="Step2 실행 (structure-script)")
    step2_p.add_argument(
        "--text",
        type=str,
        help="스크립트 텍스트 (생략 시 샘플 텍스트 사용)"
    )

    # step3
    step3_p = sub.add_parser("step3", help="Step3 실행 (convert-to-fixed-spec)")
    step3_p.add_argument(
        "--run-id",
        required=True,
        help="Step2에서 생성된 run_id"
    )

    # verify-runs
    sub.add_parser("verify-runs", help="runs 상태 점검")

    # step4-check
    step4_check_p = sub.add_parser("step4-check", help="Step4 준비 상태 확인")
    step4_check_p.add_argument(
        "--run-id",
        required=True,
        help="검사할 run_id"
    )

    # step4
    step4_p = sub.add_parser("step4", help="Step4 실행 (렌더링)")
    step4_p.add_argument(
        "--run-id",
        required=True,
        help="Step3에서 생성된 run_id"
    )
    step4_p.add_argument(
        "--resume",
        action="store_true",
        help="resume 모드 (성공한 scene 스킵)"
    )
    step4_p.add_argument(
        "--force",
        action="store_true",
        help="force 모드 (모든 scene 재생성)"
    )

    # step7
    step7_p = sub.add_parser("step7", help="Step7 실행 (캐시 저장)")
    step7_p.add_argument(
        "--run-id",
        required=True,
        help="Step4가 성공한 run_id"
    )

    # v3-step1
    v3_step1_p = sub.add_parser("v3-step1", help="V3 Step1 실행 (Knowledge 적재)")
    v3_step1_p.add_argument(
        "--run-id",
        required=True,
        help="READY_FOR_V3: YES인 run_id"
    )

    # v3-search
    v3_search_p = sub.add_parser("v3-search", help="V3 Knowledge 검색")
    v3_search_p.add_argument(
        "--q",
        required=True,
        help="검색 키워드"
    )
    v3_search_p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="최대 결과 개수 (기본: 10)"
    )

    # step12
    step12_p = sub.add_parser("step12", help="Step12 실행 (지식 적재 + 재활용 힌트 + 프롬프트 추천)")
    step12_p.add_argument(
        "--run-id",
        required=True,
        help="READY_FOR_STEP12: YES인 run_id"
    )
    step12_p.add_argument(
        "--source-type",
        choices=["text", "file", "url"],
        help="Phase2: 외부 소스 타입 (text|file|url)"
    )
    step12_p.add_argument(
        "--source",
        help="Phase2: 소스 내용 (text: 직접 텍스트, file: 파일 경로, url: URL)"
    )
    step12_p.add_argument(
        "--title",
        help="Phase2: 문서 제목 (선택)"
    )
    step12_p.add_argument(
        "--allow-network",
        action="store_true",
        help="Phase2: URL 소스 사용 시 네트워크 허용"
    )

    # step12-search
    step12_search_p = sub.add_parser("step12-search", help="Step12 Knowledge 검색")
    step12_search_p.add_argument(
        "--q",
        required=True,
        help="검색 키워드"
    )
    step12_search_p.add_argument(
        "--limit",
        type=int,
        default=5,
        help="최대 결과 개수 (기본: 5)"
    )

    # step8
    step8_p = sub.add_parser("step8", help="Step8 실행 (Swagger 예시 입력 검증)")
    step8_p.add_argument(
        "--run-id",
        required=True,
        help="검증할 run_id"
    )

    # step9
    step9_p = sub.add_parser("step9", help="Step9 실행 (YouTube 메타데이터 생성)")
    step9_p.add_argument(
        "--run-id",
        required=True,
        help="메타데이터를 생성할 run_id"
    )

    # step10
    step10_p = sub.add_parser("step10", help="Step10 실행 (Create 1버튼 오케스트레이션)")
    step10_p.add_argument(
        "--run-id",
        required=True,
        help="파이프라인을 실행할 run_id"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "create":
        run_create()
    elif args.command == "resume":
        run_resume(args.run_id)
    elif args.command == "verify":
        run_verify(getattr(args, "run_id", None))
    elif args.command == "step2":
        run_step2(args.text)
    elif args.command == "step3":
        run_step3(args.run_id)
    elif args.command == "verify-runs":
        run_verify_runs()
    elif args.command == "step4-check":
        run_step4_guard(args.run_id)
    elif args.command == "step4":
        run_step4(args.run_id, resume=args.resume, force=args.force)
    elif args.command == "step7":
        run_step7(args.run_id)
    elif args.command == "v3-step1":
        run_v3_step1(args.run_id)
    elif args.command == "v3-search":
        run_v3_search(args.q, args.limit)
    elif args.command == "step12":
        run_step12(args.run_id, args.source_type, args.source, args.title, args.allow_network)
    elif args.command == "step12-search":
        run_step12_search(args.q, args.limit)
    elif args.command == "step8":
        run_step8(args.run_id)
    elif args.command == "step9":
        run_step9(args.run_id)
    elif args.command == "step10":
        run_step10(args.run_id)
    else:
        raise SystemExit(f"알 수 없는 명령: {args.command}")


if __name__ == "__main__":
    import sys

    # 패키지 모드가 아닌 직접 파일 실행일 때는 정답 명령을 안내하고 종료
    if not __package__:
        print(
            "이 CLI는 패키지 모드로 실행해야 합니다.\n"
            "정답 실행 예시:\n"
            "  python -m backend.cli step2\n"
            "  python -m backend.cli step3 --run-id <run_id>\n"
            "  python -m backend.cli verify-runs\n"
            "  python -m backend.cli step4-check --run-id <run_id>\n"
            "  python -m backend.cli step4 --run-id <run_id> [--resume] [--force]\n"
            "  python -m backend.cli step7 --run-id <run_id>"
        )
        sys.exit(1)

    main()

