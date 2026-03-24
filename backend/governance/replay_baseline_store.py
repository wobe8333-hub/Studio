"""
Replay Baseline Store - replay_baselines.json v2 스키마 SSOT

스키마(v2):
{
  "schema_version": 2,
  "baselines": {
    "<input_hash>": {
      "input_hash": "<...>",
      "run_id": "<...>",
      "policy_version": "<...>",
      "api_snapshot_hash": "<...>",
      "fingerprints": {
        "assets_canonical_sha256": "<...>",
        "chunks_canonical_sha256": "<...>",
        "gate_stats_canonical_sha256": "<...>"
      },
      "created_at": "<iso>",
      // (선택) raw fingerprints, counts 등 디버그용 필드 허용
    }
  }
}
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.knowledge_v1 import paths as kv_paths
from backend.knowledge_v1.store import atomic_write_json

REPLAY_BASELINES_FILENAME = "replay_baselines.json"
SCHEMA_VERSION = 2


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_replay_baselines_path(repo_root: Path) -> Path:
    """
    repo_root 기준 replay_baselines.json 경로 (SSOT).
    """
    repo_root = kv_paths.as_path(repo_root)
    governance_dir = kv_paths.ensure_governance_dir(repo_root)
    return governance_dir / REPLAY_BASELINES_FILENAME


def _backup_file(path: Path) -> None:
    """
    원본 파일 원자적 보존용 백업.
    replay_baselines.json.bak.<timestamp> 이름으로 같은 폴더에 저장.
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(path.name + f".bak.{ts}")
    try:
        shutil.copy2(path, backup_path)
    except Exception:
        # 백업 실패해도 본 파일은 건드리지 않음
        pass


def _normalize_v1_entry(input_hash: str, payload: Dict[str, Any], now: str) -> Dict[str, Any]:
    """
    v1 엔트리를 v2 엔트리로 승격.
    """
    run_id = payload.get("run_id") or "unknown"
    created_at = payload.get("created_at") or now
    policy_version = payload.get("policy_version") or "unknown"
    api_snapshot_hash = payload.get("api_snapshot_hash") or "unknown"

    entry: Dict[str, Any] = {
        "input_hash": input_hash,
        "run_id": run_id,
        "policy_version": policy_version,
        "api_snapshot_hash": api_snapshot_hash,
        "fingerprints": {
            # 기존 v1에는 없으므로 우선 None, 이후 첫 canonical 측정 시 채워짐
            "assets_canonical_sha256": payload.get("assets_canonical_sha256"),
            "chunks_canonical_sha256": payload.get("chunks_canonical_sha256"),
            "gate_stats_canonical_sha256": payload.get("gate_stats_canonical_sha256"),
        },
        "created_at": created_at,
    }

    # raw SHA는 디버그용으로 보존
    for key in ("assets_sha256", "chunks_sha256", "gate_stats_sha256"):
        if key in payload:
            entry[key] = payload[key]

    return entry


def _upgrade_to_v2(data: Any) -> Tuple[Dict[str, Any], bool]:
    """
    임의의 JSON을 v2 스키마로 승격.

    Returns:
        (v2_obj, changed_flag)
    """
    now = _now_iso()

    # 이미 v2 형식
    if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION and isinstance(
        data.get("baselines"), dict
    ):
        return data, False

    # items(list) 형식 → baselines로 변환
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        baselines: Dict[str, Any] = {}
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            ih = item.get("input_hash")
            if not ih:
                continue
            baselines[ih] = _normalize_v1_entry(str(ih), item, now)
        return {"schema_version": SCHEMA_VERSION, "baselines": baselines}, True

    # 최상위 dict의 키가 input_hash 들인 현재(v1) 형식
    if isinstance(data, dict):
        # schema_version, baselines, items 가 없으면 v1 dict 로 간주
        special_keys = {"schema_version", "baselines", "items"}
        if not (set(data.keys()) & special_keys):
            baselines: Dict[str, Any] = {}
            for ih, payload in data.items():
                if not isinstance(payload, dict):
                    continue
                baselines[str(ih)] = _normalize_v1_entry(str(ih), payload, now)
            return {"schema_version": SCHEMA_VERSION, "baselines": baselines}, True

    # 알 수 없는 형식 → 빈 v2 객체
    return {"schema_version": SCHEMA_VERSION, "baselines": {}}, True


def load_replay_baselines(path: Path) -> Dict[str, Any]:
    """
    replay_baselines.json 로드 + v2 스키마 보장.

    - 파일이 없으면 빈 v2 객체 반환 (저장은 호출자가 필요 시 수행).
    - v1(dict/items) 형식이면 v2로 승격 후 즉시 저장.
    - 파싱 실패 시 원본 백업 후 빈 v2로 재시작.
    """
    path = kv_paths.as_path(path)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "baselines": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        _backup_file(path)
        return {"schema_version": SCHEMA_VERSION, "baselines": {}}

    v2_obj, changed = _upgrade_to_v2(raw)
    if changed:
        _backup_file(path)
        atomic_write_json(path, v2_obj, sort_keys=True)
    return v2_obj


def save_replay_baselines(path: Path, obj: Dict[str, Any]) -> None:
    """
    v2 스키마 객체 저장. schema_version/baselines 필드를 강제.
    """
    path = kv_paths.as_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    schema_version = obj.get("schema_version") or SCHEMA_VERSION
    baselines = obj.get("baselines") or {}
    v2_obj = {
        "schema_version": schema_version,
        "baselines": baselines,
    }
    atomic_write_json(path, v2_obj, sort_keys=True)


def get_baseline_entry(root: Dict[str, Any], input_hash: str) -> Optional[Dict[str, Any]]:
    """
    v2 루트 객체에서 특정 input_hash baseline 엔트리 조회.
    """
    baselines = root.get("baselines") or {}
    entry = baselines.get(input_hash)
    return entry if isinstance(entry, dict) else None


def verify_or_update_canonical_baseline(
    root: Dict[str, Any],
    *,
    input_hash: str,
    run_id: str,
    policy_version: str,
    api_snapshot_hash: str,
    canonical_fingerprints: Dict[str, Optional[str]],
    raw_fingerprints: Optional[Dict[str, Optional[str]]] = None,
    counts: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    canonical 3종 SHA 기반 baseline 검증/업데이트.

    Returns:
        (verified, reason, updated_root, diff_payload_or_None)
        - verified: True → PASS (baseline_created 포함), False → canonical mismatch
        - reason ∈ {"baseline_created", "match", "mismatch"}
    """
    if "schema_version" not in root or "baselines" not in root:
        root.setdefault("schema_version", SCHEMA_VERSION)
        root.setdefault("baselines", {})

    baselines: Dict[str, Any] = root["baselines"]
    now = created_at or _now_iso()

    def _norm(h: Optional[str]) -> str:
        return (h or "").strip().lower()

    canonical_keys = [
        "assets_canonical_sha256",
        "chunks_canonical_sha256",
        "gate_stats_canonical_sha256",
    ]

    current_fp = {k: canonical_fingerprints.get(k) for k in canonical_keys}

    existing = baselines.get(input_hash)
    if not isinstance(existing, dict):
        # baseline 없음 → 생성
        baselines[input_hash] = {
            "input_hash": input_hash,
            "run_id": run_id,
            "policy_version": policy_version,
            "api_snapshot_hash": api_snapshot_hash,
            "fingerprints": current_fp,
            "created_at": now,
        }
        if raw_fingerprints:
            baselines[input_hash]["raw_fingerprints"] = {
                k: v for k, v in raw_fingerprints.items() if v is not None
            }
        if counts:
            baselines[input_hash]["counts"] = counts
        return True, "baseline_created", root, None

    # 정책/스냅샷 해시 변경 시에는 새로운 baseline으로 간주 (기존 엔트리 덮어쓰기)
    if (
        existing.get("policy_version") != policy_version
        or existing.get("api_snapshot_hash") != api_snapshot_hash
    ):
        baselines[input_hash] = {
            "input_hash": input_hash,
            "run_id": run_id,
            "policy_version": policy_version,
            "api_snapshot_hash": api_snapshot_hash,
            "fingerprints": current_fp,
            "created_at": now,
        }
        if raw_fingerprints:
            baselines[input_hash]["raw_fingerprints"] = {
                k: v for k, v in raw_fingerprints.items() if v is not None
            }
        if counts:
            baselines[input_hash]["counts"] = counts
        return True, "baseline_created", root, None

    baseline_fp = (existing.get("fingerprints") or {}) if isinstance(existing, dict) else {}

    # canonical 필드가 비어 있으면 첫 canonical 기준으로 baseline 재설정
    if any(baseline_fp.get(k) is None for k in canonical_keys):
        existing.update(
            {
                "run_id": run_id,
                "policy_version": policy_version,
                "api_snapshot_hash": api_snapshot_hash,
                "fingerprints": current_fp,
                "created_at": existing.get("created_at") or now,
            }
        )
        if raw_fingerprints:
            existing["raw_fingerprints"] = {
                k: v for k, v in raw_fingerprints.items() if v is not None
            }
        if counts:
            existing["counts"] = counts
        baselines[input_hash] = existing
        return True, "baseline_created", root, None

    # canonical 비교
    changed_keys: List[str] = []
    for k in canonical_keys:
        b = _norm(baseline_fp.get(k))
        c = _norm(current_fp.get(k))
        if b != c:
            changed_keys.append(k)

    if not changed_keys:
        # match 시에도 최신 run_id/counts 업데이트 (디버그 가독성)
        existing["run_id"] = run_id
        if counts:
            existing["counts"] = counts
        baselines[input_hash] = existing
        return True, "match", root, None

    # mismatch diff payload 구성 (E 조건 충족)
    baseline_policy = existing.get("policy_version")
    baseline_api_hash = existing.get("api_snapshot_hash")
    baseline_counts = existing.get("counts") or {}

    diff_canonical = {
        key: {
            "baseline": baseline_fp.get(key),
            "current": current_fp.get(key),
        }
        for key in changed_keys
    }

    first_n_changed_keys = changed_keys[:3]

    diff_payload: Dict[str, Any] = {
        "input_hash": input_hash,
        "run_id": run_id,
        "baseline": {
            "policy_version": baseline_policy,
            "api_snapshot_hash": baseline_api_hash,
            "fingerprints": {
                k: baseline_fp.get(k) for k in canonical_keys
            },
            "raw_fingerprints": existing.get("raw_fingerprints") or {
                # 레거시 호환: v1 필드 보존된 경우 매핑
                "assets_sha256": existing.get("assets_sha256"),
                "chunks_sha256": existing.get("chunks_sha256"),
                "gate_stats_sha256": existing.get("gate_stats_sha256"),
            },
        },
        "current": {
            "policy_version": policy_version,
            "api_snapshot_hash": api_snapshot_hash,
            "fingerprints": current_fp,
            "raw_fingerprints": raw_fingerprints or {},
        },
        "counts": {
            "baseline": {
                "assets_lines": baseline_counts.get("assets_lines"),
                "chunks_lines": baseline_counts.get("chunks_lines"),
            },
            "current": {
                "assets_lines": (counts or {}).get("assets_lines") if counts else None,
                "chunks_lines": (counts or {}).get("chunks_lines") if counts else None,
            },
        },
        "changed_canonical_keys": changed_keys,
        "first_n_changed_keys": first_n_changed_keys,
        "diff_canonical": diff_canonical,
    }

    return False, "mismatch", root, diff_payload

