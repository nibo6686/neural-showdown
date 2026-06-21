# diagnostic_300_v7_v7 Dataset Quality Audit

## Scope and verdict

This is a read-only audit of
`datasets/diagnostic_300_v7_v7/diagnostic_300_v7_v7.npz` and its metadata.
No dataset was materialized or changed, no training ran, and no checkpoint or
live setting changed.

**Verdict:** the artifact is structurally valid and useful as a frozen
materializer/schema/feature-coverage diagnostic, but it is **not approved for
tiny smoke training**. Fix and test the replay-state/materializer reconstruction
issues below before rematerializing or training. Do not implement
`legal-action-v8` first: a v8 threat slice would not repair mislabeled or
under-informed v7 states.

## Structural integrity

- Source: commit `63484055aad7b5d45102fa53e431fe682cc3bb45`.
- Battles: 300/300 valid, 0 failed; battle splits exactly 210 train / 45
  validation / 45 test.
- State matrix: `(25,396, 3,208)`, `float16`.
- Action matrix: `(189,957, 552)`, `float16`.
- State schema: `live-private-belief-v7`, 3208D.
- Action schema: `legal-action-v7`, 552D.
- Action ordered-name fingerprint:
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
- State rows by split: 20,713 / 2,255 / 2,428.
- Candidate rows by split: 155,853 / 16,683 / 17,421.
- All state/action values are finite. Candidate state indices are ordered and
  in range. No duplicate `(candidate_kind, candidate_action_index)` was found
  within a state.
- `observed_actions` and `action_rank_labels` are byte-identical. Every matched
  group has exactly one positive; there are no multi-positive groups.
- The frozen 331D v6 prefix of every v7 candidate is byte-identical to the
  corresponding `diagnostic_300_v7_v6` candidate. Apart from expected schema
  metadata/source-commit differences, non-action arrays match the v7/v6
  artifact.

These checks find no archive corruption, schema drift, split crossing, NaN/Inf,
or v7-prefix regression.

## Labels and candidate sets

- Matched action groups: 24,624 / 25,396, for a **96.9602% match rate**.
- Unmatched groups: 772 (3.0398%); these retain state/value rows but have no
  candidate rows or action-rank positive.
- Initial deployments excluded as non-decisions: 600.
- Candidates per all state rows: mean **7.48**, min **0**, median **7**, max
  **13**.
- Candidates per candidate-bearing state: mean **7.71**, min **1**, median
  **7**, max **13**.
- Empty candidate groups: 772, exactly the unmatched-label states.

Candidate/positive counts:

| Kind | Candidates | Positives |
| --- | ---: | ---: |
| ordinary move | 73,836 | 17,960 |
| Tera move | 42,034 | 426 |
| switch | 74,087 | 6,238 |

The unmatched groups are a material quality concern, not just a reported
aggregate:

- 654 are `move_missing_from_reconstructed_active_moves`;
- 118 are `switch_target_missing_from_pre_action_legal_roster`;
- 769 are in train, 1 in validation, and 2 in test;
- 48 replays are affected;
- one train replay contributes 253 unmatched states (32.77% of all unmatched
  states), after its reconstructed roster diverges; the top ten replays
  contribute 68.65%.

The concentration follows the fixed battle split rather than indicating split
crossing, but it creates avoidable train-only missing-label bias. The affected
states should not be accepted for a smoke-training baseline until roster/form
and active-move reconstruction is repaired or the exclusion policy is made
explicit at the state level.

## Action and mechanic coverage

Action-class candidate/positive counts include:

| Class | Candidates | Positives |
| --- | ---: | ---: |
| damaging | 65,962 | 11,313 |
| status | 29,193 | 2,429 |
| setup | 6,602 | 1,947 |
| recovery | 8,642 | 1,508 |
| hazards | 2,765 | 653 |
| pivot class | 3,491 | 466 |
| protect | 2,706 | 536 |

There are no forced-switch states or forced-switch candidate commands in the
artifact. All 74,087 switch rows are ordinary switch commands. This is a
coverage omission for forced replacement behavior, not structural corruption.

The eight appended v7 slices are active:

| Slice | Fields nonzero | Candidate rows with any nonzero |
| --- | ---: | ---: |
| status/stat | 21 / 30 | 41,822 |
| volatile | 13 / 14 | 14,290 |
| item effects | 9 / 13 | 4,387 |
| timing/priority | 15 / 18 | 8,199 |
| HP side effects | 12 / 14 | 19,242 |
| field/side effects | 20 / 32 | 6,325 |
| risk/probability | 49 / 59 | 115,870 |
| forced decision/secondary | 25 / 41 | 29,932 |

All 115,870 move/Tera rows exercise the Batch 7 risk slice. More specific
coverage is:

- branch pressure: 1,263 candidates / 192 positives;
- delayed pressure: 66 / 11;
- residual pressure: 6,613 / 932;
- self-pivot replacement pressure: 3,321 / 446;
- self-KO pressure: 17 / 3;
- phazing: 740 / 123;
- item-trigger group: 2,370 / 360, primarily the unknown/generic branch;
- base secondary chance: 23,484 / 4,269;
- known-modified secondary chance: 77 / 23;
- explicit secondary modifier/blocker coverage: **0 / 0**.

The possible-absorb risk bit fires on 2,111 candidates / 312 positives, and the
known ability-blocker bit fires on 490 / 111. Multi-hit-known fires on 926 / 177
and Loaded Dice on 83 / 14; Skill Link does not fire. Shield Dust, Covert Cloak,
Serene Grace, and Sheer Force modifier/blocker fields do not fire. Thus Batch
7/8 are not globally zero, but several rare or belief-sensitive branches are
untested by this sample.

## Public-belief and no-leakage-sensitive findings

No true hidden opponent team or private request payload is recorded in metadata,
and this audit found no direct hidden-opponent identity feature. The metadata
does explicitly disclose an own-side reconstruction proxy: later public
reveals may complete own roster/moves. That approximates information the player
would have received privately, but it is not the actual timestamped request
payload and is implicated in the roster/move mismatches above.

Materialized public-belief indicators show:

- possible opponent ability count: 25,261 states;
- revealed opponent ability: 2,772;
- revealed opponent item: 3,668;
- own active ability known: 2,550;
- own active item known: 5,359;
- opponent displayed species uncertain: **25,381 / 25,396 states**;
- Illusion revealed: 15.

The near-global displayed-species uncertainty contradicts the intended
calibration that Illusion guards only genuinely unresolved identities.
Ordinary switch handling currently marks displayed species uncertain, so
species-singleton public ability inference is effectively unavailable in this
materialized path. Exact own request facts are also only sparsely represented,
confirming that the recently added public-belief contracts remain largely
contract-level rather than integrated into replay extraction/materialization.

This is conservative rather than hidden-truth leakage, but it deprives the
ranker of information a skilled player has and prevents this artifact from
validating the intended calibrated belief representation.

## Possible-threat audit in the materialized data

The previous representation gaps are visible:

- no action/state field name directly identifies possible Unaware, Magic Bounce,
  Good as Gold, Levitate, Covert Cloak, Shield Dust, Inner Focus, or a specific
  Water Absorb-like identity;
- absorb risk is present only as a generic known-or-possible applicability bit;
- known blocker coverage exists, but specific possible blocker identities do
  not;
- explicit secondary-blocker/modifier fields are zero in this sample;
- species-correlated indirect learning is weakened by the near-global
  displayed-species-uncertain flag.

Therefore v7 remains only partially possible-threat-aware. A future append-only
v8 slice is still appropriate, but only after the current dataset-state
reconstruction issue is fixed and a clean v7 baseline can be audited.

## Decision and next gate

1. **Do not train this artifact yet.**
2. Fix the replay materializer/state extraction so:
   - ordinary switches do not globally mark displayed species uncertain;
   - own legal roster/moves are reconstructed without persistent divergence;
   - transformed/form-changed names match legal roster candidates;
   - forced-replacement decisions are either represented or explicitly
     excluded with audited coverage.
3. Add integration tests over ordinary switch, Illusion/replace, Tera/form
   changes, roster continuity, and action-label matching.
4. With explicit approval, rematerialize to a new artifact or replace this
   diagnostic artifact under the repository's dataset policy, then repeat this
   audit.
5. Only after a clean v7/v7 smoke baseline should the append-only
   `legal-action-v8` possible-threat slice become the next schema task.

The dataset remains valid for read-only schema, prefix, distribution, and
materializer diagnostics. Tiny smoke training, checkpoint promotion, and
production/live use remain closed.
