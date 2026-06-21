import json
import tempfile
import unittest
from pathlib import Path

from neural.randbats_meta_prior_audit import audit_manifest


class RandbatsMetaPriorAuditTest(unittest.TestCase):
    def test_tiny_manifest_keeps_suffix_and_hidden_truth_causal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            replay = root / "fixture.log"
            replay.write_text(
                "\n".join(
                    [
                        "|switch|p1a: Dondozo|Dondozo, L78|100/100",
                        "|switch|p2a: Hatterene|Hatterene, L85|100/100",
                        "|turn|1",
                        "|move|p2a: Hatterene|Psychic|p1a: Dondozo",
                        "|turn|2",
                        "|-ability|p2a: Hatterene|Magic Bounce",
                        "|-terastallize|p2a: Hatterene|Steel",
                    ]
                ),
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "replay_id": "fixture",
                                "path": str(replay),
                                "split": "test",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            source = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "random-battles"
                / "gen9"
                / "sets.json"
            )
            summary = audit_manifest(
                manifest_path=manifest,
                prior_source_path=source,
                split="test",
                limit=1,
            )
        self.assertEqual(summary["battle_count"], 1)
        self.assertEqual(summary["species_coverage_pct"], 100.0)
        self.assertEqual(summary["prefix_causality_failures"], [])
        self.assertEqual(summary["hidden_truth_failures"], [])
        self.assertEqual(
            summary["event_support"]["ability_revealed"]["support_pct"], 100.0
        )
        self.assertEqual(
            summary["event_support"]["tera_type_revealed"]["support_pct"], 100.0
        )


if __name__ == "__main__":
    unittest.main()
