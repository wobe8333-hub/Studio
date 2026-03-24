"""
Knowledge v1 Paths - 경로 단일화 (재발 방지)

이 모듈은 runtime_paths.py를 기반으로 하며, 레거시 경로에 대한 읽기 폴백을 지원합니다.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union
from backend.knowledge_v1.layers import Layer


Store = Literal["discovery", "approved"]

# 마이그레이션 플래그 (CLI 옵션으로 설정 가능)
_MIGRATE_LEGACY_FLAG = False


def set_migrate_legacy_flag(value: bool) -> None:
    """레거시 마이그레이션 플래그 설정 (CLI 옵션용)"""
    global _MIGRATE_LEGACY_FLAG
    _MIGRATE_LEGACY_FLAG = value


def get_root() -> Path:
    """
    Knowledge v1 Store 루트 경로 반환 (쓰기 전용)
    
    쓰기는 항상 새 runtime store만 사용합니다.
    
    Returns:
        Path: <repo_root>/data/knowledge_v1_store 또는 KNOWLEDGE_STORE_ROOT/knowledge_v1_store
    """
    from backend.config.runtime_paths import (
        get_knowledge_v1_store_root,
        should_migrate_from_legacy
    )
    
    # 쓰기는 항상 새 경로만 사용
    new_root = get_knowledge_v1_store_root()
    
    # 마이그레이션 플래그가 설정되어 있고, 마이그레이션이 필요하면 레거시에서 복사
    if _MIGRATE_LEGACY_FLAG and should_migrate_from_legacy():
        from backend.config.runtime_paths import get_legacy_knowledge_v1_path
        import shutil
        
        legacy_root = get_legacy_knowledge_v1_path()
        if legacy_root.exists() and legacy_root.is_dir():
            try:
                # 레거시에서 새 경로로 마이그레이션 (디렉토리 구조 복사)
                for store_name in ["discovery", "approved"]:
                    legacy_store = legacy_root / store_name
                    new_store = new_root / store_name
                    
                    if legacy_store.exists() and legacy_store.is_dir():
                        if new_store.exists():
                            # 이미 존재하면 파일별로 병합 (덮어쓰지 않음)
                            for legacy_file in legacy_store.rglob("*"):
                                if legacy_file.is_file():
                                    rel_path = legacy_file.relative_to(legacy_store)
                                    new_file = new_store / rel_path
                                    if not new_file.exists():
                                        new_file.parent.mkdir(parents=True, exist_ok=True)
                                        shutil.copy2(legacy_file, new_file)
                        else:
                            # 새로 복사
                            shutil.copytree(legacy_store, new_store, dirs_exist_ok=True)
                
                # keyword_discovery, keyword_approval 등도 마이그레이션
                for subdir in ["keyword_discovery", "keyword_approval", "inputs", "reports", "audit", "used", "blocked", "index"]:
                    legacy_subdir = legacy_root / subdir
                    new_subdir = new_root / subdir
                    
                    if legacy_subdir.exists() and legacy_subdir.is_dir():
                        if not new_subdir.exists():
                            shutil.copytree(legacy_subdir, new_subdir, dirs_exist_ok=True)
                        else:
                            # 파일별로 병합
                            for legacy_file in legacy_subdir.rglob("*"):
                                if legacy_file.is_file():
                                    rel_path = legacy_file.relative_to(legacy_subdir)
                                    new_file = new_subdir / rel_path
                                    if not new_file.exists():
                                        new_file.parent.mkdir(parents=True, exist_ok=True)
                                        shutil.copy2(legacy_file, new_file)
            except Exception as e:
                # 마이그레이션 실패해도 계속 진행 (로그만 출력하지 않음)
                pass
    
    return new_root


def get_read_root() -> Path:
    """
    Knowledge v1 Store 루트 경로 반환 (읽기 전용, 레거시 폴백 허용)
    
    읽기는 새 경로를 우선하고, 없으면 레거시 경로를 사용합니다.
    
    Returns:
        Path: 읽기에 사용할 루트 경로
    """
    from backend.config.runtime_paths import (
        get_knowledge_v1_store_root,
        get_legacy_knowledge_v1_path
    )
    
    # 새 경로 우선
    new_root = get_knowledge_v1_store_root()
    
    # 새 경로에 데이터가 없고 레거시에 있으면, 레거시를 반환 (읽기 폴백)
    legacy_root = get_legacy_knowledge_v1_path()
    if not _has_data_in_path(new_root) and _has_data_in_path(legacy_root):
        return legacy_root
    
    return new_root


def _has_data_in_path(root: Path) -> bool:
    """경로에 실제 데이터가 있는지 확인"""
    if not root.exists():
        return False
    
    # discovery 또는 approved store에 assets.jsonl이 있으면 데이터가 있다고 판단
    discovery_assets = root / "discovery" / "raw" / "assets.jsonl"
    approved_assets = root / "approved" / "raw" / "assets.jsonl"
    
    return discovery_assets.exists() or approved_assets.exists()


def get_store_root(store: Store) -> Path:
    """
    Store별 루트 경로 반환
    
    Args:
        store: "discovery" | "approved"
    
    Returns:
        Path: Store 루트 경로
    """
    root = get_root()
    if store == "discovery":
        return root / "discovery"
    elif store == "approved":
        return root / "approved"
    else:
        raise ValueError(f"Unknown store: {store}")


def get_assets_path(store: Store) -> Path:
    """Assets JSONL 경로"""
    return get_store_root(store) / "raw" / "assets.jsonl"


def get_chunks_path(store: Store) -> Path:
    """Chunks JSONL 경로"""
    return get_store_root(store) / "derived" / "chunks.jsonl"


def get_audit_path(store: Store) -> Path:
    """Audit JSONL 경로"""
    return get_store_root(store) / "audit" / "audit.jsonl"


def get_reports_dir() -> Path:
    """
    Reports 디렉토리 경로 (쓰기 전용)
    
    리포트는 항상 새 runtime store에 저장됩니다.
    """
    return get_root() / "reports"


def get_inputs_dir() -> Path:
    """Inputs 디렉토리 경로"""
    return get_root() / "inputs"


def get_keywords_dir() -> Path:
    """Keywords 디렉토리 경로"""
    return get_inputs_dir() / "keywords"


def ensure_dirs(store: Store) -> None:
    """Store별 필수 디렉토리 생성 (Path API 사용)"""
    store_root = get_store_root(store)  # 이미 Path 반환
    (store_root / "raw").mkdir(parents=True, exist_ok=True)
    (store_root / "derived").mkdir(parents=True, exist_ok=True)
    (store_root / "audit").mkdir(parents=True, exist_ok=True)
    (store_root / "indexes").mkdir(parents=True, exist_ok=True)


def ensure_reports_dir() -> None:
    """Reports 디렉토리 생성 (Path API 사용)"""
    d = get_reports_dir()  # 이미 Path 반환
    d.mkdir(parents=True, exist_ok=True)


def ensure_keywords_dir() -> None:
    """Keywords 디렉토리 생성 (Path API 사용)"""
    d = get_keywords_dir()  # 이미 Path 반환
    d.mkdir(parents=True, exist_ok=True)


def ensure_keywords_files(categories: list[str]) -> None:
    """
    카테고리별 키워드 파일 생성 (없으면 기본 키워드로 생성)
    
    Args:
        categories: 카테고리 리스트
    """
    ensure_keywords_dir()
    keywords_dir = get_keywords_dir()  # 이미 Path 반환
    
    # 카테고리별 기본 seed 키워드 (최소 1건 보장용)
    default_keywords = {
        "science": ["gravity"],
        "economy": ["inflation"],
        "geography": ["latitude"],
        "history": ["cold war"],
        "common_sense": ["electricity"],
        "papers": ["transformer attention"]
    }
    
    for category in categories:
        keywords_file = keywords_dir / f"{category}.txt"
        if not keywords_file.exists():
            # 기본 키워드로 파일 생성 (최소 1개)
            keywords = default_keywords.get(category, [f"{category}_seed"])
            keywords_dir.mkdir(parents=True, exist_ok=True)
            with open(keywords_file, "w", encoding="utf-8") as f:
                for keyword in keywords:
                    f.write(f"{keyword}\n")


# === Repo-root 기반 SSOT 경로 (reports/gate_stats/diagnostics 등) ===


def get_repo_root() -> Path:
    """
    레포 루트 경로 (SSOT). 반환 타입 Path 하드락.
    """
    this_file = Path(__file__).resolve()
    # backend/knowledge_v1/paths.py → parents[0]=knowledge_v1, [1]=backend, [2]=repo_root
    return this_file.parents[2]


def as_path(p: Union[Path, str]) -> Path:
    """str/Path 혼용 방지: 항상 Path 반환."""
    return p if isinstance(p, Path) else Path(str(p)).resolve()


@dataclass(frozen=True)
class ReportPaths:
    """리포트/진단 경로 SSOT (경로 변수 단일화, 하드락)."""
    gate_stats: Path
    governance_dir: Path


def get_report_paths(repo_root: Path) -> ReportPaths:
    """
    repo_root 기반 리포트 경로 단일 객체 반환 (SSOT).
    모든 파일 경로는 paths.py에서만 생성·관리.
    """
    base = repo_root / "data" / "knowledge_v1_store"
    reports = base / "reports"
    governance = base / "governance"
    reports.mkdir(parents=True, exist_ok=True)
    governance.mkdir(parents=True, exist_ok=True)
    return ReportPaths(
        gate_stats=reports / "gate_stats.json",
        governance_dir=governance,
    )


def get_reports_dir_from_repo_root(repo_root: Path) -> Path:
    """repo_root 기반 reports 디렉터리 경로."""
    return repo_root / "data" / "knowledge_v1_store" / "reports"


def get_gate_stats_path_from_repo_root(repo_root: Path) -> Path:
    """repo_root 기반 gate_stats.json 경로 (SSOT)."""
    return get_reports_dir_from_repo_root(repo_root) / "gate_stats.json"


def get_cycle_report_path_from_repo_root(repo_root: Path, cycle_id: str) -> Path:
    """repo_root 기반 discovery cycle report 경로 (SSOT)."""
    return get_reports_dir_from_repo_root(repo_root) / f"discovery_cycle_{cycle_id}.json"


def get_derive_zero_report_path_from_repo_root(repo_root: Path, category: str, cycle_id: str) -> Path:
    """repo_root 기반 derive_zero 리포트 경로 (SSOT)."""
    return get_reports_dir_from_repo_root(repo_root) / f"derive_zero_{category}_{cycle_id}.json"


def get_empty_drop_report_path_from_repo_root(repo_root: Path, cycle_id: str) -> Path:
    """repo_root 기반 empty_drop 리포트 경로 (SSOT)."""
    return get_reports_dir_from_repo_root(repo_root) / f"empty_drop_{cycle_id}.json"


def get_governance_dir(repo_root: Path) -> Path:
    """repo_root 기반 governance 디렉터리 경로 (SSOT)."""
    return repo_root / "data" / "knowledge_v1_store" / "governance"


def ensure_governance_dir(repo_root: Path) -> Path:
    """governance 디렉터리 생성 및 반환 (SSOT)."""
    governance_dir = get_governance_dir(repo_root)
    governance_dir.mkdir(parents=True, exist_ok=True)
    return governance_dir


def get_source_probabilities_path(repo_root: Path) -> Path:
    """repo_root 기반 source_probabilities.json 경로 (SSOT)."""
    return get_governance_dir(repo_root) / "source_probabilities.json"


def get_evolution_history_path(repo_root: Path) -> Path:
    """repo_root 기반 evolution_history.json 경로 (SSOT)."""
    return get_governance_dir(repo_root) / "evolution_history.json"


def get_keyword_discovery_snapshots_dir(repo_root: str) -> str:
    """
    keyword_discovery snapshots 루트 경로 (SSOT).

    Args:
        repo_root: 레포 루트 절대경로 (예: C:\\Users\\...\\AI_Animation_Stuidio)

    Returns:
        snapshots 루트 경로 (str)
    """
    path = os.path.join(
        repo_root,
        "backend",
        "output",
        "knowledge_v1",
        "keyword_discovery",
        "snapshots",
    )
    os.makedirs(path, exist_ok=True)
    return path


def get_cycle_snapshot_dir(repo_root: str, cycle_id: str) -> str:
    """
    특정 cycle_id의 snapshot 디렉토리 경로 (SSOT).

    Args:
        repo_root: 레포 루트 절대경로
        cycle_id: cycle ID (예: "20260203_141300")

    Returns:
        cycle snapshot 디렉토리 경로 (str)
    """
    snapshots_root = get_keyword_discovery_snapshots_dir(repo_root)
    cycle_dir = os.path.join(snapshots_root, cycle_id)
    os.makedirs(cycle_dir, exist_ok=True)
    return cycle_dir


def get_discovery_raw_assets_path() -> Path:
    """discovery raw assets JSONL 경로 (SSOT)."""
    return get_store_root("discovery") / "raw" / "assets.jsonl"


def get_discovery_derived_chunks_path() -> Path:
    """discovery derived chunks JSONL 경로 (SSOT)."""
    return get_store_root("discovery") / "derived" / "chunks.jsonl"


def get_gate_stats_path() -> Path:
    """gate_stats.json 경로 (SSOT: ReportPaths 위임, 중복 제거)."""
    return get_report_paths(get_repo_root()).gate_stats


def get_cycle_report_path(cycle_id: str) -> Path:
    """discovery cycle report 경로 (runtime store 기반 SSOT)."""
    return get_reports_dir() / f"discovery_cycle_{cycle_id}.json"


def get_derive_zero_report_path(category: str, cycle_id: str) -> Path:
    """derive_zero 리포트 경로 (runtime store 기반 SSOT)."""
    return get_reports_dir() / f"derive_zero_{category}_{cycle_id}.json"


def get_empty_drop_report_path(cycle_id: str) -> Path:
    """empty_drop 리포트 경로 (runtime store 기반 SSOT)."""
    return get_reports_dir() / f"empty_drop_{cycle_id}.json"


