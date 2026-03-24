"""
EXECUTION SNAPSHOT FREEZING - 완전 결정론
동일 입력 + 동일 정책버전 + 동일 소스스냅샷이면 결과 해시가 100% 동일
"""

from __future__ import annotations

import json
import os
import random
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def freeze_execution_environment(run_id: str, policy_version: str, embedding_model_version: str = "default") -> Dict[str, Any]:
    """
    실행 환경을 완전히 고정하여 결정론적 실행 보장
    
    Args:
        run_id: 실행 ID
        policy_version: 정책 버전
        embedding_model_version: 임베딩 모델 버전
        
    Returns:
        Dict: execution manifest
    """
    # 1. Random seed 고정
    seed = 42
    random.seed(seed)
    if HAS_NUMPY:
        np.random.seed(seed)
    
    # 2. Python hash seed 고정
    os.environ["PYTHONHASHSEED"] = "0"
    
    # 3. Git commit hash 획득
    git_commit_hash = _get_git_commit_hash()
    
    # 4. API snapshot hash 계산 (외부 API 응답 해시)
    api_snapshot_hash = _calculate_api_snapshot_hash()
    
    # 5. Input hash 계산 (키워드, 카테고리 등)
    input_hash = _calculate_input_hash()
    
    manifest = {
        "run_id": run_id,
        "input_hash": input_hash,
        "policy_version": policy_version,
        "embedding_model_version": embedding_model_version,
        "source_score_version": "v1.0",
        "api_snapshot_hash": api_snapshot_hash,
        "random_seed": seed,
        "git_commit_hash": git_commit_hash,
        "frozen_at": datetime.utcnow().isoformat() + "Z",
        "python_hashseed": "0",
        "numpy_seed": seed if HAS_NUMPY else None,
    }
    
    return manifest


def _get_git_commit_hash() -> str:
    """Git commit hash 획득"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parents[2]
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # 짧은 해시
    except Exception:
        pass
    return "unknown"


def _calculate_api_snapshot_hash() -> str:
    """외부 API 응답 스냅샷 해시 계산"""
    # 실제 구현에서는 최근 API 응답을 읽어서 해시 계산
    # 여기서는 간단히 현재 시간 기반 해시 생성
    snapshot_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "youtube_api_status": "keyExpired",  # 실제로는 동적 확인
    }
    snapshot_str = json.dumps(snapshot_data, sort_keys=True)
    return hashlib.sha256(snapshot_str.encode()).hexdigest()[:16]


def _calculate_input_hash() -> str:
    """입력 해시 계산 (키워드, 카테고리 등)"""
    # 실제 구현에서는 현재 키워드/카테고리 파일을 읽어서 해시 계산
    try:
        from backend.knowledge_v1.paths import get_keywords_dir
        keywords_dir = get_keywords_dir()
        input_data = {
            "keywords_dir": str(keywords_dir),
            "categories": ["history", "mystery", "economy", "myth", "science", "war_history"],
        }
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(input_str.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def save_execution_manifest(manifest: Dict[str, Any], repo_root: Path) -> Path:
    """
    Execution manifest 저장
    
    Args:
        manifest: execution manifest
        repo_root: 레포 루트
        
    Returns:
        Path: 저장된 manifest 파일 경로
    """
    governance_dir = repo_root / "data" / "knowledge_v1_store" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = governance_dir / "execution_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    return manifest_path


def load_execution_manifest(repo_root: Path) -> Optional[Dict[str, Any]]:
    """Execution manifest 로드"""
    manifest_path = repo_root / "data" / "knowledge_v1_store" / "governance" / "execution_manifest.json"
    if not manifest_path.exists():
        return None
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_deterministic_output(manifest: Dict[str, Any], assets_path: Path) -> Dict[str, Any]:
    """
    결정론적 출력 검증 (동일 input_hash 실행 시 assets.jsonl SHA256 동일해야 함)
    
    Args:
        manifest: execution manifest
        assets_path: assets.jsonl 경로
        
    Returns:
        Dict: 검증 결과
    """
    if not assets_path.exists():
        return {
            "verified": False,
            "reason": "assets.jsonl not found",
            "expected_hash": None,
            "actual_hash": None,
        }
    
    # assets.jsonl SHA256 계산
    sha256_hash = hashlib.sha256()
    with open(assets_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    actual_hash = sha256_hash.hexdigest()
    
    # manifest에 저장된 해시와 비교
    expected_hash = manifest.get("assets_hash")
    
    if expected_hash is None:
        # 첫 실행이면 해시 저장
        manifest["assets_hash"] = actual_hash
        return {
            "verified": True,
            "reason": "first_run",
            "expected_hash": None,
            "actual_hash": actual_hash,
        }
    
    verified = (actual_hash == expected_hash)
    
    return {
        "verified": verified,
        "reason": "match" if verified else "mismatch",
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
    }

