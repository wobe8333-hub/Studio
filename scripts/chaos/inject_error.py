"""
inject_error.py — Chaos Engineering: 파이프라인 특정 Step에 에러 주입
Step 실행 로직에 임시 예외 발생 장치를 삽입하여 복원력 테스트.
사용법: python scripts/chaos/inject_error.py {step_number} {error_type}
에러 유형: timeout | quota | file_not_found | api_error | memory_oom
"""
import sys
import io
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent
CHAOS_LOG_DIR = ROOT / "data" / "sre" / "chaos"

ERROR_TEMPLATES = {
    "timeout": "raise TimeoutError('Chaos: 강제 타임아웃 주입')",
    "quota": "raise Exception('Chaos: API 쿼터 초과 시뮬레이션 (429)')",
    "file_not_found": "raise FileNotFoundError('Chaos: 필수 파일 없음 시뮬레이션')",
    "api_error": "raise RuntimeError('Chaos: Gemini API 오류 시뮬레이션 (500)')",
    "memory_oom": "raise MemoryError('Chaos: 메모리 부족 시뮬레이션')",
}

CHAOS_MARKER = "# CHAOS_INJECT_POINT — 아래 줄을 inject_error.py가 자동 주입/제거"


def find_step_init(step_number: int) -> Path | None:
    """Step 모듈 __init__.py 또는 주요 파일 탐색"""
    candidates = [
        ROOT / f"src/step{step_number:02d}/__init__.py",
        ROOT / f"src/step{step_number:02d}/orchestrator.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def inject(step: int, error_type: str) -> None:
    target = find_step_init(step)
    if not target:
        print(f"❌ Step{step:02d} 파일 없음 (src/step{step:02d}/)")
        sys.exit(1)

    if error_type not in ERROR_TEMPLATES:
        print(f"❌ 지원하지 않는 에러 유형: {error_type}")
        print(f"   지원: {list(ERROR_TEMPLATES.keys())}")
        sys.exit(1)

    content = target.read_text(encoding="utf-8")
    if CHAOS_MARKER in content:
        print(f"⚠️ 이미 에러 주입됨: {target}")
        sys.exit(1)

    inject_code = f"\n{CHAOS_MARKER}\n{ERROR_TEMPLATES[error_type]}\n"
    # 첫 번째 함수 정의 앞에 주입
    import re
    new_content = re.sub(r"(\ndef |\nclass )", inject_code + r"\1", content, count=1)

    target.write_text(new_content, encoding="utf-8")

    CHAOS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = {
        "type": "error_injection",
        "step": step, "error_type": error_type,
        "target": str(target), "injected_at": datetime.now().isoformat(),
        "status": "active"
    }
    log_path = CHAOS_LOG_DIR / f"inject-step{step:02d}-{date_str}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"💉 에러 주입: Step{step:02d} → {error_type}")
    print(f"   파일: {target}")
    print(f"   제거 명령: python scripts/chaos/inject_error.py --remove {step} --log {log_path}")


def remove_injection(step: int, log_path_str: str) -> None:
    log_path = Path(log_path_str)
    if not log_path.exists():
        print(f"❌ Chaos 로그 없음: {log_path}")
        sys.exit(1)

    log = json.loads(log_path.read_text(encoding="utf-8"))
    target = Path(log["target"])
    content = target.read_text(encoding="utf-8")

    # 주입 코드 제거
    import re
    new_content = re.sub(
        rf"\n{re.escape(CHAOS_MARKER)}\n.*?\n", "", content, flags=re.DOTALL
    )
    target.write_text(new_content, encoding="utf-8")

    log["status"] = "removed"
    log["removed_at"] = datetime.now().isoformat()
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 에러 제거 완료: Step{step:02d} ({target})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="파이프라인 에러 주입/제거")
    parser.add_argument("step", nargs="?", type=int, help="Step 번호")
    parser.add_argument("error_type", nargs="?", help=f"에러 유형: {list(ERROR_TEMPLATES.keys())}")
    parser.add_argument("--remove", type=int, help="에러 제거할 Step 번호")
    parser.add_argument("--log", help="Chaos 로그 경로")
    args = parser.parse_args()

    if args.remove and args.log:
        remove_injection(args.remove, args.log)
    elif args.step and args.error_type:
        inject(args.step, args.error_type)
    else:
        parser.print_help()
