"""대시보드 — 전체 KPI + 파이프라인 상태."""

import streamlit as st
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import (
    CHANNELS_DIR, RUNS_DIR, CHANNEL_CATEGORIES, CHANNEL_CATEGORY_KO,
    REVENUE_TARGET_PER_CHANNEL, REVENUE_TARGET_TOTAL,
)
from dashboard.components.charts import kpi_card, channel_bar_chart, revenue_gauge


def _load_channel_stats(channel_id: str) -> dict:
    """채널별 최신 KPI 데이터 로드."""
    stats = {
        "channel_id": channel_id,
        "category_ko": CHANNEL_CATEGORY_KO.get(channel_id, ""),
        "subscribers": 0,
        "total_views": 0,
        "revenue_month": 0,
        "video_count": 0,
    }

    # algorithm_policy에서 기본 정보
    ap = CHANNELS_DIR / channel_id / "algorithm_policy.json"
    if ap.exists():
        try:
            data = json.loads(ap.read_text(encoding="utf-8"))
            stats["_policy"] = True
        except Exception:
            pass

    # runs/ 에서 최근 실행 영상 수 카운트
    runs_ch = RUNS_DIR / channel_id
    if runs_ch.exists():
        stats["video_count"] = sum(1 for _ in runs_ch.iterdir() if _.is_dir())

    return stats


def render():
    st.title("📊 KAS 전체 채널 KPI 대시보드")

    CHANNEL_IDS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]

    # ── 전체 요약 카드 ────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(kpi_card("총 채널 수", "7개", "운영 중"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("월 수익 목표", "1,400만원", "7채널 합산"), unsafe_allow_html=True)
    with col3:
        total_videos = sum(
            len(list((RUNS_DIR / ch).iterdir())) if (RUNS_DIR / ch).exists() else 0
            for ch in CHANNEL_IDS
        )
        st.markdown(kpi_card("총 생성 영상", f"{total_videos}편", "누적"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("월 목표 달성률", "—", "데이터 수집 중"), unsafe_allow_html=True)

    st.divider()

    # ── 채널별 현황 ────────────────────────────────────────────────
    st.subheader("📺 채널별 현황")
    cols = st.columns(7)
    for i, ch in enumerate(CHANNEL_IDS):
        stats = _load_channel_stats(ch)
        with cols[i]:
            st.metric(
                label=f"{ch}\n{stats['category_ko']}",
                value=f"{stats['video_count']}편",
                delta="생성 완료",
            )

    st.divider()

    # ── 파이프라인 상태 ────────────────────────────────────────────
    st.subheader("⚙️ 파이프라인 실행 상태")
    st.caption("manifest.json 기반 최신 실행 현황 (5초마다 자동 갱신)")

    STATE_ICON = {
        "COMPLETED": "✅",
        "RUNNING":   "🔄",
        "FAILED":    "❌",
        "UNKNOWN":   "⬜",
    }
    STEP_LABELS = ["step08", "step09", "step10", "step11", "step12"]

    for ch in CHANNEL_IDS:
        runs_ch = RUNS_DIR / ch
        if not runs_ch.exists():
            st.text(f"⬜ {ch} — 실행 기록 없음")
            continue

        run_dirs = sorted([d for d in runs_ch.iterdir() if d.is_dir()])
        if not run_dirs:
            st.text(f"⬜ {ch} — 실행 기록 없음")
            continue

        latest = run_dirs[-1]
        manifest_path = latest / "manifest.json"
        run_state = "UNKNOWN"
        steps_completed = []
        topic_title = ""
        if manifest_path.exists():
            try:
                m = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                run_state = m.get("run_state", "UNKNOWN")
                steps_completed = m.get("steps_completed", [])
                topic_title = m.get("topic", {}).get("reinterpreted_title", "")[:40]
            except Exception:
                pass

        icon = STATE_ICON.get(run_state, "⬜")
        step_badges = " ".join(
            f"[{s.replace('step', 'S')}✓]" if s in steps_completed else f"[{s.replace('step', 'S')}]"
            for s in STEP_LABELS
        )
        steps_done = len([s for s in STEP_LABELS if s in steps_completed])
        pct = int(steps_done / len(STEP_LABELS) * 100)

        col1, col2 = st.columns([2, 5])
        with col1:
            st.markdown(f"**{icon} {ch}** `{CHANNEL_CATEGORY_KO.get(ch, '')}`")
            st.caption(f"{latest.name}")
        with col2:
            st.progress(pct / 100, text=f"{step_badges} — {pct}%")
            if topic_title:
                st.caption(f"주제: {topic_title}")

    # ── 새로고침 ────────────────────────────────────────────────────
    if st.button("🔄 새로고침"):
        st.rerun()
