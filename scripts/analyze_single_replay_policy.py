import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from neural.build_replay_value_dataset import (
    _apply_event,
    _feature_vector,
    _initial_state,
    _load_trajectories,
    _new_recent,
)
from neural.models.policy_value_mlp import PolicyValueMLP

def norm_name(s):
    if not s:
        return ""
    return str(s).split(",")[0].strip()

def actor_species(actor):
    if not actor or ": " not in actor:
        return ""
    return norm_name(actor.split(": ", 1)[1])

def load_model(path, feature_dim):
    ckpt = torch.load(path, map_location="cpu")
    state = ckpt.get("model_state_dict") or ckpt.get("state_dict") or ckpt
    hidden = ckpt.get("hidden_sizes") or [128, 128]
    model = PolicyValueMLP(input_size=feature_dim, hidden_sizes=hidden, action_size=13)
    model.load_state_dict(state, strict=False)
    model.eval()
    return model

def forward_parts(model, features):
    x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        out = model(x)
    if isinstance(out, tuple):
        logits, value = out[0], out[1]
    elif isinstance(out, dict):
        logits = out.get("policy_logits") or out.get("logits") or out.get("policy")
        value = out.get("value") or out.get("values")
    else:
        raise RuntimeError(f"Unexpected model output type: {type(out)}")
    probs = torch.softmax(logits, dim=-1).reshape(-1)
    value = float(value.reshape(-1)[0].item())
    return probs, value

def update_public_tracker(event, active, roster, moves):
    side = event.get("side")
    if side not in ("p1", "p2"):
        return

    if event.get("type") == "switch":
        mon = norm_name(event.get("details"))
        if mon:
            active[side] = mon
            if mon not in roster[side]:
                roster[side].append(mon)

    elif event.get("type") == "move":
        mon = actor_species(event.get("actor"))
        move = event.get("move")
        if mon:
            active[side] = mon
            if mon not in roster[side]:
                roster[side].append(mon)
        if mon and move and move not in moves[side][mon]:
            moves[side][mon].append(move)

    elif event.get("type") == "faint":
        target = actor_species(event.get("target"))
        if target and active.get(side) == target:
            active[side] = None

def actual_label(event):
    if event.get("type") == "move":
        return f"move:{event.get('move')}"
    if event.get("type") == "switch":
        return f"switch:{event.get('details')}"
    return str(event.get("type"))

def index_label(idx, side, active, roster, moves):
    # IMPORTANT: this follows the current public replay mapper convention:
    # 0-3 = move slots, 4-9 = switch/team slots, 10-12 = currently unused/other.
    if 0 <= idx <= 3:
        mon = active.get(side)
        known = moves[side].get(mon, []) if mon else []
        if idx < len(known):
            return f"move slot {idx + 1}: {known[idx]}"
        return f"move slot {idx + 1}: unknown/unrevealed"

    if 4 <= idx <= 9:
        slot = idx - 4
        if slot < len(roster[side]):
            return f"switch slot {slot}: {roster[side][slot]}"
        return f"switch slot {slot}: unknown"

    return f"action index {idx}: unknown/unused in replay mapper"

parser = argparse.ArgumentParser()
parser.add_argument("--side", default="p1", choices=["p1", "p2"])
parser.add_argument("--trajectories", default=r".\data\replays\processed\gen9randombattle_single_trajectories.jsonl.gz")
parser.add_argument("--checkpoint", default=r".\artifacts\checkpoints\gen9randombattle_replay_policy.pt")
parser.add_argument("--topk", type=int, default=5)
args = parser.parse_args()

trajectories = _load_trajectories(Path(args.trajectories))
traj = trajectories[0]
state = _initial_state(traj)
feature0 = _feature_vector(state, _new_recent(), 0)
model = load_model(Path(args.checkpoint), len(feature0))

active = {"p1": None, "p2": None}
roster = {"p1": [], "p2": []}
moves = {"p1": defaultdict(list), "p2": defaultdict(list)}

print("=" * 100)
print(f"Replay: {traj.get('replay_id')}")
print(f"Players: {traj.get('players')}")
print(f"Showing model suggestions for side={args.side} player={traj.get('players', {}).get(args.side)}")
print("Note: move names are only shown after they are known/revealed in the replay.")
print("=" * 100)

for turn_record in sorted(traj.get("turns", []), key=lambda t: int(t.get("turn", 0) or 0)):
    turn = int(turn_record.get("turn", 0) or 0)
    recent = _new_recent()

    printed_turn = False

    for event in turn_record.get("events", []):
        if not isinstance(event, dict):
            continue

        if event.get("type") in ("move", "switch") and event.get("side") == args.side:
            if not printed_turn:
                print()
                print(f"TURN {turn}")
                print("-" * 100)
                printed_turn = True

            features = _feature_vector(state, recent, turn)
            probs, value = forward_parts(model, features)

            top = torch.topk(probs, k=min(args.topk, len(probs)))
            print(f"Actual: {actual_label(event)}")
            print(f"Model value for p1: {value:+.3f} | p1_win_prob={(value + 1) / 2:.1%}")
            print("Model top actions:")
            for rank, (idx, prob) in enumerate(zip(top.indices.tolist(), top.values.tolist()), start=1):
                print(f"  {rank}. index={idx:2d} prob={prob:.1%}  {index_label(idx, args.side, active, roster, moves)}")

        _apply_event(state, recent, event)
        update_public_tracker(event, active, roster, moves)
