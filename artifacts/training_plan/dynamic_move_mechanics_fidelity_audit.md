# Dynamic Move Mechanics Fidelity Audit

## Scope

This audit compares the v7/v6 reconstruction and resolved-impact path against Pokémon Showdown mechanics, using the existing sim-core `@smogon/calc` damage oracle plus Showdown's bundled move callbacks for dependencies the calculator does not model. v6 preserves the complete v5 prefix.

- Schema: `legal-action-v6`, 331D; unchanged 318D v5 prefix.
- Summary: **PASS 12 / FAIL 0 / NEEDS_VERIFICATION 0**.
- No training, dataset materialization, checkpoint promotion, or live-default change occurred.

## Results

| Mechanic | Required dependency | Showdown/sim-core source | v7 preservation | v5 use | Unknown handling | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rage Fist | Per-Pokémon successful attacks received (`timesAttacked`) | Showdown `Pokemon.timesAttacked`; Rage Fist callback. sim-core receives `times_attacked`. | Preserved in tactical snapshot with known/unknown provenance; not a new vector field. | Used to override Rage Fist BP before resolved impact. | Unknown history fails closed. | **PASS** | 0.3577 -> 0.7021 |
| Last Respects | Fainted allies (`side.totalFainted`) | Showdown side counter; Last Respects callback. sim-core receives `allies_fainted`. | Fainted own species/count are preserved. | Known count overrides Last Respects BP before resolved impact. | Incomplete history fails closed. | **PASS** | 0 vs 3 fainted: 0.3577 -> 1.0000 |
| Rollout / Fury Cutter | Consecutive successful-use volatile counters | Showdown per-Pokémon `rollout`/`furycutter` volatiles. | Protocol-complete tactical reconstruction preserves successful chain count, reset evidence, Defense Curl, and forced continuation. | v6 appends exact/provenance fields and supplies exact chain context to sim-core; the unchanged v5 prefix remains mechanically stale. | Unknown or non-exact repeat-chain state fails closed and is encoded as unknown, never zero. | **PASS** | Rollout 0.0830 -> 0.1642; Fury Cutter 0.3577 -> 0.7021 |
| Stored Power / Power Trip | Sum of positive user stat stages | `@smogon/calc` counts attacker boosts. | Own boost stages are preserved. | Known live tactical boosts are merged into the damage payload. | Unknown boost state fails closed for these moves. | **PASS** | direct 0.0454->0.4327; live-like 0.0454->0.4327 |
| Eruption / Water Spout / Reversal / Flail | Current/max user HP | `@smogon/calc` derives BP from current HP; Showdown marks Reversal/Flail as variable-power moves. | Own HP is preserved. | Known zero-metadata variable-power move IDs are routed to sim-core instead of classified as non-damaging. | Reversal/Flail fail closed when current HP is unavailable or the oracle fails. | **PASS** | Eruption 0.5636->0.2092; Reversal 0.0376->0.2810 |
| Facade / Hex / Venoshock | User or target status | `@smogon/calc` applies status-conditioned BP modifiers. | Own/opponent status is preserved. | Tactical statuses are merged into attacker/defender payloads. | Unknown opponent status is explicit in state, but impact assumes current supplied value. | **PASS** | Facade 0.3052->0.9088; Hex 0.5707->1.0000 |
| Knock Off / Acrobatics | Target/user held item | `@smogon/calc` reads held items. | Own item and known/inferred opponent item are represented. | Items are passed to sim-core. | Opponent item inference provenance exists, but impact is a point estimate. | **PASS** | Knock Off item/none 0.7929/0.5297; Acrobatics item/none 0.1839/0.3611 |
| Weather Ball / Terrain Pulse | Weather/terrain and grounding | `@smogon/calc` reads field state. | Weather, terrain, species, typing, and ability context are preserved. | Field and Pokémon context are passed to sim-core; its grounding check suppresses Terrain Pulse scaling for an airborne user. | The resolved impact remains a point estimate, with normal exact/inferred input flags. | **PASS** | Weather Ball 0.1332->0.3917; grounded Terrain Pulse 0.1198->0.3025; airborne 0.1432->0.1432 |
| Body Press / Foul Play | User Defense / target Attack as attack source | `@smogon/calc` selects nonstandard attack stats. | Exact own stats, public/inferred target state, and both sides' known boost stages are available. | Exact stats and known tactical boosts are passed to sim-core; Body Press uses user Defense while Foul Play uses target Attack. | Existing exact-stat and inferred-target flags expose approximation; no new field is required. | **PASS** | Body Press 0.0488->0.1469; Def+2/Atk+2 0.1923/0.0960; Foul Play 0.3577->1.0000; target/user Atk+2 1.0000/0.6633 |
| Gyro/Electro Ball and weight moves | Speed ratio or species weight ratio | `@smogon/calc` derives BP from stats/canonical species weights. | Species, exact/inferred stats, and known speed stages are preserved. | Known zero-metadata variable-power IDs are routed to sim-core; exact stats and species determine speed/weight formulas. | Missing species/context or oracle failure fails closed; exact-stat flags distinguish inferred speed inputs. | **PASS** | Gyro Ball 0.5000/0.0468; Electro Ball 0.4318/0.1182; Grass Knot 0.0600/0.1800; Low Kick 0.1225/0.3631; Heavy Slam 1.0000/0.4544; Heat Crash 0.9000/0.3034 |
| Curse (Ghost vs non-Ghost) | User's current Ghost typing | Showdown `onTryHit`: Ghost sacrifices HP/curses target; non-Ghost changes Atk/Def/Spe. | Current types are preserved. | Existing stat-delta and next-state fields are conditioned on current Ghost typing. | Unknown current type fails closed. | **PASS** | self deltas Ghost/non-Ghost: atk 0.0/0.5, def 0.0/0.5, spe 0.0/-0.5 |
| Accuracy-sensitive comparison | Move accuracy separate from conditional-on-hit damage | Showdown move accuracy; sim-core damage is conditional on hit. | No extra state dependency. | Stores hit chance and conditional damage separately; no explicit multiplied field. | Known accuracy is flagged; ranker must learn the interaction. | **PASS** | Psychic hit=1.00, adjusted=0.2279; Focus Blast hit=0.70, adjusted=0.1418 |

## Representative Counterfactual Gate

- Rage Fist: PASS after the `times_attacked` correction.
- Last Respects: PASS after fainted-ally count plumbing and unknown-history fail-closed behavior.
- Rollout/Fury Cutter: PASS in v6 with exact protocol-derived repeat count/provenance; unknown state fails closed.
- Stored Power: PASS after known tactical boosts are merged into damage input.
- Reversal/Flail: PASS after zero-metadata variable-power moves are routed to the HP-aware oracle.
- Speed/weight variable-power moves: PASS across both directions of each ratio dependency.
- Weather Ball/Terrain Pulse: PASS including a grounded-versus-airborne Terrain Pulse check.
- Body Press/Foul Play: PASS for exact-stat and boost-source counterfactuals.
- Facade/Hex: PASS with tactical status propagation.
- Curse: PASS using existing fields: non-Ghost stat deltas versus Ghost HP/status deltas.
- Accuracy: PASS as separate conditional damage and hit-chance fields; no explicit accuracy-adjusted feature exists.

## Schema and Staleness Decision

v6 appends repeat-chain context/provenance after the byte-identical 318D v5 prefix. v5 remains unchanged, but existing v5 datasets/checkpoints are mechanically stale for all repaired mechanics and cannot represent exact repeat-chain provenance. A v5 checkpoint must not load as v6.

## Gen 9 Random Battles Completeness Override

This 12-case counterfactual suite is representative, not exhaustive. The companion `gen9randbats_mechanics_completeness_audit.md` enumerates all 350 moves in the bundled Gen 9 Random Battles pool. After mechanics-repair batches 1-5 it classifies **138 PASS / 0 FAIL / 212 INEXACT / 0 NOT_RELEVANT** (was 121 / 176 / 53). With zero wrong-exact entries, the mechanics-fidelity criterion for the training gate is met; the gate now turns on the separate training-readiness review.

Batch 1 (`mechanics_repair_batch_1_fixed_multihit_accuracy.md`): Seismic Toss and Night Shade route level-based fixed damage through the oracle (PASS); Super Fang, Ruination, Endeavor, Mirror Coat and the 11 multi-hit moves fail closed (`impact_unknown`) -> INEXACT rather than wrong-exact; weather-dependent accuracy (Blizzard, Thunder, Hurricane, Bleakwind Storm) is computed from the protocol-observable weather and fails closed when no weather context is supplied.

Batch 2 (`mechanics_repair_batch_2_secondary_effects.md`): a coarse presence detector fills the existing next-state change flags (`next_opp_status_change`, `next_own_status_change`, `next_opp_stat_change`, `next_own_stat_change`) so secondary/primary status, volatile and stat effects are no longer encoded as a wrong-exact "no change". Exact status type, chance and magnitude stay unrepresented, so these moves are INEXACT (the four weather-accuracy moves now leave FAIL on this basis). Item-swap/copy/random-call status moves are flagged as non-damaging actions and noted as needing typed v7 fields.

Batch 3 (`mechanics_repair_batch_3_dynamic_type_charge.md`): sim-core returns the resolved (post-`calculate`) move type, so impact type-effectiveness and STAB use the actual dynamic type (Weather Ball, Terrain Pulse, Judgment, Ivy Cudgel, Raging Bull, Revelation Dance, Aura Wheel, Tera Blast -> PASS; Tera Starstorm fails closed on Stellar). Two-turn charge / delayed moves no longer emit on-hit damage as immediate: Solar Beam (sun/Power Herb) and Meteor Beam (Power Herb) are exact only when they fire this turn, otherwise fail closed; Future Sight always fails closed; Beak Blast is PASS (same-turn damage).

Batch 4 (`mechanics_repair_batch_4_conditional_execution_history_power.md`): conditional-execution and turn/history-power moves fail closed when success or power depends on the opponent's same-turn action, the first-active turn, the user's form, the target's item, within-turn order, or unplumbed prior-move-failure history (Fake Out, First Impression, Sucker Punch, Thunderclap, Focus Punch, Double Shock, Hyperspace Fury, Poltergeist, Payback, Avalanche, Lash Out, Stomping Tantrum, Temper Flare). Fusion Bolt / Fusion Flare and Pollen Puff are PASS (their doubling / ally-heal branch cannot occur in singles). Brick Break / Psychic Fangs keep exact screen-bypassing damage and coarsely flag the screen removal.

Batch 5 (`mechanics_repair_batch_5_final_failures.md`) cleared the final 9 FAILs to reach zero wrong-exact. PASS: Flower Trick / Wicked Blow (guaranteed crit baked into the calc rolls; crit_included=True), Freeze-Dry (sim-core reflects its special 2x-vs-Water effectiveness), Photon Geyser (calc selects the higher attacking stat and matching category, verified exact). INEXACT, fail-closed (damage itself wrong-exact): Beat Up (per-ally-Attack returns 0) and Fickle Beam (random double power). INEXACT, damage kept exact (only an unrepresented next-state effect remains, documented for v7): Knock Off (item removal), Bug Bite (stolen berry), Grassy Glide (terrain +1 priority). No schema name/order/dim changed; v6 remains 331D.

## Gate Decision

Training and further rematerialization must not proceed without explicit approval. The exhaustive move-pool mechanics criterion (every material move PASS or explicitly INEXACT/fail-closed) is now met with zero wrong-exact FAILs, so the gate turns on the separate training-readiness review (stale v5/v6 data/checkpoint disposition, value-label quality, larger-dataset value learning) rather than on mechanics fidelity.
