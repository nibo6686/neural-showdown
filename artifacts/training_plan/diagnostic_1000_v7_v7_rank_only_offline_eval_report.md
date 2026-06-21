# v7/v7 Rank-Only Diagnostic Offline Evaluation

## Scope and decision

The selected non-production checkpoint loaded successfully through the strict
vNext inference harness and was evaluated on all 8,327 matched groups in the
untouched 150-battle test split. No training, rematerialization, checkpoint
promotion, browser/live shadow, live/default change, or v8 implementation
occurred.

Checkpoint:

`artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/model.best.pt`

The checkpoint remains `production_eligible: false`.

## Exact command

```powershell
$py='D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path

& $py -m neural.evaluate_vnext_action_rank `
  --config .\configs\diagnostic_1000_action_rank_v7_v7_post_ditto.rank_only.windows.json `
  --checkpoint .\artifacts\diagnostic_training\diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only\model.best.pt `
  --split test `
  --examples 12 `
  --out .\artifacts\diagnostic_training\diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only\action_rank_offline_eval_test.json
```

The JSON output is generated beside the unstaged checkpoint and is not part of
the commit.

## Load and compatibility checks

Strict inference load: **PASS**.

- state: `live-private-belief-v7`, 3208D, fingerprint
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`;
- action: `legal-action-v7`, 552D, fingerprint
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`;
- both ordered-name fingerprints were required and validated;
- model state loaded without missing or unexpected tensors;
- inference used the existing precomputed test states/candidates only.

The evaluator also copied the checkpoint metadata in memory, changed one
identity field at a time, and confirmed hard rejection for:

- wrong state schema;
- wrong action schema;
- wrong state dimension;
- wrong action dimension;
- wrong state ordered-name fingerprint;
- wrong action ordered-name fingerprint.

No tampered checkpoint was written.

## Aggregate held-out metrics

| Method | NLL | top-1 | top-3 | MRR |
| --- | ---: | ---: | ---: | ---: |
| **v7/v7 rank model** | **1.1814** | **0.5076** | **0.8863** | **0.7001** |
| type-prior move | — | 0.3768 | 0.7290 | 0.5784 |
| max expected damage | — | 0.3804 | 0.6723 | 0.5521 |
| max KO chance | — | 0.3555 | 0.6722 | 0.5363 |
| random legal | — | 0.1659 | 0.4791 | 0.3902 |

The evaluator exactly reproduces the training report's selected-checkpoint test
NLL/top-1/top-3/MRR. The model beats the best heuristic top-1 by 12.7 points and
the best heuristic top-3 by 15.7 points. It ranks the replay label first while
max expected damage does not in 1,923 groups; the reverse occurs in 864 groups.

Compared with the prior v7/v5 diagnostic test result
(`1.3252 / 0.4608 / 0.8504` NLL/top-1/top-3), v7/v7 improves NLL by 0.1438,
top-1 by 4.68 points, and top-3 by 3.59 points.

## Held-out slices

Slices can overlap. “Magic Bounce replay” and “Good as Gold replay” are broad
replay-context slices found from the frozen source logs, not claims that every
decision directly invoked the ability. “Prevention interaction” is the narrower
candidate-feature slice. “Obvious revenge kill” is a reproducible proxy:
recent target faint evidence plus at least 0.75 chosen-action KO chance.

| Slice | groups | NLL | top-1 | top-3 | max-damage top-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Normal move choice | 5,972 | 0.9917 | 0.5764 | 0.9385 | 0.5184 |
| Forced switch / all-switch group | 139 | 0.7751 | 0.6115 | 0.9928 | 0.5180 |
| Voluntary switch | 2,216 | 1.7182 | 0.3159 | 0.7387 | 0.0000 |
| Low HP or endgame | 4,164 | 1.0462 | 0.5454 | 0.9253 | 0.3710 |
| Tera available | 5,580 | 1.2212 | 0.5014 | 0.8747 | 0.3728 |
| Tera already used or chosen now | 1,061 | 1.3594 | 0.4307 | 0.8313 | 0.3327 |
| Hazards or removal context | 3,398 | 1.1680 | 0.5244 | 0.8893 | 0.3796 |
| Setup or sweep context | 2,478 | 1.0538 | 0.5500 | 0.9266 | 0.4730 |
| Obvious revenge-kill proxy | 1,097 | 0.7433 | 0.7457 | 0.9736 | 0.8232 |
| Prevention interaction | 17 | 1.5210 | 0.4118 | 0.7647 | 0.2941 |
| Magic Bounce replay context | 160 | 1.2939 | 0.4313 | 0.9063 | 0.3500 |
| Good as Gold replay context | 36 | 1.3746 | 0.5000 | 0.8333 | 0.3056 |
| Illusion/displayed-species signal | 5 | 0.8537 | 0.4000 | 1.0000 | 0.6000 |
| More than 12 candidates | 321 | 1.6304 | 0.3676 | 0.7695 | 0.2991 |

The prevention and Illusion slices are too small for a confident safety claim.
They are useful as failure detectors, not promotion evidence.

## Mistake patterns

- **Voluntary switching is the largest structural weakness.** Top-1 is 31.6%;
  937 misses choose a move over the replay switch, and another 562 choose the
  wrong switch. Forced replacement is much easier at 61.2% top-1 / 99.3% top-3.
- **Tera commitment remains weak.** Chosen `move_tera` test accuracy is 24.8%
  top-1 / 58.9% top-3. In the broader Tera-used/chosen slice, the most common
  distinctive error is `move_tera -> move` (128 cases).
- **Candidate count matters.** Above 12 candidates, top-1 falls to 36.8% and
  NLL rises to 1.6304.
- **Prevention-sensitive decisions remain uncertain.** The 17 feature-level
  prevention interactions reach only 41.2% top-1 / 76.5% top-3. This is
  directionally consistent with the documented v7 absence of explicit possible
  Magic Bounce / Good as Gold threat features.
- **Most top-1 misses remain useful shortlist recommendations.** In 3,153
  groups, top-1 is wrong but top-3 contains the replay label. That is 76.9% of
  the 4,100 top-1 errors. The dominant pair is choosing the wrong move for a
  move label (1,924), followed by wrong-switch selection (527) and predicting a
  move for a switch label (458).
- **Strong regions are ordinary attacks, endgames, setup contexts, and obvious
  revenge kills.** These slices all retain high top-3 accuracy; the revenge-kill
  proxy reaches 97.4% top-3.

## Gate disposition

This offline evaluation supports:

1. **larger non-production rank training**, because v7/v7 strictly loads,
   reproduces held-out metrics, and materially beats random/legal, damage, and
   prior v7/v5 baselines;
2. **targeted v8 threat-awareness work**, because prevention-sensitive examples
   remain sparse and weak and v7 cannot distinguish all relevant possible
   Magic Bounce / Good as Gold threats explicitly.

It does **not** provide new evidence for value-dataset quality; that remains a
separate data program. It also does **not** by itself open browser/live shadow:
candidate/slot parity on recorded real extension packets, explicit v8
disposition, fail-closed checks, and a separately approved display-only plan
remain required.

No promotion or production/live gate is opened.
