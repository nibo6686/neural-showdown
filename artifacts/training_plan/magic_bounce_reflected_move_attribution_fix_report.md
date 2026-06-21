# Magic Bounce Reflected-Move Attribution Fix Report

## Scope

Targeted source/test repair for the two Magic Bounce failures surfaced by the
1,000-battle v7/v7 audit. No training, full rematerialization, checkpoint
promotion, live/default change, schema change, v8 work, or push occurred.

The materialization/audit baseline was checkpointed first at
`03ad2fc` (`checkpoint: diagnostic 1000 v7 v7 materialization audit`).

## Targeted reproduction

The read-only reproducer is:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
& $py scripts\recompute_magic_bounce_reflected_move_cases.py
```

Before the fix it reproduced both failures:

- `gen9randombattle-2589608300`, turn 5, p2:
  reflected `Defog` was present in Hatterene's completed moveset. At the later
  turn-24 `Psychic` decision, request-like four-slot reconstruction offered
  `Defog`, `Draining Kiss`, `Mystical Fire`, and `Nuzzle`, crowding out
  `Psychic`; the replay choice could not match.
- `gen9randombattle-2594129364`, turn 2, p2:
  reflected `Will-O-Wisp` (`[from] ability: Magic Bounce`) was labeled
  `move_tera: Will-O-Wisp`, even though Hatterene did not select that action.

The pre-fix targeted command exited 1 with all four desired checks false.

## Fix

`vnext_labels.is_magic_bounce_reflection` recognizes only the explicit public
protocol provenance marker `[from] ability: Magic Bounce`.

That predicate is applied at both attribution points:

1. `chosen_action_label` returns no actor-choice label for a reflected move;
2. completed-team action reconstruction does not treat a reflected move as
   learned/selected moveset evidence for the reflector.

No hidden ability, moveset, request payload, or future opponent fact is
inferred. The fix removes an illegal reflected candidate instead of adding a
candidate. Existing fail-closed possible-threat behavior is unchanged.

## Post-fix targeted result

The same command now exits 0:

- Hatterene moves: `Draining Kiss`, `Mystical Fire`, `Nuzzle`, `Psychic`;
- reflected `Defog` absent;
- turn-24 `Psychic` present and matched;
- reflected `Will-O-Wisp` label is `None`;
- all targeted checks pass.

Regression coverage:

- replay-backed completed-moveset/candidate test for reflected Defog and later
  Psychic;
- replay-backed no-choice-label test for reflected Will-O-Wisp;
- direct label/provenance unit test for the Magic Bounce marker.

## Dataset disposition

The checked-in/generated
`diagnostic_1000_v7_v7_post_ditto` artifact remains unchanged and stale with
respect to this source fix. It still reports 80,601 matched / 43 unmatched and
contains at least one false-positive reflected decision (`Defog`) in addition
to the two audited unmatched effects.

After a future explicitly approved full rematerialization:

- the two audited Magic Bounce residuals should no longer be unmatched;
- expected unmatched count is **41**, all currently classified as quarantined
  non-self-confirming Illusion/public-replay ambiguity;
- reflected protocol move rows should not become decision states or moveset
  evidence.

Rank-only training remains blocked until that future artifact is materialized
and re-audited. No claim is made that counts other than the expected 43 → 41
residual change will be byte-identical, because removing reflected false
decisions/candidates correctly changes the materialized tables.
