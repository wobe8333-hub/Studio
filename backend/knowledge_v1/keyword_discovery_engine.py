"""
Keyword Discovery Engine - STEP4 키워드 발굴 오케스트레이션
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

from backend.knowledge_v1.paths import get_root
from backend.knowledge_v1.keyword_sources.youtube_data_api import fetch_youtube_keywords
from backend.knowledge_v1.keyword_sources.youtube_videos_list import fetch_videos_list_snapshot
from backend.knowledge_v1.keyword_sources.youtube_platform_top import fetch_platform_top_video_ids
from backend.knowledge_v1.keyword_sources.wikidata_wikipedia import expand_keywords
from backend.knowledge_v1.keyword_sources.news_context import fetch_news_context
from backend.knowledge_v1.keyword_sources.google_trends import fetch_trends_scores
from backend.knowledge_v1.keyword_sources.trending_dataset import fetch_trending_keywords
from backend.knowledge_v1.keyword_sources.ytdlp_channels import collect_snapshot as collect_ytdlp_snapshot
from backend.knowledge_v1.text_mining.ngram import normalize_text, extract_ngrams
from backend.knowledge_v1.schema import AuditEvent
from backend.knowledge_v1.store import append_jsonl
from backend.knowledge_v1.keyword_signals import collect_kr_trend_signals
from backend.knowledge_v1.keyword_scoring import compute_kr_trend_keyword_scores
from backend.knowledge_v1.keyword_sources.youtube_videos_list import fetch_most_popular_titles
from backend.knowledge_v1.utils.keyword_contract import normalize_kw_list
from backend.knowledge_v1.utils.keyword_uniqueness import normalize as normalize_unique


# 불용어 리스트 (간단)
_STOPWORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}


def _normalize_keyword(keyword: str) -> Optional[str]:
    """키워드 전처리"""
    kw = keyword.strip().lower()
    if len(kw) < 3:
        return None
    # 불용어 제거
    words = kw.split()
    words = [w for w in words if w not in _STOPWORDS]
    if not words:
        return None
    return " ".join(words)


def _score_keywords(
    candidate_keywords: List[str],
    demand_score: Dict[str, float],
    evidence_snapshot: List[str],
    performance_hint: Dict[str, float]
) -> List[Dict[str, Any]]:
    """키워드 스코어링"""
    scored = []
    evidence_set = set([_normalize_keyword(k) for k in evidence_snapshot if _normalize_keyword(k)])
    
    for kw in candidate_keywords:
        kw_norm = _normalize_keyword(kw)
        if not kw_norm:
            continue
        
        score = 0.0
        sources_count = 0
        
        # YouTube present: +3
        if kw_norm in [_normalize_keyword(c) for c in candidate_keywords]:
            score += 3.0
            sources_count += 1
        
        # Trends score: +(2 * trends_score)
        trends_val = demand_score.get(kw, demand_score.get(kw_norm, 0.0))
        if trends_val > 0:
            score += 2.0 * trends_val
            sources_count += 1
        
        # Dataset present: +1
        if kw_norm in evidence_set:
            score += 1.0
            sources_count += 1
        
        # Analytics hint: +(1 * hint) (OAuth 있을 때만)
        hint_val = performance_hint.get(kw, performance_hint.get(kw_norm, 0.0))
        if hint_val > 0:
            score += 1.0 * hint_val
            sources_count += 1
        
        scored.append({
            "keyword": kw_norm,
            "original": kw,
            "final_score": score,
            "sources_count": sources_count,
            "youtube_present": kw_norm in [_normalize_keyword(c) for c in candidate_keywords],
            "trends_score": trends_val,
            "dataset_present": kw_norm in evidence_set,
            "analytics_hint": hint_val
        })
    
    # 정렬: final_score 내림차순, 동점이면 keyword 사전순
    scored.sort(key=lambda x: (-x["final_score"], x["keyword"]))
    
    return scored


def _extract_ngrams(text: str, max_n: int = 3, max_per_video: int = 200) -> List[str]:
    """n-gram 추출 (1~max_n그램, 최대 max_per_video개) - 레거시 호환"""
    if not text:
        return []
    
    words = re.findall(r'\b\w+\b', text.lower())
    ngrams = []
    
    for n in range(1, min(max_n + 1, len(words) + 1)):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            if len(ngram) >= 3:  # 최소 길이
                ngrams.append(ngram)
            if len(ngrams) >= max_per_video:
                break
        if len(ngrams) >= max_per_video:
            break
    
    return ngrams[:max_per_video]


def _fetch_video_metadata_batch(video_ids: List[str], api_key: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """
    YouTube Data API v3 videos.list로 title/description/tags 가져오기 (50개 단위 배치)
    
    Returns:
        {videoId: {"title": str, "description": str, "tags": List[str]}}
    """
    if not video_ids or not api_key:
        return {}
    
    # youtube_videos_list 모듈 사용
    snapshot = fetch_videos_list_snapshot(video_ids)
    
    # metadata dict 생성
    metadata = {}
    for item in snapshot.get("items", []):
        video_id = item.get("video_id", "")
        if video_id:
            metadata[video_id] = {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "tags": item.get("tags", [])
            }
    
    return metadata


def _compute_analytics_hint(
    top_videos: List[Dict[str, Any]],
    api_key: Optional[str]
) -> Dict[str, float]:
    """
    Analytics Top Videos 기반 analytics_hint 계산
    
    Returns:
        {keyword: score_norm (0~1)}
    """
    if not top_videos or not api_key:
        return {}
    
    # videoId 리스트 추출
    video_ids = [v["videoId"] for v in top_videos if v.get("videoId")]
    if not video_ids:
        return {}
    
    # 배치로 메타데이터 가져오기
    metadata = _fetch_video_metadata_batch(video_ids, api_key)
    
    # videoId -> score_norm 매핑
    video_scores = {v["videoId"]: v.get("score_norm", 0.0) for v in top_videos}
    
    # n-gram 후보 추출 및 빈도 계산
    keyword_scores = Counter()
    
    for video_id, meta in metadata.items():
        score_norm = video_scores.get(video_id, 0.0)
        if score_norm <= 0:
            continue
        
        # title, description, tags에서 n-gram 추출
        text_parts = [
            meta.get("title", ""),
            meta.get("description", ""),
            " ".join(meta.get("tags", []))
        ]
        combined_text = " ".join(text_parts)
        
        ngrams = _extract_ngrams(combined_text, max_n=3, max_per_video=200)
        for ngram in ngrams:
            ngram_norm = _normalize_keyword(ngram)
            if ngram_norm:
                # 최대 score_norm 사용
                keyword_scores[ngram_norm] = max(
                    keyword_scores.get(ngram_norm, 0.0),
                    score_norm
                )
    
    # 상위 2000개만 유지
    top_keywords = keyword_scores.most_common(2000)
    return {kw: float(score) for kw, score in top_keywords}


def _get_category_hints() -> Dict[str, List[str]]:
    """V7 카테고리별 힌트 (6개 카테고리)"""
    return {
        "history": ["ancient", "dynasty", "empire", "revolution", "civilization", "rome", "greece", "joseon", "medieval"],
        "mystery": ["unsolved", "mystery", "disappearance", "ufo", "secret", "conspiracy", "cold case", "cryptic"],
        "economy": ["inflation", "gdp", "interest rate", "stock", "market", "recession", "trade", "currency"],
        "myth": ["myth", "legend", "god", "goddess", "norse", "greek", "roman", "egyptian", "dragon", "olympus"],
        "science": ["quantum", "space", "physics", "biology", "ai", "astronomy", "experiment", "nasa", "black hole"],
        "war_history": ["war", "battle", "ww1", "ww2", "vietnam war", "korean war", "napoleon", "army", "navy", "strategy"]
    }


def _fetch_youtube_most_popular_titles(api_key: str, region_code: str = "KR", max_results: int = 50) -> List[str]:
    """YouTube mostPopular API로 title 리스트 가져오기"""
    import requests
    
    if not api_key:
        return []
    
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(max_results, 50),
            "key": api_key
        }
        
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            titles = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                title = snippet.get("title", "").strip()
                if title:
                    titles.append(title)
            return titles
    except Exception:
        pass
    
    return []


def _normalize_keyword_for_dedup(kw: str) -> str:
    """중복 검사용 정규화"""
    return kw.strip().lower()


def _match_keyword_to_category(keyword: str, category_hints: Dict[str, List[str]]) -> Optional[str]:
    """키워드를 카테고리 힌트와 매칭"""
    kw_lower = keyword.lower()
    
    for cat, hints in category_hints.items():
        for hint in hints:
            if hint.lower() in kw_lower:
                return cat
    
    return None


def _generate_top5_keywords_per_category(
    cycle_id: str,
    api_key: str,
    categories: List[str],
    target_per_category: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """
    YouTube mostPopular 기반 카테고리별 TOP5 키워드 생성
    
    Returns:
        {category: [{"keyword": str, "source": str, "rank": int, "is_trending": bool, "score": float}, ...]}
    """
    # YouTube mostPopular title 수집
    titles = _fetch_youtube_most_popular_titles(api_key, region_code="KR", max_results=50)
    
    if not titles:
        # Fallback: 빈 결과 반환
        return {cat: [] for cat in categories}
    
    # 카테고리 힌트
    category_hints = _get_category_hints()
    
    # title에서 키워드 후보 추출 및 카테고리 매칭
    category_candidates = {cat: [] for cat in categories}
    seen_normalized = set()  # 카테고리 간 중복 방지
    
    for title in titles:
        # title을 키워드로 사용 (또는 n-gram 추출)
        kw_candidate = title.strip()
        if len(kw_candidate) < 3:
            continue
        
        kw_norm = _normalize_keyword_for_dedup(kw_candidate)
        if kw_norm in seen_normalized:
            continue
        
        # 카테고리 매칭
        matched_cat = _match_keyword_to_category(kw_candidate, category_hints)
        if matched_cat and matched_cat in categories:
            if len(category_candidates[matched_cat]) < target_per_category * 2:  # 여유분 확보
                category_candidates[matched_cat].append({
                    "keyword": kw_candidate,
                    "normalized": kw_norm,
                    "score": 1.0
                })
                seen_normalized.add(kw_norm)
    
    # 각 카테고리별 정확히 target_per_category개 선택
    result = {}
    for cat in categories:
        candidates = category_candidates[cat]
        
        # 점수 기준 정렬 (동일하면 키워드 순)
        candidates.sort(key=lambda x: (-x["score"], x["keyword"]))
        
        # 정확히 target_per_category개 선택
        selected = candidates[:target_per_category]
        
        # 결과 포맷 변환
        result[cat] = []
        for idx, item in enumerate(selected, 1):
            result[cat].append({
                "keyword": item["keyword"],
                "source": "yt_api",
                "rank": idx,
                "is_trending": True,
                "score": float(item["score"])
            })
    
    return result


def get_category_keywords_topk(
    categories: List[str],
    k: int = 5,
    region_code: str = "KR",
) -> Dict[str, List[str]]:
    """
    카테고리별 독립 TOP-k 키워드 반환.
    - 반환 계약: dict[category] -> list[str]
    - 데이터 부족 시 빈 리스트를 반환한다(동일 리스트 복제 금지).
    """
    category_hints = _get_category_hints()
    out: Dict[str, List[str]] = {cat: [] for cat in categories}
    global_seen = set()

    yt_result = fetch_most_popular_titles(region_code=region_code, max_results=50)
    titles = yt_result.get("titles", []) if isinstance(yt_result, dict) else []

    # 카테고리별 candidate pool 구축 (동일 리스트 복제 금지)
    pools: Dict[str, List[str]] = {cat: [] for cat in categories}
    for title in titles:
        normalized_title = normalize_unique(title)
        if not normalized_title:
            continue
        for cat in categories:
            hints = category_hints.get(cat, [])
            score = 0
            for hint in hints:
                hint_norm = normalize_unique(hint)
                if hint_norm and hint_norm in normalized_title:
                    score += 1
            if score > 0:
                pools[cat].append(title.strip())

    # 카테고리별로 독립 리스트 생성 + 카테고리 간 중복 차단
    for cat in categories:
        selected: List[str] = []
        local_seen = set()
        for cand in pools.get(cat, []):
            norm = normalize_unique(cand)
            if not norm:
                continue
            if norm in local_seen or norm in global_seen:
                continue
            local_seen.add(norm)
            global_seen.add(norm)
            selected.append(cand.strip())
            if len(selected) >= k:
                break
        out[cat] = normalize_kw_list(selected)

    return out


def _distribute_keywords_to_categories(
    global_candidates: List[Dict[str, Any]],
    categories: List[str],
    cat_min: int = 50,
    cat_max: int = 200
) -> Dict[str, List[str]]:
    """
    전역 후보를 카테고리별로 분배 (레거시 호환)
    
    Returns:
        {category: [keyword, ...]}
    """
    # 카테고리별 키워드 힌트 룰 (레거시)
    category_hints = {
        "science": ["physics", "chemistry", "biology", "space", "quantum", "gravity", "evolution", "climate", "black hole", "atom", "molecule"],
        "history": ["war", "ancient", "dynasty", "empire", "medieval", "renaissance", "revolution", "civilization", "battle", "king", "queen"],
        "common_sense": ["how to", "basics", "simple", "everyday", "electricity", "water cycle", "photosynthesis", "magnetism", "light", "sound"],
        "economy": ["inflation", "gdp", "interest rate", "stock", "market", "trade", "currency", "bank", "finance", "economic"],
        "geography": ["climate", "tectonic", "latitude", "longitude", "ocean", "mountain", "river", "continent", "country", "map"],
        "papers": ["transformer", "attention", "neural network", "llm", "arxiv", "paper", "deep learning", "ai", "machine learning", "algorithm"]
    }
    
    category_keywords = {cat: [] for cat in categories}
    used_keywords = set()
    
    # 1단계: 룰 기반 매핑
    for candidate in global_candidates:
        keyword = candidate.get("keyword", "")
        if not keyword or keyword in used_keywords:
            continue
        
        keyword_lower = keyword.lower()
        matched = False
        
        for cat in categories:
            if len(category_keywords[cat]) >= cat_max:
                continue
            
            hints = category_hints.get(cat, [])
            for hint in hints:
                if hint in keyword_lower:
                    category_keywords[cat].append(keyword)
                    used_keywords.add(keyword)
                    matched = True
                    break
            
            if matched:
                break
    
    # 2단계: 부족분 채우기 (전역 상위 순)
    for candidate in global_candidates:
        keyword = candidate.get("keyword", "")
        if not keyword or keyword in used_keywords:
            continue
        
        # 가장 부족한 카테고리에 할당
        min_cat = min(categories, key=lambda c: len(category_keywords[c]))
        if len(category_keywords[min_cat]) < cat_max:
            category_keywords[min_cat].append(keyword)
            used_keywords.add(keyword)
    
    # 3단계: 최소값 보장 (부족하면 다른 카테고리에서 가져오기)
    for cat in categories:
        if len(category_keywords[cat]) < cat_min:
            # 다른 카테고리에서 가져오기
            for other_cat in categories:
                if other_cat == cat:
                    continue
                if len(category_keywords[other_cat]) > cat_min:
                    # 초과분에서 가져오기
                    needed = cat_min - len(category_keywords[cat])
                    available = category_keywords[other_cat][cat_min:]
                    transfer = min(needed, len(available))
                    category_keywords[cat].extend(available[:transfer])
                    category_keywords[other_cat] = category_keywords[other_cat][:cat_min] + category_keywords[other_cat][cat_min+transfer:]
                    break
    
    return category_keywords


def _save_snapshots(
    cycle_id: str,
    category: str,
    youtube_result: Dict[str, Any],
    trends_result: Dict[str, Any],
    dataset_result: Dict[str, Any],
    analytics_result: Dict[str, Any]
) -> None:
    """소스별 스냅샷 저장 (기존 파일명 + 표준 파일명 병행)"""
    snapshots_dir = get_root() / "keyword_discovery" / "snapshots" / cycle_id
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    # YouTube 스냅샷
    youtube_path = snapshots_dir / f"{category}_youtube.json"
    with open(youtube_path, "w", encoding="utf-8") as f:
        json.dump(youtube_result, f, ensure_ascii=False, indent=2)
    
    # Trends 스냅샷 (기존 파일명)
    trends_path = snapshots_dir / f"{category}_trends.json"
    with open(trends_path, "w", encoding="utf-8") as f:
        json.dump(trends_result, f, ensure_ascii=False, indent=2)
    
    # Dataset 스냅샷 (기존 파일명)
    dataset_path = snapshots_dir / f"{category}_dataset.json"
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset_result, f, ensure_ascii=False, indent=2)
    
    # Analytics Top Videos 스냅샷 (있으면)
    if analytics_result.get("oauth_configured") and analytics_result.get("snapshot"):
        analytics_path = snapshots_dir / "analytics_top_videos.json"
        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(analytics_result["snapshot"], f, ensure_ascii=False, indent=2)


def run_keyword_discovery(
    categories: List[str],
    mode: str = "run",
    max_keywords: int = 30
) -> Dict[str, Any]:
    """
    키워드 발굴 실행 (V7: 6개 카테고리 + YouTube mostPopular TOP5)
    
    Returns:
        {
            "cycle_id": str,
            "started_at": str,
            "ended_at": str,
            "categories": Dict[str, Dict],
            "summary": Dict
        }
    """
    # V7: 정책 로드 및 검증
    try:
        from backend.knowledge_v1.policy.validator import validate_and_load_policy
        policy, is_valid, conflicts = validate_and_load_policy()
        
        if not is_valid:
            # 정책 충돌 시 즉시 종료
            return {
                "cycle_id": "",
                "started_at": datetime.utcnow().isoformat() + "Z",
                "ended_at": datetime.utcnow().isoformat() + "Z",
                "categories": {},
                "summary": {
                    "total_keywords": 0,
                    "policy_conflict": True,
                    "conflict_list": conflicts
                }
            }
        
        # 정책에서 카테고리 및 목표 키워드 수 가져오기
        policy_categories = policy.get("categories", categories)
        target_per_category = policy.get("per_category_target_keywords", 5)
        
        # 카테고리가 정책과 다르면 정책 우선
        if set(categories) != set(policy_categories):
            categories = policy_categories
    except Exception as e:
        # 정책 로드 실패 시 기본값 사용
        target_per_category = 5
        conflicts = [f"policy_load_failed: {type(e).__name__}"]
    
    cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    started_at = datetime.utcnow()
    
    # SSOT: cycle_id 확정 후 즉시 last_cycle_id.txt 작성
    discovery_root = get_root() / "keyword_discovery"
    snapshots_base_dir = discovery_root / "snapshots"
    snapshots_base_dir.mkdir(parents=True, exist_ok=True)
    last_cycle_id_path = snapshots_base_dir / "last_cycle_id.txt"
    try:
        with open(last_cycle_id_path, "w", encoding="utf-8") as f:
            f.write(f"{cycle_id}\n")
    except Exception:
        pass  # 실패해도 파이프라인은 계속 진행
    
    # snapshot_dir 단 1번만 계산
    snapshot_dir = snapshots_base_dir / cycle_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # V7: YouTube mostPopular 기반 TOP5 키워드 생성
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        project_root = Path(__file__).resolve().parents[4]
        key_file = project_root / "backend" / "credentials" / "youtube_api_key.txt"
        if key_file.exists():
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    api_key = f.read().strip()
            except Exception:
                pass
    
    # 카테고리별 TOP5 키워드 생성
    category_keywords_map = _generate_top5_keywords_per_category(
        cycle_id=cycle_id,
        api_key=api_key or "",
        categories=categories,
        target_per_category=target_per_category
    )
    
    # 스냅샷 저장: snapshots/<cycle_id>/keywords_<category>_raw.jsonl
    for category, keywords_list in category_keywords_map.items():
        keywords_file = snapshot_dir / f"keywords_{category}_raw.jsonl"
        with open(keywords_file, "w", encoding="utf-8") as f:
            for kw_entry in keywords_list:
                f.write(json.dumps(kw_entry, ensure_ascii=False) + "\n")
    
    # 5개 미달 시 cycle FAIL
    for category in categories:
        if len(category_keywords_map.get(category, [])) < target_per_category:
            return {
                "cycle_id": cycle_id,
                "started_at": started_at.isoformat() + "Z",
                "ended_at": datetime.utcnow().isoformat() + "Z",
                "categories": {},
                "summary": {
                    "total_keywords": 0,
                    "cycle_failed": True,
                    "reason": f"category_{category}_keywords_below_target",
                    "expected": target_per_category,
                    "actual": len(category_keywords_map.get(category, []))
                }
            }
    
    # Audit 경로 설정 (yt-dlp 호출 전에 정의)
    discovery_root = get_root() / "keyword_discovery"
    audit_path = get_root() / "audit" / "audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    
    # V7 feature flag: yt-dlp 강제 enable / 최소 타이틀 기준
    enable_ytdlp_flag = os.getenv("V7_ENABLE_YTDLP", "0").strip() == "1"
    min_titles_required = int(os.getenv("V7_YTDLP_MIN_TITLES_REQUIRED", "10"))
    
    # yt-dlp enabled 판단 (여러 환경변수 키 체크, 우선순위 고정)
    ytdlp_enabled = False
    recorded_env_key = None
    for env_key in ["YTDLP_CHANNELS_ENABLED", "YTDLP_ENABLED", "ENABLE_YTDLP"]:
        env_value = os.getenv(env_key, "0")
        if env_value in ["1", "true", "True"]:
            ytdlp_enabled = True
            recorded_env_key = env_key
            break
    
    # V7_ENABLE_YTDLP=1 이면 절대 disabled 되지 않도록 강제
    if enable_ytdlp_flag:
        ytdlp_enabled = True
        recorded_env_key = "V7_ENABLE_YTDLP"
    
    # yt-dlp 스냅샷 수집 (KR 채널만, enabled 여부와 관계없이 항상 호출)
    ytdlp_result = None
    ytdlp_title_count = 0
    ytdlp_keyword_count = 0
    ytdlp_date_coverage_ratio = 0.0
    ytdlp_reason = None
    ytdlp_source_mode = None
    ytdlp_latest_n = None
    ytdlp_collection_date_local = None
    
    try:
        from backend.knowledge_v1.keyword_sources import ytdlp_channels
        
        # KR 채널 파일 선택 (채널 파일 분리 강제)
        ytdlp_channels_file_kr = os.getenv("YTDLP_CHANNELS_FILE_KR", "backend/config/ytdlp_channels_kr.txt")
        
        ytdlp_result = ytdlp_channels.collect_snapshot(
            cycle_id=cycle_id,
            snapshot_dir=str(snapshot_dir),
            enabled=ytdlp_enabled,
            channels_file=ytdlp_channels_file_kr,
            latest_n=int(os.getenv("YTDLP_MAX_VIDEOS_PER_CHANNEL", "300")),
            min_videos_required=int(os.getenv("YTDLP_MIN_VIDEOS_REQUIRED", "80")),
            allow_fail=(os.getenv("ALLOW_YTDLP_FAIL", "0") in ["1", "true", "True"]),
            timeout_seconds=int(os.getenv("YTDLP_TIMEOUT_SECONDS", "30")),
            max_channels=int(os.getenv("YTDLP_MAX_CHANNELS_PER_RUN", "30")),
            mode="KR"  # KR 채널만 수집
        )
        
        # yt-dlp 통계 추출
        if ytdlp_result:
            ytdlp_reason = ytdlp_result.get("reason")
            ytdlp_source_mode = ytdlp_result.get("source_mode")
            ytdlp_latest_n = ytdlp_result.get("latest_n")
            ytdlp_collection_date_local = ytdlp_result.get("collection_date_local")
            if ytdlp_result.get("metrics"):
                metrics = ytdlp_result.get("metrics", {})
                metrics_count = metrics.get("videos_after_dedupe", 0)
                # C-2: ytdlp_title_count 산정 일관성 (기본값은 metrics에서)
                ytdlp_title_count = metrics_count
                ytdlp_date_coverage_ratio = metrics.get("date_key_coverage_ratio", 0.0)
    except Exception as e:
        # yt-dlp 수집 실패해도 계속 진행 (무중단)
        ytdlp_reason = f"exception: {type(e).__name__}"
        pass
    
    # BULK 모드 강제 (환경변수로만 비활성화 가능)
    bulk_mode = os.getenv("KNOWLEDGE_STEP4_BULK", "1") != "0"
    max_videos = int(os.getenv("KNOWLEDGE_STEP4_MAX_VIDEOS", "300"))
    global_min_candidates = int(os.getenv("KNOWLEDGE_STEP4_GLOBAL_MIN_CANDIDATES", "2000"))
    cat_min = int(os.getenv("KNOWLEDGE_STEP4_CAT_MIN", "50"))
    cat_max = int(os.getenv("KNOWLEDGE_STEP4_CAT_MAX", "200"))
    
    # 디렉토리 생성 (discovery_root는 이미 위에서 계산됨)
    (discovery_root / "raw").mkdir(parents=True, exist_ok=True)
    (discovery_root / "scored").mkdir(parents=True, exist_ok=True)
    (discovery_root / "reports").mkdir(parents=True, exist_ok=True)
    
    # Audit: START (audit_path는 이미 위에서 정의됨)
    
    if bulk_mode:
        append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_BULK_START", {
            "cycle_id": cycle_id,
            "categories": categories,
            "mode": mode,
            "max_keywords": max_keywords,
            "max_videos": max_videos
        }).to_dict())
    else:
        append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_START", {
            "cycle_id": cycle_id,
            "categories": categories,
            "mode": mode,
            "max_keywords": max_keywords
        }).to_dict())
    
    report = {
        "cycle_id": cycle_id,
        "started_at": started_at.isoformat() + "Z",
        "mode": mode,
        "categories": {},
        "summary": {
            "total_keywords": 0,
            "total_scored": 0,
            "bulk_mode": bulk_mode,
            "videos_requested": 0,
            "videos_fetched": 0,
            "global_candidates": 0,
            "category_candidates": {},
            "failure_reasons": {
                "analytics": None,
                "videos_list": None,
                "trends": None,
                "dataset": None,
                "ytdlp": None
            },
            "warnings": []
        }
    }
    
    # yt-dlp reason을 failure_reasons 또는 warnings에 기록
    if ytdlp_reason:
        # V7_ENABLE_YTDLP=1 인 경우 "disabled" 경고는 절대 기록하지 않는다
        if enable_ytdlp_flag and str(ytdlp_reason).strip().lower() == "disabled":
            pass
        else:
            if ytdlp_reason in ["channels_file_missing", "channels_file_empty", "channels_file_read_error", "channels_file_create_failed"]:
                report["summary"]["failure_reasons"]["ytdlp"] = ytdlp_reason
                report["summary"]["warnings"].append(f"yt-dlp: {ytdlp_reason}. Please add channel URLs to backend/config/ytdlp_channels.txt")
            else:
                report["summary"]["warnings"].append(f"yt-dlp: {ytdlp_reason}")
    
    # 표준 스냅샷 파일용 누적 데이터
    trends_snapshot_all = {}
    dataset_snapshot_all = {}
    
    # BULK 모드: 전역 후보 생성
    global_candidates = []
    videos_list_snapshot = None
    keyword_candidates_snapshot = None
    platform_top_snapshot = None
    wikidata_snapshot = None
    news_context_snapshot = None
    video_ids = []
    video_scores = {}
    synthetic_used = False
    
    if bulk_mode:
        # API 키 로드
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            project_root = Path(__file__).resolve().parents[3]
            key_file = project_root / "backend" / "credentials" / "youtube_api_key.txt"
            if key_file.exists():
                with open(key_file, "r", encoding="utf-8") as f:
                    api_key = f.read().strip()
        
        # (1) YouTube Platform Top Videos 수집 (Analytics 제거)
        platform_video_ids, platform_top_snapshot = fetch_platform_top_video_ids(categories, max_videos, cycle_id=cycle_id)
        video_ids = platform_video_ids[:max_videos]
        
        # video_scores 초기화 (모든 video에 동일 가중치 0.3)
        video_scores = {vid: 0.3 for vid in video_ids}
        
        report["summary"]["platform_top_used"] = platform_top_snapshot.get("ok", False)
        report["summary"]["platform_top_video_ids_count"] = len(video_ids)
        
        # (2) videos.list 대량 호출 (video_ids가 있으면)
        if api_key and video_ids:
            videos_list_snapshot = fetch_videos_list_snapshot(video_ids)
            fetched_items = videos_list_snapshot.get("fetched_items", 0)
            
            if fetched_items >= 1:
                # N-gram 후보 생성
                keyword_scores = Counter()
                
                for item in videos_list_snapshot.get("items", []):
                    video_id = item.get("video_id", "")
                    weight = video_scores.get(video_id, 0.3)
                    
                    # 텍스트 결합
                    text_parts = [
                        item.get("title", ""),
                        item.get("description", ""),
                        " ".join(item.get("tags", []))
                    ]
                    combined_text = " ".join(text_parts)
                    
                    # N-gram 추출
                    ngrams = extract_ngrams(combined_text, max_n=3, max_terms=2000)
                    
                    for ngram in ngrams:
                        keyword_scores[ngram] += weight
                
                # 빈도 보너스
                if keyword_scores:
                    max_freq = max(keyword_scores.values())
                    for kw in keyword_scores:
                        freq_norm = keyword_scores[kw] / max_freq if max_freq > 0 else 0
                        keyword_scores[kw] += 0.1 * freq_norm
                
                # 상위 2000개 선택
                top_keywords = keyword_scores.most_common(2000)
                global_candidates = [
                    {"keyword": kw, "score": float(score)}
                    for kw, score in top_keywords
                ]
                
                # yt-dlp title 키워드 합산 (ytdlp_result가 있으면 항상 시도)
                if ytdlp_result:
                    snapshot_path = ytdlp_result.get("snapshot_path") or str(snapshot_dir / "ytdlp_channels_snapshot.jsonl")
                    if snapshot_path and os.path.exists(snapshot_path):
                        try:
                            ytdlp_titles = []
                            with open(snapshot_path, "r", encoding="utf-8") as f:
                                for line in f:
                                    line = line.strip()
                                    if not line:
                                        continue
                                    try:
                                        video_data = json.loads(line)
                                        # C-1: title_norm 우선 사용
                                        title = (video_data.get("title_norm") or video_data.get("title") or "").strip()
                                        if title:
                                            ytdlp_titles.append(title)
                                    except Exception:
                                        continue
                            
                            if ytdlp_titles:
                                ytdlp_keyword_scores = Counter()
                                for title in ytdlp_titles:
                                    normalized = normalize_text(title)
                                    if normalized:
                                        ngrams = extract_ngrams(normalized, max_n=3, max_terms=2000)
                                        for ngram in ngrams:
                                            ytdlp_keyword_scores[ngram] += 1.0
                                
                                # Fallback: ngrams가 비어 ytdlp_keyword_scores가 0인 경우 토큰 기반으로 최소 생성
                                if not ytdlp_keyword_scores and ytdlp_titles:
                                    for title in ytdlp_titles:
                                        normalized2 = normalize_text(title)
                                        if not normalized2:
                                            continue
                                        toks = [t for t in normalized2.split() if len(t) > 1]
                                        for t in toks[:10]:
                                            ytdlp_keyword_scores[t] += 1.0
                                    # 경고 기록
                                    try:
                                        report["summary"].setdefault("warnings", []).append("ytdlp_keywords_fallback_tokens_used")
                                    except Exception:
                                        pass
                                
                                # ytdlp_keyword_count 업데이트
                                ytdlp_keyword_count = len(ytdlp_keyword_scores)
                                
                                # HARDLOCK: prevent ytdlp_keyword_count from being 0 when titles exist
                                if (ytdlp_keyword_count == 0) and ytdlp_titles:
                                    for _t in ytdlp_titles:
                                        _n = normalize_text(_t)
                                        if not _n:
                                            continue
                                        for _tok in _n.split():
                                            if len(_tok) > 1:
                                                ytdlp_keyword_scores[_tok] += 1.0
                                    ytdlp_keyword_count = len(ytdlp_keyword_scores)
                                    try:
                                        report["summary"].setdefault("warnings", []).append("ytdlp_keywords_fallback_used")
                                    except Exception:
                                        pass
                                
                                # C-2: ytdlp_title_count 보정 (titles 리스트 길이와 metrics 중 큰 값)
                                ytdlp_title_count = max(ytdlp_title_count, len(ytdlp_titles))
                                
                                if ytdlp_keyword_count > 0:
                                    # 기존 global_candidates와 합산
                                    existing_keywords = {c["keyword"]: c["score"] for c in global_candidates}
                                    for kw, score in ytdlp_keyword_scores.most_common(500):
                                        if kw in existing_keywords:
                                            # 기존 키워드면 점수 증가
                                            existing_keywords[kw] += float(score) * 0.5
                                        else:
                                            # 새 키워드면 추가
                                            existing_keywords[kw] = float(score) * 0.5
                                    
                                    # 다시 리스트로 변환 및 정렬
                                    global_candidates = [
                                        {"keyword": kw, "score": float(score)}
                                        for kw, score in sorted(existing_keywords.items(), key=lambda x: -x[1])
                                    ][:2000]  # 상위 2000개만 유지
                        except Exception:
                            pass
                    else:
                        try:
                            report["summary"].setdefault("warnings", []).append("ytdlp_snapshot_missing_for_global_merge")
                        except Exception:
                            pass
                
                # Audit: CANDIDATES_OK
                append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_CANDIDATES_OK", {
                    "cycle_id": cycle_id,
                    "global_candidates": len(global_candidates)
                }).to_dict())
            else:
                # videos.list 실패
                errors = videos_list_snapshot.get("errors", [])
                error_msg = errors[0].get("message", "unknown_error") if errors else "fetched_items=0"
                report["summary"]["failure_reasons"]["videos_list"] = error_msg
                append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_VIDEOS_LIST_FAIL", {
                    "cycle_id": cycle_id,
                    "error": error_msg
                }).to_dict())
        elif not api_key:
            # API 키 없음
            report["summary"]["failure_reasons"]["videos_list"] = "api_key_not_configured"
            # 빈 스냅샷 생성
            videos_list_snapshot = {
                "ok": False,
                "requested_video_ids": len(video_ids),
                "fetched_items": 0,
                "missing_video_ids": len(video_ids),
                "batches": 0,
                "errors": [{"batch_index": 0, "http_status": None, "message": "api_key_not_configured"}],
                "items": []
            }
        elif not video_ids:
            # video_ids 없음
            report["summary"]["failure_reasons"]["videos_list"] = "no_video_ids"
            videos_list_snapshot = {
                "ok": False,
                "requested_video_ids": 0,
                "fetched_items": 0,
                "missing_video_ids": 0,
                "batches": 0,
                "errors": [{"batch_index": 0, "http_status": None, "message": "no_video_ids"}],
                "items": []
            }
        
        # 카테고리별 분배
        # global_candidates가 global_min_candidates 미만이면 synthetic 후보 생성
        if len(global_candidates) < global_min_candidates:
            # Synthetic 후보 생성 (seed_map 기반)
            synthetic_candidates = []
            seed_map = {
                "science": ["gravity", "quantum physics", "evolution", "climate change", "black hole", "atom", "molecule", "energy", "light", "wave"],
                "history": ["world war", "ancient rome", "renaissance", "cold war", "industrial revolution", "empire", "civilization", "medieval", "revolution", "dynasty"],
                "common_sense": ["electricity", "water cycle", "photosynthesis", "gravity", "magnetism", "light", "sound", "temperature", "pressure", "force"],
                "economy": ["inflation", "gdp", "stock market", "cryptocurrency", "trade", "currency", "bank", "finance", "economic", "market"],
                "geography": ["latitude", "longitude", "tectonic plates", "ocean currents", "climate zones", "mountain", "river", "continent", "country", "map"],
                "papers": ["transformer", "attention mechanism", "neural network", "deep learning", "llm", "ai", "machine learning", "algorithm", "nlp", "computer vision"]
            }
            
            for cat in categories:
                seeds = seed_map.get(cat, [])
                for seed in seeds:
                    if seed not in [c["keyword"] for c in global_candidates]:
                        synthetic_candidates.append({"keyword": seed, "score": 0.1})
            
            # global_candidates에 synthetic 추가
            global_candidates.extend(synthetic_candidates[:global_min_candidates - len(global_candidates)])
            synthetic_used = len(synthetic_candidates) > 0
            report["summary"]["synthetic_used"] = synthetic_used
        else:
            synthetic_used = False
            report["summary"]["synthetic_used"] = False
        
        # 카테고리별 분배
        if global_candidates:
            category_keywords_map = _distribute_keywords_to_categories(
                global_candidates, categories, cat_min, cat_max
            )
            # per_category_candidates 생성 (리스트 형태)
            per_category_candidates = {cat: kws for cat, kws in category_keywords_map.items()}
            
            keyword_candidates_snapshot = {
                "ok": True,
                "global_candidates": [c["keyword"] if isinstance(c, dict) else c for c in global_candidates],
                "per_category_candidates": per_category_candidates,
                "category_candidates": {cat: len(kws) for cat, kws in category_keywords_map.items()},
                "synthetic_used": synthetic_used,
                "counts": {
                    "global_candidates": len(global_candidates),
                    "category_candidates": {cat: len(kws) for cat, kws in category_keywords_map.items()}
                },
                "error": None
            }
        else:
            # Fallback: seed_map 사용
            category_keywords_map = {}
            seed_map = {
                "science": ["gravity", "quantum physics", "evolution", "climate change", "black hole"],
                "history": ["world war", "ancient rome", "renaissance", "cold war", "industrial revolution"],
                "common_sense": ["electricity", "water cycle", "photosynthesis", "gravity", "magnetism"],
                "economy": ["inflation", "gdp", "stock market", "cryptocurrency", "trade"],
                "geography": ["latitude", "longitude", "tectonic plates", "ocean currents", "climate zones"],
                "papers": ["transformer", "attention mechanism", "neural network", "deep learning", "llm"]
            }
            for cat in categories:
                category_keywords_map[cat] = seed_map.get(cat, [f"{cat} topic"])
            
            per_category_candidates = {cat: kws for cat, kws in category_keywords_map.items()}
            
            keyword_candidates_snapshot = {
                "ok": False,
                "global_candidates": [],
                "per_category_candidates": per_category_candidates,
                "category_candidates": {cat: len(kws) for cat, kws in category_keywords_map.items()},
                "synthetic_used": True,
                "counts": {
                    "global_candidates": 0,
                    "category_candidates": {cat: len(kws) for cat, kws in category_keywords_map.items()}
                },
                "error": "global_candidates=0, using fallback seed_map"
            }
        
        # (3) Wikidata/Wikipedia 확장 (5중 데이터셋)
        try:
            first_category = categories[0] if categories else "science"
            sample_keywords = [c["keyword"] if isinstance(c, dict) else c for c in global_candidates[:50]]
            expanded_keywords, wikidata_snapshot = expand_keywords(sample_keywords, first_category)
        except Exception as e:
            wikidata_snapshot = {
                "ok": False,
                "mode": "stub",
                "used_sources": [],
                "mapping_hints": {},
                "errors": [{"message": f"{type(e).__name__}: {str(e)}"}]
            }
        
        # (4) News Context (5중 데이터셋)
        news_scores = {}
        try:
            sample_keywords = [c["keyword"] if isinstance(c, dict) else c for c in global_candidates[:20]]
            news_scores, news_context_snapshot = fetch_news_context(sample_keywords, lookback_days=7, max_items=50)
        except Exception as e:
            news_context_snapshot = {
                "ok": False,
                "provider": "rss",
                "items_count": 0,
                "top_headlines": [],
                "errors": [{"message": f"{type(e).__name__}: {str(e)}"}]
            }
        
        # (5) 외부 트렌드 신호 수집 (③ KR 트렌드 키워드 확정 전)
        signals_result = None
        try:
            signals_result = collect_kr_trend_signals(cycle_id=cycle_id, snapshot_dir=snapshot_dir)
        except Exception as e:
            signals_result = {
                "signals_path": str(snapshot_dir / "signals" / "kr_trend_signals.json"),
                "errors_path": str(snapshot_dir / "signals" / "kr_trend_signals_errors.json"),
                "ok": False
            }
            pass
        
        # (6) KR 트렌드 키워드 확정 (yt-dlp + KR 뉴스 + 외부 신호 가중치)
        kr_trend_keywords = []
        kr_trend_keywords_top = []
        kr_scoring_metadata = {}
        
        if bulk_mode and mode == "run":
            try:
                # ytdlp 스냅샷 경로
                ytdlp_snapshot_path = None
                if ytdlp_result and ytdlp_result.get("snapshot_path"):
                    ytdlp_snapshot_path = ytdlp_result.get("snapshot_path")
                else:
                    # 기본 경로 시도
                    ytdlp_snapshot_path = str(snapshot_dir / "ytdlp_channels_snapshot.jsonl")
                
                # 외부 신호 경로
                signals_json_path = signals_result.get("signals_path") if signals_result else str(snapshot_dir / "signals" / "kr_trend_signals.json")
                
                # Data API 트렌딩 경로
                ytdapi_trending_json_path = str(snapshot_dir / "signals" / "ytdapi_trending_kr.json")
                
                # collection_date_local (yt-dlp에서 가져오거나 현재 날짜)
                collection_date_local = ytdlp_collection_date_local
                if not collection_date_local:
                    from datetime import timedelta
                    utc_now = datetime.utcnow()
                    kst_offset = timedelta(hours=9)
                    kst_now = utc_now + kst_offset
                    collection_date_local = kst_now.strftime("%Y-%m-%d")
                
                # signal_boost_max 환경변수
                signal_boost_max = float(os.getenv("SIGNAL_BOOST_MAX", "0.30"))
                signal_match_mode = os.getenv("SIGNAL_MATCH_MODE", "substring_ko")
                
                # KR 트렌드 키워드 점수 계산
                kr_trend_keywords, kr_scoring_metadata = compute_kr_trend_keyword_scores(
                    ytdlp_snapshot_path=ytdlp_snapshot_path,
                    news_context_scores=news_scores,
                    signals_json_path=signals_json_path,
                    collection_date_local=collection_date_local,
                    signal_boost_max=signal_boost_max,
                    signal_match_mode=signal_match_mode,
                    ytdapi_trending_json_path=ytdapi_trending_json_path
                )
                
                # top N개 선택 (기본 50개)
                top_n = int(os.getenv("KR_TREND_KEYWORDS_TOP_N", "50"))
                kr_trend_keywords_top = kr_trend_keywords[:top_n]
                
                # 스냅샷 저장
                kr_trend_path = snapshot_dir / "kr_trend_keywords.json"
                with open(kr_trend_path, "w", encoding="utf-8") as f:
                    json.dump(kr_trend_keywords, f, ensure_ascii=False, indent=2)
                
                kr_trend_top_path = snapshot_dir / "kr_trend_keywords_top.json"
                with open(kr_trend_top_path, "w", encoding="utf-8") as f:
                    json.dump(kr_trend_keywords_top, f, ensure_ascii=False, indent=2)
                
                # global_keywords_candidates.json (기존 global_candidates 저장)
                global_candidates_path = snapshot_dir / "global_keywords_candidates.json"
                with open(global_candidates_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "ok": True,
                        "cycle_id": cycle_id,
                        "global_candidates": [c["keyword"] if isinstance(c, dict) else c for c in global_candidates],
                        "counts": {
                            "global_candidates": len(global_candidates)
                        }
                    }, f, ensure_ascii=False, indent=2)
                
                # global_context_candidates.jsonl (기존 스냅샷들을 JSONL로 저장, 비저장 스냅샷)
                global_context_path = snapshot_dir / "global_context_candidates.jsonl"
                with open(global_context_path, "w", encoding="utf-8") as f:
                    # 각 스냅샷을 한 줄씩 저장
                    context_items = []
                    if videos_list_snapshot:
                        context_items.append({"type": "youtube_videos_list", "data": videos_list_snapshot})
                    if news_context_snapshot:
                        context_items.append({"type": "news_context", "data": news_context_snapshot})
                    if wikidata_snapshot:
                        context_items.append({"type": "wikidata_wikipedia", "data": wikidata_snapshot})
                    
                    for item in context_items:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
                report["summary"]["kr_trend_keywords_count"] = len(kr_trend_keywords)
                report["summary"]["kr_trend_keywords_top_count"] = len(kr_trend_keywords_top)
                report["summary"]["kr_scoring_metadata"] = kr_scoring_metadata
            except Exception as e:
                # KR 트렌드 키워드 확정 실패해도 파이프라인은 계속 진행
                report["summary"]["warnings"].append(f"kr_trend_keywords_computation_failed: {type(e).__name__}: {str(e)}")
                pass
    
    # 카테고리별 처리
    for category in categories:
        cat_start = datetime.utcnow()
        
        # BULK 모드: category_keywords_map에서 가져오기
        if bulk_mode and 'category_keywords_map' in locals() and category in category_keywords_map:
            candidate_keywords = category_keywords_map[category]
            youtube_result = {
                "candidate_keywords": candidate_keywords,
                "source": "youtube_bulk_mode",
                "api_key_configured": True,
                "api_key_masked": None,
                "error": None
            }
        else:
            # 기존 로직 (fallback)
            youtube_result = fetch_youtube_keywords(category, max_results=max_keywords)
            candidate_keywords = youtube_result.get("candidate_keywords", [])
        
        trends_result = fetch_trends_scores(candidate_keywords, category)
        demand_score = trends_result.get("demand_score", {})
        
        dataset_result = fetch_trending_keywords(category)
        evidence_snapshot = dataset_result.get("evidence_snapshot", [])
        
        # BULK 모드가 아니면 Analytics 수집 (카테고리별)
        if not bulk_mode:
            analytics_result = fetch_analytics_top_videos(category, oauth_client_path, oauth_token_path)
            analytics_oauth_configured = analytics_result.get("oauth_configured", False)
            analytics_snapshot = analytics_result.get("snapshot", {})
            analytics_snapshot_ok = analytics_snapshot.get("ok", False)
            union_count = analytics_snapshot.get("merge", {}).get("union_count", 0)
            overlap_count = analytics_snapshot.get("merge", {}).get("overlap_count", 0)
            top_videos = analytics_result.get("top_videos", [])
            
            # analytics_used 판정: oauth_configured && snapshot_ok && union_count >= 1
            analytics_used = analytics_oauth_configured and analytics_snapshot_ok and union_count >= 1
            
            # analytics_hint 계산 (merged_set 기반)
            performance_hint = {}
            analytics_failed_reason = None
            if analytics_used and top_videos:
                api_key = os.getenv("YOUTUBE_API_KEY")
                performance_hint = _compute_analytics_hint(top_videos, api_key)
            elif analytics_oauth_configured and analytics_snapshot_ok and union_count == 0:
                analytics_failed_reason = "union_count_zero"
                performance_hint = {}
            elif analytics_oauth_configured and not analytics_snapshot_ok:
                error_info = analytics_result.get("error", "unknown_error")
                analytics_failed_reason = f"snapshot_failed: {error_info}"
                performance_hint = {}
            elif not analytics_oauth_configured:
                analytics_failed_reason = "oauth_not_configured"
                performance_hint = {}
            
            # Analytics audit 기록
            if analytics_oauth_configured:
                if analytics_used:
                    pass_watchtime_ok = analytics_snapshot.get("passes", {}).get("watchtime", {}).get("ok", False)
                    pass_views_ok = analytics_snapshot.get("passes", {}).get("views", {}).get("ok", False)
                    pass_watchtime_count = analytics_snapshot.get("passes", {}).get("watchtime", {}).get("returned_count", 0)
                    pass_views_count = analytics_snapshot.get("passes", {}).get("views", {}).get("returned_count", 0)
                    
                    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_ANALYTICS_FETCH_OK", {
                        "cycle_id": cycle_id,
                        "category": category,
                        "lookback_days": 30,
                        "top_k_each": 200,
                        "watchtime_ok": pass_watchtime_ok,
                        "views_ok": pass_views_ok,
                        "union_count": union_count,
                        "overlap_count": overlap_count
                    }).to_dict())
                    
                    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_ANALYTICS_USED", {
                        "cycle_id": cycle_id,
                        "category": category,
                        "union_count": union_count,
                        "overlap_count": overlap_count
                    }).to_dict())
                else:
                    error_info = analytics_result.get("error", "unknown_error")
                    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_ANALYTICS_FETCH_FAIL", {
                        "cycle_id": cycle_id,
                        "category": category,
                        "lookback_days": 30,
                        "top_k_each": 200,
                        "error_class": type(error_info).__name__ if error_info and not isinstance(error_info, str) else "Unknown",
                        "error_message": str(error_info) if error_info else "fetch_failed"
                    }).to_dict())
        else:
            # BULK 모드: analytics_result는 이미 수집됨 (BULK 모드 시작 부분에서)
            # BULK 모드에서는 카테고리별 analytics를 사용하지 않음
            if 'analytics_result' not in locals():
                analytics_result = {"oauth_configured": False, "snapshot": {}, "top_videos": []}
            analytics_oauth_configured = False
            analytics_snapshot = {}
            analytics_snapshot_ok = False
            union_count = 0
            overlap_count = 0
            analytics_used = False
            analytics_failed_reason = None
            performance_hint = {}
        
        # 스냅샷 저장 (성공/실패 관계없이 항상 생성)
        if mode == "run":
            _save_snapshots(cycle_id, category, youtube_result, trends_result, dataset_result, analytics_result)
            
            # 표준 스냅샷 파일용 데이터 누적
            trends_snapshot_all[category] = trends_result
            dataset_snapshot_all[category] = dataset_result
        
        # 스코어링
        scored = _score_keywords(candidate_keywords, demand_score, evidence_snapshot, performance_hint)
        
        # 최소 1개 보장
        if not scored:
            scored = [{
                "keyword": f"{category}_seed",
                "original": f"{category}_seed",
                "final_score": 0.0,
                "sources_count": 0,
                "youtube_present": False,
                "trends_score": 0.0,
                "dataset_present": False,
                "analytics_hint": 0.0,
                "source": "fallback_seed"
            }]
        
        # 저장
        scored_path = discovery_root / "scored" / f"{category}_{cycle_id}.json"
        with open(scored_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, ensure_ascii=False, indent=2)
        
        # 리포트
        cat_elapsed = (datetime.utcnow() - cat_start).total_seconds()
        pass_watchtime_count = 0
        pass_views_count = 0
        if not bulk_mode and 'analytics_snapshot' in locals():
            pass_watchtime_count = analytics_snapshot.get("passes", {}).get("watchtime", {}).get("returned_count", 0)
            pass_views_count = analytics_snapshot.get("passes", {}).get("views", {}).get("returned_count", 0)
        
        report["categories"][category] = {
            "keywords_count": len(candidate_keywords),
            "scored_count": len(scored),
            "elapsed_seconds": cat_elapsed,
            "youtube_configured": youtube_result.get("api_key_configured", False),
            "trends_available": trends_result.get("pytrends_available", False),
            "analytics_configured": analytics_oauth_configured if not bulk_mode else False,
            "analytics_used": analytics_used if not bulk_mode else False,
            "analytics_union_count": union_count if not bulk_mode else 0,
            "analytics_overlap_count": overlap_count if not bulk_mode else 0,
            "analytics_rows_watchtime": pass_watchtime_count,
            "analytics_rows_views": pass_views_count,
            "analytics_failed_reason": analytics_failed_reason if not bulk_mode else None
        }
        
        report["summary"]["total_keywords"] += len(candidate_keywords)
        report["summary"]["total_scored"] += len(scored)
        report["summary"]["category_candidates"][category] = len(candidate_keywords)
        
        # Audit: CATEGORY_DONE
        append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_CATEGORY_DONE", {
            "cycle_id": cycle_id,
            "category": category,
            "scored_count": len(scored)
        }).to_dict())
    
    # 리포트 저장
    ended_at = datetime.utcnow()
    report["ended_at"] = ended_at.isoformat() + "Z"
    report["total_elapsed_seconds"] = (ended_at - started_at).total_seconds()
    
    # BULK 모드 데이터 추가
    if bulk_mode:
        if videos_list_snapshot:
            report["summary"]["videos_requested"] = videos_list_snapshot.get("requested_video_ids", 0)
            report["summary"]["videos_fetched"] = videos_list_snapshot.get("fetched_items", 0)
        report["summary"]["global_candidates"] = len(global_candidates)
        report["summary"]["synthetic_used"] = report["summary"].get("synthetic_used", False)
    
    # yt-dlp 통계 추가
    # STEP B 최소 타이틀 기준: 스냅샷 라인 수 기반으로 재계산
    try:
        snapshot_file_for_titles = snapshot_dir / "ytdlp_channels_snapshot.jsonl"
        titles_from_snapshot = 0
        if snapshot_file_for_titles.exists():
            with open(snapshot_file_for_titles, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        titles_from_snapshot += 1
        ytdlp_title_count = titles_from_snapshot
        # 최소 타이틀 기준 미달 시 즉시 FAIL
        if ytdlp_title_count < min_titles_required:
            try:
                report["summary"].setdefault("warnings", []).append("YTDLP_TOO_FEW_TITLES")
            except Exception:
                pass
            raise RuntimeError("YTDLP_TOO_FEW_TITLES_FOR_VERIFY")
    except RuntimeError:
        # 위에서 명시적으로 발생시킨 에러는 그대로 전파
        raise
    except Exception:
        # 타이틀 재계산 실패 시 기존 값 유지
        pass
    
    report["summary"]["ytdlp_title_count"] = ytdlp_title_count
    report["summary"]["ytdlp_keyword_count"] = ytdlp_keyword_count
    report["summary"]["ytdlp_date_coverage_ratio"] = ytdlp_date_coverage_ratio
    if ytdlp_source_mode:
        report["summary"]["ytdlp_source_mode"] = ytdlp_source_mode
    if ytdlp_latest_n:
        report["summary"]["ytdlp_latest_n"] = ytdlp_latest_n
    if ytdlp_collection_date_local:
        report["summary"]["ytdlp_collection_date_local"] = ytdlp_collection_date_local
    
    # C-4: FAIL 증거 기록
    if ytdlp_title_count >= 1 and ytdlp_keyword_count == 0:
        try:
            report["summary"].setdefault("warnings", []).append("ytdlp_keywords_zero_with_titles")
        except Exception:
            pass
    
    report_path = discovery_root / "reports" / f"keyword_discovery_{cycle_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # C-3: SSOT summary 파일 생성 (STEP A~C 단일 SSOT 스키마)
    try:
        ssot_dir = get_root() / "ssot" / cycle_id
        ssot_dir.mkdir(parents=True, exist_ok=True)
        ssot_summary_path = ssot_dir / "ytdlp_ssot_summary.json"

        # STEP A: HTTPS / SSL 상태
        step_a_env = os.getenv("STEP_A_HTTPS_OK")
        if step_a_env is None:
            transport_https_ok = None
        else:
            transport_https_ok = step_a_env.strip().lower() in ["1", "true", "yes", "y"]
        ssl_cert_file = os.getenv("SSL_CERT_FILE")

        # STEP B: 제목 개수 (snapshots/<cycle_id>/ytdlp_channels_snapshot.jsonl 라인 수)
        snapshot_file = snapshot_dir / "ytdlp_channels_snapshot.jsonl"
        ssot_title_count = 0
        ssot_warnings: List[str] = []

        if snapshot_file.exists():
            try:
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            ssot_title_count += 1
            except Exception:
                ssot_warnings.append("YTDLP_SNAPSHOT_READ_ERROR")
        else:
            ssot_warnings.append("YTDLP_SNAPSHOT_MISSING")

        # STEP C: 후보 키워드 개수 (파일 집합 기반)
        candidate_files_used: List[str] = []
        candidate_total_count = 0

        def _accumulate_json_count(path: Path) -> int:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return len(data)
                if isinstance(data, dict):
                    return len(data)
            except Exception:
                ssot_warnings.append("YTDLP_CANDIDATES_READ_ERROR")
            return 0

        def _accumulate_jsonl_count(path: Path) -> int:
            count = 0
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            count += 1
            except Exception:
                ssot_warnings.append("YTDLP_CANDIDATES_READ_ERROR")
            return count

        # 1) global_keywords_candidates.json
        gk_file = snapshot_dir / "global_keywords_candidates.json"
        if gk_file.exists():
            candidate_files_used.append(gk_file.name)
            candidate_total_count += _accumulate_json_count(gk_file)

        # 2) global_context_candidates.jsonl
        gcc_file = snapshot_dir / "global_context_candidates.jsonl"
        if gcc_file.exists():
            candidate_files_used.append(gcc_file.name)
            candidate_total_count += _accumulate_jsonl_count(gcc_file)

        # 3) kr_trend_keywords.json
        kr_file = snapshot_dir / "kr_trend_keywords.json"
        if kr_file.exists():
            candidate_files_used.append(kr_file.name)
            candidate_total_count += _accumulate_json_count(kr_file)

        # 4) *_youtube.json, *_trends.json, *_dataset.json
        for pattern in ["*_youtube.json", "*_trends.json", "*_dataset.json"]:
            for p in snapshot_dir.glob(pattern):
                # 중복 파일명은 한 번만 집계
                if p.name in candidate_files_used:
                    continue
                candidate_files_used.append(p.name)
                candidate_total_count += _accumulate_json_count(p)

        ytdlp_candidate_keyword_count = int(candidate_total_count) if candidate_total_count > 0 else 0

        # 최종 키워드 개수는 STEP C에서는 확정하지 않음
        ytdlp_final_keyword_count = 0
        final_zero_reason = "PIPELINE_NOT_ADVANCED"
        final_zero_evidence = {
            "stage": "STEP_C",
            "candidate_count": int(ytdlp_candidate_keyword_count),
        }

        # STEP 상태 계산
        step_status = {
            "STEP_A": "PASS" if transport_https_ok is True else "FAIL",
            "STEP_B": "PASS" if ssot_title_count >= 1 else "FAIL",
            "STEP_C": "PASS" if ytdlp_candidate_keyword_count >= 1 else "FAIL",
        }

        # FAIL 시 warnings 규칙
        if step_status["STEP_A"] != "PASS":
            ssot_warnings.append("TRANSPORT_HTTPS_FAILED")
        if step_status["STEP_B"] != "PASS":
            ssot_warnings.append("YTDLP_TITLES_ZERO")
        if step_status["STEP_C"] != "PASS":
            ssot_warnings.append("YTDLP_CANDIDATES_ZERO")

        # 기존 warnings와 병합 (YTDLP_ 접두사 정규화)
        warnings_normalized: List[str] = []
        for w in report["summary"].get("warnings", []):
            if isinstance(w, str) and w.startswith("YTDLP_"):
                warnings_normalized.append("ytdlp_" + w[6:])
            else:
                warnings_normalized.append(w)

        # ssot_warnings 추가 (중복 제거 및 접두사 정규화)
        for w in ssot_warnings:
            w_norm = "ytdlp_" + w[6:] if isinstance(w, str) and w.startswith("YTDLP_") else w
            if w_norm not in warnings_normalized:
                warnings_normalized.append(w_norm)

        # SSOT 스키마에 맞춘 요약
        ssot_summary = {
            "cycle_id": cycle_id,
            "step_status": step_status,
            "summary": {
                "transport_https_ok": transport_https_ok,
                "ssl_cert_file": ssl_cert_file,
                "ytdlp_title_count": int(ssot_title_count),
                "ytdlp_candidate_keyword_count": int(ytdlp_candidate_keyword_count),
                "ytdlp_final_keyword_count": int(ytdlp_final_keyword_count),
                "final_zero_reason": final_zero_reason,
                "final_zero_evidence": final_zero_evidence,
                "candidate_files_used": candidate_files_used,
                "warnings": warnings_normalized,
            },
        }

        with open(ssot_summary_path, "w", encoding="utf-8") as f:
            json.dump(ssot_summary, f, ensure_ascii=False, indent=2)

        # E) Fail-Fast: STEP_B PASS인데 STEP_C FAIL이면 구조적 결선 오류로 간주
        if step_status["STEP_B"] == "PASS" and step_status["STEP_C"] == "FAIL":
            raise RuntimeError("YTDLP_CANDIDATE_EXTRACTION_ZERO_WITH_TITLES")

    except Exception as e:
        # 구조 오류(YTDLP_CANDIDATE_EXTRACTION_ZERO_WITH_TITLES)는 상위로 전파
        if isinstance(e, RuntimeError) and "YTDLP_CANDIDATE_EXTRACTION_ZERO_WITH_TITLES" in str(e):
            raise
        # 그 외 SSOT summary 생성 실패해도 파이프라인은 계속 진행
        try:
            report["summary"].setdefault("warnings", []).append(f"ssot_summary_write_failed: {type(e).__name__}")
        except Exception:
            pass
    
    # STEP D/E/F 실행 (A~C 이후 동일 cycle에서)
    step_d_status = "SKIP"
    step_e_status = "SKIP"
    step_f_contract_status = "SKIP"
    
    if mode == "run" and step_status.get("STEP_C") == "PASS":
        try:
            # STEP D: YouTube Data API 트렌드 앵커
            from backend.knowledge_v1.anchors.youtube_data_api_anchor import collect_trending_anchor
            
            anchor_region = os.getenv("ANCHOR_REGION", "KR")
            anchor_max = int(os.getenv("ANCHOR_MAX", "50"))
            
            anchor_result = collect_trending_anchor(
                region=anchor_region,
                max_keywords=anchor_max,
                cycle_id=cycle_id
            )
            
            if anchor_result.get("ok") and len(anchor_result.get("keywords", [])) >= 1:
                step_d_status = "PASS"
            else:
                step_d_status = "FAIL"
        except Exception as e:
            step_d_status = "FAIL"
            try:
                report["summary"].setdefault("warnings", []).append(f"step_d_failed: {type(e).__name__}")
            except Exception:
                pass
        
        if step_d_status == "PASS":
            try:
                # STEP E: 승격 게이트 + 지식 적재
                from backend.knowledge_v1.promotions.promotion_gate import promote_keywords
                from backend.knowledge_v1.knowledge_store.ingest_knowledge import ingest_knowledge
                
                kd_root = get_root() / "keyword_discovery"
                anchor_dir = kd_root / "anchors"
                anchor_file = anchor_dir / f"youtube_data_api_anchor_{anchor_region.lower()}.json"
                
                # 승격 게이트
                promo_result = promote_keywords(
                    cycle_id=cycle_id,
                    snapshot_dir=snapshot_dir,
                    anchor_file=anchor_file if anchor_file.exists() else None
                )
                
                if promo_result.get("ok") and promo_result.get("promoted_count", 0) >= 1:
                    # 지식 적재
                    promo_dir = kd_root / "promotions"
                    promoted_file = promo_dir / "promoted_keywords.jsonl"
                    
                    ingest_result = ingest_knowledge(
                        promoted_keywords_file=promoted_file,
                        cycle_id=cycle_id
                    )
                    
                    if ingest_result.get("ok") and ingest_result.get("ingested_count", 0) >= 1:
                        step_e_status = "PASS"
                    else:
                        step_e_status = "FAIL"
                else:
                    step_e_status = "FAIL"
            except Exception as e:
                step_e_status = "FAIL"
                try:
                    report["summary"].setdefault("warnings", []).append(f"step_e_failed: {type(e).__name__}")
                except Exception:
                    pass
            
            if step_e_status == "PASS":
                try:
                    # STEP F: 프롬프트 계약 스켈레톤
                    from backend.knowledge_v1.script_contracts.build_prompt_contract import build_prompt_contract
                    
                    kd_root = get_root() / "keyword_discovery"
                    promo_dir = kd_root / "promotions"
                    promoted_file = promo_dir / "promoted_keywords.jsonl"
                    
                    ks_dir = get_root() / "knowledge_store"
                    manifest_file = ks_dir / "manifest.jsonl"
                    
                    contract_result = build_prompt_contract(
                        cycle_id=cycle_id,
                        promoted_keywords_file=promoted_file,
                        knowledge_manifest_file=manifest_file
                    )
                    
                    if contract_result.get("ok") and len(contract_result.get("evidence_hashes", [])) >= 1:
                        step_f_contract_status = "PASS"
                    else:
                        step_f_contract_status = "FAIL"
                except Exception as e:
                    step_f_contract_status = "FAIL"
                    try:
                        report["summary"].setdefault("warnings", []).append(f"step_f_contract_failed: {type(e).__name__}")
                    except Exception:
                        pass
    
    # SSOT summary에 STEP D/E/F 상태 추가
    try:
        ssot_summary_path = get_root() / "ssot" / cycle_id / "ytdlp_ssot_summary.json"
        if ssot_summary_path.exists():
            with open(ssot_summary_path, "r", encoding="utf-8") as f:
                ssot_data = json.load(f)
            
            ssot_data["step_status"]["STEP_D"] = step_d_status
            ssot_data["step_status"]["STEP_E"] = step_e_status
            ssot_data["step_status"]["STEP_F_CONTRACT"] = step_f_contract_status
            
            with open(ssot_summary_path, "w", encoding="utf-8") as f:
                json.dump(ssot_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    
    # 표준 스냅샷 파일명 병행 저장 (try/except로 감싸서 실패해도 파이프라인 중단 방지)
    if mode == "run":
        # snapshot_dir는 이미 위에서 계산됨 (단 1번만 계산)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # trends_snapshot.json
            trends_standard_path = snapshot_dir / "trends_snapshot.json"
            with open(trends_standard_path, "w", encoding="utf-8") as f:
                json.dump(trends_snapshot_all, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 실패해도 파이프라인은 계속 진행
        
        try:
            # trending_dataset_snapshot.json
            dataset_standard_path = snapshot_dir / "trending_dataset_snapshot.json"
            with open(dataset_standard_path, "w", encoding="utf-8") as f:
                json.dump(dataset_snapshot_all, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 실패해도 파이프라인은 계속 진행
        
        # BULK 모드 스냅샷 저장 (항상 생성 보장)
        if bulk_mode:
            # youtube_platform_top_videos.json (항상 생성)
            try:
                video_ids_count = len(video_ids) if video_ids else 0
                videos_requested = max_videos
                videos_fetched = videos_list_snapshot.get("fetched_items", 0) if videos_list_snapshot else 0
                
                if not platform_top_snapshot:
                    platform_top_snapshot = {
                        "ok": False,
                        "source": "none",
                        "selected_video_ids": [],
                        "counts": {
                            "video_ids": video_ids_count,
                            "videos_requested": videos_requested,
                            "videos_fetched": videos_fetched
                        },
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "reason": "NO_VIDEO_IDS"
                    }
                else:
                    # 스키마 통일: selected_video_ids, counts, ts 포함
                    if "selected_video_ids" not in platform_top_snapshot:
                        platform_top_snapshot["selected_video_ids"] = platform_top_snapshot.get("sampled_video_ids", [])[:300]
                    if "counts" not in platform_top_snapshot or "video_ids" not in platform_top_snapshot.get("counts", {}):
                        platform_top_snapshot["counts"] = {
                            "video_ids": video_ids_count,
                            "videos_requested": videos_requested,
                            "videos_fetched": videos_fetched
                        }
                    if "ts" not in platform_top_snapshot:
                        platform_top_snapshot["ts"] = datetime.utcnow().isoformat() + "Z"
                    if video_ids_count == 0 and "reason" not in platform_top_snapshot:
                        platform_top_snapshot["reason"] = "NO_VIDEO_IDS"
                    if "source" not in platform_top_snapshot:
                        platform_top_snapshot["source"] = platform_top_snapshot.get("source", "youtube_data_api_search")
                
                platform_top_path = snapshot_dir / "youtube_platform_top_videos.json"
                with open(platform_top_path, "w", encoding="utf-8") as f:
                    json.dump(platform_top_snapshot, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    video_ids_count = len(video_ids) if video_ids else 0
                    platform_top_path = snapshot_dir / "youtube_platform_top_videos.json"
                    with open(platform_top_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "source": "none",
                            "selected_video_ids": [],
                            "counts": {
                                "video_ids": video_ids_count,
                                "videos_requested": max_videos,
                                "videos_fetched": 0
                            },
                            "ts": datetime.utcnow().isoformat() + "Z",
                            "reason": "NO_VIDEO_IDS"
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            # youtube_videos_list_snapshot.json (항상 생성)
            try:
                if not videos_list_snapshot:
                    videos_list_snapshot = {
                        "ok": False,
                        "requested_video_ids": 0,
                        "fetched_items": 0,
                        "missing_video_ids": 0,
                        "batches": 0,
                        "errors": [{"batch_index": 0, "http_status": None, "message": "videos_list_snapshot_not_created"}],
                        "items": []
                    }
                videos_list_path = snapshot_dir / "youtube_videos_list_snapshot.json"
                with open(videos_list_path, "w", encoding="utf-8") as f:
                    json.dump(videos_list_snapshot, f, ensure_ascii=False, indent=2)
                
                # Audit: VIDEOS_LIST_OK/FAIL
                if videos_list_snapshot.get("ok"):
                    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_VIDEOS_LIST_OK", {
                        "cycle_id": cycle_id,
                        "fetched_items": videos_list_snapshot.get("fetched_items", 0)
                    }).to_dict())
                else:
                    errors = videos_list_snapshot.get("errors", [])
                    error_msg = errors[0].get("message", "unknown_error") if errors else "fetched_items=0"
                    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_VIDEOS_LIST_FAIL", {
                        "cycle_id": cycle_id,
                        "error": error_msg
                    }).to_dict())
            except Exception as e:
                # 실패해도 최소 구조 생성
                try:
                    videos_list_path = snapshot_dir / "youtube_videos_list_snapshot.json"
                    with open(videos_list_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "requested_video_ids": 0,
                            "fetched_items": 0,
                            "missing_video_ids": 0,
                            "batches": 0,
                            "errors": [{"batch_index": 0, "http_status": None, "message": f"snapshot_write_error: {type(e).__name__}"}],
                            "items": []
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            # keyword_candidates_snapshot.json (항상 생성)
            try:
                if not keyword_candidates_snapshot:
                    keyword_candidates_snapshot = {
                        "ok": False,
                        "global_candidates": [],
                        "category_candidates": {},
                        "counts": {
                            "global_candidates": 0,
                            "category_candidates": {}
                        },
                        "error": "keyword_candidates_snapshot_not_created"
                    }
                candidates_path = snapshot_dir / "keyword_candidates_snapshot.json"
                with open(candidates_path, "w", encoding="utf-8") as f:
                    json.dump(keyword_candidates_snapshot, f, ensure_ascii=False, indent=2)
            except Exception as e:
                # 실패해도 최소 구조 생성
                try:
                    candidates_path = snapshot_dir / "keyword_candidates_snapshot.json"
                    with open(candidates_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "global_candidates": [],
                            "category_candidates": {},
                            "counts": {
                                "global_candidates": 0,
                                "category_candidates": {}
                            },
                            "error": f"snapshot_write_error: {type(e).__name__}"
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            # wikidata_wikipedia_snapshot.json (항상 생성)
            try:
                if not wikidata_snapshot:
                    wikidata_snapshot = {
                        "ok": False,
                        "mode": "stub",
                        "used_sources": [],
                        "mapping_hints": {},
                        "errors": [{"message": "wikidata_snapshot_not_created"}]
                    }
                wikidata_path = snapshot_dir / "wikidata_wikipedia_snapshot.json"
                with open(wikidata_path, "w", encoding="utf-8") as f:
                    json.dump(wikidata_snapshot, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    wikidata_path = snapshot_dir / "wikidata_wikipedia_snapshot.json"
                    with open(wikidata_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "mode": "stub",
                            "used_sources": [],
                            "mapping_hints": {},
                            "errors": [{"message": f"snapshot_write_error: {type(e).__name__}"}]
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            # news_context_snapshot.json (항상 생성)
            try:
                if not news_context_snapshot:
                    news_context_snapshot = {
                        "ok": False,
                        "provider": "rss",
                        "items_count": 0,
                        "top_headlines": [],
                        "errors": [{"message": "news_context_snapshot_not_created"}]
                    }
                news_path = snapshot_dir / "news_context_snapshot.json"
                with open(news_path, "w", encoding="utf-8") as f:
                    json.dump(news_context_snapshot, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    news_path = snapshot_dir / "news_context_snapshot.json"
                    with open(news_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "provider": "rss",
                            "items_count": 0,
                            "top_headlines": [],
                            "errors": [{"message": f"snapshot_write_error: {type(e).__name__}"}]
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            # trends_snapshot.json / trending_dataset_snapshot.json (항상 생성 보장)
            try:
                if not trends_snapshot_all:
                    trends_snapshot_all = {}
                trends_standard_path = snapshot_dir / "trends_snapshot.json"
                with open(trends_standard_path, "w", encoding="utf-8") as f:
                    json.dump(trends_snapshot_all, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    trends_standard_path = snapshot_dir / "trends_snapshot.json"
                    with open(trends_standard_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "error": f"snapshot_write_error: {type(e).__name__}",
                            "categories": {}
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            
            try:
                if not dataset_snapshot_all:
                    dataset_snapshot_all = {}
                dataset_standard_path = snapshot_dir / "trending_dataset_snapshot.json"
                with open(dataset_standard_path, "w", encoding="utf-8") as f:
                    json.dump(dataset_snapshot_all, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    dataset_standard_path = snapshot_dir / "trending_dataset_snapshot.json"
                    with open(dataset_standard_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "ok": False,
                            "error": f"snapshot_write_error: {type(e).__name__}",
                            "categories": {}
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
    
    # Audit: END
    append_jsonl(audit_path, AuditEvent.create("KEYWORD_DISCOVERY_END", {
        "cycle_id": cycle_id,
        "total_scored": report["summary"]["total_scored"]
    }).to_dict())
    
    return report

