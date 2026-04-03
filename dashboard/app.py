"""
KAS Dashboard — Streamlit 메인 앱.

실행: streamlit run dashboard/app.py

기능:
  - 7채널 KPI 대시보드
  - 트렌드 주제 관리 (수집 결과 + 승인/거부)
  - 수익 추적
  - 설정 관리 (API 키, 쿼터)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="KAS Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 다크 테마 커스텀 CSS
st.markdown("""
<style>
    .stApp { background-color: #13131F; }
    .sidebar .sidebar-content { background-color: #1E1E2E; }
    h1, h2, h3 { color: #E0E0FF; }
    .stMetric { background-color: #1E1E2E; padding: 12px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎬 KAS Studio")
    st.caption("Knowledge Animation Studio")
    st.divider()

    page = st.radio(
        "메뉴",
        ["📊 전체 KPI", "🔍 트렌드 관리", "💰 수익 추적", "💸 비용 추적", "⚙️ 설정"],
        key="nav_page",
    )

    if page == "🔍 트렌드 관리":
        from src.core.config import CHANNEL_CATEGORY_KO
        channel_id = st.selectbox(
            "채널 선택",
            ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"],
            format_func=lambda x: f"{x} ({CHANNEL_CATEGORY_KO.get(x, '')})",
        )
    else:
        channel_id = "CH1"

    st.divider()
    st.caption("🤖 KAS v2.2 — Phase A~F 완료")

# ── 메인 콘텐츠 ────────────────────────────────────────────────────
if page == "📊 전체 KPI":
    from dashboard.pages.overview import render
    render()

elif page == "🔍 트렌드 관리":
    from dashboard.pages.trends import render
    render(channel_id)

elif page == "💰 수익 추적":
    from dashboard.pages.revenue import render
    render()

elif page == "💸 비용 추적":
    from dashboard.pages.cost import render
    render()

elif page == "⚙️ 설정":
    from dashboard.pages.settings import render
    render()
