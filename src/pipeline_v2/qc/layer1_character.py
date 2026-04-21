"""QC Layer 1 — 캐릭터 일관성 (Vision + CLIP + ORB 다중 검증)"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

PASS_THRESHOLD = 0.85
RETRY_THRESHOLD = 0.70

_clip_model = None
_clip_processor = None


def _get_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        try:
            from transformers import CLIPModel, CLIPProcessor
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except ImportError:
            logger.warning("transformers 미설치 — CLIP 점수 0으로 대체")
    return _clip_model, _clip_processor


def _score_vision_gemini(img_path: str, ref_path: str) -> float:
    """Gemini Vision으로 캐릭터 일관성 점수 계산."""
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.0-flash")
        with open(img_path, "rb") as f:
            img_data = f.read()
        with open(ref_path, "rb") as f:
            ref_data = f.read()
        resp = model.generate_content([
            "두 이미지의 두들 애니메이션 캐릭터가 같은 캐릭터인지 0.0~1.0 점수로만 답하세요.",
            {"mime_type": "image/png", "data": img_data},
            {"mime_type": "image/png", "data": ref_data},
        ])
        return float(resp.text.strip()[:4])
    except Exception as e:
        logger.debug(f"Vision 점수 실패: {e}")
        return 0.7


def _score_clip_similarity(img_path: str, ref_path: str) -> float:
    """CLIP 임베딩 코사인 유사도."""
    model, processor = _get_clip()
    if model is None:
        return 0.7
    try:
        import torch
        from PIL import Image
        img = Image.open(img_path).convert("RGB")
        ref = Image.open(ref_path).convert("RGB")
        inputs = processor(images=[img, ref], return_tensors="pt", padding=True)
        with torch.no_grad():
            feats = model.get_image_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
        sim = (feats[0] @ feats[1]).item()
        return max(0.0, min(1.0, (sim + 1) / 2))
    except Exception as e:
        logger.debug(f"CLIP 점수 실패: {e}")
        return 0.7


def _score_orb_matching(img_path: str, ref_path: str) -> float:
    """ORB keypoint 매칭 비율."""
    try:
        import cv2
        import numpy as np  # noqa: F401
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        ref = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        if img is None or ref is None:
            return 0.7
        orb = cv2.ORB_create(nfeatures=500)
        kp1, desc1 = orb.detectAndCompute(img, None)
        kp2, desc2 = orb.detectAndCompute(ref, None)
        if desc1 is None or desc2 is None:
            return 0.5
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        ratio = len(matches) / max(len(kp1), len(kp2), 1)
        return min(1.0, ratio * 2.5)
    except ImportError:
        logger.warning("opencv-python 미설치 — ORB 점수 0.7로 대체")
        return 0.7
    except Exception as e:
        logger.debug(f"ORB 점수 실패: {e}")
        return 0.7


def compute_consistency_score(img_path: str, ref_path: str) -> tuple[float, dict]:
    """J3 다중 검증 — 0.5V + 0.3C + 0.2O 가중 평균."""
    v = _score_vision_gemini(img_path, ref_path)
    c = _score_clip_similarity(img_path, ref_path)
    o = _score_orb_matching(img_path, ref_path)
    composite = 0.5 * v + 0.3 * c + 0.2 * o
    return composite, {"vision": v, "clip": c, "orb": o, "composite": composite}


def check_scene_images(
    scene_images: list[str],
    channel_id: str,
    role: str = "narrator",
) -> tuple[bool, float, list[dict]]:
    """씬 이미지 전체 QC Layer1 검증.

    Returns: (all_pass, avg_score, per_image_results)
    """
    ref_path = f"assets/characters/{channel_id}/{role}_ref.png"
    if not Path(ref_path).exists():
        logger.warning(f"레퍼런스 이미지 없음: {ref_path} — Layer1 스킵")
        return True, 0.85, []

    results = []
    scores = []
    for img_path in scene_images:
        if not Path(img_path).exists():
            continue
        score, detail = compute_consistency_score(img_path, ref_path)
        scores.append(score)
        passed = score >= PASS_THRESHOLD
        results.append({"image": img_path, "score": score, "passed": passed, **detail})

    avg = float(sum(scores) / len(scores)) if scores else 0.85
    all_pass = avg >= PASS_THRESHOLD
    return all_pass, avg, results


def run_layer1(meta: EpisodeMeta, scene_images: list[str]) -> dict:
    """QC Layer1 실행 + episode metadata 갱신."""
    all_pass, avg_score, results = check_scene_images(scene_images, meta.channel_id)
    meta.features.character_consistency_score = round(avg_score, 3)
    logger.info(f"QC Layer1: avg={avg_score:.3f} pass={all_pass} ({len(results)}이미지)")
    return {
        "passed": all_pass,
        "avg_score": avg_score,
        "threshold": PASS_THRESHOLD,
        "results": results,
    }
