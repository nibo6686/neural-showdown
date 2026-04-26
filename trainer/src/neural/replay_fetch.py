import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .logging_helper import print_line_safe


SEARCH_ENDPOINT = "https://replay.pokemonshowdown.com/search.json"
REPLAY_BASE_URL = "https://replay.pokemonshowdown.com"
DEFAULT_FORMAT = "gen9randombattle"
DEFAULT_DELAY_SEC = 0.5
DEFAULT_MAX_REPLAYS = 1000
DEFAULT_FAILURES_PATH = Path("artifacts/replays/fetch_failures.jsonl")
DEFAULT_REPORT_PATH = Path("artifacts/replays/fetch_report.json")
USER_AGENT = "NeuralShowdownReplayIngest/0.1 public-replay-research"
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass
class HttpResult:
    ok: bool
    status_code: int
    body: bytes
    error: Optional[str] = None
    url: str = ""


class RateLimiter:
    def __init__(self, delay_sec: float = DEFAULT_DELAY_SEC) -> None:
        self.delay_sec = max(0.0, float(delay_sec))
        self._last_request_at = 0.0

    def wait(self) -> None:
        if self.delay_sec <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if self._last_request_at > 0 and elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)
        self._last_request_at = time.monotonic()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_search_url(format_name: str, before: Optional[Any] = None, base_endpoint: str = SEARCH_ENDPOINT) -> str:
    params: Dict[str, str] = {"format": str(format_name)}
    if before not in (None, ""):
        params["before"] = str(before)
    return f"{base_endpoint}?{urllib.parse.urlencode(params)}"


def sanitize_replay_id(replay_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", replay_id).strip("._") or "unknown_replay"


def _strip_known_suffix(value: str) -> str:
    for suffix in (".json", ".log"):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _replay_id_from_url(value: str) -> Optional[str]:
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    tail = parsed.path.rstrip("/").split("/")[-1]
    return _strip_known_suffix(tail) if tail else None


def replay_id_from_entry(entry: Dict[str, Any]) -> str:
    for key in ("id", "replay_id", "replayid", "battleid"):
        value = entry.get(key)
        if value:
            return str(value)
    for key in ("url", "href", "source_url"):
        value = entry.get(key)
        replay_id = _replay_id_from_url(str(value)) if value else None
        if replay_id:
            return replay_id
    raise ValueError(f"Replay search entry does not include an id: {entry}")


def upload_time_from_entry(entry: Dict[str, Any]) -> Optional[Any]:
    for key in ("uploadtime", "upload_time", "uploaded", "timestamp"):
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def _players_from_entry(entry: Dict[str, Any]) -> Dict[str, Optional[str]]:
    players = entry.get("players")
    if isinstance(players, dict):
        return {"p1": players.get("p1"), "p2": players.get("p2")}
    if isinstance(players, list):
        return {
            "p1": str(players[0]) if len(players) > 0 and players[0] is not None else None,
            "p2": str(players[1]) if len(players) > 1 and players[1] is not None else None,
        }
    return {
        "p1": entry.get("p1") or entry.get("p1_name") or entry.get("player1"),
        "p2": entry.get("p2") or entry.get("p2_name") or entry.get("player2"),
    }


def _rating_from_entry(entry: Dict[str, Any]) -> Optional[Any]:
    for key in ("rating", "elo", "p1rating", "p2rating"):
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def metadata_from_search_entry(entry: Dict[str, Any], format_name: str) -> Dict[str, Any]:
    replay_id = replay_id_from_entry(entry)
    entry_format = entry.get("format") or entry.get("formatid") or format_name
    return {
        "replay_id": replay_id,
        "format": str(entry_format),
        "upload_time": upload_time_from_entry(entry),
        "players": _players_from_entry(entry),
        "rating": _rating_from_entry(entry),
        "source_url": f"{REPLAY_BASE_URL}/{urllib.parse.quote(replay_id, safe='-_.~')}",
        "search_metadata": entry,
    }


def _http_get(
    url: str,
    *,
    timeout_sec: float = 30.0,
    retries: int = 3,
    retry_delay_sec: float = 1.0,
    rate_limiter: Optional[RateLimiter] = None,
) -> HttpResult:
    attempts = max(1, int(retries))
    last_error: Optional[str] = None
    for attempt in range(1, attempts + 1):
        if rate_limiter:
            rate_limiter.wait()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                status_code = int(getattr(response, "status", response.getcode()))
                return HttpResult(True, status_code, response.read(), url=url)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code in RETRYABLE_STATUS_CODES and attempt < attempts:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                sleep_sec = _retry_after_seconds(retry_after, retry_delay_sec, attempt)
                time.sleep(sleep_sec)
                continue
            return HttpResult(False, int(exc.code), body, last_error, url=url)
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = str(exc)
            if attempt < attempts:
                time.sleep(retry_delay_sec * attempt)
                continue
            return HttpResult(False, 0, b"", last_error, url=url)
    return HttpResult(False, 0, b"", last_error or "request failed", url=url)


def _retry_after_seconds(value: Optional[str], fallback: float, attempt: int) -> float:
    if not value:
        return fallback * attempt
    try:
        return max(0.0, float(value))
    except ValueError:
        return fallback * attempt


def _decode_json(body: bytes, *, url: str) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not decode JSON response from {url}: {exc}") from exc


def _extract_search_entries(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("results", "replays", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    raise ValueError("Replay search response did not contain a list of replay metadata.")


def query_replay_search(
    format_name: str,
    *,
    before: Optional[Any] = None,
    base_endpoint: str = SEARCH_ENDPOINT,
    rate_limiter: Optional[RateLimiter] = None,
    retries: int = 3,
    timeout_sec: float = 30.0,
) -> List[Dict[str, Any]]:
    url = build_search_url(format_name, before=before, base_endpoint=base_endpoint)
    result = _http_get(url, retries=retries, timeout_sec=timeout_sec, rate_limiter=rate_limiter)
    if not result.ok:
        raise RuntimeError(f"Replay search failed for {url}: {result.error}")
    return _extract_search_entries(_decode_json(result.body, url=url))


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def known_downloaded_ids(out_dir: Path) -> Set[str]:
    known: Set[str] = set()
    metadata_path = out_dir / "metadata.jsonl"
    for record in _read_jsonl(metadata_path):
        replay_id = record.get("replay_id") or record.get("id")
        if replay_id:
            known.add(str(replay_id))
    if out_dir.exists():
        for pattern in ("*.log", "*.json"):
            for path in out_dir.glob(pattern):
                if path.name == "metadata.jsonl":
                    continue
                known.add(path.stem)
    return known


def is_replay_downloaded(replay_id: str, out_dir: Path, known_ids: Optional[Set[str]] = None) -> bool:
    if known_ids is not None and replay_id in known_ids:
        return True
    safe_id = sanitize_replay_id(replay_id)
    return (out_dir / f"{safe_id}.log").exists() or (out_dir / f"{safe_id}.json").exists()


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _replay_asset_urls(replay_id: str, base_url: str = REPLAY_BASE_URL) -> Tuple[str, str]:
    quoted = urllib.parse.quote(replay_id, safe="-_.~")
    return f"{base_url}/{quoted}.json", f"{base_url}/{quoted}.log"


def _embedded_log_from_json(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("log", "inputlog"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
    return None


def _merge_json_metadata(metadata: Dict[str, Any], payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return metadata
    merged = dict(metadata)
    merged["replay_id"] = str(payload.get("id") or merged["replay_id"])
    merged["format"] = str(payload.get("format") or payload.get("formatid") or merged["format"])
    merged["upload_time"] = payload.get("uploadtime", merged.get("upload_time"))
    merged["players"] = _players_from_entry({**payload, "players": payload.get("players")})
    merged["rating"] = _rating_from_entry(payload) or merged.get("rating")
    return merged


def download_replay_assets(
    metadata: Dict[str, Any],
    out_dir: Path,
    *,
    rate_limiter: Optional[RateLimiter] = None,
    retries: int = 3,
    timeout_sec: float = 30.0,
    replay_base_url: str = REPLAY_BASE_URL,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    replay_id = str(metadata["replay_id"])
    safe_id = sanitize_replay_id(replay_id)
    json_path = out_dir / f"{safe_id}.json"
    log_path = out_dir / f"{safe_id}.log"
    json_url, log_url = _replay_asset_urls(replay_id, replay_base_url)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_available = False
    log_available = False
    json_payload: Any = None
    errors: List[str] = []

    json_result = _http_get(json_url, retries=retries, timeout_sec=timeout_sec, rate_limiter=rate_limiter)
    if json_result.ok:
        json_available = True
        json_path.write_bytes(json_result.body)
        try:
            json_payload = _decode_json(json_result.body, url=json_url)
            metadata = _merge_json_metadata(metadata, json_payload)
        except ValueError as exc:
            errors.append(str(exc))
    elif json_result.status_code != 404:
        errors.append(f"json download failed: {json_result.error or json_result.status_code}")

    log_result = _http_get(log_url, retries=retries, timeout_sec=timeout_sec, rate_limiter=rate_limiter)
    if log_result.ok:
        log_available = True
        log_path.write_bytes(log_result.body)
    elif log_result.status_code != 404:
        errors.append(f"log download failed: {log_result.error or log_result.status_code}")

    if not log_available:
        embedded_log = _embedded_log_from_json(json_payload)
        if embedded_log:
            log_path.write_text(embedded_log.rstrip("\n") + "\n", encoding="utf-8")
            log_available = True

    if not json_available and not log_available:
        reason = "; ".join(errors) if errors else "neither JSON nor log endpoint returned public data"
        return None, reason

    downloaded_at = utc_now_iso()
    record = {
        **metadata,
        "source_url": metadata.get("source_url") or f"{REPLAY_BASE_URL}/{urllib.parse.quote(replay_id, safe='-_.~')}",
        "json_url": json_url,
        "log_url": log_url,
        "downloaded_at": downloaded_at,
        "json_available": bool(json_available),
        "log_available": bool(log_available),
        "json_path": str(json_path) if json_available else None,
        "log_path": str(log_path) if log_available else None,
        "file_paths": {
            "json": str(json_path) if json_available else None,
            "log": str(log_path) if log_available else None,
        },
        "warnings": errors,
    }
    return record, None


def fetch_public_replays(
    *,
    format_name: str = DEFAULT_FORMAT,
    max_replays: int = DEFAULT_MAX_REPLAYS,
    out_dir: Optional[Path] = None,
    delay_sec: float = DEFAULT_DELAY_SEC,
    failures_path: Path = DEFAULT_FAILURES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    search_endpoint: str = SEARCH_ENDPOINT,
    replay_base_url: str = REPLAY_BASE_URL,
    retries: int = 3,
    timeout_sec: float = 30.0,
    progress_interval: int = 50,
    checkpoint_interval: int = 100,
) -> Dict[str, Any]:
    selected_out_dir = out_dir or Path("data/replays/raw") / format_name
    selected_out_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = selected_out_dir / "metadata.jsonl"
    failures_path.parent.mkdir(parents=True, exist_ok=True)
    if not failures_path.exists():
        failures_path.write_text("", encoding="utf-8")
    rate_limiter = RateLimiter(delay_sec)
    downloaded_ids = known_downloaded_ids(selected_out_dir)
    failures: List[Dict[str, Any]] = []
    reason_counts: Dict[str, int] = {}
    fetched = 0
    downloaded = 0
    skipped = 0
    before: Optional[Any] = None
    seen_cursors: Set[str] = set()
    started_at = time.perf_counter()
    last_progress_at = started_at

    while fetched < max(0, int(max_replays)):
        cursor_key = "" if before in (None, "") else str(before)
        if cursor_key in seen_cursors:
            break
        seen_cursors.add(cursor_key)
        try:
            entries = query_replay_search(
                format_name,
                before=before,
                base_endpoint=search_endpoint,
                rate_limiter=rate_limiter,
                retries=retries,
                timeout_sec=timeout_sec,
            )
        except Exception as exc:
            failure = {
                "format": format_name,
                "before": before,
                "stage": "search",
                "reason": str(exc),
                "timestamp": utc_now_iso(),
            }
            failures.append(failure)
            _append_jsonl(failures_path, failure)
            reason_counts["search_failed"] = reason_counts.get("search_failed", 0) + 1
            break

        if not entries:
            break

        has_more = len(entries) > 50
        page_entries = entries[:50] if has_more else entries
        remaining = max(0, int(max_replays) - fetched)
        page_entries = page_entries[:remaining]

        for entry in page_entries:
            fetched += 1
            try:
                metadata = metadata_from_search_entry(entry, format_name)
                replay_id = str(metadata["replay_id"])
                if is_replay_downloaded(replay_id, selected_out_dir, downloaded_ids):
                    skipped += 1
                    reason_counts["already_downloaded"] = reason_counts.get("already_downloaded", 0) + 1
                    continue
                record, error = download_replay_assets(
                    metadata,
                    selected_out_dir,
                    rate_limiter=rate_limiter,
                    retries=retries,
                    timeout_sec=timeout_sec,
                    replay_base_url=replay_base_url,
                )
                if record is None:
                    failure = {
                        "replay_id": replay_id,
                        "format": format_name,
                        "source_url": metadata.get("source_url"),
                        "stage": "download",
                        "reason": error or "download failed",
                        "timestamp": utc_now_iso(),
                    }
                    failures.append(failure)
                    _append_jsonl(failures_path, failure)
                    reason_counts["download_failed"] = reason_counts.get("download_failed", 0) + 1
                    continue
                _append_jsonl(metadata_path, record)
                downloaded_ids.add(replay_id)
                downloaded_ids.add(sanitize_replay_id(replay_id))
                downloaded += 1
            except Exception as exc:
                replay_id = None
                try:
                    replay_id = replay_id_from_entry(entry)
                except Exception:
                    pass
                failure = {
                    "replay_id": replay_id,
                    "format": format_name,
                    "stage": "download",
                    "reason": str(exc),
                    "timestamp": utc_now_iso(),
                }
                failures.append(failure)
                _append_jsonl(failures_path, failure)
                reason_counts["exception"] = reason_counts.get("exception", 0) + 1

            # Progress reporting: print every progress_interval replays
            if fetched % progress_interval == 0:
                elapsed = time.perf_counter() - started_at
                avg_per_sec = downloaded / elapsed if elapsed > 0 else 0
                remaining_target = max(0, int(max_replays) - fetched)
                eta_sec = remaining_target / avg_per_sec if avg_per_sec > 0 else 0
                print_line_safe(
                    f"fetch-replays | format={format_name} fetched={fetched}/{max_replays} "
                    f"downloaded={downloaded} skipped={skipped} failed={len(failures)} "
                    f"rate={avg_per_sec:.1f}/sec eta={int(eta_sec)}s"
                )
                last_progress_at = time.perf_counter()

            # Batch checkpoint: write intermediate metadata every checkpoint_interval replays
            if downloaded > 0 and downloaded % checkpoint_interval == 0:
                checkpoint_metadata = {
                    "format": format_name,
                    "checkpoint_at_downloaded": downloaded,
                    "checkpoint_at_fetched": fetched,
                    "checkpoint_timestamp": utc_now_iso(),
                }
                _append_jsonl(metadata_path.parent / "checkpoint.jsonl", checkpoint_metadata)

        # Page-level progress
        print_line_safe(
            f"fetch-replays | format={format_name} fetched={fetched} downloaded={downloaded} "
            f"skipped={skipped} failed={len(failures)}"
        )

        if not has_more or fetched >= int(max_replays) or not page_entries:
            break
        next_before = upload_time_from_entry(page_entries[-1])
        if next_before in (None, before):
            break
        before = next_before

    wall_time = time.perf_counter() - started_at
    report = {
        "format": format_name,
        "max_replays": int(max_replays),
        "out_dir": str(selected_out_dir),
        "metadata_path": str(metadata_path),
        "failures_path": str(failures_path),
        "search_endpoint": search_endpoint,
        "replay_base_url": replay_base_url,
        "delay_sec": float(delay_sec),
        "fetched": int(fetched),
        "downloaded": int(downloaded),
        "skipped": int(skipped),
        "failed": int(len(failures)),
        "failure_reasons": reason_counts,
        "wall_time_sec": wall_time,
        "timestamp": utc_now_iso(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_line_safe(
        f"fetch-replays done | format={format_name} fetched={fetched} downloaded={downloaded} "
        f"skipped={skipped} failed={len(failures)} wall_time={int(wall_time)}s report={report_path}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public saved Pokemon Showdown replays with caching and rate limiting.")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Pokemon Showdown format id to search.")
    parser.add_argument("--max-replays", type=int, default=DEFAULT_MAX_REPLAYS, help="Maximum search results to process.")
    parser.add_argument("--out-dir", default=None, help="Raw replay output directory.")
    parser.add_argument("--delay-sec", type=float, default=DEFAULT_DELAY_SEC, help="Minimum delay between HTTP requests.")
    parser.add_argument("--failures", default=str(DEFAULT_FAILURES_PATH), help="JSONL path for failed replay ids.")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_PATH), help="Fetch report JSON path.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path("data/replays/raw") / args.format
    fetch_public_replays(
        format_name=args.format,
        max_replays=args.max_replays,
        out_dir=out_dir,
        delay_sec=args.delay_sec,
        failures_path=Path(args.failures),
        report_path=Path(args.report_json),
    )


if __name__ == "__main__":
    main()
