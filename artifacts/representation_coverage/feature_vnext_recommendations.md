# Feature vNext Recommendations

## Implementation status

Slice 1 is implemented as diagnostic-only `live-private-belief-v3` (217D):

- perspective-normalized seven-stat stages;
- separate active base/current type multi-hots;
- explicit type provenance;
- public type-change and Tera-current typing tracking.

The existing 115D v2 schema remains the live/default schema. No v3 checkpoint
has been trained or promoted.

Slice 2 is implemented as immutable diagnostic-only
`live-private-belief-v4` (765D):

- dual stable SHA-256 bucket encodings for current/last item and base/current ability;
- explicit item lifecycle and suppression state;
- explicit ability changed/suppressed state;
- perspective-relative own/opponent placement and source provenance.

No v4 checkpoint has been trained or promoted.

Slice 3 is implemented as immutable diagnostic-only
`live-private-belief-v5` (2293D):

- active base/current/displayed species identity;
- Transform and Illusion reveal state;
- six ordered own/public-opponent roster slots with explicit unknown masks;
- active and roster major-status identity;
- public sleep/Toxic elapsed evidence.

No v5 checkpoint has been trained or promoted.

Slice 4 is implemented as immutable diagnostic-only
`live-private-belief-v6` (2493D):

- own/public-opponent Tera availability, use, type and provenance;
- explicit weather, terrain and room identity;
- perspective-relative screens, Tailwind, Safeguard and Mist;
- exact public hazard identities/layers;
- public elapsed-turn evidence.

No v6 checkpoint has been trained or promoted.

Slice 5 is implemented as immutable diagnostic-only
`live-private-belief-v7` (3208D) and diagnostic `legal-action-v4` (269D):

- own per-slot move identity, exact PP and disabled state; opponent per-slot
  revealed move identity with unknown PP; known-vs-unknown slot masks;
- recharge, two-turn lock, soft single-move lock, Encore lock, inferred Choice
  lock, plus Taunt/Torment/Heal Block/Imprison/Disable states;
- action self/opponent per-stat deltas, recoil/drain/recharge/lock/pivot effects,
  classification, command identity and switch-target identity.

No v7 / legal-action-v4 checkpoint has been trained or promoted.

Slice 6 is implemented as immutable diagnostic-only `legal-action-v5` (318D):

- exact 269D `legal-action-v4` prefix;
- expected/min/max damage, uncertainty, KO and two-hit-KO proxy;
- hit chance, effectiveness, immunity, resistance and STAB;
- exact/approximate/unavailable and state-input provenance;
- graceful known-zero non-damaging handling and explicit switch/unavailable
  handling;
- immediate opponent-HP delta, with full branch-derived future deltas kept
  separate.

No legal-action-v5 checkpoint has been trained or promoted. Live/default action
features remain `legal-action-v3`.

## Versioning

Create new immutable schemas rather than mutating current dimensions:

- State: `live-private-belief-v7` (current diagnostic head)
- Action: `legal-action-v5` (current diagnostic head)
- Dataset metadata must store exact feature version, ordered names, dimensions,
  source commit/package versions and information-boundary mode.

Keep v2 through v7 and action-v3/v4 builders side by side during migration. Existing
checkpoints continue to load only with their exact old schema. Strict startup
must reject cross-version checkpoint use.

## Proposed state additions

### Core active identity

- own active current species identity;
- opponent active displayed/confirmed species identity;
- original/base species and `transformed` flag where legally known;
- normalized level;
- current active/bench slot masks.

Use a stable vocabulary or hashed/embedded categorical representation with an
unknown mask. Do not infer hidden true opponent identity beyond public/belief
state.

### Current mechanics

- current type slots and separately inferred base type slots;
- own/opponent `atk`, `def`, `spa`, `spd`, `spe`, `accuracy`, `evasion` stages;
- own exact active stats; opponent stat belief summaries, never hidden exact stats;
- major active status one-hots;
- weather and terrain one-hots;
- Reflect, Light Screen, Aurora Veil and Tailwind separately;
- Trick Room, Gravity, Magic Room and Wonder Room flags;
- public duration/counter bounds where derivable.

### Items, abilities and Tera

- own held-item identity;
- opponent revealed item and belief distribution;
- item-state enum: unknown, held known, confirmed none, consumed, removed,
  transferred;
- base/current ability identity, changed/suppressed flags;
- opponent revealed/current ability and belief distribution;
- own Tera availability/type/use/current type;
- opponent Tera availability/use and revealed type.

Every opponent field needs a provenance mask: `public_exact`, `private_own`,
`belief_distribution`, or `unknown`.

The current-type/stat-stage bullets are complete in Slice 1. Item and ability
identity/state bullets are complete in Slice 2. Species/roster and major-status
identity are complete in Slice 3. Tera and field identity are complete in
Slice 4. Move identity, PP/disable state and lock/recharge constraints are
complete in Slice 5 (`live-private-belief-v7`). The remaining bullets are planned.

### Moves and constraints

- own four move-slot identities and per-slot PP/disabled masks — **done (v7)**;
- opponent revealed move identities and public PP-use bounds — **done (v7)**
  (per-slot revealed identity + unknown-PP marker);
- own/opponent last public move and result — partially in tactical v2;
- Disable/Encore affected move — **done (v7)** (Encore lock + Disable state;
  Encore-locked move identity hash);
- Choice/forced lock move — **done (v7)** (inferred Choice lock, two-turn lock,
  forced switch, recharge);
- recharge, two-turn — **done (v7)**; partial trapping and perish/confusion
  counters/bounds — planned.

## Proposed action additions

### Resolved immediate impact

- damage mean/min/max — **done (legal-action-v5)**;
- KO chance and two-hit-KO proxy — **done (v5)**;
- effectiveness/immunity — **done (v5)**;
- exact/approximate/unavailable provenance — **done (v5)**;
- target known/inferred masks — **done (v5)**.

### General move consequences

- signed expected self and target deltas for all seven stages — **done
  (legal-action-v4)** (static moves.ts deltas; probability weighting planned);
- probability of each delta — planned;
- recoil/crash/drain/heal fraction — recoil/drain/heal booleans **done (v4)**;
  exact fractions planned;
- self-KO and target-status probabilities — planned;
- recharge, lock-in and two-turn commitment — **done (v4)**;
- pivot/forced-switch behavior — **done (v4)** (`effect_switch_move`,
  `cmd_forced_switch`);
- hazard set/remove and screen/field set/remove deltas — `class_hazard` **done
  (v4)**; explicit set/remove deltas planned.

These must be structural fields derived from Showdown move data or simulator
transitions—not move-name bans or hand-authored strategic rules.

### Switch candidate representation

- switch target species/current types;
- normalized stats and HP/status;
- item/ability/Tera identities;
- move-set embedding;
- resolved entry-hazard HP delta;
- relevant matchup damage/order summaries under opponent beliefs.

## Dataset implications

The state and action dimensions, feature ordering and labels will change.
Therefore:

- existing live-private value datasets are incompatible with state v3/v4/v5/v6/v7;
- existing action-rank and action-value datasets are incompatible with action
  v4/v5 and state v3+;
- all current live-private, live-sim-value, action-ranker and action-value-ranker
  checkpoints remain valid only for their old schemas;
- public replay raw logs and simulator traces can be re-featurized after schema
  code and tests are final; raw source collection does not necessarily need to be
  repeated;
- transition-derived action-value labels should be rebuilt only after both schemas
  pass counterfactual gates.

Before a full rebuild, freeze the final ordered schemas, profile the replay pool,
generate a small diagnostic dataset and run small/medium training benchmarks.

## Backward compatibility

1. Never resize or reinterpret old feature arrays in place.
2. Keep named schema registries and explicit adapters only for diagnostics.
3. Do not pad/truncate across semantic versions in production loading.
4. Record separate state/action schema versions in every ranker checkpoint.
5. Keep current live defaults on v2/v3-action until vNext evaluation passes.
6. Add strict checkpoint metadata checks before any candidate can serve.

## Promotion gates

A candidate vNext model is not eligible for live or branch-leaf use until:

- all blocker counterfactuals change the intended features only;
- perspective mirroring is correct;
- no hidden opponent truth leaks;
- clear expected scorer orderings pass;
- seeded branch audits beat or match the current material baseline;
- damage diagnostics report provenance and no silent fallback.
