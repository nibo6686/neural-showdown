# Action-Rank and Value-Dataset Next Steps

## Decision summary

The action-rank path is ready for **one larger, non-production v7/v7 diagnostic
run**, conditional on first materializing and auditing a fresh 1,000-battle
post-Ditto v7/v7 dataset. The existing 300-battle artifact is sufficient for
plumbing but is not a larger independent-battle experiment.

The next action run should be **rank-only**. State value and action value should
both be disabled. This gives an interpretable comparison with the prior
1,000-battle v7/v5 rank-only result and prevents the weak value objective from
updating the shared state encoder or influencing checkpoint selection.

Value learning should move to a separate, larger, quality-filtered Gen 9
Random Battles dataset with battle-level splits, phase-balanced state sampling,
and a multi-target design. It should not be treated as a side objective on the
action-rank dataset.

Future v8 possible-threat features do not need to precede this one diagnostic
v7/v7 rank-only run. The run can establish the frozen-v7 baseline and quantify
where threat-sensitive decisions fail. v8 disposition is required before a
durable/promotable training decision, or it must be explicitly accepted as a
bounded limitation for a display-only shadow evaluation.

Training, materialization, browser/live shadow testing, checkpoint promotion,
and live/default changes remain blocked pending their separate explicit gates.

## Interpretation of the post-Ditto smoke

The smoke succeeded at its intended job:

- the trainer accepted `live-private-belief-v7` 3208D and `legal-action-v7`
  552D with exact ordered-name fingerprints;
- the post-Ditto dataset loaded with 25,232 matched groups and only the three
  quarantined, non-self-confirming Illusion rows excluded;
- the tiny overfit check passed;
- checkpoint/report generation completed with finite values and correct
  non-production metadata;
- no live/default behavior changed.

The one-epoch rank metrics are encouraging but not a quality baseline:
validation NLL/top-1/top-3 were 1.383279 / 0.434146 / 0.838137 and test
NLL/top-1/top-3 were 1.414682 / 0.410626 / 0.815486. They show that v7 ranking
learns through the complete path, not that the 300-battle model is ready for
shadow use.

There is stronger supporting evidence from the earlier 1,000-battle v7/v5
rank-only diagnostic: best epoch 8, validation top-1 0.4626 versus approximately
0.382 for the best simple baseline, and test top-1/top-3/NLL
0.4608 / 0.8504 / 1.3252. That result established that the grouped rank
objective can generalize beyond damage heuristics. The post-Ditto smoke now
establishes that the repaired v7/v7 schema and checkpoint path work. Together,
these justify one controlled larger v7/v7 diagnostic, not promotion.

## Why the next action run should be rank-only

Rank-dominant joint training would be less informative than rank-only:

- On the smoke dataset, about 20,552 train states at value batch size 64 produce
  roughly 322 value batches, while 20,549 rank groups at group batch size 8
  produce 2,569 rank batches. Most optimizer steps are rank-only, but the first
  value batches still alter the shared state encoder.
- In the earlier joint experiment, shared-encoder interference was measurable:
  removing rank gradients improved the value result, although it did not solve
  the underlying data problem.
- The current trainer selects a joint model when either validation value MSE or
  rank NLL improves. Downweighting value would reduce its gradient magnitude but
  would not remove shared-encoder updates or the mixed checkpoint-selection
  semantics.
- A rank-only run uses `optimizer_step_source=rank_batches_only` and selects
  solely by validation action-rank NLL, making comparison with the earlier
  1,000-battle v7/v5 run clean.

No value loss should be included in this run. If a later experiment studies
multi-task regularization, it should follow successful independent rank and
value baselines and use an explicit selection rule designed for multi-task
training.

## Proposed larger rank-focused diagnostic

### Required dataset before training

Proposed future dataset:

`artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_ditto/diagnostic_1000_v7_v7_post_ditto.npz`

It should reuse the existing 1,000-battle action-rank manifest and fixed
700/150/150 battle splits, but be freshly materialized through the post-Ditto
reconstruction path with `legal-action-v7`. This is a future approval-gated
materialization, not part of this planning task.

Before training, its report and independent audit must establish:

- 1,000/1,000 eligible battles or an explicitly reviewed replacement manifest;
- exact `live-private-belief-v7` 3208D and `legal-action-v7` 552D versions,
  dimensions, ordered-name fingerprints, and manifest checksum;
- no battle crosses train/validation/test;
- finite arrays and one positive per included action group;
- all structural skips and unmatched actions counted and categorized;
- no unsupported custom/team-size replay;
- no future-reveal leakage;
- action mix and validation/test coverage for moves, Tera, switches,
  non-damaging choices, forced decisions, dynamic mechanics, and v7 batch-7/8
  features;
- old datasets and live defaults unchanged.

### Draft config

`configs/diagnostic_1000_action_rank_v7_v7_post_ditto.rank_only.windows.json`

The proposal intentionally retains the prior 1,000-battle rank-only
architecture and optimizer settings so the v5-to-v7 comparison changes the
action schema/data repair path rather than model capacity:

- state value disabled, loss weight 0;
- action rank enabled, grouped cross-entropy, loss weight 1;
- action value disabled;
- state/action/rank hidden sizes 64/32/32;
- seed `20260619`;
- maximum 12 epochs;
- 64 action groups per batch;
- AdamW learning rate `0.001`, weight decay `0.0001`;
- gradient clipping at `1.0`;
- early stopping after three epochs without validation rank-NLL improvement;
- best checkpoint selected only by validation action-rank NLL;
- test evaluated once after model selection;
- `production_eligible: false`.

The approximately 226,274 parameters reflect the wider 552D action input while
preserving the previous hidden sizes.

### Exact future commands

**DO NOT RUN UNLESS THE 1,000-BATTLE MATERIALIZATION AND TRAINING RUN ARE
EXPLICITLY APPROVED.**

First, after the future dataset exists, run the read-only validation gate:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
& $py -m neural.train_vnext_diagnostic --config .\configs\diagnostic_1000_action_rank_v7_v7_post_ditto.rank_only.windows.json --validate-only
```

Only after that reports `PASS`, the proposed training command is:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
& $py -m neural.train_vnext_diagnostic --config .\configs\diagnostic_1000_action_rank_v7_v7_post_ditto.rank_only.windows.json
```

The run should be stopped and reviewed if the tiny rank overfit check fails,
metadata differs, non-finite values appear, or the validation behavior is
materially worse than the prior rank-only baseline.

## Why the value head did not beat the constant baseline

The smoke value result was validation MSE 1.483368 and test MSE 1.478658 versus
an approximately 1.0 constant baseline. This is consistent with the already
observed value-learning failure mode rather than a new schema failure:

1. **The effective sample size is battles, not states.** The 20,552 training
   states come from only 210 independent battles. Every state from one
   perspective repeats the same terminal label, so row count greatly
   overstates independent supervision.
2. **Raw terminal outcome is noisy for early and middle states.** A single
   +1/-1 target gives no graded indication of material, HP, remaining team,
   matchup, or game phase. Many superficially similar states legitimately have
   different outcomes because of later play.
3. **Long battles are overrepresented.** Without phase-aware per-battle
   sampling, games with more turns contribute more near-duplicate labels and
   optimizer weight.
4. **The model is large relative to independent battles.** Earlier experiments
   showed rapid memorization and saturated tanh predictions. A smaller,
   regularized value-only model briefly beat the baseline
   (validation/test MSE 0.9478/0.9453), but only by a thin margin and with
   overfitting after one epoch.
5. **Joint gradients are a confounder.** Rank updates dominate the number of
   optimizer steps and also update the shared state encoder. Isolation improved
   value performance, proving interference was real, but isolation alone still
   did not provide enough independent signal.

The conclusion is not that state value is impossible. It is that terminal
outcome on 210 battles, sampled as many correlated states, is the wrong data
regime for the current capacity and objective.

## Separate value-dataset plan

### Source and selection

Build a dedicated Gen 9 Random Battles value corpus from rated games whose
rating metadata can be preserved at collection time. Before fixing quotas,
profile the available counts in these proposed buckets:

- 1900+ premium/high-confidence;
- 1700-1899 primary high-Elo;
- 1500-1699 supporting competitive;
- below 1500 excluded from the first curated value baseline unless needed for
  an explicitly labeled distribution-shift evaluation.

Use the lower of the two players' pre-battle ratings for conservative
eligibility. Do not select only long games. Keep short games when both players
made meaningful decisions, the game ended normally, and reconstruction is
complete.

Exclude:

- forfeits before both players made a minimum meaningful-decision contribution;
- disconnect, timeout, inactivity, or abandonment endings;
- malformed/custom battles, unsupported team sizes, or format mismatches;
- obvious abandonment-driven blowouts;
- replay/state reconstruction failures;
- unresolved structural skips or identity ambiguities that would require
  forcing a label.

Do not reject a clean game merely because it ended quickly through decisive
competitive play. The curation report should distinguish normal win, valid
competitive forfeit after substantial play, early forfeit, timeout/disconnect,
and malformed/reconstruction failure rather than using turn count alone.

### Split and sampling

- Assign train/validation/test at battle level before featurization.
- Freeze a manifest and prevent every state from a battle from crossing splits.
- Balance winner and loser perspectives within each split.
- Stratify the battle split by Elo bucket, ending type, and broad game length.
- Sample early, middle, and late states explicitly. Define phase by normalized
  progress (for example decision-index thirds), not fixed turn numbers alone.
- Cap states per battle and per phase so long games do not dominate.
- Retain both perspectives only when their time-causal private/public inputs can
  be reconstructed correctly.
- Record skipped/quarantined public-replay ambiguities; never backfill them from
  future reveals.

A reasonable first diagnostic target is at least several thousand independent
battles, with a 70/15/15 battle split and enough 1700+ and 1900+ battles to
report bucket-specific uncertainty. Final counts should be chosen only after a
read-only availability/profile report.

### Target design

Use a multi-head value dataset rather than blending every signal into one
opaque scalar:

- **Primary terminal outcome:** win/loss from the state owner's perspective.
  Prefer a calibrated win-probability head (logit with binary cross-entropy or
  Brier/MSE reporting) rather than relying only on saturated tanh regression.
- **Current normalized team-HP advantage:** own minus opponent aggregate
  remaining HP, normalized to `[-1, 1]`.
- **Current remaining-Pokémon advantage:** own minus opponent available count,
  normalized by six.
- **Current material summary:** a documented combination of remaining Pokémon,
  normalized HP, status burden, and known/revealed resource state. Keep its
  components available separately so the scalar is auditable.
- **Optional phase/horizon diagnostics:** report outcome calibration separately
  for early, middle, and late states rather than allowing late, easy states to
  hide weak early-game value estimates.

Keep terminal outcome as the primary model-selection target. Auxiliary
material/HP/count heads should regularize the representation and provide
diagnostics; they should not silently replace the meaning of win probability.
All input features and current-state auxiliary targets must be computed from
information available at that replay prefix. Final outcome is the supervised
future target; future species, moves, items, abilities, or Illusion identity
must never enter the input.

Before training, compare:

- constant and Elo-bucket priors;
- phase-conditioned constant baselines;
- simple current-material baselines;
- calibration/Brier score, log loss, sign/accuracy, and reliability curves;
- per-Elo-bucket and early/mid/late confidence intervals.

## v8 threat-awareness ordering

One larger v7/v7 rank-only diagnostic should happen **before** implementing v8:

- v7 is frozen, materializable, and now proven end to end;
- the v7 run provides a clean baseline for whether the typed-effect expansion
  improves rank learning over the old v5 result;
- implementing v8 first would combine schema changes with dataset scale and
  reconstruction changes, weakening attribution;
- known possible-threat gaps can be measured as explicit offline slices.

However, this does not grant durable training or promotion on v7. Before a
durable/promotable run, choose one of two explicit dispositions:

1. implement and re-audit v8 possible-threat features, rematerialize, and train
   the durable candidate; or
2. document acceptance of the bounded v7 threat-awareness limitation and show
   that threat-sensitive offline/manual shadow slices are safe enough for the
   narrowly approved use.

The first option is preferred before any production-directed model.

## Gates before browser/live shadow testing

All of the following should pass before a new checkpoint is shown in a browser
or live-room shadow test:

- [ ] The future 1,000-battle v7/v7 dataset materialization is explicitly
  approved, completed in a new path, and independently quality-audited.
- [ ] Exact v7 state/action versions, dimensions, ordered-name fingerprints,
  manifest checksum, split counts, and finite arrays are verified.
- [ ] The rank-only training run is separately explicitly approved.
- [ ] Tiny-overfit, training, early stopping, and single-use test evaluation
  complete without NaN/Inf; checkpoint metadata is strict and
  `production_eligible: false`.
- [ ] Validation and test rank metrics beat or credibly match simple
  max-damage/type-prior baselines with uncertainty.
- [ ] Offline slices are reported for Tera, switches, forced switches,
  non-damaging/status choices, exact versus INEXACT impact, dynamic mechanics,
  v7 batch-7/8 fields, and known possible-threat cases.
- [ ] Immunity, unavailable-action masking, perspective/privacy, Tera
  serialization, switch serialization, and fail-closed regression tests pass.
- [ ] The offline evaluator and controlled inference harness reproduce scores
  and rankings from the selected checkpoint.
- [ ] Strict live checkpoint loading rejects schema/dimension/fingerprint
  mismatches; the deferred live-loader schema-assert hardening is completed or
  the vNext harness is proven to bypass the weak legacy loader.
- [ ] Candidate-to-Showdown slot mapping and forced-switch/live parity are
  validated on recorded real extension packets before recommendation quality is
  judged in a room.
- [ ] Warm latency remains acceptable and missing/ambiguous inputs fail closed
  to no recommendation/default behavior.
- [ ] The v8 possible-threat gap is either implemented or explicitly bounded in
  the approved shadow-test protocol, with threat-sensitive cases called out.
- [ ] A manual display-only test plan is reviewed and explicitly approved,
  including stop conditions and capture/report requirements.
- [ ] Shadow mode remains opt-in/display-only; no command is auto-submitted, no
  checkpoint is promoted, and no live default changes.

Passing these gates authorizes only the specifically approved shadow test. It
does not authorize production or autonomous play.

## Current gate status

The initial planning task created only a plan and draft config. The subsequent
explicitly approved 1,000-battle materialization is recorded below. No training
or browser/live test was run, no checkpoint was promoted, and no live/default
behavior changed. Rank-only training, value-dataset work, v8 work, and
browser/live shadow testing remain blocked pending their separate gates.

## 1,000-battle v7/v7 materialization update

The explicitly approved materialization completed in
`datasets/diagnostic_1000_v7_v7_post_ditto`: 1,000/1,000 valid battles,
80,644 states, 617,687 candidates, exact 700/150/150 battle splits,
`live-private-belief-v7` 3208D plus `legal-action-v7` 552D /
`956da3d2…1bf39d7`, and all 18 structural checks passed. Match quality is
80,601 / 43 (99.9467%).

Quality audit disposition: 41 residuals are quarantined non-self-confirming
Illusion/public-replay ambiguity, but two newly surfaced Magic Bounce rows are
fixable. Reflected `Defog` is incorrectly admitted as Hatterene moveset evidence
and crowds out `Psychic`; reflected `Will-O-Wisp` is incorrectly parsed as a
Hatterene decision. Because reflected-move contamination can affect unchosen
candidate sets, the proposed rank-only run remains **blocked** pending that
source fix, regression tests, approved rematerialization, and re-audit. The
draft config now points at the actual materialized dataset path but must not be
run.

## Post-Magic-Bounce dataset update

The approved superseding materialization completed in
`datasets/diagnostic_1000_v7_v7_post_magic_bounce` and passes independent
quality audit: 1,000/1,000 valid battles, 80,635 states, 617,555 candidates,
80,594 matched / 41 quarantined unmatched (99.9492%), finite arrays, exact
700/150/150 battle splits, and frozen v7/v7 metadata/fingerprints. All nine
explicit Magic Bounce reflection rows are nondecisions; the earlier Defog and
Will-O-Wisp defects are absent. The remaining 41 rows are exactly the known
public-replay Illusion ambiguity set.

The draft rank-only config now points to this post-Magic-Bounce dataset and
uses a post-Magic-Bounce non-production output directory. The data-quality gate
for that diagnostic is open, but the training command remains
`do_not_run_unless_explicitly_approved`. Recommended next step: run only the
read-only `--validate-only` command, review its result, and seek separate
explicit approval before training.

## Post-Magic-Bounce rank-only training result

The separately approved run completed successfully on CUDA in 375.94 seconds.
It trained only action rank for 10 epochs / 10,070 optimizer steps and selected
epoch 7 by validation rank NLL after early stopping. The tiny overfit check
passed at top-1 0.96875.

Selected validation NLL/top-1/top-3/MRR:
1.175278 / 0.515985 / 0.888422 / 0.705594.
The test split was evaluated once after selection:
1.181397 / 0.507626 / 0.886274 / 0.700131.

Compared with the earlier v7/v5 test result
(1.3252 / 0.4608 / 0.8504), v7/v7 improves NLL by 0.1438, top-1 by 0.0468
absolute, and top-3 by 0.0359 absolute. This establishes the clean
post-Magic-Bounce v7/v7 model as the stronger offline diagnostic baseline.

`model.best.pt` is epoch 7 / step 7,049; `model.pt` is the final epoch 10 /
step 10,070 checkpoint. Both have exact v7/v7 metadata, finite tensors, and
`production_eligible: false`. See
`training_runs/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only_report.md`.

No checkpoint is promoted. Browser/live shadow evaluation, live/default
changes, production use, and v8 disposition remain separate approval gates.

## Selected-checkpoint offline evaluation update

The selected epoch-7 v7/v7 checkpoint now passes strict clean-command inference
loading and full-test offline evaluation. Exact schema versions, dimensions, and
ordered-name fingerprints validate; deliberate in-memory mutations of each
state/action identity field are rejected.

On 8,327 test groups, NLL/top-1/top-3/MRR are
`1.181397 / 0.507626 / 0.886274 / 0.700131`, exactly reproducing the training
report. Random legal reaches 16.6% top-1, max expected damage 38.0%, and the
move type-prior 37.7%; the model is materially stronger. It also retains the
documented improvement over v7/v5.

The slice review changes the recommended ordering:

1. a larger non-production rank experiment is technically supported by the
   strict loader, held-out metrics, and baseline margin;
2. targeted v8 possible-threat work should be designed before any
   production-directed or durable candidate, because prevention interactions
   are sparse/weak and v7 lacks explicit possible Magic Bounce / Good as Gold
   threat identity;
3. browser/live shadow preparation remains closed until recorded real-packet
   slot/forced-switch parity and v8 disposition are complete and a display-only
   run is separately approved;
4. value-dataset work remains independent: this rank-only evaluation neither
   validates nor blocks the separate larger value corpus.

The largest rank mistakes are voluntary switches (31.6% top-1), chosen Tera
moves (24.8%), and turns with more than 12 candidates (36.8%). Forced switches
(61.2% top-1 / 99.3% top-3) and obvious revenge-kill proxies
(74.6% / 97.4%) are substantially stronger. Full definitions and caveats are in
`diagnostic_1000_v7_v7_rank_only_offline_eval_report.md`.

## v8 meta-prior design update

The source-agnostic opponent-set belief design is now documented in
`v8_meta_prior_opponent_set_belief_design.md`. It separates a pinned
`MetaPriorSource`, a public-prefix-only `OpponentSetBelief` posterior over
joint set hypotheses, and compact state/action feature projections.

The code audit found that v7 keeps multiple Randbats candidates but exposes
mostly counts/entropy to the state encoder. One damage path also fills missing
ability/item/Tera from the first marginal entry, which can manufacture an
impossible pseudo-set. The v8 path must instead reserve exact mechanics for
confirmed/deterministic facts, expose semantic posterior probabilities to the
ranker, and sample complete joint hypotheses only inside belief-search nodes.

Recommended ordering is now:

1. implement and validate the source-neutral prior/posterior contracts and
   leakage tests;
2. generate a pinned Randbats prior snapshot from the actual Showdown set
   generator, then freeze compact v8 state/action slices;
3. run a tiny approval-gated v8 materialization/audit;
4. only then consider the next durable or substantially larger rank run.

Another larger v7 run remains useful only as an explicitly chosen scale-control
comparison. The separate value-dataset plan remains independent.

## Meta-prior contract implementation update

The source-neutral foundation is now implemented without model/schema wiring:

- immutable prior metadata and joint set hypotheses;
- abstract `MetaPriorSource`;
- deterministic fixture source;
- immutable `OpponentSetBelief` posterior snapshots;
- ordered public move/ability/item/Tera evidence updates;
- confirmed, possible, and ruled-out support;
- retained unknown tail mass and explicit contradiction fallback;
- public-prefix and hidden-truth no-leakage tests.

No Randbats sampling or Smogon/replay ingestion was added. No v8 state/action
features exist yet, and the v7 dimensions/fingerprints are untouched.

Recommended next sequence:

1. use the completed diagnostic replay-prefix adapter to run a held-out
   coverage, contradiction, and prefix-invariance audit with the completed
   pinned existing-data source adapter;
2. separately decide whether to build the full generator-sampled snapshot and
   convergence report described by the design;
3. audit posterior calibration on held-out public reveals without hidden-truth
   completion;
4. only then design/freeze the compact append-only v8 feature slices.

## Diagnostic replay-prefix adapter update

`opponent_set_belief_replay_adapter.py` now bridges existing parsed replay
trajectories to the source-neutral belief contracts without producing model
features. It reads only retained public protocol prefixes, supports inclusive
turn and exclusive line truncation, tracks active/known public identity
segments, and applies only explicit move/ability/item/Tera and named
prevention/reflection/immunity evidence. Explicit Poltergeist item display is
also accepted. Generic damage, generic immunity, switches, speed order, and
strategic behavior are non-evidence.

The replay tests use exact public rows from the existing Magic Bounce and
Illusion audit cases. Reflected Defog and Will-O-Wisp confirm Magic Bounce on
the reflector without polluting its move set. A later Illusion `replace`
creates a new Zoroark-Hisui segment and cannot mutate the earlier displayed
Avalugg prefix belief. Missing fixture priors remain `other_mass = 1`.

This remains diagnostic infrastructure only. No Randbats/Smogon prior
ingestion, v8 feature encoder, schema change, materialization, training, or
live behavior is included.

## Pinned existing Randbats source adapter update

`randbats_meta_prior_source.py` now wraps the exact checked-in source selected
by the old shortcut:

`data/random-battles/gen9/sets.json`

The adapter fingerprints the raw file, records the source locator, adapter and
data versions, and emits deterministic `SetPrior` records. The file has 508
species/forms and 877 role declarations. It supplies role movepools,
abilities, and Tera alternatives, but not items, exact generated four-move
sets, or empirical role weights. Priors therefore use `joint_quality =
factorized`, explicit coverage warnings, `sample_count = 0`, and a conservative
unvalidated `other_mass = 0.5` policy.

Focused tests cover known Dondozo, Hatterene, and Great Tusk declarations,
missing species, format rejection, deterministic fingerprints, and invariance
to hidden replay/context truth. See
`randbats_meta_prior_source_adapter_report.md`.

No Randbats data was scraped, regenerated, sampled, or changed. The full
generator-sampled prior snapshot remains a separate future task.

## Held-out Randbats public-prefix audit update

The full 150-battle test split of
`diagnostic_1000_v7_v7_post_ditto_manifest.json` was scanned read-only.
Coverage is 97.62% of 1,600 public identity slots and 95.07% of 487 unique
displayed species/forms. The 38 missing slots are form/alias normalization
gaps; no source row was invented or silently substituted.

Unique eventual public labels are supported at:

- abilities: 306/337 (90.80%);
- moves: 2,984/3,071 (97.17%);
- Tera types: 205/214 (95.79%).

These values measure declaration support, not calibrated frequency. The fixed
tail and equal role/alternative weighting remain too coarse for probability
claims. More importantly, 45.25% of public slots reach explicit contradiction
and 67.00% end tail-dominant. Most collapse is from items absent in the source;
the remainder exposes Trace/Transform/composite-form evidence semantics and a
small set of unsupported moves.

Prefix causality and hidden-truth invariance both pass 300/300, and the observed
Illusion/reflection cases pass. Therefore the next work should not be v8 schema
wiring. First implement and test:

1. an explicit public species/form alias policy;
2. conditioning that lets unknown tail absorb unsupported item/fact reveals
   without falsely declaring prior contradiction;
3. dynamic ability and Transform/Imposter evidence semantics that distinguish
   current copied state from base hidden-set facts.

Then rerun the same audit. See
`randbats_meta_prior_public_prefix_audit.md`.

Update: item (2) is now implemented and the audit has been re-run.
`OpponentSetBelief.update` derives per-dimension source coverage and absorbs
source-absent reveals (items for Randbats; any reveal on a missing-species
belief) into the unknown tail as confirmed public facts without forcing
`prior_contradiction`, while preserving explicit contradiction for source-covered
dimensions. The re-run audit (150-battle test split) confirms the explicit
contradiction rate fell 45.25% → **1.75%** with **0** item contradictions across
2,207 item reveals; tail-dominant fell 67.00% → 44.31%. The 28 remaining
contradictions are all source-covered: 16 dynamic/copied-state (Trace/Imposter),
9 forme-tied abilities, 2 true source gaps, 1 Struggle.

Update 2: blockers (1) alias policy and (3) dynamic-ability/Transform semantics
are now implemented and re-audited. An explicit versioned form-alias policy
(`randbats-form-alias-v1`) and copied/forme current-state semantics
(`current_state_only` for Trace, Imposter/Transform, Struggle, As One/Tera
Shell/Battle Bond/Embody Aspect) bring coverage to **100%/100%** and the explicit
contradiction rate to **0.12% (2/1600)** — only the genuine source gaps
`leavanny:pickpocket` and `beartic:dryskin` remain (correctly visible). All
causality/hidden-truth/Illusion/reflection checks pass. The source is now clean
enough for the first append-only v8 belief-feature slice (features must expose
source-quality/unknown provenance and treat coarse support as uncalibrated); the
generator-sampled snapshot remains the route to calibrated joint probabilities.
See `randbats_meta_prior_public_prefix_audit.md`.
