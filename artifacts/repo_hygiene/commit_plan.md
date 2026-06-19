# Commit Checkpoint Plan

**Date:** 2026-06-18
**Status:** PLAN ONLY — do not commit until the user explicitly approves.
**Base:** `de49cc0`

## Recommendation

**Do one large checkpoint commit** (optionally split into exactly two: code+reports, then
repo-hygiene). A fine-grained 10-commit history is **not safely separable** here because
several files each span multiple logical sections:

- `trainer/src/neural/two_ply_branch.py` contains the **exact two-ply**, the
  **randbats-belief**, and the **three-particle aggregation** logic together (sections 6, 7, 8).
- `trainer/src/neural/agent_audit.py` orchestrates every agent (one-turn, two-ply, belief,
  particles, value, rollout) in one module (sections 4–8).
- `trainer/src/neural/sim_branch_evaluator.py` (rollout plumbing, section 3) is imported by
  `live_action_recommender.py`, `live_eval_server.py`, and analysis modules (section 1/9).

Splitting these would require partial-line staging (`git add -p`) that risks committing a
non-building intermediate state. The whole tree builds and passes tests **together** (177
Python + 26 sim-core), so commit it as one coherent, verified checkpoint.

The logical sections below are the **changelog structure for the commit message**, not
separate commits.

## Pre-commit verification (run before committing)

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native   # {"ok": true}
.\scripts\run_windows.ps1 -Action test -SimCoreMode native                # 177 + 26 pass
git status --short                                                        # no stray JSON
```

All three already pass as of this checkpoint.

## Logical sections (changelog grouping)

1. **Simulator correctness fixes** — exact-stat damage through TS/Python/RPC, dependency
   pins. `sim-core/src/damage_calc.ts`, `env_manager.ts`, `server.ts`, `types.ts`;
   `sim-core/package.json`, `package-lock.json`; `trainer/src/neural/damage_engine.py`,
   `env_client.py`, `live_private_state.py`, `parse_replay_logs.py`,
   `build_replay_policy_dataset.py`; tests `damage_calc.test.ts`, `action_codec.test.ts`,
   `state_extractor.test.ts`, `test_damage_engine.py`, `test_public_replays.py`.
2. **Validation / parity tooling** — `trainer/src/neural/validate_sim_core.py`,
   `trainer/tests/test_sim_core_parity.py`, `sim-core/tests/mechanics_parity.test.ts`,
   `artifacts/validation/*.md`.
3. **Rollout damage plumbing** — `trainer/src/neural/sim_branch_evaluator.py`,
   `live_action_recommender.py`; `artifacts/agent_audit/rollout_damage_plumbing_report.md`.
4. **One-turn branch evaluator** — `trainer/src/neural/one_turn_branch.py`,
   `trainer/tests/test_one_turn_branch.py`; `one_turn_branch_design.md`, `_report.md`.
5. **Live/sim value-head experiments** — `build_live_sim_value_dataset.py`,
   `train_live_sim_value.py`, `models/value_mlp.py`; `live_sim_value_*.md`,
   `value_model_*.md`, `state_scorer_*.md`.
6. **Exact two-ply branch evaluator** — `trainer/src/neural/two_ply_branch.py` (exact path),
   `trainer/tests/test_two_ply_branch.py`; `two_ply_branch_design.md`, `_report.md`.
7. **Belief branch evaluator** — `sim-core/src/belief_fork.ts`,
   `sim-core/tests/belief_fork.test.ts`, `two_ply_branch.py` (belief path),
   `trainer/tests/test_belief_branch.py`; `randbats_belief_branch_design.md`, `_report.md`.
8. **Belief-particle aggregation** — `two_ply_branch.py` (3-particle path), `agent_audit.py`;
   `belief_particles_design.md`, `_report.md`.
9. **Docs / reports / tests / harness** — `README.md`, `docs/architecture.md`,
   `scripts/run_windows.ps1`, `agent_audit.py`, `build_agent_audit_reports.py`,
   `run_agent_tournament.py`, `test_agent_audit.py`, `recommendations.md`,
   `agent_inventory.md`, `agent_ablation_report.md`, `tactical_failure_report.md`,
   `live_eval_sanity.md`, `CLAUDE.md`, `artifacts/environment/*`.
10. **Repo hygiene** — `.gitignore` (ignore generated agent-audit/validation JSON),
    `artifacts/repo_hygiene/git_status_audit.md`, `artifacts/repo_hygiene/commit_plan.md`.

## Option A — single checkpoint commit (recommended)

```text
Validate sim-core and add branch-search research agents

- fix exact-stat damage and replay winner parsing; pin pokemon-showdown@0.11.10
  and @smogon/calc@0.11.0
- add simulator parity validation gate and environment fingerprint checks
- add rollout damage plumbing fixes (no heuristic fallbacks)
- add one-turn material and exact two-ply branch evaluators
- add randbats belief branching and deterministic three-particle aggregation
- add live/sim bounded value-head experiments (diagnostic only; live defaults
  unchanged)
- add agent-audit reports, designs, and regression tests (177 py + 26 sim-core)
- clean generated per-battle JSON from git status via .gitignore

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

Staging:

```powershell
git add -A          # 45 new + 21 modified files; generated JSON already gitignored
git commit          # paste message above
```

## Option B — two-commit split (only safe separation)

If you prefer a smaller-footprint history, the one clean cut is **tooling/hygiene vs.
research code**, because hygiene touches no source:

```text
Commit 1 — "Add branch-search research agents and validation tooling"
  everything except .gitignore + artifacts/repo_hygiene/*

Commit 2 — "Repo hygiene: ignore generated agent-audit/validation JSON dumps"
  .gitignore, artifacts/repo_hygiene/git_status_audit.md, commit_plan.md
```

```powershell
git add .gitignore artifacts/repo_hygiene
git stash --keep-index            # set aside everything else
git commit -m "Repo hygiene: ignore generated agent-audit/validation JSON dumps ..."
git stash pop
git add -A
git commit                        # research-code message
```

(Do hygiene *first* if you want the ignore rules in history before the code, or reverse the
order — either is fine since they don't overlap.)

## Open decisions before committing

- **`CLAUDE.md`** at repo root: confirm you want it tracked (duplicate of the parent-dir copy).
- **`sim_core_validation_results.json`**: currently ignored; force-add if you want a
  committed machine-readable parity snapshot.
- **`.gitignore` pre-existing duplicates**: left untouched (surgical); de-dupe later if desired.
- **`.gitattributes`**: not added; consider pinning line endings if others clone on non-Windows.
