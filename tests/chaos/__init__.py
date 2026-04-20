"""Chaos Engineering 테스트 모음.

외부 API가 무작위로 실패할 때 파이프라인이 올바르게 대응하는지 검증한다.
정상 경로 테스트와 격리하기 위해 별도 디렉토리에 배치한다.

실행 방법:
    pytest tests/chaos/ -v
"""
