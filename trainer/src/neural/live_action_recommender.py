from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from .action_features import ACTION_FEATURE_DIM, build_action_feature_vector
from .build_replay_value_dataset import FEATURE_NAMES as PUBLIC_FEATURE_NAMES
from .checkpoints import torch_load
from .live_private_features import build_live_private_feature_vector
from .models.action_ranker import ActionRankerMLP


PolicyLoader = Callable[[], Tuple[Optional[torch.nn.Module], Optional[Dict[str, Any]]]]
DEFAULT_ACTION_RANKER_PATH = Path("artifacts/checkpoints/gen9randombattle_action_ranker.pt")
_action_ranker_model: Optional[ActionRankerMLP] = None
_action_ranker_metadata: Optional[Dict[str, Any]] = None


def reset_action_ranker_cache() -> None:
    global _action_ranker_model, _action_ranker_metadata
    _action_ranker_model = None
    _action_ranker_metadata = None


def load_action_ranker_once(
    *,
    path: Optional[Path] = None,
    device: torch.device,
) -> Tuple[Optional[ActionRankerMLP], Optional[Dict[str, Any]]]:
    global _action_ranker_model, _action_ranker_metadata
    selected_path = path or DEFAULT_ACTION_RANKER_PATH
    if _action_ranker_model is not None or _action_ranker_metadata is not None:
        return _action_ranker_model, _action_ranker_metadata
    if not selected_path.exists():
        _action_ranker_metadata = {"warning": f"Action ranker checkpoint missing: {selected_path}"}
        return None, _action_ranker_metadata
    checkpoint = torch_load(selected_path, device)
    input_size = int(checkpoint.get("input_size", 0) or 0)
    hidden_sizes = list(checkpoint.get("hidden_sizes", [256, 128]))
    action_dim = int(checkpoint.get("action_dim", ACTION_FEATURE_DIM))
    model = ActionRankerMLP(input_size=input_size, hidden_sizes=hidden_sizes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    model.eval()
    _action_ranker_model = model
    _action_ranker_metadata = {
        **checkpoint,
        "path": str(selected_path),
        "input_size": input_size,
        "action_dim": action_dim,
        "model_type": "action-ranker",
    }
    return _action_ranker_model, _action_ranker_metadata


def _model_output_value(output: Any) -> float:
    if isinstance(output, tuple):
        value_tensor = output[1]
    elif isinstance(output, dict):
        value_tensor = output.get("value") or output.get("values")
    else:
        value_tensor = output
    return float(value_tensor.squeeze().detach().cpu().item())


def _legal_action_to_dict(action: Any) -> Dict[str, Any]:
    if isinstance(action, dict):
        return dict(action)
    if hasattr(action, "model_dump"):
        return action.model_dump()
    if hasattr(action, "dict"):
        return action.dict()
    return {}


def _request_active_moves(request_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    active = request_payload.get("active")
    active_block = active[0] if isinstance(active, list) and active else active if isinstance(active, dict) else {}
    moves = active_block.get("moves") if isinstance(active_block, dict) else None
    if not isinstance(moves, list):
        return []
    result = []
    for index, move in enumerate(moves):
        if not isinstance(move, dict):
            continue
        name = move.get("move") or move.get("name") or move.get("id") or f"move {index + 1}"
        result.append(
            {
                "index": int(move.get("index", index) if move.get("index") is not None else index),
                "kind": "move",
                "label": f"move: {name}",
                "slot": int(move.get("slot", index + 1) if move.get("slot") is not None else index + 1),
                "disabled": bool(move.get("disabled", False)),
                "source": "request.active.moves",
            }
        )
    return result


def _request_switches(request_payload: Optional[Dict[str, Any]], existing_labels: Sequence[str]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    side = request_payload.get("side") if isinstance(request_payload.get("side"), dict) else {}
    team = side.get("pokemon") if isinstance(side.get("pokemon"), list) else []
    existing = {label.lower() for label in existing_labels}
    switches = []
    switch_index = 8
    for slot, mon in enumerate(team):
        if not isinstance(mon, dict):
            continue
        if mon.get("active") or mon.get("fainted") or "fnt" in str(mon.get("condition", "")):
            continue
        details = str(mon.get("details") or mon.get("ident") or f"slot {slot + 1}")
        species = details.split(",", 1)[0].split(": ", 1)[-1].strip()
        label = f"switch: {species}"
        if label.lower() in existing:
            continue
        switches.append(
            {
                "index": int(mon.get("index", switch_index) if mon.get("index") is not None else switch_index),
                "kind": "switch",
                "label": label,
                "slot": slot,
                "disabled": False,
                "source": "request.side.pokemon",
            }
        )
        switch_index += 1
    return switches


def _normalize_payload_legal_actions(raw_legal_actions: Sequence[Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for fallback_index, action in enumerate(raw_legal_actions):
        action_dict = _legal_action_to_dict(action)
        kind = str(action_dict.get("kind") or "")
        label = str(action_dict.get("label") or "")
        if not label:
            continue
        display_label = label
        if kind == "move" and not display_label.lower().startswith("move:"):
            display_label = f"move: {display_label}"
        if kind == "switch" and not display_label.lower().startswith("switch:"):
            display_label = f"switch: {display_label}"
        candidates.append(
            {
                "index": int(action_dict.get("index") if action_dict.get("index") is not None else fallback_index),
                "kind": kind,
                "label": display_label,
                "slot": action_dict.get("slot"),
                "disabled": bool(action_dict.get("disabled", False)),
                "source": "payload.legal_actions",
            }
        )
    return candidates


def legal_action_candidates(payload: Any) -> List[Dict[str, Any]]:
    request_payload = getattr(payload, "request", None)
    raw_legal_actions = getattr(payload, "legal_actions", []) or []
    if raw_legal_actions:
        candidates = _normalize_payload_legal_actions(raw_legal_actions)
    else:
        candidates = _request_active_moves(request_payload)
        labels = [str(candidate["label"]) for candidate in candidates]
        candidates.extend(_request_switches(request_payload, labels))

    seen = set()
    deduped = []
    for candidate in candidates:
        key = (candidate.get("index"), candidate.get("kind"), candidate.get("label"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _policy_features_for_model(
    *,
    policy_metadata: Dict[str, Any],
    public_features: np.ndarray,
    live_features: np.ndarray,
) -> np.ndarray:
    input_size = int(policy_metadata.get("input_size", len(PUBLIC_FEATURE_NAMES)))
    if input_size == live_features.shape[0]:
        return live_features.astype(np.float32)
    if input_size == public_features.shape[0]:
        return public_features.astype(np.float32)
    selected = live_features if live_features.shape[0] < input_size else live_features[:input_size]
    if selected.shape[0] == input_size:
        return selected.astype(np.float32)
    padded = np.zeros(input_size, dtype=np.float32)
    padded[: selected.shape[0]] = selected
    return padded


def _policy_probs(
    *,
    policy_loader: PolicyLoader,
    public_features: np.ndarray,
    live_features: np.ndarray,
    device: torch.device,
) -> Tuple[Optional[np.ndarray], Dict[str, Any], List[str]]:
    policy_model, policy_metadata = policy_loader()
    metadata = policy_metadata or {}
    if policy_model is None or metadata.get("warning"):
        return None, metadata, [str(metadata.get("warning") or "No replay-policy checkpoint found; action recommendations limited.")]

    features = _policy_features_for_model(
        policy_metadata=metadata,
        public_features=public_features,
        live_features=live_features,
    )
    x = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)
    with torch.no_grad():
        policy_logits, _ = policy_model(x)
        probs = torch.softmax(policy_logits.squeeze(0), dim=0).detach().cpu().numpy()
    return probs, metadata, []


def _switch_proxy_private_state(private_state: Dict[str, Any], action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if str(action.get("kind")) != "switch":
        return None
    label = str(action.get("label") or "")
    target_species = label.split(":", 1)[1].strip() if ":" in label else label.strip()
    if not target_species:
        return None

    proxy = deepcopy(private_state)
    team = proxy.get("team") if isinstance(proxy.get("team"), list) else []
    selected = None
    for mon in team:
        if not isinstance(mon, dict):
            continue
        species = str(mon.get("species") or "")
        if species.lower() == target_species.lower():
            selected = mon
            break
    if selected is None:
        return None
    for mon in team:
        if isinstance(mon, dict):
            mon["active"] = False
    selected["active"] = True
    proxy["active_species"] = selected.get("species") or target_species
    proxy["active_moves"] = [
        {"id": str(move).lower().replace(" ", ""), "name": str(move), "pp": 1, "maxpp": 1, "disabled": False}
        for move in selected.get("moves", [])[:4]
        if str(move)
    ]
    return proxy


def _estimate_switch_value(
    *,
    action: Dict[str, Any],
    private_state: Dict[str, Any],
    public_features: np.ndarray,
    opponent_belief: Dict[str, Any],
    trajectory: Dict[str, Any],
    player_side: Optional[str],
    value_model: Optional[torch.nn.Module],
    value_metadata: Dict[str, Any],
    device: torch.device,
) -> Tuple[Optional[float], Optional[str], Dict[str, Any]]:
    if value_model is None or not value_metadata.get("uses_live_private_features"):
        return None, None, {}
    proxy_state = _switch_proxy_private_state(private_state, action)
    if proxy_state is None:
        return None, None, {}
    features, _ = build_live_private_feature_vector(
        public_features=public_features,
        private_state=proxy_state,
        opponent_belief=opponent_belief,
        trajectory=trajectory,
        player_side=player_side,
    )
    x = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)
    with torch.no_grad():
        estimated_value = _model_output_value(value_model(x))
    return estimated_value, "switch_proxy", {"proxy_feature_dim": int(features.shape[0])}


class ActionValueEstimator:
    def __init__(
        self,
        *,
        value_model: Optional[torch.nn.Module],
        value_metadata: Dict[str, Any],
        policy_loader: PolicyLoader,
        action_ranker_model: Optional[ActionRankerMLP],
        action_ranker_metadata: Optional[Dict[str, Any]],
        device: torch.device,
    ) -> None:
        self.value_model = value_model
        self.value_metadata = value_metadata
        self.policy_loader = policy_loader
        self.action_ranker_model = action_ranker_model
        self.action_ranker_metadata = action_ranker_metadata or {}
        self.device = device

    def estimate(
        self,
        *,
        payload: Any,
        legal_action: Dict[str, Any],
        private_state: Dict[str, Any],
        opponent_belief: Dict[str, Any],
        trajectory: Dict[str, Any],
        public_features: np.ndarray,
        live_features: np.ndarray,
        current_value: float,
        policy_probs: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        action_index = int(legal_action.get("index", 0) or 0)
        disabled = bool(legal_action.get("disabled", False))
        policy_prob = (
            float(policy_probs[action_index])
            if policy_probs is not None and 0 <= action_index < len(policy_probs) and not disabled
            else 0.0
        )
        player_side = private_state.get("player_side") if private_state.get("player_side") in ("p1", "p2") else None
        estimated_value, proxy_method, proxy_components = _estimate_switch_value(
            action=legal_action,
            private_state=private_state,
            public_features=public_features,
            opponent_belief=opponent_belief,
            trajectory=trajectory,
            player_side=player_side,
            value_model=self.value_model,
            value_metadata=self.value_metadata,
            device=self.device,
        )
        ranker_score = None
        if self.action_ranker_model is not None:
            state_dim = int(self.action_ranker_metadata.get("state_dim", live_features.shape[0]))
            action_dim = int(self.action_ranker_metadata.get("action_dim", ACTION_FEATURE_DIM))
            state_part = live_features.astype(np.float32)
            if state_part.shape[0] != state_dim:
                state_part = state_part[:state_dim] if state_part.shape[0] > state_dim else np.pad(state_part, (0, state_dim - state_part.shape[0]))
            action_features = build_action_feature_vector(legal_action, private_state).astype(np.float32)
            if action_features.shape[0] != action_dim:
                action_features = action_features[:action_dim] if action_features.shape[0] > action_dim else np.pad(action_features, (0, action_dim - action_features.shape[0]))
            ranker_input = np.concatenate([state_part, action_features]).astype(np.float32)
            x_ranker = torch.from_numpy(ranker_input).to(self.device).unsqueeze(0)
            with torch.no_grad():
                ranker_score = float(self.action_ranker_model(x_ranker).squeeze().detach().cpu().item())

        if ranker_score is not None:
            method = "action_ranker"
        elif proxy_method and policy_probs is not None:
            method = "policy_prior+switch_proxy"
        else:
            method = proxy_method or ("policy_prior" if policy_probs is not None else "rollout_unavailable")
        value_component = 0.0 if estimated_value is None else 0.05 * float(estimated_value)
        score = 0.0 if disabled else float(ranker_score if ranker_score is not None else policy_prob + value_component)
        return {
            "index": action_index,
            "label": str(legal_action.get("label") or f"action:{action_index}"),
            "kind": str(legal_action.get("kind") or "unknown"),
            "disabled": disabled,
            "policy_prob": policy_prob if policy_probs is not None else None,
            "ranker_score": ranker_score,
            "estimated_value": estimated_value,
            "score": score,
            "score_components": {
                "policy_prob": policy_prob if policy_probs is not None else None,
                "ranker_score": ranker_score,
                "current_value": float(current_value),
                "estimated_value_weight": 0.0 if ranker_score is not None else 0.05 if estimated_value is not None else 0.0,
                **proxy_components,
            },
            "method": method,
            "rollout_count": 0,
            "depth": 0,
            "mean_value": estimated_value,
            "std_value": None,
        }


def recommend_actions(
    *,
    payload: Any,
    private_state: Dict[str, Any],
    opponent_belief: Dict[str, Any],
    trajectory: Dict[str, Any],
    public_features: np.ndarray,
    live_features: np.ndarray,
    current_value: float,
    value_model: Optional[torch.nn.Module],
    value_metadata: Dict[str, Any],
    policy_loader: PolicyLoader,
    device: torch.device,
    limit: int = 5,
) -> Dict[str, Any]:
    candidates = legal_action_candidates(payload)
    if not candidates:
        return {
            "top_actions": [],
            "action_recommendation_method": "no_legal_actions",
            "policy_checkpoint_loaded": False,
            "policy_checkpoint_path": None,
            "warnings": ["No legal actions supplied by request."],
        }

    policy_probs, policy_metadata, warnings = _policy_probs(
        policy_loader=policy_loader,
        public_features=public_features,
        live_features=live_features,
        device=device,
    )
    action_ranker_model, action_ranker_metadata = load_action_ranker_once(device=device)
    if action_ranker_model is None and action_ranker_metadata and action_ranker_metadata.get("warning"):
        warnings.append(str(action_ranker_metadata["warning"]))
    estimator = ActionValueEstimator(
        value_model=value_model,
        value_metadata=value_metadata,
        policy_loader=policy_loader,
        action_ranker_model=action_ranker_model,
        action_ranker_metadata=action_ranker_metadata,
        device=device,
    )
    all_rows = [
        estimator.estimate(
            payload=payload,
            legal_action=candidate,
            private_state=private_state,
            opponent_belief=opponent_belief,
            trajectory=trajectory,
            public_features=public_features,
            live_features=live_features,
            current_value=current_value,
            policy_probs=policy_probs,
        )
        for candidate in candidates
    ]

    enabled = [row for row in all_rows if not row.get("disabled")]
    rows = enabled if enabled else all_rows
    ranked = sorted(rows, key=lambda item: item["score"], reverse=True)
    if not enabled:
        warnings.append("All legal actions are marked disabled or forced; returning disabled actions.")
    if policy_probs is None:
        warnings.append("No replay-policy checkpoint found; action recommendations limited.")

    methods = {row["method"] for row in ranked}
    if "action_ranker" in methods:
        recommendation_method = "action_ranker"
    elif "policy_prior+switch_proxy" in methods or "switch_proxy" in methods:
        recommendation_method = "policy_prior+switch_proxy"
    elif policy_probs is not None:
        recommendation_method = "policy_prior"
    else:
        recommendation_method = "rollout_unavailable"

    return {
        "top_actions": ranked[:limit],
        "all_action_estimates": rows,
        "action_recommendation_method": recommendation_method,
        "policy_checkpoint_loaded": policy_probs is not None,
        "policy_checkpoint_path": policy_metadata.get("path"),
        "action_ranker_loaded": action_ranker_model is not None,
        "action_ranker_path": (action_ranker_metadata or {}).get("path"),
        "warnings": sorted(set(warnings)),
    }
