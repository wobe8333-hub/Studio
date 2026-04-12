---
paths:
  - src/agents/**/*.py
---

### Sub-Agent 시스템 (`src/agents/`)

**원칙**: 기존 파이프라인(Step00~17)을 수정하지 않고, 수동 고통점만 자동화. JSON 결과물을 읽어 정책만 업데이트하는 비침습적 설계.

```
src/agents/
  base_agent.py                  — BaseAgent: root/runs_dir/data_dir 경로 초기화, _log_start/_log_done
  dev_maintenance/
    __init__.py                  — DevMaintenanceAgent: 파이프라인 실패 감지 + 헬스체크 + HITL 신호
    log_monitor.py               — find_failed_runs(): runs/*/manifest.json FAILED 스캔
    health_checker.py            — run_tests(): pytest subprocess 실행
    schema_validator.py          — find_missing_types(): SQL↔types.ts 불일치 감지
    hitl_signal.py               — emit_hitl_signal(): hitl_signals.json 기록
  analytics_learning/
    __init__.py                  — AnalyticsLearningAgent: KPI 분석 + 패턴 추출 + Phase 승격 + A/B
    kpi_analyzer.py              — compute_algorithm_stage(): 4단계 판정
    pattern_extractor.py         — is_winning() (CTR≥6.0% AND AVP≥50.0%), update_winning_patterns()
    phase_promoter.py            — promote_if_eligible(): 단방향 승격만 허용
    ab_selector.py               — select_winner(): curiosity→authority→benefit 우선순위
    notifier.py                  — record_phase_promotion(): notifications.json 기록
  ui_ux/
    __init__.py                  — UiUxAgent: 스키마 변경 감지 → types.ts 자동 동기화
    schema_watcher.py            — has_schema_changed(): SHA-256 해시 비교
    type_syncer.py               — generate_ts_interface(): SQL→TypeScript 변환 (_to_pascal_case)
  video_style/
    __init__.py                  — VideoStyleAgent: 캐릭터 드리프트 감지 + Manim fallback 모니터링
    character_monitor.py         — check_character_drift(): 드리프트 임계값 0.7
    style_optimizer.py           — check_manim_fallback_rate(): 경고 임계값 0.5
  cost_optimizer/
    __init__.py                  — CostOptimizerAgent: Gemini/YouTube 쿼터 사용 분석 + 낭비 감지
                                   경고 임계값: 80%(WARNING) / 95%(CRITICAL)
  script_quality/
    __init__.py                  — ScriptQualityAgent: Step08 생성 스크립트 Hook/CTA/구조 품질 평가
                                   채널별 톤 키워드 검증, 최소 Hook 길이 20자, 최소 씬 수 3개
```

**BaseAgent 패턴** — 모든 Agent가 따라야 하는 규칙:
```python
class MyAgent(BaseAgent):
    def __init__(self, root: Optional[Path] = None):
        super().__init__("AgentName")
        if root is not None:   # if root: 금지 — Path는 항상 truthy
            self.root = root
            self.data_dir = root / "data"

    def run(self) -> dict[str, Any]:   # 반드시 dict[str, Any] 반환
        ...
```

**알림/HITL 신호 파일**:
- `data/global/notifications/notifications.json` — Phase 승격 알림 (`type: "phase_promotion"`, `read: false`)
- `data/global/notifications/hitl_signals.json` — 운영자 확인 필요 신호 (`type: "pipeline_failure"|"pytest_failure"`, `resolved: false`)

**HITL 자동/수동 분기**:
- 자동 처리: 스키마 불일치 → UiUxAgent 위임, Phase 승격 → 알림만 기록
- 운영자 확인: FAILED 실행 1건 이상, pytest 실패
