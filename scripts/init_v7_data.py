#!/usr/bin/env python3
"""
v7.0 신규 SSOT 디렉토리·파일 초기화 스크립트.
data/legal/, data/bi/, data/prompts/versions/ 초기화.
실행: python scripts/init_v7_data.py
"""
from __future__ import annotations

import io
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp949 콘솔에서 한글 출력 보장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.ssot import write_json  # noqa: E402


def init_legal_data() -> None:
    """data/legal/ 초기화 — legal-counsel SSOT."""
    legal_dir = ROOT / "data" / "legal"
    reviews_dir = legal_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    # 빈 index 파일 생성
    index_path = legal_dir / "review_index.json"
    if not index_path.exists():
        write_json(index_path, {
            "schema_version": "1.0",
            "description": "legal-counsel 계약서 검토 인덱스",
            "reviews": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        print("[OK] data/legal/review_index.json 초기화")
    else:
        print("[SKIP] data/legal/review_index.json 이미 존재")


def init_bi_data() -> None:
    """data/bi/ 초기화 — data-analyst SSOT."""
    bi_dir = ROOT / "data" / "bi"
    bi_dir.mkdir(parents=True, exist_ok=True)

    dashboard_path = bi_dir / "weekly_dashboard.json"
    if not dashboard_path.exists():
        write_json(dashboard_path, {
            "schema_version": "1.0",
            "description": "data-analyst 주간 BI 대시보드",
            "period": None,
            "generated_at": None,
            "channel_kpi": {},
            "cost_summary": {
                "gemini_api_usd": 0.0,
                "elevenlabs_usd": 0.0,
                "total_usd": 0.0,
                "cost_per_video_usd": 0.0,
            },
            "sales_funnel": {
                "leads": 0,
                "proposals": 0,
                "contracts": 0,
                "conversion_rate_pct": 0.0,
            },
            "key_insights": [],
            "recommendations": [],
        })
        print("[OK] data/bi/weekly_dashboard.json 초기화")
    else:
        print("[SKIP] data/bi/weekly_dashboard.json 이미 존재")


def init_prompts_data() -> None:
    """data/prompts/ 초기화 — prompt-engineer SSOT."""
    prompts_dir = ROOT / "data" / "prompts"
    versions_dir = prompts_dir / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    index_path = prompts_dir / "version_index.json"
    if not index_path.exists():
        write_json(index_path, {
            "schema_version": "1.0",
            "description": "prompt-engineer 프롬프트 버전 관리 인덱스",
            "steps": {},
            "ab_tests": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        print("[OK] data/prompts/version_index.json 초기화")
    else:
        print("[SKIP] data/prompts/version_index.json 이미 존재")


def main() -> None:
    print("[v7.0 SSOT 초기화 시작]")
    init_legal_data()
    init_bi_data()
    init_prompts_data()
    print("\n[OK] v7.0 SSOT 초기화 완료")
    print("  - data/legal/reviews/      — legal-counsel 검토 결과 저장소")
    print("  - data/bi/                 — data-analyst BI 대시보드")
    print("  - data/prompts/versions/   — prompt-engineer 버전 관리")


if __name__ == "__main__":
    main()
