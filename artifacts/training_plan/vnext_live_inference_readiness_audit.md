# vNext Live Inference Readiness Audit

## Purpose and Scope

Determine what must be true before the v7/v5 action-rank checkpoint can be safely
tested in private Pokémon Showdown matches. Read-only audit: no training, no
checkpoint promotion, no live-default change, **no matches run**. A read-only
tool (`trainer/src/neural/audit_vnext_live_inference_readiness.py`) loads the
checkpoint, validates schema/fingerprints, runs a controlled scorer, checks
candidate→command serialization, cross-checks parity with the offline evaluator,
measures scoring latency, and scans the live code for v2/v3 assumptions.

## Checkpoint / Config Inspected

- Checkpoint: `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v5_rank_only/model.best.pt`
- Config: `configs/diagnostic_1000_action_rank_v7_v5.rank_only.windows.json`
- Model: `shared_state_action_diagnostic_mlp`, 218,786 params; rank head only trained.

## Schema / Fingerprint Validation (Q1)

**PASS** under strict validation (`require_fingerprints=True`):

- state `live-private-belief-v7` (3208D) — version, dim, and `state_feature_names_sha256` all `validated`
- action `legal-action-v5` (318D) — version, dim, and `action_feature_names_sha256` all `validated`
- `fingerprints_complete = true`

So **the v7/v5 checkpoint can be loaded in a controlled inference path with strict
schema/fingerprint validation** (audit Q1: yes). A legacy checkpoint lacking
fingerprints is rejected (tested).

## Current Live Defaults (and whether they changed)

Unchanged. Live defaults remain **state `live-private-belief-v2`, action
`legal-action-v3`**, served by `ActionRankerMLP`/`ActionValueRankerMLP` from
`artifacts/checkpoints/`. This audit changed **no** live defaults and promoted
**no** checkpoints.

## Live Path Assumptions Found (Q2)

Scan of `live_action_recommender.py` and `live_eval_server.py`:

- **Zero** references to any vNext marker (`VNextDiagnosticMLP`, `legal-action-v5`,
  `live-private-belief-v7`, `build_action_feature_vector_v5`, `resolve_action_impact`).
- `live_action_recommender.py`: `ActionRankerMLP` ×5, `build_action_feature_vector(`
  (v3) ×1, `np.pad` ×2.

The live scorer (`ActionValueEstimator.estimate`) concatenates `[state || action]`
into one vector for a single `ActionRankerMLP`, builds **v3** action features via
`build_action_feature_vector`, uses **v2** live state, and **pad/truncates** both
to the checkpoint's declared dims. This is architecturally and schema-incompatible
with the vNext `VNextDiagnosticMLP` (separate state/action encoders + rank trunk).
**The current live path cannot load or run the v7/v5 checkpoint** (audit Q2: yes,
it assumes v2/v3 dims and legacy checkpoint structure).

## Offline Scorer vs Proposed Live Scorer Parity (Q5)

A controlled scorer using the exact model calls a live decision would use
(`encode_states` → `rank_from_embeddings`) reproduces the offline evaluator
**bit-for-bit**: audit-recomputed validation top-1 `0.4625833` == evaluator top-1
`0.4625833` over all 7,951 groups (`top1_match = true`). Scoring is deterministic
across repeated calls. So the *scoring* step is portable; the gap is entirely in
*feature generation and candidate generation* upstream of scoring.

## Live State Feature Generation (Q3)

Not ready. The live path builds **v2** state via `build_live_private_feature_vector`
(default version). It does **not** produce `live-private-belief-v7` (3208D). The
v7 builder exists (`feature_version=FEATURE_VERSION_V7`) and is what training used,
but the live path does not call it. Until the live decision path emits v7 state in
the exact trained order, live features will not match the checkpoint.

## Live Legal-Action Feature Generation (Q4)

Not ready. The live scorer builds **v3** action features (`build_action_feature_vector`)
without per-candidate `resolve_action_impact`. The trained schema is
`legal-action-v5` (318D), whose impact block (expected damage, KO chance, resolved
next-state) requires a sim-core damage call per candidate. The live path does not
compute these, so live action features cannot match training schema/order without
new wiring.

## Legal Candidate Parity (Q5, candidate level)

Live candidate generation (`legal_action_candidates`) is a **different** generator
from training. Training/offline used `_legal_actions_from_private_state` (rich
reconstructed candidates feeding v5 featurization). Live parses the Showdown
request payload (`request.active.moves`, `request.side.pokemon`, or
`payload.legal_actions`) into `{index, kind, label, slot, disabled}`. These must be
reconciled so the live candidate set matches what the model was trained to score.

## Tera Candidate / Command Findings (Q6)

**Major gap.** Live `legal_action_candidates` emits only `kind="move"` and
`kind="switch"` — it generates **no `move_tera` candidates**. The live code only
*observes* opponent `-terastallize` from protocol; it never produces an own-Tera
action. So Tera cannot be scored or selected live today. The training schema and
dataset distinguish `move` vs `move_tera` (with `is_tera_action`, `can_tera`,
`cmd_tera_move` features), and the audit's command contract maps Tera to a distinct
choice string (`move <slot> terastallize`) verified distinct from the plain move.
(Note: the model itself under-ranks Tera — validation Tera top-1 0.178 — so even
once Tera candidates are generated, Tera selection quality is a known weakness.)

## Switch Candidate / Command Findings (Q7)

Switches are generated live (`_request_switches` from `request.side.pokemon`, with
`forceSwitch`/`trapped` handling) and map to a `switch <slot>` choice. The audit's
controlled scorer selected switches in 28/300 sampled groups and serialized them
cleanly. Switch *representation* is adequate to serialize; switch *candidate
features* must still be produced under v5 (Q4) and the slot indexing reconciled
with the live payload. Model switch quality is moderate (validation switch top-1
0.255).

## Legal-Action Masking (Q8)

In the dataset, only legal candidates are materialized (unavailable/disabled moves
and illegal switches are excluded upstream), so the trained model never sees
illegal actions. Live, `legal_action_candidates` marks `disabled` (PP-empty,
disabled, trapped) and the legacy scorer forces `score=0.0` for disabled actions.
A vNext live path must enforce the same: never emit or select a masked candidate.
This is a contract to re-implement in the new path, not something the checkpoint
guarantees by itself.

## Command Serialization (Q9)

The audit defines the contract a live serializer must honor: `move`,
`move_tera → "move <slot> terastallize"`, `switch → "switch <slot>"`. All selected
candidates in the sample serialized to a valid, non-empty command and Tera was
distinct from the plain move. The runner sends a per-side `choice` string to
sim-core (`runner.py`, with `"default"` fallback), so the new path must convert the
selected candidate into that exact choice string (slot indexing reconciled with the
live request payload).

## Fallback / Error Handling (Q10)

- Today: missing checkpoint → `load_action_ranker_once` returns a warning and the
  recommender falls back to policy-prior / switch-proxy scoring; the runner uses
  `"default"` when no action is chosen. Schema mismatches are silently absorbed by
  pad/truncate (a risk, not a safe failure).
- For a vNext live path, the safe design is the opposite: **fail closed**. If schema/
  fingerprint validation, v7/v5 feature generation, scoring, or command
  serialization fails, do not silently reshape — fall back to a defined safe choice
  (e.g. `"default"` or the existing v2/v3 path) and log explicitly. The strict
  validator added here (`validate_vnext_checkpoint_metadata`) is the load-time gate.

## Latency Estimate (Q11)

- **Model scoring only**: mean **0.91 ms/decision**, p95 1.26 ms (300 groups, CUDA;
  first-call warmup ~90 ms). Negligible.
- **Not measured here**: live feature generation (v7 state reconstruction + opponent
  belief + per-candidate `resolve_action_impact` sim-core calls). From the 1000
  materialization (80,899 states in 409 s wall with 6 workers ≈ ~30 ms/state of
  single-thread feature work, dominated by ~7.5 sim-core impact calls/decision),
  a single live decision's feature gen is likely **tens of ms**, far exceeding
  scoring. Real live latency must be measured end-to-end before testing.

## Blockers Before Private-Match Testing (Q12)

1. **No vNext live path**: live loads `ActionRankerMLP` (v2 state / v3 action,
   pad/truncate) and cannot load `VNextDiagnosticMLP`.
2. **Tera candidates not generated** live (`legal_action_candidates` lacks
   `move_tera`), so Tera is unselectable.
3. **v7 state + v5 action features not produced** live (no per-candidate
   `resolve_action_impact`), so live features wouldn't match training schema/order.
4. **No candidate→Showdown choice serializer** for vNext candidates wired to model
   selection (incl. Tera).
5. **Masking + fail-closed fallback** must be re-implemented for the new path.
6. **End-to-end live latency** unmeasured.
7. (Quality, not a load blocker) Tera selection is weak (0.178) and switch moderate
   (0.255); acceptable for a dry run, flagged for monitoring.

## Recommended Implementation Steps

1. Add an **opt-in vNext inference harness** (env-gated, default off; do not touch
   the v2/v3 default path): load checkpoint with strict fingerprint validation;
   build v7 state and v5 candidate features using the **same** generators as
   training (`build_live_private_feature_vector(v7)`, `_legal_actions_from_private_state`,
   `build_action_feature_vector_v5` + `resolve_action_impact`); generate `move`,
   `move_tera`, and `switch` candidates; score with the rank head; map the argmax to
   a Showdown choice string; enforce masking and a fail-closed fallback.
2. Add a parity test that the harness's candidate set + scores match the offline
   evaluator on recorded states.
3. Measure end-to-end per-decision latency on a few real requests.
4. Only then build a **controlled private-match dry-run harness**.

## Explicit Statement

No private matches were run. No live defaults or checkpoints were changed or
promoted. The gate remains closed.
