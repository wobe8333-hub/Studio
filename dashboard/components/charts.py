"""공통 차트 컴포넌트 — Plotly 래퍼."""

from typing import List, Dict, Any


def kpi_card(label: str, value: str, delta: str = "", color: str = "#4CAF50"):
    """KPI 카드 HTML."""
    delta_html = f'<span style="color:{color}; font-size:0.9em">{delta}</span>' if delta else ""
    return f"""
    <div style="background:#1E1E2E; border-radius:10px; padding:16px; text-align:center; border:1px solid #333">
        <div style="color:#888; font-size:0.85em">{label}</div>
        <div style="color:#FFF; font-size:1.8em; font-weight:bold">{value}</div>
        {delta_html}
    </div>
    """


def channel_bar_chart(channel_data: Dict[str, float], title: str):
    """채널별 수평 막대차트."""
    try:
        import plotly.graph_objects as go

        channels = list(channel_data.keys())
        values = list(channel_data.values())
        colors = ["#4CAF50" if v > 0 else "#F44336" for v in values]

        fig = go.Figure(go.Bar(
            x=values,
            y=channels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f}" for v in values],
            textposition="inside",
        ))
        fig.update_layout(
            title=title,
            paper_bgcolor="#1E1E2E",
            plot_bgcolor="#2A2A3E",
            font_color="#CCC",
            height=300,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig
    except ImportError:
        return None


def trend_score_chart(topics: List[Dict], title: str = "트렌드 주제 점수"):
    """트렌드 주제 점수 차트."""
    try:
        import plotly.graph_objects as go

        if not topics:
            return None

        labels = [t.get("original_topic", t.get("topic", ""))[:20] for t in topics[:10]]
        scores = [t.get("score", 0) for t in topics[:10]]
        colors = []
        for s in scores:
            if s >= 80:
                colors.append("#4CAF50")
            elif s >= 60:
                colors.append("#FFC107")
            else:
                colors.append("#F44336")

        fig = go.Figure(go.Bar(
            y=labels,
            x=scores,
            orientation="h",
            marker_color=colors,
            text=scores,
            textposition="outside",
        ))
        fig.update_layout(
            title=title,
            xaxis_range=[0, 100],
            paper_bgcolor="#1E1E2E",
            plot_bgcolor="#2A2A3E",
            font_color="#CCC",
            height=max(300, len(labels) * 30),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig
    except ImportError:
        return None


def revenue_gauge(current: int, target: int, channel_id: str):
    """수익 달성률 게이지."""
    try:
        import plotly.graph_objects as go

        pct = min(100, current / max(target, 1) * 100)
        color = "#4CAF50" if pct >= 80 else "#FFC107" if pct >= 50 else "#F44336"

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=pct,
            number={"suffix": "%", "font": {"color": "#FFF"}},
            delta={"reference": 80, "valueformat": ".1f"},
            title={"text": f"{channel_id} 목표 달성률", "font": {"color": "#CCC"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#CCC"},
                "bar": {"color": color},
                "bgcolor": "#2A2A3E",
                "steps": [
                    {"range": [0, 50], "color": "#1E1E2E"},
                    {"range": [50, 80], "color": "#2A2A3E"},
                ],
                "threshold": {
                    "line": {"color": "#4CAF50", "width": 2},
                    "thickness": 0.75,
                    "value": 80,
                },
            },
        ))
        fig.update_layout(
            paper_bgcolor="#1E1E2E",
            font_color="#CCC",
            height=250,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        return fig
    except ImportError:
        return None
