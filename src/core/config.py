import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

KAS_ROOT = Path(os.getenv(
    "KAS_ROOT",
    r"C:\Users\조찬우\Desktop\AI_Animation_Stuidio",
))

# ─── API 키 ─────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY     = os.getenv("YOUTUBE_API_KEY", "")
SENTRY_DSN          = os.getenv("SENTRY_DSN", "")
TAVILY_API_KEY      = os.getenv("TAVILY_API_KEY", "")
PERPLEXITY_API_KEY  = os.getenv("PERPLEXITY_API_KEY", "")
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
SERPAPI_KEY         = os.getenv("SERPAPI_KEY", "")
NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 채널별 ElevenLabs 보이스 ID (등록 후 업데이트)
CHANNEL_VOICE_IDS = {
    "CH1": os.getenv("CH1_VOICE_ID", ""),
    "CH2": os.getenv("CH2_VOICE_ID", ""),
    "CH3": os.getenv("CH3_VOICE_ID", ""),
    "CH4": os.getenv("CH4_VOICE_ID", ""),
    "CH5": os.getenv("CH5_VOICE_ID", ""),
    "CH6": os.getenv("CH6_VOICE_ID", ""),
    "CH7": os.getenv("CH7_VOICE_ID", ""),
}

# USD → KRW 환산율 (YouTube 수익은 USD 기준)
USD_TO_KRW = int(os.getenv("USD_TO_KRW", "1350"))

# ─── 로그 / 모델 설정 ────────────────────────────────────────────
LOG_LEVEL         = os.getenv("KAS_LOG_LEVEL", "INFO")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-pro")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
MANIM_QUALITY     = os.getenv("MANIM_QUALITY", "l")
FFMPEG_PATH       = os.getenv("FFMPEG_PATH", "ffmpeg")
GTTS_LANG         = os.getenv("GTTS_LANG", "ko")

# ─── 디렉토리 구조 ───────────────────────────────────────────────
DATA_DIR      = KAS_ROOT / "data"
GLOBAL_DIR    = DATA_DIR / "global"
CHANNELS_DIR  = DATA_DIR / "channels"
KNOWLEDGE_DIR = DATA_DIR / "knowledge_store"
RUNS_DIR      = KAS_ROOT / "runs"
CREDENTIALS_DIR = KAS_ROOT / "credentials"
BGM_DIR       = KAS_ROOT / "bgm"
LOGS_DIR      = KAS_ROOT / "logs"

QUOTA_DIR   = GLOBAL_DIR / "quota"
CACHE_DIR   = GLOBAL_DIR / "cache"
MEMORY_DIR  = GLOBAL_DIR / "memory_store"
PILOT_DIR   = GLOBAL_DIR / "manim_pilot"
PLAN_DIR    = GLOBAL_DIR / "monthly_plan"
COST_DIR    = GLOBAL_DIR / "cost"
REVENUE_DIR = GLOBAL_DIR / "revenue"
RISK_DIR    = GLOBAL_DIR / "risk"
SUSTAIN_DIR = GLOBAL_DIR / "sustainability"

# ─── 7채널 구성 (2026-04-01 확정) ───────────────────────────────
CHANNEL_IDS = {
    "CH1": os.getenv("CH1_CHANNEL_ID", ""),
    "CH2": os.getenv("CH2_CHANNEL_ID", ""),
    "CH3": os.getenv("CH3_CHANNEL_ID", ""),
    "CH4": os.getenv("CH4_CHANNEL_ID", ""),
    "CH5": os.getenv("CH5_CHANNEL_ID", ""),
    "CH6": os.getenv("CH6_CHANNEL_ID", ""),
    "CH7": os.getenv("CH7_CHANNEL_ID", ""),
}

# 내부 카테고리 키 (scorer.py, trend_collector.py 등에서 사용)
CHANNEL_CATEGORIES = {
    "CH1": "economy",
    "CH2": "science",
    "CH3": "realestate",
    "CH4": "psychology",
    "CH5": "mystery",
    "CH6": "history",
    "CH7": "war_history",
}

# 표시용 한국어 카테고리명
CHANNEL_CATEGORY_KO = {
    "CH1": "경제",
    "CH2": "과학",
    "CH3": "부동산",
    "CH4": "심리",
    "CH5": "미스터리",
    "CH6": "역사",
    "CH7": "전쟁사",
}

# RPM 프록시 (원화, 안정화 후 예상값)
CHANNEL_RPM_PROXY = {
    "CH1": 7000,
    "CH2": 6000,
    "CH3": 4000,
    "CH4": 3500,
    "CH5": 3500,
    "CH6": 4000,
    "CH7": 4000,
}

# RPM 초기값 (런칭 후 3개월 내 예상값)
CHANNEL_RPM_INITIAL = {
    "CH1": 3500,
    "CH2": 3000,
    "CH3": 2000,
    "CH4": 1750,
    "CH5": 1750,
    "CH6": 2000,
    "CH7": 2000,
}

# 월 영상 편수 목표 (Long-form)
CHANNEL_MONTHLY_TARGET = {
    "CH1": 10,
    "CH2": 10,
    "CH3": 10,
    "CH4": 12,
    "CH5": 12,
    "CH6": 10,
    "CH7": 10,
}

# Shorts 월 편수 목표
CHANNEL_SHORTS_TARGET = {
    "CH1": 30,
    "CH2": 30,
    "CH3": 30,
    "CH4": 40,
    "CH5": 40,
    "CH6": 30,
    "CH7": 30,
}

# 론칭 Phase (숫자가 낮을수록 먼저 론칭)
CHANNEL_LAUNCH_PHASE = {
    "CH1": 1,
    "CH2": 1,
    "CH3": 2,
    "CH4": 2,
    "CH5": 3,
    "CH6": 3,
    "CH7": 3,
}

# 수익 목표
REVENUE_TARGET_PER_CHANNEL = 2_000_000   # 채널당 월 200만원 (안정화 목표)
REVENUE_TARGET_TOTAL       = 14_000_000  # 7채널 합산 월 1,400만원

# Phase별 단계적 수익 목표 (채널당, 원화)
# Phase 1 (month 1~2): 초기 - 알고리즘 진입 전 수익 미미
# Phase 2 (month 3~5): 성장 - 구독자 확보 단계
# Phase 3 (month 6+): 안정화 - 목표 수익 달성 단계
REVENUE_TARGET_BY_PHASE = {
    1: 0,           # 초기: 수익화 미적용, 알고리즘 진입 집중
    2: 500_000,     # 성장: 채널당 월 50만원 목표
    3: 2_000_000,   # 안정화: 채널당 월 200만원 목표
}

# RPM 실측값 (원화/1,000회 조회수) — 파이프라인 실행 후 KPI 수집 시 업데이트
# None = 아직 실측 데이터 없음 (CHANNEL_RPM_INITIAL/PROXY 사용)
CHANNEL_RPM_ACTUAL = {
    "CH1": None,
    "CH2": None,
    "CH3": None,
    "CH4": None,
    "CH5": None,
    "CH6": None,
    "CH7": None,
}

# 채널별 훅 방향 (step03/step06 공통 SSOT)
CHANNEL_HOOK_DIRECTION = {
    "CH1": "경제적 손실 공포 + 기회 제시",
    "CH2": "과학적 충격 사실 + 원리 해설 약속",
    "CH3": "부동산 손실 위험 + 기회 포착 방법",
    "CH4": "행동 패턴 충격 사실 + 변화 약속",
    "CH5": "미스터리 서스펜스 + 미해결 의문 제기",
    "CH6": "숨겨진 역사적 진실 + 교훈 제시",
    "CH7": "충격적 전황 + 숨겨진 역사적 사실 제시",
}

# 채널별 최적 업로드 시간 (KST 24시간 형식)
CHANNEL_OPTIMAL_UPLOAD_KST: dict = {
    "CH1": "14:00",  # 경제 — 점심 후 직장인
    "CH2": "19:00",  # 과학 — 저녁 여가
    "CH3": "12:00",  # 부동산 — 점심 탐색
    "CH4": "21:00",  # 심리 — 취침 전
    "CH5": "20:00",  # 미스터리 — 저녁
    "CH6": "18:00",  # 역사 — 퇴근 후
    "CH7": "17:00",  # 전쟁사 — 퇴근 직후
}
