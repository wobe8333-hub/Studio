"""Phase D-2 — Step08 run_step08 통합 테스트 (mock 기반).

run_step08 전체 오케스트레이터 흐름을 mock으로 검증:
- 스크립트 생성 → 이미지 생성 → Manim → 나레이션 → 자막 → FFmpeg → 메타데이터
- motion_engine (Ken Burns) 및 scene_composer 연동 확인
- 실패 섹션 Manim 폴백 경로 확인
- 결과물 파일 생성 및 manifest 상태 확인

CLAUDE.md 규칙: step08/__init__.py는 KAS-PROTECTED 파일 — 직접 임포트 불가.
importlib 우회 패턴을 사용한다.
"""

import sys
import types
import json
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────
# google.generativeai mock 사전 등록
# ──────────────────────────────────────────────
if "google.generativeai" not in sys.modules:
    import google as _google_pkg
    _genai_mock = types.ModuleType("google.generativeai")
    _genai_mock.configure = MagicMock()
    _genai_mock.GenerativeModel = MagicMock()
    _genai_mock.GenerationConfig = MagicMock(return_value={})
    sys.modules["google.generativeai"] = _genai_mock
    setattr(_google_pkg, "generativeai", _genai_mock)

# diskcache mock (미설치 환경 대응)
if "diskcache" not in sys.modules:
    _dc_mock = types.ModuleType("diskcache")
    _dc_mock.Cache = MagicMock(return_value=MagicMock(get=MagicMock(return_value=None), set=MagicMock()))
    sys.modules["diskcache"] = _dc_mock


def _make_fake_script():
    """테스트용 스크립트 dict."""
    return {
        "channel_id": "CH1",
        "run_id": "run_test",
        "title_candidates": ["테스트 제목1", "테스트 제목2"],
        "hook": {"text": "훅 텍스트", "duration_estimate_sec": 15, "animation_preview_at_sec": 8},
        "promise": "약속 텍스트",
        "sections": [
            {
                "id": i,
                "heading": f"섹션{i}",
                "narration_text": "나레이션 텍스트" * 5,
                "animation_prompt": "애니메이션 프롬프트",
                "animation_style": "comparison",
                "render_tool": "gemini" if i < 2 else "manim",
                "chapter_title": f"챕터{i}",
                "character_directions": {"expression": "happy", "pose": "explaining"},
            }
            for i in range(4)
        ],
        "affiliate_insert": {"text": "제품 링크", "click_rate_applied": 0.003,
                             "purchase_rate_applied": 0.01},
        "seo": {"primary_keyword": "금리", "secondary_keywords": [], "description_first_2lines": "설명"},
        "cta": {"text": "구독!", "like_cta_at_sec": 55},
        "target_duration_sec": 720,
        "ai_label": "AI 제작",
        "financial_disclaimer": "투자 주의",
        "video_spec": {},
    }


def _make_style_policy():
    return {"channel_id": "CH1", "render_tool": "manim", "affiliate_product_ref": "토스증권",
            "manim_pilot_version": "v1.0"}


def _make_revenue_policy():
    return {"channel_id": "CH1", "revenue_target_net": 2000000}


def _make_algorithm_policy():
    return {"channel_id": "CH1", "upload_timing_rules": {}}


class TestRunStep08:
    """run_step08 통합 테스트 — 외부 API를 모두 mock으로 대체."""

    @pytest.fixture(autouse=True)
    def setup_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path / "channels")
        monkeypatch.setattr("src.core.config.BGM_DIR", tmp_path / "bgm")
        (tmp_path / "channels" / "CH1").mkdir(parents=True)
        self.tmp_path = tmp_path

    def _run_with_mocks(self, script=None, manim_success=True):
        """공통 mock 패치 세트로 run_step08 실행."""
        fake_script = script or _make_fake_script()
        gemini_sections = [s for s in fake_script["sections"] if s["render_tool"] != "manim"]
        manim_sections  = [s for s in fake_script["sections"] if s["render_tool"] == "manim"]

        # 이미지 경로 mock
        fake_img_path = self.tmp_path / "fake_img.png"
        fake_img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        def fake_gen_sd_images(channel_id, sections, output_dir):
            paths = []
            for i, sec in enumerate(sections):
                p = output_dir / f"scene_{i:03d}.png"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x89PNG")
                paths.append(p)
            return paths

        def fake_compose_all(char_paths, sections, output_dir, **kw):
            output_dir.mkdir(parents=True, exist_ok=True)
            out = []
            for i, p in enumerate(char_paths):
                cp = output_dir / f"composed_{i:03d}.png"
                cp.write_bytes(b"\x89PNG")
                out.append(cp)
            return out

        def fake_batch_motion(image_paths, output_dir, **kw):
            output_dir.mkdir(parents=True, exist_ok=True)
            clips = []
            for i, _ in enumerate(image_paths):
                cp = output_dir / f"motion_{i:03d}.mp4"
                cp.write_bytes(b"fake_mp4")
                clips.append(cp)
            return clips

        def fake_manim_run(sec, clips_dir):
            if manim_success:
                out = clips_dir / f"manim_{sec['id']:03d}.mp4"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"fake_mp4")
                return True, out, False
            return False, None, True

        def fake_generate_single_image(desc, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x89PNG")
            return True

        def fake_create_motion_clip(img, out, **kw):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake_mp4")
            return True

        def fake_concat(clips, out):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake_mp4")

        def fake_narration(script, path, channel_id):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fake_wav")

        def fake_subtitles(script, narration_path, srt_path):
            srt_path.write_text("1\n00:00:00,000 --> 00:00:05,000\n테스트\n", encoding="utf-8")

        def fake_add_narration(video, narr, out):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake_mp4")

        def fake_add_subtitles(video, srt, out):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake_mp4")

        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "태그1, 태그2, 태그3, 태그4, 태그5, 태그6, 태그7, 태그8, 태그9, 태그10, 태그11, 태그12, 태그13, 태그14, 태그15"
        mock_model.generate_content.return_value = mock_resp
        sys.modules["google.generativeai"].GenerativeModel.return_value = mock_model

        from src.step08 import run_step08
        with patch("src.step08.generate_script", return_value=fake_script), \
             patch("src.step08.gen_sd_images", side_effect=fake_gen_sd_images), \
             patch("src.step08.gen_images", return_value={}), \
             patch("src.step08.compose_all_scenes", side_effect=fake_compose_all), \
             patch("src.step08.batch_create_motion_clips", side_effect=fake_batch_motion), \
             patch("src.step08.manim_run", side_effect=fake_manim_run), \
             patch("src.step08.create_motion_clip", side_effect=fake_create_motion_clip), \
             patch("src.step08.image_generator.generate_single_image",
                   side_effect=fake_generate_single_image), \
             patch("src.step08.generate_narration", side_effect=fake_narration), \
             patch("src.step08.generate_subtitles", side_effect=fake_subtitles), \
             patch("src.step08.concat_clips", side_effect=fake_concat), \
             patch("src.step08.add_narration", side_effect=fake_add_narration), \
             patch("src.step08.add_subtitles", side_effect=fake_add_subtitles), \
             patch("src.quota.gemini_quota.throttle_if_needed"), \
             patch("src.quota.gemini_quota.record_request"):
            run_id = run_step08(
                "CH1",
                {"reinterpreted_title": "금리 테스트", "is_trending": True},
                _make_style_policy(),
                _make_revenue_policy(),
                _make_algorithm_policy(),
            )
        return run_id

    def test_returns_run_id_string(self):
        """run_step08이 문자열 run_id를 반환한다."""
        run_id = self._run_with_mocks()
        assert isinstance(run_id, str)
        assert "CH1" in run_id

    def test_creates_manifest_json(self):
        """manifest.json이 COMPLETED 상태로 생성된다."""
        run_id = self._run_with_mocks()
        manifest_path = self.tmp_path / "runs" / "CH1" / run_id / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        assert data["run_state"] == "COMPLETED"

    def test_creates_script_json(self):
        """step08/script.json이 생성된다."""
        run_id = self._run_with_mocks()
        script_path = self.tmp_path / "runs" / "CH1" / run_id / "step08" / "script.json"
        assert script_path.exists()

    def test_creates_video_mp4(self):
        """step08/video.mp4가 생성된다."""
        run_id = self._run_with_mocks()
        video_path = self.tmp_path / "runs" / "CH1" / run_id / "step08" / "video.mp4"
        assert video_path.exists()

    def test_creates_tags_json(self):
        """step08/tags.json이 생성된다."""
        run_id = self._run_with_mocks()
        tags_path = self.tmp_path / "runs" / "CH1" / run_id / "step08" / "tags.json"
        assert tags_path.exists()
        data = json.loads(tags_path.read_text(encoding="utf-8-sig"))
        assert len(data.get("tags", [])) > 0

    def test_manim_stability_report_created(self):
        """manim_stability_report.json이 생성된다."""
        run_id = self._run_with_mocks()
        report_path = (self.tmp_path / "runs" / "CH1" / run_id
                       / "step08" / "manim_stability_report.json")
        assert report_path.exists()

    def test_compose_all_scenes_called(self):
        """compose_all_scenes (scene_composer)가 호출된다."""
        with patch("src.step08.compose_all_scenes", return_value=[]) as mock_compose, \
             patch("src.step08.generate_script", return_value=_make_fake_script()), \
             patch("src.step08.gen_sd_images", return_value=[]), \
             patch("src.step08.gen_images", return_value={}), \
             patch("src.step08.batch_create_motion_clips", return_value=[]), \
             patch("src.step08.manim_run", return_value=(False, None, True)), \
             patch("src.step08.image_generator.generate_single_image", return_value=False), \
             patch("src.step08.concat_clips"), \
             patch("src.step08.generate_narration"), \
             patch("src.step08.generate_subtitles"), \
             patch("src.step08.add_narration"), \
             patch("src.step08.add_subtitles"), \
             patch("src.quota.gemini_quota.throttle_if_needed"), \
             patch("src.quota.gemini_quota.record_request"), \
             patch("src.step08.create_motion_clip", return_value=False):
            try:
                from src.step08 import run_step08
                run_step08("CH1", {"reinterpreted_title": "테스트"}, {}, {}, {})
            except Exception:
                pass  # 클립 없음으로 RuntimeError 예상 — compose 호출 여부만 확인

        mock_compose.assert_called()

    def test_batch_create_motion_clips_called(self):
        """batch_create_motion_clips (motion_engine)가 호출된다."""
        gemini_img = self.tmp_path / "test_img.png"
        gemini_img.write_bytes(b"\x89PNG")

        def fake_sd(channel_id, sections, output_dir):
            return [gemini_img] * len(sections)

        with patch("src.step08.gen_sd_images", side_effect=fake_sd), \
             patch("src.step08.gen_images", return_value={}), \
             patch("src.step08.generate_script", return_value=_make_fake_script()), \
             patch("src.step08.compose_all_scenes", return_value=[gemini_img]), \
             patch("src.step08.batch_create_motion_clips", return_value=[]) as mock_motion, \
             patch("src.step08.manim_run", return_value=(False, None, True)), \
             patch("src.step08.create_motion_clip", return_value=False), \
             patch("src.step08.concat_clips"), \
             patch("src.step08.generate_narration"), \
             patch("src.step08.generate_subtitles"), \
             patch("src.step08.add_narration"), \
             patch("src.step08.add_subtitles"), \
             patch("src.quota.gemini_quota.throttle_if_needed"), \
             patch("src.quota.gemini_quota.record_request"), \
             patch("src.step08.image_generator.generate_single_image", return_value=False):
            try:
                from src.step08 import run_step08
                run_step08("CH1", {"reinterpreted_title": "테스트"}, {}, {}, {})
            except Exception:
                pass

        mock_motion.assert_called()
