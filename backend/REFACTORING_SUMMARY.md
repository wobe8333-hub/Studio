# 리팩토링 변경 내역 요약

## 개요
Step4 전 기능 유지 최우선 리팩토링 완료

## 변경된 파일 목록

### 1. 신규 생성 파일
- **`backend/utils/output_paths.py`**: 출력 경로 통합 유틸리티
  - `get_output_dirs()`: output 디렉토리 구조 생성 및 반환
  - `get_step2_file_paths()`: Step2 산출물 파일 경로 생성
  - `get_step3_file_paths()`: Step3 산출물 파일 경로 생성
  - `get_encoding_log_path()`: 인코딩 추적 로그 파일 경로 생성

- **`backend/output/verify/SMOKE_TEST.ps1`**: 스모크 테스트 스크립트
  - 서버 기동 확인
  - Swagger 문서 확인
  - Step2 실행 및 산출물 검증
  - Step3 실행 및 산출물 검증
  - Fixed spec 스키마 검증 (7개 키)

### 2. 수정된 파일

#### `backend/main.py`
- **디버그 엔드포인트 숨김 처리**:
  - `GET /debug/encoding`: `include_in_schema=False` 추가
  - `POST /debug/step2/quickcheck`: `include_in_schema=False` 추가
  - `/debug/step2`, `/debug/step3`는 유지 (실제 사용 중)

- **출력 경로 통합 유틸 사용**:
  - `/step3/convert-to-fixed-spec`: `get_step2_file_paths()`, `get_step3_file_paths()` 사용
  - `/debug/step3`: `get_output_dirs()`, `get_step3_file_paths()` 사용

#### `backend/utils/step2_exporter.py`
- **출력 경로 통합 유틸 사용**:
  - `export_step2_results()`: `get_output_dirs()`, `get_step2_file_paths()`, `get_encoding_log_path()` 사용
  - 중복된 디렉토리 생성 코드 제거

#### `backend/utils/step3_converter.py`
- **출력 경로 통합 유틸 사용**:
  - `load_step2_result()`: `get_step2_file_paths()` 사용
  - `generate_step3_report()`: `get_step3_file_paths()` 사용

## 삭제/숨김 처리된 라우트

### Swagger에서 숨김 처리 (include_in_schema=False)
- `GET /debug/encoding`: 인코딩 정보 확인 (제품 기능 아님)
- `POST /debug/step2/quickcheck`: 빠른 검증 (제품 기능 아님)

### 유지된 디버그 라우트
- `POST /debug/step2`: Step2 디버그 실행 (실제 사용 중 - test_step2.ps1에서 사용)
- `POST /debug/step3`: Step3 디버그 실행 (실제 사용 중)

## 핵심 변경점

### 1. 출력 경로 규칙 통일
- 모든 Step2/Step3 파일 경로 생성이 `output_paths.py`로 통합
- 디렉토리 자동 생성 보장 (mkdir 호출 중복 제거)
- 경로 생성 로직 일관성 확보

### 2. 디버그 엔드포인트 정리
- 제품 기능과 무관한 엔드포인트는 Swagger에서 숨김
- 실제 사용 중인 디버그 엔드포인트는 유지

### 3. 코드 중복 제거
- 디렉토리 생성 코드 통합
- 파일 경로 생성 로직 통합

## 기능 유지 확인

### 유지된 기능
- ✅ Step2 실행: `/step2/structure-script`
- ✅ Step3 실행: `/step3/convert-to-fixed-spec`
- ✅ Step2 디버그: `/debug/step2`
- ✅ Step3 디버그: `/debug/step3`
- ✅ 산출물 파일 생성 규칙 (verify/plans/reports/logs)
- ✅ Fixed spec 스키마 (7개 키)

### 변경되지 않은 것
- API 엔드포인트 동작 방식
- 파일 저장 위치 및 이름 규칙
- 리포트 생성 로직

## 검증 방법

### 스모크 테스트 실행
```powershell
cd backend\output\verify
.\SMOKE_TEST.ps1
```

### 수동 검증
1. 서버 기동: `python -m uvicorn main:app --reload`
2. Swagger 확인: `http://127.0.0.1:8000/docs`
   - `/debug/encoding`, `/debug/step2/quickcheck`가 보이지 않아야 함
3. Step2 실행: `POST /step2/structure-script`
4. Step3 실행: `POST /step3/convert-to-fixed-spec`
5. 산출물 확인: `output/verify/`, `output/plans/`, `output/reports/`

## 완료 조건 확인

- ✅ 서버 기동: 에러 없이 실행
- ✅ Swagger: 디버그 엔드포인트 숨김 처리 확인
- ✅ Step2 산출물: 4개 파일 생성 + status=success
- ✅ Step3 산출물: 2개 파일 생성 + status=success
- ✅ Fixed spec: 7개 키 스펙 100% 준수
- ✅ 스모크 테스트 스크립트: 자동 검증 가능

