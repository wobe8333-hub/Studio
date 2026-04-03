"""대시보드 — API 비용 추적.
F-5: 채널/실행별 Gemini/YouTube API 비용 시각화.
"""

import streamlit as st
from pathlib import Path
import json
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import RUNS_DIR, GLOBAL_DIR, CHANNEL_CATEGORY_KO
from src.quota.gemini_quota import get_quota as get_gemini_quota
from src.quota.youtube_quota import get_quota as get_youtube_quota

CHANNEL_IDS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]


def _load_run_cost(channel_id: str, run_id: str) -> dict:
    """runs/{ch}/{run_id}/cost.json 로드."""
    cost_path = RUNS_DIR / channel_id / run_id / "cost.json"
    if not cost_path.exists():
        return {}
    try:
        return json.loads(cost_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _collect_channel_costs(channel_id: str) -> list:
    """채널의 모든 run에서 비용 데이터 수집."""
    runs_ch = RUNS_DIR / channel_id
    if not runs_ch.exists():
        return []
    costs = []
    for run_dir in sorted(runs_ch.iterdir()):
        if not run_dir.is_dir():
            continue
        cost = _load_run_cost(channel_id, run_dir.name)
        if cost:
            costs.append({"run_id": run_dir.name, **cost})
    return costs


def render():
    st.title("💸 API 비용 추적 대시보드")

    # ── 오늘 Gemini 쿼터 현황 ────────────────────────────────────
    st.subheader("🤖 Gemini API 오늘 사용량")
    try:
        gq = get_gemini_quota()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 요청 수", f"{gq.get('total_requests', 0):,}회")
        with col2:
            st.metric("이미지 생성", f"{gq.get('images_generated', 0):,}장")
        with col3:
            hit_rate = gq.get("cache_hit_rate", 0.0)
            st.metric("캐시 히트율", f"{hit_rate * 100:.1f}%",
                      delta=f"절감 {gq.get('cost_saved_by_cache_krw', 0):,.0f}원")
        with col4:
            rpm_peak = gq.get("rpm_peak", 0)
            st.metric("RPM 피크", f"{rpm_peak:.1f}rpm")
        with st.expander("상세 보기"):
            st.json({
                k: v for k, v in gq.items()
                if k not in ("rpm_timestamps",)
            })
    except Exception as e:
        st.warning(f"Gemini 쿼터 로드 실패: {e}")

    st.divider()

    # ── YouTube 쿼터 현황 ─────────────────────────────────────────
    st.subheader("📺 YouTube API 오늘 쿼터")
    try:
        yq = get_youtube_quota()
        col1, col2, col3 = st.columns(3)
        with col1:
            used = yq.get("quota_used", 0)
            limit = yq.get("quota_limit", 10000)
            st.metric("사용량", f"{used:,} / {limit:,}",
                      delta=f"잔여 {yq.get('quota_remaining', limit - used):,}")
        with col2:
            deferred = len(yq.get("deferred_jobs", []))
            st.metric("이연된 업로드", f"{deferred}건")
        with col3:
            pct = round(used / limit * 100, 1) if limit else 0
            st.metric("쿼터 소진율", f"{pct}%")
        st.progress(min(used / limit, 1.0) if limit else 0, text=f"{pct}% 소진")
        if yq.get("deferred_jobs"):
            with st.expander(f"이연된 업로드 {deferred}건"):
                for job in yq["deferred_jobs"]:
                    st.text(f"• {job.get('channel_id', '?')}/{job.get('run_id', '?')}"
                            f" — {job.get('deferred_at', '')[:19]}")
    except Exception as e:
        st.warning(f"YouTube 쿼터 로드 실패: {e}")

    st.divider()

    # ── 채널별 누적 비용 ──────────────────────────────────────────
    st.subheader("📊 채널별 누적 API 비용")
    channel_totals = {}
    for ch in CHANNEL_IDS:
        costs = _collect_channel_costs(ch)
        total_krw = 0
        for c in costs:
            # gemini_api 항목 합산
            gapi = c.get("gemini_api", {})
            for k, v in gapi.items():
                if isinstance(v, dict):
                    total_krw += v.get("cost_krw", 0) or 0
        channel_totals[ch] = {"total_krw": total_krw, "run_count": len(costs)}

    col_headers = st.columns(7)
    for i, ch in enumerate(CHANNEL_IDS):
        with col_headers[i]:
            cat = CHANNEL_CATEGORY_KO.get(ch, "")
            total = channel_totals[ch]["total_krw"]
            runs = channel_totals[ch]["run_count"]
            st.metric(f"{ch}\n{cat}", f"{total:,.0f}원",
                      delta=f"{runs}회 실행")

    st.divider()

    # ── 채널별 최근 실행 비용 상세 ────────────────────────────────
    st.subheader("🔍 채널 선택 → 실행별 비용 상세")
    selected_ch = st.selectbox("채널 선택", CHANNEL_IDS)
    costs = _collect_channel_costs(selected_ch)

    if not costs:
        st.info(f"{selected_ch}: 비용 기록 없음")
    else:
        for c in reversed(costs[-10:]):  # 최근 10건
            run_id = c.get("run_id", "")
            gapi = c.get("gemini_api", {})
            script_cost = gapi.get("script_generation", {}).get("cost_krw", 0) or 0
            image_cost = gapi.get("image_generation", {}).get("cost_krw", 0) or 0
            total = sum(
                v.get("cost_krw", 0) or 0
                for v in gapi.values() if isinstance(v, dict)
            )
            with st.expander(f"{run_id} — 총 {total:,.2f}원"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("스크립트 생성", f"{script_cost:,.2f}원")
                with c2:
                    st.metric("이미지 생성", f"{image_cost:,.2f}원")
                with c3:
                    st.metric("합계", f"{total:,.2f}원")
