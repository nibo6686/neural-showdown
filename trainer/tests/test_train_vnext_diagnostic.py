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
    build_vnext_checkpoint_metadata,
    forward_loss_smoke_check,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
    main,
    validate_vnext_checkpoint_metadata,
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
    rank_enabled: bool = True,
    value_enabled: bool = True,
    overfit_enabled: bool = True,
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
                "enabled": value_enabled,
                "target": "state_value_targets",
                "loss": "mean_squared_error",
                "loss_weight": 1.0 if value_enabled else 0.0,
            },
            "action_rank": {
                "enabled": rank_enabled,
                "target": "action_rank_labels",
                "group_index": "candidate_state_indices",
                "loss": "grouped_cross_entropy",
                "loss_weight": 1.0 if rank_enabled else 0.0,
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
        "overfit_check": {
            "enabled": overfit_enabled,
            "state_examples": 8,
            "action_groups": 4 if rank_enabled else 0,
            "max_steps": 2,
            "required_value_train_mse_max": 2.0,
            "required_action_train_top1_min": 0.0,
            "fail_main_run_if_not_met": True,
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
    def test_config_explicitly_accepts_v6_dimension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_fixture(Path(tmpdir))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["dataset"]["action_feature_version"] = "legal-action-v6"
            payload["dataset"]["action_feature_dim"] = 331
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_and_validate_diagnostic_config(path)
        self.assertEqual(config["dataset"]["action_feature_version"], "legal-action-v6")
        self.assertEqual(config["dataset"]["action_feature_dim"], 331)

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

    def test_value_only_validate_skips_rank_forward(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), rank_enabled=False)
            with patch(
                "neural.models.vnext_diagnostic.VNextDiagnosticMLP.rank_from_embeddings",
                side_effect=AssertionError("rank forward must stay disabled"),
            ):
                report = main(["--config", str(config_path), "--validate-only"])
        self.assertFalse(report["heads_enabled"]["action_rank"])
        self.assertFalse(report["smoke_check"]["rank_enabled"])
        self.assertIsNone(report["smoke_check"]["action_rank_loss"])
        self.assertEqual(report["smoke_check"]["rank_group_count"], 0)

    def test_value_only_training_uses_only_value_batches(self):
        from neural.train_vnext_diagnostic import train_diagnostic

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(
                root,
                rank_enabled=False,
                overfit_enabled=False,
            )
            with patch(
                "neural.train_vnext_diagnostic._rank_batch",
                side_effect=AssertionError("rank batches must stay disabled"),
            ), patch(
                "neural.train_vnext_diagnostic._rank_metrics",
                side_effect=AssertionError("rank metrics must stay disabled"),
            ):
                report = train_diagnostic(config_path)
        self.assertFalse(report["heads_trained"]["action_rank"])
        self.assertEqual(report["optimizer_step_source"], "value_batches_only")
        self.assertEqual(report["global_step"], 27)
        self.assertIsNone(report["test_action_rank"])
        self.assertEqual(report["test_split_evaluations"], 1)


class VNextRankOnlyTrainingTest(unittest.TestCase):
    def test_validate_only_rank_only_disables_value_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir), value_enabled=False)
            report = main(["--config", str(config_path), "--validate-only"])
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["heads_enabled"]["state_value"])
        self.assertTrue(report["heads_enabled"]["action_rank"])
        self.assertFalse(report["heads_enabled"]["action_value"])
        self.assertEqual(report["optimizer_step_source"], "rank_batches_only")
        self.assertFalse(report["smoke_check"]["value_enabled"])
        self.assertIsNone(report["smoke_check"]["value_loss"])
        self.assertIsNotNone(report["smoke_check"]["action_rank_loss"])

    def test_rank_only_training_uses_only_rank_batches(self):
        from neural.train_vnext_diagnostic import train_diagnostic

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root, value_enabled=False, overfit_enabled=False)
            # The value head must never be exercised in a rank-only run.
            with patch(
                "neural.models.vnext_diagnostic.VNextDiagnosticMLP.value_from_embedding",
                side_effect=AssertionError("value head must stay disabled"),
            ):
                report = train_diagnostic(config_path)
        self.assertFalse(report["heads_trained"]["state_value"])
        self.assertTrue(report["heads_trained"]["action_rank"])
        self.assertEqual(report["optimizer_step_source"], "rank_batches_only")
        self.assertEqual(report["checkpoint_selection_metric"], "validation_action_rank_nll")
        self.assertIsNone(report["test_value"])
        self.assertIsNone(report["best_validation_value_mse"])
        self.assertIsNotNone(report["test_action_rank"])
        self.assertEqual(report["test_split_evaluations"], 1)


class VNextLiveReadinessAuditTest(unittest.TestCase):
    def test_audit_validates_schema_and_matches_offline_scorer(self):
        from neural.audit_vnext_live_inference_readiness import (
            audit_readiness,
            candidate_to_showdown_command,
        )

        self.assertEqual(candidate_to_showdown_command("move", 2), "move 2")
        self.assertEqual(
            candidate_to_showdown_command("move_tera", 2), "move 2 terastallize"
        )
        self.assertEqual(candidate_to_showdown_command("switch", 5), "switch 5")
        self.assertNotEqual(
            candidate_to_showdown_command("move", 2),
            candidate_to_showdown_command("move_tera", 2),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root)
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
            model = build_diagnostic_model(config)
            checkpoint = {
                "model_state_dict": model.state_dict(),
                **build_vnext_checkpoint_metadata(dataset),
                "model_config": config["model"],
            }
            checkpoint_path = root / "audit_model.pt"
            torch.save(checkpoint, checkpoint_path)
            summary = audit_readiness(config_path, checkpoint_path, split="validation")

        self.assertEqual(summary["schema_validation"]["status"], "PASS")
        self.assertTrue(summary["schema_validation"]["fingerprints_complete"])
        self.assertTrue(summary["all_selected_candidates_serializable"])
        self.assertTrue(summary["scoring_determinism_ok"])
        self.assertTrue(summary["offline_scorer_parity"]["top1_match"])
        self.assertFalse(summary["private_matches_run"])
        self.assertFalse(summary["live_defaults_changed"])

    def test_audit_requires_fingerprints(self):
        from neural.audit_vnext_live_inference_readiness import audit_readiness

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root)
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
            model = build_diagnostic_model(config)
            # Legacy-style checkpoint without fingerprints must be rejected for live use.
            checkpoint = {
                "model_state_dict": model.state_dict(),
                "state_feature_version": "live-private-belief-v7",
                "action_feature_version": "legal-action-v5",
                "state_dim": EXPECTED_STATE_DIM,
                "action_dim": EXPECTED_ACTION_DIM,
                "model_config": config["model"],
            }
            checkpoint_path = root / "legacy_no_fp.pt"
            torch.save(checkpoint, checkpoint_path)
            with self.assertRaisesRegex(ValueError, "missing required fingerprint"):
                audit_readiness(config_path, checkpoint_path, split="validation")


class VNextCheckpointSchemaGuardrailTest(unittest.TestCase):
    EXPECTED_STATE_FP = _names_fingerprint(_names("state", EXPECTED_STATE_DIM))
    EXPECTED_ACTION_FP = _names_fingerprint(_names("action", EXPECTED_ACTION_DIM))

    def _checkpoint_metadata(self, tmpdir):
        config_path = _write_fixture(Path(tmpdir))
        config = load_and_validate_diagnostic_config(config_path)
        dataset = load_diagnostic_dataset(config)
        return build_vnext_checkpoint_metadata(dataset)

    def test_built_metadata_includes_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        self.assertEqual(metadata["state_feature_version"], "live-private-belief-v7")
        self.assertEqual(metadata["action_feature_version"], "legal-action-v5")
        self.assertEqual(metadata["state_dim"], EXPECTED_STATE_DIM)
        self.assertEqual(metadata["action_dim"], EXPECTED_ACTION_DIM)
        self.assertEqual(metadata["state_feature_names_sha256"], self.EXPECTED_STATE_FP)
        self.assertEqual(metadata["action_feature_names_sha256"], self.EXPECTED_ACTION_FP)

    def test_saved_checkpoint_payload_includes_fingerprints(self):
        from neural.train_vnext_diagnostic import train_diagnostic

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root, rank_enabled=False, overfit_enabled=False)
            train_diagnostic(config_path)
            checkpoint = torch.load(
                root / "output" / "model.pt", map_location="cpu", weights_only=False
            )
        self.assertEqual(checkpoint["state_feature_names_sha256"], self.EXPECTED_STATE_FP)
        self.assertEqual(checkpoint["action_feature_names_sha256"], self.EXPECTED_ACTION_FP)
        self.assertEqual(checkpoint["state_feature_version"], "live-private-belief-v7")
        self.assertEqual(checkpoint["action_feature_version"], "legal-action-v5")
        self.assertEqual(checkpoint["state_dim"], EXPECTED_STATE_DIM)
        self.assertEqual(checkpoint["action_dim"], EXPECTED_ACTION_DIM)

    def test_matching_metadata_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        result = validate_vnext_checkpoint_metadata(
            metadata,
            expected_state_feature_names_sha256=self.EXPECTED_STATE_FP,
            expected_action_feature_names_sha256=self.EXPECTED_ACTION_FP,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["state_fingerprint_status"], "validated")
        self.assertEqual(result["action_fingerprint_status"], "validated")
        self.assertTrue(result["fingerprints_complete"])

    def test_wrong_state_schema_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        metadata["state_feature_version"] = "live-private-belief-v6"
        with self.assertRaisesRegex(ValueError, "state schema mismatch"):
            validate_vnext_checkpoint_metadata(metadata)

    def test_wrong_action_schema_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        metadata["action_feature_version"] = "legal-action-v3"
        with self.assertRaisesRegex(ValueError, "action schema mismatch"):
            validate_vnext_checkpoint_metadata(metadata)

    def test_wrong_state_dimension_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        metadata["state_dim"] = EXPECTED_STATE_DIM - 1
        with self.assertRaisesRegex(ValueError, "state dimension mismatch"):
            validate_vnext_checkpoint_metadata(metadata)

    def test_wrong_action_dimension_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        metadata["action_dim"] = EXPECTED_ACTION_DIM - 1
        with self.assertRaisesRegex(ValueError, "action dimension mismatch"):
            validate_vnext_checkpoint_metadata(metadata)

    def test_reordered_feature_fingerprint_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        reordered_fp = _names_fingerprint(
            list(reversed(_names("state", EXPECTED_STATE_DIM)))
        )
        self.assertNotEqual(reordered_fp, self.EXPECTED_STATE_FP)
        with self.assertRaisesRegex(ValueError, "state_feature_names_sha256 mismatch"):
            validate_vnext_checkpoint_metadata(
                metadata, expected_state_feature_names_sha256=reordered_fp
            )

    def test_missing_fingerprint_is_legacy_not_equivalent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = self._checkpoint_metadata(tmpdir)
        metadata.pop("state_feature_names_sha256")
        metadata.pop("action_feature_names_sha256")
        # Schema name/dim still validate, but fingerprints are flagged as legacy.
        result = validate_vnext_checkpoint_metadata(metadata)
        self.assertEqual(result["state_fingerprint_status"], "missing_legacy")
        self.assertEqual(result["action_fingerprint_status"], "missing_legacy")
        self.assertFalse(result["fingerprints_complete"])
        # And can be rejected outright when fingerprints are required.
        with self.assertRaisesRegex(ValueError, "missing required fingerprint"):
            validate_vnext_checkpoint_metadata(metadata, require_fingerprints=True)


class VNextActionRankOfflineEvalTest(unittest.TestCase):
    def test_evaluate_runs_on_validation_split_with_baselines(self):
        from neural.evaluate_vnext_action_rank import evaluate

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = _write_fixture(root)
            config = load_and_validate_diagnostic_config(config_path)
            dataset = load_diagnostic_dataset(config)
            model = build_diagnostic_model(config)
            checkpoint = {
                "model_state_dict": model.state_dict(),
                **build_vnext_checkpoint_metadata(dataset),
                "model_config": config["model"],
            }
            checkpoint_path = root / "eval_model.pt"
            torch.save(checkpoint, checkpoint_path)
            summary = evaluate(config_path, checkpoint_path, split="validation")

        self.assertEqual(summary["split"], "validation")
        self.assertEqual(summary["matched_groups"], 45)
        self.assertEqual(summary["schema_validation"]["status"], "PASS")
        for key in ("top1", "top3", "mrr", "nll"):
            self.assertIn(key, summary["model"])
        self.assertIn("max_expected_damage", summary["baselines"])
        self.assertIn("random_legal", summary["baselines"])
        # Fixture's chosen candidate is always a "move".
        self.assertIn("move", summary["model_by_chosen_kind"])


if __name__ == "__main__":
    unittest.main()
