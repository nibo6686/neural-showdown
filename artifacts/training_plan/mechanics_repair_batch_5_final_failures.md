# Mechanics Repair Batch 5: Final Failures (Zero Wrong-Exact)

## Scope

Fifth and final mechanics-repair batch. Clears the last 9 wrong-exact FAILs from
the comprehensive Gen 9 Random Battles audit: Beat Up, Photon Geyser, Flower
Trick, Wicked Blow, Freeze-Dry, Fickle Beam, Grassy Glide, Knock Off, Bug Bite.
Rule: exact PASS when the calc/state resolves it and v6 fields encode it
truthfully; INEXACT/fail-closed otherwise; no wrong-exact; no new schema fields
(document v7). No training, rematerialization, checkpoint promotion, or
live-default change. v6 stays 331D.

## Verification probes

Each candidate was probed against the sim-core calc before deciding:

- **Wicked Blow / Flower Trick** — Flower Trick (BP 70, Grass STAB) did 1.495x the
  damage of an equal-BP non-crit move; Wicked Blow ~1.515x Sucker Punch (BP-
  adjusted). The calc bakes the guaranteed 1.5x crit into the rolls → damage exact.
- **Photon Geyser** — for a physical user (Atk 300 / SpA 50) it matched Zen
  Headbutt scaled by BP (used Atk, physical); for a special user (Atk 50 / SpA
  300) it matched Psychic scaled by BP (used SpA). The calc selects the higher
  attacking stat and matching category → damage exact.
- **Freeze-Dry** — damage already reflected 2x vs Water, but the reported
  `type_effectiveness` used the generic Ice-vs-Water 0.5.
- **Beat Up** — the calc returns 0 (per-ally Attack not modeled).
- **Knock Off** — item 1.5x scaling resolves correctly (item 0.79 / none 0.53).

## Exact fixes (PASS, +4)

- **Flower Trick, Wicked Blow** — the calc includes the guaranteed crit in the
  damage; the impact now reports `crit_included=True` for
  `GUARANTEED_CRIT_MOVE_IDS` (was hardcoded False). Damage exact + flag truthful.
- **Freeze-Dry** — sim-core now overrides the reported effectiveness so Water
  counts as 2x (e.g. vs Water 2x, Water/Flying 4x), matching the damage the calc
  already produces. `type_effectiveness` / `super_effective` / `resisted` are now
  correct.
- **Photon Geyser** — no code change needed; the calc's stat/category selection
  was verified exact, so it is reclassified PASS.

## INEXACT — damage itself wrong-exact, fail-closed (2)

- **Beat Up** — `party_attack_stats`: the calc cannot resolve per-ally-Attack
  damage (returns 0), so the impact fails closed (`impact_unknown`) rather than
  emit 0.
- **Fickle Beam** — `random_power`: 30% chance to double power; the single value
  is wrong-exact, so it fails closed.

## INEXACT — damage exact, unrepresented effect (3, kept damage)

These deal exact damage, so the damage is kept (failing it closed would discard a
correct, validated value — the representative fidelity suite checks Knock Off's
item-scaled damage). Only a material next-state/priority effect is unrepresented,
which leaves them INEXACT and is documented for a future v7 typed field:

- **Knock Off** — damage incl. the item 1.5x is exact; the target's item removal
  next-state is unrepresented (v7 item-delta).
- **Bug Bite** — damage is exact; the stolen-berry consumption effect is
  unrepresented (v7 item-delta).
- **Grassy Glide** — damage is exact; the terrain-conditional +1 priority modifier
  is not representable in the static priority feature (the declared base priority 0
  is correct, the modifier needs v7 conditional-priority).

## Result

- FAIL **9 → 0**; PASS **134 → 138**; INEXACT **207 → 212**.
- The comprehensive audit now reads **138 PASS / 0 FAIL / 212 INEXACT / 0
  NOT_RELEVANT** — every material move-impact mechanic is PASS or explicitly
  INEXACT/fail-closed. Zero wrong-exact.
- The representative fidelity suite remains **12 PASS / 0 FAIL** (Knock Off damage
  preserved).

## v6 changed? / v7 proposals

No action feature name, order, or dimension changed; v6 remains 331D. sim-core's
`DamageEstimate` reporting changed (Freeze-Dry effectiveness override) but no
action-feature schema field was added. The remaining 212 INEXACT moves rely on
fail-closed/coarse encodings; raising them toward PASS needs the documented v7
typed fields (secondary status/chance, volatile id, item-delta, delayed-damage/
charge-state, conditional-execution flag, conditional-priority, Stellar typing).
None were implemented here.

## Tests

New `trainer/tests/test_mechanics_repair_batch_5.py` (5 tests): guaranteed-crit
flagged + exact (Wicked Blow, Flower Trick), ordinary move crit_included False,
Freeze-Dry 2x vs Water, Photon Geyser uses higher attacking stat, Beat Up / Fickle
Beam fail closed, Knock Off / Bug Bite / Grassy Glide keep exact damage.

Regression: action-features v4/v5/v6, batch-1/2/3/4, damage_engine,
sim_core_parity, action_ranker, mechanics_audit (103 passed, 4 skipped); generator
audit test (now asserts zero FAIL, 12 passed); sim-core jest suite (35 passed).
`git diff --check` clean.

## Schema and gate

No v6 schema field changed; v6 remains 331D. Existing v5/v6 data/checkpoints remain
mechanically stale (their resolved-impact values predate batches 1-5).

**The mechanics-fidelity criterion is now met: zero wrong-exact FAIL.** The gate's
"Gen 9 Random Battles mechanics completeness has no wrong-exact FAIL entries" item
can be checked. The gate nonetheless remains **closed** on the separate,
approval-gated training-readiness items that are unrelated to mechanics fidelity:

- mechanically-stale v5/v6 data/checkpoint disposition,
- value-label quality audit,
- larger-dataset value learning,
- live action-ranker loader hardening,
- any checkpoint approved for production/live use.

Training, rematerialization, checkpoint promotion, and live-default changes must
not proceed without that explicit approval.

## Next recommendation

Mechanics fidelity is complete. The next step is **not** code — it is the
approval-gated training-readiness review: confirm the stale-data disposition and
decide whether to (a) rematerialize a tiny diagnostic dataset on the now-fidelity-
clean v6 impact path and re-run the value/action-rank diagnostics, or (b) design
the v7 typed-effect schema to convert high-value INEXACT moves (secondary status,
item-delta, delayed damage) to PASS before a larger build. Both remain closed
pending explicit user approval.
