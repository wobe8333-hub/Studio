# Reproducible Build Guide

이 문서는 AI Animation Studio v2 프로젝트를 클린 상태에서 재현 가능하게 빌드하고 실행하는 방법을 설명합니다.

## 전제조건

- Python 3.11 이상
- Node.js 18 이상 및 npm
- Git (프로젝트 클론용)

## 1. 프로젝트 클론

```bash
git clone <repository-url>
cd "AI Animation Studio"
```

## 2. 백엔드 의존성 설치

### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

### Linux/macOS

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

## 3. 프론트엔드 의존성 설치

```bash
cd frontend
npm ci
# 또는
npm install
cd ..
```

## 4. 환경 변수 설정 (선택사항)

`.env.example` 파일을 참고하여 필요한 환경 변수를 설정합니다.

```bash
# .env.example을 복사하여 .env 생성 (필요한 경우)
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

## 5. 기능 무결성 검증

프로젝트 루트에서 다음 명령을 실행하여 기능이 정상 동작하는지 확인합니다.

### Import Sanity 검증

```bash
python -m backend.scripts.import_sanity
```

기대 출력:
```
✅ PASSED
```

### Verify Runs 검증

```bash
python -m backend.scripts.verify_runs
```

기대 출력:
```
==================================================
✅ VERIFY_RUNS: PASS
...
==================================================
```

### Step12 실행 (Phase2 포함)

```bash
python -m backend.cli step12 --run-id <run_id>
```

또는 Phase2 실행:

```bash
python -m backend.cli step12 --run-id <run_id> --source-type text --source "..." --title "..." --allow-network
```

## 6. 출력 디렉토리 자동 생성

프로젝트는 실행 시 필요한 출력 디렉토리를 자동으로 생성합니다:

- `backend/output/runs/` - Run 실행 결과
- `backend/output/cache/` - 캐시 파일
- `backend/output/knowledge/` - 지식 베이스 파일

출력 디렉토리가 없어도 실행 시 자동으로 생성되므로, 클린 상태에서도 정상 동작합니다.

## 7. 프로젝트 정리 (선택사항)

대용량 재생성 가능 파일을 제거하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup_repo.ps1
```

용량 리포트 확인:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\size_report.ps1
```

## 8. 문제 해결

### Import 오류 발생 시

- Python 가상환경이 활성화되어 있는지 확인
- `pip install -r requirements.txt` 재실행
- `python -m backend.scripts.import_sanity`로 import 경로 검증

### Verify Runs 실패 시

- `backend/output/runs/` 디렉토리가 없어도 정상 (자동 생성됨)
- manifest.json이 없는 run은 자동으로 스킵됨
- release 모드에서는 runs_root 없어도 PASS 처리됨

### Step12 실행 실패 시

- Step1~4가 모두 success 상태인지 확인
- `python -m backend.scripts.verify_runs`로 READY_FOR_STEP12 확인
- AUTO_CACHE가 자동으로 캐시를 생성하므로 cached_scenes < 1이어도 진행 가능

## 9. 정답 실행 명령 (고정)

### 백엔드 검증
```bash
python -m backend.scripts.import_sanity
python -m backend.scripts.verify_runs
```

### Step 실행
```bash
python -m backend.cli step2
python -m backend.cli step3 --run-id <run_id>
python -m backend.cli step4 --run-id <run_id>
python -m backend.cli step12 --run-id <run_id>
```

### 릴리즈 생성
```powershell
.\scripts\release.ps1 -Version "v2.11.0"
```

## 10. 의존성 파일

- `backend/requirements.txt` - Python 패키지 의존성
- `frontend/package.json` - Node.js 패키지 의존성
- `frontend/package-lock.json` - Node.js 패키지 잠금 파일 (존재 시)

이 파일들은 프로젝트에 포함되어 있으며, 재현 가능한 빌드를 보장합니다.

