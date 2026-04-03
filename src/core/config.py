from pathlib import Path
from dotenv import load_dotenv
import os

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

# ─── 로그 / 모델 설정 ────────────────────────────────────────────
LOG_LEVEL         = os.getenv("KAS_LOG_LEVEL", "INFO")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")
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
    "CH2": "realestate",
    "CH3": "psychology",
    "CH4": "mystery",
    "CH5": "war_history",
    "CH6": "science",
    "CH7": "history",
}

# 표시용 한국어 카테고리명
CHANNEL_CATEGORY_KO = {
    "CH1": "경제",
    "CH2": "부동산",
    "CH3": "심리",
    "CH4": "미스터리",
    "CH5": "전쟁사",
    "CH6": "과학",
    "CH7": "역사",
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
REVENUE_TARGET_PER_CHANNEL = 2_000_000   # 채널당 월 200만원
REVENUE_TARGET_TOTAL       = 14_000_000  # 7채널 합산 월 1,400만원

# 채널별 훅 방향 (step03/step06 공통 SSOT)
CHANNEL_HOOK_DIRECTION = {
    "CH1": "경제적 손실 공포 + 기회 제시",
    "CH2": "부동산 손실 위험 + 기회 포착 방법",
    "CH3": "행동 패턴 충격 사실 + 변화 약속",
    "CH4": "미스터리 서스펜스 + 미해결 의문 제기",
    "CH5": "충격적 전황 + 숨겨진 역사적 사실 제시",
    "CH6": "과학적 충격 사실 + 원리 해설 약속",
    "CH7": "숨겨진 역사적 진실 + 교훈 제시",
}
