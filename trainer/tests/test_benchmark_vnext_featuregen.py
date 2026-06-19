import unittest

import numpy as np

from neural.benchmark_vnext_featuregen import (
    benchmark_metadata,
    select_manifest_subset,
    validate_benchmark_arrays,
)


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
            "state_replay_ids": np.asarray([selected[0]["replay_id"], selected[1]["replay_id"]]),
            "state_splits": np.asarray([selected[0]["split"], selected[1]["split"]]),
        }
        self.assertTrue(validate_benchmark_arrays(arrays, metadata)["passed"])
        arrays["action_features"] = np.zeros((3, 317), dtype=np.float16)
        result = validate_benchmark_arrays(arrays, metadata)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["action_dim_318"])


if __name__ == "__main__":
    unittest.main()
