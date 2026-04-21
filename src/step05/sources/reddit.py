"""
Reddit API 소스 (Layer 3 — 주간)
카테고리별 서브레딧 핫토픽 수집 (PRAW 라이브러리)
"""

import os
from typing import Any, Dict, List

# 7채널 카테고리별 서브레딧 매핑
_SUBREDDIT_MAP: Dict[str, List[str]] = {
    "economy":      ["finance", "economics", "investing", "korea"],
    "realestate":   ["RealEstate", "realestateinvesting", "PersonalFinanceKorea"],
    "psychology":   ["psychology", "selfimprovement", "mentalhealth", "getdisciplined"],
    "mystery":      ["UnsolvedMysteries", "mystery", "creepy", "Unexplained"],
    "war_history":  ["MilitaryHistory", "WarCollege", "history", "ww2"],
    "science":      ["science", "space", "physics", "biology", "Futurology"],
    "history":      ["history", "AskHistorians", "ArtefactPorn", "worldhistory"],
}


def _load_credentials():
    return (
        os.getenv("REDDIT_CLIENT_ID", "").strip(),
        os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
        os.getenv("REDDIT_USER_AGENT", "KAS-TrendBot/2.0").strip(),
    )


def fetch_reddit_topics(
    category: str,
    limit: int = 25,
    time_filter: str = "week",
) -> Dict[str, Any]:
    """
    카테고리별 서브레딧 핫/탑 포스트 제목 수집

    Args:
        category: 채널 카테고리 (economy, mystery, ...)
        limit: 수집할 포스트 수
        time_filter: 'day' | 'week' | 'month'

    Returns:
        {
            "topics": List[str],
            "scores": Dict[str, float],  — 업보트 기반 정규화
            "source": "reddit",
            "configured": bool,
            "subreddits_used": List[str],
            "error": Optional[str]
        }
    """
    try:
        import praw
    except ImportError:
        return {
            "topics": [],
            "scores": {},
            "source": "reddit",
            "configured": False,
            "subreddits_used": [],
            "error": "praw not installed",
        }

    client_id, client_secret, user_agent = _load_credentials()
    if not client_id or not client_secret:
        return {
            "topics": [],
            "scores": {},
            "source": "reddit",
            "configured": False,
            "subreddits_used": [],
            "error": "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 미설정",
        }

    subreddits = _SUBREDDIT_MAP.get(category, ["worldnews"])
    topics: List[str] = []
    scores: Dict[str, float] = {}
    errors: List[str] = []
    all_posts = []

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        for subreddit_name in subreddits[:3]:  # 최대 3개 서브레딧
            try:
                sub = reddit.subreddit(subreddit_name)
                for post in sub.top(time_filter=time_filter, limit=limit // len(subreddits[:3]) + 1):
                    all_posts.append({
                        "title": post.title,
                        "score": post.score,
                        "subreddit": subreddit_name,
                    })
            except Exception as e:
                errors.append(f"r/{subreddit_name}: {str(e)[:100]}")

    except Exception as e:
        return {
            "topics": [],
            "scores": {},
            "source": "reddit",
            "configured": True,
            "subreddits_used": subreddits,
            "error": f"Reddit 연결 실패: {str(e)[:200]}",
        }

    # 업보트 기반 점수 정규화
    if all_posts:
        max_score = max(p["score"] for p in all_posts) or 1
        for post in all_posts:
            title = post["title"]
            topics.append(title)
            scores[title] = round(min(1.0, post["score"] / max_score), 3)

    return {
        "topics": topics[:50],
        "scores": scores,
        "source": "reddit",
        "configured": True,
        "subreddits_used": subreddits,
        "error": "; ".join(errors) if errors else None,
    }
