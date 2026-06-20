# Mechanics Repair Batch 3: Dynamic Type/STAB and Charge/Delay Timing

## Scope

Third targeted repair of the comprehensive Gen 9 Random Battles mechanics audit.
This batch handles two remaining wrong-exact buckets: dynamic move type/STAB
(8 moves) and charge/delay/two-turn timing (4 moves). The rule: repair to PASS
when Showdown/sim-core can resolve the mechanic exactly from state already
available; otherwise mark INEXACT/fail-closed. No live defaults, training,
rematerialization, or checkpoint promotion. v6 stays 331D.

## The wrong-exact bugs

- **Dynamic type/STAB.** The calc's *damage* already reflected the dynamic type,
  but the impact's `type_effectiveness` field and STAB were computed from the
  **static** metadata type. So for Weather Ball (Ice in snow), Judgment (the held
  Plate's type), Ivy Cudgel (Ogerpon form), Revelation Dance (user's primary
  type), etc., the impact reported `type_effectiveness=1` / wrong STAB even though
  the damage was correct — a wrong-exact derived field.
- **Charge/delay.** The calc returns the on-hit damage as if it lands this turn.
  For two-turn moves (Solar Beam, Meteor Beam) and the always-delayed Future
  Sight, encoding that as immediate damage is wrong-timing.

## Exact fixes (PASS)

sim-core (`damage_calc.ts`) now returns the **resolved** move type used by the
calculation (`result.move.type`, exposed as `move_type_resolved`) and computes
`type_effectiveness` from it instead of the static type. The Python impact then
uses `move_type_resolved` for STAB. This is a single small change that corrects
every dynamic-type move at once from already-available state (weather, terrain,
held item, species/form, current types, Tera):

- **Weather Ball, Terrain Pulse** — type from weather/terrain (grounding handled
  by the calc). PASS.
- **Judgment** — type from the held Plate. PASS.
- **Ivy Cudgel, Raging Bull, Aura Wheel** — type from species/form. PASS.
- **Revelation Dance** — type from the user's primary current type. PASS.
- **Tera Blast** — Tera type when Terastallizing, Normal otherwise. PASS.

Probe confirmation (vs Dragonite): Weather Ball snow `eff=4 resolved=Ice`,
Judgment + Icicle Plate `eff=4 resolved=Ice`, Ivy Cudgel Hearthflame
`eff=0.5 resolved=Fire`, Revelation Dance Primarina `eff=0.5 resolved=Water`;
controls Surf `eff=0.5 resolved=Water`, Earthquake `eff=0 resolved=Ground`
(unchanged — ordinary moves resolve to their static type).

Charge: **Beak Blast** deals its damage the same turn (a -3 priority charge, not a
two-turn move), so its immediate damage is exact — PASS. Its reactive
contact-burn is out of v6 impact scope.

## INEXACT / fail-closed fallbacks

- **Solar Beam** — exact only when it fires this turn: harsh sun or Power Herb
  (both in state). Otherwise it charges and deals no damage this turn, so the
  impact fails closed (`two_turn_charge_delayed_damage`).
- **Meteor Beam** — exact only with Power Herb (sun does not skip its charge);
  otherwise fails closed.
- **Future Sight** — always delayed (hits two turns later); always fails closed.
- **Tera Starstorm** — becomes Stellar-typed when Terastallized; Stellar STAB
  (2x) and effectiveness are not representable by the standard type chart, so it
  fails closed (`stellar_type`).

Fail-closed impacts set `available=False`, which the feature builder encodes as
`impact_unknown=1` — an honest "not represented this turn", not a wrong value.

## v7 fields proposed (documented, not implemented)

No v7 field was needed for the dynamic-type repair (the resolved type plus the
existing STAB/effectiveness fields suffice). The remaining gaps that *would* need
typed v7 fields are timing-related and were left INEXACT:

- a **delayed-damage / charge-state** field pair (e.g. `impact_delayed_this_turn`,
  `impact_lands_in_turns`) so Solar Beam / Meteor Beam / Future Sight could carry
  their scheduled damage instead of failing closed; and
- a **Stellar-type** effectiveness/STAB encoding for Tera Starstorm.

These are recorded only; the batch-3 fix did not add them.

## Result

- FAIL **39 → 27**; PASS **123 → 131**; INEXACT **188 → 192**.
- Dynamic type/STAB: 8 moves leave FAIL — 7 PASS, Tera Starstorm INEXACT.
- Charge/delay: 4 moves leave FAIL — Beak Blast PASS, Solar Beam / Meteor Beam /
  Future Sight INEXACT.

## Tests

New `trainer/tests/test_mechanics_repair_batch_3.py` (11 tests, all pass):
Weather Ball dynamic type-effectiveness (snow 4x vs clear 1x) and resolved-type
STAB, Revelation Dance STAB from user type, Tera Starstorm Stellar fail-closed,
ordinary Surf unaffected; Solar Beam fail-closed without sun/herb and exact with
each, Meteor Beam needs Power Herb, Future Sight always fail-closed, Beak Blast
same-turn damage available.

Regression: `test_action_features_v4/v5/v6`, batch-1, batch-2, `test_damage_engine`,
`test_sim_core_parity`, `test_action_ranker`, `test_mechanics_audit` (84 passed,
4 skipped); generator audit test (9 passed); sim-core jest suite (35 passed).
`git diff --check` clean.

## Schema and gate

sim-core `DamageEstimate` gained a `move_type_resolved` field (an estimate output,
not an action-feature schema field). No action feature name, order, or dimension
changed — v6 remains 331D and the v5 prefix is unchanged; only impact **values**
(type-effectiveness, STAB, charge fail-close) changed, plus the new move-id sets
and the audit reclassification. Existing v5/v6 data/checkpoints remain stale.

The gate remains **closed**: 27 wrong-exact FAILs remain (conditional
move-success/execution, turn/history-conditional power, guaranteed-crit metadata,
special type-effectiveness, terrain-dependent priority, random base power,
callback-dependent damage/type, target item removal, berry consumption). No
training, no diagnostic_300/1000 rematerialization, no checkpoint promotion, and
no live-default change occurred.

## Next recommendation

Batch 4: the conditional/execution groups — move-success conditions (Fake Out,
First Impression, Sucker Punch, Focus Punch, Thunderclap, ...) and conditional
success/failure paths (Brick Break, Pollen Puff, Psychic Fangs). These need a
"may fail / conditional execution" coarse flag; most will be INEXACT/fail-closed
rather than exact. Turn/history-conditional power (Payback, Lash Out, Stomping
Tantrum, Avalanche, Fusion Bolt/Flare) can be exact where the turn-order/history
state is already reconstructed, else INEXACT.
