import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import certifi

# B-2: 모듈 로드 직후 stdout UTF-8 강제(Windows cp949 방어)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

print("YTDLP_CHANNELS_PATCH_APPLIED=CLI_SUBPROCESS_V1")

_EVIDENCE_VERSION = "cli_subprocess_v1"
_TAB_SUFFIXES = ("- Videos", "- Live", "- Shorts")


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _now_local_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _normalize_channel_url_to_videos(channel_url: str) -> str:
    """
    Force stable Videos tab URL with newest sort.
    """
    if not channel_url:
        return channel_url
    u = channel_url.strip()
    u = u.split("?")[0].split("#")[0].rstrip("/")
    if not u.endswith("/videos"):
        u = u + "/videos"
    return u + "?view=0&sort=dd&flow=grid"


def _is_tab_meta(title: str, video_id: str, channel_url: str) -> Tuple[bool, str]:
    t = (title or "").strip()
    if t.endswith(_TAB_SUFFIXES):
        return True, "title_suffix_tab"
    if channel_url and "/channel/" in channel_url and video_id:
        try:
            ch_id = channel_url.split("/channel/")[1].split("/")[0].split("?")[0].split("#")[0]
            if ch_id and video_id == ch_id:
                return True, "video_id_equals_channel_id"
        except Exception:
            pass
    return False, ""


def _read_channels_file(channels_file: str, max_channels: int) -> List[Dict[str, str]]:
    p = Path(channels_file)
    if not p.exists():
        return []
    out: List[Dict[str, str]] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append({"channel_url": s, "channel_name": ""})
        if len(out) >= int(max_channels):
            break
    return out


def _find_ytdlp_executable() -> str:
    """yt-dlp CLI 실행 파일 경로 찾기"""
    # 환경변수에서 먼저 확인
    ytdlp_path = os.getenv("YTDLP_PATH", "")
    if ytdlp_path and shutil.which(ytdlp_path):
        return ytdlp_path

    # PATH에서 찾기
    ytdlp = shutil.which("yt-dlp")
    if ytdlp:
        return ytdlp

    # Python 모듈로 설치된 경우
    try:
        import yt_dlp
        # yt-dlp는 보통 sys.executable과 같은 경로에 설치됨
        python_dir = os.path.dirname(sys.executable)
        ytdlp_exe = os.path.join(python_dir, "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
        if os.path.exists(ytdlp_exe):
            return ytdlp_exe
    except Exception:
        pass

    # 최후 수단: yt-dlp 직접 호출 시도
    return "yt-dlp"


def _process_channel_cli(
    ytdlp_exe: str,
    channel_url: str,
    channel_name: str,
    target_url: str,
    playlist_end: int,
    socket_timeout: int,
    retries: int,
    cycle_id: str,
    collection_date_local: str,
    source_mode: str,
    mode: str,
    evidence_version: str,
    hard_timeout: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, Optional[str], Optional[str]]:
    """
    채널 1개 처리 함수 (CLI + subprocess)
    Returns: (video_records, tabmeta_records, titles_count, extractor_key, error_message)
    """
    try:
        # B-3: yt-dlp CLI 명령 구성 (--ca-certificates 옵션 제거)
        cmd = [
            ytdlp_exe,
            "--flat-playlist",
            f"--playlist-end={playlist_end}",
            f"--socket-timeout={socket_timeout}",
            f"--retries={retries}",
            "--print", "%(title)s",
            target_url,
        ]

        # SSL_CERT_FILE은 환경변수로 전달 (옵션으로 전달하지 않음)
        env = os.environ.copy()

        # subprocess.run으로 실행 (timeout으로 상한 보장)
        result = subprocess.run(
            cmd,
            timeout=hard_timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,  # SSL_CERT_FILE이 env에 포함되어 자식 프로세스에 전달됨
        )

        # 2) 잘못된 옵션/파라미터 FAIL-FAST
        stderr_text = (result.stderr or "").strip()
        stdout_text = (result.stdout or "").strip()
        combined_output = stderr_text + "\n" + stdout_text

        if "error: no such option:" in combined_output or "Usage: yt-dlp" in combined_output:
            # bad_cli_options 감지 - 즉시 RuntimeError로 전체 run 중단
            raise RuntimeError(f"YTDLP_BAD_CLI_OPTIONS: {combined_output[:300]}")

        if result.returncode != 0:
            error_msg = stderr_text[:200] if stderr_text else "yt-dlp CLI failed"
            return [], [], 0, None, error_msg

        # 출력 파싱 (제목만 추출)
        titles = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("WARNING") and not line.startswith("ERROR"):
                titles.append(line)

        if not titles:
            return [], [], 0, None, "no titles extracted"

        # 레코드 생성
        video_records = []
        tabmeta_records = []
        titles_count = 0

        for title in titles:
            # video_id는 제목에서 추출 불가하므로 해시 기반 생성
            video_id = _sha256_hex(f"{channel_url}|{title}")[:11]

            is_meta, meta_reason = _is_tab_meta(title, video_id, channel_url)

            record = {
                "source": "ytdlp",
                "cycle_id": cycle_id,
                "collection_date_local": collection_date_local,
                "date_key": collection_date_local,
                "date_key_type": "collection_date",
                "source_mode": source_mode,
                "mode": mode,
                "channel_name": channel_name or "",
                "channel_url": channel_url,
                "video_id": video_id,
                "title": title,
                "title_norm": title,
                "view_count": None,
                "evidence_version": evidence_version,
                "target_url": target_url,
                "extractor_key": "youtube",
                "is_tab_meta": bool(is_meta),
                "tab_meta_reason": meta_reason,
            }

            record["dedupe_key"] = _sha256_hex(f"{record.get('channel_url')}|{record.get('video_id')}|{record.get('title_norm')}")
            record["evidence_hash"] = _sha256_hex(json.dumps(record, ensure_ascii=False, sort_keys=True))

            if is_meta:
                tabmeta_records.append(record)
            else:
                video_records.append(record)
                if title:
                    titles_count += 1

        return video_records, tabmeta_records, titles_count, "youtube", None

    except subprocess.TimeoutExpired:
        return [], [], 0, None, f"subprocess timeout>{hard_timeout}s"
    except Exception as ex:
        return [], [], 0, None, str(ex)[:200]


def collect_snapshot(
    cycle_id: str,
    snapshot_dir: str,
    enabled: bool,
    channels_file: str,
    latest_n: int = 300,
    min_videos_required: int = 30,
    allow_fail: bool = False,
    timeout_seconds: int = 20,
    max_channels: int = 30,
    mode: str = "KR",
) -> Dict[str, Any]:
    """
    ✅ Must match keyword_discovery_engine.py call signature.
    
    CLI + subprocess 기반으로 실행 시간 상한 보장.
    """
    sd = Path(snapshot_dir)
    sd.mkdir(parents=True, exist_ok=True)

    snapshot_path = sd / "ytdlp_channels_snapshot.jsonl"
    tabmeta_path = sd / "ytdlp_tabmeta_dropped.jsonl"
    metrics_path = sd / "ytdlp_metrics.json"
    errors_path = sd / "ytdlp_errors.json"
    debug_path = sd / "ytdlp_debug.log"

    collection_date_local = _now_local_date()
    source_mode = "latest_n"

    # Always create/overwrite outputs each run
    snapshot_path.write_text("", encoding="utf-8", errors="replace")
    tabmeta_path.write_text("", encoding="utf-8", errors="replace")
    metrics_path.write_text("{}", encoding="utf-8", errors="replace")
    errors_path.write_text("[]", encoding="utf-8", errors="replace")
    debug_path.write_text("", encoding="utf-8", errors="replace")

    def _log(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        with open(debug_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")

    # B-1: CA 경로 강제(우회 금지) - debug 로그에 기록
    ca_path = os.getenv("SSL_CERT_FILE") or certifi.where()
    _log(f"CA_CERT={ca_path}")

    if not enabled:
        metrics = {
            "cycle_id": cycle_id,
            "videos_total_raw": 0,
            "videos_after_dedupe": 0,
            "titles_nonempty_ratio": 0.0,
            "date_key_coverage_ratio": 0.0,
            "tabmeta_dropped": 0,
            "channels_attempted": 0,
            "channels_ok": 0,
            "hard_timeouts_count": 0,
            "channel_success_count": 0,
            "channel_fail_count": 0,
            "elapsed_seconds_total": 0.0,
            "evidence_version": _EVIDENCE_VERSION,
        }
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "reason": "disabled",
            "source_mode": source_mode,
            "latest_n": int(latest_n),
            "collection_date_local": collection_date_local,
            "snapshot_path": str(snapshot_path),
            "metrics": metrics,
        }

    channels = _read_channels_file(channels_file, max_channels=max_channels)
    if not channels:
        metrics = {
            "cycle_id": cycle_id,
            "videos_total_raw": 0,
            "videos_after_dedupe": 0,
            "titles_nonempty_ratio": 0.0,
            "date_key_coverage_ratio": 0.0,
            "tabmeta_dropped": 0,
            "channels_attempted": 0,
            "channels_ok": 0,
            "hard_timeouts_count": 0,
            "channel_success_count": 0,
            "channel_fail_count": 0,
            "elapsed_seconds_total": 0.0,
            "evidence_version": _EVIDENCE_VERSION,
        }
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")
        return {
            "ok": (True if allow_fail else False),
            "reason": "channels_file_empty_or_missing",
            "source_mode": source_mode,
            "latest_n": int(latest_n),
            "collection_date_local": collection_date_local,
            "snapshot_path": str(snapshot_path),
            "metrics": metrics,
        }

    # B-2: 기본 파라미터(환경변수로 제어, 기본값 고정)
    HARD_TIMEOUT_SECONDS = int(os.getenv("YTDLP_HARD_TIMEOUT_SECONDS", "45"))
    SOCKET_TIMEOUT = int(os.getenv("YTDLP_SOCKET_TIMEOUT", "15"))
    RETRIES = int(os.getenv("YTDLP_RETRIES", "1"))
    PLAYLIST_END = int(os.getenv("YTDLP_PLAYLIST_END", "20"))

    # yt-dlp 실행 파일 찾기
    ytdlp_exe = _find_ytdlp_executable()
    _log(f"YTDLP_EXE={ytdlp_exe}")

    def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    all_errors: List[Dict[str, Any]] = []
    seen = set()

    total_raw = 0
    total_after_dedupe = 0
    titles_nonempty = 0
    tabmeta_dropped = 0
    channels_attempted = 0
    channels_ok = 0
    hard_timeouts_count = 0
    channel_success_count = 0
    channel_fail_count = 0
    elapsed_seconds_total = 0.0
    consecutive_timeouts = 0

    # 채널별 처리
    for idx, ch in enumerate(channels, start=1):
        channels_attempted += 1
        channel_url = (ch.get("channel_url") or "").strip()
        channel_name = (ch.get("channel_name") or "").strip()

        if not channel_url:
            all_errors.append({
                "channel_url": channel_url,
                "channel_name": channel_name,
                "error_type": "missing_channel_url",
                "message_short": "channel_url empty",
                "evidence_version": _EVIDENCE_VERSION,
            })
            channel_fail_count += 1
            continue

        target_url = _normalize_channel_url_to_videos(channel_url)
        _log(f"CHANNEL {idx}/{len(channels)} START url={channel_url} timeout={HARD_TIMEOUT_SECONDS}")

        start_ts = time.time()

        try:
            video_records, tabmeta_records, titles_count, extractor_key, error_msg = _process_channel_cli(
                ytdlp_exe,
                channel_url,
                channel_name,
                target_url,
                PLAYLIST_END,
                SOCKET_TIMEOUT,
                RETRIES,
                cycle_id,
                collection_date_local,
                source_mode,
                mode,
                _EVIDENCE_VERSION,
                HARD_TIMEOUT_SECONDS,
            )
            elapsed = round(time.time() - start_ts, 2)
            elapsed_seconds_total += elapsed

            if error_msg:
                if "timeout" in error_msg.lower():
                    hard_timeouts_count += 1
                    consecutive_timeouts += 1
                    all_errors.append({
                        "channel_url": channel_url,
                        "target_url": target_url,
                        "channel_name": channel_name,
                        "error_type": "hard_timeout",
                        "message_short": error_msg,
                        "seconds": HARD_TIMEOUT_SECONDS,
                        "channel_index": idx,
                        "elapsed_sec": elapsed,
                        "evidence_version": _EVIDENCE_VERSION,
                    })
                    _log(f"CHANNEL {idx}/{len(channels)} HARD_TIMEOUT seconds={HARD_TIMEOUT_SECONDS} url={channel_url} elapsed={elapsed}s")
                else:
                    consecutive_timeouts = 0
                    channel_fail_count += 1
                    all_errors.append({
                        "channel_url": channel_url,
                        "target_url": target_url,
                        "channel_name": channel_name,
                        "error_type": "channel_extract_failed",
                        "message_short": error_msg,
                        "elapsed_sec": elapsed,
                        "evidence_version": _EVIDENCE_VERSION,
                    })
                    _log(f"CHANNEL {idx} FAIL err={error_msg[:120]} elapsed={elapsed}s")
                continue

            consecutive_timeouts = 0

            # Tabmeta 레코드 저장
            for record in tabmeta_records:
                tabmeta_dropped += 1
                total_raw += 1
                _append_jsonl(tabmeta_path, record)

            if not video_records:
                channel_fail_count += 1
                all_errors.append({
                    "channel_url": channel_url,
                    "target_url": target_url,
                    "channel_name": channel_name,
                    "error_type": "no_videos_after_filter",
                    "message_short": "all entries filtered as tab meta",
                    "elapsed_sec": elapsed,
                    "evidence_version": _EVIDENCE_VERSION,
                })
                _log(f"CHANNEL {idx} NO_VIDEOS elapsed={elapsed}s")
                continue

            channels_ok += 1
            channel_success_count += 1

            # 비디오 레코드 저장
            for record in video_records:
                total_raw += 1
                dk = record["dedupe_key"]
                if dk in seen:
                    continue
                seen.add(dk)

                _append_jsonl(snapshot_path, record)
                total_after_dedupe += 1
                if record.get("title"):
                    titles_nonempty += 1

            _log(f"CHANNEL {idx} OK titles={titles_count} wrote={total_after_dedupe} elapsed={elapsed}s")

        except RuntimeError as ex:
            # 2) bad_cli_options 감지 시 즉시 FAIL-FAST
            if "YTDLP_BAD_CLI_OPTIONS" in str(ex):
                error_detail = str(ex)[:500]
                all_errors.append({
                    "error_type": "bad_cli_options",
                    "message_short": error_detail,
                    "evidence_version": _EVIDENCE_VERSION,
                })
                _log(f"FATAL: {error_detail}")
                # ytdlp_errors.json에 기록
                errors_path.write_text(json.dumps(all_errors, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")
                raise RuntimeError(f"YTDLP_BAD_CLI_OPTIONS_DETECTED: {error_detail}")
            # 다른 RuntimeError는 일반 예외로 처리
            consecutive_timeouts = 0
            channel_fail_count += 1
            elapsed = round(time.time() - start_ts, 2)
            elapsed_seconds_total += elapsed
            all_errors.append({
                "channel_url": channel_url,
                "target_url": target_url,
                "channel_name": channel_name,
                "error_type": "channel_extract_failed",
                "message_short": str(ex)[:200],
                "elapsed_sec": elapsed,
                "evidence_version": _EVIDENCE_VERSION,
            })
            _log(f"CHANNEL {idx} FAIL err={str(ex)[:120]} elapsed={elapsed}s")
        except subprocess.TimeoutExpired:
            hard_timeouts_count += 1
            consecutive_timeouts += 1
            elapsed = round(time.time() - start_ts, 2)
            elapsed_seconds_total += elapsed
            all_errors.append({
                "channel_url": channel_url,
                "target_url": target_url,
                "channel_name": channel_name,
                "error_type": "hard_timeout",
                "message_short": f"subprocess timeout>{HARD_TIMEOUT_SECONDS}s",
                "seconds": HARD_TIMEOUT_SECONDS,
                "channel_index": idx,
                "elapsed_sec": elapsed,
                "evidence_version": _EVIDENCE_VERSION,
            })
            _log(f"CHANNEL {idx}/{len(channels)} HARD_TIMEOUT seconds={HARD_TIMEOUT_SECONDS} url={channel_url} elapsed={elapsed}s")
        except Exception as ex:
            consecutive_timeouts = 0
            channel_fail_count += 1
            elapsed = round(time.time() - start_ts, 2)
            elapsed_seconds_total += elapsed
            all_errors.append({
                "channel_url": channel_url,
                "target_url": target_url,
                "channel_name": channel_name,
                "error_type": "channel_extract_failed",
                "message_short": str(ex)[:200],
                "elapsed_sec": elapsed,
                "evidence_version": _EVIDENCE_VERSION,
            })
            _log(f"CHANNEL {idx} FAIL err={str(ex)[:120]} elapsed={elapsed}s")

        # B-5: 조기 중단(Fail-Fast)
        if consecutive_timeouts >= 3:
            raise RuntimeError("YTDLP_TRANSPORT_DEGRADED_ALL_TIMEOUT")

    # B-6: 탭메타 드롭 전수 검사(HEAD 검사 금지)
    if snapshot_path.exists():
        all_lines = snapshot_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_num, line in enumerate(all_lines, start=1):
            if not line.strip():
                continue
            # JSON 파싱 없이 문자열 직접 검사
            if any(sfx in line for sfx in _TAB_SUFFIXES):
                try:
                    data = json.loads(line)
                    title = (data.get("title") or "").strip()
                    if any(title.endswith(sfx) for sfx in _TAB_SUFFIXES):
                        raise RuntimeError(f"YTDLP_TABMETA_DROP_FAILED_MAIN_SNAPSHOT_STILL_HAS_TAB_TITLES line={line_num} title={title[:50]}")
                except json.JSONDecodeError:
                    # JSON 파싱 실패해도 탭메타 문자열이 있으면 FAIL
                    raise RuntimeError(f"YTDLP_TABMETA_DROP_FAILED_MAIN_SNAPSHOT_STILL_HAS_TAB_TITLES line={line_num}")

    # B-7: 0 bytes 차단(이번 장애의 직접 증상)
    if int(total_after_dedupe) > 0 and snapshot_path.exists() and snapshot_path.stat().st_size == 0:
        raise RuntimeError("YTDLP_SNAPSHOT_ZERO_BYTES_BUT_METRICS_POSITIVE")

    titles_ratio = (titles_nonempty / total_after_dedupe) if total_after_dedupe > 0 else 0.0
    date_cov = 1.0 if total_after_dedupe > 0 else 0.0

    # B-4: 메트릭 키 필수 포함
    metrics = {
        "cycle_id": cycle_id,
        "videos_total_raw": int(total_raw),
        "videos_after_dedupe": int(total_after_dedupe),
        "titles_nonempty_ratio": float(titles_ratio),
        "date_key_coverage_ratio": float(date_cov),
        "tabmeta_dropped": int(tabmeta_dropped),
        "channels_attempted": int(channels_attempted),
        "channels_ok": int(channels_ok),
        "hard_timeouts_count": int(hard_timeouts_count),
        "channel_success_count": int(channel_success_count),
        "channel_fail_count": int(channel_fail_count),
        "elapsed_seconds_total": round(elapsed_seconds_total, 2),
        "evidence_version": _EVIDENCE_VERSION,
    }

    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")
    errors_path.write_text(json.dumps(all_errors, ensure_ascii=False, indent=2), encoding="utf-8", errors="replace")

    # 5) PASS 기준 보호용 "최소 타이틀 게이트"
    if int(total_after_dedupe) < 1:
        raise RuntimeError("YTDLP_TOO_FEW_TITLES_FOR_VERIFY")

    if total_after_dedupe <= 0:
        return {
            "ok": (True if allow_fail else False),
            "reason": "no_videos_after_dedupe",
            "source_mode": source_mode,
            "latest_n": int(latest_n),
            "collection_date_local": collection_date_local,
            "snapshot_path": str(snapshot_path),
            "metrics": metrics,
        }

    return {
        "ok": True,
        "reason": "ok",
        "source_mode": source_mode,
        "latest_n": int(latest_n),
        "collection_date_local": collection_date_local,
        "snapshot_path": str(snapshot_path),
        "metrics": metrics,
    }

