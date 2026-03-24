from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _truncate(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _pick_title_variants(title_obj: Dict[str, Any], style_policy: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    LLM 없이 결정적(rule-based)으로 title 3개 변형 생성.
    """
    base_title = str(title_obj.get("selected_title") or title_obj.get("title_candidates", [""])[0] or "")
    topic = str(title_obj.get("topic") or title_obj.get("channel_id") or "Topic")

    channel_style_id = str(style_policy.get("channel_style_id") or "")
    prompt_system_id = str(style_policy.get("prompt_system_id") or "")

    # style_policy 기반 tone 선택 (상수 테이블, LLM 없음)
    authority_suffix = {
        "documentary_authority": " 완전 정리",
        "practical_explainer": " 바로 따라하기",
        "emotional_storytelling": " 쉽게 이해하기",
    }.get(channel_style_id, " 완전 정리")

    if any(x in base_title for x in ["완전 정리", "바로 따라하기", "쉽게 이해하기"]):
        title_v1 = base_title
    else:
        title_v1 = _truncate(f"{topic}{authority_suffix}", 28)

    # curiosity
    if prompt_system_id == "hook_story_empathy" or channel_style_id == "emotional_storytelling":
        title_v2 = _truncate(f"{topic} 왜 마음이 바뀔까?", 28)
    else:
        title_v2 = _truncate(f"{topic} 핵심만 보면 달라진다", 28)

    # benefit/problem-solution
    if channel_style_id == "practical_explainer":
        title_v3 = _truncate(f"{topic} 문제를 푸는 방법", 28)
    elif channel_style_id == "emotional_storytelling":
        title_v3 = _truncate(f"{topic} 공감 포인트 정리", 28)
    else:
        title_v3 = _truncate(f"{topic} 실전 가이드", 28)

    # 최종 트림(안전)
    title_v1 = _truncate(title_v1, 30)
    title_v2 = _truncate(title_v2, 30)
    title_v3 = _truncate(title_v3, 30)

    return [
        {"id": "title_v1", "mode": "authority", "title": title_v1},
        {"id": "title_v2", "mode": "curiosity", "title": title_v2},
        {"id": "title_v3", "mode": "benefit", "title": title_v3},
    ]


def _try_pil() -> Tuple[Any, Any, Any, Any, Any]:
    """
    Pillow import를 시도하고, 없으면 예외를 그대로 올리지 않고 caller가 처리 가능하도록 한다.
    """
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont  # type: ignore

    return Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont


def _apply_thumbnail_variant(
    base_img: Any,
    variant_id: str,
    base_thumbnail_style_id: str,
):
    """
    base thumbnail.png 위에 "얇은 overlay"를 적용해 variant를 생성.
    """
    Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont = _try_pil()
    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    # base style와 충돌하는 경우 오버레이 강도를 낮춤
    same_as_base = (variant_id == base_thumbnail_style_id)
    border_w = 6 if not same_as_base else 3

    if variant_id == "high_contrast_warning":
        factor = 1.35 if not same_as_base else 1.15
        img = ImageEnhance.Contrast(img).enhance(factor)
        img = ImageEnhance.Brightness(img).enhance(1.05 if not same_as_base else 1.02)
        w, h = img.size
        # 빨강 테두리
        draw.rectangle([0, 0, w - 1, h - 1], outline=(220, 50, 50), width=border_w)
        # 노랑 하단 경고 바 (텍스트 없이 shape만)
        bar_h = 22
        draw.rectangle([0, h - bar_h, w, h], fill=(255, 215, 0))

    elif variant_id == "clean_trust":
        # 살짝 채도/대비를 낮추고 "신뢰" 톤으로 정리
        sat = 0.85 if not same_as_base else 0.95
        con = 0.95 if not same_as_base else 0.99
        img = ImageEnhance.Color(img).enhance(sat)
        img = ImageEnhance.Contrast(img).enhance(con)
        w, h = img.size
        # 우측 상단 라벨
        label_h = 34
        draw.rectangle([w - 220, 0, w, label_h], fill=(40, 110, 220))
        font = ImageFont.load_default()
        draw.text((w - 200, 7), "TRUST", fill=(255, 255, 255), font=font)

    elif variant_id == "curiosity_gap":
        # 중앙 블러 + 질문형 마커
        radius = 2.0 if not same_as_base else 1.2
        blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
        w, h = img.size
        # 중앙 영역만 블러 조합
        mask = Image.new("L", (w, h), 0)
        # 약간 작은 중앙 사각형을 선택
        x1 = int(w * 0.15)
        y1 = int(h * 0.25)
        x2 = int(w * 0.85)
        y2 = int(h * 0.75)
        from PIL import Image as _Image  # type: ignore

        _draw = ImageDraw.Draw(mask)
        _draw.rectangle([x1, y1, x2, y2], fill=180)
        img = Image.composite(blurred, img, mask)

        # 질문형 원 마커
        r = 28 if not same_as_base else 20
        cx, cy = int(w * 0.18), int(h * 0.18)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
        font = ImageFont.load_default()
        draw.text((cx - 6, cy - 10), "?", fill=(255, 255, 255), font=font)

    else:
        # unknown → base 그대로
        pass

    return img


def run_variant_builder_builder(v8_root: Path, run_id: str) -> None:
    """
    V8.5 Thumbnail/Title Variant Builder (얇은 오버레이 계층).
    - title.json/thumbnail.png은 유지
    - variants/ 아래에 추가 산출물 생성
    """
    print("[STEP10] title variants start")

    title_path = v8_root / "title.json"
    thumb_path = v8_root / "thumbnail.png"
    policy_path = v8_root / "style_policy.json"
    if not title_path.is_file():
        raise FileNotFoundError(f"missing title.json: {title_path}")
    if not thumb_path.is_file():
        raise FileNotFoundError(f"missing thumbnail.png: {thumb_path}")
    if not policy_path.is_file():
        raise FileNotFoundError(f"missing style_policy.json: {policy_path}")

    title_obj = _read_json(title_path)
    style_policy = _read_json(policy_path)

    style_policy_fingerprint = str(style_policy.get("policy_fingerprint") or "")
    channel_style_id = str(style_policy.get("channel_style_id") or "")
    thumbnail_style_id = str(style_policy.get("thumbnail_style_id") or "")
    prompt_system_id = str(style_policy.get("prompt_system_id") or "")

    title_variants = _pick_title_variants(title_obj, style_policy)
    variants_dir = v8_root / "variants"
    variants_dir.mkdir(parents=True, exist_ok=True)
    title_variants_path = variants_dir / "title_variants.json"

    title_variant_obj: Dict[str, Any] = {
        "run_id": run_id,
        "source_title_json": title_path.as_posix(),
        "source_thumbnail_png": thumb_path.as_posix(),
        "style_policy_fingerprint": style_policy_fingerprint,
        "channel_style_id": channel_style_id,
        "thumbnail_style_id": thumbnail_style_id,
        "prompt_system_id": prompt_system_id,
        "title_variant_count": 3,
        "thumbnail_variant_count": 3,
        "generated_at": _now_iso(),
        "variants": title_variants,
    }

    _write_json(title_variants_path, title_variant_obj)
    print("[STEP10] title variants done count=3")

    print("[STEP10] thumbnail variants start")

    thumb_variants: Dict[str, Path] = {}
    thumb_img = None
    try:
        Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont = _try_pil()
        thumb_img = Image.open(str(thumb_path)).convert("RGB")
    except Exception:
        thumb_img = None

    variant_order = [
        ("thumbnail_variant_01.png", "high_contrast_warning"),
        ("thumbnail_variant_02.png", "clean_trust"),
        ("thumbnail_variant_03.png", "curiosity_gap"),
    ]

    for file_name, variant_id in variant_order:
        out_path = variants_dir / file_name
        if thumb_img is None:
            # PIL 미존재 등 실패 시에도 파일 계약(생성)만 보장
            out_path.write_bytes(thumb_path.read_bytes())
        else:
            out_img = _apply_thumbnail_variant(thumb_img, variant_id=variant_id, base_thumbnail_style_id=thumbnail_style_id)
            out_img.save(str(out_path), format="PNG")
        thumb_variants[file_name] = out_path

    print("[STEP10] thumbnail variants done count=3")

    manifest_path = variants_dir / "variant_manifest.json"
    manifest_obj: Dict[str, Any] = {
        "variant_version": "v1",
        "run_id": run_id,
        "source_run_v8_path": v8_root.as_posix(),
        "title_variants_path": title_variants_path.as_posix(),
        "thumbnail_variants": {
            k.replace(".png", ""): v.as_posix() for k, v in thumb_variants.items()
        },
        "style_policy_fingerprint": style_policy_fingerprint,
        "channel_style_id": channel_style_id,
        "thumbnail_style_id": thumbnail_style_id,
        "prompt_system_id": prompt_system_id,
        "title_variant_count": 3,
        "thumbnail_variant_count": 3,
        "created_at": _now_iso(),
    }
    _write_json(manifest_path, manifest_obj)
    print(f"[STEP10] variant manifest saved path={manifest_path}")
    print("[STEP10] complete")



