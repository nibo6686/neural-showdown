import argparse
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .logging_helper import print_line_safe


PROFILE_VERSION = "replay-pool-profile-v1"
DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_CATALOG_PATH = Path("artifacts/training_plan/replay_catalog.jsonl")
DEFAULT_SUMMARY_PATH = Path("artifacts/training_plan/replay_pool_summary.md")

MECHANIC_FLAGS = (
    "tera",
    "boosts_drops",
    "major_status",
    "item_reveal_loss",
    "ability_reveal_change_suppression",
    "type_change",
    "transform",
    "illusion",
    "weather",
    "terrain",
    "screens",
    "tailwind",
    "hazards",
    "recharge_lock_constraints",
    "encore",
    "disable",
    "taunt",
    "choice_like_constraints",
)

RARE_FLAGS = (
    "transform",
    "illusion",
    "type_change",
    "ability_reveal_change_suppression",
    "tailwind",
    "recharge_lock_constraints",
    "encore",
    "disable",
)

_BOOST_COMMANDS = {
    "-boost", "-unboost", "-setboost", "-swapboost", "-invertboost",
    "-copyboost", "-clearboost", "-clearallboost", "-clearpositiveboost",
    "-clearnegativeboost",
}
_SCREEN_EFFECTS = {"reflect", "lightscreen", "auroraveil"}
_HAZARD_EFFECTS = {"spikes", "toxicspikes", "stealthrock", "stickyweb"}
_TERRAIN_EFFECTS = {
    "electricterrain", "grassyterrain", "mistyterrain", "psychicterrain",
}
_LOCK_EFFECTS = {
    "mustrecharge", "recharge", "twoturnmove", "uproar", "rollout",
    "outrage", "petaldance", "thrash", "bide",
}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _metadata_by_id(replay_dir: Path) -> Tuple[Dict[str, Dict[str, Any]], int]:
    path = replay_dir / "metadata.jsonl"
    records: Dict[str, Dict[str, Any]] = {}
    invalid = 0
    if not path.exists():
        return records, invalid
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            replay_id = record.get("replay_id") if isinstance(record, dict) else None
            if replay_id:
                records[str(replay_id)] = record
    return records, invalid


def _safe_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalize_format(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    normalized = re.sub(r"[^a-z0-9]+", "", str(value).lower())
    if normalized == "gen9randombattle":
        return "gen9randombattle"
    return normalized or None


def _upload_iso(value: Any) -> Optional[str]:
    number = _safe_number(value)
    if number is None or number <= 0:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def _effect_id(text: str) -> str:
    value = str(text).lower()
    value = re.sub(r"\[.*?\]", " ", value)
    value = value.replace("move:", " ").replace("ability:", " ").replace("item:", " ")
    return re.sub(r"[^a-z0-9]+", "", value)


def _player_ratings(inputlog: str) -> Dict[str, Optional[float]]:
    ratings: Dict[str, Optional[float]] = {"p1": None, "p2": None}
    for line in inputlog.splitlines():
        match = re.match(r"^>player (p[12]) (.+)$", line.strip())
        if not match:
            continue
        try:
            payload = json.loads(match.group(2))
        except json.JSONDecodeError:
            continue
        rating = _safe_number(payload.get("rating")) if isinstance(payload, dict) else None
        ratings[match.group(1)] = rating if rating and rating > 0 else None
    return ratings


def _decision_count(inputlog: str, command_counts: Counter) -> int:
    count = 0
    for line in inputlog.splitlines():
        match = re.match(r"^>(p[12])\s+(\S+)", line.strip())
        if not match:
            continue
        command = match.group(2).lower()
        if command in {"move", "switch", "team", "pass", "default"}:
            count += 1
            command_counts[f"input:{command}"] += 1
    return count


def extract_replay_profile(
    log_text: str,
    *,
    replay_id: str,
    path: Path,
    metadata: Optional[Dict[str, Any]] = None,
    replay_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = metadata or {}
    replay_json = replay_json or {}
    command_counts: Counter = Counter()
    flags = {name: False for name in MECHANIC_FLAGS}
    players: Dict[str, Optional[str]] = {"p1": None, "p2": None}
    winner: Optional[str] = None
    total_turns = 0
    public_actions = 0
    faint_counts: Counter = Counter()
    revealed: Dict[str, set] = {"p1": set(), "p2": set()}
    team_sizes: Dict[str, int] = {}
    warnings: List[str] = []
    timer_or_forfeit_evidence = False

    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        command = parts[1].lower() if len(parts) > 1 else ""
        if not command:
            continue
        command_counts[command] += 1
        lower = line.lower()
        effect = _effect_id("|".join(parts[2:]))

        if command == "player" and len(parts) >= 4 and parts[2] in players and parts[3]:
            players[parts[2]] = parts[3]
        elif command == "teamsize" and len(parts) >= 4 and parts[2] in ("p1", "p2"):
            try:
                team_sizes[parts[2]] = int(parts[3])
            except ValueError:
                warnings.append(f"invalid team size: {parts[2]}={parts[3]}")
        elif command == "turn" and len(parts) >= 3:
            try:
                total_turns = max(total_turns, int(parts[2]))
            except ValueError:
                warnings.append(f"invalid turn: {parts[2]}")
        elif command == "win" and len(parts) >= 3:
            winner = parts[2]
        elif command == "tie":
            winner = "tie"
        elif command in {"move", "switch", "drag"}:
            public_actions += 1
        if command in {"switch", "drag", "replace"} and len(parts) >= 4:
            side_match = re.match(r"^(p[12])", parts[2])
            if side_match:
                species = parts[3].split(",")[0].strip().lower()
                if species:
                    revealed[side_match.group(1)].add(species)
        if command == "faint" and len(parts) >= 3:
            side_match = re.match(r"^(p[12])", parts[2])
            if side_match:
                faint_counts[side_match.group(1)] += 1

        if command == "-terastallize":
            flags["tera"] = True
        if command in _BOOST_COMMANDS:
            flags["boosts_drops"] = True
        if command in {"-status", "-curestatus", "-cureteam"}:
            flags["major_status"] = True
        if command in {"-item", "-enditem"}:
            flags["item_reveal_loss"] = True
        if command in {"-ability", "-endability"} or "neutralizinggas" in effect:
            flags["ability_reveal_change_suppression"] = True
        if command in {"-transform"}:
            flags["transform"] = True
        if command == "replace" or (
            command in {"-start", "-end", "-ability", "-endability", "switch"}
            and "illusion" in effect
        ):
            flags["illusion"] = True
        if command in {"-start", "-end"} and ("typechange" in effect or "typeadd" in effect):
            flags["type_change"] = True
        if command == "-weather" and len(parts) >= 3 and parts[2].lower() != "none":
            flags["weather"] = True
        if command in {"-fieldstart", "-fieldend"} and any(name in effect for name in _TERRAIN_EFFECTS):
            flags["terrain"] = True
        if command in {"-sidestart", "-sideend"}:
            if any(name in effect for name in _SCREEN_EFFECTS):
                flags["screens"] = True
            if "tailwind" in effect:
                flags["tailwind"] = True
            if any(name in effect for name in _HAZARD_EFFECTS):
                flags["hazards"] = True
        if command in {"-mustrecharge", "-prepare"}:
            flags["recharge_lock_constraints"] = True
        if command in {"-start", "-end", "cant"}:
            if any(name in effect for name in _LOCK_EFFECTS):
                flags["recharge_lock_constraints"] = True
            if "encore" in effect:
                flags["encore"] = True
            if "disable" in effect:
                flags["disable"] = True
            if "taunt" in effect:
                flags["taunt"] = True
            if "choice" in effect:
                flags["choice_like_constraints"] = True
        if command == "inactive" and any(token in lower for token in ("forfeit", "lost due to inactivity")):
            timer_or_forfeit_evidence = True

    json_players = replay_json.get("players")
    metadata_players = metadata.get("players")
    if isinstance(json_players, list):
        players["p1"] = players["p1"] or (str(json_players[0]) if len(json_players) > 0 else None)
        players["p2"] = players["p2"] or (str(json_players[1]) if len(json_players) > 1 else None)
    if isinstance(metadata_players, dict):
        players["p1"] = players["p1"] or metadata_players.get("p1")
        players["p2"] = players["p2"] or metadata_players.get("p2")

    inputlog_value = replay_json.get("inputlog")
    inputlog = inputlog_value if isinstance(inputlog_value, str) else ""
    decisions = _decision_count(inputlog, command_counts) if inputlog else public_actions
    decision_source = "inputlog" if inputlog else "public_move_switch_actions"
    ratings = _player_ratings(inputlog)
    rating = _safe_number(metadata.get("rating"))
    if rating is None:
        rating = _safe_number(replay_json.get("rating"))
    if rating is None:
        available_player_ratings = [value for value in ratings.values() if value is not None]
        rating = sum(available_player_ratings) / len(available_player_ratings) if available_player_ratings else None

    format_value = (
        metadata.get("format") or replay_json.get("formatid") or replay_json.get("format")
    )
    loser_side = None
    if winner and winner != "tie":
        for side, name in players.items():
            if name and str(name).strip().lower() != str(winner).strip().lower():
                loser_side = side
    short_or_forfeit = (
        total_turns < 5
        or winner is None
        or timer_or_forfeit_evidence
        or (loser_side is not None and faint_counts[loser_side] < 5)
    )
    close_game = (
        len(revealed["p1"]) >= 5
        and len(revealed["p2"]) >= 5
        and faint_counts["p1"] >= 4
        and faint_counts["p2"] >= 4
    )
    parse_error = not bool(log_text.strip()) or total_turns <= 0
    if not log_text.strip():
        warnings.append("empty protocol log")
    elif total_turns <= 0:
        warnings.append("no valid turn commands")
    eligible = (
        not parse_error
        and winner is not None
        and total_turns >= 5
        and decisions > 0
        and _normalize_format(format_value) == "gen9randombattle"
        and all(0 < size <= 6 for size in team_sizes.values())
    )
    upload_time = metadata.get("upload_time")
    if upload_time in (None, ""):
        upload_time = replay_json.get("uploadtime")

    return {
        "profile_version": PROFILE_VERSION,
        "replay_id": replay_id,
        "path": str(path),
        "json_path": str(path.with_suffix(".json")) if path.with_suffix(".json").exists() else None,
        "format": str(format_value) if format_value not in (None, "") else None,
        "format_normalized": _normalize_format(format_value),
        "upload_time": upload_time,
        "upload_time_iso": _upload_iso(upload_time),
        "players": players,
        "rating": rating,
        "player_ratings": ratings,
        "winner": winner,
        "turn_count": total_turns,
        "approx_decision_state_count": decisions,
        "decision_count_source": decision_source,
        "early_forfeit_or_short": short_or_forfeit,
        "long_game": total_turns >= 30,
        "close_game_proxy": close_game,
        "parse_error": parse_error,
        "eligible_diagnostic_300": eligible,
        "mechanics": flags,
        "rare_mechanic": any(flags[name] for name in RARE_FLAGS),
        "raw_command_counts": dict(sorted(command_counts.items())),
        "revealed_species_counts": {
            "p1": len(revealed["p1"]),
            "p2": len(revealed["p2"]),
        },
        "faint_counts": {"p1": faint_counts["p1"], "p2": faint_counts["p2"]},
        "team_sizes": dict(sorted(team_sizes.items())),
        "warnings": warnings,
        "error": "; ".join(warnings) if parse_error else None,
    }


def _quantiles(values: Sequence[float]) -> Dict[str, Optional[float]]:
    ordered = sorted(float(value) for value in values if value is not None)
    if not ordered:
        return {key: None for key in ("min", "p25", "median", "p75", "p90", "max")}

    def percentile(fraction: float) -> float:
        index = fraction * (len(ordered) - 1)
        low = int(math.floor(index))
        high = int(math.ceil(index))
        if low == high:
            return ordered[low]
        return ordered[low] + (ordered[high] - ordered[low]) * (index - low)

    return {
        "min": ordered[0],
        "p25": percentile(0.25),
        "median": percentile(0.5),
        "p75": percentile(0.75),
        "p90": percentile(0.9),
        "max": ordered[-1],
    }


def catalog_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summary_markdown(summary: Dict[str, Any]) -> str:
    total = summary["total_replays_scanned"]
    lines = [
        "# Replay Pool Summary",
        "",
        f"- Profile version: `{summary['profile_version']}`",
        f"- Replay pool: `{summary['replay_dir']}`",
        f"- Total replays scanned: {total:,}",
        f"- Valid / invalid: {summary['valid_count']:,} / {summary['invalid_count']:,}",
        f"- Eligible for `diagnostic_300`: {summary['eligible_diagnostic_300']:,}",
        f"- Rating available: {summary['rating_available']:,} ({summary['rating_available_pct']:.1f}%)",
        f"- Short/forfeit proxy: {summary['short_forfeit_count']:,}",
        f"- Long games (30+ turns): {summary['long_game_count']:,}",
        f"- Close-game proxy: {summary['close_game_count']:,}",
        f"- Catalog SHA-256: `{summary['catalog_checksum']}`",
        "",
        "## Format Distribution",
        "",
    ]
    for name, count in summary["format_distribution"].items():
        lines.append(f"- `{name}`: {count:,}")
    lines.extend(["", "## Distribution Quantiles", "", "| Metric | Min | P25 | Median | P75 | P90 | Max |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for label, key in (
        ("Rating", "rating_quantiles"),
        ("Turns", "turn_quantiles"),
        ("Approx. decisions", "decision_quantiles"),
    ):
        values = summary[key]
        cells = [label] + ["n/a" if values[name] is None else f"{values[name]:.1f}" for name in ("min", "p25", "median", "p75", "p90", "max")]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "## Mechanic Coverage", "", "| Mechanic | Battles | Percent |", "| --- | ---: | ---: |"])
    for name, count in summary["mechanic_counts"].items():
        pct = 100.0 * count / total if total else 0.0
        lines.append(f"| `{name}` | {count:,} | {pct:.1f}% |")
    lines.extend([
        "",
        "## Assessment",
        "",
        summary["sufficiency_assessment"],
        "",
        summary["download_recommendation"],
        "",
        "Detection is conservative and protocol-only: flags use public command IDs/effect text, "
        "decision count prefers `inputlog` commands, long means 30+ turns, and close means both "
        "sides publicly revealed at least five species and each suffered at least four faints. "
        "The short/forfeit proxy includes games under five turns, missing winners, timer evidence, "
        "or a winner before five publicly observed loser faints.",
        "",
    ])
    return "\n".join(lines)


def profile_replay_pool(
    *,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
) -> Dict[str, Any]:
    metadata_by_id, invalid_metadata_rows = _metadata_by_id(replay_dir)
    log_paths = sorted(path for path in replay_dir.glob("*.log") if path.is_file())
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    duplicate_ids: List[str] = []
    seen_ids = set()
    for index, path in enumerate(log_paths, start=1):
        replay_id = path.stem
        if replay_id in seen_ids:
            duplicate_ids.append(replay_id)
        seen_ids.add(replay_id)
        metadata = metadata_by_id.get(replay_id, {})
        replay_json = _read_json(path.with_suffix(".json"))
        try:
            row = extract_replay_profile(
                path.read_text(encoding="utf-8", errors="replace"),
                replay_id=replay_id,
                path=path,
                metadata=metadata,
                replay_json=replay_json,
            )
        except Exception as exc:
            row = {
                "profile_version": PROFILE_VERSION,
                "replay_id": replay_id,
                "path": str(path),
                "parse_error": True,
                "eligible_diagnostic_300": False,
                "mechanics": {name: False for name in MECHANIC_FLAGS},
                "warnings": [],
                "error": str(exc),
            }
        rows.append(row)
        if index % 1000 == 0:
            print_line_safe(f"profile-replays | scanned={index}/{len(log_paths)}")

    with catalog_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    checksum = catalog_checksum(catalog_path)
    mechanic_counts = {
        name: sum(bool(row.get("mechanics", {}).get(name)) for row in rows)
        for name in MECHANIC_FLAGS
    }
    ratings = [row["rating"] for row in rows if row.get("rating") is not None]
    valid = sum(not row.get("parse_error") for row in rows)
    eligible = sum(bool(row.get("eligible_diagnostic_300")) for row in rows)
    format_distribution = Counter(str(row.get("format_normalized") or "unknown") for row in rows)
    sufficient = eligible >= 300 and sum(mechanic_counts[name] > 0 for name in RARE_FLAGS) >= 4
    summary = {
        "profile_version": PROFILE_VERSION,
        "replay_dir": str(replay_dir),
        "catalog_path": str(catalog_path),
        "catalog_checksum": checksum,
        "total_replays_scanned": len(rows),
        "valid_count": valid,
        "invalid_count": len(rows) - valid,
        "eligible_diagnostic_300": eligible,
        "format_distribution": dict(sorted(format_distribution.items())),
        "rating_available": len(ratings),
        "rating_available_pct": 100.0 * len(ratings) / len(rows) if rows else 0.0,
        "rating_quantiles": _quantiles(ratings),
        "turn_quantiles": _quantiles([row.get("turn_count", 0) for row in rows]),
        "decision_quantiles": _quantiles([row.get("approx_decision_state_count", 0) for row in rows]),
        "short_forfeit_count": sum(bool(row.get("early_forfeit_or_short")) for row in rows),
        "long_game_count": sum(bool(row.get("long_game")) for row in rows),
        "close_game_count": sum(bool(row.get("close_game_proxy")) for row in rows),
        "mechanic_counts": mechanic_counts,
        "rare_mechanic_counts": {name: mechanic_counts[name] for name in RARE_FLAGS},
        "duplicate_ids": duplicate_ids,
        "invalid_metadata_rows": invalid_metadata_rows,
        "metadata_rows": len(metadata_by_id),
        "logs_without_metadata": sum(path.stem not in metadata_by_id for path in log_paths),
        "logs_without_json": sum(not path.with_suffix(".json").exists() for path in log_paths),
        "sufficient_for_diagnostic_300": sufficient,
        "sufficiency_assessment": (
            "The existing pool is sufficient for a 300-battle diagnostic sample."
            if sufficient else
            "The existing pool is not sufficiently broad for the requested diagnostic sample."
        ),
        "download_recommendation": (
            "No targeted replay downloads are needed now; reassess after diagnostic feature-build coverage."
            if sufficient else
            "Targeted downloads are recommended for missing rare-mechanic strata."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_summary_markdown(summary), encoding="utf-8")
    print_line_safe(
        f"profile-replays done | scanned={len(rows)} valid={valid} eligible={eligible} "
        f"catalog={catalog_path}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile an existing replay pool without feature generation.")
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH))
    args = parser.parse_args()
    profile_replay_pool(
        replay_dir=Path(args.replay_dir),
        catalog_path=Path(args.catalog),
        summary_path=Path(args.summary),
    )


if __name__ == "__main__":
    main()
