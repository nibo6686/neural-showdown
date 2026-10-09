# SLICE-001 — Schema-Closure Audit

**Status:** Completed documentation audit; no implementation change, coverage
digest refresh, or coverage attestation.

## Current status note — 2026-10-01

This remains a schema-closure audit, not a complete-episode acceptance. The
separate SLICE-002A scanner and SLICE-002B format-provenance/reachability work
has since received scoped acceptance and attestation; that later evidence does
not turn every schema finding here into accepted runtime behavior. The
complete-episode closure audit is separately complete as a gap inventory and
backlog, while episode implementation remains open and
`faithful_complete_episode:false` remains required. See
[`PROJECT_STATUS.md`](../PROJECT_STATUS.md) for the current milestone and next
sequence.

## Recorded audit snapshot

- Recorded branch: `refactor/state-001-observable-state`
- Recorded HEAD: `b056f7ef5433cef254d2cfdaf822cc23c0c24b0c`
- Recorded worktree status: clean before this audit document was created.
- Scope: only `pokemon-showdown@0.11.10` and `gen9randombattle` (Gen 9
  singles). Package-wide emitter evidence is not a reachability claim.
- Preserved boundary: `faithful_complete_episode:false`; no mechanics, feature,
  dataset, training, model, replay, network, install, or cleanup work.

## Evidence Reviewed

The inventory backbone is
`trainer/src/neural/protocol_contract.json` (`showdown-protocol-contract/v2`):
114 supported tokens, one record fixture per token, 44 valid controls, 112
rejection fixtures, six recognized-but-unsupported spellings, and one
framing-only record. The following sources establish the implementation path:

- Contract loaders: `sim-core/src/protocol_contract.ts:129-279` and
  `trainer/src/neural/protocol_contract.py:113-259` require the exact asset
  shape, exact rule object, unique fixture/token coverage, and the pinned
  simulator identity.
- TypeScript validation and projection:
  `sim-core/src/observable_state.ts:330-910,997-1010,1190-1219`,
  `sim-core/src/state_extractor.ts:187-290,805-872`, and
  `sim-core/src/public_boosts.ts:7-92`.
- Pipeline filtering/stop boundary:
  `sim-core/src/pipeline_integration.ts:188-218,260-286` and
  `sim-core/src/pipeline_episode.ts:101-114`.
- Python validation/DATA-001 publication:
  `trainer/src/neural/protocol_contract.py:261-629` and
  `trainer/src/neural/pipeline_record.py:113-154,260-410`, with
  `trainer/src/neural/ts_identity.py:47-156` for cross-runtime identity joins.
- Focused boundary tests (read, not re-run):
  `sim-core/tests/protocol_contract_validation.test.ts`,
  `sim-core/tests/public_stages.test.ts:230-264`, and
  `trainer/tests/test_pipeline_record.py:231-403,486-564`.
- Product and source context: `docs/requirements/spec.md`,
  `docs/PROJECT_STATUS.md`, `docs/refactor/FACTORY_BACKLOG.md`,
  `docs/refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md`, and
  `docs/contracts/SIMULATOR_COVERAGE.md`.

`C` below means the exact sanitized record fixture in the shared asset.
`S` means that fixture declares pinned-source/current-adapter grammar evidence;
the source-coverage document qualifies it as package-wide inventory evidence,
not proven Random Battle reachability. `T0` means both focused runtime suites
iterate every `C` record and every rejection fixture. `T1` means a more specific
control/rehashed publication test is present. Evidence is listed as existing
coverage; this audit did not execute it.

Current direct random-set evidence in the reviewed coverage document is limited
to Beak Blast, Focus Punch, Protect, and Roost. Every other `C/S` entry is
source/fixture evidence only until SLICE-002B establishes direct or indirect
`gen9randombattle` reachability.

## Terms Used in the Matrix

All fields are ordered pipe-delimited payloads after a token. `>=` permits the
shown required fields plus the validator's currently unconstrained trailing
fields; that permissiveness is called out where it prevents grammar closure.

| Mark | Meaning |
|---|---|
| `A` | Active player identifier: `p1a:`/`p2a:` through slots `a`–`f`, exact `: ` separator, trimmed nonempty display name. |
| `SOA` | Side-or-active player identifier: `p1:`/`p2:` or an active identifier. |
| `S` | Side-only player identifier. |
| `P` | Side ID (`p1` or `p2`), not a Pokémon identifier. |
| `TXT` | Trimmed nonempty free text; it is not an enumerated simulator value. |
| `INT` | ASCII safe integer, no leading zeroes except `0`; signed only where stated. |
| `HP` | `0 fnt` or positive safe `current/max` with `current <= max`, optionally one of `brn`, `par`, `slp`, `psn`, `tox`, `frz`. |
| `PUB` | Validated record retained in the shared sanitized public prefix. |
| `REQ(p)` | Private to its addressed perspective; never public raw evidence. |
| `RAW` | Retained evidence, but no ordinary typed state is projected. |

An **effective typed** result means current TypeScript projection can place a
value in an observation (including v2 `public_boosts`). It does not claim that
every value or full mechanic lifecycle is semantically closed. Python validates
the retained prefix and v2 stage evidence before it constructs the DATA-001
record; it does not independently reconstruct the full TypeScript view.

## Runtime Boundary and Filter Order

| Stage | Verified behavior |
|---|---|
| Contract load | Both runtimes reject missing, malformed, structurally incomplete, duplicate, conflicting, or rule-mutated assets before exposing command sets. `-singlemove` must remain `unsupported_stop`. |
| TypeScript raw validation | `validateRawProtocolRecord` checks framing, token disposition, and token grammar before `ObservableBattleState` routes an event. Unknown and recognized unsupported tokens reject; malformed supported grammar rejects. |
| Direct observable projection | It validates the whole raw prefix, verifies request ownership when raw `side.id`/`player` is present, then removes framing/`tier` and replaces a request body with canonical `|request|{}` or `|request|{"rqid":N}`. The addressed request object remains separately private. |
| Pipeline-prefix projection | It validates each nonempty normalized line before filtering `|`, `request`, and `tier`; it keeps other records and rewrites a valid `|t:|N` to `|t:|0`. The blank-line exception in **B-01** is the only pre-validation drop found. |
| Python publication | `_prefix` validates every retained record, rejects retained framing and `tier`, permits only `{}`/`{"rqid":N}` request prefix JSON, verifies the TypeScript observable hash, exact successor extension, identity joins, and then writes DATA-001. Failure yields exit 2 and no stdout. |
| Episode outcome | Unknown/recognized-unsupported protocol is an explicit protocol truncation before commit; malformed supported grammar is a failure, not a truncation. |

## Complete Accepted-Record Matrix

This table covers every one of the 114 supported tokens exactly once. `T` is
effective typed projection, `R` is raw-only, and `F` is filtered after
validation. `T†` is a classification discrepancy: the contract fixture labels
the token `raw-only`, but v2 public-stage code types it (see **B-02**).

| ID | Exact token(s): effective disposition | Ordered field grammar, cardinality, and identifier role | Visibility and TypeScript projection | Python/DATA-001 and evidence |
|---|---|---|---|---|
| G01 | `ability` R; `-ability` T | `A`, ability `TXT`; `>=2` payloads; trailing tags are unconstrained. | `PUB`; only `-ability` calls typed ability projection. | Retained and revalidated. `C/S/T0`; bare `ability` has fixture-only evidence (**B-05**). |
| G02 | `block`, `-block` R | `A`, effect `TXT`; `>=2`; trailing tags unconstrained. | `PUB/RAW`. | Retained/revalidated; `C/S/T0`. |
| G03 | `boost` T†, `-boost` T; `unboost` T†, `-unboost` T | `A`, stat `atk|def|spa|spd|spe|accuracy|evasion`, unsigned `INT` `0..12`, then zero or more ordered singleton tags from `[from] TXT`, `[silent]`, `[zeffect]`. | Dash forms update typed boosts. Bare forms are normalized to dash forms for v2 public stages. | Prefix and v2 stage evidence revalidated; repeated tag kinds reject before projection/publication; `C/S/T0/T1` (public-stage controls). |
| G04 | `setboost` T†, `-setboost` T | `A`, stat enum, signed `INT` `-6..6`, then G03 ordered singleton tags. | Dash form updates typed boosts; bare form normalizes for v2 stages. | `C/S/T0/T1`; signed source control is `sim/battle.ts:1941-1942`. |
| G05 | `clearallboost` T†, `-clearallboost` T | Exact no-payload record, optionally one final empty field only. | Dash form clears typed boosts; bare form normalizes for v2 stages. | `C/S/T0/T1`. |
| G06 | `clearnegativeboost`, `-clearnegativeboost` T | Exactly `A`, optionally one `[silent]` or `[zeffect]` tag. | Typed selective negative-stage clear; bare form is v2 public-stage normalization. | `C/S/T0/T1`. |
| G07 | `clearpositiveboost`, `-clearpositiveboost` T | `A`, source `A`, effect `TXT`; `>=3`; further fields currently accepted. | Typed selective positive-stage clear; both identifiers must be active. | `C/S/T0/T1`; extra-field grammar remains open. |
| G08 | `clearboost` T†, `-clearboost` T | Exactly `A`. | Dash form clears typed boosts; bare form normalizes for v2 stages. | `C/S/T0/T1`. |
| G09 | `status`, `curestatus` R; `-status`, `-curestatus` T | `A`, status `TXT`; `>=2`; trailing tags unconstrained. | Dash forms update typed public status; bare forms remain raw. | `C/S/T0`; status vocabulary is only closed inside `HP`, not here. |
| G10 | `damage`, `heal`, `sethp` R; `-damage`, `-heal`, `-sethp` T | `A`, `HP`, then zero or more ordered singleton tags. Damage allows `[from] TXT`, `[of] SOA`, `[silent]`, `[partiallytrapped]`; heal adds `[zeffect]`, `[wisher] TXT`; sethp permits `[from] TXT`, `[silent]`. | Dash forms update typed HP/status. `-heal` uniquely accepts `S` only for exactly `-heal|S|HP|[from] move: Revival Blessing`; otherwise target is `A`. | `C/S/T0/T1`; shared CE-02 cardinality rejects repeated tag kinds before projection/publication. |
| G11 | `switch`, `drag` T | Exactly `A`, details `TXT`, `HP`, with optional final `[from] TXT`; 3 or 4 payload fields. | Typed roster/active state. | `C/S/T0/T1`; public prefix is retained. |
| G12 | `detailschange` T | `A`, details `TXT`, optionally `HP`; exactly 2 or 3 payload fields. | Typed source/detail change. | `C/S/T0`; conditionless source form is accepted. |
| G13 | `end` R | Exact no-payload record, optional final empty field only. | `PUB/RAW` battle marker. | `C/S/T0`. |
| G14 | `-end` T | `A`, effect `TXT`; `>=2`; extra effect fields/tags unconstrained. | Typed volatile/type lifecycle handling. | `C/S/T0`; unclassified effect-value path is **B-03**. |
| G15 | `endability` R; `-endability` T | Bare form is exactly `A`. Dash form is either exactly `A`, or exactly `A`, old-ability `TXT`, `[from] move: TXT`. | Dash form updates ability/suppression state. | `C/S/T0/T1`; extended move-source form is validated. |
| G16 | `enditem` R; `-enditem` T | `A`, item `TXT`; `>=2`; tags unconstrained. | Dash form updates item state. | `C/S/T0`. |
| G17 | `faint` T | Exactly `A`. | Typed faint/reset state. | `C/S/T0/T1`. |
| G18 | `fieldend`, `fieldstart`, `weather` R; `-fieldend`, `-fieldstart`, `-weather` T; `-fieldactivate` R | Effect `TXT` at payload 1; `>=1`; extra fields/tags unconstrained. | Dash weather/field forms type coarse field state; `-fieldactivate` remains raw. | `C/S/T0`; unenumerated effect values can become typed (**B-03**). |
| G19 | `formechange` R; `-formechange` T | `A`, species/details `TXT`; `>=2`; extra fields/tags unconstrained. | Dash form types form state. | `C/S/T0`. |
| G20 | `gen`, `turn` T | Exactly one unsigned `INT`. | Typed battle metadata. | `C/S/T0`; exact prefix/identity checks bind it. |
| G21 | `hitcount`, `-hitcount` R | `A`, unsigned `INT`; `>=2`. | `PUB/RAW` outcome evidence. | `C/S/T0`. |
| G22 | `immune`, `-immune`, `resisted`, `-resisted`, `crit`, `-crit`, `supereffective`, `-supereffective`, `mustrecharge`, `-mustrecharge` R | `A`; `>=1`; optional effect/tag fields are unconstrained. | `PUB/RAW` outcome evidence. | `C/S/T0`; no legal-action inference. |
| G23 | `item` R; `-item` T | `A`, item `TXT`; `>=2`; tags unconstrained. | Dash form types item state. | `C/S/T0`. |
| G24 | `miss`, `-miss` R | Source `A`, target `A`; `>=2`; tags unconstrained. | `PUB/RAW` outcome evidence. | `C/S/T0`. |
| G25 | `move` T | Source `A`, move `TXT`; target may be omitted/empty, `null` only with one final `[notarget]`, or `SOA`; then allowed tags `[still]`, `[miss]`, `[notarget]`, `[zeffect]`, `[from] TXT`, `[anim]TXT`, `[spread] pXa,pYb`. `[notarget]` is unique/final. | Typed last-move evidence; target is not rewritten. | `C/S/T0/T1`; fixture prose's `or -` conflicts with both validators (**B-06**). |
| G26 | `-nothing` R | Exact no-payload record, optional final empty field only. | `PUB/RAW`; exact hyphenated spelling is preserved. | `C/T0`; pinned Splash source evidence is recorded in `SIMULATOR_COVERAGE.md`. |
| G27 | `-singleturn` R | Exactly `A`, effect. Untagged effect must be one of the 19 literal contract values; or exactly one tagged form: `move: Follow Me|[zeffect]`, or `Helping Hand|[of] A`. | `PUB/RAW`; never becomes a volatile. Helping Hand's `[of]` is **active**, unlike generic health `[of]` `SOA`. | `C/S/T0/T1`; all configured literal/tagged templates have controls. |
| G28 | `cant` R | `A`, reason `TXT`, optional move `TXT`; `>=2`; fields after the optional move are unconstrained. | `PUB/RAW`; cannot define legal actions. | `C/S/T0`. |
| G29 | `player` T | `P`, name `TXT`; `>=2`; avatar/rating/trailing metadata accepted. | Typed player/name metadata. | `C/S/T0`. |
| G30 | `poke` T | `P`, details `TXT`; `>=2`; optional item marker/trailing data. | Typed public team-preview evidence. | `C/S/T0`. |
| G31 | `replace` T | Exactly `A`, details `TXT`, optionally one `HP`; no tags. | Typed Illusion appearance/reveal state. | `C/S/T0/T1`; conditionless source form is retained. |
| G32 | `request` T / filtered-private | JSON object reconstructed from all payload chunks; root object only, finite numbers; optional safe-integer `rqid`, never null/bool; other keys transient-private. Raw `side.id`/`player`, when present, are `P`. | `REQ(p)`: TS checks those fields against perspective. Direct observation keeps only canonical `rqid`; pipeline projection removes the record and keeps only addressed request state. | Python allows structurally only `{}`/`{rqid}` if retained; raw/private body fails before DATA-001. Canonical spelling and `rqid` cross-check drift are **B-08**. `C/S/T0/T1`. |
| G33 | `error`, `gametype`, `rule` R | Payload `TXT`; `>=1`; suffix fields accepted. | `error` is channel-scoped/private-or-stream diagnostic and has no player field; the contract relies on caller stream routing. Other records are raw metadata. | `C/S/T0`; per-record privacy routing is an open source-boundary item (**B-07**). |
| G34 | `sidestart`, `sideend` R; `-sidestart`, `-sideend` T | Side field begins `p1`/`p2` and ends or continues with `:`; condition `TXT`; `>=2`; tags unconstrained. | Dash forms type coarse side-condition counts. | `C/S/T0`; condition/layer semantics are not closed (**B-03**). |
| G35 | `-hint` R | Message `TXT`; `>=1`. | `PUB/RAW`; no prose-derived state. | `C/S/T0`. |
| G36 | `-anim` R | Exactly source `A`, literal `Spectral Thief`, target `A`. | `PUB/RAW` animation evidence. | `C/T0`; scoped fixture/source evidence only. |
| G37 | `-copyboost` T | Exactly recipient `A`, donor `A`, literal `[from] move: Psych Up`. | Typed bounded public-stage copy. | `C/T0/T1`; source/fixture controls are scoped to Psych Up. |
| G38 | `-invertboost` T | Exactly `A`, literal `[from] move: Topsy-Turvy`. | Typed only for bounded base Topsy-Turvy stage inversion. | `C/T0/T1`; no broader inversion semantics. |
| G39 | `start` R | Exact no-payload record, optional final empty field only. | `PUB/RAW` battle marker. | `C/S/T0`. |
| G40 | `-start` T | `A`, effect `TXT`; `>=2`; extra effect fields/tags unconstrained. | Types volatile/type lifecycle evidence. | `C/S/T0`; arbitrary effect values currently pass (**B-03**). |
| G41 | `teamsize` T | Exactly `P`, unsigned `INT`. | Typed team-size metadata. | `C/S/T0`. |
| G42 | `terastallize` R; `-terastallize` T | `A`, type `TXT`; `>=2`; extra fields accepted. | Dash form types public Tera event. | `C/S/T0`; type value is not enumerated. |
| G43 | `tier` F | Exactly one format-label `TXT`. | Validated then removed from direct observable and pipeline public prefixes. | Python rejects a retained `tier`; `C/S/T0/T1`. |
| G44 | `upkeep` R | Exact no-payload record, optional final empty field only. | `PUB/RAW`. | `C/S/T0`. |
| G45 | `win` T | Exactly winner `TXT`. | Typed terminal winner evidence. | `C/S/T0`. |
| G46 | `tie` T | No payload, or exactly one final empty field. | Typed terminal tie evidence. | `C/S/T0`. |
| G47 | `transform` T†; `-transform` T | Bare: source `A`, target `TXT`, `>=2`. Dash: source `A`, target `A`, `>=2`. | Bare form normalizes for v2 public-stage evidence; dash form types Transform state. | `C/S/T0/T1`; asset calls bare form raw-only despite v2 projection (**B-02**). |
| G48 | `swapsideconditions` R; `-swapsideconditions` T | Exact no-payload record, optional final empty field only. | Dash form swaps typed coarse side-condition maps. | `C/S/T0`. |
| G49 | `fail`, `-fail` R | `A`, optional action `TXT`; `>=1`; trailing fields unconstrained. | `PUB/RAW` failure evidence. | `C/S/T0`. |
| G50 | `activate`, `-activate` R | `A`, effect `TXT`; `>=2`; trailing fields unconstrained. | `PUB/RAW`. | `C/S/T0`. |
| G51 | `-message` R | Message `TXT`; `>=1`. | `PUB/RAW` diagnostic text. | `C/S/T0`. |
| G52 | `prepare`, `-prepare` R | `A`, move `TXT`, optional target `A` or literal `-`; `>=2`; trailing fields unconstrained. | `PUB/RAW` preparation evidence. | `C/S/T0`. |
| G53 | `c`, `chat` R | User `TXT`, message `TXT`; `>=2`. | `PUB/RAW`; no model state. | `C/S/T0`. |
| G54 | `rated` R | No payload or exactly one nonempty rating `TXT`; no more fields. | `PUB/RAW` metadata. | `C/S/T0`. |
| G55 | `teampreview`, `clearpoke`, `done` R | Exact no-payload record, optional final empty field only. | `PUB/RAW`. | `C/S/T0`. |
| G56 | `inactive`, `inactiveoff` R | Message `TXT`; `>=1`. | `PUB/RAW` inactivity evidence. | `C/S/T0`. |
| G57 | `t:` R | Exactly one unsigned `INT` timestamp. | Validated, then pipeline normalizes it to `|t:|0`; raw timing is not state. | `C/S/T0`. |
| G58 | `message` R | Message `TXT`; `>=1`. | `PUB/RAW` public diagnostic. | `C/T0`; fixture cites pinned `sim/battle.ts:1393`. |

The count reconciles as follows: 51 effective typed tokens (including the six
`T†` v2-only exceptions and bounded `-invertboost`), 62 effective raw-only
tokens, and one filtered token (`tier`) = 114. The framing-only `|` is not a
supported token and is recorded separately below.

### Exact `-singleturn` Raw-Only Vocabulary

The G27 literal set is intentionally closed at this boundary. Its untagged
effects are `move: Protect`, `move: Beak Blast`, `Crafty Shield`,
`move: Electrify`, `move: Endure`, `move: Focus Punch`, `move: Follow Me`,
`Protect`, `move: Magic Coat`, `Mat Block`, `Max Guard`, `Powder`,
`Quick Guard`, `move: Rage Powder`, `move: Roost`, `move: Shell Trap`,
`Snatch`, `move: Spotlight`, and `Wide Guard`. The only tagged templates are
`move: Follow Me|[zeffect]` and `Helping Hand|[of] A`.

All 21 templates have valid controls; the Helping Hand controls exercise both
active sides. Nothing in this list promotes a one-turn effect into typed volatile
state.

## Filtering, Framing, and Private Request Ledger

| Input | Validate before removal/sanitization? | TypeScript result | Python/DATA-001 result | Closure status |
|---|---|---|---|---|
| `|` | Yes in normal paths; contract cites `sim/battle.ts:1451,2754,2881`. | Removed from direct observable and pipeline prefixes. | Rejects if it survives into a publication prefix. | Closed for defined framing. |
| `|tier|LABEL` | Yes; exactly one nonempty label; fixture cites `sim/battle.ts:1857`. | Removed from direct observable and pipeline prefixes. | Rejects if retained. | Closed. |
| Valid raw `|request|JSON` | Yes; object/finite/rqid checks. | Direct projection canonicalizes to `rqid` only; pipeline projection removes it. Addressed `ChoiceRequestView` stays private. | Only empty or `rqid`-only sanitized request marker may remain; raw/private body rejects. | Structurally closed; canonical retained form/rqid binding is **B-08**. |
| Malformed request or malformed tier/framing | Yes, except B-01. | Throws before any filter. | Cannot publish. | Closed for defined records. |
| `|t:|N` | Yes. | Retained as `|t:|0` in pipeline prefix. | Revalidates normalized retained record. | Closed; raw timestamp intentionally not retained. |
| Empty raw/empty delimiter segment | **No** in pipeline-prefix projection. | Dropped by `if (line === '') continue`. | Never sees it. | **Open: B-01.** |

## Explicit Stops and Generic Unknowns

| Class | Exact input / rule | TypeScript and Python disposition | Publication result |
|---|---|---|---|
| Recognized unresolved alias | `clearstatus`, `-clearstatus`, `nothing`; no accepted field grammar. | Reject before routing; Python emits stable unresolved-alias diagnostic with index/command. | No DATA-001; episode truncates as unsupported protocol. |
| Recognized internal alias | `copyboost`, `invertboost`; no accepted field grammar. | Reject before routing; only hyphenated canonical forms are accepted. | No DATA-001; unsupported protocol path. |
| Explicit stop | `-singlemove` (`data/moves.ts:3619,6896,8176,15098` in the shared contract); no accepted field grammar. | Reject before routing; retained neither typed nor raw. | No DATA-001; episode truncates before candidate commit. |
| Unknown token | Any token outside the supported/recognized lists, for example `|futuremechanic|opaque`. | Reject before routing. | No DATA-001; episode truncates as unsupported protocol. |
| Malformed accepted token | Wrong arity, identifier, numeric syntax/range, configured tag, JSON, or literal template. | Reject before projection. | No DATA-001; episode reports `failed`, not a supported-mechanic truncation. |
| Unclassified value inside a generic accepted token | For example a new effect value in `-start`, `-weather`, `-fieldstart`, or `-sidestart`. | **Currently accepted** as nonempty `TXT`; several paths project it to typed state. | Python validates syntax and may publish the resulting observation. | **Open: B-03.** |

## Focused Coverage Inventory

| Coverage | What the existing focused test source proves |
|---|---|
| `T0` shared fixture loop | TypeScript and Python accept all 114 record fixtures and valid controls; both reject all 112 rejection fixtures with matching rejection categories. |
| Loader tests | Both loaders reject missing, malformed, structurally invalid, duplicate, mismatched-fixture, conflicting supported/unsupported, and altered-rule assets. |
| Filtering tests | TypeScript proves malformed `request`/`tier` fail before filtering and valid `|`, request, and tier filter as designed. Python rehashed cases reject retained tier and private request fields with no stdout. |
| Rehashed publication matrix | v1/v2 × p1/p2 × input/successor prefixes use every rejection fixture; Python CLI exits 2 with empty stdout while valid controls publish. |
| Identifier and Helping Hand controls | Exact colon-space spelling is required. Both active sides are valid Helping Hand sources; side-only/missing/malformed sources reject before projection/publication. |
| v2 public stages | Public-prefix reconstruction normalizes bare boost-family tokens and `transform` to their hyphenated forms; this is the evidence for B-02. |

No inspected test covers an empty segment through
`projectPipelineProtocolPrefix`, a noncanonical retained sanitized request, or a
synthetic unclassified generic effect value before typed projection. Those are
follow-up coverage gaps, not an authorization to change this slice.

## Verified Blockers and Follow-ups

### B-01 — Pre-validation empty-record bypass (TypeScript/Python publication boundary)

`sim-core/src/pipeline_integration.ts:193-198` strips a final line delimiter and
then drops `''` before `validateRawProtocolRecord`. In contrast,
`normalizeProtocolPrefix` rejects the same normalized empty record at
`observable_state.ts:330-348`, and Python cannot reject a record that TypeScript
has removed.

Static reproduction path: pass `['|gen|9', '', '|turn|1']` (or an isolated
`'\n'` segment) to `projectPipelineProtocolPrefix`. The empty segment is omitted;
the resulting retained prefix can reach TypeScript observation projection and
Python sees only the remaining records. Direct raw validation of `''` is
malformed. This is a genuine fail-closed gap at the cross-runtime handoff.

**Follow-up classification:** boundary repair and regression test, outside
SLICE-001. Do not treat the defined `|` framing record as equivalent to this
unclassified empty segment.

### B-02 — Raw-only fixture classifications disagree with v2 typed projection

The asset labels `boost`, `unboost`, `setboost`, `clearboost`,
`clearallboost`, and `transform` as `raw-only`. However,
`sim-core/src/public_boosts.ts:19-20` canonicalizes each bare token to its
hyphenated counterpart, and `projectObservableBattleState` uses that result to
populate v2 opponent `public_boosts` (`observable_state.ts:1195-1198`). The
Python public-stage implementation mirrors the same normalization and validates
the v2 result before DATA-001 publication.

Static reproduction path: the existing focused stage control uses
`['|-setboost|p2a: Target|atk|-6', '|boost|p2a: Target|atk|12']` and observes
typed `atk: 6` for the target. Thus this is metadata/classification drift, not a
TypeScript/Python calculation mismatch.

**Follow-up classification:** contract-metadata/schema-closure correction and
fixture coverage review; no mechanics change is implied.

### B-03 — Generic effect values are not fail-closed before typed projection

`-start`/`-end`, `-weather`, `-fieldstart`/`-fieldend`, and
`-sidestart`/`-sideend` accept a nonempty free-text effect/condition without a
shared source-derived value allowlist. The TypeScript extractor inserts such
values into volatiles, weather, pseudo-weather, or side-condition maps
(`state_extractor.ts:819-872`). Python validates only the token grammar and
published v2 stage evidence; it has no generic effect-value classifier.

Static reproduction path: an otherwise valid prefix containing
`|-start|p1a: Pikachu|futurecondition` passes the current raw grammar and adds
`futurecondition` to the typed volatile set. Equivalent unreviewed values in
`-weather`, `-fieldstart`, and `-sidestart` follow their typed handlers. This is
the documented scanner/condition-closure gap, not a new mechanic request.

**Follow-up classification:** fail-closed source-inventory and value-disposition
work in SLICE-002A before any faithful typed-state claim.

### B-04 — Tag dependency/order closure remains incomplete

Health-event tags are individually allowlisted and unique, but the validators
do not encode all source-required dependencies/order. Several `>=` grammar
templates also leave trailing fields unconstrained. This agrees with the
mechanical assessment's stated HP-tag and optional-tag grammar gap.

**Follow-up classification:** source grammar scan plus exact accepted/rejection
controls; retain raw-only or stop dispositions until then.

### B-05 — Bare `ability` has sanitized-fixture, not pinned-emitter evidence

Its fixture explicitly says “bare ability has no pinned emitter.” It is safely
raw-only, but no source evidence establishes it as an emitted
`gen9randombattle` record. This is a source-evidence gap, not a request to
remove support in this audit.

### B-06 — `move` inventory prose conflicts with both validators

The `move` fixture's optional-field prose says “target ident or `-`.” Both
validators instead accept an omitted/empty target, literal `null` with final
`[notarget]`, or an `SOA` identifier; a literal `-` is rejected by the move
target validator. The source-coverage narrative likewise names omitted/empty
and `null`, not `-`.

Static reproduction path: `|move|p1a: Pikachu|Tackle|-` is rejected by both
runtime validators. This is shared inventory metadata drift, not a runtime
parity defect.

### B-07 — Stream visibility is not encoded for generic diagnostics

`error` has no player/side field despite being described as a private choice or
stream error. Its safe visibility therefore depends on upstream stream routing,
not record grammar. The shared contract correctly keeps it raw-only, but lacks
field-level evidence that a private error cannot enter the shared spectator
prefix. Keep this as a source-routing/privacy review input rather than infer a
public audience from the token.

### B-08 — Python accepts noncanonical retained request records and does not bind their `rqid`

TypeScript consumer validation requires a retained request record to equal the
canonical serialization of its object (`observable_state.ts:1145-1183`), and
when a request is available it checks the raw `rqid` against it. Python
`pipeline_record._prefix` only parses JSON and restricts keys to `rqid`
(`pipeline_record.py:136-146`); `ts_identity.py` verifies the rehashed literal
prefix but has no request-prefix-to-request-object join.

Static reproduction path using the existing Python fixture helper:
`_rehashed_protocol_candidate(_bundle(), "input", '|request|{ "rqid": 12 }')`
updates both prefixes and all content identities. Python's structural request
check accepts the whitespace spelling, while TypeScript
`validateObservableProtocolPrefix` rejects it because its canonical form is
`|request|{"rqid":12}`. Replacing `12` with a different safe integer also lacks a
Python request-object cross-check after rehashing.

**Follow-up classification:** TypeScript/Python publication-parity repair and
rehashed regression; no request-schema expansion or data publication is
authorized here.

## Precise Input for SLICE-002A Scanner Expansion

The scanner must produce source-location, value, emission-template, visibility,
and disposition rows for the following concrete inputs, then reconcile them to
the G18/G34/G40 and generic-tag rules above:

1. Resolved Gen 9 `Move.condition`, `Move.slotCondition`,
   `Move.self.volatileStatus`, nested self/hit/secondary effect records, and
   callback-created/dynamic `addVolatile` arguments in
   `data/moves.ts` and relevant `sim` callbacks.
2. Resolved `Ability.condition` and `Item.condition` hooks plus nested callback
   effects in `data/abilities.ts` and `data/items.ts`.
3. Literal and computed protocol emitters from `Battle.add`, `addSplit`,
   `addMove`, `BattleActions`, `Pokemon`, `Side`, and `Field`, including the
   optional tag order and source/target role for each generated template.
4. Every value that reaches typed fields through `-start`, `-end`, `-weather`,
   `-fieldstart`, `-fieldend`, `-sidestart`, and `-sideend`; classify it as
   typed with lifecycle evidence, validated raw-only, or explicit stop.
5. Operative `gen9randombattle` format/configuration provenance and direct versus
   indirect reachability. Do not promote package-wide emitter presence or a
   random-set candidate to reachability proof.

The scanner output must make B-03 values fail closed when unclassified and
resolve B-04's field ordering/dependency rules. It should also provide the
source evidence needed to close B-05/B-07 or explicitly keep those records
raw-only/stream-scoped.

## Boundary Conclusion

The shared contract has a complete token inventory and both runtime loaders
enforce the same asset, core identifier grammar, request `rqid` rules,
recognized-stop list, and fixture/rejection matrix. Defined request, tier, and
`|` filtering is validation-first in both the direct projection/publication
paths. The audit does **not** establish complete effect-value, tag-order,
source-routing, reachability, or faithful-episode closure.

The concrete exceptions B-01 through B-08 remain follow-ups. In particular,
keep `-singleturn` raw-only, keep `-singlemove` as an explicit unsupported
stop, and retain `faithful_complete_episode:false`.
