from typing import Any, Optional, List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
try:
    from neural.build_replay_value_dataset import (
        _initial_state,
        _new_recent,
        _apply_event,
        _feature_vector,
        FEATURE_VERSION,
        FEATURE_NAMES,
    )
except ImportError:
    from trainer.src.neural.build_replay_value_dataset import (
        _initial_state,
        _new_recent,
        _apply_event,
        _feature_vector,
        FEATURE_VERSION,
        FEATURE_NAMES,
    )

class LegalAction(BaseModel):
    kind: str
    label: str
    slot: Optional[int] = None
    disabled: bool = False


class EvalRequest(BaseModel):
    room_id: str
    url: str
    player: Optional[str] = None
    log: List[str] = Field(default_factory=list)
    request: Optional[Dict[str, Any]] = None
    legal_actions: List[LegalAction] = Field(default_factory=list)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://play.pokemonshowdown.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from typing import Dict, Any, List
import torch
import numpy as np

# Adjust this import if your model path is different
try:
    from neural.models.policy_value_mlp import PolicyValueMLP
except ImportError:
    from trainer.src.neural.models.policy_value_mlp import PolicyValueMLP


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

from pathlib import Path

MODEL_PATH = Path("artifacts/checkpoints/gen9randombattle_replay_value.pt")
INPUT_SIZE = 31
HIDDEN_SIZES = [128, 128]
ACTION_SIZE = 13                       # your model seemed to use 13 actions earlier

_model = None


def load_model_once():
    global _model

    if _model is not None:
        return _model

    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)

    if isinstance(checkpoint, dict):
        state_dict = (
            checkpoint.get("model_state_dict")
            or checkpoint.get("state_dict")
            or checkpoint.get("model")
            or checkpoint
        )
        hidden_sizes = (
            checkpoint.get("hidden_sizes")
            or checkpoint.get("model_config", {}).get("hidden_sizes")
            or checkpoint.get("config", {}).get("hidden_sizes")
            or HIDDEN_SIZES
        )
    else:
        state_dict = checkpoint
        hidden_sizes = HIDDEN_SIZES

    model = PolicyValueMLP(
        input_size=INPUT_SIZE,
        hidden_sizes=hidden_sizes,
        action_size=ACTION_SIZE,
    )

    model.load_state_dict(state_dict, strict=False)
    model.to(DEVICE)
    model.eval()

    _model = model
    return _model

def _side_from_actor(actor: str) -> Optional[str]:
    if not actor or len(actor) < 2:
        return None
    if actor.startswith("p1"):
        return "p1"
    if actor.startswith("p2"):
        return "p2"
    return None

def _event_from_protocol_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Convert a Showdown protocol line into the same approximate event schema used by
    parse_replay_logs.py / build_replay_value_dataset.py.

    This is intentionally descriptive only; it does not hardcode battle rules.
    """
    if not line or not line.startswith("|"):
        return None

    parts = line.split("|")
    if len(parts) < 2:
        return None

    tag = parts[1]
    raw = line

    if tag == "turn" and len(parts) >= 3:
        try:
            return {"type": "turn", "turn": int(parts[2]), "raw": raw}
        except Exception:
            return {"type": "turn", "turn": 0, "raw": raw}

    if tag == "player" and len(parts) >= 4:
        return {
            "type": "player",
            "side": parts[2],
            "player": parts[3],
            "raw": raw,
        }

    if tag == "switch" and len(parts) >= 5:
        actor = parts[2]
        return {
            "type": "switch",
            "side": _side_from_actor(actor),
            "actor": actor,
            "details": parts[3],
            "hp": parts[4],
            "raw": raw,
        }

    if tag == "drag" and len(parts) >= 5:
        actor = parts[2]
        return {
            "type": "switch",
            "side": _side_from_actor(actor),
            "actor": actor,
            "details": parts[3],
            "hp": parts[4],
            "raw": raw,
        }

    if tag == "replace" and len(parts) >= 5:
        actor = parts[2]
        return {
            "type": "replace",
            "side": _side_from_actor(actor),
            "actor": actor,
            "details": parts[3],
            "hp": parts[4],
            "raw": raw,
        }

    if tag == "move" and len(parts) >= 5:
        actor = parts[2]
        return {
            "type": "move",
            "side": _side_from_actor(actor),
            "actor": actor,
            "move": parts[3],
            "target": parts[4],
            "raw": raw,
        }

    if tag == "faint" and len(parts) >= 3:
        target = parts[2]
        return {
            "type": "faint",
            "side": _side_from_actor(target),
            "target": target,
            "raw": raw,
        }

    # Minor events start with tags like |-damage|, |-heal|, |-status|
    if tag.startswith("-"):
        event_type = tag[1:]

        if event_type in ("damage", "heal") and len(parts) >= 4:
            target = parts[2]
            return {
                "type": event_type,
                "side": _side_from_actor(target),
                "target": target,
                "hp": parts[3],
                "raw": raw,
            }

        if event_type == "status" and len(parts) >= 4:
            target = parts[2]
            return {
                "type": "status",
                "side": _side_from_actor(target),
                "target": target,
                "status": parts[3],
                "raw": raw,
            }

        if event_type in ("boost", "unboost") and len(parts) >= 5:
            target = parts[2]
            return {
                "type": event_type,
                "side": _side_from_actor(target),
                "target": target,
                "stat": parts[3],
                "amount": parts[4],
                "raw": raw,
            }

        if event_type in ("supereffective", "resisted", "immune") and len(parts) >= 3:
            target = parts[2]
            return {
                "type": event_type,
                "side": _side_from_actor(target),
                "target": target,
                "raw": raw,
            }

        if event_type == "terastallize" and len(parts) >= 4:
            target = parts[2]
            return {
                "type": "terastallize",
                "side": _side_from_actor(target),
                "target": target,
                "tera_type": parts[3],
                "raw": raw,
            }

        if event_type in ("sidestart", "sideend") and len(parts) >= 4:
            # Example: |-sidestart|p1: name|move: Stealth Rock
            side_field = parts[2]
            side = "p1" if side_field.startswith("p1") else "p2" if side_field.startswith("p2") else None
            return {
                "type": event_type,
                "side": side,
                "condition": parts[3],
                "raw": raw,
            }

        return {"type": event_type, "raw": raw}

    if tag == "win" and len(parts) >= 3:
        return {"type": "win", "winner": parts[2], "raw": raw}

    return None


def _trajectory_from_live_payload(payload: EvalRequest) -> Dict[str, Any]:
    players: Dict[str, str] = {}

    for line in payload.log:
        event = _event_from_protocol_line(line)
        if event and event.get("type") == "player":
            side = event.get("side")
            player = event.get("player")
            if side in ("p1", "p2") and player:
                players[side] = player

    return {
        "replay_id": payload.room_id,
        "format": "gen9randombattle",
        "players": players,
        "winner_side": None,
        "turns": [],
    }

def build_features_from_payload(payload: EvalRequest) -> np.ndarray:
    """
    Build the exact 31D public replay event feature vector used by
    build_replay_value_dataset.py.

    This replaces the old placeholder feature vector.
    """
    trajectory = _trajectory_from_live_payload(payload)
    state = _initial_state(trajectory)
    recent = _new_recent()
    turn = 0

    for line in payload.log:
        event = _event_from_protocol_line(line)
        if not event:
            continue

        if event.get("type") == "turn":
            turn = int(event.get("turn", turn) or turn)
            recent = _new_recent()
            continue

        _apply_event(state, recent, event)

    features = _feature_vector(state, recent, turn)

    if features.shape[0] != INPUT_SIZE:
        raise ValueError(
            f"Feature size mismatch: got {features.shape[0]}, expected {INPUT_SIZE}. "
            f"Feature version={FEATURE_VERSION}"
        )

    return features.astype(np.float32)

def action_index_to_label(index: int, legal_actions: List[LegalAction]) -> str:
    """
    Maps model action index back to the actual Showdown action label.
    This assumes index 0-3 are moves and later indexes are switches.
    Adjust this if your training used a different action mapping.
    """

    if index < len(legal_actions):
        return legal_actions[index].label

    return "Unknown action {}".format(index)


def evaluate_with_model(payload: EvalRequest) -> Dict[str, Any]:
    model = load_model_once()

    features = build_features_from_payload(payload)
    x = torch.tensor(features, dtype=torch.float32, device=DEVICE).unsqueeze(0)

    with torch.no_grad():
        output = model(x)

    # Adjust this depending on your model's forward() return format.
    # Common possibilities:
    # 1. output = (policy_logits, value)
    # 2. output = {"policy": ..., "value": ...}
    # 3. output = just value
    if isinstance(output, tuple):
        policy_logits, value_tensor = output
    elif isinstance(output, dict):
        policy_logits = output.get("policy")
        value_tensor = output.get("value")
    else:
        policy_logits = None
        value_tensor = output

    value = float(value_tensor.squeeze().cpu().item())

    # Convert value from [-1, 1] to win probability.
    p1_win_prob = max(0.0, min(1.0, (value + 1.0) / 2.0))
    p2_win_prob = 1.0 - p1_win_prob

    top_actions = []
    policy_logits = None

    if policy_logits is not None and len(payload.legal_actions) > 0:
        probs = torch.softmax(policy_logits.squeeze(), dim=0).cpu().numpy()

        legal_count = min(len(payload.legal_actions), len(probs))
        legal_probs = probs[:legal_count]

        ranked = sorted(
            range(legal_count),
            key=lambda i: legal_probs[i],
            reverse=True,
        )

        for i in ranked[:4]:
            top_actions.append({
                "label": action_index_to_label(i, payload.legal_actions),
                "prob": float(legal_probs[i]),
            })

    return {
        "p1_win_prob": p1_win_prob,
        "p2_win_prob": p2_win_prob,
        "value": value,
        "top_actions": top_actions,
        "warning": "Using 31D public-replay value model; policy/top_actions are not reliable unless a replay-policy checkpoint is loaded.",
    }


@app.post("/evaluate")
def evaluate(payload: EvalRequest):
    return evaluate_with_model(payload)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)