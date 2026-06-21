# Transform / Imposter Reconstruction Fix Report

> **Follow-up (later task):** the full post-Illusion materialization surfaced a
> related gap — re-transforming into the **same species** produced identical
> `-transform` `raw` markers, so this report's stint anchor bound to the wrong
> occurrence. Fixed by anchoring the stint by event object identity; see
> `ditto_retransform_same_species_fix_report.md`. That fix also resolved the single
> `Struggle` residual. The expected residual after a future rematerialization is
> now 3 (irreducible non-self-confirming Illusion stints).

## Scope

Source/test-only fix for the one residual unmatched case the residual-8
verification found still fixable: a Ditto/Imposter Transform reconstruction bug.
No training, dataset rematerialization, checkpoint promotion, live-default
change, live-bot change, push, `legal-action-v8`, old-gen, NatDex, Mega,
Z-Move, Dynamax, or `legal-action-v7` schema work occurred. `legal-action-v7`
stays 552D with fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.

Checkpoint before this fix:

`5ad748b78670d565056b9273c72e1d3ad0c4337e`
(`checkpoint: residual unmatched triage fixes`)

## Target case

- Replay: `gen9randombattle-2589571474`
- Turn: 20, side p1
- Active: Ditto, transformed into p2 Sableye via ability Imposter
- Parsed action: `move: Thunder Wave`

Before the fix the reconstructed active move list was
`[Brave Bird, Knock Off, Leaf Blade, Recover]` and `Thunder Wave` was missing,
so the chosen action did not match any legal candidate.

## Root cause

`-transform` was never parsed into a typed event, so the reconstruction had no
Transform awareness. Every move Ditto used while transformed was attributed to
its base species across the whole battle. Ditto's global moveset therefore
merged copied moves from three separate Transform stints:

- Ho-Oh stint: `Brave Bird`
- Sableye stint: `Knock Off`, `Recover`, `Thunder Wave`
- Virizion stint (after turn 20): `Leaf Blade`

`_request_like_move_names` sorts alphabetically and keeps the first four, so the
five-move merged set dropped `Thunder Wave`. The merge also pulled the future
`Leaf Blade` from a Transform stint that begins *after* the turn-20 decision.

## Fix

Transform/Imposter copied moves are now scoped to the current Transform stint.

1. `trainer/src/neural/parse_replay_logs.py`
   - Parse `|-transform|` into a typed `transform` event
     (`type`, `side`, `actor`, `target`, `raw`).

2. `trainer/src/neural/benchmark_vnext_featuregen.py`
   (`_completed_teams_for_action_reconstruction`)
   - Track a per-side `transformed` flag (set on `transform`, cleared on
     `switch`). While transformed, copied moves are **not** added to the base
     species' global moveset. This prevents copied opponent moves from being
     globally backfilled into the transformed Pokemon's species features.

3. `trainer/src/neural/build_live_private_value_dataset.py`
   - New `_active_transform_copied_moves(prefix, full_trajectory, side)` helper.
     It detects, from the causal prefix, whether the active is currently
     transformed and into which target, then reconstructs the current stint's
     copied moveset (the actor's stint moves plus the target species' revealed
     moves), bounded by the actor's switch / next transform / faint. Within the
     current stint the existing own-side future-public-reveal assumption still
     applies (a move revealed later in the same stint is part of the same copied
     request), but other Transform stints are excluded.
   - `_reconstructed_private_state_for_side` accepts an optional
     `full_trajectory` and uses the helper's copied moveset for `active_moves`
     when the active is transformed, falling back to the completed-team moveset
     otherwise. `_context_for_prefix` passes the full trajectory through.

## Behavior after the fix

Recomputed read-only from the raw replay (no rematerialization):

- Turn 20 (Sableye stint): `active_moves = [Encore, Knock Off, Recover, Thunder
  Wave]`; `move: Thunder Wave` **matches**; future `Leaf Blade` is absent.
- Turn ~ (Ho-Oh stint, `Brave Bird` decision): `active_moves = [Brave Bird,
  Sacred Fire]`; the self-revealing `Brave Bird` still matches (no regression
  for in-stint future reveals) and excludes `Thunder Wave` / `Leaf Blade`.
- Global `Ditto` moveset is empty — copied opponent moves are not globally
  backfilled into the species.

## No-leakage

- Copied moves are used only for the transformed actor's own current-stint
  active state. Transform legitimately shows the transforming player the copied
  moveset in their own request, so this is an own-side/request-visible fact.
- Copied opponent moves are not merged into the base species' global moveset
  and are not backfilled into the public opponent belief (built separately).
- No future Transform stint is used to reconstruct an earlier decision.
- No illegal fifth move is added; the request-like four-slot cap is preserved.

## Regression tests

`trainer/tests/test_benchmark_vnext_featuregen.py` adds:

- `test_ditto_transform_exposes_current_stint_copied_move` — `Thunder Wave`
  present and matched at turn 20.
- `test_ditto_transform_excludes_future_transform_stint_move` — future
  `Leaf Blade` absent at turn 20.
- `test_transform_copied_moves_do_not_merge_across_stints` — the Ho-Oh stint
  exposes its own copied moves only (no `Thunder Wave` / `Leaf Blade`) and
  matches.
- `test_transform_copied_moves_not_globally_backfilled_into_species` — copied
  opponent moves are not present in Ditto's global moveset.

## Reproducible residual harness

`scripts/recompute_v7_v7_residual_unmatched_from_replays.py` recomputes the
documented residual cases read-only from raw replays. After this fix it reports
8 cases checked, **1 matched** (the Ditto/Imposter case) and **7 unmatched**
(4 no-leakage Illusion move cases + 3 unsupported Illusion duplicate switch
artifacts), `all_as_expected=True`.

## Expected residual count

The expected residual unmatched count after a future approved rematerialization
is now **7**, not 8. The remaining 7 are bounded Illusion/public-replay
ambiguity (pre-reveal Illusion moves) and unsupported duplicate-Illusion switch
artifacts. The never-revealed-Zoroark-in-public-replay ambiguity is an
irreducible public-replay limitation, not a live-play limitation: in live play
the bot knows its own true side from the Showdown request.

> **Update (follow-up task):** the 7 Illusion residuals were subsequently
> audited and 6 were fixed by actor-private reconstruction
> (`illusion_zoroark_actor_private_reconstruction_report.md`), lowering the
> expected residual count to **1** (the quarantined non-self-confirming turn-1
> Avalugg stint in `gen9randombattle-2593348981`).

## Gate status

Source is ready for an explicitly approved corrected v7/v7 rematerialization.
The checked-in `diagnostic_300_v7_v7_corrected` dataset remains stale with
respect to this fix; smoke training stays blocked until a future approved
rematerialization and a fresh artifact audit. Production and live gates remain
**closed**.
