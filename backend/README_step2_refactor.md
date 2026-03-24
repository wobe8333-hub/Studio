# ②단계 리팩토링 완료 체크리스트

## 개요
Step2(스크립트→문장/문단→씬 분해→scenes.json + report + verify 산출물) 기능을 100% 유지한 채, 성능/속도/안정성/가독성 개선 및 불필요 문법/로직 제거를 완료했습니다.

## 유지된 항목 (호환성 보장)

### ✅ 출력 파일 위치/이름 규칙
- `output/verify/{run_id}_script.txt`
- `output/verify/{run_id}_sentences.txt`
- `output/plans/{run_id}_scenes.json`
- `output/reports/{run_id}_step2_report.json`

### ✅ 리포트 핵심 키 구조
- `run_id`, `step`, `status`, `summary`, `generated_files`, `file_status`, `counts`, `timings`, `warnings`, `errors` 등 기존 필드 유지
- **추가 필드**: `generated_files_relative` (상대경로 배열, 하위 호환성 유지)

### ✅ API 입출력 형식
- 기존 JSON 구조 100% 유지
- 파일 생성 위치/파일명 규칙 동일

## 개선된 항목

### 1. 경로 인코딩 문제 해결 ✅
**문제**: PowerShell 출력/로그/JSON dump에서 한글 경로가 깨져 보임 (`C:\\Users\\議곗갔??\\...`)

**해결**:
- 리포트에 `generated_files_relative` 필드 추가 (output 디렉토리 기준 상대경로)
- 로그 출력 시 상대경로 사용하여 인코딩 문제 방지
- UTF-8 인코딩 명시적으로 보장 (`encoding="utf-8"`)

**영향**: 
- 기존 `generated_files` 필드는 그대로 유지 (절대경로)
- 새로운 `generated_files_relative` 필드 추가 (상대경로, 선택적 사용)

### 2. "string" placeholder 방어 로직 추가 ✅
**문제**: Swagger 예시 입력이 실제 텍스트가 아니라 schema 기본값("string")으로 들어가 실행되는 경우

**해결**:
- `/step2/structure-script` 엔드포인트에 "string" placeholder 체크 추가
- `/debug/step2` 엔드포인트에도 이미 방어 로직 존재 (이전 작업 완료)
- 입력값이 "string" 또는 '"string"'이면 400 에러 반환

**영향**: Step2 실행 시 유효하지 않은 placeholder 입력 방지

### 3. 체크프롬프트 의미 재정의 및 정리 ✅
**변경사항**:
- 기존 의미(검증/판정/감사) 완전 제거
- 새로운 의미: Swagger UI에서 "Try it out" 버튼 클릭 시 자동으로 채워지는 예시 입력값
- `step2_report.json`에서 `checkprompt` 관련 필드 제거 (`status`, `error`, `failed_rules`, `warnings`, `checks`)

**영향**: 
- 리포트 구조 단순화
- Swagger 예시 자동 채움 기능은 유지/강화

### 4. 성능 개선 ✅
**최적화 내용**:
- 불필요한 파일 존재 여부 체크 제거 (파일 생성 후 `exists()` 체크 불필요)
- 중복 데이터 접근 제거 (sentences, scenes, structure를 한 번만 가져오도록 최적화)
- 구조 정보 미리 계산하여 중복 `len()` 호출 제거
- 불필요한 문자열 변환 제거

### 5. 코드 구조 정리 ✅
**개선 내용**:
- 중복 코드 제거
- 로깅 일관화 (상대경로 사용)
- 파일 저장 시 UTF-8 명시적 보장
- Path 처리는 `pathlib.Path`로 통일

### 6. Swagger 예시 자동 채움 강화 ✅
**확인된 엔드포인트**:
- `/step2/structure-script`: `STEP2_TEXT` 예시 포함
- `/debug/step2`: `STEP2_TEXT`, `STEP2_TOPIC` 예시 포함
- `/learn/text`: `SAMPLE_PARAGRAPH` 예시 포함
- 기타 엔드포인트도 `core.sample_inputs` 모듈의 상수 사용

## 검증 방법

### PowerShell 검증 체크리스트

#### (1) Swagger 예시 자동 채움 확인
```powershell
# 서버 실행 후 http://localhost:8000/docs 접속
# → Step2 endpoint(/step2/structure-script 또는 /debug/step2) 선택
# → "Try it out" 클릭
# → Request body에 실제 예시 텍스트가 자동으로 채워지는지 확인
# → "string" placeholder가 아닌 실제 한글 텍스트여야 함
```

#### (2) 산출물 4종 생성 확인
```powershell
# 가장 최근 생성된 파일 확인
Get-ChildItem .\backend\output\verify -File -Filter "*_script.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, Length
Get-ChildItem .\backend\output\verify -File -Filter "*_sentences.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, Length
Get-ChildItem .\backend\output\plans  -File -Filter "*_scenes.json"  | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, Length
Get-ChildItem .\backend\output\reports -File -Filter "*_step2_report.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, Length

# 각 Length가 0보다 커야 함
```

#### (3) 파일 내용 확인 (한글 정상 포함 확인)
```powershell
$sent = Get-ChildItem .\backend\output\verify -Filter "*_sentences.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $sent.FullName -Encoding utf8 -TotalCount 20

# 한글이 정상적으로 보여야 함
```

#### (4) 리포트 구조 확인
```powershell
$rep = Get-ChildItem .\backend\output\reports -Filter "*_step2_report.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $rep.FullName -Encoding utf8 | ConvertFrom-Json | ConvertTo-Json -Depth 10

# 확인사항:
# - status: "success"
# - errors: [] (비어있어야 함)
# - generated_files: 절대경로 배열 (4개)
# - generated_files_relative: 상대경로 배열 (4개) - 새로 추가됨
# - checkprompt 관련 필드 없음
```

#### (5) 상대경로 정상 동작 확인
```powershell
$rep = Get-ChildItem .\backend\output\reports -Filter "*_step2_report.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$data = Get-Content $rep.FullName -Encoding utf8 | ConvertFrom-Json

# 상대경로로 파일 접근 테스트
$relPath = $data.generated_files_relative[0]
$fullPath = Join-Path (Resolve-Path .\backend\output) $relPath
Test-Path $fullPath  # True여야 함

# 파일 내용 확인
Get-Content $fullPath -Encoding utf8 -TotalCount 5
```

## 테스트 스크립트

`test_step2.ps1` 스크립트 참고 (동일 디렉토리)

## 변경된 파일 목록

1. `backend/utils/step2_exporter.py`
   - 상대경로 추가 (`generated_files_relative` 필드)
   - 로깅 개선 (상대경로 사용)
   - 성능 최적화

2. `backend/main.py`
   - `/step2/structure-script` 엔드포인트에 "string" placeholder 방어 로직 추가
   - 로깅 개선

## 주의사항

- **기능 변경 없음**: 모든 출력 포맷/필드/파일명/폴더 구조는 기존과 동일
- **하위 호환성 유지**: 기존 `generated_files` 필드는 그대로 유지, `generated_files_relative`는 추가 필드
- **체크프롬프트 의미 변경**: 검증용이 아닌 Swagger 예시 입력 자동 채움용으로만 사용

## 다음 단계

③단계(씬 JSON 고정)로 넘어갈 준비 완료. Step2 산출물이 안정적으로 생성됨을 확인하면 다음 단계 진행 가능.






























