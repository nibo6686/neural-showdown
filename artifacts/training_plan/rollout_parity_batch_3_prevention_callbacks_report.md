# Rollout Parity Batch 3 - Prevention Callbacks

## Result

The deterministic harness now has **32 fixtures: 27 PASS / 0 FAIL / 5 GAP**.

New prevention PASS cases:

- Psychic Terrain blocks positive-priority Quick Attack into a grounded target.
- Psychic Terrain does not block non-priority Tackle.
- Psychic Terrain does not block Quick Attack into an airborne target when
  airborne provenance is represented.
- Psychic Terrain does not block Grassy Glide in the fixture where Grassy
  Terrain is absent and the move is not priority.
- Substitute blocks Leech Seed when the target substitute and move
  substitute-blocking provenance are represented.
- Misty Terrain blocks Spore into a grounded target.
- Electric Terrain blocks Spore into a grounded target.
- Damp blocks Explosion when the target ability is represented.

Remaining explicit prevention/callback GAP cases:

- Magic Bounce reflection: Showdown reflects the move, so local rollout needs
  reflected action target/side-condition provenance instead of a simple
  prevented bit.
- Good as Gold: the controlled oracle fixture blocks Spore, but arbitrary local
  rollout states do not yet guarantee ability provenance or broad status-move
  callback routing.

Pre-existing non-prevention GAPs remain: Binding/partial trapping, Grassy
Terrain healing, and replacement Future Sight damage without target-specific
landing-damage provenance.

## Implementation

`trainer/src/neural/prevention.py` adds a dependency-free immediate-prevention
helper. It returns `available=false` rather than guessing when required
provenance is missing.

Supported local checks:

- target grounding for Psychic/Misty/Electric Terrain;
- represented move priority;
- represented move status kind;
- represented Substitute plus explicit `blocked_by_substitute`;
- represented attacker/target ability for Damp.

`trainer/src/neural/rollout_parity.py` now dispatches supported `immediate`
fixtures to this helper. `sim-core/src/rollout_parity_oracle.ts` supplies the
Showdown-backed prevention fixtures.

## Provenance still missing

The current local rollout adapter still needs richer state/provenance before
broader callback parity can be claimed:

- complete active ability provenance, including suppression/ignoring;
- target grounding under Gravity, Iron Ball, Air Balloon, Magnet Rise, Smack
  Down, and similar effects outside controlled fixtures;
- per-move target/reflection metadata for Magic Bounce and related callbacks;
- broad status-move callback routing for Good as Gold and move-specific
  bypasses;
- Substitute bypass metadata for every relevant move;
- sound/bullet/powder move flags plus Soundproof/Bulletproof/Powder volatile
  provenance.

## NatDex

This batch is scoped to Gen 9 custom-game fixtures. NatDex or older-generation
coverage needs explicit format-scoped fixtures before reusing terrain,
priority, ability, and callback-order assumptions.

## Operations and gate

No materialization or training ran. No checkpoint was promoted. No schema,
fingerprint, live default, or production path changed. The rollout-parity and
diagnostic training gates remain **closed**.
