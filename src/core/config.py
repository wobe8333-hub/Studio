from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

KAS_ROOT = Path(os.getenv(
    "KAS_ROOT",
    r"C:\Users\조찬우\Desktop\AI_Animation_Stuidio",
))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LOG_LEVEL = os.getenv("KAS_LOG_LEVEL", "INFO")
MANIM_QUALITY = os.getenv("MANIM_QUALITY", "l")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
GTTS_LANG = os.getenv("GTTS_LANG", "ko")

DATA_DIR = KAS_ROOT / "data"
GLOBAL_DIR = DATA_DIR / "global"
CHANNELS_DIR = DATA_DIR / "channels"
KNOWLEDGE_DIR = DATA_DIR / "knowledge_store"
RUNS_DIR = KAS_ROOT / "runs"
CREDENTIALS_DIR = KAS_ROOT / "credentials"
BGM_DIR = KAS_ROOT / "bgm"
LOGS_DIR = KAS_ROOT / "logs"

QUOTA_DIR = GLOBAL_DIR / "quota"
CACHE_DIR = GLOBAL_DIR / "cache"
MEMORY_DIR = GLOBAL_DIR / "memory_store"
PILOT_DIR = GLOBAL_DIR / "manim_pilot"
PLAN_DIR = GLOBAL_DIR / "monthly_plan"
COST_DIR = GLOBAL_DIR / "cost"
REVENUE_DIR = GLOBAL_DIR / "revenue"
RISK_DIR = GLOBAL_DIR / "risk"
SUSTAIN_DIR = GLOBAL_DIR / "sustainability"

CHANNEL_IDS = {
    "CH1": os.getenv("CH1_CHANNEL_ID", ""),
    "CH2": os.getenv("CH2_CHANNEL_ID", ""),
    "CH3": os.getenv("CH3_CHANNEL_ID", ""),
    "CH4": os.getenv("CH4_CHANNEL_ID", ""),
    "CH5": os.getenv("CH5_CHANNEL_ID", ""),
}

CHANNEL_CATEGORIES = {
    "CH1": "경제_재테크",
    "CH2": "건강_의학",
    "CH3": "심리_행동",
    "CH4": "부동산_경매",
    "CH5": "AI_테크",
}

CHANNEL_RPM_PROXY = {
    "CH1": 7000,
    "CH2": 5500,
    "CH3": 4000,
    "CH4": 6000,
    "CH5": 4500,
}

CHANNEL_RPM_INITIAL = {
    "CH1": 3500,
    "CH2": 2750,
    "CH3": 2000,
    "CH4": 3000,
    "CH5": 2250,
}

CHANNEL_MONTHLY_TARGET = {
    "CH1": 8,
    "CH2": 10,
    "CH3": 10,
    "CH4": 10,
    "CH5": 10,
}

CHANNEL_LAUNCH_PHASE = {
    "CH1": 1,
    "CH2": 1,
    "CH3": 2,
    "CH4": 2,
    "CH5": 3,
}

REVENUE_TARGET_PER_CHANNEL = 1_500_000
REVENUE_TARGET_TOTAL = 7_500_000

GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash")

