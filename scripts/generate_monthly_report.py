#!/usr/bin/env python3
"""
월간 경영 리포트 생성 스크립트.
4개 데이터 소스를 집계하여 data/exec/monthly_report.json에 저장.
ceo 에이전트가 매월 말 호출하거나 수동 실행 가능.
실행: python scripts/generate_monthly_report.py [--month YYYY-MM]
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


def get_target_month(month_str: str | None) -> str:
    """YYYY-MM 형식의 대상 월 반환. None이면 이번 달."""
    if month_str:
        return month_str
    return datetime.now().strftime("%Y-%m")


def collect_kas_kpi(month: str) -> dict:
    """KAS 7채널 KPI 집계 (step12 유튜브 응답에서 추출)."""
    kpi: dict[str, dict] = {}
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return kpi

    for ch_dir in sorted(runs_dir.iterdir()):
        if not ch_dir.is_dir() or not ch_dir.name.startswith("CH"):
            continue
        ch_id = ch_dir.name
        views_total, videos_count = 0, 0

        for run_dir in ch_dir.iterdir():
            if not run_dir.is_dir():
                continue
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = read_json(manifest_path)
                run_month = str(manifest.get("month", "")).zfill(2)
                run_year = str(manifest.get("year", ""))
                if f"{run_year}-{run_month}" != month:
                    continue
                # step12 유튜브 응답에서 뷰 카운트 추출
                yt_resp = run_dir / "step12" / "youtube_response.json"
                if yt_resp.exists():
                    yt_data = read_json(yt_resp)
                    views_total += yt_data.get("views", 0) if isinstance(yt_data, dict) else 0
                    videos_count += 1
            except Exception:
                continue

        if videos_count > 0:
            kpi[ch_id] = {
                "videos_uploaded": videos_count,
                "views_total": views_total,
                "avg_views_per_video": round(views_total / videos_count, 1),
            }
    return kpi


def collect_finance(month: str) -> dict:
    """재무 데이터 집계 (invoices + quota 비용)."""
    result = {
        "revenue_client_krw": 0,
        "api_cost_usd": 0.0,
        "api_cost_krw": 0,
    }

    # 청구서에서 수주 수익 집계
    invoices_path = ROOT / "data" / "finance" / "invoices.json"
    if invoices_path.exists():
        try:
            invoices = read_json(invoices_path)
            if isinstance(invoices, list):
                for inv in invoices:
                    if not isinstance(inv, dict):
                        continue
                    paid_at = inv.get("paid_at") or ""
                    if paid_at.startswith(month) and inv.get("status") == "paid":
                        result["revenue_client_krw"] += inv.get("total_krw", 0)
        except Exception:
            pass

    # Gemini API 비용 추계
    gemini_quota = ROOT / "data" / "global" / "quota" / "gemini_quota_daily.json"
    if gemini_quota.exists():
        try:
            quota_data = read_json(gemini_quota)
            if isinstance(quota_data, dict):
                # 일간 비용 합산 (month 필터는 단순 구현)
                cost = quota_data.get("total_cost_usd", 0.0)
                result["api_cost_usd"] = round(float(cost), 4)
        except Exception:
            pass

    # USD → KRW 변환 (config에서 환율 로드 시도)
    try:
        import os
        usd_to_krw = float(os.environ.get("USD_TO_KRW", "1350"))
        result["api_cost_krw"] = round(result["api_cost_usd"] * usd_to_krw)
    except Exception:
        result["api_cost_krw"] = round(result["api_cost_usd"] * 1350)

    return result


def collect_sales_pipeline(month: str) -> dict:
    """영업 파이프라인 현황 집계."""
    result = {"new_leads": 0, "contracts": 0, "total_contracted_krw": 0}
    leads_path = ROOT / "data" / "sales" / "leads.json"
    if not leads_path.exists():
        return result
    try:
        leads = read_json(leads_path)
        if isinstance(leads, list):
            for lead in leads:
                if not isinstance(lead, dict):
                    continue
                if str(lead.get("created_at", "")).startswith(month):
                    result["new_leads"] += 1
                if lead.get("status") == "contracted":
                    if str(lead.get("updated_at", "")).startswith(month):
                        result["contracts"] += 1
                        result["total_contracted_krw"] += lead.get("estimated_value", 0)
    except Exception:
        pass
    return result


def main(month: str | None = None) -> None:
    target_month = get_target_month(month)
    print(f"[월간 리포트 생성] 대상 월: {target_month}")

    # 데이터 집계
    kas_kpi = collect_kas_kpi(target_month)
    finance = collect_finance(target_month)
    sales = collect_sales_pipeline(target_month)

    # 총 수익 계산 (KAS AdSense는 현재 데이터 없으므로 0으로 표기)
    total_revenue_krw = finance["revenue_client_krw"]  # AdSense 별도 추가 필요
    net_profit_krw = total_revenue_krw - finance["api_cost_krw"]
    profit_margin = (
        round(net_profit_krw / total_revenue_krw * 100, 1) if total_revenue_krw > 0 else 0.0
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "month": target_month,
        "kas_channel_kpi": kas_kpi,
        "sales_pipeline": sales,
        "revenue": {
            "kas_adsense_krw": 0,  # AdSense 데이터는 step12 KPI 집계 후 별도 업데이트
            "client_projects_krw": finance["revenue_client_krw"],
            "total_krw": total_revenue_krw,
        },
        "cost": {
            "api_cost_usd": finance["api_cost_usd"],
            "api_cost_krw": finance["api_cost_krw"],
        },
        "net_profit_krw": net_profit_krw,
        "profit_margin_pct": profit_margin,
        "next_month_strategy": "",  # ceo가 채워 넣는 필드
    }

    # SSOT 저장
    report_path = ROOT / "data" / "exec" / "monthly_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, report)

    print("[OK] data/exec/monthly_report.json 저장 완료")
    print(f"  - KAS 채널 KPI: {len(kas_kpi)}개 채널")
    print(f"  - 외주 수익: {finance['revenue_client_krw']:,}원")
    print(f"  - API 비용: ${finance['api_cost_usd']} ({finance['api_cost_krw']:,}원)")
    print(f"  - 순이익: {net_profit_krw:,}원 (마진 {profit_margin}%)")
    print(f"  - 신규 리드: {sales['new_leads']}건 | 수주: {sales['contracts']}건")

    # API 비용 HITL 경고
    if finance["api_cost_usd"] > 50:
        print(f"\n[WARN] API 비용 ${finance['api_cost_usd']} > $50 임계값 초과!")
        print("  → finance-manager가 ceo에게 HITL 에스컬레이션 필요")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAS 월간 경영 리포트 생성")
    parser.add_argument("--month", type=str, help="대상 월 (YYYY-MM, 기본: 이번 달)")
    args = parser.parse_args()
    main(month=args.month)
