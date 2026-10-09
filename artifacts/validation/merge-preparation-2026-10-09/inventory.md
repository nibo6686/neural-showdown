# Refactor merge packaging candidate — 2026-10-09

Documentation and packaging preparation only. Nothing staged, committed, pushed, merged, deleted, uploaded or archived. The original 119-file proposed inventory was reconciled against current files; all exist. It is preserved as the original reviewed proposal in /tmp/neural-showdown-merge-inventory.md. This packet adds .gitignore and six packaging files: **134 current proposed inclusions** (126 before the bounded policy repair), **21 exclusions**, **two separate owner files**. These are dirty/untracked candidate files; already tracked unchanged dependencies remain in the branch. The existing 14-commit delta (179 files) requires whole-branch review separately.

## Changes and acceptance boundary

README now opens with accepted pinned v2 PIPELINE-002 capture and conditional per-result runtime semantics, support exclusions, and remaining merge gates. Its previous 2026-10-08 pending/false-only summary is retained in a dated historical details block. Architecture/workflows explicitly state current acceptance; pre-review CE-08B pending paragraphs remain dated history. Project/refactor 2026-10-07 snapshots and old next steps are labeled historical; current 2026-10-09 verdicts are untouched. No production code, test semantics or prior verdict changed.

The inverse of exactly these five covered documentation edits reproduces accepted digest `919e608db591d606c2a8370bc4df1511e962612a07af421aa9d9ba7ed6f9fbbc`. Current 121-input local digest is `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce`; reviewed_sha256 and all prior attestation records still contain their accepted values. Only local sha256 was refreshed. Independent bookkeeping review must inspect these five doc diffs, ignore rules, compact retention/inventory/pathspec packet and unchanged production/fixture hashes, then attest the resulting documentation digest if justified. No implementation test rerun is implied. No coverage checker/self-test ran in this task.

## Required compact fixtures

- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/predecessor.json` — 51,325 bytes; hash pinned and read by pipeline_episode_saved_helpers.ts. Explicitly included.
- `artifacts/validation/faithful-flag-2026-10-09/segment-start.json` — 111,452 bytes; hash pinned and read by pipeline_episode_faithful.test.ts. Explicitly included.

Neither exact large-envelope ignore rule hides these fixtures. The helper's diagnostic output directory exists from included fixture/log files. Coverage has all 121 required files. Existing sim-core/package-lock.json, trainer/pyproject.toml, locked simulator-record requirements and protocol package-data configuration remain tracked.

## Evidence retention

See large-evidence-retention.json for all three excluded 182 MB envelope paths, sizes, accepted recorded SHA-256s and the positive/rejection evidence depending on them. Current size and mtime checks match accepted recovery verification; hashes are reused, not recomputed. Every payload remains at its original local path. **Durable external storage is pending an owner-selected destination; no archive or upload exists from this preparation.** Review result metadata and compact logs ship; large payload references identify externally retained/local evidence, not files available in a fresh clone. Arrange retrieval by hashes before treating the evidence archive as durable.

Existing ignore rules excluded only top-level validation JSON, leaving nested dumps visible. New exact-file rules exclude only the three large envelope names, plus generated egg-info and the unrelated empty root npm lock. Ignore rules cannot hide already tracked egg-info modifications; their explicit exclusion remains necessary. Smaller diagnostic payloads and future strategy/policy files remain preserved through explicit pathspec omission. No source, compact fixture, summary metadata or lock under sim-core is ignored.

## Exact inclusion list

- `.gitignore`
- `README.md`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/forged-origin.stderr`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/forged-origin.stdout`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/predecessor.json`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/python-controls.json`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/recovery.json`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/wrong-outcome.stderr`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/wrong-outcome.stdout`
- `artifacts/validation/ce08a-current-source-2026-10-09/metadata.json`
- `artifacts/validation/ce08a-current-source-2026-10-09/recovery-console.log`
- `artifacts/validation/ce08a-current-source-2026-10-09/witness.log`
- `artifacts/validation/ce08b-four-finding-repair-2026-10-09/evidence.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/results.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/review-metadata.json`
- `artifacts/validation/ce08b-stop-reconciliation-2026-10-09/evidence.json`
- `artifacts/validation/ce08b-stop-reconciliation-2026-10-09/final-checks.json`
- `artifacts/validation/ce08b-stop-reconciliation-2026-10-09/focused-output.log`
- `artifacts/validation/faithful-flag-2026-10-09/build.log`
- `artifacts/validation/faithful-flag-2026-10-09/cleanup-retry.log`
- `artifacts/validation/faithful-flag-2026-10-09/cleanup.log`
- `artifacts/validation/faithful-flag-2026-10-09/coverage-checker.log`
- `artifacts/validation/faithful-flag-2026-10-09/coverage-self-test.log`
- `artifacts/validation/faithful-flag-2026-10-09/eligible.log`
- `artifacts/validation/faithful-flag-2026-10-09/evidence.json`
- `artifacts/validation/faithful-flag-2026-10-09/ineligible.log`
- `artifacts/validation/faithful-flag-2026-10-09/limits.log`
- `artifacts/validation/faithful-flag-2026-10-09/revival.log`
- `artifacts/validation/faithful-flag-2026-10-09/segment-start.json`
- `artifacts/validation/faithful-flag-2026-10-09/tamper.log`
- `artifacts/validation/merge-preparation-2026-10-09/exclude.paths`
- `artifacts/validation/merge-preparation-2026-10-09/include.paths`
- `artifacts/validation/merge-preparation-2026-10-09/inventory.md`
- `artifacts/validation/merge-preparation-2026-10-09/large-evidence-retention.json`
- `artifacts/validation/merge-preparation-2026-10-09/presence-checks.json`
- `artifacts/validation/merge-preparation-2026-10-09/replay-policy-boundaries.log`
- `artifacts/validation/merge-preparation-2026-10-09/replay-policy-duplicate.log`
- `artifacts/validation/merge-preparation-2026-10-09/replay-policy-repair.json`
- `artifacts/validation/merge-preparation-2026-10-09/replay-policy-single.log`
- `artifacts/validation/merge-preparation-2026-10-09/replay-policy-suffix.log`
- `artifacts/validation/merge-preparation-2026-10-09/separate.paths`
- `docs/PROJECT_STATUS.md`
- `docs/architecture.md`
- `docs/contracts/DATASET_LINEAGE.md`
- `docs/contracts/PIPELINE_EPISODE.md`
- `docs/contracts/SEEDED_TRANSITION.md`
- `docs/contracts/SIMULATOR_COVERAGE.md`
- `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md`
- `docs/refactor/CONTINUATION.md`
- `docs/refactor/DECISIONS.md`
- `docs/refactor/DEFINITION_OF_DONE.md`
- `docs/refactor/ENVIRONMENT_VALIDATION.md`
- `docs/refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md`
- `docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`
- `docs/refactor/PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`
- `docs/refactor/RISKS.md`
- `docs/refactor/SCANNER_EXPANSION_PROGRESS.md`
- `docs/refactor/SCHEMA_CLOSURE_AUDIT.md`
- `docs/refactor/STATUS.md`
- `docs/refactor/WORK_ITEMS.md`
- `docs/requirements/spec.md`
- `docs/workflows.md`
- `sim-core/package.json`
- `sim-core/scripts/check-simulator-coverage.cjs`
- `sim-core/scripts/recover-ce08a-adversarial.cjs`
- `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`
- `sim-core/src/action_codec.ts`
- `sim-core/src/baselines/heuristic.ts`
- `sim-core/src/belief_state.ts`
- `sim-core/src/effect_inventory.ts`
- `sim-core/src/env_manager.ts`
- `sim-core/src/observable_state.ts`
- `sim-core/src/pipeline_episode.ts`
- `sim-core/src/pipeline_episode_evidence.ts`
- `sim-core/src/pipeline_integration.ts`
- `sim-core/src/protocol_contract.ts`
- `sim-core/src/public_ability.ts`
- `sim-core/src/public_health.ts`
- `sim-core/src/public_item.ts`
- `sim-core/src/state_extractor.ts`
- `sim-core/src/typed_state_lifecycle.ts`
- `sim-core/src/types.ts`
- `sim-core/tests/ability_callback.test.ts`
- `sim-core/tests/belief_state.test.ts`
- `sim-core/tests/court_change.test.ts`
- `sim-core/tests/entry_hazard.test.ts`
- `sim-core/tests/env_manager.test.ts`
- `sim-core/tests/forced_switch.test.ts`
- `sim-core/tests/future_sight.test.ts`
- `sim-core/tests/healing_wish.test.ts`
- `sim-core/tests/item.test.ts`
- `sim-core/tests/item_identity.test.ts`
- `sim-core/tests/major_status.test.ts`
- `sim-core/tests/observable_state.test.ts`
- `sim-core/tests/observable_state_fixture.test.ts`
- `sim-core/tests/pipeline_episode.test.ts`
- `sim-core/tests/pipeline_episode_faithful.test.ts`
- `sim-core/tests/pipeline_episode_saved_helpers.ts`
- `sim-core/tests/pipeline_episode_stop_repair.test.ts`
- `sim-core/tests/pipeline_integration.test.ts`
- `sim-core/tests/protocol_contract_validation.test.ts`
- `sim-core/tests/public_consequence_test_helpers.ts`
- `sim-core/tests/public_consequences.test.ts`
- `sim-core/tests/public_stages.test.ts`
- `sim-core/tests/repeat_use.test.ts`
- `sim-core/tests/revival.test.ts`
- `sim-core/tests/roost.test.ts`
- `sim-core/tests/screen.test.ts`
- `sim-core/tests/simulator_coverage.test.ts`
- `sim-core/tests/singlemove.test.ts`
- `sim-core/tests/slot_consequence_fixtures.ts`
- `sim-core/tests/spirit_shackle.test.ts`
- `sim-core/tests/state_extractor.test.ts`
- `sim-core/tests/terrain.test.ts`
- `sim-core/tests/trick_room.test.ts`
- `sim-core/tests/typed_state_lifecycle.test.ts`
- `sim-core/tests/weather.test.ts`
- `sim-core/tests/wish.test.ts`
- `sim-core/tests/wish_fixture.ts`
- `tests/fixtures/observable_state_v1.json`
- `trainer/src/neural/build_replay_policy_dataset.py`
- `trainer/src/neural/pipeline_record.py`
- `trainer/src/neural/protocol_contract.json`
- `trainer/src/neural/protocol_contract.py`
- `trainer/src/neural/public_ability.py`
- `trainer/src/neural/public_health.py`
- `trainer/src/neural/public_item.py`
- `trainer/src/neural/ts_identity.py`
- `trainer/src/neural/typed_state.py`
- `trainer/tests/test_major_status_contract.py`
- `trainer/tests/test_pipeline_record.py`
- `trainer/tests/test_public_consequences.py`
- `trainer/tests/test_replay_policy_lineage.py`
- `trainer/tests/test_typed_state.py`

## Exact exclusions — preserve locally

- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/forged-origin.json`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/run-isolated-controls.py`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/valid-envelope.json`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/wrong-outcome.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/invalid-limits-array.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/invalid-limits-null.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/invalid-limits-number.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/reproduce-limit-sibling.cjs`
- `artifacts/validation/ce08b-independent-review-2026-10-09/reproduce.cjs`
- `artifacts/validation/ce08b-independent-review-2026-10-09/seeded-forced-switch-candidate.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/seeded-forced-switch-pre-selection.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/seeded-revival-candidate.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/seeded-revival-pre-selection.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/unknown-limit-key-result.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/unknown-limit-key.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/valid-cancellation-control.json`
- `artifacts/validation/ce08b-independent-review-2026-10-09/valid-limit-negative-control.json`
- `package-lock.json`
- `trainer/src/neural_trainer.egg-info/PKG-INFO`
- `trainer/src/neural_trainer.egg-info/SOURCES.txt`
- `trainer/src/neural_trainer.egg-info/requires.txt`

## Separate owner files — outside implementation commit

- `AGENTS.md`
- `docs/refactor/DATA_INGESTION_AND_TRAINING_STRATEGY.md`

Also omit ignored environments, dependencies, build output, caches, local/private captures and replay dumps. No deletion or revert is proposed. Already committed generated metadata remains in existing branch history; this packet only excludes new dirty/generated edits.

## Later staging plan — requires separate approval

The .paths files contain exact repository-relative literal pathspecs. Only include.paths is a proposed staging input; exclude.paths and separate.paths are audit inventories, not staging commands. After approving the updated scope and fixing any review findings:

```sh
git add --pathspec-from-file=artifacts/validation/merge-preparation-2026-10-09/include.paths
git diff --cached --check
git diff --cached --name-status
git diff --cached --stat
```

These commands were not executed. Do not use git add -A. Confirm excluded/separate files remain unstaged.

## Remaining review and validation

1. Independently review/reseal the documentation-only candidate digest and packaging scope; preserve earlier runtime acceptance.
2. Select durable evidence destination and separately authorize retention/upload.
3. Review the complete branch delta against verified target main, including old 14 commits; approve commit inventory explicitly.
4. Authorize final-candidate checks on the exact assembled candidate: file/coverage/package presence, one build, coverage checker/self-test and whitespace; exact saved flag/stop controls only where needed for assembly/dependency changes. Sequential real-timeout controls, no implicit broad/combined/long run. Existing matching-source mechanic and publication evidence remains reusable.
5. Recheck target tip, repository/PR checks and rules at publication time; commit/push/PR/merge operations require separate authorization. The prior inspection found main at c4477b6, no target-only divergence, no workflow files, no surfaced required checks; detailed protection API was inaccessible. No mandatory CI job is invented.

Historical combined 182.032s timeout and original failed long invocation remain failures; separate accepted passes are not those invocations. Windows/cross-platform, datasets, training/live readiness and merge approval remain outside pinned capture acceptance.


## Independent packaging and whole-branch review — 2026-10-09

### Findings

**Medium — committed legacy policy-builder lineage collision (whole-branch blocker).** `trainer/src/neural/build_replay_policy_dataset.py:87-104` gives every move/switch example for one perspective in a turn the same `_protocol_prefix_until_turn` prefix, and supplies no action/observation/transition identity. `dataset_lineage.py:148-163` therefore hashes identical identity payloads for distinct same-side actions. `build_replay_policy_dataset.py:175` calls duplicate-rejecting `validate_records` before opening the output. `parse_replay_logs.py:184-215` retains move and switch/drag events under the same current turn, so a turn containing a move and subsequent pivot/forced switch triggers a deterministic duplicate ID and rejects the otherwise eligible collection. This is a static code contradiction to retained builder compatibility, not a newly executed test result. Historical DATA-001 acceptance is retained as history; its recorded simple controls do not establish this sibling. No new DATA-001/core capture or mechanic defect is inferred.

**Smallest follow-up:** separately authorize a narrow policy-builder per-action source-prefix/identity repair using existing canonical lineage helpers, plus a synthetic same-turn move/switch publication regression and distinct-event/stable-ID controls. Preserve core duplicate rejection; do not fix this by suppressing duplicate errors or inventing a second hash scheme. No real replay acquisition, dataset generation, training or simulator battle is needed. If owner instead selects a capture-only branch, explicitly separate this already committed legacy-builder change and its dependent tests; the dirty-file exclusion list alone cannot remove it from the 14-commit PR. No production repair performed in this review.

No material packaging defect remains. Large evidence still resides at its original local paths with owner-selected external storage pending; this is a retention prerequisite, not an archive success claim. Prior execution limitations remain unchanged.

### Open questions

Owner must choose the legacy-builder repair versus explicit branch-scope separation, the external evidence destination, separate handling of AGENTS/ingestion strategy, and later commit/merge approvals. None changes pinned capture or conditional runtime acceptance.

### Packaging verdict and digest disposition

Approve **126 included / 21 excluded / two separate owner files for proposal only**, unchanged. All entries are unique disjoint exact `:(literal)` repository paths, without wildcards, traversal or absolute paths; all exist. Every visible dirty/untracked file is accounted for. The include list contains no excluded/separate artifact. All 121 coverage inputs are already tracked or included. Both compact fixture hashes, references and ignore boundaries match. The exact large-file ignore rules retain the required fixtures; generated tracked egg-info still requires explicit pathspec exclusion. No staged content exists.

README's current scope, architecture/workflow acceptance and historical checkpoint annotations agree with the accepted episode/flag contracts and current status. Failed invocations remain failed. Simulator-record locks, protocol package data and macOS scope remain intact; Windows/datasets/training/live exclusions remain explicit. Small metadata/logs are retained without implying excluded payload availability in a fresh clone. Accepted large hashes are reused from unchanged verification records with matching size/mtime; no large rehash or relocation.

Prepared local digest `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce` reproduces. Only five covered documentation inputs changed from accepted `919e608db591d606c2a8370bc4df1511e962612a07af421aa9d9ba7ed6f9fbbc`; the inspected inverse edits reproduce that baseline, and runtime/test/fixture hashes remain unchanged. Attest only the accumulated pinned capture/runtime inputs plus these documentation corrections. Packaging/ignore/pathspec review is separately recorded here, since those files are outside the coverage digest. **This is not a whole-branch digest attestation or merge approval:** the demonstrated policy-builder boundary is outside the 121-input list. Prior scoped attestations remain preserved in the manifest. No tests or coverage validator workloads ran.

### Whole-branch review crosswalk

Verified local branch `refactor/state-001-observable-state` at `6475d01`; local target `origin/main`/origin HEAD is `main` at `c4477b6`. Divergence remains 0 target-only / 14 branch-only. Review covers the 179-file committed delta plus the 126-file proposed dirty scope, reusing accepted component evidence at dependency/branch scope rather than asserting a new combined test pass.

| Branch/integration group | Review basis / disposition |
| --- | --- |
| WM assets, AGENTS, ignores | Portable skills/registry are retained; owner-local policy stays outside dirty implementation commit. Exact ignore and pathspec boundaries reviewed. No runtime readiness authority added. |
| Capture contracts, source inventory, parser/extractor, lifecycle/health/item/ability validators | Accepted C01–C30/FCE gates and current pinned digest; unchanged runtime dependencies and typed/public/private boundaries reused. No concrete contradiction discovered in accepted mechanics. |
| Canonical action/belief/transition, settling, environment and RPC/controller wiring | Existing accepted lower-slice and deterministic controller/RPC evidence, source inspection of additive canonical/snapshot dispatch, seed isolation and retained legacy defaults. Snapshot RPC remains internal simulator tooling, not observation/DATA-001 publication. No new network/live or broad legacy RPC hardening claim. |
| Episode/full/bulk bridge, terminal authority and faithful claim | Accepted CE-06/08A/08B and conditional runtime review with exact fixture/actor/origin/cleanup/atomic publication boundaries. Component hash-bound evidence reused, not broad rerun. |
| Python/Node dependency and package wiring | sim-core package/lock scope, simulator-record hash lock and pyproject/protocol package-data declaration match accepted macOS profile. Generated egg-info edits excluded; already committed historical metadata is not removed. Final assembled package presence still requires final-candidate check. |
| DATA-001 and legacy replay/live-private builders | Historical additive contract/control review reused; no dataset/feature acceptance implied. Concrete same-turn policy identity collision is a bounded compatibility blocker. Value/private builder additions are lineage plumbing, not accepted decision-time model inputs. |
| Fixtures, tests, replay markers and long evidence | Compact required fixtures included; opt-in replay fixtures remain separate and skipped explicitly when absent. Long payload metadata identifies original/local evidence; failed original/combined invocations remain documented. No automatic long rerun. |
| Status, training/model placeholders and historical artifacts | Current versus historical readiness is explicit. No checkpoint/model/training/live activation or Windows support promotion is included. |

**Whole-branch verdict:** withhold merge readiness for the exact legacy policy collision plus pending final-candidate validation and owner scope decisions. This does not revoke scoped capture/runtime acceptance.

### Smallest final-candidate workload — proposed, not executed

After the bounded blocker is repaired/reviewed or explicitly separated, and the selected commit scope is approved, validate the exact assembled candidate under the accepted macOS simulator-record profile:

1. `npm run build --prefix sim-core` once.
2. `node sim-core/scripts/check-simulator-coverage.cjs` and then `node sim-core/scripts/check-simulator-coverage.cjs --reachability-self-test`, sequentially.
3. `git diff --check`; verify all 121 coverage files, the two pinned compact fixtures, sim-core lock and Python protocol package-data are present in the candidate, not merely in the dirty source checkout.
4. Exact three `pipeline_episode_faithful.test.js` positive selectors: `^faithful claim saved win tie and bound continuation publish conservatively or true$`, `^faithful claim ineligible stops segments terminal-only and schemas reject without mutation$`, `^faithful claim coherent origin and actor tampering reaches semantic validators$`. Use PYTHON=.venv-simulator/bin/python and trainer/src PYTHONPATH, visible output, one workload at a time with real 180s process-group limits. These are assembly/fixture/full-bulk integration checks, not mechanic or long-chain reruns.
5. Only exact new policy-builder controls from the separate repair need fresh execution; reuse unchanged limits/Revival/cleanup and other accepted source evidence. No broad, combined, long-witness, replay acquisition or performance run is implicit.

Before publication recheck main tip and actual PR rules/checks; no mandatory CI job beyond repository evidence is invented. No staging/commit/push/merge/archive/upload authorized or performed.

## Replay policy boundary repair checkpoint — 2026-10-09

Authoring candidate for the whole-branch same-turn lineage finding; independent semantic review remains required. The policy builder reparses retained public protocol and requires exact stored-event agreement, then uses each ordered action line's **preceding** prefix with existing DATA-001 canonical helpers. A same-player move followed by a switch receives distinct cursors, prefix hashes and IDs. Mapper tracking is sequential so later same-turn suffixes cannot seed earlier labels; feature state still advances after the row. No duplicate exception, arbitrary suffix or new identity scheme was introduced. Missing/stale evidence skips explicitly as `unverifiable_action_boundaries`; no decision/request boundary is fabricated.

| Exact focused control | Result | Process elapsed |
| --- | --- | --- |
| Same-turn move/switch + actual temporary collection publication (4 rows including initial switches) | 1/1 pass | 3.591s |
| Genuine duplicate, collection rejection before write, existing output/input preservation | 1/1 pass | 0.668s |
| Later same-turn suffix, complete earlier-row/prefix/identity equality | 1/1 pass | 0.401s |
| Ordinary single action + missing/stale/omitted event evidence | 1/1 pass | 0.460s |

Only these four exact Python selections ran, sequentially under the accepted macOS interpreter with enforced 180-second process-group limits. No download, battle, full suite, long witness, or non-temporary dataset generation. Logs and affected/dependency SHA-256s are in `replay-policy-repair.json`. Fresh controls cover the changed builder; unrelated capture evidence remains retained, not presented as a rerun.

Legacy replay limitations remain: observable event boundaries are not owned-request decision boundaries; mapping/features and public-only replay data are not certified for the new training pipeline. Historical records are not rewritten. No implementation blocker remains within the requested four controls; independent repair review and the previously specified final assembled-candidate workload remain pending.

Proposed inventory is now **134 inclusions**, unchanged **21 exclusions**, and **two separate owner files**. Eight additions: builder, focused test, lineage contract and five compact result/log files. All literal inclusion paths exist and remain disjoint from exclusions/owner files. Required fixtures and excluded evidence remain untouched. Relevant source/contract hashes:

- `trainer/src/neural/build_replay_policy_dataset.py`: `d035fdd49f8764b31014eb3a9bdd0e304dec37f0480b1da8d4108df101320515`
- `trainer/tests/test_replay_policy_lineage.py`: `1cfb8428d572a009afa5d4245ca1f50cd4b3871f7c867e990cdadfadbf138574`
- `docs/contracts/DATASET_LINEAGE.md`: `fd67ed5c3402f927f01de79ec86eb543ed4bec349ab7d8bbbf09709c606cd894`
- `trainer/src/neural/dataset_lineage.py`: `4178367b0f8dcb319471f749ff6ef64d39b15e0d95716eb5b77876587ce670f0`
- `trainer/src/neural/parse_replay_logs.py`: `7f02c81aaba5e29fae0c5f080822a4e9637e225adabb8698e33ad1cc814cd40d`
- `trainer/src/neural/build_replay_value_dataset.py`: `21de7b0fb737ae06ba195edf2bcae2709971103cdce142e7a28b824c881649a6`
- `trainer/src/neural/action_mapper.py`: `afbaec7230282583d47bd690451cd1507ad758e57e6ba2ead1f3f1d378cf9259`

All repair inputs are outside the accepted 121-file capture list; the reproducible capture/local/reviewed digest remains `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce`. This repair is separately hash-bound and pending independent review; that digest does not attest the legacy policy repair or whole branch. Manifest and prior attestations are unchanged. Whitespace and path-presence checks supplement the four focused passes. No staging/commit/push/merge performed.

## Independent legacy replay-policy repair review — 2026-10-09

**Scoped verdict: the whole-branch legacy same-turn lineage regression is resolved.** This verdict supersedes only that finding and the preceding repair checkpoint's pending independent-review boundary; it does not accept the whole branch or approve a merge.

No material findings. Inspected the builder diff, parser event ordering, feature updates, sequential mapper tracking, existing canonical DATA-001 helpers and collection validation, all four focused controls and their saved outputs, lineage contract and REQ-005/legacy replay exclusions. All seven recorded source/test/contract dependency hashes, four result-log hashes and the coverage manifest hash match `replay-policy-repair.json`. Reuse all four passes (3.591s, 0.668s, 0.401s and 0.460s); no test, download, battle or regeneration ran during review.

| Obligation | Reviewed proof / disposition |
| --- | --- |
| Distinct same-turn boundaries and identities | Exact stored-event/fresh-protocol join plus ordered action occurrence; prefix excludes the action line. Existing cursor/prefix canonical helper supplies distinct IDs, without arbitrary suffixes. Accepted within this legacy repair. |
| Causal input and mapping | Feature update follows row creation; mapper sees only preceding events/current supervised label. Suffix control compares the entire earlier row, including its input, mapping and identity. No later same-turn event enters that earlier row. |
| Duplicate rejection and valid publication | Unchanged `validate_records` runs before opening output. Real temporary four-row publication succeeds; repeated trajectory/row rejects with the duplicate-identity diagnostic, preserves existing output and writes no report. |
| Missing or stale boundary evidence | Exact parser agreement and ordered search reject/skip missing, stale or omitted event evidence rather than fabricate a cursor. |
| Legacy scope | Observable event boundaries do not reconstruct private decision requests/legal actions. Mapping/features, historical files, generated-format eligibility and new training readiness remain outside this acceptance. |

No open question blocks this narrow verdict. Constructed fixtures establish the builder contract, not generated-team mechanics. Historical data is not migrated. No accepted capture semantics, runtime flag, manifest, reviewed digest, prior attestation or owner/excluded file changed. The 134 literal inclusions remain present, unique and disjoint from the unchanged 21 exclusions and two separate owner files.

The previously proposed **final assembled-candidate workload may now proceed after owner authorization of the selected candidate/workload**: one simulator build, coverage checker then synthetic self-test, whitespace/required fixture/package presence, and the three exact short faithful-claim integration controls listed above. The four unchanged policy controls already have applicable reviewed passes and need no repetition unless their dependencies or assembly change. No broad/combined/long witness rerun is implied. Whole-branch/merge approval, staging/commit authorization and external evidence storage remain separate. Historical failed/timeout invocations remain limitations. Capture digest remains `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce`; it does not attest this outside-list legacy repair or the whole branch.

## Final proposed-candidate checkout validation — 2026-10-09

**Verdict: the explicitly authorized workload passed.** This is validation of the current proposed 134-path dirty candidate and tracked dependencies in the existing checkout, not a committed tip, whole-branch acceptance or merge approval. No detected drift in reviewed runtime/test/fixture/config inputs: the accepted 121-source digest reproduces, all seven legacy-repair dependency hashes and four logs match, literal inventories remain 134/21/2 and disjoint, and all 298 frozen candidate/dependency/packaging hashes remained unchanged through validation. `final-candidate/hashes.json` records the branch/HEAD, pathspec hashes, initial status and complete freeze. `final-candidate/results.json` records commands, environment, limits, elapsed times, log hashes, check-script sources and exclusions. The earlier authoring presence packet's pending repair-review field is historical; the independent review above resolves it.

| Workload (one invocation each, sequential) | Exit / result | Process elapsed | Log under `final-candidate/` |
| --- | --- | --- | --- |
| `npm run build --prefix sim-core` | 0 / pass | 4.550s | `build.log` |
| `node sim-core/scripts/check-simulator-coverage.cjs` | 0 / pass | 4.161s | `coverage.log` |
| Same checker `--reachability-self-test` | 0 / pass | 0.672s | `self-test.log` |
| `git diff --check` | 0 / pass | 0.078s | `whitespace.log` |
| Compact fixture hashes, dependency/lock and package-data declarations, interpreter/import/frozen-file checks | 0 / pass | 0.564s | `presence.log` |
| Exact eligible faithful-result selector below | 0 / 1 test pass | 3.111s | `faithful-eligible.log` |
| Exact ineligible faithful-result selector below | 0 / 1 test pass | 2.417s | `faithful-ineligible.log` |
| Exact coherent-tamper selector below | 0 / 1 test pass | 0.509s | `faithful-tampering.log` |

All workloads used enforced 180-second owned-process-group limits. Node tests used `--test --test-reporter=spec`, exactly one positive anchored selector per invocation and only `sim-core/dist/tests/pipeline_episode_faithful.test.js`; each reported one selected test, zero failures. `PYTHON` was the absolute `.venv-simulator/bin/python`, `PYTHONPATH` absolute `trainer/src` (macOS arm64 / Python 3.9.6). No install, battle regeneration, broad/combined/long suite, benchmark or redundant policy regression ran. Matching accepted evidence outside this workload is reused.

Exact selectors:

- `^faithful claim saved win tie and bound continuation publish conservatively or true$`
- `^faithful claim ineligible stops segments terminal-only and schemas reject without mutation$`
- `^faithful claim coherent origin and actor tampering reaches semantic validators$`

Both compact fixtures match their pinned hashes and are included/not ignored. Package checks cover tracked sim-core package/lock with installed Showdown 0.11.10, simulator-record hash lock, pyproject extra and protocol JSON package-data declaration. Source imports resolve to trainer/src. No wheel construction, isolated package install or dependency resolution is claimed. Build exercises whole checkout TS src/tests (candidate or tracked unchanged), coverage exercises declared sources/pinned installed simulator, and exact tests exercise included saved fixtures and source Python. No explicitly excluded payload, generated egg-info or owner document is a runtime input to these checks; installed environments/dependencies are local prerequisites rather than commit contents. Whole tracked-diff whitespace also examines excluded egg-info and AGENTS edits, without proposing their inclusion. Owner AGENTS guidance governs execution only.

The only new files are the ten compact validation artifacts (eight logs and hashes/results JSON) under `final-candidate/`. They are **additional proposed evidence**, outside the unchanged 134-path inclusion list, pending owner selection; approving all ten would yield 144 proposed inclusions. No paths were silently added to the approved-for-proposal inventory. The checkpoint inventory update is documentary; captured pre-check inventory hash is intentionally retained. Manifest, coverage digest and reviewed_sha256 remain unchanged: `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce`. No new attestation.

### Concrete staging/commit proposal — not executed

After explicit owner approval of the scope, use the existing literal `include.paths` with `git add --pathspec-from-file=artifacts/validation/merge-preparation-2026-10-09/include.paths`; add only individually approved literal validation-packet paths (enumerated by results/log metadata), never `git add -A` or the entire artifact directory. Inspect staged name/status, diff/stat and `git diff --cached --check`, verify no exclude/separate paths entered the index, then create a reviewable commit only with separate authorization. Proposed commit subject: `Complete pinned v2 capture refactor and repair replay action lineage`. No stage, commit, push or merge was performed; index remains empty.

After the approved commit exists: compare its complete candidate input hashes/fixture/package presence to this freeze and verify excluded/separate membership; perform staged/commit whitespace and reproducible coverage checks on that exact candidate. Unchanged build/short integration evidence may be reused when inputs and assembly match. Missing or changed runtime/compiled/dependency inputs require only their affected build/integration checks, not automatic long or broad reruns. Recheck main divergence and actual required PR checks/rules at publication. Historical failed/combined timeout invocations remain limitations, not successful runs. Owner decisions remain: commit scope (including optional validation packet), separate AGENTS/ingestion-document handling, durable large-evidence storage destination/upload authorization, publication and merge approval. No dataset/training/Windows/live readiness is implied.

## Whitespace-only follow-up to 849f523 — 2026-10-09

Removed only reported trailing whitespace from witness.log lines 31/33/35 and cleanup.log lines 19/21, and excess EOF blank lines from the three reported TypeScript helpers. Token/content equality verified; no implementation tests run. Historical audit/frozen manifests retain execution-time hashes; this mapping records their byte-only successors. The current witness-log manifest pin and faithful-flag evidence pins are updated with before/after provenance. Required compact JSON fixtures and canonical runtime identities are unchanged.

- `artifacts/validation/ce08a-current-source-2026-10-09/witness.log`: `a3872edcb1c909f867454bc3f4f02bd9be317b151e88d3fc654b3eb74efd096d` → `16e5d8b3b8d98b32f12e79036877316b4b3e0649f81dcefa7227823428e57906`
- `artifacts/validation/faithful-flag-2026-10-09/cleanup.log`: `fbbebb2151bcbc5f925ce8e22e1e8a725cdad2cc361e46aa6964d4afb96c85b4` → `f1f63a551765b2cee4bf40ad55f2db619189c8c1c5f9d567d4825da5b94130bc`
- `sim-core/tests/pipeline_episode_saved_helpers.ts`: `9c24cfbefe269096d20f6da419c93651fdde3dd341eb6c3c3f0d2ee17c723ed0` → `95bfd6436598753fa0a24bfec1a1de401585f6c3d8ea2c210cae67cc239fcb2c`
- `sim-core/tests/slot_consequence_fixtures.ts`: `344612f48b43b25cccd1d0dd1965f9e1989cee008f49a24a2ab94215d4ff2f71` → `80f8236264ba8c15ba341a5de68b058defc4abee2840601e4d5573e859e9dee6`
- `sim-core/tests/wish_fixture.ts`: `ce6b4dd36ce55f1c38b0e96ce7e7381870b8bff2ba28c81850e68f1f73ae077d` → `c83a6a1b785b14747ac9a8c4471f0f853d2f6d06aca8aa1f9b0684bd1dac6334`

The three TS helpers are coverage inputs. Local digest changes from `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce` to `10a58699b7857ae158ed85224a33dbe35d62df25462666c950fb6c865e526de2`; reviewed_sha256 remains `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce`. **Independent attestation refresh is required; no semantic verdict was promoted.** Frozen validation packets and historical audit hashes are not rewritten as new executions. Unrelated local files, owner documents, excluded payloads and prior attestations are preserved. No push, PR, merge or upload authorized.

## Independent whitespace normalization attestation — 2026-10-09

No material findings in 286e2de against 849f523: exact two-log trailing-space and three-helper EOF normalization verified, with unchanged executable text, assertion/fixture payloads and historical pass/failure results. Current pins match corrected bytes; before/after provenance retained. Reproduce local digest `10a58699b7857ae158ed85224a33dbe35d62df25462666c950fb6c865e526de2`; refresh reviewed_sha256 only for this whitespace normalization and necessary bookkeeping, preserving prior `15366961d663ecd4f6a2a93e485f2d4d55738202ba819e3bdf2ed644ef0361ce` and every earlier scoped verdict. Existing accepted source/test evidence remains applicable; no implementation test/battle rerun or broader acceptance. Coverage checker passed (4.334s), synthetic self-test passed (0.616s); combined refactor and bookkeeping whitespace checks pass. These are the only validation workload for this review. Separate bookkeeping commit authorized; no prior commit amended.

Publication still requires owner push/PR authorization, target/required-check verification, external evidence storage decision and separate owner-document handling. No merge approval or training/live readiness. The uncommitted validation packets containing local-machine paths remain excluded. Historical execution limitations remain explicit.

## PR #2 publication-text repair — 2026-10-09

The private historical review pointer is removed; the README current-focus paragraph now reflects accepted pinned v2 capture and conditional per-result fidelity, and the specification no longer links the excluded ingestion proposal. Historical verdicts, failed invocations, runtime versions, platform facts and deferred Windows/training/live limits remain unchanged.

Personal checkout/home/pytest-temp text is sanitized in published documentation and historical log derivatives. Repository paths, `$HOME`, `<NVM_DIR>`, `<repository-root>`, `<local-downloads>` and `<temporary-directory>` replace personal locations; standard `/Library`, system/runtime and meaningful generic `/tmp` paths remain. The compact [publication-sanitization.json](publication-sanitization.json) records each changed path with original and publication SHA-256. Original byte copies are retained under ignored `artifacts/analysis/pr2-publication-originals-2026-10-09/`; do not stage or upload them. Existing execution-time log hashes remain historical; explicit publication hashes identify the sanitized copies. No evidence result, fixture payload or executable behavior changed.

Remaining disclosures outside the authorized text-only boundary: the legacy main script `scripts/analyze_decision_categories.py:194-195` and PR script `scripts/generate_cross_platform_simulator_record.ps1:3` still contain personal Windows paths in executable arguments. A separately authorized narrow source-default repair is required to remove those; no source change is made here.

Coverage bookkeeping refreshes only the candidate local digest and current publication-artifact pins, retaining original hash provenance. `reviewed_sha256` and prior semantic attestations are unchanged; independent documentation/publication review and digest refresh remain required before an authorized follow-up commit/push. Nothing is staged, committed, pushed or marked ready. Whitespace, tracked-reference/personal-path scans, preserved-byte checks and one normal coverage checker are the only checks in this repair; implementation validation remains reused and no tests or long workload run.

**Checks:** whitespace exit 0; zero broken Markdown targets in tracked candidate plus the new compact sanitization manifest; all 25 original/publication hash pairs verified; runtime/config/test/fixture coverage inputs match HEAD. Normal checker exit 1 only for pending separate review. Candidate `d02f9220582d770a567a22d695b6924a4c50445442e1b6adb85bc8b83259a039`; reviewed digest remains `10a58699b7857ae158ed85224a33dbe35d62df25462666c950fb6c865e526de2`. Include the new untracked `publication-sanitization.json` explicitly in the future reviewed commit. Do not include ignored original copies. The two executable-path disclosures above remain explicit. Index empty; pre-existing local edits untouched.

## PR #2 executable-path repair — 2026-10-09

Python analysis now requires `--input`, accepts an exact `--output` override, and defaults output relative to the repository; import/help/argument checks perform no analysis. The former analysis body is unchanged inside `main`. PowerShell generation now requires `-PatchPath`, resolves it before changing directories, and fails before build/generation when patch or explicitly selected executable paths are missing. Existing Python/Node/npm/output overrides and environment selection remain unchanged. Usage is updated in README and the historical Windows record without claiming a new Windows pass.

Focused sequential checks passed: Python syntax/import, explicit paths including spaces, default output, missing arguments/file exit 2 with empty stdout, help, and body equivalence; PowerShell static parameter/preflight ordering; whitespace. No data or battle generation, installs, implementation suites, staging or publication. `pwsh` is unavailable, so PowerShell parser and Windows execution evidence remain absent. Additional hardcoded Conda defaults in this generator, `scripts/validate_windows_simulator_record.ps1`, and `scripts/run_windows.ps1` are reported without expansion. Standard Program Files Node/npm locations are system paths, not redacted.

The consolidated publication manifest records current source/doc hashes and preserves original/sanitization-only hash distinctions. Independent review must cover both the text sanitization and narrow argument changes before attestation or an explicitly authorized follow-up commit/push. Preserved original evidence and all unrelated local work remain local; reviewed digests/prior verdicts are unchanged.

Candidate digest `dced76bcc1b24ebb015fdc45befc6b584f1b7bf623ddbb3447906be45e37b757`; normal coverage checker exit 1 solely at the unchanged reviewed-digest gate. Changed covered inputs: README, coverage contract, status, specification, and cross-platform generator. The legacy analysis script is outside the existing coverage source list and has its exact repair hash in the consolidated manifest. Independent review remains required; no semantic attestation is changed.

## Independent PR #2 publication-portability cleanup review — 2026-10-09

**Findings:** no material finding within the two explicitly authorized path sites and text-only cleanup. Low residual limitation: existing hardcoded Conda defaults in the generator, Windows validator and legacy launcher remain unchanged and are not certified portable. No private home/check-out path or private-document pointer remains in the intended publication tree. Meaningful system/runtime provenance is preserved.

**Open questions:** Windows parser/execution proof and external evidence destination remain separate; neither is claimed complete. Executable overrides must name the documented selected environment. No installation, automatic runtime fallback, broad suite, battle or publication sweep ran.

**Change summary / verdict:** accept scoped documentation/log derivatives, README/proposal-link corrections, required explicit Python input/output behavior and PowerShell patch/preflight behavior. Independently checked 25 baseline/original/current-publication hash pairs, exact eight path-only log transformations, unchanged historical JSON results, Python syntax/import/argument/help/error/body parity and PowerShell static parameter/preflight ordering; no pwsh available. Reviewed all five changed coverage inputs; accepted capture/flag and fixture/validator semantic evidence is reused unchanged. Candidate and reviewed digest `dced76bcc1b24ebb015fdc45befc6b584f1b7bf623ddbb3447906be45e37b757`; previous digest `10a58699b7857ae158ed85224a33dbe35d62df25462666c950fb6c865e526de2` and all prior attestations preserved. New compact sanitization manifest contains original/publication provenance; ignored originals and unrelated local files must remain unstaged. Coverage checker/self-test and staged/committed whitespace are the final bookkeeping checks. This task authorizes one exact-path follow-up commit only, with normal push requiring separate authorization.
