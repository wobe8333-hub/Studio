# 플레이북: 파이프라인 장애 대응 (Step08 FFmpeg 실패)

## 트리거
Step08 FFmpeg 오류, manifest.json status: "failed", 연속 3회 실패

## 대응 절차

```
/mission "Step08 FFmpeg 에러 조사"
-> cto: TeamCreate("incident-{날짜}-step08")
  1) pipeline-debugger: 로그·manifest·쿼터 분석 (read-only)
  2) backend-engineer: 수정 구현 (src/step08/ffmpeg_composer.py)
-> pipeline-debugger -> SendMessage -> backend-engineer에 근본 원인 전달
-> 수정 -> pytest -> TeamDelete
```

## SRE 에스컬레이션 (v8.0)

연속 3회 실패 시 `sre-engineer`가 `hitl_signals.json`에 `sre_escalation` 신호 삽입.
cto가 HITL 신호 확인 후 TeamCreate 실행.

## 완료 기준
- `pytest tests/ -q` PASS
- manifest.json status: "completed"
- HITL 신호 resolved: true
