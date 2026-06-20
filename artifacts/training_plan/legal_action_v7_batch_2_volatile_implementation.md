# legal-action-v7 Batch 2: Typed Volatile Effects Implementation

Appends the typed-volatile slice (SLICE9) of `legal-action-v7` after the frozen
361D v7 batch-1 prefix. **No training, no materialization, no checkpoint
promotion, no live-default change.** v6 remains the stable zero-FAIL baseline; the
gate stays closed.

## What was added

### Schema (append-only)

- `SLICE9_VOLATILE_FEATURE_NAMES` (14) appended after the v6 (331) + batch-1
  status/stat (30) prefix.
- **`ACTION_FEATURE_DIM_V7 = 375`** (was 361). Version string unchanged
  (`legal-action-v7`); v7 grows per batch since no v7 data has been materialized.
- Full v7 fingerprint (SHA-256 of the ordered names):
  `7f102fd8abc51bc6c776a1447bf27a15ec71352e3d6a9f9ba901d7f7eecc0252`.
- The frozen 361D v7 batch-1 prefix is byte-identical and its fingerprint is still
  `85225a44776b6fc6e44b9900432acb253bacf3339a276d60febbd70eac4fd77f`; the 331D v6
  prefix fingerprint remains `ac8fb3d3…73f049`. Exposed
  `ACTION_FEATURE_NAMES_V7_BATCH1` / `ACTION_FEATURE_DIM_V7_BATCH1` for guards/tests.
- `feature_schema()` now also reports `v7_slice9_feature_names`.

### SLICE9 fields (14)

Target: `effect_target_flinch_chance`, `effect_target_trap_chance`,
`effect_target_taunt`, `effect_target_encore`, `effect_target_disable`,
`effect_target_leech_seed`, `effect_target_yawn`, `effect_target_heal_block`,
`effect_target_volatile_other`.
Self: `effect_self_substitute`, `effect_self_protect`, `effect_self_destiny_bond`,
`effect_self_magnet_rise`, `effect_self_volatile_other`.

### Extractor — `action_side_effects.move_volatile_effects`

Cached `_raw_volatile_effects` parses the bundled `moves.ts` (the oracle): each
`volatileStatus` string maps to its v7 field; flinch (and any secondary volatile)
carries the secondary `chance`, primary/guaranteed-on-hit volatiles are 1.0.
Volatiles without a dedicated field fall into a side-appropriate
`*_volatile_other` catch-all. `build_action_feature_vector_v7` is now
`v6 ⊕ SLICE8 ⊕ SLICE9`; switches and non-move actions are all-zero.

## Field mapping (pool-derived)

The randbats pool's `volatileStatus` strings drove the design:

| Showdown volatile | v7 field |
| --- | --- |
| flinch (15 moves) | `effect_target_flinch_chance` (secondary chance) |
| partiallytrapped (Magma Storm, Whirlpool) | `effect_target_trap_chance` |
| taunt / encore / disable / leechseed / yawn | the matching `effect_target_*` |
| healblock (Psychic Noise) | `effect_target_heal_block` |
| substitute (Substitute, Shed Tail) | `effect_self_substitute` |
| protect (+ detect/spikyshield/banefulbunker/kingsshield/silktrap/burningbulwark/obstruct/maxguard) | `effect_self_protect` |
| destinybond / magnetrise | `effect_self_destiny_bond` / `effect_self_magnet_rise` |
| saltcure, sparklingaria | `effect_target_volatile_other` |
| noretreat | `effect_self_volatile_other` |

## Rules honored

- Oracle-only; nothing invented. Chance-based volatiles (flinch) carry their
  probability; guaranteed volatiles are 1.0.
- Distinct effects get distinct fields (flinch, trap, taunt, encore, disable,
  leech seed, yawn, heal block, substitute, protect, destiny bond, magnet rise);
  only genuinely-untyped volatiles use the `*_volatile_other` catch-all.
- v6 and v7 batch-1 fields preserved exactly (verified by value-equality tests).
- Ordinary moves (Surf, Earthquake, Close Combat) and switches → all volatile
  fields zero.

## Representative moves verified (tests)

Fake Out flinch 1.0; Air Slash / Iron Head flinch 0.30 (secondary, not 1.0);
Leech Seed, Yawn, Taunt, Encore, Disable, Magma Storm/Whirlpool trap, Psychic
Noise heal-block all 1.0; Substitute / Shed Tail self substitute; Protect self
protect; Destiny Bond, Magnet Rise self; Salt Cure → target_volatile_other,
No Retreat → self_volatile_other; Confuse Ray / Hurricane confusion via the
batch-1 `effect_target_status_confusion_chance` (1.0 / 0.30); Surf / Earthquake /
switch all-zero.

## INEXACT categories now modeled

Adds typed **volatile** effects to the typed status/stat from batch 1. Volatile
moves whose INEXACT reason was an omitted volatile — flinch (Iron Head, Air Slash,
Fake Out), trapping (Magma Storm, Whirlpool), Taunt, Encore, Disable, Leech Seed,
Yawn, Heal Block, Substitute, Protect, Destiny Bond, Magnet Rise — now carry typed
v7 fields. (The completeness audit reclassification to PASS is applied once the
audit generator is taught the v7 classifier, in a later step.)

## Deferred volatile mechanics (documented)

- **confusion** — kept in the batch-1 status slice (`effect_target_status_confusion_chance`); not duplicated as a volatile.
- **curse** (ghost Curse) — special-cased in `resolve_action_impact`; excluded here.
- **lockedmove** (Outrage, Petal Dance), **mustrecharge** (Giga Impact),
  **two-turn charge / roost grounding** — multi-turn / timing / recovery
  mechanics for later v7 batches (timing & recoil/heal slices); excluded.
- **glaiverush** — a self drawback volatile on a foe-targeting move (side can't be
  inferred from the move target by the generic parser); deferred and excluded
  rather than mis-sided.
- **saltcure / sparklingaria / noretreat** — real but singleton volatiles with no
  dedicated field yet; honestly flagged via the `*_volatile_other` catch-all.

## Tests

Updated `trainer/tests/test_action_features_v7.py` (dim now 375; batch-1 361-prefix
fingerprint assertion). New `trainer/tests/test_action_features_v7_volatile.py`
(17 tests): full v7 dim/fingerprint, batch-1 prefix name+value equality, ordinary/
switch zero, guaranteed and secondary flinch, confusion-in-batch-1, leech/yawn,
taunt/encore/disable, trap/heal-block, substitute, protect, destiny bond/magnet
rise, volatile_other catch-all. Combined v7 suite: **30 passed**.

Regression: action-features v4/v5/v6, mechanics-repair batch-1..5, generator audit,
action_ranker, mechanics_audit — **108 passed** (no sim-core change this batch).
`git diff --check` clean.

## Status

v6 and v7 batch-1 unchanged in behavior (prefix byte-identical). v7 is now 375D
with typed status/stat (batch 1) + volatile (batch 2) effects, and is **not**
materialized, trained, or promoted, and does not change live defaults.
Rematerialization and training remain blocked pending explicit approval. The gate
stays **closed**.
