"""Loomix G2 파이프라인 v2.1

4 병렬 트랙 DAG: Track A(Narrative) / B(Audio) / C(Visual) / D(Assembly)
QC 5 레이어, 피드백 루프, 쇼츠 자동 파생, Manim 인서트 포함.

DEPRECATION NOTICE (T51):
src/step00~17 (KAS 선형 파이프라인) → src/pipeline_v2/ 로 이관 예정.
기존 Step 모듈은 DEPRECATED 상태이나 즉시 삭제하지 않고 6개월 공존 운영.
새 에피소드는 모두 pipeline_v2를 통해 제작한다.
"""
