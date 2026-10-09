# PIPELINE-002 gap disposition — 2026-09-24

## CE-01 `-singlemove` raw-protocol closure — implementation checkpoint (2026-10-01)

- The shared TypeScript/Python contract now accepts only four pinned base-source
  forms as raw public evidence: `-singlemove|ACTIVE|Destiny Bond`,
  `-singlemove|ACTIVE|Glaive Rush|[silent]`,
  `-singlemove|ACTIVE|Grudge`, and `-singlemove|ACTIVE|Rage`. The first two
  have generated-set source witnesses; Grudge and Rage remain package-only/
  indirect-reachability-unproven and receive no format or mechanic acceptance.
- Every other `-singlemove` spelling is malformed before projection and Python
  publication. This includes missing, reordered, duplicated, invented and
  category-prefixed fields, extra tags, and side-only or malformed target
  identifiers. Rejection leaves the committed boundary and lineage unchanged
  and emits no DATA-001 row.
- The exact records remain raw-only. They create no typed volatile, belief
  inference, timer, action restriction, or hidden-state disclosure; legal
  actions continue to come only from the addressed request.
- Focused review accepted CE-01's exact raw-evidence boundary and attested local
  digest `1a3a57ceaf5096b6a83b2466c13e01b6206ad04939409adb170ed4428e0affbd`.
  This does not accept PIPELINE-002, assert complete-episode behavior, or alter
  the remaining closure backlog; `faithful_complete_episode:false` remains
  required.

### CE-01 aggregate Glaive Rush typed-state repair checkpoint (2026-10-06, unreviewed)

The aggregate simulator-coverage fixture had retained a synthetic `-start`
Glaive Rush record and asserted a typed volatile. Pinned
`Moves.glaiverush.condition.onStart` instead emits the exact raw public record
`|-singlemove|ACTIVE|Glaive Rush|[silent]`; its `self.volatileStatus` is
simulator-only. The repaired aggregate control retains the exact record in the
public prefix and proves that extraction creates no typed volatile. Existing
source-engine witnesses, both-perspective privacy, restored deterministic
continuation, rollback, historical fixture behavior, and Python publication
coverage are unchanged. The checker reports
`457396db95e5b3ff641e8e849007a86b7456ff093ca3f48f730b2bca4540a44c`
as unreviewed local drift. Manifest digest/review fields remain unchanged; no
new CE-01 or PIPELINE-002 acceptance is attested.

**CE-01 aggregate Glaive Rush typed-state repair verdict (2026-10-06, accepted):**
Review verified the pinned `pokemon-showdown@0.11.10`
`Moves.glaiverush.condition.onStart` emitter produces only the exact public
`-singlemove|ACTIVE|Glaive Rush|[silent]` record; the volatile, accuracy, and
damage behavior remain simulator-only. The repaired aggregate fixture retains
that raw prefix and proves no typed `glaiverush` volatile is created. Focused
source-witness, TypeScript contract/extractor/protocol, both-perspective
restore/rollback/privacy, and Python publication tests passed, as did the
aggregate coverage suite, checker self-test, and post-attestation checker.
Digest `457396db95e5b3ff641e8e849007a86b7456ff093ca3f48f730b2bca4540a44c`
is attested only for this aggregate-fixture repair. No generic mechanic or
damage model, private state, CE-01 lifecycle expansion, PIPELINE-002
acceptance, or complete-episode claim is added; `faithful_complete_episode:false`
remains required.

## CE-04D3 generated Court Change witness repair checkpoint (2026-10-05, unreviewed)

`sim-core/tests/court_change.test.ts` now generates every witness through the
pinned `Teams.generate('gen9randombattle', {seed})` path. The source roots are
Cinderace `[91,274,457,640]`; Skarmory/Spikes `[212,637,1062,1487]`; Iron
Treads/Stealth Rock `[6,19,32,45]`; Ribombee/Sticky Web `[26,79,132,185]`;
Meowstic/Reflect + Light Screen `[32,97,162,227]`; Abomasnow/Aurora Veil
`[45,136,227,318]`; Ariados/two-layer Toxic Spikes `[119,358,597,836]`; and
Shiftry/Tailwind `[110,331,552,773]`. No fixture assigns a move, ability,
item, weather, or battle state. Abomasnow's generated Snow Warning establishes
the Aurora Veil weather route.

Mirrored p1/p2 v2 witnesses execute legal generated switches/actions, prove
asymmetric transfers for all eight reachable represented siblings, post-swap
hazard switch-ins, Tailwind expiry, deterministic twin identity, direct-runtime
restore, stale-rqid rollback, public-only observations, and both Python
successor publications. Focused Court Change/contract/extractor/pipeline
TypeScript tests passed 80/80; Python publication tests passed 41/41; the
coverage reachability self-test and `git diff --check` passed. The normal
coverage checker reports unreviewed local digest
`110e286b51c6c1530b231cc428c498711a0fa067ad93a535029df9bfb5110856`.
No coverage manifest or attestation field changed.

The broader `simulator_coverage.test` remains a separate reproducible baseline
failure: two consecutive runs fail 1/9 because its pre-existing
`|-weather|raindance` fixture is rejected as unsupported generated weather.
This repair does not change that test, weather validation, PIPELINE-002
acceptance, or `faithful_complete_episode:false`.

**CE-04D3 scoped review verdict (2026-10-05, accepted):** Review accepts the
source-faithful generated Court Change witness set and exact public boundary.
Separate seeded generator roots cover Cinderace/Court Change and all eight
reachable represented side conditions: Spikes, Stealth Rock, Sticky Web,
Reflect, Light Screen, Aurora Veil under generated Snow Warning, two-layer
Toxic Spikes, and Tailwind. Mirrored p1/p2 v2 sessions use legal actions only,
prove asymmetric count/presence transfer, direct restore and deterministic
continuation, stale-rqid rollback, request privacy, later hazard/Tailwind
evidence, and Python successor publication. Exact grammar and the finite
normal-side transfer list remain bounded; weather and all other field state do
not transfer. Mist, Safeguard, Lucky Chant, Pledges, and G-Max conditions retain
the documented no-route dispositions. Digest
`110e286b51c6c1530b231cc428c498711a0fa067ad93a535029df9bfb5110856` is
attested for CE-04D3 only. The independent legacy `|-weather|raindance`
simulator-coverage failure remains outside this scope; PIPELINE-002 and
`faithful_complete_episode:false` remain unchanged.

## SLICE-003 v2 per-side projection closure — implementation checkpoint (2026-09-29)

- Start: branch `refactor/state-001-observable-state`, HEAD
  `868e2734a273bdabb387304bfb6b8ce8113b4e2b`; the pre-existing untracked
  `FACTORY_V2_CAPTURE_QA_PLAN.md` was preserved.
- Added one versioned synthetic pinned fixture:
  `tests/fixtures/observable_state_v2_per_side_gen9randombattle.json`.
  At the same 13-record normalized public cursor it creates immutable
  `observable-battle-state/v2` views for p1 and p2, with distinct owned
  requests/actions, a public known-absent status, and an unrevealed
  `status_source: "unknown"` entry for each perspective.
- The fixture-derived TypeScript regression verifies private request raw fields
  and opponent request details do not cross perspectives or enter the shared
  prefix/hash; the same-turn suffix cannot alter either earlier frozen
  observation, hash, or identity. It retains source-shaped `-singleturn`
  evidence without a typed `protect` volatile. It also confirms well-formed
  `-singlemove`, an unclassified volatile, a side-condition value in the
  volatile family, and malformed `-start` all reject before typed projection.
- No projection or extractor correction was required. Unrevealed ability
  details are omitted from the sanitized observable view; explicit
  `status_source: "unknown"` is the fixture's three-valued unknown marker,
  while public active `status: null` plus `status_source: "protocol"` is the
  evidence-backed known absence. Every fixture result retains
  `faithful_complete_episode:false`.
- Validation: `npm run build --prefix sim-core` passed. The newly added
  fixture regression and all selected observable/extractor/pipeline tests
  passed. The prescribed combined four-file command remains blocked by two
  pre-existing `public_stages` Illusion-reveal cases (p1 and p2), each failing
  with `settling/v1/simulator-error`; this slice did not modify their source
  or behavior. Final `git diff --check` passed.
- SLICE-004 remains required for candidate execution, snapshot restoration,
  transition rollback, Python/DATA-001 publication, and cross-runtime
  publication parity. The six unresolved computed `addVolatile` paths remain
  unknown/fail-closed; `-singlemove` remains unsupported and `-singleturn`
  remains raw-only.

### Separate review, blocker, and local coverage attestation (2026-09-29)

- An isolated worktree at the committed pre-SLICE-003 HEAD
  `868e2734a273bdabb387304bfb6b8ce8113b4e2b` rebuilt and ran
  `public_stages.test.js`: 20 tests passed and the same two p1/p2
  Illusion-reveal tests failed with `settling/v1/simulator-error`. The changed
  projection/extractor production sources and `public_stages.test.ts` are
  byte-identical to that baseline. This is a separate pre-existing
  settling/Illusion blocker, not a SLICE-003 regression; it requires separate
  ownership before SLICE-004 and was not repaired here.
- Independent review found the fixture and regression limited to the stated
  per-side projection scope. They do not execute candidates, restore state,
  exercise transition rollback, or invoke Python/DATA-001 publication.
- Review also found that the new fixture was absent from
  `local_coverage_sources.files`. It was added before attestation; the
  current/reviewed local coverage digest is now
  `a2e71a78c53fa9f9672df173b930ee9264e0cabb141ce1b2e411a6c60bbf3389`,
  with prior reviewed digest
  `34f086aa2ffc896caf39f11e3ff1c8139cda75cde3a851e550d6c7c60fc66ca9`.
  This attests only SLICE-003's fixture/test/coverage-source boundary and
  does not accept the separate Illusion blocker, mechanics, publication, or
  complete-episode behavior.

### Separate raw-only `-end Illusion` repair and attestation (2026-09-29)

- Separate ownership localized the prior p1/p2
  `settling/v1/simulator-error` to an inventory omission, before settling
  delivery or v2 projection. Pinned `Abilities.illusion.onEnd` emits
  `replace` immediately followed by `-end|ACTOR|Illusion`.
- The source-backed `-end Illusion` disposition is raw-only. `replace` alone
  reconciles public identity and stages; both p1/p2 regressions retain the
  exact end record in the public prefix, preserve the revealed Fox's `spa: 2`,
  and add no typed `illusion` volatile. No lifecycle semantics are claimed.
- Independent semantic review found no material finding. The changed
  `tests/public_stages.test.ts` was already listed in coverage hashing. The
  reviewed local digest is now
  `b6219f5ea41c804eb4b1f9a8e2ec7535a570590ee3c8cd923dddd82fa058e099`,
  with SLICE-003's independently reviewed digest
  `a2e71a78c53fa9f9672df173b930ee9264e0cabb141ce1b2e411a6c60bbf3389`
  retained as its predecessor. This repair does not alter SLICE-003's fixture
  or acceptance, and does not authorize SLICE-004.

## SLICE-004A v2 deterministic joint transition — implementation checkpoint (2026-09-29)

- Start: branch `refactor/state-001-observable-state`, HEAD
  `868e2734a273bdabb387304bfb6b8ce8113b4e2b`; all pre-existing SLICE-003,
  Illusion, coverage-manifest, and fixture work remains preserved.
- Added one focused TypeScript-only regression in
  `sim-core/tests/pipeline_integration.test.ts`. It creates two
  `observable-battle-state/v2` ordinary joint-action boundaries at the same
  pinned `gen9randombattle` seed, reuses one legal canonical action pair, and
  observes the disposable runner restoring byte-identical serialized input
  snapshots for the rejected and accepted candidate attempts.
- No production correction was required. Existing candidate execution already
  restores and fingerprints the input snapshot, validates both restored
  request IDs, projects both successors before commit, and discards a failed
  candidate. The regression compares transition and branch IDs, output
  fingerprint, both action IDs, timestamp-normalized emitted deltas, successor
  cursors, observation IDs, and belief IDs across the independent restored
  runs. Both successors remain v2, retain only their owned actionable request,
  and retain no `|request|` record in the shared public prefix.
- The same regression proves stale request IDs, malformed canonical actions,
  a candidate-only per-player choice rejection, and a separate candidate-only
  top-level `diagnostics.last_error` environment-error rejection preserve the
  complete committed boundary: snapshot fingerprint, step, branch, cursor,
  observation/belief identities, active slots, and belief lineage. The latter
  asserts `pipeline/v1/rejected-action` and the `simulator reported an
  environment error` diagnostic. Every prototype override is restored in
  `finally`; the next valid transition exactly matches an untouched control.
  This is a bounded transition proof only; no complete-episode semantics were
  added and `faithful_complete_episode:false` remains required.
- Validation: `npm run build --prefix sim-core` and the prescribed
  `transition.test.js` plus `pipeline_integration.test.js` command passed
  **13/13**. Final semantic review found no material SLICE-004A finding:
  candidate-only p1 choice and top-level environment-error rejections preserve
  the committed boundary and recover deterministically. The coverage list
  already includes `tests/pipeline_integration.test.ts`; replacing only that
  covered file with its pre-SLICE-004A version reproduces the separately
  reviewed `b6219f5ea41c804eb4b1f9a8e2ec7535a570590ee3c8cd923dddd82fa058e099`
  baseline. The reviewed local digest is now
  `1c96450fa2e53d73e229a61dc1c916d28e503d914ca2607b6c6052ad49891308`.
  The coverage checker and synthetic drift self-tests passed after attestation;
  `git diff --check` passed.
- SLICE-004B remains separate: forced-switch, Revival Blessing, waiting,
  requestless, episode-runner behavior, Python/DATA-001 publication, and
  cross-runtime publication parity are out of scope.

## SLICE-004B v2 joint-transition TypeScript/Python publication parity — implementation checkpoint (2026-09-29)

- Extended the same deterministic ordinary `gen9randombattle` v2 joint
  transition regression in `sim-core/tests/pipeline_integration.test.ts`; no
  TypeScript or Python production/contract correction was required. Both
  perspective bundles pass `python3 -m neural.pipeline_record` and emit one
  DATA-001 record with `observable-battle-state/v2` as the observation
  fingerprint. The p1/p2 record IDs are respectively
  `datarec-f4b83a69d488b081fe3a57b2d01042d2fdeac2cfa075d38ead344a4db6fa1969`
  and `datarec-305f868555bc9751be9181035d79846155b40b8263092af29d314f3b60f919ef`.
  They share transition
  `transition-7720e6ff11763331d87bd38f869ba092f0c3003cc88fe0480d9ca85ccd47b5f5`,
  branch `branch-5151a1e1b4046c1dfe782451bb61e7f5253c9a914be4acfd61704143881224be`,
  and the input/output state fingerprints
  `88c7a99186975bbdab350f60e4a103e300623cc72ffe4f065206bb394cdd2874` /
  `f41b4ead5d5e85209f7ee777e24b79cfbc8398ce9111fb32b26225e87ec564c3`.
- The proof directly joins each input/successor observation and belief,
  action, transition, branch/lineage, cursor, and exact successor prefix to
  its TypeScript bundle. A fresh independent session produces the identical
  per-perspective validated record. The published record has only DATA-001
  fields and excludes requests, snapshots, seeds, hidden opponent data, and
  successor/future records.
- The p1 and p2 compact tamper matrices each reject before output (exit 2 and
  empty stdout): a public-stage change with successor observation/belief IDs
  recomputed, mixed v1/v2 observations, wrong perspective, broken
  observation/transition references, a rehashed non-extending successor
  prefix, a forbidden raw request, and a malformed action identity. The
  existing candidate-only choice/environment rejection proof remains in the
  same run: its committed boundary stays separate and its valid retry matches
  the untouched control.
- Evidence hashes: `sim-core/tests/pipeline_integration.test.ts`
  `7f4f52534715c47b5dda2169a3a0aca61f839c67ee51a1953bba80ed28df2887`;
  `sim-core/src/pipeline_integration.ts`
  `939081e963020cd8f7e72e65990fa10f3dfbfb91fe02f79027fdde36254cbd1b`;
  `trainer/src/neural/pipeline_record.py`
  `5a25774de80ece830f7be56e8ac0f7c5503045b37faf451da615b9502e4b7c9f`;
  `trainer/src/neural/ts_identity.py`
  `115af529c5c9c873d18c1e76cb3ca0cb8e543d24e32cc6a76ae534551d7d411a`.
- Final semantic review found no material SLICE-004B finding. The documented
  `/Library/Developer/CommandLineTools/usr/bin/python3` runs both real v2
  bundle controls and `trainer/tests/test_pipeline_record.py` (**25 passed**)
  without repair; the focused pipeline command passed **9/9**. The only new
  covered path is the already-listed `tests/pipeline_integration.test.ts`; the
  current reviewed local digest is
  `4a43068ae878aaa5a3d6624220d424ff09cbdd5f2350c73303bfe1e5985daa77`, with
  SLICE-004A's separately accepted
  `1c96450fa2e53d73e229a61dc1c916d28e503d914ca2607b6c6052ad49891308` retained
  as its predecessor. The coverage checker and synthetic drift self-tests
  passed after attestation; `git diff --check` passed. This attests only
  ordinary v2 joint-transition bundle validation and does not accept broader
  publication, episode, mechanics, dataset, feature, training, or live-model
  scope.
- `faithful_complete_episode:false` remains required. No forced-switch,
  Revival Blessing, waiting/requestless, episode, dataset-writing, Python
  feature/training, or live-model claim is added. The next scope is
  SLICE-004B semantic review and conditional coverage attestation.

## Prior raw player-identifier review — blocked (2026-09-28)

The raw-repair fix and active `-transform` target validation pass focused checks,
but the shared boundary is not ready for scoped acceptance. The remaining
source-grammar defect is a side-only Helping Hand source accepted in both
runtimes, even though its pinned emitter formats the move's active `source`
Pokémon.

### Contract player-identifier field map

| Contract field | Pinned source form | Slot requirement |
|---|---|---|
| Shared `ident()` actor fields, including terminal actors | Pokémon object fields are stringified by `Battle.add()`; `Pokemon.toString()` returns `p1a: Name` for active battlers. Relevant examples: `faint` (`sim/battle.ts:2457`), `-clearboost` (`data/moves.ts:2643`), and `-endability` (`sim/pokemon.ts:1861-1866`). | Active slot required. Terminal records use the same raw validator. |
| `move` target | `BattleActions` emits the target Pokémon at `sim/battle-actions.ts:455`; `Pokemon.toString()` selects active-slot or side-only spelling based on `isActive` (`sim/pokemon.ts:504-512`). | Active or side-only. |
| Health-event `[of]` source | `Battle.damage()`/`heal()` interpolate `${source}` (`sim/battle.ts:2046,2189,2201`); `Pokemon.toString()` preserves its active or inactive form. | Active or side-only. |
| Revival Blessing `-heal` target | `sim/battle.ts:2738` emits `action.target`, the revived benched Pokémon. | Side-only. |
| Helping Hand `-singleturn` `[of]` source | `data/moves.ts:8885-8891` emits `${source}`. `runMove` receives the acting Pokémon (`sim/battle-actions.ts:206-219`); action execution skips it when inactive (`sim/battle.ts:2648-2650`). | Active slot required. **Current contract incorrectly uses generic `player-ident`.** |
| `-copyboost` donor, `-anim` target, `-clearpositiveboost` source, and `-transform` target | `data/moves.ts:14575`; `sim/battle-actions.ts:790,799`; `sim/pokemon.ts:1288-1290`; all are Pokémon-object fields. | Active slot required for these reviewed supported shapes. |

Side IDs in `player`, `teamsize`, `poke`, and side-condition records are not
Pokémon player identifiers; display names and free text also remain outside
this rule. Bare `transform` has no pinned emitter and retains its existing
compatibility grammar.

### Minimal source-backed reproduction

The contract's `singleturn.tagged_forms` defines Helping Hand `[of]` as generic
`player-ident`; the TypeScript validator calls `isCanonicalPlayerIdent` with
the default `activeRequired=false` (`sim-core/src/observable_state.ts:563`),
and Python does the same (`trainer/src/neural/protocol_contract.py:470`). Both
therefore accept this side-only source:

```text
|-singleturn|p1a: Pikachu|Helping Hand|[of] p2: Eevee
```

Observed on the current checkout: TypeScript raw validation and prefix
projection accept it; Python protocol and publication-prefix validation accept
it. A fully rehashed v2 candidate built from the existing synthetic bundle
passes `verify_bundle_identities` and `validate_pipeline_bundle`; Python's
DATA-001 publisher returns status 0 with 1,326 output bytes. This is an
unsupported emitted source shape, not a state-reconstruction claim.

The existing focused regression set still passes: TypeScript build; 35 focused
protocol/pipeline/extractor tests, including both v1/v2 rejection matrices
(224 rehashed valid controls and 856 rejected candidates); and 20 Python
pipeline-record tests. The matrix omits the side-only Helping Hand source, so
those passing counts do not close this blocker. The malformed terminal-actor
control now rejects in both runtimes and the valid form retains its raw spelling.
`git diff --check` and the staged whitespace check pass. No code, staged state,
coverage manifest, stored digest, or attestation was changed by this review.
Stored/reviewed digest remains
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`.

## Current implementation checkpoint — Helping Hand source role enforced (2026-09-29)

The shared `singleturn.tagged_forms` contract assigns `ident_role: "active"`
only to the Helping Hand `[of]` template. TypeScript raw and prefix validation,
and Python protocol/publication-prefix validation, pass that field-specific role
to the canonical player-identifier check. A side-only source is therefore
rejected before projection or DATA-001 publication; generic health-event `[of]`
and move-target rules remain side-or-active.

Pinned `data/moves.ts:8885-8891` emits the callback's `${source}` as the final
`[of]` field. `runMove` receives the acting Pokémon at
`sim/battle-actions.ts:206-219`, and `sim/battle.ts:2648-2650` skips inactive
move actors.

The source-backed controls include active sources on both sides:

```text
|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a: Eevee
|-singleturn|p2a: Eevee|Helping Hand|[of] p1a: Pikachu
```

The rejection set now includes both side-only forms, a missing source payload,
a source with no side label, and the existing malformed spacing and invalid-
side forms. The rehashed Python matrix applies every rejection across v1/v2,
p1/p2, and input/successor prefixes. Its publication assertion requires exit
status 2 and empty stdout, then validates the untouched original bundle, which
covers no DATA-001 output and preserved identity/lineage. The TypeScript
rollback matrix injects these cases and asserts that the committed boundary,
lineage, active slots, and subsequent transition remain unchanged. The raw
extractor check also confirms an active Pokémon remains in its slot after each
invalid record. `-singleturn` remains raw-only.

Separate review accepted this protocol-boundary batch. `npm run build`, 36
TypeScript protocol/pipeline/extractor tests, Python `test_pipeline_record.py`
with 20 tests, the coverage checker, and its drift self-tests pass. The reviewed
local digest is
`985f33403ea2a5af4fe83aa8e647efba70d3f1f21a7809d3200c88805efafd5b`.
This attestation accepts only the field-specific Helping Hand correction and
the listed protocol-boundary sources and tests. `-singlemove` remains an
unsupported stop and `faithful_complete_episode:false` remains required.
Scanner expansion and operative format coverage remain separate work.

## Separate protocol-boundary review and coverage attestation (2026-09-29)

### Findings

No material findings. The field-specific active role matches the pinned Helping
Hand emitter, and both runtimes enforce it before projection or publication.
The review found no privacy expansion: `-singleturn` remains raw-only, no typed
volatile is inferred, and invalid candidates cannot emit DATA-001 output.

### Open questions

None for this batch. HP-tag ordering, Instruct, scanner expansion, and
operative-format coverage remain documented separate scopes.

### Change summary

The review covers the shared contract, TypeScript validation/projection and
rollback tests, Python publication matrix, and raw-extractor atomicity test.
The coverage manifest now attests local digest
`985f33403ea2a5af4fe83aa8e647efba70d3f1f21a7809d3200c88805efafd5b`.
It accepts this protocol-boundary batch with documented gaps; it does not
accept broader mechanics or complete episodes.

## Implementation checkpoint — emitted player-ident spelling enforced (2026-09-28)

The shared contract now applies the exact `Pokemon.toString()` spelling to
every player-identifier field in both runtimes. The separator is one ASCII
colon followed by one ASCII space; neither validator trims, normalizes, nor
repairs an identifier. Names remain part of the identifier grammar, so ordinary
punctuation such as `Mr: Mime` and `Farfetch'd` is preserved. Free-text and
display-name fields that are not player identifiers keep their own rules.

### Source-backed player-ident grammar

| Emitted form | Pinned Showdown evidence | Contract rule and boundary |
|---|---|---|
| Side-only Pokémon: `p1: Name`, `p2: Name` | `sim/pokemon.ts:325` builds `fullname`; inactive `Pokemon.toString()` returns it at `sim/pokemon.ts:510-512`. `Battle.add` stringifies fields and joins them with `|` at `sim/battle.ts:3022-3025`; Revival Blessing emits a benched Pokémon as a heal target at `sim/battle.ts:2738`. | Empty slot is valid only for fields that permit a non-active Pokémon reference, including `[of]`, move targets, and the Revival Blessing exception. Fields marked active-required still reject this form. |
| Active Pokémon: `p1a: Name` through source formatter slots `a`-`f` on either side | `sim/pokemon.ts:504-512`: `getSlot()` selects from `abcdef`; active `toString()` combines that slot with the `fullname` suffix. | Contract slots are `a`-`f`; field-specific active requirements apply. `gen9randombattle` is singles, so direct format evidence exercises slot `a`; the other formatter slots are syntax support only, with no reachability claim. |
| Side display label: `p1: Player`, `p2: Player` | `sim/side.ts:315-317` | This is `Side.toString()`, not a Pokémon identifier. Side IDs, player labels, and other display/free-text fields are not routed through the player-ident rule unless a contract field explicitly says `player-ident`. |

The pinned display-name path runs through `Dex.getName()` (`sim/dex.ts:213`),
which normalizes team nicknames before `Pokemon.fullname` is constructed. The
runtime validators treat names and identifiers as opaque text after
validation; they do not rewrite them. Punctuation and embedded colons are
preserved (`Mr: Mime`, `Farfetch'd`), and edge whitespace is rejected rather
than trimmed. `Dex.getName()` also collapses interior whitespace and removes
some characters before emission; the current contract intentionally does not
replicate that whole nickname sanitizer, so its display-name grammar remains
broader than the normal validated-team output.

### Historical review finding — terminal actor repair (corrected below)

The shared raw validators reject this malformed source record, but the
TypeScript prefix projection accepts it after silently trimming the final
space:

```ts
'|faint|p1a: Pikachu\x20'
```

Here `\x20` is a JavaScript escape for the final ASCII space.

`validateRawProtocolRecord('|faint|p1a: Pikachu ')` and Python
`validate_protocol_record(...)` both reject the original. In contrast,
`projectPipelineProtocolPrefix(['|faint|p1a: Pikachu '])` returns
`['|faint|p1a: Pikachu']`. `pipeline_integration.ts:194-200` calls
`validatePlayerIdentAtRecordEnd()` and then trims the record before grammar
validation. The helper at `observable_state.ts:348-374` recognizes final move
targets and `[of]` fields but omits terminal actor identifiers such as `faint`
and `-endability`. Pinned Showdown emits `faint` with a Pokémon object at
`sim/battle.ts:2457`; `Pokemon.toString()` supplies its exact identity at
`sim/pokemon.ts:504-512`, and `Battle.add()` joins those fields unchanged at
`sim/battle.ts:3022-3025`. Thus the projection path repairs a malformed
identifier before filtering/publication, despite correct raw-validator
behavior.

At that review checkpoint, the existing 192-control/768-rejection rehashed
matrix did not include this terminal-actor case. The reproduction is retained
here as historical evidence; the current implementation and focused result are
recorded below. The prior stored/reviewed coverage digest was preserved.

## Current implementation checkpoint — raw identifiers validate before projection (2026-09-28)

The projection paths now validate the original protocol record before
filtering or publishing it. `projectPipelineProtocolPrefix` and
`normalizeProtocolPrefix` remove only one final CR/LF line delimiter as
transport framing; neither trims, rewrites embedded line breaks, or repairs
fields. `PlayerStateExtractor.consumeChunk` likewise removes only the stream's
final CR and rejects whitespace-prefixed protocol records without passing a
repaired copy to the parser. This closes the terminal-actor gap for `faint`,
`-clearboost`, `-endability`, and other typed actor fields checked by
`validateRawProtocolRecord`.

Pinned source evidence:

| Claim | Pinned source | Enforced and tested |
|---|---|---|
| Actor/target spelling is `p1`/`p2`, optional source slot `a`-`f`, exact `: `, then the emitted Pokémon name | `sim/pokemon.ts:325,504-512`; `sim/battle.ts:3022-3025` | Shared `isCanonicalPlayerIdent`; direct record validation, `projectPipelineProtocolPrefix`, `validateObservableProtocolPrefix`, and `PlayerStateExtractor.consumeChunk`; punctuation controls cover `Mr: Mime` and `Farfetch'd`. |
| Terminal actor records retain the same exact spelling | `sim/battle.ts:2457` (`faint`); `data/moves.ts:2643` (`-clearboost`); `sim/pokemon.ts:1861-1866` (`-endability`) | New valid controls plus trailing-space rejections; typed actor records pass the same raw validator before extraction/projection. |
| `-transform` actor and target are Pokemon objects, therefore active player identifiers | `sim/pokemon.ts:1288-1290`; formatter `sim/pokemon.ts:504-512` | TS and Python now validate both fields with the active player-ident rule. Bare `transform` retains its previous compatibility grammar because no pinned emitter was found for that token. |

The shared matrix now publishes **224 valid rehashed controls** and rejects
**856 rehashed candidates** (107 source/contract rejections across both
observation versions, p1/p2 perspectives, and input/successor prefixes).
Python publication checks verify recomputed bundle identities and joins and
produce no DATA-001 output for rejected candidates. Direct TS validation,
observation-prefix validation, and prefix projection agree on the new malformed
identifier cases. Valid controls retain their exact protocol spelling.
Integration rollback tests inject malformed terminal actors and transform
targets and confirm committed state, lineage, and the next transition are
unchanged.

Focused verification: TypeScript build passed; the protocol, pipeline, and
extractor test files passed **35 tests**; Python `test_pipeline_record.py`
passed **20 tests**. `-singleturn` remains raw-only; `-singlemove` remains an
enforced stop; `faithful_complete_episode:false` remains required. This
implementation checkpoint does not attest coverage or semantic transition
fidelity. The prior coverage digest is unchanged. Broader nickname grammar,
`-transform` format reachability, scanner expansion, and operative format
coverage remain outside this correction; scanner expansion and operative
format coverage are the next separate batch.

Earlier `-singleturn` source-form checks, HP-event, and move-target cases remain
part of the shared matrix. No coverage checker, digest, or attestation was
changed.

The current emitter table below remains the source inventory. Only Beak Blast,
Focus Punch, Protect and Roost have direct Gen 9 Random Battle set evidence;
all other listed forms are syntax-only here and do not imply format
reachability. HP-event tag ordering, Instruct, scanner expansion and operative
format coverage remain outside this review.

## Implementation checkpoint — `-singleturn` source forms constrained (2026-09-28)

The shared contract now allows only pinned source literals/templates for
`-singleturn`. Helping Hand is the literal bare label `Helping Hand`; its source
identity is the final `[of] ${source}` field. Follow Me emits `move: Follow Me`
with no tag, or with final `[zeffect]` only in the Z-power branch. Every
accepted record remains raw-only: no volatile state is inferred. Unknown
effect labels and unsupported shapes fail protocol validation before
publication, and an episode candidate stops with
`pipeline/v1/unsupported-observable-protocol`.

### Source identifier roles

| Source-backed field/template | Source parameter | Contract role |
|---|---|---|
| Standard actor fields, `-copyboost` donor, `-anim` target, `-clearpositiveboost` source, and `-transform` target | `Pokemon` | Active |
| `move` target and health-event `[of]` source | `Pokemon` or inactive/active `Pokemon.toString()` output | Side-or-active |
| Revival Blessing `-heal` target | Benched `Pokemon` | Side-only exception |
| Helping Hand `-singleturn` `[of]` source | Acting `Pokemon` from `data/moves.ts:8885-8891` | Active |

`singleturn.tagged_forms` records Helping Hand's `ident_role: "active"`; the
validator applies that role only to this source template. The general
`player-ident` grammar still accepts side-only references where the pinned
source permits them. Rehashed v1/v2 controls cover active sources on p1 and p2,
and side-only sources reject without altering the serialized prefix.

HEAD remains `a2ef3a6c3d2c27bb396bc55fc7dc10a0fcc29c2c`; the original staged
batch and its unstaged review/correction work are preserved. This task added
only unstaged contract, validator, test and documentation changes. No files
were staged, unstaged or committed by git actions. No coverage attestation or
digest was changed.

### Pinned emitter and format evidence

`Battle.add` preserves fields in the supplied order (`sim/battle.ts:3022-3025`),
so tags below follow the emitter literally. Direct reachability means a move
appears in a `data/random-battles/gen9/sets.json` movepool. “No direct entry” is
not proof of unreachability; indirect call/copy paths are not closed here. The
pinned-package token search found 28 base `data/moves.ts` call sites, including
the excluded Instruct emitter; no applicable base `sim`, ability, item,
condition or Gen 9 override emitter was found. Other `data/mods/*` emitters are
outside `gen9randombattle`.

| Emitted effect text | Emitter lines in `data/moves.ts` | Permitted tag and order | Direct Gen 9 random-set evidence | Disposition |
|---|---:|---|---|---|
| `move: Protect` | 1038, 2109, 18222 | None | No direct entry for Baneful Bunker/Burning Bulwark/Spiky Shield | Exact literal, raw-only |
| `move: Beak Blast` | 1175 | None | Yes: Toucannon, `sets.json:5160-5166` | Exact literal, raw-only |
| `Crafty Shield` | 3265 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Electrify` | 4737 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Endure` | 4995 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Focus Punch` | 6234 | None | Yes: Dusknoir, `sets.json:3230-3234` | Exact literal, raw-only |
| `move: Follow Me` | 6269; Z branch 6267 | None, or final `[zeffect]` after the effect | No direct set evidence; reachability unresolved | Exact source forms, raw-only |
| `Helping Hand` | 8887, 8891; ident text via `sim/pokemon.ts:325,510-512` | Final `[of] ${source}` after the effect | No direct entry; indirect paths unresolved | Exact template, raw-only |
| `Protect` | 10284, 13335, 14483, 17034 | None | Yes: Protect, e.g. `sets.json:194-201` | Exact literal, raw-only |
| `move: Magic Coat` | 11095 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `Mat Block` | 11404 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `Max Guard` | 11582 | None | No direct set evidence; reachability unresolved | Exact literal, raw-only |
| `Powder` | 14165 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `Quick Guard` | 15034 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Rage Powder` | 15148 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Roost` | 16026 | None | Yes: Articuno, `sets.json:946-953` (also Zapdos/Moltres) | Exact literal, raw-only |
| `move: Shell Trap` | 16903 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `Snatch` | 17778 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `move: Spotlight` | 18462 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |
| `Wide Guard` | 21637 | None | No direct entry; indirect paths unresolved | Exact literal, raw-only |

The package-level Instruct emitter at `data/moves.ts:10009` is excluded by this
task; no Instruct grammar or reachability disposition was changed. The contract
contains 19 exact untagged literals and two tagged templates. It rejects bare
`Follow Me|[zeffect]`, prefixed `move: Helping Hand`, wrong/mismatched tags,
invalid `[of]` identities, duplicate/reordered tags, extra fields, and unknown
untagged or tagged labels such as `Future Mechanic`. These rejected
`-singleturn` forms use the existing unsupported-protocol stop. `-singlemove`
remains separately recognized as an enforced unsupported stop.

All in-scope exact emitter shapes are dispositioned raw-only because retaining
the validated line adds no typed state or legal-action inference. The missing
direct-movepool entries remain reachability unknowns, not mechanics support;
they do not widen the reconstructed state. No additional per-form stop was
needed in this batch.

### Focused verification

- `cd sim-core && npm run build` passed.
- Focused TypeScript build passed; the affected selected set passed **125 tests**. The Python `test_pipeline_record.py` suite passed **20 tests**.
- The shared contract contains 21 `-singleturn` controls, three raw-only player-ident controls, and 96 rejection fixtures. The rehashed matrix publishes **192 valid controls** and rejects **768 candidates** across v1/v2, p1/p2 and input/successor prefixes. Every rejection candidate has recomputed identities and joins; Python publication returns no DATA-001 output. Integration rollback checks malformed player identifiers as well as protocol failures and preserves committed state, lineage, and the next transition. Raw-only extraction adds no volatile state.
- Prior focused evidence remains 125 selected TypeScript tests and 20 Python tests; it did not test terminal-actor whitespace before projection and does not close this review. Privacy, historical identities, raw-only records, field/loader/filtering regressions, and the `-singlemove` stop remain covered within their stated scopes. `faithful_complete_episode:false` remains required. HP-event tag order, indirect random-format reachability, Instruct, global scanner expansion, and operative-format digest coverage remain outside this batch. The existing coverage digest was preserved; no coverage attestation was issued.

## Earlier checkpoint — protocol-boundary source review blocked (2026-09-28, pre-correction)

This checkpoint records a blocked source review of the staged boundary batch. It
does not grant scoped acceptance or update the coverage attestation or reviewed
digest. The previous blocked review below remains the historical reproduction
of the pre-correction checkout. Current checkout: branch
`refactor/state-001-observable-state`, HEAD
`a2ef3a6c3d2c27bb396bc55fc7dc10a0fcc29c2c` before this correction.

### Changes present in the staged implementation

- Both runtimes now use ASCII canonical integer lexemes and safe integer limits.
  Request JSON must have an object root; a missing `rqid` is distinct from
  explicit `null`, and booleans, strings, fractional/unsafe IDs, and non-finite
  numbers reject. Other request fields are transient and do not enter public
  observations.
- Pinned-source grammar now validates HP/status ratios, boost stats/ranges and
  known tag vocabularies, `-singleturn` arity/tag vocabulary, switch/drag `[from]` forms, and one-label
  `tier`. Valid `tier` and bare `|` framing records are validated then filtered;
  malformed request/tier records fail before filtering. Direct TypeScript
  observation projection also sanitizes request fields and filters tier/frame
  records. Python rejects private requests and filtered tier/frame records if
  they reach publication.
- `detailschange` accepts the pinned four-field form and a documented
  condition-bearing form. When condition is absent, state extraction retains
  HP, status and fainting evidence. `-endability` accepts target-only
  suppression and the five-field move-source form. The latter clears current
  ability knowledge without asserting suppression.
- Contract loaders reject unsupported schema/rule values, wrong container
  shapes, duplicate/conflicting dispositions, fixture/record token mismatch,
  inconsistent rejection classes, and missing/invalid-JSON assets. The bare
  `ability` fixture now matches the `ability` token and remains accepted raw-only
  compatibility, with no pinned emitter claim.

Evidence boundary: `sim/pokemon.ts:1391` plus
`data/abilities.ts:5559-5565` and
`data/random-battles/gen9/sets.json:6840+` support Palafin detailschange;
`sim/pokemon.ts:1861-1866` supports the extended `-endability` form;
`sim/pokemon.ts:1990-2020` and `sim/dex.ts:581-588` define health/stat fields;
`sim/battle.ts:1857,1910-1969,2034+` defines tier, stage and HP emission;
`sim/battle-actions.ts:142` emits switch/drag source tags; and
`sim/battle.ts:1451,2754,2881` emits bare separator records. The contract has
114 command fixtures, 17 valid-record controls and 62 rejection cases. The 17
controls are not all source-backed: the staged `-singleturn` controls include a
source-inconsistent record, and health-event tag dependencies/order remain
permissive. Remaining syntax uncertainty includes dynamic source/effect values
and the distinction between package-wide emitter presence and actual
random-battle reachability. This batch does not close grammar for every token.

### Source review table and blocker

| Claim | Pinned source and enforcement/regression | Review result |
|---|---|---|
| Numeric/request parsing | `sim/battle.ts:1700,1855,2882`; `SIM-PROTOCOL.md:744-750`; server `room-battle.ts:536,785-791`. TS `observable_state.ts:421,471`; Python `protocol_contract.py:286,348`; shared rejection matrix. | Unicode digits, null, booleans, fractions and unsafe IDs reject. Negative safe `rqid` remains a contract-policy allowance, not a server-emitted value. |
| Validate before filtering | `sim/battle.ts:1857,1451,2754,2881`; `sim/side.ts:483-485`. TS `pipeline_integration.ts:188` and observable-prefix validation; Python `pipeline_record.py:113`; projection/rehashed tests. | Request, tier and framing records validate before their privacy/filter boundary. |
| `detailschange` / `-endability` | `sim/pokemon.ts:1388-1391,1861-1866`; `SIM-PROTOCOL.md:275-283,525-527`; TS/Python exact forms and `state_extractor.test.ts:126,139`. | Reviewed four/five-field detailschange and target-only/five-field endability forms pass; state treatment remains bounded. |
| HP/stage tags and `-singleturn` | `sim/pokemon.ts:1990-2018`; `sim/battle.ts:2034-2048,2154-2160,2186-2203`; `sim/dex.ts:581-588`; `data/moves.ts:6267,8887-8891`. TS/Python grammar and shared controls. | HP/stage values are represented; tags remain raw. Tag dependency/order and effect/tag combinations are not fully source-constrained. |
| Loader, rollback and stops | Shared contract loaders and tests; `pipeline_integration.test.ts`, `pipeline_episode.test.ts`; `-singlemove` emitters in the manifest. | Structural failure, rehashed no-output rejection, committed-lineage preservation and the unsupported stop are covered. |

Minimal source-backed blocker:

```text
|-singleturn|p1a: Pikachu|Follow Me|[zeffect]
```

Both staged validators accept this valid control, but pinned
`data/moves.ts:6267` emits `move: Follow Me` before `[zeffect]`. The other staged
control combines the Follow Me effect with the `[of] source` shape emitted by
Helping Hand at `data/moves.ts:8887-8891`. Do not treat the current controls as
evidence of complete `-singleturn` grammar.

### Verification

- `cd sim-core && npm run build` passed.
- `node --test dist/tests/protocol_contract_validation.test.js dist/tests/pipeline_integration.test.js dist/tests/state_extractor.test.js` passed 28 TypeScript tests. The shared rejection matrix checks 496 rehashed candidates across v1/v2, p1/p2, and input/successor prefixes; the saved 16 Unicode/null publication candidates all verify joins, reject with status 2 and emit zero stdout.
- `PYTHONPATH=src /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -q tests/test_pipeline_record.py` passed 18 Python tests, including exact identity recomputation, zero-output rejection, request privacy, filtered-tier rejection and a count assertion for those original 16 cases.
- This review rebuilt the staged source and reran the focused suites: build passed, the three TypeScript protocol/integration/extractor files passed 28 tests, and Python `test_pipeline_record.py` passed 18. Direct calls reproduced acceptance of the minimal `-singleturn` record above in both validators. No implementation files were changed during this review.
- Previously recorded broader evidence (57 selected TypeScript tests and 29 Python pipeline/lineage tests) used this same staged source/test set and computed local source digest `0675208ee538f33d378861f648021624222283c42fd911420a6ef40c68c3a625`; it was reused without another full cycle. The coverage checker was not rerun for this blocked review. The stored/reviewed digest remains `d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`, and the prior coverage attestation is unchanged.

Clean-environment recreation from the pinned tarball remains incomplete. Semantic
transition evidence in the scoped tests does not establish environment
reproducibility, and environment reproducibility would not establish semantic
transition fidelity. Keep `faithful_complete_episode:false`.

### Next separate implementation batch

Expand the source scanner for nested/self/slot conditions and dynamic callbacks,
then cover operative format configuration in the digest. Classify every newly
found effect and its format/reachability evidence before implementing mechanics.
The shared protocol correction remains blocked on the source-inconsistent
`-singleturn` control and permissive event-tag combinations. Correct and review
those contract claims before a coverage attestation can be issued.

## Current checkpoint — protocol boundary review blocked (2026-09-25)

### Protocol validation/publication review — blocked

The independent source/runtime review does **not** accept this batch. The prior
coverage attestation and reviewed digest remain unchanged. Concrete reproductions
are recorded in
[`reproduce_review_blockers.py`](../../artifacts/validation/protocol-boundary-review-2026-09-25/reproduce_review_blockers.py)
and its result JSON.

- Python publishes fully rehashed `|turn|١` and
  `|request|{"rqid":null}` candidates; TypeScript rejects them. All 16
  combinations of v1/v2, p1/p2 and input/successor prefixes published with
  nonempty CLI output.
- Both loaders fail closed for missing or invalid-JSON assets but accept a
  structurally invalid contract with `supported_commands: "move"`; Python
  then accepts `|m|opaque`. The built Python package includes the JSON and loads
  outside the checkout; this is not fresh-environment reproducibility.
- The simulator emits a four-field `detailschange` through Palafin’s
  Zero-to-Hero path, but both parsers require an extra condition. The source
  also emits tagged `-endability` records that both reject; reachability of that
  ability-change path in random battles remains unresolved.
- TypeScript removes malformed `request` and unclassified `tier` lines before
  grammar validation. The nominal 113-token fixture set also labels one
  `|-ability|...` record as `ability` without comparing fixture and record
  tokens.
- Grammar checks remain too broad for some supported records: both runtimes
  accept malformed damage conditions and unknown boost stats/amounts. This is
  not complete protocol grammar validation.

`|futuremechanic|opaque` still rejects after identity joins are recomputed;
candidate rollback, raw-only/privacy, historical-reference and `-singlemove`
stop regressions pass. Bounded Topsy-Turvy remains limited to the previously
reviewed base move and exact tag. `faithful_complete_episode:false` remains
required. The final checker run computes local digest
`9793ca11d6ac3c696794027e0cab4150fe970bc52ee1c5fce59dcf124102b140`; stored
and reviewed digests remain
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`. Checker
drift self-tests pass, while the full checker exits on the expected unreviewed
local digest change. Fix and review this shared boundary before attestation; then continue
with scanner expansion and operative format coverage, classifying newly found
effects before implementing them. Clean-environment reproducibility remains a
separate open question from semantic transition fidelity.

### Topsy-Turvy scoped verdict

**No blocker for the bounded base-move inversion scope.** Independent read-only
review against pinned Showdown `0.11.10` confirmed `data/moves.ts:20427–20436`
negates each nonzero stage on the target and emits only
`|-invertboost|TARGET|[from] move: Topsy-Turvy`; all-zero stages fail without
that event. `sim/pokemon.ts:505–512` confirms the public active identity used
by the event. The recorded seven implementation/test hashes match, and a
bounded pinned-Dex callback probe passed all seven stages, target identity,
repeated inversion and zero/no-event behavior. Existing TypeScript/Python
replay, restoration, privacy and fully rehashed grammar evidence remains
applicable.

This closes the semantic review for target-only base Topsy-Turvy. It does not
accept the other package emitter (Gen9SSB Rigged Dice), stage swaps or Baton
Pass. After recording this verdict, the canonical event grammar and shared
TypeScript/Python publication boundary were reviewed and implemented. Final
coverage attestation for that shared boundary remains pending a separate
implementation review. `faithful_complete_episode:false` remains required.

### Combined protocol validation checkpoint — implemented; review blocked

The shared JSON contract at `trainer/src/neural/protocol_contract.json` feeds
TypeScript and Python. Its 113 supported-command fixtures include deliberate
raw-only records, canonical Psych Up/Topsy-Turvy grammar, and source-backed
signed `-setboost`. Six recognized unsupported spellings classify legacy and
internal aliases separately from `-singlemove`; unknown tokens and malformed
supported records have separate rejection classes. Request privacy and
sanitized-`rqid` handling remain enforced.

The assessment's fully rehashed `|futuremechanic|opaque` case now verifies all
identity joins then rejects with Python CLI exit 2 and empty stdout. The
cross-runtime publication matrix covers 14 rejection fixtures × both observation
versions × both perspectives × input/successor = 112 fully rehashed rejections;
supported controls pass. Episode probes cover unsupported truncation, malformed
failure and committed-boundary/lineage rollback. `-singlemove` remains
explicitly unsupported. Grammar support for signed `-setboost` follows pinned
source, without a random-team occurrence claim.

Previously recorded focused verification passed: `npm run build`; 127 affected TypeScript
tests (protocol contract, observation, episode/integration, Topsy-Turvy, Psych Up,
identity, public stages and related boost replay); and 31 Python record,
canonical-action and lineage tests. Coverage-checker synthetic drift tests pass.
The implementation batch review freshly passed `npm run build`, focused raw-only/privacy and
historical-reference tests, committed-boundary rollback tests, the `-singlemove`
stop test, installed Python package loading and external-CWD TypeScript loading.
The 16 malformed Python publication candidates all reproduced. Checker drift
self-tests pass. That review recorded local digest
`68df8b2fb6c387758c37af2aef3fe04e230cd6bb92bbb70474a41a0d10c84be2`; this
independent review adds the reproduction assets to hashing and computes
`9793ca11d6ac3c696794027e0cab4150fe970bc52ee1c5fce59dcf124102b140`.
Stored and reviewed digests remain
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`.
The pinned simulator digest is unchanged. See the assessment and reproduction
artifact for exact details.

Preserve existing accepted scopes and historical identities. Keep
`faithful_complete_episode:false`. **Resume:** fix the recorded cross-runtime,
source-shape, loader-schema, fixture and pre-filter gaps before attestation; then
continue with scanner expansion, nested-effect modeling and format-digest coverage.

### Source / decisions

Pinned Showdown0.11.10 `data/moves.ts:20427–20436` negates each nonzero target stage,
leaves zero unchanged, and emits exactly
`|-invertboost|TARGET|[from] move: Topsy-Turvy`. When all seven stages are zero, onHit
returns false: the simulator emits failure for the move actor, not an inversion event.
The other package emitter (`data/mods/gen9ssb/moves.ts:2117`, Rigged Dice tag) is excluded.

Raw extraction inverts only existing sparse public entries into a fresh map. TS/Python
v2 prefix reconstruction negates each known nonzero value, preserves explicit zero as
zero (not negative zero), and leaves unknown null unchanged. No inference of hidden
stages from move success. Only the event target changes; order and independent earlier
snapshots are preserved. Refresh/restoration replay this same public evidence.

Exact four-field grammar, complete trimmed target identifier and exact Topsy-Turvy tag
validate before side filtering in both evidence helpers and the observable parser.
Python v1/v2 publication prefix validation applies the same grammar before stage replay;
bare `invertboost` rejects regardless of payload. Internal helper aliases retain existing
compatibility but do not authorize publication. Valid unresolved identity syntax is
allowed; no roster matching expansion. Raw malformed inversion records are ignored
without state mutation; strict publication rejects them.

V1 remains default and omits opponent stages. No schema, canonical identity algorithm,
legacy-reference exception or historical artifacts changed. Newly corrected raw/self
trajectories can have different IDs than previously incorrect projections. No simulator
private data is added. Psych Up/Transform/selective behavior stays within prior accepted
scopes. Rigged Dice, swap, Baton Pass and critical-hit volatiles remain excluded.
The bounded base-move semantics have scoped acceptance; combined protocol
coverage attestation remains pending. Keep `faithful_complete_episode:false`.

### Changed files / verification

Five implementation/validation sources and two new self-contained tests (hashes below).
Build and79 relevant TypeScript tests pass;28 Python canonical-action/record/lineage
checks pass. Nine new tests cover mirrored simulator inversion of mixed positive,
negative and explicit-zero stages, repeated inversion, zero-failure/no-event behavior,
later stage changes, exact event boundaries, both perspectives, private-field exclusion,
immutable earlier views, request refresh, restoration and deterministic full transitions.
Actual v2 records pass28 new Python publications across two repeat sessions per actor.
Sparse-prefix TS/Python/raw checks preserve unknown versus zero and double inversion.

Expanded cross-runtime inversion matrix:29 malformed/alias variants × both versions ×
both perspectives × input/successor =232 rehashed rejection cases. Python verifies IDs
and joins before grammar rejection. Twelve valid controls include canonical unresolved
identities. Four rehashed false-stage cases cover both perspectives/input-successor:
TS and Python reject exact-prefix disagreement; CLI exits2 with no output. Malformed
bare/missing/invalid/empty target, wrong tag (including Rigged Dice), missing/extra fields
and valid-shaped bare aliases reject. Existing Psych Up matrix, saved historical v1/v2
identity controls, public-stage/Illusion, selective clearing and Transform tests also pass.
Unaffected snapshot/transition source remains unchanged; prior six lifecycle probes reused.

Commands: `npm run build` in sim-core; selected
`PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3 node --test dist/tests/{topsy_turvy,topsy_turvy_validation,psych_up,psych_up_validation,record_identity,public_stages,selective_boosts,transform_boosts}.test.js`;
`PYTHONPATH=trainer/src` selected Python pytest on `test_pipeline_record.py`,
`test_canonical_action.py`, `test_dataset_lineage.py`. Logs `/tmp/topsy-{build,relevant,python}.log`.
Diff checks pass. Independent read-only pinned-source audit requested gpt-6-astra/high;
effective settings unverified, no delegated edits/descendants. No dependency/env changes.

### Review scope / next action

Topsy-Turvy semantic review is closed at the bounded base-move scope above.
The cross-runtime matrix now verifies canonical `-invertboost` grammar and
publication rejection behavior, retains unchanged v1 IDs and historical
references, and includes the shared test and contract in the local coverage
inventory. Classify canonical `-invertboost` as bounded Topsy-Turvy only;
Rigged Dice/mod and bare-alias exclusions remain explicit. Separate review of
the complete validator implementation remains required before attestation.

The machine protocol inventory now includes canonical `-invertboost` at the
bounded base-move scope and raw-only public `message`, while six recognized
unsupported entries remain outside accepted commands. The manifest's previous
reviewed local digest (`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`)
is preserved; the computed local digest is `df0244b25b6b4253497df70863cd5224213dcd3f8066bace37f14e87d30eabb3`.
Coverage-checker synthetic drift tests pass; the full checker intentionally
reports the changed local digest until the separate coverage review.

| Changed file | SHA-256 |
| --- | --- |
| `sim-core/src/state_extractor.ts` | `9e1adfde5d477f1513454b99f68169c8cd94810c2633fa471289f06e2bd42ced` |
| `sim-core/src/observable_state.ts` | `d329d67ad66a3c60dfecdd8ddc2118b40d010bdc10813a44dccce0e6cec37b4f` |
| `sim-core/src/public_boosts.ts` | `979fb8bb52e9b35d11f65e78049229ed12a4ecb421af7995dc8875c3594fb0de` |
| `trainer/src/neural/public_boosts.py` | `241462fcd96bfb364ad42260c98f01f646ea4c76c0f13a524f9b70b935b86339` |
| `trainer/src/neural/pipeline_record.py` | `a83eb57d65910ac5ecaad0baabd6411811f5a9f8e94995b796398f5a3579cf73` |
| `sim-core/tests/topsy_turvy.test.ts` | `a8c588f4973b613ea1baa10735e644690a2c445f138388d23a195af154c8e9e0` |
| `sim-core/tests/topsy_turvy_validation.test.ts` | `3252e2012e8efdf61b287480e9dbf7ca602e8921b7c0495f9ad31d0651b06e89` |

## Prior accepted checkpoint — combined Psych Up stage/grammar review (2026-09-25)

### Verdict / supported boundary

No scoped blockers. Bounded Psych Up public stage copying, canonical pre-filter grammar,
and Python publication alias correction are accepted and attested. No production/test
corrections in this review. Keep `faithful_complete_episode:false`; this is not complete
Psych Up mechanics, broader feature readiness or faithful complete-episode publication.

Pinned Showdown0.11.10 `data/moves.ts:14559–14575` replaces every caller stage from the
target and emits `|-copyboost|RECIPIENT|DONOR|[from] move: Psych Up`. First identifier
receives second's public-stage snapshot at the event; raw maps and TS/Python v2 maps
are independent replacements. Opposite signs, zero and unknown/null evidence persist
as copied; stale recipient entries disappear. Subsequent donor changes cannot mutate
the copy. Request refresh, restoration and standard lifecycle clearing remain intact.

Publication supports only canonical `-copyboost`, exact five fields and Psych Up tag.
Both complete trimmed identifiers validate before stage-helper side filtering/lookup;
Python validates both observation prefixes before stage reconstruction in v1 and v2.
Bare `copyboost` rejects independently of payload shape. Internal helper alias support
is not publishable grammar. Syntactic validity does not establish roster identity;
existing active-side routing is unchanged, and absent donor evidence remains unknown.
No broader identity-routing acceptance is implied. Raw extraction stays a tolerant
protocol consumer; strict malformed-record rejection is enforced on publication paths.

V1 stays default and omits opponent stages, v2 stays explicit. Valid IDs, canonicalization
and historical references are unchanged; no historical artifacts are rewritten. New
corrected self/raw trajectories can differ from previously incorrect projections.
Critical-hit volatile removal/copying (`dragoncheer`, `focusenergy`, `gmaxchistrike`,
`laserfocus`) is explicitly excluded: emitted volatile records follow existing handling,
while silent/layered changes remain unresolved. Costar/other copy tags, swap/inversion,
Baton Pass, general mechanics and features remain excluded.

### Evidence / independent reproduction

Seven scoped source/test hashes match checkpointed implementation/correction evidence.
Reused passing build19 TS/28 Python, prior privacy/Illusion/independence/restoration and
six mirrored switch/drag/faint probes where source hashes match. Fresh build14
Psych Up/validation tests pass:408 fully rehashed rejection cases cover both versions,
perspectives and input/successor prefixes;12 supported matrix controls pass. Simulator
cases retain28 Python publications and20 correctly rehashed false-stage rejections.

Independently loaded all five saved malformed-recipient/alias bundles, verified complete
identities/joins, then ran Python CLI: all exit2 with empty stdout. Paired saved v1/v2
controls publish with unchanged observation IDs. No reliance on stale-hash failures.
Logs `/tmp/psych-final-{build,tests,repro}.log`; durable originals remain in
`artifacts/validation/psych-up-review-2026-09-25/` and
`artifacts/validation/psych-up-alias-review-2026-09-25/`. Historical reproduction scripts
assert old failures intentionally; current regression tests assert the fixes.
Commands: `npm run build` then selected
`PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3 node --test dist/tests/psych_up_validation.test.js dist/tests/psych_up.test.js` in sim-core.
Independent read-only gpt-6-astra/high source review found no blocker; effective settings
unverified, no delegated edits/descendants.

### Coverage / exact reviewed state

Classified canonical `-copyboost` as represented only for bounded Psych Up stages;
Costar/mod emissions and critical-hit volatiles remain excluded. Reconciled parser count,
fingerprint, emitter and boost-group dispositions. Added two tests and seven consumed
JSON fixtures to hashing (45→54 files); affected implementation/validators already hashed.
Computed/reviewed digest:
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`.
Previous attestation: `15e0e2b5c8b77b615a420be79634f4d3fc01924a5723eb02ddcc040e867064a9`.
Pinned simulator digest unchanged:
`95cc2b31a17340cf376739ad8f02570cd847e6647da2a0760f8623aef75290fe`.
Reviewed checkout: HEAD `117df85247846548fe99ee7e3d60a26d827fc05c` plus local state
bound by this digest; HEAD alone does not contain the accepted changes.
Coverage checker, ten drift self-tests, three coverage tests and diff checks pass.
Commands: `node sim-core/scripts/check-simulator-coverage.cjs` with/without `--self-test`;
`node --test sim-core/dist/tests/simulator_coverage.test.js`. Logs
`/tmp/psych-final-{coverage,selftest,manifest-tests}.log`.

### Single next prerequisite

Implement bounded **Topsy-Turvy public stage inversion**. Pinned
`data/moves.ts:20427–20436` negates each nonzero target stage and emits
`|-invertboost|TARGET|[from] move: Topsy-Turvy`; all-zero failure emits no inversion.
Current raw extraction omits it and v2 rejects it. Trace exact grammar and add event-boundary
inversion to raw extraction and TS/Python prefix evidence, retaining zero/unknown and
independent state. Require mirrored positive/negative/zero cases, repeat inversion,
post-event changes, restoration, publication, malformed grammar and fully rehashed
false-stage rejection. Affected files: state_extractor.ts, observable_state.ts,
public_boosts.ts, Python public_boosts.py and focused tests/publication guards as needed.
Do not expand swap/Baton Pass or critical-hit volatile behavior in that slice.

## Prior blocked review — Psych Up command alias (2026-09-25)

### Scoped verdict

Canonical `-copyboost` grammar correction and valid stage-copy semantics pass review,
but combined acceptance/coverage attestation remain **blocked** by a publication command
alias bypass. No production/test/manifest edits in this review. Keep
`faithful_complete_episode:false`; critical-hit volatiles, Costar and other boost
mechanics remain excluded. V1 stays default; historical valid identities are unchanged.

### Confirmed fixed behavior / reused evidence

All four current correction hashes below match; original raw extractor, observable
parser and Psych Up simulator-test hashes also match recorded evidence. Both public
stage helpers validate canonical copy count/tag and both trimmed identifiers before
side/roster routing. Python's `_prefix` calls the same guard in v1/v2 for `-copyboost`.
Valid syntax does not require confirmed roster identity. Existing routing selects active
side evidence; unknown stages remain null when no routed donor evidence exists. This
is not a new guarantee that any unmatched displayed name yields unknown stages.

Independently reran all three original malformed-recipient artifacts: bundle identities
and joins verify, Python exits2 with empty stdout; valid control exits0 and publishes.
Log `/tmp/psych-close-originals.log`. Fresh build and13 Psych Up/validation tests pass,
including200 fully rehashed malformed cases (both versions/perspectives/input-successor
positions),28 valid Python publications and20 rehashed false-stage rejections.
Logs `/tmp/psych-close-{build,tests}.log`; command `npm run build` then selected
`PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3 node --test dist/tests/psych_up_validation.test.js dist/tests/psych_up.test.js` in sim-core.
Matching39 TS/28 Python evidence and prior six mirrored lifecycle/restoration probes
reused. Pinned moves.ts14559–14575 still establishes recipient-first, all-seven-stage
replacement, independent maps and critical-hit volatile exclusions. No identity,
snapshot, raw copying or default changes in the grammar correction.

### Exact remaining blocker

`trainer/src/neural/pipeline_record.py:136` recognizes only literal `-copyboost` for
publication grammar validation. TS observable allowlist supports only that spelling
(`observable_state.ts:879`). However both public-stage helpers normalize bare
`copyboost` as an alias; Python v1 does not run stage reconstruction at all.

Fully rehashed actual linked bundles reproduce:

- V1 successor `|copyboost||p2a: Donor|[from] move: Psych Up`: malformed empty recipient
  bypasses Python's command guard and publishes (exit0, nonempty stdout).
- V2 successor `|copyboost|p2a: Gengar|p1a: Mew|[from] move: Psych Up`: unsupported command
  spelling is normalized by Python and publishes. TS rejects both as unsupported event.

Each reproduction recomputes prefix hash/cursor, observation ID, all affected history
and transition joins and belief ID; `verify_bundle_identities` passes before publication.
Valid original controls pass. Durable self-contained scripts/controls/bundles/results:
`artifacts/validation/psych-up-alias-review-2026-09-25/`.
Run `PYTHONPATH=trainer/src /Library/Developer/CommandLineTools/usr/bin/python3 artifacts/validation/psych-up-alias-review-2026-09-25/reproduce.py` after build.
This is command-policy parity, not unresolved roster identity or stale-hash rejection.

### Single next prerequisite

Reject unsupported bare `copyboost` at Python publication entry for both v1/v2, matching
TS's exact command spelling. Keep intentional internal helper alias compatibility
separate from publishable-prefix grammar. Add valid-shaped and malformed alias cases to
the rehashed matrix across both perspectives and input/successor positions, retaining
canonical valid controls and unknown-stage behavior. Then repeat combined review.
No requirement to expand the TS grammar or rewrite historical records.

### Coverage / review status

No classifications or attestations changed. Existing45-file computed digest remains
`4ae9411a8f016f6adda22db484324ff96e30b6d4d8ee14aa4bf72aa8c45eb693`;
checker flags expected source drift and new `-copyboost`. Ten synthetic drift self-tests
pass before expected failure; logs `/tmp/psych-close-{coverage,selftest}.log`. Diff checks
pass. After correction/acceptance review both new Psych Up tests and consumed malformed
fixture JSONs for hashing, plus exact canonical-command/Costar exclusions. Independent
read-only gpt-6-astra/high review confirmed alias blocker; effective settings unavailable,
no delegated edits/descendants. No complete Psych Up or faithful-publication acceptance.

| Changed file this correction | SHA-256 |
| --- | --- |
| `sim-core/src/public_boosts.ts` | `fb90a9226bf214bd5e608f58825b5b10f8e454be13fafc722db205e0c6f2a05f` |
| `trainer/src/neural/public_boosts.py` | `3a9ea81dd9891357f59af99bfeb76f2c4afaea9aa3d7f3cafe7c3dbef6d849dc` |
| `trainer/src/neural/pipeline_record.py` | `3622d34e14c5ca7f1fecce4027aec11f665773f929daed8f3cf9880786b40d30` |
| `sim-core/tests/psych_up_validation.test.ts` | `44e354a928a79b423b8e163426096cd4f34dfdde1f14cdd1a5db32c8b584982c` |

## Prior blocked review — bounded Psych Up (2026-09-25)

### Verdict / blocking reproduction

**Acceptance blocked; no coverage attestation.** Valid stage semantics pass review, but
malformed copy records can be published by Python. All five checkpoint hashes match;
no implementation/test edits made during review. Keep `faithful_complete_episode:false`.
V1 default and prior accepted scopes remain unchanged; no historical identities rewritten.

At `sim-core/src/public_boosts.ts:19` and `trainer/src/neural/public_boosts.py:26`,
`if (!player) continue` / `if not player: continue` runs before copy grammar validation.
The later copy branches (TS:42, Python:53) validate only the donor identifier. Thus a
missing/unrecognized recipient skips validation, and an empty recipient name passes
side detection. TS observable parsing rejects these, but Python publication accepts:

- `|-copyboost||p1a: Mew|[from] move: Psych Up`
- `|-copyboost|garbage|p1a: Mew|[from] move: Psych Up`
- `|-copyboost|p2a: |p1a: Mew|[from] move: Psych Up`

Reproduction appends each line to a valid actual v2 successor prefix, recomputes cursor,
prefix hash, observation ID, all affected references/transition joins and belief ID.
Python exits 0 and publishes; TS rejects the same observation. Valid control passes.
Durable scripts/control/bundles/results:
`artifacts/validation/psych-up-review-2026-09-25/`.
Run `PYTHONPATH=trainer/src /Library/Developer/CommandLineTools/usr/bin/python3 artifacts/validation/psych-up-review-2026-09-25/reproduce.py` after build.
Direct helper probes also accept bare `|-copyboost`, invalid p3 recipient and
missing-recipient Costar. These are grammar bypasses, not permissible unknown evidence.

### Pinned source and supported grammar

Showdown 0.11.10 `data/moves.ts:14559–14575` assigns every target boost directly to the
Psych Up caller, then emits `|-copyboost|RECIPIENT|DONOR|[from] move: Psych Up`.
All seven stages exist in simulator state (`sim/pokemon.ts:406`). The first protocol
identifier receives the second's stages, replacing rather than accumulating. Only this
exact five-field Psych Up grammar is supported. Missing/extra fields and different
from-tags reject in the observable parser and TS/Python stage replayers. Costar's
`data/abilities.ts:712` emission remains unsupported; swap/inversion and Baton Pass
remain excluded. Existing public-stage replay alias handling remains unchanged.

Raw extraction clones the donor's public sparse map at the exact event, clearing stale
recipient entries without inventing absent evidence. V2 independently clones the seven
public-prefix integer/null stages; missing donor evidence is unknown. Later changes are
independent. No simulator-private stats/counters, request-derived opponent facts or
recipient species/type changes are inferred. Transform remains separate and unchanged.

Critical-hit volatiles remain outside stage acceptance. Psych Up removes/copies
`dragoncheer`, `focusenergy`, `gmaxchistrike`, `laserfocus` before the copy event. Pinned
`moves.ts:4211–4223,6191–6201,7058–7071,10393–10409` includes silent starts, suppressed
G-Max Chi Strike start, copied layers/Dragon-type flag and removals without end events.
This implementation does not infer those changes from `-copyboost`: existing emitted
volatile records follow existing handling, so silent state can remain incomplete.
Their presence is not a stage-only rejection trigger and does not establish complete
Psych Up correctness or faithful episode publication. Constructed tests use no such
volatiles; no broader volatile support is claimed.

### Changes / validation

Four implementation files and one new self-contained regression (hashes below).
Build and 101 relevant TypeScript tests pass, including nine new Psych Up cases;
28 Python canonical-action/record/lineage tests pass. New mirrored tests compare all
seven stages to the real simulator with mixed signs/zero, previously boosted caller,
repeated copy, later independent changes, request refresh, restored snapshots, exact
prefix boundary, immutable earlier observations, private-field exclusion and v1 omission.
Two repeat sessions produce identical transitions/records. 28 new Python publication
checks pass; 20 false-stage bundles with recomputed observation/belief/reference IDs
reject in both runtimes against prefix evidence (Python emits no record). Two incomplete
prefix cases retain null/absent evidence and verify TS/Python parity. Grammar tests
reject Costar/other tags and missing/extra fields. Refreshed Transform/selective/public
stage suites preserve accepted clearing, Illusion, privacy and lifecycle behavior.

Commands: `npm run build` in sim-core; with
`PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3`, run
`node --test dist/tests/{psych_up,selective_boosts,public_stages,transform_boosts,record_identity,observable_state,pipeline_integration,state_extractor}.test.js`.
Python: `PYTHONPATH=trainer/src` pytest on `test_pipeline_record.py`,
`test_canonical_action.py`, `test_dataset_lineage.py`. Logs `/tmp/psych-{build,relevant,python}.log`.
Diff checks pass. Read-only source audit requested gpt-6-astra/high; effective settings
unverified, no delegated edits/descendants. No dependency/environment changes.

Coverage intentionally pending: existing 45-file computed digest
`921f3974723da699aadd8bea49243021e6413c42ed046893a015d39a528b90e5`
differs from accepted `15e0e2b5c8b77b615a420be79634f4d3fc01924a5723eb02ddcc040e867064a9`;
checker also reports new `-copyboost` parser token. Ten drift self-tests pass, then
report expected drift. Logs `/tmp/psych-{coverage,selftest}.log`. Manifest/attestation
untouched; new regression is not yet included in hashing.

### Review evidence / single next prerequisite

Fresh build and nine Psych Up cases pass, including28 valid Python publications and20
fully rehashed false-stage rejections. Matching101 TS/28 Python evidence reused.
Fresh six mirrored simulator probes show copied stages clear at switch/drag/faint,
restoration agrees, and earlier prefixes remain immutable; logs/scripts
`/tmp/psych-review-lifecycle.{cjs,log}`. Source review confirms first recipient, independent
replacement, unknown propagation, exact Psych Up-only tag and explicit volatile scope.
Logs `/tmp/psych-review-{build,tests}.log`. Independent read-only gpt-6-astra/high review
confirmed blocker; effective settings unavailable, no delegated edits/descendants.

**Next task: fix copy-event grammar validation before side filtering in both public-stage
helpers.** Require exact count/tag and both full identifiers before any no-player skip;
reject rather than repair. Add compact malformed-recipient/donor/tag tables plus actual
rehashed Python-publication regressions. Preserve valid controls, v1 behavior and
replacement/null semantics. Then repeat scoped review. Existing implementation sources
are hashed; new `tests/psych_up.test.ts` needs coverage inclusion after acceptance.
Do not classify/attest now. Checker reports expected changed45-file digest and new
`-copyboost`; all ten synthetic drift self-tests pass before expected drift failure.
Logs `/tmp/psych-review-{coverage,selftest}.log`; diff checks pass.

| Changed file | SHA-256 |
| --- | --- |
| `sim-core/src/state_extractor.ts` | `81682695126e8add8670370d73a9d568fbf009ba3a2c4da6f120f1199b4ab0a3` |
| `sim-core/src/observable_state.ts` | `1979de89499655c488ab59e62c4535de59715ed80e29d7cac6be83978b996be1` |
| `sim-core/src/public_boosts.ts` | `4edff29e0c3288868a243b6860c9feb2c95764567e876799ff4220ca8f423292` |
| `trainer/src/neural/public_boosts.py` | `8f4182af637db10edd890e3e773d0ff5e179f4b8e57eb65c92a4c8c414619bd1` |
| `sim-core/tests/psych_up.test.ts` | `b7cca09ddf4f6bdc1b7158daa4baadcc43164bc2911ef42f80659f061ff475ab` |

## Prior accepted checkpoint — selective stage clearing scoped accepted (2026-09-25)

### Verdict and scope

No blocking findings or production/test corrections. All six implementation-checkpoint
hashes below match. Prior v2/reference acceptance stands. Selective sign clearing is now
scoped accepted and attested; `faithful_complete_episode:false` remains required.
V1 stays default, opponent stages remain omitted there, and v2 stays explicit. Identity
algorithms/schema versions did not change; no historical record/reference is rewritten.
Corrected new raw/self values can yield different identities for previously incorrect
trajectories, which is not a migration of stored records.

### Source / semantics reviewed

Pinned Showdown 0.11.10 `data/items.ts:7173–7214` selects only negative stages for held/
flung White Herb and emits `[silent]`; `sim/battle-actions.ts:1526–1535` emits `[zeffect]`
for Z effects. `battle-actions.ts:774–804` emits Spectral Thief target positive-clear,
separate user boost deltas, then `-anim`. Only the first clear identifier is modified;
recipient gains are never applied implicitly or twice. Raw maps retain opposite signs,
explicit zero and absent keys. TS/Python v2 maps retain opposite signs, zero and null.
An individual selective clear does not establish an unknown value; the bounded scalar
model conservatively does not infer sign intervals across unknown-stage sequences.

Negative grammar accepts untagged legacy records or exactly one `[silent]`/`[zeffect]`
tag; malformed extras reject. Spectral Thief animation requires exactly source ident,
literal move name and target ident, is retained raw-only and changes no stages. Other
animations reject. Positive-clear validation retains its existing target/source/effect
shape with possible further fields; only the pinned no-extra-field emitter is reviewed.
Constructed Spectral Thief fixtures (Past move) verify simulator mechanics, not expanded
Gen 9 random-team legality. Copy/swap/inversion, Baton Pass, general animations and
broader lifecycle/feature correctness remain excluded.

### Validation / coverage

Reused matching build/92 relevant TS/28 Python evidence, including 36 new Python record
publications. Fresh build and 17 selective/identity cases pass, including the 12 mirrored
selective cases and 36 Python publications. Evidence covers mixed signs/zero, repeated
clears, later deltas, exact event boundaries, request refresh, snapshot restoration,
immutable earlier frames, independent target/source state, private-field exclusion,
v1 omission and deterministic transition results. Prior matched Illusion/lifecycle and
Transform evidence remains applicable. Independent actual White Herb v2 probe accepts
the valid bundle, then rejects false retained Attack in both TS/Python even after all
observation/belief/reference identities are recomputed; Python publishes no output.
Logs `/tmp/selective-review-{build,tests,probe}.log`; probe scripts
`/tmp/selective-review-probe.{cjs,py}`. Selected Python remains
`/Library/Developer/CommandLineTools/usr/bin/python3`. Independent read-only source
review found no blocker; requested gpt-6-astra/high, effective settings unverified,
no delegated edits or descendants.

Added `tests/selective_boosts.test.ts` to hashing (44→45 files); all four implementation
files and existing changed regression were already included. Classified selective clears
as represented (raw/self and opt-in v2), added narrow raw-only `-anim` parser disposition,
and documented its `addMove` emitter beyond the literal `.add` inventory. Recomputed
parser fingerprint/count; known exclusions remain explicit. New computed/reviewed digest:
`15e0e2b5c8b77b615a420be79634f4d3fc01924a5723eb02ddcc040e867064a9`.
Prior digest `96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d`.
Pinned simulator digest unchanged:
`95cc2b31a17340cf376739ad8f02570cd847e6647da2a0760f8623aef75290fe`.
Reviewed checkout: HEAD `117df85247846548fe99ee7e3d60a26d827fc05c` plus local changes
bound by the new digest; HEAD alone is not the accepted implementation.
Coverage checker, all ten drift self-tests, three coverage tests and diff checks pass.
Commands: `node sim-core/scripts/check-simulator-coverage.cjs` with/without `--self-test`;
`node --test sim-core/dist/tests/simulator_coverage.test.js`. Logs
`/tmp/selective-review-{coverage,selftest,manifest-tests}.log`.

### Single next prerequisite

Implement bounded **Psych Up `-copyboost` stage reconstruction**. Pinned
`data/moves.ts:14556–14575` replaces the caller's complete stage table from the target
and emits `-copyboost|SOURCE|TARGET|[from] move: Psych Up`; current raw extraction omits
it and v2/parser reject it. Affect `state_extractor.ts`, `observable_state.ts`,
`public_boosts.ts`, Python `public_boosts.py` and a focused regression. Copy all seven
stages at the event into an independent map; preserve null evidence, clear stale caller
stages, and verify mirrored refresh/restoration/publication and later independent changes.
Keep Psych Up critical-hit volatile copying, swap/inversion and Baton Pass separate;
do not claim full Psych Up or faithful complete-episode readiness.

| Changed file | SHA-256 |
| --- | --- |
| `sim-core/src/state_extractor.ts` | `3b086276ed29c393c0147c44a1f07a5b9bef505a677da1031a6ef5882e07c023` |
| `sim-core/src/observable_state.ts` | `dc473841b5b62523199aded52dc43fe25cbefdbc909f9d68f1bbb64f6d9e9680` |
| `sim-core/src/public_boosts.ts` | `f360094ce16a9fbe8972977c8d4a39d5ba74d67d4c73e5d46715095d738cb718` |
| `trainer/src/neural/public_boosts.py` | `452c2fddb24d3ea2f89a72bcc7de079b2a504294ce6c23525cf1694d454ae8b4` |
| `sim-core/tests/selective_boosts.test.ts` | `8175b0d851c51848be806073d66b6d3f9cc869f57ecdd877920a237eacf53aee` |
| `sim-core/tests/public_stages.test.ts` | `1abc71275fd4ffe823ff8634cf1b5663053228c118f41ef6e93f4bea3e55b1d4` |

## Prior accepted checkpoint — historical-reference and v2 publication (2026-09-25)

### Scope / decisions

Combined public-stage v2 publication, Python content identity enforcement and
historical-reference validation are scoped accepted and attested. No blocking findings.
Prior accepted simulator/lifecycle/raw Transform slices stand. Default observable v1,
opt-in v2, canonical identity definitions and execution contracts remain unchanged.
Keep `faithful_complete_episode:false`. Existing local work/historical artifacts are
preserved; no installs, training, feature expansion or environment changes.

Original reproductions remain under
`artifacts/validation/identity-history-review-2026-09-25/`; fresh results are recorded below.

### Complete reference contract / parity findings

Source: `sim-core/src/belief_state.ts` current/history validation around 896-945.
Python uses one `_verify_reference` for current and every historical entry:

| Field / boundary | Required validation |
| --- | --- |
| object / keys | Object with exactly six fields; no missing/extra keys except the explicit v1 omission below |
| schema_version | Supported version, homogeneous with enclosing observation; null/unknown/mixed reject |
| observation_id | String, exactly obs- plus 64 lowercase hex characters; history IDs unique |
| source_kind | String: sim_core/replay/live |
| event_cursor | Non-boolean safe integer, nonnegative, bounded by source prefix; nondecreasing history |
| protocol_prefix_hash | String, 64 lowercase hex characters; matches exact prefix slice at cursor |
| snapshot_phase | String: pre_decision/post_resolution/forced_switch/terminal/other |
| joins | Nonempty history; last entry equals current canonically; current matches verified observation; successor preserves input history; known references match supplied observations |

Current and historical refs share type checks, closing Python boolean/numeric equality
aliases. Approved integral float spelling is a JS-number equivalent, not coercion of
strings/bools. Canonical comparison preserves absent/null distinctions. Supported
historical source/phase values need not equal current values, matching TS.

Two nearby TS object-contract holes were corrected: first historical cursor -1 is now
explicitly rejected; current/history observation IDs require exact length 68, excluding
a trailing newline that JavaScript's dollar-anchor regex alone could admit. These are
malformed-reference restrictions; no valid producer identity changes.

Legacy compatibility stays explicit: only otherwise complete v1 references may omit
schema_version. Actual absence remains in the hash; no defaults or repaired values are
serialized. V2 requires the field; null is not omission. Valid histories/IDs/publication
remain unchanged. Historical payloads absent from a bundle cannot be rehashed from
references alone; this work validates fields and anchored joins, not unseen content.

### Changed files / hashes

- `trainer/src/neural/ts_identity.py`: `115af529c5c9c873d18c1e76cb3ca0cb8e543d24e32cc6a76ae534551d7d411a`
- `trainer/src/neural/pipeline_record.py`: `04a6784391d5e0dcd2435a40835b7a6787677a3323dd315d2678691512eab282`
- `sim-core/src/belief_state.ts`: `ad9d1da67135fec857f7c4dc9de6e1217483d7280d94be0d33a67f2955b0d5d1`
- `sim-core/tests/record_identity.test.ts`: `4a342c28a60cc5c2e85023a6883dd4151a3ef85e61c0a361c58f5623e3fa80e1`

The implementation replaced ad-hoc version checks with complete reference validation.
This review changes only manifest classifications/attestation and documentation.

### Validation / commands

- `npm run build --prefix sim-core`: pass (`/tmp/history-fix-build.log`).
- `PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3 node --test` on dist/tests
  record_identity,public_stages,belief_state,pipeline_integration,forced_switch,revival,
  pipeline_episode,transition: 78/78 (`/tmp/history-fix-regressions.log`).
- Two-transition v1/v2 table-driven regressions mutate all six fields at all three
  positions, resealing both beliefs and successor parent references. Missing/extra keys,
  null/bool/number/array/object values, unknown versions/domains, malformed/duplicate IDs,
  stale hashes, negative/fractional/unsafe/decreasing/out-of-bounds cursors and broken
  current/history joins reject before publication. Supported source/phase combinations,
  valid controls, legacy v1 omission and original identity/immutability checks pass.
- Prior downgrade regressions, nested content identity and public-stage checks are
  included in the 78 tests. Matching prior 268-test evidence reused for unaffected
  lifecycle/Illusion/restoration/typing mechanics.
- `PYTHONPATH=trainer/src /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_canonical_action.py
  trainer/tests/test_dataset_lineage.py -q`: 28/28 (`/tmp/history-fix-python.log`).
- Original reproduction rerun with the selected Python interpreter: both previously
  accepted invalid fields now exit 2; valid control exits 0. `git diff --check`: pass.
- Read-only contract audit requested gpt-6-astra/high; effective settings unavailable;
  no delegated edits or descendants.

### Combined semantic review / coverage — accepted (2026-09-25)

All four checkpoint hashes match. Source review confirms six-field validation at every
history position, exact prefix/identity joins and no coercion. Negative first cursors
and trailing-newline IDs are malformed under the contract; stricter TS guards preserve
valid IDs. Legacy omission remains deliberately Python-only compatibility for otherwise
complete v1 references; TS-produced references stay explicit. V1 remains default;
v2 requires opt-in. No observation, belief, record or historical reference is repaired
or migrated in place. Unseen historical payloads remain outside content-verification
claims. Canonical parity and public-stage evidence checks remain independent.

Fresh build and 26 identity/public-stage tests pass (`/tmp/history-final-{build,tests}.log`),
including full two-transition field tables, legacy controls and immutable original IDs.
Matching 78 targeted TS/28 Python evidence and prior 268 unaffected lifecycle/Illusion/
restoration/typing evidence reused. Independently reran original domain reproductions:
control passes both runtimes; invalid source_kind/snapshot_phase with recomputed outer
hashes reject before publication (`/tmp/history-final-repro.log`). Both old downgrade
reproductions reject; fully rehashed false stages also reject against the exact public
prefix (`/tmp/history-final-identity-probes.log`). Raw-view/public-stage privacy,
Transform copying, lifecycle resets and deterministic publication remain within scope.
Independent read-only reviewer found no blocker; requested gpt-6-astra/high, effective
settings unavailable, no delegated edits/descendants. No production/test corrections.

Added six files to coverage hashing (38→44): `src/public_boosts.ts`,
`../trainer/src/neural/public_boosts.py`, `../trainer/src/neural/ts_identity.py`,
`tests/public_stages.test.ts`, `tests/record_identity.test.ts`, `tests/belief_state.test.ts`.
Other changed validators and shared lifecycle fixture were already included.
Qualified ordinary boost/Transform classifications for default v1 omission versus
bounded v2 publication. Selective clears are explicitly unsupported (raw implementation
clears too much; v2 rejects). Added the opt-in observation version to manifest contracts;
updated the representation gap without accepting feature consumers or broader mechanics.

Computed/reviewed 44-file digest:
`96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d`.
Prior attestation:
`16819a7d19f47b6a412a8a9ed540cde284ac524df290cc5ac52d4293082eaab7`.
Pinned simulator digest unchanged:
`95cc2b31a17340cf376739ad8f02570cd847e6647da2a0760f8623aef75290fe`.
Reviewed checkout: HEAD `117df85247846548fe99ee7e3d60a26d827fc05c` plus local changes
bound by that digest; this is not a claim that HEAD alone contains the accepted slice.
Coverage checker, all ten synthetic drift self-tests, three simulator coverage tests
and diff checks pass. Commands: `node sim-core/scripts/check-simulator-coverage.cjs`
(with/without `--self-test`), `node --test sim-core/dist/tests/simulator_coverage.test.js`.
Logs `/tmp/history-final-{coverage,selftest,manifest-tests}.log`.

### Single next prerequisite

**Correct selective positive/negative stage clearing.** Pinned-source public events
must clear only stages of the indicated sign while retaining opposite/zero stages;
unknown stages must not become unjustified zeros. Affected implementation:
`sim-core/src/state_extractor.ts` (combined clear cases around 233),
`sim-core/src/public_boosts.ts`, `trainer/src/neural/public_boosts.py`; add focused
simulator-backed regressions, then update the observation contract/classification in
a separate review. Acceptance: mirrored mixed positive/negative/zero maps, exact event
order, request refresh, restoration and deterministic Python publication; ordinary
clear-all and accepted Transform behavior remain compatible. Keep copy/swap/inversion,
Baton Pass, broader lifecycle/field reconstruction and feature consumers separate.
`faithful_complete_episode:false` remains required.

### CE-02 checkpoint — grammar and audience boundary (2026-10-01)

CE-02 adds no coverage-digest attestation and does not accept PIPELINE-002.
The shared contract now classifies the six bare v2-stage aliases as represented,
states the validator-effective `move` target grammar, orders accepted HP/stage
tags, and rejects repeated source-singleton HP/heal/stage tag kinds before TypeScript
projection or Python publication; it also requires the reviewed exact `clearpositiveboost` payload. The pinned
public auto-tie `bigerror` warning is raw-only and exact; other diagnostic text
is rejected. Spectator ingestion and both publication boundaries fail closed if
private request/error/split evidence appears. CE-03 source/reachability rows,
complete-episode evidence, and `faithful_complete_episode:false` remain open.
The observable-state fixture's exact Destiny Bond control is aligned with the
already accepted CE-01 raw grammar; its malformed tagged variant remains a stop.
Focused macOS validation for the CE-02 singleton-tag repair computes unreviewed local coverage digest
`ff28391b147085606c0cdd7898abca255ba6d0e6407247daef5912ecd33ab74e`.
The manifest's stored and reviewed CE-01 digest remains unchanged; semantic
acceptance and any CE-02 digest attestation require a separate review.

### CE-02 checkpoint — spectator private-channel ingress repair (2026-10-01)

`appendPublicSpectatorChunk`, the `listenSpectator` ingestion boundary, now
rejects every CE-02 nonpublic command (`request`, `error`, `split`, `debug`,
and `showteam`) before appending to the public candidate log. The addressed
player request path remains unchanged. Focused TypeScript checks exercise each
record through direct validation and the candidate-ingress path, prove that a
rejection leaves the accumulated public candidate untouched, and retain public
`turn` and exact auto-tie warning controls. This is an unreviewed repair;
CE-03 route proof, CE-02 semantic acceptance, and `faithful_complete_episode:false`
remain unchanged. The resulting unreviewed local coverage digest is recorded
by the focused checker: `8e9fa02026be4613695a3e0996ce27370fedf34e956d6f8753e6d7f87475b232`.

### CE-02 scoped review verdict (2026-10-01)

Focused review accepts the complete bounded CE-02 grammar, privacy-routing,
and reachability closure batch, including the singleton-tag and spectator-ingress
repairs. It attests local coverage digest
`8e9fa02026be4613695a3e0996ce27370fedf34e956d6f8753e6d7f87475b232`.
This verdict does not accept PIPELINE-002, close CE-03, or change
`faithful_complete_episode:false`.

### CE-03A checkpoint — generator-to-output closure ledger (2026-10-01)

CE-03A binds the pinned direct `gen9randombattle` generator surface without
adding lifecycle behavior. The coverage checker now compares the complete
generated move and ability candidate memberships, finite direct move-origin
sets for `twoturnmove`, `cantusetwice`, and `moveData.volatileStatus`, plus the
`randomMoveset`/ability/item selector source slices and the singles/doubles
item guard. It fails closed on a new direct candidate, finite value, selector,
or guard until the closure ledger has an explicit disposition.

The ledger distinguishes authored membership, generator selection, and realized
battle witnesses. It records deterministic generated Destiny Bond/Glaive Rush
witnesses as CE-01 raw-only evidence; it leaves repeat-use hints, called/copy
two-turn paths, callback-mutated volatile values, ability/item callback output,
and linked status as CE-03B/CE-04 work. No item, ability, lifecycle, request,
episode-envelope, or `faithful_complete_episode` behavior changed.

Focused source/configuration self-tests cover synthetic generated-candidate,
finite-value, and item/ability guard drift. The new local digest is unreviewed:
`3adb4789cb87e6a8750af0e8fefa9d424e40ee25b61a870e1c54ca5fbf1be774`.
This is not a PIPELINE-002 or faithful-episode acceptance.

### CE-03A scoped review verdict (2026-10-01)

Focused review accepts the bounded direct generator-to-output ledger and its
fail-closed drift coverage. It attests local coverage digest
`3adb4789cb87e6a8750af0e8fefa9d424e40ee25b61a870e1c54ca5fbf1be774`.
This verdict does not close CE-03B/CE-04, accept PIPELINE-002, or change
`faithful_complete_episode:false`.

### CE-03B checkpoint — indirect and no-route source proofs (2026-10-01)

The [complete-episode audit](COMPLETE_EPISODE_CLOSURE_AUDIT.md#ce-03b-source-proof-closure-matrix-2026-10-01)
now contains the CE-03B proof matrix B01–B32 for all assigned C/R routes.
These are source-proof dispositions for the pinned generated-origin path,
not a coverage attestation or an acceptance of capture/lifecycle behavior.
Historical candidate/unproven labels remain historical; the new matrix is the
current evidence checkpoint for the paths it explicitly proves.

The move-access proof starts with 350 authored IDs, follows Sleep Talk's own
slots, Transform/Imposter copying, Magic Bounce reflection, Dancer re-execution
and Encore/lock selection, and adds only Struggle (recharge is a control
request). Metronome and other registry/call/copy expanders have no seed.
The ability bound is 203 authored candidates plus the six Ogerpon/Terapagos
form defaults; item selectors and existing-item transfer/reuse give a finite
66-ID conservative bound, with five Gluttony alternatives explicitly
unreachable. These are bounds, not claims that every candidate is selected
or witnessed. Items and selector inputs remain private until public evidence.

This closes source no-route obligations for Grudge/Rage, Instruct, Psych Up,
unseeded singleturn/two-turn/stage-swap/theft/Baton Pass/Reflect Type routes,
unseeded copied abilities/items, parser aliases and legacy RainDance field-end,
and the named other-format routes. Costar/Commander also have independent
single-active ally-guard proofs. Contrary+Belly Drum is excluded by the
relational slot/ability-copy proof, not independent candidate absence.
Lunar Dance/Doom Desire are unseeded; healreplacement is a Z-only slot path.
Revival's active-target/fainted-reviver and simultaneous two-side selection
variants have singles source-order no-route proofs; consecutive selections
and copied users remain explicit CE-05 capture obligations. Requestless or
all-wait nonterminal snapshots are transient/error states, not stable engine
decisions; settling/restoration acceptance remains CE-05.

**New narrow reachable blocker: CE-04-ANIM.** Generated Sunflora using Solar
Beam in sun and generated Armarouge consuming Power Herb for Meteor Beam emit
public `-anim` forms rejected by the current Spectral-Thief-only grammar.
Minimal source reproductions use `Teams.generate('gen9randombattle',
{seed:[n,2,3,4]})[slot]` (zero-based): Sunflora `93/4` versus Ursaluna-Bloodmoon
`53/5`, `sunnyday/calmmind` then `solarbeam/calmmind`; or Armarouge `22/4`
versus that Ursaluna, `meteorbeam/calmmind`. A controlled battle with seed
`[1,2,3,4]` emits respectively `|-anim|p1a: Sunflora|Solar Beam|p2a: Ursaluna`
and `|-anim|p1a: Armarouge|Meteor Beam|p2a: Ursaluna`; both are expected
`Unsupported raw -anim record.` rejections. The future child must derive
source suffixes/roles and validate both runtimes, with no generic allowlist.
No correction was implemented here.

Other precise children retain existing semantics boundaries: Shed Tail silently
transfers only Substitute, Spirit Shackle establishes private trapped/trapper
links, ability/item/slot consequences need existing-field truth validation,
and Encore can force repeated Blood Moon/Gigaton Hammer before the next
Struggle request. The audit gives exact generated-set witnesses and focused
OBS/BEL/ACT/TRANS/PRO/PIPE/DATA acceptance obligations for CE-04/CE-05.

Validation: local source/configuration probes confirmed the domains, sole
generated call entry and 21 nested move-hit volatile values; deterministic
witnesses confirmed both rejected charge animations, both accepted repeat-use
hints with subsequent Struggle requests, Spirit Shackle links, and Shed Tail's
Substitute-only transfer. These use real selected sets in controlled source
battles and do not claim full random episodes or absence from sampling.
`git diff --check` passed. Only this checkpoint and the closure audit changed.
All proof dependencies are already covered by the scanner's source/runtime
root hashes, so no scanner regression was needed. No manifest, code, test,
dependency, or digest field changed; existing attestation
`3adb4789cb87e6a8750af0e8fefa9d424e40ee25b61a870e1c54ca5fbf1be774`
is untouched. **CE-03B scoped source-evidence review verdict: unresolved.**
B10/CE-04-ANIM omits Dragon Darts: pinned `data/moves.ts:4265–4275` marks it
two-hit `smartTarget`, and `sim/battle-actions.ts:896–898` emits `-anim` on the
second hit. `Teams.generate('gen9randombattle', {seed:[59,2,3,4]})` selects a
Dragapult set with Dragon Darts; a controlled battle (seed `[1,2,3,4]`) against
passive Snorlax emits `|-anim|p1a: Dragapult|Dragon Darts|p2a: Snorlax` after
`dragondarts`/`splash`. The current raw grammar accepts only Spectral Thief, so
this reachable single-target animation remains unaccounted. Include the exact
form in the source disposition and CE-04-ANIM boundary before closing CE-03B.
No parser or runtime change was made; PIPELINE-002 and
`faithful_complete_episode:false` remain unchanged.

### CE-04-ANIM implementation checkpoint (2026-10-01, unreviewed)

CE-04-ANIM now source-closes the directly reachable public `-anim` family for
the pinned `gen9randombattle` generator. The source table in the closure audit
traces every base emitter and its condition: Solar Beam in sun, Meteor Beam
after generated Power Herb consumption, and Dragon Darts on its second
`smartTarget` hit. Spectral Thief remains a bounded compatibility form outside
the generated domain. Electro Shot and Solar Blade are excluded because their
emitter conditions exist but neither move is in the generated M domain; custom
mod emitters are outside pinned Gen 9 singles.

Shared TS/Python contracts now accept only the four exact labels with active,
opposing `p1a`/`p2a` actor/target roles and no tags. They retain them as raw
public evidence only. Table-driven controls cover all labels, both perspectives
and input/successor prefixes; malformed labels, identifiers, roles, field
counts and tags reject before projection and publication. Mirrored generated
fixtures reproduce Solar Beam, Meteor Beam and Dragon Darts for p1 and p2;
the Dragon Darts second-hit record projects and publishes while its malformed
controls produce no output. No request progression or other CE-04 lifecycle
behavior changed. The resulting local coverage digest is recorded as
**unreviewed** (`ce0171ddd7377e3a2f24464212c6e48223f7ef73228098320132ce147843da7e`) in the closure audit; this checkpoint does not attest it, accept
PIPELINE-002, or change `faithful_complete_episode:false`.

### CE-04-ANIM scoped review verdict (2026-10-01): accepted

The source table now supports Solar Beam only through its direct generated
sun route. Meteor Beam remains directly supported by generated Power Herb
consumption, and Dragon Darts by the second singles `smartTarget` hit. The
generic Power Herb-to-Solar-Beam transfer remains explicitly unproven and is
assigned to the named CE-04-CALLBACK item-transfer child; it supplies no current
format-reachability assertion or grammar expansion.

Focused TypeScript/Python validation confirms exact active-opponent grammar,
raw-only handling, public rejection/publication rollback, both perspectives,
both prefixes, and coverage-source inclusion. The six base-package emitter
sites are accounted for; Spectral Thief stays constrained, while Electro Shot
and Solar Blade remain rejected. The reviewed local digest is
`ce0171ddd7377e3a2f24464212c6e48223f7ef73228098320132ce147843da7e`.
This accepts CE-04-ANIM only; the CE-04-CALLBACK item-transfer child,
PIPELINE-002, and `faithful_complete_episode:false` remain unchanged.

### CE-03B scoped source-proof review verdict (2026-10-01): accepted

The earlier Dragon Darts gap is resolved: generated `multihit:2`,
`smartTarget:true` Dragon Darts reaches `BattleActions`' second-hit `-anim`
emitter and CE-04-ANIM accepts its exact opposing-active singles record.
The CE-03B matrix therefore no longer implies that singles excludes this path.

All B01–B32 source dispositions remain as reviewed: no-route conclusions have
their pinned source chains, while reachable effects stay assigned to explicit
CE-04/CE-05 children. The indirect Power Herb-to-Solar-Beam transfer remains
unproven and assigned to CE-04-CALLBACK; it is not treated as CE-03B closure.
No implementation, scanner, manifest, dependency, staging, commit, or broader
documentation change entered this closeout. This accepts CE-03B source-proof
closure only and leaves PIPELINE-002 and `faithful_complete_episode:false`
unchanged.

### CE-04-SHEDTAIL implementation checkpoint (2026-10-01, unreviewed)

Pinned `Moves.shedtail` and `BattleActions.switchIn` prove that the outgoing
Substitute starts with `[from] move: Shed Tail`, while the incoming replacement
switch is exactly suffixed `[from] Shed Tail`. `Pokemon.copyVolatileFrom` with
the `shedtail` cause copies Substitute only, skips boosts, and clears the
departing volatile state. The source/lifecycle table in the closure audit
records the public HP, Substitute, switch/end/reset and restoration boundaries;
it deliberately omits private Substitute HP, hidden selection state and every
unrelated copied simulator field.

The extractor now requires that exact incoming switch suffix before projecting a
Substitute transfer. A generic valid switch tag such as `[from] move: Shed
Tail` remains raw evidence and cannot manufacture typed state. Focused pinned
fixtures cover both acting sides, both perspectives, exact prefixes,
Substitute removal, drag/faint clearing, privacy, deterministic restoration,
rejected forced-switch rollback, and Python publication of the emitted
transition record. No CE-04-LINK/CALLBACK/SLOTS or CE-05 behavior changed.

Focused build and 25 targeted TypeScript cases pass; the coverage self-test
passes. The computed local coverage digest
`14107dfaeb916b654b1acf376cf61226088abdc3fb6939d64098779f2f979d62` is
**unreviewed**. It does not accept PIPELINE-002 or change
`faithful_complete_episode:false`.

### CE-04-SHEDTAIL scoped review verdict (2026-10-01): accepted

The exact pinned incoming `switch ...|[from] Shed Tail` signal is now the
sole typed Substitute-transfer trigger. The outgoing `[from] move: Shed Tail`
start remains evidence of the move, and generic tagged switch forms cannot
create a transfer. Pinned lifecycle behavior copies only Substitute, skips
boosts, and clears the outgoing volatile state. Focused TypeScript and Python
evidence covers both perspectives, removal/reset paths, v2 publication,
restoration, and forced-switch rollback. The reviewed local coverage digest is
`14107dfaeb916b654b1acf376cf61226088abdc3fb6939d64098779f2f979d62`.

This accepts CE-04-SHEDTAIL only. CE-04-LINK, CE-04-CALLBACK, CE-04-SLOTS,
CE-05, PIPELINE-002, and `faithful_complete_episode:false` remain outside
this checkpoint.

### CE-04-LINK implementation checkpoint (2026-10-01, unreviewed)

Spirit Shackle is now bounded as a private pinned `trapped`/`trapper` link.
The shared coverage classification records its exact `Moves.spiritshackle`
origin and the `Pokemon` unlink lifecycle. Its sole public effect is raw
`-activate …|trapped` evidence; it creates no public link, target, duration,
counter, volatile, or belief field. Only the addressed target request controls
switch legality. Focused fixtures cover both actors, Ghost immunity,
source/target departure, faint/drag/replacement, request restoration,
rollback, parser near misses, and TypeScript/Python publication.

The focused checker computes local coverage digest
`8b54db8829a06218431536d669c0391aacd0bc0794ca331c309249a60fb8609f` as
**unreviewed**. The manifest's stored/review digest fields remain unchanged.
This checkpoint does not accept CE-04-LINK, PIPELINE-002, or change
`faithful_complete_episode:false`.

### CE-04-LINK scoped review finding (2026-10-01, not accepted)

The v2 fixture does not exercise source faint after Spirit Shackle links the
target. Pinned source-faint cleanup reaches `clearVolatile` and linked-status
removal, which differs from the covered source-switch path. Add a pinned
simulator sequence that faints the source while the target is trapped and
asserts request-gated switch restoration for the target owner. The computed
`21b05aa836b14a4019a91db9d619cc954af82063199205aa26cf63e4e01f6d34` remains
unreviewed; no manifest digest field changed.

### CE-04-LINK repair implementation checkpoint (2026-10-01, unreviewed)

The shared TypeScript/Python validators now permit trapped only as
`|-activate|<active>|trapped`. Source tags, arbitrary labels, extra fields,
side-only targets, and whitespace-altered target/effect fields reject before
projection and Python publication. The fabricated `[of]` disclosure is now a
rehashed rejection control for both perspectives and input/successor prefixes;
it produces no DATA output.

The pinned simulator fixture explicitly requests `observable-battle-state/v2`
and executes both actor sides. It publishes both successor perspectives through
Python, keeps each bundle bound to its owning request, excludes raw requests
and `trapper`, proves source departure/release and request-gated switch
restoration, compares independently restored twins for matching trap/release
transition IDs, bundles, and boundaries, and retains stale-action rollback.

The focused checker computes local coverage digest
`21b05aa836b14a4019a91db9d619cc954af82063199205aa26cf63e4e01f6d34` as
**unreviewed**. The manifest's stored/review digest fields remain unchanged.
This checkpoint does not accept CE-04-LINK, PIPELINE-002, or change
`faithful_complete_episode:false`.

### CE-04-LINK source-faint evidence checkpoint (2026-10-01, unreviewed)

The Spirit Shackle fixture now exercises both acting sides through the pinned
simulator's real faint lifecycle. A surviving source first traps a live target
with a bench; on the following turn, the slower target's source-shaped Eruption
faints the source. The fixture observes `clearVolatile` unlinking the target's
private trap, then performs the source owner's one-sided forced switch. The
next target-owner request alone has `trapped:false`, `can_switch:true`, and a
legal bench switch. It rejects the stale target switch while the link is live,
checks that no request or `trapper` value enters either perspective or
publication, and compares independently restored twins for matching link,
source-faint, and replacement transition IDs, bundles, and boundaries. Every
emitted bundle is accepted independently by the Python publication validator.

The focused TypeScript source/request/transition suite (38 cases), focused
Python trap-publication test, and coverage synthetic self-test pass. The full
coverage checker reports local digest
`4398a8f03c730f43f0867477e71334555cda19641cd84ec9d74d8535ff0e3faa` as
**unreviewed**; manifest stored/review digest fields remain unchanged. This
checkpoint does not accept CE-04-LINK, PIPELINE-002, or change
`faithful_complete_episode:false`.

### CE-04-LINK source-faint scoped review verdict (2026-10-01): accepted

The pinned source-faint path is now covered for both acting sides. An ordinary
target move faints the active Spirit Shackle source, `clearVolatile` unlinks
the target, and target switching returns only through its subsequent owned
request after the source forced-replacement boundary. The v2 restored twins
match transition IDs, publication bundles, and successor boundaries, while
raw protocol/request privacy remains intact. The reviewed local coverage digest
is `4398a8f03c730f43f0867477e71334555cda19641cd84ec9d74d8535ff0e3faa`.

This accepts CE-04-LINK only. CE-04-CALLBACK, CE-04-SLOTS, CE-05,
PIPELINE-002, and `faithful_complete_episode:false` remain outside this
checkpoint.

### CE-04-SLOTS Wish implementation checkpoint (2026-10-01, unreviewed)

Pinned `Moves.wish` stores its amount, source, source slot and start turn only
inside the simulator slot-condition state. The public capture retains the
activation `move` record and, only when the current living slot occupant is
actually healed, the exact `-heal` record with `[from] move: Wish` and
`[wisher]`. Existing HP projection remains the sole typed public state; tags
stay raw evidence. No pending timer, recipient forecast, source link or private
snapshot enters v2 observations, beliefs or Python records.

The focused pinned-engine fixture covers both actors, generator membership,
pending resolution after switch, drag, source/recipient faint, replacement,
terminal-before-resolution, deterministic candidate restoration, rejected
replacement rollback, privacy and Python publication. Python accepts the exact
Wish public-heal grammar in both v1/v2 input and successor prefixes and rejects
tag-order, duplicate-wisher and invalid-HP rehashes without mutation.

`tests/wish.test.ts` is now included in local coverage hashing. The resulting
local digest is `9b7276277d51db992b2014b178e9dfad484aba92adbab750b54ac92200be763f`,
recorded as **unreviewed**; `reviewed_sha256` remains the prior reviewed digest.
This checkpoint does not attest coverage, accept CE-04-SLOTS or PIPELINE-002,
or change `faithful_complete_episode:false`.

### CE-04-SLOTS Wish `[wisher]` cross-field repair checkpoint (2026-10-01, unreviewed)

Pinned base data has one reachable `[wisher]` emitter:
`data/moves.ts:Moves.wish.condition.onEnd:21760`, which emits `[from] move:
Wish` followed by `[wisher] <source name>`. Historical `data/mods/gen4` and
custom `data/mods/gen9ssb` copies are outside the Gen 9 Random Battle base path.
The shared TypeScript/Python contract now makes the base source pair indivisible:
`[wisher]` requires exactly `[from] move: Wish` first, with no other tags.

Focused table-driven controls cover the one valid base source form and missing,
ability-mismatched, reordered, duplicate and extra-tag rehashes across v1/v2,
both perspectives and input/successor prefixes. Invalid candidates reject before
projection/publication, emit no DATA-001 output, and leave committed candidate
state and lineage unchanged; non-Wish heals without `[wisher]` retain their
existing source-backed grammar. No public pending Wish state, timer, source
link, private request or simulator snapshot is introduced. The replacement
digest `9b7276277d51db992b2014b178e9dfad484aba92adbab750b54ac92200be763f`
remains unreviewed; CE-04-SLOTS, PIPELINE-002 and
`faithful_complete_episode:false` remain unaccepted.

### CE-04-SLOTS Wish `[wisher]` scoped review verdict (2026-10-01): accepted

The sole pinned base-data `[wisher]` emitter is Wish `onEnd`, with the exact
ordered source pair `[from] move: Wish`, `[wisher] <source name>`; Gen 4 and
`gen9ssb` copies are outside the operative format. Shared TypeScript/Python
validation rejects every missing, mismatched, reordered, duplicate, extra, or
malformed pairing before projection/publication, while preserving non-Wish heals
without `[wisher]`. Rehashed v1/v2, p1/p2, input/successor controls prove
rollback, lineage preservation, and no DATA-001 output. The reviewed local
digest is `9b7276277d51db992b2014b178e9dfad484aba92adbab750b54ac92200be763f`.

This accepts CE-04-SLOTS Wish evidence only. CE-04-CALLBACK, other delayed
effects, CE-05, PIPELINE-002, and `faithful_complete_episode:false` remain
outside this verdict.

### CE-04-CALLBACK-A implementation checkpoint (2026-10-01, unreviewed)

The CE-04-CALLBACK-A audit table binds the operative public ability forms to
base `-ability` reveal/boost/copy/weather-fail output and `-endability`
suppression/replacement lifecycle. Generated Gardevoir/Trace is the direct
singles witness; Power of Alchemy/Receiver require an allied active and remain
excluded. Doodle, Entrainment, Role Play, Simple Beam, Worry Seed and Gastro
Acid retain exact base grammar controls without a generated-move claim.

Shared TypeScript/Python validation now rejects malformed, reordered, missing,
extra, unsupported-provenance, and non-active source combinations before
projection or publication. The extractor clears stale current ability on
silent Transform/form changes, restores only independently public base ability
through `clearVolatile` lifecycle boundaries, and keeps all raw provenance.
`-activate` and other heterogeneous ability-tagged outcomes remain raw-only;
no generic callback state is inferred. Rehashed v1/v2, p1/p2 input/successor
controls preserve candidate state and lineage and produce no DATA-001 output
on rejection. The resulting digest is recorded as unreviewed after validation;
no coverage attestation, CE-04-CALLBACK closeout, PIPELINE-002 change, or
`faithful_complete_episode:false` change is made.

The computed local coverage digest is
`403e5818240fb7e2afdc34a13e9fe5d68369eeaba1671aefb3052c9fa1088cfa`;
its `reviewed_sha256` remains the prior reviewed value.

### CE-04-CALLBACK-A scoped review finding (2026-10-01, not accepted)

The implemented ability grammar exceeds the source-proven `gen9randombattle`
singles surface. Both validators accept Receiver/Power of Alchemy copy forms
despite their ally-active requirement, arbitrary move provenance such as
`|-ability|p1a: Pikachu|Insomnia|[from] move: Splash`, and its matching
unrestricted `-endability` provenance. They also accept failed-weather evidence
without a generated weather-blocker route, and apply callback provenance to the
bare compatibility `ability` alias although pinned callback emitters use
`-ability`. These records can pass projection and publication.

CE-04-CALLBACK-A remains unaccepted until its projected/publication grammar is
narrowed to source-proven reachable forms or broader forms are explicitly
raw-only/excluded and cannot project. The digest remains unreviewed; this does
not alter CE-04 scope, PIPELINE-002, or `faithful_complete_episode:false`.

### CE-04-CALLBACK-A source-form repair checkpoint (2026-10-01, unreviewed)

The shared boundary now accepts only the operative singles `-ability` reveal,
literal `boost`, and ordered Trace copy templates, plus the unsuffixed
raw-only bare `ability` compatibility record. The generator proofs are
Rayquaza/Air Lock, Arcanine/Intimidate, and Gardevoir/Trace. Receiver, Power
of Alchemy, every move-sourced replacement or `-endability`, failed weather,
and bare callback suffixes are recognized as unsupported or malformed before
TypeScript projection and Python publication. Rehashed v1/v2, p1/p2,
input/successor controls retain lineage and produce no DATA-001 output on each
rejection. The new local digest is recorded as unreviewed after focused
validation; this is not a CE-04-CALLBACK acceptance, PIPELINE-002 closeout, or
change to `faithful_complete_episode:false`.

### CE-04-CALLBACK-A repaired grammar review finding (2026-10-01, not accepted)

The repair remains unaccepted. Both TypeScript and Python accept
`|-ability|p1a: Gardevoir|Immunity|[from] ability: Trace|[of] p1a: Eevee`,
although the pinned Trace emitter uses `adjacentFoes()` and a Gen 9 singles
Trace `[of]` source must be the opposing active slot. Both also accept the
fabricated payload `Definitely Not An Ability` in plain `-ability` and bare
`ability` records. The first can fabricate a private same-side Trace link;
the second broadens the accepted source form beyond the generated ability
payload domain. Each must reject before projection/publication. Do not attest
the local digest until the shared validators enforce the opposing Trace role
and finite operative ability payloads.

### CE-04-CALLBACK-A finite-domain repair checkpoint (2026-10-01, unreviewed)

The shared JSON and matching TypeScript/Python expected-rule tables now carry
four exact `validation_rules.ability.payload_domains`: 17 literal generated
dash reveals, 32 generated ability-boost values, 186 generated Trace-copy
values allowed by Trace's `notrace` guard, and the same 17 values for bare
raw-only compatibility reveals. Every dash/bare validator checks its matching
domain before projection/publication. Trace additionally requires an active
actor and opposing active `[of]` source because `Abilities.trace.onUpdate`
selects `adjacentFoes()`.

Focused v1/v2 p1/p2 input/successor rehash controls cover valid publication
and same-side Trace, invented/unknown payloads, and cross-template payloads as
immutable Python-publication rejections. The computed digest is unreviewed;
`0ab90b62c0b1f41cb750f1ab2759fc3df9389fb5bfdb4edac59c5c5c97ac48ad`; this
is not a CE-04-CALLBACK acceptance, PIPELINE-002 closeout, or attestation.

### CE-04-CALLBACK-A finite-domain review finding (2026-10-01, not accepted)

The `dash_boost` list accepts unsupported `As One (Glastrier)` and `As One
(Spectrier)` payloads. The pinned As One callbacks pass `chillingneigh` and
`grimneigh` explicitly to `Battle#boost`, and that emitter publishes
`effect.name`; generated Calyrex therefore emits `Chilling Neigh` or `Grim
Neigh`, never either As One variant. Both TypeScript and Python accept the
fabricated `|-ability|p1a: Calyrex|As One (Glastrier)|boost` record. Remove
the two values, add cross-runtime rehash controls, and leave the digest
unattested until the exact emitted boost domain is restored.

### CE-04-CALLBACK-A emitted-boost repair checkpoint (2026-10-01, unreviewed)

`dash_boost` now contains 30 `Battle#boost` `effect.name` payloads. Generated
As One callbacks publish Chilling Neigh or Grim Neigh; both As One variant
names reject. Rehashed v1/v2 p1/p2 input/successor controls prove rollback and
no Python publication for each rejected variant. The local digest remains
unreviewed (`50585303834f13303dc7c45bd51d40d9d135fe02ff03b74957f8b952fa0dbdda`)
and no attestation is made.

### CE-04-CALLBACK-A emitted-boost review finding (2026-10-01, not accepted)

The 30 emitted `Battle#boost` values are correct, including Chilling/Grim
Neigh and excluding the two As One variants. Attestation remains blocked:
the existing `tests/fixtures/observable_state_v1.json` golden prefix contains
`|-ability|p1a: Pikachu|Illusion`, which the repaired finite dash-reveal rule
rejects, failing its decision-time projection test. The coverage checker
otherwise reports only its expected pre-attestation semantic-review binding
condition. Reconcile the fixture before any CE-04-CALLBACK-A attestation.

### CE-04-CALLBACK-A golden-fixture repair checkpoint (2026-10-02, unreviewed)

Pinned `Abilities.illusion.onEnd` emits `replace` and then `-end` for the
revealed Pokémon. The observable-state golden prefix now uses
`|replace|p1a: Zoroark|Zoroark, L80|75/100` followed immediately by
`|-end|p1a: Zoroark|Illusion`; it removes the unrelated synthetic Eevee
replacement while retaining the ten-record ordered cutoff and its public
projection assertions. A focused regression proves this repaired fixture
projects and that the old fabricated `|-ability|p1a: Pikachu|Illusion` record
rejects before projection.

The static ability-record audit retained source-backed Ting-Lu/Vessel of Ruin
and Pressure evidence, contract acceptance/rejection fixtures, and persisted
negative review artifacts; the golden pair was the only invalid golden
projection fixture record. The manifest now hashes this fixture and its focused test. Its computed
local digest is `ed88914a455d16e17f25e81e3e107706fbaf8bee0b6d75169b4aaf1b9451778b`,
which is **unreviewed**. No attestation or CE-04-CALLBACK-A acceptance is made.

### CE-04-CALLBACK-A scoped review verdict (2026-10-02): accepted

Focused review accepts only the bounded public ability lifecycle surface: the
finite dash reveal/boost/Trace-copy/bare domains, exact public source grammar,
privacy and restoration behavior, and the source-shaped Illusion golden
fixture. Both runtimes retain v1/v2 and input/successor rejection/publication
parity with no output or committed-lineage advance on malformed evidence. The
attested local digest is
`ed88914a455d16e17f25e81e3e107706fbaf8bee0b6d75169b4aaf1b9451778b`.

This accepts CE-04-CALLBACK-A only. The baseline `env_manager` settling
failure, item/status callback work, other CE-04 slices, CE-05, PIPELINE-002,
and `faithful_complete_episode:false` remain outside this verdict.

### Random-controller terminal settling repair checkpoint (2026-10-02, unreviewed)

The fixed `[5,6,7,8]` random battle originally stopped when a generated
Protosynthesis callback emitted `|-start|...|protosynthesisatk`; the extractor
treated that source-derived best-stat suffix as unknown and the consumer error
became a settling failure. Pinned Protosynthesis and Quark Drive callbacks
append only `Pokemon.getBestStat(false, true)`, whose exact finite values are
`atk`, `def`, `spa`, `spd`, and `spe`. The corresponding ten start tags are now
raw-only evidence; all other suffixes still reject before projection.

The same fixed terminal then reached `|-hitcount|p1: Houndstone|2` after a
final multi-hit KO. Pinned `BattleActions` emits the count after
`faintMessages`, so the target may be a canonical side-only Pokémon reference.
The raw-only `-hitcount` validator accepts that source form without typed
state mutation and still rejects malformed references. Two independent seeded
random-controller runs now complete with identical terminal logs. The computed
local digest is `ed0e358983cd7860ba65f777db4087edac876c5fde603b51a6d6d01ca6689dfd`,
which is **unreviewed**; `reviewed_sha256` remains the prior CE-04-CALLBACK-A
attestation and this checkpoint makes no new attestation.

### Random-controller terminal settling review reproduction (2026-10-02, repaired)

The finite Protosynthesis/Quark Drive raw-only start forms match their pinned
source. Review reproduced that the former generic `-hitcount` identifier helper
accepted doubles-only slots in supported singles, and its generic nonnegative
integer rule accepted counts not emitted by `BattleActions`. The minimal former
accepted reproductions were `|-hitcount|p1b: Mew|2`,
`|-hitcount|p1: Mew|0`, `|-hitcount|p1: Mew|1`, and
`|-hitcount|p1: Mew|11`. Pinned `BattleActions` emits only an active singles
target (`p1a`/`p2a`) or the post-faint side-only target, and only after two
through ten hits (the pinned maximum is Population Bomb). Restrict the slot
grammar and finite count semantics with rehashed rejection coverage; the
following unreviewed checkpoint records that repair. No `reviewed_sha256`
update is authorized here.

### Random-controller terminal settling `-hitcount` repair checkpoint (2026-10-02, unreviewed)

The shared TypeScript/Python rule now accepts only exact four-field
`|-hitcount|<target>|<count>` raw evidence. `BattleActions.hitStepMoveHitLoop`
emits after `faintMessages`, so `<target>` is either an active `p1a:`/`p2a:`
identifier or the `p1:`/`p2:` side-only identifier after a final KO;
`Pokemon.toString()` supplies those forms. The loop increments `hit` before a
one-hit KO break and then emits `hit - 1`; generated Maushold has Population
Bomb (`multihit: 10`). The finite accepted ASCII count set is exactly `1`
through `10`.

The rule rejects every other slot, side, whitespace spelling, count lexeme,
out-of-domain count, tag, and extra field before projection or publication.
It remains raw evidence only: no hit count, ability, boost, action, feature,
or hidden-state field is projected. TypeScript/Python rehashed matrices cover
v1/v2, p1/p2, input/successor prefixes, no DATA-001 output, and unchanged
candidate state/lineage on rejection. The deterministic terminal controller
fixture still retains its real `|-hitcount|p1: Houndstone|2` record.

The requested checker computed local coverage digest
`0d3adff3b68903e8a37ad0a951260cdd20dc9b65f0827a8aa7f9015a66a72380`.
It is **unreviewed**. `sha256` and `reviewed_sha256` remain unchanged; this is
not an attestation of the settling repair, PIPELINE-002, or
`faithful_complete_episode:false`.

### Random-controller terminal settling `-hitcount` count-one correction (2026-10-02, unreviewed)

The former `2..10` domain omitted a pinned source-reachable value. In
`BattleActions.hitStepMoveHitLoop`, a one-hit KO increments `hit` before the
break at `battle-actions.ts:969-971`; after `faintMessages`, line 979 emits
`hit - 1`. The pinned Maushold Population Bomb witness against a 1-HP target
emits `|faint|p2a: Target` then `|-hitcount|p2: Target|1`. Both shared
validators now admit exact decimal `1..10` for the reviewed active and
post-faint singles forms. The witness replaces the old `1` rejection control;
`0`, `11`, leading-zero, malformed identifier, tag, and extra-field controls
remain pre-projection/pre-publication failures. The coverage checker now
computes `e7173364c14678c448adfeab0ce81eed56109776e8cdae501d6b6e2e7be71d1a`. It is unreviewed; no manifest digest field changes in
this repair.

### Random-controller terminal settling `-hitcount` scoped review verdict (2026-10-02): accepted

Focused review accepts the corrected raw-only `-hitcount` boundary. Pinned hit-loop ordering proves the one-hit Population Bomb post-faint form `|-hitcount|p2: Target|1`; generated Maushold's Population Bomb (`multihit: 10`) establishes the source-backed upper bound. The shared validators accept only exact four-field singles active (`p1a:`/`p2a:`) or post-faint side-only (`p1:`/`p2:`) identifiers with ASCII counts `1..10`. Invalid candidates reject before projection or DATA-001 publication and preserve committed lineage. Rehashed TypeScript/Python parity covers v1/v2, both perspectives, input/successor prefixes, rollback, and no-output rejection. The fixed-seed terminal controller run excludes only timestamp framing. The attested local coverage digest is `e7173364c14678c448adfeab0ce81eed56109776e8cdae501d6b6e2e7be71d1a`.

### CE-04-SLOTS Healing Wish review finding (2026-10-02, superseded by unreviewed implementation checkpoint)

**Historical blocker.** The prior finding identified absent Healing Wish lifecycle,
fixture, exact provenance and v2 publication evidence, including acceptance of
`|-heal|p1a: Target|100/100|[from] move: Healing Wisp`. The bounded checkpoint
below supplies the implementation evidence without changing any manifest
attestation.

### CE-04-SLOTS Healing Wish implementation checkpoint (2026-10-02, unreviewed)

Pinned `Moves.healingwish` creates a private `side.slotConditions` entry, then
on a qualifying incoming replacement heals to full HP, silently clears status,
emits exact public `|-heal|<active>|100/100|[from] move: Healing Wish`, and
removes that condition. The shared TypeScript/Python validator accepts only an
active target, literal public status-free `100/100`, and exactly that one
`[from]` tag. The owner-private exact-HP split is omitted before typed routing;
only the spectator public record clears typed status. It rejects `Healing Wisp` and other
invented Healing-prefix moves, side-only targets, partial/status-bearing health,
and reordered, duplicate, or extra tags before projection/DATA-001. Ordinary
heals and Wish `[wisher]` grammar remain unchanged.

The existing typed public status is cleared only when that exact Healing Wish
public evidence is processed; no slot condition, source identity, timer, raw
request, snapshot, forecast, or generic delayed-effect state is projected.
Pinned-engine p1/p2 fixtures use a real Will-O-Wisp status before Healing Wish
and cover forced replacement, healthy nonapplication, `canSwitch` cancellation,
terminal-before-replacement, privacy, restored twins and deterministic
continuation. The selected replacement's actor record validates in Python; its
immediate joint continuation supplies two actual v2 bundles whose input prefixes
include the resolved Healing Wish record, and both validate in Python without
repair. Rehashed v1/v2, p1/p2, input/successor malformed forms preserve the
candidate and lineage and produce no Python stdout.

`tests/healing_wish.test.ts` is listed in local coverage sources. The checker
computed `eff9daa2ac3b737c7983d0ff951244d48b9b532c54b3595904cfb2be63c023ef`,
which is **unreviewed**. Manifest `sha256`, `reviewed_sha256`, and all
attestation fields remain unchanged. This checkpoint does not attest CE-04-SLOTS,
PIPELINE-002, or `faithful_complete_episode:false`; it does not broaden Future
Sight, other delayed effects, item callbacks, Revival Blessing, or episode
readiness.

### CE-04-SLOTS Healing Wish scoped review verdict (2026-10-02): accepted

Pinned Healing Wish provides one public result only: exact active-target `|-heal|<target>|100/100|[from] move: Healing Wish`, after its private slot condition resolves on a qualifying replacement. The owner-private exact HP branch is omitted; only the public spectator record clears typed HP/status. Both-actor v2 fixtures cover public privacy, healthy retention, cancellation, terminal behavior, restored twins, continuation and Python successor publication. Shared TypeScript/Python validation rejects malformed provenance, target, HP, and tag forms before projection or DATA-001 output while preserving committed lineage. This scoped review attests `eff9daa2ac3b737c7983d0ff951244d48b9b532c54b3595904cfb2be63c023ef` for CE-04-SLOTS Healing Wish only. It does not accept Future Sight, other delayed effects, item callbacks, Revival Blessing, CE-05, PIPELINE-002, or `faithful_complete_episode:false`.

### CE-04-SLOTS Future Sight delayed public-consequence checkpoint (2026-10-02, unreviewed)

Pinned `Moves.futuresight.onTry` creates a private `futuremove` target-slot condition and emits exactly `|-start|<active source>|move: Future Sight`. Pinned `Conditions.futuremove.onEnd` removes that condition at its private ending turn, emits exactly `|-end|<active target>|move: Future Sight`, then runs ordinary damage. The damage record has no Future Sight tag, so only the public spectator `-damage` record changes typed HP/faint/status; the exact owner split branch, timer, source, target slot, move data, requests and simulator state remain private.

The shared TypeScript/Python contract binds the public start/end forms to their active targets and exact field count, rejecting misspellings, side-only targets, leading/extra/reseparated source-family spellings, and added tags/fields. Generic `-damage` grammar remains unchanged. `futuremove.onEnd` does not cancel for a fainted source, so the pinned fixture proves that source faint plus forced replacement still resolves against the living target slot. Pinned v2 fixtures cover both actors and perspectives, source switch/faint, target drag, target faint/replacement, terminal-before-residual, restored twins, deterministic continuation, split-HP privacy, rehashed v1/v2 p1/p2 input/successor rejection rollback, and actual Python transition-bundle publication. Malformed candidates fail before projection/DATA-001 output and leave committed lineage unchanged.

`tests/future_sight.test.ts`, the shared contracts, extractor route and Python publication test are coverage-hashed. The checker computed `563cd723d2b31429eb4ca5a2570211b3b81035a1979c42536d7d38b620243e1d` as **unreviewed**; manifest attestation fields are unchanged. This checkpoint excludes Doom Desire, Lunar Dance, generic delayed-effect modeling, item callbacks, CE-05, complete-episode claims, and any change to `faithful_complete_episode:false`.

### CE-04-SLOTS Future Sight scoped review verdict (2026-10-02): accepted

Focused review accepts the bounded Future Sight public consequence only. The
pinned generated route emits exact raw-only active-source
`|-start|<active source>|move: Future Sight` and, on a valid living slot
occupant, exact raw-only active-target
`|-end|<active target>|move: Future Sight`; ordinary public spectator damage
then supplies the only typed HP/faint effect. The private slot condition,
timer, source, target, move data, exact owner HP, request and snapshot data
never enter observations or DATA-001. Pinned p1/p2 v2 fixtures cover source
switch/faint, target drag/faint/replacement, terminal/no-result, restored
twins, deterministic continuation, rollback and actual Python publication.
Shared TypeScript/Python source-form validation rejects malformed labels,
roles, tags, fields and whitespace/reseparator forms before projection or
publication. The attested local coverage digest is
`563cd723d2b31429eb4ca5a2570211b3b81035a1979c42536d7d38b620243e1d`.

This accepts CE-04-SLOTS Future Sight only. Doom Desire, Lunar Dance, generic
delayed effects, item callbacks, CE-05, PIPELINE-002, and
`faithful_complete_episode:false` remain outside this verdict.

### CE-05-REPEAT Encore/repeat-use implementation checkpoint (2026-10-02, unreviewed)

Pinned direct generated Blood Moon and Gigaton Hammer are the complete
`cantusetwice` domain. `Battle#runEvent('DisableMove')` supplies the normal
disabled owned request; faster Encore's `onOverrideAction` can replace a
queued alternate with the stored prior move; `BattleActions.runMove` then
emits exactly one raw hint after a successful forced repeat. Shared
TypeScript/Python validation accepts only the two exact three-field hint
strings and rejects source-family misspellings, invented labels, whitespace,
tags, and extra fields before projection or DATA-001 publication.

The correction is limited to source-request Struggle:
`Pokemon.getMoveRequestData` returns `Struggle` without PP when Encore plus
repeat-use disablement leaves no ordinary move, and `action_codec` now treats
that owned source move as legal. No hint-derived action mask or generic
move-lock model was added. The simulator-backed v2 fixture covers both actor
sides and both repeat IDs, normal restriction, Encore override, exact raw
evidence, Struggle, restored twins, deterministic continuation, stale-action
rollback, request privacy, and actual Python transition-bundle publication.
`tests/repeat_use.test.ts` and all changed contract/action/publication paths
are coverage-hashed.

The local coverage digest `99af6315d68ff86879e2baf6cdbbd2ee0a01caa8a24779a0ca7f9e588cfe0bbc`
is **unreviewed** after focused validation. This checkpoint does not attest CE-05-REPEAT, PIPELINE-002, or
`faithful_complete_episode:false`; it excludes generic locks, other Encore
interactions, item callbacks, Revival progression, training, and complete
episode claims.

### CE-05-REPEAT scoped review verdict (2026-10-02): accepted

Focused review accepts only the pinned generated Blood Moon/Gigaton Hammer
repeat-use chain. `cantusetwice` disablement, Encore's override, its exact
raw-only post-repeat hint, and a later source-owned Struggle request are each
covered by the shared TS/Python boundary and real v2 p1/p2 transitions. Legal
actions derive exclusively from addressed simulator requests; raw hints do not
create an action mask. Both perspectives preserve private requests and hidden
team data, while malformed hint-family records stop before projection,
lineage advancement, and DATA-001 publication. Restored twins and actual
Python bundles remain deterministic. This review attests local digest
`99af6315d68ff86879e2baf6cdbbd2ee0a01caa8a24779a0ca7f9e588cfe0bbc` for
CE-05-REPEAT only. Generic move locks, other Encore paths, item callbacks,
Revival, CE-05 request-pair closure, training, PIPELINE-002, and
`faithful_complete_episode:false` remain unaccepted.

### CE-05-REVIVAL sequential progression checkpoint (2026-10-02, unreviewed)

Pinned Gen 9 Random Battle directly generates Pawmot/Rabsca Revival Blessing
and Ditto/Imposter. `Moves.revivalblessing.onTryHit` requires an owner fainted
party member, then `slotCondition` plus `selfSwitch` creates one owner-only
selection. `Side.chooseSwitch` accepts only a fainted target. The revive action
clears faint/status state, restores half HP, emits the split side-only
`-heal ... [from] move: Revival Blessing`, and removes the condition.

The source sequencing witness proves `turnLoop` pauses after fast Pawmot,
`commitChoices` places its consumed revive action ahead of the saved queue,
and queued Rabsca then creates the opposite owner-only selection. Each
nonacting side has only its own waiting request. Both choices produce
actor-only v2 record bundles, validate through Python, preserve private target
selection/request contents, and reach an ordinary joint transition that matches
a restored twin. A separate copied-Ditto witness takes the same bounded
selector; a queued opposing terminal action after consumption yields terminal
observations with no fabricated request. Rejected candidates leave the boundary
unchanged.

The source-proven exclusions remain active/fainted revivers, active targets,
instaswitch, multi-active/doubles, simultaneous selection, a combined
multi-revival API, generic waiting, CE-05 boundary closure, and complete
episodes. `tests/revival.test.ts` was already coverage-hashed. Focused build,
10 TypeScript revival tests, 34 Python pipeline-record tests, coverage self-test,
and whitespace validation pass. The local digest
`1d5757be1d09c5ced11e260017f9e87cfc13045147a0de1adf3371db8d3bb1ce` is
**unreviewed**; manifest digest fields remain unchanged.

### CE-05-REVIVAL scoped v2 progression review verdict (2026-10-02): accepted

Pinned Gen 9 Random Battle singles supports the direct Pawmot/Rabsca and
bounded Imposter-copy Revival Blessing paths. One owner alone receives the
fainted-bench selector while the other perspective has only its own wait
request. The source queue pauses at the first request, consumes it, then may
create the queued opposite-side selection; it does not create simultaneous or
generic waiting behavior. Revival emits the existing split source-qualified
bench `-heal` record, with owner-only private request data.

Mirrored v2 fixtures verify both actor sides, copied-user selection, sequential
requests, rollback, restoration from consumed requests, deterministic continuation
into ordinary joint play, terminal-after-selection without a fabricated request,
and Python publication of the actual actor-only bundles. Active-target, inactive
or fainted reviver, doubles/multi-active, combined multi-revival, and generic
waiting variants remain excluded.

The reviewed local coverage digest is `1d5757be1d09c5ced11e260017f9e87cfc13045147a0de1adf3371db8d3bb1ce`. This accepts CE-05-REVIVAL
only; CE-05-BOUNDARY, PIPELINE-002, and `faithful_complete_episode:false`
remain unaccepted.

### CE-05-BOUNDARY request-pair closure checkpoint (2026-10-02, unreviewed)

The closure audit now records the pinned stable Gen 9 Random Battle singles
request-pair table. `makeRequest/getRequests` supports owned move-plus-move
requests and source-owned voluntary switch-plus-switch choices; a direct v2
witness restores real serialized engine states before and after consumption,
validates both voluntary switch bundles through Python, and compares pipeline
twins' cursor, branch, transition, and successor identities. Existing
forced-switch fixtures cover source `switch+wait`, and existing Revival
fixtures cover bounded owner-only `revival+wait`, consecutive selections, and
resumption into ordinary joint play. Both retain only their own request and no
public protocol prefix or DATA-001 row includes an opposite owner's request.

`Battle.win` clears active requests and ends `turnLoop`, so terminal
requestlessness is terminal-only: matching terminal views have null requests
and no fabricated future action. The engine's request construction makes
nonterminal `move+wait`, `move+requestless`, `wait+wait`,
`requestless+requestless`, and nonwaiting empty-move-menu pairs source-proven
impossible stable boundaries. They remain explicit guards, not artificial
fixtures or generic waiting/requestless execution.

No production change was required. `pipeline_integration.test.ts`,
`forced_switch.test.ts`, `revival.test.ts`, and `pipeline_episode.test.ts` are
already coverage-hashed. The resulting local digest
`3d65ae223bb5d9d3aadd7aaf6a3b35239b69c9c03b513e3ee7deb473de3161a8` is
**unreviewed**; manifest digest fields remain unchanged. This does not
accept CE-06, team preview, doubles, generic requestless execution,
PIPELINE-002, or `faithful_complete_episode:false`.

### CE-05-BOUNDARY scoped request-pair review verdict (2026-10-02): accepted

Review accepts the pinned singles stable-pair closure: move-plus-move,
voluntary switch-plus-switch, forced switch-plus-wait, and bounded
revival-plus-wait have direct owner-only v2 witnesses with restoration,
deterministic identity/cursor evidence, rollback, and Python publication.
The switch-pair witness restores the real engine request before consumption and
its successor afterward. Opposite-side requests never enter public protocol or
DATA-001 output.

Terminal requestlessness is terminal-only with matching null-request
perspectives and no fabricated action. Nonterminal move-plus-wait,
move-plus-requestless, wait-plus-wait, requestless-plus-requestless, and
nonwaiting empty-menu states are source-proven impossible stable boundaries.
Team preview, doubles, generic requestless execution, CE-06 terminal envelopes,
PIPELINE-002, and complete-episode acceptance remain excluded.

This attests local coverage digest
`3d65ae223bb5d9d3aadd7aaf6a3b35239b69c9c03b513e3ee7deb473de3161a8` for
CE-05-BOUNDARY only; `faithful_complete_episode:false` remains required.

### CE-04B Roost boundary-typing checkpoint (2026-10-02, unreviewed)

Pinned `Moves.roost` has `duration: 1`: a successful non-Tera use emits only
`|-singleturn|<active>|move: Roost` and applies an internal `onType` filter that
removes Flying for the current turn. It stores `typeWas` privately. The residual
queue decrements/removes the condition before `turnLoop` can publish another
request, so no stable v1/v2 boundary can truthfully expose the temporary type.
The ordinary public `-heal` remains the existing HP consequence; the
`-singleturn` is exact raw evidence only.

Direct source fixtures cover both actor sides: a dual-Flying Articuno is hit by
a slower Ground move during Roost, then both next-request views correctly return
to `Ice/Flying`; a generated Empoleon Roost + Tera Flying row emits the pinned
raw hint and no `-singleturn`, retaining public `Flying`. The repaired fixture
also uses generated Articuno Roost before a slower U-turn pivot, then generated
Ditto/Imposter replacement. That reaches `transformInto` while private
`roost.typeWas` is live, emits the exact public `-transform ... [from] ability:
Imposter`, and leaves both public active types `Ice/Flying` after residual.
Mirrored v2 candidate restoration, deterministic continuation, stale/wrong
selection rollback, later source departure plus Rock-hit Ditto faint,
owner-only replacement, drag cleanup, prefix extension and Python bundle
publication pass. The source queue completes residual before any post-Imposter
move request, but earlier residual handlers can still faint copied Ditto before
Roost order-25 expiry; the dedicated residual witness below covers that route. An unrevealed target-side Zoroark/Illusion
bench remains absent from the Ditto observer. No production correction or new grammar was needed. The
manifest corrects Roost from a stale typed volatile classification to raw-only
and lists `tests/roost.test.ts`; digest fields remain unchanged.

Soak/added-type co-occurrence lacks a generated indirect route proof here;
unrevealed Illusion, Reflect Type, generic temporary types, offense, doubles
and complete episodes remain out of scope. The resulting local coverage digest
is `13023945c453d8dd5a312487edb5482fe2d7ac74f58bae2f62723f14bd6c0ad2`,
**unreviewed**; manifest attestation fields remain unchanged.

### CE-04B Transform/Roost repair checkpoint (2026-10-02, unreviewed)

The prior review gap is closed by a real source-shaped singles sequence, not
by inspecting or projecting `typeWas`: Articuno uses Roost, slower U-turn
creates a forced switch before residual, and Ditto's Imposter transform runs
against the active Roost target. The consumed-request snapshot restores the
same forced boundary; both mirror pairs produce deterministic identities in
their own prefix lineages and the same output state fingerprint. Raw requests,
private condition fields and Illusion identity stay absent from observations and
publication. CE-04B awaits scoped digest review only.

### CE-04B active-Transform faint repair (2026-10-05, unreviewed)

Pinned ordering confirms no successor move can faint the newly
Imposter-transformed Ditto before residual completes: U-turn replacement runs
`Imposter.onSwitchIn → transformInto`, then residual resolves before the next
request. The mirrored p1/p2 v2 fixture records the first move-request faint path:
source departure, a Rock hit against the copied `Ice/Flying` Ditto, its public
faint/native-Normal bench cleanup, and owner-only replacement. It restores
twins before and after the faint, matches transition identities and public state
fingerprints, rejects a stale replacement request without mutation, continues
deterministically, and validates all actual available Python record bundles.
No observation or publication exports `typeWas`, raw request data, or the
unrevealed Zoroark identity. No production code, generic temporary type or
Transform model, manifest attestation field, or grammar changed. The local
coverage digest is `13023945c453d8dd5a312487edb5482fe2d7ac74f58bae2f62723f14bd6c0ad2`, **unreviewed**.

### CE-04B active-Transform faint review finding (2026-10-05): superseded

The earlier broader source-impossibility claim was incorrect; the following residual-KO repair supersedes this finding. `Battle.fieldEvent('Residual')`
orders and runs all field/status/volatile handlers, calling `faintMessages()`
after each (`sim/battle.ts:477-533`). Sandstorm's field residual is order 1 and
damages (`data/conditions.ts:620-659`); poison/toxic are order 9
(`data/conditions.ts:127-160`); Roost's duration handler is order 25
(`data/moves.ts:16016-16030`). A pre-damaged Ditto can consequently transform
against the live Roost target and faint to an earlier residual before Roost
expires. Generated Toxic Spikes and Sand Stream roots mean the later
Rock-hit-only fixture does not exclude the path. CE-04B remains unreviewed and
unattested pending a mirrored real v2 earlier-residual faint witness (or a
complete generated-route exclusion) with the existing privacy, restoration,
rollback, and Python-publication obligations.

### CE-04B pre-Roost-expiry residual-KO repair (2026-10-05, unreviewed)

This supersedes the prior no-interleaving claim. Generated Tyranitar Sand
Stream runs at residual order 1 and `Battle.fieldEvent` calls `faintMessages()`
after it; Roost expires only at order 25. Mirrored p1/p2 v2 source fixtures
pre-damage Ditto, establish Sand Stream, use Articuno Roost plus slower U-turn,
and have Ditto/Imposter transform while `roost.typeWas` remains private. The
real upkeep then faints copied Ditto before Roost expiry. Both views retain the
active `Ice/Flying` target and public Ditto faint/native-Normal cleanup.
Restored twins, deterministic same-lineage transitions, stale-choice rollback,
owner-only replacement, continuation and actual Python v2 publication pass.
No output exports `typeWas`, raw request data or unrevealed Zoroark identity.

Poison/toxic residual handlers are order 9; their status/damage records differ
but their `faintMessages()`-before-order-25 type cleanup is identical, so no
second CE-04B type fixture is necessary. No production feature, generic
residual/type/Transform support, manifest field or attestation changed. Local
digest: `bf4c57ae0745d28c7d2d9dd9bf0999e753c53fe6c26e12e12eedf13c3e11a1f4`, **unreviewed**.

### CE-04B Roost and active-Transform scoped review verdict (2026-10-05): accepted

Focused review accepts the bounded Roost public defensive-type closure,
including the active-Roost Imposter/Transform and pre-expiry residual-faint
paths. Sand Stream order 1 and poison/toxic order 9 each invoke
`faintMessages()` before Roost order 25; the Sandstorm fixture supplies the
mirrored source-backed type/faint/replacement witness and poison/toxic share the
same bounded transform/type cleanup. Both actor directions, public privacy,
restored twins, deterministic continuation, rollback, and Python v2 publication
are covered. The attested local coverage digest is
`bf4c57ae0745d28c7d2d9dd9bf0999e753c53fe6c26e12e12eedf13c3e11a1f4`.

This acceptance is limited to CE-04B. It does not add generic residual,
Transform, temporary-type, Reflect Type, or offensive-calculation behavior, and
does not accept PIPELINE-002 or complete-episode capture.

### CE-04D1 entry-hazard layer checkpoint (2026-10-05, accepted scoped closure)

Pinned `Moves.spikes` and `toxicspikes` emit one public `-sidestart` per source-bounded layer (3 and 2); Stealth Rock and Sticky Web have no restart callback and stay at one. Their switch-in consequences remain existing public HP/status/stage records. Pinned Rapid Spin, Mortal Spin, Defog and Tidy Up produce the exact reviewed side-end forms; Poison absorption is Toxic Spikes' separate `[of]` form. Generated Gen 9 rows root every family and removal route, while generated Court Change remains explicitly excluded.

The public extractor now rejects unsupported hazard source forms and a cap overflow before mutation, retains only public effect/count, and deletes the count at public `-sideend`. Mirrored simulator-backed v2 tests cover p1/p2 layer evidence, Rapid Spin clear, restored twins, deterministic identities, stale-candidate rollback and Python transition publication; direct source-engine tests cover all distinct caps, duplicates, switch-in, Rapid Spin/Mortal Spin/Defog/Tidy Up removals, and Poison absorption. No source/timer/request/snapshot data crosses the observation boundary.

**Switch-in witness repair (2026-10-05):** Four additional source-engine-prepared, real v2 successor transitions now cover both actor directions: Skarmory Stealth Rock causes the exact public `-damage|<active>|<HP>|[from] Stealth Rock` when Charizard enters; Ariados Sticky Web causes `-activate|<active>|move: Sticky Web` followed by `-unboost|<active>|spe|1`; Ariados Toxic Spikes emits `-status …|psn` at one layer and `-status …|tox` at two. Their pre-switch snapshots are restored into independent twins and produce equal transition IDs/fingerprints. Stale-rqid candidates reject without boundary mutation, each player sees the same public layer/consequence while retaining only its own request, and every actual successor bundle validates through Python. Existing shared HP/status/activation/stage grammar already validates these source shapes, so no broad protocol family was added. **CE-04D1 scoped verdict (2026-10-05, accepted):** Source and fixture review accepts the four distinct switch-in consequences and the pre-existing cap/removal/Poison-absorption evidence. Digest `f302c335197264979d898e7db62828934d5100aff474bef3212de06124207fe0` is attested for CE-04D1 only. Screens, weather, terrain, Court Change, generic side swapping, doubles, private hazard/source data, and complete-episode acceptance remain outside scope.

### CE-04E1 public weather-state checkpoint (2026-10-05, unreviewed)

Pinned `Field.setWeather/clearWeather` and the four `Conditions` weather
entries give one exact public `-weather` family for operative Gen 9 Random
Battle singles: generated move starts are untagged RainDance, SunnyDay, or
Snowscape; generated ability starts have exact `[from] ability: …|[of]
<active>` provenance for Drizzle, Drought, Orichalcum Pulse, Sand Stream, and
Snow Warning; each weather emits `[upkeep]`; expiry alone emits untagged
`none`. Replacement directly sets the next ID and does not invent a clear.
Sandstorm's only generated root is Sand Stream, so an untagged Sandstorm start
fails closed. Weather Rocks affect private duration only.

Generated Cloud Nine and Air Lock use `suppressWeather` and WeatherChange
without clearing `Field.weather`, so public typed weather remains the actual
source-backed ID and suppression has no invented typed field. The v2 fixture
mirrors both actor sides through Drought start, Rain Dance replacement, upkeep,
Cloud Nine switch suppression, restored continuation, stale-rqid rollback, and
actual Python publication. Direct source evidence also covers all generated
ability starts, duration clear, and terminal behavior without an invented
`none`. Neither requests, split HP, `weatherState`, source slot, duration,
hidden ability/item, nor snapshots appear in observations or records.

The shared TypeScript/Python validator rejects historical/extreme weather,
untagged Sandstorm, wrong origins, side-only or doubles sources, reordered or
extra tags, and whitespace variants before projection/DATA-001 publication.
No extractor production change, terrain/pseudo-weather/generic-field model,
weather-damage model, doubles support, or complete-episode claim entered this
slice. The coverage digest is unreviewed pending the checker result; manifest
digest fields remain unchanged. Computed local coverage digest:
`a2c6b2a3a424c74d6d1241c5990174d1d227f462be40a494057243b9482ab9fa`
(unreviewed).

**CE-04E1 scoped review verdict (2026-10-05, accepted):** Pinned
`Field.setWeather/clearWeather` and the four generated `Conditions` forms
establish exact untagged move starts, tagged active ability starts, literal
upkeep, and untagged `none` clear records. Generated Cloud Nine and Air Lock
suppress effects without clearing actual weather, so the bounded public field
retains the weather ID and has no invented suppression value. Mirrored p1/p2
v2 fixtures, restored twins, stale-candidate rollback, privacy assertions, and
Python transition-bundle publication pass. The shared TypeScript/Python rules
reject unsupported weather IDs, origins, identifier roles, tag orders, and
whitespace forms before projection or DATA-001 output. The attested local
coverage digest is `a2c6b2a3a424c74d6d1241c5990174d1d227f462be40a494057243b9482ab9fa`.
This accepts CE-04E1 only; terrain, pseudo-weather, generic field mechanics,
weather damage modeling beyond public HP evidence, private weather causes,
doubles, PIPELINE-002, and complete-episode claims remain outside scope.

**CE-04E1 baseline-fixture repair verdict (2026-10-05, accepted):** The failing
`simulator_coverage.test.ts` record `|-weather|raindance` was synthetic stale
input. Pinned `Moves.raindance` passes `weather: 'RainDance'`; after
`Field.setWeather`, `Conditions.raindance.onFieldStart` emits exactly
`|-weather|RainDance`. The repair changes only that fixture to the actual
tagless move-start record. It does not add a lowercase alias, tagged move form,
duration field, or suppression field. Matching TypeScript and Python negative
controls now reject lowercase `raindance` before state extraction and DATA-001
publication. The attested local coverage digest is
`b778e062f3934444adec94fc865fd6840d1514cc4551a818ae5c5701dde4151d`.
Focused weather validation, checker/self-test, and Python publication pass.
The aggregate coverage fixture still rejects its separate lowercase
`electricterrain` baseline under CE-04E2's unreviewed terrain grammar; that
failure does not broaden the weather grammar or block this weather-only verdict.

### CE-04E2 public terrain-state checkpoint (2026-10-05, unreviewed)

Pinned `Field.setTerrain/clearTerrain` plus the three operative terrain
conditions produce a finite public family. Generated Pincurchin/Electric Surge
and Miraidon/Hadron Engine set Electric Terrain; Rillaboom/Grassy Surge and
Arboliva/Seed Sower set Grassy Terrain; Indeedee/Indeedee-F/Psychic Surge set
Psychic Terrain. Each emits only `|-fieldstart|move: <Terrain>|[from] ability:
<finite setter>|[of] <active>`. Replacement calls the next FieldStart directly,
without a fabricated old-terrain end. Every source-backed clear (natural expiry,
generated Ice Spinner, generated Defog, and Teraform Zero where applicable)
uses the matching untagged `|-fieldend|move: <Terrain>` callback. No terrain
upkeep record exists. Misty Terrain and all direct terrain-move starts lack an
operative generated root and reject.

The existing public extractor already stores only the field terrain ID and
clears it at matching FieldEnd. The shared TypeScript/Python boundary now
requires the finite generated IDs, exact ability provenance, ordered active
`[of]` role, and exact tagless clear. It rejects source-less/reordered/extra
forms, wrong IDs/origins, side-only or doubles identifiers, whitespace forms,
and ungenerated Misty Terrain before projection or DATA-001. Pinned
per-target `effectiveTerrain` suppression has no public state-changing record,
so no public suppression field is added. Duration/source slot, Terrain Extender,
callback inputs, private requests, split HP, and simulator state remain absent.

`tests/terrain.test.ts` supplies direct source-engine checks for all five
generated callbacks, natural expiry, Ice Spinner clear, and terminal behavior,
plus mirrored p1/p2 real v2 transitions through Electric start, Grassy
replacement, public clear, restored twins, deterministic identities, stale-rqid
rollback, privacy, and Python successor publication. Python rehashed controls
cover v1/v2, both perspectives, and input/successor insertion with no-output
rejection. Terrain-induced mechanics, pseudo-weather, doubles, and
complete-episode claims remain out of scope. The computed local coverage digest
is `cb6a971ed3bf7706a6a268c3f93ba8e1068545e786bc835bebdf5b517cf395a7`
(unreviewed); manifest attestation fields are unchanged.

**CE-04E2 scoped review verdict (2026-10-05, accepted):** The review accepts the finite generated singles terrain family and exact public boundary: active-source ability FieldStarts for Electric Terrain (Electric Surge/Hadron Engine), Grassy Terrain (Grassy Surge/Seed Sower), and Psychic Terrain (Psychic Surge), plus the individual untagged matching FieldEnds. Replacement has no fabricated interim end; expiry and reachable clear routes use the same FieldEnd grammar; terminal completion retains terrain without inventing a clear. Focused TypeScript and Python checks cover p1/p2 real v2 transitions, restored deterministic twins, rollback, privacy, malformed rejection before publication, and successor-bundle publication. The attested local coverage digest is `cb6a971ed3bf7706a6a268c3f93ba8e1068545e786bc835bebdf5b517cf395a7`. This accepts CE-04E2 only; pseudo-weather, generic terrain mechanics, action inference outside owned requests, doubles, PIPELINE-002, and complete-episode claims remain outside scope.

**CE-04E2 aggregate coverage-fixture repair checkpoint (2026-10-05, unreviewed):** The aggregate effect-inventory fixture is corrected from its stale compact `|-fieldstart|electricterrain` synthetic record to the pinned Electric Surge emitter's ordered active-source record, `|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin`. The pinned condition has no compact generated terrain branch. Existing TypeScript/Python CE-04E2 controls accept that finite source form and reject compact/source-less terrain starts before projection or DATA-001. No grammar, extractor, finite terrain ID, private duration/source/request state, generic terrain support, manifest attestation, PIPELINE-002, or complete-episode claim changes. Computed local coverage digest: `9f88b5ebdba384722bd38351f09dfbd617907f3ced85fa9363ab26f8e5a40a0a` (unreviewed).

**CE-04E2 aggregate coverage-fixture repair verdict (2026-10-06, accepted):** Review verified the pinned Electric Surge emitter and generated `gen9randombattle` root produce the ordered active-source record and never the compact source-less form. The finite shared grammar, public-only terrain ID, and omission of duration, source state, requests, split-private HP, and simulator state remain unchanged. Build, focused terrain/protocol checks, Python record checks, and checker self-tests passed. The aggregate test progresses only to a separate stale Glaive Rush typed-volatile assertion; Glaive Rush is currently raw-only, so that assertion does not execute or contradict the terrain case and does not block this fixture-only attestation. Digest `9f88b5ebdba384722bd38351f09dfbd617907f3ced85fa9363ab26f8e5a40a0a` is attested only for this CE-04E2 aggregate-fixture repair. No terrain grammar, extractor, finite terrain ID, private-state boundary, generic terrain support, PIPELINE-002, or complete-episode claim changes.

### CE-04E3 public Trick Room pseudo-weather checkpoint (2026-10-05, unreviewed)

Pinned `Moves.trickroom.condition` emits only `|-fieldstart|move: Trick Room|[of] <active>` for the operative generated singles route. Its active reapplication invokes `onFieldRestart`, which calls `Field.removePseudoWeather` and produces the one tagless `|-fieldend|move: Trick Room`; residual expiry uses that same end callback. The generated set domain has Trick Room roots in Slowbro-Galar, Trevenant, Calyrex-Ice, and Rabsca, while Persistent's otherwise possible `[persistent]` start tag has no generated root and rejects. Trick Room is field-owned, so source switch/faint/form does not fabricate a clear; terminal delivery likewise retains the preceding public state without a FieldEnd.

The existing extractor retains only `pseudo_weather: trickroom`. It does not project `Field.pseudoWeather` duration, source, sourceSlot, a setter identity, queue speed state, raw requests, or simulator snapshots. The move-order witness is actual simulator protocol ordering through `Pokemon.getActionSpeed`; it never becomes a derived action mask or future-order prediction. Mirrored p1/p2 v2 fixtures prove start, slower-first next-turn order, reapplication clear, natural expiry, switch persistence, terminal preservation, restored twins, deterministic transition/fingerprint identity, stale-rqid rollback, both-perspective privacy, and Python successor-bundle publication.

A shared TypeScript/Python boundary now accepts only the exact active-source start and tagless end forms. It rejects source-less, legacy-command, side-only/doubles, Persistent-tagged, extra/reordered, and whitespace-repaired candidates before projection or DATA-001 across v1/v2, p1/p2, and input/successor rehashing. Other pseudo-weather IDs, generic priority/speed inference, doubles, and complete-episode claims remain outside this slice. The computed local coverage digest is `6c49f1c3b3573020baa3d76c988f6637ddcdb3e883185c5092bcd308ee6facea` (unreviewed); manifest attestation fields remain unchanged.

**CE-04E3 scoped review verdict (2026-10-05, accepted):** Review verified the generated singles Trick Room roots in Slowbro-Galar, Trevenant, Calyrex-Ice, and Rabsca, the exact active-source `-fieldstart|move: Trick Room|[of] <active>` form, and the tagless `-fieldend|move: Trick Room` form for reapplication removal and residual expiry. Source switch, faint, and form changes retain the field-owned public ID; terminal delivery does not fabricate a clear. Mirrored p1/p2 v2 transitions, actual simulator slower-first ordering, restored deterministic twins, stale-rqid rollback, private request boundaries, malformed rejection before publication, and Python successor publication passed. The public view contains only `pseudo_weather: trickroom`; queue speed, action legality, duration, setter identity, requests, and simulator state remain unprojected. Digest `6c49f1c3b3573020baa3d76c988f6637ddcdb3e883185c5092bcd308ee6facea` is attested only for CE-04E3; other pseudo-weather, generic priority/speed inference, doubles, and complete-episode claims remain outside scope.

### CE-04F1 public item reveal, consumption, and transfer checkpoint (2026-10-05, unreviewed)

Pinned base emitters and operative generated singles roots establish four bounded public item shapes: Frisk's ordered opposing-active reveal; Sitrus Berry's `[eat]` consumption; Knock Off's ordered opposing-active removal; and Trick/Switcheroo's item recipient plus their silent empty-side removal. Generated selectors provide the finite initial/transfer payload domain; public evidence updates only the named recipient or target. Existing extraction already clears known public item state and records public `last_item` as consumed or removed, without inferring an item from species, request, selector, or callback state.

**`[eat]` source-form repair (2026-10-05, unreviewed):** `Pokemon.eatItem`
emits `[eat]`, but only the 13 selector-reachable edible payloads are accepted:
Aguav, Chesto, Custap, Figy, Iapapa, Leppa, Lum, Mago, Passho, Rindo, Salac,
Sitrus, and Wiki Berry. The previous tag-only form admitted Choice Scarf. Both
runtimes now reject it and Air Balloon across rehashed v1/v2 p1/p2
input/successor candidates before projection or DATA-001 output, preserving
candidate lineage. The revised digest is unreviewed; attestation fields remain
unchanged.

The shared TypeScript/Python contract now requires canonical active singles identifiers, finite generated payload spelling, exact tag order, and the source-specific opposing role for Frisk and Knock Off. It fails closed before projection/DATA-001 on invented names, whitespace repair, side-only/doubles targets, private/same-side sources, reordered/duplicate/extra tags, non-edible `[eat]` payloads, and provenance on raw-only bare aliases. Mirrored p1/p2 actual v2 fixtures cover reveal, consumption, removal, transfer, restored deterministic twins, continuation, rollback, both-perspective request privacy, and Python successor-bundle publication. Rehashed Python controls cover v1/v2, p1/p2, input/successor validation and no-output rejection. Harvest/Recycle history, Pickup/Magician/Pickpocket, Choice locks, Fling, generic inventory inference, doubles, and training remain excluded. Computed local coverage digest: `538efd728a628201d5957dc881ee2cc56582b41f04280f82b8c05d80f598934d` (unreviewed); manifest attestation fields remain unchanged.

**CE-04F1 tagless `-enditem` repair (2026-10-05, unreviewed):** The empty-tag `dash_enditem` template now accepts only `Air Balloon`, exactly matching `data/items.ts:187-202`; the extractor classifies that tagless public form as `removed` rather than `consumed`, while tagged `[eat]`, Knock Off, Trick, and Switcheroo source forms retain their reviewed behavior. The mirrored p1/p2 Air Balloon v2 fixture proves removal, restored deterministic continuation, stale-rqid rollback, public-only perspectives, and Python successor publication. Rehashed TypeScript/Python v1/v2 p1/p2 input/successor controls accept exact Air Balloon and fail closed before projection/DATA-001 on Choice Scarf or other generated tagless payloads, malformed/side-only/doubles targets, tags, field-count changes, whitespace, and extra payload. Computed local coverage digest: `538efd728a628201d5957dc881ee2cc56582b41f04280f82b8c05d80f598934d` (unreviewed; manifest attestation fields unchanged).

**CE-04F1 tagless `-enditem` review blocker (2026-10-05):** Air Balloon is not the sole source-backed empty-tag payload. `Pokemon.useItem` (`sim/pokemon.ts:1758-1769`) emits a tagless end-item record for non-Gem items; generated Meteor Beam selects Power Herb (`data/random-battles/gen9/teams.ts:1229`), and `Items.powerherb.onChargeMove` invokes that method (`data/items.ts:4421-4427`). The resulting direct generated chain emits `|-enditem|p1a: Armarouge|Power Herb` before the accepted Meteor Beam `-anim` output. The Air Balloon-only shared rule rejects it before projection/Python publication. CE-04F1 remains unaccepted, and manifest digest fields remain unchanged, pending a complete source-qualified disposition for reachable tagless `useItem` forms.

### CE-04F1 tagless `-enditem` non-Gem `useItem()` repair checkpoint (2026-10-05, unreviewed)

The Air Balloon-only repair was narrowed incorrectly. Pinned `Pokemon.useItem` emits tagless `-enditem` for non-Gem use; the complete source-qualified generated singles domain is **Booster Energy, Focus Sash, Power Herb, Throat Spray, Weakness Policy, and White Herb**, plus the separately direct-emitted Air Balloon pop. Their generator roots are respectively Paradox ability selection, Smeargle/lead selection, generated Meteor Beam, generated sound-move selection, generated setup-policy selection, and generated Shell Smash/Unburden selection. Their callbacks are `Items.boosterenergy.onUpdate`, `focussash.onDamage`, `powerherb.onChargeMove`, `throatspray.onAfterMoveSecondarySelf`, `weaknesspolicy.onDamagingHit`, and `whiteherb.onUpdate`; each produces the exact active-target empty-tag record through `useItem`.

The shared TypeScript/Python form accepts only those seven payloads. Air Balloon is publicly `removed`; the six `useItem` forms are publicly `consumed`. This carries no callback, item selector, source, timer, history, request, or simulator-state data. `item.test.ts` now has mirrored p1/p2 source-engine v2 witnesses for every payload, restoration, deterministic continuation, rollback, privacy, and successor Python publication. Rehashed v1/v2/p1/p2/input/successor matrices accept every finite form and reject fabricated Choice Scarf/Leftovers, malformed/side-only/doubles targets, whitespace repair, tags, and extra payload before projection or DATA-001 output without lineage advance. Gems retain their tagged `[from] gem` form; selector-rootless callbacks and doubles-only Blunder Policy remain excluded. Computed local coverage digest: `ac2c0fbb51697d75eef1b8c2b8b55b2c721c1c193b7f62edbcb9e750c48c824e` (unreviewed; manifest attestation fields unchanged).

**CE-04F1 scoped review verdict (2026-10-05, accepted):** Review verified the finite generated-singles intersection of actual non-Gem `useItem` callbacks, including generated Meteor Beam → Power Herb, rather than treating the item selector as an output domain. Exact tagless and tagged forms remain disjoint; malformed or fabricated tagless candidates fail before projection and Python DATA-001 publication in both schemas, perspectives, and prefix positions. Mirrored v2 item transitions confirm owner-only typed reconciliation, shared raw evidence, restoration, deterministic continuation, rollback, and Python publication. Digest `ac2c0fbb51697d75eef1b8c2b8b55b2c721c1c193b7f62edbcb9e750c48c824e` is accepted for CE-04F1 only; generic item callbacks/history, doubles, and complete-episode claims remain excluded.

### CE-04D2 public nonstacking screen checkpoint (2026-10-05, unreviewed)

Pinned `Moves.reflect`, `lightscreen` and `auroraveil` plus `Side.addSideCondition/removeSideCondition` establish the finite generated singles screen family: Reflect uses tagless `-sidestart/-sideend ...|Reflect`; Light Screen and Aurora Veil use `move:`-prefixed forms; duplicate application has no restart and natural expiry uses the same untagged end. Generated Meowstic roots Reflect/Light Screen; Ninetales-Alola and Abomasnow root Aurora Veil under generated snow. Defog, Brick Break, Raging Bull, and Psychic Fangs remove screens through the same SideEnd path; the pinned Psychic Fangs callback removes all three screens before damage, with generated Mew a direct route. Switch/faint preserve the side condition; terminal delivery fabricates no end. Duration, Light Clay, setter/source slot, mitigation and snapshots remain private.

The shared TypeScript/Python grammar accepts only those six side-only exact forms and rejects aliases, active/doubles/whitespace sides, wrong label/prefix, tags/extra fields and ungenerated Safeguard/Mist before projection or DATA-001. Mirrored p1/p2 v2 fixtures cover all three public starts and Psychic Fangs ends, post-start restoration, same-lineage deterministic transitions, stale-candidate rollback, request privacy and Python publication; direct source-engine witnesses cover duplicate, expiry, Defog, Brick Break and Raging Bull. Generated Court Change remains explicitly unsupported, as do generic side swapping, doubles, Safeguard/Mist and other side-condition families. Computed local coverage digest is recorded below after focused validation (unreviewed; manifest fields unchanged).

**CE-04D2 Psychic Fangs repair (2026-10-05, unreviewed):** The source table
now distinguishes Psychic Fangs from Defog, Brick Break, and Raging Bull.
Pinned `onTryHit` calls all three ordinary screen `SideEnd` callbacks before
damage; generated Mew establishes the direct singles route. The direct fixture
and mirrored p1/p2 v2 transitions witness Reflect, Light Screen, and Aurora
Veil removal, public side deletion, both-perspective privacy, restored-twin
continuation, stale-action rollback, and Python publication. No grammar,
generic removal, side-swap, or attestation surface changed. Computed local
coverage digest: `8171d803227cdf218e3b24def428c11152345476834efde4b8ec3c6eb261a56a` (unreviewed; manifest
fields unchanged).

**CE-04D2 scoped review verdict (2026-10-05, accepted):** Review verified the
direct generated Mew → Psychic Fangs path and pinned pre-damage removal of
Reflect, Light Screen, and Aurora Veil through the ordinary tagless SideEnd
records. The p1/p2 v2 witnesses retain public side-state deletion,
both-perspective privacy, restoration, deterministic continuation, rollback,
and Python publication; Defog, Brick Break, and Raging Bull evidence remains
intact. Digest `8171d803227cdf218e3b24def428c11152345476834efde4b8ec3c6eb261a56a`
is accepted for CE-04D2 only. Generic removal, side swapping, doubles, damage
calculation, and complete-episode claims remain excluded.

### CE-04D3 Court Change public side-condition swap checkpoint (2026-10-05, unreviewed)

Pinned `Moves.courtchange.onHitField` exchanges its finite normal-side condition list before emitting exact no-payload `|-swapsideconditions`; the subsequent `|-activate|<active>|move: Court Change` occurs only after a successful exchange. Generated Cinderace supplies the direct Gen 9 Random Battle singles root. The shared TypeScript/Python rule admits only those exact source shapes: the dash swap record has no actor, side, tags, or payload; the activation must use a canonical singles active actor. Bare aliases, participant fields, doubles slots, tags, reordering, whitespace variants, and extra payload reject before projection/DATA-001.

The public extractor atomically exchanges only the pinned source-list IDs. This preserves public hazard layer counts and screen presence without carrying source setter, duration, Light Clay, item, request, or simulator-state data. Mirrored p1/p2 v2 source-engine fixtures prepare asymmetric Spikes/Toxic Spikes and Reflect/Light Screen, execute Court Change, verify both public perspectives, then switch both reserves to witness the swapped Spikes damage and Toxic Spikes poison. Restored twins, deterministic transition/fingerprint identities, stale-rqid rollback, request privacy, and Python successor publication pass. Free-for-all's distinct silent protocol, G-Max-only conditions, doubles, weather/terrain/pseudo-weather transfer, generic side swaps, damage calculation, and complete-episode claims remain excluded. Computed local coverage digest: `b99158a110b0546936e6f98077214d4eda7dfadc9815230bc632ea11ba4b05ac` (unreviewed; manifest attestation fields unchanged).

**CE-04D3 review blocker (2026-10-05):** Generated Shiftry can establish public Tailwind (`data/random-battles/gen9/sets.json:1926-1945`; `Moves.tailwind` at `data/moves.ts:19608-19618`), and pinned Court Change includes `tailwind` in its normal-side transfer list. The current generic side-condition extraction types Tailwind, so `|-sidestart|p1: One|Tailwind`, `|-sidestart|p2: Two|Spikes`, `|-swapsideconditions` changes p1's public map to `{spikes:1}` and p2's to `{tailwind:1}`. The CE-04D3 fixture and v2/Python evidence cover only hazards and screens. This unreviewed reachable typed side-condition transfer is broader than the scoped hazard/screen closure; it has no simulator-backed restoration or publication proof. CE-04D3 remains unaccepted and the manifest digest fields remain unchanged.

**CE-04D3 transferable-side-condition inventory repair (2026-10-05, unreviewed):** The complete pinned normal-side list is `mist`, `lightscreen`, `reflect`, `spikes`, `safeguard`, `tailwind`, `toxicspikes`, `stealthrock`, `waterpledge`, `firepledge`, `grasspledge`, `stickyweb`, `auroraveil`, and `luckychant`. The represented and generated-singles subset is exactly Spikes (1–3), Toxic Spikes (1–2), Stealth Rock, Sticky Web, Reflect, Light Screen, Aurora Veil, and Tailwind (all presence `1` except layers). Existing CE-04D1/D2 and Court Change witnesses cover the hazard/screen forms, including their distinct later switch-in records. A new mirrored p1/p2 v2 source-engine fixture pairs generated Cinderace with generated Shiftry: Cinderace establishes Stealth Rock/Sticky Web while Shiftry establishes two-layer Toxic Spikes, Light Screen, Aurora Veil under source-backed snow, and Tailwind; Court Change swaps the exact public count/presence values atomically, and Tailwind later emits `|-sideend|<new side>|move: Tailwind` on its transferred side. Restored twins converge with untouched sessions, stale rqid candidates preserve their boundary, both perspectives retain only owned requests, and actual successor bundles publish through Python. `mist`, `safeguard`, and `luckychant` have no selected Gen 9 Random Battle root; the three pledge conditions require `isAlly` Pledge combinations and are singles-impossible; the five G-Max IDs have no Gen 9 Random Battle route. Those unrepresented routes have explicit no-route dispositions rather than synthetic fixtures. Grammar remains only the exact no-payload swap plus canonical active Court Change activation; no generic swapping, doubles, G-Max, field transfer, duration/setter inference, or complete-episode scope was added. Computed local coverage digest is recorded after validation (unreviewed; manifest fields unchanged).

Focused build, Court Change/contract/extractor/pipeline TypeScript tests (50/50), Python publication tests (41/41), coverage self-test, and `git diff --check` pass. The standard coverage checker reports expected unreviewed drift `62e63cd27d89281efa242bdc20e3692f17479d13fa2fdd0d93fb8caff9741e58`; manifest digest fields are unchanged and no verdict is attested.

**CE-04D3 closure review hold (2026-10-05):** The inventory's route
classification is source-backed, but the asserted combined generated fixture
is not. Cinderace's selected rows supply Court Change only; they do not supply
Spikes, Reflect, Stealth Rock, or Sticky Web. Shiftry's Tailwind row supplies
Wind Rider and Tailwind only; it does not supply Snow Warning, Toxic Spikes,
Light Screen, or Aurora Veil. The fixture injects those invalid combinations,
so it is an engine-state test rather than proof of the claimed generated-set
routes. The complete reachable represented sibling set needing
format-faithful Court Change source-engine coverage is **Spikes, Stealth Rock,
Sticky Web, Reflect, Light Screen, and Aurora Veil**. Toxic Spikes/Ariados
and Tailwind/Shiftry retain individual direct roots. Mist, Safeguard, and
Lucky Chant have no selected route; Pledges require an ally in singles; and
the five G-Max conditions have no operative route. CE-04D3 remains
unaccepted, the computed digest
`62e63cd27d89281efa242bdc20e3692f17479d13fa2fdd0d93fb8caff9741e58` is
unreviewed only, and no manifest digest or review verdict was changed.

### CE-04F2 major-status projection checkpoint (2026-10-06, unreviewed)

The public protocol gate now validates source-shaped major-status apply and
cure records before TypeScript extraction and Python pipeline publication.
The gate accepts only the six status IDs, ordinary untagged status effects,
Rest, Flame/Toxic Orb, Effect Spore/Flame Body/Static/Toxic Chain, ordinary
`[msg]` cures, Natural Cure, and the generated frozen self-defrost rows. It
rejects fabricated status IDs, wrong item or ability pairings, malformed or
same-side provenance, unsupported cures, and tagged compatibility aliases
before a candidate observation can be projected or published.

The extractor records a new public status/replacement/cure from the accepted
record, treats an explicit statusless HP condition as a known clear, retains a
status that is explicitly present on switch-in, and clears the public
major-status field at faint. Existing Healing Wish and Revival Blessing exact
heal records remain the only silent-clear evidence. Status timers, sleep
selection, toxic counter, source object, terrain/item/ability guards,
private request state, generic callbacks, doubles, and episode claims remain
outside this checkpoint.

`tests/major_status.test.ts` covers both perspectives and lifecycle state;
`trainer/tests/test_major_status_contract.py` verifies the same accepted and
rejected grammar in Python. The existing mirrored v2 Healing Wish/Revival
fixtures cover restore, deterministic continuation, rollback, and Python
publication for silent clears. Computed local coverage digest:
`ba328907f58d969aebeb167b834fcf9262bf2c87f5620047bef705c61722ea8b` (**unreviewed**); manifest attestation fields remain
unchanged.

**CE-04F2 review hold (2026-10-06):** Do not attest this checkpoint. The
shared validators accept unsupported bare `|status|...` and
`|curestatus|...` aliases although the pinned base emitters use dashed
commands. They also reject four reachable source families: frozen
self-defrost records for generated Hydro Steam, Matcha Gotcha, and Steam
Eruption; Poison Touch's generated `psn` ability provenance; and move-origin
sleep records for generated Sleep Powder, Hypnosis, and Spore. Pinned
`Conditions.frz.onModifyMove`, `Conditions.psn.onStart`, and
`Conditions.slp.onStart` establish those exact public forms. The four current
`selective_boosts` failures are separate: the White Herb scenario rejects an
unsupported `-item` source form under current item grammar, not CE-04F2.
No code, tests, manifest digest, review verdict, or readiness claim changed.

### CE-04F shared status and White Herb repair checkpoint (2026-10-06, unreviewed)

| Contract family | Finite source domain | Pipeline disposition |
|---|---|---|
| Dashed status command | `-status` and `-curestatus` only | Bare `status`/`curestatus` are recognized unsupported aliases and stop before DATA-001 publication. |
| Poison Touch | `psn`, `[from] ability: Poison Touch`, opposing active `[of]` from `data/abilities.ts:3275-3287` through `Conditions.psn.onStart` | The public status ID changes; ability ownership, chance, guards, and callback state remain absent. |
| Direct sleep | Sleep Powder, Hypnosis, Spore only, each `slp|[from] move: <name>` from `Conditions.slp.onStart` | Pinned Gen 9 Random Battle movepool inventory has these three direct sleep roots. Other move names stop. |
| Frozen self-defrost | Flare Blitz, Fusion Flare, Hydro Steam, Matcha Gotcha, Pyro Ball, Sacred Fire, Scald, Scorching Sands, Steam Eruption | `Conditions.frz.onModifyMove` emits the dashed source tag; the generated-movepool inventory has exactly these nine defrost moves. |
| White Herb repeat | tagless `-enditem White Herb`, silent negative clear, then exact `-item White Herb|[from] move: Recycle` | `data/items.ts:7201-7214` consumes and clears; `data/moves.ts:15376-15381` restores. The extractor returns held then consumed state without generic history inference. |

`major_status.test.ts`, `selective_boosts.test.ts`, item controls, the shared
contract matrix, and Python rehash controls cover v1/v2, p1/p2, input/successor,
valid records, malformed records, no-output rejection, and unchanged candidates
after rejection. The White Herb simulator paths cover restoration, deterministic
continuation, rollback, privacy, and successor publication.

Exclusions remain explicit: generic status/item callback handling, unlisted
sleep/defrost moves, generic Recycle payloads, private counters/history/requests,
doubles, and complete episodes. Computed local coverage digest
`16bfe90d2fc9e54efbb16aa13d47a26c642d51f18f198edc4519618c11b0b05b` is
**unreviewed**; manifest attestation fields are unchanged.

**CE-04F2 scoped review verdict (2026-10-06, accepted):** The pipeline review
accepts only dashed `-status` and `-curestatus` records in the finite shared
table: Poison Touch `psn` with its opposing-active source, direct Sleep Powder,
Hypnosis, and Spore `slp` rows, and the nine generated frozen self-defrost
moves including Hydro Steam, Matcha Gotcha, and Steam Eruption. Bare aliases,
unlisted move names, malformed provenance, and non-singles identifiers stop
before projection and publication. Rehashed TypeScript/Python v1/v2, p1/p2,
input/successor controls preserve candidate state and produce no output on
rejection. No generic status callback, private state, doubles, or complete
episode support is accepted.

**CE-04F1 scoped review verdict (2026-10-06, accepted):** The pipeline review
accepts exactly the White Herb Recycle output
`|-item|<active>|White Herb|[from] move: Recycle` after the independently
bounded tagless consume and silent negative clear. Mirrored p1/p2 source-engine
paths restore, consume again, continue deterministically, roll back rejected
candidates, retain private request boundaries, and publish successor bundles
through Python. Generic Recycle, other restored payloads, item-history
inference, doubles, and complete-episode claims remain rejected or out of
scope. Digest `16bfe90d2fc9e54efbb16aa13d47a26c642d51f18f198edc4519618c11b0b05b`
is attested only for these CE-04F1 and CE-04F2 repairs; PIPELINE-002 remains
unaccepted.
