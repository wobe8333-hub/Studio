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
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

from src.core.ssot import read_json, write_json  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
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
    "CH1": ("#F4C420", "#DC2626"),
    "CH2": ("#00E5FF", "#FFFFFF"),
    "CH3": ("#E67E22", "#2ECC71"),
    "CH4": ("#9B59B6", "#BDC3C7"),
    "CH5": ("#1C2833", "#AAAAAA"),
    "CH6": ("#A0522D", "#C4A35A"),
    "CH7": ("#C0392B", "#2C3E50"),
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
        "mascot_size": "55-65% of frame, center or center-right",
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


def _generate_thumbnail_scene(channel: str, topic: str) -> str:
    """Gemini Text로 구성 유형 선택 + 썸네일 장면 대사 생성.

    반환 형식: "TYPE{N}: [English scene description 2~3 sentences]"
    LLM이 6가지 유형 중 주제에 가장 적합한 TYPE를 직접 선택한다.
    """
    from src.core.llm_client import generate_text

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
        "near-black or deep navy (dark dramatic)" if is_dark
        else f"bold {main_color} (channel primary)"
    )

    system = (
        "You are a Korean YouTube thumbnail art director specializing in 사물궁이 잡학지식 doodle style.\n"  # noqa: E501
        "Analyze the topic and select the composition type that creates maximum CTR (curiosity + visual impact).\n\n"  # noqa: E501
        f"Recommended composition types for '{category}' channel:\n{type_guide}\n\n"
        "Output rules:\n"
        "- MUST start with one of: TYPE1: / TYPE2: / TYPE3: / TYPE4: / TYPE5: / TYPE6:\n"
        "- PROPS must be SPECIFIC named objects (e.g. 'one oversized gold coin', 'a single bar chart arrow up').\n"  # noqa: E501
        "- BACKGROUND: NEVER use flat solid color. Use illustrated environment, dark atmospheric gradient, or two-tone split.\n"  # noqa: E501
        f"- Dark/dramatic topics may use: near-black {bg_hint} atmospheric backdrop.\n"
        "- COSTUME: mascot should wear topic-appropriate role outfit (e.g. chef hat, lab coat, historical costume).\n"  # noqa: E501
        "- Output: TYPE prefix + 2~3 English sentences ONLY. No bullet points. No explanation."
    )
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

    scene_type = _extract_scene_type(scene_desc)
    # TYPE 접두사 제거한 순수 장면 묘사
    if scene_desc.upper().startswith(scene_type):
        scene_clean = scene_desc[len(scene_type):].lstrip(":").strip()
    else:
        scene_clean = scene_desc

    if not scene_clean:
        scene_clean = (
            f"mascot character in topic-appropriate costume reacts with {chosen_expr} expression, "
            f"dark atmospheric {main_color}-tinted gradient background, one topic-related prop visible."  # noqa: E501
        )

    # 구성 유형별 마스코트 크기
    _mascot_size_str = {
        "TYPE1": "35% of frame, integrated into illustrated environment",
        "TYPE2": "55-65% of frame, center-right dominant",
        "TYPE3": "10-20% of frame (INTENTIONALLY TINY — scale contrast is the hook)",
        "TYPE4": "20-25% of frame, positioned to point at graphic elements",
        "TYPE5": "25-35% per character — TWO mascots interact",
        "TYPE6": "10-15% of frame, secondary to the concept visual",
    }.get(scene_type, "55% of frame")

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
            f"dark atmospheric gradient with {main_color} tint, "
            "topic-context props loosely in background. "
            "NO flat solid color — always gradient or illustrated elements."
        )

    # ── 캐릭터 지시문 ────────────────────────────────────────────────────────────
    # TYPE5는 2~3명 드라마 구조, 나머지는 단일 주인공 + 주제별 코스튬
    if scene_type == "TYPE5":
        char_rule = (
            "CHARACTER REFERENCE: The LAST attached image is the official mascot. "
            "Draw TWO instances of this mascot in DIFFERENT topic-appropriate costumes/roles "
            f"(e.g. hero vs villain, before vs after, character A vs B). Base face: {persona}. "
            "OPTIONAL: one character may be an antagonist variant — darker tone, evil expression. "
            f"Each character fills {_mascot_size_str}. "
            f"Main character: expression {chosen_expr}. Opposite character: contrasting expression. "  # noqa: E501
            "They face each other or interact. Speech bubbles allowed but leave interior EMPTY. "
            "DIRECT EYE CONTACT with viewer from at least one character. "
        )
    else:
        char_rule = (
            "CHARACTER REFERENCE: The LAST attached image is the official mascot. "
            f"Replicate this EXACT character — same round head, same proportions ({persona}). "
            "COSTUME: adapt the mascot's outfit to fit the topic role "
            "(e.g. chef hat for food topic, lab coat for science, traditional hanbok for history). "
            f"Character fills {_mascot_size_str}. "
            f"Expression: {chosen_expr}, exaggerated cartoon emotion, clearly visible. "
            "DIRECT EYE CONTACT with viewer. Dynamic pose with motion energy. "
        )

    base = (
        "flat 2D doodle illustration, Korean YouTube thumbnail 1920x1080, "
        "사물궁이 잡학지식 SAMU style — bold outlines, flat colors, high-contrast professional palette. "  # noqa: E501
    )

    scene_instruction = f"SCENE ({_COMPOSITION_TYPES[scene_type]['name']}): {scene_clean} "

    bg_instruction = f"BACKGROUND: {bg_rule} "

    composition = (
        "COMPOSITION RULES: "
        "TOP-LEFT area (left 55% width, top 35% height): keep clear for title text overlay zone. "
        "TOP-RIGHT corner (12% width x 12% height): completely empty for logo watermark. "
    )

    style = (
        f"Colors: main={main_color}, accent={accent_color}. Bold, saturated, high-contrast. "
        "2px black outline on ALL doodle elements. Flat colors only — no gradients, no shadows, no textures. "  # noqa: E501
        "Subtle motion lines around character for energy and impact. "
        "CRITICAL: NO text, NO letters, NO numbers anywhere in the image. "
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


def generate_episode_illustration(
    channel: str,
    topic: str,
    run_id: str,
    output_path: Path,
    max_retries: int = 2,
    *,
    expression: str | None = None,
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
    mascot_ref = _ROOT / "assets" / "channels" / channel / "characters" / "character_default.png"

    refs = [p for p in style_refs if p.exists()]
    if logo_ref.exists():
        refs.append(logo_ref)
    if mascot_ref.exists():
        refs.append(mascot_ref)  # 항상 마지막 — 프롬프트의 "LAST attached image" 지시에 대응

    if not refs:
        logger.warning(f"[STEP10-ILLUST] 레퍼런스 이미지 없음 ({channel}) — 폴백으로 진행")
        return None

    # LLM이 먼저 "구성 유형 선택 + 무엇을 그릴지" 장면 대사 기획
    scene_desc = _generate_thumbnail_scene(channel, topic)
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
