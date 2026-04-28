"""STEP 10 — Gemini 멀티레퍼런스 에피소드 일러스트 생성.

각 영상마다 마스코트가 토픽 핵심 장면에 등장하는
풀스크린 두들 일러스트를 Gemini Image로 생성한다.
thumbnail_generator.py 가 이 모듈을 호출해 L1 베이스 레이어로 사용.

구성 유형 6가지 (60장 사물궁이 실측 분석 기반):
  TYPE5 다중캐릭터   32%: 마스코트 2명+, 드라마/대화/VS
  TYPE2 캐릭터반응형 23%: 마스코트 55~65%, 주제별 코스튬
  TYPE1 환경몰입형   22%: 마스코트 30~40%, 그려진 환경 필수
  TYPE4 그래픽오버레이17%: 마스코트 20~25%, 차트/화살표/UI
  TYPE3 규모대비형   10%: 마스코트 10~20%, 오브젝트가 60~70%
  TYPE6 개념변형형    5%: 개념이 시각, 마스코트 통합

⚠️ 배경 단색 금지: 60장 실측에서 flat solid color는 단 1장도 없음.
   모든 배경은 그려진 환경/대기 그라디언트/두 색 분할 중 하나.
"""
import json
import os
import random
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

from src.core.ssot import read_json, write_json  # noqa: E402

_ROOT = Path(os.environ["KAS_ROOT"]) if os.environ.get("KAS_ROOT") else Path(__file__).resolve().parents[2]
_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

# ── 7채널 마스코트 페르소나 (SSOT — track_a_narrative.py 에서 임포트해 사용) ────
# category: "info"(정보형) | "stimulating"(자극형) | "stimulating_strong"(자극형 강)
# expressions: CTR 데이터 기반 표정 우선순위 (놀람>충격>호기심 순)
CHANNEL_MASCOT_PERSONA: dict[str, dict] = {
    "CH1": {
        "persona": (
            "원이₩ — round bald kawaii doodle character with gold crown "
            "bearing lowercase 'w', wearing business suit and holding a briefcase"
        ),
        "category": "info",
        "mascot_ratio": "60%",
        "expressions": ["surprised", "curious", "thoughtful", "amazed", "smiling"],
    },
    "CH2": {
        "persona": (
            "가설낙서 scientist — neon-cyan lab coat doodle character "
            "with safety goggles and glowing test tube"
        ),
        "category": "stimulating",
        "mascot_ratio": "65%",
        "expressions": ["shocked", "wide-eyed", "amazed", "alarmed", "curious"],
    },
    "CH3": {
        "persona": (
            "홈팔레트 builder — orange tool-belt doodle character "
            "with hard hat, holding blueprints and ruler"
        ),
        "category": "info",
        "mascot_ratio": "60%",
        "expressions": ["surprised", "curious", "thoughtful", "amazed", "smiling"],
    },
    "CH4": {
        "persona": (
            "오묘한심리 — lavender cardigan doodle character "
            "with round glasses, holding an open notebook"
        ),
        "category": "stimulating",
        "mascot_ratio": "65%",
        "expressions": ["shocked", "worried", "wide-eyed", "curious", "mysterious"],
    },
    "CH5": {
        "persona": (
            "검은물음표 detective — dark trench coat doodle character "
            "with magnifying glass, mysterious suspicious expression"
        ),
        "category": "stimulating_strong",
        "mascot_ratio": "60%",
        "expressions": ["shocked", "worried", "alarmed", "wide-eyed", "mysterious"],
    },
    "CH6": {
        "persona": (
            "오래된두루마리 scholar — brown robe doodle character "
            "with quill pen and ancient unrolled scroll"
        ),
        "category": "info",
        "mascot_ratio": "60%",
        "expressions": ["surprised", "curious", "thoughtful", "amazed", "smiling"],
    },
    "CH7": {
        "persona": (
            "워메이징 general — red military field uniform doodle character "
            "with small flag and medal on chest"
        ),
        "category": "stimulating_strong",
        "mascot_ratio": "60%",
        "expressions": ["shocked", "alarmed", "worried", "determined", "wide-eyed"],
    },
}

# ── 채널별 메인·액센트 컬러 ────────────────────────────────────────────────────
CHANNEL_COLORS: dict[str, tuple[str, str]] = {
    # (signature_color, point_color) — 파스텔 톤 (HSV S=0.30~0.50, V=0.80~0.92)
    # 낮은 채도로 제목 가독성 확보. 색 정체성은 유지.
    # signature: 배경·의상·소품 dominant 사용
    # point: 모자·아이콘 등 1~2개 focal 요소에만 sparingly
    "CH1": ("#FFD97A", "#FF9090"),   # 경제: 페일 골드 + 살몬 레드
    "CH2": ("#7BE0F0", "#7BAAE0"),   # 과학: 소프트 시안 + 소프트 블루
    "CH3": ("#8FCC8F", "#FFC890"),   # 부동산: 세이지 그린 + 페일 피치 (S=0.44)
    "CH4": ("#C9A0DC", "#F9A8C0"),   # 심리: 라벤더 퍼플 + 소프트 핑크
    "CH5": ("#B080CC", "#F5B880"),   # 미스터리: 미디엄 라벤더 + 페일 살몬 오렌지 (S=0.47)
    "CH6": ("#D4A870", "#F0D080"),   # 역사: 웜 샌디 탄 + 페일 앰버
    "CH7": ("#E88888", "#8898CC"),   # 전쟁사: 로즈 레드 + 페리윙클 블루
}

# ── 60장 실측 기반 6가지 구성 유형 ────────────────────────────────────────────
_COMPOSITION_TYPES: dict[str, dict] = {
    "TYPE1": {
        "name": "환경몰입형",
        "mascot_size": "30-40% of frame, integrated into the drawn scene",
        "bg_style": "fully illustrated drawn environment — buildings, nature, indoor room, NOT gradient or solid",  # noqa: E501
        "hook": "viewer is pulled into a vivid doodle world — scene tells the story",
    },
    "TYPE2": {
        "name": "캐릭터반응형",
        "mascot_size": "35-45% of frame height, center or center-right — character dominates visually",
        "bg_style": "dark atmospheric gradient (deep green/navy/amber) OR topic-context props filling background — NEVER flat solid color",  # noqa: E501
        "hook": "oversized mascot reaction + topic-relevant costume creates immediate curiosity",
    },
    "TYPE3": {
        "name": "규모대비형",
        "mascot_size": "10-20% of frame — intentionally TINY for scale contrast",
        "bg_style": "illustrated environment OR photorealistic dramatic backdrop — dominant object fills 60-70%",  # noqa: E501
        "hook": "extreme size asymmetry shocks viewer — tiny mascot vs enormous subject",
    },
    "TYPE4": {
        "name": "그래픽오버레이형",
        "mascot_size": "20-25% of frame, pointing at or reacting to graphics",
        "bg_style": "background FILLED with UI elements, arrows, charts, price boards, data visuals",  # noqa: E501
        "hook": "dense information with mascot as guide — info overload drives curiosity",
    },
    "TYPE5": {
        "name": "다중캐릭터드라마형",
        "mascot_size": "25-40% each — TWO or THREE mascot instances interact",
        "bg_style": "illustrated environment OR two-tone split background (VS format) — NOT solid single color",  # noqa: E501
        "hook": "multi-character drama with villain/victim/hero roles — story implied in one image",
    },
    "TYPE6": {
        "name": "개념변형형",
        "mascot_size": "10-15% or fully integrated as part of the concept visual",
        "bg_style": "concept/object visual dominates 60-70% — mascot observes or merges with it",
        "hook": "abstract concept made viscerally concrete — viewer must click to understand",
    },
}

# ── 채널 카테고리별 권장 구성 유형 (60장 실측 빈도 기반) ────────────────────────
_CATEGORY_PREFERRED_TYPES: dict[str, list[str]] = {
    "info": ["TYPE2", "TYPE5", "TYPE1"],          # 정보형: 반응>드라마>환경
    "stimulating": ["TYPE5", "TYPE2", "TYPE1"],   # 자극형: 드라마>반응>환경
    "stimulating_strong": ["TYPE5", "TYPE1", "TYPE3"],  # 자극형강: 드라마>환경>규모대비
}

# ── 비용 추적 경로 ──────────────────────────────────────────────────────────────
_COST_FILE = _ROOT / "data" / "finance" / "api_costs_thumbnails.json"

# ── 비용 단가 추정 (USD/call) ────────────────────────────────────────────────────
_COST_PER_CALL = 0.04

# ── 패러디 뱅크 ────────────────────────────────────────────────────────────────
_PARODY_BANK_FILE = _ROOT / "data" / "thumbnails" / "parody_bank.json"
_parody_bank_cache: list[dict] | None = None  # 모듈 레벨 캐시 (1회 로드)
_parody_refresh_done: set[str] = set()  # 이번 프로세스 세션에서 refresh 시도한 채널


def _load_parody_bank() -> list[dict]:
    """패러디 뱅크 JSON 로드. 파일 없으면 빈 리스트. 모듈 레벨 캐시 사용.

    _ROOT를 동적으로 참조하므로 런타임 패치(_ROOT 변경)에도 올바르게 동작한다.
    """
    global _parody_bank_cache
    if _parody_bank_cache is not None:
        return _parody_bank_cache
    path = _ROOT / "data" / "thumbnails" / "parody_bank.json"
    try:
        data = read_json(path)
        _parody_bank_cache = data.get("entries", [])
    except Exception:
        _parody_bank_cache = []
    return _parody_bank_cache


def _get_channel_parodies(channel: str) -> list[dict]:
    """채널에 해당하는 패러디 항목 반환 (channels=null 이면 범용)."""
    entries = _load_parody_bank()
    return [
        e for e in entries
        if not e.get("channels") or channel in (e.get("channels") or [])
    ]


def _parse_parody_tag(scene_desc: str) -> tuple[str, str | None]:
    """scene_desc에서 TYPE 코드와 패러디 ID를 분리.

    형식: 'TYPE5|PARODY=entry_id: description' 또는 'TYPE2: description'
    반환: (type_code, parody_id_or_None)
    """
    match = re.match(r"^(TYPE\d)\|PARODY=([^:]+):", scene_desc, re.IGNORECASE)
    if match:
        return match.group(1).upper(), match.group(2).strip()
    return _extract_scene_type(scene_desc), None


def _build_parody_prompt_section(entries: list[dict], force: bool = False) -> str:
    """패러디 옵션을 Gemini 프롬프트에 주입할 텍스트 블록 생성.

    force=True 이면 "반드시 사용" 모드 — 가장 잘 맞는 항목 1개를 의무 선택.
    """
    if not entries:
        return ""
    lines = []
    for e in entries[:12]:  # force 모드에선 더 많은 옵션 제공
        kw = ", ".join(e.get("keywords", [])[:5])
        lines.append(
            f"  [{e['id']}] {e['name']} (from: {e['source']}): {e['scene'][:100]} "
            f"| fit-keywords: {kw}"
        )
    if force:
        return (
            "\n\n─── MANDATORY PARODY MODE ──────────────────────────────────────\n"
            "⚠️ YOU MUST USE PARODY. This is a parody-style thumbnail.\n"
            "Pick the SINGLE BEST matching parody from the list below and adapt it to the topic.\n"
            "Output format: TYPE5|PARODY={id}: [2-3 sentences adapting the iconic scene to this topic]\n"
            "The mascot replaces the original character. Keep the iconic visual elements recognizable.\n"
            "Available parodies (pick the best fit):\n"
            + "\n".join(lines)
            + "\n────────────────────────────────────────────────────────────────────"
        )
    return (
        "\n\n─── OPTIONAL PARODY MODE ───────────────────────────────────────\n"
        "Use ONLY if topic has 90%+ natural thematic match with any parody below.\n"
        "When using parody: start with 'TYPE5|PARODY={id}: [1-2 sentences adapting the iconic scene to the topic]'\n"  # noqa: E501
        "When NOT using parody: use normal 'TYPE{N}: [scene description]'\n"
        "Parody is OPTIONAL — only if it genuinely amplifies the topic's humor or drama.\n"
        "Available parodies:\n"
        + "\n".join(lines)
        + "\n────────────────────────────────────────────────────────────────────"
    )


def _should_refresh_bank() -> bool:
    """parody_bank.json last_updated 기준 30일 이상 경과 여부."""
    try:
        path = _ROOT / "data" / "thumbnails" / "parody_bank.json"
        data = read_json(path)
        updated = date.fromisoformat(data.get("last_updated", "2000-01-01"))
        return (date.today() - updated).days >= 30
    except Exception:
        return False


def discover_parodies(channel: str, count: int = 5) -> list[dict]:
    """Gemini가 새 패러디 엔트리를 자동 발굴해 parody_bank.json에 추가.

    Returns: 새로 추가된 엔트리 리스트 (중복·파싱 실패 항목 제외)
    """
    from src.core.llm_client import generate_text

    _CHANNEL_TOPICS: dict[str, str] = {
        "CH1": "경제·재테크·투자·직장생활·세금·월급",
        "CH2": "과학·우주·기술·AI·발명·자연현상",
        "CH3": "부동산·집값·전세·월세·청약·인테리어",
        "CH4": "심리학·인간관계·감정·MBTI·설득·습관",
        "CH5": "미스터리·음모론·범죄·사건·미확인",
        "CH6": "역사·고대·조선·전통·인물·문화",
        "CH7": "전쟁사·군사·전략·무기·전투",
    }
    topics = _CHANNEL_TOPICS.get(channel, "일반 지식")

    existing = _load_parody_bank()
    existing_ids = {e["id"] for e in existing}
    existing_names = ", ".join(e["name"] for e in existing[:25])

    prompt = (
        f"당신은 한국 YouTube 썸네일 기획자입니다.\n"
        f"채널 {channel} 주제({topics})에 어울리는 새 패러디 아이디어 {count}개를 발굴하세요.\n\n"
        "패러디 소스: 한국 드라마/영화/예능/밈 + 해외 유명 콘텐츠 (한국 시청자에게 친숙한 것)\n"
        f"뱅크에 이미 있음 — 중복 금지: {existing_names}\n\n"
        "각 항목은 아래 JSON 형식을 사용하세요:\n"
        '{"id":"snake_case_고유ID","name":"한국어 패러디 이름","source":"원작 출처(한국어)",'
        '"mascot_costume":"마스코트 의상(영어)","scene":"아이코닉 장면 — 마스코트 주인공(영어 120자이내)",'
        '"iconic_prop":"핵심 소품(영어)","mood":"분위기 키워드(영어)",'
        '"keywords":["한국어키워드1","키워드2"],"channels":null}\n\n'
        f'channels: null이면 전 채널 적용 / ["{channel}"]이면 이 채널 전용\n'
        "scene, mascot_costume, iconic_prop, mood 는 반드시 영어로 작성.\n"
        "반환: JSON 배열만. 설명 없음. 마크다운 코드블록 없음."
    )

    try:
        raw = generate_text(prompt).strip()
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        candidates: list = json.loads(raw)
        if not isinstance(candidates, list):
            candidates = [candidates]
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 패러디 발굴 응답 파싱 실패: {e}")
        return []

    required = {"id", "name", "source", "mascot_costume", "scene", "iconic_prop", "mood", "keywords"}
    new_entries: list[dict] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        if not required.issubset(c.keys()):
            continue
        entry_id = str(c["id"]).strip()
        if entry_id in existing_ids:
            continue
        c["id"] = entry_id
        c["_source"] = "AI-generated"
        new_entries.append(c)
        existing_ids.add(entry_id)

    if not new_entries:
        logger.info("[STEP10-ILLUST] 패러디 발굴: 추가할 신규 항목 없음 (모두 중복 또는 파싱 실패)")
        return []

    try:
        path = _ROOT / "data" / "thumbnails" / "parody_bank.json"
        bank_data = read_json(path)
        bank_data["entries"].extend(new_entries)
        bank_data["last_updated"] = date.today().isoformat()
        write_json(path, bank_data)

        global _parody_bank_cache
        _parody_bank_cache = None  # 캐시 무효화 — 다음 호출 시 갱신 데이터 로드

        ids = [e["id"] for e in new_entries]
        logger.info(f"[STEP10-ILLUST] 패러디 뱅크 자동 추가: {len(new_entries)}개 {ids}")
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 패러디 뱅크 저장 실패: {e}")
        return []

    return new_entries


def _maybe_refresh_bank(channel: str) -> None:
    """30일 이상 갱신 안 됐고 이번 세션 미시도 채널이면 자동 발굴."""
    if channel in _parody_refresh_done:
        return
    _parody_refresh_done.add(channel)
    if not _should_refresh_bank():
        return
    try:
        new_entries = discover_parodies(channel, count=5)
        if new_entries:
            logger.info(f"[STEP10-ILLUST] 패러디 뱅크 자동 갱신 완료: +{len(new_entries)}개")
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 패러디 자동 발굴 실패 (무시): {e}")


def _make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수 미설정")
    return genai.Client(api_key=api_key)


def _extract_scene_type(scene_desc: str) -> str:
    """scene_desc 첫머리 'TYPE{N}:' 접두사에서 구성 유형 추출. 없으면 TYPE2 기본."""
    for t in _COMPOSITION_TYPES:
        if scene_desc.upper().startswith(t):
            return t
    return "TYPE2"


def _generate_thumbnail_scene(channel: str, topic: str, force_parody: bool = False) -> str:
    """Gemini Text로 구성 유형 선택 + 썸네일 장면 대사 생성.

    반환 형식: "TYPE{N}: [English scene description 2~3 sentences]"
              또는 "TYPE5|PARODY={id}: [scene description]" (패러디 매칭 시)
    LLM이 6가지 유형 중 주제에 가장 적합한 TYPE를 직접 선택한다.
    """
    from src.core.llm_client import generate_text

    # 30일 이상 갱신 안 됐으면 채널당 1회 자동 발굴 (비동기 없이 블로킹 — 약 3초 추가)
    _maybe_refresh_bank(channel)

    info = CHANNEL_MASCOT_PERSONA.get(channel, {})
    category = info.get("category", "info") if isinstance(info, dict) else "info"
    main_color, _ = CHANNEL_COLORS.get(channel, ("#FFFFFF", "#000000"))
    is_dark = category == "stimulating_strong"

    preferred = _CATEGORY_PREFERRED_TYPES.get(category, ["TYPE2", "TYPE3"])

    type_options = []
    for t in preferred:
        ct = _COMPOSITION_TYPES[t]
        type_options.append(
            f"- {t} [{ct['name']}]: {ct['hook']}. "
            f"Mascot size: {ct['mascot_size']}. Background: {ct['bg_style']}."
        )
    type_guide = "\n".join(type_options)

    bg_hint = (
        f"near-black with {main_color} tint (dark dramatic)" if is_dark
        else f"{main_color} signature gradient or illustrated scene"
    )

    system = (
        "You are a Korean YouTube thumbnail art director specializing in Korean doodle cartoon YouTube style.\n"  # noqa: E501
        "Analyze the topic and select the composition type that creates maximum CTR (curiosity + visual impact).\n\n"  # noqa: E501
        f"Recommended composition types for '{category}' channel:\n{type_guide}\n\n"
        "HIGH-CTR SCENE FORMULAS — pick one:\n"
        "- COMEDY SHOCK: mascot discovers/finds a secret and reacts with MAXIMUM cartoon panic or ecstatic joy (jaw dropping off, eyes spinning, flying backwards).\n"  # noqa: E501
        "- SECRET REVEAL: mascot looks SMUG and victorious, holding THE ONE thing others don't know, while a second mascot is stunned.\n"  # noqa: E501
        "- ABSURD SCALE: a tiny mascot next to a GIANT ridiculous prop — the size contrast is the punchline.\n"  # noqa: E501
        "- BEFORE/AFTER SPLIT: TYPE5 left=suffering mascot, right=triumphant mascot in same role — the transformation is the hook.\n"  # noqa: E501
        "Korean YouTube hook formula: '내가 몰랐던 사실' + EXTREME REACTION = MAX CTR.\n"
        "The scene must make a viewer LAUGH or say 'wait WHAT?!' within 0.5 seconds.\n\n"
        "Output rules:\n"
        "- MUST start with one of: TYPE1: / TYPE2: / TYPE3: / TYPE4: / TYPE5: / TYPE6:\n"
        "- PROPS must be SPECIFIC and EXAGGERATED (e.g. 'one comically oversized gold coin taller than the mascot', 'a single glowing tax document with a giant X on it').\n"  # noqa: E501
        "- BACKGROUND: NEVER use flat solid color. Use illustrated environment, dark atmospheric gradient, or two-tone split.\n"  # noqa: E501
        f"- Dark/dramatic topics may use: near-black {bg_hint} atmospheric backdrop.\n"
        "- COSTUME: mascot should wear topic-appropriate role outfit that AMPLIFIES the comedy (e.g. tiny office worker suit, giant lab coat, oversized detective coat).\n"  # noqa: E501
        "- Output: TYPE prefix + 2~3 English sentences ONLY. No bullet points. No explanation."
    )
    # 채널별 패러디 뱅크 주입 (force_parody=True면 의무 선택)
    parody_entries = _get_channel_parodies(channel)
    if parody_entries:
        system += _build_parody_prompt_section(parody_entries, force=force_parody)
    user = f"Topic (Korean): {topic}\nChannel category: {category}\nWrite scene brief:"

    try:
        scene = generate_text(f"{system}\n\n{user}")
        scene = scene.strip()
        # TYPE prefix 없으면 기본값 삽입
        if not any(scene.upper().startswith(t) for t in _COMPOSITION_TYPES):
            scene = f"TYPE2: {scene}"
        logger.info(f"[STEP10-ILLUST] 장면 대사 ({_extract_scene_type(scene)}): {scene[:140]}")
        return scene
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 장면 대사 생성 실패 (폴백): {e}")
        return "TYPE2: Mascot character in topic-appropriate costume reacts with shocked expression. Dark atmospheric gradient background with one topic-related prop visible. Direct eye contact with camera, high-contrast exaggerated expression."  # noqa: E501


def _build_prompt(channel: str, topic: str, expression: str | None = None,
                  scene_desc: str = "") -> str:
    info = CHANNEL_MASCOT_PERSONA.get(channel, {})
    persona = info.get("persona", "cute doodle mascot character") if isinstance(info, dict) else str(info)  # noqa: E501
    category = info.get("category", "info") if isinstance(info, dict) else "info"
    expressions = (
        info.get("expressions", ["surprised", "curious"])
        if isinstance(info, dict)
        else ["surprised", "curious"]
    )

    chosen_expr = expression or random.choice(expressions)
    main_color, accent_color = CHANNEL_COLORS.get(channel, ("#FFFFFF", "#000000"))
    is_dark = category == "stimulating_strong"

    scene_type, parody_id = _parse_parody_tag(scene_desc)
    parody_entry = None
    if parody_id:
        parody_entry = next(
            (e for e in _load_parody_bank() if e["id"] == parody_id), None
        )
        if parody_entry:
            logger.info(f"[STEP10-ILLUST] 패러디 적용: {parody_entry['name']} ({parody_id})")

    # TYPE 접두사 + PARODY 태그 제거한 순수 장면 묘사
    colon_pos = scene_desc.find(":")
    if colon_pos != -1:
        scene_clean = scene_desc[colon_pos + 1:].strip()
    else:
        scene_clean = scene_desc

    if not scene_clean:
        scene_clean = (
            f"mascot character in topic-appropriate costume reacts with {chosen_expr} expression, "
            f"dark atmospheric {main_color}-tinted gradient background, one topic-related prop visible."  # noqa: E501
        )

    # 구성 유형별 마스코트 크기
    _mascot_size_str = {
        "TYPE1": "30-40% of frame height, integrated into illustrated environment — natural part of the scene",
        "TYPE2": "35-45% of frame height — character is visually dominant, positioned center-right",
        "TYPE3": "10-20% of frame height (INTENTIONALLY TINY — scale contrast is the hook)",
        "TYPE4": "20-25% of frame height, positioned to point at graphic elements",
        "TYPE5": "20-30% of frame height per character — TWO mascots with clear space between them",
        "TYPE6": "10-15% of frame height, secondary to the concept visual",
    }.get(scene_type, "35-45% of frame height — character fills center-right boldly")

    # ── 배경 규칙 (60장 실측: 단색 0건, 그라디언트/환경/분할 100%) ─────────────
    if scene_type == "TYPE1":
        bg_rule = (
            "ILLUSTRATED DRAWN ENVIRONMENT — fully rendered doodle world. "
            "Draw topic-appropriate setting: interior room, outdoor landscape, fantasy space. "
            "Flat doodle art style with bold outlines. NO gradient or solid fill."
        )
    elif scene_type == "TYPE2":
        bg_rule = (
            f"dark atmospheric gradient — deep {main_color}-tinted shadow fading to near-black, "
            "OR topic-context props loosely arranged in background. "
            "NEVER flat solid color. Slight vignette at edges for depth."
        )
    elif scene_type == "TYPE3":
        bg_rule = (
            "illustrated environment OR photorealistic dramatic backdrop — dominant object "
            "must fill 60-70% with hyper-detailed rendering. "
            "Mascot is INTENTIONALLY tiny (10-20%) for scale shock."
        )
    elif scene_type == "TYPE4":
        bg_rule = (
            f"background FILLED with flat bold graphic elements: arrows, bar charts, UI screens, "
            f"price boards, signs in {main_color} and {accent_color}. Dense but readable. "
            "NO solid fill — the graphics ARE the background."
        )
    elif scene_type == "TYPE5":
        bg_rule = (
            "illustrated topic environment OR two-tone split background (left color vs right color). "  # noqa: E501
            "NEVER single solid color. If VS format: bold diagonal or vertical divider. "
            "Each character occupies their own zone."
        )
    elif scene_type == "TYPE6":
        bg_rule = (
            "concept/object visual dominates 60-70% of frame with hyper-detailed rendering. "
            "Background integrates with the concept — no separate solid fill. "
            "Mascot is secondary, observing or embedded in the concept."
        )
    elif is_dark:
        bg_rule = (
            f"deep {main_color}-tinted atmospheric gradient, near-black. "
            "Cinematic dark mood — 1-2 silhouette or fog elements max. "
            "NO flat solid color."
        )
    else:
        bg_rule = (
            f"atmospheric gradient background — choose from: "
            f"(A) medium-gray (#888~#aaa) base with subtle {main_color} tint bleeding from edges, "
            f"(B) deep darkened {main_color} to near-black gradient (channel dark mode), "
            f"(C) illustrated scene environment with topic-relevant props filling left side. "
            "DO NOT use flat solid color. Background brightness: 0.4–0.65 (medium-bright range). "
        )

    # ── 캐릭터 지시문 ────────────────────────────────────────────────────────────
    # 패러디 > TYPE5 드라마 > 일반 단일 캐릭터 순으로 적용
    if parody_entry:
        char_rule = (
            "CHARACTER REFERENCE: The LAST attached image is the official mascot. "
            f"USE THIS EXACT CHARACTER — replicate the same round head, same face, same proportions: {persona}. "
            "⚠️ DO NOT invent a new character. ONLY change the COSTUME and POSE — head/face/body shape MUST stay identical to the reference. "
            "⚠️ STYLE: bold clean doodle cartoon — crisp confident outlines with a subtle natural hand-drawn feel. PASTEL-TONE fills (soft, muted, low-saturation) — NOT oversaturated, NOT neon. NOT photorealistic, NOT cinematic. "
            f"PARODY COSTUME: dress this mascot in '{parody_entry['mascot_costume']}' to re-enact '{parody_entry['name']}'. "
            f"ICONIC PROP: {parody_entry['iconic_prop']}. "
            f"SCENE RECREATION: {parody_entry['scene']} "
            f"MOOD: {parody_entry['mood']}. "
            "The comedy = CONTRAST between the ORIGINAL CUTE DOODLE MASCOT in a dramatic parody costume. "
            f"Mascot fills {_mascot_size_str}. DIRECT EYE CONTACT with viewer from at least one character. "
            "Maximize the cartoon exaggeration of the parody moment. "
        )
    elif scene_type == "TYPE5":
        char_rule = (
            "CHARACTER REFERENCE: The LAST attached image is the official mascot. "
            "⚠️ CRITICAL: DO NOT create a new character design. Use ONLY this exact mascot — replicate the same head shape, face, and body proportions exactly. "
            "Draw TWO instances of this mascot in DIFFERENT topic-appropriate costumes/roles "
            f"(e.g. hero vs villain, before vs after, character A vs B). Base face: {persona}. "
            "ONLY the COSTUME and EXPRESSION may change — head/face/body proportions MUST stay identical to the reference. "
            "COMEDY DRAMA: one character is TOTALLY CRUSHED/SHOCKED (crying, sweating, fainting), "
            "the other is TRIUMPHANT/SMUG (victory pose, pointing, laughing). "
            "The contrast is the PUNCHLINE — like a comic strip panel. "
            f"Each character fills {_mascot_size_str}. "
            f"Main character: MAXIMUM LEVEL 5 {chosen_expr} — jaw off, eyes spinning, sweat flying. "
            "Opposite character: completely contrasting emotion for comedic effect. "
            "They face each other or interact with exaggerated physical comedy. "
            "NO speech bubbles, NO dialogue boxes — body language and expression convey all emotion. "
            "DIRECT EYE CONTACT with viewer from at least one character. "
        )
    else:
        char_rule = (
            "CHARACTER REFERENCE: The LAST attached image is the official mascot. "
            f"⚠️ CRITICAL: DO NOT create a new character design. Replicate this EXACT character — same round head, same face, same proportions ({persona}). "
            "ONLY the COSTUME and EXPRESSION may change — head/face/body shape MUST stay identical to the reference. "
            "COSTUME: adapt the mascot's outfit to fit the topic role AND amplify the comedy "
            "(e.g. a comically oversized office worker tie, a tiny chef hat, a ridiculously big detective magnifying glass). "  # noqa: E501
            f"Character fills {_mascot_size_str}. "
            f"Expression: {chosen_expr} — MAXIMUM CARTOON LEVEL 5 EXAGGERATION. "
            "Eyes wide as dinner plates, jaw literally dropping off face, sweat drops flying, "
            "or pure ecstatic joy with fists pumping — so exaggerated it makes you LAUGH on first glance. "
            "DIRECT EYE CONTACT with viewer. Dynamic pose — leaning forward, jumping, or recoiling. "
        )

    base = (
        "Bold clean doodle cartoon illustration, Korean YouTube thumbnail 1920x1080. "
        "Korean doodle cartoon style: "
        "clean confident cartoon outlines with a subtle natural hand-drawn feel — crisp and bold lines, "
        "NOT rough or scratchy, NOT pencil-texture heavy. "
        "PASTEL-TONE colors — soft, muted, low-saturation marker fills inside bold cartoon outlines. "
        "CHARACTER CONTRAST: the character body should be significantly LIGHTER (2-3× brighter) than "
        "the background — white or light-colored body against medium-gray/dark background. "
        "Fun energetic doodle character art — clean and punchy like a professional webtoon illustration. "
        "Character fills the CENTER-RIGHT area with bold presence, occupying 35-45% of frame height. "
    )

    scene_instruction = f"SCENE ({_COMPOSITION_TYPES[scene_type]['name']}): {scene_clean} "

    bg_instruction = f"BACKGROUND: {bg_rule} "

    composition = (
        "COMPOSITION RULES (based on 142 real YouTube thumbnail analysis): "
        "CHARACTER POSITION: Place the character(s) in the CENTER-RIGHT area (x=45–75%), "
        "VERTICALLY CENTERED (y=35–65%) — body fills the frame boldly. "
        "Characters may bleed off the right or bottom edges for dynamic cropping. "
        "Character GAZE: face forward or slightly left — maintain strong eye contact with viewer. "
        "LEFT SIDE (x=0–45%): fill with scene environment — objects, props, atmosphere. "
        "Keep the left side at MEDIUM detail level — interesting but not overly complex. "
        "⚠️ CRITICAL TEXT ZONE — LOWER-LEFT (x=0–50%, y=58–100%): "
        "this area MUST stay VISUALLY SIMPLE. No dense props, no complex patterns, "
        "no character limbs, no overlapping objects. Use a simple gradient or single flat color. "
        "Title text will overlay here — competing visual elements will make it unreadable. "
        "UPPER-LEFT corner (x=0–40%, y=0–18%): also keep lighter/simpler for possible subtitle. "
        "TOP-RIGHT corner (10% width x 10% height): completely empty for logo watermark. "
        "MOST IMPORTANT: the composition should feel like character and background are ONE integrated scene, "
        "NOT a character pasted onto a background. "
    )

    style = (
        "⚠️ COLOR RULE — PASTEL TONE MANDATORY: ALL colors in this image must be PASTEL / MUTED. "
        "HSV saturation target: 0.30–0.50 (NEVER above 0.60). "
        "Brightness target: 0.75–0.92 (light, airy, soft). "
        "NO neon, NO fluorescent, NO deep-saturated vivid colors. "
        "Think 'soft watercolor illustration' or 'Studio Ghibli palette' — gentle and breathable. "
        "This keeps text overlaid on the image clearly readable. "
        f"CHANNEL SIGNATURE COLOR: {main_color} — use as pastel-tinted base for "
        "background, costume, and dominant props. Desaturate if needed to stay pastel. "
        f"CHANNEL POINT COLOR: {accent_color} — apply SPARINGLY to 1-2 small focal elements only "
        "(hat brim, badge, small icon, highlight detail). Keep it pastel too — no deep intense fills. "
        "BACKGROUND: soft pastel gradient or lightly-tinted illustrated scene — "
        "light enough that white text overlaid on the bottom-left will be clearly legible. "
        "Bold black cartoon outlines on ALL elements — clean and confident. "
        "Motion lines, sweat drops, and action effects drawn in bold clean cartoon style. "
        "NO photorealistic rendering. NO smooth 3D shading. NO airbrush. NO rough pencil texture. "
        "Shading: simple flat color or very minimal hatching — clean cartoon style. "
        "CRITICAL: ABSOLUTELY NO text, letters, numbers, captions, watermarks, or reference labels "
        "(including [Image #1], [Image #2], or any bracketed labels) anywhere in the image. NON-NEGOTIABLE. "
        "CRITICAL: ABSOLUTELY NO speech bubbles, dialogue boxes, or thought bubbles of any kind. NON-NEGOTIABLE. "
    )

    return base + char_rule + scene_instruction + bg_instruction + composition + style


def _record_cost(run_id: str, channel: str, calls: int, success: bool) -> None:
    try:
        _COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = read_json(_COST_FILE)
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            data = {"records": [], "total_calls": 0, "total_cost_usd": 0.0}

        record = {
            "run_id": run_id,
            "channel": channel,
            "gemini_calls": calls,
            "cost_usd": round(calls * _COST_PER_CALL, 4),
            "success": success,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        data.setdefault("records", []).append(record)
        data["total_calls"] = data.get("total_calls", 0) + calls
        data["total_cost_usd"] = round(
            data.get("total_cost_usd", 0.0) + record["cost_usd"], 4
        )
        write_json(_COST_FILE, data)
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 비용 기록 실패 (무시): {e}")


def _build_background_prompt(channel: str, topic: str, scene_desc: str = "") -> str:
    """배경 전용 프롬프트 — 캐릭터 없음 (A안).

    generate_background_illustration() 전용.
    오른쪽(x=45-100%) 영역은 단순 그라디언트로 유지 — L2 캐릭터 합성 공간.
    """
    info = CHANNEL_MASCOT_PERSONA.get(channel, {})
    category = info.get("category", "info") if isinstance(info, dict) else "info"
    main_color, accent_color = CHANNEL_COLORS.get(channel, ("#FFFFFF", "#000000"))
    is_dark = category == "stimulating_strong"

    scene_type, _ = _parse_parody_tag(scene_desc)
    colon_pos = scene_desc.find(":")
    scene_clean = scene_desc[colon_pos + 1:].strip() if colon_pos != -1 else scene_desc
    if not scene_clean:
        scene_clean = f"atmospheric scene background relevant to: {topic}"

    if scene_type == "TYPE1":
        bg_rule = (
            "ILLUSTRATED DRAWN ENVIRONMENT — fully rendered doodle world, NO CHARACTERS. "
            "Topic-appropriate setting: interior room, outdoor landscape, fantasy space. "
            "Flat doodle art style with bold outlines. LEFT side (x=0-45%) has main detail. "
            "RIGHT side (x=45-100%) stays relatively simple — gradient or open space."
        )
    elif scene_type in ("TYPE2", "TYPE5"):
        bg_rule = (
            f"dark atmospheric gradient — deep {main_color}-tinted shadow fading to near-black. "
            "OR topic-context props loosely arranged on left side. "
            "NEVER flat solid color. RIGHT SIDE (x=45-100%): simple gradient only — "
            "character will be composited here."
        )
    elif scene_type == "TYPE3":
        bg_rule = (
            "dominant object fills 60-70% with hyper-detailed illustration rendering. "
            "LEFT SIDE: main scene detail. "
            "RIGHT SIDE: simpler gradient for character compositing."
        )
    elif scene_type == "TYPE4":
        bg_rule = (
            f"background FILLED with flat bold graphic elements: arrows, bar charts, UI screens, "
            f"price boards in {main_color} and {accent_color}. "
            "RIGHT SIDE: slightly simpler for character placement."
        )
    elif scene_type == "TYPE6":
        bg_rule = (
            "concept/object visual dominates 60-70% of frame. "
            "No character present — background tells the story visually."
        )
    elif is_dark:
        bg_rule = (
            f"deep {main_color}-tinted atmospheric gradient, near-black. "
            "Cinematic dark mood. 1-2 silhouette or fog elements. NO flat solid color."
        )
    else:
        bg_rule = (
            f"atmospheric gradient — deep darkened {main_color} to near-black. "
            "OR illustrated scene with topic-relevant props on LEFT SIDE (x=0-45%). "
            "RIGHT SIDE (x=45-100%): simple gradient — character PNG composited here later. "
            "DO NOT use flat solid color."
        )

    base = (
        "Bold clean doodle cartoon BACKGROUND illustration only. Korean YouTube thumbnail 1920x1080. "
        "⚠️ ABSOLUTELY NO CHARACTERS, NO PEOPLE, NO MASCOTS — environment and props only. "
        "Korean doodle cartoon style: bold outlines, pastel-tone colors. "
    )
    scene_instruction = (
        f"SCENE BACKGROUND: {scene_clean} "
        "Remove ALL characters — draw only the environment, props, and atmosphere. "
    )
    bg_instruction = f"BACKGROUND: {bg_rule} "
    composition = (
        "COMPOSITION RULES: "
        "LEFT SIDE (x=0-45%): main scene detail, props, atmospheric elements. "
        "⚠️ LOWER-LEFT (x=0-50%, y=58-100%): KEEP VISUALLY SIMPLE — soft gradient or single-tone. "
        "Title text will overlay here. "
        "RIGHT SIDE (x=45-100%): simple gradient background — character PNG composited here. "
        "TOP-RIGHT corner (10% × 10%): completely empty for watermark. "
    )
    style = (
        "⚠️ NO TEXT, NO CHARACTERS, NO PEOPLE anywhere. "
        "PASTEL TONE MANDATORY: HSV saturation 0.30-0.50. "
        f"Channel signature color: {main_color} — dominant tint. "
        "Bold black cartoon outlines on all elements. "
        "NO photorealistic rendering. NO speech bubbles. "
        "ABSOLUTELY NO text, letters, numbers, captions in image. "
    )
    return base + scene_instruction + bg_instruction + composition + style


def generate_background_illustration(
    channel: str,
    topic: str,
    run_id: str,
    output_path: Path,
    max_retries: int = 2,
    *,
    force_parody: bool = False,
    client: Optional[genai.Client] = None,
) -> tuple[Path | None, str | None]:
    """배경 전용 일러스트 생성 (캐릭터 없음, A안).

    L2 캐릭터를 오른쪽에 합성하기 위해 배경만 생성.
    스타일 레퍼런스만 전달 (마스코트 레퍼런스 제외).

    Returns:
        (output_path | None, parody_costume | None)
        parody_costume: 패러디 감지 시 mascot_costume 키워드 문자열, 아니면 None
    """
    ref_dir = _ROOT / "assets" / "references"
    style_refs = [
        ref_dir / "logo_ref_01.png",
        ref_dir / "logo_ref_02.png",
        ref_dir / "logo_ref_03.png",
        ref_dir / "logo_ref_04.png",
    ]
    refs = [p for p in style_refs if os.path.exists(str(p))]
    if not refs:
        logger.warning(f"[STEP10-BG] 스타일 레퍼런스 없음 ({channel}) — 폴백 진행")
        return None, None

    scene_desc = _generate_thumbnail_scene(channel, topic, force_parody=force_parody)
    prompt = _build_background_prompt(channel, topic, scene_desc=scene_desc)

    # 패러디 의상 키워드 추출 (배경 생성 성공/실패와 무관하게 L2에 전달)
    parody_costume: str | None = None
    _, parody_id = _parse_parody_tag(scene_desc)
    if parody_id:
        entry = next((e for e in _load_parody_bank() if e["id"] == parody_id), None)
        if entry:
            parody_costume = entry.get("mascot_costume")
            logger.info(f"[STEP10-BG] 패러디 의상 추출: {parody_costume!r} ({parody_id})")

    if client is None:
        client = _make_client()

    calls = 0
    for attempt in range(max_retries + 1):
        try:
            ref_parts = [
                types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png")
                for p in refs
            ]
            response = client.models.generate_content(
                model=_IMAGE_MODEL,
                contents=ref_parts + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            calls += 1

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(part.inline_data.data)
                    logger.info(
                        f"[STEP10-BG] 배경 생성 성공: {output_path.name} "
                        f"({len(part.inline_data.data):,} bytes, 시도={attempt+1})"
                    )
                    _record_cost(run_id, channel, calls, True)
                    return output_path, parody_costume

            logger.warning(f"[STEP10-BG] 이미지 응답 없음 (시도 {attempt+1}/{max_retries+1})")

        except Exception as e:
            calls += 1
            logger.warning(f"[STEP10-BG] 생성 실패 (시도 {attempt+1}): {e}")

        if attempt < max_retries:
            time.sleep(2.0)

    _record_cost(run_id, channel, calls, False)
    logger.warning(f"[STEP10-BG] {max_retries+1}회 모두 실패 → 폴백 ({channel})")
    return None, parody_costume


def generate_episode_illustration(
    channel: str,
    topic: str,
    run_id: str,
    output_path: Path,
    max_retries: int = 2,
    *,
    expression: str | None = None,
    force_parody: bool = False,
    client: Optional[genai.Client] = None,
) -> Path | None:
    """에피소드별 마스코트 통합 풀스크린 일러스트 생성.

    레퍼런스 이미지(두들 스타일 4장 + 채널 로고 + 마스코트)를 few-shot으로
    전달해 일관된 두들 스타일을 확보한다.

    Returns:
        성공 시 output_path, 실패(모든 재시도 소진) 시 None
    """
    ref_dir = _ROOT / "assets" / "references"
    style_refs = [
        ref_dir / "logo_ref_01.png",
        ref_dir / "logo_ref_02.png",
        ref_dir / "logo_ref_03.png",
        ref_dir / "logo_ref_04.png",
    ]
    # 로고는 앞에, 마스코트(character_default)는 마지막에 — Gemini 어텐션 최강화
    logo_ref = _ROOT / "assets" / "channels" / channel / "logo" / "logo.png"
    mascot_ref = _ROOT / "assets" / "channels" / channel / "mascot" / "mascot_default.png"

    refs = [p for p in style_refs if os.path.exists(str(p))]
    if os.path.exists(str(logo_ref)):
        refs.append(logo_ref)
    if os.path.exists(str(mascot_ref)):
        refs.append(mascot_ref)  # 항상 마지막 — 프롬프트의 "LAST attached image" 지시에 대응

    if not refs:
        logger.warning(f"[STEP10-ILLUST] 레퍼런스 이미지 없음 ({channel}) — 폴백으로 진행")
        return None

    # LLM이 먼저 "구성 유형 선택 + 무엇을 그릴지" 장면 대사 기획
    scene_desc = _generate_thumbnail_scene(channel, topic, force_parody=force_parody)
    prompt = _build_prompt(channel, topic, expression, scene_desc=scene_desc)
    if client is None:
        client = _make_client()

    calls = 0
    for attempt in range(max_retries + 1):
        try:
            ref_parts = [
                types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png")
                for p in refs
            ]
            response = client.models.generate_content(
                model=_IMAGE_MODEL,
                contents=ref_parts + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            calls += 1

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(part.inline_data.data)
                    logger.info(
                        f"[STEP10-ILLUST] 생성 성공: {output_path.name} "
                        f"({len(part.inline_data.data):,} bytes, 시도={attempt+1})"
                    )
                    _record_cost(run_id, channel, calls, True)
                    return output_path

            logger.warning(
                f"[STEP10-ILLUST] 이미지 응답 없음 (시도 {attempt+1}/{max_retries+1})"
            )

        except Exception as e:
            calls += 1
            logger.warning(f"[STEP10-ILLUST] 생성 실패 (시도 {attempt+1}): {e}")

        if attempt < max_retries:
            time.sleep(2.0)

    _record_cost(run_id, channel, calls, False)
    logger.warning(f"[STEP10-ILLUST] {max_retries+1}회 모두 실패 → 폴백 사용 ({channel})")
    return None
