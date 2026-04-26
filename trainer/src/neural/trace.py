"""
Battle trace logging module for recording and analyzing battle replays.

Provides BattleTracer class for collecting turn-by-turn battle data,
writing JSON traces, markdown summaries, and protocol logs.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BattleTracer:
    """Manages JSON/Markdown/protocol log writing for battle replays."""

    def __init__(self, output_dir: str, run_name: str = "default"):
        """Initialize tracer with output directory.

        Args:
            output_dir: Base directory for trace output (e.g., artifacts/battles)
            run_name: Subdirectory name for this run
        """
        self.base_dir = Path(output_dir) / run_name
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_battle: Optional[Dict[str, Any]] = None
        self.battle_count = 0

    def start_battle(self, battle_index: int, env_id: str, format_str: str) -> None:
        """Start recording a new battle.

        Args:
            battle_index: Index of the battle
            env_id: Environment ID from sim-core
            format_str: Battle format (e.g., "gen9randombattle")
        """
        self.current_battle = {
            "battle_index": battle_index,
            "env_id": env_id,
            "format": format_str,
            "winner": None,
            "total_turns": 0,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "turns": [],
            "diagnostics": [],
            "protocol_log": [],
        }
        self.battle_count = battle_index

    def add_turn(self, turn_num: int, p1_state: Dict[str, Any], p2_state: Dict[str, Any],
                 p1_action: Dict[str, Any], p2_action: Optional[Dict[str, Any]] = None,
                 protocol_lines: Optional[List[str]] = None) -> None:
        """Record a turn of battle.

        Args:
            turn_num: Turn number (1-indexed)
            p1_state: Player 1 active Pokemon state
            p2_state: Player 2 active Pokemon state
            p1_action: Player 1's chosen action
            p2_action: Player 2's action (if known)
            protocol_lines: Raw Showdown protocol lines from this turn
        """
        if self.current_battle is None:
            return

        turn_data = {
            "turn": turn_num,
            "steps": [
                {
                    "player": "p1",
                    "p1_species": p1_state.get("species"),
                    "p1_hp_ratio": p1_state.get("hp_ratio"),
                    "p1_status": p1_state.get("status"),
                    "p1_boosts": p1_state.get("boosts", {}),
                    "active_species": p1_state.get("species"),
                    "hp_ratio": p1_state.get("hp_ratio"),
                    "status": p1_state.get("status"),
                    "boosts": p1_state.get("boosts", {}),
                    "legal_actions": p1_state.get("legal_action_count", 0),
                    "chosen_action": p1_action.get("choice"),
                    "chosen_action_label": p1_action.get("label"),
                    "chosen_action_index": p1_action.get("index"),
                    "model_logits": p1_action.get("logits"),
                    "opponent_active_species": p2_state.get("species"),
                    "opponent_hp_ratio": p2_state.get("hp_ratio"),
                    "opponent_status": p2_state.get("status"),
                },
            ]
        }

        if p2_action is not None:
            turn_data["steps"].append({
                "player": "p2",
                "active_species": p2_state.get("species"),
                "hp_ratio": p2_state.get("hp_ratio"),
                "status": p2_state.get("status"),
                "chosen_action": p2_action.get("choice"),
                "chosen_action_label": p2_action.get("label"),
            })

        self.current_battle["turns"].append(turn_data)
        self.current_battle["total_turns"] = turn_num

        if protocol_lines:
            self.current_battle["protocol_log"].extend(protocol_lines)

    def finalize_battle(self, winner: Optional[str], diagnostics: Optional[List[str]] = None) -> None:
        """Finalize and write trace files for current battle.

        Args:
            winner: "p1", "p2", or None for tie
            diagnostics: List of diagnostic warnings
        """
        if self.current_battle is None:
            return

        self.current_battle["winner"] = winner
        if diagnostics:
            self.current_battle["diagnostics"] = diagnostics

        # Write JSON trace
        json_path = self.base_dir / f"battle_{self.battle_count}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.current_battle, f, indent=2)

        # Write markdown summary
        md_path = self.base_dir / f"battle_{self.battle_count}.md"
        md_content = "\n".join(self._build_markdown_lines())
        md_path.write_text(md_content, encoding="utf-8")

        # Write protocol log ONLY if there's real protocol data
        protocol_log = self.current_battle.get("protocol_log", [])
        if protocol_log and any(line and line.startswith("|") for line in protocol_log):
            log_path = self.base_dir / f"battle_{self.battle_count}.showdown.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in protocol_log:
                    f.write(line + "\n")

        self.current_battle = None

    def _build_markdown_lines(self) -> List[str]:
        """Build markdown lines for the battle."""
        if not self.current_battle:
            return []

        lines = [
            f"# Battle {self.current_battle['battle_index']}: {self.current_battle['format']}",
            f"**Result:** {self.current_battle['winner']} win ({self.current_battle['total_turns']} turns)",
            "",
        ]

        # Track if we have protocol logs
        has_real_logs = any(self.current_battle.get("protocol_log", []))

        # Turn-by-turn summary
        for turn_data in self.current_battle["turns"]:
            turn_num = turn_data["turn"]
            lines.append(f"## Turn {turn_num}")

            for step in turn_data["steps"]:
                # Handle both old-style and new-style steps
                if "player" in step:
                    # Old-style step
                    player = step["player"]
                    species = step.get("active_species", "Unknown")
                    hp = step.get("hp_ratio", 0) or 0
                    status = step.get("status", "no status")
                    choice = step.get("chosen_action_label", "?")
                else:
                    # New-style step - infer player as p1 since we only trace p1
                    player = "p1"
                    species = step.get("p1_species", "Unknown")
                    hp = step.get("p1_hp_ratio", 0)
                    status = step.get("p1_status", "no status")
                    choice = step.get("chosen_action_label", "?")

                # Include boosts if non-empty
                boosts = step.get("p1_boosts" if player == "p1" else "boosts", {})
                if "boosts" in step and player == "p1":  # Handle old-style
                    boosts = step["boosts"]

                boost_str = ""
                if boosts:
                    boost_items = [f"{k}:{v:+d}" for k, v in boosts.items() if v != 0]
                    if boost_items:
                        boost_str = f" ({', '.join(boost_items)})"

                lines.append(f"### {player}: {species} (HP {hp*100:.0f}%, {status}{boost_str})")
                lines.append(f"- **Choice:** {choice}")

                # Legal actions count
                legal_count = step.get("legal_actions_count", step.get("legal_actions"))
                if legal_count:
                    if isinstance(legal_count, list):
                        legal_count = len(legal_count)
                    lines.append(f"- **Legal actions:** {legal_count}")

                # Show model confidence if available
                if step.get("chosen_action_probability"):
                    prob = step["chosen_action_probability"]
                    lines.append(f"- **Model confidence:** {prob*100:.1f}%")

                lines.append("")

        # Diagnostics
        if self.current_battle.get("diagnostics"):
            lines.append("## Diagnostics")
            for diagnostic in self.current_battle["diagnostics"]:
                lines.append(f"- WARNING: {diagnostic}")
            lines.append("")

        # Protocol log status
        if not has_real_logs:
            lines.append("## Replay Data")
            lines.append("WARNING: **Showdown protocol logs are not available.** This trace shows decision points but not full battle events.")

        return lines

    def _write_markdown(self, path: Path) -> None:
        """Write human-readable markdown summary."""
        if not self.current_battle:
            return

        lines = [
            f"# Battle {self.current_battle['battle_index']}: {self.current_battle['format']}",
            f"**Result:** {self.current_battle['winner']} win ({self.current_battle['total_turns']} turns)",
            "",
        ]

        # Track if we have protocol logs
        has_real_logs = any(self.current_battle.get("protocol_log", []))

        # Turn-by-turn summary
        for turn_data in self.current_battle["turns"]:
            turn_num = turn_data["turn"]
            lines.append(f"## Turn {turn_num}")

            for step in turn_data["steps"]:
                player = step["player"]
                species = step.get("active_species", "Unknown")
                hp = step.get("hp_ratio", 0)
                status = step.get("status", "no status")
                choice = step.get("chosen_action_label", "?")

                # Include boosts if non-empty
                boosts = step.get("boosts", {})
                boost_str = ""
                if boosts:
                    boost_items = [f"{k}:{v:+d}" for k, v in boosts.items() if v != 0]
                    if boost_items:
                        boost_str = f" ({', '.join(boost_items)})"

                lines.append(f"### {player}: {species} (HP {hp*100:.0f}%, {status}{boost_str})")
                lines.append(f"- **Choice:** {choice}")
                if step.get("legal_actions_count"):
                    lines.append(f"- **Legal actions:** {step['legal_actions_count']}")

                # Show model confidence if available
                if step.get("chosen_action_probability"):
                    prob = step["chosen_action_probability"]
                    lines.append(f"- **Model confidence:** {prob*100:.1f}%")

                lines.append("")

        # Diagnostics
        if self.current_battle.get("diagnostics"):
            lines.append("## Diagnostics")
            for diagnostic in self.current_battle["diagnostics"]:
                lines.append(f"- WARNING: {diagnostic}")
            lines.append("")

        # Protocol log status
        if not has_real_logs:
            lines.append("## Replay Data")
            lines.append("WARNING: **Showdown protocol logs are not available.** This trace shows decision points but not full battle events.")

        path.write_text("\n".join(lines))
