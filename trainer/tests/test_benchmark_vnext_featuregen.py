import unittest
from pathlib import Path

import numpy as np

from neural.benchmark_vnext_featuregen import (
    _validate_full_preflight,
    _completed_teams_for_action_reconstruction,
    _trajectory_prefix_before_event,
    benchmark_metadata,
    select_manifest_subset,
    validate_benchmark_arrays,
)
from neural.action_features import ACTION_FEATURE_NAMES_V5
from neural.live_private_features import FEATURE_NAMES_V7


def _entry(index, split):
    mechanics = {
        "tera": index % 2 == 0,
        "transform": index % 5 == 0,
        "tailwind": index % 7 == 0,
    }
    return {
        "replay_id": f"battle-{index}",
        "path": f"battle-{index}.log",
        "split": split,
        "profile_version": "replay-pool-profile-v1",
        "turn_count": 15 + index,
        "mechanics": mechanics,
    }


class VNextFeaturegenBenchmarkTest(unittest.TestCase):
    def setUp(self):
        entries = (
            [_entry(index, "train") for index in range(20)]
            + [_entry(100 + index, "validation") for index in range(10)]
            + [_entry(200 + index, "test") for index in range(10)]
        )
        self.manifest = {
            "manifest_version": "diagnostic-300-manifest-v1",
            "seed": 123,
            "catalog_checksum": "abc",
            "entries": entries,
        }

    def test_subset_selection_is_deterministic_and_split_preserving(self):
        first = select_manifest_subset(self.manifest, size=10, seed=9)
        second = select_manifest_subset(self.manifest, size=10, seed=9)
        self.assertEqual(first, second)
        self.assertEqual(len({row["replay_id"] for row in first}), 10)
        self.assertEqual(sum(row["split"] == "train" for row in first), 4)
        self.assertEqual(sum(row["split"] == "validation" for row in first), 3)
        self.assertEqual(sum(row["split"] == "test" for row in first), 3)

    def test_metadata_records_v7_v5_and_live_defaults(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(manifest=self.manifest, selected_entries=selected, seed=9)
        self.assertEqual(metadata["state_feature_version"], "live-private-belief-v7")
        self.assertEqual(metadata["state_feature_dim"], 3208)
        self.assertEqual(metadata["action_feature_version"], "legal-action-v5")
        self.assertEqual(metadata["action_feature_dim"], 318)
        self.assertEqual(len(metadata["state_feature_names_sha256"]), 64)
        self.assertEqual(len(metadata["action_feature_names_sha256"]), 64)
        self.assertEqual(metadata["live_default_state_feature_version"], "live-private-belief-v2")
        self.assertEqual(metadata["live_default_action_feature_version"], "legal-action-v3")
        self.assertFalse(metadata["state_vectors_duplicated_per_candidate"])

    def test_array_validation_checks_dimensions_and_split_separation(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(manifest=self.manifest, selected_entries=selected, seed=9)
        arrays = {
            "state_features": np.zeros((2, 3208), dtype=np.float16),
            "action_features": np.zeros((3, 318), dtype=np.float16),
            "candidate_state_indices": np.asarray([0, 0, 1], dtype=np.int32),
            "state_value_targets": np.asarray([1.0, -1.0], dtype=np.float32),
            "action_rank_labels": np.asarray([1, 0, 1], dtype=np.int8),
            "state_replay_ids": np.asarray([selected[0]["replay_id"], selected[1]["replay_id"]]),
            "state_splits": np.asarray([selected[0]["split"], selected[1]["split"]]),
            "state_feature_names": np.asarray(FEATURE_NAMES_V7),
            "action_feature_names": np.asarray(ACTION_FEATURE_NAMES_V5),
        }
        self.assertTrue(validate_benchmark_arrays(arrays, metadata)["passed"])
        arrays["action_features"] = np.zeros((3, 317), dtype=np.float16)
        result = validate_benchmark_arrays(arrays, metadata)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["action_dim_318"])

    def test_full_preflight_rejects_non_diagnostic_output(self):
        with self.assertRaises(ValueError):
            _validate_full_preflight(
                manifest=self.manifest,
                manifest_path=Path("artifacts/training_plan/manifests/diagnostic_300_manifest.json"),
                output_dir=Path("data/production"),
            )

    def test_completed_team_assigns_moves_to_active_species_not_actor_alias(self):
        switch = {"type": "switch", "side": "p1", "details": "Dugtrio-Alola, L84", "actor": "p1a: Dugtrio"}
        move = {"type": "move", "side": "p1", "actor": "p1a: Dugtrio", "move": "Stealth Rock"}
        trajectory = {"turns": [{"turn": 0, "events": [switch]}, {"turn": 1, "events": [move]}], "protocol_log": []}
        teams = _completed_teams_for_action_reconstruction(trajectory)
        self.assertIn("Stealth Rock", teams["p1"]["Dugtrio-Alola"]["moves"])
        self.assertNotIn("Dugtrio", teams["p1"])

    def test_pre_action_prefix_stops_before_same_decision_tera_event(self):
        tera = {"type": "tera", "side": "p1", "raw": "|-terastallize|p1a: X|Ghost"}
        move = {"type": "move", "side": "p1", "move": "Shadow Ball", "raw": "|move|p1a: X|Shadow Ball|p2a: Y"}
        trajectory = {
            "turns": [{"turn": 1, "events": [tera, move]}],
            "protocol_log": ["|turn|1", tera["raw"], move["raw"]],
        }
        prefix = _trajectory_prefix_before_event(
            trajectory, turn_number=1, event=move, turn_events=[tera, move]
        )
        self.assertNotIn(tera["raw"], prefix["protocol_log"])


if __name__ == "__main__":
    unittest.main()
