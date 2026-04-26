"""
Decision analyzer for categorizing and analyzing Pokemon battle decisions.

Provides categorization of battle actions into types (attack, setup, recovery, etc.)
and pattern detection for loop analysis. These categories are diagnostics only; they
are not action filters or policy rules.
"""

import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class DecisionCategorizer:
    """Categorizes battle decisions into action types."""

    def __init__(self):
        """Initialize with Pokemon type matchup knowledge."""
        self.recovery_moves = {
            "recover", "roost", "synthesis", "morning sun", "moonlight",
            "refresh", "heal bell", "aromatherapy", "wish", "healing wish",
            "regenerator", "aqua ring", "leech seed", "rest"
        }
        self.setup_moves = {
            "nasty plot", "swords dance", "dragon dance", "bulk up",
            "calm mind", "cosmic power", "growth", "work up", "meditate",
            "agility", "amnesia", "barrier", "iron defense", "splash",
            "autoize", "soak", "power split", "guard split"
        }
        self.hazard_moves = {
            "stealth rock", "spikes", "toxic spikes", "sticky web",
            "reflect", "light screen", "aurora veil", "tailwind", "trick room"
        }

    def categorize(self, record: Dict[str, Any]) -> Tuple[str, str]:
        """Compatibility wrapper returning (category, subcategory)."""
        category_info = self.categorize_decision(record, [record], 0)
        return category_info.get("category", "unknown"), category_info.get("subcategory", "unknown")

    def summarize(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        categorized = []
        for index, record in enumerate(records):
            categorized.append({**record, **self.categorize_decision(record, records, index)})
        return _compute_summary(categorized)

    def generate_csv_rows(self, records: List[Dict[str, Any]]):
        for index, record in enumerate(records):
            category_info = self.categorize_decision(record, records, index)
            yield {
                "battle_index": record.get("battle_index", ""),
                "step_index": record.get("step_index", ""),
                "player": record.get("player", ""),
                "category": category_info.get("category", "unknown"),
                "subcategory": category_info.get("subcategory", "unknown"),
            }

    def analyze_dataset(self, records: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        categorized = [{**record, **self.categorize_decision(record, records, index)} for index, record in enumerate(records)]
        summary = _compute_summary(categorized)

        csv_path = output_path / "decision_categories.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["battle_index", "step_index", "player", "category", "subcategory"]
            )
            writer.writeheader()
            for row in self.generate_csv_rows(records):
                writer.writerow(row)

        json_path = output_path / "decision_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        _write_markdown_report(output_path / "decision_summary.md", summary, categorized)
        return summary

    def categorize_decision(
        self, record: Dict[str, Any], all_records: List[Dict[str, Any]], record_index: int
    ) -> Dict[str, str]:
        """Categorize a single decision.

        Args:
            record: Battle record with view, request, and choice
            all_records: All records for context (to detect patterns)
            record_index: Index of current record in all_records

        Returns:
            Dict with category, subcategory, and reasoning
        """
        view = record.get("view", {})
        request = record.get("request", {})
        choice = record.get("choice", "")
        legal_actions = request.get("legal_actions", {}).get("actions", [])

        # Check if forced switch
        if self._truthy_flag(request.get("force_switch")):
            return {"category": "switch", "subcategory": "forced_switch"}

        # Check if only switches are legal (no move options)
        has_moves = any(action and action.get("kind") == "move" for action in legal_actions)
        has_switches = any(action and action.get("kind") == "switch" for action in legal_actions)

        if not has_moves and has_switches:
            return {"category": "switch", "subcategory": "no_move_options_switch"}

        # If it's a switch and we got here, it's voluntary
        if choice.startswith("switch"):
            return {"category": "switch", "subcategory": "voluntary_switch"}

        # Get the active Pokemon and analyze the move
        active_idx = view.get("active", {}).get("self", 0) or 0
        self_team = view.get("self_team", [])
        if active_idx >= len(self_team):
            return {"category": "unknown", "subcategory": "invalid_active"}

        active_pokemon = self_team[active_idx]
        opponent_idx = view.get("active", {}).get("opponent", 0) or 0
        opponent_team = view.get("opponent_team", [])
        if opponent_idx >= len(opponent_team):
            return {"category": "unknown", "subcategory": "invalid_opponent"}

        opponent_pokemon = opponent_team[opponent_idx]

        # Extract move from choice
        move_name = self._extract_move_name(choice, request)
        if not move_name:
            return {"category": "unknown", "subcategory": "unparseable_move"}

        # Categorize the move
        move_name_lower = move_name.lower()

        if move_name_lower in self.recovery_moves:
            # Check HP ratio
            hp_ratio = active_pokemon.get("hp_ratio", 0)
            if hp_ratio > 0.95:
                return {"category": "recovery", "subcategory": "full_hp_recover"}
            else:
                return {"category": "recovery", "subcategory": "partial_hp_recover"}

        if move_name_lower in self.setup_moves:
            # Check for repeated setup
            recent_setup_count = self._count_recent_same_move(
                all_records, record_index, move_name_lower, window=5
            )
            if recent_setup_count >= 3:
                return {"category": "setup", "subcategory": f"repeated_setup_{recent_setup_count}"}
            else:
                return {"category": "setup", "subcategory": "first_boost"}

        if move_name_lower in self.hazard_moves:
            # Check if hazard already placed
            if self._is_hazard_redundant(view, move_name_lower):
                return {"category": "hazard", "subcategory": "redundant_hazard"}
            else:
                return {"category": "hazard", "subcategory": "first_placement"}

        # Otherwise it's an attack
        if move_name_lower == "struggle":
            return {"category": "attack", "subcategory": "struggle"}

        # Try to determine effectiveness
        effectiveness = self._get_type_effectiveness(
            move_name, active_pokemon, opponent_pokemon
        )

        if effectiveness == "super_effective":
            return {"category": "attack", "subcategory": "super_effective_attack"}
        elif effectiveness == "resisted":
            return {"category": "attack", "subcategory": "resisted_attack"}
        elif effectiveness == "no_effect":
            return {"category": "attack", "subcategory": "no_effect_attack"}
        else:
            return {"category": "attack", "subcategory": "neutral_attack"}

    def _extract_move_name(self, choice: str, request: Dict[str, Any]) -> Optional[str]:
        """Extract move name from choice string and request."""
        if not choice.startswith("move"):
            return None

        parts = choice.split()
        if len(parts) < 2:
            return None

        try:
            slot = int(parts[1]) - 1
        except ValueError:
            return None

        active = request.get("active", {})
        moves = active.get("moves", []) if isinstance(active, dict) else []
        if slot >= len(moves) or slot < 0:
            return None

        move = moves[slot]
        return move.get("move")

    def _count_recent_same_move(
        self, records: List[Dict[str, Any]], current_idx: int, move_name: str, window: int
    ) -> int:
        """Count how many times the same move was used recently."""
        count = 0
        start_idx = max(0, current_idx - window)
        for idx in range(start_idx, current_idx):
            record = records[idx]
            if record.get("battle_index") != records[current_idx].get("battle_index"):
                break  # Different battle
            extracted = self._extract_move_name(record.get("choice", ""), record.get("request", {}))
            if extracted and extracted.lower() == move_name:
                count += 1
        return count

    def _is_hazard_redundant(self, view: Dict[str, Any], hazard_move: str) -> bool:
        """Check if hazard move is redundant (already placed)."""
        field = view.get("field", {})
        pseudo_weather = field.get("pseudo_weather", [])
        side_conditions = field.get("side_conditions", {}).get("self", {})

        hazard_names = {
            "stealth rock": "stealthrock",
            "spikes": "spikes",
            "toxic spikes": "toxicspikes",
            "sticky web": "stickyweb",
            "reflect": "reflect",
            "light screen": "lightscreen",
            "aurora veil": "auroraveil",
            "tailwind": "tailwind",
            "trick room": "trickroom"
        }

        field_name = hazard_names.get(hazard_move)
        if not field_name:
            return False

        if field_name in ["trickroom"]:
            return field_name in pseudo_weather
        else:
            return side_conditions.get(field_name, 0) > 0

    def _get_type_effectiveness(
        self, move_name: str, user_pokemon: Dict[str, Any], target_pokemon: Dict[str, Any]
    ) -> Optional[str]:
        """Determine if move is super_effective, resisted, or no_effect.

        Returns:
            "super_effective", "resisted", "no_effect", or None (unknown)
        """
        # Simplified type matchup table (16 types × 16 = 256 possible matchups)
        type_chart = {
            ("Normal", "Rock"): "resisted",
            ("Normal", "Ghost"): "no_effect",
            ("Fire", "Fire"): "resisted",
            ("Fire", "Water"): "resisted",
            ("Fire", "Grass"): "super_effective",
            ("Fire", "Ice"): "super_effective",
            ("Fire", "Bug"): "super_effective",
            ("Fire", "Steel"): "super_effective",
            ("Fire", "Fairy"): "super_effective",
            ("Water", "Fire"): "super_effective",
            ("Water", "Water"): "resisted",
            ("Water", "Grass"): "resisted",
            ("Water", "Ground"): "super_effective",
            ("Water", "Rock"): "super_effective",
            ("Grass", "Fire"): "resisted",
            ("Grass", "Water"): "super_effective",
            ("Grass", "Grass"): "resisted",
            ("Grass", "Ground"): "super_effective",
            ("Grass", "Rock"): "super_effective",
            ("Electric", "Water"): "super_effective",
            ("Electric", "Grass"): "resisted",
            ("Electric", "Flying"): "super_effective",
            ("Psychic", "Fighting"): "super_effective",
            ("Psychic", "Poison"): "super_effective",
            ("Psychic", "Dark"): "no_effect",
            ("Dragon", "Dragon"): "super_effective",
            ("Dark", "Ghost"): "super_effective",
            ("Dark", "Dark"): "resisted",
            ("Dark", "Psychic"): "super_effective",
            ("Steel", "Normal"): "super_effective",
            ("Steel", "Flying"): "super_effective",
            ("Steel", "Rock"): "super_effective",
            ("Steel", "Fairy"): "super_effective",
            ("Steel", "Ice"): "super_effective",
        }

        # Get move type from hardcoded database (simplified)
        move_types = {
            "thunderbolt": "Electric",
            "thunder": "Electric",
            "lightning rod": "Electric",
            "earthquake": "Ground",
            "surf": "Water",
            "hydro pump": "Water",
            "fire blast": "Fire",
            "flamethrower": "Fire",
            "psychic": "Psychic",
            "shadow ball": "Ghost",
            "ice beam": "Ice",
            "dragon claw": "Dragon",
            "dragon dance": "Dragon",
            "close combat": "Fighting",
        }

        move_type = move_types.get(move_name.lower())
        if not move_type:
            return None  # Unknown move type

        target_types = target_pokemon.get("types", [])
        if not target_types:
            return None

        # Check first type
        effectiveness = type_chart.get((move_type, target_types[0]))
        if effectiveness:
            return effectiveness

        # Check second type if present
        if len(target_types) > 1:
            effectiveness = type_chart.get((move_type, target_types[1]))
            if effectiveness:
                return effectiveness

        return None  # Neutral effectiveness (no match in type chart)

    def _truthy_flag(self, value: Any) -> bool:
        if isinstance(value, list):
            return any(bool(item) for item in value)
        return bool(value)


def analyze_dataset(jsonl_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Analyze a dataset JSONL file.

    Returns:
        (records with categories, summary statistics)
    """
    categorizer = DecisionCategorizer()
    records = []

    # Read all records first
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Categorize each record
    categorized_records = []
    for idx, record in enumerate(records):
        category_info = categorizer.categorize_decision(record, records, idx)
        categorized_record = {**record, **category_info}
        categorized_records.append(categorized_record)

    # Compute summary statistics
    summary = _compute_summary(categorized_records)

    return categorized_records, summary


def _compute_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics from categorized records."""
    category_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total = len(records)

    for record in records:
        cat = record.get("category", "unknown")
        subcat = record.get("subcategory", "unknown")
        category_counts[cat][subcat] += 1

    # Build summary
    summary = {"total_records": total, "categories": {}}

    for cat, subcats in category_counts.items():
        count = sum(subcats.values())
        summary["categories"][cat] = {
            **subcats,
            "pct": 100.0 * count / total if total > 0 else 0,
            "total": count
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze battle decisions and categorize them.")
    parser.add_argument("--input", required=True, help="Path to raw JSONL dataset")
    parser.add_argument("--output", required=True, help="Output directory for analysis")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    categorized_records, summary = analyze_dataset(input_path)

    # Write CSV
    csv_path = output_dir / "decision_categories.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["battle_index", "step_index", "player", "category", "subcategory"]
        )
        writer.writeheader()
        for record in categorized_records:
            writer.writerow({
                "battle_index": record.get("battle_index", ""),
                "step_index": record.get("step_index", ""),
                "player": record.get("player", ""),
                "category": record.get("category", ""),
                "subcategory": record.get("subcategory", ""),
            })
    print(f"Wrote {len(categorized_records)} records to {csv_path}")

    # Write JSON summary
    json_path = output_dir / "decision_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary to {json_path}")

    # Write markdown report
    md_path = output_dir / "decision_summary.md"
    _write_markdown_report(md_path, summary, categorized_records)
    print(f"Wrote report to {md_path}")


def _write_markdown_report(
    path: Path, summary: Dict[str, Any], records: List[Dict[str, Any]]
) -> None:
    """Write human-readable markdown report."""
    lines = [
        "# Decision Analysis Report",
        "",
        f"**Total Records:** {summary['total_records']}",
        "",
        "## Category Breakdown",
        "",
    ]

    for cat, details in summary.get("categories", {}).items():
        total = details.get("total", 0)
        pct = details.get("pct", 0)
        lines.append(f"### {cat.upper()} ({total} records, {pct:.1f}%)")
        lines.append("")
        for subcat, count in details.items():
            if subcat not in ["pct", "total"]:
                lines.append(f"- **{subcat}**: {count} records")
        lines.append("")

    path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
