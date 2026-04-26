import gzip
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from neural.models.policy_value_mlp import PolicyValueMLP

DATASET = Path(r".\data\replays\processed\gen9randombattle_public_policy.jsonl.gz")
OUT = Path(r".\artifacts\checkpoints\gen9randombattle_replay_policy.pt")
OUT.parent.mkdir(parents=True, exist_ok=True)

xs = []
ys = []
values = []

with gzip.open(DATASET, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        idx = r.get("mapped_action_index")
        ctx = (r.get("public_context") or {}).get("feature_values")
        if idx is None or ctx is None:
            continue
        if not (0 <= int(idx) < 13):
            continue
        xs.append(ctx)
        ys.append(int(idx))
        values.append(float(r.get("final_result", 0.0)))

X = torch.tensor(np.asarray(xs, dtype=np.float32))
y = torch.tensor(np.asarray(ys, dtype=np.int64))
v = torch.tensor(np.asarray(values, dtype=np.float32))

n = len(X)
perm = torch.randperm(n)
split = int(n * 0.9)
train_idx = perm[:split]
val_idx = perm[split:]

train_loader = DataLoader(
    TensorDataset(X[train_idx], y[train_idx], v[train_idx]),
    batch_size=256,
    shuffle=True,
)
val_loader = DataLoader(
    TensorDataset(X[val_idx], y[val_idx], v[val_idx]),
    batch_size=512,
    shuffle=False,
)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = PolicyValueMLP(input_size=X.shape[1], hidden_sizes=[128, 128], action_size=13).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)

def forward_parts(model, xb):
    out = model(xb)
    if isinstance(out, tuple):
        return out[0], out[1].reshape(-1)
    if isinstance(out, dict):
        logits = out.get("policy_logits") or out.get("logits") or out.get("policy")
        value = out.get("value") or out.get("values")
        return logits, value.reshape(-1)
    raise RuntimeError(f"Unexpected model output type: {type(out)}")

print(f"train-replay-policy start examples={n} train={len(train_idx)} val={len(val_idx)} feature_dim={X.shape[1]} device={device}")

for epoch in range(1, 9):
    model.train()
    total_loss = total_policy = total_value = total_correct = total_seen = 0

    for xb, yb, vb in train_loader:
        xb, yb, vb = xb.to(device), yb.to(device), vb.to(device)

        logits, pred_v = forward_parts(model, xb)
        policy_loss = F.cross_entropy(logits, yb)
        value_loss = F.mse_loss(pred_v, vb)
        loss = policy_loss + 0.25 * value_loss

        opt.zero_grad()
        loss.backward()
        opt.step()

        total_loss += loss.item() * len(xb)
        total_policy += policy_loss.item() * len(xb)
        total_value += value_loss.item() * len(xb)
        total_correct += (logits.argmax(dim=-1) == yb).sum().item()
        total_seen += len(xb)

    model.eval()
    val_correct = val_seen = 0
    val_loss = 0
    with torch.no_grad():
        for xb, yb, vb in val_loader:
            xb, yb, vb = xb.to(device), yb.to(device), vb.to(device)
            logits, pred_v = forward_parts(model, xb)
            loss = F.cross_entropy(logits, yb) + 0.25 * F.mse_loss(pred_v, vb)
            val_loss += loss.item() * len(xb)
            val_correct += (logits.argmax(dim=-1) == yb).sum().item()
            val_seen += len(xb)

    print(
        f"epoch={epoch} "
        f"loss={total_loss/total_seen:.4f} "
        f"policy={total_policy/total_seen:.4f} "
        f"value={total_value/total_seen:.4f} "
        f"train_acc={total_correct/total_seen:.3f} "
        f"val_loss={val_loss/val_seen:.4f} "
        f"val_acc={val_correct/val_seen:.3f}"
    )

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "input_size": int(X.shape[1]),
        "hidden_sizes": [128, 128],
        "action_size": 13,
        "source": "public_replay_policy_31d",
    },
    OUT,
)
print(f"saved {OUT}")
