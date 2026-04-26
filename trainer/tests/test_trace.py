"""Test suite for battle tracing module."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from neural.trace import BattleTracer


class TestBattleTracer(unittest.TestCase):
    """Test BattleTracer class functionality."""

    def setUp(self):
        """Create temporary directory for trace output."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracer = BattleTracer(self.temp_dir, run_name="test_run")

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_battle_creates_current_battle(self):
        """Test that start_battle initializes current_battle correctly."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.assertIsNotNone(self.tracer.current_battle)
        self.assertEqual(self.tracer.current_battle["battle_index"], 0)
        self.assertEqual(self.tracer.current_battle["env_id"], "env-1")
        self.assertEqual(self.tracer.current_battle["format"], "gen9randombattle")
        self.assertIsNone(self.tracer.current_battle["winner"])
        self.assertEqual(self.tracer.current_battle["total_turns"], 0)
        self.assertEqual(len(self.tracer.current_battle["turns"]), 0)

    def test_add_turn_records_turn_data(self):
        """Test that add_turn correctly records turn data."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")

        p1_state = {"species": "Pikachu", "hp_ratio": 1.0, "status": None}
        p2_state = {"species": "Charizard", "hp_ratio": 0.8, "status": None}
        p1_action = {"choice": "move 1", "label": "Thunderbolt", "index": 0}

        self.tracer.add_turn(1, p1_state, p2_state, p1_action)

        self.assertEqual(self.tracer.current_battle["total_turns"], 1)
        self.assertEqual(len(self.tracer.current_battle["turns"]), 1)

        turn = self.tracer.current_battle["turns"][0]
        self.assertEqual(turn["turn"], 1)
        self.assertEqual(len(turn["steps"]), 1)
        self.assertEqual(turn["steps"][0]["p1_species"], "Pikachu")

    def test_finalize_battle_writes_json(self):
        """Test that finalize_battle writes JSON trace file."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.tracer.current_battle["winner"] = "p1"

        self.tracer.finalize_battle("p1")

        json_path = Path(self.temp_dir) / "test_run" / "battle_0.json"
        self.assertTrue(json_path.exists())

        with open(json_path) as f:
            data = json.load(f)

        self.assertEqual(data["battle_index"], 0)
        self.assertEqual(data["winner"], "p1")

    def test_finalize_battle_writes_markdown(self):
        """Test that finalize_battle writes markdown file."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.tracer.current_battle["total_turns"] = 5

        self.tracer.finalize_battle("p1")

        md_path = Path(self.temp_dir) / "test_run" / "battle_0.md"
        self.assertTrue(md_path.exists())

        with open(md_path) as f:
            content = f.read()

        self.assertIn("Battle 0", content)
        self.assertIn("p1 win", content)

    def test_finalize_battle_writes_protocol_log_when_valid(self):
        """Test protocol log file is written only with valid data."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.tracer.current_battle["protocol_log"] = [
            "|start p1: Pikachu",
            "|move p1: Thunderbolt",
            "|damage p2: 25%",
        ]

        self.tracer.finalize_battle("p1")

        log_path = Path(self.temp_dir) / "test_run" / "battle_0.showdown.log"
        self.assertTrue(log_path.exists())

        with open(log_path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("|"))

    def test_finalize_battle_skips_empty_protocol_log(self):
        """Test protocol log file is not written with empty data."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.tracer.current_battle["protocol_log"] = []

        self.tracer.finalize_battle("p1")

        log_path = Path(self.temp_dir) / "test_run" / "battle_0.showdown.log"
        self.assertFalse(log_path.exists())

    def test_multiple_battles_isolation(self):
        """Test that tracing multiple battles maintains isolation."""
        # Battle 1
        self.tracer.start_battle(0, "env-1", "gen9randombattle")
        self.tracer.add_turn(1, {"species": "A"}, {"species": "B"}, {"choice": "move 1"})
        self.tracer.finalize_battle("p1")

        # Battle 2
        self.tracer.start_battle(1, "env-2", "gen9randombattle")
        self.tracer.add_turn(1, {"species": "C"}, {"species": "D"}, {"choice": "move 2"})
        self.tracer.finalize_battle("p2")

        # Verify both files exist
        json_path_0 = Path(self.temp_dir) / "test_run" / "battle_0.json"
        json_path_1 = Path(self.temp_dir) / "test_run" / "battle_1.json"

        self.assertTrue(json_path_0.exists())
        self.assertTrue(json_path_1.exists())

        with open(json_path_0) as f:
            data0 = json.load(f)
        with open(json_path_1) as f:
            data1 = json.load(f)

        self.assertEqual(data0["battle_index"], 0)
        self.assertEqual(data1["battle_index"], 1)
        self.assertEqual(data0["winner"], "p1")
        self.assertEqual(data1["winner"], "p2")

    def test_build_markdown_handles_new_style_steps(self):
        """Test markdown generation with new-style step format."""
        self.tracer.start_battle(0, "env-1", "gen9randombattle")

        # Create new-style step
        self.tracer.current_battle["turns"] = [
            {
                "turn": 1,
                "steps": [
                    {
                        "p1_species": "Pikachu",
                        "p1_hp_ratio": 0.75,
                        "p1_status": None,
                        "chosen_action_label": "Thunderbolt",
                        "legal_actions_count": 5,
                        "chosen_action_probability": 0.85,
                    }
                ]
            }
        ]

        lines = self.tracer._build_markdown_lines()
        content = "\n".join(lines)

        self.assertIn("Pikachu", content)
        self.assertIn("75%", content)
        self.assertIn("85.0%", content)


if __name__ == "__main__":
    unittest.main()
