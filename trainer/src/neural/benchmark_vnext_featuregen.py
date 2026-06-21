import argparse
import hashlib
import json
import os
import pickle
import subprocess
import time
import tracemalloc
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .action_features import (
    ACTION_FEATURE_DIM,
    ACTION_FEATURE_DIM_V5,
    ACTION_FEATURE_NAMES_V5,
    ACTION_FEATURE_VERSION,
    ACTION_FEATURE_VERSION_V5,
    ACTION_FEATURE_VERSION_V6,
    ACTION_FEATURE_VERSION_V7,
    action_feature_schema,
    to_id,
)
from .build_action_rank_dataset import _legal_actions_from_private_state
from .build_live_private_value_dataset import (
    _replay_roster_alias_id,
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
    actor_private_switch_relabel,
)
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V7,
    FEATURE_NAMES_V7,
    FEATURE_VERSION,
    FEATURE_VERSION_V7,
    build_live_private_feature_vector,
    public_feature_vector_from_trajectory,
)
from .logging_helper import print_line_safe
from .parse_replay_logs import parse_protocol_log
from .resolved_action_impact import resolve_action_impact
from .tactical_state import build_tactical_state
from .vnext_labels import (
    ACTION_RANK_TARGET,
    ACTION_VALUE_STATUS,
    LABEL_VERSION,
    STATE_VALUE_TARGET,
    chosen_action_label,
    match_chosen_action,
    state_value_label,
)


BENCHMARK_VERSION = "vnext-featuregen-tiny-v1"
DEFAULT_MANIFEST = Path("artifacts/training_plan/manifests/diagnostic_300_manifest.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/training_plan/benchmarks/vnext_featuregen_tiny_10")
DEFAULT_FULL_OUTPUT_DIR = Path("artifacts/training_plan/datasets/diagnostic_300_v7_v5")
DEFAULT_LABEL_MANIFEST = Path("artifacts/training_plan/vnext_label_manifest.json")
DEFAULT_SEED = 20260619
DEFAULT_BATTLES = 10
# Conservative default for a 16 GB / 8-logical-CPU box: each worker also spawns a
# node sim-core process, so leave headroom rather than saturating all cores.
DEFAULT_WORKERS = 4
SPLIT_QUOTAS_10 = {"train": 4, "validation": 3, "test": 3}
RARE_MECHANICS = {
    "transform",
    "illusion",
    "type_change",
    "tailwind",
    "recharge_lock_constraints",
    "encore",
    "disable",
}


def _repeat_chain_enabled(action_feature_version: str) -> bool:
    return action_feature_version in {ACTION_FEATURE_VERSION_V6, ACTION_FEATURE_VERSION_V7}


def _stable_key(seed: int, replay_id: str, namespace: str) -> str:
    return hashlib.sha256(f"{seed}:{namespace}:{replay_id}".encode("utf-8")).hexdigest()


def _mechanic_score(entry: Dict[str, Any]) -> int:
    mechanics = entry.get("mechanics") if isinstance(entry.get("mechanics"), dict) else {}
    total = sum(bool(value) for value in mechanics.values())
    rare = sum(bool(mechanics.get(name)) for name in RARE_MECHANICS)
    return total + 3 * rare


def select_manifest_subset(
    manifest: Dict[str, Any],
    *,
    size: int = DEFAULT_BATTLES,
    seed: int = DEFAULT_SEED,
) -> List[Dict[str, Any]]:
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    if size <= 0 or size > len(entries):
        raise ValueError(f"Subset size must be between 1 and {len(entries)}, got {size}.")
    if size == 10:
        quotas = dict(SPLIT_QUOTAS_10)
    else:
        available_splits = [name for name in ("train", "validation", "test") if any(row.get("split") == name for row in entries)]
        quotas = {name: 1 for name in available_splits[: min(size, len(available_splits))]}
        remaining = size - sum(quotas.values())
        for index in range(remaining):
            quotas[available_splits[index % len(available_splits)]] += 1

    selected: List[Dict[str, Any]] = []
    for split, count in quotas.items():
        candidates = [row for row in entries if row.get("split") == split]
        candidates.sort(
            key=lambda row: (
                -_mechanic_score(row),
                abs(int(row.get("turn_count", 0) or 0) - 25),
                _stable_key(seed, str(row.get("replay_id")), split),
            )
        )
        if len(candidates) < count:
            raise ValueError(f"Split {split!r} has only {len(candidates)} entries; need {count}.")
        selected.extend(candidates[:count])
    if len(selected) != size:
        raise ValueError(f"Subset selection produced {len(selected)} entries, expected {size}.")
    ids = [str(row.get("replay_id")) for row in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Subset selection produced duplicate replay IDs.")
    return sorted(selected, key=lambda row: (str(row.get("split")), str(row.get("replay_id"))))


def _git_commit() -> Optional[str]:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _names_fingerprint(names: Sequence[str]) -> str:
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _overwrite_guard(output_dir: Path, manifest_path: Path) -> Tuple[bool, str]:
    """Reject pointing a new manifest at a dataset built from a different manifest.

    Idempotent re-runs of the same manifest are allowed (the existing convention);
    a mismatching source manifest is treated as an accidental overwrite.
    """
    existing_metadata = output_dir / "feature_metadata.json"
    if not existing_metadata.is_file():
        return True, "fresh_or_empty_output_dir"
    try:
        existing = json.loads(existing_metadata.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, "unreadable_existing_metadata"
    existing_sha = existing.get("source_manifest_sha256")
    new_sha = _file_sha256(manifest_path) if manifest_path.is_file() else None
    if existing_sha and new_sha and existing_sha != new_sha:
        return False, f"existing_dataset_from_different_manifest_sha256={existing_sha}"
    return True, "same_manifest_or_unknown"


def _explicit_protocol_team_sizes(path: Path) -> Dict[str, int]:
    sizes: Dict[str, int] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.startswith("|teamsize|"):
            continue
        parts = raw_line.split("|")
        if len(parts) >= 4 and parts[2] in ("p1", "p2"):
            try:
                sizes[parts[2]] = int(parts[3])
            except ValueError:
                continue
    return sizes


def _unsupported_team_size_entries(entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unsupported = []
    for entry in entries:
        path = Path(str(entry.get("path") or ""))
        if not path.is_file():
            continue
        sizes = _explicit_protocol_team_sizes(path)
        if any(size <= 0 or size > 6 for size in sizes.values()):
            unsupported.append(
                {
                    "replay_id": str(entry.get("replay_id") or ""),
                    "team_sizes": sizes,
                }
            )
    return unsupported


def _validate_supported_replay_team_sizes(
    trajectory: Dict[str, Any], *, replay_id: str
) -> None:
    sizes = trajectory.get("teamsize") if isinstance(trajectory.get("teamsize"), dict) else {}
    unsupported = {
        str(side): int(size)
        for side, size in sizes.items()
        if int(size) <= 0 or int(size) > 6
    }
    if unsupported:
        raise ValueError(
            f"{replay_id}: explicit team sizes {unsupported} exceed the frozen six-slot schema"
        )


def _validate_full_preflight(
    *,
    manifest: Dict[str, Any],
    manifest_path: Path,
    output_dir: Path,
    label_manifest_path: Path = DEFAULT_LABEL_MANIFEST,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Dict[str, Any]:
    """Generalized full-manifest preflight.

    Expected battle/split counts are derived from the manifest's ``split_targets``
    (falling back to the observed entry split distribution), so manifests other
    than the legacy 300-battle one are accepted without weakening any check.
    """
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    replay_ids = [str(row.get("replay_id") or "") for row in entries]
    split_counts = Counter(str(row.get("split") or "") for row in entries)
    split_targets = manifest.get("split_targets")
    if isinstance(split_targets, dict) and split_targets:
        expected_split_counts = Counter({str(key): int(value) for key, value in split_targets.items()})
    else:
        expected_split_counts = Counter(split_counts)
    expected_total = sum(expected_split_counts.values())
    missing_paths = [str(row.get("path") or "") for row in entries if not Path(str(row.get("path") or "")).is_file()]
    replay_to_splits: Dict[str, set] = {}
    for row in entries:
        replay_to_splits.setdefault(str(row.get("replay_id") or ""), set()).add(str(row.get("split") or ""))
    label_manifest = json.loads(label_manifest_path.read_text(encoding="utf-8"))
    compatibility = label_manifest.get("schema_compatibility") or {}
    action_schema = action_feature_schema(action_feature_version)
    overwrite_ok, overwrite_reason = _overwrite_guard(output_dir, manifest_path)
    unsupported_team_sizes = _unsupported_team_size_entries(entries)
    checks = {
        "manifest_has_entries": len(entries) > 0,
        "entry_count_matches_split_targets": len(entries) == expected_total,
        "unique_ids": len(set(replay_ids)) == len(entries) and all(replay_ids),
        "split_sizes_match_targets": split_counts == expected_split_counts,
        "no_split_overlap": all(len(splits) == 1 for splits in replay_to_splits.values()),
        "all_paths_exist": not missing_paths,
        "team_sizes_fit_frozen_six_slot_schema": not unsupported_team_sizes,
        "label_manifest_valid": (
            label_manifest.get("label_version") == LABEL_VERSION
            and compatibility.get("state_feature_version") == FEATURE_VERSION_V7
            and compatibility.get("state_feature_dim") == FEATURE_DIM_V7
            and compatibility.get("action_feature_version") in {
                ACTION_FEATURE_VERSION_V5,
                action_feature_version,
            }
            and int(compatibility.get("action_feature_dim", 0) or 0) in {
                ACTION_FEATURE_DIM_V5,
                int(action_schema["dim"]),
            }
            and (label_manifest.get("action_value") or {}).get("target_status") == ACTION_VALUE_STATUS
        ),
        "schema_dimensions_requested": FEATURE_DIM_V7 == 3208 and int(action_schema["dim"]) > 0,
        "output_dir_safe_to_write": overwrite_ok,
    }
    if not all(checks.values()):
        raise ValueError(
            f"full-manifest preflight failed: checks={checks}, "
            f"missing_paths={missing_paths[:5]}, "
            f"unsupported_team_sizes={unsupported_team_sizes[:5]}, "
            f"overwrite={overwrite_reason}"
        )
    return {
        "checks": checks,
        "manifest_path": str(manifest_path),
        "manifest_sha256": _file_sha256(manifest_path),
        "label_manifest_path": str(label_manifest_path),
        "label_manifest_sha256": _file_sha256(label_manifest_path),
        "split_counts": dict(split_counts),
        "expected_split_counts": dict(expected_split_counts),
        "expected_total_battles": expected_total,
        "unsupported_team_size_replays": unsupported_team_sizes,
        "overwrite_reason": overwrite_reason,
    }


def _damage_client() -> Any:
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    if not command_json or not cwd:
        return None
    from .env_client import SimCoreClient

    client = SimCoreClient(json.loads(command_json), cwd)
    client.ping()
    return client


def _opponent_view(tactical_state: Dict[str, Any]) -> Dict[str, Any]:
    opponent = tactical_state.get("opponent") if isinstance(tactical_state.get("opponent"), dict) else {}
    species = opponent.get("active_current_species") or opponent.get("active_species")
    if not species:
        return {"opponent_team": []}
    mon = {
        "species": species,
        "hp_fraction": opponent.get("active_hp_fraction", 1.0),
        "types": list(opponent.get("active_current_types") or opponent.get("active_base_types") or []),
        "status": opponent.get("active_status"),
        "item": opponent.get("active_item"),
        "ability": opponent.get("active_current_ability"),
        "boosts": dict(opponent.get("boosts") or {}),
        "tera_type": opponent.get("active_tera_type"),
        "terastallized": bool(opponent.get("active_terastallized")),
    }
    return {"opponent_team": [mon]}


def _trajectory_prefix_before_event(
    trajectory: Dict[str, Any],
    *,
    turn_number: int,
    event: Dict[str, Any],
    turn_events: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    prefix = dict(trajectory)
    cutoff_event = event
    if event.get("type") == "move":
        for candidate in reversed(list(turn_events)):
            if candidate is event:
                continue
            if candidate.get("type") == "tera" and candidate.get("side") == event.get("side"):
                cutoff_event = candidate
                break
    earlier_events = []
    for candidate in turn_events:
        if candidate is cutoff_event:
            break
        earlier_events.append(candidate)
    prior_turns = [
        dict(turn)
        for turn in trajectory.get("turns", [])
        if isinstance(turn, dict) and int(turn.get("turn", 0) or 0) < int(turn_number)
    ]
    if earlier_events:
        prior_turns.append({"turn": int(turn_number), "events": list(earlier_events)})
    prefix["turns"] = prior_turns
    prefix["total_turns"] = int(turn_number)

    raw_target = str(cutoff_event.get("raw") or "")
    same_raw_before = 0
    found_event = False
    for turn in trajectory.get("turns", []):
        for candidate in turn.get("events", []) if isinstance(turn, dict) else []:
            if candidate is cutoff_event:
                found_event = True
                break
            if str(candidate.get("raw") or "") == raw_target:
                same_raw_before += 1
        if found_event:
            break
    prefix_log = []
    raw_seen = 0
    for line in trajectory.get("protocol_log", []):
        if raw_target and str(line) == raw_target:
            if raw_seen == same_raw_before:
                break
            raw_seen += 1
        prefix_log.append(str(line))
    prefix["protocol_log"] = prefix_log
    return prefix


def _completed_teams_for_action_reconstruction(
    trajectory: Dict[str, Any],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    original = _reconstructed_completed_private_teams(trajectory)
    teams: Dict[str, Dict[str, Dict[str, Any]]] = {"p1": {}, "p2": {}}
    active: Dict[str, Optional[str]] = {"p1": None, "p2": None}
    active_stint_moves: Dict[str, set] = {"p1": set(), "p2": set()}
    transformed: Dict[str, bool] = {"p1": False, "p2": False}
    canonical_species: Dict[str, Dict[str, str]] = {"p1": {}, "p2": {}}

    def ensure(side: str, species: str) -> Dict[str, Any]:
        alias_id = _replay_roster_alias_id(species)
        species = canonical_species[side].setdefault(alias_id, species)
        return teams[side].setdefault(
            species,
            {"species": species, "moves": set(), "item": None, "ability": None, "tera_type": None},
        )

    for turn in sorted(trajectory.get("turns", []), key=lambda row: int(row.get("turn", 0) or 0)):
        for event in turn.get("events", []) if isinstance(turn, dict) else []:
            if not isinstance(event, dict):
                continue
            side = event.get("side")
            if side not in ("p1", "p2"):
                continue
            if event.get("type") == "switch":
                details = str(event.get("details") or "")
                species = details.split(",", 1)[0].strip()
                if species:
                    active[side] = species
                    active_stint_moves[side] = set()
                    transformed[side] = False
                    ensure(side, species)
            elif event.get("type") == "transform":
                transformed[side] = True
            elif event.get("type") == "replace":
                details = str(event.get("details") or "")
                species = details.split(",", 1)[0].strip()
                if species:
                    previous = active.get(side)
                    revealed = ensure(side, species)
                    if previous and _replay_roster_alias_id(previous) != _replay_roster_alias_id(species):
                        previous_slot = ensure(side, str(previous))
                        for move in active_stint_moves[side]:
                            previous_slot["moves"].discard(move)
                            revealed["moves"].add(move)
                    active[side] = species
                    active_stint_moves[side] = set()
            elif event.get("type") == "move" and event.get("move") and active.get(side):
                # Copied moves used while transformed (Imposter/Transform) are
                # transient stint facts; do not attribute them to the base
                # species' global moveset.
                if not transformed[side]:
                    move = str(event["move"])
                    ensure(side, str(active[side]))["moves"].add(move)
                    active_stint_moves[side].add(move)
            elif event.get("type") == "tera" and event.get("tera_type") and active.get(side):
                ensure(side, str(active[side]))["tera_type"] = str(event["tera_type"])

    for side in ("p1", "p2"):
        original_by_id = {to_id(species): data for species, data in original.get(side, {}).items()}
        original_by_alias: Dict[str, Dict[str, Any]] = {}
        for species, source in original.get(side, {}).items():
            alias_id = _replay_roster_alias_id(species)
            merged = original_by_alias.setdefault(
                alias_id,
                {"species": species, "moves": set(), "item": None, "ability": None, "tera_type": None},
            )
            for key in ("item", "ability", "tera_type"):
                if merged.get(key) is None and source.get(key) is not None:
                    merged[key] = source[key]
        for species, data in teams[side].items():
            source = original_by_id.get(to_id(species), {}) or original_by_alias.get(_replay_roster_alias_id(species), {})
            for key in ("item", "ability", "tera_type"):
                if data.get(key) is None and source.get(key) is not None:
                    data[key] = source[key]
    return teams


def _candidate_summaries(actions: Sequence[Dict[str, Any]]) -> List[str]:
    return [
        f"{action.get('kind')}:{action.get('move') or action.get('species') or action.get('label')}"
        for action in actions
    ]


def _mismatch_reason(chosen_label: str, actions: Sequence[Dict[str, Any]]) -> str:
    chosen_kind, chosen_name = chosen_label.split(":", 1)
    chosen_id = "".join(char for char in chosen_name.lower() if char.isalnum())
    same_name_kinds = []
    for action in actions:
        action_name = str(action.get("move") or action.get("species") or action.get("label") or "")
        if ":" in action_name:
            action_name = action_name.split(":", 1)[1]
        action_id = "".join(char for char in action_name.lower() if char.isalnum())
        if action_id == chosen_id:
            same_name_kinds.append(str(action.get("kind") or ""))
    if same_name_kinds:
        return "action_kind_or_tera_availability_mismatch"
    if chosen_kind.strip() == "switch":
        return "switch_target_missing_from_pre_action_legal_roster"
    if chosen_kind.strip() in {"move", "move_tera"}:
        return "move_missing_from_reconstructed_active_moves"
    return "unsupported_or_unknown_action"


def _context_for_prefix(
    *,
    trajectory: Dict[str, Any],
    prefix: Dict[str, Any],
    side: str,
    through_turn: int,
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    sets_path: Optional[str],
) -> Tuple[np.ndarray, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
    private_state = _reconstructed_private_state_for_side(
        prefix,
        side=side,
        through_turn=through_turn,
        completed_teams=completed_teams,
        full_trajectory=trajectory,
    )
    opponent_belief = build_opponent_beliefs(
        protocol_log=prefix.get("protocol_log", []),
        trajectory=prefix,
        player_side=side,
        sets_path=sets_path,
    )
    tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
    private_state["opponent_belief"] = opponent_belief
    private_state["tactical_state"] = tactical_state
    own_tactical = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
    private_state["tera_used"] = bool(own_tactical.get("tera_used"))
    private_state["can_tera"] = not private_state["tera_used"]
    active_species = private_state.get("active_species")
    completed_active = completed_teams.get(side, {}).get(active_species, {}) if active_species else {}
    private_state["active_tera_type"] = completed_active.get("tera_type")
    return public_features, private_state, opponent_belief, tactical_state


def _decision_features(
    *,
    trajectory: Dict[str, Any],
    side: str,
    turn_number: int,
    event: Dict[str, Any],
    turn_events: Sequence[Dict[str, Any]],
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    original_completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    sets_path: Optional[str],
    damage_client: Any,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Optional[Dict[str, Any]]:
    chosen_label = chosen_action_label(event, turn_events=turn_events)
    chosen_label = actor_private_switch_relabel(chosen_label, trajectory, side, event)
    if not chosen_label:
        return None
    context_turn = max(0, int(turn_number) - 1)
    legacy_prefix = _trajectory_prefix_for_training(trajectory, context_turn)
    _, legacy_private, _, _ = _context_for_prefix(
        trajectory=trajectory,
        prefix=legacy_prefix,
        side=side,
        through_turn=context_turn,
        completed_teams=original_completed_teams,
        sets_path=sets_path,
    )
    legacy_actions = _legal_actions_from_private_state(legacy_private, "")
    legacy_match = match_chosen_action(legacy_actions, chosen_label)

    prefix = _trajectory_prefix_before_event(
        trajectory=trajectory,
        turn_number=turn_number,
        event=event,
        turn_events=turn_events,
    )
    public_features, private_state, opponent_belief, tactical_state = _context_for_prefix(
        trajectory=trajectory,
        prefix=prefix,
        side=side,
        through_turn=turn_number,
        completed_teams=completed_teams,
        sets_path=sets_path,
    )
    state_features, state_debug = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=side,
        tactical_state=tactical_state,
        feature_version=FEATURE_VERSION_V7,
    )
    # Empty chosen label prevents the legacy helper from injecting an unmatched
    # replay action into the candidate set. Unmatched decisions are explicit.
    actions = _legal_actions_from_private_state(private_state, "")
    chosen_ordinal = match_chosen_action(actions, chosen_label)
    outcome = state_value_label(trajectory.get("winner_side"), side)

    approx_state = {
        "private_state": private_state,
        "opponent_belief": opponent_belief,
        "tactical_state": tactical_state,
        "view": _opponent_view(tactical_state),
    }
    action_features = []
    impact_methods: Counter[str] = Counter()
    action_schema = action_feature_schema(action_feature_version)
    action_builder = action_schema["builder"]
    for action in actions:
        impact = resolve_action_impact(
            action,
            approx_state,
            client=damage_client,
            enable_repeat_chain=_repeat_chain_enabled(action_feature_version),
        )
        impact_methods[str(impact.get("method") or "unavailable")] += 1
        action_features.append(
            action_builder(
                action,
                private_state,
                tactical_state=tactical_state,
                impact=impact,
            )
        )
    return {
        "state_features": state_features,
        "state_debug": state_debug,
        "actions": actions,
        "action_features": action_features,
        "observed": [1 if index == chosen_ordinal else 0 for index in range(len(actions))],
        "chosen_label": chosen_label,
        "chosen_ordinal": chosen_ordinal,
        "matched": chosen_ordinal is not None,
        "legacy_matched": legacy_match is not None,
        "state_value_target": outcome,
        "impact_methods": impact_methods,
        "turn": int(turn_number),
        "side": side,
        "raw_command": event.get("raw"),
        "candidate_summaries": _candidate_summaries(actions),
        "legacy_candidate_summaries": _candidate_summaries(legacy_actions),
        "mismatch_reason": None if chosen_ordinal is not None else _mismatch_reason(chosen_label, actions),
        "legacy_mismatch_reason": None if legacy_match is not None else _mismatch_reason(chosen_label, legacy_actions),
    }


def benchmark_metadata(
    *,
    manifest: Dict[str, Any],
    selected_entries: Sequence[Dict[str, Any]],
    seed: int,
    manifest_path: Path = DEFAULT_MANIFEST,
    command: Optional[str] = None,
    artifact_kind: str = "tiny_10_benchmark",
    preflight: Optional[Dict[str, Any]] = None,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Dict[str, Any]:
    action_schema = action_feature_schema(action_feature_version)
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "artifact_kind": artifact_kind,
        "state_feature_version": FEATURE_VERSION_V7,
        "state_feature_dim": FEATURE_DIM_V7,
        "state_feature_names_sha256": _names_fingerprint(FEATURE_NAMES_V7),
        "action_feature_version": action_schema["version"],
        "action_feature_dim": action_schema["dim"],
        "action_feature_names_sha256": _names_fingerprint(action_schema["names"]),
        "live_default_state_feature_version": FEATURE_VERSION,
        "live_default_state_feature_dim": FEATURE_DIM,
        "live_default_action_feature_version": ACTION_FEATURE_VERSION,
        "live_default_action_feature_dim": ACTION_FEATURE_DIM,
        "dtype_on_disk": "float16",
        "generation_dtype": "float32",
        "storage_layout": "one state row per decision; separate candidate action rows linked by candidate_state_indices",
        "state_vectors_duplicated_per_candidate": False,
        "selection_seed": seed,
        "manifest_version": manifest.get("manifest_version"),
        "manifest_seed": manifest.get("seed"),
        "manifest_catalog_checksum": manifest.get("catalog_checksum"),
        "source_manifest_path": str(manifest_path),
        "source_manifest_sha256": _file_sha256(manifest_path) if manifest_path.is_file() else None,
        "source_replay_pool_path": manifest.get("catalog_path"),
        "profile_versions": sorted({
            str(row.get("profile_version"))
            for row in selected_entries
            if row.get("profile_version")
        }),
        "selected_replay_ids": [str(row.get("replay_id")) for row in selected_entries],
        "selected_splits": {str(row.get("replay_id")): str(row.get("split")) for row in selected_entries},
        "source_commit": _git_commit(),
        "generation_timestamp_utc": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "command": command,
        "preflight": preflight,
        "information_boundary": (
            "Public replay protocol prefixes and randbats opponent beliefs are used. "
            "Own-side private state follows the existing replay-training assumption that "
            "later public reveals may complete the own roster/moves; no true hidden opponent "
            "team or original private request payload is read."
        ),
        "label_version": LABEL_VERSION,
        "state_value_target": STATE_VALUE_TARGET,
        "action_rank_target": ACTION_RANK_TARGET,
        "action_value_target_status": ACTION_VALUE_STATUS,
    }


def validate_benchmark_arrays(arrays: Dict[str, np.ndarray], metadata: Dict[str, Any]) -> Dict[str, Any]:
    action_schema = action_feature_schema(str(metadata.get("action_feature_version") or ""))
    action_dim = int(action_schema["dim"])
    action_names = list(action_schema["names"])
    states = arrays["state_features"]
    actions = arrays["action_features"]
    state_ids = [str(value) for value in arrays["state_replay_ids"].tolist()]
    state_splits = [str(value) for value in arrays["state_splits"].tolist()]
    candidate_state_indices = arrays["candidate_state_indices"]
    value_targets = arrays["state_value_targets"]
    rank_labels = arrays["action_rank_labels"]
    grouped_positive_counts = [
        int(rank_labels[candidate_state_indices == state_index].sum())
        for state_index in np.unique(candidate_state_indices)
    ]
    replay_split_pairs = set(zip(state_ids, state_splits))
    replay_to_splits: Dict[str, set] = {}
    for replay_id, split in replay_split_pairs:
        replay_to_splits.setdefault(replay_id, set()).add(split)
    manifest_ids = set(str(value) for value in metadata["selected_replay_ids"])
    selected_splits = {
        str(replay_id): str(split)
        for replay_id, split in (metadata.get("selected_splits") or {}).items()
    }
    embedded_state_names = [str(value) for value in arrays.get("state_feature_names", np.asarray([])).tolist()]
    embedded_action_names = [str(value) for value in arrays.get("action_feature_names", np.asarray([])).tolist()]
    checks = {
        "state_dim_3208": states.ndim == 2 and states.shape[1] == FEATURE_DIM_V7,
        "action_dim_matches_schema": actions.ndim == 2 and actions.shape[1] == action_dim,
        "state_dtype_float16": states.dtype == np.float16,
        "action_dtype_float16": actions.dtype == np.float16,
        "candidate_state_indices_valid": (
            candidate_state_indices.ndim == 1
            and candidate_state_indices.shape[0] == actions.shape[0]
            and (candidate_state_indices.size == 0 or (
                int(candidate_state_indices.min()) >= 0
                and int(candidate_state_indices.max()) < states.shape[0]
            ))
        ),
        "no_battle_crosses_splits": all(len(splits) == 1 for splits in replay_to_splits.values()),
        "all_examples_trace_to_manifest": set(state_ids).issubset(manifest_ids),
        "all_selected_battles_represented": (
            set(state_ids) == manifest_ids
            if str(metadata.get("artifact_kind") or "").endswith("materialization")
            else set(state_ids).issubset(manifest_ids)
        ),
        "state_splits_match_manifest": all(
            selected_splits.get(replay_id) == split
            for replay_id, split in replay_split_pairs
        ),
        "metadata_records_requested_schema": (
            metadata.get("state_feature_version") == FEATURE_VERSION_V7
            and metadata.get("action_feature_version") == action_schema["version"]
        ),
        "metadata_records_name_fingerprints": (
            metadata.get("state_feature_names_sha256") == _names_fingerprint(FEATURE_NAMES_V7)
            and metadata.get("action_feature_names_sha256") == _names_fingerprint(action_names)
        ),
        "embedded_names_match_schema_and_metadata": (
            embedded_state_names == list(FEATURE_NAMES_V7)
            and embedded_action_names == action_names
            and _names_fingerprint(embedded_state_names) == metadata.get("state_feature_names_sha256")
            and _names_fingerprint(embedded_action_names) == metadata.get("action_feature_names_sha256")
        ),
        "metadata_records_manifest_profile_source": (
            bool(metadata.get("manifest_version"))
            and bool(metadata.get("manifest_catalog_checksum"))
            and bool(metadata.get("profile_versions"))
            and bool(metadata.get("source_commit"))
        ),
        "live_defaults_unchanged": (
            metadata.get("live_default_state_feature_version") == "live-private-belief-v2"
            and metadata.get("live_default_action_feature_version") == "legal-action-v3"
        ),
        "state_not_duplicated_per_candidate": not metadata.get("state_vectors_duplicated_per_candidate"),
        "state_value_labels_valid": (
            value_targets.shape == (states.shape[0],)
            and set(float(value) for value in np.unique(value_targets)).issubset({-1.0, 1.0})
        ),
        "action_rank_labels_valid": (
            rank_labels.shape == (actions.shape[0],)
            and all(count == 1 for count in grouped_positive_counts)
        ),
        "action_value_labels_absent": (
            metadata.get("action_value_target_status") == "not_generated"
            and not any(str(name).startswith("action_value") for name in arrays)
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_benchmark(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    battles: int = DEFAULT_BATTLES,
    seed: int = DEFAULT_SEED,
    sets_path: Optional[str] = None,
    full_manifest: bool = False,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    action_schema = action_feature_schema(action_feature_version)
    is_legacy_300 = full_manifest and output_dir.resolve() == DEFAULT_FULL_OUTPUT_DIR.resolve()
    # Dataset name derives from the output directory; the report name drops the
    # trailing schema suffix, preserving both the legacy diagnostic_300 filename
    # and the diagnostic_1000_action_rank convention.
    dataset_name = output_dir.name
    if full_manifest:
        if is_legacy_300:
            command = ".\\scripts\\run_windows.ps1 -Action materialize-diagnostic-300 -SimCoreMode native"
        else:
            command = (
                "python -m neural.benchmark_vnext_featuregen --full-manifest "
                f"--manifest {manifest_path} --output-dir {output_dir}"
            )
    else:
        command = (
            "python -m neural.benchmark_vnext_featuregen "
            f"--manifest {manifest_path} --output-dir {output_dir} --battles {battles} "
            f"--action-feature-version {action_feature_version}"
        )
    preflight = (
        _validate_full_preflight(
            manifest=manifest,
            manifest_path=manifest_path,
            output_dir=output_dir,
            action_feature_version=action_feature_version,
        )
        if full_manifest
        else None
    )
    selected_entries = (
        list(manifest.get("entries") or [])
        if full_manifest
        else select_manifest_subset(manifest, size=battles, seed=seed)
    )
    battles = len(selected_entries)
    metadata = benchmark_metadata(
        manifest=manifest,
        selected_entries=selected_entries,
        seed=seed,
        manifest_path=manifest_path,
        command=command,
        artifact_kind=(
            ("diagnostic_300_materialization" if is_legacy_300 else "diagnostic_full_materialization")
            if full_manifest
            else "tiny_10_benchmark"
        ),
        preflight=preflight,
        action_feature_version=action_feature_version,
    )
    metadata["dataset_name"] = dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    subset_path = output_dir / ("source_manifest_snapshot.json" if full_manifest else "subset_manifest.json")
    dataset_path = output_dir / (f"{dataset_name}.npz" if full_manifest else "vnext_features_tiny_10.npz")
    metadata_path = output_dir / "feature_metadata.json"
    report_json_path = output_dir / ("materialization_report.json" if full_manifest else "benchmark_report.json")
    report_md_path = (
        output_dir / (dataset_name.replace("_v7_v5", "") + "_materialization_report.md")
        if full_manifest
        else output_dir.parent / "vnext_featuregen_tiny_10_report.md"
    )
    subset_path.write_text(
        json.dumps({"metadata": metadata, "entries": selected_entries}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    state_rows: List[np.ndarray] = []
    state_replay_ids: List[str] = []
    state_splits: List[str] = []
    state_turns: List[int] = []
    state_sides: List[str] = []
    action_rows: List[np.ndarray] = []
    candidate_state_indices: List[int] = []
    candidate_action_indices: List[int] = []
    candidate_kinds: List[str] = []
    observed_actions: List[int] = []
    state_value_targets: List[float] = []
    failures: List[Dict[str, str]] = []
    battle_counts: Counter[str] = Counter()
    impact_methods: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    unmatched_audit: List[Dict[str, Any]] = []
    skip_audit: List[Dict[str, Any]] = []

    client = None
    started = time.perf_counter()
    tracemalloc.start()
    try:
        client = _damage_client()
        if client is None:
            raise RuntimeError(
                "Benchmark requires NEURAL_SIM_CORE_COMMAND_JSON/NEURAL_SIM_CORE_CWD; "
                "run through scripts/run_windows.ps1."
            )
        for ordinal, entry in enumerate(selected_entries, start=1):
            replay_id = str(entry["replay_id"])
            path = Path(str(entry["path"]))
            before_states = len(state_rows)
            try:
                trajectory = parse_protocol_log(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(),
                    replay_id=replay_id,
                    format_name="gen9randombattle",
                    source_path=str(path),
                )
                _validate_supported_replay_team_sizes(trajectory, replay_id=replay_id)
                original_completed_teams = _reconstructed_completed_private_teams(trajectory)
                completed_teams = _completed_teams_for_action_reconstruction(trajectory)
                turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
                for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
                    turn_number = int(turn_record.get("turn", 0) or 0)
                    events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
                    for event in events:
                        if not isinstance(event, dict) or event.get("type") not in ("move", "switch"):
                            continue
                        side = event.get("side")
                        if side not in ("p1", "p2"):
                            continue
                        if turn_number <= 0 and event.get("type") == "switch":
                            label_counts["skipped_initial_deployment_nondecision"] += 1
                            label_counts["legacy_unmatched"] += 1
                            label_counts["legacy_unmatched_reason:initial_deployment_nondecision"] += 1
                            unmatched_audit.append({
                                "replay_id": replay_id,
                                "turn": int(turn_number),
                                "side": side,
                                "raw_replay_command": event.get("raw"),
                                "parsed_command": chosen_action_label(event, turn_events=events),
                                "inferred_action_type": "team_preview_or_initial_deployment",
                                "legacy_candidates": [],
                                "pre_action_candidates": [],
                                "legacy_reason": "initial_deployment_nondecision",
                                "after_fix_matched": False,
                                "after_fix_reason": "skipped_nondecision",
                                "fix_classification": "intentionally_skipped_nondecision",
                            })
                            skip_audit.append({
                                "replay_id": replay_id,
                                "turn": int(turn_number),
                                "side": side,
                                "raw_replay_command": event.get("raw"),
                                "reason": "initial_deployment_nondecision",
                            })
                            continue
                        decision = _decision_features(
                            trajectory=trajectory,
                            side=side,
                            turn_number=turn_number,
                            event=event,
                            turn_events=events,
                            completed_teams=completed_teams,
                            original_completed_teams=original_completed_teams,
                            sets_path=sets_path,
                            damage_client=client,
                            action_feature_version=action_feature_version,
                        )
                        if not decision:
                            label_counts["skipped_no_action_label"] += 1
                            skip_audit.append({
                                "replay_id": replay_id,
                                "turn": int(turn_number),
                                "side": side,
                                "raw_replay_command": event.get("raw"),
                                "reason": "no_action_label",
                            })
                            continue
                        if decision["state_value_target"] is None:
                            label_counts["skipped_unknown_or_draw_outcome"] += 1
                            skip_audit.append({
                                "replay_id": replay_id,
                                "turn": int(turn_number),
                                "side": side,
                                "raw_replay_command": event.get("raw"),
                                "reason": "unknown_or_draw_outcome",
                            })
                            continue
                        state_index = len(state_rows)
                        state_rows.append(decision["state_features"])
                        state_replay_ids.append(replay_id)
                        state_splits.append(str(entry["split"]))
                        state_turns.append(decision["turn"])
                        state_sides.append(decision["side"])
                        state_value_targets.append(float(decision["state_value_target"]))
                        label_counts["state_value_labels"] += 1
                        label_counts["state_value_wins" if decision["state_value_target"] > 0 else "state_value_losses"] += 1
                        impact_methods.update(decision["impact_methods"])
                        chosen_kind = str(decision["chosen_label"]).split(":", 1)[0]
                        label_counts["legacy_matched" if decision["legacy_matched"] else "legacy_unmatched"] += 1
                        if not decision["legacy_matched"]:
                            label_counts[f"legacy_unmatched_reason:{decision['legacy_mismatch_reason']}"] += 1
                        if not decision["matched"]:
                            label_counts["chosen_action_unmatched"] += 1
                            label_counts[f"unmatched_kind:{chosen_kind}"] += 1
                            label_counts[f"unmatched_reason:{decision['mismatch_reason']}"] += 1
                            skip_audit.append({
                                "replay_id": replay_id,
                                "turn": int(decision["turn"]),
                                "side": decision["side"],
                                "raw_replay_command": decision["raw_command"],
                                "parsed_command": decision["chosen_label"],
                                "reason": "chosen_action_unmatched_for_action_rank",
                                "detail": decision["mismatch_reason"],
                                "candidates": decision["candidate_summaries"],
                            })
                        if not decision["legacy_matched"]:
                            unmatched_audit.append({
                                "replay_id": replay_id,
                                "turn": int(decision["turn"]),
                                "side": decision["side"],
                                "raw_replay_command": decision["raw_command"],
                                "parsed_command": decision["chosen_label"],
                                "inferred_action_type": chosen_kind,
                                "legacy_candidates": decision["legacy_candidate_summaries"],
                                "pre_action_candidates": decision["candidate_summaries"],
                                "legacy_reason": decision["legacy_mismatch_reason"],
                                "after_fix_matched": bool(decision["matched"]),
                                "after_fix_reason": decision["mismatch_reason"],
                                "fix_classification": (
                                    "fixed_by_exact_pre_action_event_prefix"
                                    if decision["matched"]
                                    else "intentionally_still_unmatched"
                                ),
                            })
                        if not decision["matched"]:
                            continue
                        label_counts["chosen_action_matched"] += 1
                        label_counts[f"matched_kind:{chosen_kind}"] += 1
                        for action, features, observed in zip(
                            decision["actions"],
                            decision["action_features"],
                            decision["observed"],
                        ):
                            action_rows.append(features)
                            candidate_state_indices.append(state_index)
                            candidate_action_indices.append(int(action.get("index", 0) or 0))
                            candidate_kinds.append(str(action.get("kind") or ""))
                            observed_actions.append(int(observed))
                            label_counts["action_rank_positive" if observed else "action_rank_unchosen"] += 1
                if len(state_rows) == before_states:
                    failures.append({"replay_id": replay_id, "reason": "no valid decision states"})
                else:
                    battle_counts["valid"] += 1
            except Exception as exc:
                failures.append({"replay_id": replay_id, "reason": f"{type(exc).__name__}: {exc}"})
            print_line_safe(
                f"benchmark-vnext-featuregen | battle={ordinal}/{len(selected_entries)} "
                f"states={len(state_rows)} candidates={len(action_rows)} failures={len(failures)}"
            )
    finally:
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if client is not None:
            client.close()

    arrays = {
        "state_features": np.asarray(state_rows, dtype=np.float16),
        "state_replay_ids": np.asarray(state_replay_ids),
        "state_splits": np.asarray(state_splits),
        "state_turns": np.asarray(state_turns, dtype=np.int16),
        "state_sides": np.asarray(state_sides),
        "state_value_targets": np.asarray(state_value_targets, dtype=np.float32),
        "action_features": np.asarray(action_rows, dtype=np.float16),
        "candidate_state_indices": np.asarray(candidate_state_indices, dtype=np.int32),
        "candidate_action_indices": np.asarray(candidate_action_indices, dtype=np.int16),
        "candidate_kinds": np.asarray(candidate_kinds),
        "observed_actions": np.asarray(observed_actions, dtype=np.int8),
        "action_rank_labels": np.asarray(observed_actions, dtype=np.int8),
        "state_feature_version": np.asarray(FEATURE_VERSION_V7),
        "state_feature_names": np.asarray(FEATURE_NAMES_V7),
        "action_feature_version": np.asarray(action_schema["version"]),
        "action_feature_names": np.asarray(action_schema["names"]),
        "manifest_catalog_checksum": np.asarray(str(manifest.get("catalog_checksum") or "")),
        "source_commit": np.asarray(str(metadata.get("source_commit") or "")),
    }
    if not state_rows or not action_rows:
        raise ValueError("Benchmark produced no feature rows.")
    validation = validate_benchmark_arrays(arrays, metadata)
    if not validation["passed"]:
        raise ValueError(f"Benchmark validation failed: {validation['checks']}")
    np.savez_compressed(dataset_path, **arrays)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    skip_audit_path = output_dir / "decision_skip_audit.jsonl"
    skip_audit_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in skip_audit),
        encoding="utf-8",
    )

    elapsed = time.perf_counter() - started
    dataset_bytes = dataset_path.stat().st_size
    output_bytes = sum(path.stat().st_size for path in output_dir.glob("*") if path.is_file())
    splits = Counter(state_splits)
    battle_splits = Counter(str(row.get("split") or "") for row in selected_entries)
    report = {
        **metadata,
        "command": command,
        "output_dir": str(output_dir),
        "files_produced": [
            str(subset_path),
            str(dataset_path),
            str(metadata_path),
            str(skip_audit_path),
            str(report_json_path),
            str(report_md_path),
        ],
        "battles_requested": battles,
        "battles_processed": len(selected_entries),
        "valid_battles": int(battle_counts["valid"]),
        "failed_battles": len(failures),
        "failures": failures,
        "decision_states": len(state_rows),
        "legal_action_candidates": len(action_rows),
        "average_legal_actions_per_state": len(action_rows) / max(1, len(state_rows)),
        "split_state_counts": dict(splits),
        "split_battle_counts": dict(battle_splits),
        "impact_method_counts": dict(impact_methods),
        "label_version": LABEL_VERSION,
        "state_value_label_count": int(label_counts["state_value_labels"]),
        "state_value_distribution": {
            "wins": int(label_counts["state_value_wins"]),
            "losses": int(label_counts["state_value_losses"]),
            "draws": 0,
        },
        "chosen_action_matched_count": int(label_counts["chosen_action_matched"]),
        "chosen_action_unmatched_count": int(label_counts["chosen_action_unmatched"]),
        "chosen_action_match_rate": float(
            label_counts["chosen_action_matched"] / max(
                1,
                label_counts["chosen_action_matched"] + label_counts["chosen_action_unmatched"],
            )
        ),
        "chosen_action_matched_by_kind": {
            key.split(":", 1)[1]: int(value)
            for key, value in sorted(label_counts.items())
            if key.startswith("matched_kind:")
        },
        "chosen_action_unmatched_by_kind": {
            key.split(":", 1)[1]: int(value)
            for key, value in sorted(label_counts.items())
            if key.startswith("unmatched_kind:")
        },
        "matcher_before": {
            "matched": int(label_counts["legacy_matched"]),
            "unmatched": int(label_counts["legacy_unmatched"]),
            "match_rate": float(label_counts["legacy_matched"] / max(1, label_counts["legacy_matched"] + label_counts["legacy_unmatched"])),
            "unmatched_reasons": {
                key.split(":", 1)[1]: int(value)
                for key, value in sorted(label_counts.items())
                if key.startswith("legacy_unmatched_reason:")
            },
        },
        "matcher_after": {
            "matched": int(label_counts["chosen_action_matched"]),
            "unmatched": int(label_counts["chosen_action_unmatched"]),
            "match_rate": float(label_counts["chosen_action_matched"] / max(1, label_counts["chosen_action_matched"] + label_counts["chosen_action_unmatched"])),
            "unmatched_reasons": {
                key.split(":", 1)[1]: int(value)
                for key, value in sorted(label_counts.items())
                if key.startswith("unmatched_reason:")
            },
        },
        "unmatched_action_audit": unmatched_audit,
        "decision_skip_audit_file": str(skip_audit_path),
        "action_rank_positive_count": int(label_counts["action_rank_positive"]),
        "action_rank_unchosen_count": int(label_counts["action_rank_unchosen"]),
        "skipped_state_count": int(
            label_counts["skipped_no_action_label"]
            + label_counts["skipped_unknown_or_draw_outcome"]
            + label_counts["chosen_action_unmatched"]
            + label_counts["skipped_initial_deployment_nondecision"]
        ),
        "skip_reasons": {
            "no_action_label": int(label_counts["skipped_no_action_label"]),
            "unknown_or_draw_outcome": int(label_counts["skipped_unknown_or_draw_outcome"]),
            "chosen_action_unmatched_for_action_rank": int(label_counts["chosen_action_unmatched"]),
            "initial_deployment_nondecision": int(label_counts["skipped_initial_deployment_nondecision"]),
        },
        "action_value_labels_generated": 0,
        "runtime_total_sec": elapsed,
        "runtime_per_battle_sec": elapsed / max(1, len(selected_entries)),
        "runtime_per_decision_state_sec": elapsed / max(1, len(state_rows)),
        "runtime_per_action_candidate_sec": elapsed / max(1, len(action_rows)),
        "dataset_size_bytes": dataset_bytes,
        "dataset_size_mb": dataset_bytes / (1024 * 1024),
        "total_output_size_bytes": output_bytes,
        "total_output_size_mb": output_bytes / (1024 * 1024),
        "dense_uncompressed_payload_bytes": int(arrays["state_features"].nbytes + arrays["action_features"].nbytes),
        "peak_python_tracemalloc_bytes": int(peak_memory),
        "peak_python_tracemalloc_mb": peak_memory / (1024 * 1024),
        "validation": validation,
        "warnings": [
            "Peak memory is Python tracemalloc heap only; it excludes sim-core and NumPy native allocations.",
            "Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.",
            "Action-rank groups with unmatched replay actions are excluded; inspect the reported match rate before training.",
        ] + (
            []
            if full_manifest
            else ["This is a 10-battle feasibility benchmark, not the full diagnostic_300 materialization."]
        ),
        "schema_bug_found": False,
        "ready_for_full_diagnostic_300": len(failures) == 0 and validation["passed"],
        "ready_for_first_diagnostic_training_command_design": (
            full_manifest
            and len(failures) == 0
            and validation["passed"]
            and (
                preflight is None
                or battle_splits == Counter(preflight.get("expected_split_counts") or {})
            )
        ),
    }
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report_md_path.write_text(
        _materialization_report_markdown(report) if full_manifest else _report_markdown(report),
        encoding="utf-8",
    )
    if full_manifest:
        report["total_output_size_bytes"] = sum(
            path.stat().st_size for path in output_dir.glob("*") if path.is_file()
        )
        report["total_output_size_mb"] = report["total_output_size_bytes"] / (1024 * 1024)
        report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report_md_path.write_text(_materialization_report_markdown(report), encoding="utf-8")
    if not full_manifest:
        label_report_path = output_dir.parent / "vnext_label_tiny_10_report.md"
        label_report_path.write_text(_label_report_markdown(report), encoding="utf-8")
        unmatched_audit_path = output_dir.parent / "vnext_unmatched_action_audit_tiny_10.md"
        unmatched_audit_path.write_text(_unmatched_audit_markdown(report), encoding="utf-8")
        matcher_report_path = output_dir.parent / "vnext_label_tiny_10_after_matcher_fixes_report.md"
        matcher_report_path.write_text(_matcher_report_markdown(report), encoding="utf-8")
    print_line_safe(
        f"benchmark-vnext-featuregen done | battles={len(selected_entries)} "
        f"states={len(state_rows)} candidates={len(action_rows)} runtime={elapsed:.2f}s "
        f"dataset_mb={report['dataset_size_mb']:.2f}"
    )
    return report


def _materialize_one_battle(
    entry: Dict[str, Any],
    *,
    sets_path: Optional[str],
    client: Any,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Dict[str, Any]:
    """Materialize one battle into local (per-battle) arrays and counters.

    Mirrors the sequential loop body but uses battle-local state indices; global
    candidate_state_indices are assigned during the combine step. Returns a
    self-contained, picklable result so each battle can be sharded to disk.
    """
    replay_id = str(entry["replay_id"])
    split = str(entry.get("split") or "")
    path = Path(str(entry["path"]))
    state_rows: List[np.ndarray] = []
    state_turns: List[int] = []
    state_sides: List[str] = []
    state_value_targets: List[float] = []
    action_rows: List[np.ndarray] = []
    candidate_local_state_indices: List[int] = []
    candidate_action_indices: List[int] = []
    candidate_kinds: List[str] = []
    observed_actions: List[int] = []
    label_counts: Counter = Counter()
    impact_methods: Counter = Counter()
    skip_audit: List[Dict[str, Any]] = []
    unmatched_audit: List[Dict[str, Any]] = []
    failure: Optional[Dict[str, str]] = None
    try:
        trajectory = parse_protocol_log(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            replay_id=replay_id,
            format_name="gen9randombattle",
            source_path=str(path),
        )
        _validate_supported_replay_team_sizes(trajectory, replay_id=replay_id)
        original_completed_teams = _reconstructed_completed_private_teams(trajectory)
        completed_teams = _completed_teams_for_action_reconstruction(trajectory)
        turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
        for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
            turn_number = int(turn_record.get("turn", 0) or 0)
            events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
            for event in events:
                if not isinstance(event, dict) or event.get("type") not in ("move", "switch"):
                    continue
                side = event.get("side")
                if side not in ("p1", "p2"):
                    continue
                if turn_number <= 0 and event.get("type") == "switch":
                    label_counts["skipped_initial_deployment_nondecision"] += 1
                    label_counts["legacy_unmatched"] += 1
                    label_counts["legacy_unmatched_reason:initial_deployment_nondecision"] += 1
                    unmatched_audit.append({
                        "replay_id": replay_id,
                        "turn": int(turn_number),
                        "side": side,
                        "raw_replay_command": event.get("raw"),
                        "parsed_command": chosen_action_label(event, turn_events=events),
                        "inferred_action_type": "team_preview_or_initial_deployment",
                        "legacy_candidates": [],
                        "pre_action_candidates": [],
                        "legacy_reason": "initial_deployment_nondecision",
                        "after_fix_matched": False,
                        "after_fix_reason": "skipped_nondecision",
                        "fix_classification": "intentionally_skipped_nondecision",
                    })
                    skip_audit.append({
                        "replay_id": replay_id,
                        "turn": int(turn_number),
                        "side": side,
                        "raw_replay_command": event.get("raw"),
                        "reason": "initial_deployment_nondecision",
                    })
                    continue
                decision = _decision_features(
                    trajectory=trajectory,
                    side=side,
                    turn_number=turn_number,
                    event=event,
                    turn_events=events,
                    completed_teams=completed_teams,
                    original_completed_teams=original_completed_teams,
                    sets_path=sets_path,
                    damage_client=client,
                    action_feature_version=action_feature_version,
                )
                if not decision:
                    label_counts["skipped_no_action_label"] += 1
                    skip_audit.append({
                        "replay_id": replay_id,
                        "turn": int(turn_number),
                        "side": side,
                        "raw_replay_command": event.get("raw"),
                        "reason": "no_action_label",
                    })
                    continue
                if decision["state_value_target"] is None:
                    label_counts["skipped_unknown_or_draw_outcome"] += 1
                    skip_audit.append({
                        "replay_id": replay_id,
                        "turn": int(turn_number),
                        "side": side,
                        "raw_replay_command": event.get("raw"),
                        "reason": "unknown_or_draw_outcome",
                    })
                    continue
                state_index = len(state_rows)
                state_rows.append(decision["state_features"])
                state_turns.append(decision["turn"])
                state_sides.append(decision["side"])
                state_value_targets.append(float(decision["state_value_target"]))
                label_counts["state_value_labels"] += 1
                label_counts["state_value_wins" if decision["state_value_target"] > 0 else "state_value_losses"] += 1
                impact_methods.update(decision["impact_methods"])
                chosen_kind = str(decision["chosen_label"]).split(":", 1)[0]
                label_counts["legacy_matched" if decision["legacy_matched"] else "legacy_unmatched"] += 1
                if not decision["legacy_matched"]:
                    label_counts[f"legacy_unmatched_reason:{decision['legacy_mismatch_reason']}"] += 1
                if not decision["matched"]:
                    label_counts["chosen_action_unmatched"] += 1
                    label_counts[f"unmatched_kind:{chosen_kind}"] += 1
                    label_counts[f"unmatched_reason:{decision['mismatch_reason']}"] += 1
                    skip_audit.append({
                        "replay_id": replay_id,
                        "turn": int(decision["turn"]),
                        "side": decision["side"],
                        "raw_replay_command": decision["raw_command"],
                        "parsed_command": decision["chosen_label"],
                        "reason": "chosen_action_unmatched_for_action_rank",
                        "detail": decision["mismatch_reason"],
                        "candidates": decision["candidate_summaries"],
                    })
                if not decision["legacy_matched"]:
                    unmatched_audit.append({
                        "replay_id": replay_id,
                        "turn": int(decision["turn"]),
                        "side": decision["side"],
                        "raw_replay_command": decision["raw_command"],
                        "parsed_command": decision["chosen_label"],
                        "inferred_action_type": chosen_kind,
                        "legacy_candidates": decision["legacy_candidate_summaries"],
                        "pre_action_candidates": decision["candidate_summaries"],
                        "legacy_reason": decision["legacy_mismatch_reason"],
                        "after_fix_matched": bool(decision["matched"]),
                        "after_fix_reason": decision["mismatch_reason"],
                        "fix_classification": (
                            "fixed_by_exact_pre_action_event_prefix"
                            if decision["matched"]
                            else "intentionally_still_unmatched"
                        ),
                    })
                if not decision["matched"]:
                    continue
                label_counts["chosen_action_matched"] += 1
                label_counts[f"matched_kind:{chosen_kind}"] += 1
                for action, features, observed in zip(
                    decision["actions"], decision["action_features"], decision["observed"]
                ):
                    action_rows.append(features)
                    candidate_local_state_indices.append(state_index)
                    candidate_action_indices.append(int(action.get("index", 0) or 0))
                    candidate_kinds.append(str(action.get("kind") or ""))
                    observed_actions.append(int(observed))
                    label_counts["action_rank_positive" if observed else "action_rank_unchosen"] += 1
        if len(state_rows) == 0 and failure is None:
            failure = {"replay_id": replay_id, "reason": "no valid decision states"}
    except Exception as exc:  # noqa: BLE001 - per-battle isolation
        failure = {"replay_id": replay_id, "reason": f"{type(exc).__name__}: {exc}"}
    return {
        "replay_id": replay_id,
        "split": split,
        "state_rows": (
            np.asarray(state_rows, dtype=np.float16)
            if state_rows
            else np.zeros((0, FEATURE_DIM_V7), dtype=np.float16)
        ),
        "state_turns": state_turns,
        "state_sides": state_sides,
        "state_value_targets": state_value_targets,
        "action_rows": (
            np.asarray(action_rows, dtype=np.float16)
            if action_rows
            else np.zeros((0, int(action_feature_schema(action_feature_version)["dim"])), dtype=np.float16)
        ),
        "candidate_local_state_indices": candidate_local_state_indices,
        "candidate_action_indices": candidate_action_indices,
        "candidate_kinds": candidate_kinds,
        "observed_actions": observed_actions,
        "label_counts": dict(label_counts),
        "impact_methods": dict(impact_methods),
        "skip_audit": skip_audit,
        "unmatched_audit": unmatched_audit,
        "failure": failure,
        "valid": len(state_rows) > 0,
    }


_WORKER_CLIENT: Any = None
_WORKER_SETS_PATH: Optional[str] = None
_WORKER_ACTION_FEATURE_VERSION = ACTION_FEATURE_VERSION_V5


def _worker_init(
    sets_path: Optional[str],
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> None:
    """Per-worker sim-core client; one node process per pool worker."""
    global _WORKER_ACTION_FEATURE_VERSION, _WORKER_CLIENT, _WORKER_SETS_PATH
    import atexit

    _WORKER_SETS_PATH = sets_path
    _WORKER_ACTION_FEATURE_VERSION = action_feature_version
    _WORKER_CLIENT = _damage_client()
    if _WORKER_CLIENT is None:
        raise RuntimeError(
            "Materialization worker requires NEURAL_SIM_CORE_COMMAND_JSON/NEURAL_SIM_CORE_CWD; "
            "run through scripts/run_windows.ps1."
        )
    atexit.register(lambda: _WORKER_CLIENT.close() if _WORKER_CLIENT is not None else None)


def _materialize_battle_worker(entry: Dict[str, Any]) -> Dict[str, Any]:
    return _materialize_one_battle(
        entry,
        sets_path=_WORKER_SETS_PATH,
        client=_WORKER_CLIENT,
        action_feature_version=_WORKER_ACTION_FEATURE_VERSION,
    )


def _shard_path(shards_dir: Path, replay_id: str) -> Path:
    return shards_dir / (hashlib.sha1(replay_id.encode("utf-8")).hexdigest() + ".pkl")


def run_full_materialization(
    *,
    manifest_path: Path,
    output_dir: Path,
    seed: int = DEFAULT_SEED,
    sets_path: Optional[str] = None,
    workers: int = DEFAULT_WORKERS,
    resume: bool = True,
    action_feature_version: str = ACTION_FEATURE_VERSION_V5,
) -> Dict[str, Any]:
    """Parallel, crash-safe, resumable full-manifest materialization.

    Each battle is processed in a worker process with its own sim-core client and
    written to a per-battle shard immediately, so an interruption never discards
    completed work. The final dataset is assembled from shards and validated with
    the same checks as the sequential path.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    action_schema = action_feature_schema(action_feature_version)
    is_legacy_300 = output_dir.resolve() == DEFAULT_FULL_OUTPUT_DIR.resolve()
    dataset_name = output_dir.name
    command = (
        "python -m neural.benchmark_vnext_featuregen --full-manifest "
        f"--manifest {manifest_path} --output-dir {output_dir} --workers {workers} "
        f"--action-feature-version {action_feature_version}"
    )
    preflight = _validate_full_preflight(
        manifest=manifest,
        manifest_path=manifest_path,
        output_dir=output_dir,
        action_feature_version=action_feature_version,
    )
    selected_entries = list(manifest.get("entries") or [])
    metadata = benchmark_metadata(
        manifest=manifest,
        selected_entries=selected_entries,
        seed=seed,
        manifest_path=manifest_path,
        command=command,
        artifact_kind="diagnostic_300_materialization" if is_legacy_300 else "diagnostic_full_materialization",
        preflight=preflight,
        action_feature_version=action_feature_version,
    )
    metadata["dataset_name"] = dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    shards_dir = output_dir / "_shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    subset_path = output_dir / "source_manifest_snapshot.json"
    subset_path.write_text(
        json.dumps({"metadata": metadata, "entries": selected_entries}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    pending = [
        entry
        for entry in selected_entries
        if not (resume and _shard_path(shards_dir, str(entry["replay_id"])).is_file())
    ]
    done = len(selected_entries) - len(pending)
    total = len(selected_entries)
    print_line_safe(
        f"materialize-full start | dataset={dataset_name} battles={total} "
        f"already_sharded={done} pending={len(pending)} workers={workers}"
    )
    started = time.perf_counter()
    if pending:
        with ProcessPoolExecutor(
            max_workers=max(1, int(workers)),
            initializer=_worker_init,
            initargs=(sets_path, action_feature_version),
        ) as executor:
            futures = {executor.submit(_materialize_battle_worker, entry): entry for entry in pending}
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                with open(_shard_path(shards_dir, result["replay_id"]), "wb") as handle:
                    pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
                completed += 1
                done += 1
                elapsed = time.perf_counter() - started
                eta_min = (elapsed / completed) * (len(pending) - completed) / 60.0
                print_line_safe(
                    f"materialize-full | done={done}/{total} this_run={completed}/{len(pending)} "
                    f"battle_states={result['state_rows'].shape[0]} valid={result['valid']} "
                    f"failed={result['failure'] is not None} eta={eta_min:.1f}min"
                )

    # Combine shards in manifest order.
    state_arrays: List[np.ndarray] = []
    action_arrays: List[np.ndarray] = []
    state_replay_ids: List[str] = []
    state_splits: List[str] = []
    state_turns: List[int] = []
    state_sides: List[str] = []
    state_value_targets: List[float] = []
    candidate_state_indices: List[int] = []
    candidate_action_indices: List[int] = []
    candidate_kinds: List[str] = []
    observed_actions: List[int] = []
    label_counts: Counter = Counter()
    impact_methods: Counter = Counter()
    failures: List[Dict[str, str]] = []
    unmatched_audit: List[Dict[str, Any]] = []
    skip_audit: List[Dict[str, Any]] = []
    valid_battles = 0
    total_states = 0
    for entry in selected_entries:
        replay_id = str(entry["replay_id"])
        shard = _shard_path(shards_dir, replay_id)
        if not shard.is_file():
            raise ValueError(f"Missing shard for battle {replay_id}; re-run to resume materialization.")
        with open(shard, "rb") as handle:
            result = pickle.load(handle)
        n = int(result["state_rows"].shape[0])
        if n:
            state_arrays.append(result["state_rows"])
            state_replay_ids.extend([replay_id] * n)
            state_splits.extend([result["split"]] * n)
            state_turns.extend(result["state_turns"])
            state_sides.extend(result["state_sides"])
            state_value_targets.extend(result["state_value_targets"])
        if result["action_rows"].shape[0]:
            action_arrays.append(result["action_rows"])
            candidate_state_indices.extend(total_states + li for li in result["candidate_local_state_indices"])
            candidate_action_indices.extend(result["candidate_action_indices"])
            candidate_kinds.extend(result["candidate_kinds"])
            observed_actions.extend(result["observed_actions"])
        total_states += n
        label_counts.update(result["label_counts"])
        impact_methods.update(result["impact_methods"])
        skip_audit.extend(result["skip_audit"])
        unmatched_audit.extend(result["unmatched_audit"])
        if result["failure"]:
            failures.append(result["failure"])
        if result["valid"]:
            valid_battles += 1

    arrays = {
        "state_features": (
            np.concatenate(state_arrays) if state_arrays else np.zeros((0, FEATURE_DIM_V7), dtype=np.float16)
        ),
        "state_replay_ids": np.asarray(state_replay_ids),
        "state_splits": np.asarray(state_splits),
        "state_turns": np.asarray(state_turns, dtype=np.int16),
        "state_sides": np.asarray(state_sides),
        "state_value_targets": np.asarray(state_value_targets, dtype=np.float32),
        "action_features": (
            np.concatenate(action_arrays)
            if action_arrays
            else np.zeros((0, int(action_schema["dim"])), dtype=np.float16)
        ),
        "candidate_state_indices": np.asarray(candidate_state_indices, dtype=np.int32),
        "candidate_action_indices": np.asarray(candidate_action_indices, dtype=np.int16),
        "candidate_kinds": np.asarray(candidate_kinds),
        "observed_actions": np.asarray(observed_actions, dtype=np.int8),
        "action_rank_labels": np.asarray(observed_actions, dtype=np.int8),
        "state_feature_version": np.asarray(FEATURE_VERSION_V7),
        "state_feature_names": np.asarray(FEATURE_NAMES_V7),
        "action_feature_version": np.asarray(action_schema["version"]),
        "action_feature_names": np.asarray(action_schema["names"]),
        "manifest_catalog_checksum": np.asarray(str(manifest.get("catalog_checksum") or "")),
        "source_commit": np.asarray(str(metadata.get("source_commit") or "")),
    }
    if arrays["state_features"].shape[0] == 0 or arrays["action_features"].shape[0] == 0:
        raise ValueError("Full materialization produced no feature rows.")
    validation = validate_benchmark_arrays(arrays, metadata)

    elapsed = time.perf_counter() - started
    dataset_path = output_dir / f"{dataset_name}.npz"
    metadata_path = output_dir / "feature_metadata.json"
    report_json_path = output_dir / "materialization_report.json"
    report_md_path = output_dir / (dataset_name.replace("_v7_v5", "") + "_materialization_report.md")
    skip_audit_path = output_dir / "decision_skip_audit.jsonl"

    battle_splits = Counter(str(row.get("split") or "") for row in selected_entries)
    split_state_counts = Counter(state_splits)
    expected_split_counts = Counter(preflight.get("expected_split_counts") or {})
    report = {
        **metadata,
        "command": command,
        "workers": int(workers),
        "output_dir": str(output_dir),
        "shards_dir": str(shards_dir),
        "files_produced": [
            str(subset_path),
            str(dataset_path),
            str(metadata_path),
            str(skip_audit_path),
            str(report_json_path),
            str(report_md_path),
        ],
        "battles_requested": total,
        "battles_processed": total,
        "valid_battles": valid_battles,
        "failed_battles": len(failures),
        "failures": failures,
        "decision_states": int(arrays["state_features"].shape[0]),
        "legal_action_candidates": int(arrays["action_features"].shape[0]),
        "average_legal_actions_per_state": arrays["action_features"].shape[0] / max(1, arrays["state_features"].shape[0]),
        "split_state_counts": dict(split_state_counts),
        "split_battle_counts": dict(battle_splits),
        "impact_method_counts": dict(impact_methods),
        "label_version": LABEL_VERSION,
        "state_value_label_count": int(label_counts["state_value_labels"]),
        "state_value_distribution": {
            "wins": int(label_counts["state_value_wins"]),
            "losses": int(label_counts["state_value_losses"]),
            "draws": 0,
        },
        "chosen_action_matched_count": int(label_counts["chosen_action_matched"]),
        "chosen_action_unmatched_count": int(label_counts["chosen_action_unmatched"]),
        "chosen_action_match_rate": float(
            label_counts["chosen_action_matched"]
            / max(1, label_counts["chosen_action_matched"] + label_counts["chosen_action_unmatched"])
        ),
        "chosen_action_matched_by_kind": {
            key.split(":", 1)[1]: int(value)
            for key, value in sorted(label_counts.items())
            if key.startswith("matched_kind:")
        },
        "chosen_action_unmatched_by_kind": {
            key.split(":", 1)[1]: int(value)
            for key, value in sorted(label_counts.items())
            if key.startswith("unmatched_kind:")
        },
        "unmatched_action_audit": unmatched_audit,
        "decision_skip_audit_file": str(skip_audit_path),
        "action_rank_positive_count": int(label_counts["action_rank_positive"]),
        "action_rank_unchosen_count": int(label_counts["action_rank_unchosen"]),
        "skip_reasons": {
            "no_action_label": int(label_counts["skipped_no_action_label"]),
            "unknown_or_draw_outcome": int(label_counts["skipped_unknown_or_draw_outcome"]),
            "chosen_action_unmatched_for_action_rank": int(label_counts["chosen_action_unmatched"]),
            "initial_deployment_nondecision": int(label_counts["skipped_initial_deployment_nondecision"]),
        },
        "action_value_labels_generated": 0,
        "runtime_total_sec": elapsed,
        "dataset_size_bytes": 0,
        "dataset_size_mb": 0.0,
        "total_output_size_bytes": 0,
        "total_output_size_mb": 0.0,
        "validation": validation,
        "warnings": [
            "Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.",
            "Action-rank groups with unmatched replay actions are excluded; inspect the reported match rate before training.",
            "Per-battle shards persist under _shards/ for crash recovery and resume.",
        ],
        "schema_bug_found": False,
        "ready_for_first_diagnostic_training_command_design": (
            len(failures) == 0
            and validation["passed"]
            and (not expected_split_counts or battle_splits == expected_split_counts)
        ),
    }
    if not validation["passed"]:
        report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise ValueError(
            f"Full materialization validation failed: {validation['checks']}; "
            f"failures={failures[:5]}. Shards retained at {shards_dir} for inspection/resume."
        )
    np.savez_compressed(dataset_path, **arrays)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    skip_audit_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in skip_audit),
        encoding="utf-8",
    )
    dataset_bytes = dataset_path.stat().st_size
    output_bytes = sum(p.stat().st_size for p in output_dir.glob("*") if p.is_file())
    report["dataset_size_bytes"] = dataset_bytes
    report["dataset_size_mb"] = dataset_bytes / (1024 * 1024)
    report["total_output_size_bytes"] = output_bytes
    report["total_output_size_mb"] = output_bytes / (1024 * 1024)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_materialization_report_markdown(report), encoding="utf-8")
    print_line_safe(
        f"materialize-full done | battles={total} states={report['decision_states']} "
        f"candidates={report['legal_action_candidates']} runtime={elapsed:.1f}s "
        f"dataset_mb={report['dataset_size_mb']:.2f} validation_passed={validation['passed']}"
    )
    return report


def _materialization_report_markdown(report: Dict[str, Any]) -> str:
    checks = report["validation"]["checks"]
    dataset_name = report.get("dataset_name") or "diagnostic_300_v7_v5"
    lines = [
        f"# {dataset_name} Materialization Report",
        "",
        f"- Command: `{report['command']}`",
        f"- Runtime: {report['runtime_total_sec']:.2f}s",
        f"- Storage size: {report['total_output_size_mb']:.2f} MiB total; "
        f"{report['dataset_size_mb']:.2f} MiB dataset",
        f"- Battles processed: {report['battles_processed']} "
        f"({report['valid_battles']} valid / {report['failed_battles']} failed)",
        f"- State count: {report['decision_states']:,}",
        f"- Action candidate count: {report['legal_action_candidates']:,}",
        f"- Average candidates/state: {report['average_legal_actions_per_state']:.2f}",
        f"- State-label distribution: {report['state_value_distribution']}",
        f"- Action-rank positives: {report['action_rank_positive_count']:,}",
        f"- Unchosen candidates: {report['action_rank_unchosen_count']:,}",
        f"- Matched / unmatched decisions: {report['chosen_action_matched_count']:,} / "
        f"{report['chosen_action_unmatched_count']:,}",
        f"- Skip reasons: {report['skip_reasons']}",
        f"- Battle split counts: {report['split_battle_counts']}",
        f"- State split counts: {report['split_state_counts']}",
        f"- Dtype/layout: {report['dtype_on_disk']}; {report['storage_layout']}",
        f"- Duplicated state vectors: {report['state_vectors_duplicated_per_candidate']}",
        f"- State schema: `{report['state_feature_version']}`, {report['state_feature_dim']}D",
        f"- Action schema: `{report['action_feature_version']}`, {report['action_feature_dim']}D",
        f"- Action-value labels: {report['action_value_labels_generated']}",
        "",
        "## Files Produced",
        "",
    ]
    lines.extend(f"- `{path}`" for path in report["files_produced"])
    lines.extend(["", "## Validation", ""])
    lines.extend(f"- [{'x' if passed else ' '}] `{name}`" for name, passed in checks.items())
    lines.extend(["", "## Warnings and Limitations", ""])
    lines.extend(f"- {warning}" for warning in report["warnings"])
    lines.extend([
        "",
        "- Ready for first diagnostic training command design: "
        f"**{'yes' if report['ready_for_first_diagnostic_training_command_design'] else 'no'}**",
        "- Training gate: **closed** pending written plan/config/command, sanity-check review, "
        "and explicit user approval.",
        "",
    ])
    return "\n".join(lines)


def _report_markdown(report: Dict[str, Any]) -> str:
    checks = report["validation"]["checks"]
    lines = [
        "# vNext Feature Generation Tiny-10 Benchmark",
        "",
        f"- Command: `{report['command']}`",
        f"- Battles: {report['valid_battles']} valid / {report['failed_battles']} failed",
        f"- Decision states: {report['decision_states']:,}",
        f"- Legal action candidates: {report['legal_action_candidates']:,}",
        f"- Average legal actions/state: {report['average_legal_actions_per_state']:.2f}",
        f"- Runtime: {report['runtime_total_sec']:.2f}s total; "
        f"{report['runtime_per_battle_sec']:.2f}s/battle; "
        f"{report['runtime_per_decision_state_sec'] * 1000:.2f}ms/state; "
        f"{report['runtime_per_action_candidate_sec'] * 1000:.2f}ms/candidate",
        f"- Dataset size: {report['dataset_size_mb']:.2f} MiB compressed",
        f"- Dense state/action payload: {report['dense_uncompressed_payload_bytes'] / (1024 * 1024):.2f} MiB",
        f"- Peak Python tracemalloc heap: {report['peak_python_tracemalloc_mb']:.2f} MiB",
        f"- State: `{report['state_feature_version']}`, {report['state_feature_dim']}D",
        f"- Action: `{report['action_feature_version']}`, {report['action_feature_dim']}D",
        f"- Dtype/layout: {report['dtype_on_disk']}; {report['storage_layout']}",
        f"- State duplicated per candidate: {report['state_vectors_duplicated_per_candidate']}",
        f"- Split state counts: {report['split_state_counts']}",
        f"- Impact methods: {report['impact_method_counts']}",
        "",
        "## Validation",
        "",
    ]
    for name, passed in checks.items():
        lines.append(f"- [{'x' if passed else ' '}] `{name}`")
    lines.extend([
        "",
        "## Files Produced",
        "",
    ])
    for path in report["files_produced"]:
        lines.append(f"- `{path}`")
    lines.extend([
        "",
        "## Warnings and Decision",
        "",
    ])
    lines.extend(f"- {warning}" for warning in report["warnings"])
    lines.extend([
        "",
        f"- Schema bug found: **{'yes' if report['schema_bug_found'] else 'no'}**",
        f"- Ready for full `diagnostic_300` feature materialization: "
        f"**{'yes' if report['ready_for_full_diagnostic_300'] else 'no'}**",
        "- Training gate: **closed**; labels, full materialization, training command, "
        "and materialized-feature sanity checks remain outstanding.",
        "",
    ])
    return "\n".join(lines)


def _label_report_markdown(report: Dict[str, Any]) -> str:
    return "\n".join([
        "# vNext Label Tiny-10 Dry Run",
        "",
        f"- Label version: `{report['label_version']}`",
        f"- Battles: {report['valid_battles']} valid / {report['failed_battles']} failed",
        f"- State-value labels: {report['state_value_label_count']}",
        f"- State-value distribution: {report['state_value_distribution']}",
        f"- Legal candidates retained for action rank: {report['legal_action_candidates']}",
        f"- Chosen actions matched: {report['chosen_action_matched_count']}",
        f"- Chosen actions unmatched: {report['chosen_action_unmatched_count']}",
        f"- Chosen action match rate: {report['chosen_action_match_rate']:.1%}",
        f"- Matched by kind: {report['chosen_action_matched_by_kind']}",
        f"- Unmatched by kind: {report['chosen_action_unmatched_by_kind']}",
        f"- Action-rank positives / unchosen: "
        f"{report['action_rank_positive_count']} / {report['action_rank_unchosen_count']}",
        f"- Skipped states: {report['skipped_state_count']}",
        f"- Skip reasons: {report['skip_reasons']}",
        f"- Split state counts: {report['split_state_counts']}",
        "",
        "State value is terminal outcome from the state owner's perspective "
        "(win +1, loss -1; ties/unknown excluded). Action rank is replay "
        "imitation with exactly one matched positive and unchosen candidates "
        "treated as unchosen rather than bad. Action-value labels are not generated.",
        "",
        f"- Ready for full `diagnostic_300` label extraction: "
        f"**{'yes' if report['failed_battles'] == 0 else 'no'}**",
        "- Training gate: **closed**.",
        "",
    ])


def _unmatched_audit_markdown(report: Dict[str, Any]) -> str:
    before = report["matcher_before"]
    after = report["matcher_after"]
    lines = [
        "# vNext Unmatched Action Audit — Tiny 10",
        "",
        f"- Before: {before['matched']} matched / {before['unmatched']} unmatched ({before['match_rate']:.1%})",
        f"- After safe fixes: {after['matched']} matched / {after['unmatched']} unmatched ({after['match_rate']:.1%})",
        f"- Initial-deployment non-decisions skipped: {report['skip_reasons'].get('initial_deployment_nondecision', 0)}",
        f"- Legacy root causes: {before['unmatched_reasons']}",
        f"- Remaining root causes: {after['unmatched_reasons']}",
        "",
        "No closest-candidate heuristic, guessed switch identity, or injected positive was used.",
        "",
        "## Original Unmatched Groups",
        "",
    ]
    for row in report["unmatched_action_audit"]:
        lines.extend([
            f"### `{row['replay_id']}` turn {row['turn']} {row['side']}",
            "",
            f"- Raw: `{row['raw_replay_command']}`",
            f"- Parsed: `{row['parsed_command']}`",
            f"- Type: `{row['inferred_action_type']}`",
            f"- Legacy reason: `{row['legacy_reason']}`",
            f"- Result: `{row['fix_classification']}`",
            f"- Remaining reason: `{row['after_fix_reason']}`",
            f"- Legacy candidates: `{row['legacy_candidates']}`",
            f"- Pre-action candidates: `{row['pre_action_candidates']}`",
            "",
        ])
    return "\n".join(lines)


def _matcher_report_markdown(report: Dict[str, Any]) -> str:
    before = report["matcher_before"]
    after = report["matcher_after"]
    return "\n".join([
        "# vNext Label Tiny-10 After Matcher Fixes",
        "",
        f"- Matched before / after: {before['matched']} / {after['matched']}",
        f"- Unmatched before / after: {before['unmatched']} / {after['unmatched']}",
        f"- Match rate before / after: {before['match_rate']:.1%} / {after['match_rate']:.1%}",
        f"- Unmatched reasons before: {before['unmatched_reasons']}",
        f"- Unmatched reasons after: {after['unmatched_reasons']}",
        f"- Skipped non-decision states: {report['skip_reasons'].get('initial_deployment_nondecision', 0)}",
        f"- Intentionally still unmatched: {after['unmatched']}",
        "- Labels injected or guessed: **0**",
        "",
        "Safe fixes: skip turn-0 initial deployments; assign public move reveals to "
        "the chronologically active species rather than actor aliases; stop the "
        "pre-action prefix before the current decision's Tera commitment; and build "
        "candidates from the exact event prefix. Remaining groups stay excluded.",
        "",
    ])


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark explicit v7 action-schema feature generation.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--battles", type=int, default=DEFAULT_BATTLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--sets-path", default=None)
    parser.add_argument("--full-manifest", action="store_true")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument(
        "--action-feature-version",
        choices=(ACTION_FEATURE_VERSION_V5, ACTION_FEATURE_VERSION_V6, ACTION_FEATURE_VERSION_V7),
        default=ACTION_FEATURE_VERSION_V5,
    )
    args = parser.parse_args(argv)
    if args.full_manifest:
        run_full_materialization(
            manifest_path=Path(args.manifest),
            output_dir=Path(args.output_dir),
            seed=args.seed,
            sets_path=args.sets_path,
            workers=args.workers,
            resume=not args.no_resume,
            action_feature_version=args.action_feature_version,
        )
    else:
        run_benchmark(
            manifest_path=Path(args.manifest),
            output_dir=Path(args.output_dir),
            battles=args.battles,
            seed=args.seed,
            sets_path=args.sets_path,
            full_manifest=False,
            action_feature_version=args.action_feature_version,
        )


if __name__ == "__main__":
    main()
