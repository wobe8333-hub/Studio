"""Step05 dedup — packages/ 하위 디렉토리 재귀 탐색 테스트."""
import json
from pathlib import Path
import pytest
from unittest.mock import patch


class TestLoadExistingTopics:
    """_load_existing_topics가 packages/ 하위 JSON을 탐색해야 한다."""

    def test_finds_topics_in_packages_subdir(self, tmp_path, monkeypatch):
        """packages/ 하위 knowledge package를 기존 주제로 인식해야 한다."""
        from src.step05.dedup import _load_existing_topics, _normalize
        from src.core.config import DATA_DIR

        # 가상 knowledge_store 구조 생성
        store_dir = tmp_path / "knowledge_store" / "CH1"
        packages_dir = store_dir / "packages"
        packages_dir.mkdir(parents=True)

        # packages/ 하위에 knowledge package 저장 (knowledge_package.py와 동일 형식)
        pkg = {
            "channel_id": "CH1",
            "reinterpreted_title": "금리 인하의 경제적 영향",
            "topics": [],
        }
        (packages_dir / "pkg_001.json").write_text(
            json.dumps(pkg, ensure_ascii=False), encoding="utf-8"
        )

        # DATA_DIR을 tmp_path로 대체
        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        existing = _load_existing_topics("CH1")

        normalized_target = _normalize("금리 인하의 경제적 영향")
        assert normalized_target in existing, \
            f"packages/ 하위 주제 '{normalized_target}'이 기존 주제 목록에 없음. " \
            f"glob('*.json')이 재귀 탐색을 하지 않는 버그. 실제 존재 목록: {existing}"

    def test_root_json_still_found(self, tmp_path, monkeypatch):
        """루트 JSON 파일은 기존처럼 탐색되어야 한다."""
        from src.step05.dedup import _load_existing_topics, _normalize

        store_dir = tmp_path / "knowledge_store" / "CH1"
        store_dir.mkdir(parents=True)

        root_data = {"topic": "블랙홀의 비밀"}
        (store_dir / "topics.json").write_text(
            json.dumps(root_data, ensure_ascii=False), encoding="utf-8"
        )

        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        existing = _load_existing_topics("CH1")
        assert _normalize("블랙홀의 비밀") in existing, "루트 JSON 주제가 탐색되지 않음"


class TestDeduplicateTopics:
    """deduplicate_topics가 packages/ 하위 주제와 중복을 올바르게 감지해야 한다."""

    def test_duplicate_in_packages_subdir_is_removed(self, tmp_path, monkeypatch):
        """packages/ 하위에 있는 주제와 중복되는 후보는 제거되어야 한다."""
        from src.step05.dedup import deduplicate_topics

        store_dir = tmp_path / "knowledge_store" / "CH1"
        packages_dir = store_dir / "packages"
        packages_dir.mkdir(parents=True)

        pkg = {"reinterpreted_title": "금리인하경제영향"}
        (packages_dir / "pkg.json").write_text(
            json.dumps(pkg, ensure_ascii=False), encoding="utf-8"
        )

        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        # "금리인하경제영향"과 유사한 후보
        candidates = ["금리인하경제영향", "완전히 새로운 주제"]
        result = deduplicate_topics("CH1", candidates, similarity_threshold=0.75)

        assert "완전히 새로운 주제" in result, "새로운 주제가 필터링됨"
        assert "금리인하경제영향" not in result, \
            "packages/에 있는 주제와 동일한 후보가 제거되지 않음 (버그)"
