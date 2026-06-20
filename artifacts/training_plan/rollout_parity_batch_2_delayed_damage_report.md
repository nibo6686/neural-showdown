# Rollout Parity Batch 2 — Delayed Damage

## Result

The deterministic harness now has **26 fixtures: 19 PASS / 0 FAIL / 7 GAP**.

New delayed-damage PASS cases:

- Future Sight schedules without immediate damage.
- It remains pending through the intervening turn.
- It lands at the end of the second later turn.
- It targets the current occupant of the original target slot after a switch.
- A duplicate Future Sight fails without overwriting the original event.
- Doom Desire shares the timing and slot mechanism.

An explicit replacement-damage GAP remains when exact landing damage for the
new slot occupant is unavailable.

## Implementation

`trainer/src/neural/delayed_damage.py` provides a focused queue with:

- move (`futuresight` or `doomdesire`);
- scheduled turn and derived landing turn;
- source side and source Pokémon identity;
- target side and slot;
- target-specific landing damage;
- damage provenance.

Resolution looks up the active occupant at landing time. Empty/fainted slots
consume the event without damage. If a replacement is present but lacks exact
target-specific landing damage, resolution returns unavailable rather than
using the original target's value.

## Provenance boundary

The queue/timing/slot mechanics are represented. General damage generation is
not.

For arbitrary battle states, exact Gen 9 Future Sight/Doom Desire damage may
need:

- source species, level, natural/current Special Attack, boosts, and active
  versus switched-out state;
- source item/ability and relevant ally effects;
- current target species, exact HP/defensive stats, types, ability, item, and
  Tera/type changes;
- landing-time weather, terrain, screens, and other field context;
- format/generation.

Current approximate state does not expose this complete scheduled-attack
provenance or an exact landing-time damage resolver. Controlled fixtures supply
target-specific damage with explicit bundled-Showdown provenance.

## Architecture boundary

Future Sight remains non-immediate in `legal-action-v7`. No click-time action
field was changed to predict future HP. The queue is rollout transition
behavior only.

## NatDex

The implementation is scoped to Gen 9 timing. Older generations differ in
Future Sight/Doom Desire typing, damage timing, and source/target snapshot
semantics. NatDex support needs format-scoped fixtures and must not reuse Gen 9
damage provenance rules blindly.

## Operations and gate

No materialization or training ran. No checkpoint was promoted. No schema,
fingerprint, live default, or production path changed. The rollout-parity and
diagnostic training gates remain **closed**.
