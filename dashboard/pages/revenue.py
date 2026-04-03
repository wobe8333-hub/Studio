"""대시보드 — 채널별 수익 추적.
F-1: revenue_monthly.json 실데이터 연동.
"""

import streamlit as st
from pathlib import Path
import json
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import (
    CHANNELS_DIR, CHANNEL_CATEGORY_KO,
    REVENUE_TARGET_PER_CHANNEL, REVENUE_TARGET_TOTAL,
    CHANNEL_RPM_PROXY,
)
from dashboard.components.charts import channel_bar_chart, revenue_gauge

CHANNEL_IDS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]


def _load_revenue_policy(channel_id: str) -> dict:
    """채널 수익 정책(정적 설정) 로드."""
    rp_path = CHANNELS_DIR / channel_id / "revenue_policy.json"
    if rp_path.exists():
        try:
            return json.loads(rp_path.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {}


def _load_monthly_actuals(channel_id: str, month_str: str) -> dict:
    """revenue_monthly.json에서 해당 월 실적 로드.

    Returns:
        {"net_profit": int, "total_revenue": int, "target_achieved": bool}
    """
    rm_path = CHANNELS_DIR / channel_id / "revenue_monthly.json"
    if not rm_path.exists():
        return {}
    try:
        data = json.loads(rm_path.read_text(encoding="utf-8-sig"))
        return data.get("monthly_records", {}).get(month_str, {})
    except Exception:
        return {}


def _load_all_months(channel_id: str) -> dict:
    """revenue_monthly.json 전체 월별 기록 반환."""
    rm_path = CHANNELS_DIR / channel_id / "revenue_monthly.json"
    if not rm_path.exists():
        return {}
    try:
        data = json.loads(rm_path.read_text(encoding="utf-8-sig"))
        return data.get("monthly_records", {})
    except Exception:
        return {}


def render():
    st.title("💰 KAS 7채널 수익 추적")

    # 월 선택
    current_month = datetime.utcnow().strftime("%Y-%m")
    selected_month = st.text_input("조회 월 (YYYY-MM)", value=current_month)

    # ── 이번 달 실적 집계 ─────────────────────────────────────────
    total_actual = 0
    channel_actuals = {}
    for ch in CHANNEL_IDS:
        actuals = _load_monthly_actuals(ch, selected_month)
        net = actuals.get("net_profit", 0) or 0
        channel_actuals[ch] = {"net_profit": net, "actuals": actuals}
        total_actual += net

    achievement_pct = round(total_actual / REVENUE_TARGET_TOTAL * 100, 1) if REVENUE_TARGET_TOTAL else 0

    # ── 전체 목표 요약 ─────────────────────────────────────────────
    st.subheader(f"🎯 {selected_month} 월간 수익 현황")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("채널당 목표", f"{REVENUE_TARGET_PER_CHANNEL:,}원")
    with col2:
        st.metric("7채널 합산 목표", f"{REVENUE_TARGET_TOTAL:,}원")
    with col3:
        delta_color = "normal" if total_actual >= REVENUE_TARGET_TOTAL * 0.7 else "inverse"
        st.metric("실적 합산", f"{total_actual:,}원",
                  delta=f"목표 대비 {achievement_pct}%")
    with col4:
        achieved_count = sum(
            1 for ch in CHANNEL_IDS
            if channel_actuals[ch]["actuals"].get("target_achieved", False)
        )
        st.metric("목표 달성 채널", f"{achieved_count}/7개")

    st.divider()

    # ── 채널별 수익 바 차트 ────────────────────────────────────────
    st.subheader("📈 채널별 수익 현황")
    bar_data = {ch: channel_actuals[ch]["net_profit"] for ch in CHANNEL_IDS}
    fig = channel_bar_chart(bar_data, f"{selected_month} 채널별 순이익 (원)")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 채널별 수익 상세 ───────────────────────────────────────────
    st.subheader("🔍 채널별 수익 상세")

    cols = st.columns(2)
    for i, ch in enumerate(CHANNEL_IDS):
        policy = _load_revenue_policy(ch)
        category_ko = CHANNEL_CATEGORY_KO.get(ch, "")
        actuals = channel_actuals[ch]["actuals"]
        net = channel_actuals[ch]["net_profit"]

        with cols[i % 2]:
            target = policy.get("monthly_target_revenue", REVENUE_TARGET_PER_CHANNEL)
            achieved = actuals.get("target_achieved", False)
            badge = "✅" if achieved else "⏳"
            with st.expander(f"{badge} {ch} ({category_ko}) — {net:,}원 / {target:,}원"):
                c1, c2 = st.columns(2)
                with c1:
                    rpm = policy.get("rpm_proxy_krw", CHANNEL_RPM_PROXY.get(ch, 0))
                    st.metric("RPM 프록시", f"{rpm:,}원")
                    total_rev = actuals.get("total_revenue", 0) or 0
                    st.metric("총 수익", f"{total_rev:,}원")
                with c2:
                    adsense = actuals.get("adsense_krw", 0) or 0
                    affiliate = actuals.get("affiliate_krw", 0) or 0
                    st.metric("AdSense", f"{adsense:,}원")
                    st.metric("제휴", f"{affiliate:,}원")

                gauge_fig = revenue_gauge(net, target, ch)
                if gauge_fig:
                    st.plotly_chart(gauge_fig, use_container_width=True)

                # 월별 추이
                all_months = _load_all_months(ch)
                if all_months:
                    months_sorted = sorted(all_months.keys())[-6:]
                    trend_data = {m: (all_months[m].get("net_profit") or 0)
                                  for m in months_sorted}
                    trend_fig = channel_bar_chart(trend_data, "최근 6개월 순이익 추이")
                    if trend_fig:
                        st.plotly_chart(trend_fig, use_container_width=True)

    st.divider()

    # ── 수익 공식 설명 ─────────────────────────────────────────────
    with st.expander("📐 수익 공식 보기"):
        st.code("""
월 순이익 = AdSense + 제휴 + Shorts + 멤버십 - 운영비

수익원 비율 (목표 200만원/채널):
  AdSense Long-form (55%): 약 110만원
  제휴/스폰서 (20%): 약 40만원
  YouTube Shorts (15%): 약 30만원
  멤버십/슈퍼챗 (10%): 약 20만원

운영비: 약 15만원/월 (API 비용 + 인프라)
        """, language="text")
