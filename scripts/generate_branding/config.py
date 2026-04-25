# scripts/generate_branding/config.py
"""7채널 브랜딩 메타데이터 SSOT"""
from pathlib import Path

KAS_ROOT = Path(__file__).parent.parent.parent
CHANNELS_DIR = KAS_ROOT / "assets" / "channels"
BRANDING_REF_DIR = KAS_ROOT / "essential_branding"

# CH1 퀄리티 강화 상수 (Imagen Best-of-N + 2K 파이프라인)
CANONICAL_BG_CREAM = "#FFFFFF"   # CH1 캔버스 기준 흰색 배경
BEST_OF_N = 3                     # Imagen variant 생성 수 (Best-of-3)
MAX_REPROMPT_ROUNDS = 3           # 프롬프트 반복 개선 최대 라운드 수

# ─── 원이(₩) 캐릭터 프롬프트 기본 텍스트 ────────────────────────────────────
_WONEE_BASE = (
    "kawaii human doodle mascot in flat 2D hand-drawn illustration style, thin black (#333333) outline 2px: "
    "STRUCTURE — large perfectly round circle head; short visible neck; "
    "rectangular-ish torso body with rounded corners and clear shoulder line "
    "(body is slightly wider than head at shoulder, like wearing a simple white jacket); "
    "two arms extending from shoulders — upper arm and forearm with small rounded hand and index finger detail; "
    "two short legs with small simple rounded feet at the bottom. "
    "FACE on the round head — two small round black dot eyes with white highlight, "
    "wide open upward-curved smile (happy expression), "
    "soft golden blush circles on both cheeks. "
    "CROWN — gold (#F4C420) crown sitting on top of the round head, "
    "three rounded bumps on top edge, small lowercase letter 'w' written in dark on the front face of the crown. "
    "Pure white #FFFFFF fill for head and body, pure white #FFFFFF background. "
    "Flat coloring, zero shading, zero gradients, zero 3D effects. "
    "CRITICAL: NO other text, NO numbers, NO labels anywhere except the 'w' on the crown."
)

CHANNELS = {
    "CH1": {
        "name": "머니그래픽", "domain": "경제",
        "main_color": "#F4C420",
        "secondary_color": "#333333",
        "accent_red": "#DC2626",
        "accent_green": "#16A34A",
        "bg_color": "#FFFFFF",
        "sub_colors": ["#DC2626", "#16A34A", "#333333"],
        "stroke_color": "#333333",
        "characters": ["default", "explain", "surprised", "happy", "sad",
                       "think", "victory", "warn", "sit", "run"],
        "character_prompts": {
            "default": _WONEE_BASE + (
                ", neutral standing pose: body centered, arms hanging naturally at sides, "
                "gentle content closed smile, looking directly forward"
            ),
            "explain": _WONEE_BASE + (
                ", right arm raised and index finger pointing forward/upward confidently, "
                "left arm at side, mouth slightly open in explaining expression, "
                "eyes wide and attentive"
            ),
            "surprised": _WONEE_BASE + (
                ", both arms spread wide to sides in shock, "
                "mouth open in large O shape, eyes stretched wide, "
                "small exclamation lines radiating outward around head"
            ),
            "happy": _WONEE_BASE + (
                ", jumping upward, both arms raised above head forming a V shape, "
                "big wide arc smile, two small 4-pointed sparkle stars floating nearby"
            ),
            "sad": _WONEE_BASE + (
                ", body slightly drooped forward, both arms hanging down limp, "
                "downward curved sad mouth frown, single small teardrop beside one eye"
            ),
            "think": _WONEE_BASE + (
                ", body tilted slightly to one side, one arm raised with index finger "
                "touching cheek or chin, eyes looking upward thoughtfully, "
                "three small thought ellipsis dots nearby"
            ),
            "victory": _WONEE_BASE + (
                ", one arm raised with thumb pointing up (thumbs-up gesture), "
                "one eye in a playful wink, confident wide grin"
            ),
            "warn": _WONEE_BASE + (
                ", both arms stretched forward toward viewer with palms facing outward "
                "in a stop/warning gesture, eyebrows furrowed downward, "
                "firm closed straight-line mouth expression"
            ),
            "sit": _WONEE_BASE + (
                ", seated cross-legged on the ground, arms resting relaxed on knees, "
                "calm neutral expression with gentle small smile"
            ),
            "run": _WONEE_BASE + (
                ", sideways profile view, body leaning forward in full sprint, "
                "arms pumping alternating front and back, legs bent in running motion, "
                "three short horizontal speed lines behind the body"
            ),
        },
        "icons": ["money", "coin", "stock_up", "stock_down", "bank", "interest",
                  "exchange", "piggy", "card", "wallet", "calculator",
                  "graph_up", "graph_down", "dollar", "won", "tax",
                  "inflation", "recession", "growth", "bond"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH2": {
        "name": "가설낙서", "domain": "과학",
        "main_color": "#00E5FF", "bg_color": "#1A1A2E",
        "sub_colors": ["#00B8D4", "#FFFFFF", "#1A1A2E"],
        "stroke_color": "#00E5FF",
        "characters": ["curious", "explain", "research", "serious", "data"],
        "character_prompts": {
            "curious": "cute doodle style scientist character, wearing lab coat, curious expression, magnifying glass, neon cyan color scheme, dark background, simple outlines, Korean science YouTube",
            "explain": "cute doodle style scientist character, wearing lab coat, explaining with chalkboard, neon cyan color scheme, dark background, Korean science YouTube",
            "research": "cute doodle style scientist character, looking through microscope, focused expression, neon cyan color scheme, dark background, Korean science YouTube",
            "serious": "cute doodle style scientist character, serious thinking expression, holding formula paper, neon cyan color scheme, dark background, Korean science YouTube",
            "data": "cute doodle style scientist character, analyzing data on screen, excited expression, neon cyan color scheme, dark background, Korean science YouTube",
        },
        "icons": ["flask","microscope","atom","dna","telescope","rocket",
                  "lightbulb","magnet","circuit","graph","beaker","planet",
                  "formula","lab_coat","notebook","fire","water","wind",
                  "electricity","virus"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH3": {
        "name": "홈팔레트", "domain": "부동산",
        "main_color": "#E67E22", "bg_color": "#FFFFFF",
        "sub_colors": ["#3498DB", "#2ECC71", "#F1C40F"],
        "stroke_color": "#2C3E50",
        "characters": ["explain", "buy", "invest", "contract", "profit", "dream"],
        "character_prompts": {
            "explain": "cute doodle style character holding house model, explaining real estate, Korean YouTube, white background, orange color scheme, simple outlines",
            "buy": "cute doodle style character shaking hands in front of house, buying/selling pose, Korean YouTube, white background, orange color scheme",
            "invest": "cute doodle style character with rising graph and house, investment pose, Korean YouTube, white background, orange color scheme",
            "contract": "cute doodle style character signing contract document, serious expression, Korean YouTube, white background, orange color scheme",
            "profit": "cute doodle style character celebrating with money and house, profit expression, Korean YouTube, white background, orange color scheme",
            "dream": "cute doodle style character dreaming of perfect house, starry eyes, Korean YouTube, white background, orange color scheme",
        },
        "icons": ["house","apartment","building","key","contract","loan","interest",
                  "calculator","chart_up","chart_down","location_pin","map",
                  "wallet","handshake","crown","door","window","garden","elevator","bus"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH4": {
        "name": "오묘한심리", "domain": "심리",
        "main_color": "#9B59B6", "bg_color": "#FFFFFF",
        "sub_colors": ["#2C3E50", "#BDC3C7", "#FFFFFF"],
        "stroke_color": "#2C3E50",
        "characters": ["explore", "explain", "anxiety", "stress", "growth"],
        "character_prompts": {
            "explore": "cute doodle style character with brain symbol, exploring psychology theories, purple color scheme, white background, Korean psychology YouTube, simple outlines",
            "explain": "cute doodle style character with thought bubble, explaining mind concepts, purple color scheme, white background, Korean psychology YouTube",
            "anxiety": "cute doodle style character showing anxiety emotion, sweat drops, worried expression, purple color scheme, white background, Korean psychology YouTube",
            "stress": "cute doodle style character managing stress, calming expression, purple color scheme, white background, Korean psychology YouTube",
            "growth": "cute doodle style character with upward arrow, self-growth pose, confident expression, purple color scheme, white background, Korean psychology YouTube",
        },
        "icons": ["brain","heart","mirror","eye","thought_bubble","stress_cloud",
                  "growth_arrow","book","couch","clock","spiral","question",
                  "star","shield","hand_holding","meditation","journal",
                  "door_open","balance","mask"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH5": {
        "name": "검은물음표", "domain": "미스터리",
        "main_color": "#1C2833", "bg_color": "#F0F0F0",
        "sub_colors": ["#2E4057", "#AAAAAA", "#FFFFFF"],
        "stroke_color": "#1C2833",
        "characters": ["curious", "explain", "shocked", "think", "investigate", "win"],
        "character_prompts": {
            "curious": "cute doodle style mystery character with question mark, curious suspicious expression, dark color scheme, white background, Korean mystery YouTube, simple outlines",
            "explain": "cute doodle style mystery character explaining with magnifying glass, dark color scheme, white background, Korean mystery YouTube",
            "shocked": "cute doodle style mystery character with shocked expression, eyes wide open, dark color scheme, white background, Korean mystery YouTube",
            "think": "cute doodle style mystery character deep in thought, dark questioning expression, dark color scheme, white background, Korean mystery YouTube",
            "investigate": "cute doodle style mystery character searching for clues, detective pose, dark color scheme, white background, Korean mystery YouTube",
            "win": "cute doodle style mystery character celebrating solving mystery, triumphant expression, dark color scheme, white background, Korean mystery YouTube",
        },
        "icons": ["question_mark","eye_dark","magnifier","key_old","lock","shadow",
                  "ghost","skull","map_torn","compass","candle","raven","clue",
                  "fingerprint","door_mystery","fog","ancient_book","crystal_ball",
                  "spider","moon"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH6": {
        "name": "오래된두루마리", "domain": "역사",
        "main_color": "#A0522D", "bg_color": "#F5F0E0",
        "sub_colors": ["#C4A35A", "#6B4C11", "#F5F0E0"],
        "stroke_color": "#6B4C11",
        "characters": ["explore", "explain", "scholar", "travel"],
        "character_prompts": {
            "explore": "cute doodle style historian character with scroll, exploring ancient history, parchment brown color scheme, aged paper background, Korean history YouTube, simple outlines",
            "explain": "cute doodle style historian character explaining with open scroll, parchment brown color scheme, aged paper background, Korean history YouTube",
            "scholar": "cute doodle style historian character as scholar with quill pen, parchment brown color scheme, aged paper background, Korean history YouTube",
            "travel": "cute doodle style historian character on historical journey with map, parchment brown color scheme, aged paper background, Korean history YouTube",
        },
        "icons": ["scroll","map_old","sword","crown","castle","ship","compass_old",
                  "book_aged","hourglass","coin_old","portrait","flag","temple",
                  "arch","quill","shield_crest","lantern","cart","gate","column"],
        "intro_duration": 3, "outro_duration": 10,
    },
    "CH7": {
        "name": "워메이징", "domain": "전쟁사",
        "main_color": "#C0392B", "bg_color": "#FFFFFF",
        "sub_colors": ["#2C3E50", "#7F8C8D", "#F1C40F"],
        "stroke_color": "#2C3E50",
        "characters": ["victory", "strategy", "battle", "general", "soldier"],
        "character_prompts": {
            "victory": "cute doodle style military general character, victory pose with raised fist, red military color scheme, white background, Korean war history YouTube, simple outlines",
            "strategy": "cute doodle style military general character, studying battle map, strategic thinking expression, red military color scheme, white background, Korean war history YouTube",
            "battle": "cute doodle style military general character, charging battle pose, determined expression, red military color scheme, white background, Korean war history YouTube",
            "general": "cute doodle style military general character, commanding pose, medal on chest, red military color scheme, white background, Korean war history YouTube",
            "soldier": "cute doodle style military soldier character, saluting pose, red military color scheme, white background, Korean war history YouTube",
        },
        "icons": ["sword_crossed","shield","tank","plane","ship_war","flag_military",
                  "medal","map_battle","cannon","helmet","rifle","bomb",
                  "general_star","binoculars","radio","trench","grenade",
                  "compass","dog_tag","victory"],
        "intro_duration": 3, "outro_duration": 10,
    },
}

SUBDIRS = ["logo", "characters", "intro", "outro", "icons", "templates", "extras", "transitions"]

# ── src/adapters/character_generator.py 상수 (스크립트 내 쉬운 import용) ──────

# 두들 캐릭터 스타일 고정 프리픽스 — 바디/얼굴 불변, 의상만 변경
STYLE_PREFIX = (
    "Keep the EXACT same body as shown in the reference image: "
    "3.5-head-tall doodle character, completely bald round head, same round face with "
    "black dot eyes, tiny smile, pink blush cheeks, same body proportions and medium-length legs. "
    "Pure white background. Flat 2D cartoon doodle style. Clean 2px black outline. "
    "Flat colors only, no gradients, no shadows. Full body visible head to feet. "
    "ONLY change the outfit, accessories, and expression as described. "
)

# 채널별 의상 컬러 가이드
CHANNEL_COLOR_GUIDE: dict[str, str] = {
    "CH1": "Prefer gold (#E8A44C) and navy (#1A237E) tones in the costume design.",
    "CH2": "Prefer teal (#00CED1) and white tones in the costume design.",
    "CH3": "Prefer orange (#FF8C42) and sage green (#52B788) tones in the costume design.",
    "CH4": "Prefer lavender (#9B59B6) and soft coral tones in the costume design.",
    "CH5": "Prefer dark navy (#1F3A5F) and purple tones in the costume design.",
    "CH6": "Prefer golden brown (#8B6914) and burgundy tones in the costume design.",
    "CH7": "Prefer forest green (#2E5B3C) and warm amber tones in the costume design.",
}

# 채널별 마스코트 의상 설명
MASCOT_COSTUME: dict[str, str] = {
    "CH1": "smart business suit with a briefcase, tie, clean formal look",
    "CH2": "white lab coat with safety goggles, test tube in hand",
    "CH3": "casual builder outfit with tool belt, hard hat",
    "CH4": "soft cardigan with round glasses, holding a notebook",
    "CH5": "dark detective trench coat with magnifying glass, mysterious look",
    "CH6": "classical scholar robe with a quill pen and scroll",
    "CH7": "historical military field uniform with a small flag",
}
