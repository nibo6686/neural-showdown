# Randbats Joint Set Posterior Fidelity Audit

## Scope and question

Audit-only. Randbats-only. No v8 schema/features, no scraping, no regeneration,
no sampling, no materialization, no training, no live-behavior change.

Core question: does `data/random-battles/gen9/sets.json` contain enough
structure to represent **joint** set/archetype hypotheses more faithfully than
the current factorized adapter, such that one public reveal (move, ability,
item, Tera) collapses the posterior toward a coherent role/set rather than
merely updating independent marginals?

Source pinned for this audit:

- file: `data/random-battles/gen9/sets.json`
- SHA-256: `7dc75740d17755d921c473fca68b3022f6f37a2af387d3cd9c94432bd646eaef`
- loader: `live_opponent_beliefs.load_randbats_index`
- adapter under audit: `neural/randbats_meta_prior_source.py`
  (`randbats-role-data-adapter-v1`)
- posterior under audit: `neural/opponent_set_belief.py`

## Headline finding

**The current adapter does not lose the joint correlations that `sets.json`
actually contains.** Each emitted hypothesis is bundled per declared set
(`role` + that set's `movepool` support + one `ability` + one `teraType`), so a
move, ability, or Tera reveal already collapses the posterior toward a coherent
role through `OpponentSetBelief.update`, not merely an independent marginal.
Verified live on real source rows (see "Observed current behavior").

The "factorized" label is therefore narrower than it sounds. The only
factorization the adapter introduces is the **within-set ability × Tera cross
product**, which is faithful to the generator (it draws ability and Tera
independently per role). What `sets.json` genuinely cannot express — exact
four-move sets with combo/incompatibility rules, items, and role/move
frequencies — is **absent from the source entirely** and cannot be recovered by
any smarter static adapter. It requires the generator-sampled snapshot already
specified in `v8_meta_prior_opponent_set_belief_design.md` §4.

There is exactly one real, source-faithful, in-scope fidelity gap, and it lives
in the **posterior conditioning, not the adapter**: an item reveal (and any
attribute the source structurally lacks) currently triggers a false
`prior_contradiction` that nukes the whole role/move/ability/Tera posterior,
instead of being absorbed by the explicit unknown tail as a confirmed public
fact.

## 1. What structure exists in `sets.json`

Measured across the full file: **508 species/forms, 877 sets.**

Every set has exactly four fields and nothing else:

| Field | Present | Notes |
|---|---|---|
| `role` | 877/877 | e.g. `Bulky Setup`, `AV Pivot`, `Bulky Support` |
| `movepool` | 877/877 | 5–7 moves; a **support superset**, not a four-move set |
| `abilities` | 877/877 | alternative abilities for that role |
| `teraTypes` | 877/877 | alternative Tera types for that role |
| items | absent | no item field anywhere in the file |
| probabilities/weights | absent | no per-set or per-move frequency |
| bundled/combo moves | absent | no 4-move subsets, no incompatibility rules |
| `level` | per species | tuning only, not a set hypothesis field |

Joint correlation that *does* exist, by how it varies across a species' sets:

- sets-per-species: 204 single-set, 239 two-set, 65 three-set (304 multi-set);
- of 304 multi-set species, **role-specific moves** exist in **299** (movepool
  is bundled to role almost universally);
- **Tera list varies by role** in **224** of 304;
- **ability list varies by role** in **45** of 304.

So `sets.json` encodes a genuine role-conditioned joint over
`{movepool support, ability options, Tera options}`. It does **not** encode any
joint involving items, exact move combinations, or frequency.

## 2. Where the older brittle shortcut uses this data

`live_opponent_beliefs.build_opponent_beliefs` is the older path. It:

- loads the same `sets.json` via `load_randbats_index`;
- filters candidate sets against revealed moves/ability/item/Tera
  (`_filter_candidates_for_reveal`), **relaxing** a filter (and warning) when a
  reveal eliminates everything;
- emits up to five `top_candidates` plus independent **marginal** distributions
  for abilities/items/Tera (`_distribution_from_candidates`).

Two brittleness points relevant to this audit:

1. it exposes mostly independent marginals to downstream consumers, discarding
   the role bundle when it flattens to ability/item/Tera distributions;
2. `damage_engine._opponent_view_mon` (per the v8 design audit) fills missing
   ability/item/Tera from the **first marginal entry**, which can fabricate an
   illegal pseudo-set. That is the anti-pattern v8 must avoid; it is not how the
   new `OpponentSetBelief` posterior behaves.

The new contract path (`randbats_meta_prior_source` + `opponent_set_belief`)
already improves on (1): it keeps the role bundle inside each hypothesis.

## 3. What correlations the current factorized adapter loses

Precisely:

- **Within-set ability × Tera independence (benign).** A set with abilities
  `[A, B]` and Tera `[X, Y]` is expanded to four equally weighted hypotheses
  `A-X, A-Y, B-X, B-Y`. This is faithful: the generator draws ability and Tera
  independently per role, so no real correlation is destroyed and no *illegal*
  joint is invented (every combination is within one declared set).
- **Equal role weighting (mildly lossy, roughly faithful).** No source weights
  exist; the adapter weights roles equally. The Showdown generator selects a
  role by near-uniform sampling among a species' sets, so equal weighting is a
  reasonable, honestly labeled approximation rather than a fabricated
  distribution.

What is **not** lost by the adapter because it was **never in the source**:

- exact four-move sets and move incompatibility/combo/guaranteed-move rules;
- which 4 of the 5–7 movepool moves co-occur, and their probabilities;
- items (entirely absent);
- empirical move/role frequencies.

These are generator-only facts (design §4). No static-`sets.json` adapter can
reconstruct them without sampling the generator, which is explicitly out of
scope here.

## Observed current behavior (verified on real source rows)

Reproduced through `initialize_belief` + `OpponentSetBelief.update`:

| Reveal | Species | Result | Joint collapse? |
|---|---|---|---|
| Ability `Water Absorb` | Clodsire | `unaware` ruled out; both roles kept | ability marginal, both roles legal |
| Move `Curse` | Clodsire | collapses to `bulkyattacker` only | **yes** — move→role |
| Move `Spikes` | Clodsire | collapses to `bulkysupport` only | **yes** — move→role |
| Tera `Fighting` | Gholdengo | collapses to `bulkyattacker` set | **yes** — Tera→role |
| Reflected `Stealth Rock` (`[from] ability: Magic Bounce`) | Hatterene | confirms `magicbounce`; **not** added as a move | reflection not polluted |
| Item `Leftovers` | Gholdengo | **false `prior_contradiction`**, support → 0, tail → 1.0 | **gap** |

The Clodsire/Gholdengo move and Tera cases prove the joint role bundle survives
into the posterior: a single reveal yields a coherent role, not just an updated
marginal. The item case is the one genuine fidelity failure.

These are locked in by `trainer/tests/test_randbats_joint_set_posterior_fidelity.py`.

## 4. Can we represent joint hypotheses without scraping/regenerating/sampling?

For the structure the source *contains* — yes, and it already is. Each
hypothesis carries `(role, movepool support, ability, tera_type)`. No new data
is needed to preserve role↔move↔ability↔Tera correlation.

For the structure the source *lacks* (exact sets, items, frequencies) — no. By
construction those facts are not in `sets.json`. Representing them faithfully
requires the generator-sampled snapshot (design §4) or a usage source, both out
of scope for this Randbats audit.

## 5. The honest fallback when exact joint sets are unavailable

The current implementation already matches the recommended honest fallback, and
should keep doing so:

- factorized/role-level joint hypotheses (role-bundled, ability×Tera expanded);
- explicit unknown tail (`other_mass`, currently `0.5`, policy-flagged);
- `joint_quality = FACTORIZED`;
- per-approximation `coverage_warnings`
  (`role_declarations_are_not_complete_generated_sets`,
  `movepool_is_not_an_exact_four_move_set`,
  `items_absent_from_existing_role_data`,
  `role_weights_unavailable_equal_weight_assumption`,
  `unvalidated_unknown_tail_policy:0.5`);
- `sample_count = 0` and pinned source SHA-256 as source-quality metadata.

The only honesty defect is that the posterior currently converts a
source-absent attribute reveal into a contradiction rather than into tail mass +
a confirmed fact (item case above; the prior public-prefix audit reported 45.25%
of slots reaching contradiction, item reveals dominating).

## 6. Minimal improvement that preserves more correlation, source-faithfully

The adapter itself needs **no change** to preserve more correlation — it already
preserves everything `sets.json` carries. The minimal, source-faithful,
correlation-preserving improvement is in the **posterior conditioning**, and it
is the highest-value pre-v8 fix:

> When a revealed attribute is one the pinned source structurally does not carry
> (item always; and, with an explicit alias/dynamic-ability policy, abilities or
> moves outside coarse support), **record it as a confirmed public fact and let
> the existing unknown tail absorb it — do not declare `prior_contradiction` and
> do not drop the role/move/ability/Tera hypotheses.**

Concretely, distinguish two cases that `update` currently conflates:

1. **source-covered attribute, reveal incompatible with all hypotheses** →
   legitimate contradiction (keep current behavior); the snapshot genuinely
   failed to cover reality.
2. **source-uncovered attribute** (e.g. `item` when every hypothesis has
   `item is None`, i.e. the source never claimed items) → confirm the fact,
   keep hypotheses, absorb into `other_mass`. This is "the source doesn't know,"
   not "the reveal contradicts the source."

This is design-consistent (design §"Contradictions and incomplete sources"
already separates "snapshot did not cover reality" from "the reveal did not
happen") and is a prerequisite the prior public-prefix audit already flagged
(item collapses + Trace/Transform/composite-form separation + alias policy).

It is intentionally **not implemented in this audit task** (audit-only). It
should be its own small, tested change to `opponent_set_belief.py` before any v8
feature wiring, then re-run the public-prefix audit.

Note: this still does not give calibrated joint probabilities. The equal-weight
role split and coarse movepool support remain uncalibrated; calibrated joint
probabilities remain a generator-snapshot job, not a `sets.json` job.

## 7. How constructed-format Smogon / co-usage priors fit later (not now)

Out of scope to implement; recorded for continuity and consistent with the v8
design §5:

- **Smogon individual usage** → a `MetaPriorSource` providing per-Pokémon
  ability/item/move/spread/Tera **marginals**, imported with
  `joint_quality = FACTORIZED` (or `RECONSTRUCTED`), pinned month/format/rating
  cutoff/checksum, and an explicit unknown tail. It must not claim exact joint
  sets.
- **Smogon co-usage / team-builder stats** → a future, separate
  `TeamPriorSource` for team-level correlations, never folded into the
  per-Pokémon Randbats path.
- **Randbats stays per-Pokémon set/role posterior only.** Do not infer
  constructed-style team archetypes (Trick Room teams, weather cores, etc.) from
  Randbats data — `sets.json` has no team-composition signal, and Randbats teams
  are independently generated per slot subject only to duplicate-role limits.
- The strategic-collapse examples (Shell Smash + Weakness Policy, Trick Room
  archetypes, Extreme Killer Arceus) are valid **constructed-format** posterior
  illustrations; they must not be hardcoded as Randbats strategy.

## Conclusion

- Does the current adapter lose important joint correlations? **No** — it
  preserves all role↔move↔ability↔Tera correlation that `sets.json` contains,
  and a single move/ability/Tera reveal already collapses the posterior to a
  coherent role.
- Does `sets.json` support better joint hypotheses than the adapter emits?
  **No** — the richer joint facts (exact sets, items, frequencies) are not in
  the source; recovering them needs the generator snapshot.
- Recommended adapter change: **none to the adapter.** The single recommended
  change is a posterior-conditioning fix so source-absent reveals (items first)
  are absorbed by the unknown tail instead of forcing a false contradiction.
  Deferred to its own tested change before v8 feature wiring.

This keeps the project on the design's stated path: faithful factorized
role-level Randbats priors now, generator-sampled calibrated joint snapshot for
real v8 belief features, Smogon/co-usage reserved for constructed formats.
