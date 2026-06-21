# Ditto / Imposter Re-Transform-Into-Same-Species Fix Report

## Scope

Source/test-only fix for the 11 Ditto/Imposter residual unmatched rows surfaced by
the full post-Illusion materialization, plus resolution of the single `Struggle`
residual. No training, rematerialization, checkpoint promotion, live-default
change, live-bot change, push, `legal-action-v8`, or old-gen work occurred.
`legal-action-v7` stays 552D / fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`; no state
dimension changed.

Checkpoint before this fix:
`cffb8714827f329f06285c814a29d9521a382ec8`
(`checkpoint: post illusion materialization audit`)

## Bug

`_active_transform_copied_moves`
(`trainer/src/neural/build_live_private_value_dataset.py`) anchored the current
Transform stint in the full-trajectory walk by `event.raw == stint_raw`. A
Ditto/Imposter that re-transforms into the **same species** emits identical
`|-transform|...|[from] ability: Imposter` markers, so the string match bound
`in_stint` to the **earliest** occurrence and then stopped at the intervening
switch-out — never reaching the actual current stint. The reconstructed copied
moveset therefore reflected an earlier stint and omitted the move chosen in the
current stint.

The earlier Transform regression (`gen9randombattle-2589571474`) only transformed
into **distinct** species (Ho-Oh, Sableye, Virizion), whose `raw` markers differ,
so the bug was not exposed.

## The 11 Ditto residuals (from the post-Illusion `decision_skip_audit.jsonl`)

| Replay | Turns | Side | Move | Target species | Transform occurrences (same-species repeat) | Why the old lookup failed | Now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gen9randombattle-2590922693` | 92,93,94 | p2 | Sacred Fire | Entei | Magmortar → Cryogonal → Entei → **Entei** | bound to the 1st Entei stint (Flare Blitz/Stone Edge), stopped at the switch before the 2nd | matched (copied `Flare Blitz, Sacred Fire`) |
| `smogtours-gen9randombattle-929481` | 68,69,70,71 | p2 | Energy Ball | Meganium | Heracross → Sableye → Meganium → Sableye → Sableye → **Meganium** | bound to an earlier Sableye/Meganium stint | matched (copied `Energy Ball, Synthesis`) |
| `gen9randombattle-2594584178` | 25,26,27,28 | p1 | Outrage | Koraidon | Koraidon → **Koraidon** | bound to the 1st Koraidon stint (Flare Blitz), stopped at the switch | matched (copied `Outrage`) |

All 11 now match. The fix preserves the no-cross-stint guarantee: e.g. the
`2590922693` re-transform stint copies `Sacred Fire` but **not** `Stone Edge`
(which belonged to the earlier Entei stint).

## Fix

Anchor the current Transform stint by **event object identity**, not by `raw`
string. The helper now captures the actual anchor `-transform` event object from
the causal prefix and matches it in the full-trajectory walk with `event is
anchor_event` (and `event is not anchor_event` for the "a different transform ends
the stint" check). Re-transforming into the same species yields distinct event
objects, so each is its own stint. Prefix and full-trajectory event dicts are
shared objects (the prefix is built from the same trajectory), so identity
matching is reliable.

This is a minimal change inside `_active_transform_copied_moves`; the global
completed-team accumulation is unchanged, so copied opponent moves are still never
backfilled into Ditto's base/global moveset, and the previously-fixed
`gen9randombattle-2589571474` t20 `Thunder Wave` case still matches with future
`Leaf Blade` still absent.

## Struggle inspection (Part 3)

- **Replay/turn:** `smogtours-gen9randombattle-929481` turn 65, p2 Ditto
  `Struggle`.
- **Was Struggle forced?** Yes. The Ditto (transformed) had exhausted the PP of
  all copied moves; `Struggle` is the forced fallback, observed in the replay.
- **Does Showdown expose it?** Yes — when every move is out of PP, the live
  request offers a Struggle-only move option; it is a deterministic forced legal
  action.
- **Schema-safe under `legal-action-v7`?** Yes. It is represented as the existing
  exhaustion-fallback `move: Struggle` candidate (added only when the reconstructed
  active has replay-observed `Struggle`). No schema/dim/fingerprint change and no
  illegal candidate.
- **Was it intentionally excluded?** It was an explicit skip in earlier audits,
  but the real cause here was the re-transform stint bug masking the
  replay-observed `Struggle`. With the corrected stint, `struggle_available`
  becomes true and the fallback candidate is generated.
- **Decision: fixed.** With the corrected stint the row matches naturally
  (`copied = {Knock Off, Recover, Struggle, Thunder Wave}` → exhaustion fallback
  adds `move: Struggle`). No schema change, no illegal candidate.

## Regression tests

`trainer/tests/test_benchmark_vnext_featuregen.py`:

- `test_ditto_retransform_same_species_matches_sacred_fire` — Sacred Fire matches;
  the earlier-stint `Stone Edge` is excluded (separate stints, no merge).
- `test_ditto_retransform_same_species_matches_energy_ball` — Energy Ball matches.
- `test_ditto_retransform_same_species_matches_outrage` — Outrage matches.
- `test_ditto_struggle_pp_exhaustion_matches_with_correct_stint` — `move: Struggle`
  candidate present and matched.
- Existing `test_ditto_transform_exposes_current_stint_copied_move`,
  `test_ditto_transform_excludes_future_transform_stint_move`,
  `test_transform_copied_moves_do_not_merge_across_stints`, and
  `test_transform_copied_moves_not_globally_backfilled_into_species` still pass
  (Thunder Wave matches, Leaf Blade absent, no global backfill).

## Residual recomputation harness

`scripts/recompute_v7_v7_residual_unmatched_from_replays.py` now covers all 22
post-Illusion residual cases (the original documented 8 plus the 11 Ditto
re-transform rows, the Struggle row, and the 2 additional non-self-confirming
Illusion rows). Result: **22 cases, 19 matched, 3 unmatched**, categories
`{transform_reconstruction_fixed: 1, actor_private_illusion_fixed: 6,
ditto_retransform_fixed: 11, struggle_pp_exhaustion_fixed: 1,
unsupported_or_quarantined: 3}`, `all_as_expected = True`.

## Expected residual count after a future approved rematerialization

**3**, down from the materialized 15. The remaining 3 are the irreducible
non-self-confirming Illusion stints:

- `gen9randombattle-2593348981` t1 `Will-O-Wisp`
- `gen9randombattle-2593348981` t2 `Poltergeist`
- `gen9randombattle-2593283718` t3 `Hyper Voice`

Each disguised entity switched out before any `replace` reveal in that stint and
is publicly indistinguishable from the player's genuine same-species Pokemon. This
is an irreducible public-replay attribution limitation, not a live-play one (live
play knows its own true side from the Showdown request).

## Gate status

This is a source/test/report change only and is verified by replay-prefix
recomputation; the checked-in `diagnostic_300_v7_v7_post_illusion` dataset remains
as materialized (15 residuals) until a future explicitly approved rematerialization
applies this fix. Smoke training remains blocked until that rematerialization and a
fresh audit. Production and live gates remain **closed**.
