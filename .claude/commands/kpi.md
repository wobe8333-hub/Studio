---
description: KPI 수집 + AnalyticsLearningAgent 실행
---

다음을 순서대로 실행하세요:

1. AnalyticsLearningAgent 실행:
   ```bash
   python -c "from src.agents.analytics_learning import AnalyticsLearningAgent; print(AnalyticsLearningAgent().run())"
   ```

2. 결과 분석:
   - Phase 승격/강등 알림: `data/global/notifications/notifications.json` (`type: "phase_promotion"`)
   - KPI 요약: 채널별 CTR, AVP, 알고리즘 단계 변화

3. 개선 필요 채널은 mission-controller 에게 SendMessage 로 에스컬레이션.

$ARGUMENTS: 특정 채널 지정 (예: "CH1"). 미지정 시 전체 7채널.
