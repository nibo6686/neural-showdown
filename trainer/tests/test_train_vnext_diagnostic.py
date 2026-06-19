import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural.train_vnext_diagnostic import (
    EXPECTED_ACTION_DIM,
    EXPECTED_STATE_DIM,
    _names_fingerprint,
    build_diagnostic_model,
    forward_loss_smoke_check,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
    main,
)


def _names(prefix, count):
    return [f"{prefix}_{index}" for index in range(count)]


def _write_fixture(
    root: Path,
    *,
    action_dim: int = EXPECTED_ACTION_DIM,
    metadata_state_version: str = "live-private-belief-v7",
    leak_split: bool = False,
    multi_positive: bool = False,
    zero_positive: bool = False,
    include_action_value: bool = False,
):
    state_names = _names("state", EXPECTED_STATE_DIM)
    action_names = _names("action", action_dim)
    replay_ids = (
        [f"train-{index}" for index in range(210)]
        + [f"validation-{index}" for index in range(45)]
        + [f"test-{index}" for index in range(45)]
    )
    splits = ["train"] * 210 + ["validation"] * 45 + ["test"] * 45
    if leak_split:
        replay_ids[210] = replay_ids[0]
    states = np.zeros((300, EXPECTED_STATE_DIM), dtype=np.float16)
    actions = np.zeros((600, action_dim), dtype=np.float16)
    candidate_state_indices = np.repeat(np.arange(300, dtype=np.int32), 2)
    labels = np.tile(np.asarray([1, 0], dtype=np.int8), 300)
    if multi_positive:
        labels[1] = 1
    if zero_positive:
        labels[0] = 0
    arrays = {
        "state_features": states,
        "state_replay_ids": np.asarray(replay_ids),
        "state_splits": np.asarray(splits),
        "state_turns": np.arange(300, dtype=np.int16),
        "state_value_targets": np.tile(
            np.asarray([1.0, -1.0], dtype=np.float32), 150
        ),
        "action_features": actions,
        "candidate_state_indices": candidate_state_indices,
        "candidate_action_indices": np.tile(
            np.asarray([0, 1], dtype=np.int16), 300
        ),
        "candidate_kinds": np.asarray(["move", "switch"] * 300),
        "action_rank_labels": labels,
        "state_feature_version": np.asarray("live-private-belief-v7"),
        "state_feature_names": np.asarray(state_names),
        "action_feature_version": np.asarray("legal-action-v5"),
        "action_feature_names": np.asarray(action_names),
        "manifest_catalog_checksum": np.asarray("catalog-checksum"),
    }
    if include_action_value:
        arrays["action_value_targets"] = np.zeros(600, dtype=np.float32)
    dataset_path = root / "dataset.npz"
    np.savez_compressed(dataset_path, **arrays)

    metadata_path = root / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "state_feature_version": metadata_state_version,
                "state_feature_dim": EXPECTED_STATE_DIM,
                "state_feature_names_sha256": _names_fingerprint(state_names),
                "action_feature_version": "legal-action-v5",
                "action_feature_dim": action_dim,
                "action_feature_names_sha256": _names_fingerprint(action_names),
                "dtype_on_disk": "float16",
                "storage_layout": (
                    "one state row per decision; separate candidate action rows "
                    "linked by candidate_state_indices"
                ),
                "state_vectors_duplicated_per_candidate": False,
                "manifest_catalog_checksum": "catalog-checksum",
                "action_value_target_status": "not_generated",
                "selected_replay_ids": replay_ids,
                "selected_splits": dict(zip(replay_ids, splits)),
            }
        ),
        encoding="utf-8",
    )
    report_path = root / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "split_battle_counts": {
                    "train": 210,
                    "validation": 45,
                    "test": 45,
                },
                "action_value_labels_generated": 0,
                "chosen_action_unmatched_count": 7,
                "skip_reasons": {"initial_deployment_nondecision": 4},
            }
        ),
        encoding="utf-8",
    )
    config = {
        "profile": "test",
        "implementation_status": "implemented_validate_only_tested",
        "entrypoint": "neural.train_vnext_diagnostic",
        "dataset": {
            "path": "dataset.npz",
            "metadata_path": "metadata.json",
            "materialization_report_path": "report.json",
            "state_feature_version": "live-private-belief-v7",
            "state_feature_dim": EXPECTED_STATE_DIM,
            "state_feature_names_sha256": _names_fingerprint(state_names),
            "action_feature_version": "legal-action-v5",
            "action_feature_dim": EXPECTED_ACTION_DIM,
            "action_feature_names_sha256": _names_fingerprint(
                _names("action", EXPECTED_ACTION_DIM)
            ),
            "dtype_on_disk": "float16",
            "storage_layout": "separate_state_and_candidate_tables",
            "expected_battle_split_counts": {
                "train": 210,
                "validation": 45,
                "test": 45,
            },
            "split_source": "state_splits",
            "train_split": "train",
            "validation_split": "validation",
            "test_split": "test",
        },
        "objectives": {
            "state_value": {
                "enabled": True,
                "target": "state_value_targets",
                "loss": "mean_squared_error",
                "loss_weight": 1.0,
            },
            "action_rank": {
                "enabled": True,
                "target": "action_rank_labels",
                "group_index": "candidate_state_indices",
                "loss": "grouped_cross_entropy",
                "loss_weight": 1.0,
            },
            "action_value": {"enabled": False},
        },
        "model": {
            "type": "shared_state_action_diagnostic_mlp",
            "state_encoder_hidden_sizes": [64],
            "action_encoder_hidden_sizes": [32],
            "rank_head_hidden_sizes": [32],
            "activation": "relu",
            "value_output": "tanh",
            "dropout": 0.0,
            "expected_parameter_count_approx": 218786,
        },
        "training": {
            "seed": 1,
            "epochs": 1,
            "value_batch_size": 8,
            "rank_groups_per_batch": 4,
            "learning_rate": 0.001,
            "weight_decay": 0.0001,
            "gradient_clip_norm": 1.0,
            "save_every_epochs": 1,
            "early_stopping_patience_epochs": 1,
        },
        "outputs": {
            "directory": "output",
            "checkpoint_path": "output/model.pt",
            "best_checkpoint_path": "output/model.best.pt",
            "report_json_path": "output/report.json",
            "report_md_path": "output/report.md",
            "production_eligible": False,
        },
    }
    config_path = root / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


class VNextDiagnosticTrainingTest(unittest.TestCase):
    def test_config_parsing_and_dataset_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir))
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
        self.assertEqual(dataset.validation["state_dim"], EXPECTED_STATE_DIM)
        self.assertEqual(dataset.validation["action_dim"], EXPECTED_ACTION_DIM)
        self.assertEqual(
            dataset.validation["battle_split_counts"],
            {"train": 210, "validation": 45, "test": 45},
        )
        self.assertEqual(dataset.validation["included_action_groups"], 300)
        self.assertEqual(dataset.validation["action_value_label_count"], 0)

    def test_metadata_schema_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(
                Path(tmpdir), metadata_state_version="live-private-belief-v6"
            )
            config = load_and_validate_diagnostic_config(config_path)
            with self.assertRaisesRegex(ValueError, "metadata state schema mismatch"):
                load_diagnostic_dataset(config)

    def test_split_leakage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), leak_split=True)
            config = load_and_validate_diagnostic_config(config_path)
            with self.assertRaisesRegex(ValueError, "split leakage"):
                load_diagnostic_dataset(config)

    def test_action_dimension_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(
                Path(tmpdir), action_dim=EXPECTED_ACTION_DIM - 1
            )
            config = load_and_validate_diagnostic_config(config_path)
            with self.assertRaisesRegex(ValueError, "Action feature dimension mismatch"):
                load_diagnostic_dataset(config)

    def test_multi_positive_group_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), multi_positive=True)
            config = load_and_validate_diagnostic_config(config_path)
            with self.assertRaisesRegex(ValueError, "at most one"):
                load_diagnostic_dataset(config)

    def test_zero_positive_group_is_masked_and_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), zero_positive=True)
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
        self.assertEqual(dataset.validation["ignored_zero_positive_action_groups"], 1)
        self.assertEqual(dataset.validation["included_action_groups"], 299)
        self.assertNotIn(
            0, set(dataset.split_group_state_indices["train"].tolist())
        )

    def test_action_value_arrays_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), include_action_value=True)
            config = load_and_validate_diagnostic_config(config_path)
            with self.assertRaisesRegex(ValueError, "action-value/Q-value"):
                load_diagnostic_dataset(config)

    def test_model_forward_and_loss_shapes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir))
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
            model = build_diagnostic_model(config)
            report = forward_loss_smoke_check(model, dataset)
        self.assertEqual(report["value_output_shape"], [8])
        self.assertEqual(report["rank_group_count"], 4)
        self.assertGreater(report["rank_output_shape"][0], 4)
        self.assertEqual(report["optimizer_steps"], 0)

    def test_validate_only_creates_no_optimizer_or_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root)
            with patch(
                "neural.train_vnext_diagnostic.torch.optim.AdamW",
                side_effect=AssertionError("optimizer must not be created"),
            ):
                report = main(["--config", str(config_path), "--validate-only"])
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["optimizer_created"])
            self.assertEqual(report["optimizer_steps"], 0)
            self.assertFalse(report["training_launched"])
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
