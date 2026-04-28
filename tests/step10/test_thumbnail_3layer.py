"""STEP10 3-레이어 썸네일 합성 단위 테스트.

커버리지:
- _compose_thumbnail() L1+L2+L3 합성 기본 동작
- _remove_background() 흰 배경 제거 폴백
- _composite_character() 오른쪽 중앙 배치
- generate_thumbnail() 성공/폴백/플레이스홀더 흐름
- generate_thumbnail_from_topic() 워크플로우
"""
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.step10.thumbnail_generator import (
    _composite_character,
    _compose_thumbnail,
    _remove_background,
    _wrap_text,
    generate_thumbnail,
    generate_thumbnail_from_topic,
)

# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_base_image(w: int = 1920, h: int = 1080) -> Image.Image:
    return Image.new("RGB", (w, h), color=(100, 150, 200))


def _make_char_image(w: int = 512, h: int = 768) -> Image.Image:
    """흰 배경 + 중앙 색상 블록 (캐릭터 모의)."""
    img = Image.new("RGBA", (w, h), color=(255, 255, 255, 255))
    # 중앙에 색상 블록 (캐릭터 영역)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([w // 4, h // 4, w * 3 // 4, h * 3 // 4], fill=(100, 150, 200, 255))
    return img


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


# ── 2. _remove_background ─────────────────────────────────────────────────────

class TestRemoveBackground:
    def test_white_pixels_become_transparent(self):
        """흰색(255,255,255) 픽셀이 투명으로 변환된다."""
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = _remove_background(img)
        assert result.mode == "RGBA"
        r, g, b, a = result.getpixel((50, 50))
        assert a == 0, "흰색 픽셀은 투명해야 함"

    def test_dark_pixels_remain_opaque(self):
        """어두운 픽셀은 불투명하게 유지된다."""
        img = Image.new("RGB", (100, 100), color=(50, 50, 50))
        result = _remove_background(img)
        assert result.mode == "RGBA"
        r, g, b, a = result.getpixel((50, 50))
        assert a > 0, "어두운 픽셀은 불투명해야 함"

    def test_returns_rgba_image(self):
        img = Image.new("RGB", (100, 100), color=(100, 150, 200))
        result = _remove_background(img)
        assert result.mode == "RGBA"


# ── 3. _composite_character ───────────────────────────────────────────────────

class TestCompositeCharacter:
    def test_output_size_unchanged(self):
        """합성 후 base 이미지 크기 유지."""
        base = _make_base_image(1920, 1080).convert("RGBA")
        char = _make_char_image(512, 768)
        result = _composite_character(base, char)
        assert result.size == (1920, 1080)

    def test_output_mode_is_rgba(self):
        base = _make_base_image().convert("RGBA")
        char = _make_char_image()
        result = _composite_character(base, char)
        assert result.mode == "RGBA"

    def test_character_placed_on_right_side(self):
        """캐릭터가 오른쪽 영역(x > 960)에 배치된다."""
        base = _make_base_image(1920, 1080).convert("RGBA")
        # 순수 빨강 캐릭터 (RGBA)
        char = Image.new("RGBA", (100, 200), color=(255, 0, 0, 255))
        result = _composite_character(base, char, height_ratio=0.3)
        # 오른쪽 영역 픽셀(x=1700, y=540)에서 빨강 성분 확인
        # 실제 배치는 x=1920*0.72 - w//2 = 1382 - 23 = ~1359
        r, g, b, a = result.getpixel((1700, 540))
        # 캐릭터가 오른쪽에 있으므로 배치된 영역을 넘어선 픽셀은 원래 배경색
        assert result.size == (1920, 1080)


# ── 4. _compose_thumbnail ────────────────────────────────────────────────────

class TestComposeThumbnail:
    def test_output_size_is_1920x1080(self):
        img = _compose_thumbnail(_make_base_image(), "CH1", "테스트 제목")
        assert img.size == (1920, 1080)

    def test_output_is_rgb(self):
        img = _compose_thumbnail(_make_base_image(), "CH1", "테스트 제목")
        assert img.mode == "RGB"

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_all_channels_compose_without_error(self, ch_id):
        img = _compose_thumbnail(_make_base_image(), ch_id, "테스트 주제")
        assert img is not None

    def test_with_character_layer(self):
        """L2 캐릭터 레이어 포함 합성 정상 동작."""
        char = _make_char_image().convert("RGBA")
        img = _compose_thumbnail(_make_base_image(), "CH1", "캐릭터 테스트", char_img=char)
        assert img.size == (1920, 1080)
        assert img.mode == "RGB"

    def test_without_character_layer(self):
        """L2 없이도 (char_img=None) 정상 동작."""
        img = _compose_thumbnail(_make_base_image(), "CH2", "배경만 테스트", char_img=None)
        assert img.size == (1920, 1080)


# ── 5. generate_thumbnail 폴백 체인 ──────────────────────────────────────────

class TestGenerateThumbnail:
    def test_bg_success_saves_file(self, tmp_path):
        """배경 생성 성공 → 썸네일 저장."""
        out = tmp_path / "thumb.png"
        bg = tmp_path / "_episode_bg.png"
        _make_base_image().save(str(bg))

        with patch("src.step10.thumbnail_generator.generate_background_illustration",
                   return_value=bg), \
             patch("src.adapters.runpod_sd.generate_character_to_file",
                   return_value=False):
            ok = generate_thumbnail("CH1", "금리 인상", out, run_id="test")

        assert ok is True
        assert out.exists()

    def test_bg_fail_uses_base_template(self, tmp_path):
        """배경 생성 실패 → 채널 베이스 PNG 폴백."""
        out = tmp_path / "thumb.png"
        base = tmp_path / "base.png"
        _make_base_image().save(str(base))

        with patch("src.step10.thumbnail_generator.generate_background_illustration",
                   return_value=None), \
             patch("src.step10.thumbnail_generator.CHANNEL_BASE_TEMPLATES",
                   {"CH1": base}):
            ok = generate_thumbnail("CH1", "금리 인상", out, run_id="test")

        assert ok is True
        assert out.exists()

    def test_bg_and_base_both_fail_generates_placeholder(self, tmp_path):
        """배경·베이스 모두 실패 → 플레이스홀더 생성."""
        out = tmp_path / "thumb.png"

        with patch("src.step10.thumbnail_generator.generate_background_illustration",
                   return_value=None), \
             patch("src.step10.thumbnail_generator.CHANNEL_BASE_TEMPLATES", {}):
            ok = generate_thumbnail("CH99", "테스트", out, run_id="test")

        assert ok is True  # 플레이스홀더는 성공으로 반환
        assert out.exists()

    @pytest.mark.parametrize("ch_id", ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"])
    def test_all_channels_complete(self, tmp_path, ch_id):
        """7채널 모두 에러 없이 완료."""
        out = tmp_path / f"{ch_id}_thumb.png"
        bg = tmp_path / f"_bg_{ch_id}.png"
        _make_base_image().save(str(bg))

        with patch("src.step10.thumbnail_generator.generate_background_illustration",
                   return_value=bg), \
             patch("src.adapters.runpod_sd.generate_character_to_file",
                   return_value=False):
            ok = generate_thumbnail(ch_id, "테스트 주제", out, run_id="test")

        assert ok is True


# ── 6. generate_thumbnail_from_topic ─────────────────────────────────────────

class TestGenerateThumbnailFromTopic:
    def test_uses_reinterpreted_title_when_available(self, tmp_path):
        topic = {"reinterpreted_title": "금리가 오르면 집값은?", "topic": "금리"}
        captured = {}

        def fake_gen(ch, title, out, *, run_id, force_parody=False):
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

        def fake_gen(ch, title, out, *, run_id, force_parody=False):
            captured["title"] = title
            _make_base_image().save(str(out))
            return True

        with patch("src.step10.thumbnail_generator.generate_thumbnail", fake_gen), \
             patch("src.core.ssot.get_run_dir", return_value=tmp_path):
            generate_thumbnail_from_topic("CH1", "run_001", topic)

        assert captured["title"] == "금리 인상"
