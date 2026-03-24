from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@dataclass(frozen=True)
class RawKeyword:
    keyword: str
    source: str              # "youtube" | "trending" | "google_trends" | "wikipedia" | "gdelt_news"
    subtype: str             # e.g. "mostPopular", "search_viewCount", "snapshot_kr", ...
    country: str             # "KR"
    window: str              # e.g. "30d", "7d", "snapshot"
    fetched_at: str          # ISO-like string (from fixture if present else "")
    evidence_hash: str       # sha256(source|subtype|raw_ref|keyword_norm)
    raw_ref: str             # fixture filename or id


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _norm_keyword(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    return s


def _yield_strings(obj: Any) -> Iterable[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for x in obj:
            yield from _yield_strings(x)
    elif isinstance(obj, dict):
        # 흔한 키 우선
        preferred = ["keyword", "keywords", "query", "queries", "title", "titles", "name", "label", "topic", "topics", "trend", "trends"]
        for k in preferred:
            if k in obj:
                yield from _yield_strings(obj.get(k))
        # 전체 탐색(최후)
        for v in obj.values():
            yield from _yield_strings(v)


def _read_fixture_json_or_jsonl(path: Path) -> Iterable[Any]:
    if path.suffix.lower() == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    else:
        with open(path, "r", encoding="utf-8") as f:
            try:
                yield json.load(f)
            except Exception:
                return


def _collect_by_filename_hint(
    source: str,
    subtype: str,
    country: str,
    window: str,
    filename_contains_any: List[str],
) -> List[RawKeyword]:
    out: List[RawKeyword] = []
    if not FIXTURES_DIR.exists():
        return out

    paths = sorted(list(FIXTURES_DIR.glob("*.json")) + list(FIXTURES_DIR.glob("*.jsonl")))
    for p in paths:
        name = p.name.lower()
        if not any(h in name for h in filename_contains_any):
            continue

        for obj in _read_fixture_json_or_jsonl(p):
            for s in _yield_strings(obj):
                kw = _norm_keyword(s)
                if len(kw) < 3:
                    continue
                kw_norm = kw.lower()
                raw_ref = p.name
                ev = _sha256(f"{source}|{subtype}|{raw_ref}|{kw_norm}")
                out.append(
                    RawKeyword(
                        keyword=kw,
                        source=source,
                        subtype=subtype,
                        country=country,
                        window=window,
                        fetched_at="",
                        evidence_hash=ev,
                        raw_ref=raw_ref,
                    )
                )
    return out


def collect_youtube_keywords() -> List[RawKeyword]:
    # 파일명 힌트 기반 분류 (fixtures-only)
    a = _collect_by_filename_hint("youtube", "mostPopular", "KR", "snapshot", ["youtube", "mostpopular", "popular"])
    b = _collect_by_filename_hint("youtube", "search_viewCount", "KR", "30d", ["youtube", "viewcount", "search"])
    c = _collect_by_filename_hint("youtube", "search_relevance", "KR", "30d", ["youtube", "relevance", "search"])
    return a + b + c


def collect_trending_keywords() -> List[RawKeyword]:
    return _collect_by_filename_hint("trending", "snapshot_kr", "KR", "snapshot", ["trending", "snapshot", "kr"])


def collect_google_trends_keywords() -> List[RawKeyword]:
    return _collect_by_filename_hint("google_trends", "youtube_search_30d_kr", "KR", "30d", ["trends", "googletrends", "youtube", "30d", "kr"])


def collect_wikipedia_keywords() -> List[RawKeyword]:
    return _collect_by_filename_hint("wikipedia", "entity_expand", "KR", "evergreen", ["wiki", "wikipedia", "wikidata"])


def collect_gdelt_keywords() -> List[RawKeyword]:
    return _collect_by_filename_hint("gdelt_news", "kr_7d", "KR", "7d", ["gdelt", "news", "7d", "kr"])

