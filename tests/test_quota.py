"""Phase D-6 — quota 모듈 단위 테스트.

gemini_quota: RPM 카운터 파일 기반 전환 포함
youtube_quota: 쿼터 소비/차단 로직
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch


# ──────────────────────────────────────────────
# Gemini Quota 테스트
# ──────────────────────────────────────────────

class TestGeminiQuota:
    @pytest.fixture(autouse=True)
    def reset_memory(self):
        """각 테스트 전 인메모리 _request_times 초기화."""
        import src.quota.gemini_quota as gq
        gq._request_times = []
        yield
        gq._request_times = []

    def test_init_quota_file_creates_json(self, tmp_path, monkeypatch):
        """_init_quota_file이 오늘 날짜로 quota JSON을 생성한다."""
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        from src.quota.gemini_quota import _init_quota_file
        data = _init_quota_file()

        assert quota_file.exists()
        assert data["total_requests"] == 0
        assert "rpm_timestamps" in data

    def test_record_request_increments_total(self, tmp_path, monkeypatch):
        """record_request()가 total_requests를 증가시킨다."""
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        from src.quota.gemini_quota import record_request, get_quota
        record_request()
        record_request()
        data = get_quota()

        assert data["total_requests"] == 2

    def test_rpm_timestamps_persisted_in_file(self, tmp_path, monkeypatch):
        """record_request()가 rpm_timestamps를 파일에 저장한다."""
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        from src.quota.gemini_quota import record_request, get_quota
        record_request()

        data = get_quota()
        assert len(data.get("rpm_timestamps", [])) >= 1

    def test_current_rpm_restored_from_file(self, tmp_path, monkeypatch):
        """프로세스 재시작(메모리 초기화) 후 파일에서 RPM이 복원된다."""
        import src.quota.gemini_quota as gq
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        # 요청 1회 기록
        from src.quota.gemini_quota import record_request
        record_request()

        # 메모리 초기화 (재시작 시뮬레이션)
        gq._request_times = []

        from src.quota.gemini_quota import _current_rpm
        rpm = _current_rpm()
        assert rpm >= 1

    def test_record_image_blocks_when_exceeded(self, tmp_path, monkeypatch):
        """daily 이미지 한도 초과 시 record_image가 False를 반환한다."""
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        # 한도(500)에 딱 맞게 초기화
        init_data = {
            "date": __import__("src.core.ssot", fromlist=["now_iso"]).now_iso()[:10],
            "total_requests": 0,
            "rpm_peak": 0.0,
            "rpm_timestamps": [],
            "images_generated": 500,
            "scoring_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_rate": 0.0,
            "retry_count": 0,
            "sequential_mode_activations": 0,
            "cost_saved_by_cache_krw": 0.0,
        }
        quota_file.write_text(json.dumps(init_data), encoding="utf-8")

        from src.quota.gemini_quota import record_image
        result = record_image(1)
        assert result is False

    def test_record_cache_hit_updates_hit_rate(self, tmp_path, monkeypatch):
        """record_cache_hit / record_cache_miss가 hit_rate를 올바르게 계산한다."""
        quota_file = tmp_path / "gemini_quota_daily.json"
        monkeypatch.setattr("src.quota.gemini_quota.QUOTA_FILE", quota_file)

        from src.quota.gemini_quota import record_cache_hit, record_cache_miss, get_quota
        record_cache_hit()
        record_cache_hit()
        record_cache_miss()
        data = get_quota()

        assert data["cache_hits"] == 2
        assert data["cache_misses"] == 1
        assert abs(data["cache_hit_rate"] - 2/3) < 0.01


# ──────────────────────────────────────────────
# YouTube Quota 테스트
# ──────────────────────────────────────────────

class TestYouTubeQuota:
    def test_consume_returns_true_when_within_limit(self, tmp_path, monkeypatch):
        """쿼터 여유가 있으면 consume이 True를 반환한다."""
        quota_file = tmp_path / "youtube_quota_daily.json"
        monkeypatch.setattr("src.quota.youtube_quota.QUOTA_FILE", quota_file)

        from src.quota.youtube_quota import consume
        result = consume(100, "search")

        assert result is True

    def test_consume_returns_false_when_exceeded(self, tmp_path, monkeypatch):
        """쿼터 초과 시 consume이 False를 반환한다."""
        from src.quota.youtube_quota import BLOCK_THRESHOLD
        quota_file = tmp_path / "youtube_quota_daily.json"
        monkeypatch.setattr("src.quota.youtube_quota.QUOTA_FILE", quota_file)

        from src.core.ssot import now_iso
        init_data = {
            "date": now_iso()[:10],
            "quota_used": BLOCK_THRESHOLD,  # 이미 차단 임계값에 도달
            "quota_limit": 10000,
            "quota_remaining": 0,
            "operations": {},
        }
        quota_file.write_text(json.dumps(init_data), encoding="utf-8")

        from src.quota.youtube_quota import consume
        result = consume(100, "upload")

        assert result is False

    def test_can_upload_returns_bool(self, tmp_path, monkeypatch):
        """can_upload()가 bool을 반환한다."""
        quota_file = tmp_path / "youtube_quota_daily.json"
        monkeypatch.setattr("src.quota.youtube_quota.QUOTA_FILE", quota_file)

        from src.quota.youtube_quota import can_upload
        result = can_upload()

        assert isinstance(result, bool)

    def test_defer_job_appends_to_quota(self, tmp_path, monkeypatch):
        """defer_job이 quota 파일의 deferred_jobs에 항목을 추가한다."""
        quota_file = tmp_path / "youtube_quota_daily.json"
        monkeypatch.setattr("src.quota.youtube_quota.QUOTA_FILE", quota_file)

        from src.quota.youtube_quota import defer_job, get_quota
        defer_job("run_001", "CH1")

        data = get_quota()
        assert len(data.get("deferred_jobs", [])) >= 1
        assert data["deferred_jobs"][-1]["run_id"] == "run_001"

    def test_daily_reset_on_new_date(self, tmp_path, monkeypatch):
        """날짜가 바뀌면 쿼터가 0으로 초기화된다."""
        quota_file = tmp_path / "youtube_quota_daily.json"
        monkeypatch.setattr("src.quota.youtube_quota.QUOTA_FILE", quota_file)

        # 어제 날짜로 저장
        old_data = {"date": "2000-01-01", "quota_used": 9000, "quota_limit": 10000,
                    "quota_remaining": 1000, "deferred_jobs": []}
        quota_file.write_text(json.dumps(old_data), encoding="utf-8")

        from src.quota.youtube_quota import get_quota
        data = get_quota()  # 오늘 날짜로 리셋

        assert data["quota_used"] == 0
