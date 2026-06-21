import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from neural.replay_pool_profiler import MECHANIC_FLAGS
from neural.replay_sample_manifest import (
    ACTION_RANK_SPLIT_TARGETS,
    ACTION_RANK_TOTAL,
    SWITCH_HEAVY_MIN,
    _fits_frozen_six_slot_schema,
    generate_action_rank_manifest,
)


def _write_catalog(root: Path, n: int = 1200) -> Path:
    dummy = root / "replay.json"
    dummy.write_text("{}", encoding="utf-8")
    rows = []
    for i in range(n):
        # Broad, generous distributions so every enrichment bucket is satisfiable.
        all_mech = i % 3 == 0
        mechanics = {name: bool(all_mech or (i % 5 == 0)) for name in MECHANIC_FLAGS}
        rows.append(
            {
                "replay_id": f"r{i}",
                "path": str(dummy),
                "eligible_diagnostic_300": True,
                "parse_error": False,
                "mechanics": mechanics,
                "rating": (1000 + i) if i % 4 != 0 else None,
                "turn_count": 10 + (i % 40),
                "approx_decision_state_count": 20 + (i % 60),
                "long_game": i % 2 == 0,
                "close_game_proxy": i % 3 == 0,
                "early_forfeit_or_short": i % 7 == 0,
                "raw_command_counts": {
                    "input:move": 40,
                    "input:switch": SWITCH_HEAVY_MIN + (i % 10) if i % 2 == 0 else 3,
                    "-terastallize": (i % 3) if i % 2 == 0 else 0,
                },
            }
        )
    catalog = root / "catalog.jsonl"
    catalog.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return catalog


class ActionRankManifestTest(unittest.TestCase):
    def test_rejects_protocol_team_sizes_above_six(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            replay = Path(tmpdir) / "custom.log"
            replay.write_text("|teamsize|p1|8\n|teamsize|p2|8\n", encoding="utf-8")
            self.assertFalse(_fits_frozen_six_slot_schema({"path": str(replay)}))

    def test_generates_valid_1000_battle_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = _write_catalog(root)
            output = root / "manifest.json"
            manifest, report = generate_action_rank_manifest(
                catalog_path=catalog, output_path=output
            )

            self.assertTrue(report["passed"], report["checks"])
            self.assertEqual(len(manifest["entries"]), ACTION_RANK_TOTAL)
            ids = [e["replay_id"] for e in manifest["entries"]]
            self.assertEqual(len(set(ids)), ACTION_RANK_TOTAL)
            self.assertEqual(
                Counter(e["split"] for e in manifest["entries"]),
                Counter(ACTION_RANK_SPLIT_TARGETS),
            )
            # No battle crosses splits (unique ids already guarantee this here).
            self.assertEqual(report["split_counts"], ACTION_RANK_SPLIT_TARGETS)
            # Frozen schema metadata is recorded.
            self.assertEqual(manifest["state_feature_version"], "live-private-belief-v7")
            self.assertEqual(manifest["action_feature_version"], "legal-action-v5")
            # Enrichment lifts switch volume above the random baseline without distortion.
            sel = manifest["selected_enrichment"]
            base = manifest["random_baseline"]["enrichment"]
            self.assertGreaterEqual(sel["switch_decision_total"], base["switch_decision_total"])
            self.assertTrue(output.exists())
            self.assertTrue(output.with_name(output.stem + "_report.md").exists())

    def test_rejects_insufficient_pool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = _write_catalog(root, n=500)
            with self.assertRaisesRegex(ValueError, "eligible unique replays"):
                generate_action_rank_manifest(
                    catalog_path=catalog, output_path=root / "m.json"
                )


if __name__ == "__main__":
    unittest.main()
