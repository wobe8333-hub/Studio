# scripts/generate_branding/config.py
"""7채널 브랜딩 메타데이터 SSOT"""
from pathlib import Path

KAS_ROOT = Path(__file__).parent.parent.parent
CHANNELS_DIR = KAS_ROOT / "assets" / "channels"
BRANDING_REF_DIR = KAS_ROOT / "essential_branding"

CHANNELS = {
    "CH1": {
        "name": "머니그래픽", "domain": "경제",
        "main_color": "#2ECC71", "bg_color": "#FFFFFF",
        "sub_colors": ["#3498DB", "#F1C40F", "#2C3E50"],
        "stroke_color": "#2C3E50",
        "characters": ["explain", "rich", "money", "lucky"],
        "character_prompts": {
            "explain": "cute doodle style character with crown, pointing finger explaining, Korean YouTube economics channel, white background, simple black outlines, cheerful expression",
            "rich": "cute doodle style character with crown, holding money bags, wealthy pose, Korean YouTube economics channel, white background, simple black outlines",
            "money": "cute doodle style character with crown, surrounded by flying money bills, excited expression, Korean YouTube economics channel, white background",
            "lucky": "cute doodle style character with crown, shocked happy expression, holding lottery ticket, Korean YouTube economics channel, white background",
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

# ── CH1 에센셜 브랜딩 레퍼런스 Crop 설정 (essential_branding/CH1.png, 1379×752px) ──────
CH1_CROP_REGIONS: dict[str, tuple[int, int, int, int]] = {
    # 섹션 1: 비주얼 아이덴티티 (좌측)
    "logo":               (22,  75, 238, 295),   # 원형 프레임 + 왕관 캐릭터 + 머니그래픽 텍스트
    "character_explain":  (245, 65, 365, 195),   # 설명하는 (Explaining)
    "character_rich":     (360, 65, 478, 195),   # 부자 (Rich Full of Coins)
    "character_money":    (245, 200, 365, 360),  # 부자 돈많음 (Rich More Money)
    "character_lucky":    (360, 200, 478, 360),  # 복권당첨 (Lottery Winner)
    # 섹션 2: 영상 제작 에센셜 — 인트로 분해 요소
    "intro_frame":        (490,  50, 660, 210),  # 인트로(3s) 박스 전체 (원형 프레임 포함)
    "intro_text":         (505, 140, 650, 205),  # 머니그래픽 텍스트 부분
    "intro_character":    (510,  58, 645, 150),  # 인트로 박스 내 캐릭터
    "intro_sparkle":      (490,  50, 545, 105),  # 반짝이 요소
    # 섹션 2: 영상 제작 에센셜 — 아웃트로 분해 요소
    "outro_background":   (665,  50, 880, 210),  # 아웃트로(10s) 박스 전체 배경
    "outro_bill":         (675,  55, 820, 140),  # 돈다발 요소
    "outro_character":    (790,  60, 872, 205),  # 아웃트로 캐릭터
    "outro_cta":          (665, 155, 880, 205),  # 구독좋아요 CTA 영역
    # 섹션 2: 영상 스타일 예시 썸네일 3종
    "thumbnail_sample_1": (885,  50, 1010, 210), # 코인 차트의 마법!
    "thumbnail_sample_2": (1015, 50, 1145, 210), # 금리 인상, 내 지갑은?
    "thumbnail_sample_3": (1150, 50, 1290, 210), # 주식 초보 이것만 알아!
    # 섹션 2: 자막 Bar 3종
    "subtitle_bar_key":    (490, 215, 870, 268), # Bar 1 Key 강조 (노란 하이라이트)
    "subtitle_bar_dialog": (490, 270, 870, 328), # Bar 2 대사/해설
    "subtitle_bar_info":   (490, 330, 870, 388), # Bar 3 정보 강조
    # 섹션 2: 장면 전환 3종
    "transition_paper":   (880, 215, 1010, 390), # 종이 넘기기
    "transition_ink":     (1015, 215, 1145, 390), # 잉크 번지기
    "transition_zoom":    (1150, 215, 1290, 390), # 확대/축소
}

# 후처리 정책: bg_remove=True → PIL 흰색 배경 알파 제거, target/longer_side → LANCZOS 업스케일
CH1_POST_POLICY: dict[str, dict] = {
    "logo":               {"bg_remove": True,  "target": (1024, 1024)},
    "character_explain":  {"bg_remove": True,  "target": (1024, 1024)},
    "character_rich":     {"bg_remove": True,  "target": (1024, 1024)},
    "character_money":    {"bg_remove": True,  "target": (1024, 1024)},
    "character_lucky":    {"bg_remove": True,  "target": (1024, 1024)},
    "intro_frame":        {"bg_remove": True,  "longer_side": 512},
    "intro_text":         {"bg_remove": True,  "longer_side": 512},
    "intro_character":    {"bg_remove": True,  "longer_side": 512},
    "intro_sparkle":      {"bg_remove": True,  "longer_side": 256},
    "outro_background":   {"bg_remove": False, "target": (1280, 720)},
    "outro_bill":         {"bg_remove": True,  "longer_side": 256},
    "outro_character":    {"bg_remove": True,  "longer_side": 512},
    "outro_cta":          {"bg_remove": True,  "longer_side": 512},
    "thumbnail_sample_1": {"bg_remove": False, "target": (1920, 1080)},
    "thumbnail_sample_2": {"bg_remove": False, "target": (1920, 1080)},
    "thumbnail_sample_3": {"bg_remove": False, "target": (1920, 1080)},
    "subtitle_bar_key":   {"bg_remove": False, "target": (1280, 120)},
    "subtitle_bar_dialog":{"bg_remove": False, "target": (1280, 120)},
    "subtitle_bar_info":  {"bg_remove": False, "target": (1280, 120)},
    "transition_paper":   {"bg_remove": False, "target": (1920, 1080)},
    "transition_ink":     {"bg_remove": False, "target": (1920, 1080)},
    "transition_zoom":    {"bg_remove": False, "target": (1920, 1080)},
}
