# Simulator State and Protocol Coverage

**Status:** Source-reviewed inventory with explicit known gaps. This is not an acceptance of PIPELINE-001 or FEATURE-001.

## Provenance and supported format

The repository declares `pokemon-showdown` exactly at `0.11.10` in `sim-core/package.json`. `sim-core/package-lock.json` resolves the same version and has npm `resolved` and `integrity` fields. Installed `node_modules/pokemon-showdown/package.json` also reports `0.11.10`. The package is not a Git checkout, so an upstream source commit ID is unavailable. The lock integrity records the expected tarball hash; it does **not** prove the unpacked active files equal that tarball without a clean install. This task did not install packages.

The exact scope is `gen9randombattle`: the installed format metadata identifies Gen 9 (`gen9`), singles, randomized teams, and two players. Six is the generated-team expectation. The emitted `teamsize` record remains authoritative per battle. This is not a claim about other formats, generations, doubles, custom formats, or all Showdown protocol output.

The durable machine inventory is [pokemon-showdown-0.11.10-gen9randombattle.json](/Users/nbolger/Desktop/neural-showdown/sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json). It binds both TypeScript source and active compiled runtime directories (`sim`, `data`, `dist/sim`, `dist/data`) to SHA-256 digests. It also hashes the local parser, projection, action, transition, pipeline and focused-test files. Separate reviewed digests are required for simulator and local coverage sources: refreshing either digest alone fails the checker and does not attest review.

## Classification vocabulary

- **represented:** the current wrapper exposes a typed value from the relevant record or request. This can still be coarse; group notes specify loss of precision.
- **raw-only:** the public, validated protocol prefix can retain evidence, but no typed state field represents it.
- **explicitly unsupported:** the adapter rejects the shape or scope intentionally and reports the failure. There are no simulator condition IDs classified this way for this format.
- **unknown:** the exact source semantics or visibility cannot be established within the supported scope. The JSON `review.unknowns` entries state the evidence and blocking consequence.
- **silently omitted:** the simulator has a state detail, but the current typed projection does not carry it and no observation-level exclusion represents that detail. These omissions are enumerated below; they are not treated as absent/false.

The manifest attaches every condition/effect ID to a semantic group containing its source files and symbols, lifecycle, visibility, observable/belief treatment, legal-action impact, raw evidence, implementation, tests, classification, and specific gaps. IDs can belong to multiple runtime inventories; the manifest preserves those memberships.

## Condition and state inventory

The pinned runtime surface was read through `Dex.mod('gen9')`, including resolved Gen 9 move, ability, item, and condition records, and checked against `sim/pokemon.ts`, `sim/side.ts`, `sim/field.ts`, `sim/battle.ts`, `sim/dex-conditions.ts`, and `data/{conditions,moves,abilities,items}.ts`.

| Runtime inventory | Count | Source / symbol | Current observable treatment and lifecycle |
|---|---:|---|---|
| Major status IDs: `brn`, `par`, `slp`, `frz`, `psn`, `tox` | 6 | `data/conditions.ts`, `Conditions.<id>.onStart/onEnd`; `sim/pokemon.ts`, `Pokemon.status/statusState` | **represented** coarsely by `status` and `status_source`. Status records start/end; residuals and action prevention use simulator-private timers/stages. `status=null` with source `request` means known absent; source `unknown` is not absence. Hidden opponent counters are not in BeliefState. |
| `Move.volatileStatus` IDs | 55 | `data/moves.ts`, `Moves[*].volatileStatus` | **represented** as an untyped public-presence set when `-start`/`-end` are processed. Lifetimes, counters, sources, target locks, switch/faint clearing and expiration vary by effect. |
| `secondary[].volatileStatus` IDs | 6 (59-value union with the preceding set; 2 overlap) | resolved Gen 9 `Moves[*].secondaries` | Same presence-only treatment. Union adds `flinch`, `saltcure`, `sparklingaria`, `syrupbomb`; `confusion` and `healblock` overlap the direct property set. |
| Direct callback `addVolatile` identifiers | 46 literal IDs | Applicable Gen 9 callback paths in `data/moves.ts`, `data/abilities.ts`, `data/items.ts`, `data/conditions.ts`, `sim/battle-actions.ts`, `sim/battle.ts` | Includes both public effect IDs and internal/mechanics IDs such as `trapped`, `twoturnmove`, `stall`, `choicelock`; not interchangeable with the 59 move field IDs. Five source call sites use a dynamic argument and are source-digest protected rather than statically classified by value. |
| Side conditions | 15 | resolved Gen 9 `Moves[*].sideCondition`; `sim/side.ts`, `Side.sideConditions` | **represented** in `FieldView.side_conditions` as counts. Start/end/swap are public. Hazard layers, caps, duration and per-effect update semantics are partly **silently omitted** by a simple count map. |
| Pseudo-weather | 8 | resolved Gen 9 `Moves[*].pseudoWeather`; `sim/field.ts`, `Field.pseudoWeather` | **represented** as IDs on field start/end. Duration, source and suppression state are **silently omitted**. |
| Terrain | 4 | resolved Gen 9 `Moves[*].terrain`; `Field.terrain/setTerrain/clearTerrain` | **represented** through current field parsing for the four runtime IDs. Duration/source remain **silently omitted**. Checker compares the whole move registry so a new terrain stops for review. |
| Weather | 8 total condition IDs (5 ordinary move properties plus weather-condition/ability variants) | `data/conditions.ts`, weather condition callbacks; `sim/field.ts`, `Field.weather/setWeather/clearWeather` | **represented** by coarse weather ID. Duration, source and suppression counters are **silently omitted**. |
| Internal condition/effect state | Registry entries plus callback-created IDs are individually listed in the manifest | `Pokemon.volatiles/statusState`, `Side.slotConditions`, `Field.weatherState`, `Conditions.<id>` | **raw-only** or simulator-only unless a public result record is emitted. Private counters/source links are not projected. Legal consequences must be learned from the acting side’s request or public outcome, never an omniscient snapshot. |

Other authoritative state covered in the manifest includes boosts (seven stages: attack, defense, special attack/defense, speed, accuracy, evasion), HP/fainting, active and switching state, roster identity, species/forms/types/Tera, abilities/items, move slots/PP/disabled state/locks, requests, side/slot conditions, field state and terminal lifecycle. `sim/pokemon.ts`, `sim/side.ts`, `sim/field.ts`, and `sim/battle.ts` define the mutable state; requests are produced by `Battle.makeRequest` and `Side.emitRequest`.

### Visibility, legality, and current contract mapping

- Major status IDs are public when exposed by protocol/HP condition. Private durations and toxic-stage counters are not. Status can affect action execution; the following private request remains the immediate legal-action authority.
- Volatile presence is public only when emitted in the addressed player’s shared log. Effects can carry private state, duration, source, counters, or lock targets. The current `string[]` cannot preserve those semantics. `BeliefState` has no status/volatile hypothesis categories; do not infer them from the simulator snapshot.
- Side and field records are public where emitted; visibility can differ by record because `Battle.addSplit` emits side-specific values. A token name alone does not establish visibility.
- Opponent roster arrays are partial. A missing slot is unknown if team size/preview indicates more roster members; it is not a nonexistent member. The current representation uses actual revealed entries plus separate `team_size`, not placeholder Pokémon.
- Own request data includes move slot/identity, PP, disabled, target class, forced-switch/trapped and Tera availability. `CanonicalAction` binds slots to a request but v1 has no targeted-action target grammar. Future feature mapping must preserve the current request’s move identity and slot together.
- ObservableBattleState preserves an exact ordered event cursor and sanitized prefix. The cursor is record count, not turn number. A pre-decision feature cutoff must use only that observation and its own request: no successor, terminal outcome, completed trajectory, future record or other perspective’s private request.
- SeededTransition contains authoritative simulator lineage but does not make hidden simulator state a player observation. BeliefState simulator-truth evidence is only valid in its `simulator_research` regime, never as player-visible evidence.

### Known lifecycle gaps

Confusion is a public volatile with `-start|target|confusion` and `-end|target|confusion` in `data/conditions.ts:163-198`; its duration is simulator-private. The new test forces the pinned simulator to emit both start and end and checks projection for both perspectives. Substitute is tested as another emitted volatile. These tests establish those paths only, not all 59 IDs.

`-singleturn` is shape-validated and preserved in the exact raw prefix, but `PlayerStateExtractor` does not project it into `PokemonView.volatiles`. This is **raw-only**, not a claimed persistent volatile. Its one-turn expiry is not reconstructed. Other volatile duration/source/lock details and side-condition layer/duration transitions remain explicitly **silently omitted** and block treating current typed state as complete simulator state.

## Protocol inventory and reconciliation

The manifest contains:

- **111 parser allowlist tokens**, each mapped to a grammar group and assigned a coverage disposition; three generic unknown aliases remain rejected by the PIPELINE publication boundary;
- **86 literal emitter tokens** found by the package-wide source scan, each with source-file references and an explicit scope disposition;
- separate emission-path descriptions for `Battle.add`, `addSplit`, `addMove`/`attrLastMove`, private `Side.emitRequest`/choice errors, and `BattleStream` routing;
- the computed `msg` family for `-boost`, `-unboost`, and `-setboost`.

The 86 tokens are package-wide across generations and formats, not a Gen 9 execution trace. The 111 parser allowlist tokens include adapter-only/request/diagnostic forms and the three generic unknown aliases that pipeline publication now blocks. Their set difference is expected and is documented in each manifest entry; neither count alone proves coverage. `Battle.add` supports computed arguments/functions, `addSplit` has per-side visibility, move lines may be post-mutated, and requests/errors are side-private channels rather than ordinary public battle-log records. Five callback sites construct volatile arguments dynamically; the digest guard covers these source paths.

The parser now explicitly validates and retains these common raw-only Gen 9 records which were previously rejected: `cant|target|reason|move?`, `-hitcount|target|integer`, `-fieldactivate|effect|tags?`, and `-message|text`. None is projected as feature state. A `cant` or `-hitcount` outcome does not define the next legal-action set. Existing parser behavior rejects any unlisted command; malformed listed forms also fail closed. Request JSON is transient and private, then sanitized to an `rqid` marker in the observable prefix.

Other relevant grammar groups and their required/optional fields are in `protocol.grammar_groups` and per-token `record_grammar`/support entries in the machine manifest. Examples include switch/drag/replace (`target|details|condition|tags?`), move (`active source|name|target?|tags*`), start/end (`target|effect|tags?`), field/weather (`effect|tags?`), side conditions (`side|effect|tags?`), and status/boost/HP records. For moves, a target may be an active or non-active Pokémon reference (`p1a: ...` or `p1: ...`), or may be omitted/empty. The literal `null` requires exactly one final `[notarget]`; preceding metadata is limited to source-generated `[from]` or `[anim]` fields, matching `useMoveInner` (`sim/battle-actions.ts:446-462`). Accepted move tag forms are pinned emitter tags `[from]`, `[anim]`, `[still]`, `[spread]`, `[miss]`, `[notarget]`, and `[zeffect]` with source-shaped payloads; arbitrary bracket names fail closed. Trailing bracket tags are metadata fields; `[notarget]` is a tag and cannot satisfy the target field. Target meaning is token-specific; an omitted self-target field is not rewritten to an opponent target. The source basis is `sim/battle-actions.ts:412-462,545,590-640,1512-1516`, `sim/battle.ts:3046-3067`, `sim/pokemon.ts:504-512`, and `sim/SIM-PROTOCOL.md:240-252`.

Three generic allowlist aliases (`clearstatus`, `-clearstatus`, `nothing`) still have no supported-format emitter path or reliable state semantics established by the source audit. Their parser shape check is not grammar acceptance for collection: current PIPELINE projection stops them with `pipeline/v1/unresolved-protocol-alias` and a structured `pipeline-diagnostic/v1` containing the record index and command. This guard runs while building the protocol prefix, at direct step-result projection, and in the Python record validator before it constructs a DATA-001 record. They remain **unknown**, not supported raw-only events; any observation must stop publication pending classification.

Keep `-nothing` separate. It is a supported no-payload raw-only record with a pinned Gen 9 emitter: `data/moves.ts:18380-18384` emits `this.add('-nothing')` in Splash's `onHit` callback. The parser and pipeline retain `-nothing` unchanged. Its existence does not establish grammar or meaning for `nothing`.

Package-wide static emitters not enabled in the Gen 9 singles grammar—such as `-burst`, `-candynamax`, `-mega`, `-primal`, `-zpower`, and multi-active `swap`—are explicitly source-classified as other-format/mechanic or diagnostic records, not silently discarded from the inventory. `-message` and other diagnostic text are raw-only. A change to simulator source, installed version, format metadata, condition registry, emitter set, or parser allowlist requires review before the drift check passes.

## Drift protection

From `sim-core/` run:

```sh
npm run check:simulator-coverage
node scripts/check-simulator-coverage.cjs --self-test
```

The check compares the exact package declaration/lock/installed version, requires lock `resolved` and `integrity`, confirms Gen 9 Random Battle metadata, compares condition/move/secondary/side/pseudo-weather/terrain registries, compares parser and literal-emitter tokens, validates per-entry classification/source/semantic-group completeness, and hashes installed TypeScript plus active compiled `sim`/`data` trees. It also hashes the local parser/projection/pipeline sources and focused tests. Review digests and semantic review status are separately recorded. The self-test detects synthetic new condition, protocol and emitter IDs, missing classification, and simulator or local-source digest-only updates.

Limits: this is not a clean-environment tarball verification; no network/install was used. Static scanning cannot resolve all callback parameters or execute every ability/move/ruleset path. Dynamic `addVolatile` call sites and indirect emission paths remain protected by source digests; those digests stop for review but do not establish semantics. The supported format’s current request/output behavior is tested with deterministic synthetic teams under the same Gen 9 mechanics mod; not every event is proven reachable in random-battle generation. The three aliases remain a semantic review gap even though the collection boundary now stops them. Cross-format portability and exact private duration/counter semantics also remain outside the established contract.

### Scoped local-source semantic review — 2026-09-24

The local digest below was independently reviewed for the listed parser,
projection, action, transition, pipeline, and focused-test files. Review covered
the non-active and null move-target forms against pinned `BattleActions` and
`Pokemon.toString()` emission, exact trailing-tag handling, the unresolved
alias guards at both TypeScript projection and Python DATA publication
boundaries, and candidate discard/lineage preservation. It also covered the
natural hidden-trap rejection regression and deterministic controller trace
tests. This attestation does not certify all 142 semantic inventories, every
runtime event path, the unpacked package against its lock tarball, or
PIPELINE-001/FEATURE-001 as blanket semantic completeness.

Previously attested local coverage-source SHA-256:
`479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2`.
The pinned simulator source digest is unchanged.

### PIPELINE-002 reporting review — 2026-09-24

A separate review accepted opt-in wait reporting, per-player classification,
consumed-request suppression during restoration, privacy and retained execution
guards. The reviewed slice matched its recorded passing build, 53 TypeScript
tests and 18 Python tests. Reviewed `tests/env_manager.test.ts` is now included
in the local hashed list, changing the computed digest from the implementation
checkpoint's `ae29d0f002983ae83080cc6f7d64d11df5fda49dc748e3586bc25f4929eb184f`.

Reporting-slice reviewed local coverage-source SHA-256:
`3d4f9c1a5d41aef6ed8047dfc5faad87ddf86176f1022f7744b963fee042bab2`.
At that reporting review, the checker and all six drift self-tests passed with matching computed/attested
digests. This review accepts only the reporting slice, not one-sided execution,
complete episodes, full typed-view reconstruction or blanket simulator coverage.

### PIPELINE-002 ordinary forced-switch review — 2026-09-24

A separate semantic review accepted ordinary forced-switch-plus-wait execution:
actor-only submission/publication, both private successor perspectives and belief
joins, additive versions, deterministic TypeScript/Python identities, live guards,
Revival Blessing exclusion and atomic candidate rollback/cleanup. No blocking
findings or production corrections. Reused matching build and 67 TypeScript passes;
freshly passed all five forced-switch regressions and 20 Python record/lineage tests.

Added `tests/forced_switch.test.ts`, `../trainer/src/neural/pipeline_record.py` and
`../trainer/tests/test_pipeline_record.py` to the hashed list because they enforce
cross-language publication and regression claims. The four changed implementation
sources were already included; paths remain relative to `sim-core`. The expanded
list is not a claim to cover every transitive dependency.

Forced-switch review computed/attested local SHA-256:
`b37c9b26a82b8a389042cdf84f107788baaaf63624f4bc9a167625542adc2bf2`.
The checker and all six self-tests pass; simulator source digest is unchanged.
This acceptance covers real p2 KO and p1 U-turn cases with resumed joint play.
It does not accept complete episodes, chained-hazard coverage, requestless
progression, revival support, full typed-view fidelity or feature completeness.
See the [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

### Bounded settling review — scoped acceptance 2026-09-24

Accepted for the pinned simulator and serialized session operations. Review of
source emission, asynchronous fan-out and consumer acknowledgement established
complete delivery before decision publication. Terminal requires end plus both
matching terminal views; buffered terminal delivery after EOF is supported.
Deadlines do not reset on progress; message budgets reset only after a settled
boundary. Error/timeout/exhaustion/closure/cancellation release resources, and
candidate failure remains sticky despite late output. No blocking findings or
production corrections. Synchronous simulator calls remain non-preemptible.

All four checkpoint hashes and the implementation digest matched. Reused build,
85 TypeScript and 20 Python evidence; freshly passed 18 settling regressions.
Two controlled review probes verified repeated-progress budgets and late-output
rollback/next-transition equality; commands and logs are in the checkpoint.

Added `src/settling.ts` and `tests/settling.test.ts` to hashing; changed environment
and pipeline files were already listed. They implement/enforce the reviewed
lifecycle and must invalidate attestation on drift. Settling-review computed/attested
local SHA-256: `ffc9091735e5838b66a1d29cda6afcc973a9953bf01fcbb72132217335bff1b2`.
The coverage checker and all six self-tests pass; simulator digest is unchanged.
Complete-episode execution/outcomes, recovery limits, Revival Blessing and full
typed-state fidelity remain unaccepted. This is not blanket simulator coverage.

### Bounded episode orchestration review — 2026-09-24

Accepted `pipeline-episode/v1` and the episode-only request scope preflight under
exclusive serialized-session ownership. No blocking findings or corrections.
Reviewed distinct outcomes, default 256/512/3 accounting and resets, current-request
tuple exclusion, explicit-choice-rejection-only recovery, actor-only committed
publication, partial lineage, cancellation, unsupported/revival stops and cleanup.
Existing transition/Python record schemas and perspective privacy remain intact.

Added `src/pipeline_episode.ts` and `tests/pipeline_episode.test.ts` to the hashed
list (22 files). `src/pipeline_integration.ts` and Python validators/tests were
already covered. Computed and separately attested local SHA-256:
`4cb99bbc935da7db2edf70568099a19e4876eba049301d459481a0c27077d1c1`.
Coverage checker and all six drift self-tests pass; simulator digest is unchanged.
Matched all three implementation hashes; reused 102 TypeScript/20 Python evidence,
freshly passed build/17 runner regressions and two focused review probes for exact
terminal-limit/cancellation precedence and exhausted action combinations.

This supersedes the preceding historical exclusion of bounded episode outcomes
and recovery only. `faithful_complete_episode:false` remains required. Switch/faint
boost/volatile clearing and supported Shed Tail transfer are the next bounded task;
Revival Blessing, broader lifecycle coverage and faithful publication remain open.
See the [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

### State lifecycle review — blocked on 2026-09-24

Extractor corrections clear switch/drag/faint/re-entry boosts and volatiles, retain
source-supported nonvolatile evidence/Eternamax exception, and copy only Substitute
on a public Shed Tail switch tag. Request identity/order handling and canonical self
move IDs preserve the tested live/restored state. No privacy/schema expansion.
Build, 117 TypeScript tests and 20 Python tests pass. New regressions use constructed
teams executing real simulator moves for both actors; synthetic retention checks
are distinguished in the checkpoint. Existing runner/transition behavior still passes.

Listed-source digest is now
`d231c19ccde9feed1454315418b2eeb56f8bc63ea00ffab27a01af09788db6fc`.
Both checker commands exit 1 solely on drift; six synthetic self-tests pass.
The prior `4cb99bbc935da7db2edf70568099a19e4876eba049301d459481a0c27077d1c1`
attestation is untouched. Review extractor and changed state/environment/forced-switch
regressions; also review inclusion of new `tests/helpers/state_lifecycle.ts` before
recomputing and attesting. Review confirmed the helper belongs in the list, but
list/attestation updates are deferred until corrections pass semantic review.

All five hashes matched. Fresh build and 16 focused tests pass; the prior
117 TypeScript/20 Python evidence is reused. Additional real-engine probes for both
actors expose blocking Illusion failures: public boosts attach to the bench disguise
in the owner view, move evidence diverges after replay, and the valid conditionless
`replace` emitted by abilities.ts is rejected by observable_state.ts:511-518. The
synthetic replacement fixture uses the same identity and an extra condition, missing
both failures. Exact paths, evidence and next correction are in the checkpoint.
No semantic acceptance or new attestation; checker still exits 1 solely on drift,
while all six self-tests pass.
Other switch/faint fields, linked effects and wider lifecycle coverage remain open;
faithful complete-episode publication is unaccepted.

### Illusion correction implementation — review pending

The reproduced alias and replace failures are corrected in implementation. Public
active appearances are separate from own request roster projection; reveal restores
the impersonated entry and reconciles accumulated evidence to the actual identity.
Conditionless replace has its own strict grammar. The accompanying `-hint` from
pinned Battle.hint is explicitly raw-only and retained, with no prose-derived state.
No schema/private visibility expansion. Build, 126 TypeScript and 20 Python tests
pass, including real both-actor live/replay and deterministic publication regressions.
Original review probes now pass; this is not semantic acceptance.

Manifest/list/attestation unchanged. Both checker commands exit 1 on local digest
`8e74d9cf02e2d920c4131bfbb040d4167b05c62c612e8df445d6d08a5fd8d713`
and added parser token `-hint`; six synthetic self-tests pass. The separate review
must examine the combined lifecycle/Illusion change, classify `-hint` as raw-only,
update its parser inventory, and include `tests/helpers/state_lifecycle.ts` plus
`tests/illusion.test.ts` in source hashing before recomputing/attesting. Review
conditionless and legacy replace validation and preserve malformed-input rejection.
Prior attestation remains
`4cb99bbc935da7db2edf70568099a19e4876eba049301d459481a0c27077d1c1`.
Broader lifecycle and faithful complete-episode publication remain unaccepted.

## Required FEATURE-001 revisions and remaining blockers

1. Consume only public/revealed condition identifiers or the current acting-side request. Do not use opponent-private counters, source pointers, simulator snapshots, or hidden state as player-regime features.
2. Distinguish unknown from known absent status and unknown opponent roster slots from absent/nonexistent slots.
3. Either specify volatile inputs as public presence-only values with a complete registry and explicit raw-only counter exclusions, or keep them out until their effect-specific semantics are chosen. Do not silently treat missing volatile IDs as false.
4. Preserve exact move identity/request-slot binding; validate against the current request before action features or labels.
5. Treat `cant`, hit-count, failure, miss, activation, and other outcome records as event evidence. Do not derive legal masks from outcomes; masks come from the addressed side’s current request.
6. Specify if side-condition features need layers/duration. Current integer map does not reconstruct every lifecycle.
7. Keep exact event cursor and perspective provenance. Feature source cursor must not exceed observation cursor, and successor/future/terminal data must not leak into pre-decision inputs.
8. Keep format ID and actual `teamsize` metadata; six is not a parser invariant.
9. Resolve targeted/multi-active command semantics in a new action-contract work item if needed; CanonicalAction v1 explicitly excludes them.

Known unknowns are narrowly stated in the manifest: choice of private duration/counter semantics (blocking feature semantics), complete per-effect side-layer expiry semantics (blocking claims of full side-condition reconstruction), and protocol portability beyond this exact format (blocking any cross-format claim). PIPELINE-001 is accepted only for its joint-actionable scope; FEATURE-001 remains unaccepted.

### Combined lifecycle/Illusion review — blocked, 2026-09-24

The original identity contamination and conditionless replace failures pass the
scoped review. Pinned Illusion.onEnd/Battle.hint support conditionless replace and
raw-only hint; malformed-input guards remain. Existing mirrored tests verify
ownership, privacy, immutable prefixes, replay and deterministic publication.
However, fresh appearances at state_extractor.ts:406-448 discard public Tera on
re-entry: both-actor real probes emit tera:Fire while opponent views report
Normal/false and owner views Fire/true. Combined acceptance is blocked.

Eight checkpoint hashes match; fresh build and 43 focused tests pass; matching
126 TypeScript/20 Python evidence reused. Existing source/test coverage inclusion
is appropriate; helper and Illusion tests must also be hashed after correction.
Manifest, token classifications and attestations remain untouched. Both checker
commands fail digest and added -hint drift; all six synthetic self-tests pass.
Checkpoint contains exact digest, reproduction and completion criteria. Next:
correct explicit public Tera re-entry without alias leakage, then semantic review.
Other fields, linked effects and Revival Blessing remain outstanding;
faithful_complete_episode:false remains mandatory.

### Public Tera re-entry correction — implementation, 2026-09-24

Fresh switch/drag appearances now set their Terastallized flag from public tera:TYPE
before resolving types, matching pinned getFullDetails for both emitters and Illusion
without importing private identity. Only state_extractor.ts, illusion.test.ts and the
shared lifecycle helper changed in source/tests. Four real mirrored switch/drag cases
cover both perspectives, no-tag teammate isolation, hidden identity/reveal, restoration,
immutable prefixes, repeatable records/beliefs and Python record validation.

Fresh build/130 TypeScript tests/diff checks pass; prior 20 Python tests reused.
Original ordinary Snorlax reproduction passes. Combined acceptance remains pending;
manifest/list/classifications/attestation unchanged. Listed digest is now
5e69a24866f9142cd0414b38f5d7ec2e70ca440f8a8986b52d56eca6737cfa5a;
checker commands reject digest and -hint drift, six synthetic self-tests pass.
Next: combined semantic review, then helper/Illusion test inclusion and raw-only hint
classification/inventory before recomputing/attesting. Checkpoint records exact scope,
hashes and evidence. Broader fields/linked effects/Revival Blessing remain open;
faithful_complete_episode:false remains.

### Combined lifecycle/Illusion/Tera acceptance — 2026-09-24

Scoped acceptance: ordinary boost/volatile switch/drag/faint/re-entry clearing,
Shed Tail Substitute-only transfer, Illusion appearance/own-request ownership and
reveal reconciliation, conditionless replace/raw-only hint, and explicit non-Stellar
public Tera switch/drag re-entry. Existing Eternamax retention exception does not
expand supported formats. Pinned source and mirrored constructed-team Fire tests
support both perspectives, restore/reveal, immutable prefixes, privacy and repeatable
Python-validated records. No production corrections during review.

Eight hashes match; passing build/130 TS/prior 20 Python evidence reused. Fresh
29 Illusion/observable tests pass, including new Python publication checks. Added
shared lifecycle helper and Illusion/Tera tests to hashing (24 files), classified
-hint raw-only, reconciled its inventory/exclusion and corrected replace grammar.
Computed and attested local digest: `3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2`.
Pinned simulator digest remains unchanged. Coverage checker and six synthetic
self-tests pass. Evidence and exact source hashes are in the current checkpoint.

This supersedes earlier pending/blocked dispositions only for the accepted scope.
Next bounded prerequisite: public Tera reset on faint with mirrored real KO,
privacy/prefix/restoration and publication checks. Stellar defensive typing,
other fields, linked effects, wider transfers, Revival Blessing and faithful
complete-episode publication remain separate gates. Keep faithful_complete_episode:false.

### Faint Tera and terminal restoration implementation — 2026-09-24

Non-Stellar faint now deactivates Tera and restores observable non-Tera typing while
retaining known Tera type. Own projection overrides stale pre-faint request flags.
Unrevealed Illusion Explosion preserves opponent uncertainty and bench teammate data.
Exact terminal restoration exposed missing legitimate own-request history: optional
terminal-only terminal-request-history/v1 metadata now stores addressed side-bearing
requests behind opaque snapshots. No public records or actions are created; malformed
version/side/roster/nonterminal metadata rejects before replacing current state.
Outer schemas unchanged; terminal fingerprints include metadata. Bare legacy terminal
JSON lacks historical private data and cannot provide exact observation restoration.

Changed: state_extractor.ts, env_manager.ts, shared lifecycle helper, illusion.test.ts.
Parent build/134 relevant TS tests pass; delegated full suite157 passes; prior20 Python
tests reused and new records validated through Python. Mirrored terminal/Illusion KO
cases verify both perspectives, replay, immutable prefixes, teammate privacy and
repeatable records/beliefs. Diff checks pass. Checkpoint contains hashes and logs.

Implementation only; separate semantic review/attestation required. Four changed
files already hashed. Manifest untouched; both checker commands fail solely on digest
300cfa84ccf97db8fb54653a02fe45c657c6c7ce45a4676448bfa60fcf7c0c02;
six synthetic self-tests pass. Prior accepted digest remains
3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2.
Next: review this correction and terminal metadata compatibility/privacy, then attest.
Stellar and broader lifecycle gaps remain; faithful_complete_episode:false unchanged.

### Faint/terminal-history review — blocked, 2026-09-24

Pinned non-Stellar faint semantics and normal mirrored privacy/Illusion/teammate/
immutable-history checks pass. All four source/test hashes match; reuse build134/full157
TS and prior20 Python evidence. Fresh16 Illusion/Tera tests pass including Python
publication. No production changes or acceptance/attestation in this review.

Blocker: env_manager.ts:55-83 validates the request envelope and roster array but not
its entries. A real terminal snapshot with requests.p1.side.pokemon[0].ident = 7
passes validation, destroys prior state at line441, then throws in selfFromRequest.
Numeric details/condition also reject late; null entries and string stats succeed
as corrupt own observations. Parent confirmed the independent probe:
/tmp/neural-terminal-history-nested-probe.cjs and
/tmp/neural-faint-review-confirmed-probe.json.

The raw request also contains unused active/action and roster fields. Next task:
minimize and recursively validate restoration history before destructive reset,
with mirrored rejection tests preserving fingerprint, observations and usability.
Valid history creates no actions and raw metadata stays out of logs/records; only
its existing opaque snapshot commitment enters lineage. Legacy compatibility limits
remain documented. Four changed files already covered; manifest/list/attestation
unchanged. Both coverage commands fail only digest drift; six self-tests pass.
Current digest300cfa84ccf97db8fb54653a02fe45c657c6c7ce45a4676448bfa60fcf7c0c02;
prior reviewed3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2.
Stellar and wider lifecycle gaps remain; faithful_complete_episode:false unchanged.

### Terminal-history validation correction — implementation, 2026-09-24

Nested consumed fields are now validated before teardown, with structured
TerminalRequestHistoryValidationError code/path/reason and no private error values.
Minimal v1 writers retain only the own-roster fields consumed during restoration;
historical raw-v1 readers validate then drop unused action/roster data and canonicalize
Tera markers. Old raw-v1 fingerprints may migrate once; canonical round trips remain
stable. Missing-metadata legacy behavior remains. Valid history creates no actions
or raw public records. Faint semantics unchanged; separate acceptance remains pending.

Only env_manager.ts and illusion.test.ts changed. Parent build136 relevant TS tests
pass, including Python publication; prior20 Python evidence reused. Original five
malformed probes reject with unchanged fingerprints. Nested cases cover both owners,
live-state/branch preservation and continued request execution versus a twin; valid
migration/restoration tests preserve observations. Diff checks pass. Checkpoint has
source hashes and /tmp/neural-history-validation-* evidence.

Manifest/list/attestation untouched; existing list covers all affected source/tests.
Checker commands fail only on digest9a05263276c0f17e7c2f3b6baf77b874c48c07c0967b3858eb91d1fdd4a29016;
six synthetic self-tests pass. Next: review corrected minimal-v1 validation and
migration with the pending faint slice, then separately attest. Wider lifecycle
prerequisites and faithful_complete_episode:false remain unchanged.

### Faint/minimal-v1 restoration acceptance — 2026-09-24

Scoped acceptance closes the pending non-Stellar faint and terminal restoration
slice. Faint deactivates Tera while retaining known type and restoring observable
non-Tera typing; Illusion privacy and teammate/earlier-observation preservation hold.
Minimal-v1 validates consumed nested fields before teardown, returns structured
errors and preserves state/fingerprint/branch/continued choices on rejection.
Only necessary owner-roster fields persist. Terminal restoration creates no actions
or public raw history. Historical raw-v1 normalization may change identity: recapture
references and preserve historical records; old-reference/normalized-state pairing
rejects. Canonical round trips are deterministic and idempotent.

Four input hashes match. Reused build136 TS/prior20 Python and faint evidence;
fresh build18 Illusion tests (including Python publication) and3 coverage tests pass.
Independent review found one wall-clock-only flaky comparator; test-only normalization
now matches existing identity rules, with exact per-run prefix checks unchanged.
No production correction. Lineage probe and logs are in the current checkpoint.

Existing24-file list covers extractor, environment, helper and regressions; no
inclusion changes needed. Updated computed/reviewed digest:
`6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70`.
Removed resolved faint-Tera known gap; coverage checker and six self-tests pass.
This supersedes earlier pending/blocked dispositions only for this scoped slice.
Next: Stellar defensive typing correction with mirrored lifecycle/restore/publication
checks. Other fields, linked effects, Revival Blessing and broader episode fidelity
remain open. Keep faithful_complete_episode:false.
