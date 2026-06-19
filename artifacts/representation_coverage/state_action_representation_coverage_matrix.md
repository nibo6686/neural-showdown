# State/Action Representation Coverage Matrix

**Date:** 2026-06-19  
**Audited path:** Pokémon Showdown 0.11.10 truth → legal public/private observation →
sim-core view/request → `live-private-belief-v2` (115D) and
`legal-action-v3` (165D).

Diagnostic append-only state schemas now also cover Slice 1 v3 (217D), Slice 2
v4 (765D), Slice 3 v5 (2293D), Slice 4 v6 (2493D), and Slice 5 v7 (3208D).
Diagnostic action schemas cover Slice 5 `legal-action-v4` (269D) and Slice 6
`legal-action-v5` (318D), whose first 269 dimensions are the exact v4 vector.
Production remains on v2.

Slice 5 update: rows for own/opponent move slots, PP and disabled state
(`Moves and PP`), Disable / recharge / two-turn / Choice lock
(`Volatiles/constraints`), and action self/target stat deltas, recharge/lock-in,
classification and Tera/switch-target identity (`Action features`) are now
implemented diagnostically in `live-private-belief-v7` and `legal-action-v4`.
Slice 6 additionally represents resolved immediate damage/range, KO,
effectiveness, accuracy and provenance. Authoritative full next-state deltas
still require seeded transitions, so that distinction remains open. Per-row
status lives in the JSON
`implementation_status` field. Production still consumes v2 / legal-action-v3.

The machine-readable companion contains the same findings with longer gap and
recommendation text:
`state_action_representation_coverage_matrix.json`.

## Source-of-truth boundary

- True state: `pokemon-showdown/sim/pokemon.ts`, `side.ts`, `field.ts`,
  `battle.ts`, and `state.ts`.
- Public/revealed state: `pokemon-showdown/sim/SIM-PROTOCOL.md` plus each
  player's `|request|` JSON.
- sim-core: `state_extractor.ts`, `types.ts`, and `action_codec.ts`.
- AI state: current serving/value/ranker state input
  `live-private-belief-v2`, 115 dimensions.
- AI action: `legal-action-v3`, 165 dimensions.

The older local-simulator featurizer is materially richer in two places: it has
current-type one-hots and seven separate stat-stage values per Pokémon. Those
fields are **not** present in the current 115D serving/value/ranker state vector,
so they do not remove the retraining blockers below.

Priority meanings:

- `blocker_before_retraining`: old-schema aliasing would make a rebuild/retrain
  knowingly wasteful.
- `important_vnext`: should be in the next version, but can follow the corrected
  core schema.
- `nice_to_have`: useful lower-impact context.
- `long_tail_regression`: preserve with targeted mechanics tests.

## Matrix

| Category | Mechanic/state field | Showdown source/truth | Publicly observable? | sim-core extracted view | AI feature encoding | Identity preserved? | Counterfactual test exists? | Priority | Gap | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core identity | Species/base species | `Pokemon.baseSpecies/species` | Displayed species public; base may differ | **Slice 3:** separate base/current/displayed species | **v5 diagnostic:** stable dual hashes + provenance | Yes in v5; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; no v5 model | Preserve exact/public boundary when rebuilding |
| Core identity | Transform/original identity | `transformed`, species/stats/moves, `-transform` | Transform target public | **Slice 3:** Transform updates current species and retains base | **v5:** base/current hashes + transformed flag | Yes in v5 | Yes | `blocker_before_retraining` | Copied moves/stats remain future slices | Preserve identity split; add copied move/stat representation later |
| Core identity | Illusion/display identity | `illusion`, `replace` | Display public; truth revealed later | **Slice 3:** active slot reconciled on `replace` | **v5:** displayed/current/base + uncertainty/reveal flags | Partial | Yes | `important_vnext` | Historical move reconciliation remains conservative | Retain slot/display separation and regression coverage |
| Core identity | Level/gender/form/active | Pokémon fields; details/form protocol | Generally public after reveal | Level/gender/active yes; `-formechange` absent | Active aggregate only | Partial | Partial | `important_vnext` | Level/form effects lost | Add level/current form; handle `-formechange` |
| HP/fainting | HP/max HP/fraction/faint | `hp/maxhp/fainted`; request condition | Own exact, foe public fraction | HP ratio/text/faint retained | Good fractional/count coverage | Partial | Yes | `important_vnext` | Exact own max HP and stable slot link absent | Keep fractions; optionally add normalized own exact HP |
| HP/fainting | Substitute HP | Substitute EffectState | Existence public; exact HP limited | Volatile name only | Substitute booleans | Partial | Existence only | `nice_to_have` | No durability estimate | Track only public evidence/bounds |
| Typing | Base/current types | `baseTypes/types/addedType/apparentType` | Public type-change events | Species/Tera types only | No live-v2 type identity | No | No | `blocker_before_retraining` | Current typing absent/stale | Encode base-inferred and public current types separately |
| Typing | Soak/Protean/type changes | `typechange/typeadd` protocol/data | Public when announced | Generic volatile; `types` unchanged | Count at most | No | No | `blocker_before_retraining` | Soaked state aliases base state | Add current-type event handling and counterfactual |
| Typing | Tera current type | `teraType/terastallized/baseTypes` | Own known; used type public | Retained | State has flags only; action has type | Partial | Partial | `blocker_before_retraining` | State value cannot distinguish Tera types | Add own/revealed current Tera one-hots |
| Stats/stages | Seven stat stages | `Pokemon.boosts`; full boost protocol | Active stages public | Per-stat simple events; incomplete swap/invert/copy/partial clear | Signed total only | No | Simple changes only | `blocker_before_retraining` | SpA and Speed alias | Add seven own/opponent stages and complete handlers |
| Stats/stages | Own/current raw stats | `baseStoredStats/storedStats/getStat` | Own exact; foe hidden | Own raw stats retained | Dropped from live v2 | No | Damage tests only | `blocker_before_retraining` | Own stat profile invisible | Add normalized own active stats; foe belief summaries only |
| Stats/stages | Effective speed/order | Speed + stages/status/field/abilities | Own exact; foe inferred | Components separate | No combined order context | No | No | `blocker_before_retraining` | Order-sensitive decisions blind | Add effective-speed context and foe faster probability |
| Status | Major status identity | `status/statusState` | Public | **Slice 3:** status identity/provenance retained | **v5:** active and per-roster-slot status enums | Yes in v5; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; production remains coarse | Preserve status identity when rebuilding |
| Status | Sleep/toxic counters | `statusState` counters | Publicly inferable bounds | **Slice 3:** public elapsed evidence | **v5:** known mask + normalized elapsed turns | Partial | Yes | `important_vnext` | Hidden internal timer/stage intentionally excluded | Keep public bounds only |
| Volatiles/constraints | Substitute/Taunt/Encore/Leech Seed | `volatiles`, start/end | Public | Generic + tactical identity | Dedicated booleans | Yes | Yes | `important_vnext` | Duration/affected move missing | Retain; add public duration and affected move |
| Volatiles/constraints | Confusion/Torment/Perish/trap | `volatiles` EffectState | Public; counters inferable | Tracked raw/tactical | Volatile count only | No | Tracker partial | `important_vnext` | Distinct effects alias | Add dedicated flags/public counters |
| Volatiles/constraints | Disable identity | Disable + request `disabled` | Own slots exact | Disabled booleans retained | Count and candidate flag only | Partial | Legality only | `blocker_before_retraining` | Key move versus irrelevant move disabled aliases | Add per-slot mask and affected move identity |
| Volatiles/constraints | Recharge/two-turn/lock-in | `mustrecharge/twoturnmove/lockedmove` | Public | No dedicated protocol handling | Absent; diagnostic annotation only | No | No | `blocker_before_retraining` | Forced future action invisible | Add state flags and action commitment fields |
| Volatiles/constraints | Choice lock/maybeLocked | Request disabling, `maybeDisabled` | Own exact; foe belief | Legal mask reflects lock; maybe flags dropped | Counts only | No | Legality only | `blocker_before_retraining` | Locked move identity/uncertainty lost | Add own locked slot and legal foe belief fields |
| Volatiles/constraints | Protect chain | Protect + `stall` counter | Publicly derivable | Protect retained, counter absent | Indirect repeat/failure features | Partial | Partial | `important_vnext` | Success odds indirect | Add consecutive-chain count |
| Volatiles/constraints | Heal Block/attract/curse/flinch | Open volatile state/data | Usually public | Generic list | Count at most | No | No | `long_tail_regression` | Long-tail effects alias | Frequency-gated additions plus regressions |
| Items | Current held item identity | `item/itemState`; own request | Own exact; foe reveal/belief | Exact known item retained | **v4 diagnostic:** dual stable identity hashes + state/source | Yes in v4; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; production still knownness-only | Train only after remaining slices |
| Items | Removed/consumed/last item | `lastItem/usedItemThisTurn`, `-enditem` | Public with caveats | **Slice 2:** last item and lifecycle retained | **v4:** unknown/none/removed/consumed are distinct | Yes in v4 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; no v4 model | Preserve lifecycle when rebuilding |
| Items | Suppression/Boots evidence | Magic Room/Embargo/effect callbacks | Public/inferable | **Slice 2:** Magic Room suppression retained | **v4:** item suppression + Boots identity hashes | Partial | Yes for Magic Room/Boots | `important_vnext` | Embargo and inference remain | Add remaining generic suppression evidence later |
| Abilities | Base/current/revealed identity | `baseAbility/ability/abilityState` | Own exact; foe revealed/inferred | Exact known ability retained | **v4:** separate base/current dual identity hashes | Yes in v4; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; no v4 model | Preserve exact vs belief provenance |
| Abilities | Changed/suppressed/global | `-ability`, `-endability`, Neutralizing Gas | Public when announced | **Slice 2:** changed and direct suppression retained | **v4:** changed/suppressed state and identity | Partial | Yes for sourced change/`-endability` | `blocker_before_retraining` | Neutralizing Gas per-target suppression remains implicit in identity | Add generic global suppression context in later field slice |
| Moves/PP | Own slots/identity/PP/disable | `moveSlots`; request moves | Own exact | Fully retained | PP slots/counts; move identities absent in state | Partial | PP/legal yes | `blocker_before_retraining` | Own movesets alias | Add per-slot move encoder |
| Moves/PP | Foe revealed moves/PP evidence | Public move history; true set hidden | IDs/uses public | Revealed IDs/use counts retained | Counts only | No | No | `blocker_before_retraining` | Earthquake and Recover reveals alias | Encode revealed move identities and PP bounds |
| Moves/PP | Last move/result/lock | Last-move fields and public events | Public | Tactical raw state | Coarse failure/repeat only | Partial | Partial | `important_vnext` | Last move identity absent | Add last move ID/category/result |
| Tera | Availability/use/type/action | Tera fields and request | Own exact; foe type hidden until use | Good extraction/action legality | **v6 diagnostic:** availability/use/active/type/provenance | Yes in v6; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; no v6 model | Preserve request/protocol boundary when rebuilding |
| Field/side | Hazards/layers | `sideConditions` | Public | Retained | **v6:** separate Stealth Rock/Web and exact Spikes/Toxic Spikes layers | Yes | Yes | `important_vnext` | State identity complete; action removal consequence remains | Retain; add action deltas |
| Field/side | Screens/Tailwind | Side conditions/durations | Public | Retained by name | **v6:** separate perspective-relative identities + public elapsed evidence | Yes in v6; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; no v6 model | Preserve named effects when rebuilding |
| Field/side | Weather | `weather/weatherState` | Public | Identity retained | **v6:** explicit weather enum + public elapsed evidence | Yes in v6; no in v2 | Yes | `blocker_before_retraining` | Exact hidden duration intentionally excluded | Preserve legal public boundary |
| Field/side | Terrain | `terrain/terrainState` | Public | Identity retained | **v6:** explicit terrain enum + public elapsed evidence | Yes in v6; no in v2 | Yes | `blocker_before_retraining` | Exact hidden duration intentionally excluded | Preserve legal public boundary |
| Field/side | Trick/Gravity/Magic/Wonder Room | `pseudoWeather` | Public | Names retained | **v6:** separate state and public elapsed evidence | Yes in v6 | Yes | `important_vnext` | Implemented diagnostic-only | Retain named rooms |
| Field/side | Safeguard/Mist/other | Open side-condition map | Public | Generic map | **v6:** Safeguard and Mist explicit; other long tail absent | Partial | Yes for Safeguard/Mist | `nice_to_have` | Remaining rare conditions frequency-gated | Keep explicit common conditions |
| Team/global | Remaining/revealed roster | Side roster/counts | Counts/reveals public | Own full, foe revealed | **v5 diagnostic:** six ordered identity/unknown/placement/life slots | Yes in v5; no in v2 | Yes | `blocker_before_retraining` | Implemented diagnostic-only; opponent hidden slots stay unknown | Preserve request order/public reveal order and masks |
| Team/global | Turn/perspective/terminal/format | Battle state | Public | Retained | Turn/perspective good; format implicit | Partial | Perspective yes | `important_vnext` | Multi-format compatibility weak | Add format/version ID if mixed |
| Team/global | Randbats belief content | Hidden truth must stay hidden | Priors + reveals only | Sanitized belief paths | Counts/entropy, no content embedding | Partial | Privacy/determinism yes | `important_vnext` | Distinct distributions alias | Compact move/item/ability/Tera distribution embeddings |
| Action | Type/category/power/accuracy/priority | Dex/request metadata | Known | Mostly retained/static parsed | Dedicated features | Yes | Partial | `important_vnext` | Dynamic resolution not always captured | Add resolved current metadata |
| Action | Damage/range/effectiveness/KO | Simulator/calc | Computable under assumptions | Damage RPC + opt-in current-type override | **v5 diagnostic:** expected/min/max, KO, hit chance, effectiveness and provenance | Yes diagnostically; no live model | Yes, 10-case Slice 6 suite | `blocker_before_retraining` | Implemented diagnostic-only; belief calibration/training remains | Preserve provenance and benchmark before promotion |
| Action | Self/target stat deltas | Move boosts/self/secondary | Known/chance-based | Diagnostics parse some self effects | Setup flag only | No | Draco only | `blocker_before_retraining` | Draco/Close Combat/setup alias | Seven-stat signed expected deltas |
| Action | Recoil/crash/drain/heal | Move data + transition | Known/state-dependent | Diagnostic booleans | Recovery only | No | No | `blocker_before_retraining` | HP consequences invisible | Add expected self-HP delta/fractions |
| Action | Recharge/lock/two-turn | Move flags/volatiles | Known | Diagnostic booleans only | Absent | No | No | `blocker_before_retraining` | Commitment invisible | Add commitment flags/durations |
| Action | Pivot/setup/status/hazard/removal | Structured move effects | Known | Parsed flags/selected IDs | Partial flags | Partial | Partial | `important_vnext` | Quantitative target effects missing | Parse structured effects and deltas |
| Action | Tera action/consequence | Legal request + Tera mechanics | Own exact | Separate action kind | Strong action coverage | Yes | Yes | `important_vnext` | Defensive consequence unresolved | Add belief-conditioned defensive delta later |
| Action | Switch target representation | Own request + field | Own exact | Slot/species/data available | HP/status/knownness only | No | Partial | `blocker_before_retraining` | Switch targets alias | Add identity/type/stats/item/ability/moves/hazard delta |
| Action | Resulting-state delta | Authoritative post-transition state | Exact only in sim/research; estimated live | Branch tools available | **v5:** immediate opponent-HP estimate plus optional branch source; full deltas unavailable without transition | Partial | Draco/branch + Slice 6 | `blocker_before_retraining` | Immediate impact is not full future-position evaluation | Generate transition labels after final schema freeze |

## Coverage conclusion

Pokémon Showdown supplies the needed source-of-truth inventory. The primary
failure is downstream representation, not lack of upstream mechanics data:

1. sim-core has a useful public view but misses several protocol state mutations
   (`-transform`, `-formechange`, type changes, ability suppression, complex boost
   operations, recharge/two-turn state).
2. the current live state vector collapses many retained identities into counts,
   booleans or summed values.
3. the current action vector describes static move metadata well, but not general
   state consequences.

The full reindex/retrain remains blocked pending final schema freeze, replay-pool
profiling, a small diagnostic dataset, small/medium training benchmarks and the
remaining full-transition/switch/belief gaps.
