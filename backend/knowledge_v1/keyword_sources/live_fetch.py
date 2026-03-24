from __future__ import annotations
import json
import os
import re
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import requests

from backend.knowledge_v1.keyword_sources.keyword_sources import RawKeyword, _norm_keyword
from backend.knowledge_v1.secrets import redact_text

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _utc_ts() -> str:
    # 간단 타임스탬프 (재현용)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def fetch_youtube_most_popular(*, api_key: str, region_code: str = "KR", max_results: int = 50) -> Dict:
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part":"snippet,statistics", "chart":"mostPopular", "regionCode":region_code, "maxResults":max_results, "key":api_key}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def fetch_youtube_search(*, api_key: str, query: str, order: str, region_code: str = "KR", max_results: int = 50) -> Dict:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part":"snippet", "q":query, "order":order, "regionCode":region_code, "type":"video", "maxResults":max_results, "key":api_key}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def build_keywords_from_youtube_payload(payload: Dict, *, subtype: str, country: str, window: str, raw_ref: str) -> List[RawKeyword]:
    out: List[RawKeyword] = []
    items = payload.get("items", [])
    for it in items:
        sn = it.get("snippet") or {}
        title = _norm_keyword(sn.get("title",""))
        if len(title) >= 3:
            ev = _sha256(f"youtube|{subtype}|{raw_ref}|{title.lower()}")
            out.append(RawKeyword(keyword=title, source="youtube", subtype=subtype, country=country, window=window, fetched_at=_utc_ts(), evidence_hash=ev, raw_ref=raw_ref))
    return out

def live_collect_and_snapshot(
    *,
    store_root: Path,
    cycle_id: str,
    category: str,
    youtube_api_key: Optional[str],
) -> List[RawKeyword]:
    """
    live 모드 수집 + snapshot 저장
    저장 위치: <store_root>/snapshots/<cycle_id>/
    """
    if not youtube_api_key:
        # live_fetch는 키가 없으면 수집 불가 (호출자에서 live 모드 정책으로 강제 처리)
        snap_dir = store_root / "snapshots" / cycle_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
        return []

    snap_dir = store_root / "snapshots" / cycle_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    all_kw: List[RawKeyword] = []

    # 1) YouTube (필수는 아님. 키 없으면 skip)
    if youtube_api_key:
        import datetime
        def _mask_key(u: str | None) -> str | None:
            if not u:
                return u
            sp = urlsplit(u)
            qs = parse_qsl(sp.query, keep_blank_values=True)
            qs2 = []
            for k, v in qs:
                if k.lower() == "key":
                    qs2.append((k, "***REDACTED***"))
                else:
                    qs2.append((k, v))
            new_q = urlencode(qs2)
            return urlunsplit((sp.scheme, sp.netloc, sp.path, new_q, sp.fragment))

        _KEY_RE = re.compile(r"(AIza[0-9A-Za-z\-_]{20,})")

        def _redact_any(text: str | None) -> str | None:
            if text is None:
                return None
            # 1) AIza... 토큰 형태 제거
            t = _KEY_RE.sub("AIza***REDACTED***", str(text))
            # 2) key= 파라미터 값 제거(혹시 url/text에 그대로 박힌 케이스)
            t = re.sub(r"(key=)[^&\s\"']+", r"\1***REDACTED***", t, flags=re.IGNORECASE)
            return t

        def _sanitize_error_dict(err: dict) -> dict:
            # url / text 필드를 무조건 정화
            if "url" in err:
                err["url"] = _redact_any(err.get("url"))
                # _mask_key가 있어도 한 번 더 안전망
                if err["url"]:
                    err["url"] = _mask_key(err["url"])
            if "text" in err:
                err["text"] = _redact_any(err.get("text"))
            return err

        # PATCH-11.1: 이전 실행에서 남은 youtube_error_*.json도 즉시 정화(verify가 최신 snapshot을 보기 때문)
        for _p in snap_dir.glob("youtube_error_*.json"):
            try:
                _j = json.loads(_p.read_text(encoding="utf-8"))
                _j = _sanitize_error_dict(_j)
                _p.write_text(json.dumps(_j, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        try:
            mp = fetch_youtube_most_popular(api_key=youtube_api_key, region_code="KR", max_results=50)
            mp_path = snap_dir / "youtube_mostPopular_KR.json"
            _write_json(mp_path, mp)
            mp_items = mp.get("items", [])
            if not mp_items or len(mp_items) == 0:
                err = {
                    "source": "youtube",
                    "category": category,
                    "ok": False,
                    "exc": "EmptyItems",
                    "status_code": 200,
                    "url": "https://www.googleapis.com/youtube/v3/videos?chart=mostPopular",
                    "text": "EMPTY_ITEMS: YouTube API returned 0 items. Check API enabled/quota/project.",
                    "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                }
                err = _sanitize_error_dict(err)
                err_path = snap_dir / f"youtube_error_{category}.json"
                err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
                _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
                allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
                if allow:
                    return []
                sc = err.get("status_code")
                msg = (err.get("text") or "")[:300]
                url = (err.get("url") or "")[:300]
                raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")
            all_kw += build_keywords_from_youtube_payload(mp, subtype="mostPopular", country="KR", window="snapshot", raw_ref=mp_path.name)

            # PATCH-13: search.list는 기본 OFF (YOUTUBE_SEARCH_ENABLED=1일 때만 수행)
            yt_search_enabled = (os.getenv("YOUTUBE_SEARCH_ENABLED", "") or "").strip() == "1"
            if yt_search_enabled:
                # category를 query로 사용(단순 정책)
                s1 = fetch_youtube_search(api_key=youtube_api_key, query=category, order="viewCount", region_code="KR", max_results=50)
                s1_path = snap_dir / f"youtube_search_viewCount_{category}_KR.json"
                _write_json(s1_path, s1)
                s1_items = s1.get("items", [])
                if not s1_items or len(s1_items) == 0:
                    err = {
                        "source": "youtube",
                        "category": category,
                        "ok": False,
                        "exc": "EmptyItems",
                        "status_code": 200,
                        "url": f"https://www.googleapis.com/youtube/v3/search?q={category}&order=viewCount",
                        "text": "EMPTY_ITEMS: YouTube API returned 0 items. Check API enabled/quota/project.",
                        "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                    }
                    err = _sanitize_error_dict(err)
                    err_path = snap_dir / f"youtube_error_{category}.json"
                    err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
                    _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
                    allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
                    if allow:
                        return []
                    sc = err.get("status_code")
                    msg = (err.get("text") or "")[:300]
                    url = (err.get("url") or "")[:300]
                    raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")
                all_kw += build_keywords_from_youtube_payload(s1, subtype="search_viewCount", country="KR", window="30d", raw_ref=s1_path.name)

                s2 = fetch_youtube_search(api_key=youtube_api_key, query=category, order="relevance", region_code="KR", max_results=50)
                s2_path = snap_dir / f"youtube_search_relevance_{category}_KR.json"
                _write_json(s2_path, s2)
                s2_items = s2.get("items", [])
                if not s2_items or len(s2_items) == 0:
                    err = {
                        "source": "youtube",
                        "category": category,
                        "ok": False,
                        "exc": "EmptyItems",
                        "status_code": 200,
                        "url": f"https://www.googleapis.com/youtube/v3/search?q={category}&order=relevance",
                        "text": "EMPTY_ITEMS: YouTube API returned 0 items. Check API enabled/quota/project.",
                        "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                    }
                    err = _sanitize_error_dict(err)
                    err_path = snap_dir / f"youtube_error_{category}.json"
                    err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
                    _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
                    allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
                    if allow:
                        return []
                    sc = err.get("status_code")
                    msg = (err.get("text") or "")[:300]
                    url = (err.get("url") or "")[:300]
                    raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")
                all_kw += build_keywords_from_youtube_payload(s2, subtype="search_relevance", country="KR", window="30d", raw_ref=s2_path.name)
        except requests.exceptions.HTTPError as e:
            resp = getattr(e, "response", None)
            sc = getattr(resp, "status_code", None)
            raw_text = (getattr(resp, "text", "") or "")[:1000]

            # quotaExceeded / dailyLimitExceeded 등을 강하게 감지 (키 노출 방지: redact + sanitize는 기존 함수 사용)
            lowered = raw_text.lower()
            is_quota = (sc == 403) and (
                ("quotaexceeded" in lowered) or
                ("dailylimitexceeded" in lowered) or
                ("exceeded your quota" in lowered) or
                ("quota exceeded" in lowered)
            )

            err = {
                "source": "youtube",
                "category": category,
                "error_type": "HTTPError",
                "status_code": sc,
                "url": _mask_key(getattr(resp, "url", None)),
                "text": redact_text(raw_text[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                "quota_exceeded": bool(is_quota),
            }
            err = _sanitize_error_dict(err)
            err_path = snap_dir / f"youtube_error_{category}.json"
            err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])

            # quotaExceeded면 "특수 코드"로 올려서 상위(cycle)가 자동 격리하도록 한다.
            if is_quota:
                raise RuntimeError(
                    f"YOUTUBE_QUOTA_EXCEEDED status={sc} err_file={err_path.as_posix()}"
                )

            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if allow:
                return []

            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")
        except requests.exceptions.RequestException as e:
            err = {
                "source": "youtube",
                "category": category,
                "error_type": type(e).__name__,
                "status_code": None,
                "url": _mask_key(getattr(getattr(e, "request", None), "url", None)) if hasattr(e, "request") else None,
                "text": redact_text(str(e)[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            err = _sanitize_error_dict(err)
            err_path = snap_dir / f"youtube_error_{category}.json"
            err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if allow:
                return []
            sc = err.get("status_code")
            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")
        except Exception as e:
            err = {
                "source": "youtube",
                "category": category,
                "error_type": type(e).__name__,
                "status_code": None,
                "url": None,
                "text": redact_text(str(e)[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            err = _sanitize_error_dict(err)
            err_path = snap_dir / f"youtube_error_{category}.json"
            err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", [])
            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if allow:
                return []
            sc = err.get("status_code")
            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={err_path.as_posix()}")

    # 나머지 4개 데이터셋(Trends/Wiki/GDELT/News)은 다음 PATCH-09B에서 연결 (현재는 snapshot 구조만 확정)
    # 여기서는 최소 스냅샷 디렉토리/형식/해시 규칙만 고정한다.

    # JSONL로 RawKeyword도 함께 스냅샷 저장(재현용)
    kw_rows = [asdict(rk) for rk in all_kw]
    _write_jsonl(snap_dir / f"keywords_{category}_raw.jsonl", kw_rows)

    return all_kw


def live_collect_and_snapshot_once(
    *,
    store_root: Path,
    cycle_id: str,
    youtube_api_key: Optional[str],
    categories: List[str],
) -> Dict[str, List[RawKeyword]]:
    """
    PATCH-13Q: 사이클당 1회 YouTube API 호출 + 카테고리별 결정론적 분배
    
    저장 위치: <store_root>/snapshots/<cycle_id>/
    반환: {category: [RawKeyword, ...]} 형태의 dict
    """
    snap_dir = store_root / "snapshots" / cycle_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    
    # 초기 bucket: 모든 카테고리에 대해 빈 리스트
    buckets = {c: [] for c in categories}
    
    if not youtube_api_key:
        # 키가 없으면 빈 bucket 반환
        _write_jsonl(snap_dir / "keywords___global___raw.jsonl", [])
        return buckets
    
    global_youtube_keywords: List[RawKeyword] = []
    
    # YouTube API 호출 (1회 세트만)
    if youtube_api_key:
        import datetime
        import hashlib
        def _mask_key(u: str | None) -> str | None:
            if not u:
                return u
            sp = urlsplit(u)
            qs = parse_qsl(sp.query, keep_blank_values=True)
            qs2 = []
            for k, v in qs:
                if k.lower() == "key":
                    qs2.append((k, "***REDACTED***"))
                else:
                    qs2.append((k, v))
            new_q = urlencode(qs2)
            return urlunsplit((sp.scheme, sp.netloc, sp.path, new_q, sp.fragment))

        _KEY_RE = re.compile(r"(AIza[0-9A-Za-z\-_]{20,})")

        def _redact_any(text: str | None) -> str | None:
            if text is None:
                return None
            t = _KEY_RE.sub("AIza***REDACTED***", str(text))
            t = re.sub(r"(key=)[^&\s\"']+", r"\1***REDACTED***", t, flags=re.IGNORECASE)
            return t

        def _sanitize_error_dict(err: dict) -> dict:
            if "url" in err:
                err["url"] = _redact_any(err.get("url"))
                if err["url"]:
                    err["url"] = _mask_key(err["url"])
            if "text" in err:
                err["text"] = _redact_any(err.get("text"))
            return err

        # 이전 실행에서 남은 youtube_error___global__.json 정화
        global_err_path = snap_dir / "youtube_error___global__.json"
        if global_err_path.exists():
            try:
                _j = json.loads(global_err_path.read_text(encoding="utf-8"))
                _j = _sanitize_error_dict(_j)
                global_err_path.write_text(json.dumps(_j, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        try:
            # 1) mostPopular 호출 (항상 수행)
            mp = fetch_youtube_most_popular(api_key=youtube_api_key, region_code="KR", max_results=50)
            mp_path = snap_dir / "youtube_mostPopular___global___KR.json"
            _write_json(mp_path, mp)
            mp_items = mp.get("items", [])
            if not mp_items or len(mp_items) == 0:
                err = {
                    "source": "youtube",
                    "category": "__global__",
                    "ok": False,
                    "exc": "EmptyItems",
                    "status_code": 200,
                    "url": "https://www.googleapis.com/youtube/v3/videos?chart=mostPopular",
                    "text": "EMPTY_ITEMS: YouTube API returned 0 items. Check API enabled/quota/project.",
                    "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                }
                err = _sanitize_error_dict(err)
                global_err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
                _write_jsonl(snap_dir / "keywords___global___raw.jsonl", [])
                # EmptyItems는 빈 bucket 반환 (파이프라인 무중단)
                return buckets
            global_youtube_keywords += build_keywords_from_youtube_payload(mp, subtype="mostPopular", country="KR", window="snapshot", raw_ref=mp_path.name)

            # 2) search.list 호출 (YOUTUBE_SEARCH_ENABLED=1일 때만)
            yt_search_enabled = (os.getenv("YOUTUBE_SEARCH_ENABLED", "") or "").strip() == "1"
            if yt_search_enabled:
                # search는 category 없이 "trending" 같은 일반 쿼리로 호출
                search_query = "trending"
                s1 = fetch_youtube_search(api_key=youtube_api_key, query=search_query, order="viewCount", region_code="KR", max_results=50)
                s1_path = snap_dir / "youtube_search_viewCount___global___KR.json"
                _write_json(s1_path, s1)
                s1_items = s1.get("items", [])
                if s1_items and len(s1_items) > 0:
                    global_youtube_keywords += build_keywords_from_youtube_payload(s1, subtype="search_viewCount", country="KR", window="30d", raw_ref=s1_path.name)

                s2 = fetch_youtube_search(api_key=youtube_api_key, query=search_query, order="relevance", region_code="KR", max_results=50)
                s2_path = snap_dir / "youtube_search_relevance___global___KR.json"
                _write_json(s2_path, s2)
                s2_items = s2.get("items", [])
                if s2_items and len(s2_items) > 0:
                    global_youtube_keywords += build_keywords_from_youtube_payload(s2, subtype="search_relevance", country="KR", window="30d", raw_ref=s2_path.name)

        except requests.exceptions.HTTPError as e:
            resp = getattr(e, "response", None)
            sc = getattr(resp, "status_code", None)
            raw_text = (getattr(resp, "text", "") or "")[:1000]

            # PATCH-13Q.1: 400 expired, 403 quota 감지 (파이프라인 무중단)
            lowered = raw_text.lower()
            is_key_expired = (sc == 400) and ("api key expired" in lowered)
            is_quota = (sc == 403) and (
                ("quotaexceeded" in lowered) or
                ("dailylimitexceeded" in lowered) or
                ("exceeded your quota" in lowered) or
                ("quota exceeded" in lowered)
            )

            err = {
                "source": "youtube",
                "category": "__global__",
                "error_type": "HTTPError",
                "status_code": sc,
                "url": _mask_key(getattr(resp, "url", None)),
                "text": redact_text(raw_text[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
                "quota_exceeded": bool(is_quota),
            }
            err = _sanitize_error_dict(err)
            global_err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / "keywords___global___raw.jsonl", [])

            # keyExpired 또는 quotaExceeded 처리
            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            require_ok = (os.getenv("REQUIRE_YOUTUBE_OK", "") or "").strip() == "1"
            
            if is_key_expired or is_quota:
                # REQUIRE_YOUTUBE_OK=1이면 keyExpired/quota 시 즉시 FAIL
                if require_ok:
                    reason = "keyExpired" if is_key_expired else "quotaExceeded"
                    raise RuntimeError(
                        f"YOUTUBE_API_KEY_{reason.upper()}: "
                        f"REQUIRE_YOUTUBE_OK=1이 설정되어 있어 키 오류 시 즉시 실패합니다. "
                        f"status={sc} err_file={global_err_path.as_posix()}"
                    )
                # 기본값은 무중단 유지 (빈 bucket 반환)
                return buckets

            # 그 외 HTTPError는 기존 정책 (ALLOW_YOUTUBE_FAIL=1이면 빈 bucket 반환)
            if allow:
                return buckets

            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={global_err_path.as_posix()}")
        except requests.exceptions.RequestException as e:
            err = {
                "source": "youtube",
                "category": "__global__",
                "error_type": type(e).__name__,
                "status_code": None,
                "url": _mask_key(getattr(getattr(e, "request", None), "url", None)) if hasattr(e, "request") else None,
                "text": redact_text(str(e)[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            err = _sanitize_error_dict(err)
            global_err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / "keywords___global___raw.jsonl", [])
            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if allow:
                return buckets
            sc = err.get("status_code")
            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={global_err_path.as_posix()}")
        except Exception as e:
            err = {
                "source": "youtube",
                "category": "__global__",
                "error_type": type(e).__name__,
                "status_code": None,
                "url": None,
                "text": redact_text(str(e)[:500]),
                "occurred_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            err = _sanitize_error_dict(err)
            global_err_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_jsonl(snap_dir / "keywords___global___raw.jsonl", [])
            allow = (os.getenv("ALLOW_YOUTUBE_FAIL", "") or "").strip() == "1"
            if allow:
                return buckets
            sc = err.get("status_code")
            msg = (err.get("text") or "")[:300]
            url = (err.get("url") or "")[:300]
            raise RuntimeError(f"YOUTUBE_LIVE_FETCH_FAILED status={sc} msg={msg} url={url} err_file={global_err_path.as_posix()}")

    # 결정론적 분배: global_youtube_keywords를 categories에 분배
    if global_youtube_keywords and categories:
        for rk in global_youtube_keywords:
            kw_lower = rk.keyword.lower()
            hash_bytes = hashlib.sha256(kw_lower.encode("utf-8")).hexdigest()
            bucket_idx = int(hash_bytes[:8], 16) % len(categories)
            target_category = categories[bucket_idx]
            buckets[target_category].append(rk)

    # global raw keywords를 jsonl로 저장
    kw_rows = [asdict(rk) for rk in global_youtube_keywords]
    _write_jsonl(snap_dir / "keywords___global___raw.jsonl", kw_rows)

    return buckets

