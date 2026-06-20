# vNext Live Eval Server — Recommendation Shadow Mode Report

## Purpose and Scope

Add an **opt-in, default-off** vNext (v7/v5) recommendation shadow mode to the
existing live eval server / extension workflow. A real Showdown payload (the same
one the browser extension already sends) is reconstructed into
`live-private-belief-v7` state and `legal-action-v5` candidates (including
`move_tera` when Tera is legal), scored with the `VNextActionRanker`, and returned
as a dry-run recommendation + diagnostics **for display only**. No command is sent
to Showdown, no browser state is changed, no battle is played, and the default
`/evaluate` path is untouched.

## Files Changed

- `trainer/src/neural/vnext_live_shadow.py` (new) — the shadow orchestration:
  reconstruct + v7 state + v5 candidates + impact + scoring + fail-closed
  diagnostics.
- `trainer/src/neural/live_eval_server.py` — added one route,
  `POST /evaluate-vnext-dry-run` (lazy import; gated; default path unchanged).
- `trainer/tests/test_vnext_live_shadow.py` (new) — 8 focused tests.
- `artifacts/training_plan/vnext_live_eval_server_shadow_mode_report.md` (this report).
- `artifacts/training_plan/diagnostic_training_gate.md` (gate updated; still closed).

No live defaults, checkpoints, models, or the existing v2/v3 `/evaluate` handler
were changed.

## Opt-In Mechanism

- New route `POST /evaluate-vnext-dry-run`. When `NEURAL_VNEXT_INFERENCE` is unset,
  it returns `{ok:false, fallback_reason:"vnext_inference_disabled", choice:"default"}`
  and does nothing else.
- The shadow module is imported **lazily inside the route handler only**; the
  default `/evaluate` path never imports or calls it (asserted by test).
- Optional overrides: `NEURAL_VNEXT_CONFIG`, `NEURAL_VNEXT_CHECKPOINT` (default to
  the rank-only config/checkpoint).

## Existing Live Server / Extension Path Used

The browser extension posts the real `EvalRequest` (`room_id`, `url`, `player`,
protocol `log`, latest `request`, optional `legal_actions`) to the local server.
The shadow route consumes that same payload and reuses the existing
`build_features_from_live_payload` (in `live_private_features.py`) for
reconstruction + featurization — the same function the v2 path and the v7 feature
tests already use — so no new reconstruction logic was introduced. The extension
still only displays recommendations; the user chooses manually.

## Checkpoint / Config Used

- Config: `configs/diagnostic_1000_action_rank_v7_v5.rank_only.windows.json`
- Checkpoint: `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v5_rank_only/model.best.pt`
- Loaded via `vnext_inference.VNextActionRanker` with strict schema/fingerprint
  validation (status **PASS**, fingerprints complete).

## Fixture / Packet Source

A sanitized synthetic Gen 9 request fixture (Charizard + 2 bench, four moves,
`canTerastallize` set; public log with both leads) — no cookies, tokens, auth, or
session identifiers (the `EvalRequest` schema carries none). The shadow response
echoes only derived diagnostics, never the raw payload, `url`, or `room_id`.

## v7 State Generation

**Succeeded.** `build_features_from_live_payload(..., feature_version=v7)` produced
a `live-private-belief-v7` vector of dimension **3208**. The shadow path rejects
any other dimension (no pad/truncate).

## v5 Candidate Generation

**Succeeded.** `_legal_actions_from_private_state` (the same generator training
used) produced candidates, and each was featurized with
`build_action_feature_vector_v5` + `resolve_action_impact` to dimension **318**
(wrong dimension → fail closed). On the fixture: **4 move + 4 move_tera + 2 switch
= 10 candidates**. Impact methods: `smogon_calc` 6, `non_damaging` 2,
`unavailable` 2.

## Tera Candidate Result

**Generated.** With `canTerastallize` set, four `move_tera` candidates were
created (distinct from the four plain moves); `tera.can_tera=true`,
`tera_candidates_generated=4`. With Tera not legal, zero `move_tera` candidates
are generated (tested).

## Switch Candidate Result

**Generated and serializable.** Two switch candidates (Blastoise, Venusaur),
each mapped to a 1-based team slot for a `switch <slot>` choice.

## Recommendation Response Shape

```jsonc
{
  "ok": true,
  "mode": "vnext_dry_run",
  "choice": "move 2",                 // or "move N terastallize" / "switch N" / "default"
  "fallback_reason": null,
  "missing_fields": [],
  "selected": { "kind", "label", "move_slot", "switch_slot", "is_tera", "score" },
  "candidates": [ { "kind", "label", "score" }, ... ],   // sorted, available only
  "candidate_kind_counts": { "move": 4, "move_tera": 4, "switch": 2 },
  "tera": { "can_tera": true, "tera_candidates_generated": 4 },
  "switch_candidate_count": 2,
  "impact_methods": { "smogon_calc": 6, "non_damaging": 2, "unavailable": 2 },
  "schema": { "state_feature_version", "state_feature_dim": 3208,
              "action_feature_version", "action_feature_dim": 318,
              "fingerprint_status": "PASS", "fingerprints_complete": true },
  "player_side": "p1",
  "latency_ms": { ... },
  "command_sent_to_showdown": false,
  "battle_played_by_model": false,
  "live_defaults_changed": false
}
```

## Fail-Closed Behavior

Returns a safe `choice:"default"` with an explicit reason for:

- ranker load failure (`ranker_load_failed: ...`)
- state feature generation failure / wrong dim (`state_feature_generation_failed`,
  `state_feature_dim_mismatch`)
- missing required live fields (`missing_required_live_fields`, with `missing_fields`)
- no legal candidates (`no_legal_candidates`)
- action feature generation failure / wrong dim (`action_feature_generation_failed`,
  `action_feature_dim_mismatch`)
- command serialization failure (`command_serialization_failed`)
- flag off (`vnext_inference_disabled`)

No field is guessed when missing; the reason and missing fields are reported.

## Latency Breakdown

Cold single-call on the fixture (CUDA, no warm sim-core client):

| Stage | ms |
| --- | ---: |
| request parsing | (upstream of handler; FastAPI) |
| state feature generation (v7 + reconstruction) | 62.7 |
| action candidate generation | 0.03 |
| sim-core impact resolution (10 candidates) | **2895.4** |
| model scoring (first-call warmup) | 88.5 |
| response serialization | 0.01 |
| total | 3273.4 |

Impact resolution dominates (per-candidate smogon damage calc). The number above
is a **cold** measurement; a persistent live server with a warm sim-core client
will be substantially faster, and model scoring at steady state is well under
1 ms. End-to-end latency with a warm client still needs a dedicated measurement.

## Missing Live-Data Fields

None for a well-formed request. When the active Pokémon cannot be recovered from
either the request or public reveals (e.g. empty request + bare log), the path
fails closed with `missing_required_live_fields` / `no_legal_candidates`.

## Safety Confirmations

- Command sent to Showdown: **no**.
- Battle played by the model: **no**.
- Browser state modified: **no**.
- Live defaults changed: **no** (default `/evaluate` returns the legacy v2/v3
  response and never touches this path).
- Sensitive fields: the response stores only derived diagnostics; the raw payload,
  `url`, and `room_id` are not echoed, and the dry-run route does not log them.

## Blockers Before Manual Private-Match Recommendation Testing

1. **End-to-end latency with a warm sim-core client** is unmeasured; cold impact
   resolution (~2.9 s for 10 candidates) must be brought down (persistent client /
   batching) for an interactive UX.
2. **Slot-index reconciliation**: switch/move slot mapping is derived from the
   reconstructed team/request; it should be validated against live Showdown choice
   acceptance on real rooms before trusting the serialized command.
3. **Semantic parity** of live-reconstructed v7 state / v5 candidates vs the
   training distribution is assumed, not yet audited field-by-field for live
   packets.
4. **Model quality**: Tera under-ranked (validation 0.178) and switch moderate
   (0.255); recommendations are advisory.

## Explicit Statement

No private or public matches were run. No command was sent to Showdown. No model
was trained, no checkpoint promoted, and no live default changed. The gate remains
closed.
