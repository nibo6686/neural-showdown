# Counterfactual Test Plan

Each test should construct two states that differ in exactly one public/private
legal field, then check four layers:

1. Showdown transition/protocol contains the intended change.
2. sim-core view/request changes only the intended representation.
3. old schema demonstrates the known alias when applicable.
4. vNext feature vector changes with correct perspective and no hidden leak.

## Blocker tests

| Test | Controlled mutation | sim-core assertion | Old-schema assertion | vNext assertion |
| --- | --- | --- | --- | --- |
| Species identity | Same HP/status, Latios versus Garchomp | Active `species` differs | 115D may remain identical/near-identical | Species encoding differs |
| Transform | Ditto before/after Transform | Original species retained; current species/stats/moves/types copied; transformed flag set | Old live vector misses distinction | Original/current fields differ correctly |
| Current typing/Soak | Same Pokémon before/after Soak | `types` becomes Water while species stays fixed | Old live vector identical except coarse volatile count | Current-type one-hot differs; base type stable |
| Tera type | Same state, used Fire Tera versus Water Tera | `tera_type/types` differ | State vector currently only sees used/known | Tera/current type differs |
| Per-stat stages | Own SpA −6 versus Speed −6 | Correct boost key differs | Old 115D vectors equal | Seven-stage vectors differ |
| Complex boosts | Swap/invert/copy/clear-positive/clear-negative | Per-stat view matches protocol operation | Expose current extractor gaps | vNext matches resulting stages |
| Raw own stats | Same species/HP with different legal exact stats | Request/view stats differ | Old live vector equal | Normalized stat fields differ |
| Effective order | Neutral versus paralysis/Tailwind/Trick Room combinations | Components extracted | No combined order context | Effective-order feature changes/sign flips |
| Status identity | Burn versus paralysis versus sleep at same HP | `status` differs only | Coarse status fraction equal | Active status one-hot differs |
| Disable slot | Disable strongest move versus weakest move | Different request slot disabled | Disabled count equal | Per-slot mask/move identity differs |
| Choice lock | Lock to move 1 versus move 2 | Legal actions/disabled slots differ | Counts can match | Locked slot/last move differs |
| Recharge | Hyper Beam post-state versus neutral identical HP | Recharge/forced action visible | Old state misses it | Recharge flag differs |
| Two-turn/lock-in | Fly/Outrage committed versus neutral | Phase/locked move differs | Old state misses or counts only | Commitment fields differ |
| Held item identity | Leftovers versus Choice Scarf | Own item differs | Both item-known = 1 | Item identity differs |
| Knock Off | Item unknown versus confirmed removed | View carries removal state/history | Both can become item-known = 0 | Item-state enum differs |
| Consumed item | Berry held versus consumed | Last item/cause retained | Held-known versus unknown ambiguity | Consumed state differs |
| Ability identity | Levitate versus Unaware | Current ability differs | Both ability-known = 1 | Ability identity differs |
| Ability change | Base ability versus Skill Swap/Entrainment result | Base/current differ | Knownness unchanged | Current/base fields differ |
| Ability suppression | Active ability versus Gastro Acid/Neutralizing Gas | Suppressed/global state differs | Old vector unchanged | Suppression flag differs |
| Own moveset | Equal PP counts, different four move identities | Request moves differ | State PP/count features equal | Move-set encoding differs |
| Revealed foe move | Reveal Earthquake versus Recover | `revealed_moves` differs | Revealed count equal | Revealed move encoding differs |
| Weather identity | Rain versus sun at same turn | `field.weather` differs | `weather_active` equal | Weather one-hot differs |
| Terrain identity | Electric versus Psychic Terrain | `field.terrain` differs | `terrain_active` equal | Terrain one-hot differs |
| Screen identity | Reflect versus Light Screen | Side condition key differs | Screen count equal | Dedicated flags differ |
| Tailwind versus screen | Tailwind versus Reflect | Side condition key differs | Current count can alias | Tailwind/order feature differs |
| Roster identity | Same remaining count, different known bench species | Team entries differ | Counts equal | Roster encoding differs |
| Damage impact | Same move metadata against two different current types | Damage RPC differs | Ranker action vector lacks damage | Damage/KO/effectiveness differ |
| Self stat delta | Draco Meteor versus clean same-power special move | Transition has SpA drop only for Draco | No signed delta field | Self `spa` delta differs |
| Target stat delta | Parting Shot/stat-drop move versus neutral analog | Target stage transition differs | Setup/status flags insufficient | Target signed deltas differ |
| Recoil/drain | Recoil versus no-recoil equal damage fixture | Post self HP differs | Recoil absent | Expected self-HP delta differs |
| Recharge/lock action | Hyper Beam/Outrage versus clean analog | Move metadata/transition differs | Commitment absent | Action commitment differs |
| Switch identity | Two healthy switches with equal HP/status but different species/types | Target slots differ | Current switch vectors can equal | Switch representation differs |
| Resulting-state delta | Identical pre-state, two simulator actions | Post-state delta differs | Metadata-only ranker can miss it | Transition-derived action target differs |

## Perspective and privacy checks

Every public-state test must also:

- featurize the same physical state from p1 and p2;
- swap own/opponent fields and negate signed differences where defined;
- verify categorical identities move to the opposite-side slots without changing
  their meaning;
- ensure own private exact stats/items/moves never appear as exact opponent fields;
- ensure opponent unrevealed values affect only belief/unknown masks, never exact
  feature slots.

## Recommended implementation order

1. Per-stat boosts and current typing.
2. Species/roster identity and own/revealed moves.
3. Item/ability/status/Tera identity and state enums.
4. Weather/terrain/screens/Tailwind and action constraints.
5. General action consequences and switch-target representation.
6. Long-tail mechanics and duration/counter regressions.

Do not rebuild datasets until steps 1–5 have stable ordered feature names and all
their counterfactual tests pass.
