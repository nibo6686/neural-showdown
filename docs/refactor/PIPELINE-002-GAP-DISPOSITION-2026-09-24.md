# PIPELINE-002 gap disposition — 2026-09-24

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
