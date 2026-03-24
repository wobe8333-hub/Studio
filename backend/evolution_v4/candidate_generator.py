"""
v4-Step2: Candidate Generation

기능:
- BaselineV4를 기준으로 개선/유지/회피 관점의 후보 생성
- 자동 선택/점수화/랭킹 금지
- 후보 설명만 제공
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone

from backend.evolution_v4.schema import utc_now_iso

CANDIDATE_TYPE = Literal["SUCCESS_REINFORCE", "FAILURE_AVOID", "DIVERSITY_EXPLORE"]


def load_baseline(baseline_path: Path) -> Optional[Dict[str, Any]]:
    """
    BaselineV4 로드
    
    Args:
        baseline_path: baseline JSON 경로
    
    Returns:
        Optional[Dict]: baseline 데이터 (실패 시 None)
    """
    if not baseline_path.exists():
        return None
    
    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def generate_candidates(baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    후보 생성 (데이터 기반)
    
    Args:
        baseline: BaselineV4 데이터
    
    Returns:
        List[Dict]: 후보 리스트
    """
    candidates = []
    kpis = baseline.get("kpis", {})
    
    # KPI 값 추출 (missing이 아닌 값만)
    verify_pass = kpis.get("verify_pass")
    failure_count = kpis.get("failure_count")
    has_valuable_failure = kpis.get("has_valuable_failure")
    scene_count = kpis.get("scene_count")
    retry_regenerate = kpis.get("retry_regenerate")
    retry_render = kpis.get("retry_render")
    silence_signal_count = kpis.get("silence_signal_count")
    total_duration_sec = kpis.get("total_duration_sec")
    
    candidate_index = 1
    
    # 1) FAILURE_AVOID 후보 생성
    failure_candidates = []
    
    # failure_count > 0
    if isinstance(failure_count, int) and failure_count > 0:
        failure_candidates.append({
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
            "type": "FAILURE_AVOID",
            "title": "실패 카운트 감소 후보",
            "description": f"Baseline에서 failure_count={failure_count}이 관측되었습니다. 실패 패턴 회피를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["failure_count"],
                "signals": [f"failure_count={failure_count}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"failure_count": failure_count},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "실패 패턴 회피 시 다른 영역에 영향 가능",
                "open_questions": ["실패 원인 근본 분석 필요 여부"]
            }
        })
        candidate_index += 1
    
    # has_valuable_failure == True
    if has_valuable_failure is True:
        failure_candidates.append({
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
            "type": "FAILURE_AVOID",
            "title": "가치 있는 실패 회피 후보",
            "description": "Baseline에서 valuable_failure=True가 관측되었습니다. 유사한 실패 패턴 회피를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["has_valuable_failure"],
                "signals": ["valuable_failure=True"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"has_valuable_failure": True},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "가치 있는 실패는 학습 기회일 수 있음",
                "open_questions": ["실패 보존 vs 회피 전략 선택 기준"]
            }
        })
        candidate_index += 1
    
    # retry_render > 0
    if isinstance(retry_render, int) and retry_render > 0:
        failure_candidates.append({
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
            "type": "FAILURE_AVOID",
            "title": "렌더 재시도 감소 후보",
            "description": f"Baseline에서 retry_render={retry_render}이 관측되었습니다. 렌더 재시도 패턴 회피를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["retry_render"],
                "signals": [f"retry_render={retry_render}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"retry_render": retry_render},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "재시도 감소 시 성공률 변화 가능",
                "open_questions": ["재시도 임계값 조정 기준"]
            }
        })
        candidate_index += 1
    
    # retry_regenerate > 0
    if isinstance(retry_regenerate, int) and retry_regenerate > 0:
        failure_candidates.append({
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
            "type": "FAILURE_AVOID",
            "title": "재생성 재시도 감소 후보",
            "description": f"Baseline에서 retry_regenerate={retry_regenerate}이 관측되었습니다. 재생성 재시도 패턴 회피를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["retry_regenerate"],
                "signals": [f"retry_regenerate={retry_regenerate}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"retry_regenerate": retry_regenerate},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "재생성 재시도 감소 시 품질 변화 가능",
                "open_questions": ["재생성 임계값 조정 기준"]
            }
        })
        candidate_index += 1
    
    # silence_signal_count > 0
    if isinstance(silence_signal_count, int) and silence_signal_count > 0:
        failure_candidates.append({
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
            "type": "FAILURE_AVOID",
            "title": "침묵 신호 감소 후보",
            "description": f"Baseline에서 silence_signal_count={silence_signal_count}이 관측되었습니다. 침묵 신호 패턴 회피를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["silence_signal_count"],
                "signals": [f"silence_signal_count={silence_signal_count}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"silence_signal_count": silence_signal_count},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "침묵 신호 감소 시 다른 신호 변화 가능",
                "open_questions": ["침묵 신호 임계값 조정 기준"]
            }
        })
        candidate_index += 1
    
    # FAILURE_AVOID 후보 선택 (최소 1개, 최대 3개)
    if failure_candidates:
        candidates.extend(failure_candidates[:3])
    
    # 2) SUCCESS_REINFORCE 후보 생성
    success_candidates = []
    
    # verify_pass == True
    if verify_pass is True:
        success_candidates.append({
            "candidate_id": f"cand_v4_step2:SUCCESS_REINFORCE:{candidate_index}",
            "type": "SUCCESS_REINFORCE",
            "title": "검증 통과 유지 강화 후보",
            "description": "Baseline에서 verify_pass=True가 관측되었습니다. 검증 통과 패턴 유지·강화를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["verify_pass"],
                "signals": ["verify_pass=True"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"verify_pass": True},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "유지 강화 시 다른 영역 변화 가능",
                "open_questions": ["강화 범위 및 방법"]
            }
        })
        candidate_index += 1
    
    # failure_count == 0
    if isinstance(failure_count, int) and failure_count == 0:
        success_candidates.append({
            "candidate_id": f"cand_v4_step2:SUCCESS_REINFORCE:{candidate_index}",
            "type": "SUCCESS_REINFORCE",
            "title": "실패 없음 유지 강화 후보",
            "description": "Baseline에서 failure_count=0이 관측되었습니다. 실패 없음 패턴 유지·강화를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["failure_count"],
                "signals": ["failure_count=0"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"failure_count": 0},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "유지 강화 시 다른 영역 변화 가능",
                "open_questions": ["강화 범위 및 방법"]
            }
        })
        candidate_index += 1
    
    # SUCCESS_REINFORCE 후보 선택 (최소 1개, 최대 2개)
    if success_candidates:
        candidates.extend(success_candidates[:2])
    
    # 3) DIVERSITY_EXPLORE 후보 생성
    diversity_candidates = []
    
    # scene_count가 있고 안정적인 경우
    if isinstance(scene_count, int) and scene_count > 0:
        diversity_candidates.append({
            "candidate_id": f"cand_v4_step2:DIVERSITY_EXPLORE:{candidate_index}",
            "type": "DIVERSITY_EXPLORE",
            "title": "씬 구성 다양성 탐색 후보",
            "description": f"Baseline에서 scene_count={scene_count}이 관측되었습니다. 씬 구성 다양성 확보를 위한 대안적 시도를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["scene_count"],
                "signals": [f"scene_count={scene_count}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"scene_count": scene_count},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "다양성 확보 시 안정성 변화 가능",
                "open_questions": ["다양성 확보 범위 및 방법"]
            }
        })
        candidate_index += 1
    
    # total_duration_sec가 있는 경우
    if isinstance(total_duration_sec, (int, float)) and total_duration_sec > 0:
        diversity_candidates.append({
            "candidate_id": f"cand_v4_step2:DIVERSITY_EXPLORE:{candidate_index}",
            "type": "DIVERSITY_EXPLORE",
            "title": "지속 시간 분포 다양성 탐색 후보",
            "description": f"Baseline에서 total_duration_sec={total_duration_sec}이 관측되었습니다. 지속 시간 분포 다양성 확보를 위한 대안적 시도를 고려할 수 있습니다.",
            "based_on": {
                "kpis": ["total_duration_sec"],
                "signals": [f"total_duration_sec={total_duration_sec}"]
            },
            "constraints": {
                "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
            },
            "evidence": {
                "baseline_kpi_snapshot": {"total_duration_sec": total_duration_sec},
                "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
            },
            "notes": {
                "risk": "다양성 확보 시 안정성 변화 가능",
                "open_questions": ["다양성 확보 범위 및 방법"]
            }
        })
        candidate_index += 1
    
    # DIVERSITY_EXPLORE 후보 선택 (최소 1개, 최대 2개)
    if diversity_candidates:
        candidates.extend(diversity_candidates[:2])
    
    # 최소 3개, 최대 7개 보장
    # 이미 각 타입별로 제한했으므로, 전체가 7개를 넘지 않도록 조정
    if len(candidates) > 7:
        # 타입별로 균등하게 선택
        failure_count = sum(1 for c in candidates if c["type"] == "FAILURE_AVOID")
        success_count = sum(1 for c in candidates if c["type"] == "SUCCESS_REINFORCE")
        diversity_count = sum(1 for c in candidates if c["type"] == "DIVERSITY_EXPLORE")
        
        # 최소 1개씩은 보장하고 나머지 조정
        final_candidates = []
        final_candidates.extend([c for c in candidates if c["type"] == "FAILURE_AVOID"][:min(failure_count, 3)])
        final_candidates.extend([c for c in candidates if c["type"] == "SUCCESS_REINFORCE"][:min(success_count, 2)])
        final_candidates.extend([c for c in candidates if c["type"] == "DIVERSITY_EXPLORE"][:min(diversity_count, 2)])
        
        candidates = final_candidates[:7]
    
    # 최소 3개 보장 (각 타입 최소 1개)
    if len(candidates) < 3:
        # 부족한 타입에 대해 기본 후보 추가
        if not any(c["type"] == "FAILURE_AVOID" for c in candidates):
            candidates.append({
                "candidate_id": f"cand_v4_step2:FAILURE_AVOID:{candidate_index}",
                "type": "FAILURE_AVOID",
                "title": "일반적 실패 회피 후보",
                "description": "Baseline KPI를 기반으로 실패 패턴 회피를 고려할 수 있습니다.",
                "based_on": {
                    "kpis": list(kpis.keys()),
                    "signals": ["Baseline KPI 관측"]
                },
                "constraints": {
                    "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                    "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
                },
                "evidence": {
                    "baseline_kpi_snapshot": kpis,
                    "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
                },
                "notes": {
                    "risk": "회피 전략 시 다른 영역 변화 가능",
                    "open_questions": ["회피 범위 및 방법"]
                }
            })
            candidate_index += 1
        
        if not any(c["type"] == "SUCCESS_REINFORCE" for c in candidates):
            candidates.append({
                "candidate_id": f"cand_v4_step2:SUCCESS_REINFORCE:{candidate_index}",
                "type": "SUCCESS_REINFORCE",
                "title": "일반적 성공 유지 강화 후보",
                "description": "Baseline KPI를 기반으로 성공 패턴 유지·강화를 고려할 수 있습니다.",
                "based_on": {
                    "kpis": list(kpis.keys()),
                    "signals": ["Baseline KPI 관측"]
                },
                "constraints": {
                    "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                    "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
                },
                "evidence": {
                    "baseline_kpi_snapshot": kpis,
                    "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
                },
                "notes": {
                    "risk": "유지 강화 시 다른 영역 변화 가능",
                    "open_questions": ["강화 범위 및 방법"]
                }
            })
            candidate_index += 1
        
        if not any(c["type"] == "DIVERSITY_EXPLORE" for c in candidates):
            candidates.append({
                "candidate_id": f"cand_v4_step2:DIVERSITY_EXPLORE:{candidate_index}",
                "type": "DIVERSITY_EXPLORE",
                "title": "일반적 다양성 탐색 후보",
                "description": "Baseline KPI를 기반으로 다양성 확보를 위한 대안적 시도를 고려할 수 있습니다.",
                "based_on": {
                    "kpis": list(kpis.keys()),
                    "signals": ["Baseline KPI 관측"]
                },
                "constraints": {
                    "must_not_change": ["baseline 입력 파일", "v3 산출물"],
                    "allowed_scope": ["Step3 정책 엔진에서 고려 가능"]
                },
                "evidence": {
                    "baseline_kpi_snapshot": kpis,
                    "source_paths": [v for v in baseline.get("inputs", {}).values() if v is not None]
                },
                "notes": {
                    "risk": "다양성 확보 시 안정성 변화 가능",
                    "open_questions": ["다양성 확보 범위 및 방법"]
                }
            })
    
    return candidates


def create_candidate_set(
    run_id: str,
    baseline: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    baseline_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    CandidateSet 생성
    
    Args:
        run_id: 실행 ID
        baseline: BaselineV4 데이터
        candidates: 후보 리스트
        baseline_path: baseline 파일 경로 (None이면 계산)
    
    Returns:
        Dict: CandidateSet JSON 데이터
    """
    if baseline_path is None:
        # baseline의 inputs에서 경로 추론
        snapshot_path_str = baseline.get("inputs", {}).get("memory_snapshot_path", "")
        if snapshot_path_str:
            snapshot_path = Path(snapshot_path_str)
            # snapshots/<run_id>.json -> baselines/<run_id>.json
            baseline_path = snapshot_path.parent.parent.parent / "baselines" / f"{run_id}.json"
        else:
            baseline_path = Path("")
    
    baseline_path_str = str(baseline_path.resolve().as_posix()) if baseline_path and baseline_path.exists() else ""
    
    return {
        "run_id": run_id,
        "baseline_ref": {
            "baseline_id": baseline.get("baseline_id", ""),
            "baseline_path": baseline_path_str
        },
        "created_at": utc_now_iso(),
        "candidates": candidates,
        "version": "v4_step2",
        "state": "CANDIDATES_ONLY"
    }


def generate_candidate_set(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    CandidateSet 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (candidate_set, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # Baseline 로드
    baseline_path = project_root / "backend" / "output" / "evolution_v4" / "baselines" / f"{run_id}.json"
    
    if not baseline_path.exists():
        return None, f"Baseline not found: {baseline_path.resolve()}"
    
    baseline = load_baseline(baseline_path)
    if baseline is None:
        return None, f"Failed to load baseline: {baseline_path.resolve()}"
    
    # 후보 생성
    candidates = generate_candidates(baseline)
    
    # CandidateSet 생성
    candidate_set = create_candidate_set(run_id, baseline, candidates, baseline_path)
    
    return candidate_set, None

