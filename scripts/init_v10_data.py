"""
v10.0 신규 SSOT 디렉토리 및 초기 JSON 파일 생성
7개 신규 경로: compliance, moderation, partnerships, ops/evals, ops/routing, exec/debates, mlops/media
"""
import sys
import io
import os
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트를 KAS_ROOT 또는 현재 디렉토리로 결정
ROOT = os.environ.get("KAS_ROOT", os.getcwd())


def write_json(path: str, data: dict) -> None:
    """SSOT 원칙: ssot.write_json 패턴 준수 (직접 open 대신)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {path}")


TODAY = datetime.now().strftime("%Y-%m-%d")
YEAR = datetime.now().strftime("%Y")
MONTH = datetime.now().strftime("%Y%m")

INIT_DATA = {
    # compliance-officer SSOT
    f"data/compliance/daily_audit.json": {
        "date": TODAY,
        "channel_audits": [],
        "policy_violations": [],
        "content_id_strikes": [],
        "status": "pending"
    },
    f"data/compliance/content_id_queue.json": {
        "queue": [],
        "processed": [],
        "last_updated": TODAY
    },
    f"data/compliance/gdpr_requests.json": {
        "requests": [],
        "last_updated": TODAY
    },

    # content-moderator SSOT
    f"data/moderation/queue.json": {
        "pending": [],
        "processed": [],
        "crisis_log": [],
        "last_updated": TODAY
    },

    # partnerships-manager SSOT
    f"data/partnerships/pipeline.json": {
        "prospects": [],
        "proposals": [],
        "active_deals": [],
        "closed": [],
        "last_updated": TODAY
    },

    # agent-evaluator SSOT
    f"data/ops/evals/.gitkeep": None,  # 디렉토리 생성용

    # cost-router SSOT
    f"data/ops/routing.json": {
        "monthly_stats": {
            MONTH: {
                "haiku_calls": 0,
                "sonnet_calls": 0,
                "opus_calls": 0,
                "estimated_savings_usd": 0.0
            }
        },
        "last_updated": TODAY
    },

    # debate-facilitator SSOT
    f"data/exec/debates/.gitkeep": None,  # 디렉토리 생성용

    # media-engineer SSOT
    f"data/mlops/media/encoding_params.json": {
        "current": {
            "crf": 23,
            "preset": "slow",
            "audio_target_lufs": -14.0,
            "video_codec": "libx264",
            "audio_codec": "aac"
        },
        "history": [],
        "last_updated": TODAY
    },

    # agent-evaluator — 샘플 golden test
    f".claude/evals/backend-engineer/golden.jsonl": None,  # 별도 처리

    # cost-tracker 출력 경로
    f"data/ops/agent_cost.json": {
        "sessions": [],
        "monthly_summary": {
            MONTH: {
                "total_cost_usd": 0.0,
                "by_agent": {}
            }
        },
        "last_updated": TODAY
    },

    # OKR 분기 계획
    f"data/exec/okrs/{YEAR}-q2.json": {
        "quarter": f"{YEAR}-Q2",
        "objectives": [
            {
                "id": "O1",
                "title": "7채널 월 수익 1,400만원 달성",
                "key_results": [
                    {"id": "KR1.1", "title": "채널당 월 200만원", "target": 2000000, "current": 0},
                    {"id": "KR1.2", "title": "평균 조회수 10만/영상", "target": 100000, "current": 0}
                ]
            },
            {
                "id": "O2",
                "title": "에이전트 시스템 품질 24.5/25 달성",
                "key_results": [
                    {"id": "KR2.1", "title": "Eval 커버리지 90%+", "target": 90, "current": 0},
                    {"id": "KR2.2", "title": "월 API 비용 $35 이하", "target": 35.0, "current": 0}
                ]
            }
        ],
        "created_by": "ceo",
        "created_at": TODAY
    },

    # 월간 성과 디렉토리
    f"data/exec/agent_performance/.gitkeep": None,
}


def write_golden_tests() -> None:
    """37개 에이전트별 golden.jsonl 초기 파일 생성"""
    import glob
    agent_files = glob.glob(".claude/agents/*.md")

    SAMPLE_TESTS = {
        "backend-engineer": [
            {"id": "be-001", "input": "src/step08/orchestrator.py에서 FFmpeg 타임아웃 발생", "expected_tools": ["Read", "Grep", "Edit"], "judge_criteria": "오류 원인 파악 + 수정안 제시"},
            {"id": "be-002", "input": "pytest tests/unit/test_ssot.py 실패 원인 분석", "expected_tools": ["Read", "Bash"], "judge_criteria": "실패 원인 + 수정 계획"},
        ],
        "frontend-engineer": [
            {"id": "fe-001", "input": "web/app/dashboard/page.tsx 데이터 로딩 오류", "expected_tools": ["Read", "Grep"], "judge_criteria": "컴포넌트 오류 원인 + 수정안"},
        ],
        "db-architect": [
            {"id": "db-001", "input": "trend_topics 테이블에 RPM 컬럼 추가 스키마 변경", "expected_tools": ["Read", "Write"], "judge_criteria": "마이그레이션 스크립트 + RLS 정책 + types.ts 동기화 3종 포함"},
        ],
        "qa-auditor": [
            {"id": "qa-001", "input": "src/core/oauth_setup.py OWASP Top10 감사", "expected_tools": ["Read", "Grep"], "judge_criteria": "취약점 분류 + 심각도 + 수정 담당자 명시"},
        ],
        "compliance-officer": [
            {"id": "co-001", "input": "CH4(미스터리) 신규 영상 콘텐츠 정책 체크", "expected_tools": ["Read"], "judge_criteria": "정책 위반 여부 + 조치 필요 항목"},
        ],
        "agent-evaluator": [
            {"id": "ae-001", "input": "backend-engineer 세션 결과물 품질 채점", "expected_tools": ["Read", "Bash"], "judge_criteria": "0~10 점수 + 근거 + data/ops/evals 기록"},
        ],
        "cost-router": [
            {"id": "cr-001", "input": "뉴스 기사 300자 요약 과업 모델 선택", "expected_tools": [], "judge_criteria": "haiku 권장 + 복잡도 1~3 + 이유"},
            {"id": "cr-002", "input": "src/ 전체 OWASP 정적 분석 과업 모델 선택", "expected_tools": [], "judge_criteria": "sonnet 이상 권장 + 복잡도 7+"},
        ],
        "debate-facilitator": [
            {"id": "df-001", "input": "수주 150만원 계약 HITL 토론 진행", "expected_tools": ["SendMessage"], "judge_criteria": "패널 3명 식별 + synthesis + COMPANY.md 준수 여부 체크"},
        ],
    }

    import glob as glob_mod

    for agent_file in agent_files:
        agent_name = os.path.basename(agent_file).replace(".md", "")
        eval_dir = f".claude/evals/{agent_name}"
        os.makedirs(eval_dir, exist_ok=True)
        golden_path = f"{eval_dir}/golden.jsonl"

        if not os.path.exists(golden_path):
            tests = SAMPLE_TESTS.get(agent_name, [
                {
                    "id": f"{agent_name[:2]}-001",
                    "input": f"{agent_name} 기본 미션 수행",
                    "expected_tools": ["Read"],
                    "judge_criteria": "SSOT 준수 + 역할 경계 내 작업 + 결과물 명확"
                }
            ])
            with open(golden_path, "w", encoding="utf-8") as f:
                for test in tests:
                    f.write(json.dumps(test, ensure_ascii=False) + "\n")

    eval_count = len(glob_mod.glob(".claude/evals/*/golden.jsonl"))
    print(f"  ✓ .claude/evals/ — {eval_count}개 에이전트 golden.jsonl 생성")


if __name__ == "__main__":
    print("=== v10.0 SSOT 디렉토리 + 초기 데이터 생성 ===")

    for path, data in INIT_DATA.items():
        if data is None:
            # .gitkeep 또는 별도 처리
            os.makedirs(os.path.dirname(path) if "." in os.path.basename(path) else path, exist_ok=True)
            if path.endswith(".gitkeep"):
                with open(path, "w") as f:
                    f.write("")
                print(f"  ✓ {path}")
        else:
            write_json(path, data)

    print("\n--- Golden test 파일 생성 ---")
    write_golden_tests()

    print("\n✅ v10.0 SSOT 초기화 완료")
    print(f"  신규 SSOT 경로: compliance, moderation, partnerships, ops/evals, ops/routing, exec/debates, mlops/media")
