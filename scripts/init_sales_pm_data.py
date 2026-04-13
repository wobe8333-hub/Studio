#!/usr/bin/env python3
"""
Phase 2 SSOT 초기화 스크립트.
data/exec/, data/sales/, data/pm/ 디렉토리의 JSON 파일을 초기 스키마로 생성.
실행: python scripts/init_sales_pm_data.py
이미 존재하는 파일은 --force 옵션 없이 덮어쓰지 않음.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Windows cp949 콘솔에서 한글 출력 보장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.ssot import write_json  # noqa: E402


# ── 초기화 대상 파일 정의 ─────────────────────────────────────────────────
INIT_DATA: dict[str, object] = {
    # Executive Office
    "data/exec/decisions.json": [],
    "data/exec/team_lifecycle.json": [],
    "data/exec/monthly_report.json": {
        "generated_at": None,
        "month": None,
        "revenue_total_krw": 0,
        "kas_channel_kpi": {},
        "api_cost_usd": 0,
        "net_profit_krw": 0,
        "next_month_strategy": "",
    },
    # Sales & Delivery
    "data/sales/leads.json": [],
    # Finance (미리 생성 — Phase 3에서 확장)
}

# ── proposals/, pm/projects/ 는 하위 디렉토리만 생성 (동적 파일 저장소) ──
DIRS_ONLY: list[str] = [
    "data/sales/proposals",
    "data/pm/projects",
    "data/global/audits",   # Quality Assurance 감사 리포트 저장소 (Phase 1 보완)
    "data/creative",        # Creative Studio 리뷰 리포트 (Phase 1 보완)
]


def main(force: bool = False) -> None:
    created, skipped = [], []

    # JSON 파일 초기화
    for rel_path, initial_data in INIT_DATA.items():
        target = ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not force:
            skipped.append(rel_path)
            continue

        write_json(target, initial_data)
        created.append(rel_path)

    # 디렉토리만 생성 (빈 폴더 — .gitkeep 포함)
    for rel_dir in DIRS_ONLY:
        d = ROOT / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
            created.append(f"{rel_dir}/.gitkeep")
        else:
            skipped.append(rel_dir)

    # 결과 출력
    if created:
        print(f"[OK] 생성 완료 ({len(created)}개):")
        for p in created:
            print(f"  + {p}")
    if skipped:
        print(f"[SKIP] 이미 존재 ({len(skipped)}개) — --force로 덮어쓰기 가능:")
        for p in skipped:
            print(f"  = {p}")
    print("Phase 2 SSOT 초기화 완료.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAS Phase 2 SSOT 초기화")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    args = parser.parse_args()
    main(force=args.force)
