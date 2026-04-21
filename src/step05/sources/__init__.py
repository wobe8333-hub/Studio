"""
Step05 트렌드 수집 소스 패키지
각 소스 모듈은 독립적으로 동작하며, trend_collector.py에서 오케스트레이션됩니다.

Layer 1 (실시간): google_trends, naver
Layer 2 (일간):   youtube_trending, rss
Layer 3 (주간):   reddit, community
Layer 4 (월간):   arxiv, scholar, nasa
Layer 5 (에버그린): wikipedia, curated
"""

# Layer 1 — 실시간
# Layer 4 — 월간
from src.step05.sources.arxiv import fetch_arxiv_papers
from src.step05.sources.community import fetch_community_topics
from src.step05.sources.curated import fetch_curated_topics
from src.step05.sources.google_trends import fetch_trends_scores
from src.step05.sources.nasa import fetch_nasa_data
from src.step05.sources.naver import fetch_naver_trends as fetch_naver_topics

# Layer 3 — 주간
from src.step05.sources.reddit import fetch_reddit_topics
from src.step05.sources.rss import fetch_news_context
from src.step05.sources.scholar import fetch_scholar_papers

# Layer 5 — 에버그린
from src.step05.sources.wikipedia import expand_keywords

# Layer 2 — 일간
from src.step05.sources.youtube_trending import fetch_youtube_trending

__all__ = [
    # Layer 1
    "fetch_trends_scores",
    "fetch_naver_topics",
    # Layer 2
    "fetch_youtube_trending",
    "fetch_news_context",
    # Layer 3
    "fetch_reddit_topics",
    "fetch_community_topics",
    # Layer 4
    "fetch_arxiv_papers",
    "fetch_scholar_papers",
    "fetch_nasa_data",
    # Layer 5
    "expand_keywords",
    "fetch_curated_topics",
]
