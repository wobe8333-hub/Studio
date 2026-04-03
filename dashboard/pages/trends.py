"""대시보드 — 트렌드 주제 관리 (실시간 수집 결과 + 승인/거부).
F-2: 승인/거부 파이프라인 연동 — assets.jsonl 직접 수정.
"""

import streamlit as st
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import KNOWLEDGE_DIR, CHANNEL_CATEGORIES, CHANNEL_CATEGORY_KO
from dashboard.components.charts import trend_score_chart

_ASSETS_FILENAME = "assets.jsonl"


def _get_assets_path(channel_id: str) -> Path:
    return KNOWLEDGE_DIR / channel_id / "discovery" / "raw" / _ASSETS_FILENAME


def _load_topics(channel_id: str) -> list:
    """knowledge_store에서 채널 트렌드 주제 로드."""
    assets_path = _get_assets_path(channel_id)
    if not assets_path.exists():
        return []
    topics = []
    try:
        for line in assets_path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                topics.append(json.loads(line))
    except Exception:
        pass
    return sorted(topics, key=lambda x: -x.get("score", 0))


def _save_topics(channel_id: str, topics: list) -> None:
    """수정된 주제 목록을 assets.jsonl에 저장 (점수 내림차순)."""
    assets_path = _get_assets_path(channel_id)
    assets_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(t, ensure_ascii=False) for t in topics]
    assets_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_topic_grade(channel_id: str, topic_original: str, new_grade: str) -> bool:
    """original_topic 기준으로 특정 주제의 grade를 변경한다."""
    topics = _load_topics(channel_id)
    updated = False
    for t in topics:
        if t.get("original_topic") == topic_original or t.get("reinterpreted_title") == topic_original:
            t["grade"] = new_grade
            updated = True
    if updated:
        _save_topics(channel_id, topics)
    return updated


def render(channel_id: str):
    category_ko = CHANNEL_CATEGORY_KO.get(channel_id, "")
    st.title(f"🔍 {channel_id} ({category_ko}) 트렌드 주제 관리")

    topics = _load_topics(channel_id)

    if not topics:
        st.info("수집된 주제가 없습니다. 트렌드 수집을 먼저 실행하세요.")
        if st.button("▶️ 트렌드 수집 실행"):
            with st.spinner("수집 중..."):
                try:
                    from src.step05.knowledge_store import run_step05
                    from src.core.config import CHANNEL_MONTHLY_TARGET
                    result = run_step05(channel_id, CHANNEL_MONTHLY_TARGET.get(channel_id, 10))
                    st.success(f"{len(result)}개 주제 수집 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"수집 실패: {e}")
        return

    # ── 차트 ─────────────────────────────────────────────────────
    fig = trend_score_chart(topics, f"{channel_id} 트렌드 점수")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # ── 주제 목록 + 승인/거부 ─────────────────────────────────────
    st.subheader(f"📋 수집된 주제 ({len(topics)}개)")

    grade_filter = st.selectbox(
        "등급 필터",
        ["전체", "auto (자동승격)", "review (리뷰대기)", "reject (폐기)"],
    )

    for i, topic in enumerate(topics):
        grade = topic.get("grade", "unknown")
        score = topic.get("score", 0)

        # 필터 적용
        if grade_filter != "전체" and not grade_filter.startswith(grade):
            continue

        # 등급별 색상
        if grade == "auto":
            badge = "🟢 자동승격"
        elif grade == "review":
            badge = "🟡 리뷰대기"
        else:
            badge = "🔴 폐기"

        title = topic.get("reinterpreted_title") or topic.get("original_topic", "")

        with st.expander(f"{badge} [{score:.0f}점] {title}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"원본 주제: {topic.get('original_topic', '')}")
                st.text(f"카테고리: {topic.get('category', '')}")
                st.text(f"수집: {topic.get('collected_at', '')[:19]}")
                st.text(f"현재 등급: {grade}")
            with col2:
                topic_key = topic.get("original_topic", title)
                if grade != "auto":
                    if st.button("✅ 승인", key=f"approve_{channel_id}_{i}"):
                        if _update_topic_grade(channel_id, topic_key, "auto"):
                            st.success("✅ 자동승격(auto)으로 변경됨")
                            st.rerun()
                        else:
                            st.error("업데이트 실패")
                if grade != "reject":
                    if st.button("❌ 거부", key=f"reject_{channel_id}_{i}"):
                        if _update_topic_grade(channel_id, topic_key, "reject"):
                            st.warning("❌ 폐기(reject)로 변경됨")
                            st.rerun()
                        else:
                            st.error("업데이트 실패")
