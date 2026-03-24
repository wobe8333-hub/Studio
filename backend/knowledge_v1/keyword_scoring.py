"""
Keyword Scoring - KR 트렌드 키워드 점수 계산 (base_score + 외부 신호 가중치)
"""

import os
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict

from backend.knowledge_v1.text_mining.ngram import normalize_text, extract_ngrams


def _recency_weight(date_str: Optional[str], collection_date_local: str) -> float:
    """
    최신성 가중치 계산
    
    Args:
        date_str: 업로드 날짜 (YYYY-MM-DD 또는 None)
        collection_date_local: 수집일 (YYYY-MM-DD)
    
    Returns:
        recency_weight: 0.0 ~ 1.0
    """
    if not date_str:
        return 0.1  # 날짜 없으면 최소 가중치
    
    try:
        # collection_date_local과 date_str을 datetime으로 변환
        collection_date = datetime.strptime(collection_date_local, "%Y-%m-%d")
        upload_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # 날짜 차이 (일)
        days_diff = (collection_date - upload_date).days
        
        if days_diff < 0:
            return 0.1  # 미래 날짜면 최소 가중치
        
        # recency_weight 계산
        if days_diff <= 3:
            return 1.0
        elif days_diff <= 7:
            return 0.7
        elif days_diff <= 14:
            return 0.4
        else:
            return 0.1
    except Exception:
        return 0.1


def _compute_channel_diversity_factor(video_channel_urls: List[str]) -> float:
    """
    채널 다양성 팩터 계산
    
    Args:
        video_channel_urls: 키워드가 등장한 영상들의 채널 URL 리스트
    
    Returns:
        channel_diversity_factor: 1.0 (≥2 채널) 또는 0.5 (1개 채널)
    """
    unique_channels = len(set(video_channel_urls))
    return 1.0 if unique_channels >= 2 else 0.5


def _normalize_keyword_for_matching(keyword: str) -> str:
    """키워드 매칭용 정규화 (substring 매칭 전용)"""
    # 공백/특수문자 정규화
    kw = normalize_text(keyword)
    # 추가 공백 제거
    kw = " ".join(kw.split())
    return kw.lower()


def _match_signal_term(keyword_norm: str, signal_term: str) -> bool:
    """
    외부 신호 term과 키워드 매칭 (substring_ko 모드)
    
    Args:
        keyword_norm: 정규화된 키워드
        signal_term: 외부 신호 term
    
    Returns:
        매칭 여부
    """
    signal_norm = _normalize_keyword_for_matching(signal_term)
    
    # substring 매칭
    return signal_norm in keyword_norm or keyword_norm in signal_norm


def compute_kr_trend_keyword_scores(
    ytdlp_snapshot_path: str,
    news_context_scores: Dict[str, float],
    signals_json_path: str,
    collection_date_local: str,
    signal_boost_max: float = 0.30,
    signal_match_mode: str = "substring_ko",
    ytdapi_trending_json_path: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    KR 트렌드 키워드 점수 계산 (base_score + 외부 신호 가중치 + Data API 앵커 부스트)
    
    Args:
        ytdlp_snapshot_path: ytdlp_channels_snapshot.jsonl 경로
        news_context_scores: 뉴스 컨텍스트 점수 {keyword: score}
        signals_json_path: kr_trend_signals.json 경로
        collection_date_local: 수집일 (YYYY-MM-DD)
        signal_boost_max: 외부 신호 부스트 최대값 (기본 0.30)
        signal_match_mode: 신호 매칭 모드 (기본 "substring_ko")
        ytdapi_trending_json_path: ytdapi_trending_kr.json 경로 (선택)
    
    Returns:
        (scored_keywords: List[Dict], metadata: Dict)
    """
    # 1. yt-dlp 스냅샷에서 키워드 후보 추출 및 base_score 계산
    keyword_videos = defaultdict(list)  # keyword -> [(channel_url, video_id, view_count, date_key), ...]
    keyword_titles = defaultdict(list)  # keyword -> [title, ...]
    
    if Path(ytdlp_snapshot_path).exists():
        try:
            with open(ytdlp_snapshot_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        video_data = json.loads(line)
                        channel_url = video_data.get("channel_url", "")
                        video_id = video_data.get("video_id", "")
                        title = video_data.get("title", "")
                        view_count = video_data.get("view_count")
                        date_key = video_data.get("date_key")  # collection_date_local
                        
                        if not title or not title.strip():
                            continue
                        
                        # title에서 n-gram 키워드 추출
                        normalized_title = normalize_text(title)
                        ngrams = extract_ngrams(normalized_title, max_n=3, max_terms=2000)
                        
                        for ngram in ngrams:
                            if len(ngram) < 3:
                                continue
                            keyword_videos[ngram].append((channel_url, video_id, view_count, date_key))
                            keyword_titles[ngram].append(title)
                    except Exception:
                        continue
        except Exception:
            pass
    
    # 2. base_score 계산
    keyword_base_scores = {}
    keyword_channels = defaultdict(set)
    keyword_video_counts = Counter()
    
    for keyword, videos in keyword_videos.items():
        keyword_channels[keyword] = set(v[0] for v in videos)  # channel_url
        keyword_video_counts[keyword] = len(videos)
        
        # base_score = Σ_i ( log10(view_count_i + 1) × recency_weight(upload_date_i) ) × channel_diversity_factor(k)
        base_score_sum = 0.0
        
        for channel_url, video_id, view_count, date_key in videos:
            # view_count 처리 (None이면 0으로 간주)
            vc = view_count if view_count is not None else 0
            log_view = math.log10(vc + 1) if vc > 0 else 0.0
            
            # recency_weight 계산 (date_key는 collection_date_local이므로 항상 최신)
            recency = _recency_weight(date_key, collection_date_local)
            
            base_score_sum += log_view * recency
        
        # channel_diversity_factor
        channel_diversity = _compute_channel_diversity_factor([v[0] for v in videos])
        
        # base_score 계산
        base_score = base_score_sum * channel_diversity
        keyword_base_scores[keyword] = base_score
    
    # 3. 뉴스 컨텍스트 점수 추가 (base_score에 가산)
    for keyword, news_score in news_context_scores.items():
        keyword_norm = _normalize_keyword_for_matching(keyword)
        if keyword_norm not in keyword_base_scores:
            # 뉴스에만 있고 yt-dlp에 없는 키워드는 base_score=0으로 시작
            keyword_base_scores[keyword_norm] = 0.0
            keyword_channels[keyword_norm] = set()
            keyword_video_counts[keyword_norm] = 0
        # 뉴스 점수를 base_score에 가산 (가중치 적용 가능)
        keyword_base_scores[keyword_norm] += news_score * 0.5  # 뉴스 가중치 0.5
    
    # 4. 외부 신호 수집 및 매칭
    signal_scores = defaultdict(float)  # keyword -> signal_score
    ytdapi_anchor_hits = set()  # Data API 앵커 히트 키워드
    
    # 4-1. 일반 외부 신호 (kr_trend_signals.json)
    if Path(signals_json_path).exists():
        try:
            with open(signals_json_path, "r", encoding="utf-8") as f:
                signals_data = json.load(f)
            
            # 모든 소스 순회
            for source in signals_data.get("sources", []):
                if source.get("status") != "ok":
                    continue
                
                items = source.get("items", [])
                if not items:
                    continue
                
                # items의 score를 normalize (0~1 범위)
                scores = [item.get("score", 0.0) for item in items if item.get("score", 0.0) > 0]
                max_score = max(scores) if scores else 1.0
                min_score = min(scores) if scores else 0.0
                score_range = max_score - min_score if max_score > min_score else 1.0
                
                for item in items:
                    signal_term = item.get("term", "")
                    signal_score_raw = item.get("score", 0.0)
                    
                    if not signal_term or signal_score_raw <= 0:
                        continue
                    
                    # normalize
                    signal_score_norm = (signal_score_raw - min_score) / score_range if score_range > 0 else 0.0
                    
                    # 모든 키워드와 매칭
                    for keyword in keyword_base_scores.keys():
                        if _match_signal_term(keyword, signal_term):
                            signal_scores[keyword] += signal_score_norm
        except Exception:
            pass
    
    # 4-2. Data API 트렌딩 앵커 히트 (ytdapi_trending_kr.json)
    ytdapi_anchor_boost = float(os.getenv("YTDAPI_ANCHOR_BOOST", "0.15"))
    if ytdapi_trending_json_path and Path(ytdapi_trending_json_path).exists():
        try:
            with open(ytdapi_trending_json_path, "r", encoding="utf-8") as f:
                ytdapi_data = json.load(f)
            
            # 모든 카테고리의 영상 제목 수집
            trending_titles = []
            for category in ytdapi_data.get("categories", []):
                if category.get("status") == "ok":
                    for item in category.get("items", []):
                        title = item.get("title", "")
                        if title:
                            trending_titles.append(title)
            
            # 키워드와 매칭하여 앵커 히트 확인
            for keyword in keyword_base_scores.keys():
                keyword_norm = _normalize_keyword_for_matching(keyword)
                for title in trending_titles:
                    title_norm = _normalize_keyword_for_matching(title)
                    # substring 매칭
                    if keyword_norm in title_norm or title_norm in keyword_norm:
                        ytdapi_anchor_hits.add(keyword)
                        break
        except Exception:
            pass
    
    # 5. final_score 계산 및 필터링
    scored_keywords = []
    
    for keyword, base_score in keyword_base_scores.items():
        # 최소 조건: 등장 영상수 ≥2 OR 서로 다른 채널수 ≥2
        video_count = keyword_video_counts.get(keyword, 0)
        channel_count = len(keyword_channels.get(keyword, set()))
        
        if video_count < 2 and channel_count < 2:
            continue  # 제외
        
        # signal_score 계산 (일반 외부 신호)
        signal_score = signal_scores.get(keyword, 0.0)
        
        # Data API 앵커 부스트 추가
        ytdapi_hit = 1 if keyword in ytdapi_anchor_hits else 0
        ytdapi_boost = ytdapi_hit * ytdapi_anchor_boost
        
        # total_signal_boost = 일반 신호 + Data API 앵커
        total_signal_boost = min(max(signal_score + ytdapi_boost, 0.0), signal_boost_max)
        
        # final_score = base_score × (1 + clamp(total_signal_boost, 0.0, signal_boost_max))
        # 단, base_score가 0이면 부스트 적용 금지 (부활 금지)
        if base_score <= 0:
            final_score = base_score
        else:
            final_score = base_score * (1.0 + total_signal_boost)
        
        scored_keywords.append({
            "keyword": keyword,
            "base_score": base_score,
            "signal_score": signal_score,
            "ytdapi_anchor_hit": ytdapi_hit,
            "ytdapi_boost": ytdapi_boost,
            "signal_boost": total_signal_boost,
            "final_score": final_score,
            "video_count": video_count,
            "channel_count": channel_count,
            "news_score": news_context_scores.get(keyword, 0.0)
        })
    
    # 정렬: final_score 내림차순
    scored_keywords.sort(key=lambda x: -x["final_score"])
    
    # 메타데이터
    metadata = {
        "collection_date_local": collection_date_local,
        "signal_boost_max": signal_boost_max,
        "signal_match_mode": signal_match_mode,
        "ytdapi_anchor_boost": ytdapi_anchor_boost,
        "total_keywords_scored": len(scored_keywords),
        "keywords_with_signal": len([k for k in scored_keywords if k["signal_score"] > 0]),
        "keywords_with_ytdapi_anchor": len([k for k in scored_keywords if k.get("ytdapi_anchor_hit", 0) == 1]),
        "max_signal_boost": max([k["signal_boost"] for k in scored_keywords], default=0.0)
    }
    
    return scored_keywords, metadata

