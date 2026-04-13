#!/usr/bin/env python3
"""
v8.0 신규 SSOT 디렉토리 초기화 스크립트.
data/sre/, data/mlops/, data/security/, data/etl/, data/community/, data/research/
실행: python scripts/init_v8_data.py
"""
from __future__ import annotations

import io
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.ssot import write_json  # noqa: E402


def init_sre_data() -> None:
    """data/sre/ 초기화 — sre-engineer SSOT."""
    sre_dir = ROOT / "data" / "sre"
    runbooks_dir = sre_dir / "runbooks"
    runbooks_dir.mkdir(parents=True, exist_ok=True)

    slo_path = sre_dir / "slo_status.json"
    if not slo_path.exists():
        write_json(slo_path, {
            "schema_version": "1.0",
            "description": "sre-engineer SLO 상태 대시보드",
            "updated_at": None,
            "pipeline_error_rate_pct": 0.0,
            "consecutive_failures": 0,
            "hitl_escalations": [],
            "sentry_dsn_configured": False,
        })
        print("[OK] data/sre/slo_status.json 초기화")
    else:
        print("[SKIP] data/sre/slo_status.json 이미 존재")


def init_mlops_data() -> None:
    """data/mlops/ 초기화 — mlops-engineer SSOT."""
    mlops_dir = ROOT / "data" / "mlops"
    mlops_dir.mkdir(parents=True, exist_ok=True)

    checkpoints_path = mlops_dir / "checkpoints.json"
    if not checkpoints_path.exists():
        write_json(checkpoints_path, {
            "schema_version": "1.0",
            "description": "mlops-engineer 모델 버전 이력",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sd_xl": {
                "current_version": None,
                "history": [],
                "drift_threshold": 0.7,
            },
            "lora": {
                "channels": {},
                "last_drift_check": None,
            },
            "elevenlabs": {
                "ab_tests": [],
                "active_voices": {},
            },
            "faster_whisper": {
                "current_model": None,
                "accuracy_history": [],
            },
        })
        print("[OK] data/mlops/checkpoints.json 초기화")
    else:
        print("[SKIP] data/mlops/checkpoints.json 이미 존재")


def init_security_data() -> None:
    """data/security/ 초기화 — security-engineer SSOT."""
    security_dir = ROOT / "data" / "security" / "audit"
    security_dir.mkdir(parents=True, exist_ok=True)

    audit_log_path = security_dir / "audit_log.json"
    if not audit_log_path.exists():
        write_json(audit_log_path, {
            "schema_version": "1.0",
            "description": "security-engineer 보안 감사 이력",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "oauth_rotation_schedule": {
                "CH1": None, "CH2": None, "CH3": None,
                "CH4": None, "CH5": None, "CH6": None, "CH7": None,
            },
            "vulnerabilities": [],
            "last_secret_scan": None,
        })
        print("[OK] data/security/audit/audit_log.json 초기화")
    else:
        print("[SKIP] data/security/audit/audit_log.json 이미 존재")


def init_etl_data() -> None:
    """data/etl/ 초기화 — data-engineer SSOT."""
    etl_dir = ROOT / "data" / "etl"
    etl_dir.mkdir(parents=True, exist_ok=True)

    schedule_path = etl_dir / "pipeline_schedule.json"
    if not schedule_path.exists():
        write_json(schedule_path, {
            "schema_version": "1.0",
            "description": "data-engineer ETL 파이프라인 스케줄",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "step05_sources": {
                "stage1_tavily": {"enabled": True, "quality_threshold": 0.7, "retry_count": 3},
                "stage2_fred": {"enabled": True, "quality_threshold": 0.6, "retry_count": 2},
                "stage2_nasa": {"enabled": True, "quality_threshold": 0.6, "retry_count": 2},
                "stage2_reddit": {"enabled": True, "quality_threshold": 0.5, "retry_count": 2},
                "stage3_perplexity": {"enabled": True, "quality_threshold": 0.8, "retry_count": 3},
            },
            "supabase_sync": {
                "idempotency_key": "run_id",
                "last_sync": None,
                "sync_failures": [],
            },
        })
        print("[OK] data/etl/pipeline_schedule.json 초기화")
    else:
        print("[SKIP] data/etl/pipeline_schedule.json 이미 존재")


def init_community_data() -> None:
    """data/community/ 초기화 — community-manager SSOT."""
    community_dir = ROOT / "data" / "community"
    community_dir.mkdir(parents=True, exist_ok=True)

    feedback_path = community_dir / "feedback_summary.json"
    if not feedback_path.exists():
        write_json(feedback_path, {
            "schema_version": "1.0",
            "description": "community-manager 시청자 피드백 요약",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "channels": {
                "CH1": {"pending_comments": 0, "escalated": 0},
                "CH2": {"pending_comments": 0, "escalated": 0},
                "CH3": {"pending_comments": 0, "escalated": 0},
                "CH4": {"pending_comments": 0, "escalated": 0},
                "CH5": {"pending_comments": 0, "escalated": 0},
                "CH6": {"pending_comments": 0, "escalated": 0},
                "CH7": {"pending_comments": 0, "escalated": 0},
            },
            "topic_suggestions": [],
            "last_scan": None,
        })
        print("[OK] data/community/feedback_summary.json 초기화")
    else:
        print("[SKIP] data/community/feedback_summary.json 이미 존재")


def init_research_data() -> None:
    """data/research/ 초기화 — research-lead SSOT."""
    research_dir = ROOT / "data" / "research"
    benchmarks_dir = research_dir / "benchmarks"
    benchmarks_dir.mkdir(parents=True, exist_ok=True)

    index_path = research_dir / "tech_radar.json"
    if not index_path.exists():
        write_json(index_path, {
            "schema_version": "1.0",
            "description": "research-lead AI 기술 레이더",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "technologies": {
                "adopt": [],
                "trial": [],
                "assess": ["Veo", "Sora", "Suno", "Runway", "HeyGen"],
                "hold": [],
            },
            "monthly_report": None,
            "last_scan": None,
        })
        print("[OK] data/research/tech_radar.json 초기화")
    else:
        print("[SKIP] data/research/tech_radar.json 이미 존재")


def main() -> None:
    print("[v8.0 SSOT 초기화 시작]")
    init_sre_data()
    init_mlops_data()
    init_security_data()
    init_etl_data()
    init_community_data()
    init_research_data()
    print("\n[OK] v8.0 SSOT 초기화 완료")
    print("  - data/sre/              — sre-engineer SLO·런북")
    print("  - data/mlops/            — mlops-engineer 모델 이력")
    print("  - data/security/audit/   — security-engineer 감사 로그")
    print("  - data/etl/              — data-engineer ETL 스케줄")
    print("  - data/community/        — community-manager 시청자 피드백")
    print("  - data/research/         — research-lead AI 기술 레이더")


if __name__ == "__main__":
    main()
