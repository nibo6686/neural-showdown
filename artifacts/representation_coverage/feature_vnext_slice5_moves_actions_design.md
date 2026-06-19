# Feature vNext Slice 5 — Moves and Action Consequences Design

**Status:** implemented, diagnostic-only
**New immutable state version:** `live-private-belief-v7`
**New diagnostic action version:** `legal-action-v4`
**State dimension:** 3208
**Action dimension:** 269
**State prefix chain:** v2 115D → v3 217D → v4 765D → v5 2293D → v6 2493D → v7 3208D
**Action prefix:** legal-action-v3 165D → legal-action-v4 269D

## Versioning decision

v6 stays immutable at 2493 dimensions. Slice 5 appends 715 explicitly named
state fields to form v7. `legal-action-v3` (165D) stays immutable; Slice 5
appends 104 explicitly named action fields to form `legal-action-v4`.

The live/default builder remains `live-private-belief-v2` and the
strict production checkpoint validator (`_validate_live_private_checkpoint`)
still only accepts v1/v2 — so v7, like v3–v6, is diagnostic and is *rejected* by
production loading. Old action-ranker checkpoints continue to load against the
unchanged `legal-action-v3`.

## State side (`live-private-belief-v7`)

Perspective-normalized; `own` is always the request side, `opponent` the foe.
715 fields in four blocks.

### Own active move slots (296D = 4 × 74)

Four ordered slots taken from the live `request.active[0].moves`. Each slot:

- 64-dim two-family bucket hash of the move identity;
- `known` / `unknown` (an absent request slot is explicitly *unknown*, never
  collapsed to a real move);
- `disabled` (the request's per-move disabled flag);
- `pp_known` + `pp_norm` (exact request PP when present);
- 5-way provenance: unknown / request / protocol / sim_core / inferred.

### Opponent active move slots (296D = 4 × 74)

Four ordered slots taken from the perspective-relative
`revealed_moves_by_species[active]`. Same layout, with `revealed`/`unknown`
instead of `known`/`unknown`. Opponent exact PP is never request-visible, so
`pp_known` is always 0 (`pp_norm` 0); provenance is `protocol`.

### Own constraints (101D)

- known/unknown/disabled/selectable move counts (normalized);
- recharge state, two-turn-lock state, single-move (soft) lock state, and
  Encore-lock state, each unknown/inactive/active;
- `choice_lock_inferred` (one selectable move among several disabled, with no
  Encore volatile);
- `force_switch`, `must_recharge`, `wait_forced`, `trapped`;
- Taunt, Torment, Heal Block, Imprison, and Disable, each unknown/inactive/active;
- `substitute_present` (Substitute is already encoded by the immutable v2
  tactical features `own_active_substitute` — this is an additive convenience
  copy, not a re-derivation);
- a 64-dim hash of the constraint-locked move identity (the single selectable /
  locked move when a lock is active).

### Opponent constraints (22D)

- revealed/unknown move-slot counts;
- Taunt, Torment, Heal Block, Imprison, Disable, and Encore lock, each
  unknown/inactive/active (from public protocol volatiles);
- `substitute_present`;
- `pp_known_any` (always 0; opponent exact PP is never legally known).

### Lock / constraint extraction (Showdown-faithful)

- **Recharge** — `request.active[0].moves == [{move: Recharge, id: recharge}]`
  with no PP (Showdown's hard `lockedMove === 'recharge'`).
- **Two-turn / lock-in** — a single request move with no PP and id ≠ recharge
  (Outrage / Petal Dance / charging moves; Showdown's `getLockedMove`).
- **Soft single-move lock** — all slots present, exactly one selectable
  (Choice item or Encore disabling the rest via `disableMove`).
- **Encore** — public `-start … move: Encore` volatile.
- **Choice (inferred)** — soft single-move lock with no Encore volatile.

Disable / Heal Block / Imprison are tracked in a **separate**
`constraint_volatiles` set in `tactical_state` so the immutable v2–v6
`volatiles` list (and `own_active_volatile_count_norm`) stays byte-identical.

## Action side (`legal-action-v4`, 104 new fields)

Appended to the unchanged 165D `legal-action-v3`:

- `self_stat_delta_{atk,def,spa,spd,spe,accuracy,evasion}` — signed, ÷2 clipped;
- `opponent_stat_delta_{...}` — signed;
- `self_has_stat_drop` / `self_has_stat_boost` / `opponent_has_stat_drop`;
- `effect_recoil`, `effect_drain_or_heal`, `effect_recharge`,
  `effect_locks_user`, `effect_switch_move`, `effect_has_drawback`,
  `effect_priority_norm`;
- classification: `class_{damage,status,setup,recovery,hazard,pivot,protect}`;
- command identity: `cmd_{move,switch,tera_move,forced_switch}`;
- lock compatibility: `lock_disabled`, `lock_encore_compatible`,
  `lock_choice_compatible`;
- switch target: `switch_target_known`, `switch_target_slot_norm`, and a 64-dim
  switch-target species hash.

Stat deltas are parsed structurally from the bundled `moves.ts`:

- `self: { boosts }` → user drops/boosts (Draco Meteor `spa: -2`, Close Combat);
- `move.self = { boosts }` (dynamic) → Curse's mixed `{atk:+1, def:+1, spe:-1}`;
- top-level `boosts` with `target: self` → user setup (Bulk Up, Swords Dance);
- top-level `boosts` on a foe-target status move → opponent drops (Growl, Leer).

#### Exact stage-delta fidelity and normalization

Per-stat magnitude and sign are preserved exactly — a self drop is **not**
flattened to a single `has_stat_drop` flag. The raw integer stage delta parsed
from `moves.ts` is written per stat as:

```
normalized_delta = clip(raw_stage_delta / 2, -1.0, +1.0)
```

So a two-stage change maps to ±1.0 and a one-stage change to ±0.5 — distinct, not
aliased. Worked examples (raw → `self_stat_delta_*`):

| Move | Raw self delta | Normalized field(s) |
|---|---|---|
| Draco Meteor / Overheat / Leaf Storm | `spa: -2` | `self_stat_delta_spa = -1.0` |
| Close Combat | `def: -1, spd: -1` | `def = -0.5, spd = -0.5` |
| Superpower | `atk: -1, def: -1` | `atk = -0.5, def = -0.5` |
| Curse (non-Ghost) | `atk: +1, def: +1, spe: -1` | `atk = +0.5, def = +0.5, spe = -0.5` |
| Bulk Up | `atk: +1, def: +1` | `atk = +0.5, def = +0.5` |

Only the affected stats are nonzero; all other `self_stat_delta_*` stay 0.
`self_has_stat_drop` / `self_has_stat_boost` are derived *in addition to* (not
instead of) the exact per-stat fields. `effect_priority_norm` uses
`(priority + 7) / 14`; all other slice-5 effect fields are 0/1.

**Curse Ghost/non-Ghost note:** the stat change lives in an `onModifyMove` that
runs only for non-Ghost users (`move.self = { boosts: {...} }`); Ghost Curse
sacrifices HP and has no stat delta. The user's typing is not statically knowable
from `moves.ts`, so the parser returns the non-Ghost `{+Atk, +Def, -Spe}` case.

Fidelity is asserted at both layers (raw parser output and feature-vector fields)
in `trainer/tests/test_action_stat_delta_fidelity.py`.

## Representation, not tactics

No move-specific recommendation rule is added. The point is that future training
can *learn* that Draco Meteor lowers the user's Special Attack and that Curse
trades Speed for bulk — the features expose the consequence; they do not encode a
policy.

## Compatibility and scope

- v2/v3/v4/v5/v6 names, dimensions, and ordering are unchanged; v6 is the exact
  v7 prefix.
- `legal-action-v3` is unchanged and is the exact v4 prefix.
- No dataset, checkpoint, live default, or production model changed.
- Full reindex/retraining remains blocked (see `retraining_blockers.md`).
