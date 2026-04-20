"""API 실패 시나리오 Chaos 테스트 (Plan C-3 T7).

외부 API(Gemini, YouTube, 파일 시스템)가 다양한 방식으로 실패할 때
파이프라인이 올바르게 대응하는지 검증한다.
"""
import json
import os
import threading
import tempfile
import pytest
from unittest.mock import patch, MagicMock


class TestGeminiFailureChaos:
    """Gemini API 장애 시나리오"""

    def test_gemini_failure_falls_back_to_claude(self):
        """Gemini 장애 시 Claude fallback이 응답해야 한다."""
        from src.core.llm_client import generate_text

        with patch("src.core.llm_client._call_gemini",
                   side_effect=Exception("서비스 불가")), \
             patch("src.core.llm_client._call_claude",
                   return_value="Claude 대체 응답"):
            result = generate_text("대본 생성해줘")

        assert result == "Claude 대체 응답"

    def test_both_llm_down_raises_clear_error(self):
        """Gemini와 Claude 모두 다운 시 명확한 오류 코드로 실패해야 한다."""
        from src.core.llm_client import generate_text

        with patch("src.core.llm_client._call_gemini",
                   side_effect=Exception("Gemini 다운")), \
             patch("src.core.llm_client._call_claude",
                   side_effect=Exception("Claude 다운")):
            with pytest.raises(RuntimeError, match="LLM_ALL_PROVIDERS_FAILED"):
                generate_text("프롬프트")

    def test_gemini_first_call_then_success(self):
        """Gemini가 첫 호출에 성공하면 Claude는 호출하지 않아야 한다."""
        from src.core.llm_client import generate_text

        with patch("src.core.llm_client._call_gemini",
                   return_value="Gemini 정상 응답") as mock_g, \
             patch("src.core.llm_client._call_claude") as mock_c:
            result = generate_text("프롬프트")

        mock_g.assert_called_once()
        mock_c.assert_not_called()
        assert result == "Gemini 정상 응답"

    def test_copyright_checker_safe_on_llm_outage(self):
        """LLM 전체 장애 시 저작권 체크는 안전(0.0)으로 처리해야 한다."""
        from src.step11.copyright_checker import check_copyright_risk

        with patch("src.step11.copyright_checker.generate_text",
                   side_effect=RuntimeError("LLM_ALL_PROVIDERS_FAILED")):
            result = check_copyright_risk("대본 내용입니다.")

        # LLM 장애 시 안전으로 처리 — 파이프라인 중단 방지
        assert result["risk_score"] == 0.0
        assert result["reasons"] == []


class TestYouTubeQuotaExhaustedChaos:
    """YouTube API 쿼터 소진 시나리오"""

    def test_upload_blocked_when_quota_exhausted(self):
        """YouTube 쿼터 소진 시 can_upload가 False를 반환해야 한다."""
        from src.quota.youtube_quota import can_upload, UPLOAD_COST, BLOCK_THRESHOLD

        # 쿼터를 UPLOAD_COST보다 적게 남긴 상황 시뮬레이션
        exhausted_quota = {
            "date": "2026-04-20",
            "quota_used": BLOCK_THRESHOLD + 100,
            "quota_limit": 10000,
            "quota_remaining": UPLOAD_COST - 1,  # UPLOAD_COST(1700) - 1 남음
            "deferred_jobs": [],
        }
        with patch("src.quota.youtube_quota.get_quota", return_value=exhausted_quota):
            assert can_upload() is False

    def test_upload_allowed_when_quota_sufficient(self):
        """쿼터 충분 시 can_upload가 True를 반환해야 한다."""
        from src.quota.youtube_quota import can_upload, UPLOAD_COST

        sufficient_quota = {
            "date": "2026-04-20",
            "quota_used": 0,
            "quota_limit": 10000,
            "quota_remaining": UPLOAD_COST * 2,  # 충분한 잔여 쿼터
            "deferred_jobs": [],
        }
        with patch("src.quota.youtube_quota.get_quota", return_value=sufficient_quota):
            assert can_upload() is True

    def test_upload_error_raises_runtime_error_with_context(self):
        """쿼터 부족 시 upload_video가 run_id 정보와 함께 RuntimeError를 발생해야 한다."""
        from src.step12.uploader import upload_video

        # uploader.py는 from src.quota.youtube_quota import can_upload로 바인딩
        # → 사용 위치에서 패치해야 함
        with patch("src.step12.uploader.can_upload", return_value=False), \
             patch("src.step12.uploader.defer_job"):
            with pytest.raises(RuntimeError, match="YOUTUBE_QUOTA_INSUFFICIENT"):
                upload_video("CH1", "test_run_999")


class TestFileSystemChaos:
    """파일 시스템 장애 시나리오"""

    def test_ssot_write_concurrent_no_corruption(self):
        """SSOT 동시 쓰기 시 데이터 손상 없이 완료되어야 한다."""
        from pathlib import Path
        from src.core.ssot import write_json

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "concurrent.json"  # write_json은 Path 필요
            errors = []

            def write_worker(i):
                try:
                    write_json(test_path, {"worker": i, "payload": "x" * 100})
                except Exception as e:
                    errors.append(str(e))

            threads = [
                threading.Thread(target=write_worker, args=(i,)) for i in range(5)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 동시 쓰기 오류 없어야 함
            assert len(errors) == 0, f"동시 쓰기 오류: {errors}"

            # 마지막으로 쓴 데이터가 유효한 JSON이어야 함
            with open(test_path, encoding="utf-8-sig") as f:
                data = json.load(f)
            assert "worker" in data
