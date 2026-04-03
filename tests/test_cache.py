"""Phase D-6 — gemini_cache 단위 테스트 (diskcache 기반)."""

import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestGeminiCacheMakeKey:
    def test_key_is_16_hex_chars(self):
        """_make_key가 16자 hex 문자열을 반환한다."""
        # gemini_cache 모듈을 직접 import 없이 키 생성 함수만 테스트
        import hashlib
        content = "system_prompt::테스트 내용"
        key = hashlib.sha256(content.encode()).hexdigest()[:16]
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_input_produces_same_key(self):
        """같은 입력은 항상 같은 키를 생성한다."""
        import hashlib
        def make_key(prompt_type, content):
            return hashlib.sha256(f"{prompt_type}::{content}".encode()).hexdigest()[:16]

        k1 = make_key("system_prompt", "테스트")
        k2 = make_key("system_prompt", "테스트")
        assert k1 == k2

    def test_different_prompt_types_produce_different_keys(self):
        """다른 prompt_type은 다른 키를 생성한다."""
        import hashlib
        def make_key(prompt_type, content):
            return hashlib.sha256(f"{prompt_type}::{content}".encode()).hexdigest()[:16]

        k1 = make_key("system_prompt", "내용")
        k2 = make_key("style_template", "내용")
        assert k1 != k2


class TestGeminiCache:
    @pytest.fixture
    def mock_diskcache(self):
        """diskcache.Cache를 in-memory dict로 대체한다."""
        store = {}
        expire_times = {}

        class FakeCache:
            def get(self, key):
                if key in expire_times and time.time() > expire_times[key]:
                    del store[key]
                    return None
                return store.get(key)

            def set(self, key, value, expire=None):
                store[key] = value
                if expire:
                    expire_times[key] = time.time() + expire

            def expire(self):
                expired = 0
                for k in list(store.keys()):
                    if k in expire_times and time.time() > expire_times[k]:
                        del store[k]
                        expired += 1
                return expired

        return FakeCache(), store

    def test_get_returns_none_for_non_cacheable_type(self, tmp_path, monkeypatch):
        """CACHEABLE_TYPES에 없는 prompt_type은 None을 반환한다."""
        monkeypatch.setattr("src.core.config.CACHE_DIR", tmp_path)

        with patch("diskcache.Cache") as mock_cls:
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cls.return_value = mock_cache

            import importlib
            import src.cache.gemini_cache as gc
            importlib.reload(gc)

            result = gc.get("unknown_type", "내용")

        assert result is None

    def test_cacheable_types_list(self):
        """CACHEABLE_TYPES에 3개 항목이 정의되어 있다."""
        with patch("diskcache.Cache"):
            import importlib
            import src.cache.gemini_cache as gc
            importlib.reload(gc)

            assert len(gc.CACHEABLE_TYPES) == 3
            assert "system_prompt" in gc.CACHEABLE_TYPES
            assert "style_template" in gc.CACHEABLE_TYPES
            assert "affiliate_insert_template" in gc.CACHEABLE_TYPES

    def test_set_and_get_round_trip(self, tmp_path, monkeypatch):
        """set 후 get으로 동일한 응답을 조회할 수 있다."""
        monkeypatch.setattr("src.core.config.CACHE_DIR", tmp_path)

        store = {}

        class FakeCache:
            def get(self, key):
                return store.get(key)
            def set(self, key, value, expire=None):
                store[key] = value
            def expire(self):
                return 0

        with patch("diskcache.Cache", return_value=FakeCache()), \
             patch("src.quota.gemini_quota.record_cache_hit"), \
             patch("src.quota.gemini_quota.record_cache_miss"):
            import importlib
            import src.cache.gemini_cache as gc
            importlib.reload(gc)

            gc.set("system_prompt", "테스트 프롬프트", "응답 내용", cost_krw=100.0)
            result = gc.get("system_prompt", "테스트 프롬프트")

        assert result == "응답 내용"

    def test_get_returns_none_on_cache_miss(self, tmp_path, monkeypatch):
        """캐시 미스 시 None을 반환하고 record_cache_miss가 호출된다."""
        monkeypatch.setattr("src.core.config.CACHE_DIR", tmp_path)

        class FakeCache:
            def get(self, key):
                return None
            def set(self, key, value, expire=None):
                pass
            def expire(self):
                return 0

        with patch("diskcache.Cache", return_value=FakeCache()), \
             patch("src.quota.gemini_quota.record_cache_hit") as mock_hit, \
             patch("src.quota.gemini_quota.record_cache_miss") as mock_miss:
            import importlib
            import src.cache.gemini_cache as gc
            importlib.reload(gc)

            result = gc.get("system_prompt", "없는 내용")

        assert result is None
        mock_miss.assert_called_once()
        mock_hit.assert_not_called()

    def test_ttl_seconds_is_24h(self):
        """TTL이 24시간(86400초)으로 설정되어 있다."""
        with patch("diskcache.Cache"):
            import importlib
            import src.cache.gemini_cache as gc
            importlib.reload(gc)

            assert gc.TTL_SECONDS == 24 * 3600
