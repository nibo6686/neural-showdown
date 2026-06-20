# vNext Inference Harness Report

## Purpose and Scope

Implement an **opt-in, default-off** vNext (v7/v5) action-rank inference harness
that can load the diagnostic checkpoint with strict schema/fingerprint validation,
score precomputed legal-action candidates with the rank head, mask unavailable
candidates, serialize the selected candidate to a Showdown choice string, and
**fail closed** on any inconsistency. It does not generate features, run battles,
train, promote checkpoints, or change any live default. The existing v2/v3 live
path is untouched.

## Files Changed

- `trainer/src/neural/vnext_inference.py` (new) — the harness.
- `trainer/tests/test_vnext_inference.py` (new) — 10 focused tests.
- `artifacts/training_plan/vnext_inference_harness_report.md` (this report).
- `artifacts/training_plan/diagnostic_training_gate.md` (gate updated; still closed).

No production/live code was modified. The harness is a standalone module **not
imported by `live_action_recommender.py` or `live_eval_server.py`** (asserted by
test).

## Opt-In Mechanism

- The harness is a separate module the default live path never imports, so it is
  inert unless a caller explicitly uses it.
- `vnext_inference.is_enabled()` reads `NEURAL_VNEXT_INFERENCE` (default off; `1`/
  `true`/`yes` to enable) as the documented gate for any future wiring.
- No default code path consults this flag yet, so default behavior is unchanged.

## Checkpoint / Config Used

- Config: `configs/diagnostic_1000_action_rank_v7_v5.rank_only.windows.json`
- Checkpoint: `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v5_rank_only/model.best.pt`
- Model: `VNextDiagnosticMLP`, 218,786 params; device CUDA.

## Schema / Fingerprint Validation

`VNextActionRanker.load` validates version, dimension, **and** feature-name
fingerprints against the config's declared frozen v7/v5 values via
`validate_vnext_checkpoint_metadata(require_fingerprints=True)`:

- state `live-private-belief-v7` (3208D) — `validated`
- action `legal-action-v5` (318D) — `validated`
- status **PASS**, `fingerprints_complete = true`

A checkpoint missing fingerprints is **rejected** (raises; `safe_load` returns
`ok=false`). A missing checkpoint file fails closed via `safe_load`.

## Offline Parity Result

Harness top-1 over the validation split reproduces the offline evaluator
**bit-for-bit**: `0.4625833 == 0.4625833` (`top1_match = true`). Scoring is
deterministic across repeated calls. The harness uses the same
`encode_states → rank_from_embeddings` path as `evaluate_vnext_action_rank`.

## Candidate / Command Serialization Result

`serialize_candidate_command` honors the Showdown choice grammar and fails closed
on invalid input:

- regular move → `move <slot>` (slot 1–4)
- Tera move → `move <slot> terastallize` (distinct from the plain move)
- switch → `switch <slot>` (slot 1–6)
- invalid/missing slot or unknown kind → `None` (→ harness returns safe fallback)

`recommend` masks unavailable/disabled candidates **before** scoring (they can
never be selected), scores the remainder, picks the top-1, and serializes it. A
real-checkpoint `recommend` on a validation group returned `ok=true, choice="move 1"`.

## Tera Handling Result

Tera candidates are first-class: `kind="move_tera"` (or `is_tera=true`) serializes
to a **distinct** `move <slot> terastallize` command, verified not equal to the
plain `move <slot>`. (Note: the harness only scores/serializes Tera candidates it
is *given*; generating `move_tera` candidates from a live request is a feature-gen
responsibility deferred to the dry-run harness, and the model still under-ranks
Tera — validation Tera top-1 0.178.)

## Switch Handling Result

Switches serialize to `switch <slot>` (1–6) and are scored like any candidate.
Masking applies (trapped/forced-switch handling remains a feature-gen concern for
the caller). Switch slot indexing must be reconciled with the live request payload
in the dry-run harness.

## Fallback Behavior (fail-closed)

`recommend` returns `{ok: false, choice: "default", reason: ...}` for:

- no legal candidates (`no_legal_candidates`)
- all candidates unavailable/disabled (`all_candidates_unavailable`)
- command serialization failure (`command_serialization_failed`)
- any exception during scoring (`<ExceptionType>: ...`)

`load`/`safe_load` fail closed for: missing checkpoint, schema/version/dimension
mismatch, and missing/mismatched fingerprints. **No pad/truncate anywhere**: a
wrong-sized state or action vector raises (`does not pad or truncate`), asserted by
test, and the module source contains no `np.pad`.

## Latency Result

Model scoring only (CUDA, 300 validation groups): mean **0.97 ms**, p95
**2.43 ms**, max 3.2 ms per decision group. This excludes live feature generation
(v7 state + per-candidate `resolve_action_impact`), which dominates real live
latency and must be measured end-to-end in the dry-run harness.

## Remaining Blockers Before a Private-Match Dry Run

1. **Live feature generation** is not wired: the harness consumes precomputed
   v7 state and v5 candidate features. A dry-run path must build them with the same
   generators as training (`build_live_private_feature_vector(v7)`,
   `_legal_actions_from_private_state`, `build_action_feature_vector_v5` +
   `resolve_action_impact`) from a real Showdown request.
2. **Tera/switch candidate generation** from the live request payload (the current
   live `legal_action_candidates` emits no `move_tera`).
3. **Slot reconciliation**: map generated candidates' move/switch slots to the
   exact indices Showdown expects for the choice string.
4. **End-to-end latency** unmeasured.
5. (Quality, not a blocker) Tera selection weak (0.178), switch moderate (0.255).

## Explicit Statement

No private (or public) matches were run. No live defaults or checkpoints were
changed or promoted. No model was trained. The gate remains closed.
