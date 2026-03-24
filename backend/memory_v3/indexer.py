"""
MemorySnapshotV3 의미 인덱싱 로직

v3-Step3: v3-Step2 정규화 산출물로부터 의미 인덱싱 결과 생성
- Reference-only 인덱스
- 추천/선택/판단/상태전이 금지
- 관측된 의미를 구조화만 수행
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_question_seeds(patterns_tags: Dict[str, Any]) -> Tuple[list, Optional[str]]:
    """
    question_seeds.json 생성

    Args:
        patterns_tags: patterns_tags.json 데이터

    Returns:
        Tuple[list, Optional[str]]: (question_seeds, warning_message)
    """
    # patterns_tags.questions_seed를 source of truth로 사용
    # 최우선: "questions_seed", 호환용: "questions_seeds"
    questions_seed_candidates = patterns_tags.get("questions_seed")
    if questions_seed_candidates is None:
        questions_seed_candidates = patterns_tags.get("questions_seeds", [])

    # candidates가 list가 아니면 []로 처리
    if not isinstance(questions_seed_candidates, list):
        warning = f"QUESTIONS_SEED_MISSING_OR_INVALID: patterns_tags.questions_seed is not a list (type: {type(questions_seed_candidates).__name__})"
        return [], warning

    # 빈 리스트면 그대로 반환
    if len(questions_seed_candidates) == 0:
        return [], None

    # 각 원소를 정규화 (스키마 강제: {kind,text,source,confidence_hint})
    normalized_seeds = []
    for item in questions_seed_candidates:
        # dict가 아닌 원소는 버림 (추측 금지)
        if not isinstance(item, dict):
            continue

        # 정확히 4키만 가진 dict인지 확인
        required_keys = {"kind", "text", "source", "confidence_hint"}
        if set(item.keys()) != required_keys:
            continue  # 추가키가 있거나 필수키가 없으면 해당 seed는 버림

        # text가 빈 문자열/공백이면 버림 (추측 금지)
        if not isinstance(item.get("text"), str) or len(item["text"].strip()) == 0:
            continue

        # 통과한 seed는 그대로 복사 (필드 매핑/보정/기본값 삽입 금지)
        normalized_seeds.append({
            "kind": item["kind"],
            "text": item["text"],
            "source": item["source"],
            "confidence_hint": item["confidence_hint"]
        })

    if not normalized_seeds and questions_seed_candidates:
        return [], "QUESTION_SEEDS_EMPTY (reference-only): All candidates filtered out."
    
    return normalized_seeds, None


def build_semantic_tags(patterns_tags: Dict[str, Any]) -> Dict[str, Any]:
    """
    semantic_tags.json 생성

    Args:
        patterns_tags: patterns_tags.json 데이터

    Returns:
        Dict: semantic_tags 데이터
    """
    tags = patterns_tags.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    
    # 정렬만 허용 (재작성/합성/요약 금지)
    tags_sorted = sorted(tags) if isinstance(tags, list) else []
    
    return {
        "tags": tags_sorted,
        "source": "patterns_tags",
        "reference_only": True
    }


def build_failure_taxonomy(patterns_verify: Dict[str, Any]) -> Dict[str, Any]:
    """
    failure_taxonomy.json 생성

    Args:
        patterns_verify: patterns_verify.json 데이터

    Returns:
        Dict: failure_taxonomy 데이터
    """
    return {
        "pass_fail": patterns_verify.get("pass_fail", False),
        "failure_taxonomy": patterns_verify.get("failure_taxonomy", []),
        "secondary_tags": patterns_verify.get("secondary_tags", []),
        "valuable_failure": patterns_verify.get("valuable_failure", False),
        "valuable_reason": patterns_verify.get("valuable_reason"),
        "reference_only": True
    }


def build_signal_index(patterns_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    signal_index.json 생성

    Args:
        patterns_metrics: patterns_metrics.json 데이터

    Returns:
        Dict: signal_index 데이터
    """
    signals = {}
    for key, value in patterns_metrics.items():
        if key != "status":  # status 필드는 제외
            signals[key] = value
    
    return {
        "signals": signals,
        "source": "patterns_metrics",
        "reference_only": True
    }


def build_index(run_id: str, input_dir: Path, output_dir: Path) -> Optional[str]:
    """
    v3-Step3 의미 인덱싱 실행

    Args:
        run_id: 실행 ID
        input_dir: Step2 정규화 입력 디렉토리 (normalized/<run_id>/)
        output_dir: Step3 출력 디렉토리 (indexed/<run_id>/)

    Returns:
        Optional[str]: error_message (성공 시 None)
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 필수 입력 파일 확인
    required_files = [
        "snapshot_raw.json",
        "snapshot_meta.json",
        "patterns_structure.json",
        "patterns_verify.json",
        "patterns_metrics.json",
        "patterns_tags.json",
        "index.json"
    ]
    
    for filename in required_files:
        filepath = input_dir / filename
        if not filepath.exists():
            return f"Required input file not found: {filepath.resolve()}"

    # 입력 파일 로드
    try:
        with open(input_dir / "patterns_tags.json", "r", encoding="utf-8") as f:
            patterns_tags = json.load(f)
    except Exception as e:
        return f"Failed to load patterns_tags.json: {str(e)}"

    try:
        with open(input_dir / "patterns_verify.json", "r", encoding="utf-8") as f:
            patterns_verify = json.load(f)
    except Exception as e:
        return f"Failed to load patterns_verify.json: {str(e)}"

    try:
        with open(input_dir / "patterns_metrics.json", "r", encoding="utf-8") as f:
            patterns_metrics = json.load(f)
    except Exception as e:
        return f"Failed to load patterns_metrics.json: {str(e)}"

    # 1) semantic_tags.json 생성
    try:
        semantic_tags = build_semantic_tags(patterns_tags)
        semantic_tags_path = output_dir / "semantic_tags.json"
        with open(semantic_tags_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(semantic_tags, f, ensure_ascii=False, indent=2)
        print("SEMANTIC_TAGS_WRITTEN")
    except Exception as e:
        return f"Failed to create semantic_tags.json: {str(e)}"

    # 2) failure_taxonomy.json 생성
    try:
        failure_taxonomy = build_failure_taxonomy(patterns_verify)
        failure_taxonomy_path = output_dir / "failure_taxonomy.json"
        with open(failure_taxonomy_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(failure_taxonomy, f, ensure_ascii=False, indent=2)
        print("FAILURE_TAXONOMY_WRITTEN")
    except Exception as e:
        return f"Failed to create failure_taxonomy.json: {str(e)}"

    # 3) signal_index.json 생성
    try:
        signal_index = build_signal_index(patterns_metrics)
        signal_index_path = output_dir / "signal_index.json"
        with open(signal_index_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(signal_index, f, ensure_ascii=False, indent=2)
        print("SIGNAL_INDEX_WRITTEN")
    except Exception as e:
        return f"Failed to create signal_index.json: {str(e)}"

    # 4) question_seeds.json 생성
    try:
        question_seeds, warning = build_question_seeds(patterns_tags)
        if warning:
            print(f"WARN: {warning}")
        question_seeds_path = output_dir / "question_seeds.json"
        with open(question_seeds_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(question_seeds, f, ensure_ascii=False, indent=2)
        print("QUESTION_SEEDS_WRITTEN")
    except Exception as e:
        return f"Failed to create question_seeds.json: {str(e)}"

    # 5) semantic_index.json 생성 (통합)
    try:
        indexed_at = utc_now_iso()
        semantic_index = {
            "run_id": run_id,
            "indexed_at": indexed_at,
            "semantic_tags": semantic_tags,
            "failure_taxonomy": failure_taxonomy,
            "signal_index": signal_index,
            "question_seeds": question_seeds,
            "reference_only": True
        }
        semantic_index_path = output_dir / "semantic_index.json"
        with open(semantic_index_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(semantic_index, f, ensure_ascii=False, indent=2)
        print("SEMANTIC_INDEX_WRITTEN")
    except Exception as e:
        return f"Failed to create semantic_index.json: {str(e)}"

    # 6) index.json 생성
    try:
        indexed_at = utc_now_iso()
        index = {
            "run_id": run_id,
            "step": "v3_step3",
            "indexed_at": indexed_at,
            "files": {
                "semantic_tags": "semantic_tags.json",
                "failure_taxonomy": "failure_taxonomy.json",
                "signal_index": "signal_index.json",
                "question_seeds": "question_seeds.json",
                "semantic_index": "semantic_index.json"
            }
        }
        index_path = output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print("INDEX_WRITTEN")
    except Exception as e:
        return f"Failed to create index.json: {str(e)}"

    return None

