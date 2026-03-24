# RUNBOOK - AI Animation Studio v7

## 운영 검증 표준 (SSOT)

이 RUNBOOK은 **3개의 검증 명령만** 운영 표준으로 봉인합니다. 이 명령들은 항상 동일한 결과를 재현해야 합니다.

### 1. 레포지토리 건강검진 (SSOT)

**명령**:
```bash
python -m backend.scripts.verify_repo_health
```

**기능**:
- 금지 파일/폴더 검사 (backend/.env, **/__pycache__/, **/*.pyc, frontend/node_modules, frontend/.next)
- SSOT dry-run 실행 및 모듈 누락 감지
- 누락 모듈 제안 리포트 생성 (`data/health/requirements_patch_suggestion.txt`)

**Exit Code**:
- `0`: PASS (모든 검증 통과)
- `2`: FAIL (금지 파일/폴더 발견, dry-run 실패, 또는 누락 모듈 존재)

**리포트 위치**: `data/health/last_healthcheck.log`

### 2. v7 실행 (SSOT Dry-Run)

**명령**:
```bash
python -m backend.cli.run knowledge v7-run --mode dry-run
```

**기능**:
- v7 지식 적재 파이프라인 실행 (dry-run 모드)
- fixtures 기반 폴백으로 자산 생성 보장
- 게이트 통계 산출 및 저장

**Exit Code**:
- `0`: 성공 (JSON 출력)
- `1`: 에러 발생 (JSON 출력)

**출력**: JSON 1줄 (stdout)

**참고**: 실제 실행은 `--mode run`을 사용하지만, 검증 목적으로는 `--mode dry-run`만 SSOT로 지정됩니다.

### 3. 적재량 통계 검증 (SSOT)

**명령**:
```bash
python -m backend.scripts.verify_v7_ingestion_stats
```

**기능**:
- assets 라인수 확인 (>= 200)
- chunks 라인수 확인 (>= 600)
- READY 수 확인 (>= 30)
- avg_chunks_per_asset 확인 (>= 3.0)
- READY=0일 때 reason_code 진단 정보 출력

**Exit Code**:
- `0`: PASS (모든 기준 충족)
- `2`: FAIL (기준 미달 또는 reason_code 진단 불가)

**리포트 위치**: `<store_root>/reports/last_v7_stats.txt`, `last_v7_stats.json`

## 표준 실행 순서

운영 표준 검증을 수행하려면 다음 순서로 실행하세요:

```bash
# 1. 건강검진
python -m backend.scripts.verify_repo_health

# 2. v7 실행 (dry-run)
python -m backend.cli.run knowledge v7-run --mode dry-run

# 3. 적재량 검증
python -m backend.scripts.verify_v7_ingestion_stats
```

**중요**: 세 명령 모두 동일한 결과를 재현해야 합니다. 재현되지 않으면 운영 표준 위반입니다.

## Exit Code 규칙

운영 표준 검증 명령의 exit code 규칙:

- **PASS**: `exit code = 0`
- **FAIL**: `exit code = 2` (강제, 운영 표준)

**주의**: 일반적인 에러는 `exit code = 1`을 사용하지만, 검증 실패는 반드시 `exit code = 2`를 사용합니다.

## 추가 명령 (참고용)

다음 명령들은 SSOT가 아니며, 필요에 따라 사용하세요:

### 레거시 마이그레이션

레거시 store (backend/output/knowledge_v1)에서 새 store (data/knowledge_v1_store)로 마이그레이션:
```bash
python -m backend.cli.run knowledge v7-run --mode run --migrate-legacy-store
```

**주의**: 마이그레이션은 레거시 경로에 데이터가 있고 새 경로가 비어있을 때만 수행됩니다.

### 실제 실행 (운영)

```bash
python -m backend.cli.run knowledge v7-run --mode run
```

### 롤백 명령

모든 변경사항을 되돌리려면:
```bash
git checkout .
git clean -fd
```

**주의**: 이 명령은 모든 로컬 변경사항과 추적되지 않은 파일을 삭제합니다. 중요한 데이터는 백업하세요.

## 런타임 데이터 경로

- 기본 경로: `<repo_root>/data/knowledge_v1_store`
- 환경변수 우선: `KNOWLEDGE_STORE_ROOT` 환경변수가 설정되면 해당 경로 사용
- 레거시 경로 (읽기 폴백): `<repo_root>/backend/output/knowledge_v1`

## 주요 변경사항

- v7 적재량 증대:
  - `max_keywords_per_category`: 20 → 80
  - `DAILY_TOTAL_LIMIT`: 100 → 400
  - 멀티 청크 생성: 1 asset → 3~5 chunks
  - fixtures 폴백: API 실패 시 최소 50개 수준 데이터 공급

- 런타임 데이터 분리:
  - `backend/output/**`는 더 이상 기본 저장 위치가 아님 (git ignore 적용)
  - 새 경로: `<repo_root>/data/knowledge_v1_store`

