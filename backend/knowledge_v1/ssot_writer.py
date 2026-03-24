"""
SSOT Writer - daily_keywords_gate1.json 생성
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from backend.knowledge_v1.paths import get_root


def _read_ytdlp_ssot_summary(cycle_id: str) -> Optional[Dict[str, Any]]:
    """ytdlp_ssot_summary.json 읽기"""
    root = get_root()
    ssot_file = root / "ssot" / cycle_id / "ytdlp_ssot_summary.json"
    
    if not ssot_file.exists():
        return None
    
    try:
        with open(ssot_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_anchor_keywords_count() -> Optional[int]:
    """anchor 파일에서 keywords count 읽기"""
    root = get_root()
    anchor_file = root / "keyword_discovery" / "anchors" / "youtube_data_api_anchor_kr.json"
    
    if not anchor_file.exists():
        return None
    
    try:
        with open(anchor_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            keywords = data.get("keywords", [])
            if isinstance(keywords, list):
                return len(keywords)
            return None
    except Exception:
        return None


def _read_assets_count() -> Optional[int]:
    """assets.jsonl 라인수 읽기"""
    root = get_root()
    assets_file = root / "discovery" / "raw" / "assets.jsonl"
    
    if not assets_file.exists():
        return None
    
    try:
        with open(assets_file, "r", encoding="utf-8") as f:
            count = sum(1 for line in f if line.strip())
            return count if count > 0 else None
    except Exception:
        return None


def _read_step_f_evidence_hashes_count(cycle_id: str) -> Optional[int]:
    """Step F prompt_manifest.json 최신 1개에서 evidence_hashes count 읽기"""
    root = get_root()
    script_prompts_dir = root / "script_prompts"
    
    if not script_prompts_dir.exists():
        return None
    
    # cycle_id로 시작하는 디렉토리 중 최신 것 찾기
    candidates = []
    for d in script_prompts_dir.iterdir():
        if d.is_dir() and d.name.startswith(cycle_id):
            manifest_file = d / "prompt_manifest.json"
            if manifest_file.exists():
                try:
                    mtime = manifest_file.stat().st_mtime
                    candidates.append((mtime, manifest_file))
                except Exception:
                    continue
    
    if not candidates:
        return None
    
    # 최신 파일 선택
    candidates.sort(key=lambda x: x[0], reverse=True)
    manifest_file = candidates[0][1]
    
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            evidence_hashes = data.get("evidence_hashes", [])
            if isinstance(evidence_hashes, list):
                return len(evidence_hashes)
            return None
    except Exception:
        return None


def write_gate1(cycle_id: str) -> Dict[str, Any]:
    """
    daily_keywords_gate1.json 생성
    
    Args:
        cycle_id: cycle_id
    
    Returns:
        {"ok": bool, "path": str, "error": Optional[str]}
    """
    root = get_root()
    ssot_dir = root / "ssot" / cycle_id
    ssot_dir.mkdir(parents=True, exist_ok=True)
    
    gate1_file = ssot_dir / "daily_keywords_gate1.json"
    
    # ytdlp_ssot_summary.json 읽기 (필수)
    ytdlp_summary = _read_ytdlp_ssot_summary(cycle_id)
    if not ytdlp_summary:
        return {
            "ok": False,
            "error": "ytdlp_ssot_summary.json not found",
            "path": str(gate1_file)
        }
    
    # summary에서 값 추출 (fallback 규칙)
    summary_data = ytdlp_summary.get("summary", {})
    ytdlp_title_count = summary_data.get("ytdlp_title_count", 0)
    
    # ytdlp_keyword_count fallback 규칙
    ytdlp_keyword_count = summary_data.get("ytdlp_keyword_count")
    if ytdlp_keyword_count is None:
        ytdlp_keyword_count = summary_data.get("ytdlp_candidate_keyword_count", 0)
    if ytdlp_keyword_count is None:
        ytdlp_keyword_count = 0
    
    # 선택 입력 읽기
    anchor_keywords_count = _read_anchor_keywords_count()
    assets_count = _read_assets_count()
    step_f_evidence_hashes_count = _read_step_f_evidence_hashes_count(cycle_id)
    
    # sources 경로 수집
    sources = {
        "ytdlp_ssot_summary_path": str(root / "ssot" / cycle_id / "ytdlp_ssot_summary.json"),
        "anchor_path": str(root / "keyword_discovery" / "anchors" / "youtube_data_api_anchor_kr.json") if anchor_keywords_count is not None else None,
        "ingestion_stats_path": str(root / "discovery" / "raw" / "assets.jsonl") if assets_count is not None else None,
        "step_f_manifest_path": None
    }
    
    # step_f_manifest_path 찾기
    if step_f_evidence_hashes_count is not None:
        script_prompts_dir = root / "script_prompts"
        if script_prompts_dir.exists():
            for d in script_prompts_dir.iterdir():
                if d.is_dir() and d.name.startswith(cycle_id):
                    manifest_file = d / "prompt_manifest.json"
                    if manifest_file.exists():
                        sources["step_f_manifest_path"] = str(manifest_file)
                        break
    
    # warnings 수집
    warnings = []
    if ytdlp_title_count == 0:
        warnings.append("ytdlp_title_count_zero")
    if ytdlp_keyword_count == 0:
        warnings.append("ytdlp_keyword_count_zero")
    if assets_count is not None and assets_count < 200:
        warnings.append("assets_count_below_threshold")
    if step_f_evidence_hashes_count is not None and step_f_evidence_hashes_count == 0:
        warnings.append("step_f_evidence_hashes_zero")
    
    # gate1 JSON 생성
    gate1_data = {
        "ok": True,
        "cycle_id": cycle_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "ytdlp_title_count": ytdlp_title_count,
            "ytdlp_keyword_count": ytdlp_keyword_count,
            "step_d_anchor_keywords_count": anchor_keywords_count,
            "step_e_assets_count": assets_count,
            "step_f_evidence_hashes_count": step_f_evidence_hashes_count,
            "warnings": warnings
        },
        "sources": sources
    }
    
    # 파일 저장
    try:
        with open(gate1_file, "w", encoding="utf-8") as f:
            json.dump(gate1_data, f, ensure_ascii=False, indent=2)
        
        return {
            "ok": True,
            "path": str(gate1_file),
            "cycle_id": cycle_id
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to write gate1 file: {type(e).__name__}: {e}",
            "path": str(gate1_file)
        }

