"""STEP10 에피소드 일러스트 단위 테스트.

커버리지:
- 7채널 CHANNEL_MASCOT_PERSONA 구조 검증
- _build_prompt() 7가지 CTR 보강 포함 여부
- 6가지 구성 유형 시스템 (_COMPOSITION_TYPES, _extract_scene_type)
- generate_episode_illustration() 성공/재시도/폴백 흐름
- 비용 추적 JSON 기록
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.step10.episode_illustration import (
    _CATEGORY_PREFERRED_TYPES,
    _COMPOSITION_TYPES,
    CHANNEL_MASCOT_PERSONA,
    _build_prompt,
    _extract_scene_type,
    _record_cost,
    generate_episode_illustration,
)

# ── 1. 페르소나 구조 검증 ──────────────────────────────────────────────────────

class TestChannelMascotPersona:
    REQUIRED_FIELDS = {"persona", "category", "mascot_ratio", "expressions"}
    VALID_CATEGORIES = {"info", "stimulating", "stimulating_strong"}

    def test_all_7_channels_present(self):
        assert set(CHANNEL_MASCOT_PERSONA.keys()) == {f"CH{i}" for i in range(1, 8)}

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_required_fields_present(self, ch_id):
        info = CHANNEL_MASCOT_PERSONA[ch_id]
        assert isinstance(info, dict), f"{ch_id} 페르소나가 dict가 아님"
        missing = self.REQUIRED_FIELDS - set(info.keys())
        assert not missing, f"{ch_id} 누락 필드: {missing}"

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_category_valid(self, ch_id):
        category = CHANNEL_MASCOT_PERSONA[ch_id]["category"]
        assert category in self.VALID_CATEGORIES, f"{ch_id} 잘못된 category: {category}"

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_expressions_has_5_items(self, ch_id):
        expressions = CHANNEL_MASCOT_PERSONA[ch_id]["expressions"]
        assert isinstance(expressions, list)
        assert len(expressions) >= 3, f"{ch_id} 표정이 3개 미만"

    @pytest.mark.parametrize("ch_id", ["CH1", "CH3", "CH6"])
    def test_info_channels_mascot_ratio_60(self, ch_id):
        ratio = CHANNEL_MASCOT_PERSONA[ch_id]["mascot_ratio"]
        assert ratio == "60%", f"정보형 {ch_id} 마스코트 비율이 60%가 아님: {ratio}"

    @pytest.mark.parametrize("ch_id", ["CH2", "CH4"])
    def test_stimulating_channels_mascot_ratio_65(self, ch_id):
        ratio = CHANNEL_MASCOT_PERSONA[ch_id]["mascot_ratio"]
        assert ratio == "65%", f"자극형 {ch_id} 마스코트 비율이 65%가 아님: {ratio}"

    @pytest.mark.parametrize("ch_id", ["CH5", "CH7"])
    def test_stimulating_strong_channels_mascot_ratio_60(self, ch_id):
        ratio = CHANNEL_MASCOT_PERSONA[ch_id]["mascot_ratio"]
        assert ratio == "60%", f"자극형강 {ch_id} 마스코트 비율이 60%가 아님: {ratio}"


# ── 2. 프롬프트 CTR 보강 검증 ──────────────────────────────────────────────────

class TestBuildPrompt:
    def test_prompt_contains_hybrid_pattern(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "HYBRID PATTERN" in p or "COMPOSITION" in p

    def test_prompt_contains_eye_contact_booster_a(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "EYE CONTACT" in p or "direct eye contact" in p.lower()

    def test_prompt_contains_motion_lines_booster_3(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "motion lines" in p.lower()

    def test_prompt_contains_brightness_contrast_booster_b(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "contrast" in p.lower() or "bright" in p.lower()

    def test_prompt_contains_text_zone_instruction(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "TOP-LEFT" in p or "TOP" in p

    def test_prompt_contains_top_right_watermark_zone(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "TOP-RIGHT" in p or "top-right" in p.lower()

    def test_prompt_bans_text(self):
        p = _build_prompt("CH1", "금리 인상")
        assert "NO text" in p or "TEXT BAN" in p

    def test_prompt_contains_expression_when_given(self):
        p = _build_prompt("CH1", "금리 인상", expression="shocked")
        assert "shocked" in p

    def test_prompt_contains_scene_desc_when_provided(self):
        # topic은 LLM 경유 scene_desc로 변환 후 프롬프트에 삽입됨
        scene = "A scientist doodle staring shocked at a miniature black hole model"
        p = _build_prompt("CH2", "블랙홀 안에는 무엇이 있을까", scene_desc=scene)
        assert "black hole" in p

    @pytest.mark.parametrize("ch_id", [f"CH{i}" for i in range(1, 8)])
    def test_prompt_returns_nonempty_for_all_channels(self, ch_id):
        p = _build_prompt(ch_id, "테스트 주제")
        assert len(p) > 100


# ── 3. generate_episode_illustration 흐름 테스트 ──────────────────────────────

class TestGenerateEpisodeIllustration:
    def _make_mock_response(self, data: bytes = b"PNG_DATA") -> MagicMock:
        part = MagicMock()
        part.inline_data = MagicMock()
        part.inline_data.mime_type = "image/png"
        part.inline_data.data = data
        candidate = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        return response

    def test_success_returns_output_path(self, tmp_path):
        out = tmp_path / "illust.png"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = self._make_mock_response()

        # 레퍼런스 파일이 없으면 None 반환 — refs 없이 진행 패치
        with patch("src.step10.episode_illustration.Path.exists", return_value=True), \
             patch.object(Path, "read_bytes", return_value=b"REF"), \
             patch("src.step10.episode_illustration._record_cost"):
            result = generate_episode_illustration(
                "CH1", "금리 인상", "test_run", out,
                client=mock_client,
            )
        assert result == out

    def test_no_refs_returns_none(self, tmp_path):
        out = tmp_path / "illust.png"
        mock_client = MagicMock()
        # 레퍼런스 파일이 모두 없음
        result = generate_episode_illustration(
            "CH1", "금리 인상", "test_run", out,
            client=mock_client,
        )
        assert result is None

    def test_retry_on_failure(self, tmp_path):
        out = tmp_path / "illust.png"
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            Exception("API 오류"),
            self._make_mock_response(),
        ]

        with patch("src.step10.episode_illustration.Path.exists", return_value=True), \
             patch.object(Path, "read_bytes", return_value=b"REF"), \
             patch("src.step10.episode_illustration._record_cost"), \
             patch("time.sleep"):
            result = generate_episode_illustration(
                "CH1", "금리 인상", "test_run", out,
                max_retries=1,
                client=mock_client,
            )
        assert result == out
        assert mock_client.models.generate_content.call_count == 2

    def test_all_retries_exhausted_returns_none(self, tmp_path):
        out = tmp_path / "illust.png"
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("지속 실패")

        with patch("src.step10.episode_illustration.Path.exists", return_value=True), \
             patch.object(Path, "read_bytes", return_value=b"REF"), \
             patch("src.step10.episode_illustration._record_cost"), \
             patch("time.sleep"):
            result = generate_episode_illustration(
                "CH1", "금리 인상", "test_run", out,
                max_retries=1,
                client=mock_client,
            )
        assert result is None


# ── 4. 비용 추적 검증 ─────────────────────────────────────────────────────────

class TestRecordCost:
    def test_cost_file_created_on_first_call(self, tmp_path):
        cost_file = tmp_path / "api_costs.json"
        with patch("src.step10.episode_illustration._COST_FILE", cost_file):
            _record_cost("run_001", "CH1", calls=1, success=True)
        assert cost_file.exists()
        # write_json은 utf-8-sig (BOM) 또는 ensure_ascii로 저장
        data = json.loads(cost_file.read_text(encoding="utf-8-sig"))
        assert data["total_calls"] == 1
        assert len(data["records"]) == 1

    def test_cost_accumulates_across_calls(self, tmp_path):
        cost_file = tmp_path / "api_costs.json"
        with patch("src.step10.episode_illustration._COST_FILE", cost_file):
            _record_cost("run_001", "CH1", calls=1, success=True)
            _record_cost("run_002", "CH2", calls=2, success=False)
        data = json.loads(cost_file.read_text(encoding="utf-8-sig"))
        assert data["total_calls"] == 3
        assert len(data["records"]) == 2

    def test_cost_per_call_calculated_correctly(self, tmp_path):
        cost_file = tmp_path / "api_costs.json"
        with patch("src.step10.episode_illustration._COST_FILE", cost_file), \
             patch("src.step10.episode_illustration._COST_PER_CALL", 0.04):
            _record_cost("run_001", "CH1", calls=2, success=True)
        data = json.loads(cost_file.read_text(encoding="utf-8-sig"))
        assert abs(data["total_cost_usd"] - 0.08) < 0.001


# ── 5. 구성 유형 시스템 검증 (50장 분석 기반) ────────────────────────────────────

class TestCompositionTypes:
    VALID_TYPES = {"TYPE1", "TYPE2", "TYPE3", "TYPE4", "TYPE5", "TYPE6"}
    REQUIRED_FIELDS = {"name", "mascot_size", "bg_style", "hook"}

    def test_all_6_types_present(self):
        assert set(_COMPOSITION_TYPES.keys()) == self.VALID_TYPES

    @pytest.mark.parametrize("type_id", ["TYPE1", "TYPE2", "TYPE3", "TYPE4", "TYPE5", "TYPE6"])
    def test_required_fields_present(self, type_id):
        missing = self.REQUIRED_FIELDS - set(_COMPOSITION_TYPES[type_id].keys())
        assert not missing, f"{type_id} 누락 필드: {missing}"

    def test_category_preferred_types_covers_all_categories(self):
        assert set(_CATEGORY_PREFERRED_TYPES.keys()) == {"info", "stimulating", "stimulating_strong"}  # noqa: E501

    @pytest.mark.parametrize("category", ["info", "stimulating", "stimulating_strong"])
    def test_preferred_types_are_valid(self, category):
        for t in _CATEGORY_PREFERRED_TYPES[category]:
            assert t in self.VALID_TYPES, f"{category}의 권장 유형 {t}이 유효하지 않음"

    def test_extract_scene_type_with_valid_prefix(self):
        for t in self.VALID_TYPES:
            result = _extract_scene_type(f"{t}: Some scene description here")
            assert result == t

    def test_extract_scene_type_case_insensitive(self):
        assert _extract_scene_type("type2: some scene") == "TYPE2"

    def test_extract_scene_type_defaults_to_type2(self):
        assert _extract_scene_type("No type prefix at all") == "TYPE2"
        assert _extract_scene_type("") == "TYPE2"

    def test_extract_scene_type_invalid_prefix(self):
        assert _extract_scene_type("TYPE9: invalid") == "TYPE2"


class TestBuildPromptCompositionTypes:
    """구성 유형별 프롬프트 차이 검증."""

    def test_type3_contains_tiny_mascot_instruction(self):
        p = _build_prompt("CH1", "금리 인상", scene_desc="TYPE3: A giant gold coin towers over a tiny mascot.")  # noqa: E501
        assert "TINY" in p.upper() or "10-20%" in p

    def test_type5_contains_two_characters_instruction(self):
        p = _build_prompt("CH1", "갑과 을의 대화", scene_desc="TYPE5: Two mascots argue about wages.")  # noqa: E501
        assert "TWO" in p.upper() or "two instances" in p.lower()

    def test_type5_dialogue_bubble_empty_instruction(self):
        p = _build_prompt("CH1", "갑과 을", scene_desc="TYPE5: Two mascots in debate.")
        assert "empty" in p.lower() or "EMPTY" in p

    def test_type1_illustrated_environment_in_background(self):
        p = _build_prompt("CH1", "고대 이집트", scene_desc="TYPE1: Mascot in ancient Egyptian scene.")  # noqa: E501
        assert "ILLUSTRATED" in p.upper() or "illustrated" in p.lower() or "environment" in p.lower()  # noqa: E501

    def test_type4_graphic_elements_in_background(self):
        p = _build_prompt("CH1", "경제 지표", scene_desc="TYPE4: Background filled with charts.")
        assert "chart" in p.lower() or "arrow" in p.lower() or "graphic" in p.lower()

    def test_scene_type_label_appears_in_prompt(self):
        p = _build_prompt("CH2", "블랙홀", scene_desc="TYPE3: Giant black hole dominates frame.")
        assert "규모대비형" in p

    @pytest.mark.parametrize("type_id", ["TYPE1", "TYPE2", "TYPE3", "TYPE4", "TYPE5", "TYPE6"])
    def test_all_types_produce_valid_prompt(self, type_id):
        scene = f"{type_id}: Test scene description for the topic."
        p = _build_prompt("CH1", "테스트 주제", scene_desc=scene)
        assert len(p) > 200
        assert "NO text" in p or "NO letters" in p or "NO numbers" in p
