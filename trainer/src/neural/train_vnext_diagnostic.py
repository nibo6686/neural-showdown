import argparse
import hashlib
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from .checkpoints import save_checkpoint
from .config import load_config, resolve_path
from .logging_helper import print_line_safe
from .models.vnext_diagnostic import VNextDiagnosticMLP


EXPECTED_STATE_VERSION = "live-private-belief-v7"
EXPECTED_ACTION_VERSION = "legal-action-v5"
EXPECTED_STATE_DIM = 3208
EXPECTED_ACTION_DIM = 318
SUPPORTED_ACTION_SCHEMAS = {
    "legal-action-v5": 318,
    "legal-action-v6": 331,
}
REQUIRED_SPLITS = ("train", "validation", "test")


@dataclass
class DiagnosticDataset:
    state_features: np.ndarray
    state_replay_ids: np.ndarray
    state_splits: np.ndarray
    state_turns: np.ndarray
    state_value_targets: np.ndarray
    action_features: np.ndarray
    candidate_state_indices: np.ndarray
    candidate_action_indices: np.ndarray
    candidate_kinds: np.ndarray
    action_rank_labels: np.ndarray
    split_state_indices: Dict[str, np.ndarray]
    split_group_state_indices: Dict[str, np.ndarray]
    candidate_rows_by_state: Dict[int, np.ndarray]
    ignored_group_state_indices: np.ndarray
    metadata: Dict[str, Any]
    materialization_report: Dict[str, Any]
    validation: Dict[str, Any]


def _require_mapping(payload: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config field {key!r} must be an object.")
    return value


def _require_keys(payload: Dict[str, Any], keys: Sequence[str], context: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{context} is missing required fields: {missing}")


def load_and_validate_diagnostic_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Diagnostic config does not exist: {path}")
    config = load_config(str(path))
    _require_keys(
        config,
        ("profile", "implementation_status", "entrypoint", "dataset", "objectives", "model", "training", "outputs"),
        "Diagnostic config",
    )
    if config["entrypoint"] != "neural.train_vnext_diagnostic":
        raise ValueError(
            "Config entrypoint must be 'neural.train_vnext_diagnostic', "
            f"got {config['entrypoint']!r}."
        )
    if config["implementation_status"] not in {"implemented_validate_only_tested", "implemented"}:
        raise ValueError(
            "Config implementation_status must indicate an implemented entrypoint; "
            f"got {config['implementation_status']!r}."
        )

    dataset_cfg = _require_mapping(config, "dataset")
    objectives = _require_mapping(config, "objectives")
    model_cfg = _require_mapping(config, "model")
    training_cfg = _require_mapping(config, "training")
    outputs_cfg = _require_mapping(config, "outputs")
    _require_keys(
        dataset_cfg,
        (
            "path",
            "metadata_path",
            "materialization_report_path",
            "state_feature_version",
            "state_feature_dim",
            "state_feature_names_sha256",
            "action_feature_version",
            "action_feature_dim",
            "action_feature_names_sha256",
            "dtype_on_disk",
            "storage_layout",
            "expected_battle_split_counts",
        ),
        "dataset config",
    )
    if dataset_cfg["state_feature_version"] != EXPECTED_STATE_VERSION:
        raise ValueError(
            f"Config state schema must be {EXPECTED_STATE_VERSION!r}, "
            f"got {dataset_cfg['state_feature_version']!r}."
        )
    if int(dataset_cfg["state_feature_dim"]) != EXPECTED_STATE_DIM:
        raise ValueError(
            f"Config state dimension must be {EXPECTED_STATE_DIM}, "
            f"got {dataset_cfg['state_feature_dim']}."
        )
    configured_action_version = str(dataset_cfg["action_feature_version"])
    if configured_action_version not in SUPPORTED_ACTION_SCHEMAS:
        raise ValueError(
            f"Config action schema must be one of {sorted(SUPPORTED_ACTION_SCHEMAS)!r}, "
            f"got {configured_action_version!r}."
        )
    configured_action_dim = SUPPORTED_ACTION_SCHEMAS[configured_action_version]
    if int(dataset_cfg["action_feature_dim"]) != configured_action_dim:
        raise ValueError(
            f"Config action dimension for {configured_action_version!r} must be {configured_action_dim}, "
            f"got {dataset_cfg['action_feature_dim']}."
        )
    if dataset_cfg["dtype_on_disk"] != "float16":
        raise ValueError("Diagnostic state/action dtype_on_disk must be 'float16'.")
    if dataset_cfg["storage_layout"] != "separate_state_and_candidate_tables":
        raise ValueError(
            "Diagnostic storage_layout must be 'separate_state_and_candidate_tables'."
        )
    configured_splits = {
        str(key): int(value)
        for key, value in dataset_cfg["expected_battle_split_counts"].items()
    }
    if set(configured_splits) != set(REQUIRED_SPLITS) or any(
        count <= 0 for count in configured_splits.values()
    ):
        raise ValueError(
            f"expected_battle_split_counts must be positive integers for splits "
            f"{REQUIRED_SPLITS}, got {configured_splits}."
        )

    state_objective = _require_mapping(objectives, "state_value")
    rank_objective = _require_mapping(objectives, "action_rank")
    action_value_objective = _require_mapping(objectives, "action_value")
    state_enabled = bool(state_objective.get("enabled"))
    if state_enabled:
        if state_objective.get("target") != "state_value_targets":
            raise ValueError("Enabled state-value objective must use target 'state_value_targets'.")
        if state_objective.get("loss") != "mean_squared_error":
            raise ValueError("State-value loss must be 'mean_squared_error'.")
        if float(state_objective.get("loss_weight", 0.0)) <= 0:
            raise ValueError("Enabled state-value objective must have positive loss_weight.")
    elif float(state_objective.get("loss_weight", 0.0)) != 0.0:
        raise ValueError("Disabled state-value objective must have loss_weight 0.")
    rank_enabled = bool(rank_objective.get("enabled"))
    if rank_enabled:
        if rank_objective.get("target") != "action_rank_labels":
            raise ValueError("Action-rank target must be 'action_rank_labels'.")
        if rank_objective.get("group_index") != "candidate_state_indices":
            raise ValueError("Action-rank group_index must be 'candidate_state_indices'.")
        if rank_objective.get("loss") != "grouped_cross_entropy":
            raise ValueError("Action-rank loss must be 'grouped_cross_entropy'.")
        if float(rank_objective.get("loss_weight", 0.0)) <= 0:
            raise ValueError("Enabled action-rank objective must have positive loss_weight.")
    elif float(rank_objective.get("loss_weight", 0.0)) != 0.0:
        raise ValueError("Disabled action-rank objective must have loss_weight 0.")
    if action_value_objective.get("enabled") is not False:
        raise ValueError("Action-value/Q-value objective must be disabled.")
    if not state_enabled and not rank_enabled:
        raise ValueError("At least one of state_value or action_rank objectives must be enabled.")

    if model_cfg.get("type") != "shared_state_action_diagnostic_mlp":
        raise ValueError("Unsupported diagnostic model type.")
    for key in (
        "state_encoder_hidden_sizes",
        "action_encoder_hidden_sizes",
        "rank_head_hidden_sizes",
    ):
        values = model_cfg.get(key)
        if not isinstance(values, list) or not values or not all(
            isinstance(value, int) and value > 0 for value in values
        ):
            raise ValueError(f"model.{key} must be a non-empty list of positive integers.")
    if model_cfg.get("activation") != "relu":
        raise ValueError("The first diagnostic model activation must be 'relu'.")
    if model_cfg.get("value_output") != "tanh":
        raise ValueError("The first diagnostic value output must be 'tanh'.")
    if float(model_cfg.get("dropout", 0.0)) < 0:
        raise ValueError("model.dropout cannot be negative.")
    if int(training_cfg.get("epochs", 0)) <= 0:
        raise ValueError("training.epochs must be positive.")
    if int(training_cfg.get("value_batch_size", 0)) <= 0:
        raise ValueError("training.value_batch_size must be positive.")
    if rank_enabled and int(training_cfg.get("rank_groups_per_batch", 0)) <= 0:
        raise ValueError("training.rank_groups_per_batch must be positive.")
    if float(training_cfg.get("learning_rate", 0.0)) <= 0:
        raise ValueError("training.learning_rate must be positive.")
    if outputs_cfg.get("production_eligible") is not False:
        raise ValueError("Diagnostic outputs must set production_eligible to false.")

    resolved = dict(config)
    resolved["_resolved_dataset_path"] = str(resolve_path(config, dataset_cfg["path"]))
    resolved["_resolved_metadata_path"] = str(resolve_path(config, dataset_cfg["metadata_path"]))
    resolved["_resolved_materialization_report_path"] = str(
        resolve_path(config, dataset_cfg["materialization_report_path"])
    )
    resolved["_resolved_output_paths"] = {
        key: str(resolve_path(config, value))
        for key, value in outputs_cfg.items()
        if key.endswith("_path") or key == "directory"
    }
    return resolved


def _names_fingerprint(names: Sequence[str]) -> str:
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path, description: str) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{description} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{description} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must contain a JSON object: {path}")
    return payload


def _required_npz_arrays() -> Tuple[str, ...]:
    return (
        "state_features",
        "state_replay_ids",
        "state_splits",
        "state_turns",
        "state_value_targets",
        "action_features",
        "candidate_state_indices",
        "candidate_action_indices",
        "candidate_kinds",
        "action_rank_labels",
        "state_feature_version",
        "state_feature_names",
        "action_feature_version",
        "action_feature_names",
        "manifest_catalog_checksum",
    )


def load_diagnostic_dataset(config: Dict[str, Any]) -> DiagnosticDataset:
    dataset_cfg = config["dataset"]
    dataset_path = Path(config["_resolved_dataset_path"])
    metadata_path = Path(config["_resolved_metadata_path"])
    report_path = Path(config["_resolved_materialization_report_path"])
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Diagnostic dataset does not exist: {dataset_path}")
    metadata = _read_json(metadata_path, "Diagnostic feature metadata")
    materialization_report = _read_json(report_path, "Diagnostic materialization report")

    with np.load(dataset_path, allow_pickle=False) as loaded:
        missing = [name for name in _required_npz_arrays() if name not in loaded.files]
        if missing:
            raise ValueError(f"Diagnostic dataset is missing required arrays: {missing}")
        unexpected_action_values = [
            name
            for name in loaded.files
            if name.startswith("action_value")
            or name in {"advantages", "target_scores", "q_values", "action_value_targets"}
        ]
        if unexpected_action_values:
            raise ValueError(
                "Diagnostic dataset unexpectedly contains action-value/Q-value arrays: "
                f"{unexpected_action_values}"
            )
        arrays = {name: loaded[name] for name in loaded.files}

    states = arrays["state_features"]
    actions = arrays["action_features"]
    replay_ids = arrays["state_replay_ids"].astype(str)
    state_splits = arrays["state_splits"].astype(str)
    state_turns = arrays["state_turns"].astype(np.int64)
    value_targets = arrays["state_value_targets"].astype(np.float32)
    candidate_state_indices = arrays["candidate_state_indices"].astype(np.int64)
    candidate_action_indices = arrays["candidate_action_indices"].astype(np.int64)
    candidate_kinds = arrays["candidate_kinds"].astype(str)
    rank_labels = arrays["action_rank_labels"].astype(np.int8)
    state_names = arrays["state_feature_names"].astype(str).tolist()
    action_names = arrays["action_feature_names"].astype(str).tolist()
    embedded_state_version = str(arrays["state_feature_version"])
    embedded_action_version = str(arrays["action_feature_version"])
    embedded_catalog_checksum = str(arrays["manifest_catalog_checksum"])

    if states.ndim != 2 or states.shape[1] != EXPECTED_STATE_DIM:
        raise ValueError(
            f"State feature dimension mismatch: expected (*, {EXPECTED_STATE_DIM}), "
            f"got {states.shape}."
        )
    configured_action_dim = int(dataset_cfg["action_feature_dim"])
    configured_action_version = str(dataset_cfg["action_feature_version"])
    if actions.ndim != 2 or actions.shape[1] != configured_action_dim:
        raise ValueError(
            f"Action feature dimension mismatch: expected (*, {configured_action_dim}), "
            f"got {actions.shape}."
        )
    if states.dtype != np.float16 or actions.dtype != np.float16:
        raise ValueError(
            "Diagnostic state/action arrays must be float16 on disk; "
            f"got state={states.dtype}, action={actions.dtype}."
        )
    if embedded_state_version != EXPECTED_STATE_VERSION:
        raise ValueError(
            f"Embedded state schema mismatch: expected {EXPECTED_STATE_VERSION!r}, "
            f"got {embedded_state_version!r}."
        )
    if embedded_action_version != configured_action_version:
        raise ValueError(
            f"Embedded action schema mismatch: expected {configured_action_version!r}, "
            f"got {embedded_action_version!r}."
        )

    for label, actual, expected in (
        ("metadata state schema", metadata.get("state_feature_version"), dataset_cfg["state_feature_version"]),
        ("metadata action schema", metadata.get("action_feature_version"), dataset_cfg["action_feature_version"]),
        ("metadata state dimension", metadata.get("state_feature_dim"), dataset_cfg["state_feature_dim"]),
        ("metadata action dimension", metadata.get("action_feature_dim"), dataset_cfg["action_feature_dim"]),
        ("metadata state fingerprint", metadata.get("state_feature_names_sha256"), dataset_cfg["state_feature_names_sha256"]),
        ("metadata action fingerprint", metadata.get("action_feature_names_sha256"), dataset_cfg["action_feature_names_sha256"]),
    ):
        if actual != expected:
            raise ValueError(f"{label} mismatch: expected {expected!r}, got {actual!r}.")
    state_fingerprint = _names_fingerprint(state_names)
    action_fingerprint = _names_fingerprint(action_names)
    if state_fingerprint != dataset_cfg["state_feature_names_sha256"]:
        raise ValueError(
            "Ordered state feature-name fingerprint mismatch: "
            f"expected {dataset_cfg['state_feature_names_sha256']}, got {state_fingerprint}."
        )
    if action_fingerprint != dataset_cfg["action_feature_names_sha256"]:
        raise ValueError(
            "Ordered action feature-name fingerprint mismatch: "
            f"expected {dataset_cfg['action_feature_names_sha256']}, got {action_fingerprint}."
        )
    if metadata.get("dtype_on_disk") != dataset_cfg["dtype_on_disk"]:
        raise ValueError(
            f"Metadata dtype mismatch: expected {dataset_cfg['dtype_on_disk']!r}, "
            f"got {metadata.get('dtype_on_disk')!r}."
        )
    if metadata.get("state_vectors_duplicated_per_candidate") is not False:
        raise ValueError("Metadata must assert that state vectors are not duplicated per candidate.")
    if "separate candidate action rows" not in str(metadata.get("storage_layout") or ""):
        raise ValueError("Metadata does not describe the required separate state/candidate layout.")
    if metadata.get("manifest_catalog_checksum") != embedded_catalog_checksum:
        raise ValueError(
            "Manifest catalog checksum mismatch between metadata and dataset: "
            f"{metadata.get('manifest_catalog_checksum')!r} != {embedded_catalog_checksum!r}."
        )

    n_states = len(states)
    n_actions = len(actions)
    aligned_state_lengths = {
        len(replay_ids),
        len(state_splits),
        len(state_turns),
        len(value_targets),
        n_states,
    }
    if len(aligned_state_lengths) != 1:
        raise ValueError(f"State arrays have inconsistent lengths: {sorted(aligned_state_lengths)}")
    aligned_action_lengths = {
        len(candidate_state_indices),
        len(candidate_action_indices),
        len(candidate_kinds),
        len(rank_labels),
        n_actions,
    }
    if len(aligned_action_lengths) != 1:
        raise ValueError(f"Action arrays have inconsistent lengths: {sorted(aligned_action_lengths)}")
    if candidate_state_indices.size and (
        int(candidate_state_indices.min()) < 0
        or int(candidate_state_indices.max()) >= n_states
    ):
        raise ValueError(
            "candidate_state_indices contains an out-of-range state reference: "
            f"min={candidate_state_indices.min()}, max={candidate_state_indices.max()}, "
            f"state_count={n_states}."
        )
    invalid_splits = sorted(set(state_splits.tolist()) - set(REQUIRED_SPLITS))
    if invalid_splits:
        raise ValueError(f"State rows contain unexpected split names: {invalid_splits}")
    missing_splits = [split for split in REQUIRED_SPLITS if not np.any(state_splits == split)]
    if missing_splits:
        raise ValueError(f"State rows are missing required splits: {missing_splits}")

    replay_to_splits: Dict[str, set] = {}
    for replay_id, split in zip(replay_ids, state_splits):
        replay_to_splits.setdefault(str(replay_id), set()).add(str(split))
    leaking = {
        replay_id: sorted(splits)
        for replay_id, splits in replay_to_splits.items()
        if len(splits) != 1
    }
    if leaking:
        sample = dict(list(leaking.items())[:5])
        raise ValueError(f"Battle split leakage detected: {sample}")
    metadata_replay_ids = {
        str(value) for value in metadata.get("selected_replay_ids", [])
    }
    if metadata_replay_ids != set(replay_to_splits):
        missing_from_metadata = sorted(set(replay_to_splits) - metadata_replay_ids)[:5]
        missing_from_dataset = sorted(metadata_replay_ids - set(replay_to_splits))[:5]
        raise ValueError(
            "Dataset battle IDs do not match metadata selected_replay_ids: "
            f"missing_from_metadata={missing_from_metadata}, "
            f"missing_from_dataset={missing_from_dataset}."
        )
    metadata_splits = {
        str(replay_id): str(split)
        for replay_id, split in (metadata.get("selected_splits") or {}).items()
    }
    if set(metadata_splits) != set(replay_to_splits):
        raise ValueError(
            "Metadata selected_splits keys do not exactly match dataset battle IDs."
        )
    split_mismatches = {
        replay_id: {
            "metadata": metadata_splits[replay_id],
            "dataset": next(iter(splits)),
        }
        for replay_id, splits in replay_to_splits.items()
        if metadata_splits[replay_id] != next(iter(splits))
    }
    if split_mismatches:
        sample = dict(list(split_mismatches.items())[:5])
        raise ValueError(f"Dataset/metadata split assignment mismatch: {sample}")
    battle_split_counts = {
        split: sum(1 for splits in replay_to_splits.values() if split in splits)
        for split in REQUIRED_SPLITS
    }
    expected_battles = {
        str(key): int(value)
        for key, value in dataset_cfg["expected_battle_split_counts"].items()
    }
    if battle_split_counts != expected_battles:
        raise ValueError(
            f"Battle split counts mismatch: expected {expected_battles}, "
            f"got {battle_split_counts}."
        )
    report_battles = {
        str(key): int(value)
        for key, value in (materialization_report.get("split_battle_counts") or {}).items()
    }
    if report_battles != expected_battles:
        raise ValueError(
            f"Materialization report split counts mismatch: expected {expected_battles}, "
            f"got {report_battles}."
        )

    unique_values = set(float(value) for value in np.unique(value_targets))
    if unique_values != {-1.0, 1.0}:
        raise ValueError(
            f"State-value labels must contain only -1 and +1, got {sorted(unique_values)}."
        )
    unique_rank_labels = set(int(value) for value in np.unique(rank_labels))
    if not unique_rank_labels.issubset({0, 1}):
        raise ValueError(
            f"Action-rank labels must be binary 0/1, got {sorted(unique_rank_labels)}."
        )

    candidate_rows_by_state: Dict[int, np.ndarray] = {}
    included_groups: List[int] = []
    ignored_groups: List[int] = []
    if candidate_state_indices.size:
        boundaries = np.flatnonzero(np.diff(candidate_state_indices)) + 1
        row_groups = np.split(np.arange(n_actions, dtype=np.int64), boundaries)
        seen_states = set()
        for rows in row_groups:
            state_index = int(candidate_state_indices[int(rows[0])])
            if state_index in seen_states:
                raise ValueError(
                    f"Action candidate rows for state {state_index} are not contiguous."
                )
            seen_states.add(state_index)
            positives = int(rank_labels[rows].sum())
            if positives > 1:
                raise ValueError(
                    f"Action-rank group for state {state_index} has {positives} positives; "
                    "at most one is allowed."
                )
            candidate_rows_by_state[state_index] = rows
            if positives == 1:
                included_groups.append(state_index)
            else:
                ignored_groups.append(state_index)

    action_value_status = metadata.get("action_value_target_status")
    action_value_count = int(materialization_report.get("action_value_labels_generated", -1))
    if action_value_status != "not_generated" or action_value_count != 0:
        raise ValueError(
            "Action-value labels must be absent: "
            f"metadata status={action_value_status!r}, report count={action_value_count}."
        )

    split_state_indices = {
        split: np.flatnonzero(state_splits == split).astype(np.int64)
        for split in REQUIRED_SPLITS
    }
    included_array = np.asarray(included_groups, dtype=np.int64)
    split_group_state_indices = {
        split: included_array[state_splits[included_array] == split]
        if included_array.size
        else np.asarray([], dtype=np.int64)
        for split in REQUIRED_SPLITS
    }
    validation = {
        "dataset_path": str(dataset_path),
        "metadata_path": str(metadata_path),
        "materialization_report_path": str(report_path),
        "state_count": int(n_states),
        "action_candidate_count": int(n_actions),
        "state_dim": int(states.shape[1]),
        "action_dim": int(actions.shape[1]),
        "state_dtype_on_disk": str(states.dtype),
        "action_dtype_on_disk": str(actions.dtype),
        "battle_split_counts": battle_split_counts,
        "state_split_counts": {
            split: int(len(indices)) for split, indices in split_state_indices.items()
        },
        "matched_action_group_split_counts": {
            split: int(len(indices))
            for split, indices in split_group_state_indices.items()
        },
        "included_action_groups": int(len(included_groups)),
        "ignored_zero_positive_action_groups": int(len(ignored_groups)),
        "unmatched_actions_reported": int(
            materialization_report.get("chosen_action_unmatched_count", 0)
        ),
        "skipped_initial_deployments_reported": int(
            (materialization_report.get("skip_reasons") or {}).get(
                "initial_deployment_nondecision", 0
            )
        ),
        "action_value_label_count": action_value_count,
        "state_feature_version": embedded_state_version,
        "action_feature_version": embedded_action_version,
        "state_feature_names_sha256": state_fingerprint,
        "action_feature_names_sha256": action_fingerprint,
        "state_vectors_duplicated_per_candidate": False,
    }
    return DiagnosticDataset(
        state_features=states,
        state_replay_ids=replay_ids,
        state_splits=state_splits,
        state_turns=state_turns,
        state_value_targets=value_targets,
        action_features=actions,
        candidate_state_indices=candidate_state_indices,
        candidate_action_indices=candidate_action_indices,
        candidate_kinds=candidate_kinds,
        action_rank_labels=rank_labels,
        split_state_indices=split_state_indices,
        split_group_state_indices=split_group_state_indices,
        candidate_rows_by_state=candidate_rows_by_state,
        ignored_group_state_indices=np.asarray(ignored_groups, dtype=np.int64),
        metadata=metadata,
        materialization_report=materialization_report,
        validation=validation,
    )


def build_diagnostic_model(config: Dict[str, Any]) -> VNextDiagnosticMLP:
    model_cfg = config["model"]
    model = VNextDiagnosticMLP(
        state_dim=int(config["dataset"]["state_feature_dim"]),
        action_dim=int(config["dataset"]["action_feature_dim"]),
        state_encoder_hidden_sizes=model_cfg["state_encoder_hidden_sizes"],
        action_encoder_hidden_sizes=model_cfg["action_encoder_hidden_sizes"],
        rank_head_hidden_sizes=model_cfg["rank_head_hidden_sizes"],
        dropout=float(model_cfg.get("dropout", 0.0)),
    )
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    expected = int(model_cfg.get("expected_parameter_count_approx", parameter_count))
    if parameter_count != expected:
        raise ValueError(
            f"Diagnostic model parameter count mismatch: expected {expected}, "
            f"got {parameter_count}."
        )
    return model


def build_vnext_checkpoint_metadata(dataset: DiagnosticDataset) -> Dict[str, Any]:
    """Schema-identity metadata embedded in vNext checkpoints for safe reload.

    Records both schema versions/dimensions and the ordered feature-name
    fingerprints so a future loader can prove a checkpoint matches the exact
    feature ordering it was trained on, not merely a version string and shape.
    """
    validation = dataset.validation
    return {
        "state_feature_version": validation["state_feature_version"],
        "action_feature_version": validation["action_feature_version"],
        "state_dim": int(validation["state_dim"]),
        "action_dim": int(validation["action_dim"]),
        "state_feature_names_sha256": validation["state_feature_names_sha256"],
        "action_feature_names_sha256": validation["action_feature_names_sha256"],
        "manifest_catalog_checksum": dataset.metadata.get("manifest_catalog_checksum"),
    }


def validate_vnext_checkpoint_metadata(
    checkpoint: Dict[str, Any],
    *,
    expected_state_version: str = EXPECTED_STATE_VERSION,
    expected_action_version: str = EXPECTED_ACTION_VERSION,
    expected_state_dim: int = EXPECTED_STATE_DIM,
    expected_action_dim: int = EXPECTED_ACTION_DIM,
    expected_state_feature_names_sha256: Optional[str] = None,
    expected_action_feature_names_sha256: Optional[str] = None,
    require_fingerprints: bool = False,
) -> Dict[str, Any]:
    """Strictly validate vNext checkpoint schema metadata before reuse.

    Raises ``ValueError`` on any schema-name, dimension, or fingerprint mismatch.
    Missing fingerprints are reported as ``"missing_legacy"`` rather than being
    treated as equivalent; set ``require_fingerprints=True`` to reject such
    legacy/incomplete checkpoints outright.
    """
    if not isinstance(checkpoint, dict):
        raise ValueError("vNext checkpoint metadata must be a mapping.")

    state_version = checkpoint.get("state_feature_version")
    if not state_version:
        raise ValueError("vNext checkpoint is missing state_feature_version.")
    if state_version != expected_state_version:
        raise ValueError(
            f"vNext checkpoint state schema mismatch: expected {expected_state_version!r}, "
            f"got {state_version!r}."
        )
    action_version = checkpoint.get("action_feature_version")
    if not action_version:
        raise ValueError("vNext checkpoint is missing action_feature_version.")
    if action_version != expected_action_version:
        raise ValueError(
            f"vNext checkpoint action schema mismatch: expected {expected_action_version!r}, "
            f"got {action_version!r}."
        )

    if "state_dim" not in checkpoint:
        raise ValueError("vNext checkpoint is missing state_dim.")
    if int(checkpoint["state_dim"]) != int(expected_state_dim):
        raise ValueError(
            f"vNext checkpoint state dimension mismatch: expected {int(expected_state_dim)}, "
            f"got {int(checkpoint['state_dim'])}."
        )
    if "action_dim" not in checkpoint:
        raise ValueError("vNext checkpoint is missing action_dim.")
    if int(checkpoint["action_dim"]) != int(expected_action_dim):
        raise ValueError(
            f"vNext checkpoint action dimension mismatch: expected {int(expected_action_dim)}, "
            f"got {int(checkpoint['action_dim'])}."
        )

    def _fingerprint_status(field: str, expected: Optional[str]) -> str:
        present = checkpoint.get(field)
        if not present:
            if require_fingerprints:
                raise ValueError(
                    f"vNext checkpoint is missing required fingerprint {field!r} "
                    "(legacy/incomplete metadata)."
                )
            return "missing_legacy"
        if expected is None:
            return "present_unverified"
        if present != expected:
            raise ValueError(
                f"vNext checkpoint {field} mismatch: expected {expected!r}, got {present!r}."
            )
        return "validated"

    state_fp_status = _fingerprint_status(
        "state_feature_names_sha256", expected_state_feature_names_sha256
    )
    action_fp_status = _fingerprint_status(
        "action_feature_names_sha256", expected_action_feature_names_sha256
    )

    return {
        "status": "PASS",
        "state_feature_version": state_version,
        "action_feature_version": action_version,
        "state_dim": int(checkpoint["state_dim"]),
        "action_dim": int(checkpoint["action_dim"]),
        "state_fingerprint_status": state_fp_status,
        "action_fingerprint_status": action_fp_status,
        "fingerprints_complete": (
            state_fp_status != "missing_legacy"
            and action_fp_status != "missing_legacy"
        ),
    }


def grouped_action_rank_loss(
    scores: torch.Tensor,
    labels: torch.Tensor,
    group_ranges: Sequence[Tuple[int, int]],
) -> torch.Tensor:
    losses = []
    for start, end in group_ranges:
        group_labels = labels[start:end]
        positives = torch.nonzero(group_labels > 0.5, as_tuple=False).flatten()
        if positives.numel() == 0:
            continue
        if positives.numel() > 1:
            raise ValueError(
                f"Grouped action-rank batch contains {positives.numel()} positives; "
                "at most one is allowed."
            )
        losses.append(
            F.cross_entropy(
                scores[start:end].unsqueeze(0),
                positives[0].reshape(1).long(),
            )
        )
    if not losses:
        raise ValueError("Grouped action-rank batch contains no matched groups.")
    return torch.stack(losses).mean()


def _rank_batch(
    dataset: DiagnosticDataset,
    group_state_indices: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Tuple[int, int]], np.ndarray]:
    state_rows = []
    action_rows = []
    labels = []
    ranges = []
    cursor = 0
    for local_state_index, state_index in enumerate(group_state_indices):
        rows = dataset.candidate_rows_by_state[int(state_index)]
        state_rows.append(dataset.state_features[int(state_index)])
        action_rows.append(dataset.action_features[rows])
        labels.append(dataset.action_rank_labels[rows])
        ranges.append((cursor, cursor + len(rows)))
        cursor += len(rows)
    if not state_rows:
        raise ValueError("Cannot build an action-rank batch with zero groups.")
    repeated_local_state_indices = np.concatenate(
        [
            np.full(end - start, local_index, dtype=np.int64)
            for local_index, (start, end) in enumerate(ranges)
        ]
    )
    return (
        np.asarray(state_rows, dtype=np.float32),
        np.concatenate(action_rows).astype(np.float32),
        np.concatenate(labels).astype(np.float32),
        ranges,
        repeated_local_state_indices,
    )


def forward_loss_smoke_check(
    model: VNextDiagnosticMLP,
    dataset: DiagnosticDataset,
    *,
    rank_enabled: bool = True,
    value_enabled: bool = True,
    split: str = "train",
    state_batch_size: int = 8,
    rank_group_count: int = 4,
) -> Dict[str, Any]:
    if split not in REQUIRED_SPLITS:
        raise ValueError(f"Unsupported smoke-check split: {split!r}")
    state_indices = dataset.split_state_indices[split][:state_batch_size]
    if value_enabled and len(state_indices) == 0:
        raise ValueError(f"Split {split!r} has no state rows for smoke checking.")
    group_indices = dataset.split_group_state_indices[split][:rank_group_count]
    if rank_enabled and len(group_indices) == 0:
        raise ValueError(f"Split {split!r} has no action groups for smoke checking.")
    model.eval()
    value_predictions = None
    value_loss = None
    with torch.no_grad():
        if value_enabled:
            value_inputs = torch.from_numpy(
                dataset.state_features[state_indices].astype(np.float32)
            )
            value_targets = torch.from_numpy(dataset.state_value_targets[state_indices])
            value_embeddings = model.encode_states(value_inputs)
            value_predictions = model.value_from_embedding(value_embeddings)
            value_loss = F.mse_loss(value_predictions, value_targets)

        rank_scores = None
        rank_loss = None
        rank_labels = np.asarray([], dtype=np.float32)
        if rank_enabled:
            rank_states, rank_actions, rank_labels, ranges, local_indices = _rank_batch(
                dataset, group_indices
            )
            rank_state_tensor = torch.from_numpy(rank_states)
            rank_action_tensor = torch.from_numpy(rank_actions)
            local_index_tensor = torch.from_numpy(local_indices)
            rank_embeddings = model.encode_states(rank_state_tensor)
            rank_scores = model.rank_from_embeddings(
                rank_embeddings[local_index_tensor],
                rank_action_tensor,
            )
            rank_loss = grouped_action_rank_loss(
                rank_scores,
                torch.from_numpy(rank_labels),
                ranges,
            )
    if value_enabled and value_predictions.shape != (len(state_indices),):
        raise ValueError(
            f"Value output shape mismatch: expected {(len(state_indices),)}, "
            f"got {tuple(value_predictions.shape)}."
        )
    if rank_enabled and rank_scores is not None and rank_scores.shape != (len(rank_labels),):
        raise ValueError(
            f"Rank output shape mismatch: expected {(len(rank_labels),)}, "
            f"got {tuple(rank_scores.shape)}."
        )
    if (value_enabled and not torch.isfinite(value_loss)) or (
        rank_enabled and rank_loss is not None and not torch.isfinite(rank_loss)
    ):
        raise ValueError(
            f"Forward/loss smoke check produced non-finite loss: "
            f"value={value_loss.item() if value_loss is not None else 'disabled'}, "
            f"rank={rank_loss.item() if rank_loss is not None else 'disabled'}."
        )
    return {
        "split": split,
        "heads_checked": (["state_value"] if value_enabled else []) + (["action_rank"] if rank_enabled else []),
        "value_enabled": value_enabled,
        "value_batch_size": int(len(state_indices)) if value_enabled else 0,
        "rank_enabled": rank_enabled,
        "rank_group_count": int(len(group_indices)) if rank_enabled else 0,
        "rank_candidate_count": int(len(rank_labels)),
        "value_output_shape": list(value_predictions.shape) if value_predictions is not None else None,
        "rank_output_shape": list(rank_scores.shape) if rank_scores is not None else None,
        "value_loss": float(value_loss.item()) if value_loss is not None else None,
        "action_rank_loss": float(rank_loss.item()) if rank_loss is not None else None,
        "value_gradient_contribution": False if not value_enabled else "not_applicable_no_grad",
        "rank_gradient_contribution": False if not rank_enabled else "not_applicable_no_grad",
        "optimizer_steps": 0,
    }


def validate_diagnostic_wiring(config_path: Path) -> Dict[str, Any]:
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    _seed_everything(int(config["training"]["seed"]))
    model = build_diagnostic_model(config)
    rank_enabled = bool(config["objectives"]["action_rank"]["enabled"])
    value_enabled = bool(config["objectives"]["state_value"]["enabled"])
    smoke = forward_loss_smoke_check(
        model, dataset, rank_enabled=rank_enabled, value_enabled=value_enabled
    )
    report = {
        "status": "PASS",
        "mode": "validate-only",
        "config_path": str(config_path.resolve()),
        "profile": config["profile"],
        "implementation_status": config["implementation_status"],
        "dataset": dataset.validation,
        "model": {
            "type": config["model"]["type"],
            "parameter_count": int(sum(p.numel() for p in model.parameters())),
            "state_dim": int(config["dataset"]["state_feature_dim"]),
            "action_dim": int(config["dataset"]["action_feature_dim"]),
        },
        "smoke_check": smoke,
        "heads_enabled": {
            "state_value": value_enabled,
            "action_rank": rank_enabled,
            "action_value": False,
        },
        "optimizer_step_source": (
            "rank_batches_only"
            if rank_enabled and not value_enabled
            else "value_batches_only"
            if value_enabled and not rank_enabled
            else "value_and_rank_batches"
        ),
        "optimizer_created": False,
        "optimizer_steps": 0,
        "training_launched": False,
    }
    print_line_safe(json.dumps(report, indent=2, sort_keys=True))
    return report


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _iter_batches(indices: np.ndarray, batch_size: int, rng: np.random.RandomState):
    order = indices.copy()
    rng.shuffle(order)
    for start in range(0, len(order), batch_size):
        yield order[start : start + batch_size]


def _run_overfit_check(
    config: Dict[str, Any],
    dataset: DiagnosticDataset,
    device: torch.device,
) -> Dict[str, Any]:
    overfit_cfg = config.get("overfit_check") or {}
    if not overfit_cfg.get("enabled"):
        return {"enabled": False, "passed": True, "steps": 0}
    model = build_diagnostic_model(config).to(device)
    training_cfg = config["training"]
    rank_enabled = bool(config["objectives"]["action_rank"]["enabled"])
    value_enabled = bool(config["objectives"]["state_value"]["enabled"])
    optimizer_parameters = list(model.state_encoder.parameters())
    if value_enabled:
        optimizer_parameters += list(model.value_head.parameters())
    if rank_enabled:
        optimizer_parameters += list(model.action_encoder.parameters())
        optimizer_parameters += list(model.rank_trunk.parameters())
        optimizer_parameters += list(model.rank_head.parameters())
    optimizer = torch.optim.AdamW(
        optimizer_parameters,
        lr=float(training_cfg["learning_rate"]),
        weight_decay=0.0,
    )
    state_indices = dataset.split_state_indices["train"][
        : int(overfit_cfg["state_examples"])
    ]
    group_indices = dataset.split_group_state_indices["train"][
        : int(overfit_cfg.get("action_groups", 0))
    ]
    if (value_enabled and len(state_indices) == 0) or (rank_enabled and len(group_indices) == 0):
        raise ValueError("Overfit check requires non-empty enabled-objective subsets.")
    state_tensor = None
    target_tensor = None
    if value_enabled:
        state_tensor = torch.from_numpy(
            dataset.state_features[state_indices].astype(np.float32)
        ).to(device)
        target_tensor = torch.from_numpy(dataset.state_value_targets[state_indices]).to(device)
    if rank_enabled:
        rank_states, rank_actions, labels, ranges, local_indices = _rank_batch(
            dataset, group_indices
        )
        rank_state_tensor = torch.from_numpy(rank_states).to(device)
        rank_action_tensor = torch.from_numpy(rank_actions).to(device)
        rank_label_tensor = torch.from_numpy(labels).to(device)
        local_index_tensor = torch.from_numpy(local_indices).to(device)
    max_steps = int(overfit_cfg["max_steps"])
    value_mse = float("inf")
    rank_top1 = 0.0
    rank_loss_value = float("inf")
    steps = 0
    for step in range(1, max_steps + 1):
        model.train()
        optimizer.zero_grad()
        value_loss = None
        if value_enabled:
            value_predictions = model.value_from_embedding(model.encode_states(state_tensor))
            value_loss = F.mse_loss(value_predictions, target_tensor)
        rank_loss = None
        if rank_enabled:
            rank_embeddings = model.encode_states(rank_state_tensor)
            rank_scores = model.rank_from_embeddings(
                rank_embeddings[local_index_tensor], rank_action_tensor
            )
            rank_loss = grouped_action_rank_loss(rank_scores, rank_label_tensor, ranges)
        total_loss = None
        for partial in (value_loss, rank_loss):
            if partial is not None:
                total_loss = partial if total_loss is None else total_loss + partial
        if not torch.isfinite(total_loss):
            raise ValueError("Overfit check produced a non-finite loss.")
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), float(training_cfg["gradient_clip_norm"])
        )
        optimizer.step()
        steps = step
        if step == 1 or step % 25 == 0 or step == max_steps:
            model.eval()
            with torch.no_grad():
                if value_enabled:
                    values = model.value_from_embedding(model.encode_states(state_tensor))
                    value_mse = float(F.mse_loss(values, target_tensor).item())
                if rank_enabled:
                    embeddings = model.encode_states(rank_state_tensor)
                    scores = model.rank_from_embeddings(
                        embeddings[local_index_tensor], rank_action_tensor
                    )
                    rank_loss_value = float(
                        grouped_action_rank_loss(scores, rank_label_tensor, ranges).item()
                    )
                    correct = 0
                    for start, end in ranges:
                        predicted = int(torch.argmax(scores[start:end]).item())
                        chosen = int(
                            torch.nonzero(
                                rank_label_tensor[start:end] > 0.5, as_tuple=False
                            )[0, 0].item()
                        )
                        correct += int(predicted == chosen)
                    rank_top1 = correct / len(ranges)
            if (
                (not value_enabled or value_mse <= float(overfit_cfg["required_value_train_mse_max"]))
                and (
                    not rank_enabled
                    or rank_top1 >= float(overfit_cfg["required_action_train_top1_min"])
                )
            ):
                break
    passed = (
        (not value_enabled or value_mse <= float(overfit_cfg["required_value_train_mse_max"]))
        and (
            not rank_enabled
            or rank_top1 >= float(overfit_cfg["required_action_train_top1_min"])
        )
    )
    result = {
        "enabled": True,
        "passed": passed,
        "steps": steps,
        "state_examples": int(len(state_indices)) if value_enabled else 0,
        "heads_checked": (["state_value"] if value_enabled else []) + (["action_rank"] if rank_enabled else []),
        "action_groups": int(len(group_indices)) if rank_enabled else 0,
        "value_train_mse": value_mse if value_enabled else None,
        "action_rank_train_nll": rank_loss_value if rank_enabled else None,
        "action_rank_train_top1": rank_top1 if rank_enabled else None,
    }
    if not passed and overfit_cfg.get("fail_main_run_if_not_met", True):
        raise ValueError(f"Mandatory overfit check failed: {result}")
    return result


def _rank_metrics(
    model: VNextDiagnosticMLP,
    dataset: DiagnosticDataset,
    groups: np.ndarray,
    device: torch.device,
) -> Dict[str, float]:
    model.eval()
    total = 0
    nll = top1 = top3 = reciprocal = 0.0
    with torch.no_grad():
        for state_index in groups:
            rows = dataset.candidate_rows_by_state[int(state_index)]
            state = torch.from_numpy(
                dataset.state_features[int(state_index)].astype(np.float32)
            ).unsqueeze(0).to(device)
            actions = torch.from_numpy(
                dataset.action_features[rows].astype(np.float32)
            ).to(device)
            embedding = model.encode_states(state).expand(len(rows), -1)
            scores = model.rank_from_embeddings(embedding, actions)
            labels = dataset.action_rank_labels[rows]
            chosen = int(np.flatnonzero(labels == 1)[0])
            order = torch.argsort(scores, descending=True).cpu().numpy()
            rank = int(np.flatnonzero(order == chosen)[0]) + 1
            probs = torch.softmax(scores, dim=0)
            nll += -math.log(max(1e-8, float(probs[chosen].item())))
            top1 += float(int(order[0]) == chosen)
            top3 += float(chosen in set(int(value) for value in order[:3]))
            reciprocal += 1.0 / rank
            total += 1
    return {
        "group_count": float(total),
        "nll": nll / max(1, total),
        "top1": top1 / max(1, total),
        "top3": top3 / max(1, total),
        "mrr": reciprocal / max(1, total),
    }


def _value_metrics(
    model: VNextDiagnosticMLP,
    dataset: DiagnosticDataset,
    indices: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> Dict[str, Any]:
    model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(indices), batch_size):
            batch_indices = indices[start : start + batch_size]
            inputs = torch.from_numpy(
                dataset.state_features[batch_indices].astype(np.float32)
            ).to(device)
            predictions.append(
                model.value_from_embedding(model.encode_states(inputs)).cpu().numpy()
            )
    preds = np.concatenate(predictions).astype(np.float32)
    targets = dataset.state_value_targets[indices]
    mean_target = float(targets.mean())
    return {
        "count": float(len(indices)),
        "mse": float(np.mean((preds - targets) ** 2)),
        "sign_accuracy": float(np.mean((preds > 0) == (targets > 0))),
        "prediction_mean": float(preds.mean()),
        "prediction_std": float(preds.std()),
        "prediction_min": float(preds.min()),
        "prediction_max": float(preds.max()),
        "prediction_abs_ge_0_90_rate": float(np.mean(np.abs(preds) >= 0.90)),
        "prediction_abs_ge_0_95_rate": float(np.mean(np.abs(preds) >= 0.95)),
        "prediction_abs_ge_0_99_rate": float(np.mean(np.abs(preds) >= 0.99)),
        "constant_baseline_mse": float(np.mean((targets - mean_target) ** 2)),
        "constant_zero_baseline_mse": float(np.mean(targets ** 2)),
    }


def train_diagnostic(config_path: Path) -> Dict[str, Any]:
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    training_cfg = config["training"]
    seed = int(training_cfg["seed"])
    _seed_everything(seed)
    model = build_diagnostic_model(config)
    rank_enabled = bool(config["objectives"]["action_rank"]["enabled"])
    value_enabled = bool(config["objectives"]["state_value"]["enabled"])
    forward_loss_smoke_check(model, dataset, rank_enabled=rank_enabled, value_enabled=value_enabled)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    overfit_result = _run_overfit_check(config, dataset, device)
    optimizer_parameters = list(model.state_encoder.parameters())
    if value_enabled:
        optimizer_parameters += list(model.value_head.parameters())
    if rank_enabled:
        optimizer_parameters += list(model.action_encoder.parameters())
        optimizer_parameters += list(model.rank_trunk.parameters())
        optimizer_parameters += list(model.rank_head.parameters())
    optimizer = torch.optim.AdamW(
        optimizer_parameters,
        lr=float(training_cfg["learning_rate"]),
        weight_decay=float(training_cfg["weight_decay"]),
    )
    value_weight = float(config["objectives"]["state_value"].get("loss_weight", 0.0))
    rank_weight = float(config["objectives"]["action_rank"].get("loss_weight", 0.0))
    value_batch_size = int(training_cfg["value_batch_size"])
    rank_groups_per_batch = int(training_cfg.get("rank_groups_per_batch", 1))
    grad_clip = float(training_cfg["gradient_clip_norm"])
    heads_trained = {
        "state_value": value_enabled,
        "action_rank": rank_enabled,
        "action_value": False,
    }
    if value_enabled and rank_enabled:
        selection_metric = "validation_value_mse_or_action_rank_nll"
    elif rank_enabled:
        selection_metric = "validation_action_rank_nll"
    else:
        selection_metric = "validation_value_mse"
    optimizer_step_source = (
        "rank_batches_only"
        if rank_enabled and not value_enabled
        else "value_batches_only"
        if value_enabled and not rank_enabled
        else "value_and_rank_batches"
    )
    rng = np.random.RandomState(seed)
    history = []
    global_step = 0
    best_value_mse = float("inf")
    best_rank_nll = float("inf")
    best_epoch = 0
    best_model_state: Optional[Dict[str, torch.Tensor]] = None
    patience = 0
    started = time.perf_counter()
    train_states = dataset.split_state_indices["train"]
    train_groups = dataset.split_group_state_indices["train"]

    for epoch in range(1, int(training_cfg["epochs"]) + 1):
        model.train()
        value_losses = []
        rank_losses = []
        value_batches = (
            list(_iter_batches(train_states, value_batch_size, rng)) if value_enabled else []
        )
        rank_batches = (
            list(_iter_batches(train_groups, rank_groups_per_batch, rng))
            if rank_enabled
            else []
        )
        batch_count = max(len(value_batches), len(rank_batches))
        for batch_index in range(batch_count):
            optimizer.zero_grad()
            total_loss = None
            if batch_index < len(value_batches):
                indices = value_batches[batch_index]
                inputs = torch.from_numpy(
                    dataset.state_features[indices].astype(np.float32)
                ).to(device)
                targets = torch.from_numpy(dataset.state_value_targets[indices]).to(device)
                predictions = model.value_from_embedding(model.encode_states(inputs))
                value_loss = F.mse_loss(predictions, targets)
                total_loss = value_weight * value_loss
                value_losses.append(float(value_loss.item()))
            if rank_enabled and batch_index < len(rank_batches):
                group_indices = rank_batches[batch_index]
                rank_states, rank_actions, labels, ranges, local_indices = _rank_batch(
                    dataset, group_indices
                )
                state_tensor = torch.from_numpy(rank_states).to(device)
                action_tensor = torch.from_numpy(rank_actions).to(device)
                label_tensor = torch.from_numpy(labels).to(device)
                local_tensor = torch.from_numpy(local_indices).to(device)
                embeddings = model.encode_states(state_tensor)
                scores = model.rank_from_embeddings(
                    embeddings[local_tensor], action_tensor
                )
                rank_loss = grouped_action_rank_loss(scores, label_tensor, ranges)
                total_loss = (
                    rank_weight * rank_loss
                    if total_loss is None
                    else total_loss + rank_weight * rank_loss
                )
                rank_losses.append(float(rank_loss.item()))
            if total_loss is None:
                continue
            total_loss.backward()
            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            global_step += 1

        value_train = (
            _value_metrics(
                model, dataset, dataset.split_state_indices["train"], device, value_batch_size
            )
            if value_enabled
            else None
        )
        value_validation = (
            _value_metrics(
                model, dataset, dataset.split_state_indices["validation"], device, value_batch_size
            )
            if value_enabled
            else None
        )
        rank_validation = (
            _rank_metrics(
                model,
                dataset,
                dataset.split_group_state_indices["validation"],
                device,
            )
            if rank_enabled
            else None
        )
        improved = False
        if value_enabled and value_validation is not None and value_validation["mse"] < best_value_mse:
            improved = True
        if rank_enabled and rank_validation is not None and rank_validation["nll"] < best_rank_nll:
            improved = True
        if improved:
            if value_enabled and value_validation is not None:
                best_value_mse = min(best_value_mse, value_validation["mse"])
            if rank_validation is not None:
                best_rank_nll = min(best_rank_nll, rank_validation["nll"])
            best_model_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            best_epoch = epoch
            patience = 0
        else:
            patience += 1
        epoch_report = {
            "epoch": epoch,
            "value_train_mse": float(np.mean(value_losses)) if value_losses else None,
            "value_train": value_train,
            "action_rank_train_nll": float(np.mean(rank_losses)) if rank_losses else None,
            "value_validation": value_validation,
            "action_rank_validation": rank_validation,
            "global_step": global_step,
        }
        history.append(epoch_report)
        rank_text = (
            f" rank_nll={rank_validation['nll']:.4f}"
            f" rank_top1={rank_validation['top1']:.3f}"
            if rank_validation is not None
            else " rank=disabled"
        )
        value_text = (
            f"train_value_mse={value_train['mse']:.4f} val_value_mse={value_validation['mse']:.4f}"
            if value_enabled and value_train is not None and value_validation is not None
            else "value=disabled"
        )
        print_line_safe(
            f"train-vnext-diagnostic epoch={epoch} {value_text}{rank_text}"
        )
        payload = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "model_type": config["model"]["type"],
            **build_vnext_checkpoint_metadata(dataset),
            "model_config": config["model"],
            "heads_trained": dict(heads_trained),
            "checkpoint_selection_metric": selection_metric,
            "epoch": epoch,
            "global_step": global_step,
            "training_history": history,
            "config_path": str(config_path.resolve()),
            "production_eligible": False,
        }
        checkpoint_path = Path(config["_resolved_output_paths"]["checkpoint_path"])
        best_path = Path(config["_resolved_output_paths"]["best_checkpoint_path"])
        if epoch % int(training_cfg["save_every_epochs"]) == 0:
            save_checkpoint(checkpoint_path, payload)
        if improved:
            save_checkpoint(best_path, payload)
        if patience >= int(training_cfg["early_stopping_patience_epochs"]):
            break

    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    test_value = (
        _value_metrics(
            model, dataset, dataset.split_state_indices["test"], device, value_batch_size
        )
        if value_enabled
        else None
    )
    test_rank = (
        _rank_metrics(
            model,
            dataset,
            dataset.split_group_state_indices["test"],
            device,
        )
        if rank_enabled
        else None
    )
    report = {
        "status": "completed",
        "training_launched": True,
        "config_path": str(config_path.resolve()),
        "dataset_validation": dataset.validation,
        "device": device.type,
        "epochs_completed": len(history),
        "global_step": global_step,
        "heads_trained": dict(heads_trained),
        "optimizer_step_source": optimizer_step_source,
        "checkpoint_selection_metric": selection_metric,
        "best_epoch": best_epoch,
        "best_validation_value_mse": best_value_mse if value_enabled else None,
        "best_validation_action_rank_nll": (
            best_rank_nll if rank_enabled else None
        ),
        "test_split_evaluations": 1,
        "runtime_sec": time.perf_counter() - started,
        "overfit_check": overfit_result,
        "training_history": history,
        "test_value": test_value,
        "test_action_rank": test_rank,
        "production_eligible": False,
    }
    report_json = Path(config["_resolved_output_paths"]["report_json_path"])
    report_md = Path(config["_resolved_output_paths"]["report_md_path"])
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# vNext Diagnostic Training Report",
                "",
                f"- Epochs: {report['epochs_completed']}",
                f"- Runtime: {report['runtime_sec']:.2f}s",
                f"- Heads trained: {report['heads_trained']}",
                f"- Checkpoint selection: {report['checkpoint_selection_metric']}",
                (
                    f"- Test value MSE: {test_value['mse']:.6f}"
                    if test_value is not None
                    else "- State value: disabled"
                ),
                (
                    f"- Test action top-1/top-3: {test_rank['top1']:.3f} / {test_rank['top3']:.3f}"
                    if test_rank is not None
                    else "- Action rank: disabled"
                ),
                "- Production eligible: no",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(
        description="Validate or train the frozen v7/v5 diagnostic multitask model."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    config_path = Path(args.config)
    if args.validate_only:
        return validate_diagnostic_wiring(config_path)
    return train_diagnostic(config_path)


if __name__ == "__main__":
    main()
