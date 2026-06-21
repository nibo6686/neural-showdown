import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_NAMES, ACTION_FEATURE_VERSION, build_action_feature_vector
from .build_live_private_value_dataset import (
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
)
from .build_replay_value_dataset import DEFAULT_FORMAT, _ensure_trajectories, _load_trajectories
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import FEATURE_DIM, FEATURE_NAMES, FEATURE_VERSION, build_live_private_feature_vector, public_feature_vector_from_trajectory
from .logging_helper import format_summary, print_line_safe
from .tactical_state import (
    TACTICAL_ACTION_FEATURE_NAMES,
    build_tactical_state,
    tactical_report_from_state,
)


DEFAULT_OUTPUT_PATH = Path("data/policy/gen9randombattle_action_rank_v2.npz")
DEFAULT_REPORT_JSON = Path("artifacts/analysis/action_rank_dataset_report.json")
DEFAULT_REPORT_MD = Path("artifacts/analysis/action_rank_dataset_report.md")
DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_TRAJECTORIES = Path("data/replays/processed/gen9randombattle_trajectories.jsonl.gz")


def _species_from_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    if ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(",", 1)[0].strip() or None


def _normalize_label(label: str) -> str:
    return " ".join(label.replace(":", ": ").split()).lower()


def _action_label_from_event(event: Dict[str, Any]) -> Optional[str]:
    if event.get("type") == "move" and event.get("move"):
        return f"move: {event.get('move')}"
    if event.get("type") == "switch":
        species = _species_from_text(event.get("details") or event.get("actor"))
        return f"switch: {species}" if species else None
    return None


def _legal_actions_from_private_state(private_state: Dict[str, Any], chosen_label: str) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    seen = set()
    active_moves = private_state.get("active_moves") if isinstance(private_state.get("active_moves"), list) else []
    can_tera = bool(private_state.get("can_tera") and not private_state.get("tera_used") and not private_state.get("force_switch"))
    tera_type = private_state.get("active_tera_type")
    for index, move in enumerate(active_moves[:4]):
        if not isinstance(move, dict):
            continue
        name = str(move.get("name") or move.get("move") or move.get("id") or f"move {index + 1}")
        label = f"move: {name}"
        key = ("move", _normalize_label(label))
        if key in seen:
            continue
        seen.add(key)
        disabled = bool(move.get("disabled", False))
        slot = int(move.get("slot", index + 1) or index + 1)
        actions.append({"index": index, "kind": "move", "label": label, "choice": f"move {slot}", "move": name, "slot": slot, "disabled": disabled})
        if can_tera and not disabled and 1 <= slot <= 4:
            tera_label = f"move_tera: {name}"
            tera_key = ("move_tera", _normalize_label(tera_label))
            if tera_key not in seen:
                seen.add(tera_key)
                actions.append(
                    {
                        "index": slot - 1 + 4,
                        "kind": "move_tera",
                        "label": tera_label,
                        "choice": f"move {slot} terastallize",
                        "move": name,
                        "slot": slot,
                        "disabled": False,
                        "is_tera_action": True,
                        "can_tera": True,
                        "tera_type": tera_type,
                    }
                )

    if private_state.get("struggle_available") and not private_state.get("force_switch"):
        label = "move: Struggle"
        key = ("move", _normalize_label(label))
        if key not in seen:
            seen.add(key)
            actions.append(
                {
                    "index": len(actions),
                    "kind": "move",
                    "label": label,
                    "choice": "move 1",
                    "move": "Struggle",
                    "slot": 1,
                    "disabled": False,
                }
            )

    chosen_kind = chosen_label.split(":", 1)[0].strip().lower()
    if chosen_kind in {"move", "move_tera"} and (chosen_kind, _normalize_label(chosen_label)) not in seen:
        actions.append({"index": min(7 if chosen_kind == "move_tera" else 3, len(actions)), "kind": chosen_kind, "label": chosen_label, "disabled": False})
        seen.add((chosen_kind, _normalize_label(chosen_label)))

    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    switch_index = 8
    for mon in team:
        if not isinstance(mon, dict):
            continue
        if mon.get("active") or mon.get("fainted"):
            continue
        species = str(mon.get("species") or "").strip()
        if not species:
            continue
        label = f"switch: {species}"
        key = ("switch", _normalize_label(label))
        if key in seen:
            continue
        seen.add(key)
        actions.append({"index": switch_index, "kind": "switch", "label": label, "disabled": False})
        switch_index += 1

    if chosen_kind == "switch" and ("switch", _normalize_label(chosen_label)) not in seen:
        actions.append({"index": switch_index, "kind": "switch", "label": chosen_label, "disabled": False})
    return actions[:13]


def _chosen_index(actions: Sequence[Dict[str, Any]], chosen_label: str) -> Optional[int]:
    target = _normalize_label(chosen_label)
    for ordinal, action in enumerate(actions):
        if _normalize_label(str(action.get("label") or "")) == target:
            return ordinal
    return None


def _decision_rows(
    *,
    trajectory: Dict[str, Any],
    side: str,
    turn_number: int,
    event: Dict[str, Any],
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    decision_id: int,
    sets_path: Optional[str],
) -> Optional[Dict[str, Any]]:
    chosen_label = _action_label_from_event(event)
    if not chosen_label:
        return None
    context_turn = max(0, int(turn_number) - 1)
    prefix = _trajectory_prefix_for_training(trajectory, context_turn)
    public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
    private_state = _reconstructed_private_state_for_side(
        trajectory,
        side=side,
        through_turn=context_turn,
        completed_teams=completed_teams,
    )
    opponent_belief = build_opponent_beliefs(
        protocol_log=prefix.get("protocol_log", []),
        trajectory=prefix,
        player_side=side,
        sets_path=sets_path,
    )
    private_state["opponent_belief"] = opponent_belief
    tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
    private_state["tactical_state"] = tactical_state
    state_features, _ = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=side,
        tactical_state=tactical_state,
    )
    actions = _legal_actions_from_private_state(private_state, chosen_label)
    chosen_ordinal = _chosen_index(actions, chosen_label)
    if chosen_ordinal is None or not actions:
        return None
    action_features = [build_action_feature_vector(action, private_state, tactical_state=tactical_state) for action in actions]
    return {
        "decision_id": decision_id,
        "state_features": state_features,
        "actions": actions,
        "action_features": action_features,
        "labels": [1 if index == chosen_ordinal else 0 for index in range(len(actions))],
        "chosen_label": chosen_label,
        "turn": int(turn_number),
        "side": side,
        "replay_id": str(trajectory.get("replay_id") or ""),
        "inferred_own_info": bool(private_state.get("inferred_from_randbats")),
        "tactical": tactical_report_from_state(tactical_state),
    }


def build_action_rank_dataset(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
    sets_path: Optional[str] = None,
    max_decisions: Optional[int] = None,
    include_debug_fields: bool = False,
    compressed: bool = True,
) -> Dict[str, Any]:
    started = time.perf_counter()
    _ensure_trajectories(format_name, replay_dir, trajectories_path)
    trajectories = _load_trajectories(trajectories_path)

    state_rows: List[np.ndarray] = []
    action_rows: List[np.ndarray] = []
    labels: List[int] = []
    group_ids: List[int] = []
    turns: List[int] = []
    action_indices: List[int] = []
    action_kinds: List[str] = []
    action_labels: List[str] = []
    source_ids: List[str] = []
    chosen_kind_counts: Counter[str] = Counter()
    chosen_slot_counts: Counter[int] = Counter()
    candidates_per_decision: List[int] = []
    inferred_count = 0
    tactical_counts: Counter[str] = Counter()
    skipped = Counter()
    decision_id = 0

    for trajectory in trajectories:
        completed_teams = _reconstructed_completed_private_teams(trajectory)
        turns_payload = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
        for turn_record in sorted(turns_payload, key=lambda item: int(item.get("turn", 0) or 0)):
            turn_number = int(turn_record.get("turn", 0) or 0)
            events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
            for event in events:
                if not isinstance(event, dict) or event.get("type") not in ("move", "switch"):
                    continue
                side = event.get("side")
                if side not in ("p1", "p2"):
                    continue
                decision = _decision_rows(
                    trajectory=trajectory,
                    side=side,
                    turn_number=turn_number,
                    event=event,
                    completed_teams=completed_teams,
                    decision_id=decision_id,
                    sets_path=sets_path,
                )
                if not decision:
                    skipped["unmatched_chosen_action"] += 1
                    continue
                if sum(decision["labels"]) != 1:
                    skipped["bad_positive_count"] += 1
                    continue

                candidates_per_decision.append(len(decision["actions"]))
                for key, value in (decision.get("tactical") or {}).items():
                    if isinstance(value, bool) and value:
                        tactical_counts[key] += 1
                chosen_kind = decision["chosen_label"].split(":", 1)[0].strip().lower()
                chosen_kind_counts[chosen_kind] += 1
                if decision["inferred_own_info"]:
                    inferred_count += 1
                for action, action_feature, label in zip(decision["actions"], decision["action_features"], decision["labels"]):
                    state_rows.append(decision["state_features"])
                    action_rows.append(action_feature)
                    labels.append(int(label))
                    group_ids.append(decision_id)
                    turns.append(decision["turn"])
                    action_indices.append(int(action.get("index", 0) or 0))
                    kind = str(action.get("kind") or "")
                    action_kinds.append(kind)
                    if include_debug_fields:
                        action_labels.append(str(action.get("label") or ""))
                        source_ids.append(decision["replay_id"])
                    if label:
                        chosen_slot_counts[int(action.get("index", 0) or 0)] += 1
                decision_id += 1
                if max_decisions is not None and decision_id >= max_decisions:
                    break
            if max_decisions is not None and decision_id >= max_decisions:
                break
        if max_decisions is not None and decision_id >= max_decisions:
            break

    if not labels:
        raise ValueError("No action-ranking examples were produced.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        "state_features": np.asarray(state_rows, dtype=np.float16),
        "action_features": np.asarray(action_rows, dtype=np.float16),
        "labels": np.asarray(labels, dtype=np.int8),
        "group_ids": np.asarray(group_ids, dtype=np.int64),
        "turns": np.asarray(turns, dtype=np.int16),
        "action_indices": np.asarray(action_indices, dtype=np.int16),
        "action_kinds": np.asarray(action_kinds),
        "state_feature_version": np.asarray(FEATURE_VERSION),
        "state_feature_names": np.asarray(FEATURE_NAMES),
        "action_feature_version": np.asarray(ACTION_FEATURE_VERSION),
        "action_feature_names": np.asarray(ACTION_FEATURE_NAMES),
        "tactical_action_feature_names": np.asarray(TACTICAL_ACTION_FEATURE_NAMES),
    }
    if include_debug_fields:
        arrays["action_labels"] = np.asarray(action_labels)
        arrays["source_ids"] = np.asarray(source_ids)
    save_npz = np.savez_compressed if compressed else np.savez
    save_npz(output_path, **arrays)

    decisions = int(decision_id)
    total_candidates = int(len(labels))
    chosen_slot1 = int(chosen_slot_counts.get(0, 0))
    report = {
        "output_path": str(output_path),
        "format": format_name,
        "decisions": decisions,
        "legal_action_candidates": total_candidates,
        "average_candidates_per_decision": float(np.mean(candidates_per_decision)) if candidates_per_decision else 0.0,
        "state_feature_version": FEATURE_VERSION,
        "state_dim": FEATURE_DIM,
        "action_feature_version": ACTION_FEATURE_VERSION,
        "action_dim": ACTION_FEATURE_DIM,
        "tactical_feature_count": int(len(TACTICAL_ACTION_FEATURE_NAMES)),
        "percent_examples_with_repeated_failed_moves": float(100.0 * tactical_counts.get("has_repeated_failed_move", 0) / max(1, decisions)),
        "percent_examples_with_target_already_seeded": float(100.0 * tactical_counts.get("target_already_seeded", 0) / max(1, decisions)),
        "percent_examples_with_move_healed_target": float(100.0 * tactical_counts.get("move_healed_target", 0) / max(1, decisions)),
        "percent_examples_with_active_seeded": float(100.0 * (tactical_counts.get("own_active_seeded", 0) + tactical_counts.get("opp_active_seeded", 0)) / max(1, decisions)),
        "percent_examples_with_active_substitute": float(100.0 * (tactical_counts.get("own_active_substitute", 0) + tactical_counts.get("opp_active_substitute", 0)) / max(1, decisions)),
        "chosen_action_distribution_by_kind": dict(chosen_kind_counts),
        "chosen_move_slot_distribution": {str(key): int(value) for key, value in sorted(chosen_slot_counts.items())},
        "chosen_move_slot_1_count": chosen_slot1,
        "chosen_move_slot_1_rate": float(chosen_slot1 / max(1, decisions)),
        "missing_action_feature_rates": {"move_metadata_missing_rate": 0.0},
        "reconstructed_vs_inferred_own_info": {
            "reconstructed_decisions": int(decisions - inferred_count),
            "inferred_decisions": int(inferred_count),
            "inferred_rate": float(inferred_count / max(1, decisions)),
        },
        "skipped": dict(skipped),
        "compressed": bool(compressed),
        "include_debug_fields": bool(include_debug_fields),
        "output_size_mb": float(output_path.stat().st_size / (1024 * 1024)) if output_path.exists() else None,
        "wall_time_sec": time.perf_counter() - started,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(
        format_summary(
            "build-action-rank-dataset",
            {
                "decisions": decisions,
                "candidates": total_candidates,
                "avg_candidates": f"{report['average_candidates_per_decision']:.2f}",
                "slot1_rate": f"{report['chosen_move_slot_1_rate']:.3f}",
                "output": str(output_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Action Rank Dataset Report",
        "",
        f"- Decisions: {report['decisions']}",
        f"- Legal action candidates: {report['legal_action_candidates']}",
        f"- Average candidates per decision: {report['average_candidates_per_decision']:.2f}",
        f"- State/action dims: {report['state_dim']} / {report['action_dim']}",
        f"- Tactical action feature count: {report.get('tactical_feature_count', 0)}",
        f"- Chosen move slot 1 rate: {report['chosen_move_slot_1_rate']:.1%}",
        f"- Repeated failed move decisions: {report.get('percent_examples_with_repeated_failed_moves', 0.0):.1f}%",
        f"- Target already seeded decisions: {report.get('percent_examples_with_target_already_seeded', 0.0):.1f}%",
        f"- Move healed target decisions: {report.get('percent_examples_with_move_healed_target', 0.0):.1f}%",
        "",
        "## Chosen Action Kinds",
        "",
    ]
    for key, value in sorted(report.get("chosen_action_distribution_by_kind", {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Chosen Slot Distribution", ""])
    for key, value in sorted(report.get("chosen_move_slot_distribution", {}).items(), key=lambda item: int(item[0])):
        lines.append(f"- {key}: {value}")
    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build grouped legal-action ranking examples from public replays.")
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--trajectories", default=str(DEFAULT_TRAJECTORIES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--sets-path", default=None)
    parser.add_argument("--max-decisions", type=int, default=None)
    parser.add_argument("--include-debug-fields", action="store_true")
    parser.add_argument("--uncompressed", action="store_true")
    args = parser.parse_args()
    build_action_rank_dataset(
        format_name=args.format,
        replay_dir=Path(args.replay_dir),
        trajectories_path=Path(args.trajectories),
        output_path=Path(args.output),
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
        sets_path=args.sets_path,
        max_decisions=args.max_decisions,
        include_debug_fields=args.include_debug_fields,
        compressed=not args.uncompressed,
    )


if __name__ == "__main__":
    main()
