"""
V7.5 Style Policy Engine - rule-based policy decision only.
V8 is execution layer; this layer only produces style_policy.json (SSOT).
No KPI inference, no LLM, deterministic selection.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils import run_manager

# Registry file names under backend/style/
REGISTRY_NAMES = ("channel_style_registry", "image_style_registry", "thumbnail_style_registry", "prompt_system_registry")
STYLE_POLICY_VERSION = "1.0.0"

# --- Selection rule constants (rule-based deterministic) ---
# Audience tags that prefer emotional_storytelling or practical_explainer
AUDIENCE_SENIOR_TAGS = ("senior", "50", "60", "elderly", "50+", "60+")
# Topic keywords that prefer clean_trust / documentary_authority
TOPIC_SAFE_GENERAL = ("health", "medical", "finance", "legal", "safety", "investment", "tax")
# Default IDs when no rule matches
DEFAULT_CHANNEL_STYLE_ID = "documentary_authority"
DEFAULT_IMAGE_STYLE_ID = "cinematic_realistic"
DEFAULT_THUMBNAIL_STYLE_ID = "curiosity_gap"
DEFAULT_PROMPT_SYSTEM_ID = "hook_openloop_authority"

# Reason codes (fixed string codes, not prose)
REASON_DEFAULT = "AUDIENCE_DEFAULT"
REASON_TOPIC_SAFE = "TOPIC_SAFE_GENERAL"
REASON_CHANNEL_BALANCED = "CHANNEL_BALANCED"
REASON_SENIOR_AUDIENCE = "SENIOR_AUDIENCE"


def _style_dir() -> Path:
    """backend/style directory (registries location)."""
    return run_manager.get_project_root() / "backend" / "style"


def _load_registry(name: str) -> Dict[str, Any]:
    path = _style_dir() / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"registry not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    return {"data": data, "entries": entries, "path": path}


def load_style_registries() -> Dict[str, Dict[str, Any]]:
    """Load all four style registries. Raises if any missing or invalid."""
    result: Dict[str, Dict[str, Any]] = {}
    for name in REGISTRY_NAMES:
        result[name] = _load_registry(name)
    return result


def _registry_hash(registry_dict: Dict[str, Any]) -> str:
    """Deterministic hash of registry: sort keys and content, then sha256."""
    # Use the raw file content for stability
    data = registry_dict.get("data") or {}
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _policy_fingerprint(policy: Dict[str, Any]) -> str:
    """Deterministic fingerprint: sort keys, exclude generated_at for reproducibility of same inputs."""
    copy = {k: v for k, v in policy.items() if k != "generated_at"}
    canonical = json.dumps(copy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ids_from_registries(regs: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return list of valid id values per registry type for validation."""
    channel_ids = [e.get("id") for e in (regs.get("channel_style_registry") or {}).get("entries") or [] if e.get("id")]
    image_ids = [e.get("id") for e in (regs.get("image_style_registry") or {}).get("entries") or [] if e.get("id")]
    thumb_ids = [e.get("id") for e in (regs.get("thumbnail_style_registry") or {}).get("entries") or [] if e.get("id")]
    prompt_ids = [e.get("id") for e in (regs.get("prompt_system_registry") or {}).get("entries") or [] if e.get("id")]
    return list(channel_ids or []) + list(image_ids or []) + list(thumb_ids or []) + list(prompt_ids or [])


def _select_channel_style(audience: str, topic_lower: str) -> tuple[str, List[str]]:
    """Rule-based: senior/elderly -> emotional or practical; health/finance/legal -> documentary; else default."""
    reasons: List[str] = []
    audience_lower = (audience or "").lower()
    if any(t in audience_lower for t in AUDIENCE_SENIOR_TAGS):
        reasons.append(REASON_SENIOR_AUDIENCE)
        return "emotional_storytelling", reasons
    if any(t in topic_lower for t in TOPIC_SAFE_GENERAL):
        reasons.append(REASON_TOPIC_SAFE)
        return "documentary_authority", reasons
    reasons.append(REASON_DEFAULT)
    return DEFAULT_CHANNEL_STYLE_ID, reasons


def _select_image_style(topic_lower: str) -> tuple[str, List[str]]:
    """Rule-based: safe topics -> editorial_clean; else cinematic_realistic."""
    reasons: List[str] = []
    if any(t in topic_lower for t in TOPIC_SAFE_GENERAL):
        reasons.append(REASON_TOPIC_SAFE)
        return "editorial_clean", reasons
    reasons.append(REASON_DEFAULT)
    return DEFAULT_IMAGE_STYLE_ID, reasons


def _select_thumbnail_style(topic_lower: str) -> tuple[str, List[str]]:
    """Rule-based: safe topics -> clean_trust; else curiosity_gap."""
    reasons: List[str] = []
    if any(t in topic_lower for t in TOPIC_SAFE_GENERAL):
        reasons.append(REASON_TOPIC_SAFE)
        return "clean_trust", reasons
    reasons.append(REASON_DEFAULT)
    return DEFAULT_THUMBNAIL_STYLE_ID, reasons


def _select_prompt_system(audience: str, topic_lower: str) -> tuple[str, List[str]]:
    """Rule-based: senior -> hook_story_empathy; safe topic -> hook_openloop_authority; else default."""
    reasons: List[str] = []
    audience_lower = (audience or "").lower()
    if any(t in audience_lower for t in AUDIENCE_SENIOR_TAGS):
        reasons.append(REASON_SENIOR_AUDIENCE)
        return "hook_story_empathy", reasons
    if any(t in topic_lower for t in TOPIC_SAFE_GENERAL):
        reasons.append(REASON_TOPIC_SAFE)
        return "hook_openloop_authority", reasons
    reasons.append(REASON_CHANNEL_BALANCED)
    return DEFAULT_PROMPT_SYSTEM_ID, reasons


def build_style_policy(
    topic: str,
    keyword: str,
    audience: Optional[str] = None,
    channel_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a single style_policy dict (deterministic, rule-based).
    topic/keyword/audience/channel_hint drive selection; no LLM.
    """
    regs = load_style_registries()
    topic_lower = (topic or "").lower()
    aud = (audience or "").strip()
    if channel_hint:
        aud = f"{aud} {channel_hint}".strip()

    channel_id, r1 = _select_channel_style(aud, topic_lower)
    image_id, r2 = _select_image_style(topic_lower)
    thumb_id, r3 = _select_thumbnail_style(topic_lower)
    prompt_id, r4 = _select_prompt_system(aud, topic_lower)

    reason_codes: List[str] = []
    reason_codes.extend(r1)
    reason_codes.extend(r2)
    reason_codes.extend(r3)
    reason_codes.extend(r4)
    reason_codes = list(dict.fromkeys(reason_codes))

    registry_hashes = {
        "channel": _registry_hash(regs["channel_style_registry"]),
        "image": _registry_hash(regs["image_style_registry"]),
        "thumbnail": _registry_hash(regs["thumbnail_style_registry"]),
        "prompt": _registry_hash(regs["prompt_system_registry"]),
    }

    policy = {
        "style_policy_version": STYLE_POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "source_topic": topic or "",
        "source_keyword": keyword or "",
        "source_audience": audience or "",
        "channel_style_id": channel_id,
        "image_style_id": image_id,
        "thumbnail_style_id": thumb_id,
        "prompt_system_id": prompt_id,
        "selection_reason_codes": reason_codes,
        "registry_hashes": registry_hashes,
    }
    policy["policy_fingerprint"] = _policy_fingerprint(policy)
    return policy


def save_style_policy(policy: Dict[str, Any], output_path: str) -> None:
    """Write policy JSON to output_path (e.g. run_root/v8/style_policy.json)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_style_policy(policy: Dict[str, Any]) -> None:
    """
    Validate schema and that referenced ids exist in registries.
    Raises ValueError on invalid.
    """
    required = (
        "style_policy_version",
        "generated_at",
        "source_topic",
        "source_keyword",
        "source_audience",
        "channel_style_id",
        "image_style_id",
        "thumbnail_style_id",
        "prompt_system_id",
        "selection_reason_codes",
        "registry_hashes",
        "policy_fingerprint",
    )
    for k in required:
        if k not in policy:
            raise ValueError(f"style_policy missing required key: {k}")

    regs = load_style_registries()
    channel_ids = {e.get("id") for e in (regs["channel_style_registry"].get("entries") or []) if e.get("id")}
    image_ids = {e.get("id") for e in (regs["image_style_registry"].get("entries") or []) if e.get("id")}
    thumb_ids = {e.get("id") for e in (regs["thumbnail_style_registry"].get("entries") or []) if e.get("id")}
    prompt_ids = {e.get("id") for e in (regs["prompt_system_registry"].get("entries") or []) if e.get("id")}

    if policy["channel_style_id"] not in channel_ids:
        raise ValueError(f"channel_style_id not in registry: {policy['channel_style_id']}")
    if policy["image_style_id"] not in image_ids:
        raise ValueError(f"image_style_id not in registry: {policy['image_style_id']}")
    if policy["thumbnail_style_id"] not in thumb_ids:
        raise ValueError(f"thumbnail_style_id not in registry: {policy['thumbnail_style_id']}")
    if policy["prompt_system_id"] not in prompt_ids:
        raise ValueError(f"prompt_system_id not in registry: {policy['prompt_system_id']}")

    rh = policy.get("registry_hashes") or {}
    for rk in ("channel", "image", "thumbnail", "prompt"):
        if rk not in rh or not isinstance(rh[rk], str):
            raise ValueError(f"registry_hashes.{rk} missing or not string")


def ensure_style_policy_for_v8(v8_root: Path, topic: str, keyword: str, audience: str = "") -> Dict[str, Any]:
    """
    Ensure style_policy.json exists in v8_root. If missing, build with defaults and save (fallback), log warning.
    Returns the policy dict (either loaded or newly built).
    """
    policy_path = v8_root / "style_policy.json"
    if policy_path.exists():
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            validate_style_policy(policy)
            return policy
        except Exception:
            pass
    # Fallback: build default and save
    policy = build_style_policy(topic=topic, keyword=keyword, audience=audience or None)
    save_style_policy(policy, str(policy_path))
    import sys
    print("[V7.5] fallback default policy applied reason=style_policy_missing_or_invalid", file=sys.stderr)
    return policy
