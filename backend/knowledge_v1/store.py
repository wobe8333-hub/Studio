"""
Knowledge v1 Store - 파일시스템 기반 저장소 유틸
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Literal


def get_store_root(layer) -> Path:
    """
    레이어별 저장소 루트 경로 반환 (하위 호환성 유지)
    
    Deprecated: paths.get_store_root()를 사용하세요.
    """
    from backend.knowledge_v1.layers import Layer
    from backend.knowledge_v1.paths import get_store_root as paths_get_store_root
    
    # Layer enum을 Store literal로 변환
    if layer == Layer.APPROVED:
        return paths_get_store_root("approved")
    elif layer == Layer.DISCOVERY:
        return paths_get_store_root("discovery")
    else:
        raise ValueError(f"Unknown layer: {layer}")


def get_knowledge_root() -> Path:
    """지식 저장소 루트 경로 반환 (Approved Layer) - paths.py 기반"""
    from backend.knowledge_v1.paths import get_store_root
    return get_store_root("approved")


def ensure_dir(path: Path) -> None:
    """디렉토리 생성 (exist_ok=True)"""
    path.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """JSONL 파일에 append (한 줄 = 한 오브젝트) - Path API 사용"""
    # Path API로 부모 디렉토리 생성
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        # 파일 쓰기 실패는 재발생 (호출자가 audit에 기록)
        raise


def atomic_write_json(path: Path, obj: Dict[str, Any], sort_keys: bool = False) -> None:
    """JSON 파일을 atomic write (임시파일→rename). sort_keys=True 시 결정론적 출력."""
    import os, json, time, random, shutil
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 고유 tmp 파일명(동시 실행/백신 스캔 충돌 완화)
    tmp_path = path.with_name(path.name + f".tmp.{os.getpid()}.{int(time.time()*1000)}.{random.randint(1000,9999)}")

    # 1) tmp로 완전 기록 + fsync
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=sort_keys)
        f.flush()
        os.fsync(f.fileno())

    # 2) 원자적 replace 재시도 (WinError 5 대비)
    last_err = None
    for i in range(8):
        try:
            os.replace(str(tmp_path), str(path))
            last_err = None
            break
        except PermissionError as e:
            last_err = e
            # 지수 백오프 + 지터 (총 ~1.5~2초 내)
            time.sleep((0.03 * (2 ** i)) + random.uniform(0.0, 0.02))
        except OSError as e:
            last_err = e
            time.sleep((0.03 * (2 ** i)) + random.uniform(0.0, 0.02))

    # 3) 최종 fallback: move (replace가 계속 실패할 때)
    if last_err is not None:
        try:
            # 대상이 잠겨있어 replace 실패한 경우를 대비
            shutil.move(str(tmp_path), str(path))
            last_err = None
        except Exception:
            # tmp 정리 시도 후 원래 에러를 다시 올림
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise last_err

    # 4) tmp 잔재 정리(정상 replace면 이미 없지만, move 등 예외 케이스 대비)
    try:
        if tmp_path.exists():
            tmp_path.unlink()
    except Exception:
        pass


def load_jsonl(path: Path) -> Generator[Dict[str, Any], None, None]:
    """
    JSONL 파일을 한 줄씩 로드 (깨진 줄 자동 복구)
    
    깨진 줄은 <원본파일명>.corrupt.jsonl에 저장하고 skip하여 계속 진행합니다.
    """
    if not path.exists():
        return
    
    corrupt_count = 0
    corrupt_path = path.parent / f"{path.stem}.corrupt.jsonl"
    corrupt_meta_path = path.parent / f"{path.stem}.corrupt.meta.json"
    last_broken_line_num = 0
    last_error_msg = ""
    
    with open(path, "r", encoding="utf-8") as f:
        line_num = 0
        for line in f:
            line_num += 1
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            try:
                yield json.loads(line_stripped)
            except (json.JSONDecodeError, ValueError) as e:
                # 깨진 줄을 corrupt 파일에 저장
                corrupt_count += 1
                last_broken_line_num = line_num
                last_error_msg = f"{type(e).__name__}: {str(e)[:200]}"
                
                try:
                    # corrupt.jsonl에 원문 그대로 append
                    with open(corrupt_path, "a", encoding="utf-8") as cf:
                        cf.write(line)  # 원문 그대로 (strip하지 않음)
                    
                    # corrupt.meta.json 업데이트
                    meta = {
                        "corrupt_count": corrupt_count,
                        "last_broken_line_num": last_broken_line_num,
                        "last_error": last_error_msg,
                        "source_file": str(path),
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    }
                    with open(corrupt_meta_path, "w", encoding="utf-8") as mf:
                        json.dump(meta, mf, ensure_ascii=False, indent=2)
                except Exception:
                    # corrupt 파일 저장 실패해도 계속 진행
                    pass
                
                # 깨진 줄은 skip하고 다음 줄 계속 처리
                continue
    
    # corrupt_count가 1 이상이면 warning 로그 출력 (throw 금지)
    if corrupt_count > 0:
        import sys
        print(f"WARNING: {corrupt_count} corrupted line(s) skipped in {path.name} (saved to {corrupt_path.name})", file=sys.stderr)


def compute_raw_hash(payload: Dict[str, Any]) -> str:
    """payload의 sha256 해시 계산"""
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


def load_scheduler_state() -> Dict[str, Any]:
    """스케줄러 상태 로드"""
    from backend.knowledge_v1.paths import get_store_root
    state_path = get_store_root("approved") / "scheduler" / "state.json"
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "last_run_date": None,
        "target_time": "17:00",
        "last_run_status": None
    }


def save_scheduler_state(state: Dict[str, Any]) -> None:
    """스케줄러 상태 저장 (atomic write)"""
    from backend.knowledge_v1.paths import get_store_root
    state_path = get_store_root("approved") / "scheduler" / "state.json"
    atomic_write_json(state_path, state)


# v7.3: Store 기반 함수들 (discovery/approved 분리)
Store = Literal["discovery", "approved"]


def get_existing_raw_hashes(store: Store) -> set[str]:
    """
    Store에 이미 존재하는 raw_hash 집합 반환
    
    Args:
        store: "discovery" | "approved"
    
    Returns:
        set[str]: raw_hash 집합
    """
    from backend.knowledge_v1.paths import get_assets_path
    
    hashes = set()
    assets_path = get_assets_path(store)  # 이미 Path 반환
    if assets_path.exists():
        for asset in load_jsonl(assets_path):
            raw_hash = asset.get("raw_hash", "")
            if raw_hash:
                hashes.add(raw_hash)
    return hashes


def append_asset(asset: Any, store: Store, skip_duplicate: bool = True) -> bool:
    """
    Asset을 Store에 추가 (raw_hash 중복 방지)
    
    Args:
        asset: KnowledgeAsset 인스턴스 또는 dict
        store: "discovery" | "approved"
        skip_duplicate: 중복 시 스킵 여부
    
    Returns:
        bool: 추가 성공 여부 (중복이면 False)
    """
    from backend.knowledge_v1.paths import get_assets_path, ensure_dirs
    
    # dict 변환
    if hasattr(asset, 'to_dict'):
        asset_dict = asset.to_dict()
    else:
        asset_dict = asset
    
    # raw_hash 확인
    raw_hash = asset_dict.get("raw_hash", "")
    if not raw_hash:
        # raw_hash가 없으면 계산
        payload = asset_dict.get("payload", {})
        raw_hash = compute_raw_hash(payload)
        asset_dict["raw_hash"] = raw_hash
    
    # 중복 확인
    if skip_duplicate:
        existing_hashes = get_existing_raw_hashes(store)
        if raw_hash in existing_hashes:
            return False  # 중복, 스킵
    
    # 추가
    assets_path = get_assets_path(store)  # 이미 Path 반환
    ensure_dirs(store)
    append_jsonl(assets_path, asset_dict)
    return True


def append_chunk(chunk: Any, store: Store) -> None:
    """
    Chunk를 Store에 추가
    
    Args:
        chunk: DerivedChunk 인스턴스 또는 dict
        store: "discovery" | "approved"
    """
    from backend.knowledge_v1.paths import get_chunks_path, ensure_dirs
    
    # dict 변환
    if hasattr(chunk, 'to_dict'):
        chunk_dict = chunk.to_dict()
    else:
        chunk_dict = chunk
    
    chunks_path = get_chunks_path(store)  # 이미 Path 반환
    ensure_dirs(store)
    append_jsonl(chunks_path, chunk_dict)


def append_audit(event: Any, store: Store) -> None:
    """
    Audit 이벤트를 Store에 추가
    
    Args:
        event: AuditEvent 인스턴스 또는 dict
        store: "discovery" | "approved"
    """
    from backend.knowledge_v1.paths import get_audit_path, ensure_dirs
    
    # dict 변환
    if hasattr(event, 'to_dict'):
        event_dict = event.to_dict()
    else:
        event_dict = event
    
    audit_path = get_audit_path(store)  # 이미 Path 반환
    ensure_dirs(store)
    append_jsonl(audit_path, event_dict)


def normalize_chunks_jsonl_for_replay(chunks_path: Path) -> Dict[str, int]:
    """
    chunks.jsonl dedupe + 결정론 직렬화 (replay fingerprint 안정화).
    - 비결정 필드 제거: generated_at, created_at, timestamp, updated_at
    - chunk_id = (asset_id|text) SHA256 16자 고정
    - chunk_id 기준 dedupe (첫 번째 1건만 유지)
    - 정렬: (asset_id, text, chunk_id), 라인별 직렬화: sort_keys=True
    Returns:
        {"before": N, "after": M, "deduped": N-M}
    """
    path = Path(chunks_path)
    if not path.exists():
        return {"before": 0, "after": 0, "deduped": 0}
    lines: list = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for key in list(obj.keys()):
                if key in ("generated_at", "created_at", "timestamp", "updated_at"):
                    obj.pop(key, None)
            aid, txt = obj.get("asset_id", ""), obj.get("text", "")
            obj["chunk_id"] = hashlib.sha256(f"{aid}|{txt}".encode("utf-8")).hexdigest()[:16]
            lines.append(obj)
    before = len(lines)
    unique_by_chunk_id: Dict[str, Dict[str, Any]] = {}
    for r in lines:
        cid = r.get("chunk_id", "")
        if cid not in unique_by_chunk_id:
            unique_by_chunk_id[cid] = r
    records = list(unique_by_chunk_id.values())
    records.sort(key=lambda r: (r.get("asset_id", ""), r.get("text", ""), r.get("chunk_id", "")))
    after = len(records)
    tmp = path.with_suffix(path.suffix + ".tmp.replay")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)
    if tmp.exists():
        try:
            tmp.unlink()
        except Exception:
            pass
    return {"before": before, "after": after, "deduped": before - after}

