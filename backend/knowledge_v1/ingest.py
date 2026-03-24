"""
Knowledge v1 Ingest - 자동 수집
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.knowledge_v1.schema import KnowledgeAsset
from backend.knowledge_v1.store import append_jsonl, compute_raw_hash
from backend.knowledge_v1.paths import get_assets_path, ensure_dirs
from backend.knowledge_v1.registry import get_sources_by_category
from backend.knowledge_v1.audit import log_event
from backend.knowledge_v1.fallback import create_fallback_asset


def ingest(category: str, keywords: List[str], depth: str = "normal", mode: str = "dry-run") -> List[KnowledgeAsset]:
    """
    지식 자동 수집
    
    Args:
        category: 카테고리 (papers 포함 모든 카테고리 허용)
        keywords: 키워드 리스트
        depth: 수집 깊이 (normal|deep)
        mode: 모드 (dry-run|run)
    
    Returns:
        List[KnowledgeAsset]: 수집된 자산 리스트 (최소 1건 보장)
    """
    import traceback
    
    # (2-1) ingest 실행 시작 시 audit 기록 (항상)
    try:
        log_event("INGEST_RUN_START", {
            "category": category,
            "keywords": keywords,
            "mode": mode,
            "depth": depth,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        # audit 기록 실패해도 계속 진행
        pass
    
    assets = []
    used_fallback = False
    
    try:
        sources = get_sources_by_category(category)
        
        # (2-2) 수집 수행
        if mode in ["dry-run", "run"]:
            # fixtures에서 payload 로드
            fixtures_path = Path(__file__).parent / "fixtures" / "sample_payloads.jsonl"
            if fixtures_path.exists():
                try:
                    with open(fixtures_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                payload_data = json.loads(line)
                                if payload_data.get("category") == category:
                                    payload_keywords = payload_data.get("keywords", [])
                                    # 키워드 매칭 (하나라도 포함되면)
                                    if any(kw.lower() in str(payload_keywords).lower() or str(payload_keywords).lower() in kw.lower() for kw in keywords):
                                        source_id = payload_data.get("source_id")
                                        source = next((s for s in sources if s.get("source_id") == source_id), None)
                                        if source:
                                            asset = KnowledgeAsset.create(
                                                category=category,
                                                keywords=keywords,
                                                source_id=source_id,
                                                source_ref=source.get("fetch_template", ""),
                                                payload=payload_data.get("payload", {}),
                                                license_status=source.get("license_profile", "UNKNOWN"),
                                                usage_rights=source.get("usage_rights", "UNKNOWN"),
                                                trust_level=source.get("trust_level_default", "MEDIUM"),
                                                impact_scope=source.get("impact_scope_default", "MEDIUM")
                                            )
                                            asset.raw_hash = compute_raw_hash(asset.payload)
                                            assets.append(asset)
                            except json.JSONDecodeError:
                                # JSON 파싱 실패는 무시하고 계속
                                continue
                except Exception as e:
                    # 파일 읽기 실패는 audit에 기록
                    log_event("INGEST_ERROR", {
                        "error_class": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc()[:500],  # 최대 500자
                        "stage": "fixture_load"
                    })
        else:
            # 유효하지 않은 mode
            raise ValueError(f"Invalid mode: {mode}. Must be 'dry-run' or 'run'")
        
        # (2-3) 수집 결과가 0건이면 fallback asset 생성
        if len(assets) == 0:
            try:
                fallback_asset = create_fallback_asset(category, keywords)
                assets.append(fallback_asset)
                used_fallback = True
                
                # (2-4) fallback 발생 시 audit 기록
                log_event("INGEST_FALLBACK_CREATED", {
                    "asset_id": fallback_asset.asset_id,
                    "category": category,
                    "keywords": keywords,
                    "reason": "NO_SOURCE_MATCH"
                })
            except Exception as e:
                # fallback 생성 실패는 심각한 오류
                log_event("INGEST_ERROR", {
                    "error_class": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()[:500],
                    "stage": "fallback_creation"
                })
                raise  # fallback 생성 실패는 재발생
        
        # 저장 (경로 보장)
        assets_path = get_assets_path("approved")
        ensure_dirs("approved")
        
        # LEGACY DATA POLICY: 기존 assets.jsonl 삭제 (깨끗한 상태 보장)
        if assets_path.exists():
            assets_path.unlink()
        
        for asset in assets:
            try:
                # HARD GUARD: category 검증 (persistence 전)
                asset.validate()
                
                # category 전파 확인: payload에서 category가 있으면 top-level에 반영
                if isinstance(asset.payload, dict) and "category" in asset.payload:
                    payload_category = asset.payload.get("category", "")
                    if payload_category and payload_category != asset.category:
                        # payload의 category가 다르면 top-level을 우선하되 경고는 하지 않음 (이미 create에서 처리됨)
                        pass
                
                append_jsonl(assets_path, asset.to_dict())
                # 기존 INGEST 이벤트는 유지 (fallback도 포함)
                log_event("INGEST", {
                    "asset_id": asset.asset_id,
                    "category": category,
                    "keywords": keywords,
                    "source_id": asset.source_id,
                    "is_fallback": asset.source_id == "fallback_synthetic"
                })
            except Exception as e:
                # 개별 asset 저장 실패는 audit에 기록하되 계속 진행
                log_event("INGEST_ERROR", {
                    "error_class": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()[:500],
                    "stage": "asset_save",
                    "asset_id": asset.asset_id
                })
        
        # (2-6) ingest 실행 종료 시 audit 기록 (항상)
        log_event("INGEST_RUN_END", {
            "category": category,
            "total_ingested_assets": len(assets),
            "used_fallback": used_fallback,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        # 전체 ingest 실패 시 audit에 기록
        log_event("INGEST_ERROR", {
            "error_class": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()[:500],
            "stage": "ingest_main"
        })
        # INGEST_RUN_END는 실패해도 기록 시도
        try:
            log_event("INGEST_RUN_END", {
                "category": category,
                "total_ingested_assets": len(assets),
                "used_fallback": used_fallback,
                "error": True,
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        except:
            pass
        # 예외 재발생 (호출자가 처리)
        raise
    
    return assets

