"""
upgrade_golden_tests.py — 37개 에이전트 전원 역할 기반 golden.jsonl 재작성.
generic 템플릿을 실제 에이전트 역할에 맞는 시나리오로 교체한다.
"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
EVALS_DIR = ROOT / ".claude" / "evals"

# 에이전트별 역할 기반 테스트 (5건씩, 실제 업무 시나리오)
ROLE_TESTS = {
    "ceo": [
        {"id": "ceo-001", "input": "수주 계약 300만원 승인 여부 HITL 판단 요청", "expected_tools": ["Read"], "expected_output_pattern": "RAPID|승인|결정|근거", "judge_criteria": "RAPID D 역할 수행, 근거 명시, debate 결과 참조"},
        {"id": "ceo-002", "input": "월간 경영 보고 초안 작성 요청 — 7채널 KPI 포함", "expected_tools": ["Read", "Write"], "expected_output_pattern": "KPI|수익|채널|월간", "judge_criteria": "7개 채널 KPI + 액션 아이템 + COMPANY.md values 반영"},
        {"id": "ceo-003", "input": "cto vs db-architect 기술 방향 충돌 — 최종 결정", "expected_tools": ["Read"], "expected_output_pattern": "RAPID|결정|근거|debate", "judge_criteria": "debate-facilitator 개입 여부 확인, RAPID D 수행"},
        {"id": "ceo-004", "input": "신규 에이전트 data-scientist 채용 제안 검토", "expected_tools": ["Read"], "expected_output_pattern": "shadow|eval|14일|lifecycle", "judge_criteria": "Phase 10D 라이프사이클 준수 확인, 14일 shadow 언급"},
        {"id": "ceo-005", "input": "월 예산 $50 초과 — circuit breaker 2인 승인 요청", "expected_tools": ["Read"], "expected_output_pattern": "circuit|승인|finance|budget", "judge_criteria": "ceo + finance-manager 2인 승인 프로세스 언급"},
    ],
    "cto": [
        {"id": "cto-001", "input": "backend-engineer.md PR 검토 — eval 없이 변경 시도", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "eval|golden|regression|차단", "judge_criteria": "golden.jsonl 없는 .md 변경 차단 여부 확인"},
        {"id": "cto-002", "input": "Team A와 Team B 동시 data/exec/ 쓰기 — 데드락 감지", "expected_tools": ["Read"], "expected_output_pattern": "deadlock|rollback|team-state|개입", "judge_criteria": "team-state.md 프로토콜 준수, 롤백 조치"},
        {"id": "cto-003", "input": "cost-router 무시하고 Opus 강제 사용 발견", "expected_tools": ["Read"], "expected_output_pattern": "라우팅|정당성|감사|cost-router", "judge_criteria": "cost-router 감사 로그 확인, 정당성 검증"},
        {"id": "cto-004", "input": "미션 팀 구성 요청 — 현재 4팀 활성 중", "expected_tools": ["Read"], "expected_output_pattern": "TeamCreate|5팀|한도|확인", "judge_criteria": "최대 5팀 한도 확인 후 1팀 여유 있음 판단"},
        {"id": "cto-005", "input": "에이전트 평균 eval 점수 5.8 — 3연속 미달 조치", "expected_tools": ["Read"], "expected_output_pattern": "eval|review|개선|알림", "judge_criteria": "Under Review 상태 전환, 개선 계획 수립"},
    ],
    "legal-counsel": [
        {"id": "lc-001", "input": "브랜드 콜라보 NDA 계약서 검토 요청", "expected_tools": ["Read"], "expected_output_pattern": "NDA|조항|법적|검토", "judge_criteria": "불공정 조항 식별, 수정 제안, data/legal/ 저장"},
        {"id": "lc-002", "input": "CH6 과학 채널 YouTube Content ID 저작권 클레임 법적 조치", "expected_tools": ["Read"], "expected_output_pattern": "Content ID|저작권|반박|절차", "judge_criteria": "클레임 반박 절차 안내, 증거 보존 지침"},
        {"id": "lc-003", "input": "GDPR 사용자 데이터 수집 동의서 양식 검토", "expected_tools": ["Read"], "expected_output_pattern": "GDPR|동의|개인정보|규정", "judge_criteria": "GDPR Article 7 준수 여부, 필수 항목 확인"},
        {"id": "lc-004", "input": "외주 계약서에 무제한 수정 의무 조항 발견", "expected_tools": ["Read"], "expected_output_pattern": "불공정|수정|조항|법적", "judge_criteria": "불공정 조항 명시, 재협상 권고, sales-manager 에스컬레이션"},
        {"id": "lc-005", "input": "크리에이터 영상 라이선스 — 독점 vs 비독점 계약 분석", "expected_tools": ["Read"], "expected_output_pattern": "독점|라이선스|분석|권고", "judge_criteria": "두 옵션 트레이드오프 분석, 비용 대비 리스크 비교"},
    ],
    "research-lead": [
        {"id": "rl-001", "input": "Google Gemini 3.0 발표 — Loomix 파이프라인 영향 분석", "expected_tools": ["Read"], "expected_output_pattern": "영향|마이그레이션|POC|분석", "judge_criteria": "현행 Gemini 2.5-flash 대비 성능·비용 분석, POC 제안"},
        {"id": "rl-002", "input": "ElevenLabs v3 TTS — 현행 나레이션 품질 대비 POC 요청", "expected_tools": ["Read"], "expected_output_pattern": "POC|품질|비교|테스트", "judge_criteria": "A/B 테스트 설계, mlops-engineer 협업 제안"},
        {"id": "rl-003", "input": "Manim CE 0.20 → 0.21 마이그레이션 호환성 검토", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "마이그레이션|호환성|API|변경", "judge_criteria": "Breaking change 식별, 영향 범위 파악"},
        {"id": "rl-004", "input": "경쟁 YouTube AI 채널 도구 스택 벤치마킹 요청", "expected_tools": ["Read"], "expected_output_pattern": "벤치마킹|경쟁|도구|분석", "judge_criteria": "3개 이상 경쟁 채널 비교, Loomix 우위/열위 식별"},
        {"id": "rl-005", "input": "채널별 LoRA fine-tuning 로드맵 2026 H2 초안", "expected_tools": ["Read", "Write"], "expected_output_pattern": "fine-tuning|로드맵|일정|우선순위", "judge_criteria": "7채널별 우선순위, mlops-engineer 협업 포함"},
    ],
    "compliance-officer": [
        {"id": "comp-001", "input": "CH4 미스터리 채널 영상 YouTube 정책 위반 가능성 감지", "expected_tools": ["Read"], "expected_output_pattern": "정책|위반|위험|조치", "judge_criteria": "위반 조항 특정, 수정 권고, content-director 에스컬레이션"},
        {"id": "comp-002", "input": "GDPR — 시청자 이메일 수집 데이터 보존 기간 감사", "expected_tools": ["Read"], "expected_output_pattern": "GDPR|보존|감사|준수", "judge_criteria": "GDPR Article 5(1)(e) 기준 준수 여부, 조치 계획"},
        {"id": "comp-003", "input": "Content ID 자동 차단 발생 — 즉시 조치 요청", "expected_tools": ["Read"], "expected_output_pattern": "Content ID|차단|반박|절차", "judge_criteria": "48시간 내 반박 절차, legal-counsel 협업 제안"},
        {"id": "comp-004", "input": "7채널 커뮤니티 가이드라인 월간 준수 점검", "expected_tools": ["Read"], "expected_output_pattern": "준수|가이드라인|월간|점검", "judge_criteria": "7채널 각각 위반 사항 유무, 리스크 수준 분류"},
        {"id": "comp-005", "input": "YouTube 광고 수익 정책 2026 변경 — 영향 분석", "expected_tools": ["Read"], "expected_output_pattern": "정책|변경|영향|수익", "judge_criteria": "변경 항목 식별, 채널별 영향도, 대응 전략"},
    ],
    "db-architect": [
        {"id": "dba-001", "input": "videos 테이블에 duration_seconds INT NOT NULL 컬럼 추가", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "migration|RLS|types.ts|ALTER", "judge_criteria": "마이그레이션 SQL + RLS 정책 + web/lib/types.ts 동시 처리"},
        {"id": "dba-002", "input": "Supabase RLS 정책 전체 감사 — service_role 우회 가능성", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "RLS|policy|service_role|security", "judge_criteria": "service_role 우회 가능 테이블 식별, 보완 정책 제시"},
        {"id": "dba-003", "input": "Step05 N+1 쿼리 발견 — 인덱스 추가 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "index|JOIN|optimize|쿼리", "judge_criteria": "인덱스 추가 마이그레이션 + EXPLAIN ANALYZE 결과 예측"},
        {"id": "dba-004", "input": "스키마 변경 후 web/lib/types.ts 인터페이스 불일치 발생", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "types.ts|sync|interface|TypeScript", "judge_criteria": "Supabase 스키마 → TypeScript 인터페이스 완전 동기화"},
        {"id": "dba-005", "input": "channel_metrics 테이블 파티셔닝 — 월별 데이터 분리 설계", "expected_tools": ["Read", "Write"], "expected_output_pattern": "파티션|partition|성능|설계", "judge_criteria": "파티션 전략(RANGE/LIST), 마이그레이션 계획, 성능 예측"},
    ],
    "backend-engineer": [
        {"id": "be-001", "input": "src/step08/orchestrator.py FFmpeg 타임아웃 발생 — 원인 수정", "expected_tools": ["Read", "Grep", "Edit"], "expected_output_pattern": "timeout|retry|exception|수정", "judge_criteria": "오류 원인 정확 파악 + 수정안 구현 + worktree 사용"},
        {"id": "be-002", "input": "SSOT 위반 — src/step05/dedup.py에서 open() 직접 사용 발견", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "ssot|read_json|fix|open", "judge_criteria": "ssot.read_json() 교체, web/ 수정 없음"},
        {"id": "be-003", "input": "새 채널 CH8 추가 — 파이프라인 전체 등록", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "config.py|SSOT|채널|CH8", "judge_criteria": "src/core/config.py 수정, web/ 직접 수정 금지"},
        {"id": "be-004", "input": "pytest tests/ -q — 5개 실패 수정 요청", "expected_tools": ["Bash", "Read", "Edit"], "expected_output_pattern": "fix|PASS|test|수정", "judge_criteria": "전부 PASS 복원, 테스트 로직 변경 없이 구현 수정"},
        {"id": "be-005", "input": "Step11 QA 자동 통과율 87% → 90% 개선 요청", "expected_tools": ["Read", "Grep", "Edit"], "expected_output_pattern": "QA|개선|통과율|수정", "judge_criteria": "실패 패턴 분석 후 구현 수정, 테스트 확인"},
    ],
    "frontend-engineer": [
        {"id": "fe-001", "input": "파이프라인 실시간 상태 페이지 — Step 진행률 컴포넌트 추가", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "컴포넌트|Next.js|Supabase|실시간", "judge_criteria": "web/ 내 컴포넌트 작성, Supabase 실시간 구독 사용"},
        {"id": "fe-002", "input": "대시보드 채널별 KPI 카드 로딩 속도 3초 → 1초 개선", "expected_tools": ["Read", "Edit", "Bash"], "expected_output_pattern": "로딩|최적화|캐시|성능", "judge_criteria": "데이터 페칭 최적화, React Query 캐시 전략"},
        {"id": "fe-003", "input": "모바일 반응형 레이아웃 깨짐 — 채널 그리드 수정", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "반응형|Tailwind|grid|모바일", "judge_criteria": "Tailwind breakpoint 수정, 모바일 UX 준수"},
        {"id": "fe-004", "input": "Playwright E2E — 파이프라인 실행 버튼 테스트 추가", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "E2E|Playwright|테스트|pass", "judge_criteria": "테스트 작성 후 실행 PASS 확인"},
        {"id": "fe-005", "input": "npm run build 실패 — TypeScript 타입 오류 수정", "expected_tools": ["Read", "Edit", "Bash"], "expected_output_pattern": "TypeScript|build|타입|수정", "judge_criteria": "타입 오류 수정 후 빌드 PASS, 타입 캐스팅 남용 금지"},
    ],
    "ui-designer": [
        {"id": "uid-001", "input": "CH1 경제 채널 썸네일 디자인 시스템 리뉴얼 — 색상 코딩 개선", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "썸네일|색상|디자인|시스템", "judge_criteria": "globals.css 토큰 수정, 채널별 색상 일관성"},
        {"id": "uid-002", "input": "globals.css Tailwind CSS v4 마이그레이션 — v3 유틸리티 제거", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "Tailwind|v4|마이그레이션|CSS", "judge_criteria": "v3 deprecated 유틸리티 교체, 디자인 토큰 유지"},
        {"id": "uid-003", "input": "LoRA 캐릭터 드리프트 비주얼 QA — 7채널 캐릭터 일관성 점검", "expected_tools": ["Read"], "expected_output_pattern": "드리프트|캐릭터|일관성|QA", "judge_criteria": "채널별 기준 시각 대비 현재 출력 비교 분석"},
        {"id": "uid-004", "input": "다크모드 색상 토큰 추가 — 모든 컴포넌트 지원", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "다크모드|토큰|CSS|변수", "judge_criteria": "CSS custom property 추가, 기존 라이트모드 유지"},
        {"id": "uid-005", "input": "온보딩 페이지 UX 개선 — ux-auditor 리포트 반영", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "온보딩|UX|개선|반영", "judge_criteria": "ux-auditor 지적 사항 수정, WCAG AA 준수"},
    ],
    "mlops-engineer": [
        {"id": "ml-001", "input": "SD XL LoRA CH3 심리 캐릭터 드리프트 DRIFT_THRESHOLD 0.7 초과", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "드리프트|재훈련|DRIFT_THRESHOLD|LoRA", "judge_criteria": "임계값 초과 감지, 재훈련 트리거, LORA_VERSION 업데이트"},
        {"id": "ml-002", "input": "ElevenLabs 나레이션 품질 저하 — 특정 음성 ID 이상 감지", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "ElevenLabs|품질|음성|분석", "judge_criteria": "음성 품질 지표 확인, 대체 음성 ID 제안"},
        {"id": "ml-003", "input": "Faster-Whisper 자막 오류율 5% 초과 — 정확도 개선", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "Whisper|자막|정확도|개선", "judge_criteria": "모델 파라미터 조정, 후처리 로직 개선"},
        {"id": "ml-004", "input": "신규 LoRA 체크포인트 v2.2 배포 — 7채널 롤아웃 계획", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "LoRA|배포|롤아웃|체크포인트", "judge_criteria": "단계적 롤아웃(CH1 먼저), A/B 비교, 롤백 계획"},
        {"id": "ml-005", "input": "SD XL 렌더링 중 GPU OOM — 배치 크기 최적화", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "OOM|배치|최적화|GPU", "judge_criteria": "배치 크기 조정, 메모리 효율 개선, 품질 손실 최소화"},
    ],
    "media-engineer": [
        {"id": "me-001", "input": "Step10 FFmpeg 인코딩 타임아웃 — CRF/preset 설정 조정 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "FFmpeg|CRF|preset|타임아웃", "judge_criteria": "CRF 값과 preset 조합 최적화, 인코딩 시간 단축"},
        {"id": "me-002", "input": "CH1 영상 EBU R128 라우드니스 -11 LUFS — -14 기준 미달", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "EBU R128|라우드니스|LUFS|필터", "judge_criteria": "loudnorm 필터 파라미터 조정, target LUFS 준수"},
        {"id": "me-003", "input": "HLS 스트리밍 세그먼트 길이 불일치 — 재생 끊김 수정", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "HLS|세그먼트|스트리밍|수정", "judge_criteria": "hls_time 파라미터 조정, 세그먼트 일관성 확보"},
        {"id": "me-004", "input": "4K 소스 → 1080p 트랜스코딩 속도 최적화 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "트랜스코딩|1080p|최적화|속도", "judge_criteria": "하드웨어 가속(nvenc/vaapi) 활용 여부 검토, 품질 유지"},
        {"id": "me-005", "input": "배경 음악 오디오 노이즈 — afftdn 필터 체인 구성", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "노이즈|필터|afftdn|오디오", "judge_criteria": "FFmpeg 필터 체인 구성, SNR 개선, 음질 유지"},
    ],
    "devops-engineer": [
        {"id": "devops-001", "input": "PreToolUse 훅 미작동 — backend-engineer web/ 접근 차단 실패", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "hook|settings|trigger|차단", "judge_criteria": "hooks 설정 확인 및 올바른 이벤트 재등록"},
        {"id": "devops-002", "input": "CLAUDE.md 토큰 250줄 초과 경고 — 최적화 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "token|on-demand|paths|줄", "judge_criteria": "paths frontmatter로 on-demand 이동, 240줄 이하 달성"},
        {"id": "devops-003", "input": "신규 에이전트 .md CI 빌드 차단 — golden.jsonl 누락", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "eval|golden.jsonl|CI|5건", "judge_criteria": "golden.jsonl 5건 추가 안내, eval.yml 게이트 설명"},
        {"id": "devops-004", "input": "ngrok 터널 단절 — cwstudio.ngrok.app 응답 없음", "expected_tools": ["Bash"], "expected_output_pattern": "ngrok|restart|kas-studio|복구", "judge_criteria": "ngrok start kas-studio 실행, 터널 복구 확인"},
        {"id": "devops-005", "input": ".env.example 신규 환경변수 3개 추가 — 문서화 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": ".env|환경변수|문서|추가", "judge_criteria": ".env.example 업데이트, CLAUDE.md 환경변수 테이블 반영"},
    ],
    "sre-engineer": [
        {"id": "sre-001", "input": "Sentry 24h Critical 에러 7건 급증 — 원인 분석 및 조치", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "Sentry|Critical|원인|조치", "judge_criteria": "에러 패턴 분류, 우선순위 별 조치 계획, data/sre/ 저장"},
        {"id": "sre-002", "input": "Step08 오케스트레이터 메모리 사용량 지속 증가 — 누수 감지", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "메모리|누수|힙|분석", "judge_criteria": "누수 원인 분석(read-only), backend-engineer에 SendMessage"},
        {"id": "sre-003", "input": "SLO 99.5% 위반 — 이번 달 다운타임 2.5시간 초과", "expected_tools": ["Read"], "expected_output_pattern": "SLO|다운타임|위반|보고", "judge_criteria": "SLO 위반 보고서 작성, Error Budget 소진율, 개선 계획"},
        {"id": "sre-004", "input": "YouTube API 일일 쿼터 95% 소진 — 긴급 운영 계획", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "쿼터|quota|긴급|운영", "judge_criteria": "쿼터 소진 속도 분석, 우선순위 채널 선정, backend-engineer 에스컬레이션"},
        {"id": "sre-005", "input": "파이프라인 Step06→Step07 순서 데드락 — 2개 run 동시 실패", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "데드락|deadlock|Step|분석", "judge_criteria": "데드락 원인 분석(read-only), pipeline-debugger 또는 backend-engineer 협업"},
    ],
    "code-refactorer": [
        {"id": "cr-001", "input": "src/step08/orchestrator.py 850줄 God Module 분해 요청", "expected_tools": ["Read", "Glob", "Bash"], "expected_output_pattern": "분해|모듈|worktree|리팩토링", "judge_criteria": "worktree 격리 후 작업, 테스트 전부 PASS 유지, 800줄 이하 분리"},
        {"id": "cr-002", "input": "src/core/config.py ↔ src/step00/channel_registry.py 순환 import 해결", "expected_tools": ["Read", "Grep", "Edit"], "expected_output_pattern": "순환|import|의존성|해결", "judge_criteria": "순환 의존성 제거, import 구조 단방향화"},
        {"id": "cr-003", "input": "동일 JSON 파싱 로직 3개 모듈 중복 — 공통 유틸 추출", "expected_tools": ["Read", "Grep", "Edit", "Write"], "expected_output_pattern": "중복|유틸|추출|공통", "judge_criteria": "공통 유틸 함수 생성, 3곳 교체, 테스트 추가"},
        {"id": "cr-004", "input": "worktree 격리 후 Step05 리팩토링 브랜치 PR 준비", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "worktree|브랜치|PR|격리", "judge_criteria": "worktree 생성, 리팩토링 완료, 테스트 PASS, PR 준비"},
        {"id": "cr-005", "input": "테스트 커버리지 38% → 80% — 구조 개선으로 테스트 용이성 향상", "expected_tools": ["Read", "Bash", "Edit"], "expected_output_pattern": "커버리지|테스트|구조|개선", "judge_criteria": "테스트 불가 원인(강결합/사이드이펙트) 해소, coverage 목표 달성"},
    ],
    "pipeline-debugger": [
        {"id": "pd-001", "input": "Step05 트렌드 수집 0건 — 원인 분석 요청", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "Step05|수집|원인|분석", "judge_criteria": "API 응답·quota·설정 순서로 원인 추적(read-only), backend-engineer에 SendMessage"},
        {"id": "pd-002", "input": "Step08 Manim 렌더 타임아웃 — 스택 트레이스 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "Manim|타임아웃|스택|분석", "judge_criteria": "트레이스 분석 후 원인 특정(read-only), python-dev 에스컬레이션"},
        {"id": "pd-003", "input": "manifest.json status FAILED — 체크포인트 복구 방법 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "manifest|FAILED|복구|분석", "judge_criteria": "실패 Step 특정, 체크포인트에서 재시작 방법 제시"},
        {"id": "pd-004", "input": "Gemini API 429 쿼터 초과 — 재시도 전략 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "429|쿼터|재시도|전략", "judge_criteria": "지수 백오프 전략 분석, gemini_quota.py 설정 확인"},
        {"id": "pd-005", "input": "Step11 QA 자동 실패율 15% — 실패 패턴 유형 분류 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "QA|실패|패턴|분류", "judge_criteria": "실패 로그 분석, 유형별 분류(스크립트/썸네일/자막), backend-engineer 권고"},
    ],
    "release-manager": [
        {"id": "rm-001", "input": "v10.0 릴리스 CHANGELOG 작성 요청", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "CHANGELOG|v10.0|Keep-a-Changelog|릴리스", "judge_criteria": "Keep-a-Changelog 형식 준수, 모든 Phase 포함"},
        {"id": "rm-002", "input": "git tag v10.0 + GitHub Release 노트 생성", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "tag|release|GitHub|v10.0", "judge_criteria": "annotated tag 생성, release notes 자동 생성"},
        {"id": "rm-003", "input": "PR 머지 후 pyproject.toml 버전 범프 자동화", "expected_tools": ["Read", "Edit", "Bash"], "expected_output_pattern": "버전|범프|pyproject|자동화", "judge_criteria": "semantic versioning 준수, CHANGELOG 동기화"},
        {"id": "rm-004", "input": "핫픽스 v10.0.1 — Step08 크리티컬 버그 긴급 패치 배포", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "핫픽스|hotfix|패치|배포", "judge_criteria": "hotfix 브랜치 전략, 패치 노트 작성, 빠른 릴리스"},
        {"id": "rm-005", "input": "릴리스 브랜치 보호 규칙 설정 — main 직접 push 차단", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "보호|branch|main|규칙", "judge_criteria": "GitHub 브랜치 보호 규칙, PR 필수 리뷰 설정"},
    ],
    "documentation-writer": [
        {"id": "dw-001", "input": "Step08 오케스트레이터 API 문서 작성 — 함수 레퍼런스 포함", "expected_tools": ["Read", "Write"], "expected_output_pattern": "API|문서|레퍼런스|Step08", "judge_criteria": "docs/ 에만 작성, 함수 시그니처·파라미터·반환값 포함"},
        {"id": "dw-002", "input": "신규 에이전트 온보딩 가이드 ADR 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "ADR|온보딩|가이드|에이전트", "judge_criteria": "ADR 형식 준수(Context/Decision/Consequences), docs/ 저장"},
        {"id": "dw-003", "input": "CLAUDE.md 누락 실행 명령어 3개 보완 요청", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "CLAUDE.md|명령어|보완|추가", "judge_criteria": "실제 동작하는 명령어만 추가, 240줄 한도 유지"},
        {"id": "dw-004", "input": "DB 스키마 변경 결정 ADR 양식 — db-architect 협업", "expected_tools": ["Read", "Write"], "expected_output_pattern": "ADR|스키마|결정|기록", "judge_criteria": "ADR 양식 작성, docs/adr/ 저장, db-architect 검토 요청"},
        {"id": "dw-005", "input": "파이프라인 Step00~17 운영 매뉴얼 초안 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "매뉴얼|Step|운영|가이드", "judge_criteria": "각 Step 입력/출력/실패 대응 포함, docs/ 저장"},
    ],
    "qa-auditor": [
        {"id": "qa-001", "input": "OWASP Top 10 기반 전체 코드 보안 감사 요청", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "OWASP|보안|감사|취약점", "judge_criteria": "감사팀 구성(security-engineer 포함), 발견 이슈 severity 분류"},
        {"id": "qa-002", "input": "신규 에이전트 partnerships-manager.md 보안 리뷰", "expected_tools": ["Read"], "expected_output_pattern": "리뷰|권한|disallowedTools|보안", "judge_criteria": "disallowedTools 적절성, permissionMode, SSOT 경계 확인"},
        {"id": "qa-003", "input": "Step11 QA 실패율 15% — 감사팀 구성 및 원인 규명", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "감사|팀|구성|원인", "judge_criteria": "코드 수정 없이 원인 분석, backend-engineer에 SendMessage"},
        {"id": "qa-004", "input": "Supabase RLS — service_role 우회 가능한 테이블 발견", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "RLS|우회|발견|보고", "judge_criteria": "발견 보고 후 db-architect에 수정 위임, 직접 수정 금지"},
        {"id": "qa-005", "input": "월간 품질 보고서 — 모든 에이전트 eval 점수 집계", "expected_tools": ["Read", "Write"], "expected_output_pattern": "품질|보고서|eval|집계", "judge_criteria": "37개 에이전트 점수 집계, 미달 에이전트 조치 계획"},
    ],
    "performance-analyst": [
        {"id": "perf-001", "input": "Step05 Supabase 쿼리 N+1 패턴 — 최적화 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "N+1|쿼리|분석|최적화", "judge_criteria": "N+1 위치 특정(read-only), 인덱스/JOIN 권고, db-architect에 SendMessage"},
        {"id": "perf-002", "input": "web/ 번들 사이즈 5.2MB — 3MB 목표 달성 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "번들|사이즈|분석|최적화", "judge_criteria": "번들 분석, 청크 분리 권고, frontend-engineer에 SendMessage"},
        {"id": "perf-003", "input": "Python 메모리 힙 프로파일 — Step08 장기 실행 누수 감지", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "메모리|힙|누수|프로파일", "judge_criteria": "메모리 증가 패턴 식별(read-only), backend-engineer 권고"},
        {"id": "perf-004", "input": "src/ time.sleep 하드코딩 17곳 발견 — 영향 분석", "expected_tools": ["Read", "Bash", "Grep"], "expected_output_pattern": "time.sleep|하드코딩|영향|분석", "judge_criteria": "모든 위치 목록화, 각 위치 위험도, backend-engineer 수정 권고"},
        {"id": "perf-005", "input": "캐시 적중률 28% — Gemini 응답 캐시 전략 개선 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "캐시|적중률|전략|개선", "judge_criteria": "현재 캐시 전략 분석, TTL·키 전략 개선안, backend-engineer 위임"},
    ],
    "ux-auditor": [
        {"id": "ux-001", "input": "대시보드 색상 대비 WCAG 2.1 AA 미달 항목 감사", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "WCAG|색상|대비|미달", "judge_criteria": "AA 기준(4.5:1) 미달 요소 특정, ui-designer/frontend-engineer에 SendMessage"},
        {"id": "ux-002", "input": "키보드 네비게이션 포커스 트랩 — 모달 내부 무한 루프", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "키보드|포커스|트랩|접근성", "judge_criteria": "트랩 위치 특정(read-only), 수정 권고, frontend-engineer에 위임"},
        {"id": "ux-003", "input": "스크린리더 aria-label 누락 20개 — 접근성 감사", "expected_tools": ["Read", "Grep"], "expected_output_pattern": "aria|스크린리더|누락|접근성", "judge_criteria": "누락 요소 전체 목록화, 올바른 aria 패턴 제시"},
        {"id": "ux-004", "input": "모바일 터치 타겟 크기 44px 미달 버튼 감사", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "터치|타겟|44px|모바일", "judge_criteria": "미달 버튼 목록, Tailwind 수정 권고, frontend-engineer에 위임"},
        {"id": "ux-005", "input": "폼 에러 메시지 접근성 — role=alert aria-live 누락 감사", "expected_tools": ["Read", "Grep"], "expected_output_pattern": "폼|에러|aria-live|접근성", "judge_criteria": "에러 메시지 패턴 분석, ARIA live region 적용 권고"},
    ],
    "security-engineer": [
        {"id": "sec-001", "input": "CH1 OAuth 액세스 토큰 만료 갱신 실패 — 런타임 원인 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "OAuth|토큰|만료|분석", "judge_criteria": "refresh 흐름 분석(read-only), 갱신 실패 원인 특정, backend-engineer 협업"},
        {"id": "sec-002", "input": "Supabase RLS service_role 우회 — 보안 취약점 긴급 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "RLS|service_role|취약점|분석", "judge_criteria": "우회 경로 분석(read-only), 즉시 조치 권고, db-architect 에스컬레이션"},
        {"id": "sec-003", "input": "로그에서 API 키 노출 감지 — 즉시 대응 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "API키|노출|대응|분석", "judge_criteria": "노출 범위 분석, 키 교체 절차, 로그 마스킹 권고"},
        {"id": "sec-004", "input": "외부 URL 직접 호출 패턴 — SSRF 취약점 가능성 분석", "expected_tools": ["Read", "Grep", "Bash"], "expected_output_pattern": "SSRF|외부URL|취약점|분석", "judge_criteria": "SSRF 가능 경로 특정(read-only), 화이트리스트 검증 권고"},
        {"id": "sec-005", "input": "Python pickle 사용 발견 — 역직렬화 공격 위험 분석", "expected_tools": ["Read", "Grep"], "expected_output_pattern": "pickle|역직렬화|위험|분석", "judge_criteria": "pickle 사용 위치 전수 조사, json 대체 권고, 위험도 평가"},
    ],
    "content-director": [
        {"id": "cd-001", "input": "CH1 경제 채널 이번 달 스크립트 4편 품질 리뷰", "expected_tools": ["Read"], "expected_output_pattern": "스크립트|품질|리뷰|개선", "judge_criteria": "채널 톤 일관성, SEO 키워드 포함, 개선 피드백(read-only)"},
        {"id": "cd-002", "input": "CH1 경제 채널 썸네일 CTR 1.8% → 4% 개선 전략", "expected_tools": ["Read"], "expected_output_pattern": "CTR|썸네일|전략|개선", "judge_criteria": "CTR 저조 원인 분석, 제목·이미지 개선안, ui-designer 위임"},
        {"id": "cd-003", "input": "7채널 SEO 제목 최적화 — 인기 키워드 반영 가이드", "expected_tools": ["Read"], "expected_output_pattern": "SEO|키워드|제목|최적화", "judge_criteria": "채널별 타겟 키워드 선정, 제목 포맷 가이드"},
        {"id": "cd-004", "input": "2026 Q3 시즌 콘텐츠 캘린더 기획 — 7채널 통합", "expected_tools": ["Read", "Write"], "expected_output_pattern": "캘린더|콘텐츠|Q3|기획", "judge_criteria": "채널별 주제 배분, revenue-strategist 협업, data/creative/ 저장"},
        {"id": "cd-005", "input": "트렌드 바이럴 주제 긴급 영상 제작 — 48시간 내 납품", "expected_tools": ["Read"], "expected_output_pattern": "긴급|트렌드|바이럴|계획", "judge_criteria": "긴급 제작 가능 채널 선정, backend-engineer 파이프라인 우선순위 조정"},
    ],
    "revenue-strategist": [
        {"id": "rev-001", "input": "이번 달 수익성 상위 주제 5개 선별 — 7채널 대상", "expected_tools": ["Read"], "expected_output_pattern": "수익성|주제|선별|RPM", "judge_criteria": "채널 RPM 기반 선별, scorer 가중치 적용(수익성 20%), 근거 명시"},
        {"id": "rev-002", "input": "scorer 가중치 수익성 파라미터 20% → 25% 재조정 분석", "expected_tools": ["Read"], "expected_output_pattern": "scorer|가중치|수익성|분석", "judge_criteria": "재조정 영향 분석(read-only), python-dev에 구현 위임"},
        {"id": "rev-003", "input": "RPM $8 경제채널 vs $3 미스터리채널 포트폴리오 균형 분석", "expected_tools": ["Read"], "expected_output_pattern": "RPM|포트폴리오|균형|분석", "judge_criteria": "수익·성장성 트레이드오프, 최적 편수 배분 권고"},
        {"id": "rev-004", "input": "YouTube 경쟁 AI 채널 상위 10개 벤치마킹 분석", "expected_tools": ["Read"], "expected_output_pattern": "벤치마킹|경쟁|분석|전략", "judge_criteria": "경쟁 채널 강점 분석, Loomix 차별화 포인트 도출"},
        {"id": "rev-005", "input": "월간 7채널 × 4편 포트폴리오 배분 최적화 제안", "expected_tools": ["Read", "Write"], "expected_output_pattern": "포트폴리오|배분|최적화|월간", "judge_criteria": "채널별 RPM·성장률 기반 편수 배분, data/creative/ 저장"},
    ],
    "sales-manager": [
        {"id": "sales-001", "input": "기업 브랜드 콜라보 월 300만원 제안서 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "제안서|콜라보|300만원|계약", "judge_criteria": "제안서 포함 항목(채널 실적·단가·일정), data/sales/ 저장"},
        {"id": "sales-002", "input": "스폰서십 단가 월 150만원 협상 — 거래처 반론 대응", "expected_tools": ["Read"], "expected_output_pattern": "협상|단가|반론|대응", "judge_criteria": "가치 기반 협상 전략, legal-counsel 검토 요청"},
        {"id": "sales-003", "input": "신규 클라이언트 온보딩 — 계약 체결 후 인수인계 프로세스", "expected_tools": ["Read", "Write"], "expected_output_pattern": "온보딩|프로세스|인수인계|클라이언트", "judge_criteria": "project-manager 협업, 온보딩 체크리스트 작성"},
        {"id": "sales-004", "input": "Q2 매출 파이프라인 현황 — 성사 확률별 가중 매출 집계", "expected_tools": ["Read", "Write"], "expected_output_pattern": "파이프라인|매출|Q2|현황", "judge_criteria": "확률 가중 집계, ceo 경영 보고 인풋, data/sales/ 저장"},
        {"id": "sales-005", "input": "계약 해지 요청 클라이언트 — 법적 해지 절차 검토 요청", "expected_tools": ["Read"], "expected_output_pattern": "해지|절차|법적|legal", "judge_criteria": "legal-counsel 에스컬레이션, 손해배상 리스크 분석"},
    ],
    "project-manager": [
        {"id": "pm-001", "input": "수주 영상 제작 프로젝트 30편 — 6주 딜리버리 일정 수립", "expected_tools": ["Read", "Write"], "expected_output_pattern": "일정|마일스톤|딜리버리|30편", "judge_criteria": "WBS 작성, 리소스 배분, data/pm/ 저장"},
        {"id": "pm-002", "input": "backend-engineer 3개 프로젝트 동시 할당 — 과부하 조정", "expected_tools": ["Read"], "expected_output_pattern": "과부하|리소스|조정|우선순위", "judge_criteria": "우선순위 재조정, cto 협의, 일정 재협상 계획"},
        {"id": "pm-003", "input": "마일스톤 1주 지연 — 클라이언트 보고 초안 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "지연|보고|클라이언트|대응", "judge_criteria": "지연 원인·복구 계획·영향 포함, 투명한 커뮤니케이션"},
        {"id": "pm-004", "input": "프로젝트 위험 요소 식별 — API 쿼터 고갈 리스크", "expected_tools": ["Read"], "expected_output_pattern": "위험|리스크|식별|완화", "judge_criteria": "리스크 매트릭스(확률×영향), 완화 계획, sre-engineer 협업"},
        {"id": "pm-005", "input": "30편 프로젝트 완료 후 회고 보고서 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "회고|보고서|완료|교훈", "judge_criteria": "KPI 달성률, 교훈, 다음 프로젝트 개선사항 포함"},
    ],
    "partnerships-manager": [
        {"id": "pt-001", "input": "화장품 브랜드 CH3 심리 채널 콜라보 계약 조건 검토", "expected_tools": ["Read"], "expected_output_pattern": "콜라보|계약|조건|검토", "judge_criteria": "채널 적합성 평가, 단가·조건 분석, legal-counsel 협업"},
        {"id": "pt-002", "input": "스폰서 콘텐츠 게시 가이드라인 — YouTube 정책 준수 수립", "expected_tools": ["Read", "Write"], "expected_output_pattern": "스폰서|가이드라인|정책|수립", "judge_criteria": "compliance-officer 확인, FTC 공시 요건 포함"},
        {"id": "pt-003", "input": "파트너십 KPI 월간 성과 — 노출·클릭·전환 보고", "expected_tools": ["Read", "Write"], "expected_output_pattern": "KPI|성과|월간|보고", "judge_criteria": "파트너별 KPI 집계, data/partnerships/ 저장, sales-manager 공유"},
        {"id": "pt-004", "input": "신규 파트너 후보 5개 기업 리서치 및 우선순위 평가", "expected_tools": ["Read", "Write"], "expected_output_pattern": "파트너|리서치|평가|우선순위", "judge_criteria": "채널 적합성·예산·성장성 기준 평가"},
        {"id": "pt-005", "input": "1년 파트너십 갱신 협상 — 단가 10% 인상 요청", "expected_tools": ["Read"], "expected_output_pattern": "갱신|협상|인상|전략", "judge_criteria": "채널 성장 데이터 기반 협상 전략, legal-counsel 검토"},
    ],
    "marketing-manager": [
        {"id": "mkt-001", "input": "7채널 통합 브랜드 캠페인 기획 — Loomix 브랜드 런칭", "expected_tools": ["Read", "Write"], "expected_output_pattern": "브랜드|캠페인|기획|런칭", "judge_criteria": "7채널 통합 메시지, 타겟 페르소나, data/marketing/ 저장"},
        {"id": "mkt-002", "input": "인바운드 마케팅 SEO 콘텐츠 전략 — 유입 채널 다각화", "expected_tools": ["Read", "Write"], "expected_output_pattern": "SEO|인바운드|콘텐츠|전략", "judge_criteria": "채널별 SEO 키워드, 콘텐츠 캘린더, content-director 협업"},
        {"id": "mkt-003", "input": "7채널 SNS 팔로워 주간 성장 지표 보고 — 목표 대비 분석", "expected_tools": ["Read", "Write"], "expected_output_pattern": "SNS|팔로워|성장|지표", "judge_criteria": "채널별 성장률 분석, 저성장 원인, 개선 액션"},
        {"id": "mkt-004", "input": "경쟁 AI YouTube 채널 마케팅 전략 벤치마킹", "expected_tools": ["Read"], "expected_output_pattern": "벤치마킹|경쟁|마케팅|분석", "judge_criteria": "3개 이상 경쟁 채널 분석, Loomix 차별화 전략"},
        {"id": "mkt-005", "input": "신규 CH8 채널 런칭 마케팅 플랜 — 1개월 내 1,000구독자", "expected_tools": ["Read", "Write"], "expected_output_pattern": "런칭|플랜|구독자|마케팅", "judge_criteria": "런칭 전후 액션 플랜, 목표 KPI, community-manager 협업"},
    ],
    "customer-support": [
        {"id": "cs-001", "input": "B2B 클라이언트 긴급 문의 — 납품 48시간 지연 항의", "expected_tools": ["Read", "Write"], "expected_output_pattern": "납품|지연|대응|에스컬레이션", "judge_criteria": "즉각 대응 초안, project-manager 에스컬레이션, SLA 확인"},
        {"id": "cs-002", "input": "서비스 품질 불만 — 영상 자막 오류 3건 클레임", "expected_tools": ["Read", "Write"], "expected_output_pattern": "불만|클레임|품질|대응", "judge_criteria": "사과·재제작 제안, qa-auditor 협업, 재발 방지"},
        {"id": "cs-003", "input": "FAQ 데이터베이스 업데이트 — 최근 반복 문의 10건 추가", "expected_tools": ["Read", "Write"], "expected_output_pattern": "FAQ|업데이트|문의|추가", "judge_criteria": "반복 패턴 식별, FAQ 항목 작성, data/cs/ 저장"},
        {"id": "cs-004", "input": "SLA 48시간 위반 — 대응 지연으로 클라이언트 패널티 요구", "expected_tools": ["Read"], "expected_output_pattern": "SLA|위반|패널티|대응", "judge_criteria": "SLA 계약 확인, 협상 전략, legal-counsel 협업"},
        {"id": "cs-005", "input": "분기 클라이언트 만족도 조사 결과 분석 — NPS 45 개선 방안", "expected_tools": ["Read", "Write"], "expected_output_pattern": "만족도|NPS|분석|개선", "judge_criteria": "NPS 저조 원인 분석, 개선 액션 플랜, marketing-manager 공유"},
    ],
    "community-manager": [
        {"id": "comm-001", "input": "CH1 경제 채널 주간 댓글 digest 작성 — 시청자 반응 분류", "expected_tools": ["Read", "Write"], "expected_output_pattern": "댓글|digest|분류|시청자", "judge_criteria": "긍정/부정/요청 분류, 주요 인사이트, content-director 루프백"},
        {"id": "comm-002", "input": "시청자 영상 주제 요청 50건 수집 — 빈도 분석 보고", "expected_tools": ["Read", "Write"], "expected_output_pattern": "요청|주제|분석|보고", "judge_criteria": "주제 빈도 집계, revenue-strategist 협업, data/community/ 저장"},
        {"id": "comm-003", "input": "CH4 미스터리 채널 악플 패턴 분석 — content-director 루프백", "expected_tools": ["Read"], "expected_output_pattern": "악플|패턴|분석|루프백", "judge_criteria": "악플 유형 분류(read-only), content-moderator 에스컬레이션"},
        {"id": "comm-004", "input": "CH6 과학 채널 커뮤니티 이벤트 기획 제안 — 구독자 참여", "expected_tools": ["Read", "Write"], "expected_output_pattern": "이벤트|기획|참여|커뮤니티", "judge_criteria": "이벤트 형식·일정·기대 효과 포함, marketing-manager 협업"},
        {"id": "comm-005", "input": "멤버십 시청자 피드백 집계 — 콘텐츠 방향 개선 보고", "expected_tools": ["Read", "Write"], "expected_output_pattern": "멤버십|피드백|집계|보고", "judge_criteria": "피드백 분류, 콘텐츠 개선 제안, content-director 전달"},
    ],
    "content-moderator": [
        {"id": "cmod-001", "input": "CH4 미스터리 채널 혐오 표현 댓글 20건 감지 — 조치", "expected_tools": ["Read"], "expected_output_pattern": "혐오|댓글|감지|조치", "judge_criteria": "심각도 분류(read-only), 즉시 삭제 권고, compliance-officer 협업"},
        {"id": "cmod-002", "input": "스팸 봇 공격 — 7채널 동시 악성 댓글 500건 처리", "expected_tools": ["Read"], "expected_output_pattern": "스팸|봇|악성|처리", "judge_criteria": "자동 필터 권고(read-only), YouTube 신고 절차, community-manager 협업"},
        {"id": "cmod-003", "input": "CH3 심리 채널 부정적 바이럴 확산 — 위기 대응", "expected_tools": ["Read"], "expected_output_pattern": "위기|바이럴|대응|확산", "judge_criteria": "위기 심각도 평가(read-only), 대응 전략, marketing-manager 에스컬레이션"},
        {"id": "cmod-004", "input": "2026 YouTube 댓글 모더레이션 정책 업데이트 — 검토", "expected_tools": ["Read"], "expected_output_pattern": "정책|업데이트|검토|준수", "judge_criteria": "변경 항목 식별, compliance-officer 협업, 내부 가이드 업데이트 권고"},
        {"id": "cmod-005", "input": "월간 콘텐츠 위반 패턴 보고서 — 채널별 위험도 분류", "expected_tools": ["Read", "Write"], "expected_output_pattern": "위반|패턴|보고서|위험도", "judge_criteria": "채널별 위반 유형·건수, 위험도 분류, 예방 권고"},
    ],
    "finance-manager": [
        {"id": "fin-001", "input": "Gemini API 일일 비용 $3.50 집계 보고 — 월간 추이 분석", "expected_tools": ["Read", "Write"], "expected_output_pattern": "비용|집계|월간|추이", "judge_criteria": "일별 비용 집계, 월간 소진율, BUDGET_LIMIT_USD 대비 현황"},
        {"id": "fin-002", "input": "월 예산 $50 한도 80% 도달 — circuit breaker 준비 알림", "expected_tools": ["Read", "Write"], "expected_output_pattern": "circuit breaker|예산|80%|알림", "judge_criteria": "잔여 예산 계산, ceo 알림, HIGH 에이전트 목록 확인"},
        {"id": "fin-003", "input": "7채널 YouTube AdSense 3월 P&L 마감 보고서 작성", "expected_tools": ["Read", "Write"], "expected_output_pattern": "P&L|마감|보고서|AdSense", "judge_criteria": "수익·비용·순이익 집계, 채널별 분류, ceo 제출"},
        {"id": "fin-004", "input": "Sonnet→Haiku 전환 비용 절감 ROI 분석", "expected_tools": ["Read", "Write"], "expected_output_pattern": "ROI|Haiku|절감|분석", "judge_criteria": "현재 Sonnet 비용 vs Haiku 비용 비교, 품질 저하 리스크 포함"},
        {"id": "fin-005", "input": "Q1 재무 보고서 ceo 제출 — 수익·비용·KPI 요약", "expected_tools": ["Read", "Write"], "expected_output_pattern": "Q1|재무|보고서|요약", "judge_criteria": "분기 재무 지표 포함, data/finance/ 저장, ceo에 SendMessage"},
    ],
    "data-analyst": [
        {"id": "da-001", "input": "Supabase BI 주간 채널 성과 대시보드 업데이트", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "대시보드|성과|업데이트|BI", "judge_criteria": "7채널 KPI 집계, 전주 대비 변화율, data/bi/ 저장"},
        {"id": "da-002", "input": "CH3 심리 채널 조회수 40% 급락 — 원인 분석", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "급락|원인|분석|조회수", "judge_criteria": "시계열 분석, 알고리즘 변화·경쟁 채널 요인 검토"},
        {"id": "da-003", "input": "7채널 CTR↔구독자 증가율 상관관계 분석 보고", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "CTR|구독자|상관관계|분석", "judge_criteria": "상관계수 계산, 유의미한 패턴 식별, revenue-strategist 공유"},
        {"id": "da-004", "input": "KPI 이상치 탐지 — CH5 전쟁사 채널 비정상 급증 원인", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "이상치|탐지|급증|원인", "judge_criteria": "통계적 이상치 판정, 바이럴 vs 데이터 오류 구분"},
        {"id": "da-005", "input": "Q1 수익 트렌드 시각화 보고 — 채널별 월간 추이", "expected_tools": ["Read", "Write"], "expected_output_pattern": "수익|트렌드|Q1|시각화", "judge_criteria": "채널별 월간 수익 집계, 성장률 분석, ceo 보고용 요약"},
    ],
    "data-engineer": [
        {"id": "de-001", "input": "Step05 ETL idempotency 위반 — 동일 트렌드 데이터 중복 수집", "expected_tools": ["Read", "Grep", "Edit"], "expected_output_pattern": "idempotency|중복|ETL|수정", "judge_criteria": "중복 원인 파악, upsert 키 수정, worktree 사용"},
        {"id": "de-002", "input": "Supabase 배치 upsert 1,000행 → 10,000행 성능 최적화", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "배치|upsert|성능|최적화", "judge_criteria": "배치 크기 조정, 인덱스 활용, 성능 개선 측정"},
        {"id": "de-003", "input": "지식 저장소 수집 파이프라인 오류 — 부분 실패 복구", "expected_tools": ["Read", "Bash", "Edit"], "expected_output_pattern": "수집|파이프라인|복구|실패", "judge_criteria": "체크포인트 기반 재시작, 데이터 일관성 보장"},
        {"id": "de-004", "input": "새 채널 CH8 데이터 파이프라인 추가 — Step05 ETL 확장", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "CH8|파이프라인|추가|ETL", "judge_criteria": "config.py 채널 추가 후 ETL 확장, worktree 격리"},
        {"id": "de-005", "input": "Step05 ETL 모듈 리팩토링 — worktree 격리 PR 준비", "expected_tools": ["Read", "Bash", "Edit"], "expected_output_pattern": "리팩토링|worktree|PR|ETL", "judge_criteria": "worktree 생성, 리팩토링 완료, 테스트 PASS, PR 브랜치"},
    ],
    "prompt-engineer": [
        {"id": "pe-001", "input": "Gemini 스크립트 생성 프롬프트 A/B 테스트 설계 — CH1 경제", "expected_tools": ["Read", "Write"], "expected_output_pattern": "A/B|프롬프트|테스트|설계", "judge_criteria": "variant A/B 차이 명확, 평가 메트릭 정의, 실험 기간 설정"},
        {"id": "pe-002", "input": "ElevenLabs 나레이션 프롬프트 토큰 사용량 30% 절감", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "토큰|절감|프롬프트|최적화", "judge_criteria": "토큰 줄이기 기법 적용, 품질 유지 확인, data/prompts/ 저장"},
        {"id": "pe-003", "input": "CH1~CH7 채널별 톤/스타일 프롬프트 변형 최적화", "expected_tools": ["Read", "Write"], "expected_output_pattern": "채널별|톤|스타일|변형", "judge_criteria": "7채널 각각의 특성 반영, 프롬프트 버전 관리"},
        {"id": "pe-004", "input": "Gemini 출력 불일치 20% — 프롬프트 안정화 방안", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "안정화|불일치|프롬프트|개선", "judge_criteria": "불일치 원인 분석, Few-shot 예제 추가, 온도 조정"},
        {"id": "pe-005", "input": "Gemini 2.5 Pro → 2.5 Flash 마이그레이션 — 품질 비교 테스트", "expected_tools": ["Read", "Write", "Bash"], "expected_output_pattern": "마이그레이션|Flash|품질|비교", "judge_criteria": "10개 샘플 비교, 품질·비용 트레이드오프, 마이그레이션 권고"},
    ],
    "agent-evaluator": [
        {"id": "ae-001", "input": "backend-engineer 세션 종료 후 SubagentStop — golden test 채점", "expected_tools": ["Read", "Write"], "expected_output_pattern": "채점|점수|golden|SubagentStop", "judge_criteria": "랜덤 1건 선택, LLM-as-judge 0~10 채점, data/ops/evals/ 저장"},
        {"id": "ae-002", "input": "mlops-engineer eval 점수 6.2→5.8→5.5 — 3연속 미달 알림", "expected_tools": ["Read", "Write"], "expected_output_pattern": "3연속|미달|알림|cto", "judge_criteria": "임계값(7점) 미달 3회 확인, cto에 SendMessage 알림"},
        {"id": "ae-003", "input": "frontend-engineer.md 변경 PR — regression 테스트 실행", "expected_tools": ["Read", "Bash"], "expected_output_pattern": "regression|PR|테스트|차단", "judge_criteria": "golden.jsonl 기반 regression 테스트, 점수 -1 이상 하락 시 차단"},
        {"id": "ae-004", "input": "pipeline-debugger LLM-as-judge 채점 결과 data/ops/evals/ 저장", "expected_tools": ["Read", "Write"], "expected_output_pattern": "채점|저장|LLM-as-judge|결과", "judge_criteria": "점수·근거·타임스탬프 포함 JSON 저장 형식 준수"},
        {"id": "ae-005", "input": "월간 eval 커버리지 리포트 — 37개 에이전트 평균 점수 집계", "expected_tools": ["Read", "Write"], "expected_output_pattern": "커버리지|리포트|37개|평균", "judge_criteria": "에이전트별 평균 점수, 미달(<7) 목록, 개선 권고"},
    ],
    "cost-router": [
        {"id": "cost-001", "input": "과업: '최신 트렌드 뉴스 300자 요약' — 모델 선택", "expected_tools": ["Read"], "expected_output_pattern": "haiku|모델|선택|복잡도", "judge_criteria": "haiku 선택, 이유 명시(단순 요약), data/ops/routing.json 업데이트"},
        {"id": "cost-002", "input": "과업: 'Supabase 전체 스키마 재설계 — 마이그레이션 포함' — 모델 선택", "expected_tools": ["Read"], "expected_output_pattern": "opus|모델|선택|복잡도", "judge_criteria": "opus 선택, 이유 명시(고복잡도), ultrathink 권고"},
        {"id": "cost-003", "input": "월간 모델 사용 비용 최적화 보고 — Haiku 전환 기회 분석", "expected_tools": ["Read", "Write"], "expected_output_pattern": "비용|최적화|Haiku|전환", "judge_criteria": "Sonnet→Haiku 전환 가능 과업 목록, 예상 절감 금액"},
        {"id": "cost-004", "input": "Haiku 전환 후 품질 저하 감지 — 자동 Sonnet 에스컬레이션", "expected_tools": ["Read", "Write"], "expected_output_pattern": "에스컬레이션|품질|Sonnet|자동", "judge_criteria": "품질 임계값 하락 감지, 자동 모델 업그레이드 로직"},
        {"id": "cost-005", "input": "복잡도 분류 기준 업데이트 — '영상 편집 지시' 신규 분류 추가", "expected_tools": ["Read", "Edit"], "expected_output_pattern": "분류|기준|업데이트|신규", "judge_criteria": "기존 분류 체계와 일관성, Sonnet 적합 이유 명시"},
    ],
    "debate-facilitator": [
        {"id": "df-001", "input": "수주 계약 200만원 승인 여부 — cto·legal-counsel·revenue-strategist 3명 debate", "expected_tools": ["Read", "Write"], "expected_output_pattern": "debate|3명|synthesis|Constitutional", "judge_criteria": "3명 병렬 의견 수렴, Constitutional AI synthesis, 핵심 쟁점 도출"},
        {"id": "df-002", "input": "CH4 미스터리 영상 정책 위반 대응 방법 — debate synthesis", "expected_tools": ["Read", "Write"], "expected_output_pattern": "정책|위반|synthesis|합의", "judge_criteria": "3개 관점(법·수익·커뮤니티) 수렴, 최선 대응안 도출"},
        {"id": "df-003", "input": "신규 에이전트 media-scientist 채용 여부 — Constitutional AI 합의", "expected_tools": ["Read", "Write"], "expected_output_pattern": "채용|합의|Constitutional|결정", "judge_criteria": "찬반 논거 균형 있게 수렴, 조건부 승인 등 합성 옵션 제시"},
        {"id": "df-004", "input": "월 예산 $50→$80 증액 여부 — ceo HITL 이전 debate", "expected_tools": ["Read", "Write"], "expected_output_pattern": "예산|증액|debate|HITL", "judge_criteria": "비용·수익·리스크 관점 3명 의견, synthesis 후 ceo HITL 전달"},
        {"id": "df-005", "input": "CH1 경제→CH8 AI 채널 전략 방향 전환 debate — 기록 저장", "expected_tools": ["Read", "Write"], "expected_output_pattern": "전략|전환|debate|기록", "judge_criteria": "data/exec/debates/ 저장, 3패널 의견 + synthesis 포함"},
    ],
}


total_updated = 0
for agent_dir in sorted(EVALS_DIR.iterdir()):
    if not agent_dir.is_dir():
        continue
    agent_name = agent_dir.name
    if agent_name not in ROLE_TESTS:
        print(f"  SKIP (no role tests defined): {agent_name}")
        continue

    golden_path = agent_dir / "golden.jsonl"
    tests = ROLE_TESTS[agent_name]
    lines = [json.dumps(t, ensure_ascii=False) for t in tests]
    golden_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total_updated += 1
    print(f"  OK {agent_name}: {len(tests)}건 역할 기반 테스트")

print(f"\n총 업데이트: {total_updated}/37 에이전트")

# 검증
total_ok = 0
for d in sorted(EVALS_DIR.iterdir()):
    f = d / "golden.jsonl"
    if f.exists():
        cnt = sum(1 for l in f.read_text(encoding="utf-8").strip().split("\n") if l.strip())
        if cnt >= 5:
            total_ok += 1
print(f"5건 이상 충족: {total_ok}/37")
