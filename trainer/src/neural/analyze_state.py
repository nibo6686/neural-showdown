import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from .checkpoints import build_model_from_checkpoint, torch_load
from .models.policy_value_mlp import masked_logits
from .value_features import (
    action_labels_from_request,
    adapt_feature_vector,
    featurize_value_state,
    flatten_trace_steps,
    load_trace,
    select_trace_step,
    view_request_from_step,
)


def _active_pokemon(view: Dict[str, Any], side: str) -> Dict[str, Any]:
    team_key = "self_team" if side == "p1" else "opponent_team"
    active_key = "self" if side == "p1" else "opponent"
    team = view.get(team_key, [])
    active_index = view.get("active", {}).get(active_key)
    if active_index is None:
        for pokemon in team:
            if pokemon.get("active"):
                return pokemon
        return team[0] if team else {}
    return team[int(active_index)] if 0 <= int(active_index) < len(team) else {}


def _format_boosts(boosts: Dict[str, Any]) -> str:
    active = [f"{stat}:{int(value):+d}" for stat, value in sorted((boosts or {}).items()) if value]
    return ", ".join(active) if active else "none"


def _format_pokemon(prefix: str, pokemon: Dict[str, Any]) -> str:
    species = pokemon.get("species") or pokemon.get("name") or "Unknown"
    hp = float(pokemon.get("hp_ratio") or 0.0)
    status = pokemon.get("status") or "none"
    boosts = _format_boosts(pokemon.get("boosts", {}))
    return f"{prefix}: {species} | hp={hp:.0%} status={status} boosts={boosts}"


def _policy_probs(
    checkpoint_path: Optional[Path],
    feature_vector: np.ndarray,
    legal_mask: np.ndarray,
    device: torch.device,
) -> Optional[np.ndarray]:
    if checkpoint_path is None or not checkpoint_path.exists():
        return None
    checkpoint = torch_load(checkpoint_path, device)
    model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=[256, 256], device=device)
    model.eval()
    model_input = adapt_feature_vector(feature_vector, int(getattr(model, "_input_size")))
    with torch.inference_mode():
        logits, _ = model(torch.from_numpy(model_input).unsqueeze(0).to(device))
        mask = torch.from_numpy(adapt_feature_vector(legal_mask, 13)).unsqueeze(0).to(device)
        probs = torch.softmax(masked_logits(logits, mask), dim=-1)
    return probs.squeeze(0).cpu().numpy()


def _trace_policy_probs(step: Dict[str, Any]) -> Optional[Dict[int, float]]:
    top_k = step.get("model_top_k")
    if not isinstance(top_k, list):
        return None
    result: Dict[int, float] = {}
    for item in top_k:
        if not isinstance(item, dict):
            continue
        try:
            result[int(item["index"])] = float(item.get("probability", 0.0))
        except (KeyError, TypeError, ValueError):
            continue
    return result


def _rank_actions(
    actions: List[Dict[str, Any]],
    policy_probs: Optional[np.ndarray],
    trace_probs: Optional[Dict[int, float]],
    limit: int,
) -> List[Tuple[Dict[str, Any], Optional[float]]]:
    scored: List[Tuple[Dict[str, Any], Optional[float]]] = []
    for action in actions:
        index = int(action["index"])
        prob = None
        if policy_probs is not None and 0 <= index < len(policy_probs):
            prob = float(policy_probs[index])
        elif trace_probs is not None:
            prob = trace_probs.get(index)
        scored.append((action, prob))
    scored.sort(key=lambda item: item[1] if item[1] is not None else -1.0, reverse=True)
    return scored[:limit]


def analyze_state(
    *,
    trace_path: Path,
    step_index: int,
    value_checkpoint: Path,
    policy_checkpoint: Optional[Path] = None,
    top_k: int = 5,
) -> str:
    trace = load_trace(trace_path)
    all_steps = flatten_trace_steps(trace)
    step, ordinal, exact_match = select_trace_step(trace, step_index)
    view, request = view_request_from_step(trace, step)
    protocol_history: List[str] = []
    for previous in all_steps[: ordinal + 1]:
        lines = previous.get("protocol_log") if isinstance(previous.get("protocol_log"), list) else []
        protocol_history.extend(str(line) for line in lines)
    feature_vector, legal_mask = featurize_value_state(
        view,
        request,
        protocol_history=protocol_history,
        step_history=all_steps[:ordinal],
        current_step=step,
        include_extras=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch_load(value_checkpoint, device)
    value_model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=[256, 256], device=device)
    value_model.eval()
    value_input = adapt_feature_vector(feature_vector, int(getattr(value_model, "_input_size")))
    with torch.inference_mode():
        _, value_tensor = value_model(torch.from_numpy(value_input).unsqueeze(0).to(device))
    value = float(value_tensor.item())
    p1_win_prob = max(0.0, min(1.0, (value + 1.0) / 2.0))

    policy_probs = _policy_probs(policy_checkpoint, feature_vector, legal_mask, device)
    trace_probs = _trace_policy_probs(step)
    actions = action_labels_from_request(request)
    ranked_actions = _rank_actions(actions, policy_probs, trace_probs, top_k)

    lines = []
    if not exact_match:
        lines.append(f"requested step_index={step_index} not found; showing nearest ordinal={ordinal}")
    lines.append(f"state value | p1_win_prob={p1_win_prob:.2f} value={value:.2f}")
    lines.append(f"trace={trace_path} battle_index={trace.get('battle_index')} turn={step.get('turn', view.get('turn'))} step_index={step.get('step_index', ordinal)}")
    lines.append(_format_pokemon("p1 active", _active_pokemon(view, "p1")))
    lines.append(_format_pokemon("p2 active", _active_pokemon(view, "p2")))
    lines.append("top legal actions:")
    if not ranked_actions:
        lines.append("  none")
    for rank, (action, prob) in enumerate(ranked_actions, start=1):
        prob_text = f" policy_prob={prob:.2f}" if prob is not None else ""
        lines.append(f"  {rank}. {action['label']}{prob_text}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a single traced battle state with a value checkpoint.")
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--step-index", type=int, required=True)
    parser.add_argument("--value-checkpoint", required=True)
    parser.add_argument("--policy-checkpoint", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    print(
        analyze_state(
            trace_path=Path(args.trace_path),
            step_index=args.step_index,
            value_checkpoint=Path(args.value_checkpoint),
            policy_checkpoint=Path(args.policy_checkpoint) if args.policy_checkpoint else None,
            top_k=args.top_k,
        )
    )


if __name__ == "__main__":
    main()
