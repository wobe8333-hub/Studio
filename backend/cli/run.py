"""
v7 CLI Entry Point
- stdout: JSON 1 line only
"""

from __future__ import annotations
import argparse
import json
import sys
import traceback
import os
from pathlib import Path
from typing import List, Optional


def _json(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def _csv(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _cmd_keyword_discovery(args: argparse.Namespace) -> int:
    try:
        from backend.knowledge_v1.keyword_discovery_engine import run_keyword_discovery
        res = run_keyword_discovery(
            categories=_csv(args.categories),
            mode=args.mode,
            max_keywords=args.max_keywords,
        )
        _json({"ok": True, "result": res})
        return 0
    except Exception as e:
        tb = traceback.format_exc()
        tb_short = tb[-4000:] if len(tb) > 4000 else tb
        
        # stderr에 traceback 출력
        print("TRACEBACK_BEGIN", file=sys.stderr)
        print(tb, file=sys.stderr)
        print("TRACEBACK_END", file=sys.stderr)
        
        # 파일 저장 (옵션)
        traceback_file = os.getenv("V7_TRACEBACK_FILE", "").strip()
        if traceback_file:
            try:
                traceback_path = Path(traceback_file)
                traceback_path.parent.mkdir(parents=True, exist_ok=True)
                traceback_path.write_text(tb, encoding="utf-8")
            except Exception:
                pass  # 파일 저장 실패해도 계속 진행
        
        _json({"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": tb_short})
        return 1


def _cmd_keyword_approve(args: argparse.Namespace) -> int:
    try:
        from backend.knowledge_v1.keyword_approval_gate import approve_keywords
        res = approve_keywords(
            cycle_id=args.cycle_id,
            categories=_csv(args.categories) if args.categories else None,
        )
        _json({"ok": True, "result": res})
        return 0
    except Exception as e:
        tb = traceback.format_exc()
        tb_short = tb[-4000:] if len(tb) > 4000 else tb
        
        # stderr에 traceback 출력
        print("TRACEBACK_BEGIN", file=sys.stderr)
        print(tb, file=sys.stderr)
        print("TRACEBACK_END", file=sys.stderr)
        
        # 파일 저장 (옵션)
        traceback_file = os.getenv("V7_TRACEBACK_FILE", "").strip()
        if traceback_file:
            try:
                traceback_path = Path(traceback_file)
                traceback_path.parent.mkdir(parents=True, exist_ok=True)
                traceback_path.write_text(tb, encoding="utf-8")
            except Exception:
                pass  # 파일 저장 실패해도 계속 진행
        
        _json({"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": tb_short})
        return 1


def _cmd_script_prompt(args: argparse.Namespace) -> int:
    try:
        from backend.knowledge_v1.script_prompt.script_prompt_engine import build_script_prompt
        res = build_script_prompt(
            cycle_id=args.cycle_id if args.cycle_id else None,
            top_k_keywords=args.top_k_keywords,
            top_k_snippets=args.top_k_snippets,
        )
        if res.get("ok"):
            _json({"ok": True, "result": res})
            # output_dir 경로를 stdout에 출력 (PS1에서 사용)
            if "output_dir" in res:
                print(f"OUTPUT_DIR={res['output_dir']}", file=sys.stderr)
            return 0
        else:
            _json({"ok": False, "error": res.get("error", "unknown error")})
            return 1
    except Exception as e:
        tb = traceback.format_exc()
        tb_short = tb[-4000:] if len(tb) > 4000 else tb
        
        # stderr에 traceback 출력
        print("TRACEBACK_BEGIN", file=sys.stderr)
        print(tb, file=sys.stderr)
        print("TRACEBACK_END", file=sys.stderr)
        
        # 파일 저장 (옵션)
        traceback_file = os.getenv("V7_TRACEBACK_FILE", "").strip()
        if traceback_file:
            try:
                traceback_path = Path(traceback_file)
                traceback_path.parent.mkdir(parents=True, exist_ok=True)
                traceback_path.write_text(tb, encoding="utf-8")
            except Exception:
                pass  # 파일 저장 실패해도 계속 진행
        
        _json({"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": tb_short})
        return 1


def _cmd_cycle(args: argparse.Namespace) -> int:
    """
    v7 실행 (SSOT)
    
    Exit Code:
    - 0: 성공 (JSON 출력)
    - 1: 에러 발생 (JSON 출력)
    
    주의: 검증 실패는 exit code 2를 사용하지 않음 (검증 스크립트에서 처리)
    """
    try:
        # 마이그레이션 플래그 설정 (CLI 옵션)
        if getattr(args, "migrate_legacy_store", False):
            from backend.knowledge_v1.paths import set_migrate_legacy_flag
            set_migrate_legacy_flag(True)
        
        # 단일 소스 원칙: CLI 인자가 명시적으로 전달되면 그대로 사용 (중복 적용 방지)
        # args.max_keywords_per_category는 argparse에서 이미 기본값 80이 설정됨
        max_keywords_per_category = args.max_keywords_per_category
        
        # daily_total_limit 크래시 방지 봉인: getattr로 안전하게 접근 (STEP 3)
        resolved_daily_total_limit = getattr(args, "daily_total_limit", None)
        if resolved_daily_total_limit is None:
            resolved_daily_total_limit = 400
        
        # 레거시 옵션 흡수 (STEP 2): --max-keywords가 있고 daily_total_limit이 기본값(400)이면 치환
        if hasattr(args, "max_keywords") and args.max_keywords is not None:
            if resolved_daily_total_limit == 400:  # 기본값 그대로면 레거시 값 사용
                resolved_daily_total_limit = args.max_keywords
        
        from backend.knowledge_v1.cycle import run_discovery_cycle
        # STEP 4: 명시적 전달로 봉인 (args 객체를 통째로 넘기지 않고 resolved 값 전달)
        cycle_id_param = args.cycle_id.strip() if hasattr(args, "cycle_id") and args.cycle_id else None
        if cycle_id_param == "":
            cycle_id_param = None
        
        try:
            res = run_discovery_cycle(
                categories=_csv(args.categories),
                mode=args.mode,
                keywords_dir=Path(args.keywords_dir) if args.keywords_dir else None,
                max_keywords_per_category=max_keywords_per_category,  # 단일 소스: CLI에서만 설정
                daily_total_limit=resolved_daily_total_limit,  # STEP 4: 명시적 전달 (재발 불가능)
                approve_fallback=args.approve_fallback,
                cycle_id=cycle_id_param,  # cycle_id 단일화
            )
            _json({"ok": True, "result": res})
            return 0  # 성공
        except SystemExit as e:
            # ingest 0 FAIL 시 sys.exit(2)가 호출되면 그대로 전달
            if e.code == 2:
                return 2
            raise
    except Exception as e:
        tb = traceback.format_exc()
        tb_short = tb[-4000:] if len(tb) > 4000 else tb
        
        # stderr에 traceback 출력
        print("TRACEBACK_BEGIN", file=sys.stderr)
        print(tb, file=sys.stderr)
        print("TRACEBACK_END", file=sys.stderr)
        
        # 파일 저장 (옵션)
        traceback_file = os.getenv("V7_TRACEBACK_FILE", "").strip()
        if traceback_file:
            try:
                traceback_path = Path(traceback_file)
                traceback_path.parent.mkdir(parents=True, exist_ok=True)
                traceback_path.write_text(tb, encoding="utf-8")
            except Exception:
                pass  # 파일 저장 실패해도 계속 진행
        
        # PATCH-13Q.1: YouTube 오류는 파이프라인 무중단을 위해 격리
        allow_fail = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
        error_msg = str(e)
        is_youtube_error = (
            "YOUTUBE_LIVE_FETCH_FAILED" in error_msg or
            "API key expired" in error_msg or
            "quotaExceeded" in error_msg or
            "quota" in error_msg.lower()
        )
        if is_youtube_error and allow_fail:
            # YouTube 오류를 격리하고 파이프라인은 성공으로 처리
            _json({"ok": True, "result": {"mode": args.mode, "youtube_skipped": True, "error": "youtube_skipped"}})
            return 0  # 성공으로 처리
        _json({"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": tb_short})
        return 1  # 에러 (검증 실패는 아니므로 exit code 1 사용)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="backend.cli.run")
    sub = p.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("knowledge")
    ks = k.add_subparsers(dest="sub", required=True)

    p1 = ks.add_parser("keyword-discovery")
    p1.add_argument("--categories", default="science,history,common_sense,economy,geography,papers")
    p1.add_argument("--mode", choices=["run", "dry-run", "live"], default="run")
    p1.add_argument("--max-keywords", type=int, default=200)
    p1.set_defaults(func=_cmd_keyword_discovery)

    p2 = ks.add_parser("keyword-approve")
    p2.add_argument("--cycle-id", required=True)
    p2.add_argument("--categories", default="")
    p2.set_defaults(func=_cmd_keyword_approve)

    p3 = ks.add_parser("cycle")
    p3.add_argument("--categories", default="science,history,common_sense,economy,geography,papers")
    p3.add_argument("--mode", choices=["run", "dry-run", "live"], default="run")
    p3.add_argument("--keywords-dir", default="")
    # v7 기본값: 단일 소스 원칙 (여기서만 설정, 중복 적용 방지)
    p3.add_argument("--max-keywords-per-category", type=int, default=80)
    p3.add_argument("--daily-total-limit", type=int, default=400, help="일일 총 키워드 제한")
    p3.add_argument("--approve-fallback", action="store_true")
    p3.add_argument("--cycle-id", default="", help="cycle_id (미지정 시 last_cycle_id.txt 또는 최신 snapshots 폴더 사용)")
    p3.add_argument("--migrate-legacy-store", action="store_true", help="레거시 store에서 새 store로 마이그레이션")
    p3.set_defaults(func=_cmd_cycle)

    p4 = ks.add_parser("v7-run")
    p4.add_argument("--categories", default="science,history,common_sense,economy,geography,papers")
    p4.add_argument("--mode", choices=["run", "dry-run", "live"], default="run")
    p4.add_argument("--keywords-dir", default="")
    # v7 기본값: 단일 소스 원칙 (여기서만 설정, 중복 적용 방지)
    p4.add_argument("--max-keywords-per-category", type=int, default=150)
    p4.add_argument("--daily-total-limit", type=int, default=900, help="일일 총 키워드 제한")
    p4.add_argument("--max-keywords", type=int, default=None, help="Alias for --daily-total-limit (deprecated)")
    p4.add_argument("--approve-fallback", action="store_true")
    p4.add_argument("--migrate-legacy-store", action="store_true", help="레거시 store에서 새 store로 마이그레이션")
    p4.add_argument("--debug", action="store_true", help="Debug mode (ignored, for compatibility)")
    p4.set_defaults(func=_cmd_cycle)

    p5 = ks.add_parser("script-prompt")
    p5.add_argument("--cycle-id", default="", help="cycle_id (미지정 시 last_cycle_id.txt 사용)")
    p5.add_argument("--top-k-keywords", type=int, default=1, help="선택할 키워드 수 (기본 1)")
    p5.add_argument("--top-k-snippets", type=int, default=5, help="키워드당 snippet 수 (기본 5)")
    p5.set_defaults(func=_cmd_script_prompt)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
