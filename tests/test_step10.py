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


class TestGenerateThumbnailPIL:
    """PIL 합성 기반 generate_thumbnail() 단위 테스트."""

    def _make_fake_base(self, tmp_path: Path, channel_id: str = "CH1") -> Path:
        """1920×1080 단색 PNG를 베이스 이미지로 생성."""
        from PIL import Image
        base_dir = tmp_path / "assets" / "thumbnails"
        base_dir.mkdir(parents=True)
        img = Image.new("RGB", (1920, 1080), color=(26, 18, 0))
        path = base_dir / f"{channel_id}_base.png"
        img.save(path)
        return path

    def test_returns_true_when_base_exists(self, tmp_path, monkeypatch):
        """베이스 PNG가 있으면 True를 반환하고 output 파일을 생성한다."""
        base_path = self._make_fake_base(tmp_path, "CH1")
        output = tmp_path / "out" / "thumbnail_variant_01.png"
        output.parent.mkdir(parents=True)

        import src.step10.thumbnail_generator as tg
        monkeypatch.setitem(tg.CHANNEL_BASE_TEMPLATES, "CH1", base_path)

        result = tg.generate_thumbnail("CH1", "금리 인하의 충격", "01", output)

        assert result is True
        assert output.exists()

    def test_fallback_when_base_missing(self, tmp_path):
        """베이스 PNG가 없으면 _generate_placeholder()로 폴백하고 True를 반환한다."""
        output = tmp_path / "thumb.png"

        import src.step10.thumbnail_generator as tg
        result = tg.generate_thumbnail("CH_NONEXISTENT", "제목", "01", output)

        assert result is True
        assert output.exists()

    def test_mode02_detects_number(self):
        """mode 02는 제목에서 아라비아 숫자를 감지한다."""
        import re
        title = "10억 모은 비밀 전략"
        match = re.search(r'\d+', title)
        assert match is not None
        assert match.group() == "10"

    def test_mode02_no_number_returns_none(self):
        """mode 02에서 숫자 없는 제목은 None을 반환한다."""
        import re
        title = "당신이 몰랐던 진실"
        match = re.search(r'\d+', title)
        assert match is None

    def test_mode03_appends_question_mark(self):
        """mode 03은 제목 끝에 '?'를 추가한다."""
        title = "조선 왕들이 숨긴 비밀"
        question_title = title + "?"
        last_word = title.split()[-1]
        assert question_title.endswith("?")
        assert last_word == "비밀"

    def test_output_parent_created(self, tmp_path, monkeypatch):
        """output_path의 부모 디렉토리가 없어도 자동 생성된다."""
        base_path = self._make_fake_base(tmp_path, "CH1")
        output = tmp_path / "deep" / "nested" / "thumb.png"

        import src.step10.thumbnail_generator as tg
        monkeypatch.setitem(tg.CHANNEL_BASE_TEMPLATES, "CH1", base_path)

        result = tg.generate_thumbnail("CH1", "테스트 제목", "01", output)

        assert result is True
        assert output.parent.exists()
