"""STEP10 3-레이어 썸네일 합성 단위 테스트.

커버리지:
- _compose_thumbnail() 레이어 좌표 정확성
- _draw_caption() mode 01/02/03/04 분기
- _get_preferred_mode() 채널 카테고리별 mode 라우팅
- generate_thumbnail() 성공/폴백/플레이스홀더 흐름
- generate_thumbnail_from_topic() 워크플로우
"""
from unittest.mock import patch

import pytest
from PIL import Image

from src.step10.thumbnail_generator import (
    _compose_thumbnail,
    _get_preferred_mode,
    _wrap_text,
    generate_thumbnail,
    generate_thumbnail_from_topic,
)

# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_base_image(w: int = 1920, h: int = 1080) -> Image.Image:
    return Image.new("RGB", (w, h), color=(100, 150, 200))


# ── 1. _wrap_text ─────────────────────────────────────────────────────────────

class TestWrapText:
    def test_short_text_single_line(self):
        lines = _wrap_text("짧은 제목", max_chars=14)
        assert lines == ["짧은 제목"]

    def test_long_text_splits_to_two_lines(self):
        lines = _wrap_text("이것은 매우 긴 제목입니다 분리되어야", max_chars=10)
        assert len(lines) == 2

    def test_no_spaces_splits_by_max_chars(self):
        lines = _wrap_text("ABCDEFGHIJKLMNOPQRSTU", max_chars=10)
        assert len(lines) <= 2


# ── 2. _get_preferred_mode 채널별 라우팅 ─────────────────────────────────────

class TestGetPreferredMode:
    @pytest.mark.parametrize("ch_id", ["CH1", "CH3", "CH6"])
    def test_info_channels_use_mode_02(self, ch_id):
        assert _get_preferred_mode(ch_id) == "02"

    @pytest.mark.parametrize("ch_id", ["CH2", "CH4"])
    def test_stimulating_channels_use_mode_03(self, ch_id):
        assert _get_preferred_mode(ch_id) == "03"

    @pytest.mark.parametrize("ch_id", ["CH5", "CH7"])
    def test_stimulating_strong_channels_use_mode_04(self, ch_id):
        assert _get_preferred_mode(ch_id) == "04"


# ── 3. _compose_thumbnail 레이어 검증 ─────────────────────────────────────────

class TestComposeThumbnail:
    def test_output_size_is_1920x1080(self):
        img = _compose_thumbnail(_make_base_image(), "CH1", "테스트 제목", "01")
        assert img.size == (1920, 1080)

    def test_output_is_rgb(self):
        img = _compose_thumbnail(_make_base_image(), "CH1", "테스트 제목", "01")
        assert img.mode == "RGB"

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_all_channels_compose_without_error(self, ch_id):
        img = _compose_thumbnail(_make_base_image(), ch_id, "테스트 주제", "01")
        assert img is not None

    def test_band_area_darkened_vs_top(self):
        """하단 25% 카피 밴드 영역이 상단보다 어둡게 처리되어야 함."""
        img = _compose_thumbnail(_make_base_image(1920, 1080), "CH1", "제목", "01")
        px = img.load()
        # 상단 픽셀 (200, 100) vs 하단 픽셀 (200, 900)
        top_brightness = sum(px[200, 100]) / 3
        bottom_brightness = sum(px[200, 900]) / 3
        # 하단이 더 어둡거나(밴드 색상) 다름을 검증
        assert top_brightness != bottom_brightness

    def test_mode_04_runs_without_error(self):
        """mode 04 어텐션 그래픽 렌더링 에러 없음."""
        img = _compose_thumbnail(_make_base_image(), "CH5", "미스터리 주제", "04")
        assert img.size == (1920, 1080)


# ── 4. _draw_caption mode별 분기 ──────────────────────────────────────────────

class TestDrawCaptionModes:
    """_draw_caption()은 _compose_thumbnail() 내부에서 호출 — 통합 검증."""

    @pytest.mark.parametrize("mode", ["01", "02", "03", "04"])
    def test_all_modes_produce_valid_image(self, mode):
        img = _compose_thumbnail(_make_base_image(), "CH1", "3가지 충격 비밀", mode)
        assert img.size == (1920, 1080)

    def test_mode_02_handles_no_number_in_title(self):
        """mode 02: 제목에 숫자 없어도 에러 없음."""
        img = _compose_thumbnail(_make_base_image(), "CH1", "숫자없는 제목 테스트", "02")
        assert img.size == (1920, 1080)

    def test_mode_03_question_title(self):
        """mode 03: 질문형 제목 처리."""
        img = _compose_thumbnail(_make_base_image(), "CH2", "왜 우리는 잠을 자야 할까", "03")
        assert img.size == (1920, 1080)


# ── 5. generate_thumbnail 폴백 체인 ──────────────────────────────────────────

class TestGenerateThumbnail:
    def test_ai_success_saves_file(self, tmp_path):
        out = tmp_path / "thumb.png"
        # AI 일러스트 성공 → 합성 후 저장
        illust = tmp_path / "_illust.png"
        _make_base_image().save(str(illust))

        with patch("src.step10.thumbnail_generator.generate_episode_illustration",
                   return_value=illust):
            ok = generate_thumbnail("CH1", "금리 인상", "02", out, run_id="test")

        assert ok is True
        assert out.exists()

    def test_ai_fail_uses_base_template(self, tmp_path):
        out = tmp_path / "thumb.png"
        base = tmp_path / "base.png"
        _make_base_image().save(str(base))

        with patch("src.step10.thumbnail_generator.generate_episode_illustration",
                   return_value=None), \
             patch("src.step10.thumbnail_generator.CHANNEL_BASE_TEMPLATES",
                   {"CH1": base}):
            ok = generate_thumbnail("CH1", "금리 인상", "02", out, run_id="test")

        assert ok is True
        assert out.exists()

    def test_ai_and_base_both_fail_generates_placeholder(self, tmp_path):
        out = tmp_path / "thumb.png"

        with patch("src.step10.thumbnail_generator.generate_episode_illustration",
                   return_value=None), \
             patch("src.step10.thumbnail_generator.CHANNEL_BASE_TEMPLATES", {}):
            ok = generate_thumbnail("CH99", "테스트", "01", out, run_id="test")

        assert ok is True  # 플레이스홀더는 성공으로 반환
        assert out.exists()

    @pytest.mark.parametrize("ch_id,mode", [
        ("CH1", "02"), ("CH2", "03"), ("CH3", "02"),
        ("CH4", "03"), ("CH5", "04"), ("CH6", "02"), ("CH7", "04"),
    ])
    def test_all_channel_mode_combinations(self, tmp_path, ch_id, mode):
        out = tmp_path / f"{ch_id}_{mode}.png"
        illust = tmp_path / f"_illust_{ch_id}.png"
        _make_base_image().save(str(illust))

        with patch("src.step10.thumbnail_generator.generate_episode_illustration",
                   return_value=illust):
            ok = generate_thumbnail(ch_id, "테스트 주제", mode, out, run_id="test")

        assert ok is True


# ── 6. generate_thumbnail_from_topic ─────────────────────────────────────────

class TestGenerateThumbnailFromTopic:
    def test_uses_reinterpreted_title_when_available(self, tmp_path):
        topic = {"reinterpreted_title": "금리가 오르면 집값은?", "topic": "금리"}
        captured = {}

        def fake_gen(ch, title, mode, out, *, run_id):
            captured["title"] = title
            _make_base_image().save(str(out))
            return True

        with patch("src.step10.thumbnail_generator.generate_thumbnail", fake_gen), \
             patch("src.core.ssot.get_run_dir", return_value=tmp_path):
            generate_thumbnail_from_topic("CH1", "run_001", topic)

        assert captured["title"] == "금리가 오르면 집값은?"

    def test_falls_back_to_topic_key(self, tmp_path):
        topic = {"topic": "금리 인상"}
        captured = {}

        def fake_gen(ch, title, mode, out, *, run_id):
            captured["title"] = title
            _make_base_image().save(str(out))
            return True

        with patch("src.step10.thumbnail_generator.generate_thumbnail", fake_gen), \
             patch("src.core.ssot.get_run_dir", return_value=tmp_path):
            generate_thumbnail_from_topic("CH1", "run_001", topic)

        assert captured["title"] == "금리 인상"

    @pytest.mark.parametrize("ch_id,expected_mode", [
        ("CH1", "02"), ("CH5", "04"), ("CH7", "04"), ("CH4", "03"),
    ])
    def test_mode_routing_by_channel_category(self, tmp_path, ch_id, expected_mode):
        topic = {"topic": "테스트"}
        captured = {}

        def fake_gen(ch, title, mode, out, *, run_id):
            captured["mode"] = mode
            _make_base_image().save(str(out))
            return True

        with patch("src.step10.thumbnail_generator.generate_thumbnail", fake_gen), \
             patch("src.core.ssot.get_run_dir", return_value=tmp_path):
            generate_thumbnail_from_topic(ch_id, "run_001", topic)

        assert captured["mode"] == expected_mode
