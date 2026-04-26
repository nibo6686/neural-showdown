"""Test suite for loop detection module."""

import unittest
from typing import Any, Dict, List

from neural.loop_detector import LoopDetector, detect_all_loops


class TestLoopDetector(unittest.TestCase):
    """Test LoopDetector class functionality."""

    def setUp(self):
        """Initialize detector for each test."""
        self.detector = LoopDetector()

    def _make_record(
        self,
        battle_index: int,
        opponent: str = "Chansey",
        move: str = "Earthquake",
        hp_ratio: float = 0.5,
    ) -> Dict[str, Any]:
        """Helper to create a mock record."""
        return {
            "battle_index": battle_index,
            "view": {
                "active": {"opponent": 0},
                "opponent_team": [{"name": opponent, "hp_ratio": hp_ratio}],
            },
            "choice": f"move {move}",
            "request": {"active": {"moves": [{"move": move}]}},
        }

    def test_detect_repeated_move_streak(self):
        """Test detection of repeated same move."""
        moves = ["Earthquake", "Earthquake", "Earthquake", "Earthquake", "Earthquake", "Protect"]
        opponents = ["Chansey"] * 6
        record_indices = list(range(6))

        diagnostics = self.detector._detect_repeated_move_streak(
            moves, opponents, record_indices, threshold=5
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("Repeated 'Earthquake'", diagnostics[0][0])

    def test_detect_repeated_move_streak_below_threshold(self):
        """Test no detection when streak is below threshold."""
        moves = ["Earthquake", "Earthquake", "Earthquake", "Protect"]
        opponents = ["Chansey"] * 4
        record_indices = list(range(4))

        diagnostics = self.detector._detect_repeated_move_streak(
            moves, opponents, record_indices, threshold=5
        )

        self.assertEqual(len(diagnostics), 0)

    def test_detect_wall_loop(self):
        """Test detection of wall loops."""
        opponents = ["Chansey"] * 20
        moves = ["Earthquake"] * 20
        hp_ratios = [1.0] + [0.95 + (i * 0.001) for i in range(19)]  # Minimal progress
        record_indices = list(range(20))

        diagnostics = self.detector._detect_wall_loop(
            opponents, moves, hp_ratios, record_indices, turn_threshold=15, progress_threshold=0.1
        )

        self.assertTrue(len(diagnostics) > 0)
        self.assertIn("Wall loop", diagnostics[0][0])

    def test_detect_wall_loop_with_progress(self):
        """Test no wall loop detection with sufficient progress."""
        opponents = ["Chansey"] * 20
        moves = ["Earthquake"] * 20
        hp_ratios = [1.0 - (i * 0.1) for i in range(20)]  # Significant progress
        record_indices = list(range(20))

        diagnostics = self.detector._detect_wall_loop(
            opponents, moves, hp_ratios, record_indices, turn_threshold=15, progress_threshold=0.1
        )

        self.assertEqual(len(diagnostics), 0)

    def test_detect_repeated_struggle(self):
        """Test detection of repeated Struggle usage."""
        moves = ["Earthquake", "Struggle", "Struggle", "Struggle", "Struggle", "Struggle", "Protect"]
        record_indices = list(range(7))

        diagnostics = self.detector._detect_repeated_struggle(moves, record_indices)

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("Repeated Struggle", diagnostics[0][0])

    def test_detect_repeated_struggle_below_threshold(self):
        """Test no Struggle detection below threshold."""
        moves = ["Earthquake", "Struggle", "Struggle", "Struggle", "Protect"]
        record_indices = list(range(5))

        diagnostics = self.detector._detect_repeated_struggle(moves, record_indices)

        self.assertEqual(len(diagnostics), 0)

    def test_extract_move_name(self):
        """Test move name extraction from choice string."""
        choice = "move 1"
        request = {"active": {"moves": [{"move": "Earthquake"}]}}

        move = self.detector._extract_move_name(choice, request)

        self.assertEqual(move, "Earthquake")

    def test_extract_move_name_invalid_format(self):
        """Test move name extraction with invalid format."""
        choice = "invalid"
        request = {"active": {"moves": [{"move": "Earthquake"}]}}

        move = self.detector._extract_move_name(choice, request)

        self.assertIsNone(move)

    def test_detect_loops_in_battle_short_battle(self):
        """Test no detection for battles shorter than threshold."""
        records = [self._make_record(0) for _ in range(3)]
        battle_records = [0, 1, 2]

        diagnostics = self.detector.detect_loops_in_battle(records, battle_records)

        self.assertEqual(len(diagnostics), 0)

    def test_detect_all_loops_multiple_battles(self):
        """Test loop detection across multiple battles."""
        records = []

        # Battle 0: normal
        for i in range(5):
            records.append(self._make_record(0, move=f"move{i%2}"))

        # Battle 1: repeated move
        for i in range(10):
            records.append(self._make_record(1, move="Earthquake"))

        result = detect_all_loops(records, max_same_action_streak=5)

        # Should detect loop in battle 1
        self.assertIn(1, result)
        self.assertTrue(len(result[1]) > 0)


if __name__ == "__main__":
    unittest.main()
