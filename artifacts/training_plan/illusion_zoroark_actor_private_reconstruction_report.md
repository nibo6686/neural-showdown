# Zoroark / Illusion Actor-Private Reconstruction Report

## Scope

Source/test-only audit and fix of the 7 remaining Zoroark/Illusion residual
unmatched rows, applying actor-private reconstruction where it is safe. No
training, dataset rematerialization, checkpoint promotion, live-default change,
live-bot change, push, `legal-action-v8`, old-gen, NatDex, Mega, Z-Move, or
Dynamax work occurred. `legal-action-v7` stays 552D with fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`; no state
dimension changed.

Checkpoint before this work:
`038f0955fe3fdd5f88dc35c52ebb0fe4cf433386`
(`checkpoint: transform imposter reconstruction fix`)

## Modeling policy applied

- **Actor-private reconstruction.** When a residual decision row belongs to the
  side controlling the Zoroark/Zoroark-Hisui, the true species and true moves are
  own-side facts. Later reveal/completed-team information may be used
  retroactively to reconstruct that actor's private decision state, because the
  actor knew their own Pokemon at the time.
- **Opponent pre-action belief is untouched.** The opponent's belief is built
  separately from the causal protocol prefix; later reveals are never used to
  alter the opponent's earlier pre-action state. The true species behind an
  Illusion never appears in the opponent's pre-reveal belief.
- **No illegal candidates / no hidden leakage.** Fixes only map a chosen action
  onto an already-legal own-side candidate or reconstruct the own active's true
  moves. No switch-to-active-displayed-species candidate is created, and copied
  opponent move/species facts are not globally backfilled.

## Reconstruction principle: self-confirming stints

An active stint **self-confirms** as an Illusion when a later `|replace|` for the
same side reveals a different species before the next `switch` for that side. A
self-confirming stint is unambiguously the revealed (true) species for that whole
stint, with no chosen-action guess and no HP heuristic. This is the safe signal
used for both move de-disguise and switch relabeling.

## Implementation

- `build_live_private_value_dataset.py`
  - `_illusion_true_species_for_stint` — true species of a self-confirming stint.
  - `_own_side_illusion_true_active` — true species of the own active when it is a
    pre-reveal Illusion (anchored by the most recent own switch in the prefix).
  - In `_reconstructed_private_state_for_side`: when the own active self-confirms,
    move the active entry from the displayed species to the true species so the
    true moves become legal candidates (the displayed species becomes a normal
    bench entry). Gated by `_replay_roster_alias_id` so it never fires on aliases.
  - `actor_private_switch_relabel` — maps a displayed own-side switch action to the
    true species when the switched-in entity self-confirms.
- `benchmark_vnext_featuregen.py` — `_decision_features` applies
  `actor_private_switch_relabel` to the chosen label before matching.
- `scripts/recompute_v7_v7_residual_unmatched_from_replays.py` — applies the
  relabel, reports the four Illusion categories and the new residual count.

The opponent-public **post-action contradiction/suspicion** signal (an apparent
species performing an impossible action, e.g. Avalugg using Will-O-Wisp) is **not
implemented**: it would require a new public-belief/threat-awareness field, and
`legal-action-v7` / state dims are frozen in this task. It is documented as
future `legal-action-v8` threat-awareness work. The safety-critical property —
the opponent's pre-reveal belief never contains the true species — is preserved
and tested.

## Per-case findings

| # | Replay | Turn | Side | Action | Perspective | Self-confirms? | Disposition |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | `gen9randombattle-2591469202` | 1 | p2 | `move Sludge Bomb` | actor (Zoroark) | yes (replace before next switch) | **Fixed** — active reconstructed as Zoroark; `move: Sludge Bomb` matches |
| 2 | `gen9randombattle-2593348981` | 1 | p1 | `move Will-O-Wisp` | actor (Zoroark-Hisui) | **no** (switched out before any reveal) | **Quarantined** — see below |
| 3 | `gen9randombattle-2593348981` | 6 | p1 | `move Will-O-Wisp` | actor (Zoroark-Hisui) | yes (replace before next switch) | **Fixed** — active reconstructed as Zoroark-Hisui; matches |
| 4 | `gen9randombattle-2593348981` | 18 | p1 | `move Will-O-Wisp` | actor (Zoroark-Hisui, revived/re-disguised) | yes (replace before next switch) | **Fixed** — matches |
| 5 | `gen9randombattle-2591404793` | 21 | p1 | `switch Houndstone` | actor | yes (replace within switched-in stint) | **Fixed** — relabeled `switch: Zoroark`; matches |
| 6 | `gen9randombattle-2591404793` | 23 | p1 | `switch Houndstone` | actor | yes | **Fixed** — relabeled `switch: Zoroark`; matches |
| 7 | `gen9randombattle-2591404793` | 25 | p1 | `switch Houndstone` | actor | yes | **Fixed** — relabeled `switch: Zoroark`; matches |

### Per-case answers to the audit questions

For every row the perspective is the **Zoroark user's own side**, so actor-private
reconstruction is the relevant lever. None requires opponent hidden leakage, and
none requires an illegal candidate.

- **Cases 1, 3, 4 (move):** The replay reveals the true species via a `replace`
  within the same active stint as the decision (`Zoroark`@line 59, `Zoroark-Hisui`
  @125 and @268). The own active is reconstructed as the true species; the true
  moves (already transferred to the revealed species by the completed-team
  builder) make `Sludge Bomb`/`Will-O-Wisp` legal. → **matched**.
- **Cases 5, 6, 7 (switch):** Each switched-in disguised entity self-confirms via
  the immediately following `replace` (@277/@296/@314). The displayed
  `switch: Houndstone` is relabeled to the true `switch: Zoroark`, which is an
  already-legal bench candidate. The real Houndstone is active, so no
  switch-to-active candidate is added. → **matched**.
- **Case 2 (move, turn 1):** The disguised entity switched out (to Miraidon @46)
  **before any reveal in that stint**, so the stint is not self-confirming. p1
  also genuinely owns a real Avalugg (max HP 310) that later appears under the
  same displayed species, while the disguised Zoroark-Hisui displays max HP 219.
  Attributing the turn-1 "Avalugg" to the disguise would require HP-signature
  physical-entity tracking across switch-outs, which is fragile and risks
  misattributing the real Avalugg. The replay does not self-confirm this stint,
  so it is **quarantined** rather than guessed. It is not a leakage or
  illegal-candidate problem; it is an irreducible public-replay attribution
  limitation for a single train row. In live play this never arises: the bot
  knows its own true side from the Showdown request.

## Result

- 6 of 7 Illusion residuals fixed (actor-private); 1 quarantined (case 2).
- Combined with the earlier Transform fix, the residual recomputation harness
  reports: 8 cases checked, **7 matched**, **1 unmatched**, categories
  `{transform_reconstruction_fixed: 1, actor_private_illusion_fixed: 6,
  unsupported_or_quarantined: 1}`, `all_as_expected = True`.
- **Expected residual unmatched count after a future approved rematerialization:
  1** (the quarantined non-self-confirming turn-1 Avalugg stint).

## Regression tests

`trainer/tests/test_benchmark_vnext_featuregen.py`:

- `test_actor_private_illusion_staraptor_sludge_bomb_matches` — actor-private
  Zoroark match; opponent pre-action belief contains neither the true species nor
  the not-yet-used move.
- `test_actor_private_illusion_avalugg_will_o_wisp_matches` — actor-private
  Zoroark-Hisui match; opponent pre-reveal belief never contains the true species.
- `test_non_self_confirming_illusion_stint_stays_unmatched` — turn-1 Avalugg stays
  apparent and unmatched (quarantined).
- `test_actor_private_duplicate_illusion_switch_relabels_to_true_species` — switch
  relabeled to `switch: Zoroark`; no `switch: Houndstone` (switch-to-active)
  candidate.
- `test_real_houndstone_switch_is_not_relabeled` — a genuine Houndstone switch is
  not relabeled.

## Gate status

Source is ready for an explicitly approved corrected v7/v7 rematerialization.
The checked-in `diagnostic_300_v7_v7_corrected` dataset remains stale with respect
to this fix; smoke training stays blocked until a future approved rematerialization
and fresh artifact audit. Production and live gates remain **closed**.
