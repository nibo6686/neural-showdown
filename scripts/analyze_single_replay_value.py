import gzip
import json
from pathlib import Path

import numpy as np
import torch

from neural.build_replay_value_dataset import (
    _apply_event,
    _feature_vector,
    _initial_state,
    _new_recent,
)
from neural.models.policy_value_mlp import PolicyValueMLP

TRAJ_PATH = Path(r".\data\replays\processed\gen9randombattle_single_trajectories.jsonl.gz")
CKPT_PATH = Path(r".\artifacts\checkpoints\gen9randombattle_replay_value.pt")

def load_first_trajectory(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            return json.loads(line)
    raise RuntimeError(f"No trajectories found in {path}")

def load_value_model(ckpt_path, feature_dim):
    ckpt = torch.load(ckpt_path, map_location="cpu")

    state_dict = (
        ckpt.get("model_state_dict")
        or ckpt.get("state_dict")
        or ckpt.get("model")
        or ckpt
    )

    hidden_sizes = (
        ckpt.get("hidden_sizes")
        or ckpt.get("model_config", {}).get("hidden_sizes")
        or ckpt.get("config", {}).get("hidden_sizes")
        or [128, 128]
    )

    model = PolicyValueMLP(
        input_size=feature_dim,
        hidden_sizes=hidden_sizes,
        action_size=13,
    )

    model.load_state_dict(state_dict, strict=False)
    model.eval()
    return model

def value_of(model, features):
    x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        out = model(x)

    if isinstance(out, tuple):
        value = out[1]
    elif isinstance(out, dict):
        value = out.get("value") or out.get("values")
    else:
        value = out

    value = float(value.reshape(-1)[0].item())
    win_prob = (value + 1.0) / 2.0
    return value, win_prob

def action_label(event):
    if event.get("type") == "move":
        return f"{event.get('side')} {event.get('actor')} used {event.get('move')}"
    if event.get("type") == "switch":
        return f"{event.get('side')} switched to {event.get('details')}"
    return str(event)

traj = load_first_trajectory(TRAJ_PATH)
state = _initial_state(traj)

# Get feature dim from the first state.
features0 = _feature_vector(state, _new_recent(), 0)
model = load_value_model(CKPT_PATH, len(features0))

print("=" * 100)
print(f"Replay: {traj.get('replay_id')}")
print(f"Players: {traj.get('players')}")
print(f"Winner side: {traj.get('winner_side')}")
print(f"Feature dim: {len(features0)}")
print("=" * 100)

last_turn = None

for turn_record in sorted(traj.get("turns", []), key=lambda t: int(t.get("turn", 0) or 0)):
    turn = int(turn_record.get("turn", 0) or 0)
    recent = _new_recent()

    if turn != last_turn:
        print()
        print(f"TURN {turn}")
        print("-" * 100)
        last_turn = turn

    for event in turn_record.get("events", []):
        if not isinstance(event, dict):
            continue

        event_type = event.get("type")

        # Print model value before each visible player action.
        if event_type in ("move", "switch"):
            features = _feature_vector(state, recent, turn)
            value, win_prob = value_of(model, features)

            print(f"Before: {action_label(event)}")
            print(f"  p1 value={value:+.3f} | p1 win_prob={win_prob:.1%}")

        _apply_event(state, recent, event)

    # End-of-turn value
    features = _feature_vector(state, recent, turn)
    value, win_prob = value_of(model, features)
    print(f"End of turn {turn}: p1 value={value:+.3f} | p1 win_prob={win_prob:.1%}")
