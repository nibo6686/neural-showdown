# Missing Candidate Reconstruction Fix Report

## Scope

This report covers a source/test-only fix for the residual missing legal
candidate paths found after the corrected `diagnostic_300_v7_v7_corrected`
materialization.

No training, dataset rematerialization, checkpoint promotion, live-default
change, live-bot change, push, `legal-action-v8` work, or `legal-action-v7`
schema change occurred.

Checkpoint before this fix:

`96e56696798dab0b5c884e3d05bcb075cf262eb7`

## Pre-Fix Residual State

Authoritative source:

`artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/decision_skip_audit.jsonl`

Pre-fix residual unmatched rows:

| Category | Count |
| --- | ---: |
| Missing reconstructed active move | 486 |
| Missing switch target in pre-action legal roster | 33 |
| Total | 519 |

The checked-in dataset remains stale with respect to this source fix. A future
approved rematerialization is required before dataset-level metrics change.

## Root Causes Fixed

1. `Struggle` slot pressure

   Replay-observed `Struggle` was stored alongside the active Pokemon's real
   moves and then sorted into the four request-like active move slots. This
   displaced real moves such as `Thunder Wave`, `Wish`, `Toxic`, `Wave Crash`,
   and `Substitute`.

2. Battle-form roster aliases

   Transient or cosmetic forms were treated as separate roster members. This
   caused duplicate slots such as `Terapagos` plus `Terapagos-Terastal`,
   `Palafin` plus `Palafin-Hero`, and `Polteageist-Antique` plus `Polteageist`,
   pushing real sixth-slot switch targets out of the capped six-slot roster.

3. Alias-aware switch matching

   Replay switch commands can name a transient battlefield form while the legal
   roster candidate is the party species. `switch: Terapagos-Terastal` should
   match a legal `switch: Terapagos` candidate for action-rank labeling.

4. Source-move merge across safe aliases

   Active-tracker reconstruction and the broader completed-team reconstruction
   could split moves across alias forms. The vNext reconstruction now merges
   completed source moves back into the anchored roster slot by safe roster
   alias.

## Guardrails Preserved

- `legal-action-v7` remains 552D with fingerprint
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
- The materializer still calls `_legal_actions_from_private_state` with an
  empty chosen label; unmatched actions are not hidden by chosen-action
  fallback injection.
- `Struggle` is represented as an exhaustion fallback candidate only when the
  reconstructed active Pokemon has replay-observed `Struggle`; it no longer
  displaces the four real active moves.
- Illusion-like rows remain unmatched when reconstructing the candidate would
  require assigning a hidden true move to an apparent public species.
- Opponent belief construction still does not read full completed-team hidden
  move lists.

## Focused Replay Audit After Source Fix

I reran a lightweight replay-prefix audit over the same 519 previously skipped
rows. This audit recomputes legal candidates from raw replay logs using the new
source code; it does not rematerialize the dataset.

| Status | Count |
| --- | ---: |
| Previously skipped rows audited | 519 |
| Now naturally matched | 485 |
| Still unmatched | 34 |

Remaining unmatched rows:

| Category | Count |
| --- | ---: |
| Switch target still missing | 19 |
| Move still missing | 15 |

The remaining rows are dominated by Illusion/ambiguous-roster cases and
apparent five-move conflicts where adding the replay command as a candidate
would be more likely to create an illegal candidate or hidden-information leak
than to reconstruct a trustworthy legal request.

Follow-up triage in `residual_34_unmatched_case_triage_report.md` found 26 of
those 34 were still safely fixable: 7 stale-fainted Revival Blessing switch
targets and 19 public Illusion `replace` / active-stint reconstruction rows.
The post-triage lightweight replay-prefix audit now naturally matches 511 of
the old 519 skipped rows and leaves 8 residual rows: 5 legitimate no-leakage
move cases and 3 unsupported Illusion duplicate switch artifacts. The checked-in
dataset remains stale until a future explicitly approved rematerialization.

## Regression Tests Added

`trainer/tests/test_benchmark_vnext_featuregen.py` now covers:

- top replay support-move recovery:
  `gen9randombattle-2592785310`, `Gholdengo` `Thunder Wave`;
- transient-form switch matching:
  `gen9randombattle-2587967313`, `Terapagos-Terastal` vs `Terapagos`;
- roster alias dedupe preserving sixth switch target:
  `gen9randombattle-2589411985`, `Glalie`;
- `move_tera` recovery:
  `gen9randombattle-2589811158`, `Glaceon` `move_tera: Wish`;
- `Struggle` as an exhaustion fallback without displacing real moves:
  `gen9randombattle-2587977426`, `Lapras`;
- illegal-candidate/no-leakage guard:
  `gen9randombattle-2591469202`, Illusion-disguised `Sludge Bomb` remains
  unmatched and does not leak into the opponent belief.

## Verification

Focused tests:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
& 'D:\Anaconda\envs\neuralgpu\python.exe' -m pytest `
  trainer/tests/test_benchmark_vnext_featuregen.py `
  trainer/tests/test_vnext_labels.py -q
```

Result: `33 passed`.

Broader verification is recorded in the final task handoff. This fix remains a
source/test/report change only until a future explicitly approved
rematerialization is run.
