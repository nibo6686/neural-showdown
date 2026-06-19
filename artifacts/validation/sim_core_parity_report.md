# Showdown Parity and Simulator Correctness Audit

Audit date: 2026-06-18

## Summary verdict

Verdict: **partial pass (correctness fixes applied)**.

`sim-core` is genuinely backed by Pokemon Showdown's battle engine and is suitable for seeded Gen 9 singles research smoke tests. Legal choices are derived from authoritative Showdown requests, player views passed the focused hidden-information checks, selected mechanics behaved correctly, and the strict damage healthcheck used `smogon_calc` without fallback.

Exact-stat damage and replay winner preservation are now fixed and regression-tested. It is still not accurate enough to treat public-replay “exact” rollouts as ground truth:

- ordinary public replays lack the seed/private teams/private requests required for exact reproduction
- the fixed codec supports singles only
- the Python damage layer can use a heuristic fallback outside strict mode

Current live evaluation and rollout can be used as a research diagnostic with those limitations visible. It should not be trusted as-is for claims requiring exact replay reproduction or exact damage from request-provided stats.

## Test results

Baseline before changes:

- Python suite: 139 passed
- sim-core suite: 14 passed
- Direct `npm test`: 14 passed

Dedicated parity suite after changes:

- sim-core: 23 passed
- Python sim-core parity: 6 passed
- Replay sanity: 5 saved public replays checked
- Damage healthcheck: 4 cases used `smogon_calc`, including exact stats; no heuristic fallback observed
- Final full repository verification: 149 Python tests passed; 23 sim-core tests passed

The former exact-stat skipped regression and replay winner expected failure now pass as normal tests.

## Coverage

Covered:

- deterministic seeded random-team generation
- normal moves, tera moves, healthy bench switches, faint replacement, forced switch, trapped state, disabled moves, zero PP, tera already used
- request-driven Choice/Encore/Taunt/Disable/Assault Vest restrictions
- own private request fields and opponent hidden-information exclusion
- immunity, effectiveness, Protect, Substitute, priority, Focus Sash
- Stealth Rock, Spikes, Toxic Spikes
- paralysis, poison, toxic, burn, sleep
- boosts, paralysis speed reduction, Choice Scarf, guaranteed critical hit
- burn damage reduction, Choice Band/Specs, weather, terrain, screens, ability and tera modifiers
- RPC/direct Smogon range agreement
- public replay move/switch/damage event parsing

Not exhaustively covered:

- every move, ability, item, field interaction, generation, or format
- doubles/multi-action requests
- exact random-battle set distribution parity across Showdown releases
- exhaustive Illusion, Transform, Revival Blessing, Shed Tail, multi-form, and edge-case protocol handling
- exact public replay reproduction

## Known limitations

- Public replay logs do not include the original PRNG seed or complete private state.
- `sim-core` cannot initialize from exact packed teams through its RPC.
- The action codec consumes only `active[0]`; doubles and multi-action formats are unsupported.
- Team preview is auto-selected with `default`.
- Approximate rollouts infer hidden information and are not Showdown-equivalent branches.
- Non-strict Python damage callers may receive `heuristic_fallback`.
- Simulator dependency changes require a deliberate version update and a fresh parity validation run.
- Switch indices `8-12` represent healthy bench order, not immutable team slots; consumers must use the concrete `choice`.

## High-priority bugs found

### 1. Exact request stats were ignored by damage_estimate — fixed

- Symptom: changing supplied attacker SpA from 50 to 500 and defender SpD from 500 to 50 produces the same range.
- Reproduction:
  - `cd sim-core`
  - run `npm test`; the exact-stat regressions compare substantially different raw stats
- Expected: exact request stats influence the Smogon calculation.
- Fix: exact raw stats now override inferred stats and survive `@smogon/calc` cloning; diagnostic flags identify exact-stat use.
- Impact: live damage diagnostics, action ranking, tactical analysis, and approximate rollout scoring can use incorrect ranges.
- Verification: TypeScript, Python direct-calc, and sim-core RPC regression tests pass without heuristic fallback.

### 2. Replay winner side could be lost after disconnect lines — fixed

- Symptom: `eternity-gen9randombattle-108.log` contains `|win|Eternity_Showdown`, but parsed `winner_side` is `null`.
- Reproduction: run `test_winner_side_survives_post_battle_player_disconnect_lines`.
- Expected: winner side remains `p2`.
- Fix: blank player names are ignored, winner side is captured at `|win|`, and absent winners are explicitly unknown and excluded from datasets.
- Impact: replay labels, value targets, evaluation summaries, and dataset quality.
- Verification: disconnect-before-win, inactive-before-win, post-win disconnect, and no-winner tests pass.

### 3. Core npm dependencies were declared as latest — fixed

- Symptom: reinstalling after lockfile regeneration can change Showdown/calc behavior without an intentional audit.
- Reproduction: inspect `sim-core/package.json`.
- Expected: research-critical engine versions are explicitly pinned.
- Fix: `pokemon-showdown@0.11.10` and `@smogon/calc@0.11.0` are pinned in both package files.
- Impact: irreproducible datasets, rollouts, and parity results.
- Upgrade rule: change versions intentionally and rerun `validate-sim-core`.

## Recommendations

Before trusting evaluation results:

1. Rebuild replay-derived datasets so corrected winner labels are reflected.
2. Rename or gate “exact” rollout so it is available only for local traces with seed, exact generated teams, and complete concrete choices.
3. Fail closed on unsupported non-singles formats.

Before each model training/eval cycle:

- run `.\scripts\run_windows.ps1 -Action test -SimCoreMode native`
- run `.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native`
- require `damage_method=smogon_calc` in strict research runs
- record dependency versions with the experiment artifacts

## Final trust statement

The battle execution path is Showdown-backed, selected singles mechanics are smoke-tested, exact private stats are honored, and winner labels are preserved. The system is reasonable for exploratory seeded Gen 9 singles research. Public replay branching remains approximate because exact public replay reproduction is not supported.
