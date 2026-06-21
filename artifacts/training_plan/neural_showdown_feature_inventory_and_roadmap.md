# Neural Showdown Feature Inventory and Implementation Roadmap

## Executive summary

This audit covers the current Gen 9 Random Battles target at checkpoint
`932ab6fce1d0433f75114bbe6142644b64d034aa`. It distinguishes four layers that
are easy to conflate:

1. Pokémon Showdown may resolve a mechanic correctly inside sim-core.
2. The replay/live state adapters may reconstruct the public or own-private
   information needed by that mechanic.
3. The neural state/action schemas may expose that information to a model.
4. A rollout or search path may branch on the mechanic rather than merely
   summarize it.

The project has a mature frozen v7 representation, an audited append-only v8
state belief slice, a source-neutral per-Pokémon posterior contract, a
public-prefix replay adapter, strong data-label quarantine policies, and a
tested but non-production bounded branch-search research layer. The largest
near-term representation gap is candidate-specific use of opponent uncertainty:
`legal-action-v7` exposes extensive mechanics, timing, stochastic, forced-switch,
and known-context fields, but it does not expose explicit posterior risk for
possible Unaware, Magic Bounce, Good as Gold, Levitate, Covert Cloak, Shield
Dust, Inner Focus, or similar candidate-sensitive threats.

The immediate next task should therefore be the design—not implementation or
training—of an append-only `legal-action-v8` belief-risk slice. It should consume
the existing `OpponentSetBelief`, preserve known-versus-possible provenance, and
remain separate from exact rollout truth. Do not train v8 yet. Do not run a
1,000-battle v8/v7 state-only materialization without a specific scale question.

Team archetype inference and role-completion priors are not missing current
Randbats requirements. They belong to future constructed/team-preview formats,
where Smogon usage, co-usage, and team-builder statistics may back separate
`MetaPriorSource` and `TeamPriorSource` implementations.

## Audit scope and status labels

Twelve major feature areas were audited. Status labels mean:

- `implemented`: code exists and is usable in its stated scope.
- `implemented and audited`: code exists with focused tests and/or artifact
  evidence.
- `implemented but coarse`: model-facing support exists but is approximate,
  compressed, uncalibrated, or incomplete.
- `partially implemented`: some required layers exist, but important neural,
  provenance, rollout, or integration pieces do not.
- `planned`: a concrete design exists but implementation is absent.
- `blocked`: intentionally gated by unresolved prerequisites.
- `future constructed-format work`: explicitly outside current Randbats scope.
- `not implemented`: inspection found no implementation.
- `unknown / needs deeper inspection`: evidence was insufficient for a reliable
  classification.

## Current status table

| Major area | Current status | Bottom line |
| --- | --- | --- |
| 1. Core schemas and materialization | implemented and audited | v7 state/action are frozen; v8 state is append-only and passed tiny plus 300-battle audits. |
| 2. Opponent belief / hidden-state system | implemented and audited | Source-neutral immutable per-Pokémon posterior, evidence ledger, tail, contradiction, and provenance are tested. |
| 3. Randbats meta-prior source | implemented but coarse | Pinned role/movepool source has full audited species coverage but no items, exact four-move sets, or calibrated frequencies. |
| 4. Public-prefix replay belief adapter | implemented and audited | Causal move/ability/item/Tera extraction, Illusion segments, copied-state semantics, and reflection attribution are tested. |
| 5. Illusion / Zoroark data policy | implemented and audited | Safe actor-private reconstruction is used when self-confirming; unresolved ambiguity is quarantined. |
| 6. Action/candidate features | implemented but coarse | v7 is extensive and audited; posterior-conditioned candidate/action v8 remains planned. |
| 7. Mechanics and statefulness exposure | partially implemented | Many mechanics are represented or fail closed, but simulator support is broader than neural exposure. |
| 8. High-variance / stochastic moves | implemented but coarse | v7 provides probabilities/distributions and explicit unknowns; exact stochastic branching is limited. |
| 9. Evaluation and training | implemented and audited | v7 diagnostic training/evaluation passed; all checkpoints remain non-production and unpromoted; v8 is untrained. |
| 10. Search / “Pokémon Stockfish” layer | partially implemented | Real seeded one-turn/two-ply/belief-particle research search exists, but is slow, weak under beliefs, and disabled live. |
| 11. Randbats non-goals / constructed formats | future constructed-format work | Team-building archetypes and role completion are deliberately excluded from current Randbats. |
| 12. Roadmap | planned | Design `legal-action-v8` belief-risk features next; keep training and constructed-format work separately gated. |

## Feature audit

### 1. Core schemas and materialization

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| `live-private-belief-v7` | implemented and audited | `trainer/src/neural/live_private_features.py` | `test_live_private_features_v7.py`; materialization/training reports | Frozen 3208D representation; does not contain the v8 posterior summary. | Preserve unchanged. |
| v7 state identity | implemented and audited | `FEATURE_NAMES_V7`, `FEATURE_DIM_V7` | Frozen tests and dataset metadata | 3208D; fingerprint `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`. | Keep as compatibility prefix. |
| `legal-action-v7` | implemented and audited | `trainer/src/neural/action_features.py` | v7 batch tests; 300/1,000 dataset and training reports | Frozen 552D schema; possible-threat identity support remains incomplete. | Preserve unchanged while designing v8. |
| v7 action identity | implemented and audited | `ACTION_FEATURE_NAMES_V7`, `ACTION_FEATURE_DIM_V7` | Schema/fingerprint guards | 552D; fingerprint `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`. | Keep as v8 prefix if action v8 is append-only. |
| `live-private-belief-v8` | implemented and audited | `live_private_features.py`, `v8_belief_features.py` | `test_v8_belief_feature_slice.py`; v8 reports | Adds only active-opponent belief summary/provenance, not candidate risk. | Use as state side of future v8/v8 design. |
| v8 state identity | implemented and audited | `FEATURE_NAMES_V8`, schema export | Tiny and 300 materialization reports | 3229D; fingerprint `8ac514415b0e35014b5fc741d54cd79599175c039bdbda0cf2309d5d4ef26053`. | Freeze unless an explicitly new state version is needed. |
| v8 append-only relationship | implemented and audited | v8 concatenation branch | Prefix assertions and 19 materialization checks | v8 adds 21 fields only. | Retain append-only contract. |
| v7 prefix preservation in v8 | implemented and audited | `FEATURE_NAMES_V8[:3208]` | Tiny/300 audits | Names/order are verified; v8 adds no action schema. | Continue exact fingerprint checks. |
| Feature schema export | implemented and audited | `feature_schema()`, `action_feature_schema()` | Schema-export and materializer tests | Live defaults intentionally remain v2/v3. | Add action-v8 export only after schema design. |
| Tiny v8/v7 smoke | implemented and audited | `benchmark_vnext_featuregen.py` | `v8_v7_belief_slice_materialization_smoke_report.md` | 10 battles only; explicit-unknown path absent in this subset. | Superseded by 300-battle audit. |
| 300-battle v8/v7 materialization | implemented and audited | generated diagnostic artifact | materialization and quality reports | 299/300 valid; one frozen-manifest 24-vs-24 replay is incompatible with six slots. | No rerun unless schema/source changes. |
| Validation checks | implemented and audited | `validate_benchmark_arrays` | All 19 checks passed | Structural checks do not establish policy quality. | Reuse for future v8/v8 materialization. |
| Old dataset hash preservation | implemented and audited | audit-side SHA-256 comparison | 300 quality audit | Covers 11 pre-existing NPZ files at audit time. | Repeat before future rematerializations. |
| Candidate/action v8 schema | planned | v8 design and threat-awareness audit | No implementation tests | No `legal-action-v8` exists. | Design next; do not silently mutate v7. |

### 2. Opponent belief / hidden-state system

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| `MetaPriorSource` | implemented and audited | `trainer/src/neural/meta_prior.py` | `test_meta_prior_belief_contracts.py` | Randbats and fixture implementations exist; Smogon/replay sources do not. | Keep interface source-neutral. |
| `SetPrior` | implemented and audited | `meta_prior.py` | Contract and Randbats-source tests | Probabilities are only as good as the source; current Randbats values are uncalibrated. | Preserve quality/tail metadata. |
| `SetHypothesis` | implemented and audited | `meta_prior.py` | Contract/fidelity tests | Current source has role movepool support, not exact generated movesets. | Generator snapshot is the calibration route. |
| `OpponentSetBelief` | implemented and audited | `opponent_set_belief.py` | Contract, adapter, fidelity, and v8 feature tests | Per-Pokémon only; no team-level posterior. | Feed candidate-sensitive summaries into action v8. |
| Immutable public evidence ledger | implemented and audited | `PublicEvidence`, `EvidenceLedgerEntry` | Prefix-causality tests/audit | Four evidence kinds only; probabilistic damage/speed inference intentionally excluded. | Add new evidence only with leakage proofs. |
| Confirmed facts | implemented and audited | `ConfirmedFacts` | Contract and replay adapter tests | Current-state-only copied facts stay ledger-only by design. | Keep base facts separate from transient state. |
| Ruled-out facts | implemented and audited | `RuledOutFacts` | Contract/fidelity tests | Coarse source support can rule out only declared hypotheses. | Expose only compact summaries unless action-specific identity matters. |
| Possible abilities | implemented and audited | `possible_abilities` | Joint-fidelity and v8 slice tests | Current probabilities are factorized/equal-weight approximations. | Candidate-v8 should distinguish known/inferred/possible. |
| Possible moves | implemented but coarse | `possible_moves` | Fidelity/public-prefix audits | Movepools are 5–7 move support supersets, not exact four-move combinations. | Do not treat as exact rollout moves. |
| Possible Tera types | implemented but coarse | `possible_tera_types` | Fidelity/public-prefix audits | Role declarations lack empirical probabilities. | Use probability-available/quality flags. |
| Item evidence | implemented and audited | `ITEM_REVEALED`, adapter extraction | Source-absent tests; 2,207-item audit | Items are confirmed public facts but absent from current prior hypotheses. | Generator snapshot should add item distributions. |
| Source-covered vs source-absent evidence | implemented and audited | `_dimension_covered`, `source_covered` | Public-prefix audit | Source-absent facts do not update unrelated posterior dimensions. | Preserve this fail-honest behavior. |
| Source-quality flags | implemented and audited | `prior_joint_quality`, warnings, v8 features | v8 provenance regression and 300 audit | Four v8 flags summarize, but do not calibrate, source quality. | Include action-v8 availability/quality flags. |
| Unknown tail mass | implemented and audited | `other_mass` | Contract, fidelity, and v8 audits | Fixed 0.5 initial policy is unvalidated; tail frequently dominates. | Replace with sampled calibration later. |
| Prior contradiction handling | implemented and audited | `prior_contradiction`, tail-only fallback | Contract/public-prefix audits | Repeated rows can expose the same genuine source mismatch. | Keep visible; do not restore contradicted hypotheses. |
| Alias provenance | implemented and audited | `prior_source_key`, alias policy version | Source and public-prefix tests | Conservative explicit list/cosmetic-prefix policy only. | Extend only for demonstrated public-form gaps. |
| Current-state-only evidence | implemented and audited | copied/forme markers in belief + adapter | Adapter and public-prefix audits | Recorded but not used to filter base sets. | Candidate-v8 may use transient known facts separately. |
| Hidden-truth invariance | implemented and audited | APIs exclude hidden truth; perturbation fixtures | 300/300 public-prefix checks | Search belief sampler is a separate implementation path. | Require the same invariant for action-v8. |
| Prefix causality | implemented and audited | immutable updates; exclusive-line/inclusive-turn adapter | 300/300 checks | Replay actor-private reconstruction has a separate own-side future-public assumption. | Keep opponent belief strictly prefix-only. |

### 3. Randbats meta-prior source

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Checked-in `sets.json` | implemented and audited | `data/random-battles/gen9/sets.json` | Source/fidelity audits | 508 species/forms, 877 role declarations; not generated sets. | Keep pinned and immutable for current diagnostics. |
| Source checksum/provenance | implemented and audited | `RandbatsMetaPriorSource.metadata` | SHA-256 audit | SHA-256 `7dc75740d17755d921c473fca68b3022f6f37a2af387d3cd9c94432bd646eaef`; generated timestamp unavailable. | Record generator identity in future snapshot. |
| `randbats_meta_prior_source.py` | implemented and audited | pinned adapter | Source and fidelity tests | `source_kind` uses generator vocabulary although the artifact is role data; warnings make the approximation explicit. | Avoid claiming sampled calibration. |
| `load_randbats_index` older path | implemented but coarse | `live_opponent_beliefs.py` | Existing opponent-belief tests/design audit | Emits top candidates and marginals; downstream top-marginal shortcuts can fabricate pseudo-sets. | Prefer `OpponentSetBelief` for new work. |
| Species/form coverage | implemented and audited | alias policy + source | Public-prefix audit | 1,600/1,600 slots and 487/487 unique public forms covered in held-out audit. | Monitor new Showdown data/forms. |
| Role/set hypotheses | implemented but coarse | role-bundled hypotheses | Joint-set fidelity audit | Preserves role↔movepool↔ability↔Tera correlation present in source. | Keep role bundle; calibrate by generator sampling later. |
| Abilities | implemented but coarse | role declarations | 299/301 held-out reveals supported | Two genuine source gaps: Leavanny Pickpocket, Beartic Dry Skin. | Keep contradictions visible; fix source only through pinned update. |
| Movepools | implemented but coarse | role declarations | 3,059/3,059 held-out move reveals supported | Support supersets, no exact four-move combinations or frequencies. | Generator-sampled joint snapshot. |
| Tera types | implemented but coarse | role declarations | 214/214 held-out reveals supported | Alternatives are uniformly weighted. | Generator-sampled probabilities. |
| Items | not implemented | absent from `sets.json`; hypotheses use `item=None` | Source/fidelity/public-prefix audits | Public item evidence is tracked but no prior item probability exists. | Add through generator snapshot, not guesses. |
| Exact four-move sets | not implemented | absent from source | Joint-set fidelity audit | Cannot recover combo/incompatibility rules statically. | Sample the pinned Showdown generator. |
| Empirical probabilities/frequencies | not implemented | source has no weights | Fidelity/calibration audits | Equal role and alternative weighting; fixed tail. | Build convergence-tested sampled snapshot. |
| EV/stat/item distributions | not implemented | absent from current prior source | Design and source audit | Exact own/public stats can still reach damage paths separately. | Add only in sampled prior metadata/hypotheses if needed. |
| Calibrated generator snapshot | planned | v8 design §4 | No artifact or builder yet | Sampling, convergence, version pinning, and checksum policy remain unimplemented. | Medium-term after action-v8 design or when calibration becomes the blocker. |

### 4. Public-prefix replay belief adapter

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Replay-prefix extraction | implemented and audited | `opponent_set_belief_replay_adapter.py` | Adapter tests | Diagnostic replay path; live packets use different extraction entrypoints. | Preserve shared evidence semantics. |
| Move reveals | implemented and audited | `_line_evidence` | Adapter/public-prefix tests | Reflected moves are deliberately excluded as actor choices. | No change. |
| Ability reveals | implemented and audited | `-ability`, named `[from] ability` | Adapter/audit tests | Generic unexplained immunity is ignored. | Add only explicit attribution rules. |
| Item reveals | implemented and audited | `-item`, `-enditem`, named item | Adapter/public-prefix audit | Source has no item hypotheses. | Continue confirming as source-absent. |
| Tera reveals | implemented and audited | `-terastallize` | Adapter tests/audit | No probabilistic inference from unrevealed Tera behavior. | No change. |
| Magic Bounce/reflection attribution | implemented and audited | named ability ownership logic | Reflection tests and recomputation script | Exact rollout still requires complete routing provenance. | Candidate-v8 should expose possible reflection risk. |
| Poltergeist item evidence | implemented and audited | `-activate ... move: Poltergeist` | Adapter tests | Only explicit displayed item is accepted. | No change. |
| Named immunity/prevention evidence | implemented and audited | named `[from] ability/item` handling | Generic-vs-named immunity tests | Generic `-immune` remains non-evidence. | Preserve fail-closed rule. |
| Illusion segment handling | implemented and audited | `replace` creates a new segment | Adapter and causality tests | Earlier disguise segment is not retrospectively rewritten. | Keep separate from actor-private label reconstruction. |
| Trace handling | implemented and audited | base Trace + copied ability current-state-only | Adapter/public-prefix audit | Copied displayed ability is not a base-set fact. | Candidate-v8 can use transient known ability safely. |
| Transform/Imposter handling | implemented and audited | transformed slot tracking | Adapter and reconstruction reports/tests | Replay own-side copied moves require separate reconstruction logic. | Preserve per-stint boundaries. |
| Ditto copied moves | implemented and audited | current-stint reconstruction | Transform/re-transform reports | Only current stint is reconstructed; no global Ditto moveset backfill. | No change. |
| Struggle/universal noise | implemented and audited | universal-noise marker + exhaustion candidate | Ditto report/tests | Not treated as a base set move. | No change. |
| Future-reveal isolation | implemented and audited | truncation APIs | Adapter/v8 no-leakage tests | Own-side replay reconstruction intentionally differs from opponent belief. | Keep boundary documented. |
| Hidden-truth perturbation | implemented and audited | public-only adapter inputs | 300/300 audit checks | Does not prove every future evidence extension is safe. | Extend tests with new evidence kinds. |

### 5. Illusion / Zoroark data policy

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Zoroark reveal reconstruction | implemented and audited | replay parser/private-state reconstruction | Illusion report/tests | Requires a self-confirming `replace` within the active stint. | Keep conservative. |
| Actor-private Illusion reconstruction | implemented and audited | `build_live_private_value_dataset.py` | Six audited residual fixes | Uses information the acting player knew about its own side. | No expansion without equally strong ownership proof. |
| Ambiguous Illusion quarantine | implemented and audited | matcher skip policy | 300 v8/v7 quality audit | Three non-self-confirming rows remain unmatched. | Continue explicit quarantine. |
| Known diagnostic unmatched labels | implemented and audited | decision skip audits | 25,017/25,020 v8/v7; residual harness | Three rows: two in `2593348981`, one in `2593283718`. | Track as known floor. |
| Impossible visible-species actions | implemented and audited | label matcher refuses absent move candidates | Illusion reports | They are not trained as clean labels. | Preserve “skip over corruption” policy. |
| Prefix salvage | partially implemented | safe self-confirming stint reconstruction | Illusion report | Salvages resolvable own-side stints, not arbitrary ambiguous prefixes. | Optional only if data loss becomes material. |
| Whole-replay discard | not implemented | per-decision matcher/quarantine | Dataset audits | Good decisions from the same replay remain usable. | Keep segment/row-level policy. |
| Segment/decision quarantine | implemented and audited | unmatched decision exclusion | Materialization reports | Current unit is effectively the decision row; ambiguity metadata is report-oriented. | Keep explicit category reporting. |
| Unresolved ambiguity tracking | implemented and audited | skip reason/category reports | Residual recomputation | No model-facing “post-action impossible disguise” feature. | Consider only in future public-belief/action-v8 work. |

Current policy is correct for supervised data quality: avoid corrupted labels
even if that sacrifices a tiny amount of Zoroark-specific data. Unresolved
ambiguity must be skipped; an apparent Avalugg using Will-O-Wisp is not a clean
“Avalugg action” label. Additional prefix salvage is optional future work, not a
current blocker.

### 6. Action/candidate features

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Action legality | implemented and audited | sim-core requests + candidate builders | featuregen/action-label tests | Replay reconstruction can only approximate original private requests. | Keep strict matching and skips. |
| Candidate matching | implemented and audited | `vnext_labels.py`, featuregen | post-Ditto/Magic-Bounce/Illusion audits | Three irreducible Illusion rows remain. | No matcher guessing. |
| Rank labels | implemented and audited | one-hot observed action groups | materialization/training tests | Imitation labels encode replay judgment, not optimality. | Use for rank-only diagnostics. |
| Action-value labels | not implemented | materializer records `not_generated` and zero labels | Validation checks | Separate builders/prototypes exist, but vNext diagnostic artifacts contain none. | Keep separate until target quality is approved. |
| Rank-only candidate training | implemented and audited | `train_vnext_diagnostic.py` | 1,000-battle report/evaluator | Non-production imitation baseline only. | No promotion. |
| Mechanics versus judgment | implemented but coarse | typed effects, impact, risk, labels | Mechanics and offline reports | Features encode mechanics/provenance; replay labels provide human/player judgment. The schema does not hardcode “best move.” | Preserve separation. |
| Batch 7 risk/probability | implemented and audited | 59-field slice in `action_features.py` | batch-7 report/tests | Probabilities use known/static/weather context; many hidden modifiers remain unknown. | Reuse as v8 prefix. |
| Batch 8 forced decisions/secondary/item triggers | implemented and audited | 41-field slice | batch-8 tests; 300 activity audit | Some `*_possible` names actually require a concrete known item/ability. | Correct semantics in a new v8 slice, not v7. |
| Known/possible absorb risk | implemented but coarse | tactical `target_known_or_possible_ability_absorbs_move_type` | threat-awareness audit | Known and possible are conflated; limited ability families. | Split provenance in action v8. |
| Possible Unaware/Haze/phazing sensitivity | planned | v8 design/threat audit | No schema tests | Phazing move pressure exists, but posterior answer-to-setup risk does not. | Design candidate applicability + posterior probability. |
| Status prevention/reflection risk | planned | v8 design | Known-context contracts exist | No candidate-conditioned posterior Magic Bounce/Good as Gold probability. | Core action-v8 field group. |
| Contact punish risk | planned | v8 design concept | No implementation | Contact-per-hit exists; posterior Rough Skin/Static/etc. risk does not. | Define bounded mechanic families. |
| Immunity/absorb risk | partially implemented | known/possible absorb bit, exact impact fields | threat audit | Levitate and known-vs-possible provenance incomplete. | Expand in action v8. |
| Current-state-only copied facts in candidate risk | planned | belief ledger already records them | No action-v8 tests | State slice summarizes count only. | Candidate v8 should prioritize confirmed transient facts over base prior. |
| Source-quality/provenance on candidate risk | planned | v8 state flags/design | No action-v8 schema | State quality exists but action candidate does not receive probability availability. | Include availability/quality bits. |
| Preserving matchup-critical Pokémon | planned | search/design discussions | No dedicated action feature | Switch target HP/species/known state exist, but no posterior matchup-preservation value. | Treat as learned/search signal, not hardcoded strategy. |
| Information-gain/scouting features | planned | v8 design/search separation | No implementation | No expected information gain calculation. | Medium-term after basic threat slice. |
| High-variance move risk | implemented but coarse | batch-7 accuracy/crit/random-call/multihit fields | batch-7 tests | Descriptive distributions; no utility/risk preference is hardcoded. | Keep model judgment separate. |

### 7. Mechanics and statefulness exposure

The table below explicitly separates Showdown execution from neural exposure.
“Impact” refers to resolved candidate-impact plumbing, not a full future-state
search.

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Choice lock | implemented and audited | sim-core legality; state `own_choice_lock_inferred`; action lock compatibility | v7 state/action tests | Opponent Choice inference is limited to public evidence; no posterior item prior. | Add item prior only through calibrated source. |
| Encore | implemented and audited | sim-core; own/opponent state; candidate compatibility/effect | state/action tests | Duration precision is limited by public reconstruction. | Preserve provenance. |
| Disable | implemented and audited | request disabled slots; own/opponent state; action effect | state/action tests | Public opponent disabled-slot reconstruction can be incomplete. | No immediate change. |
| Torment | partially implemented | sim-core; own/opponent state flags | v7 state features | No dedicated action applicability field. | Add only if offline errors justify it. |
| Recharge | implemented and audited | sim-core; own recharge/must-recharge state; action timing | timing tests | Old-generation quirks intentionally excluded. | No Gen 9 action. |
| Substitute | implemented and audited | sim-core; both-side state; action volatile and phazing interaction | volatile/batch-8/parity tests | Broad move-by-move substitute callback coverage remains simulator/search responsibility. | Keep exact branch handling in sim-core. |
| Protect success decay | partially implemented | Showdown sim resolves; protect identity and recent protected events exist | edge-case audit plan | No explicit consecutive Protect/Stall counter or success probability in v7. | Future state/provenance design if empirically important. |
| Rest sleep versus ordinary sleep | partially implemented | provenance contract exists; public sleep turns in state | uncertainty audit; provenance tests | Frozen v7 does not expose Rest-vs-natural provenance/range as dedicated fields; rollout fixture absent. | Future state schema, separate from action v8. |
| Ordinary sleep duration uncertainty | partially implemented | public elapsed-turn features; `natural_sleep_provenance` contract | no-leakage tests | Hidden sampled wake turn correctly not exposed; legal remaining range not wired into v7 vector. | Future append-only state slice. |
| Rage Fist hit counter | implemented and audited | tactical per-species counter; damage payload | dynamic mechanics audit/tests | Counter is used for impact but not a dedicated vector field. | No immediate schema change. |
| Last Respects faint count | implemented and audited | roster/faint state; `allies_fainted` impact | dynamic mechanics audit/tests | Depends on complete history for exact impact. | Keep fail-closed when incomplete. |
| Supreme Overlord faint count | partially implemented | Showdown/calc can use ability and allied faint context; state has faint counts | no dedicated focused report | No explicit selected multiplier/provenance field was found. | Add focused audit before schema work. |
| Stored Power / Power Trip | implemented and audited | state boost stages; calc impact | dynamic mechanics audit/tests | No named action feature; resolved damage carries the effect. | No immediate change. |
| Population Bomb stop-after-miss | implemented but coarse | Showdown sim; batch-7 sequential summary; exact fixture trace path | batch-7 and rollout parity reports | Exact local transition needs a complete per-hit trace; summary-only remains GAP. | Do not treat expected hits as an exact branch. |
| Electro Ball / Gyro Ball speed relation | implemented and audited | variable-power impact route using current stats/context | dynamic/completeness tests | Neural schema exposes result/impact, not an explicit speed-ratio field. | Keep impact provenance. |
| Heavy Slam / Low Kick weight relation | implemented and audited | variable-power impact route | dynamic/completeness tests | Requires reliable species/form weights; no explicit weight feature. | Keep fail-closed for missing context. |
| Protosynthesis / Quark Drive selected stat | partially implemented | Showdown sim handles; ability identity, boosts, weather/terrain state exist | limited parity/source tests | No explicit selected-stat activation field was found in v7. | Focused exposure audit before adding fields. |
| Weather/terrain duration | implemented and audited | v7 state public-known flags and normalized turns | v6 state tests | Unknown duration remains explicit; exact extension items/abilities may be absent. | Preserve known/unknown provenance. |
| Tera type interactions | implemented and audited | base/current/Tera types in state; 64 Tera action fields; impact | state/action/materialization tests | Posterior alternative-Tera candidate risk is not explicit. | Add possible-Tera interaction probabilities in action v8. |
| Transform/Imposter copied state | implemented and audited | sim-core; state transformed flags; replay stint reconstruction; belief current-state-only | Transform/Ditto reports/tests | Exact copied move request is own-private; opponent belief must remain public-only. | Preserve separation. |
| Illusion identity uncertainty | implemented and audited | displayed/current/base species and Illusion guards; segment policy | Illusion and no-leakage tests | Three replay labels remain irreducibly ambiguous. | Continue quarantine. |

### 8. High-variance and stochastic moves

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Metronome | implemented but coarse | batch-7 callable-pool summary | action-risk report/tests | No sampled called move or exact expected utility. | Keep format-scoped and fail closed. |
| Assist | planned | party/format dependency flags | inventory report | Not a current Gen 9 Randbats requirement; no party callable-pool implementation. | Defer to NatDex/constructed format adapter. |
| Sleep Talk | implemented but coarse | callable pool from known current moves | batch-7 tests/inventory | Depends on sleep provenance; no sampled call. | Improve state sleep provenance later. |
| Ordinary multi-hit moves | implemented but coarse | 2–5 distribution, Loaded Dice, Skill Link | batch-7 tests | Candidate feature is distributional; local exact transition is not generally branched per hit. | Add exact branching only where search requires it. |
| Sequential multi-hit | partially implemented | Population Bomb/Triple Axel summaries and fixture-only traces | rollout parity batch 8 | Exact transition requires oracle trace; live PRNG branching absent. | Keep explicit GAP without trace. |
| OHKO moves | not implemented | Showdown sim supports them | no focused neural audit found | Generic accuracy fields may exist, but no reliable OHKO damage/branch representation was found. | Add focused audit before claiming coverage. |
| Accuracy | implemented and audited | base/weather hit chance, miss chance, context quality | batch-7 tests | Full ability/item/evasion provenance is incomplete. | Extend only with public/known modifiers. |
| Crits | implemented but coarse | ordinary/high/guaranteed crit fields; calc rolls | batch-7 and mechanics tests | Candidate features summarize chance; search does not enumerate crit outcomes generally. | Keep probabilistic summary. |
| Secondary effects | implemented and audited | typed status/stat/volatile effects and batch-8 modified chance | v7 batch tests | Hidden possible blockers are not posterior-conditioned; rollout lacks generic secondary application. | Action-v8 blocker risk first. |
| Damage-roll distributions | implemented but coarse | sim-core returns rolls; action stores min/max/expected/uncertainty/KO | damage/action tests | Full distribution is compressed into summary fields. | Keep compact unless search needs branch quantiles. |
| RNG outcome branching | partially implemented | deterministic seeded sim branches; exact fixture traces | branch and parity tests | Live seed unavailable; no general chance-node expansion. | Research-only future work. |
| Branch explosion controls | implemented and audited | root/opponent/follow-up caps, deadlines, particle caps | one-turn/two-ply/particle reports | Bounds trade completeness for latency; tail latency remains high. | Keep opt-in and report caps/timeouts. |

### 9. Evaluation and training status

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| v7/v7 smoke training | implemented and audited | post-Ditto config/artifacts | smoke report | Plumbing success only; weak value metrics. | No promotion. |
| v7/v7 1,000-battle rank-only diagnostic | implemented and audited | post-Magic-Bounce run | training report | Imitation baseline, 80,594 matched groups; 41 quarantined Illusion rows. | Use as frozen offline baseline. |
| Offline evaluator | implemented and audited | `evaluate_vnext_action_rank.py`, strict loader | offline evaluation report | Evaluates precomputed held-out candidates, not live battle control. | Reuse for future schema comparisons. |
| Rank-only metrics | implemented and audited | selected epoch 7 | training/offline reports | Test NLL/top-1/top-3/MRR `1.181397 / 0.507626 / 0.886274 / 0.700131`. | Compare v8 against same held-out methodology. |
| Baseline comparison | implemented and audited | offline evaluator | offline report | Model beats max expected damage, but weak switch/Tera/prevention slices remain. | Use slices as v8 acceptance tests. |
| Production eligibility | blocked | checkpoint metadata | reports and strict loader | `production_eligible: false`; live parity/threat gates open. | Keep blocked. |
| Checkpoint promotion | blocked | no promoted checkpoint | gate docs | Diagnostic files exist only as unstaged/non-production artifacts. | Separate explicit approval required. |
| Live/default status | implemented and audited | defaults in source are v2/v3; vNext flag default off | inference/shadow tests | Opt-in dry-run exists but does not change default choice path. | Keep stable. |
| v8 training | not implemented | no v8 config/checkpoint | gate and v8 reports | v8 state has only been materialized/audited. | Do not train before action-v8 design and rematerialization gate. |

### 10. Search / “Pokémon Stockfish” layer

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Sim-core branch evaluation | implemented and audited | `one_turn_branch.py` | one-turn tests/report | Seeded replay branches can use exact hidden opponent state; slow. | Keep research-only. |
| State transition tooling | implemented and audited | sim-core env replay/snapshot/fork, parity helpers | branch/parity tests | No general live mid-battle chance-tree API. | Preserve isolated env semantics. |
| Expected/risk-adjusted evaluation | implemented but coarse | mean/worst/best/std and `mean - lambda*std` | branch tests/reports | Leaf score quality dominates results. | Treat as diagnostic controls. |
| Two-ply opponent-action modeling | implemented and audited | `two_ply_branch.py` | two-ply tests/report | Bounded heuristic ordering, not equilibrium search. | Keep exact mode as upper bound. |
| Hidden-world sampling | implemented and audited | `sim-core/src/belief_fork.ts`, belief particles | belief tests/reports | Runtime sampler is separate from `OpponentSetBelief`; fallback can relax impossible generated constraints. | Calibrate/weight samples before scaling. |
| Belief-particle aggregation | implemented and audited | `evaluate_belief_particle_branches` | particle tests/report | Three particles stayed at 30% and tripled latency. | Do not increase particle count blindly. |
| RNG outcome branching | partially implemented | seeded Showdown transitions and trace fixtures | parity/branch reports | No live seed and no explicit general chance nodes. | Long-term research. |
| Risk profile diagnostics | implemented and audited | branch score spread, particle disagreement, caps/errors | branch reports | Diagnostic only; not model-facing/live. | Retain for experiments. |
| Information gain | not implemented | none found | none | Search scores outcomes, not expected belief reduction. | Medium-term after calibrated beliefs. |
| Top punish branch | partially implemented | worst/best branch rows and bounded opponent replies | branch reports | No dedicated “top punish” semantic or adversarial exhaustive opponent policy. | Could derive from worst branch in future diagnostics. |
| Live search integration | blocked | `action_trace.py` marks branch scorers unavailable live | live trace/inference docs | Live battles lack seed/exact hidden reconstruction; latency is too high. | Do not enable. |

The strongest exact-seeded two-ply research result was 60% against the paired
heuristic reference, but it was an optimistic hidden-information upper bound.
Public-information belief search fell to 30%; three particles remained 30% at
roughly 3.2× latency. This is useful search research infrastructure, not a
production “Pokémon Stockfish.”

### 11. Current Randbats non-goals and future constructed-format work

| Feature area | Status | Evidence/files | Tests/reports | Limitations | Next action |
| ------------ | ------ | -------------- | ------------- | ----------- | ----------- |
| Randbats team-builder archetype inference | not implemented | explicitly excluded by scope | design/fidelity docs | Random teams are generated, not intentionally built around archetypes. | Keep out of current Randbats. |
| Randbats role-completion priors | not implemented | explicitly excluded by scope | design/fidelity docs | Do not assume every team supplies removal, speed control, or a defensive core. | Keep out of current Randbats. |
| Constructed team-preview archetypes | future constructed-format work | v8 design extension point | no implementation | Requires format/team-preview inputs. | Separate future design. |
| Constructed role-completion priors | future constructed-format work | proposed `TeamPriorSource` | no implementation | Must be conditioned on format and team evidence. | Separate source/interface. |
| Smogon usage priors | future constructed-format work | `SourceKind.SMOGON_USAGE` exists | no importer | Must pin month, format, rating, checksum, and factorization quality. | Future source implementation. |
| Smogon co-usage/team-builder priors | future constructed-format work | fidelity audit proposal | no implementation | Must not be folded into per-Pokémon Randbats prior. | Future `TeamPriorSource`. |
| Rating-conditioned priors | future constructed-format work | design metadata supports source identity | no implementation | Requires ladder/rating snapshot policy. | Future constructed-format program. |
| Rain/sun/stall/screens/webs/hazard-stack archetypes | future constructed-format work | conceptual design only | none | Invalid as assumed current Randbats team intent. | Evaluate only in constructed/team-preview formats. |

## Implemented and audited components

- Frozen v7 state/action schemas, strict dimensions, ordered names, and
  fingerprints.
- Append-only v8 state belief slice with preserved v7 prefix.
- Tiny and 300-battle v8/v7 materialization, structural validation, finite
  arrays, and old-dataset preservation.
- Source-neutral `MetaPriorSource`, joint hypotheses, immutable
  `OpponentSetBelief`, evidence ledger, confirmed/ruled-out facts, unknown tail,
  contradictions, alias provenance, and current-state-only evidence.
- Public-prefix replay adapter with causal move/ability/item/Tera evidence,
  Trace/Transform/Imposter semantics, Magic Bounce attribution, Poltergeist
  items, Illusion segments, and hidden-truth invariance.
- Safe Illusion/Transform label reconstruction and explicit quarantine.
- Extensive `legal-action-v7` mechanics, typed effects, impact, stochastic,
  forced-decision, phazing, pivot, sacrifice, and known-context fields.
- Non-production v7/v7 rank training and strict held-out evaluation.
- Deterministic rollout parity harness and opt-in one-turn/two-ply/belief-search
  research infrastructure.

## Implemented-but-coarse components

- Randbats role-data prior: full audited coverage, but no calibrated frequency,
  item, exact four-move, EV, or stat distribution.
- v8 belief state summary: useful provenance and entropy/count summaries, but no
  candidate-specific posterior interaction.
- v7 possible-threat awareness: explicit for selected absorb families and
  indirect through species/mechanics, incomplete for several high-impact
  abilities/items.
- Random-call, accuracy, crit, multi-hit, damage-roll, delayed, and residual
  features: descriptive summaries rather than a complete chance tree.
- Dynamic mechanics often reach resolved impact through exact context without a
  dedicated named model feature.
- Search beliefs: mechanically sanitized and tested, but poorly calibrated and
  not competitive with the heuristic baseline.

## Partial and planned components

- `legal-action-v8` candidate-specific belief-risk/provenance features.
- Possible Unaware, Magic Bounce, Good as Gold, Levitate, secondary-blocker, and
  contact-punish interaction probabilities.
- Candidate interaction with possible Tera and plausible coverage.
- Rest-versus-natural-sleep and ordinary sleep-range state provenance.
- Protect success-decay state.
- Focused Supreme Overlord and Protosynthesis/Quark selected-stat exposure.
- Exact live stochastic/chance-node branching, information gain, and calibrated
  hidden-world sampling.
- Generator-sampled, versioned, convergence-tested Randbats joint prior.

## Future constructed-format components

- Team-preview archetype inference.
- Role-completion/team-needs priors.
- Smogon monthly usage imports.
- Smogon co-usage and team-builder statistics.
- Rating-conditioned and date-effective priors.
- Rain, sun, stall, screens, webs, hazard-stack, balance, and defensive-core
  team-level inference.

These are not deficits in current Gen 9 Random Battles. They are separate future
format work.

## Known non-goals for current Randbats

- Do not infer that a generated opponent team was intentionally built around
  rain, sun, stall, screens, webs, hazards, Trick Room, or a defensive core.
- Do not infer a missing role merely because a constructed team “should” have
  hazard removal, speed control, recovery, or a revenge killer.
- Do not import Smogon constructed-format co-usage into the Randbats posterior.
- Do not convert possible hidden mechanics into exact simulator facts.
- Do not sample one hidden set and expose it as neural ground truth.
- Do not repair ambiguous Illusion labels by training impossible
  visible-species/action pairs.
- Do not change live defaults or promote diagnostic checkpoints based on
  offline rank metrics alone.

## Recommended next tasks

### 1. Immediate next design task

Design the append-only `legal-action-v8` belief-risk slice. The design should
specify exact names, ordering, applicability, probability source, known versus
inferred-public versus possible provenance, Illusion guards, suppression/bypass
behavior, and explicit unavailable/uncalibrated flags.

The first field families should cover:

- candidate applicability and belief availability;
- possible Unaware against setup/boost-dependent damage;
- possible Magic Bounce and Good as Gold against reflectable/status actions;
- possible Levitate and split known/possible absorb risk;
- possible Covert Cloak, Shield Dust, and Inner Focus against relevant
  secondaries;
- confirmed current-state copied facts;
- possible Tera resistance/immunity changes;
- plausible phazing/Haze/Encore answers to setup;
- source quality and unknown-tail provenance.

Do not encode strategic commands such as “do not set hazards.” Encode mechanics,
applicability, and uncertainty; let the ranker learn judgment.

### 2. Next materialization/training gate

Do not train v8 yet. After the action-v8 schema, tests, and no-leakage review are
approved:

1. run a tiny v8/v8 materialization smoke;
2. audit feature activity, known/possible separation, finite values, prefixes,
   labels, and fingerprints;
3. run a frozen 300-battle v8/v8 diagnostic materialization and read-only
   quality audit;
4. only then propose a separately approved rank-only v8 diagnostic.

A 1,000-battle v8-state/v7-action materialization is not the default next step.
Run it only to answer a specific scale/coverage question that the 300 audit
cannot answer.

### 3. Medium-term feature work

- Build the pinned generator-sampled Randbats prior with convergence and
  calibration reports.
- Add Rest/natural-sleep provenance and other high-value public counters in a
  separate append-only state version if offline slices justify them.
- Audit Supreme Overlord and Protosynthesis/Quark selected-stat exposure.
- Calibrate belief-search particles using public evidence before increasing
  particle count.
- Add information-gain and top-punish diagnostics only after belief calibration.

### 4. Long-term constructed-format work

Create a separate constructed-format program with:

- team-preview identity and format adapters;
- pinned Smogon usage sources;
- a separate `TeamPriorSource` for co-usage/team-builder correlations;
- rating/date/freshness metadata;
- team archetype and role-completion inference;
- explicit tests preventing constructed-team assumptions from leaking back into
  the Randbats path.

## Final recommendation

The project does not need another broad inventory implementation pass before
progressing. The next highest-value work is a narrow, explicit
`legal-action-v8` belief-risk schema design. The underlying per-Pokémon belief
contracts and v8 state plumbing are ready; the missing bridge is action
applicability under uncertainty. Keep v8 training, 1,000-battle v8
materialization, checkpoint promotion, live integration, and constructed-format
archetype work behind their separate gates.
