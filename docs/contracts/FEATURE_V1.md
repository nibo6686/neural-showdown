# feature-v1

Input: an addressed `observable-battle-state/v2` observation and that exact own
request (or null). `featurize` reads **only** `perspective`, `schema_version`,
`view`, and `request`. It never reads protocol history, K, labels, seeds or
opponent requests. The caller supplies validated observations (born exporter or
benchmark). Unlisted vocabulary literals reject; they are not silently mapped.

The pinned `vocab_b8f23c99.json` is generated from the installed, integrity-checked
engine. Each category reserves **PAD=0, UNKNOWN=1, ABSENT=2**; remaining IDs are
lexically sorted engine IDs. Conditions include dex Conditions plus move/ability
conditions; weather/terrain/effect namespaces deliberately share that superset.
The SHA-256 is pinned in `feature_v1.py`. Static move data supplies **base**
priority and accuracy, not inferred effective values.

All arrays use native NumPy little-endian int32/float32, uint8 or bool. `P=12`:
own slots 0â€“5, opponent public appearance slots 6â€“11. `A` is the number of
canonical legal indices, in request order (0â€“13). `C=167` condition vocabulary
entries in this version. One field token consumes the three field arrays;
PokÃ©mon and action tokens consume their corresponding arrays.

| Tensor | Shape / dtype | Source and order |
|---|---|---|
| pokemon_cat | PÃ—11 int32 | displayed species; item; ability; status; types 1,2; Tera type; moves 1â€“4 |
| pokemon_num | PÃ—22 float32 | HP ratio; level/100; atk,def,spa,spd,spe /500; active request PP/maxPP for slots 1â€“4; seven boosts /6; active,fainted,terastallized,appearance-uncertain booleans |
| pokemon_num_state | PÃ—22 uint8 | Each numeric: UNKNOWN=0, KNOWN=1, ABSENT=2, PAD=3. Unknown/absent/pad numeric payload is zero, never authoritative alone. Known zero retains KNOWN. |
| pokemon_presence | P uint8 | PAD=0 beyond publicly known team size; UNREVEALED=1; OBSERVED=2 |
| pokemon_mask | P bool | presence != PAD; unrevealed opponents remain valid placeholder tokens |
| pokemon_effects | PÃ—C bool | Typed public volatiles; a revealed empty list is known empty; unrevealed rows have presence=1 |
| field_cat | 2 int32 | Typed public weather, terrain; null or explicit `none` means known absent |
| field_num | 1 float32 | Public turn/100, known |
| field_effects | 3Ã—C float32 | pseudo-weather presence (0/1); self then opponent side-condition layers/3. Complete public maps: unlisted entries are known absent, not unknown. |
| action_cat | AÃ—4 int32 | action-kind vocabulary ID; move ID; type ID; damage-category vocabulary ID (all reserve PAD/UNKNOWN/ABSENT) |
| action_num | AÃ—6 float32 | request base power/250; dex base priority/7; dex base accuracy [0,1]; request PP/maxPP; disabled; Tera variant |
| action_num_state | AÃ—6 uint8 | Same numeric state codes; move-only fields ABSENT on switch/revive |
| action_target | A int32 | Own PokÃ©mon token index for switch/revive, bound via request slot â†’ ident â†’ own view slot; -1 for moves |
| action_indices | A int32 | Exact request legal indices; no fixed 13-output policy authority |
| action_mask | A bool | All true: only legal actions are materialized |

Boost order: atk,def,spa,spd,spe,accuracy,evasion. Own stats, moves, ability,
item and Tera use own typed view; PP uses the current own request. Bench PP is
unknown. Pokemon-slot PP requires a matching own move ID and a non-transformed
actor; copied option PP is not attached to base roster moves. Action PP still
describes the current request option. Locked request `disabled` is unknown when
normalization hides omission (zero maxPP); Struggle emits disabled explicitly.
Canonical default is not an attack: its power/priority/accuracy/type/category
are absent, PP/disabled unknown, and Tera-variant false is known. Recharge/Struggle PP is unknown because normalized requests cannot
prove emission presence. Opponent boosts use `public_boosts` (null is unknown).
Opponent stats, moves and ability identities are unknown because v2 omits them.
Opponent Tera identity remains UNKNOWN: v2 omits it, and Stellar prevents
inferring it from defensive types. The typed Terastallization boolean is encoded. One-type PokÃ©mon have an ABSENT second type; unrevealed types are
UNKNOWN. Explicit `???` in a typed type list denotes a removed type (Double
Shock), encoded ABSENT. The uncertainty numeric preserves an uncertain displayed appearance.

Own `item_state=none/removed/consumed` plus null item means ABSENT (including
Knock Off). Unknown own items remain UNKNOWN. Opponent `has-item` carries no
identity; omitted opponent item cannot distinguish unknown from removal, so
both remain UNKNOWN. Feature-v1 does not reparse history to recover omitted
public knowledge. Empty move slots on an observed own move list are ABSENT;
opponent/unrevealed moves remain UNKNOWN. Status null is ABSENT only with a
non-unknown typed status source.

Dataset storage pads A to 13 with action_mask=false, target/index=-1 and other
payloads zero. Consumers must use the mask. Shards also contain human_action
(int32 legal-list index), outcome (float32 owner win=1/loss=0/tie=.5), ending
(Unicode normal/forfeit/inactivity), rating (float32) with rating_known (bool),
battle_id and owner (Unicode), step (int32). Unknown rating has payload zero
and rating_known=false. These labels/metadata never enter featurize.

Splits are by battle: sort SHA-256(`seed + ':' + battle_id`), first floor(.90N)
train, next through floor(.95N) validation, remainder test. The source list,
seed and exact battle lists are recorded. A replay contributes examples only
after complete exact reproduction; failed partial battles are discarded.
