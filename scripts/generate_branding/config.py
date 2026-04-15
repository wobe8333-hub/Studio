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

CHANNELS = {
    "CH1": {
        "name": "머니그래픽", "domain": "경제",
        "main_color": "#2ECC71", "bg_color": "#FFFDF5",
        "sub_colors": ["#3498DB", "#F1C40F", "#2C3E50"],
        "stroke_color": "#2C3E50",
        "characters": ["explain", "rich", "money", "lucky"],
        # 공통 스타일 앵커: 4종 모두 동일 캐릭터 기반으로 일관성 확보
        # round white head with black outline · gold crown W · simple stick body · white dot eyes
        "character_prompts": {
            "explain": (
                "cute doodle style character: round white head with black outline, gold crown with ₩ Korean Won symbol on the front, "
                "simple stick body with arms, big black dot eyes, cute small smile, "
                "pointing finger explaining pose, cheerful confident expression, "
                "Korean YouTube economics channel '머니그래픽', "
                "pure white #FFFFFF background, simple black outlines, "
                "isolated character, no text, no labels, "
                "hand-drawn Korean YouTube doodle reference style, "
                "2K resolution, ultra-detailed, hand-drawn line quality, clean edges, print-quality"
            ),
            "rich": (
                "cute doodle style character: round white head with black outline, gold crown with ₩ Korean Won symbol on the front, "
                "simple stick body with arms, big black dot eyes, huge victorious grin, "
                "dynamic leaping jump pose with one fist punching the air, "
                "money bags flying and spinning around the body, tilted diagonal body angle, "
                "speed lines behind for motion effect, "
                "Korean YouTube economics channel '머니그래픽', "
                "pure white #FFFFFF background, simple black outlines, "
                "isolated character, no text, no labels, "
                "hand-drawn Korean YouTube doodle reference style, "
                "2K resolution, ultra-detailed, hand-drawn line quality, clean edges, print-quality"
            ),
            "money": (
                "cute doodle style character: round white head with black outline, gold crown with ₩ Korean Won symbol on the front, "
                "simple stick body with arms, big black dot eyes, wild open-mouth excited expression, "
                "sprinting forward at full speed with both arms stretched back, "
                "a massive explosion of money bills and coins bursting out behind like a rocket, "
                "body leaning far forward in fast run, extreme energy, "
                "Korean YouTube economics channel '머니그래픽', "
                "pure white #FFFFFF background, simple black outlines, "
                "isolated character, no text, no labels, "
                "hand-drawn Korean YouTube doodle reference style, "
                "2K resolution, ultra-detailed, hand-drawn line quality, clean edges, print-quality"
            ),
            "lucky": (
                "cute doodle style character: round white head with black outline, gold crown with ₩ Korean Won symbol on the front, "
                "simple stick body with arms, big black dot eyes, shocked jaw-drop expression with sparkle eyes, "
                "jumping high in the air with both legs kicked up, lottery ticket raised triumphantly in one hand, "
                "confetti and huge burst stars exploding all around, body twisted mid-air in celebration, "
                "Korean YouTube economics channel '머니그래픽', "
                "pure white #FFFFFF background, simple black outlines, "
                "isolated character, no text, no labels, "
                "hand-drawn Korean YouTube doodle reference style, "
                "2K resolution, ultra-detailed, hand-drawn line quality, clean edges, print-quality"
            ),
        },
        "icons": ["money","coin","stock_up","stock_down","bank","interest",
                  "exchange","piggy","card","wallet","calculator",
                  "graph_up","graph_down","dollar","won","tax",
                  "inflation","recession","growth","bond"],
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

SUBDIRS = ["logo", "characters", "intro", "outro", "icons", "templates", "extras"]
