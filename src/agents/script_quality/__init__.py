"""ScriptQualityAgent — Step08 스크립트 품질 자동 평가."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.ssot import read_json


class ScriptQualityAgent(BaseAgent):
    """Step08에서 생성된 스크립트의 Hook/CTA/구조 품질을 평가하고 개선 제안을 기록한다."""

    # 채널별 톤 키워드 (채널 카테고리 반영)
    _CHANNEL_TONE: dict[str, list[str]] = {
        "CH1": ["금리", "경제", "투자", "수익"],
        "CH2": ["과학", "연구", "발견", "실험"],
        "CH3": ["부동산", "아파트", "전세", "분양"],
        "CH4": ["심리", "감정", "마음", "관계"],
        "CH5": ["미스터리", "미스터", "불가사의", "수수께끼"],
        "CH6": ["역사", "조선", "고려", "왕조"],
        "CH7": ["전쟁", "역사", "전투", "군사"],
    }

    # 품질 평가 임계값
    _MIN_HOOK_LENGTH = 20   # 자 — Hook 텍스트 최소 길이
    _MIN_SCENES = 3         # 최소 씬 수
    _MIN_TOTAL_CHARS = 300  # 스크립트 최소 총 글자 수

    def __init__(self, root: Optional[Path] = None):
        super().__init__("ScriptQualityAgent")
        if root is not None:
            self.root = root
            self.runs_dir = root / "runs"
            self.data_dir = root / "data"

    def run(self) -> dict[str, Any]:
        self._log_start()
        results: list[dict[str, Any]] = []
        total_evaluated = 0
        total_issues = 0

        for ch_dir in sorted(self.runs_dir.iterdir()):
            if not ch_dir.is_dir() or not ch_dir.name.startswith("CH"):
                continue
            for run_dir in sorted(ch_dir.iterdir(), reverse=True)[:5]:
                # 최근 5개 run만 평가
                script_path = run_dir / "step08" / "script.json"
                if not script_path.exists():
                    continue
                try:
                    evaluation = self._evaluate_script(
                        ch_dir.name, run_dir.name, script_path
                    )
                    if evaluation:
                        results.append(evaluation)
                        total_evaluated += 1
                        total_issues += len(evaluation.get("issues", []))
                except Exception as e:
                    logger.warning(f"[ScriptQualityAgent] {run_dir.name} 평가 실패: {e}")

        # 채널별 평균 점수 집계
        channel_avg = self._compute_channel_avg(results)

        # 결과 저장
        output_path = self.data_dir / "global" / "agent_logs" / "script_quality_latest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "evaluated": total_evaluated,
                    "total_issues": total_issues,
                    "channel_averages": channel_avg,
                    "details": results[-20:],  # 최근 20개만 저장
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = {
            "evaluated": total_evaluated,
            "total_issues": total_issues,
            "channel_averages": channel_avg,
        }
        self._log_done(result)
        return result

    def _evaluate_script(
        self, channel_id: str, run_id: str, script_path: Path
    ) -> dict[str, Any] | None:
        """단일 스크립트를 평가하고 품질 점수와 이슈를 반환한다."""
        data = read_json(str(script_path))
        if not data:
            return None

        issues: list[str] = []
        score = 100

        # 1. Hook 품질 평가
        hook = data.get("hook", "")
        if isinstance(hook, dict):
            hook = hook.get("text", "")
        hook = str(hook)
        if len(hook) < self._MIN_HOOK_LENGTH:
            issues.append(f"Hook이 너무 짧음 ({len(hook)}자 < {self._MIN_HOOK_LENGTH}자)")
            score -= 20
        if not any(c in hook for c in ["?", "!", "…"]):
            issues.append("Hook에 의문/감탄/여운 부호 없음 — 시청자 호기심 유발 부족")
            score -= 10

        # 2. 씬 구성 평가
        scenes = data.get("scenes", [])
        if len(scenes) < self._MIN_SCENES:
            issues.append(f"씬 수 부족 ({len(scenes)}개 < {self._MIN_SCENES}개)")
            score -= 15

        # 3. 총 글자 수 평가
        total_text = hook + " ".join(
            str(s.get("narration", s.get("text", ""))) for s in scenes
        )
        if len(total_text) < self._MIN_TOTAL_CHARS:
            issues.append(f"스크립트 총 텍스트 부족 ({len(total_text)}자 < {self._MIN_TOTAL_CHARS}자)")
            score -= 15

        # 4. 채널 톤 일관성 평가
        expected_keywords = self._CHANNEL_TONE.get(channel_id, [])
        if expected_keywords:
            found = [kw for kw in expected_keywords if kw in total_text]
            if not found:
                issues.append(
                    f"{channel_id} 채널 키워드 없음 (기대: {expected_keywords[:2]})"
                )
                score -= 10

        # 5. CTA(Call-To-Action) 유무
        cta = data.get("cta", "")
        if not cta or len(str(cta)) < 5:
            issues.append("CTA(마무리 행동 유도) 없음 또는 너무 짧음")
            score -= 10

        return {
            "channel_id": channel_id,
            "run_id": run_id,
            "score": max(0, score),
            "issues": issues,
            "hook_length": len(hook),
            "scene_count": len(scenes),
            "total_chars": len(total_text),
        }

    def _compute_channel_avg(self, results: list[dict]) -> dict[str, float]:
        """채널별 평균 품질 점수를 계산한다."""
        ch_scores: dict[str, list[float]] = {}
        for r in results:
            ch = r.get("channel_id", "")
            if ch:
                ch_scores.setdefault(ch, []).append(float(r.get("score", 0)))
        return {
            ch: round(sum(scores) / len(scores), 1)
            for ch, scores in ch_scores.items()
            if scores
        }
