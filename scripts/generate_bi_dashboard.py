#!/usr/bin/env python3
"""
주간 BI 대시보드 생성 스크립트.
7채널 KPI, API 비용, 영업 펀널 데이터를 집계하여
data/bi/weekly_dashboard.json에 저장.
data-analyst 에이전트가 주 1회 호출하거나 수동 실행 가능.
실행: python scripts/generate_bi_dashboard.py [--period YYYY-WN]
"""
from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp949 콘솔에서 한글 출력 보장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.ssot import read_json, write_json  # noqa: E402


def get_current_period() -> str:
    """현재 연도-주차 반환 (예: 2026-W15)."""
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def collect_channel_kpi() -> dict:
    """7채널 최근 업로드 KPI 집계 (runs/에서 step12 응답 수집)."""
    kpi: dict[str, dict] = {}
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return kpi

    for ch_dir in sorted(runs_dir.iterdir()):
        if not ch_dir.is_dir() or not ch_dir.name.startswith("CH"):
            continue
        ch_id = ch_dir.name
        views_total = 0
        uploads = 0
        latest_run_date = None

        for run_dir in ch_dir.iterdir():
            if not run_dir.is_dir():
                continue
            yt_resp = run_dir / "step12" / "youtube_response.json"
            if not yt_resp.exists():
                continue
            try:
                data = read_json(yt_resp)
                if isinstance(data, dict):
                    views_total += data.get("views", 0)
                    uploads += 1
                    published = data.get("published_at", "")
                    if published and (not latest_run_date or published > latest_run_date):
                        latest_run_date = published
            except Exception:
                continue

        if uploads > 0:
            kpi[ch_id] = {
                "uploads": uploads,
                "views_total": views_total,
                "avg_views": round(views_total / uploads, 1),
                "latest_upload": latest_run_date,
            }

    return kpi


def collect_cost_summary() -> dict:
    """API 비용 집계 (gemini_quota_daily.json에서)."""
    result = {
        "gemini_api_usd": 0.0,
        "elevenlabs_usd": 0.0,
        "total_usd": 0.0,
        "cost_per_video_usd": 0.0,
    }
    gemini_quota = ROOT / "data" / "global" / "quota" / "gemini_quota_daily.json"
    if gemini_quota.exists():
        try:
            data = read_json(gemini_quota)
            if isinstance(data, dict):
                result["gemini_api_usd"] = round(float(data.get("total_cost_usd", 0.0)), 4)
        except Exception:
            pass
    result["total_usd"] = round(result["gemini_api_usd"] + result["elevenlabs_usd"], 4)
    return result


def collect_sales_funnel() -> dict:
    """영업 펀널 집계 (data/sales/leads.json에서)."""
    result = {"leads": 0, "proposals": 0, "contracts": 0, "conversion_rate_pct": 0.0}
    leads_path = ROOT / "data" / "sales" / "leads.json"
    if not leads_path.exists():
        return result
    try:
        leads = read_json(leads_path)
        if isinstance(leads, list):
            result["leads"] = len(leads)
            result["proposals"] = sum(
                1 for lead in leads
                if isinstance(lead, dict) and lead.get("status") in ("proposal", "contracted")
            )
            result["contracts"] = sum(
                1 for lead in leads
                if isinstance(lead, dict) and lead.get("status") == "contracted"
            )
            if result["leads"] > 0:
                result["conversion_rate_pct"] = round(
                    result["contracts"] / result["leads"] * 100, 1
                )
    except Exception:
        pass
    return result


def generate_insights(kpi: dict, cost: dict, funnel: dict) -> tuple[list[str], list[str]]:
    """데이터 기반 주요 인사이트 및 권장 사항 생성."""
    insights = []
    recommendations = []

    total_views = sum(ch.get("views_total", 0) for ch in kpi.values())
    if total_views > 0:
        insights.append(f"총 {len(kpi)}개 채널에서 {total_views:,}회 조회 집계")

    if cost["total_usd"] > 50:
        insights.append(f"API 비용 ${cost['total_usd']} — HITL 임계값($50) 초과")
        recommendations.append("finance-manager에게 비용 경보 전달 필요")

    if funnel["leads"] > 0 and funnel["contracts"] == 0:
        recommendations.append(f"{funnel['leads']}개 리드 중 수주 0건 — sales-manager 파이프라인 점검 필요")

    return insights, recommendations


def main(period: str | None = None) -> None:
    target_period = period or get_current_period()
    print(f"[BI 대시보드 생성] 기간: {target_period}")

    kpi = collect_channel_kpi()
    cost = collect_cost_summary()
    funnel = collect_sales_funnel()
    insights, recommendations = generate_insights(kpi, cost, funnel)

    dashboard = {
        "schema_version": "1.0",
        "period": target_period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_kpi": kpi,
        "cost_summary": cost,
        "sales_funnel": funnel,
        "key_insights": insights,
        "recommendations": recommendations,
    }

    output_path = ROOT / "data" / "bi" / "weekly_dashboard.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, dashboard)

    print("[OK] data/bi/weekly_dashboard.json 저장 완료")
    print(f"  - 채널 KPI: {len(kpi)}개 채널")
    print(f"  - API 비용: ${cost['total_usd']}")
    print(f"  - 영업 펀널: 리드 {funnel['leads']}건 / 수주 {funnel['contracts']}건")
    if insights:
        print(f"  - 인사이트: {len(insights)}건")
    if recommendations:
        print(f"  - 권장 사항: {len(recommendations)}건")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAS 주간 BI 대시보드 생성")
    parser.add_argument("--period", type=str, help="기간 (YYYY-WN, 기본: 이번 주)")
    args = parser.parse_args()
    main(period=args.period)
