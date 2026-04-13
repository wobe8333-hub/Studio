---
description: pipeline-debugger 소환 — Step 실패 분석 및 수정 방향 제시
---

pipeline-debugger 에이전트를 소환하세요.

분석 순서:
1. `logs/pipeline.log` 최근 ERROR (tail -100)
2. `runs/*/manifest.json` 중 `run_state: "FAILED"` 항목
3. `data/global/step_progress.json` 마지막 실행 상태
4. $ARGUMENTS 가 있으면 해당 Step 집중 분석 (예: "step08", "step05")

분석 후 수정 방향:
- 코드 수정이 필요하면 backend-engineer 에게 SendMessage 로 위임
- 쿼터 초과면 `data/global/quota/*.json` 확인 후 devops-engineer 에스컬레이션
- Manim 실패면 `src/step08/manim_generator.py` 집중 분석

$ARGUMENTS: 분석 대상 Step 번호 (예: "step08"). 미지정 시 전체 FAILED 스캔.
