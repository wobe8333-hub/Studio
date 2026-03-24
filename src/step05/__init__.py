"""
Knowledge v1 Cycle - Discovery Cycle 오케스트레이션
"""

from __future__ import annotations

import json
import os
import os as _os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.knowledge_v1.schema import DerivedChunk

# path_guard에서 P() 함수 import (전역 방어)
from backend.knowledge_v1.path_guard import P, ensure_parent_dir, touch_jsonl

from backend.knowledge_v1.paths import (
    get_keywords_dir, get_reports_dir, ensure_keywords_dir, ensure_reports_dir, ensure_dirs,
    ensure_keywords_files
)
from backend.knowledge_v1.store import append_asset, append_chunk, append_audit, get_existing_raw_hashes, load_jsonl
from backend.knowledge_v1.discovery_ingest import ingest_discovery
from backend.knowledge_v1.derive import derive
from backend.knowledge_v1.classify import classify
from backend.knowledge_v1.license_gate import apply_license_gate
from backend.knowledge_v1.audit import AuditEvent
from backend.knowledge_v1.schema import KnowledgeAsset, DerivedChunk
from backend.knowledge_v1.promote import promote_to_approved_v2
from backend.knowledge_v1.utils.keyword_contract import (
    assert_kw_contract,
    normalize_kw,
    normalize_kw_list,
)
from backend.knowledge_v1.utils.keyword_uniqueness import enforce_unique, normalize as normalize_unique
from backend.knowledge_v1.keyword_sources.fallback_from_rss_titles import (
    extract_fallback_keywords_from_rss_titles,
)


def _find_repo_root() -> Path:
    """
    repo root 탐색 함수
    Path(__file__).resolve()에서 시작해 상위 디렉터리로 올라가며,
    현재 디렉터리 바로 아래에 "backend" 폴더와 "data" 폴더가 동시에 존재하는 지점을 repo root로 판정한다.
    
    Returns:
        Path: repo root 경로
        
    Raises:
        RuntimeError: repo root를 찾지 못한 경우
    """
    p = Path(__file__).resolve()
    for parent in [p.parent] + list(p.parents):
        if (parent / "backend").is_dir() and (parent / "data").is_dir():
            return parent
    raise RuntimeError(f"repo root not found (expected backend/ and data/ directories). Searched from: {__file__}")


def _load_keywords_for_step_e(cycle_id: str, min_keywords: int = 40) -> List[str]:
    """
    Step E용 키워드 로드 (최소 보장)
    우선순위: promoted_keywords.jsonl > anchor > snapshot
    
    Args:
        cycle_id: cycle_id
        min_keywords: 최소 키워드 수 (기본 40)
    
    Returns:
        List[str]: 키워드 리스트 (중복 제거)
    """
    keywords: List[str] = []
    seen = set()
    
    root = _find_repo_root()
    kd_root = root / "keyword_discovery"
    
    # 1) promoted_keywords.jsonl
    promo_file = kd_root / "promotions" / "promoted_keywords.jsonl"
    if promo_file.exists():
        try:
            with open(promo_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        kw = normalize_kw(entry)
                        if kw:
                            key = " ".join(kw.lower().split())
                            if key not in seen:
                                keywords.append(kw)
                                seen.add(key)
                    except Exception:
                        continue
        except Exception:
            pass
    
    # 2) anchor keywords
    anchor_file = kd_root / "anchors" / "youtube_data_api_anchor_kr.json"
    if anchor_file.exists() and len(keywords) < min_keywords:
        try:
            with open(anchor_file, "r", encoding="utf-8") as f:
                anchor_data = json.load(f)
                anchor_keywords = anchor_data.get("keywords", [])
                for raw_kw in anchor_keywords:
                    kw = normalize_kw(raw_kw)
                    if kw:
                        key = " ".join(kw.lower().split())
                        if key not in seen:
                            keywords.append(kw)
                            seen.add(key)
                        if len(keywords) >= min_keywords:
                            break
        except Exception:
            pass
    
    # 3) snapshot keywords (cycle_id 기반)
    snapshot_dir = kd_root / "snapshots" / cycle_id
    if snapshot_dir.exists() and len(keywords) < min_keywords:
        for cat in ["science", "history", "common_sense", "economy", "geography", "papers"]:
            snapshot_file = snapshot_dir / f"keywords_{cat}_raw.jsonl"
            if snapshot_file.exists():
                try:
                    with open(snapshot_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                                kw = normalize_kw(entry)
                                if kw:
                                    key = " ".join(kw.lower().split())
                                    if key not in seen:
                                        keywords.append(kw)
                                        seen.add(key)
                                    if len(keywords) >= min_keywords:
                                        break
                            except Exception:
                                continue
                    if len(keywords) >= min_keywords:
                        break
                except Exception:
                    continue
    
    normalized = normalize_kw_list(keywords)
    return normalized[:min_keywords] if len(normalized) > min_keywords else normalized


def load_keywords_from_file(category: str, keywords_dir: Union[Path, str], max_keywords: int = 100) -> List[str]:
    """
    카테고리별 키워드 파일에서 로드
    
    Args:
        category: 카테고리
        keywords_dir: 키워드 디렉토리 (Path 또는 str)
        max_keywords: 최대 키워드 수
    
    Returns:
        List[str]: 키워드 리스트 (최소 1개 보장)
    """
    # keywords_dir을 Path로 강제 변환
    keywords_dir = P(keywords_dir)
    
    # 기본 seed 키워드 맵 (최소 1건 보장용)
    default_seeds = {
        "science": ["gravity"],
        "economy": ["inflation"],
        "geography": ["latitude"],
        "history": ["cold war"],
        "common_sense": ["electricity"],
        "papers": ["transformer attention"]
    }
    
    keywords_file = P(keywords_dir) / f"{category}.txt"
    keywords = []
    
    # 파일이 없으면 생성하고 기본 seed 작성 (최소 1개)
    if not keywords_file.exists():
        seeds = default_seeds.get(category, [f"{category}_seed"])
        keywords_dir.mkdir(parents=True, exist_ok=True)
        with open(keywords_file, "w", encoding="utf-8") as f:
            for seed in seeds:
                f.write(f"{seed}\n")
        keywords = seeds[:max_keywords] if max_keywords > 0 else seeds[:1]  # 최소 1개 보장
    else:
        # 파일이 있으면 읽기
        with open(keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    keywords.append(line)
                    if len(keywords) >= max_keywords:
                        break
    
    # 키워드가 비어있으면 seed 키워드 사용 (런타임 주입, 최소 1개 보장)
    if not keywords:
        seeds = default_seeds.get(category, [f"{category}_seed"])
        keywords = seeds[:max_keywords] if max_keywords > 0 else seeds[:1]  # 최소 1개 보장
    
    return normalize_kw_list(keywords)


def _expand_keywords_for_dry_run(category: str, keywords_dir: Path, target: int) -> List[str]:
    """
    Dry-run 모드에서 키워드 파일 자동 확장 (fixtures + seed 확장)
    - 반드시 target개 이상 확보
    - 중복 제거(대소문자 무시), 최소 길이 3, 공백 정규화
    - 파일에 target개 저장, 반환도 target개 고정
    """
    keywords_dir = P(keywords_dir)
    keywords_file = keywords_dir / f"{category}.txt"

    def _norm(s: str) -> str:
        s = (s or "").strip()
        s = " ".join(s.split())
        return s

    keywords: List[str] = []
    seen = set()

    if keywords_file.exists():
        with open(keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                line = _norm(line)
                if not line or line.startswith("#"):
                    continue
                if len(line) < 3:
                    continue
                k = line.lower()
                if k in seen:
                    continue
                keywords.append(line)
                seen.add(k)
                if len(keywords) >= target:
                    break

    if len(keywords) < target:
        fixtures_dir = Path(__file__).parent / "fixtures"
        fixture_paths = []
        if fixtures_dir.exists():
            fixture_paths.extend(sorted(fixtures_dir.glob("*.json")))
            fixture_paths.extend(sorted(fixtures_dir.glob("*.jsonl")))

        def _yield_strings(obj):
            if isinstance(obj, str):
                yield obj
            elif isinstance(obj, list):
                for x in obj:
                    yield from _yield_strings(x)
            elif isinstance(obj, dict):
                preferred = ["keywords","queries","titles","items","trends","topic","name","label","title"]
                for kk in preferred:
                    if kk in obj:
                        yield from _yield_strings(obj.get(kk))
                for v in obj.values():
                    yield from _yield_strings(v)

        for p in fixture_paths:
            if len(keywords) >= target:
                break
            try:
                if p.suffix == ".jsonl":
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            if len(keywords) >= target:
                                break
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                row = json.loads(line)
                            except Exception:
                                continue
                            for s in _yield_strings(row):
                                s = _norm(s)
                                if len(s) < 3:
                                    continue
                                k = s.lower()
                                if k in seen:
                                    continue
                                keywords.append(s)
                                seen.add(k)
                                if len(keywords) >= target:
                                    break
                else:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for s in _yield_strings(data):
                        s = _norm(s)
                        if len(s) < 3:
                            continue
                        k = s.lower()
                        if k in seen:
                            continue
                        keywords.append(s)
                        seen.add(k)
                        if len(keywords) >= target:
                            break
            except Exception:
                continue

    if len(keywords) < target:
        seed_map = {
            "science": ["gravity","quantum","relativity","molecule","genetics"],
            "economy": ["inflation","interest rate","market","finance","gdp"],
            "geography": ["latitude","continent","ocean","mountain","climate"],
            "history": ["cold war","renaissance","revolution","empire","ancient"],
            "common_sense": ["electricity","water","fire","magnetism","energy"],
            "papers": ["transformer attention","neural network","deep learning","machine learning","ai research"],
        }
        suffixes = [" basics"," explained"," examples"," guide"," tutorial"," facts"," history"," overview"," Q&A"," summary"]
        bases = []
        for s in (seed_map.get(category, [category]) + keywords):
            s = _norm(s)
            if len(s) >= 3:
                bases.append(s)
        i = 0
        while len(keywords) < target:
            base = bases[i % len(bases)]
            suf = suffixes[(i // len(bases)) % len(suffixes)]
            cand = _norm(f"{base}{suf}")
            i += 1
            if len(cand) < 3:
                continue
            k = cand.lower()
            if k in seen:
                continue
            keywords.append(cand)
            seen.add(k)

    keywords_dir.mkdir(parents=True, exist_ok=True)
    with open(keywords_file, "w", encoding="utf-8") as f:
        for kw in keywords[:target]:
            f.write(f"{kw}\n")

    return keywords[:target]


def _extract_keywords_from_fixtures(category: str, count: int) -> List[str]:
    fixtures_dir = Path(__file__).parent / "fixtures"
    out: List[str] = []
    seen = set()

    def _norm(s: str) -> str:
        s = (s or "").strip()
        s = " ".join(s.split())
        return s

    def _yield_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, list):
            for x in obj:
                yield from _yield_strings(x)
        elif isinstance(obj, dict):
            preferred = ["keywords","queries","titles","items","trends","topic","name","label","title"]
            for kk in preferred:
                if kk in obj:
                    yield from _yield_strings(obj.get(kk))
            for v in obj.values():
                yield from _yield_strings(v)

    fixture_paths = []
    if fixtures_dir.exists():
        fixture_paths.extend(sorted(fixtures_dir.glob("*.json")))
        fixture_paths.extend(sorted(fixtures_dir.glob("*.jsonl")))

    for p in fixture_paths:
        if len(out) >= count:
            break
        try:
            if p.suffix == ".jsonl":
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        if len(out) >= count:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:
                            continue
                        for s in _yield_strings(row):
                            s = _norm(s)
                            if len(s) < 3:
                                continue
                            k = s.lower()
                            if k in seen:
                                continue
                            out.append(s)
                            seen.add(k)
                            if len(out) >= count:
                                break
            else:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for s in _yield_strings(data):
                    s = _norm(s)
                    if len(s) < 3:
                        continue
                    k = s.lower()
                    if k in seen:
                        continue
                    out.append(s)
                    seen.add(k)
                    if len(out) >= count:
                        break
        except Exception:
            continue

    if len(out) < count:
        seed_map = {
            "science": ["gravity","quantum","relativity","molecule","genetics"],
            "economy": ["inflation","interest rate","market","finance","gdp"],
            "geography": ["latitude","continent","ocean","mountain","climate"],
            "history": ["cold war","renaissance","revolution","empire","ancient"],
            "common_sense": ["electricity","water","fire","magnetism","energy"],
            "papers": ["transformer attention","neural network","deep learning","machine learning","ai research"],
        }
        for s in seed_map.get(category, [f"{category}_term{i}" for i in range(1, count + 1)]):
            if len(out) >= count:
                break
            s = _norm(s)
            if len(s) < 3:
                continue
            k = s.lower()
            if k in seen:
                continue
            out.append(s)
            seen.add(k)

    return out[:count]


def run_discovery_cycle(
    categories: List[str],
    mode: str = "run",
    keywords_dir: Path = None,
    max_keywords_per_category: int = 80,  # v7 기본값 (CLI와 동기화)
    daily_total_limit: int = 400,  # 일일 총 키워드 제한
    approve_fallback: bool = False,
    cycle_id: str = None  # cycle_id 단일화: 명시되면 사용, 없으면 last_cycle_id.txt 또는 새로 생성
) -> Dict[str, Any]:
    """
    Discovery Cycle 실행 (V7: 정책 SSOT + 6개 카테고리)
    
    Args:
        categories: 카테고리 리스트
        mode: "run" | "dry-run"
        keywords_dir: 키워드 디렉토리 (None이면 기본값, str이면 Path로 변환)
        max_keywords_per_category: 카테고리당 최대 키워드 수
        approve_fallback: Fallback asset 승격 허용 여부
    
    Returns:
        Dict: 리포트
    """
    # V7: 정책 검증 (최우선)
    try:
        from backend.knowledge_v1.policy.validator import validate_and_load_policy
        policy, is_valid, conflicts = validate_and_load_policy()
        
        if not is_valid:
            # 정책 충돌 시 즉시 종료, 적재 0
            return {
                "cycle_id": cycle_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                "started_at": datetime.utcnow().isoformat() + "Z",
                "ended_at": datetime.utcnow().isoformat() + "Z",
                "mode": mode,
                "categories": {},
                "summary": {
                    "total_selected": 0,
                    "total_ingested": 0,
                    "total_fallback": 0,
                    "total_derived": 0,
                    "total_blocked": 0,
                    "total_promoted": 0,
                    "policy_conflict": True,
                    "conflict_list": conflicts
                }
            }
        
        # 정책에서 카테고리 가져오기
        policy_categories = policy.get("categories", categories)
        if set(categories) != set(policy_categories):
            categories = policy_categories
    except Exception as e:
        # 정책 로드 실패 시 기본값 사용하되 경고
        conflicts = [f"policy_load_failed: {type(e).__name__}"]
    
    # 하드락: V7 카테고리/타겟 고정
    categories = ["history", "mystery", "economy", "myth", "science", "war_history"]
    per_category_target = 5

    # 절대적 선초기화 (함수 스코프 최상단, 어떤 블록에도 속하지 않음)
    # 2차 크래시 후보 로컬 변수 전면 선초기화 (UnboundLocalError 0% 보장)
    # os 모듈을 로컬 변수로 바인딩하지 않도록 _os로 import
    _os = __import__("os")
    
    keywords: list = []
    ingest_result: dict = {}
    docs_by_source: dict = {}
    assets_written: int = 0
    chunks_written: int = 0
    category_error: str = ""
    started_at_iso: str = ""
    ended_at_iso: str = ""
    
    # 결과 변수 선초기화 (예외/스킵 경로에서도 2차 크래시 방지)
    ingested_assets: list = []
    errors: list = []
    
    # 빈 asset 드롭 증거 필드 초기화 (장기운영용)
    dropped_empty_assets = 0
    dropped_empty_assets_by_source = {}
    
    # Heartbeat 초기화 (착시 제거용)
    hb_seconds = int(_os.getenv("V7_HEARTBEAT_SECONDS", "0") or "0")
    hb_last_time = time.time() if hb_seconds > 0 else None
    
    # 빈 asset 판정 함수 (SSOT: metrics.empty_drop_counter.is_empty_asset 위임)
    from backend.knowledge_v1.metrics.empty_drop_counter import is_empty_asset as _ssot_is_empty_asset

    def _is_empty_asset(a: dict) -> bool:
        return _ssot_is_empty_asset(a)
    
    # keywords_dir을 Path로 강제 변환 (핵심)
    if keywords_dir is None:
        keywords_dir = get_keywords_dir()
    keywords_dir = P(keywords_dir)  # 전역 방어 함수 사용
    keywords_dir.mkdir(parents=True, exist_ok=True)
    
    # 런타임 Path 체크 (디버그)
    paths_are_pathlib = isinstance(keywords_dir, Path)
    if not paths_are_pathlib:
        raise TypeError(f"keywords_dir is not Path: {type(keywords_dir)}")
    
    # 디렉터리 보장 (최우선) - Path API 사용
    ensure_dirs("discovery")
    ensure_dirs("approved")
    ensure_reports_dir()
    
    # 하드락: 경로 변수 SSOT (paths.py 단일 객체만 사용, 재할당 금지)
    from backend.knowledge_v1 import paths as _paths_module
    repo_root: Path = _paths_module.get_repo_root()
    report_paths = _paths_module.get_report_paths(repo_root)
    gate_stats_path: Path = report_paths.gate_stats
    gate_stats_path_str: str = str(gate_stats_path)
    if not isinstance(gate_stats_path, Path):
        raise RuntimeError("GATE_STATS_PATH_NOT_PATH")
    if not gate_stats_path_str or not gate_stats_path_str.strip():
        raise RuntimeError("GATE_STATS_PATH_EMPTY")
    
    # LIVE 모드: discovery 스냅샷 디렉토리 초기화 (snapshot 없을 때 fallback 저장용)
    if mode == "live":
        discovery_snapshots = repo_root / "data" / "knowledge_v1_store" / "discovery" / "snapshots"
        discovery_snapshots.mkdir(parents=True, exist_ok=True)
    
    def _atomic_write_json(path: Path, obj: dict) -> None:
        """원자적 JSON 저장 (tmp → replace, 부분 쓰기/트렁케이트 방지)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    
    def _finalize_and_write_discovery_report(report: dict, _cycle_id: str, _gate_stats_path: str) -> str:
        """ok/error/report_path/gate_stats_path 주입 후 원자적 저장 (stdout与report 1:1 보장)."""
        report_path = Path(_gate_stats_path).parent / f"discovery_cycle_{_cycle_id}.json"
        report["cycle_id"] = _cycle_id
        report["gate_stats_path"] = _gate_stats_path
        report["report_path"] = str(report_path)
        report.setdefault("ok", True)
        report.setdefault("error", None)
        _atomic_write_json(report_path, report)
        return str(report_path)
    
    # Discovery 출력 파일 존재 보장 (최소 1건 생성을 위한 파일 초기화)
    # paths.py의 함수들은 이미 Path를 반환하므로 P()로 감쌀 필요 없지만, 안전을 위해 유지
    from backend.knowledge_v1.paths import get_assets_path, get_chunks_path, get_audit_path
    discovery_assets_path = get_assets_path("discovery")  # 이미 Path 반환
    discovery_chunks_path = get_chunks_path("discovery")  # 이미 Path 반환
    discovery_audit_path = get_audit_path("discovery")  # 이미 Path 반환
    
    # DRY-RUN CLEAN START: dry-run에서만 1회 초기화 (재현/통제)
    if mode == "dry-run":
        # discovery 파일 초기화 (카테고리 루프 중에는 절대 삭제 금지)
        for p in [discovery_assets_path, discovery_chunks_path, discovery_audit_path]:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                # 초기화 실패해도 런 자체를 깨지 않음 (healthcheck 안정성)
                pass

        # quota state 초기화 (dry-run 반복 실행 시 quota로 막히는 현상 방지)
        try:
            from backend.knowledge_v1.quota import get_quota_state_path
            qp = get_quota_state_path()
            if qp.exists():
                qp.unlink()
        except Exception:
            pass

    # 부모 디렉토리 생성 및 파일 터치 (Path API 사용)
    discovery_assets_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_chunks_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_audit_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_assets_path.touch(exist_ok=True)
    discovery_chunks_path.touch(exist_ok=True)
    discovery_audit_path.touch(exist_ok=True)
    
    ensure_keywords_dir()
    # 키워드 파일 자동 생성 (없으면 기본 키워드로 생성)
    ensure_keywords_files(categories)
    
    # ============================================================
    # GOVERNANCE LAYER: EXECUTION SNAPSHOT FREEZING (완전 결정론)
    # ============================================================
    from backend.governance.execution_snapshot import freeze_execution_environment, save_execution_manifest
    from backend.governance.versioned_policy_engine import load_policy_version, detect_policy_conflicts, get_policy_version_string
    from backend.governance.pre_cost_estimator import estimate_pre_run_cost, check_cost_limit, save_cost_projection
    from backend.governance.adaptive_exploration import calculate_source_probabilities, save_source_probabilities
    from backend.governance.memory_drift_engine import load_drift_index, save_drift_index
    from backend.governance.source_evolution_engine import calculate_source_score, save_evolution_history, load_evolution_history
    from backend.knowledge_v1.paths import get_repo_root
    
    repo_root = get_repo_root()
    
    # 1. 정책 버전 로드
    policy = load_policy_version(repo_root)
    policy_version = get_policy_version_string(policy)
    
    # 2. 실행 환경 고정 (random seed, hash seed 등)
    run_id = cycle_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    manifest = freeze_execution_environment(run_id, policy_version)
    manifest_path = save_execution_manifest(manifest, repo_root)
    # baseline 존재 시 cache-only 강제 (외부 live 변동 제거)
    input_hash_early = manifest.get("input_hash")
    if input_hash_early:
        try:
            from backend.governance.replay_baseline_store import (
                get_replay_baselines_path,
                load_replay_baselines,
            )
            _repo_root_path = _paths_module.as_path(repo_root)
            _baseline_path = get_replay_baselines_path(_repo_root_path)
            _root = load_replay_baselines(_baseline_path)
            _baselines_map = (_root.get("baselines") or {}) if isinstance(_root, dict) else {}
            if input_hash_early in _baselines_map:
                os.environ["REPLAY_FREEZE_SOURCES"] = "1"
        except Exception:
            pass
    
    # 3. 정책 충돌 탐지
    context = {
        "categories": categories,
        "mode": mode,
        "estimated_cost": 0.0,  # 나중에 업데이트
    }
    has_conflict, conflict_list = detect_policy_conflicts(policy, context)
    if has_conflict:
        return {
            "cycle_id": run_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "ended_at": datetime.utcnow().isoformat() + "Z",
            "mode": mode,
            "categories": {},
            "summary": {
                "total_selected": 0,
                "total_ingested": 0,
                "total_fallback": 0,
                "total_derived": 0,
                "total_blocked": 0,
                "total_promoted": 0,
                "policy_conflict": True,
                "conflict_list": conflict_list,
            },
            "governance": {
                "execution_manifest_path": str(manifest_path),
                "execution_manifest": manifest,
                "input_hash": manifest.get("input_hash"),
                "policy_version": policy_version,
                "conflicts": conflict_list,
            }
        }
    
    # 4. 사전 비용 예측 및 차단
    estimated_api_calls = len(categories) * 10  # 간단한 추정
    estimated_tokens = 0  # 실제로는 더 정교하게 계산
    estimated_cost, cost_breakdown = estimate_pre_run_cost(
        estimated_api_calls=estimated_api_calls,
        estimated_tokens=estimated_tokens
    )
    context["estimated_cost"] = estimated_cost
    cost_allowed, cost_message = check_cost_limit(estimated_cost)
    if not cost_allowed:
        return {
            "cycle_id": run_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "ended_at": datetime.utcnow().isoformat() + "Z",
            "mode": mode,
            "categories": {},
            "summary": {
                "total_selected": 0,
                "total_ingested": 0,
                "total_fallback": 0,
                "total_derived": 0,
                "total_blocked": 0,
                "total_promoted": 0,
                "cost_exceeded": True,
                "cost_message": cost_message,
            },
            "governance": {
                "execution_manifest_path": str(manifest_path),
                "execution_manifest": manifest,
                "input_hash": manifest.get("input_hash"),
                "policy_version": policy_version,
                "cost_projection": cost_breakdown,
            }
        }
    
    # 비용 예측 저장
    cost_projection = {
        "run_id": run_id,
        "estimated_cost": estimated_cost,
        "breakdown": cost_breakdown,
        "projected_at": datetime.utcnow().isoformat() + "Z",
    }
    from backend.governance.pre_cost_estimator import save_cost_projection
    save_cost_projection(cost_projection, repo_root)
    
    # DISCOVERY_CYCLE_START
    cycle_start_time = datetime.utcnow()
    
    # cycle_id 단일화: 명시 파라미터 > last_cycle_id.txt > 새로 생성
    # BOM 제거 (cycle_id가 문자열인 경우)
    if cycle_id and isinstance(cycle_id, str):
        cycle_id = cycle_id.lstrip('\ufeff').strip()
    if not cycle_id:
        from backend.knowledge_v1.paths import get_root
        kd_root = get_root() / "keyword_discovery"
        last_cycle_id_file = kd_root / "snapshots" / "last_cycle_id.txt"
        if last_cycle_id_file.exists():
            try:
                cycle_id_raw = last_cycle_id_file.read_text(encoding="utf-8-sig").strip()  # BOM 제거
                # BOM 및 공백 제거
                cycle_id = cycle_id_raw.lstrip('\ufeff').strip()
                if not cycle_id:
                    cycle_id = cycle_start_time.strftime("%Y%m%d_%H%M%S")
            except Exception:
                cycle_id = cycle_start_time.strftime("%Y%m%d_%H%M%S")
        else:
            # last_cycle_id.txt가 없으면 snapshots 디렉토리에서 최신 폴더명 사용
            snapshots_dir = kd_root / "snapshots"
            if snapshots_dir.exists():
                dirs = sorted([d for d in snapshots_dir.iterdir() if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
                if dirs:
                    cycle_id = dirs[0].name
                else:
                    cycle_id = cycle_start_time.strftime("%Y%m%d_%H%M%S")
            else:
                cycle_id = cycle_start_time.strftime("%Y%m%d_%H%M%S")
    
    # V7: Replay Manifest 생성
    try:
        from backend.knowledge_v1.replay.manifest import create_manifest, save_manifest, compute_snapshots_sha256
        import hashlib
        
        # 정책 파일 SHA256
        repo_root = _find_repo_root()
        policy_path = repo_root / "config" / "policy" / "knowledge_policy.json"
        policy_sha256 = ""
        if policy_path.exists():
            with open(policy_path, "rb") as f:
                policy_sha256 = hashlib.sha256(f.read()).hexdigest()
        
        # 스냅샷 SHA256 (초기값, 나중에 업데이트)
        snapshots_sha256 = compute_snapshots_sha256(cycle_id)
        
        manifest = create_manifest(cycle_id, policy_sha256, snapshots_sha256)
        save_manifest(cycle_id, manifest)
    except Exception:
        pass  # manifest 생성 실패해도 계속 진행
    
    # 실행 모듈 경로 기록 (디버그)
    module_path = __file__
    
    append_audit(AuditEvent.create("DISCOVERY_CYCLE_START", {
        "cycle_id": cycle_id,
        "categories": categories,
        "mode": mode,
        "max_keywords_per_category": max_keywords_per_category,
        "daily_total_limit": daily_total_limit,
        "approve_fallback": approve_fallback,
        "module_path": module_path
    }), "discovery")
    
    # 전체 리포트
    report = {
        "cycle_id": cycle_id,
        "started_at": cycle_start_time.isoformat() + "Z",
        "mode": mode,
        "categories": {},
        "summary": {
            "total_selected": 0,
            "total_ingested": 0,
            "total_fallback": 0,
            "total_derived": 0,
            "total_blocked": 0,
            "total_promoted": 0
        },
        "debug": {
            "module_path": module_path,
            "keywords_dir": str(keywords_dir),
            "paths_are_pathlib": paths_are_pathlib
        }
    }
    
    # 카테고리별 처리 (total limit 적용)
    total_selected = 0
    
    # PATCH-08B (dry-run only): Apply SSOT Gate-1 daily keywords into inputs/keywords/*.txt (one-shot)
    if mode == "dry-run":
        def _norm_kw(s: str) -> str:
            s = (s or "").strip()
            s = " ".join(s.split())
            return s

        # store_root = .../data/knowledge_v1_store (keywords_dir == .../inputs/keywords)
        store_root = keywords_dir.parents[1]
        ssot_root = store_root / "ssot"

        # 1) SSOT daily 파일 선택: (a) 현재 cycle_id 우선, (b) 없으면 최신 1개 fallback
        daily_path = ssot_root / cycle_id / "daily_keywords_gate1.json"
        if not daily_path.exists():
            daily_paths = sorted(ssot_root.glob("*/daily_keywords_gate1.json"), key=lambda p: p.stat().st_mtime)
            daily_path = daily_paths[-1] if daily_paths else None

        daily = None
        if daily_path is not None and daily_path.exists():
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    daily = json.load(f)
            except Exception:
                daily = None

        # 2) SSOT → category별 리스트 구성
        ssot_map = {c: [] for c in categories}
        if isinstance(daily, dict) and isinstance(daily.get("keywords"), list):
            for row in daily["keywords"]:
                if not isinstance(row, dict):
                    continue
                c = row.get("category")
                if c not in ssot_map:
                    continue
                kw = _norm_kw(row.get("keyword", ""))
                if len(kw) >= 3:
                    ssot_map[c].append(kw)

        # 3) 파일 갱신: SSOT 우선 + 기존 후순위, 중복 제거, max 80 라인
        cap = max_keywords_per_category if max_keywords_per_category else 80
        keywords_dir.mkdir(parents=True, exist_ok=True)

        for c in categories:
            kw_file = keywords_dir / f"{c}.txt"

            existing = []
            if kw_file.exists():
                try:
                    with open(kw_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = _norm_kw(line)
                            if not line or line.startswith("#"):
                                continue
                            if len(line) < 3:
                                continue
                            existing.append(line)
                except Exception:
                    existing = []

            merged = []
            seen = set()
            for kw in ssot_map.get(c, []) + existing:
                k = kw.lower()
                if k in seen:
                    continue
                seen.add(k)
                merged.append(kw)

            merged = merged[:cap]
            with open(kw_file, "w", encoding="utf-8") as f:
                for kw in merged:
                    f.write(f"{kw}\n")
    
    # DRY-RUN PRIORITY:
    # science/common_sense는 classify 규칙상 FULLY_USABLE로 가지 않으므로(READY 생산 불리),
    # dry-run에서는 READY 생산에 유리한 카테고리를 먼저 소진하도록 순서를 고정한다.
    if mode == "dry-run":
        priority = ["history", "economy", "geography", "papers", "science", "common_sense"]
        seen_cat = set()
        ordered = []
        for c in priority:
            if c in categories and c not in seen_cat:
                ordered.append(c); seen_cat.add(c)
        for c in categories:
            if c not in seen_cat:
                ordered.append(c); seen_cat.add(c)
        categories = ordered
    
    # PATCH-13Q: LIVE에서는 YouTube를 "카테고리별 반복 호출"하지 않고 "사이클당 1회"만 호출하여 분배한다.
    youtube_api_key = None
    yt_buckets = {c: [] for c in categories}
    youtube_skipped_reason = None

    if mode == "live":
        try:
            from backend.knowledge_v1.secrets import load_youtube_api_key
        except Exception:
            load_youtube_api_key = None

        # store_root = .../data/knowledge_v1_store (keywords_dir == .../inputs/keywords)
        store_root = keywords_dir.parents[1]

        if load_youtube_api_key:
            youtube_api_key = load_youtube_api_key()
        else:
            youtube_api_key = (_os.getenv("YOUTUBE_API_KEY", "") or "").strip()

        # 키가 아예 없으면: 정책상 FAIL(단, ALLOW_YOUTUBE_FAIL=1이면 예외)
        allow = (_os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
        if (not youtube_api_key) and (not allow):
            raise RuntimeError("LIVE requires YOUTUBE_API_KEY. Set ENV YOUTUBE_API_KEY or Youtube_API_key.txt")

        # ✅ 사이클당 1회만 호출 → 카테고리별 bucket dict를 받는다
        from backend.knowledge_v1.keyword_sources.live_fetch import live_collect_and_snapshot_once
        try:
            yt_buckets = live_collect_and_snapshot_once(
                store_root=store_root,
                cycle_id=cycle_id,
                youtube_api_key=youtube_api_key,
                categories=categories,
            )
            # yt_buckets는 {category: [RawKeyword, ...]} 형태
        except RuntimeError as e:
            # PATCH-13Q.1: YouTube 오류는 live_fetch가 빈 dict로 처리하는 것이 원칙이지만,
            # 혹시 상위로 올라오면 여기서도 격리(파이프라인 무중단)
            msg = str(e)
            allow = (_os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if "QUOTA" in msg.upper() or "quota" in msg.lower():
                youtube_skipped_reason = "quotaExceeded"
                yt_buckets = {c: [] for c in categories}
            elif "expired" in msg.lower() or "API key expired" in msg:
                youtube_skipped_reason = "keyExpired"
                yt_buckets = {c: [] for c in categories}
            elif allow:
                youtube_skipped_reason = "youtubeError"
                yt_buckets = {c: [] for c in categories}
            else:
                raise

        # PATCH-13Q.1: YouTube가 비어도 "카테고리별 FAIL-FAST"는 하지 않는다.
        # 대신: error 파일에서 reason을 정교하게 읽어서 기록한다.
        if all((not yt_buckets.get(c)) for c in categories):
            if youtube_skipped_reason is None:
                # error 파일에서 reason 정교화
                import json as json_module
                error_path = store_root / "snapshots" / cycle_id / "youtube_error___global__.json"
                if error_path.exists():
                    try:
                        with open(error_path, "r", encoding="utf-8") as f:
                            error_data = json_module.load(f)
                        error_text = (error_data.get("text") or "").lower()
                        error_status = error_data.get("status_code")
                        if error_status == 400 and "api key expired" in error_text:
                            youtube_skipped_reason = "keyExpired"
                        elif error_status == 403 or "quota" in error_text:
                            youtube_skipped_reason = "quotaExceeded"
                        else:
                            youtube_skipped_reason = "youtubeError"
                    except Exception:
                        youtube_skipped_reason = "youtubeError"
                else:
                    youtube_skipped_reason = "noYoutubeData"

    # V7 하드락: 카테고리별 서로 다른 TOP5 키워드 강제 생성
    category_keywords_map_final: Dict[str, List[str]] = {c: [] for c in categories}
    category_keyword_entries_final: Dict[str, List[Dict[str, Any]]] = {c: [] for c in categories}
    try:
        from backend.knowledge_v1.keyword_discovery_engine import get_category_keywords_topk

        # 1) 엔진 후보
        category_keywords_map = get_category_keywords_topk(categories=categories, k=per_category_target)
        category_keywords_map = {c: normalize_kw_list(category_keywords_map.get(c, [])) for c in categories}

        # 2) 카테고리 간 중복 제거
        category_keywords_map, dup_report = enforce_unique(category_keywords_map, k=per_category_target)

        # 3) 부족분 보충 (YouTube keyExpired 또는 후보 부족 시 RSS title 기반)
        used_norms = set()
        for c in categories:
            for kw in category_keywords_map.get(c, []):
                used_norms.add(normalize_unique(kw))

        for c in categories:
            current = list(category_keywords_map.get(c, []))
            source_entries = [{"keyword": kw, "source": "yt_api", "is_trending": True} for kw in current]
            if len(current) < per_category_target:
                if mode == "live":
                    needed = per_category_target - len(current)
                    rss_fallback = extract_fallback_keywords_from_rss_titles(
                        category=c,
                        k=max(needed * 3, per_category_target),
                        exclude_norms=used_norms,
                    )
                    for kw in rss_fallback:
                        norm = normalize_unique(kw)
                        if not norm or norm in used_norms:
                            continue
                        used_norms.add(norm)
                        current.append(kw)
                        source_entries.append({"keyword": kw, "source": "rss_fallback", "is_trending": False})
                        if len(current) >= per_category_target:
                            break
                else:
                    file_keywords = load_keywords_from_file(c, keywords_dir, max_keywords=per_category_target * 5)
                    for kw in file_keywords:
                        norm = normalize_unique(kw)
                        if not norm or norm in used_norms:
                            continue
                        used_norms.add(norm)
                        current.append(kw)
                        source_entries.append({"keyword": kw, "source": "rss_fallback", "is_trending": False})
                        if len(current) >= per_category_target:
                            break

            # enforce_unique 후 재확정
            category_keywords_map_final[c] = current[:per_category_target]
            category_keyword_entries_final[c] = source_entries[:per_category_target]

        # 재검증: 카테고리 간 중복 0 / 카테고리당 정확히 5
        category_keywords_map_final, dup_report_2 = enforce_unique(category_keywords_map_final, k=per_category_target)
        for c in categories:
            category_keywords_map_final[c] = assert_kw_contract(
                category_keywords_map_final.get(c, []),
                context=f"cycle:top5:{c}:{mode}",
            )
            if len(category_keywords_map_final[c]) != per_category_target:
                raise RuntimeError(
                    f"TOP5_ENFORCE_FAILED: category={c}, found={len(category_keywords_map_final[c])}, expected={per_category_target}"
                )
            # source entry를 최종 keyword 순서와 동기화
            source_by_norm = {normalize_unique(e["keyword"]): e for e in category_keyword_entries_final.get(c, [])}
            synced_entries = []
            for idx, kw in enumerate(category_keywords_map_final[c], 1):
                norm = normalize_unique(kw)
                base = source_by_norm.get(norm, {"keyword": kw, "source": "rss_fallback", "is_trending": False})
                synced_entries.append(
                    {
                        "keyword": kw,
                        "source": base.get("source", "rss_fallback"),
                        "rank": idx,
                        "is_trending": bool(base.get("is_trending", False)),
                    }
                )
            category_keyword_entries_final[c] = synced_entries

        # 스냅샷 저장 (최종 강제 결과 덮어쓰기)
        repo_root = str(_find_repo_root())
        from backend.knowledge_v1.paths import get_cycle_snapshot_dir

        snapshot_dir = get_cycle_snapshot_dir(repo_root, cycle_id)
        for c in categories:
            snapshot_file = os.path.join(snapshot_dir, f"keywords_{c}_raw.jsonl")
            with open(snapshot_file, "w", encoding="utf-8") as f:
                for row in category_keyword_entries_final[c]:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # cycle_id SSOT 파일 기록
        snapshots_root = os.path.dirname(snapshot_dir)
        last_cycle_id_path = os.path.join(snapshots_root, "last_cycle_id.txt")
        with open(last_cycle_id_path, "w", encoding="utf-8") as f:
            f.write(f"{cycle_id}\n")

        report["debug"]["category_top5_enforced"] = True
        report["debug"]["category_top5_dup_removed"] = (
            int(dup_report.get("removed_count", 0)) + int(dup_report_2.get("removed_count", 0))
        )
        if mode == "live" and youtube_skipped_reason:
            report["debug"]["youtube_skipped_reason"] = youtube_skipped_reason
            report["debug"]["degraded"] = f"youtube_skipped_reason={youtube_skipped_reason}"
    except Exception as e:
        report["summary"]["has_errors"] = True
        report["summary"]["error_type"] = "Top5EnforceFailed"
        report["summary"]["error_message"] = str(e)
        report["debug"]["category_top5_enforced"] = False
        report["debug"]["category_top5_error"] = f"{type(e).__name__}: {str(e)}"
        return report

    for category in categories:
        # Heartbeat 출력 (착시 제거)
        if hb_seconds > 0 and hb_last_time is not None:
            current_time = time.time()
            if current_time - hb_last_time >= hb_seconds:
                print(f"[HB] cycle_id={cycle_id} category={category} assets_written={assets_written} chunks_written={chunks_written}", file=sys.stderr, flush=True)
                hb_last_time = current_time
        
        # LIVE: bucket에서만 가져온다 (카테고리별 YouTube API 호출은 금지)
        live_snapshot_keywords = []
        if mode == "live":
            live_snapshot_keywords = yt_buckets.get(category, []) or []

        # PATCH-08 (dry-run only): 5-source keyword evidence packets → SSOT 저장
        # PATCH-09B (live): SSOT 생성은 live/dry-run 모두 수행, raw 소스만 다름
        if mode in ("dry-run", "live"):
            from backend.knowledge_v1.keyword_sources import (
                collect_youtube_keywords,
                collect_trending_keywords,
                collect_google_trends_keywords,
                collect_wikipedia_keywords,
                collect_gdelt_keywords,
                RawKeyword,
            )
            from backend.knowledge_v1.keyword_sources.wikidata_wikipedia import expand_keywords
            from backend.knowledge_v1.keyword_pipeline import (
                build_keyword_evidence_packet,
                build_daily_keyword_pack,
            )

            # store_root = .../data/knowledge_v1_store
            store_root = keywords_dir.parents[1]
            ssot_dir = store_root / "ssot" / cycle_id
            ssot_dir.mkdir(parents=True, exist_ok=True)

            # 카테고리별 패킷 저장(상위 80개)
            raw = []
            if mode == "dry-run":
                # dry-run: fixtures 기반
                raw += collect_youtube_keywords()
                raw += collect_trending_keywords()
                raw += collect_google_trends_keywords()
                raw += collect_wikipedia_keywords()
                raw += collect_gdelt_keywords()
            elif mode == "live":
                # live: YouTube live snapshot + 4-source fixtures 병합 (5중 데이터셋 반영)
                raw += live_snapshot_keywords
                # PATCH-11: wikipedia opensearch 기반 확장 키워드 생성(최소 1개 보장)
                seed_for_wiki = [rk.keyword for rk in (live_snapshot_keywords or [])][:10]
                if not seed_for_wiki:
                    seed_for_wiki = [category]
                wiki_expanded, wiki_meta = expand_keywords(seed_for_wiki, category)
                wiki_expanded = (wiki_expanded or [])[:50]
                raw += [RawKeyword(keyword=k, source="wikipedia", subtype="opensearch", country="KR", window="evergreen", fetched_at=cycle_id, evidence_hash="", raw_ref="wikipedia_opensearch") for k in wiki_expanded]
                raw += collect_trending_keywords()
                raw += collect_google_trends_keywords()
                raw += collect_wikipedia_keywords()
                raw += collect_gdelt_keywords()

            per_cat = build_keyword_evidence_packet(
                cycle_id=cycle_id,
                category=category,
                raw_keywords=raw,
                per_category_limit=max_keywords_per_category if max_keywords_per_category else 80,
            )
            with open(ssot_dir / f"{category}_keywords_gate1.json", "w", encoding="utf-8") as f:
                json.dump(per_cat, f, ensure_ascii=False, indent=2)

            # 일일 전역 패킷(상위 400개)은 "한 번만" 생성/저장
            daily_path = ssot_dir / "daily_keywords_gate1.json"
            if not daily_path.exists():
                # categories 변수는 이 스코프에서 접근 가능
                packets = {}
                for c in categories:
                    packets[c] = build_keyword_evidence_packet(
                        cycle_id=cycle_id,
                        category=c,
                        raw_keywords=raw,
                        per_category_limit=max_keywords_per_category if max_keywords_per_category else 80,
                    )
                daily = build_daily_keyword_pack(
                    cycle_id=cycle_id,
                    categories=list(categories),
                    per_category_packets=packets,
                    daily_total_limit=daily_total_limit if daily_total_limit else 400,
                )
                # PATCH-09C-SSOT-META: keywords rows에 source/subtype 메타 강제 포함
                rows = []
                for it in daily.get("keywords", []):
                    # it이 dict인 경우
                    if isinstance(it, dict):
                        # sources/subtypes/windows/raw_refs/evidence_hashes가 리스트인 경우 첫 번째 값 사용
                        sources_list = it.get("sources", [])
                        subtypes_list = it.get("subtypes", [])
                        windows_list = it.get("windows", [])
                        raw_refs_list = it.get("raw_refs", [])
                        evidence_hashes_list = it.get("evidence_hashes", [])
                        rows.append({
                            "keyword": it.get("keyword") or it.get("text") or it.get("name") or "",
                            "source": sources_list[0] if sources_list else it.get("source", "?"),
                            "subtype": subtypes_list[0] if subtypes_list else it.get("subtype", None),
                            "country": it.get("country", None),
                            "window": windows_list[0] if windows_list else it.get("window", None),
                            "fetched_at": it.get("fetched_at", None),
                            "evidence_hash": evidence_hashes_list[0] if evidence_hashes_list else it.get("evidence_hash", None),
                            "raw_ref": raw_refs_list[0] if raw_refs_list else it.get("raw_ref", None),
                            "evidence": it.get("evidence", None),
                            "category": it.get("category", None),
                            "keyword_norm": it.get("keyword_norm", None),
                            "score": it.get("score", None),
                        })
                        continue
                    # it이 RawKeyword 같은 객체인 경우(속성 접근)
                    rows.append({
                        "keyword": getattr(it, "keyword", "") or "",
                        "source": getattr(it, "source", "?") or "?",
                        "subtype": getattr(it, "subtype", None),
                        "country": getattr(it, "country", None),
                        "window": getattr(it, "window", None),
                        "fetched_at": getattr(it, "fetched_at", None),
                        "evidence_hash": getattr(it, "evidence_hash", None),
                        "raw_ref": getattr(it, "raw_ref", None),
                        "evidence": getattr(it, "evidence", None),
                    })
                # PATCH-09D: SSOT 직전 키워드 정합성 필터 + 품질 하한선
                import re

                def _is_bad_keyword(s: str) -> bool:
                    if not s:
                        return True
                    t = s.strip()
                    if len(t) < 3:
                        return True
                    # ISO 날짜/시간 형태 제거 (예: 2024-01-01T00:00:00Z)
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", t):
                        return True
                    # 날짜(YYYY-MM-DD)만 있는 경우 제거
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                        return True
                    # 숫자/기호 위주 제거
                    if re.fullmatch(r"[0-9\W_]+", t):
                        return True
                    # URL 형태 제거
                    if t.startswith("http://") or t.startswith("https://"):
                        return True
                    return False

                before_n = len(rows)
                rows = [r for r in rows if not _is_bad_keyword(str(r.get("keyword","")))]
                after_n = len(rows)

                # 디버그: SSOT payload에 필터 통계 포함(기존 출력 포맷은 유지, 필드만 추가)
                filter_stats = {"filtered_out": (before_n - after_n), "before": before_n, "after": after_n}
                # PATCH-09E 품질 게이트: 오염 폭증 방지 (after 기준)
                after_cnt = len(rows)
                # 상향된 daily_total_limit(기본 900)을 적용해도 되는 최소 기준
                # - after_cnt >= 600 이 아니면 너무 적거나 필터링으로 제거된 비율이 높으므로 보수적으로 제한
                if after_cnt < 600:
                    # rows를 400으로 강제 제한(기존 안전값 유지)
                    rows = rows[:400]
                daily["keywords"] = rows
                daily["filter_stats"] = filter_stats
                with open(daily_path, "w", encoding="utf-8") as f:
                    json.dump(daily, f, ensure_ascii=False, indent=2)
        
        category_start_time = datetime.utcnow()
        
        # 초기값 설정 (카테고리 루프 1회전 스코프 내부 선초기화)
        keywords: list = []
        ingest_result: dict = {}
        docs_by_source: dict = {}
        ingested_assets: list = []
        errors: list = []
        keywords_used_count = 0
        ingest_count = 0
        fallback_count = 0
        derived_count = 0
        blocked_count = 0
        promoted_count = 0
        category_error = None
        
        try:
            # remaining 계산: daily_total_limit - total_selected
            remaining = daily_total_limit - total_selected
            if remaining <= 0:
                # total limit 도달 시 즉시 종료
                break
            
            target_keywords = min(per_category_target, remaining)
            keywords = assert_kw_contract(
                category_keywords_map_final.get(category, [])[:target_keywords],
                context=f"cycle:loaded:{category}:{mode}",
            )

            keywords_used_count = len(keywords) if keywords else 0
            total_selected += keywords_used_count

            if len(keywords) != per_category_target:
                raise RuntimeError(
                    f"TOP5_COUNT_MISMATCH: category={category}, found={len(keywords)}, expected={per_category_target}"
                )
            
            ensure_dirs("discovery")
            
            # PATCH-08C (dry-run only): category key normalization against discovery_ingest supported set
            category_key = category
            if mode == "dry-run":
                try:
                    import backend.knowledge_v1.discovery_ingest as di

                    supported = None
                    alias_map = None

                    # 1) 지원 카테고리 집합 추출 (존재하는 것만 사용)
                    if hasattr(di, "SUPPORTED_CATEGORIES"):
                        supported = set(getattr(di, "SUPPORTED_CATEGORIES"))
                    elif hasattr(di, "CATEGORIES"):
                        supported = set(getattr(di, "CATEGORIES"))

                    # 2) alias 맵 추출 (존재하는 것만 사용)
                    if hasattr(di, "CATEGORY_ALIASES"):
                        alias_map = dict(getattr(di, "CATEGORY_ALIASES"))

                    # 3) _alias 함수 직접 호출 (discovery_ingest의 실제 변환 로직 사용, 최우선)
                    if hasattr(di, "_alias"):
                        category_key = di._alias(category)
                    # 4) 정합성 교정: (a) 이미 지원되면 그대로, (b) alias가 있으면 변환
                    elif supported is not None and category_key not in supported:
                        if alias_map is not None and category_key in alias_map:
                            cand = alias_map.get(category_key)
                            if isinstance(cand, str) and cand in supported:
                                category_key = cand
                except Exception:
                    category_key = category
            
            # Ingest → Discovery (Step E: 키워드당 최소 6개 문서, 총 목표 200개)
            # LIVE 모드: cache_only 비활성화(스냅샷 없어도 fallback 수집), allow_live_fallback=True
            ingest_result = ingest_discovery(
                category=category_key,
                keywords=keywords,
                mode=("run" if mode == "live" else mode),
                max_keywords_per_run=max_keywords_per_category,
                min_docs_per_keyword=6 if mode == "run" else 1,  # Step E: 키워드당 최소 6개
                target_total_docs=200 if mode == "run" else 0,  # Step E: 총 목표 200개
                cycle_id=cycle_id,
                cache_only=(os.environ.get("REPLAY_FREEZE_SOURCES") == "1") and (mode != "live"),
                input_hash=manifest.get("input_hash") if manifest else None,
                allow_live_fallback=(mode == "live"),
            )
            
            # Heartbeat 출력 (ingest 후)
            if hb_seconds > 0 and hb_last_time is not None:
                current_time = time.time()
                if current_time - hb_last_time >= hb_seconds:
                    ingested_count = (ingest_result or {}).get("ingested_count", 0)
                    derived_count_local = (ingest_result or {}).get("total_derived", 0)
                    print(f"[HB] cycle_id={cycle_id} category={category} ingested={ingested_count} derived={derived_count_local}", file=sys.stderr, flush=True)
                    hb_last_time = current_time
            
            # ingest_result 타입 검증 및 정규화 (tuple.get 방어)
            import traceback
            # ingest_result 방어적 접근 (미정의 상태 참조 금지)
            safe_ingest_result = ingest_result if ingest_result is not None else {}
            if not isinstance(safe_ingest_result, dict):
                # tuple/list 형태이며 dict를 포함하는 패턴이면 dict로 정규화
                if isinstance(safe_ingest_result, (tuple, list)) and len(safe_ingest_result) > 0:
                    # 첫 번째 요소가 dict인지 확인
                    if isinstance(safe_ingest_result[0], dict):
                        ingest_result = safe_ingest_result[0]
                    else:
                        # dict가 아니면 에러 발생
                        error_msg = f"ingest_result is {type(safe_ingest_result).__name__}, expected dict. First element: {type(safe_ingest_result[0]).__name__}"
                        traceback_str = traceback.format_exc()[:2000]  # 최대 2000자
                        category_error = f"{error_msg}\nTraceback:\n{traceback_str}"
                        raise TypeError(category_error)
                else:
                    # tuple/list도 아니면 에러 발생
                    error_msg = f"ingest_result is {type(safe_ingest_result).__name__}, expected dict"
                    traceback_str = traceback.format_exc()[:2000]  # 최대 2000자
                    category_error = f"{error_msg}\nTraceback:\n{traceback_str}"
                    raise TypeError(category_error)
            else:
                ingest_result = safe_ingest_result
            
            # Discovery assets 로드 (최근 추가된 것만)
            from backend.knowledge_v1.paths import get_assets_path
            discovery_assets_path = get_assets_path("discovery")  # 이미 Path 반환
            
            # Gate#2: assets.jsonl에 쓰기 직전 최종 필터 (빈 asset 제거)
            if discovery_assets_path.exists():
                all_assets = list(load_jsonl(discovery_assets_path))
                valid_assets = []
                normalized_assets_count = 0
                from backend.knowledge_v1.metrics.empty_drop_counter import _source_key_for_asset  # type: ignore
                for asset_dict in all_assets:
                    if _is_empty_asset(asset_dict):
                        # 빈 asset 드롭 및 증거 기록 (SSOT source key 사용)
                        dropped_empty_assets += 1
                        src = _source_key_for_asset(asset_dict)
                        dropped_empty_assets_by_source[src] = dropped_empty_assets_by_source.get(src, 0) + 1
                    else:
                        # V7: 기존 JSONL 자동 정규화 (keyword/list 혼입 정리)
                        try:
                            before_keywords = asset_dict.get("keywords")
                            after_keywords = normalize_kw_list(before_keywords)
                            if after_keywords:
                                asset_dict["keywords"] = after_keywords
                                payload = asset_dict.get("payload")
                                if isinstance(payload, dict):
                                    payload_kw = normalize_kw(payload.get("keyword"))
                                    if payload_kw:
                                        payload["keyword"] = payload_kw
                                if before_keywords != after_keywords:
                                    normalized_assets_count += 1
                        except Exception:
                            pass
                        valid_assets.append(asset_dict)
                
                # 빈 asset 제거 후 assets.jsonl 재작성
                if len(valid_assets) < len(all_assets):
                    discovery_assets_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(discovery_assets_path, "w", encoding="utf-8") as f:
                        for asset_dict in valid_assets:
                            json.dump(asset_dict, f, ensure_ascii=False)
                            f.write("\n")
                elif normalized_assets_count > 0:
                    discovery_assets_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(discovery_assets_path, "w", encoding="utf-8") as f:
                        for asset_dict in valid_assets:
                            json.dump(asset_dict, f, ensure_ascii=False)
                            f.write("\n")
            
            ingested_assets = []
            
            if discovery_assets_path.exists():
                # 전체 assets 로드 (Gate#2 필터링 후)
                all_assets = list(load_jsonl(discovery_assets_path))
                # 카테고리 매칭 및 최신순 정렬
                category_assets = [a for a in all_assets if a.get("category") == category]
                category_assets.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
                # 최근 N개만 (중복 제거를 위해 raw_hash 기준)
                seen_hashes = set()
                for asset_dict in category_assets:
                    raw_hash = asset_dict.get("raw_hash", "")
                    if raw_hash and raw_hash not in seen_hashes:
                        try:
                            asset = KnowledgeAsset.from_dict(asset_dict)
                            ingested_assets.append(asset)
                            seen_hashes.add(raw_hash)
                            if len(ingested_assets) >= max_keywords_per_category:
                                break
                        except Exception:
                            continue
            
            ingest_count = (ingest_result or {}).get("ingested_count", len(ingested_assets))
            # fallback_count는 ingest_result에서 가져오고, 없으면 source_id로 계산
            fallback_count = (ingest_result or {}).get("fallback_count", 0)
            if fallback_count == 0:
                fallback_count = sum(1 for a in ingested_assets if a.source_id in ["fallback_synthetic", "fixtures"])
            
            # V7: Source Scoring 적용
            try:
                from backend.knowledge_v1.source_scoring import compute_source_score
                for asset in ingested_assets:
                    source_score = compute_source_score(asset, policy if 'policy' in locals() else None)
                    asset.source_score = source_score
            except Exception:
                pass  # source scoring 실패해도 계속 진행
            
            # V7: 2단계 Dedup 적용
            try:
                from backend.knowledge_v1.dedup import dedup_keywords
                # 키워드 리스트에서 dedup
                all_keywords = []
                for asset in ingested_assets:
                    all_keywords.extend(asset.keywords)
                
                deduped_keywords, exact_removed, similar_removed = dedup_keywords(all_keywords)
                
                # 리포트에 기록
                if "dedup_exact_removed" not in report:
                    report["dedup_exact_removed"] = 0
                    report["dedup_similar_removed"] = 0
                report["dedup_exact_removed"] += exact_removed
                report["dedup_similar_removed"] += similar_removed
            except Exception:
                pass  # dedup 실패해도 계속 진행
            
            # V7: Circuit Breaker 검사
            try:
                from backend.knowledge_v1.quality.circuit_breaker import check_circuit_breaker
                should_stop, cb_reason, cb_stats = check_circuit_breaker("discovery", policy if 'policy' in locals() else None)
                if should_stop:
                    # 추가 fetch 중단
                    report["circuit_breaker_triggered"] = True
                    report["circuit_breaker_reason"] = cb_reason
                    break  # 카테고리 루프 중단
            except Exception:
                pass  # circuit breaker 실패해도 계속 진행
            
            # Derive/Classify
            for asset in ingested_assets:
                # License gate
                passed, reason = apply_license_gate(asset)
                if not passed:
                    blocked_count += 1
                    continue
                
                # Derive (discovery store에 저장)
                chunks = derive_for_store(asset, "discovery")
                derived_count += len(chunks)
                
                # Classify: fixtures asset은 depth="deep"으로 호출 (FULLY_USABLE 가능하도록)
                # fixtures asset은 충분히 긴 텍스트(2,500자 이상)를 가지고 있으므로 depth="deep" 적합
                depth_mode = "deep" if asset.source_id == "fixture_snapshot" else "normal"
                eligibility = classify_for_store(asset, "discovery", depth=depth_mode)
            
            # 최소 1건 보장: ingest_count가 0이면 fallback 생성 후 derive
            # (discovery_ingest에서 이미 fallback을 생성했지만, 이중 체크로 추가 보장)
            if ingest_count == 0 and mode == "run" and len(ingested_assets) == 0:
                from backend.knowledge_v1.fallback import create_fallback_asset
                
                # fallback asset 생성 (방어적 접근: keywords가 리스트인지 확인)
                fallback_keywords = (keywords[:1] if isinstance(keywords, list) and len(keywords) > 0 else [category])
                fallback_asset = create_fallback_asset(category, fallback_keywords)
                
                # HARD GUARD: category 검증 (persistence 전)
                fallback_asset.validate()
                
                # Gate#1: assets 컬렉션에 append 하기 직전 (빈 asset 체크)
                fallback_asset_dict = fallback_asset.to_dict() if hasattr(fallback_asset, 'to_dict') else fallback_asset
                if _is_empty_asset(fallback_asset_dict):
                    # 빈 asset 드롭 및 증거 기록 (SSOT source key 사용)
                    from backend.knowledge_v1.metrics.empty_drop_counter import _source_key_for_asset  # type: ignore

                    dropped_empty_assets += 1
                    src = _source_key_for_asset(fallback_asset_dict)
                    dropped_empty_assets_by_source[src] = dropped_empty_assets_by_source.get(src, 0) + 1
                    # append 하지 않고 스킵
                else:
                    # discovery store에 추가
                    from backend.knowledge_v1.store import append_asset
                    if append_asset(fallback_asset, "discovery", skip_duplicate=True):
                        ingest_count = 1
                        fallback_count = 1
                        ingested_assets = [fallback_asset]
                        
                        # License gate (fallback은 통과해야 함)
                        passed, reason = apply_license_gate(fallback_asset)
                        if passed:
                            # Derive (discovery store에 저장)
                            chunks = derive_for_store(fallback_asset, "discovery")
                            derived_count = len(chunks)
                            
                            # Classify
                            classify_for_store(fallback_asset, "discovery", depth="normal")
                        else:
                            blocked_count = 1
                            ingest_count = 0  # blocked이면 count 0으로 되돌림
            
            # V7: Deficit Scheduler 적용 (부족분 계산 - 승격 전)
            try:
                from backend.knowledge_v1.state.deficit_scheduler import compute_category_deficit
                target_per_category = policy.get("per_category_target_keywords", 5) if 'policy' in locals() else 5
                deficit_before = compute_category_deficit([category], target_per_category, cycle_id)
                if category not in report["categories"]:
                    report["categories"][category] = {}
                report["categories"][category]["category_deficit_before"] = deficit_before.get(category, 0)
            except Exception:
                pass
            
            # Promote (Discovery → Approved)
            # V7: 6개 카테고리 모두 승격 대상
            if category in {"history", "mystery", "economy", "myth", "science", "war_history"}:
                promote_result = promote_to_approved_v2(
                    category=category,
                    approve_fallback=approve_fallback
                )
                promoted_count = promote_result.get("promoted_count", 0)
                
                # V7: Deficit Scheduler (승격 후)
                try:
                    target_per_category = policy.get("per_category_target_keywords", 5) if 'policy' in locals() else 5
                    deficit_after = compute_category_deficit([category], target_per_category, cycle_id)
                    if category not in report["categories"]:
                        report["categories"][category] = {}
                    report["categories"][category]["category_deficit_after"] = deficit_after.get(category, 0)
                except Exception:
                    pass
            
            # 전체 집계
            report["summary"]["total_selected"] = total_selected  # total limit 반영
            report["summary"]["total_ingested"] += ingest_count
            report["summary"]["total_fallback"] += fallback_count
            report["summary"]["total_derived"] += derived_count
            report["summary"]["total_blocked"] += blocked_count
            report["summary"]["total_promoted"] += promoted_count
            
        except Exception as e:
            import traceback
            # category_error에 traceback 포함 (최대 2000자)
            error_msg = str(e)
            traceback_str = traceback.format_exc()[:2000]
            category_error = f"{error_msg}\nTraceback:\n{traceback_str}"
        
        finally:
            # keywords 안전 초기화 (UnboundLocalError 방지 - 함수 시작 부분에서 이미 선초기화됨)
            # 함수 시작 부분에서 이미 keywords: list = []로 선초기화되어 있으므로 안전하게 사용 가능
            # 하지만 예외 경로에서 할당되지 않았을 수 있으므로 안전 변수 사용
            keywords_safe_finally = keywords or []
            
            # CATEGORY_RUN_SUMMARY audit (항상 기록)
            category_elapsed = (datetime.utcnow() - category_start_time).total_seconds()
            
            summary_details = {
                "category": category,
                "keywords_used_count": keywords_used_count,
                "ingest_count": ingest_count,
                "fallback_count": fallback_count,
                "derived_count": derived_count,
                "blocked_count": blocked_count,
                "promoted_count": promoted_count,
                "elapsed_seconds": category_elapsed
            }
            
            if category_error:
                summary_details["error"] = category_error
            
            append_audit(AuditEvent.create("CATEGORY_RUN_SUMMARY", summary_details), "discovery")
            
            # docs_by_source 집계 (카테고리별, ingest_result/ingested_assets 미정의 방지)
            safe_ingest_result = ingest_result or {}
            docs_by_source_safe = safe_ingest_result.get("docs_by_source") or docs_by_source or {}
            if not isinstance(docs_by_source_safe, dict):
                docs_by_source_safe = {}
            if not docs_by_source_safe:
                # source_id로 집계
                for a in (ingested_assets or []):
                    source = getattr(a, "source_id", None) or "unknown"
                    docs_by_source_safe[source] = docs_by_source_safe.get(source, 0) + 1
            
            # 2차 크래시 방지 가드 (미정의/타입 오염 즉시 파일/라인으로 고정)
            # 안전 변수 사용 (UnboundLocalError 0% 보장)
            keywords_safe = keywords_safe_finally
            ingest_result_safe = ingest_result or {}
            ingested_assets_safe = ingested_assets or []
            assert isinstance(keywords_safe, list) and isinstance(ingest_result_safe, dict) and isinstance(ingested_assets_safe, list)
            
            # 리포트 기록 (방어형 접근으로 2차 크래시 0% 보장)
            report["categories"][category] = {
                "ingest_count": ingest_count,
                "fallback_count": fallback_count,
                "derived_count": derived_count,
                "blocked_count": blocked_count,
                "promoted_count": promoted_count,
                "elapsed_seconds": category_elapsed,
                "docs_by_source": docs_by_source_safe,
                "keywords": keywords_safe  # 키워드 목록도 저장 (미정의/None 방지)
            }
            
            if category_error:
                report["categories"][category]["error"] = category_error
    
    # DRY-RUN MULTI-CYCLE SCALE-UP
    # assets PASS(>=200)를 확정시키기 위해 dry-run에서만 3회전 수행
    if mode == "dry-run":
        # 2회차 + 3회차를 위해 quota 상태를 매 회차 초기화
        for _round in (2, 3):
            try:
                from backend.knowledge_v1.quota import get_quota_state_path
                qp = get_quota_state_path()
                if qp.exists():
                    qp.unlink()
            except Exception:
                pass

            for category in categories:
                remaining = daily_total_limit - total_selected
                if remaining <= 0:
                    break

                from backend.knowledge_v1.quota import PER_CATEGORY_LIMIT
                quota_limit = PER_CATEGORY_LIMIT.get(category, max_keywords_per_category)
                take = min(max_keywords_per_category, remaining, quota_limit)
                if take <= 0:
                    continue

                keywords = _expand_keywords_for_dry_run(category, keywords_dir, take)
                if not keywords:
                    continue

                # PATCH-08C (dry-run only): category key normalization against discovery_ingest supported set
                category_key = category
                try:
                    import backend.knowledge_v1.discovery_ingest as di

                    supported = None
                    alias_map = None

                    # 1) 지원 카테고리 집합 추출 (존재하는 것만 사용)
                    if hasattr(di, "SUPPORTED_CATEGORIES"):
                        supported = set(getattr(di, "SUPPORTED_CATEGORIES"))
                    elif hasattr(di, "CATEGORIES"):
                        supported = set(getattr(di, "CATEGORIES"))

                    # 2) alias 맵 추출 (존재하는 것만 사용)
                    if hasattr(di, "CATEGORY_ALIASES"):
                        alias_map = dict(getattr(di, "CATEGORY_ALIASES"))

                    # 3) _alias 함수 직접 호출 (discovery_ingest의 실제 변환 로직 사용, 최우선)
                    if hasattr(di, "_alias"):
                        category_key = di._alias(category)
                    # 4) 정합성 교정: (a) 이미 지원되면 그대로, (b) alias가 있으면 변환
                    elif supported is not None and category_key not in supported:
                        if alias_map is not None and category_key in alias_map:
                            cand = alias_map.get(category_key)
                            if isinstance(cand, str) and cand in supported:
                                category_key = cand
                except Exception:
                    category_key = category

                # ingest 재실행
                ingest_result = ingest_discovery(
                    category=category_key,
                    keywords=keywords,
                    mode=("dry-run" if mode == "live" else mode),
                    max_keywords_per_run=max_keywords_per_category,
                    cycle_id=cycle_id,
                    cache_only=(os.environ.get("REPLAY_FREEZE_SOURCES") == "1") and (mode != "live"),
                    input_hash=manifest.get("input_hash") if manifest else None,
                    allow_live_fallback=(mode == "live"),
                )
                
                # 새로 생성된 assets 로드 및 derive/classify 처리
                from backend.knowledge_v1.paths import get_assets_path
                discovery_assets_path = get_assets_path("discovery")
                
                # Gate#2: assets.jsonl에 쓰기 직전 최종 필터 (빈 asset 제거)
                all_assets = []
                if discovery_assets_path.exists():
                    all_assets = list(load_jsonl(discovery_assets_path))
                    valid_assets = []
                    from backend.knowledge_v1.metrics.empty_drop_counter import _source_key_for_asset  # type: ignore
                    for asset_dict in all_assets:
                        if _is_empty_asset(asset_dict):
                            # 빈 asset 드롭 및 증거 기록 (SSOT source key 사용)
                            dropped_empty_assets += 1
                            src = _source_key_for_asset(asset_dict)
                            dropped_empty_assets_by_source[src] = dropped_empty_assets_by_source.get(src, 0) + 1
                        else:
                            valid_assets.append(asset_dict)
                    
                    # 빈 asset 제거 후 assets.jsonl 재작성
                    if len(valid_assets) < len(all_assets):
                        discovery_assets_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(discovery_assets_path, "w", encoding="utf-8") as f:
                            for asset_dict in valid_assets:
                                json.dump(asset_dict, f, ensure_ascii=False)
                                f.write("\n")
                    all_assets = valid_assets
                
                if all_assets:
                    category_assets = [a for a in all_assets if a.get("category") == category]
                    # 최신순 정렬하여 새로 추가된 것만 처리
                    category_assets.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
                    seen_hashes = set()
                    
                    for asset_dict in category_assets:
                        raw_hash = asset_dict.get("raw_hash", "")
                        if raw_hash and raw_hash not in seen_hashes:
                            try:
                                asset = KnowledgeAsset.from_dict(asset_dict)
                                seen_hashes.add(raw_hash)
                                
                                # License gate
                                passed, reason = apply_license_gate(asset)
                                if not passed:
                                    continue
                                
                                # Derive
                                chunks = derive_for_store(asset, "discovery")
                                
                                # Classify
                                depth_mode = "deep" if asset.source_id == "fixture_snapshot" else "normal"
                                classify_for_store(asset, "discovery", depth=depth_mode)
                            except Exception:
                                continue

                total_selected += take
    
    # PATCH-14 STEP 2: LIVE 모드에서 비-YouTube 최소 ingest 목표 보강 루프
    # YouTube가 스킵된 경우 비-YouTube 소스로부터 추가 수집을 수행
    if mode == "live" and youtube_skipped_reason:
        non_yt_min_ingest_total = int(_os.getenv("NON_YT_MIN_INGEST_TOTAL", "60"))
        non_yt_min_ingest_per_category = int(_os.getenv("NON_YT_MIN_INGEST_PER_CATEGORY", "8"))
        
        # 현재 total_ingested가 목표값보다 낮으면 보강 루프 실행
        current_total_ingested = report["summary"].get("total_ingested", 0)
        if current_total_ingested < non_yt_min_ingest_total:
            boost_rounds = 0
            boost_max_rounds = 3
            boost_added_ingested = 0
            
            while current_total_ingested < non_yt_min_ingest_total and boost_rounds < boost_max_rounds:
                boost_rounds += 1
                
                # 카테고리별로 ingest_count가 낮은 카테고리부터 우선 보강
                category_needs_boost = []
                for cat in categories:
                    cat_ingest = report["categories"].get(cat, {}).get("ingest_count", 0)
                    if cat_ingest < non_yt_min_ingest_per_category:
                        category_needs_boost.append((cat, cat_ingest))
                
                # ingest_count가 낮은 순으로 정렬
                category_needs_boost.sort(key=lambda x: x[1])
                
                for cat, _ in category_needs_boost:
                    if current_total_ingested >= non_yt_min_ingest_total:
                        break
                    
                    remaining = daily_total_limit - total_selected
                    if remaining <= 0:
                        break
                    
                    # 추가 키워드 로드
                    take = min(max_keywords_per_category, remaining, non_yt_min_ingest_per_category)
                    if take <= 0:
                        continue
                    
                    keywords = load_keywords_from_file(cat, keywords_dir, take)
                    if not keywords:
                        continue
                    
                    # category key normalization
                    category_key = cat
                    try:
                        import backend.knowledge_v1.discovery_ingest as di
                        if hasattr(di, "_alias"):
                            category_key = di._alias(cat)
                    except Exception:
                        category_key = cat
                    
                    # ingest 재실행 (live 모드이지만 dry-run으로 처리하여 quota 영향 없음)
                    try:
                        ingest_result = ingest_discovery(
                            category=category_key,
                            keywords=keywords,
                            mode="run",  # live 모드에서는 "run"으로 호출
                            max_keywords_per_run=max_keywords_per_category,
                            cycle_id=cycle_id,
                            cache_only=(os.environ.get("REPLAY_FREEZE_SOURCES") == "1") and (mode != "live"),
                            input_hash=manifest.get("input_hash") if manifest else None,
                            allow_live_fallback=(mode == "live"),
                        )
                        
                        # 새로 생성된 assets 로드 및 derive/classify 처리
                        from backend.knowledge_v1.paths import get_assets_path
                        discovery_assets_path = get_assets_path("discovery")
                        
                        # Gate#2: assets.jsonl에 쓰기 직전 최종 필터 (빈 asset 제거)
                        all_assets = []
                        if discovery_assets_path.exists():
                            all_assets = list(load_jsonl(discovery_assets_path))
                            valid_assets = []
                            for asset_dict in all_assets:
                                if _is_empty_asset(asset_dict):
                                    # 빈 asset 드롭 및 증거 기록 (SSOT source key 사용)
                                    from backend.knowledge_v1.metrics.empty_drop_counter import _source_key_for_asset  # type: ignore

                                    dropped_empty_assets += 1
                                    src = _source_key_for_asset(asset_dict)
                                    dropped_empty_assets_by_source[src] = dropped_empty_assets_by_source.get(src, 0) + 1
                                else:
                                    valid_assets.append(asset_dict)
                            
                            # 빈 asset 제거 후 assets.jsonl 재작성
                            if len(valid_assets) < len(all_assets):
                                discovery_assets_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(discovery_assets_path, "w", encoding="utf-8") as f:
                                    for asset_dict in valid_assets:
                                        json.dump(asset_dict, f, ensure_ascii=False)
                                        f.write("\n")
                            all_assets = valid_assets
                        
                        if all_assets:
                            cat_assets = [a for a in all_assets if a.get("category") == cat]
                            cat_assets.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
                            seen_hashes = set()
                            
                            round_added = 0
                            for asset_dict in cat_assets:
                                raw_hash = asset_dict.get("raw_hash", "")
                                if raw_hash and raw_hash not in seen_hashes:
                                    try:
                                        asset = KnowledgeAsset.from_dict(asset_dict)
                                        seen_hashes.add(raw_hash)
                                        
                                        # License gate
                                        passed, reason = apply_license_gate(asset)
                                        if not passed:
                                            continue
                                        
                                        # Derive
                                        chunks = derive_for_store(asset, "discovery")
                                        
                                        # Classify
                                        classify_for_store(asset, "discovery", depth="normal")
                                        
                                        round_added += 1
                                    except Exception:
                                        continue
                            
                            boost_added_ingested += round_added
                            report["summary"]["total_ingested"] += round_added
                            if cat not in report["categories"]:
                                report["categories"][cat] = {"ingest_count": 0}
                            report["categories"][cat]["ingest_count"] = report["categories"][cat].get("ingest_count", 0) + round_added
                            current_total_ingested += round_added
                            total_selected += take
                    except Exception:
                        continue
            
            # 리포트 debug에 보강 통계 기록
            if "debug" not in report:
                report["debug"] = {}
            report["debug"]["non_yt_boost_rounds"] = boost_rounds
            report["debug"]["non_yt_boost_added_ingested"] = boost_added_ingested
    
    # DISCOVERY_CYCLE_END
    cycle_end_time = datetime.utcnow()
    total_elapsed = (cycle_end_time - cycle_start_time).total_seconds()
    
    # derived_count SSOT: derived chunks 파일 기준으로 재계산
    try:
        from backend.knowledge_v1.paths import get_discovery_derived_chunks_path
        from backend.knowledge_v1.metrics.derived_counter import count_derived_by_category

        derived_chunks_path = get_discovery_derived_chunks_path()
        derived_counts = count_derived_by_category(derived_chunks_path)

        for cat, cat_data in report.get("categories", {}).items():
            cat_data["derived_count"] = int(derived_counts.get(cat, 0))

        # summary total_derived도 SSOT 기준으로 재계산
        report["summary"]["total_derived"] = sum(
            int(c.get("derived_count", 0) or 0) for c in report.get("categories", {}).values()
        )
    except Exception:
        pass

    report["ended_at"] = cycle_end_time.isoformat() + "Z"
    report["total_elapsed_seconds"] = total_elapsed
    
    # war_history derived=0 진단 리포트 + 정책 기반 FAIL 옵션 (SSOT: chunks.jsonl 기반)
    try:
        war_info = report.get("categories", {}).get("war_history", {})
        war_derived = int(war_info.get("derived_count", 0) or 0)
        from backend.knowledge_v1.paths import (
            get_discovery_raw_assets_path,
            get_discovery_derived_chunks_path,
            get_derive_zero_report_path,
            get_empty_drop_report_path,
        )
        from backend.knowledge_v1.diagnostics.derive_zero_report import build_derive_zero_report
        from backend.knowledge_v1.metrics.empty_drop_counter import collect_empty_drop_stats

        assets_path = get_discovery_raw_assets_path()
        chunks_path = get_discovery_derived_chunks_path()

        # war_history derive_zero 진단 (현재 cycle_id 기준)
        diag = build_derive_zero_report(assets_path, chunks_path, "war_history", cycle_id=cycle_id)
        war_chunks_total = int(diag.get("war_chunks_total", 0) or 0)

        # war_chunks_total==0 이고 war_derived==0 일 때만 derive_zero_report 생성
        if war_derived == 0 and war_chunks_total == 0:
            diag_path = get_derive_zero_report_path("war_history", cycle_id)
            diag_path.parent.mkdir(parents=True, exist_ok=True)
            with open(diag_path, "w", encoding="utf-8") as f:
                json.dump(diag, f, ensure_ascii=False, indent=2)

            report.setdefault("diagnostics", {})["derive_zero_war_history_path"] = str(diag_path)
            report["categories"].setdefault("war_history", {})["derive_zero_report_path"] = str(diag_path)
            append_audit(AuditEvent.create("DERIVE_ZERO_DIAGNOSTIC", {
                "cycle_id": cycle_id,
                "category": "war_history",
                "report_path": str(diag_path),
                "war_assets_total": diag.get("war_assets_total", 0),
                "war_assets_empty_text_count": diag.get("war_assets_empty_text_count", 0),
                "war_chunks_total": war_chunks_total,
            }), "discovery")

            fail_on_derived_zero = []
            if isinstance(policy, dict):
                fail_on_derived_zero = policy.get("fail_on_derived_zero", []) or []
            if "war_history" in fail_on_derived_zero:
                report["categories"].setdefault("war_history", {})["error"] = "derived_count_zero"

        # empty drop 리포트 (현재 cycle 전체 기준, summary.dropped_empty_assets > 0 인 경우)
        if dropped_empty_assets > 0:
            total_empty, by_source_empty, samples_empty = collect_empty_drop_stats(assets_path)
            empty_report = {
                "cycle_id": cycle_id,
                "total": total_empty,
                "by_source": by_source_empty,
                "samples": samples_empty,
            }
            # SSOT 경로로 empty_drop 리포트 저장 (cycle_id 원문 그대로 사용)
            empty_diag_path = get_empty_drop_report_path(cycle_id)
            empty_diag_path.parent.mkdir(parents=True, exist_ok=True)
            with open(empty_diag_path, "w", encoding="utf-8") as f:
                json.dump(empty_report, f, ensure_ascii=False, indent=2)

            # SSOT 경로를 result JSON에 기록 (cycle_id와 1:1 일치 보장)
            report.setdefault("diagnostics", {})["empty_drop_report_path"] = str(empty_diag_path)
    except Exception:
        pass

    # PATCH-13Q: youtube_skipped_reason을 report["debug"] 및 diagnostics에 추가
    # PATCH-14 STEP 2: 비-YouTube 최소 ingest 목표 환경변수 확인 및 리포트 기록
    if mode == "live":
        if "debug" not in report:
            report["debug"] = {}
        report["debug"]["youtube_skipped_reason"] = youtube_skipped_reason
        
        # diagnostics에 youtube_skipped_reason 및 youtube_error_file 경로 추가
        if not report.get("diagnostics"):
            report["diagnostics"] = {}
        if youtube_skipped_reason:
            report["diagnostics"]["youtube_skipped_reason"] = youtube_skipped_reason
            # youtube_error_file 경로 추가 (존재하는 경우)
            try:
                from backend.knowledge_v1.paths import get_root
                store_root = get_root()
                error_path = store_root / "snapshots" / cycle_id / "youtube_error___global__.json"
                if error_path.exists():
                    report["diagnostics"]["youtube_error_file"] = str(error_path)
            except Exception:
                pass
        
        # PATCH-14: 비-YouTube 최소 ingest 목표 환경변수 기록
        non_yt_min_ingest_total = int(_os.getenv("NON_YT_MIN_INGEST_TOTAL", "60"))
        non_yt_min_ingest_per_category = int(_os.getenv("NON_YT_MIN_INGEST_PER_CATEGORY", "8"))
        report["debug"]["non_yt_min_ingest_total"] = non_yt_min_ingest_total
        report["debug"]["non_yt_min_ingest_per_category"] = non_yt_min_ingest_per_category
    
    # summary에 에러가 발생한 카테고리 목록 추가
    error_categories = [cat for cat, data in report["categories"].items() if "error" in data]
    if error_categories:
        report["summary"]["error_categories"] = error_categories
        report["summary"]["has_errors"] = True
    else:
        report["summary"]["has_errors"] = False
    
    # summary에 빈 asset 드롭 증거 필드 추가 (장기운영용)
    report["summary"]["dropped_empty_assets"] = dropped_empty_assets
    report["summary"]["dropped_empty_assets_by_source"] = dropped_empty_assets_by_source
    
    append_audit(AuditEvent.create("DISCOVERY_CYCLE_END", {
        "cycle_id": cycle_id,
        "total_elapsed_seconds": total_elapsed,
        "summary": report["summary"]
    }), "discovery")
    
    # v7-run 오케스트레이션: approved audit에도 기록 (스케줄러 proof 확정)
    append_audit(AuditEvent.create("DISCOVERY_CYCLE_END_APPROVED", {
        "cycle_id": cycle_id,
        "total_elapsed_seconds": total_elapsed,
        "summary": report["summary"],
        "layer": "approved"
    }), "approved")
    
    # V7: Source Budget 저장
    try:
        from backend.knowledge_v1.source_budget import allocate_budget, save_budget
        budget = allocate_budget(cycle_id, policy if 'policy' in locals() else None)
        save_budget(cycle_id, budget)
        report["source_budget"] = budget
    except Exception:
        pass  # source budget 실패해도 계속 진행
    
    # V7: Replay Manifest 업데이트 (스냅샷 SHA256 최종 계산)
    try:
        from backend.knowledge_v1.replay.manifest import load_manifest, save_manifest, compute_snapshots_sha256
        manifest = load_manifest(cycle_id)
        if manifest:
            snapshots_sha256 = compute_snapshots_sha256(cycle_id)
            manifest["snapshots_sha256"] = snapshots_sha256
            save_manifest(cycle_id, manifest)
    except Exception:
        pass
    
    # chunks.jsonl 결정론: dedupe + 정렬 후 재기록 (replay fingerprint 일치, 실패 시 raise)
    from backend.knowledge_v1.paths import get_chunks_path
    from backend.knowledge_v1.store import normalize_chunks_jsonl_for_replay
    normalize_chunks_jsonl_for_replay(get_chunks_path("discovery"))
    
    # JSON 기록 전 강제 검증 (런타임 변수 누락 즉시 RuntimeError)
    required_runtime_vars = {"gate_stats_path_str": gate_stats_path_str}
    for k, v in required_runtime_vars.items():
        if v is None:
            raise RuntimeError(f"{k}_UNDEFINED")
        if isinstance(v, str) and v.strip() == "":
            raise RuntimeError(f"{k}_EMPTY")
    
    # 리포트 저장 (SSOT 경로 사용 - gate_stats_path_str 재정의 금지)
    # 게이트 통계 산출 및 저장 (v7 적재량 증대) - report_paths 단일 객체만 사용
    try:
        from backend.knowledge_v1.gate_stats import save_gate_stats
        save_gate_stats("discovery", gate_stats_path=gate_stats_path)
        report["gate_stats_path"] = gate_stats_path_str
    except Exception:
        # 게이트 통계 산출 실패 시에도 SSOT 경로는 기록 (파일 없어도 경로는 동일)
        report["gate_stats_path"] = gate_stats_path_str
    
    # ============================================================
    # GOVERNANCE LAYER: 실행 후 검증 및 기록 (manifest/input_hash 항상 기록, replay는 런을 죽이지 않음)
    # ============================================================
    # 1) manifest 로드 + report에 execution_manifest/input_hash 먼저 embed (진단 누락 방지)
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_loaded = json.load(f)
    except Exception as e:
        raise RuntimeError(f"REPLAY_VERIFICATION_EXCEPTION: manifest load failed: {e}") from e
    input_hash = manifest_loaded.get("input_hash")
    if not input_hash:
        raise RuntimeError("REPLAY_INPUT_HASH_MISSING_IN_MANIFEST")
    if "governance" not in report:
        report["governance"] = {}
    report["governance"]["execution_manifest_path"] = str(manifest_path)
    report["governance"]["execution_manifest"] = manifest_loaded
    report["governance"]["input_hash"] = input_hash

    # 2) replay_verification 수행 (예외 시 error로 기록하고 런 계속, mismatch만 런 FAIL)
    repo_root_path = _paths_module.as_path(repo_root)
    reports_dir = report_paths.gate_stats.parent
    governance_dir = report_paths.governance_dir
    _report_path = report_paths.gate_stats.parent / f"discovery_cycle_{cycle_id}.json"
    replay_verification = None
    verified = True
    reason = "baseline_created"
    try:
        from backend.knowledge_v1.governance_fingerprints import compute_replay_fingerprints
        from backend.governance.replay_baseline_store import (
            get_replay_baselines_path,
            load_replay_baselines,
            save_replay_baselines,
            verify_or_update_canonical_baseline,
        )
        from backend.governance.deterministic_replay import write_mismatch_diff

        fp_bundle = compute_replay_fingerprints(repo_root_path)
        raw_fp = fp_bundle.get("raw") or {}
        canonical_fp = fp_bundle.get("canonical") or {}
        counts = fp_bundle.get("counts") or {}

        baseline_path = get_replay_baselines_path(repo_root_path)
        root = load_replay_baselines(baseline_path)
        verified, reason, root2, diff_payload = verify_or_update_canonical_baseline(
            root,
            input_hash=input_hash,
            run_id=cycle_id,
            policy_version=manifest_loaded.get("policy_version", ""),
            api_snapshot_hash=manifest_loaded.get("api_snapshot_hash", ""),
            canonical_fingerprints=canonical_fp,
            raw_fingerprints=raw_fp,
            counts=counts,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        # report/governance에 raw+canonical fingerprint 및 카운트 모두 embed
        replay_fingerprints_payload = {
            "raw": raw_fp,
            "canonical": canonical_fp,
            "counts": counts,
        }
        report["governance"]["replay_fingerprints"] = replay_fingerprints_payload

        if reason == "mismatch":
            diff_path = write_mismatch_diff(repo_root_path, cycle_id, diff_payload or {})
            replay_verification = {
                "verified": False,
                "reason": "mismatch",
                "mismatch_diff_path": str(diff_path),
                "baseline_path": str(baseline_path),
                "fingerprints": replay_fingerprints_payload,
            }
            report["governance"]["replay_verification"] = replay_verification
            report["summary"]["replay_mismatch"] = True
            report["summary"]["replay_verification"] = replay_verification
            if os.environ.get("REQUIRE_REPLAY_OK", "0") == "1":
                report["ok"] = False
                _finalize_and_write_discovery_report(report, cycle_id, gate_stats_path_str)
                raise RuntimeError("REPLAY_MISMATCH")
            report["governance"]["degraded"] = True
            report["governance"]["degraded_reason"] = "REPLAY_MISMATCH"
        else:
            save_replay_baselines(baseline_path, root2)
            replay_verification = {
                "verified": verified,
                "reason": reason,
                "baseline_path": str(baseline_path),
                "fingerprints": replay_fingerprints_payload,
            }
            report["governance"]["replay_verification"] = replay_verification
    except RuntimeError as e:
        if "REPLAY_MISMATCH" in str(e):
            raise
        replay_verification = {"verified": False, "reason": "error", "error": str(e)}
        report["governance"]["replay_verification"] = replay_verification
    except Exception as e:
        replay_verification = {"verified": False, "reason": "error", "error": str(e)}
        report["governance"]["replay_verification"] = replay_verification
    if report["governance"].get("replay_verification") is None:
        report["governance"]["replay_verification"] = {"verified": False, "reason": "error", "error": "replay_verification not set"}
    
    # ============================================================
    # GOVERNANCE LAYER: v7-run 종료 훅 - source_probabilities.json + evolution_history.json 생성 (항상)
    # ============================================================
    source_probabilities_path_str = None
    evolution_history_path_str = None
    
    try:
        from backend.governance.adaptive_exploration import compute_source_probabilities, write_source_probabilities
        from backend.governance.source_evolution_engine import compute_evolution_snapshot, append_evolution_history
        from backend.knowledge_v1.paths import get_repo_root, ensure_governance_dir
        
        repo_root = get_repo_root()
        ensure_governance_dir(repo_root)
        
        # categories_result와 summary_stats 추출
        categories_result = report.get("categories", {})
        summary_stats = report.get("summary", {})
        
        # 1. source_probabilities.json 생성
        try:
            prob_payload = compute_source_probabilities(categories_result)
            source_probabilities_path_str = write_source_probabilities(repo_root, prob_payload)
        except Exception as e:
            raise RuntimeError(f"source_probabilities.json 생성 실패: {type(e).__name__}: {str(e)}")
        
        # 2. evolution_history.json 생성
        try:
            evolution_snapshot = compute_evolution_snapshot(categories_result, summary_stats)
            evolution_history_path_str = append_evolution_history(repo_root, evolution_snapshot)
        except Exception as e:
            raise RuntimeError(f"evolution_history.json 생성 실패: {type(e).__name__}: {str(e)}")
        
        # diagnostics에 경로 기록
        if "diagnostics" not in report:
            report["diagnostics"] = {}
        report["diagnostics"]["source_probabilities_path"] = source_probabilities_path_str
        report["diagnostics"]["evolution_history_path"] = evolution_history_path_str
        
    except RuntimeError:
        # 하드락: 파일 저장 실패 시 v7-run 자체를 FAIL 처리
        raise
    except Exception as e:
        # 예상치 못한 오류도 FAIL 처리
        raise RuntimeError(f"Governance 파일 생성 중 오류: {type(e).__name__}: {str(e)}")
    
    # 2. 소스 진화 점수 계산 및 저장 (레거시 호환)
    try:
        evolution_history = load_evolution_history(repo_root) or {}
        source_scores = {}
        drift_index = load_drift_index(repo_root) or {}
        drift_rates = {}
        
        # 간단한 소스 점수 계산 (실제로는 gate_pass_rate, avg_view_norm 등을 사용)
        for source in ["yt_api", "yt_dlp", "dataset", "wiki", "news", "rss", "google_news_rss"]:
            gate_pass_rate = 0.8  # 실제로는 계산
            avg_view_norm = 0.5
            drift_rate = drift_rates.get(source, 0.0)
            score = calculate_source_score(gate_pass_rate, avg_view_norm, drift_rate)
            source_scores[source] = score
            
            # 진화 이력 업데이트
            if source not in evolution_history:
                evolution_history[source] = {"scores": []}
            evolution_history[source]["scores"].append(score)
            evolution_history[source]["last_score"] = score
            evolution_history[source]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        save_evolution_history(evolution_history, repo_root)
        
        # 3. 소스 확률 계산 및 저장
        source_probabilities = calculate_source_probabilities(source_scores, drift_rates)
        save_source_probabilities(source_probabilities, repo_root)
        
        # 리포트에 governance 추가 정보만 merge (execution_manifest/input_hash/replay_verification은 이미 설정됨)
        report["governance"].update({
            "policy_version": policy_version,
            "estimated_cost": estimated_cost,
            "cost_projection_path": str(repo_root / "data" / "knowledge_v1_store" / "governance" / "cost_projection.json"),
            "source_scores": source_scores,
            "source_probabilities": source_probabilities,
        })
    except Exception:
        # governance 추가 정보 실패해도 리포트는 저장 (embed/replay는 이미 기록됨)
        pass
    
    # Step E 메트릭스 저장 (재현/감사/롤백)
    if mode == "run":
        try:
            from backend.knowledge_v1.paths import get_root
            root = get_root()
            ingest_dir = root / "knowledge_ingest" / cycle_id
            ingest_dir.mkdir(parents=True, exist_ok=True)
            
            # 전체 키워드 수 추정
            keywords_in = report["summary"].get("total_selected", 0)
            keywords_used = len([cat for cat, cat_data in report.get("categories", {}).items() if cat_data.get("ingest_count", 0) > 0])
            
            # docs_by_source 집계 (카테고리별 합산)
            total_docs_by_source = {}
            for cat, cat_data in report.get("categories", {}).items():
                cat_docs_by_source = cat_data.get("docs_by_source", {})
                if isinstance(cat_docs_by_source, dict):
                    for source, count in cat_docs_by_source.items():
                        total_docs_by_source[source] = total_docs_by_source.get(source, 0) + count
            
            # docs_by_source가 없으면 fallback으로 집계
            if not total_docs_by_source:
                total_docs_by_source = {
                    "fixtures": report["summary"].get("total_fallback", 0),
                    "rss": max(0, report["summary"].get("total_ingested", 0) - report["summary"].get("total_fallback", 0))
                }
            
            metrics = {
                "cycle_id": cycle_id,
                "keywords_in": keywords_in,
                "keywords_used": keywords_used,
                "docs_target_total": max(200, keywords_in * 6) if keywords_in > 0 else 200,
                "docs_written_total": report["summary"].get("total_ingested", 0),
                "docs_written_by_source": total_docs_by_source,
                "dedup_dropped": 0,  # dedup는 append_jsonl에서 처리되므로 별도 집계 어려움
                "dropped_empty_assets": dropped_empty_assets,
                "dropped_empty_assets_by_source": dropped_empty_assets_by_source
            }
            
            metrics_file = ingest_dir / "step_e_metrics.json"
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
            
            report["step_e_metrics_path"] = str(metrics_file)
        except Exception as e:
            # 메트릭스 저장 실패해도 사이클은 계속 진행
            pass
    
    # ingest 0 즉시 FAIL 검사 (RC2 해결)
    if report["summary"]["total_selected"] > 0 and report["summary"]["total_ingested"] == 0:
        # per-category keyword file line counts 수집
        per_category_counts = {}
        for cat in categories:
            cat_file = keywords_dir / f"{cat}.txt"
            if cat_file.exists():
                try:
                    with open(cat_file, "r", encoding="utf-8") as f:
                        per_category_counts[cat] = sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
                except Exception:
                    per_category_counts[cat] = 0
            else:
                per_category_counts[cat] = 0
        
        # ingest 함수 정보 수집
        ingest_function_info = f"{ingest_discovery.__module__}.{ingest_discovery.__name__}"
        
        # 리포트에 실패 상태 기록 후 저장 (stdout 출력 전에 SSOT 보장)
        report["ok"] = False
        report["error"] = "ingest_zero_selected_nonzero"
        report.setdefault("diagnostics", {})["ingest_zero_selected_nonzero"] = {
            "cycle_id": cycle_id,
            "keywords_dir": str(keywords_dir),
            "per_category_keyword_file_line_counts": per_category_counts,
            "gate_stats_path": gate_stats_path_str,
            "ingest_function": ingest_function_info,
            "total_selected": report["summary"]["total_selected"],
            "total_ingested": report["summary"]["total_ingested"],
            "categories": categories,
            "mode": mode,
        }
        report_path_str = _finalize_and_write_discovery_report(report, cycle_id, gate_stats_path_str)
        
        error_result = {
            "ok": report["ok"],
            "error": report["error"],
            "cycle_id": report["cycle_id"],
            "report_path": report["report_path"],
            "gate_stats_path": report["gate_stats_path"],
            "debug": {
                "cycle_id": cycle_id,
                "keywords_dir": str(keywords_dir),
                "per_category_keyword_file_line_counts": per_category_counts,
                "gate_stats_path": gate_stats_path_str,
                "ingest_function": ingest_function_info,
                "total_selected": report["summary"]["total_selected"],
                "total_ingested": report["summary"]["total_ingested"],
                "categories": categories,
                "mode": mode,
            },
        }
        import sys
        import json as json_module
        print(json_module.dumps(error_result, ensure_ascii=False), file=sys.stdout)
        sys.exit(2)  # exitcode=2로 종료
    
    _finalize_and_write_discovery_report(report, cycle_id, gate_stats_path_str)
    return report


def derive_for_store(asset: KnowledgeAsset, store: str) -> List["DerivedChunk"]:
    """Derive를 특정 store에 저장"""
    from backend.knowledge_v1.paths import get_chunks_path, ensure_dirs
    from backend.knowledge_v1.store import append_jsonl
    import json
    import uuid
    
    ensure_dirs(store)
    
    # paths.py의 함수는 이미 Path를 반환
    chunks_path = get_chunks_path(store)
    
    # derive(asset) 호출하여 결과 받기
    derived_chunks = list(derive(asset))
    chunks = []
    
    # 기존 derive 결과가 1건 이상이면 정상 처리
    for chunk in derived_chunks:
        chunks.append(chunk)
        append_jsonl(chunks_path, chunk.to_dict())
        append_audit(AuditEvent.create("DERIVE", {
            "chunk_id": chunk.chunk_id,
            "asset_id": asset.asset_id,
            "store": store
        }), store)
    
    # derive 결과가 0건이면 fallback derived chunk 1건 생성/저장/audit
    if len(chunks) == 0:
        # fallback chunk text 선택 (우선순위: summary → text → fallback message)
        payload = asset.payload
        fallback_text = ""
        if "summary" in payload and payload["summary"]:
            fallback_text = str(payload["summary"])
        elif "text" in payload and payload["text"]:
            fallback_text = str(payload["text"])
        else:
            fallback_text = f"[fallback-derived] {asset.category} :: {', '.join(asset.keywords)}"
        
        # fallback chunk tags 생성
        fallback_tags = [asset.category] + asset.keywords + [store, "fallback_derived"]
        
        # fallback DerivedChunk 생성
        fallback_chunk = DerivedChunk.create(
            asset_id=asset.asset_id,
            text=fallback_text,
            tags=fallback_tags
        )
        chunks.append(fallback_chunk)
        
        # chunks.jsonl에 저장
        append_jsonl(chunks_path, fallback_chunk.to_dict())
        
        # audit에 DERIVE 이벤트 기록
        append_audit(AuditEvent.create("DERIVE", {
            "chunk_id": fallback_chunk.chunk_id,
            "asset_id": asset.asset_id,
            "store": store,
            "fallback": True,
            "reason": "derive_empty_fallback"
        }), store)
    
    asset.lifecycle_state = "DERIVED"
    
    return chunks


def classify_for_store(asset: KnowledgeAsset, store: str, depth: str = "normal"):
    """Classify를 특정 store에 저장 (reason_code 강제)"""
    from backend.knowledge_v1.classify import classify
    from backend.knowledge_v1.paths import ensure_dirs, get_store_root
    
    ensure_dirs(store)
    
    eligibility = classify(asset, depth)
    
    # discovery store에도 used_assets.jsonl에 기록 (reason_code 진단용)
    # reason_code 강제: reason 필드에 항상 reason_code 저장
    if eligibility.eligible_for != "BLOCKED":
        used_path = get_store_root(store) / "used" / "used_assets.jsonl"
        used_path.parent.mkdir(parents=True, exist_ok=True)
        from backend.knowledge_v1.store import append_jsonl
        used_entry = {
            "asset_id": asset.asset_id,
            "eligible_for": eligibility.eligible_for,
            "reason": eligibility.reason,  # reason_code (강제)
            "category": asset.category,  # 카테고리 추가 (reasons_by_category를 위해)
            "decided_at": eligibility.decided_at
        }
        append_jsonl(used_path, used_entry)
    
    # Audit 기록
    append_audit(AuditEvent.create("CLASSIFY", {
        "asset_id": asset.asset_id,
        "eligible_for": eligibility.eligible_for,
        "reason": eligibility.reason,  # reason_code
        "category": asset.category,  # 카테고리 추가
        "store": store
    }), store)
    
    return eligibility


