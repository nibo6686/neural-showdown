# diagnostic_300 v7/v6 Rematerialization Report

Fresh materialization of the frozen `diagnostic_300` split on the
mechanics-fidelity-clean impact path (batches 1-5, FAIL=0). Materialization only:
**no training, no checkpoint, no live-default change, no diagnostic_1000/full-scale
run.** The training gate stays closed.

## Command and source

- Command: `python -m neural.benchmark_vnext_featuregen --full-manifest --manifest artifacts\training_plan\manifests\diagnostic_300_manifest.json --output-dir artifacts\training_plan\datasets\diagnostic_300_v7_v6 --workers 6 --action-feature-version legal-action-v6`
- Manifest: frozen `artifacts/training_plan/manifests/diagnostic_300_manifest.json` (reused; no new split).
- Runtime: 172.7 s (6 workers, persistent sim-core RPC).
- Output: `artifacts/training_plan/datasets/diagnostic_300_v7_v6/` (new path; v5 dir untouched).
- sim-core impact resolution via `sim_core_rpc` (persistent server), not per-call node spawn.

## Schema and fingerprints (validated)

| | Version | Dim | SHA-256 (feature-name fingerprint) |
| --- | --- | --- | --- |
| State | `live-private-belief-v7` | 3208 | `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf` |
| Action | `legal-action-v6` | 331 | `ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049` |

The action fingerprint equals the frozen v6 schema fingerprint — batches 1-5
changed only feature **values**, never names/order/dim. Recorded live defaults in
the metadata remain `live-private-belief-v2` / `legal-action-v3` (unchanged). No v5
checkpoint or v5 dataset was read; output is a new directory with v7/v6 embedded
names + fingerprints.

## Counts

- Battles processed: **300** (300 valid / 0 failed).
- State rows: **25,396**; one state row per decision (no per-candidate duplication).
- Action candidate rows: **189,957** (avg 7.48 candidates/state).
- Battle split: train 210 / validation 45 / test 45 (matches manifest).
- State split: train 20,713 / validation 2,255 / test 2,428.
- State-value labels: wins 12,632 / losses 12,764 / draws 0 (±1 only).
- Action-value labels: 0 (none, by design).

## Action match rate

- Matched / unmatched decisions: **24,624 / 772** → **match rate 96.96%**.
- Action-rank positives: 24,624 (one per matched decision); unchosen candidates 165,333.
- Skip reasons: `chosen_action_unmatched_for_action_rank` 772; `initial_deployment_nondecision` 600; others 0.
- Identical to the prior v5 diagnostic_300 (same manifest/splits/matching logic); the repaired impact features do not affect replay matching.

## Candidate kinds (Tera / switch)

| Kind | Count | Share |
| --- | ---: | ---: |
| switch | 74,087 | 39.0% |
| move | 73,836 | 38.9% |
| move_tera (Tera) | 42,034 | 22.1% |

- Tera candidates present and plentiful (42,034); switch candidates 74,087 — the
  candidate generator is intact post-repair.
- Among the 24,624 positives: move 17,960, **Tera 426 (1.7%)**, **switch 6,238 (25.3%)**.
  The low Tera-positive share is the known imbalance (replays rarely Tera) — a
  ranker concern, not a materialization defect.

## Exact vs INEXACT candidate share

Per the recommended INEXACT policy, `impact_unknown=1` and coarse next-state flags
are preserved; here is the share by candidate class.

- **Damaging move candidates: 65,962.**
  - **Exact** (impact `smogon_calc`, `impact_unknown=0`): **62,130 (94.2%** of damaging moves).
  - **INEXACT fail-closed** (`impact_unknown=1`): **3,832 (5.8%** of damaging moves; **2.0%** of all candidates) — the batches 1-5 fail-closed families (multi-hit, fixed-damage HP/counter, charge/delay, conditional execution, history power, Beat Up/Fickle Beam, Tera Starstorm).
- **Non-damaging / status move candidates: 49,908** — impact is non-damaging; many carry coarse INEXACT next-state flags (secondary/status/volatile, screen removal) per batch 2/4.
- **Switch candidates: 74,087** — impact intentionally unavailable (non-damaging), as before.
- Positives: exact-impact 10,699; inexact-fail-closed 614; non-damaging move 7,073; switch 6,238; (Tera positives 426 counted within move_tera).

Takeaway: only **2.0%** of all candidate rows (5.8% of damaging moves) are
fail-closed wrong-exact avoidances; the large majority of damaging candidates
resolve exactly, and the fail-closed/coarse signals are intact for honest
exact-vs-INEXACT training breakdowns.

## Mechanics-audit cleanliness reference

This dataset was generated on the impact path validated to **138 PASS / 0 FAIL /
212 INEXACT** in `gen9randbats_mechanics_completeness_audit.md` (representative
suite 12 PASS / 0 FAIL in `dynamic_move_mechanics_fidelity_audit.md`). No
wrong-exact impact is emitted; INEXACT candidates are flagged, not faked.

## Validation result

All 18 materializer validation checks passed, including `state_dim_3208`,
`action_dim_matches_schema` (331D), float16 dtypes, `candidate_state_indices_valid`,
`no_battle_crosses_splits`, `state_splits_match_manifest`,
`metadata_records_requested_schema`, `metadata_records_name_fingerprints`,
`embedded_names_match_schema_and_metadata`, `live_defaults_unchanged`,
`state_not_duplicated_per_candidate`, `state_value_labels_valid`,
`action_rank_labels_valid`, `action_value_labels_absent`. `validation_passed=True`.

## Files produced

- `artifacts/training_plan/datasets/diagnostic_300_v7_v6/diagnostic_300_v7_v6.npz`
- `.../feature_metadata.json` (v7/v6 schema + fingerprints)
- `.../source_manifest_snapshot.json`
- `.../decision_skip_audit.jsonl`
- `.../materialization_report.json`
- `.../diagnostic_300_v7_v6_materialization_report.md` (auto-generated)
- per-battle shards under `.../_shards/` (resume/crash recovery)

## Disposition and gate

The fresh v7/v6 diagnostic_300 dataset satisfies the §3 pre-scaling checks from
`v7_v6_training_readiness_review.md`: schema/fingerprint validation, mechanics-clean
impact path, ~97% match rate, exact-vs-INEXACT share, Tera/switch counts, and no
v5/v6 stale-checkpoint reuse. The stale v5 `diagnostic_300_v7_v5` dataset and the
v7/v5 rank-only checkpoint remain not-for-conclusions.

**No training was run.** The training gate remains **closed**: the next step (tiny
rank-only training on this fresh dataset, with exact-vs-INEXACT/Tera/switch/
non-damaging/dynamic-mechanic breakdowns) and any larger materialization remain
approval-gated. No checkpoint promoted; no live default changed.
