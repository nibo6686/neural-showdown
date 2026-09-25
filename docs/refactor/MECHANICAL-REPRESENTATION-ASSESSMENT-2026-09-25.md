# Mechanical representation assessment — 2026-09-25

**Status:** assessment complete. This is a gap assessment and implementation
plan, not a new mechanic acceptance or coverage attestation.

## Scope and preserved boundary

Reviewed against branch `refactor/state-001-observable-state`, HEAD
`117df85247846548fe99ee7e3d60a26d827fc05c`, plus the pre-existing dirty working
tree. Do not reset, stage, or rewrite those changes. The current implementation
set includes uncommitted code, contracts, validation artifacts and the latest
bounded Topsy-Turvy implementation. Its scoped semantic review is closed; the
shared protocol validator awaits separate coverage review. Psych Up public-stage
semantics and grammar remain accepted. Observation v1 remains default; v2 is
opt-in. `faithful_complete_episode:false` remains required. FEATURE-001, new
training and faithful complete-episode publication are outside this assessment's
authority.

Repository instructions: no `AGENTS.md` was found in the repository or its
ancestors. Starting references: `docs/PROJECT_STATUS.md`,
`docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`,
`docs/contracts/SIMULATOR_COVERAGE.md`, and
`sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`.

## Progress / resume point

- [x] Checkout and review boundary: exact branch/HEAD, dirty paths, pending vs
  accepted scopes recorded above; no worktree changes disturbed.
- [x] Coverage boundary: the checker verifies selected registries, literal
  `add()` tokens, local parser tokens, format metadata and source digests. Its
  142 classified IDs and token counts do not establish format reachability or
  callback-semantic completeness. Format configuration is not in hashed roots.
- [x] Identity and type reconstruction through raw extraction, replay,
  restoration and both publishers.
- [x] Stage lifecycle, v1/v2 observation and publisher interaction.
- [x] HP/status, volatile and field/side lifecycle interactions.
- [x] Moves, requests, legal actions, ability/item callbacks and progression.
- [x] Unsupported-stop behavior and current-checkout validation evidence.
- [x] Final gap register, milestone, batch plan and documentation cross-links.
- [x] Shared TypeScript/Python protocol contract, rehashed publication rejection
  matrix, raw-only token preservation and stop/rollback checks.

**Resume here:** bounded Topsy-Turvy semantics are reviewed with no blocker.
The independent protocol-boundary review is blocked by cross-runtime parity,
loader-schema, source-shape, fixture-token, and pre-filter findings. Correct
those shared-boundary gaps and complete a separate review before attestation;
then take up scanner expansion, nested-effect modeling and operative
format-digest coverage. Preserve prior attestations and do not infer completeness
from inventory counts.

## Initial source-boundary findings

The installed package/declaration/lock metadata and manifest all name
`pokemon-showdown@0.11.10`; the manifest scopes mechanics to Gen 9 singles
`gen9randombattle`. Its source roots are `sim`, `data`, `dist/sim`, and
`dist/data`. The installed package is not a Git checkout, so its upstream source
commit is unavailable (`source_commit:null` in the manifest). `config/formats.ts`
and `config/custom-formats` are outside the hashed roots, while format checking
compares only ID/mod/game type/team. The lock integrity pins a tarball but the
current unpacked install has not been recreated and verified from it.

The checked registry list covers Conditions, top-level move volatile/secondary
volatile, side conditions, pseudo-weather, terrain and weather. It does not
enumerate `Move.condition`, `Move.slotCondition`, `Move.self.volatileStatus`,
nested move-hit effect records or `Ability.condition`/`Item.condition`. A
resolved Gen 9 comparison found 25 move-condition IDs missing from the
inventory, four missing self-volatile IDs and four missing slot-condition IDs;
five missing move-condition IDs occur in the generated pool (`glaiverush`,
`healingwish`, `revivalblessing`, `roost`, `wish`). Ability condition IDs
`magicbounce` and `rebound` are missing; Magic Bounce occurs in the pool. Both
current Item condition IDs happen to be classified, but the checker does not
guard their registry. Existing Revival Blessing acceptance demonstrates why
inventory omission and runtime implementation disposition must remain
separate.

The generated Gen 9 random-set file is a candidate pool, not full reachability
closure: selection/pruning, items and call/copy/reflection effects matter.
The resolved set file contains 507 species entries, 350 direct move IDs and 203
ability IDs.
Direct pool candidates include Transform/Imposter, Roost, Wish, Future Sight,
Healing Wish, Encore/Disable, Sleep Talk and Revival Blessing. Topsy-Turvy,
Psych Up, stage swaps, Baton Pass, Reflect Type and Costar are absent from the
direct pool; constructed fixtures establish simulator mechanics, not legal
random-battle occurrence.

Pinned synchronous battle probes found generated-format paths emitting
`-singlemove` for Destiny Bond and Glaive Rush. That token is absent from
`SUPPORTED_RAW_COMMANDS`; the parser rejects it and the episode error classifier
currently maps the resulting unsupported-observable-protocol error to an
unsupported-protocol truncation. This is a real reachable stop, not a silently
published state. Destiny Bond is broadly classified as represented in the
manifest and Glaive Rush has no condition entry, so inventory disposition does
not yet accurately explain this stop.

The five formerly described dynamic `addVolatile` sites have parameterized or
finite source families: originating two-turn move ID; `cantusetwice` move ID;
`moveData.volatileStatus` including nested/self hit data; and fixed critical-hit
volatile lists used by Costar/Psych Up. Public effect presence, source/target
evidence and legal locks need separate dispositions from private counters and
source object links.

## Progress note — identity, defensive typing and stages

**Verified support:** current extraction separates the active public appearance
from the owner's request roster projection and reconciles Illusion identity only
on a public `replace`. Prefix replay reconstructs these aliases. The reviewed
scopes include terminal faint/Tera history, ordinary Stellar defensive typing,
Soak/type replacement, one public added-type slot, Transform defensive-type
copying, and Transform/Psych Up stage copying. Switch/drag/faint reset the
reviewed temporary state; tests cover both perspectives, replay, refresh and
Python publication. These are scoped acceptances recorded in the latest
`SIMULATOR_COVERAGE.md` sections; they do not accept all transformations or
callbacks.

**Contract exclusion:** v1 omits opponent stages while retaining the current
acting player's request and self stages. Opt-in v2 reconstructs seven public
opponent stages from the exact protocol prefix and validates them in Python;
v1 remains unchanged/default. The v2 requirement therefore belongs in any
milestone that claims both perspectives' public stage fidelity.

**Verified scoped support:** independent review against pinned
`data/moves.ts:20427–20436`, `sim/pokemon.ts:505–512`, matching implementation
hashes and a bounded callback probe found no blocker for base Topsy-Turvy's
target-only inversion, nonzero sign reversal, zero preservation and all-zero
no-event behavior. Gen9SSB Rigged Dice, swaps and Baton Pass remain excluded.
Coverage inclusion/attestation is pending the shared protocol-boundary review.

**Intentional exclusion / unknown remainder:** swaps, Baton Pass, critical-hit
volatile transfer, other copied volatile state and general Transform mechanics
remain excluded. Roost's intra-turn type change and other temporary type hooks
need boundary-focused evidence before classifying their absence as a decision
state defect. Hidden roster identity before reveal, unrevealed opponent moves,
private request data, RNG and simulator-private counters are privacy boundaries;
their absence is not an unknown false value.

## Progress note — HP/status, effects and requests

**Verified support:** HP/faint/status are rebuilt from public condition records;
the acting player's request distinguishes known-absent status from an unknown
opponent value. Revival Blessing clears public faint/status evidence within its
accepted bench-selection boundary. Public seven-stage reconstruction is v2-only
for the opponent and preserves null versus explicit zero. The actor's current
request binds move slots, PP, disabled flags, switch/trapped state and Tera
availability to the canonical action. Requests are private, excluded from the
public prefix except a sanitized `rqid`; each record carries only its own
perspective. Existing stream settling and bounded episode code publish only
committed transitions with exact cursor/lineage.

**Intentional contract exclusions:** volatile IDs are currently presence-only.
Private volatile/status counters, source object references, RNG and duration
state are not copied out of Showdown. `-singleturn` is raw-only. Public weather,
terrain, pseudo-weather and side conditions are coarse current IDs/counts;
effect-specific duration/source/layer expiry is not claimed. Full side-condition
lifecycle remains an inventory unknown. `CanonicalAction/v1` excludes targeted
and multi-active action syntax. The simulator's current request, rather than
`cant`, hit-count or other outcome lines, remains the legality authority.

**Enforced unsupported stop:** the Gen 9 random move pool includes Destiny Bond
and Glaive Rush candidates whose pinned callbacks emit `-singlemove`. That token
is explicitly recognized-but-unsupported by the shared protocol contract.
Projection rejects it, and the episode classifier maps it to a protocol
truncation before candidate publication. This is a stop, not support for any
move lifecycle. Destiny Bond, Glaive Rush, Grudge and Rage source emitters are
identified, but complete format reachability and effects remain unreviewed.

**Confirmed publication defect, now fixed in code:** TypeScript checked raw
tokens against its parser while Python originally checked only cursor/hash,
private request sanitization and selected boost grammar. The assessment's
fully rehashed v2 case inserted `|futuremechanic|opaque` into linked prefixes;
the previous Python publisher accepted it. The durable reproduction now verifies
all observation/belief identities and joins, then confirms the publisher exits
2 with empty stdout. Both runtimes load the same command contract and share a
113-record supported-token fixture matrix; full optional-tag/effect-value closure
is still pending source scanning.

**Stop policy detail:** unsupported format, one-sided requestless/waiting
boundaries and unsupported revival variants have explicit truncation paths.
Unknown commands, unresolved aliases and `-singlemove` reject before commit;
the runner truncates protocol-scope stops. Malformed supported shapes reject
before commit and remain `failed`, not `truncated`. Internal `copyboost` and
`invertboost` aliases reject while exact canonical spellings remain supported.
Raw-only public `message` and `-nothing` records are retained. Condition values
inside generic lifecycle records and token-specific optional-tag languages still
need source-derived support/stop dispositions.

## Current-checkout verification

**Protocol-boundary batch verification (2026-09-25):** `npm run build` passes;
the TypeScript differential suite validates all 113 shared supported-token
fixtures and 14 rejection fixtures against Python. Rehashed publication tests
cover 112 rejects across both schemas, perspectives and prefix positions;
valid v1/v2 controls publish and retain identities. The focused Python record
suite passes 31 tests, including the same rehashed matrix and the exact unknown
command reproducer. The CLI rejects with exit 2 and empty stdout after
`verify_bundle_identities` succeeds. The durable reproduction is in
`artifacts/validation/protocol-boundary-review-2026-09-25/`. Simulator-backed
integration/episode tests exercise aliases, unknown commands, `-singlemove`,
malformed shapes, truncation and committed-state/lineage rollback; the broader
affected TypeScript set passes 127 tests. Coverage-checker synthetic drift tests
pass. The full checker reports the changed local source digest
`df0244b25b6b4253497df70863cd5224213dcd3f8066bace37f14e87d30eabb3` against the
preserved reviewed digest; this is intentional pending separate coverage review.
The installed Showdown source digest is unchanged. Historical Psych Up,
Topsy-Turvy and v1/v2 identity artifacts remain unchanged.

**Independent protocol-boundary review (2026-09-25): blocked; no new
attestation.** Targeted probes found a Python/TypeScript mismatch: Python accepts
Unicode decimal digits and treats explicit `rqid:null` like a missing key. Fully
rehashed candidates containing either `|turn|١` or `|request|{"rqid":null}`
published in all 16 v1/v2 × p1/p2 × input/successor cases (exit 0 and 1,325–1,331
stdout bytes); TypeScript rejected both records. The existing fully rehashed
`|futuremechanic|opaque` reproduction still rejects with exit 2 and zero stdout.

Both parsers reject source-valid
`|detailschange|p1a: Palafin|Palafin-Hero, L77` despite pinned
`Pokemon.formeChange` emitting `detailschange` with only identifier/details;
Palafin/Zero to Hero is in the Gen 9 random set pool. Both also reject the
source-emitted extended `-endability` form with its old ability and `[from]`
tag; random-battle reachability of that path remains unknown. The TypeScript
projector drops `|request|not-json` and unclassified `|tier|` before validating
either record. A fixture labelled `ability` contains `|-ability|...`, so the
113-fixture label check misses one token. Both validators also accept malformed
damage and boost values shown in
[`review-blockers-result.json`](../../artifacts/validation/protocol-boundary-review-2026-09-25/review-blockers-result.json).

Loader checks from source/build paths and an isolated Python package install
show missing files and invalid JSON fail closed, but a structurally invalid
asset with `supported_commands: "move"` loads in both runtimes; Python then
accepts `|m|opaque`. `trainer/pyproject.toml` includes the JSON in the built
package. This local package smoke check is not fresh-environment reproduction.
Targeted rollback/raw-only, `-singlemove`, privacy, historical-reference and
the existing unknown-command regressions pass. New findings and commands are
recorded in the reproduction script and result artifact; the reviewed digest is
preserved. The coverage source list includes the shared JSON contract, both
loaders, the relevant regressions, and the new reproductions. The final checker
computes local digest
`9793ca11d6ac3c696794027e0cab4150fe970bc52ee1c5fce59dcf124102b140`, while the
stored and reviewed digests remain
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`; the
synthetic drift self-tests pass, and the full checker exits on that unreviewed
digest change. Clean-environment reproducibility and semantic transition
fidelity remain separate questions.

## Gap register

Dispositions describe the current checkout; they do not grant work-item
acceptance. Inventory references use JSON paths in the coverage manifest.

### Cross-layer trace

1. Each player stream feeds a perspective-owned `PlayerStateExtractor`; the
   spectator stream supplies the shared public event prefix (`env_manager.ts`
   stream setup/result assembly). Private request JSON updates only that
   player's request and roster view.
2. `state_extractor.ts` reconstructs event state; `observable_state.ts`
   validates and sanitizes the exact prefix, projects the request for the
   addressed perspective, and hashes its cursor/identity. v2 adds public
   opponent stage evidence from that prefix.
3. `belief_state.ts` binds player-regime evidence and history to exact
   observation references/prefixes. Simulator snapshots contribute only
   lineage commitments in the pipeline contract, not simulator-truth features
   under the player regime.
4. `env_manager.ts` restores simulator snapshots and terminal request history;
   candidate transitions restore from the committed snapshot and compare the
   live request/prefix before publishing. `pipeline_integration.ts` then builds
   a per-perspective record from exact prefix extensions and lineage.
5. `trainer/src/neural/pipeline_record.py` validates public schema, action,
   exact prefix and lineage before DATA-001 conversion. The independent probe
   confirms its remaining raw-token validation gap (MEC-10).

| ID / inventory link | Source and pipeline layers | Evidence and impact | Disposition |
|---|---|---|---|
| **MEC-01 — source boundary** `simulator.source_roots`, `format`, `review.limitations` | `sim-core/scripts/check-simulator-coverage.cjs:103–130`; `config/formats.ts:29–34`; `sim/dex-formats.ts:576–592`; package lock/install | Checker confirms package version and compares only format ID/mod/game type/team. Operative format config/custom formats are outside hashed roots; tar integrity exists but the unpacked source has not been recreated from it. A ruleset change could evade the current provenance guard. | **Confirmed defect** in coverage provenance; installed-tarball equality is **unknown**. No cross-format claim. |
| **MEC-02 — registry/reachability closure** `registries`, `condition_inventory`, `condition_semantics` | Checker `scripts/check-simulator-coverage.cjs:139–147`; Gen 9 `data/moves.ts`, `data/abilities.ts`, `data/items.ts`; `data/random-battles/gen9/sets.json`; `sim/teams.ts:1461–1521,1637–1715` | Registry checks omit `Move.condition`, `slotCondition`, `self.volatileStatus`, nested hit effects and Ability/Item conditions. Resolved Gen 9 scan finds 25 unlisted move-condition IDs, four unlisted self-volatile IDs and four unlisted slot-condition IDs; five missing move-condition IDs are in random pools (`glaiverush`, `healingwish`, `revivalblessing`, `roost`, `wish`). `magicbounce`/`rebound` conditions are unlisted; Magic Bounce is pool-present. Item condition IDs happen to be listed but are not drift-checked. Random pools do not prove closure through item selection, call/copy/reflection or callback interactions. | **Confirmed defect** in inventory coverage; semantic/reachability closure is **unknown**. Revival Blessing support remains accepted only within its bounded scope. |
| **MEC-03 — identity and defensive types** `condition_semantics.move_volatile`; lifecycle sections in `SIMULATOR_COVERAGE.md` | `state_extractor.ts:412–501,503–592,619–650,778–810`; `battle_helpers.ts:117–127`; `observable_state.ts:197–246`; `env_manager.ts:625–667` | Public appearance identity is separate from owner-request roster data; Illusion reveal, Transform, Tera, Soak, added defensive type and reviewed switch/faint resets replay from prefix. Snapshot restoration reconstructs logs and terminal owner request data; candidate transitions recheck the live request. Three-type arrays survive TS/Python identity/publication. | **Verified support** for explicit accepted scopes. Other temporary type hooks (including Roost boundary behavior and Reflect Type) are **unknown/out of scope**; this is not a general type-callback model. |
| **MEC-04 — public stages** `condition_semantics` boost group; `contracts.observable_state_opt_in` | `state_extractor.ts:594–617,733–776`; `public_boosts.ts:5–76`; Python `public_boosts.py:19–107`, `pipeline_record.py`; pinned `data/moves.ts:20427–20436` | Psych Up, Transform, selective sign clearing, exact-prefix v2 reconstruction and bounded base Topsy-Turvy have scoped semantic review. v1 omits opponent stages by contract; v2 derives seven public stages and keeps unknown/null distinct from zero. | v1 omission is an **intentional contract exclusion**; bounded v2 and base Topsy-Turvy inversion are **verified support**. New shared protocol implementation still needs final coverage review. Rigged Dice/mod, other swaps, Baton Pass and unreviewed copy/transfer paths remain excluded. |
| **MEC-05 — HP/status** `condition_semantics.major_status`; `condition_inventory` | `battle_helpers.ts:51–90`; `state_extractor.ts:288–379,669–730`; Revival Blessing `data/moves.ts:15671` | Public HP/faint/status records and owner request are rebuilt; status provenance distinguishes request-known absence from unknown. Public elapsed-turn evidence is coarse; toxic/status counters remain private. Revival reset is verified within accepted bench revival. | **Verified support** for public coarse state. Hidden counters are an **intentional privacy exclusion**; full status feature/lifecycle semantics remain outside scope. |
| **MEC-06 — volatile and move conditions** `condition_semantics.move_volatile`; `registries.volatile_callback_effects` | `state_extractor.ts:778–811`; shared `protocol_contract.json`; `pipeline_episode.ts:101–109`; pinned `data/moves.ts:3619,6881,6896,8176,15098` | Volatiles are presence-only; `-singleturn` is raw-only. `-singlemove` is an explicit recognized-but-unsupported protocol stop and the runner truncates before commit. Destiny Bond, Glaive Rush, Grudge and Rage candidates have source emitters; per-family public lifecycle is not implemented. Private counters, targets, durations and source-object links are not player evidence. | The **enforced unsupported stop** is verified for the token; move-family lifecycle and random-team reachability remain **unknown/unaccepted**. Private internals remain an **intentional exclusion**. |
| **MEC-07 — requests, moves and legal actions** `protocol.grammar_groups.request/move`; `canonical_action` | `action_codec.ts:97–209`; `pipeline_integration.ts:377–388,432–456`; `pipeline_episode.ts:75–95`; Python `pipeline_record.py:167–190` | Only the addressed side's current request supplies legal slots, PP/disabled/trapped/Tera state and move identity; outcomes do not define the menu. CanonicalAction checks the current request and binds `rqid`. | **Verified support** for accepted Gen 9 singles menus. Targeted and multi-active syntax is an **intentional contract exclusion**; team preview, requestless/waiting and unsupported boundaries must not create fabricated actions. |
| **MEC-08 — abilities and items** `condition_inventory`, `condition_semantics.internal_effect`, protocol ability/item groups | `state_extractor.ts:836–917`; pinned `data/abilities.ts`, `data/items.ts`; manifest callback/effect links | Own known values and public `-ability`/`-item` evidence are represented; opponent names remain hidden until public revelation (`has-item` is a public presence marker). Magic Room and ability suppression have selected public handling. Full reachable activations, copying/suppression and field mutations are not inventoried. | Public/private boundary is **verified support** within reviewed events; broader callback composition is **unknown**. Hidden enemy loadout is an **intentional privacy boundary**. |
| **MEC-09 — field and side lifecycle** `condition_semantics.side_condition/pseudo_weather/terrain/weather`; `review.unknowns` | `state_extractor.ts:813–865`; pinned `sim/side.ts`, `sim/field.ts`, `data/conditions.ts` | Weather/terrain/pseudo-weather are current IDs; side records count starts and delete on end/swap. Counts do not encode every layer, cap, duration, source or per-effect expiry. These values can change move outcomes and switching hazards. | Coarse IDs/counts are **verified support**; full lifecycle is **unknown** and is not claimed. Do not treat counts as absent/false or as complete mechanics. |
| **MEC-10 — protocol and publication boundary** `protocol.commands`, `protocol.grammar_groups`, `protocol.recognized_unsupported_commands`; shared `trainer/src/neural/protocol_contract.json` | TS `protocol_contract.ts`, `observable_state.ts:446–901`, `pipeline_integration.ts:187–200`; Python `protocol_contract.py`, `pipeline_record.py:113–155`; `pipeline_episode.ts:101–112`; review reproduction artifact | The original fully rehashed `|futuremechanic|opaque` bypass is fixed: joins verify, then Python rejects with no output. New rehashed `|turn|١` and `|request|{"rqid":null}` candidates publish in Python across both schemas, perspectives and prefix positions, while TS rejects. The TS projector drops malformed `request` and unclassified `tier` records before validation. Source-valid `detailschange` and extended `-endability` records are rejected by both. `-singlemove` still stops before commit and failed candidates retain committed state/lineage. | Original unknown-command defect is **fixed**; the broader publication boundary is **blocked by confirmed defects**. Preserve the prior coverage attestation. |
| **MEC-13 — contract asset and fixture integrity** `protocol.contract`, shared command fixtures | `sim-core/src/protocol_contract.ts:4–30`; `trainer/src/neural/protocol_contract.py:7–11`; `tests/protocol_contract_validation.test.ts:78–107`; reproduction artifact | Missing assets and invalid JSON fail closed; source/build TypeScript lookup works outside the checkout CWD and Python wheel includes the JSON. However `supported_commands: "move"` is accepted by both loaders as four one-character commands, and Python accepts `|m|opaque`. Python also silently deduplicates supported/unsupported entries. One fixture labelled `ability` actually contains `|-ability|...`; tests check labels but not record-token equality. | **Confirmed schema-validation and evidence-coverage defects.** No reviewed digest update. |
| **MEC-14 — protocol grammar parity and source alignment** `protocol.commands[*].record_grammar`; pinned protocol emitters | TS `observable_state.ts:520–527,688–692,776–779`; Python `protocol_contract.py:159–160` plus `validate_protocol_record`; pinned `sim/pokemon.ts:1391,1863–1866`; result artifact | Python `\d` accepts Unicode decimal digits while JavaScript does not; `rqid:null` is conflated with an absent key. Both reject a source-valid four-field `detailschange` and source-emitted tagged `-endability`. Both accept invalid `-damage` condition text, unknown boost stat/amount combinations and loose `-singleturn` suffixes. Token recognition and representative fixtures do not prove full grammar. | **Confirmed cross-runtime and source-shape defects; remaining optional-tag/effect-value syntax is unknown.** Keep new effect reachability unaccepted pending scanner/source review. |
| **MEC-12 — signed `-setboost` grammar** `protocol.commands[-setboost]`; `protocol.grammar_groups.boost` | Pinned `sim/battle.ts:1941–1942`; shared protocol contract/fixtures; TS `observable_state.ts`; Python `protocol_contract.py`, `public_boosts.py` | The simulator emits the resulting signed stage (for example `-6` for a Contrary/Belly Drum probe). Raw TS grammar previously required unsigned integers while v2 stage replay already accepted signed set stages. Both validators now accept signed safe integers for `setboost` only; ordinary boost/unboost amounts remain nonnegative. The custom combination's random-team reachability was not established. | **Confirmed grammar defect, fixed for pinned protocol syntax; random-team occurrence is unknown.** This is not acceptance of Contrary/Belly Drum battle mechanics or new format reachability. |
| **MEC-11 — progression and episode claim** `contracts.seeded_transition`, `contracts.dataset_lineage`; `pipeline_episode` | `pipeline_episode.ts:70–112,120–200`; `pipeline_integration.ts:425–570`; accepted progression sections in coverage contract | Joint actions, ordinary forced switches, bounded bench Revival Blessing, settling, deterministic lineage, rejected-candidate rollback and bounded/truncated outcomes have scoped acceptance. Other boundaries and unsupported protocol can stop; a terminal result alone does not prove typed-state fidelity. | Scoped progression is **verified support**. `faithful_complete_episode:false` remains mandatory; complete episodes are an **unaccepted scope**. |

### Unsupported stop/truncate coverage

| Situation | Current guard | Assessment |
|---|---|---|
| Non-`gen9randombattle` episode | Runner emits `episode/v1/unsupported-format` and truncates. | Present. |
| Unknown protocol token | Shared contract rejects before routing/publication; episode runner truncates; rehashed Python test verifies identities then returns no output. | Present in TS/Python/runner; rejected candidates leave committed state and lineage unchanged. |
| Unresolved alias (`clearstatus`, `-clearstatus`, `nothing`) | Shared contract marks it recognized-but-unsupported; integration preserves its alias diagnostic; Python rejects both schemas. | Present before filtering and publication. |
| Internal helper aliases (`copyboost`, `invertboost`) | Rejected by the shared contract; canonical `-copyboost`/`-invertboost` retain strict accepted grammar. | Present in both runtimes; internal helpers may retain their existing alias compatibility. |
| Reachable `-singlemove` | Explicit recognized-but-unsupported token; runner maps it to protocol truncation before candidate commit. | Present in TS/Python/runner; no move lifecycle support is implied (MEC-06). |
| Malformed supported grammar | Both runtimes reject before publication; episode result remains `failed`, not `truncated`. | No publication; corrupted evidence stays distinct from a well-formed unsupported mechanic. |
| Filtered request/tier records | `projectPipelineProtocolPrefix` removes them before shared grammar validation; `|request|not-json` and `|tier|` both become an empty prefix. | **Not enforced before filtering.** Request must be validated before privacy sanitization; tier needs an explicit source/contract disposition. |
| Unsupported request/boundary or Revival variant | Explicit unsupported-boundary and Revival checks truncate; no fake action is created. | Present for reviewed cases. |
| Unreviewed condition value in an allowed generic event; unseen callback interaction | No full condition-value/callback closure guard. Generic start/end can be raw-preserved and presence-projected. | **Not enforced**; add source-derived support/stop dispositions before claiming a faithful slice that covers them. |
| Targeted/multi-active request outside v1 | CanonicalAction v1 excludes these shapes; scoped format is singles. | Contract exclusion; no cross-format extension. |

## Unexamined areas

This does not establish complete format mechanics coverage. Still unexamined or
only candidate-inventoried:

- Full random-set item selection/pruning and closure through Transform/Imposter,
  call/reflection/copy effects and indirect callback invocation.
- Every reachable Move/Ability/Item callback and combinations that mutate
  status, stages, types, suppression, slot state or request legality.
- Full grammar/visibility of every computed `add`, split output, private stream,
  animation and request path beyond the current source review.
- Every slot condition and side/field layer lifecycle; private expiry/source
  values cannot be treated as player observations.
- Whether each public one-turn effect changes a decision boundary or only an
  intra-turn outcome (including Roost and `-singlemove` families).
- Recreated package install compared to its lockfile tarball, clean-environment
  setup and fresh-machine reproducibility.
- Other formats/generations, doubles/multi-active play, replay/live ingestion,
  full feature semantics, data generation, training or release readiness.

## First usable pipeline milestone

Define `gen9randombattle` **faithful public transition capture** as one atomic,
per-perspective transition record with exact public event evidence and seeded
lineage. This is a transition-slice milestone, not a claim that an episode,
battle or dataset is mechanically complete. Require
`observable-battle-state/v2` because the accepted contract must publish
publicly reconstructible opponent stages; keep v1 unchanged/default for
existing consumers. Continue emitting `faithful_complete_episode:false`.

Faithful publication within this bounded milestone requires:

1. Both views come only from public simulator records plus that perspective's
   current request. Opponent-private requests, unrevealed roster contents, RNG
   and simulator counters never enter the view, belief or data row. Existing
   opaque simulator branch/fingerprint commitments are allowed only in their
   lineage fields.
2. Request/action identity, legality, event cursor and exact prefix lineage
   agree. Every public field is evidence-backed; unknown values remain unknown,
   and omitted timers/layers are documented instead of treated as complete.
3. TypeScript and Python validate the same command/shape grammar and supported
   effect-value sets, v2 public stages, exact prefix extension, perspective,
   canonical action, transition identity, branch/fingerprint joins and
   private-field exclusions. Rehashed unknown commands/effects or malformed
   records yield no Python output.
4. An unsupported mechanic stops before candidate commit with an explicit
   truncation reason. It cannot enter typed state or DATA-001 output through a
   generic token/effect. Settling failure, corrupted evidence and a valid but
   unsupported mechanic keep distinct outcomes.
5. Source-derived simulator probes cover each supported effect family, both
   actors, reconstruction/restoration and cross-runtime publication. The
   manifest binds operative format rules and reachable token/effect families.
   Any expanded scope receives separate review and attestation.

This capture may truncate on unsupported random-battle events such as
`-singlemove`. It does not produce accepted training features; keep
`features-not-produced/v1`. Fresh-environment recreation is a separate ENV-001
blocker to calling the milestone reproducible across machines.

### Current blockers

- The shared protocol contract has focused evidence, but this review found
  cross-runtime acceptance, source-valid rejection, pre-filter and asset-schema
  defects. Its final coverage attestation remains pending and the reviewed digest
  is preserved.
- Several direct-pool effect conditions and the operative format rules are not
  guarded by the current coverage inventory. Unknown effect values in otherwise
  allowed generic start/end commands also lack a complete stop policy.
- The `-singlemove` stop is explicit and safe, but can truncate valid generated
  battles; Destiny Bond/Glaive Rush/Grudge/Rage public lifecycle semantics remain
  open. Family expansion belongs after scanner/effect-value coverage.
- Signed `-setboost` syntax is now source-backed and accepted by both validators.
  Reachability of Contrary plus Belly Drum in generated teams is still unknown;
  this is syntax support, not mechanic-family acceptance.
- Clean installation/recreation from the pinned tarball has not been proven.
  This blocks a reproducibility claim; it does not change the mechanics scope.

FEATURE-001 and a training dataset are not requirements for this transition
capture milestone, but they remain hard gates before feature publication,
collection for training or model work.

## Prioritized implementation batches

The dependencies establish one shared grammar and effect boundary before
adding isolated mechanic cases. Bounded Topsy-Turvy semantic review and shared
protocol validation are complete; only the latter's final coverage attestation
remains pending.

1. **Next: coverage and provenance closure (separate batch).** Expand source
   scanning to nested/self/slot conditions and ability/item condition hooks;
   model dynamic/nested effect families and include operative format/config
   digests. Reconcile exact command inventory with supported grammar, explicit
   unsupported stops and accepted raw-only records. Distinguish direct random
   set candidates from package-wide emitters and indirect callback reachability.
   Acceptance: each direct candidate has source/grammar/effect disposition;
   relevant configuration drift fails the checker; unresolved closure stays
   explicitly unknown and stops collection when encountered.
2. **Public effect lifecycle foundation.** Before adding more move IDs, specify
   distinct representations for Pokémon volatiles, one-turn/one-move effects,
   side slot conditions, side layers and field effects. Define event boundary,
   reset/expiry, target/source visibility and request legality interaction. Use
   three-valued knowledge where a missing public event does not establish
   absence. Acceptance: shared TS/Python replay vectors preserve exact prefixes,
   both views, owner privacy and deterministic identities across start/end,
   switch/faint/re-entry and restoration.
3. **Reachable move families on the shared foundation.** Add bounded families
   by emitted state path: (a) `-singlemove`/turn-lock effects such as Destiny
   Bond and Glaive Rush; (b) slot-heal/revival effects such as Wish/Healing Wish
   alongside already bounded Revival Blessing; (c) temporary types such as
   Roost after boundary probes; (d) remaining callbacks that mutate already
   typed status/stages/HP. Keep explicit stops where semantics remain private or
   unreviewed. Acceptance is per family and both perspectives, with request
   legality and Python publication evidence.
4. **Side/field and callback composition.** Review side-condition layers,
   expiry, weather/terrain/pseudo-weather and priority interactions; then
   ability/item callback groups that change state visibility or action
   outcomes. Reuse registry and protocol vectors from batches 1–2. Acceptance:
   each direct random-set candidate has boundary-verified reconstruction or an
   enforced stop; no generic count is presented as full simulator state.
5. **Milestone attestation and reproducibility.** After the mechanical batches,
   run focused source-derived checks, selected cross-platform comparisons and
   fresh environment recreation; record exact package/source/config digest,
   observation v2, truncation evidence and Python validation. FEATURE-001,
   dataset generation and training remain separate gates.

### First recommended batch

Start with **coverage and provenance closure**: expand the scanner for nested
and dynamic condition/effect sources, model nested effects, and bind operative
format configuration into the digest. It builds on the shared 113-token command
contract and its supported/raw-only/recognized-unsupported distinctions. That
boundary lets later effect-family work reuse one grammar and publication gate
instead of adding isolated parser patches. Final review of the shared validator
is a prerequisite to coverage attestation, not a reason to delay this separate
scanner design work. Keep `faithful_complete_episode:false`.
