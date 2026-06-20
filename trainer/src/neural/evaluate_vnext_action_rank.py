"""Read-only offline evaluation of the vNext action-rank head against baselines.

Loads an existing diagnostic checkpoint, validates its schema/fingerprint
metadata, and compares the rank head with simple feature heuristics on a chosen
split (default: validation). Does not train, tune, or write checkpoints.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import torch

from .train_vnext_diagnostic import (
    build_diagnostic_model,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
    validate_vnext_checkpoint_metadata,
)

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
    schema_validation = validate_vnext_checkpoint_metadata(
        checkpoint,
        expected_state_feature_names_sha256=dataset.validation["state_feature_names_sha256"],
        expected_action_feature_names_sha256=dataset.validation["action_feature_names_sha256"],
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_diagnostic_model(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

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

            state = torch.from_numpy(
                dataset.state_features[int(state_index)].astype(np.float32)
            ).unsqueeze(0).to(device)
            embedding = model.encode_states(state).expand(n, -1)
            scores = model.rank_from_embeddings(
                embedding, torch.from_numpy(af).to(device)
            ).cpu().numpy()
            m_rank = _rank_of_chosen(scores, chosen)
            model_ranks.append(m_rank)
            probs = torch.softmax(torch.from_numpy(scores), dim=0).numpy()
            model_nll += -math.log(max(1e-8, float(probs[chosen])))

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

            records.append(
                {
                    "state_index": int(state_index),
                    "turn": int(dataset.state_turns[int(state_index)]),
                    "n": n,
                    "chosen_kind": str(kinds[chosen]),
                    "chosen_damaging": bool(af[chosen, COL_CLASS_DAMAGE] > 0.5),
                    "chosen_expected_damage": float(af[chosen, COL_EXPECTED_DAMAGE]),
                    "model_rank": m_rank,
                    "maxdmg_rank": baseline_ranks["max_expected_damage"][-1],
                    "model_pick_kind": str(kinds[int(np.argmax(scores))]),
                    "model_pick_expected_damage": float(
                        af[int(np.argmax(scores)), COL_EXPECTED_DAMAGE]
                    ),
                }
            )

    total = len(model_ranks)
    summary: Dict[str, Any] = {
        "split": split,
        "matched_groups": total,
        "checkpoint_path": str(checkpoint_path),
        "schema_validation": schema_validation,
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
