# Live/Sim Bounded Value Training Report (Part C)

Generated: 2026-06-18T18:10:49
Checkpoint: `C:\Users\cloud\Downloads\neural\final\artifacts\checkpoints\gen9randombattle_live_sim_value_v1.pt`
Dataset: `C:\Users\cloud\Downloads\neural\final\data\value\gen9randombattle_live_sim_value_v1.npz`

## Model

- Type: live-sim-bounded-value (tanh output, MLP)
- Feature version / dim: live-private-belief-v2 / 115
- Bounded output: true (tanh, labels in [-1,1])
- Device: cuda, epochs: 40
- Examples (train/val): 2053 (1847/206)

## Metrics

- Final train Huber: 0.0232
- Validation MSE: 0.1405
- Constant-baseline MSE: 0.5508
- Improvement over baseline: 74.4898%
- Validation sign accuracy: 0.8641
- Prediction mean/std: -0.0576 / 0.7145
- Prediction min/max: -0.9992 / 0.9991
