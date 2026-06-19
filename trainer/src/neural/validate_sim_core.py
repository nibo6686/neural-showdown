from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .damage_engine import estimate_damage
from .parse_replay_logs import parse_protocol_log


def _run(command: Sequence[str], cwd: Path) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=dict(os.environ),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout or ""
    tests = re.findall(r"(?:Ran|tests)\s+(\d+)", output)
    passed = re.findall(r"(?:pass|OK)\s*(\d+)?", output)
    return {
        "command": list(command),
        "cwd": str(cwd),
        "returncode": int(completed.returncode),
        "ok": completed.returncode == 0,
        "duration_sec": time.perf_counter() - started,
        "test_count_hints": [int(value) for value in tests],
        "pass_hints": [int(value) for value in passed if value],
        "output_tail": output.splitlines()[-80:],
    }


def _replay_sanity(replay_dir: Path, limit: int) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(replay_dir.glob("*.log"))[:limit]:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        trace = parse_protocol_log(
            lines,
            replay_id=path.stem,
            format_name="gen9randombattle",
            source_path=str(path),
        )
        rows.append(
            {
                "replay": path.name,
                "turns": trace["total_turns"],
                "moves": sum(len(value) for value in trace["move_actions"].values()),
                "switches": sum(len(value) for value in trace["switch_actions"].values()),
                "damage_events": len(trace["damage_events"]),
                "winner_side": trace["winner_side"],
                "has_seed": any(line.startswith(">start ") and "seed" in line for line in lines),
                "has_private_request": any(line.startswith("|request|") for line in lines),
            }
        )
    return {
        "ok": len(rows) >= min(3, limit),
        "replay_dir": str(replay_dir),
        "checked": len(rows),
        "rows": rows,
    }


def _damage_healthcheck() -> Dict[str, Any]:
    cases = [
        {
            "name": "baseline",
            "request": {
                "attacker": {"species": "Mew", "level": 80},
                "defender": {"species": "Mew", "level": 80},
                "move": "Aura Sphere",
            },
        },
        {
            "name": "immune",
            "request": {
                "attacker": {"species": "Pikachu", "level": 80},
                "defender": {"species": "Golem", "level": 80},
                "move": "Thunderbolt",
            },
        },
        {
            "name": "item_weather",
            "request": {
                "attacker": {"species": "Pelipper", "level": 80, "item": "Choice Specs"},
                "defender": {"species": "Arcanine", "level": 80},
                "move": "Surf",
                "field": {"weather": "Rain"},
            },
        },
        {
            "name": "exact_stats",
            "request": {
                "attacker": {"species": "Mew", "level": 80, "stats": {"spa": 500}},
                "defender": {"species": "Mew", "level": 80, "stats": {"spd": 50, "hp": 400}},
                "move": "Aura Sphere",
            },
        },
    ]
    rows = []
    for case in cases:
        result = estimate_damage(**case["request"])
        rows.append(
            {
                "name": case["name"],
                "damage_method": result.get("damage_method"),
                "min_percent": result.get("min_percent"),
                "max_percent": result.get("max_percent"),
                "immune": result.get("immune"),
                "type_effectiveness": result.get("type_effectiveness"),
                "warnings": result.get("warnings", []),
                "used_exact_attacker_stats": result.get("used_exact_attacker_stats", False),
                "used_exact_defender_stats": result.get("used_exact_defender_stats", False),
            }
        )
    return {
        "ok": (
            all(row["damage_method"] == "smogon_calc" for row in rows)
            and rows[-1]["used_exact_attacker_stats"]
            and rows[-1]["used_exact_defender_stats"]
        ),
        "heuristic_fallback_seen": "heuristic_fallback" in json.dumps(rows),
        "rows": rows,
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# sim-core Validation Results",
        "",
        f"- Overall: `{'PASS' if report['ok'] else 'FAIL'}`",
        f"- Generated: `{report['generated_at']}`",
        f"- pokemon-showdown: `{report['dependencies'].get('pokemon-showdown')}`",
        f"- @smogon/calc: `{report['dependencies'].get('@smogon/calc')}`",
        "",
        "## Commands",
        "",
    ]
    for result in report["commands"]:
        lines.append(
            f"- `{' '.join(result['command'])}`: "
            f"`{'PASS' if result['ok'] else 'FAIL'}` ({result['duration_sec']:.2f}s)"
        )
    lines.extend(
        [
            "",
            "## Damage healthcheck",
            "",
            f"- Result: `{'PASS' if report['damage']['ok'] else 'FAIL'}`",
            f"- Heuristic fallback seen: `{report['damage']['heuristic_fallback_seen']}`",
            f"- Exact attacker stats used: `{report['damage']['rows'][-1]['used_exact_attacker_stats']}`",
            f"- Exact defender stats used: `{report['damage']['rows'][-1]['used_exact_defender_stats']}`",
            "",
            "## Replay sanity",
            "",
            f"- Replays checked: `{report['replays']['checked']}`",
        ]
    )
    for row in report["replays"]["rows"]:
        lines.append(
            f"- `{row['replay']}`: turns={row['turns']} moves={row['moves']} "
            f"switches={row['switches']} seed={row['has_seed']} private_request={row['has_private_request']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Showdown parity smoke suite and write combined results.")
    parser.add_argument("--replay-limit", type=int, default=5)
    parser.add_argument("--output-dir", default="artifacts/validation")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    sim_core = repo_root / "sim-core"
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("npm was not found")

    commands = [
        _run([npm, "test"], sim_core),
        _run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(repo_root / "trainer" / "tests"),
                "-p",
                "test_sim_core_parity.py",
            ],
            repo_root,
        ),
    ]
    npm_list = _run([npm, "list", "pokemon-showdown", "@smogon/calc", "--depth=0", "--json"], sim_core)
    dependencies: Dict[str, Any] = {}
    try:
        payload = json.loads("\n".join(npm_list["output_tail"]))
        dependencies = {
            key: value.get("version")
            for key, value in payload.get("dependencies", {}).items()
            if isinstance(value, dict)
        }
    except (json.JSONDecodeError, TypeError):
        dependencies = {}

    damage = _damage_healthcheck()
    replays = _replay_sanity(
        repo_root / "data" / "replays" / "raw" / "gen9randombattle",
        max(1, args.replay_limit),
    )
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ok": all(result["ok"] for result in commands) and damage["ok"] and replays["ok"],
        "dependencies": dependencies,
        "commands": commands,
        "damage": damage,
        "replays": replays,
    }
    (output_dir / "sim_core_validation_results.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (output_dir / "sim_core_validation_results.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "output_dir": str(output_dir)}, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
