import argparse
import gzip
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .logging_helper import print_line_safe


DEFAULT_FORMAT = "gen9randombattle"
DEFAULT_RAW_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_PROCESSED_DIR = Path("data/replays/processed")
DEFAULT_REPORT_JSON = Path("artifacts/replays/parse_report.json")
DEFAULT_REPORT_MD = Path("artifacts/replays/parse_report.md")


def side_from_ident(ident: Optional[str]) -> Optional[str]:
    if not ident:
        return None
    match = re.match(r"^(p[12])", ident.strip())
    return match.group(1) if match else None


def parse_hp_fraction(condition: Optional[str]) -> Optional[float]:
    if not condition:
        return None
    text = str(condition)
    if "fnt" in text:
        return 0.0
    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    if percent:
        return max(0.0, min(1.0, float(percent.group(1)) / 100.0))
    fraction = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if fraction:
        denominator = float(fraction.group(2))
        if denominator > 0:
            return max(0.0, min(1.0, float(fraction.group(1)) / denominator))
    return None


def _status_from_condition(condition: Optional[str]) -> Optional[str]:
    if not condition:
        return None
    for token in ("brn", "par", "psn", "tox", "slp", "frz"):
        if re.search(rf"(^|\s){token}($|\s)", str(condition)):
            return token
    return None


def _split_protocol_line(raw_line: str) -> Tuple[str, List[str]]:
    line = raw_line.strip()
    if not line.startswith("|"):
        return "", []
    parts = line.split("|")
    command = parts[1] if len(parts) > 1 else ""
    return command, parts


def _winner_side(winner: Optional[str], players: Dict[str, str]) -> Optional[str]:
    if not winner:
        return None
    if winner in ("p1", "p2", "tie"):
        return winner
    winner_norm = winner.strip().lower()
    for side, name in players.items():
        if name and str(name).strip().lower() == winner_norm:
            return side
    return None


def _new_turn_record(turn: int) -> Dict[str, Any]:
    return {
        "turn": int(turn),
        "events": [],
        "move_actions": {"p1": [], "p2": []},
        "switch_actions": {"p1": [], "p2": []},
        "faint_events": [],
        "damage_events": [],
        "healing_events": [],
        "tera_events": [],
    }


def parse_protocol_log(
    lines: Iterable[str],
    *,
    replay_id: Optional[str] = None,
    format_name: Optional[str] = None,
    source_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_lines = [line.rstrip("\n") for line in lines if line.rstrip("\n")]
    players: Dict[str, str] = {}
    teamsize: Dict[str, int] = {}
    turn_numbers: List[int] = []
    turns_by_number: Dict[int, Dict[str, Any]] = {}
    turn_order: List[int] = []
    move_actions: Dict[str, List[Dict[str, Any]]] = {"p1": [], "p2": []}
    switch_actions: Dict[str, List[Dict[str, Any]]] = {"p1": [], "p2": []}
    faint_events: List[Dict[str, Any]] = []
    damage_events: List[Dict[str, Any]] = []
    healing_events: List[Dict[str, Any]] = []
    status_events: List[Dict[str, Any]] = []
    boost_events: List[Dict[str, Any]] = []
    tera_events: List[Dict[str, Any]] = []
    winner: Optional[str] = None
    winner_side: Optional[str] = None
    current_turn = 0

    def ensure_turn(turn: int) -> Dict[str, Any]:
        if turn not in turns_by_number:
            turns_by_number[turn] = _new_turn_record(turn)
            turn_order.append(turn)
        return turns_by_number[turn]

    def add_event(event: Dict[str, Any]) -> None:
        turn = int(event.get("turn", current_turn) or 0)
        turn_record = ensure_turn(turn)
        turn_record["events"].append(event)
        event_type = event.get("type")
        side = event.get("side")
        if event_type == "move" and side in ("p1", "p2"):
            turn_record["move_actions"][side].append(event)
            move_actions[side].append(event)
        elif event_type == "switch" and side in ("p1", "p2"):
            turn_record["switch_actions"][side].append(event)
            switch_actions[side].append(event)
        elif event_type == "faint":
            turn_record["faint_events"].append(event)
            faint_events.append(event)
        elif event_type == "damage":
            turn_record["damage_events"].append(event)
            damage_events.append(event)
        elif event_type == "heal":
            turn_record["healing_events"].append(event)
            healing_events.append(event)
        elif event_type == "tera":
            turn_record["tera_events"].append(event)
            tera_events.append(event)
        elif event_type == "status":
            status_events.append(event)
        elif event_type in ("boost", "unboost"):
            boost_events.append(event)

    for raw_line in raw_lines:
        command, parts = _split_protocol_line(raw_line)
        if not command:
            continue

        if command == "player" and len(parts) >= 4:
            side = parts[2]
            name = parts[3]
            if side in ("p1", "p2") and name:
                players[side] = name
            continue
        if command == "teamsize" and len(parts) >= 4:
            try:
                teamsize[parts[2]] = int(parts[3])
            except ValueError:
                pass
            continue
        if command == "turn" and len(parts) >= 3:
            try:
                current_turn = int(parts[2])
                turn_numbers.append(current_turn)
                ensure_turn(current_turn)
            except ValueError:
                pass
            continue
        if command == "win" and len(parts) >= 3:
            winner = parts[2]
            winner_side = _winner_side(winner, players)
            add_event({"turn": current_turn, "type": "win", "winner": winner, "raw": raw_line})
            continue
        if command == "tie":
            winner = "tie"
            winner_side = "tie"
            add_event({"turn": current_turn, "type": "win", "winner": "tie", "raw": raw_line})
            continue

        if command == "move" and len(parts) >= 4:
            actor = parts[2]
            event = {
                "turn": current_turn,
                "type": "move",
                "side": side_from_ident(actor),
                "actor": actor,
                "move": parts[3],
                "target": parts[4] if len(parts) > 4 else None,
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command in ("switch", "drag") and len(parts) >= 4:
            actor = parts[2]
            condition = parts[4] if len(parts) > 4 else None
            event = {
                "turn": current_turn,
                "type": "switch",
                "command": command,
                "side": side_from_ident(actor),
                "actor": actor,
                "details": parts[3],
                "condition": condition,
                "hp_fraction": parse_hp_fraction(condition),
                "status": _status_from_condition(condition),
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command == "replace" and len(parts) >= 4:
            actor = parts[2]
            condition = parts[4] if len(parts) > 4 else None
            event = {
                "turn": current_turn,
                "type": "replace",
                "command": command,
                "side": side_from_ident(actor),
                "actor": actor,
                "details": parts[3],
                "condition": condition,
                "hp_fraction": parse_hp_fraction(condition),
                "status": _status_from_condition(condition),
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command == "faint" and len(parts) >= 3:
            target = parts[2]
            event = {
                "turn": current_turn,
                "type": "faint",
                "side": side_from_ident(target),
                "target": target,
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command in ("-damage", "-heal") and len(parts) >= 4:
            target = parts[2]
            condition = parts[3]
            event = {
                "turn": current_turn,
                "type": "damage" if command == "-damage" else "heal",
                "side": side_from_ident(target),
                "target": target,
                "condition": condition,
                "hp_fraction": parse_hp_fraction(condition),
                "status": _status_from_condition(condition),
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command == "-status" and len(parts) >= 4:
            target = parts[2]
            event = {
                "turn": current_turn,
                "type": "status",
                "side": side_from_ident(target),
                "target": target,
                "status": parts[3],
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command in ("-boost", "-unboost") and len(parts) >= 5:
            target = parts[2]
            try:
                amount = int(parts[4])
            except ValueError:
                amount = 0
            event = {
                "turn": current_turn,
                "type": "boost" if command == "-boost" else "unboost",
                "side": side_from_ident(target),
                "target": target,
                "stat": parts[3],
                "amount": amount,
                "raw": raw_line,
            }
            add_event(event)
            continue
        if command == "-terastallize" and len(parts) >= 4:
            target = parts[2]
            event = {
                "turn": current_turn,
                "type": "tera",
                "side": side_from_ident(target),
                "target": target,
                "tera_type": parts[3],
                "raw": raw_line,
            }
            add_event(event)
            continue

    ordered_turns = [turns_by_number[turn] for turn in sorted(turn_order)]
    parsed_format = format_name or (metadata or {}).get("format")
    parsed_replay_id = replay_id or (metadata or {}).get("replay_id")
    if winner_side is None:
        winner_side = _winner_side(winner, players)
    winner_status = "tie" if winner_side == "tie" else "known" if winner_side in ("p1", "p2") else "unknown"
    return {
        "source": "public_pokemon_showdown_replay",
        "replay_id": parsed_replay_id,
        "format": parsed_format,
        "source_path": source_path,
        "source_url": (metadata or {}).get("source_url"),
        "players": players,
        "p1": players.get("p1"),
        "p2": players.get("p2"),
        "teamsize": teamsize,
        "winner": winner,
        "winner_side": winner_side,
        "winner_status": winner_status,
        "winner_known": winner_status != "unknown",
        "total_turns": max(turn_numbers) if turn_numbers else 0,
        "protocol_log": raw_lines,
        "turns": ordered_turns,
        "move_actions": move_actions,
        "switch_actions": switch_actions,
        "faint_events": faint_events,
        "damage_events": damage_events,
        "healing_events": healing_events,
        "status_events": status_events,
        "boost_events": boost_events,
        "tera_events": tera_events,
        "metadata": metadata or {},
        "line_count": len(raw_lines),
    }


def _read_metadata_by_id(replay_dir: Path) -> Dict[str, Dict[str, Any]]:
    metadata_path = replay_dir / "metadata.jsonl"
    by_id: Dict[str, Dict[str, Any]] = {}
    if not metadata_path.exists():
        return by_id
    with metadata_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            replay_id = record.get("replay_id")
            if replay_id:
                by_id[str(replay_id)] = record
                by_id[Path(str(record.get("log_path") or replay_id)).stem] = record
    return by_id


def _iter_log_paths(replay_dir: Path) -> List[Path]:
    return sorted(path for path in replay_dir.glob("*.log") if path.is_file())


def parse_replay_logs(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Path = DEFAULT_RAW_DIR,
    output_path: Optional[Path] = None,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> Dict[str, Any]:
    selected_output = output_path or DEFAULT_PROCESSED_DIR / f"{format_name}_trajectories.jsonl.gz"
    selected_output.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.perf_counter()
    log_paths = _iter_log_paths(replay_dir)
    metadata_by_id = _read_metadata_by_id(replay_dir)
    failures: List[Dict[str, Any]] = []
    parsed = 0
    missing_winner = 0
    total_examples = 0
    command_counts: Counter[str] = Counter()

    with gzip.open(selected_output, "wt", encoding="utf-8") as handle:
        for path in log_paths:
            replay_id = path.stem
            metadata = metadata_by_id.get(replay_id, {})
            replay_id = str(metadata.get("replay_id") or replay_id)
            try:
                trajectory = parse_protocol_log(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(),
                    replay_id=replay_id,
                    format_name=str(metadata.get("format") or format_name),
                    source_path=str(path),
                    metadata=metadata,
                )
                handle.write(json.dumps(trajectory, sort_keys=True) + "\n")
                parsed += 1
                total_examples += len(trajectory.get("turns", []))
                if not trajectory.get("winner_side"):
                    missing_winner += 1
                for line in trajectory.get("protocol_log", []):
                    command, _ = _split_protocol_line(str(line))
                    if command:
                        command_counts[command] += 1
            except Exception as exc:
                failures.append({"path": str(path), "reason": str(exc)})

    report = {
        "format": format_name,
        "replay_dir": str(replay_dir),
        "output_path": str(selected_output),
        "logs_found": int(len(log_paths)),
        "parsed_battles": int(parsed),
        "failed": int(len(failures)),
        "failures": failures,
        "missing_winner": int(missing_winner),
        "trajectory_turn_records": int(total_examples),
        "command_counts": dict(command_counts),
        "wall_time_sec": time.perf_counter() - started_at,
    }
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(
        f"parse-replays done | format={format_name} logs={len(log_paths)} parsed={parsed} "
        f"failed={len(failures)} output={selected_output}"
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Public Replay Parse Report",
        "",
        f"- Format: {report['format']}",
        f"- Logs found: {report['logs_found']}",
        f"- Parsed battles: {report['parsed_battles']}",
        f"- Failed: {report['failed']}",
        f"- Missing winner: {report['missing_winner']}",
        f"- Turn records: {report['trajectory_turn_records']}",
        "",
        "## Common Protocol Commands",
        "",
    ]
    for key, value in sorted(report.get("command_counts", {}).items(), key=lambda item: (-int(item[1]), item[0]))[:20]:
        lines.append(f"- `{key}`: {value}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in report["failures"][:20]:
            lines.append(f"- `{failure.get('path')}`: {failure.get('reason')}")
    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse public Pokemon Showdown replay protocol logs into trajectories.")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Pokemon Showdown format id.")
    parser.add_argument("--replay-dir", default=None, help="Directory containing raw .log files.")
    parser.add_argument("--output", default=None, help="Output trajectories JSONL.GZ path.")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="Parse report JSON path.")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Parse report Markdown path.")
    args = parser.parse_args()

    replay_dir = Path(args.replay_dir) if args.replay_dir else Path("data/replays/raw") / args.format
    output = Path(args.output) if args.output else DEFAULT_PROCESSED_DIR / f"{args.format}_trajectories.jsonl.gz"
    parse_replay_logs(
        format_name=args.format,
        replay_dir=replay_dir,
        output_path=output,
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
    )


if __name__ == "__main__":
    main()
