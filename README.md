# AI Animation Studio

**스스로 학습하는 AI 지식 애니메이션 스튜디오**

## 프로젝트 소개

이 프로젝트는 사용자가 주제나 키워드를 입력하면, AI가 자동으로 학습하고 애니메이션 제작에 필요한 스크립트, 씬 구성, 이미지 프롬프트를 생성하는 개인용 웹 기반 AI 스튜디오입니다.

### 주요 기능

- **지식 학습**: 위키피디아 및 웹 소스에서 자동으로 지식 습득
- **주제 분석**: 입력된 주제/키워드를 분석하여 애니메이션 제작에 필요한 메타데이터 추출
- **스크립트 생성**: 교육용 애니메이션 스크립트 자동 생성
- **씬 구성**: 각 장면의 시각적 구성 및 이미지 프롬프트 생성
- **자가 학습**: 사용자 피드백을 통한 지속적인 품질 개선

## 프로젝트 구조

```
ai-animation-studio/
├── backend/                 # FastAPI 백엔드
│   ├── main.py             # FastAPI 엔트리포인트
│   ├── ai_engine/          # AI 엔진 모듈들
│   │   ├── topic_analyzer.py      # 주제 분석
│   │   ├── script_generator.py    # 스크립트 생성
│   │   ├── scene_designer.py      # 씬 구성 설계
│   │   └── learning_engine.py     # 자가 학습 엔진
│   ├── db/                 # 데이터베이스 모델
│   │   └── models.py
│   └── crawler/            # 웹 크롤러
│       ├── wiki_crawler.py
│       └── keyword_crawler.py
│
├── frontend/               # Next.js 프론트엔드
│   ├── app/                # Next.js App Router
│   │   ├── page.tsx        # 메인 페이지
│   │   ├── create-video/   # 애니메이션 제작 페이지
│   │   └── learning-center/ # 학습 관리 페이지
│   └── components/         # 재사용 가능한 컴포넌트 (추가 예정)
│
└── README.md
```

## 현재 단계

### 완료된 작업

✅ **프로젝트 뼈대 구조 생성**
- Backend: FastAPI 기반 서버 구조 및 모듈 뼈대
- Frontend: Next.js 기반 최소 실행 구조
- 각 모듈별 함수 시그니처 및 주석 정의

✅ **Backend 모듈 구조**
- `main.py`: FastAPI 서버 엔트리포인트 (실행 가능)
- `ai_engine/`: AI 엔진 모듈들 (함수 뼈대 및 역할 정의)
- `db/models.py`: 데이터 모델 정의 (Pydantic 기반)
- `crawler/`: 크롤러 모듈 구조

✅ **Frontend 구조**
- Next.js App Router 기반
- 메인 페이지, Create Video, Learning Center 페이지 뼈대

### 아직 구현되지 않은 기능

❌ 실제 AI 로직 (LLM 연동, 프롬프트 엔지니어링)
❌ 웹 크롤링 구현
❌ 데이터베이스 연동 (SQLAlchemy 등)
❌ API 엔드포인트 구현
❌ 프론트엔드 UI/UX 디자인
❌ 영상 생성 파이프라인

## 다음 단계

### 1. Backend 기능 구현
- [ ] LLM API 연동 (OpenAI, Claude 등)
- [ ] 위키피디아 크롤링 구현
- [ ] 데이터베이스 설정 (SQLite 또는 PostgreSQL)
- [ ] API 엔드포인트 구현
- [ ] 에러 핸들링 및 로깅

### 2. Frontend 기능 구현
- [ ] 주제 입력 폼 및 UI
- [ ] 스크립트 생성 및 미리보기
- [ ] 씬 구성 시각화
- [ ] 학습 상태 대시보드
- [ ] API 연동

### 3. 통합 및 최적화
- [ ] 백엔드-프론트엔드 통합 테스트
- [ ] 성능 최적화
- [ ] 사용자 피드백 시스템
- [ ] 배포 설정

## 시작하기

### Backend 실행 (개발 서버)

```bash
cd backend
pip install -r requirements.txt
python main.py
```

서버는 `http://localhost:8000`에서 실행됩니다.

### Step2 / Step3 / verify_runs 실행 (정답 명령)

아래 명령들은 프로젝트 루트(`AI Animation Studio`)에서 실행합니다.

```bash
# Step2: 롱폼 스크립트 구조화
python -m backend.cli step2

# Step3: Scene JSON 고정 스펙 변환
python -m backend.cli step3 --run-id <run_id>

# runs 상태 점검 (READY_FOR_STEP4 여부 포함)
python -m backend.scripts.verify_runs

# Step4 준비 상태 확인
python -m backend.cli step4-check --run-id <run_id>

# Step4 실행 (렌더링)
python -m backend.cli step4 --run-id <run_id> [--resume] [--force]

# import 규칙 검증 (backend.* 통일 확인)
python -m backend.scripts.import_sanity
```

### Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드는 `http://localhost:3000`에서 실행됩니다.

## 기술 스택

- **Backend**: Python, FastAPI, Pydantic
- **Frontend**: Next.js, React, TypeScript
- **Database**: (추후 결정)
- **AI**: (추후 결정 - OpenAI, Claude 등)

## 라이선스

(추후 결정)

## Release (v2-Step11)

Create release:
scripts\release.ps1 -Version "v2.11.0"

Verify release (run inside release folder):
scripts\verify_release.ps1

Canonical verification:
python -m backend.scripts.import_sanity
python -m backend.scripts.verify_runs

## 지식 플로우 (Knowledge v1)

지식 자동 적재→메타→분류→사용 게이트→감사/롤백 플로우

### 정답 실행 명령

```bash
# 지식 적재 (dry-run 모드)
python -m backend.cli.run knowledge ingest --category economy --keywords "gdp,inflation" --mode dry-run

# 지식 조회
python -m backend.cli.run knowledge query --category economy --topic "gdp" --limit 5 --mode reference_only

# 지식 플로우 검증
python -m backend.scripts.verify_knowledge_flow
```

### 사용 예시

```bash
# 1. 지식 적재 (기존 카테고리)
python -m backend.cli.run knowledge ingest --category economy --keywords "gdp,inflation" --mode dry-run

# 2. 지식 조회
python -m backend.cli.run knowledge query --category economy --topic "gdp" --limit 5 --mode reference_only

# 3. 과학(Science) 카테고리 적재
python -m backend.cli.run knowledge ingest --category science --keywords "gravity" --mode dry-run

# 4. 상식(Common Sense) 카테고리 적재
python -m backend.cli.run knowledge ingest --category common_sense --keywords "why_sky_blue" --mode dry-run

# 5. 매일 오후 5시 자동 적재 스케줄러 시작
python -m backend.cli.run knowledge schedule-daily --category science --keywords "gravity" --mode dry-run

# 6. Discovery Layer 전량 적재
python -m backend.cli.run knowledge discovery-ingest --category science --keywords "gravity,cell division,photosynthesis" --ttl-days 14

# 7. Discovery TTL 적용
python -m backend.cli.run knowledge discovery-ttl --ttl-days 14

# 8. Discovery → Approved 승격
python -m backend.cli.run knowledge promote --category science --limit 12

# 9. Discovery 통합 사이클 (권장)
python -m backend.cli.run knowledge discovery-cycle

# 10. 전체 검증
python -m backend.scripts.verify_knowledge_flow
```

### 지원 카테고리

- `history` - 역사
- `geo` - 지리
- `mystery` - 미스터리
- `economy` - 경제
- `war` - 전쟁
- `animation` - 애니메이션
- `science` - 과학 (검증 가능한 과학적 사실/정의/연구 근거)
- `common_sense` - 상식 (일반적·비전문적·비논문 기반 사실)
- `papers` - 논문 (v7.1 복구)

### Fallback 1건 보장 정책

지식 적재 시 수집 결과가 0건인 경우에도 **반드시 1개의 fallback asset이 자동 생성**됩니다.

**Fallback Asset 특성:**
- `trust_level`: LOW
- `impact_scope`: LOW
- `source_id`: "fallback_synthetic"
- `license_status`: UNKNOWN
- `usage_rights`: ALLOWED (내부 생성 텍스트)

**주의사항:**
- Fallback asset은 실제 소스에서 검증 및 보강이 필요합니다.
- 고위험 사용 전 반드시 실제 소스로 대체해야 합니다.
- 모든 ingest 실행은 audit 로그에 기록됩니다 (0건이어도 INGEST_RUN_START/END 기록).

### 저장 위치

**Approved Layer (기존):**
- `backend/output/knowledge_v1/raw/assets.jsonl` - 원본 자산
- `backend/output/knowledge_v1/derived/chunks.jsonl` - 정규화된 청크
- `backend/output/knowledge_v1/used/used_assets.jsonl` - 사용 가능한 자산
- `backend/output/knowledge_v1/blocked/blocked_assets.jsonl` - 차단된 자산
- `backend/output/knowledge_v1/audit/audit.jsonl` - 감사 로그
- `backend/output/knowledge_v1/index/index.json` - 키워드 인덱스
- `backend/output/knowledge_v1/scheduler/state.json` - 스케줄러 상태

**Discovery Layer (신규):**
- `backend/output/knowledge_v1_discovery/raw/assets.jsonl` - 발견 자산 (임시)
- `backend/output/knowledge_v1_discovery/audit/audit.jsonl` - 감사 로그
- `backend/output/knowledge_v1_discovery/state/state.json` - 상태 파일
- `backend/output/knowledge_v1_discovery/state/quota.json` - 쿼터 상태

**주의:** Discovery Layer에는 `derived/`, `index/` 폴더가 없습니다.

### 자동 승격 대상 카테고리

다음 5개 카테고리는 Discovery Layer에서 Approved Layer로 자동 승격됩니다:

- `science` - 과학
- `history` - 역사
- `common_sense` - 상식
- `economy` - 경제
- `geo` - 지리 (geography)

**제외 카테고리:**
- `papers` - 논문 (완전 제외)
- `mystery` - 미스터리 (완전 제외, 아이디어 트리거로만 사용)

자동 승격은 `discovery-cycle` 실행 시 자동으로 수행됩니다.

### 자동 적재 스케줄러

매일 오후 5시(로컬 시간 기준)에 자동으로 지식 적재가 실행됩니다.

**주의사항:**
- 화면 꺼짐: 가능
- 절전 모드: 불가 (스케줄러 중단됨)
- 전원 OFF: 불가 (스케줄러 중단됨)
- 하루 1회만 실행 (중복 방지)

**실행 방법:**
```bash
# 스케줄러 시작 (백그라운드 실행 권장)
python -m backend.cli.run knowledge schedule-daily --category science --keywords "gravity" --mode dry-run

# 강제 실행 테스트 (환경변수 사용)
FORCE_RUN_TODAY=1 python -m backend.cli.run knowledge schedule-daily --category science --keywords "gravity" --mode dry-run
```

**중지 방법:**
- Ctrl+C로 정상 종료
- 종료 시 audit 로그에 SCHEDULER_STOP 이벤트 기록

### Preflight 검증 (안정화)

운영 전 필수 검증 스크립트로, 런타임 에러를 사전에 검출합니다.

**실행 방법:**
```bash
python -m backend.scripts.preflight
```

**검증 항목:**
- Import 검증 (주요 모듈 import 성공)
- 컴파일 검증 (문법/이름 오류 검출)
- Schema 자기검증 (KnowledgeAsset 인스턴스 생성 테스트)
- import_sanity 실행
- verify_runs 실행 (선택적)
- Knowledge ingest 스모크 테스트 (science, papers)

**PASS 조건:**
- 모든 체크가 PASS
- Science ingest: assets >= 1, chunks >= 1, LICENSE_BLOCK 없음
- Papers ingest: assets >= 1, chunks >= 1, LICENSE_BLOCK 없음














