import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.build_value_dataset import build_value_dataset, examples_from_trace_path
from neural.value_features import discounted_terminal_return


def write_tiny_trace(path: Path, winner: str = "p1") -> None:
    trace = {
        "battle_index": 0,
        "env_id": "env-1",
        "format": "gen9randombattle",
        "winner": winner,
        "turns": [
            {
                "turn": 1,
                "steps": [
                    {
                        "step_index": 0,
                        "p1_species": "Pikachu",
                        "p1_hp_ratio": 1.0,
                        "p1_status": None,
                        "p1_boosts": {},
                        "p2_species": "Charizard",
                        "p2_hp_ratio": 1.0,
                        "p2_status": None,
                        "legal_actions": [
                            {"index": 0, "kind": "move", "choice": "move 1", "label": "move:Thunderbolt", "move": "Thunderbolt"},
                            {"index": 8, "kind": "switch", "choice": "switch 1", "label": "switch:Bulbasaur"},
                        ],
                        "chosen_action_index": 0,
                        "protocol_log": ["|move|p1a: Pikachu|Thunderbolt|p2a: Charizard"],
                    }
                ],
            },
            {
                "turn": 2,
                "steps": [
                    {
                        "step_index": 1,
                        "p1_species": "Pikachu",
                        "p1_hp_ratio": 0.5,
                        "p1_status": "par",
                        "p1_boosts": {},
                        "p2_species": "Charizard",
                        "p2_hp_ratio": 0.0,
                        "p2_status": None,
                        "legal_actions": [
                            {"index": 0, "kind": "move", "choice": "move 1", "label": "move:Thunderbolt", "move": "Thunderbolt"}
                        ],
                        "chosen_action_index": 0,
                        "protocol_log": ["|faint|p2a: Charizard"],
                    }
                ],
            },
        ],
    }
    path.write_text(json.dumps(trace), encoding="utf-8")


class ValueDatasetTest(unittest.TestCase):
    def test_discounted_terminal_return(self):
        self.assertEqual(discounted_terminal_return(1.0, 0, 0.5), 1.0)
        self.assertEqual(discounted_terminal_return(1.0, 2, 0.5), 0.25)
        self.assertEqual(discounted_terminal_return(-1.0, 1, 0.5), -0.5)

    def test_value_targets_from_win_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "battle_0.json"
            write_tiny_trace(trace_path, winner="p1")
            examples = examples_from_trace_path(trace_path, gamma=0.5)
            self.assertEqual(len(examples), 2)
            self.assertEqual(examples[0]["final_result"], 1.0)
            self.assertEqual(examples[0]["value_target"], 0.5)
            self.assertEqual(examples[1]["value_target"], 1.0)

    def test_value_targets_from_loss_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "battle_0.json"
            write_tiny_trace(trace_path, winner="p2")
            examples = examples_from_trace_path(trace_path, gamma=0.5)
            self.assertEqual(examples[0]["final_result"], -1.0)
            self.assertEqual(examples[0]["value_target"], -0.5)

    def test_build_value_dataset_writes_npz_and_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_dir = root / "traces"
            trace_dir.mkdir()
            write_tiny_trace(trace_dir / "battle_0.json")
            output = root / "value.npz"
            report_json = root / "report.json"
            report_md = root / "report.md"
            report = build_value_dataset(
                trace_dirs=[trace_dir],
                output_path=output,
                report_json_path=report_json,
                report_md_path=report_md,
                gamma=1.0,
            )
            self.assertEqual(report["examples"], 2)
            self.assertTrue(output.exists())
            self.assertTrue(report_json.exists())
            self.assertTrue(report_md.exists())
            with np.load(output) as data:
                self.assertEqual(data["states"].shape[0], 2)
                self.assertIn("value_targets", data.files)
                self.assertIn("legal_masks", data.files)


if __name__ == "__main__":
    unittest.main()
