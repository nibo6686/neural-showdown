# Moves / Actions — Showdown Truth Audit (Slice 5)

Upstream truth: the bundled
`sim-core/node_modules/pokemon-showdown` (simulator, request builder, protocol
docs, move data, condition data). This audit answers, for moves / PP /
disabled / locks, what is *legally observable* and where Slice 5 reads it.

## Where Showdown stores move slots and PP

- `sim/pokemon.ts` — each Pokémon owns `moveSlots: MoveSlot[]`, where a
  `MoveSlot` has `{ id, move, pp, maxpp, target, disabled, disabledSource, used }`
  (lines ~16–30, ~358). PP is the live integer on the slot; `maxpp` is the cap.
- The request exposes them via `getMoveRequestData()` →
  `getMoves(lockedMove, restrictData)` (lines ~925–1009). Each returned move is
  `{ move, id, pp, maxpp, target, disabled }`.

## What move identity is public for the own side

Everything in the request: the full ordered move list (id + display name), exact
`pp`/`maxpp`, `target`, and `disabled`. This is the own side's authoritative,
exact moveset.

## What move identity is public / revealed for the opponent

Nothing from the request. Opponent moves are revealed **only through the
protocol** as they are used: `|move|p2a: Species|Move Name|target`. No PP is
emitted; PP can only be *inferred* from observed usage counts. There is no
public opponent `disabled` signal except inferred from volatile messages.

## How disabled moves are represented

`disableMove(moveid, isHidden, sourceEffect)` (line ~1563) sets
`moveSlot.disabled = true | 'hidden'` and `moveSlot.disabledSource = name`. In
`getMoves` the slot's `disabled` is surfaced to the request; a move with `pp<=0`
is forced `disabled`. On the **last** active Pokémon, `disabled === 'hidden'`
becomes `false` and `maybeDisabled` is set instead (information restriction).

## How Encore / Taunt / Disable / Choice lock / recharge / two-turn are represented

- **Hard locks** go through `getLockedMove()` → `runEvent('LockMove')` (line
  ~920). When locked, `getMoves` returns a **single** move `{ move, id }` with no
  PP/target/disabled and sets `trapped = true`:
  - **Recharge** (Hyper Beam, Giga Impact) → `{ move:'Recharge', id:'recharge' }`.
  - **Two-turn / lock-in** (Outrage, Petal Dance, Thrash; `self.volatileStatus:
    'lockedmove'`) → the single locked move.
- **Soft locks** are *not* in `getLockedMove`; they disable the other slots:
  - **Choice** item → `disableMove` on every non-chosen slot.
  - **Encore** → `disableMove` on every slot except the encored move; also a
    public `|-start|…|move: Encore` volatile.
  - **Disable** → `disableMove` on one slot; public `|-start|…|Disable|Move`.
  - **Taunt** → status moves disabled (`maxMoveDisabled` / `disabledSource`);
    public `|-start|…|move: Taunt`.
- **Torment / Heal Block / Imprison** are public `-start` volatiles that
  constrain legal choices without always removing a slot from the request.

## What appears in the request object

`{ active: [{ moves:[{move,id,pp,maxpp,target,disabled}], canTerastallize?,
maybeDisabled?, trapped?, maybeTrapped?, canMega?/canZMove?/canDynamax? }],
side:{ id, pokemon:[…] }, forceSwitch?, wait?, teamPreview? }`. Top-level
`forceSwitch`/`wait` and per-active `trapped`/`maybeTrapped` are the forced-action
signals.

## What appears in protocol logs

`|move|`, `|-start|`/`|-end|` (Encore, Taunt, Disable, Torment, Heal Block,
Imprison, lockedmove), `|-prepare|` (charging move turn 1), `|cant|…|recharge`,
`|-fail|`, `|-disable|`. These are the only opponent-move evidence available.

## What sim-core currently extracts

`sim-core/src/state_extractor.ts` tracks per-Pokémon `moves` (own ids),
`revealed_moves`, and `possible_moves`, and forwards the request's
`active.moves` (with their `disabled`/`pp`). It does **not** model
recharge/two-turn/Encore/Choice locks as first-class fields.

## What current state/action feature versions encode (pre-Slice-5)

- State v2–v6: aggregate own PP fractions, a disabled-move count, force-switch /
  wait / trapped booleans, and tactical Taunt/Encore/Substitute booleans. **No**
  per-slot move identity, no opponent revealed-move identity in the state vector,
  no recharge / two-turn / Choice-lock distinction.
- Action v3: move type/category/base-power/accuracy/priority/PP and coarse
  flags, but **no** explicit self/opponent stat deltas (Draco Meteor's SpA drop
  was invisible — see `draco_action_feature_vnext_report.md`).

## What Slice 5 adds

State `live-private-belief-v7`: per-slot own/opponent move identity (hash),
known-vs-unknown slots, exact own PP vs unknown opponent PP, per-move disabled,
recharge / two-turn / soft-lock / Encore-lock / inferred-Choice-lock states,
Taunt/Torment/Heal Block/Imprison/Disable states, and provenance.

Action `legal-action-v4`: explicit per-stat self/opponent deltas, recoil /
drain / recharge / lock / pivot / drawback effects, classification, command
identity, lock compatibility, and switch-target identity.

All Slice 5 fields respect the information boundary: own = exact request,
opponent = protocol-revealed only, unknown stays explicitly unknown.
