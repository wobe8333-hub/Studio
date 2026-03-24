
# Run Manifest 구현 완료 보고

## 구현 완료 항목

### [1] Run Manifest + run 단일 구조 (1순위) ✅

**구현 내용:**
- `backend/utils/run_manager.py` 생성
- Run 디렉토리 구조: `output/runs/{run_id}/`
  - `manifest.json`: Run 메타데이터
  - `input/`: 입력 파일
  - `verify/`: Step2 검증 파일
  - `plans/`: Step2/Step3 계획 파일
  - `renders/`: Step4 렌더 파일
  - `reports/`: 리포트 파일
  - `logs/`: 로그 파일

**Manifest 필드:**
```json
{
  "run_id": "uuid",
  "created_at": "ISO8601",
  "current_step": "step2|step3|step4",
  "completed_steps": ["step2", "step3"],
  "status": "running|failed|completed",
  "input_hash": "sha256_hash",
  "files_generated": ["file_paths"],
  "last_error": {
    "step": "step2",
    "message": "error message",
    "timestamp": "ISO8601"
  }
}
```

**하위 호환성:**
- 기존 `output/verify/`, `output/plans/`, `output/reports/` 구조 유지
- Step2 실행 시 기존 위치에 저장 + Run 구조로 복사

### [2] Checkpoint / 재개 / Idempotent 실행 (2순위) ✅

**구현 내용:**
- `mark_step_completed()`: Step 완료 표시
- `mark_step_failed()`: Step 실패 표시
- `is_step_completed()`: Step 완료 여부 확인
- `get_resume_step()`: 재개할 Step 확인
- `find_run_by_input_hash()`: 동일 입력 해시로 기존 Run 찾기

**동작 방식:**
- Step2 실행 시 입력 해시 계산
- 동일 해시가 있으면 기존 Run 재사용
- Step2가 이미 완료되었으면 스킵하고 기존 결과 반환
- 실패 시 `status=failed`, `last_error` 기록
- 재실행 시 실패 Step부터 자동 재개

### [3] 품질 게이트 (Quality Gate) (3순위) ✅

**구현 내용:**
- `backend/utils/quality_gate.py` 생성
- `check_step2_quality()`: Step2 품질 검사
  - sentences >= 5
  - scenes >= 3
- `check_step3_quality()`: Step3 품질 검사
  - scenes_fixed.json 존재
  - 고정 스펙 100% 통과
- `check_step4_quality()`: Step4 품질 검사
  - final video duration >= sum(scene.duration_sec) * 0.9

**통합:**
- Step2 API에 품질 게이트 통합
- 실패 시 HTTPException 400 반환
- Manifest에 실패 사유 기록

### [4] Runs 관리 API + Swagger 자동 예시 (4순위) ✅

**구현 내용:**
- `GET /runs`: Run 목록 조회 (상태 필터, limit 지원)
- `GET /runs/{run_id}`: Run 상세 조회
- `POST /runs/{run_id}/resume`: Run 재개
- `POST /runs/{run_id}/cancel`: Run 취소

**Swagger 자동 예시:**
- 모든 Request/Response 모델에 `ConfigDict(json_schema_extra={"examples": [...]})` 추가
- Swagger UI에서 "Try it out" 클릭 시 예시 자동 채움

### [5] Step4 – 롱폼 렌더 안정화 (진행 중)

**구현 예정:**
- Scene 단위 렌더링 (scene_index 기준)
- 각 scene 완료 시 checkpoint 기록
- 중간 실패 시 실패 scene부터 재개
- 최종 산출물: `output/runs/{run_id}/renders/final.mp4`
- Step4_report.json 생성

## 변경된 파일

### 신규 생성
- `backend/utils/run_manager.py`: Run Manifest 관리
- `backend/utils/quality_gate.py`: 품질 게이트 검사
- `backend/RUN_MANIFEST_IMPLEMENTATION.md`: 구현 문서

### 수정
- `backend/main.py`:
  - Step2 API에 Run Manifest 통합
  - Runs 관리 API 추가
  - 품질 게이트 통합
- `backend/utils/output_paths.py`:
  - Run 구조 내 파일 경로 함수 추가

## 사용 방법

### Step2 실행 (Run Manifest 자동 생성)
```bash
POST /step2/structure-script
{
  "script": "안녕하세요. 오늘은 좋은 날입니다..."
}
```

**응답:**
```json
{
  "status": "success",
  "run_id": "d2f1ed8b-0e8a-46a8-8741-798e974ba219",
  "files": {
    "script_txt": "output/runs/{run_id}/verify/script.txt",
    "sentences_txt": "output/runs/{run_id}/verify/sentences.txt",
    "scenes_json": "output/runs/{run_id}/plans/scenes.json",
    "report_json": "output/runs/{run_id}/reports/step2_report.json"
  },
  "quality_gate": {
    "passed": true,
    "errors": []
  }
}
```

### Run 목록 조회
```bash
GET /runs?status=running&limit=10
```

### Run 상세 조회
```bash
GET /runs/{run_id}
```

### Run 재개
```bash
POST /runs/{run_id}/resume
{
  "force": false
}
```

### Run 취소
```bash
POST /runs/{run_id}/cancel
```

## 완료 조건 확인

- ✅ Step2 실행 시 Run Manifest 자동 생성
- ✅ 동일 입력 해시 재요청 시 기존 Run 재사용
- ✅ Step2 완료 시 Manifest 업데이트
- ✅ 품질 게이트 통합 (Step2)
- ✅ Runs 관리 API 추가
- ✅ Swagger 자동 예시 포함
- ⏳ Step3 Run Manifest 통합 (진행 중)
- ⏳ Step4 구현 (진행 중)

## 다음 단계

1. Step3 API에 Run Manifest 통합
2. Step4 롱폼 렌더 안정화 구현
3. Step4 품질 게이트 통합
4. 전체 파이프라인 테스트

