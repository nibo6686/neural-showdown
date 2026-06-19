# Retraining Blockers

**Decision:** Do **not** rebuild the full dataset or retrain production models on
the current schemas.

## Slice 1 update

The first representation slice is now implemented in diagnostic-only
`live-private-belief-v3`:

- seven own/opponent stat stages preserve identity;
- active base and current typing are separate;
- public Soak/type-change and Tera-current typing are preserved with provenance.

This closes the original SpA-versus-Speed alias and stale-current-type gap in the
new schema. It does not alter v2 or make v3 eligible for production retraining.

Slice 2 is implemented in immutable diagnostic-only `live-private-belief-v4`
(765D):

- own/public opponent current and last item identity;
- unknown/held/none/removed/consumed item states;
- item suppression;
- base/current ability identity;
- unknown/known/changed/none/suppressed ability states.

v2 and v3 remain unchanged. No v4 model exists, so production learned paths still
have the original item/ability blockers.

Slice 3 is implemented in immutable diagnostic-only `live-private-belief-v5`
(2293D):

- active base/current/displayed species identity and Transform state;
- Illusion displayed-versus-revealed identity evidence;
- six ordered own/public-opponent roster slots with unknown/active/bench and
  alive/fainted state;
- burn, paralysis, sleep, poison, toxic, freeze, none and unknown status;
- public sleep/Toxic elapsed evidence without hidden counter leakage.

v2/v3/v4 remain unchanged. No v5 model exists.

Slice 4 is implemented in immutable diagnostic-only `live-private-belief-v6`
(2493D):

- own/public-opponent Tera availability, use, active state, type and provenance;
- explicit weather and terrain identity;
- Trick Room, Gravity, Magic Room and Wonder Room;
- separate screens, Tailwind, Safeguard and Mist by relative side;
- exact public hazard identities and layer counts;
- public elapsed-turn evidence without hidden duration leakage.

v2/v3/v4/v5 remain unchanged. No v6 model exists.

Slice 5 is implemented in immutable diagnostic-only `live-private-belief-v7`
(3208D) plus diagnostic `legal-action-v4` (269D):

- own per-slot move identity, exact PP and disabled state from the request;
- opponent per-slot revealed move identity (protocol-only, PP unknown);
- known-vs-unknown move slots kept distinct;
- recharge, two-turn lock, soft single-move lock, Encore lock and inferred
  Choice lock; Taunt/Torment/Heal Block/Imprison/Disable states;
- action self/opponent per-stat deltas (Draco Meteor self SpA drop, Curse vs
  Bulk Up), recoil/drain/recharge/lock/pivot effects, classification, command
  identity and switch-target identity.

v2/v3/v4/v5/v6 and `legal-action-v3` remain unchanged. No v7 / legal-action-v4
model exists. Slice 5 is **diagnostic-only and not sufficient for full
retraining by itself** — it closes the move/action-consequence representation
gaps but does not produce a trained candidate.

Slice 6 is implemented in immutable diagnostic-only `legal-action-v5` (318D).
It preserves the exact 269D v4 prefix and adds expected/min/max damage, KO
chance, accuracy, effectiveness/immunity, provenance and explicit unavailable,
non-damaging and switch handling. Current typing/Tera, stat stages and supported
field inputs affect the diagnostic calculation. No live default or checkpoint
changed.

The matrix contains 48 audited rows:

- 29 `blocker_before_retraining`
- 16 `important_vnext`
- 2 `nice_to_have`
- 1 `long_tail_regression`

## Top blockers

1. **Production state identity remains stale.** v5 now preserves active species,
   known roster species and major status diagnostically, but the live 115D v2
   path still does not.
2. **v2 still collapses per-stat stages.** v3 fixes this, but all current
   production checkpoints still consume v2.
3. **v2 still lacks current typing.** sim-core and v3 now preserve public
   Soak/type-change state, but existing checkpoints cannot consume it.
4. **Production status identity is collapsed.** v5 distinguishes burn,
   paralysis, sleep, poison, toxic and freeze, but current checkpoints still use
   coarse v2 status counts.
5. **Production item state remains ambiguous.** v4 now distinguishes identity,
   unknown, confirmed none, removed, consumed and suppressed states, but current
   checkpoints still consume v2.
6. **Production ability state remains ambiguous.** v4 now separates base/current,
   changed and directly suppressed ability state, but no learned checkpoint uses it.
7. **Action constraints are incomplete.** v7 now represents Disable, Choice lock
   (inferred), recharge, two-turn moves, Encore lock and forced lock-in
   diagnostically, plus own/opponent per-slot move identity and exact own PP, but
   production v2 still consumes only coarse counts.
8. **Production field identity is collapsed.** v6 fixes weather, terrain,
   rooms, screens, Tailwind and hazards diagnostically, but production v2 still
   consumes booleans/counts.
9. **Production Tera state is incomplete.** v6 adds exact legal
   request/protocol identity and state, but no learned checkpoint consumes it.
10. **Action consequences are diagnostically expanded.** `legal-action-v4` adds
    signed self/target stat deltas, recoil, drain, recharge, lock-in, pivot and
    classification fields diagnostically (Draco Meteor's self SpA drop is now
    explicit). `legal-action-v5` adds resolved damage/range, KO chance,
    accuracy, effectiveness and provenance. Full authoritative resulting-state
    deltas still require transition labels, and no v4/v5 ranker checkpoint exists.
11. **Switch actions are under-described.** v4 adds switch-target identity hash,
    known flag and slot; candidate typing, raw stats, item/ability identity and
    moveset embeddings are still omitted.
12. **Important public belief content collapses to counts.** Revealed moves and
    candidate item/ability/Tera distributions lose their identities.

## Upstream availability

The installed Pokémon Showdown package provides the needed source-of-truth list:

- `sim/pokemon.ts` exposes true species, original/current stats, boosts, status,
  volatiles, item, ability, trapping, Transform, Tera and action history.
- `sim/side.ts` and `sim/field.ts` expose requests, side conditions, weather,
  terrain and pseudo-weather.
- `sim/SIM-PROTOCOL.md` documents the legal public event stream, including
  identity changes, boost mutations, item/ability changes, Transform, volatile
  state and field state.
- `data/moves.ts`, `conditions.ts`, `items.ts` and `abilities.ts` define general
  action consequences and mechanic state.

The audit therefore does not need a speculative hand-maintained mechanic list.
The source data exists; extraction and feature preservation need versioning.

## Retraining gate

A full rebuild/retrain should remain blocked until, at minimum, Slices 1–4 plus:

- active species and known roster identity are distinguishable;
- major status, item and ability identities are represented with legal
  public/private provenance;
- weather, terrain, screens/Tailwind and Tera types are distinct;
- own/revealed move identities and key locks are represented;
- action features include general signed consequences and damage provenance;
- switch targets are represented materially;
- blocker counterfactuals pass perspective and information-boundary tests.

Slices 1–6 counterfactuals now pass: stat stages, typing, item/ability, species/
roster/status, Tera/field, and now move identity, revealed PP/disable state,
lock/recharge/Encore/Choice constraints, and action consequences (signed self/
target stat deltas, recoil, recharge, lock-in, pivot, switch-target identity,
resolved damage/range, KO chance, effectiveness, accuracy and provenance).

Still blocking full reindexing: final state/action schema freeze, replay-pool
profiling, diagnostic dataset generation, small/medium training benchmarks, full
resulting-state labels where required, richer switch-candidate material, and
public belief identity. Slice 6 is diagnostic-only and is not itself permission
to launch the full rebuild.

Training before these gates would preserve known feature aliasing and force
another full reindex immediately afterward.
