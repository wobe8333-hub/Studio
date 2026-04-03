"""E2E 통합 테스트 — CH1 경제 파이프라인 핵심 흐름 검증 (mock 기반)."""

import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestE2EPipelineFlow:
    """CH1 경제 채널의 핵심 파이프라인 흐름 검증."""

    def test_step00_to_step04_channel_init(self, tmp_path, mock_channels_dir):
        """Step00~04: 채널 초기화 → 포트폴리오 계획 흐름."""
        # Step00: 채널 레지스트리
        from src.step00.channel_registry import get_channel, get_active_channels
        ch1 = get_channel("CH1")
        assert isinstance(ch1, dict)

        active = get_active_channels(month_number=1)
        assert "CH1" in active

        # Step04: 포트폴리오 계획
        from src.step04.portfolio_plan import create_portfolio_plan
        plan = create_portfolio_plan(1)
        assert isinstance(plan, dict)
        assert "total_video_target" in plan

    def test_step05_trend_scoring_flow(self, sample_topic_dict):
        """Step05: 주제 점수화 흐름 (순수 계산 함수 — Gemini 불필요)."""
        from src.step05.scorer import score_topic

        # score_topic은 string topic을 받는 순수 계산 함수
        result = score_topic(
            topic="금리 인하 영향",
            category="economy",
            trends_score=0.8,
            news_score=0.6,
            community_score=0.5,
        )

        assert isinstance(result, dict)
        assert "score" in result
        assert "grade" in result
        assert 0.0 <= result["score"] <= 100.0

    def test_step05_knowledge_package_structure(self):
        """Step05: KnowledgePackage 기본 구조 확인."""
        from src.step05.knowledge.knowledge_package import build_empty_package, package_to_dict

        pkg = build_empty_package("금리 인하", "economy", "CH1")
        pkg_dict = package_to_dict(pkg)

        assert pkg_dict["topic"] == "금리 인하"
        assert pkg_dict["category"] == "economy"
        assert isinstance(pkg_dict["core_facts"], list)
        assert isinstance(pkg_dict["sources"], list)
        assert isinstance(pkg_dict["confidence_score"], float)

    def test_step08_character_manager_for_ch1(self):
        """Step08: CH1 캐릭터 매니저 정상 동작."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "character_manager",
            Path("src/step08/character_manager.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ch1_profile = mod.CHARACTER_PROFILES["CH1"]
        assert "name" in ch1_profile
        assert "seed" in ch1_profile

        prompt = mod.build_character_prompt("CH1", "happy", "explaining", "금리 설명 중")
        assert "positive" in prompt
        assert len(prompt["positive"]) > 10

    def test_step08_script_generator_structure(self, sample_topic_dict, mock_channels_dir, tmp_path):
        """Step08: 스크립트 생성 — script_generator 직접 로드 (genai 우회)."""
        import sys, importlib.util, types

        def _load_direct(key, path):
            if key in sys.modules:
                return sys.modules[key]
            spec = importlib.util.spec_from_file_location(key, Path(path))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[key] = mod
            spec.loader.exec_module(mod)
            return mod

        # genai를 mock으로 sys.modules에 사전 등록
        # 실제 google 네임스페이스 패키지를 보존하여 google.api_core 등 충돌 방지
        if "google.generativeai" not in sys.modules:
            import google as _g_pkg
            genai_mock = types.ModuleType("google.generativeai")
            genai_mock.configure = MagicMock()
            genai_mock.GenerativeModel = MagicMock()
            genai_mock.GenerationConfig = MagicMock()
            sys.modules["google.generativeai"] = genai_mock
            setattr(_g_pkg, "generativeai", genai_mock)

        # diskcache 미설치 환경 대응 — 가짜 Cache 모듈 사전 등록
        if "diskcache" not in sys.modules:
            _dc_mock = types.ModuleType("diskcache")
            _dc_mock.Cache = MagicMock(return_value=MagicMock(
                get=MagicMock(return_value=None),
                set=MagicMock(),
                expire=MagicMock(return_value=0),
            ))
            sys.modules["diskcache"] = _dc_mock

        sg_mod = _load_direct("src.step08.script_generator", "src/step08/script_generator.py")
        generate_script = sg_mod.generate_script

        mock_script = {
            "title_candidates": ["금리 인하의 비밀"],
            "hook": {"text": "충격적인 사실!", "animation_preview_at_sec": 8},
            "promise": "금리 인하 완전 해설",
            "sections": [],
            "affiliate_insert": {"purchase_rate_applied": 0.01},
            "seo": {"primary_keyword": "금리"},
            "ai_label": "AI 제작",
            "financial_disclaimer": "투자 주의",
        }

        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_script)
        mock_model.generate_content.return_value = mock_resp
        sg_mod.genai.GenerativeModel.return_value = mock_model

        with patch.object(sg_mod, "throttle_if_needed", return_value=None):
            with patch.object(sg_mod, "record_request", return_value=None):
                result = generate_script(
                    "CH1", "run_test",
                    sample_topic_dict,
                    {"animation_style": "cute"},
                    {"target_duration_sec": 720},
                    {"upload_days": ["화", "목"]},
                )

        assert isinstance(result, dict)
        assert "sections" in result or "title_candidates" in result

    def test_step11_disclaimer_keys_complete(self):
        """Step11: 7채널 면책조항 키 완비 확인."""
        from src.step11.qa_gate import CHANNEL_DISCLAIMER_KEY
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            assert ch in CHANNEL_DISCLAIMER_KEY

    def test_step14_revenue_tracker_7channels(self):
        """Step14: 7채널 수익 추적 구조 확인."""
        from src.step14.revenue_tracker import REVENUE_TARGET_PER_CHANNEL
        assert REVENUE_TARGET_PER_CHANNEL == 2_000_000

    def test_pipeline_imports_cleanly(self):
        """파이프라인 핵심 모듈 import 오류 없음 확인 (genai 비의존 모듈만 검증)."""
        # genai 의존 없는 핵심 모듈들
        from src.core.config import CHANNEL_CATEGORIES, CHANNEL_IDS
        from src.step00.channel_registry import get_channel
        from src.step05.scorer import score_topic
        from src.step05.knowledge.knowledge_package import build_empty_package
        from src.step11.qa_gate import CHANNEL_DISCLAIMER_KEY
        from src.step12.shorts_uploader import SHORTS_HASHTAGS

        assert len(CHANNEL_CATEGORIES) == 7
        assert len(CHANNEL_DISCLAIMER_KEY) == 7
        assert len(SHORTS_HASHTAGS) == 7

        # character_manager는 직접 로드 (genai 우회)
        import sys, importlib.util
        if "src.step08.character_manager" not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                "src.step08.character_manager", "src/step08/character_manager.py"
            )
            mod = importlib.util.module_from_spec(spec)
            sys.modules["src.step08.character_manager"] = mod
            spec.loader.exec_module(mod)
        char_mod = sys.modules["src.step08.character_manager"]
        assert len(char_mod.CHARACTER_PROFILES) == 7
