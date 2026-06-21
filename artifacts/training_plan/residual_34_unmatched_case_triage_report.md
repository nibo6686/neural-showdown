# Residual 34 Unmatched Case Triage Report

## Scope

This is a source/test-only triage of the 34 residual rows that remained after
the first missing-candidate reconstruction fix. No training, dataset
rematerialization, checkpoint promotion, live-default change, live-bot change,
push, `legal-action-v8`, old-gen, NatDex, Mega, Z-Move, Dynamax, or
`legal-action-v7` schema work occurred.

Checkpoint before this triage:

`11986bca237a2745a4b783aacdb4c43454ec7d22`

## Result

The 34 residual rows were audited directly with replay-prefix recomputation
against `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected`.

| Category | Count | Outcome |
| --- | ---: | --- |
| Fixable reconstruction bug | 26 | Fixed in source/tests |
| Legitimate no-leakage residual | 5 | Left unmatched |
| Replay artifact / unsupported Illusion duplicate | 3 | Left unmatched |
| Total | 34 | 8 remain |

Expected residual count after a future approved rematerialization: **8** at the
time of this triage; later reduced to **7** by the Ditto/Imposter Transform fix
(see the addendum at the end of this report).

## Fixes Implemented

### Revival Blessing Fainted-State Repair

Seven switch rows were legal after `Revival Blessing`, but the public-state
reconstructor updated HP without clearing the old `fainted` flag. Positive HP
from `|-heal|...|[from] move: Revival Blessing` now marks the Pokemon alive for
switch-candidate generation.

Fixed examples include:

- `gen9randombattle-2592073212` / `Venomoth`
- `gen9randombattle-2590070185` / `Whimsicott`
- `gen9randombattle-2593181871` / `Gumshoos`
- `gen9randombattle-2593902836` / `Skeledirge`

### Public Illusion `replace` Handling

Nineteen rows were fixed by honoring public Illusion reveal state. The parser now emits
`replace` events, the public-state reconstructor treats them as active identity
updates, and the vNext completed-team active tracker transfers moves from the
current illusion stint to the revealed species. This prevents revealed Zoroark
moves from contaminating the apparent species while allowing post-reveal
Zoroark moves and true bench switches to match naturally.

Fixed examples include:

- `gen9randombattle-2591469202` / post-reveal `Zoroark` `Sludge Bomb`
- `gen9randombattle-2591469202` / true `Staraptor` switch after Zoroark faints
- `gen9randombattle-2589571474` / `Cinderace` switch after Illusion reveal
- `gen9randombattle-2593348981` / true `Avalugg` switch after Illusion reveal
- `gen9randombattle-2594125680` / true `Tropius` switch after Illusion reveal

## Remaining 8 Rows

| Replay | Turn | Side | Parsed action | Category | Reason |
| --- | ---: | --- | --- | --- | --- |
| `gen9randombattle-2589571474` | 20 | p1 | `move: Thunder Wave` | ~~No-leakage~~ → **Fixed** | Ditto/Transform request ambiguity; **now resolved** by stint-scoped Transform reconstruction (see addendum). Matches without adding a fifth move. |
| `gen9randombattle-2591469202` | 1 | p2 | `move: Sludge Bomb` | No-leakage | Pre-reveal Illusion; matching would assign hidden Zoroark move truth to apparent Staraptor. |
| `gen9randombattle-2593348981` | 1 | p1 | `move: Will-O-Wisp` | No-leakage | Pre-reveal Illusion; matching would assign hidden Zoroark-Hisui move truth to apparent Avalugg. |
| `gen9randombattle-2593348981` | 6 | p1 | `move: Will-O-Wisp` | No-leakage | Same pre-reveal Illusion/request ambiguity. |
| `gen9randombattle-2593348981` | 18 | p1 | `move: Will-O-Wisp` | No-leakage | The `replace` reveal occurs after the move in the same turn, so the pre-action prefix cannot safely use it. |
| `gen9randombattle-2591404793` | 21 | p1 | `switch: Houndstone` | Unsupported artifact | Illusion duplicate/apparent-active switch; matching would require adding a switch to the currently active apparent species. |
| `gen9randombattle-2591404793` | 23 | p1 | `switch: Houndstone` | Unsupported artifact | Same duplicate Illusion switch pattern. |
| `gen9randombattle-2591404793` | 25 | p1 | `switch: Houndstone` | Unsupported artifact | Same duplicate Illusion switch pattern. |

## Regression Tests Added

`trainer/tests/test_benchmark_vnext_featuregen.py` now additionally covers:

- `Revival Blessing` positive heal clears stale fainted state:
  `gen9randombattle-2592073212`, `Venomoth`;
- public Illusion `replace` updates active identity for later moves:
  `gen9randombattle-2591469202`, post-reveal `Zoroark` `Sludge Bomb`;
- public Illusion `replace` restores true bench switch legality:
  `gen9randombattle-2591469202`, `Staraptor`;
- pre-reveal Illusion remains unmatched and does not leak hidden move truth:
  `gen9randombattle-2591469202`, apparent `Staraptor` `Sludge Bomb`.

## Addendum: Ditto/Imposter Transform fix (residual 8 → 7)

The residual-8 verification found that one of the five "no-leakage" rows above —
`gen9randombattle-2589571474` turn 20 p1 `move: Thunder Wave` — was actually a
fixable Ditto/Imposter Transform reconstruction bug, not an irreducible
no-leakage residual. The reconstruction merged copied moves across three
Transform stints and pulled a future `Leaf Blade` from a later stint, displacing
`Thunder Wave`.

It is now fixed with stint-scoped Transform reconstruction (parser `transform`
event, transform-aware completed-team accumulation, and a stint-scoped active
moveset helper). See `transform_imposter_reconstruction_fix_report.md`. The
Ditto case now matches without adding a fifth move and without global opponent
move leakage.

The expected residual unmatched count after a future approved rematerialization
is therefore **7**: 4 pre-reveal Illusion move cases (no-leakage) and 3
unsupported Illusion duplicate switch artifacts. The never-revealed-Zoroark
public-replay ambiguity is an irreducible public-replay limitation, not a
live-play limitation (live play knows its own true side from the Showdown
request). `scripts/recompute_v7_v7_residual_unmatched_from_replays.py`
reproduces this result (1 matched, 7 unmatched, all-as-expected).

## Gate Status

The source code is ready for an explicitly approved corrected v7/v7
rematerialization. Smoke training remains blocked until that rematerialization
is run and the fresh artifact audit confirms the expected residual count and
schema/fingerprint checks. Production and live gates remain closed.
