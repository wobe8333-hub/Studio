"""
Knowledge Ingest Smoke Tests - 최소 단위 테스트
"""

import unittest
import sys
from pathlib import Path

# 프로젝트 루트 기준으로 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.knowledge_v1.ingest import ingest
from backend.knowledge_v1.store import get_knowledge_root, load_jsonl


class TestKnowledgeIngestSmoke(unittest.TestCase):
    """지식 ingest 스모크 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.assets_path = get_knowledge_root() / "raw" / "assets.jsonl"
        self.chunks_path = get_knowledge_root() / "derived" / "chunks.jsonl"
    
    def get_line_count(self, path):
        """파일 라인 수 반환"""
        if not path.exists():
            return 0
        return sum(1 for _ in load_jsonl(path))
    
    def test_science_ingest(self):
        """Science 카테고리 ingest 테스트"""
        # 실행 전 라인 수
        assets_before = self.get_line_count(self.assets_path)
        chunks_before = self.get_line_count(self.chunks_path)
        
        # ingest 실행
        assets = ingest("science", ["black hole", "event horizon"], depth="normal", mode="dry-run")
        
        # 실행 후 라인 수
        assets_after = self.get_line_count(self.assets_path)
        chunks_after = self.get_line_count(self.chunks_path)
        
        # 검증
        self.assertGreaterEqual(len(assets), 1, "At least 1 asset should be ingested")
        self.assertGreater(assets_after, assets_before, "Assets file should have increased")
        self.assertGreater(chunks_after, chunks_before, "Chunks file should have increased")
    
    def test_papers_ingest(self):
        """Papers 카테고리 ingest 테스트"""
        # 실행 전 라인 수
        assets_before = self.get_line_count(self.assets_path)
        chunks_before = self.get_line_count(self.chunks_path)
        
        # ingest 실행
        assets = ingest("papers", ["transformer", "attention"], depth="normal", mode="dry-run")
        
        # 실행 후 라인 수
        assets_after = self.get_line_count(self.assets_path)
        chunks_after = self.get_line_count(self.chunks_path)
        
        # 검증
        self.assertGreaterEqual(len(assets), 1, "At least 1 asset should be ingested")
        self.assertGreater(assets_after, assets_before, "Assets file should have increased")
        self.assertGreater(chunks_after, chunks_before, "Chunks file should have increased")


if __name__ == "__main__":
    unittest.main()

