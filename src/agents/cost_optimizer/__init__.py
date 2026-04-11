"""CostOptimizerAgent — Gemini/YouTube 쿼터 사용 패턴 분석 및 비용 최적화."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.ssot import read_json


class CostOptimizerAgent(BaseAgent):
    """Gemini/YouTube 쿼터 사용 현황을 분석하고 낭비를 감지한다."""

    # 경고 임계값
    _GEMINI_RPM_LIMIT = 50
    _GEMINI_DAILY_IMAGE_LIMIT = 500
    _YOUTUBE_DAILY_QUOTA = 10_000
    _YOUTUBE_UPLOAD_COST = 1_700

    # 경고 트리거 임계값 (한도 대비 비율)
    _WARNING_RATIO = 0.80    # 80% 초과 시 경고
    _CRITICAL_RATIO = 0.95   # 95% 초과 시 위험

    def __init__(self, root: Optional[Path] = None):
        super().__init__("CostOptimizerAgent")
        if root is not None:
            self.root = root
            self.runs_dir = root / "runs"
            self.data_dir = root / "data"

    def run(self) -> dict[str, Any]:
        self._log_start()

        gemini_status = self._analyze_gemini_quota()
        youtube_status = self._analyze_youtube_quota()
        cost_report = self._build_cost_report(gemini_status, youtube_status)
        recommendations = self._generate_recommendations(gemini_status, youtube_status)

        # 결과 저장
        output_path = self.data_dir / "global" / "agent_logs" / "cost_optimizer_latest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gemini": gemini_status,
            "youtube": youtube_status,
            "cost_report": cost_report,
            "recommendations": recommendations,
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # HITL 에스컬레이션 (95% 초과 시)
        critical_alerts = [
            r for r in recommendations if r.get("severity") == "critical"
        ]
        if critical_alerts:
            self._emit_hitl_signal(critical_alerts)

        result = {
            "gemini_usage_ratio": gemini_status.get("image_usage_ratio", 0),
            "youtube_usage_ratio": youtube_status.get("usage_ratio", 0),
            "recommendations_count": len(recommendations),
            "critical_alerts": len(critical_alerts),
        }
        self._log_done(result)
        return result

    def _analyze_gemini_quota(self) -> dict[str, Any]:
        """Gemini 쿼터 현황을 분석한다."""
        quota_path = self.data_dir / "global" / "quota" / "gemini_quota_daily.json"
        quota_data = read_json(str(quota_path)) if quota_path.exists() else {}

        images_used = quota_data.get("images_generated_today", 0)
        image_ratio = images_used / self._GEMINI_DAILY_IMAGE_LIMIT

        return {
            "images_generated_today": images_used,
            "image_limit": self._GEMINI_DAILY_IMAGE_LIMIT,
            "image_usage_ratio": round(image_ratio, 3),
            "image_status": self._classify_ratio(image_ratio),
            "last_reset": quota_data.get("last_reset", "unknown"),
            "deferred_count": len(quota_data.get("deferred_jobs", [])),
        }

    def _analyze_youtube_quota(self) -> dict[str, Any]:
        """YouTube 쿼터 현황을 분석한다."""
        quota_path = self.data_dir / "global" / "quota" / "youtube_quota.json"
        quota_data = read_json(str(quota_path)) if quota_path.exists() else {}

        used = quota_data.get("used_today", 0)
        ratio = used / self._YOUTUBE_DAILY_QUOTA

        # 이연 업로드 수 (쿼터 부족으로 연기된 항목)
        deferred = quota_data.get("deferred_jobs", [])
        deferred_cost = len(deferred) * self._YOUTUBE_UPLOAD_COST

        return {
            "quota_used_today": used,
            "quota_limit": self._YOUTUBE_DAILY_QUOTA,
            "usage_ratio": round(ratio, 3),
            "status": self._classify_ratio(ratio),
            "deferred_jobs": len(deferred),
            "deferred_estimated_cost": deferred_cost,
        }

    def _build_cost_report(
        self,
        gemini: dict[str, Any],
        youtube: dict[str, Any],
    ) -> dict[str, Any]:
        """비용 리포트를 생성한다."""
        # 최근 runs에서 실제 비용 집계
        total_cost_krw = 0.0
        cost_by_channel: dict[str, float] = {}

        for ch_dir in sorted(self.runs_dir.iterdir()):
            if not ch_dir.is_dir() or not ch_dir.name.startswith("CH"):
                continue
            ch_cost = 0.0
            for run_dir in sorted(ch_dir.iterdir(), reverse=True)[:10]:
                cost_path = run_dir / "cost.json"
                if not cost_path.exists():
                    continue
                cost_data = read_json(str(cost_path)) or {}
                krw = float(cost_data.get("total_cost_krw", 0))
                ch_cost += krw
                total_cost_krw += krw
            if ch_cost > 0:
                cost_by_channel[ch_dir.name] = round(ch_cost, 0)

        return {
            "total_cost_krw": round(total_cost_krw, 0),
            "cost_by_channel": cost_by_channel,
            "gemini_image_ratio": gemini.get("image_usage_ratio", 0),
            "youtube_quota_ratio": youtube.get("usage_ratio", 0),
        }

    def _generate_recommendations(
        self,
        gemini: dict[str, Any],
        youtube: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """최적화 권장 사항을 생성한다."""
        recs: list[dict[str, Any]] = []

        # Gemini 이미지 쿼터 경고
        g_ratio = gemini.get("image_usage_ratio", 0)
        if g_ratio >= self._CRITICAL_RATIO:
            recs.append({
                "severity": "critical",
                "area": "gemini_quota",
                "message": f"Gemini 이미지 쿼터 {g_ratio*100:.0f}% 도달 — 오늘 추가 실행 중단 권장",
                "action": "파이프라인 실행을 내일로 연기하거나 이미지 생성 수를 줄이세요",
            })
        elif g_ratio >= self._WARNING_RATIO:
            recs.append({
                "severity": "warning",
                "area": "gemini_quota",
                "message": f"Gemini 이미지 쿼터 {g_ratio*100:.0f}% 사용 중",
                "action": "남은 채널 수와 쿼터 여유분을 확인하세요",
            })

        # YouTube 쿼터 경고
        yt_ratio = youtube.get("usage_ratio", 0)
        if yt_ratio >= self._CRITICAL_RATIO:
            recs.append({
                "severity": "critical",
                "area": "youtube_quota",
                "message": f"YouTube 쿼터 {yt_ratio*100:.0f}% 도달 — 업로드 불가",
                "action": f"deferred_jobs {youtube.get('deferred_jobs', 0)}건을 내일 처리 예정",
            })

        # 이연 업로드 경고
        deferred = youtube.get("deferred_jobs", 0)
        if deferred >= 3:
            recs.append({
                "severity": "warning",
                "area": "deferred_uploads",
                "message": f"이연된 업로드 {deferred}건 대기 중",
                "action": "다음 파이프라인 실행 시 자동으로 재시도됩니다",
            })

        return recs

    def _classify_ratio(self, ratio: float) -> str:
        """사용 비율을 상태 문자열로 변환한다."""
        if ratio >= self._CRITICAL_RATIO:
            return "critical"
        if ratio >= self._WARNING_RATIO:
            return "warning"
        return "ok"

    def _emit_hitl_signal(self, alerts: list[dict]) -> None:
        """위험 수준 쿼터 알림을 HITL 신호 파일에 기록한다."""
        signals_path = self.data_dir / "global" / "notifications" / "hitl_signals.json"
        signals_path.parent.mkdir(parents=True, exist_ok=True)

        existing = read_json(str(signals_path)) if signals_path.exists() else []
        if not isinstance(existing, list):
            existing = []

        for alert in alerts:
            existing.append({
                "type": "quota_critical",
                "source": self.name,
                "message": alert.get("message", ""),
                "action": alert.get("action", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
            })

        signals_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.warning(f"[CostOptimizerAgent] HITL 신호 발행: {len(alerts)}건")
