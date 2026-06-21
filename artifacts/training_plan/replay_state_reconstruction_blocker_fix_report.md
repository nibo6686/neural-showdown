# Replay-State Reconstruction Blocker Fix

## Scope and verdict

This task fixed the two primary blockers identified by the read-only
`diagnostic_300_v7_v7` audit without training or rematerializing:

1. the replay responsible for 253 unmatched states is now rejected as outside
   the frozen six-slot representation;
2. ordinary protocol switches no longer mark the public displayed species as
   uncertain.

The existing dataset was built before these fixes and is **known-stale for
training**. Keep it as an immutable audit artifact; do not train it. A
replacement six-Pokemon manifest and an explicitly approved full v7/v7
rematerialization are required before smoke training.

## 253-mismatch replay root cause

- Replay: `gen9randombattle-2591563263`
- Existing shard:
  `_shards/f8e0eae59ee4c86e8fce5a3356604b6f22279b8d.pkl`
- Existing shard: 372 states, 119 matched groups, 253 unmatched groups.
- Mismatches: 168 missing reconstructed active moves and 85 missing switch
  targets.

This was not a standard six-Pokemon Gen 9 Random Battle. Its public protocol
contains `maxteamsize=24`, `|teamsize|p1|24`, and `|teamsize|p2|24`.
The frozen state representation has six roster slots and the legal-action
builder assumes the standard four moves plus Tera variants and five bench
switches. Once later team members appeared, active Pokemon and switch targets
fell outside the reconstructed six-member roster, causing persistent mismatch
from turn 16 onward.

Supporting custom 24-member teams would require a different representation and
is out of scope. Silently truncating them is unsafe; rejecting them before
materialization is the correct fix.

## Team-size fix

- Replay profiling records explicit public `|teamsize|` values.
- Explicit team sizes outside 1–6 are no longer `diagnostic_300` eligible.
- Full-manifest preflight rejects entries exceeding the frozen six-slot schema.
- Per-battle materialization also fails clearly if preflight is bypassed.

The current manifest has exactly one unsupported entry:
`gen9randombattle-2591563263` with p1=24 and p2=24. It must be replaced by a
standard eligible train-split replay before future materialization. Current
preflight now intentionally rejects the old manifest.

## Displayed-species uncertainty root cause and fix

`TacticalStateTracker._handle_switch` unconditionally set
`active_displayed_species_uncertain = True` for every ordinary switch/drag.
The old dataset consequently marked opponent displayed species uncertain in
25,381 / 25,396 states.

That bit is an Illusion/true-identity guard; it does not mean the public
displayed species string is unknown. The fix:

- ordinary switch/drag events store displayed/base/current species as public
  known and leave the guard false;
- the roster entry is refreshed with the same public identity fields;
- public `replace` remains the explicit Illusion reveal path;
- an explicitly active unresolved Illusion guard still prevents
  species-singleton ability collapse;
- ambiguous ability sets remain possible/unknown.

Ordinary displayed Gholdengo can therefore imply Good as Gold, while an active
Illusion guard still blocks that inference.

## Regression coverage

Tests now prove:

- 24-member custom battles are profiler-ineligible;
- full preflight rejects replays exceeding six team slots;
- ordinary displayed species are known without a default Illusion guard;
- ordinary Gholdengo permits deterministic Good as Gold inference;
- a species with multiple possible abilities remains unknown;
- the existing explicit Illusion guard prevents singleton collapse;
- existing replace/Illusion feature behavior remains covered.

## Remaining unmatched-state expectations

The immutable old artifact remains at 772 unmatched states. The custom replay
accounts for 253. The other 519 old-artifact mismatches span 47 replays:

- 486 `move_missing_from_reconstructed_active_moves`;
- 33 `switch_target_missing_from_pre_action_legal_roster`.

These include existing Struggle/called-move and battle-form/roster-alias
limitations. They remain explicitly audited and excluded from rank positives;
this task does not weaken matching by injecting observed actions. A replacement
replay may add its own audited mismatches, so the regenerated match rate must be
measured rather than predicted.

## No-leakage analysis

- Team-size validation reads only public protocol metadata.
- Displayed species/form/level come from public switch/drag events.
- No hidden opponent team, ability, item, or request payload is read.
- Revealed replace information applies only after its public event.
- Unknown/ambiguous abilities and items remain unknown/possible.
- Singleton inference requires reliable displayed identity and an inactive
  Illusion/true-species guard.
- Future replace events do not rewrite earlier states.

No feature names, dimensions, schema versions, or fingerprints changed.
`legal-action-v7` remains 552D with fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.

## Gate status

- Existing dataset: retained, stale, and prohibited for training.
- Current manifest: stale because it contains the rejected custom replay.
- Next data step: replace that train entry, rerun read-only preflight/tests,
  obtain explicit materialization approval, rematerialize, and repeat the audit.
- Tiny smoke training and production/live promotion remain closed.

No full materialization, training, checkpoint promotion, live-default change,
live-bot change, action-schema change, or v8 implementation occurred.
