# diagnostic_300 v7/v7 Corrected Dataset Quality Audit

## Scope

This is a read-only quality audit of the corrected v7/v7 diagnostic dataset:

`artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/diagnostic_300_v7_v7_corrected.npz`

No training, checkpoint promotion, live-default change, live-bot change, schema
change, push, or `legal-action-v8` work occurred.

## Verdict

The corrected artifact is structurally valid and fixes the two primary blockers
from the stale v7/v7 artifact:

- the unsupported 24-vs-24 replay is excluded, eliminating its unmatched-action
  cluster;
- ordinary displayed opponent species are no longer globally uncertain.

The dataset is now suitable for post-materialization review and a smoke-training
gate decision, but this audit does not itself approve training. Remaining
unmatched action groups are still explicit and excluded from rank positives.

## Structural validation

- NPZ state array: 25,235 x 3,208, float16, finite.
- NPZ action array: 191,667 x 552, float16, finite.
- State split counts: train 20,552, validation 2,255, test 2,428.
- Replay count represented in states: 300.
- Candidate state indices are valid per materializer validation.
- Action-rank labels are valid per materializer validation.
- Action-value labels remain absent by design.
- State vectors are not duplicated per candidate.
- Embedded state/action names match schema and metadata.
- Live defaults are recorded unchanged.

## Schema and fingerprint

- State schema: `live-private-belief-v7`, 3208D.
- State ordered-name fingerprint:
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`.
- Action schema: `legal-action-v7`, 552D.
- Action ordered-name fingerprint:
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
- The frozen first 331 action names are byte-identical to `legal-action-v6`.

## Corrected vs stale comparison

| Metric | Stale `diagnostic_300_v7_v7` | Corrected `diagnostic_300_v7_v7_corrected` |
| --- | ---: | ---: |
| Battles valid / failed | 300 / 0 | 300 / 0 |
| State rows | 25,396 | 25,235 |
| Candidate rows | 189,957 | 191,667 |
| Matched decisions | 24,624 | 24,716 |
| Unmatched decisions | 772 | 519 |
| Match rate | 96.96% | 97.94% |
| Train state rows | 20,713 | 20,552 |
| Validation state rows | 2,255 | 2,255 |
| Test state rows | 2,428 | 2,428 |
| Displayed species uncertain states | 25,381 | 0 |
| 24-vs-24 replay selected | yes | no |
| Unsupported team-size replays | not checked in old preflight | 0 |
| Resumable shards | 300 | 300 |

The corrected manifest keeps validation/test split battles unchanged; only the
train replacement changed the train state/candidate distribution.

## 24-vs-24 cluster

The stale manifest included `gen9randombattle-2591563263`, an unsupported
custom 24-vs-24 battle. The corrected manifest excludes it and uses
`gen9randombattle-2591433931` as the train-split replacement.

Corrected audit results:

- `gen9randombattle-2591563263` is not selected.
- `gen9randombattle-2591563263` has zero corrected unmatched entries.
- The prior 24-vs-24 mismatch cluster is gone.
- Replacement replay `gen9randombattle-2591433931` is selected and contributes
  21 unmatched entries.

## Displayed species knownness

The stale artifact had `opponent_active_displayed_species_uncertain` active in
25,381 / 25,396 states, which contradicted the intended skilled-player public
belief calibration for ordinary switches.

The corrected artifact has this feature active in 0 / 25,235 states. This
confirms the ordinary switch/drag fix reached materialization. Explicit
Illusion/true-species guards remain covered at the contract/test layer.

## Remaining unmatched decisions

Corrected unmatched decisions: 519.

Unmatched by action kind:

- move: 482
- move_tera: 4
- switch: 33

Top unmatched replay contributors:

| Replay | Unmatched entries |
| --- | ---: |
| `gen9randombattle-2590239826` | 170 |
| `gen9randombattle-2589906015` | 119 |
| `gen9randombattle-2591230892` | 118 |
| `gen9randombattle-2590731584` | 108 |
| `gen9randombattle-2594262295` | 108 |
| `gen9randombattle-2590172478` | 95 |
| `gen9randombattle-2588642489` | 73 |
| `gen9randombattle-2589691701` | 67 |
| `gen9randombattle-2588957649` | 61 |
| `gen9randombattle-2594701956` | 59 |

These remaining cases are still explicitly excluded from rank positives. They
need triage before durable training claims, but they no longer include the
unsupported custom-team replay.

## Feature activity

- Batch 7 action-risk/probability slice: 59 features present; 50 active; 608,209
  nonzero entries.
- Batch 8 forced-decision/secondary-chance slice: 41 features present; 25
  active; 119,430 nonzero entries.

This confirms the corrected v7/v7 artifact exercises the late v7 action slices.

## Red flags and gate

Remaining red flags:

- 519 unmatched action groups remain.
- The replacement replay contributes 21 unmatched entries.
- The existing own-side replay-training future-public-reveal assumption remains
  documented in materializer warnings.
- This audit did not run training and does not approve checkpoint promotion or
  live use.

Gate status:

- Corrected materialization: complete and structurally valid.
- Old stale artifact: superseded for training and still prohibited.
- Smoke training: pending explicit acceptance/approval after this audit.
- Production/live: closed.
