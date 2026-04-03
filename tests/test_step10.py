"""Phase D-4 — Step10 제목/썸네일 변형 빌더 단위 테스트."""

import json
import sys
import types
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _mock_genai():
    """google.generativeai 네임스페이스 오염 없이 mock 등록."""
    import google as _google_pkg
    _genai_mock = types.ModuleType("google.generativeai")
    _genai_mock.configure = MagicMock()
    _genai_mock.GenerativeModel = MagicMock()
    _genai_mock.GenerationConfig = MagicMock(return_value={})
    sys.modules["google.generativeai"] = _genai_mock
    setattr(_google_pkg, "generativeai", _genai_mock)
    return _genai_mock


class TestRunStep10:
    @pytest.fixture(autouse=True)
    def patch_genai(self):
        _mock_genai()
        yield

    def _make_run_dir(self, tmp_path: Path, channel_id="CH1", run_id="run_001"):
        run_dir = tmp_path / "runs" / channel_id / run_id
        step08_dir = run_dir / "step08"
        step08_dir.mkdir(parents=True)
        return run_dir, step08_dir

    def test_returns_false_when_script_missing(self, tmp_path, monkeypatch):
        """script.json이 없으면 False를 반환한다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        run_dir, step08_dir = self._make_run_dir(tmp_path)
        # script.json 미생성

        from src.step10.title_variant_builder import run_step10
        result = run_step10("CH1", "run_001")

        assert result is False

    def test_returns_true_and_creates_files(self, tmp_path, monkeypatch):
        """정상 실행 시 True를 반환하고 variants 파일을 생성한다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        run_dir, step08_dir = self._make_run_dir(tmp_path)

        script = {
            "title_candidates": ["금리 인하 영향"],
            "seo": {"primary_keyword": "금리"},
        }
        (step08_dir / "script.json").write_text(
            json.dumps(script, ensure_ascii=False), encoding="utf-8"
        )

        fake_variants = [
            {"ref": "v1", "mode": "authority", "title": "금리 인하의 비밀"},
            {"ref": "v2", "mode": "curiosity", "title": "당신의 돈이 달라진다"},
            {"ref": "v3", "mode": "benefit",   "title": "금리 인하로 재테크"},
        ]

        with patch("src.step10.title_variant_builder._generate_titles",
                   return_value=fake_variants), \
             patch("src.step10.title_variant_builder.generate_thumbnail"):
            from src.step10.title_variant_builder import run_step10
            result = run_step10("CH1", "run_001")

        assert result is True
        assert (step08_dir / "variants" / "title_variants.json").exists()
        assert (step08_dir / "variants" / "variant_manifest.json").exists()

    def test_title_variants_json_contains_variants(self, tmp_path, monkeypatch):
        """title_variants.json에 variants 배열이 저장된다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        run_dir, step08_dir = self._make_run_dir(tmp_path)

        script = {"title_candidates": ["주제"], "seo": {"primary_keyword": "주제"}}
        (step08_dir / "script.json").write_text(
            json.dumps(script), encoding="utf-8"
        )
        fake_variants = [
            {"ref": "v1", "mode": "authority", "title": "제목1"},
        ]

        with patch("src.step10.title_variant_builder._generate_titles",
                   return_value=fake_variants), \
             patch("src.step10.title_variant_builder.generate_thumbnail"):
            from src.step10.title_variant_builder import run_step10
            run_step10("CH1", "run_001")

        data = json.loads(
            (step08_dir / "variants" / "title_variants.json").read_text(encoding="utf-8-sig")
        )
        assert data["title_variant_count"] == 3
        assert len(data["variants"]) == 1  # fake_variants 길이


class TestGetPreferredMode:
    def test_returns_default_curiosity_when_no_bias(self, tmp_path, monkeypatch):
        """topic_priority_bias.json이 없으면 기본값 'curiosity'를 반환한다."""
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)

        from src.step10.title_variant_builder import _get_preferred_mode
        result = _get_preferred_mode("CH1")

        assert result == "curiosity"

    def test_returns_highest_weight_mode(self, tmp_path, monkeypatch):
        """bias 파일에서 가중치가 가장 높은 mode를 반환한다."""
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.step10.title_variant_builder.MEMORY_DIR", tmp_path)
        bias = {"title_mode_weights": {"authority": 0.5, "curiosity": 0.3, "benefit": 0.2}}
        (tmp_path / "topic_priority_bias.json").write_text(
            json.dumps(bias), encoding="utf-8"
        )

        from src.step10.title_variant_builder import _get_preferred_mode
        result = _get_preferred_mode("CH1")

        assert result == "authority"
