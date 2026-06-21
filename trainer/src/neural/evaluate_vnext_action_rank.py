"""Read-only offline evaluation of the vNext action-rank head against baselines.

Loads an existing diagnostic checkpoint, validates its schema/fingerprint
metadata, and compares the rank head with simple feature heuristics on a chosen
split (default: validation). Does not train, tune, or write checkpoints.
"""

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import torch

from .train_vnext_diagnostic import (
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
    validate_vnext_checkpoint_metadata,
)
from .vnext_inference import VNextActionRanker

# legal-action-v5 column indices used by the baselines.
COL_KIND_MOVE = 0
COL_IS_TERA = 56
COL_BASE_POWER = 28
COL_ACCURACY = 29
COL_CLASS_DAMAGE = 189
COL_EXPECTED_DAMAGE = 269
COL_KO_CHANCE = 273
NEG = -1.0e9


def _rank_of_chosen(score: np.ndarray, chosen: int) -> int:
    order = np.argsort(-score, kind="stable")
    return int(np.flatnonzero(order == chosen)[0]) + 1


def _baseline_scores(af: np.ndarray) -> Dict[str, np.ndarray]:
    is_move = af[:, COL_KIND_MOVE] > 0.5
    is_damaging = af[:, COL_CLASS_DAMAGE] > 0.5
    reg_move = is_move & (af[:, COL_IS_TERA] < 0.5)
    acc = np.where(is_damaging, af[:, COL_ACCURACY], NEG)
    if not np.any(is_damaging):
        acc = af[:, COL_ACCURACY]
    no_switch = np.where(is_move, af[:, COL_EXPECTED_DAMAGE], NEG)
    if not np.any(is_move):
        no_switch = np.zeros(len(af), dtype=np.float32)
    # Prefer a regular move, then a Tera move, then a switch; break ties by damage.
    type_prior = (
        reg_move.astype(np.float32) * 2.0
        + (is_move & (af[:, COL_IS_TERA] > 0.5)).astype(np.float32) * 1.0
        + af[:, COL_EXPECTED_DAMAGE] * 1.0e-3
    )
    return {
        "max_base_power": af[:, COL_BASE_POWER].copy(),
        "max_expected_damage": af[:, COL_EXPECTED_DAMAGE].copy(),
        "max_ko_chance": af[:, COL_KO_CHANCE].copy(),
        "max_accuracy_damaging": acc,
        "best_damage_move_no_switch": no_switch,
        "type_prior_move": type_prior,
    }


def _agg(ranks: Sequence[int]) -> Dict[str, float]:
    ranks = np.asarray(ranks, dtype=np.float64)
    if ranks.size == 0:
        return {"groups": 0, "top1": 0.0, "top3": 0.0, "mrr": 0.0}
    return {
        "groups": int(len(ranks)),
        "top1": float(np.mean(ranks == 1)),
        "top3": float(np.mean(ranks <= 3)),
        "mrr": float(np.mean(1.0 / ranks)),
    }


def _feature_index(names: Sequence[str], name: str) -> int:
    try:
        return names.index(name)
    except ValueError as exc:
        raise ValueError(f"Offline evaluation requires feature {name!r}.") from exc


def verify_incompatible_checkpoint_rejections(
    checkpoint: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Prove strict metadata checks reject common incompatible checkpoint cases."""
    dataset_cfg = config["dataset"]
    expected = {
        "expected_state_version": str(dataset_cfg["state_feature_version"]),
        "expected_action_version": str(dataset_cfg["action_feature_version"]),
        "expected_state_dim": int(dataset_cfg["state_feature_dim"]),
        "expected_action_dim": int(dataset_cfg["action_feature_dim"]),
        "expected_state_feature_names_sha256": str(
            dataset_cfg["state_feature_names_sha256"]
        ),
        "expected_action_feature_names_sha256": str(
            dataset_cfg["action_feature_names_sha256"]
        ),
        "require_fingerprints": True,
    }
    mutations = {
        "state_schema": ("state_feature_version", "incompatible-state-schema"),
        "action_schema": ("action_feature_version", "incompatible-action-schema"),
        "state_dimension": ("state_dim", int(dataset_cfg["state_feature_dim"]) - 1),
        "action_dimension": ("action_dim", int(dataset_cfg["action_feature_dim"]) - 1),
        "state_fingerprint": ("state_feature_names_sha256", "0" * 64),
        "action_fingerprint": ("action_feature_names_sha256", "f" * 64),
    }
    results: Dict[str, Any] = {}
    for name, (field, value) in mutations.items():
        incompatible = copy.copy(checkpoint)
        incompatible[field] = value
        try:
            validate_vnext_checkpoint_metadata(incompatible, **expected)
        except ValueError as exc:
            results[name] = {"rejected": True, "reason": str(exc)}
        else:
            results[name] = {"rejected": False, "reason": None}
    if not all(result["rejected"] for result in results.values()):
        failed = [name for name, result in results.items() if not result["rejected"]]
        raise AssertionError(f"Incompatible checkpoint metadata was accepted: {failed}")
    return {"status": "PASS", "cases": results}


def _slice_metrics(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    ranks = [int(record["model_rank"]) for record in records]
    maxdmg_ranks = [int(record["maxdmg_rank"]) for record in records]
    result = {
        **_agg(ranks),
        "nll": float(np.mean([record["nll"] for record in records])) if records else 0.0,
        "max_expected_damage_top1": (
            float(np.mean(np.asarray(maxdmg_ranks) == 1)) if records else 0.0
        ),
        "top1_wrong_top3_contains": int(
            sum(1 for rank in ranks if 1 < rank <= 3)
        ),
        "top3_miss": int(sum(1 for rank in ranks if rank > 3)),
    }
    chosen_to_pick: Dict[str, int] = {}
    for record in records:
        if record["model_rank"] == 1:
            continue
        key = f"{record['chosen_kind']}->{record['model_pick_kind']}"
        chosen_to_pick[key] = chosen_to_pick.get(key, 0) + 1
    result["top1_mistake_kind_pairs"] = dict(
        sorted(chosen_to_pick.items(), key=lambda item: (-item[1], item[0]))[:5]
    )
    return result


def _mechanic_replay_sets(config: Dict[str, Any], config_path: Path) -> Dict[str, set]:
    """Find replay-level ability contexts without changing or rematerializing data."""
    snapshot = Path(config["_resolved_metadata_path"]).parent / "source_manifest_snapshot.json"
    result = {"magic_bounce_replay": set(), "good_as_gold_replay": set()}
    if not snapshot.is_file():
        return result
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    repo_root = Path(config_path).resolve().parent.parent
    for entry in payload.get("entries", []):
        replay_id = str(entry.get("replay_id") or "")
        replay_path = repo_root / str(entry.get("path") or "")
        if not replay_id or not replay_path.is_file():
            continue
        text = replay_path.read_text(encoding="utf-8", errors="ignore").lower()
        if "ability: magic bounce" in text:
            result["magic_bounce_replay"].add(replay_id)
        if "ability: good as gold" in text:
            result["good_as_gold_replay"].add(replay_id)
    return result


def evaluate(
    config_path: Path,
    checkpoint_path: Path,
    *,
    split: str = "validation",
    example_count: int = 6,
) -> Dict[str, Any]:
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ranker = VNextActionRanker.load(
        config_path, checkpoint_path, device=device
    )
    schema_validation = ranker.metadata["schema_validation"]
    rejection_checks = verify_incompatible_checkpoint_rejections(checkpoint, config)
    mechanic_replays = _mechanic_replay_sets(config, config_path)

    with np.load(config["_resolved_dataset_path"], allow_pickle=False) as loaded:
        state_names = loaded["state_feature_names"].astype(str).tolist()
        action_names = loaded["action_feature_names"].astype(str).tolist()
        state_sides = (
            loaded["state_sides"].astype(str)
            if "state_sides" in loaded.files
            else np.full(len(dataset.state_features), "p1")
        )

    required_state_slice_names = (
        "own_remaining_count_norm",
        "own_active_hp_fraction",
        "tera_available_visible",
        "own_current_type_is_tera",
        "own_hazard_layers_norm",
        "opp_hazard_layers_norm",
        "recent_target_fainted_count_norm",
        "own_active_displayed_species_uncertain",
        "opponent_active_displayed_species_uncertain",
        "own_active_illusion_revealed",
        "opponent_active_illusion_revealed",
        "p1_boost_sum_norm",
        "p2_boost_sum_norm",
        "own_force_switch",
    )
    required_action_slice_names = (
        "current_active_low_hp",
        "flag_setup",
        "flag_hazard",
        "move_id_flag_rapidspin",
        "move_id_flag_defog",
        "target_hp_fraction",
        "impact_ko_chance",
        "target_known_or_possible_ability_blocks_move_effect",
        "may_fail_due_to_priority_prevention",
        "effect_user_side_hazards_removed",
        "effect_target_side_hazards_removed",
        "cmd_forced_switch",
    )
    slice_features_available = all(
        name in state_names for name in required_state_slice_names
    ) and all(name in action_names for name in required_action_slice_names)
    sidx = (
        {name: _feature_index(state_names, name) for name in required_state_slice_names}
        if slice_features_available
        else {}
    )
    aidx = (
        {name: _feature_index(action_names, name) for name in required_action_slice_names}
        if slice_features_available
        else {}
    )

    groups = dataset.split_group_state_indices[split]
    baseline_names = list(_baseline_scores(np.zeros((1, dataset.action_features.shape[1]), np.float32)))
    model_ranks: List[int] = []
    model_nll = 0.0
    baseline_ranks: Dict[str, List[int]] = {name: [] for name in baseline_names}
    random_top1 = random_top3 = random_mrr = 0.0
    rmove_top1 = rmove_top3 = 0.0
    records: List[Dict[str, Any]] = []

    with torch.no_grad():
        for state_index in groups:
            rows = dataset.candidate_rows_by_state[int(state_index)]
            af = dataset.action_features[rows].astype(np.float32)
            labels = dataset.action_rank_labels[rows]
            kinds = dataset.candidate_kinds[rows]
            chosen = int(np.flatnonzero(labels == 1)[0])
            n = len(rows)

            state_vector = dataset.state_features[int(state_index)].astype(np.float32)
            candidates = [
                {"action_features": af[index], "kind": str(kinds[index])}
                for index in range(n)
            ]
            scores = ranker.score(state_vector, candidates)
            m_rank = _rank_of_chosen(scores, chosen)
            model_ranks.append(m_rank)
            probs = torch.softmax(torch.from_numpy(scores), dim=0).numpy()
            group_nll = -math.log(max(1e-8, float(probs[chosen])))
            model_nll += group_nll

            bscores = _baseline_scores(af)
            for name, score in bscores.items():
                baseline_ranks[name].append(_rank_of_chosen(score, chosen))

            random_top1 += 1.0 / n
            random_top3 += min(3, n) / n
            random_mrr += sum(1.0 / r for r in range(1, n + 1)) / n
            move_mask = af[:, COL_KIND_MOVE] > 0.5
            n_move = int(move_mask.sum())
            chosen_is_move = bool(move_mask[chosen])
            if n_move > 0 and chosen_is_move:
                rmove_top1 += 1.0 / n_move
                rmove_top3 += min(3, n_move) / n_move

            tags = {
                "high_candidate_count": n > 12,
                "top1_wrong_top3_contains": 1 < m_rank <= 3,
                "magic_bounce_replay": str(
                    dataset.state_replay_ids[int(state_index)]
                ) in mechanic_replays["magic_bounce_replay"],
                "good_as_gold_replay": str(
                    dataset.state_replay_ids[int(state_index)]
                ) in mechanic_replays["good_as_gold_replay"],
            }
            if slice_features_available:
                chosen_af = af[chosen]
                own_boost = state_vector[
                    sidx["p1_boost_sum_norm"]
                    if state_sides[int(state_index)] == "p1"
                    else sidx["p2_boost_sum_norm"]
                ]
                tags.update({
                    "normal_move_choice": bool(
                        kinds[chosen] in {"move", "move_tera"}
                        and state_vector[sidx["own_force_switch"]] < 0.5
                    ),
                    "forced_switch": bool(
                        kinds[chosen] == "switch"
                        and (
                            state_vector[sidx["own_force_switch"]] > 0.5
                            or chosen_af[aidx["cmd_forced_switch"]] > 0.5
                            or np.all(kinds == "switch")
                        )
                    ),
                    "voluntary_switch": bool(
                        kinds[chosen] == "switch"
                        and state_vector[sidx["own_force_switch"]] < 0.5
                        and chosen_af[aidx["cmd_forced_switch"]] < 0.5
                        and np.any(kinds != "switch")
                    ),
                    "low_hp_or_endgame": bool(
                        chosen_af[aidx["current_active_low_hp"]] > 0.5
                        or state_vector[sidx["own_active_hp_fraction"]] <= 0.25
                        or state_vector[sidx["own_remaining_count_norm"]] <= 0.5
                    ),
                    "tera_available": bool(
                        state_vector[sidx["tera_available_visible"]] > 0.5
                    ),
                    "tera_used_or_chosen": bool(
                        state_vector[sidx["own_current_type_is_tera"]] > 0.5
                        or kinds[chosen] == "move_tera"
                    ),
                    "hazards_or_removal": bool(
                        state_vector[sidx["own_hazard_layers_norm"]] > 0
                        or state_vector[sidx["opp_hazard_layers_norm"]] > 0
                        or chosen_af[aidx["flag_hazard"]] > 0.5
                        or chosen_af[aidx["move_id_flag_rapidspin"]] > 0.5
                        or chosen_af[aidx["move_id_flag_defog"]] > 0.5
                        or chosen_af[aidx["effect_user_side_hazards_removed"]] > 0.5
                        or chosen_af[aidx["effect_target_side_hazards_removed"]] > 0.5
                    ),
                    "setup_or_sweep": bool(
                        chosen_af[aidx["flag_setup"]] > 0.5 or own_boost >= 0.15
                    ),
                    "obvious_revenge_kill_proxy": bool(
                        state_vector[sidx["recent_target_fainted_count_norm"]] > 0
                        and chosen_af[aidx["impact_ko_chance"]] >= 0.75
                    ),
                    "prevention_interaction": bool(
                        np.any(
                            af[:, aidx["target_known_or_possible_ability_blocks_move_effect"]]
                            > 0.5
                        )
                        or np.any(
                            af[:, aidx["may_fail_due_to_priority_prevention"]] > 0.5
                        )
                    ),
                    "illusion_or_displayed_species_ambiguity": bool(
                        state_vector[sidx["own_active_displayed_species_uncertain"]] > 0.5
                        or state_vector[sidx["opponent_active_displayed_species_uncertain"]]
                        > 0.5
                        or state_vector[sidx["own_active_illusion_revealed"]] > 0.5
                        or state_vector[sidx["opponent_active_illusion_revealed"]] > 0.5
                    ),
                })
            records.append(
                {
                    "state_index": int(state_index),
                    "replay_id": str(dataset.state_replay_ids[int(state_index)]),
                    "turn": int(dataset.state_turns[int(state_index)]),
                    "n": n,
                    "chosen_kind": str(kinds[chosen]),
                    "chosen_damaging": bool(af[chosen, COL_CLASS_DAMAGE] > 0.5),
                    "chosen_expected_damage": float(af[chosen, COL_EXPECTED_DAMAGE]),
                    "model_rank": m_rank,
                    "nll": group_nll,
                    "maxdmg_rank": baseline_ranks["max_expected_damage"][-1],
                    "model_pick_kind": str(kinds[int(np.argmax(scores))]),
                    "model_pick_expected_damage": float(
                        af[int(np.argmax(scores)), COL_EXPECTED_DAMAGE]
                    ),
                    "tags": sorted(name for name, active in tags.items() if active),
                }
            )

    total = len(model_ranks)
    summary: Dict[str, Any] = {
        "split": split,
        "matched_groups": total,
        "checkpoint_path": str(checkpoint_path),
        "device": str(device),
        "schema_validation": schema_validation,
        "incompatible_checkpoint_rejection": rejection_checks,
        "slice_features_available": slice_features_available,
        "model": {**_agg(model_ranks), "nll": model_nll / max(1, total)},
        "baselines": {
            "random_legal": {
                "groups": total,
                "top1": random_top1 / total,
                "top3": random_top3 / total,
                "mrr": random_mrr / total,
            },
            "random_move": {
                "groups": total,
                "top1": rmove_top1 / total,
                "top3": rmove_top3 / total,
            },
            **{name: _agg(ranks) for name, ranks in baseline_ranks.items()},
        },
    }

    # Breakdowns by chosen action type.
    by_kind: Dict[str, List[int]] = {}
    for rec in records:
        by_kind.setdefault(rec["chosen_kind"], []).append(rec["model_rank"])
    summary["model_by_chosen_kind"] = {k: _agg(v) for k, v in sorted(by_kind.items())}

    # Breakdown: damaging vs non-damaging replay choice.
    summary["model_by_chosen_damaging"] = {
        "damaging": _agg([r["model_rank"] for r in records if r["chosen_damaging"]]),
        "non_damaging": _agg([r["model_rank"] for r in records if not r["chosen_damaging"]]),
    }

    # Breakdown by candidate-count bucket.
    def _cand_bucket(n: int) -> str:
        if n <= 4:
            return "<=4"
        if n <= 8:
            return "5-8"
        if n <= 12:
            return "9-12"
        return ">12"

    cbuckets: Dict[str, List[int]] = {}
    for rec in records:
        cbuckets.setdefault(_cand_bucket(rec["n"]), []).append(rec["model_rank"])
    summary["model_by_candidate_count"] = {
        k: _agg(cbuckets[k]) for k in ["<=4", "5-8", "9-12", ">12"] if k in cbuckets
    }

    # Breakdown by turn bucket.
    def _turn_bucket(t: int) -> str:
        if t <= 5:
            return "1-5"
        if t <= 10:
            return "6-10"
        if t <= 20:
            return "11-20"
        return ">20"

    tbuckets: Dict[str, List[int]] = {}
    for rec in records:
        tbuckets.setdefault(_turn_bucket(rec["turn"]), []).append(rec["model_rank"])
    summary["model_by_turn_bucket"] = {
        k: _agg(tbuckets[k]) for k in ["1-5", "6-10", "11-20", ">20"] if k in tbuckets
    }

    slice_names = [
        "normal_move_choice",
        "forced_switch",
        "voluntary_switch",
        "low_hp_or_endgame",
        "tera_available",
        "tera_used_or_chosen",
        "hazards_or_removal",
        "setup_or_sweep",
        "obvious_revenge_kill_proxy",
        "prevention_interaction",
        "magic_bounce_replay",
        "good_as_gold_replay",
        "illusion_or_displayed_species_ambiguity",
        "high_candidate_count",
        "top1_wrong_top3_contains",
    ]
    summary["slices"] = {
        name: _slice_metrics([record for record in records if name in record["tags"]])
        for name in slice_names
    }

    # Curated examples: model right where max-damage wrong, and vice versa.
    good = [r for r in records if r["model_rank"] == 1 and r["maxdmg_rank"] > 1]
    bad = [r for r in records if r["model_rank"] > 1 and r["maxdmg_rank"] == 1]
    good.sort(key=lambda r: r["maxdmg_rank"], reverse=True)
    bad.sort(key=lambda r: r["model_rank"], reverse=True)
    summary["model_beats_maxdmg_count"] = len(good)
    summary["maxdmg_beats_model_count"] = len(bad)
    summary["examples_model_good"] = good[:example_count]
    summary["examples_model_bad"] = bad[:example_count]
    return summary


def main(argv: Sequence[str] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--examples", type=int, default=6)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    summary = evaluate(
        Path(args.config),
        Path(args.checkpoint),
        split=args.split,
        example_count=args.examples,
    )
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return summary


if __name__ == "__main__":
    main()
