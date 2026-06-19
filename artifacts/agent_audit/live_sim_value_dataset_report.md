# Live/Sim Value Dataset Report (Part B)

Generated: 2026-06-18T18:09:25
Output: `C:\Users\cloud\Downloads\neural\final\data\value\gen9randombattle_live_sim_value_v1.npz`

## Generation

- Feature version: live-private-belief-v2
- Feature dimension: 115
- Label definition: discounted_terminal_return(perspective_final_result, turns_to_end, gamma); bounded [-1,1]
- Gamma: 0.97
- Generation mode: live-style seeded sim-core (no exact hidden opponent info in features)
- Games requested/used: 40 / 40
- Controller matchups: {'heuristic': 20, 'heuristic/random': 20}
- Wall time: 10.4s

## States

- Total states: 2053
- p1 / p2 examples: 991 / 1062
- win / loss / tie examples: 986 / 1067 / 0

## Labels

- mean / std: -0.0290 / 0.7404
- min / max: -1.0000 / 1.0000

## Skipped states

- non_actionable_request: 319
