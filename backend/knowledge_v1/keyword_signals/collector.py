"""
Keyword Signals Collector - 외부 트렌드 신호 수집 통합 모듈
"""

import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.knowledge_v1.paths import get_root
from backend.knowledge_v1.keyword_signals.schema import (
    create_empty_signals_json,
    create_source_entry,
    create_signal_item,
    validate_signals_json
)
from backend.knowledge_v1.keyword_signals.manual_seed import (
    load_manual_keywords,
    load_manual_channels
)
from backend.knowledge_v1.keyword_signals.ytdapi_trending import (
    collect_ytdapi_trending
)


def _collect_google_trends(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """Google Trends 신호 수집 (현재는 disabled만 지원)"""
    enabled = os.getenv("GOOGLE_TRENDS_ENABLED", "0") in ["1", "true", "True"]
    
    if not enabled:
        return create_source_entry(
            name="google_trends",
            enabled=False,
            status="skipped",
            skipped_reason="disabled",
            meta={"region": "KR", "time_window": "now 7-d"}
        )
    
    # API 접근 불가 (pytrends API 키 불필요하지만 rate limit/쿠키 등 이슈)
    # 현재는 기본적으로 skipped
    return create_source_entry(
        name="google_trends",
        enabled=True,
        status="skipped",
        skipped_reason="no_api_access",
        meta={"region": "KR", "time_window": "now 7-d"}
    )


def _collect_nox_influencer(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """NoxInfluencer 신호 수집 (현재는 disabled만 지원)"""
    enabled = os.getenv("NOX_ENABLED", "0") in ["1", "true", "True"]
    
    if not enabled:
        return create_source_entry(
            name="nox_influencer",
            enabled=False,
            status="skipped",
            skipped_reason="disabled",
            meta={"note": "channel discovery signal only by default"}
        )
    
    # API 키 필요 (현재 없음)
    return create_source_entry(
        name="nox_influencer",
        enabled=True,
        status="skipped",
        skipped_reason="no_api_key",
        meta={"note": "channel discovery signal only by default"}
    )


def _collect_socialblade(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """SocialBlade 신호 수집 (현재는 disabled만 지원)"""
    enabled = os.getenv("SOCIALBLADE_ENABLED", "0") in ["1", "true", "True"]
    
    if not enabled:
        return create_source_entry(
            name="socialblade",
            enabled=False,
            status="skipped",
            skipped_reason="disabled",
            meta={"note": "channel meta signal only by default"}
        )
    
    # API 키 필요 (현재 없음)
    return create_source_entry(
        name="socialblade",
        enabled=True,
        status="skipped",
        skipped_reason="no_api_key",
        meta={"note": "channel meta signal only by default"}
    )


def _collect_vling(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """vling 신호 수집 (현재는 disabled만 지원)"""
    enabled = os.getenv("VLING_ENABLED", "0") in ["1", "true", "True"]
    
    if not enabled:
        return create_source_entry(
            name="vling",
            enabled=False,
            status="skipped",
            skipped_reason="disabled",
            meta={"note": "trend ranking signal if available"}
        )
    
    # 계약 필요 (현재 없음)
    return create_source_entry(
        name="vling",
        enabled=True,
        status="skipped",
        skipped_reason="no_contract",
        meta={"note": "trend ranking signal if available"}
    )


def _collect_manual_seed(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """수동 seed 신호 수집"""
    enabled = os.getenv("MANUAL_SEED_ENABLED", "1") in ["1", "true", "True"]
    
    if not enabled:
        return create_source_entry(
            name="manual_seed",
            enabled=False,
            status="skipped",
            skipped_reason="disabled",
            meta={
                "keywords_file": os.getenv("KR_MANUAL_SEED_KEYWORDS_FILE", "backend/config/kr_manual_seed_keywords.txt"),
                "channels_file": os.getenv("KR_MANUAL_SEED_CHANNELS_FILE", "backend/config/kr_manual_seed_channels.txt")
            }
        )
    
    try:
        # 키워드 로드
        keywords_file = os.getenv("KR_MANUAL_SEED_KEYWORDS_FILE", "backend/config/kr_manual_seed_keywords.txt")
        keywords, kw_error = load_manual_keywords(keywords_file)
        
        # 채널 로드 (선택적)
        channels_file = os.getenv("KR_MANUAL_SEED_CHANNELS_FILE", "backend/config/kr_manual_seed_channels.txt")
        channels, ch_error = load_manual_channels(channels_file)
        
        # items 생성 (키워드만, score=1.0)
        items = []
        for rank, keyword in enumerate(keywords, 1):
            items.append(create_signal_item(
                term=keyword,
                score=1.0,
                rank=rank,
                evidence={
                    "provider": "manual_seed",
                    "raw": {"line": rank}
                }
            ))
        
        status = "ok"
        if kw_error:
            status = "error"
        
        return create_source_entry(
            name="manual_seed",
            enabled=True,
            status=status,
            skipped_reason=None if status == "ok" else kw_error,
            meta={
                "keywords_file": keywords_file,
                "channels_file": channels_file,
                "keywords_count": len(keywords),
                "channels_count": len(channels) if not ch_error else None
            },
            items=items
        )
    except Exception as e:
        return create_source_entry(
            name="manual_seed",
            enabled=True,
            status="error",
            skipped_reason=f"exception: {type(e).__name__}: {str(e)}",
            meta={
                "keywords_file": os.getenv("KR_MANUAL_SEED_KEYWORDS_FILE", "backend/config/kr_manual_seed_keywords.txt"),
                "channels_file": os.getenv("KR_MANUAL_SEED_CHANNELS_FILE", "backend/config/kr_manual_seed_channels.txt")
            }
        )


def collect_kr_trend_signals(
    cycle_id: str,
    snapshot_dir: Path
) -> Dict[str, Any]:
    """
    KR 트렌드 신호 수집 (모든 소스 통합)
    
    Args:
        cycle_id: 사이클 ID
        snapshot_dir: 스냅샷 디렉토리 Path
    
    Returns:
        {
            "signals_path": str,
            "errors_path": str,
            "ok": bool
        }
    """
    enabled = os.getenv("KEYWORD_SIGNALS_ENABLED", "1") in ["1", "true", "True"]
    
    # signals 디렉토리 생성
    signals_dir = snapshot_dir / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    
    signals_path = signals_dir / "kr_trend_signals.json"
    errors_path = signals_dir / "kr_trend_signals_errors.json"
    
    errors = []
    sources = []
    
    if not enabled:
        # disabled인 경우에도 빈 JSON 생성 (추적 가능하도록)
        signals_json = create_empty_signals_json(cycle_id)
        signals_json["sources"] = [
            create_source_entry(
                name="all",
                enabled=False,
                status="skipped",
                skipped_reason="KEYWORD_SIGNALS_ENABLED=0",
                meta={}
            )
        ]
        
        with open(signals_path, "w", encoding="utf-8") as f:
            json.dump(signals_json, f, ensure_ascii=False, indent=2)
        
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        return {
            "signals_path": str(signals_path),
            "errors_path": str(errors_path),
            "ok": True
        }
    
    # 각 소스 수집
    try:
        sources.append(_collect_google_trends(cycle_id, snapshot_dir))
    except Exception as e:
        error_msg = f"google_trends: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "google_trends",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        sources.append(create_source_entry(
            name="google_trends",
            enabled=True,
            status="error",
            skipped_reason=error_msg,
            meta={}
        ))
    
    try:
        sources.append(_collect_nox_influencer(cycle_id, snapshot_dir))
    except Exception as e:
        error_msg = f"nox_influencer: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "nox_influencer",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        sources.append(create_source_entry(
            name="nox_influencer",
            enabled=True,
            status="error",
            skipped_reason=error_msg,
            meta={}
        ))
    
    try:
        sources.append(_collect_socialblade(cycle_id, snapshot_dir))
    except Exception as e:
        error_msg = f"socialblade: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "socialblade",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        sources.append(create_source_entry(
            name="socialblade",
            enabled=True,
            status="error",
            skipped_reason=error_msg,
            meta={}
        ))
    
    try:
        sources.append(_collect_vling(cycle_id, snapshot_dir))
    except Exception as e:
        error_msg = f"vling: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "vling",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        sources.append(create_source_entry(
            name="vling",
            enabled=True,
            status="error",
            skipped_reason=error_msg,
            meta={}
        ))
    
    try:
        sources.append(_collect_manual_seed(cycle_id, snapshot_dir))
    except Exception as e:
        error_msg = f"manual_seed: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "manual_seed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        sources.append(create_source_entry(
            name="manual_seed",
            enabled=True,
            status="error",
            skipped_reason=error_msg,
            meta={}
        ))
    
    # YouTube Data API 트렌딩 수집 (별도 파일로 저장, kr_trend_signals.json과 분리)
    ytdapi_result = None
    try:
        ytdapi_result = collect_ytdapi_trending(
            cycle_id=cycle_id,
            snapshot_dir=snapshot_dir,
            region_code=os.getenv("YTDAPI_REGION_CODE", "KR"),
            max_results=int(os.getenv("YTDAPI_MAXRESULTS", "50")),
            categories_file=os.getenv("YTDAPI_CATEGORIES_FILE", "backend/config/ytdapi_trending_categories_kr.json"),
            quota_max_units=int(os.getenv("YTDAPI_QUOTA_MAX_UNITS_PER_RUN", "50"))
        )
    except Exception as e:
        error_msg = f"ytdapi_trending: {type(e).__name__}: {str(e)}"
        errors.append({
            "source": "ytdapi_trending",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
    
    # signals JSON 생성
    signals_json = create_empty_signals_json(cycle_id)
    signals_json["sources"] = sources
    
    # 검증
    is_valid, validation_error = validate_signals_json(signals_json)
    if not is_valid:
        errors.append({
            "source": "validation",
            "error_type": "ValidationError",
            "error_message": validation_error,
            "traceback": None
        })
    
    # 파일 저장
    try:
        with open(signals_path, "w", encoding="utf-8") as f:
            json.dump(signals_json, f, ensure_ascii=False, indent=2)
    except Exception as e:
        errors.append({
            "source": "file_write",
            "error_type": type(e).__name__,
            "error_message": f"failed to write signals_path: {str(e)}",
            "traceback": traceback.format_exc()
        })
    
    try:
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # errors 파일 쓰기 실패는 로그만 남기고 계속 진행
        pass
    
    return {
        "signals_path": str(signals_path),
        "errors_path": str(errors_path),
        "ok": is_valid and len([s for s in sources if s.get("status") == "error"]) == 0,
        "sources_count": len(sources),
        "errors_count": len(errors)
    }

