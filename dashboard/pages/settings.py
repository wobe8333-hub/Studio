"""대시보드 — 설정 관리 (API 키 상태, 쿼터, 채널 on/off)."""

import streamlit as st
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import (
    GEMINI_API_KEY, YOUTUBE_API_KEY, TAVILY_API_KEY, PERPLEXITY_API_KEY,
    ELEVENLABS_API_KEY, SERPAPI_KEY, NAVER_CLIENT_ID, SENTRY_DSN,
    QUOTA_DIR,
)


def _check_api_status() -> dict:
    """API 키 설정 상태 확인."""
    return {
        "Gemini API":        bool(GEMINI_API_KEY),
        "YouTube Data API":  bool(YOUTUBE_API_KEY),
        "Tavily AI Search":  bool(TAVILY_API_KEY),
        "Perplexity API":    bool(PERPLEXITY_API_KEY),
        "ElevenLabs TTS":    bool(ELEVENLABS_API_KEY),
        "SerpAPI":           bool(SERPAPI_KEY),
        "Naver Search API":  bool(NAVER_CLIENT_ID),
        "Sentry 모니터링":    bool(SENTRY_DSN),
    }


def _load_quota_status() -> dict:
    """일일 쿼터 사용 현황 로드."""
    quotas = {}
    for quota_file in ["gemini_quota_daily.json", "youtube_quota_daily.json"]:
        qf = QUOTA_DIR / quota_file
        if qf.exists():
            import json
            try:
                data = json.loads(qf.read_text(encoding="utf-8"))
                quotas[quota_file.replace("_daily.json", "")] = data
            except Exception:
                pass
    return quotas


def render():
    st.title("⚙️ KAS 설정 관리")

    # ── API 키 상태 ────────────────────────────────────────────────
    st.subheader("🔑 API 키 상태")
    api_status = _check_api_status()

    col1, col2 = st.columns(2)
    items = list(api_status.items())
    for i, (name, ok) in enumerate(items):
        with (col1 if i % 2 == 0 else col2):
            icon = "✅" if ok else "❌"
            status = "설정됨" if ok else "미설정"
            color = "green" if ok else "red"
            st.markdown(f"{icon} **{name}** — :{color}[{status}]")

    st.info("API 키는 `.env` 파일에서 관리합니다.")

    st.divider()

    # ── 쿼터 사용 현황 ─────────────────────────────────────────────
    st.subheader("📊 오늘의 쿼터 사용 현황")
    quotas = _load_quota_status()

    if quotas:
        for quota_name, data in quotas.items():
            with st.expander(f"{quota_name} 쿼터"):
                daily_limit = data.get("daily_total_limit") or data.get("daily_limit") or 1000
                used_keys = [k for k in data if "calls" in k or "uploads" in k or "requests" in k]
                for key in used_keys:
                    val = data.get(key, 0)
                    pct = min(1.0, val / max(daily_limit, 1))
                    st.progress(pct, text=f"{key}: {val} / {daily_limit}")
    else:
        st.info("쿼터 데이터 없음")

    st.divider()

    # ── 채널 활성화 상태 ───────────────────────────────────────────
    st.subheader("📺 채널 활성화 관리")
    from src.core.config import CHANNEL_CATEGORY_KO, CHANNEL_LAUNCH_PHASE

    CHANNEL_IDS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]
    cols = st.columns(7)
    for i, ch in enumerate(CHANNEL_IDS):
        with cols[i]:
            phase = CHANNEL_LAUNCH_PHASE.get(ch, 3)
            cat = CHANNEL_CATEGORY_KO.get(ch, "")
            active = phase <= 2  # Phase 1, 2만 활성

            st.checkbox(
                f"{ch}\n{cat}",
                value=active,
                key=f"ch_active_{ch}",
                help=f"론칭 Phase {phase}",
                disabled=True,  # 읽기 전용 (실제 변경은 config에서)
            )
