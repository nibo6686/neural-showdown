import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .logging_helper import print_line_safe


def parse_showdown_log(lines: Iterable[str], *, source_path: Optional[str] = None) -> Dict[str, Any]:
    players: Dict[str, str] = {}
    turns: List[int] = []
    moves: List[Dict[str, Any]] = []
    switches: List[Dict[str, Any]] = []
    winner: Optional[str] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        command = parts[1] if len(parts) > 1 else ""
        if command == "player" and len(parts) >= 4:
            players[parts[2]] = parts[3]
        elif command == "turn" and len(parts) >= 3:
            try:
                turns.append(int(parts[2]))
            except ValueError:
                pass
        elif command == "move" and len(parts) >= 4:
            moves.append(
                {
                    "turn": turns[-1] if turns else 0,
                    "actor": parts[2],
                    "move": parts[3],
                    "target": parts[4] if len(parts) > 4 else None,
                }
            )
        elif command in {"switch", "drag"} and len(parts) >= 4:
            switches.append(
                {
                    "turn": turns[-1] if turns else 0,
                    "actor": parts[2],
                    "details": parts[3],
                    "condition": parts[4] if len(parts) > 4 else None,
                }
            )
        elif command == "win" and len(parts) >= 3:
            winner = parts[2]
        elif command == "tie":
            winner = "tie"

    return {
        "source": "showdown_log",
        "source_path": source_path,
        "players": players,
        "winner": winner,
        "turns": max(turns) if turns else 0,
        "moves": moves,
        "switches": switches,
        "usable_for_training": False,
        "reason": "Public logs do not include exact request masks; import requires later legality reconstruction.",
    }


def import_logs(input_paths: List[Path], output_path: Path) -> Dict[str, Any]:
    summaries = []
    for path in input_paths:
        summaries.append(parse_showdown_log(path.read_text(encoding="utf-8").splitlines(), source_path=str(path)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for summary in summaries:
            handle.write(json.dumps(summary) + "\n")
    return {
        "logs": len(summaries),
        "output_path": str(output_path),
        "usable_for_training": sum(1 for summary in summaries if summary.get("usable_for_training")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import public Pokemon Showdown logs for future supervised augmentation.")
    parser.add_argument("--input", nargs="+", required=True, help="One or more Showdown log text files.")
    parser.add_argument("--output", required=True, help="JSONL summary output path.")
    args = parser.parse_args()
    report = import_logs([Path(path) for path in args.input], Path(args.output))
    print_line_safe(f"import_logs done | logs={report['logs']} output={report['output_path']} usable={report['usable_for_training']}")


if __name__ == "__main__":
    main()
