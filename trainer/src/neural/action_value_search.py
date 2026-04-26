import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
import torch

from .checkpoints import build_model_from_checkpoint, torch_load
from .value_features import (
    action_labels_from_request,
    adapt_feature_vector,
    discounted_terminal_return,
    featurize_value_state,
    final_result_from_winner,
    flatten_trace_steps,
    load_trace,
    select_trace_step,
    view_request_from_step,
)


ValueFn = Callable[[Dict[str, Any], Optional[Dict[str, Any]], Sequence[str], Sequence[Dict[str, Any]], Dict[str, Any]], float]


@dataclass
class SearchConfig:
    enabled: bool = True
    num_rollouts_per_action: int = 8
    max_depth_turns: int = 3
    opponent_policy: str = "mixture"
    rollout_policy: str = "model"
    temperature: float = 1.0


@dataclass
class ActionValueEstimate:
    action_index: int
    action_label: str
    mean_value: Optional[float]
    std_value: Optional[float]
    visit_count: int
    policy_prior: Optional[float]
    combined_score: Optional[float]
    source: str
    note: str


LIMITATION_NOTE = (
    "Exact simulator branching is not available through the current sim-core RPC. "
    "This evaluator uses trace continuations for the chosen action and leaves unvisited "
    "legal actions as value-prior estimates until clone/replay-to-state support exists."
)


def _trace_policy_priors(step: Dict[str, Any]) -> Dict[int, float]:
    priors: Dict[int, float] = {}
    top_k = step.get("model_top_k")
    if isinstance(top_k, list):
        for item in top_k:
            if not isinstance(item, dict):
                continue
            try:
                priors[int(item["index"])] = float(item.get("probability", 0.0))
            except (KeyError, TypeError, ValueError):
                continue
    return priors


def _load_value_fn(checkpoint_path: Optional[Path]) -> Optional[ValueFn]:
    if checkpoint_path is None or not checkpoint_path.exists():
        return None
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch_load(checkpoint_path, device)
    model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=[256, 256], device=device)
    model.eval()
    input_size = int(getattr(model, "_input_size"))

    def evaluate(
        view: Dict[str, Any],
        request: Optional[Dict[str, Any]],
        protocol_history: Sequence[str],
        step_history: Sequence[Dict[str, Any]],
        current_step: Dict[str, Any],
    ) -> float:
        feature_vector, _ = featurize_value_state(
            view,
            request,
            protocol_history=protocol_history,
            step_history=step_history,
            current_step=current_step,
            include_extras=True,
        )
        model_input = adapt_feature_vector(feature_vector, input_size)
        with torch.inference_mode():
            _, value = model(torch.from_numpy(model_input).unsqueeze(0).to(device))
        return float(value.item())

    return evaluate


def evaluate_actions_from_trace(
    trace: Dict[str, Any],
    step_index: int,
    *,
    value_fn: Optional[ValueFn] = None,
    config: SearchConfig = SearchConfig(),
) -> List[ActionValueEstimate]:
    steps = flatten_trace_steps(trace)
    step, ordinal, _ = select_trace_step(trace, step_index)
    view, request = view_request_from_step(trace, step)
    actions = action_labels_from_request(request)
    priors = _trace_policy_priors(step)
    chosen_raw = step.get("chosen_action_index", step.get("action_index", -1))
    chosen_index = int(chosen_raw) if chosen_raw is not None else -1
    final_result = final_result_from_winner(trace.get("winner"))
    future_depth = max(0, len(steps) - ordinal - 1)
    chosen_value = discounted_terminal_return(final_result, future_depth, 1.0)

    protocol_history: List[str] = []
    for previous in steps[: ordinal + 1]:
        lines = previous.get("protocol_log") if isinstance(previous.get("protocol_log"), list) else []
        protocol_history.extend(str(line) for line in lines)

    current_value = None
    if value_fn is not None:
        current_value = value_fn(view, request, protocol_history, steps[:ordinal], step)

    estimates: List[ActionValueEstimate] = []
    for action in actions:
        action_index = int(action["index"])
        prior = priors.get(action_index)
        if action_index == chosen_index:
            values = [chosen_value]
            mean_value = float(np.mean(values))
            std_value = float(np.std(values))
            visit_count = 1
            combined_score = mean_value
            source = "trace_chosen_continuation"
            note = "Observed chosen branch scored by final outcome."
        else:
            mean_value = current_value
            std_value = 0.0 if current_value is not None else None
            visit_count = 0
            combined_score = current_value
            source = "value_prior_only" if current_value is not None else "unvisited"
            note = LIMITATION_NOTE
        estimates.append(
            ActionValueEstimate(
                action_index=action_index,
                action_label=str(action["label"]),
                mean_value=mean_value,
                std_value=std_value,
                visit_count=visit_count,
                policy_prior=prior,
                combined_score=combined_score,
                source=source,
                note=note,
            )
        )
    estimates.sort(
        key=lambda item: item.combined_score if item.combined_score is not None else float("-inf"),
        reverse=True,
    )
    return estimates


def evaluate_trace_path(
    trace_path: Path,
    step_index: int,
    *,
    value_checkpoint: Optional[Path] = None,
    config: SearchConfig = SearchConfig(),
) -> List[ActionValueEstimate]:
    value_fn = _load_value_fn(value_checkpoint)
    return evaluate_actions_from_trace(load_trace(trace_path), step_index, value_fn=value_fn, config=config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace-based action-value evaluator interface.")
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--step-index", type=int, required=True)
    parser.add_argument("--value-checkpoint", default=None)
    args = parser.parse_args()
    estimates = evaluate_trace_path(
        Path(args.trace_path),
        args.step_index,
        value_checkpoint=Path(args.value_checkpoint) if args.value_checkpoint else None,
    )
    print(json.dumps([asdict(estimate) for estimate in estimates], indent=2))


if __name__ == "__main__":
    main()
