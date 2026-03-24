"""
DETERMINISTIC REPLAY - 재현 가능한 실행 (replay_baselines.json SSOT)

- load_baselines(): 항상 baselines 맵(dict[input_hash]=entry) 반환. v2/items/v1 형식 지원.
- save_baselines(): v2 스키마로만 저장, 기존 파일은 .bak.<timestamp> 백업 후 원자 저장.
- baseline 없을 때만 baseline_created; baseline 있는데 baseline_created 나오면 error_baseline_lookup.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from backend.knowledge_v1 import paths as kv_paths

REPLAY_BASELINES_FILENAME = "replay_baselines.json"
SCHEMA_VERSION = 2


def _norm(h: Optional[str]) -> str:
    """해시 비교 시 대소문자/공백 차이 제거 (불필요 mismatch 방지)."""
    return (h or "").strip().lower()


def _sha256_file(path: Path) -> Optional[str]:
    """파일 SHA256 해시 반환. 없으면 None."""
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_run_fingerprints(
    repo_root: Path,
    reports_dir: Path,
    governance_dir: Path,
    latest_report_path: Optional[Path] = None,
) -> Dict[str, Optional[str]]:
    """
    최신 run의 대표 산출물 SHA256 계산.
    진입 시 모든 경로 인자를 Path로 강제 (str 연산 실패 방지).
    """
    repo_root = kv_paths.as_path(repo_root)
    reports_dir = kv_paths.as_path(reports_dir)
    governance_dir = kv_paths.as_path(governance_dir)
    if latest_report_path is not None:
        latest_report_path = kv_paths.as_path(latest_report_path)

    base = repo_root / "data" / "knowledge_v1_store"
    assets_path = base / "discovery" / "raw" / "assets.jsonl"
    chunks_path = base / "discovery" / "derived" / "chunks.jsonl"
    gate_stats_path = base / "reports" / "gate_stats.json"

    assets_sha256 = _sha256_file(assets_path)
    chunks_sha256 = _sha256_file(chunks_path)
    gate_stats_sha256 = _sha256_file(gate_stats_path)

    fingerprints = {
        "assets_sha256": assets_sha256,
        "chunks_sha256": chunks_sha256,
        "gate_stats_sha256": gate_stats_sha256,
    }
    if assets_sha256 is None and chunks_sha256 is None and gate_stats_sha256 is None:
        raise RuntimeError("REPLAY_FINGERPRINT_ALL_NONE")
    return fingerprints


def load_baselines(path: Path) -> Dict[str, Any]:
    """
    replay_baselines.json 로드. 반환값은 항상 baselines 맵(dict[input_hash]=entry).

    - 파일 없거나 파싱 실패 → {}
    - schema_version in data AND baselines in data AND isinstance(baselines, dict) → data["baselines"]
    - items in data AND isinstance(items, list) → items를 input_hash 키 dict로 변환하여 반환
    - 그 외(구 v1) → 최상위 키가 input_hash인 dict로 가정하고 data 그대로 반환
    """
    path = kv_paths.as_path(path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    if "schema_version" in data and "baselines" in data and isinstance(data.get("baselines"), dict):
        return data["baselines"]
    if "items" in data and isinstance(data["items"], list):
        out: Dict[str, Any] = {}
        for item in data["items"]:
            if isinstance(item, dict) and item.get("input_hash"):
                out[str(item["input_hash"])] = item
        return out
    return data


def save_baselines(path: Path, baselines_map: Dict[str, Any]) -> None:
    """
    replay_baselines.json을 v2 스키마로 저장. 기존 파일이 있으면 .bak.<timestamp> 백업 후 원자 저장.
    """
    path = kv_paths.as_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = {"schema_version": SCHEMA_VERSION, "baselines": baselines_map}
    if path.exists():
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(path.name + f".bak.{ts}")
        try:
            os.replace(str(path), str(backup))
        except OSError:
            try:
                import shutil
                shutil.copy2(path, backup)
                path.unlink()
            except Exception:
                pass
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{int(time.time() * 1000)}")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(str(tmp), str(path))
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


REPLAY_MISMATCH_DIFFS_DIR = "replay_mismatch_diffs"


def write_mismatch_diff(repo_root: Path, run_id: str, payload: Dict[str, Any]) -> Path:
    """
    mismatch diff SSOT 저장.
    -> data/knowledge_v1_store/governance/replay_mismatch_diffs/replay_mismatch_<run_id>.json
    """
    repo_root = kv_paths.as_path(repo_root)
    root = repo_root / "data" / "knowledge_v1_store" / "governance" / REPLAY_MISMATCH_DIFFS_DIR
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"replay_mismatch_{run_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _get_baseline_fingerprints_for_compare(entry: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
    """baseline 엔트리에서 비교용 fingerprint 맵 추출. canonical 우선, 없으면 raw."""
    if not isinstance(entry, dict):
        return None
    fp = entry.get("fingerprints")
    if isinstance(fp, dict):
        canonical_keys = [
            "assets_canonical_sha256",
            "chunks_canonical_sha256",
            "gate_stats_canonical_sha256",
        ]
        if any(fp.get(k) for k in canonical_keys):
            return {k: fp.get(k) for k in canonical_keys}
    raw_keys = ["assets_sha256", "chunks_sha256", "gate_stats_sha256"]
    if any(entry.get(k) for k in raw_keys):
        return {k: entry.get(k) for k in raw_keys}
    return None


def _get_current_fingerprints_for_compare(
    current: Dict[str, Any],
    preferred_keys: Optional[set] = None,
) -> Optional[Dict[str, Optional[str]]]:
    """리포트 등에서 가져온 current에서 비교용 fingerprint 맵 추출.
    preferred_keys가 있으면 baseline과 동일 종류(canonical vs raw)를 선택해 비교 가능하게 함."""
    if not isinstance(current, dict):
        return None
    canonical_keys = ("assets_canonical_sha256", "chunks_canonical_sha256", "gate_stats_canonical_sha256")
    raw_keys = ("assets_sha256", "chunks_sha256", "gate_stats_sha256")
    use_canonical = preferred_keys is None or (preferred_keys & set(canonical_keys))
    use_raw = preferred_keys is None or (preferred_keys & set(raw_keys))
    canonical = current.get("canonical") if isinstance(current.get("canonical"), dict) else None
    raw = current.get("raw") if isinstance(current.get("raw"), dict) else current
    if not isinstance(raw, dict):
        raw = current
    if use_canonical and canonical and any(canonical.get(k) for k in canonical_keys):
        return {
            "assets_canonical_sha256": canonical.get("assets_canonical_sha256"),
            "chunks_canonical_sha256": canonical.get("chunks_canonical_sha256"),
            "gate_stats_canonical_sha256": canonical.get("gate_stats_canonical_sha256"),
        }
    if use_raw and isinstance(raw, dict) and any(raw.get(k) for k in raw_keys):
        return {
            "assets_sha256": raw.get("assets_sha256"),
            "chunks_sha256": raw.get("chunks_sha256"),
            "gate_stats_sha256": raw.get("gate_stats_sha256"),
        }
    return None


def verify_deterministic_output(
    baselines_map: Dict[str, Any],
    input_hash: str,
    current_fingerprints: Dict[str, Any],
    run_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    baseline 맵과 현재 fingerprint로 match/mismatch/baseline_created/error_baseline_lookup 판정.

    - baseline이 없을 때만 baseline_created 허용.
    - baseline이 있는데 비교 불가(엔트리 구조 문제)면 error_baseline_lookup.

    Returns:
        (verified, reason, diff_payload_or_None)
        reason in {"baseline_created", "match", "mismatch", "error_baseline_lookup"}
    """
    run_id = run_id or "unknown"
    if input_hash not in baselines_map:
        return True, "baseline_created", None

    entry = baselines_map[input_hash]
    baseline_fp = _get_baseline_fingerprints_for_compare(entry)
    current_fp = _get_current_fingerprints_for_compare(
        current_fingerprints,
        preferred_keys=set(baseline_fp.keys()) if baseline_fp else None,
    )
    if baseline_fp is None:
        diff = {
            "input_hash": input_hash,
            "run_id": run_id,
            "reason": "error_baseline_lookup",
            "diagnostic": "baseline entry has no comparable fingerprints (missing fingerprints or raw keys)",
            "baseline_keys": list(entry.keys()) if isinstance(entry, dict) else [],
        }
        return False, "error_baseline_lookup", diff
    if current_fp is None:
        diff = {
            "input_hash": input_hash,
            "run_id": run_id,
            "reason": "error_baseline_lookup",
            "diagnostic": "current_fingerprints has no comparable fingerprints (missing canonical/raw)",
            "current_keys": list(current_fingerprints.keys()) if isinstance(current_fingerprints, dict) else [],
        }
        return False, "error_baseline_lookup", diff

    keys_baseline = set(baseline_fp.keys())
    keys_current = set(current_fp.keys())
    comparable = list(keys_baseline & keys_current)
    if not comparable:
        diff = {
            "input_hash": input_hash,
            "run_id": run_id,
            "reason": "error_baseline_lookup",
            "diagnostic": "no common fingerprint keys between baseline and current",
            "baseline_keys": list(keys_baseline),
            "current_keys": list(keys_current),
        }
        return False, "error_baseline_lookup", diff

    all_match = True
    diff_keys: List[str] = []
    diff_pairs: Dict[str, Dict[str, str]] = {}
    for key in comparable:
        a = current_fp.get(key)
        b = baseline_fp.get(key)
        if a is not None and b is not None and _norm(a) != _norm(b):
            all_match = False
            diff_keys.append(key)
            diff_pairs[key] = {"baseline": (b or ""), "current": (a or "")}
    if all_match:
        return True, "match", None
    diff_payload = {
        "input_hash": input_hash,
        "run_id": run_id,
        "baseline": {k: baseline_fp.get(k) for k in comparable},
        "current": {k: current_fp.get(k) for k in comparable},
        "diff_keys": diff_keys,
        "diff_pairs": diff_pairs,
    }
    return False, "mismatch", diff_payload


def verify_or_create_baseline(
    input_hash: str,
    fingerprints: Dict[str, Optional[str]],
    baselines: Dict[str, Any],
    run_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    input_hash에 대한 baseline 없으면 생성(PASS), 있으면 비교.
    해시 비교는 _norm() 기준 (대소문자 정규화).
    load_baselines()로 얻은 baselines 맵을 넣어야 v2와 일치하게 동작.

    Returns:
        (verified, reason, updated_baselines, diff_payload_or_None)
        reason in {"baseline_created", "match", "mismatch"}
        mismatch 시 diff_payload 반환 (SSOT 저장용).
    """
    now = created_at or datetime.utcnow().isoformat() + "Z"
    run_id = run_id or "unknown"
    comparable_keys = ["assets_sha256", "chunks_sha256", "gate_stats_sha256"]

    if input_hash not in baselines:
        baselines[input_hash] = {
            **{k: v for k, v in fingerprints.items() if v is not None},
            "created_at": now,
            "run_id": run_id,
        }
        return True, "baseline_created", baselines, None

    baseline = baselines[input_hash]
    all_match = True
    diff_keys: List[str] = []
    diff_pairs: Dict[str, Dict[str, str]] = {}
    for key in comparable_keys:
        a = fingerprints.get(key)
        b = baseline.get(key)
        if a is not None and b is not None and _norm(a) != _norm(b):
            all_match = False
            diff_keys.append(key)
            diff_pairs[key] = {"baseline": (b or ""), "current": (a or "")}
    if all_match:
        return True, "match", baselines, None
    diff_payload = {
        "input_hash": input_hash,
        "run_id": run_id,
        "baseline": {k: baseline.get(k) for k in comparable_keys},
        "current": {k: fingerprints.get(k) for k in comparable_keys},
        "diff_keys": diff_keys,
        "diff_pairs": diff_pairs,
    }
    return False, "mismatch", baselines, diff_payload


def verify_replay_consistency(
    manifest: Dict[str, Any],
    assets_path: Path,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Replay 일관성 검증 (레거시 호환).

    Args:
        manifest: execution manifest
        assets_path: assets.jsonl 경로

    Returns:
        Tuple[bool, str, Dict]: (일관성 여부, 메시지, 상세 정보)
    """
    assets_path = kv_paths.as_path(assets_path)
    if not assets_path.exists():
        return False, "assets.jsonl not found", {}

    actual_hash = _sha256_file(assets_path) or ""
    expected_hash = manifest.get("assets_hash")

    if expected_hash is None:
        return True, "first_run", {"actual_hash": actual_hash}
    if actual_hash == expected_hash:
        return True, "replay_match", {
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
        }
    return False, "replay_mismatch", {
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
    }
