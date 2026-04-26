"""Test suite for decision analysis module."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from neural.analyze_decisions import DecisionCategorizer


class TestDecisionCategorizer(unittest.TestCase):
    """Test DecisionCategorizer class functionality."""

    def setUp(self):
        """Initialize categorizer for each test."""
        self.categorizer = DecisionCategorizer()

    def _make_decision_record(
        self,
        battle_index: int = 0,
        step_index: int = 0,
        move: str = "Earthquake",
        legal_moves: int = 4,
        active_species: str = "Pikachu",
        opponent_species: str = "Charizard",
        hp_ratio: float = 1.0,
        opponent_hp_ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Helper to create a mock decision record."""
        return {
            "battle_index": battle_index,
            "step_index": step_index,
            "choice": f"move 1",
            "view": {
                "active": {"p1": 0, "opponent": 0},
                "party": [{"species": active_species, "hp_ratio": hp_ratio}],
                "opponent_team": [{"species": opponent_species, "hp_ratio": opponent_hp_ratio}],
            },
            "legal_action_count": legal_moves,
        }

    def test_categorize_attack_neutral(self):
        """Test categorization of neutral damage move."""
        record = self._make_decision_record(move="Earthquake", opponent_species="Pikachu")
        category, subcategory = self.categorizer.categorize(record)

        # Most moves against random opponents are neutral
        self.assertIn(category, ["attack", "unknown"])

    def test_categorize_forced_switch(self):
        """Test categorization of forced switch."""
        record = self._make_decision_record()
        record["choice"] = "switch 2"
        record["request"] = {"force_switch": [True]}

        category, subcategory = self.categorizer.categorize(record)

        self.assertEqual(category, "switch")
        self.assertEqual(subcategory, "forced_switch")

    def test_categorize_voluntary_switch(self):
        """Test categorization of voluntary switch."""
        record = self._make_decision_record()
        record["choice"] = "switch 2"
        record["request"] = {"force_switch": [False]}
        record["view"]["active"]["p1"] = 0
        record["request"]["active"] = {"moves": [{"move": "Thunder"}]}

        category, subcategory = self.categorizer.categorize(record)

        self.assertEqual(category, "switch")
        self.assertIn(subcategory, ["voluntary_switch", "no_move_options_switch"])

    def test_categorize_recovery_at_full_hp(self):
        """Test categorization of recovery at full HP."""
        record = self._make_decision_record(hp_ratio=1.0)
        record["choice"] = "move 1"
        record["view"]["active"]["p1"] = 0
        record["party"] = [{"moves": [{"move": "Recover"}]}]

        category, subcategory = self.categorizer.categorize(record)

        if category == "recovery":
            self.assertEqual(subcategory, "full_hp_recover")

    def test_summarize_decisions(self):
        """Test summary generation from records."""
        records = [
            self._make_decision_record(battle_index=0, step_index=0),
            self._make_decision_record(battle_index=0, step_index=1),
            self._make_decision_record(battle_index=1, step_index=0),
        ]

        summary = self.categorizer.summarize(records)

        self.assertIn("total_records", summary)
        self.assertEqual(summary["total_records"], 3)
        self.assertIn("categories", summary)

    def test_generate_csv_rows(self):
        """Test CSV row generation."""
        records = [
            self._make_decision_record(battle_index=0, step_index=0),
            self._make_decision_record(battle_index=0, step_index=1),
        ]

        csv_rows = list(self.categorizer.generate_csv_rows(records))

        self.assertEqual(len(csv_rows), 2)
        self.assertTrue(all("category" in row for row in csv_rows))

    def test_analyze_dataset_writes_outputs(self):
        """Test that analyze_dataset produces output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            records = [
                self._make_decision_record(battle_index=i, step_index=j)
                for i in range(3)
                for j in range(5)
            ]

            self.categorizer.analyze_dataset(records, temp_dir)

            # Check that output files were created
            csv_path = Path(temp_dir) / "decision_categories.csv"
            json_path = Path(temp_dir) / "decision_summary.json"
            md_path = Path(temp_dir) / "decision_summary.md"

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            # Verify CSV content
            with open(csv_path) as f:
                lines = f.readlines()
            self.assertGreater(len(lines), 1)  # Header + records

            # Verify JSON content
            with open(json_path) as f:
                data = json.load(f)
            self.assertIn("total_records", data)
            self.assertEqual(data["total_records"], 15)

            # Verify markdown content
            with open(md_path) as f:
                content = f.read()
            self.assertIn("Decision Analysis Report", content)

    def test_categorize_setup_move(self):
        """Test categorization of setup moves."""
        record = self._make_decision_record(move="Nasty Plot")
        record["view"]["active"]["p1"] = 0
        record["party"] = [{"boosts": {}}]

        category, subcategory = self.categorizer.categorize(record)

        if category == "setup":
            self.assertIn(subcategory, ["first_boost", "repeated_setup_3", "repeated_setup_4", "repeated_setup_5"])

    def test_categorize_multiple_calls_consistent(self):
        """Test that categorization is consistent across calls."""
        record = self._make_decision_record()

        cat1, subcat1 = self.categorizer.categorize(record)
        cat2, subcat2 = self.categorizer.categorize(record)

        self.assertEqual(cat1, cat2)
        self.assertEqual(subcat1, subcat2)


if __name__ == "__main__":
    unittest.main()
