# legal-action-v7 Batch 1: Typed Status + Stat-Delta Implementation

Implements the first typed-effect slice of `legal-action-v7` from
`legal_action_v7_typed_effect_schema_design.md`. Schema + status/stat fields only.
**No training, no materialization, no checkpoint promotion, no live-default
change.** v6 remains the stable zero-FAIL baseline; the gate stays closed.

## What was added

### Schema shell (append-only)

- `ACTION_FEATURE_VERSION_V7 = "legal-action-v7"`.
- `ACTION_FEATURE_NAMES_V7 = ACTION_FEATURE_NAMES_V6 (331, byte-identical) + SLICE8_STATUS_STAT_FEATURE_NAMES (30)`.
- **`ACTION_FEATURE_DIM_V7 = 361`.**
- v7 fingerprint (SHA-256 over the ordered name list):
  `85225a44776b6fc6e44b9900432acb253bacf3339a276d60febbd70eac4fd77f`.
- v6 prefix preserved exactly: the first 331 v7 names equal the v6 names and their
  SHA-256 is still `ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049`.
- Registered in `action_feature_schema("legal-action-v7")` and `feature_schema()`.
- Guard: `validate_vnext_checkpoint_metadata` is version/dim/fingerprint generic;
  a v6 checkpoint is rejected when v7 is expected and vice-versa (tested).

### SLICE8 fields (30) — `SLICE8_STATUS_STAT_FEATURE_NAMES`

- Target status chance ×7: `effect_target_status_{brn,par,psn,tox,slp,frz,confusion}_chance` (probability in [0,1]).
- Self status chance ×7: `effect_self_status_{...}_chance`.
- Target stat ×7 + chance: `effect_target_boost_{atk,def,spa,spd,spe,accuracy,evasion}_stage` (signed, /6) + `effect_target_stat_chance`.
- Self stat ×7 + chance: `effect_self_boost_{...}_stage` + `effect_self_stat_chance`.

Provenance flags (exact/partial/distribution) from the design are intentionally
**deferred** to a later v7 batch: they are meant to summarize all SLICE8 effect
categories, and only status/stat exist so far. The per-type status chances already
encode multi-outcome distributions self-descriptively (e.g. Tri Attack), so no
provenance flag is needed for this slice.

### Extractor — `action_side_effects.move_typed_effects`

Parses the bundled `moves.ts` (the oracle) once (cached `_raw_typed_effects`) for:
- primary status (`status` / `volatileStatus: 'confusion'`) at chance 1.0, placed
  on self vs target by the move's `target`;
- secondary status from `secondary` / `secondaries` objects at their `chance`
  (per-object, so arrays are handled), nested `self:` separated from target;
- callback-status moves with no literal status field — Tri Attack (20% split over
  brn/par/frz) and Dire Claw (50% over psn/par/slp) — encoded as the equal-split
  distribution;
- primary (guaranteed) stat boosts from top-level `boosts`, `self: {boosts}`, and
  `selfBoost: {boosts}` (chance 1.0), kept **separate** from secondary-block self
  boosts so a 20%-secondary self boost is not mislabeled guaranteed.

`build_action_feature_vector_v7` = `build_action_feature_vector_v6` ⊕ the SLICE8
vector. The SLICE8 vector derives only from move metadata (independent of impact /
live state); switches and non-move actions are all-zero.

## Rules honored

- Oracle-only: every value comes from Showdown move data; nothing invented.
- No vague booleans where typed fields exist — chances are probabilities, stat
  deltas are signed stages with an application chance.
- v6 coarse next-state booleans are preserved in the prefix for backward
  compatibility; v7 carries the exact typed information alongside.
- Ordinary moves (Surf, Earthquake) and switches → all new fields zero.
- Chance effects encoded as probabilities (Thunderbolt par 0.10, Scald brn 0.30),
  not as fake deterministic 1.0; guaranteed effects are 1.0 (Will-O-Wisp,
  Thunder Wave, Toxic, Spore, Swords Dance).
- Multi-outcome status encoded as a distribution (Tri Attack 0.0667 each across
  brn/par/frz).

## Representative moves verified (tests)

| Move | Typed v7 output |
| --- | --- |
| Will-O-Wisp | target brn 1.0 |
| Thunder Wave / Toxic / Spore | target par / tox / slp 1.0 |
| Thunderbolt | target par 0.10 (not 1.0) |
| Scald / Ice Beam | target brn 0.30 / frz 0.10 |
| Tri Attack | target brn=par=frz ≈ 0.0667 (distribution) |
| Crunch | target def -1/6, chance 0.20 |
| Growl | target atk -1/6, chance 1.0 |
| Close Combat / Draco Meteor | self def&spd -1/6 / self spa -2/6, chance 1.0 |
| Swords Dance | self atk +2/6, chance 1.0 |
| Meteor Mash | self atk +1/6, chance 0.20 (secondary, not guaranteed) |
| Charge Beam / Fiery Dance | self spa +1/6, chance 0.70 / 0.50 |
| Scale Shot | self def -1/6 & spe +1/6, chance 1.0 (selfBoost) |
| Surf / Earthquake / switch | all SLICE8 fields zero |

## Tests

New `trainer/tests/test_action_features_v7.py` (15 tests): v7 dim/slice size; v6
prefix names + fingerprint unchanged; v7 fingerprint stable; v7 vector prefix
equals v6 (move/Tera/switch); checkpoint guard rejects v6↔v7; ordinary move and
switch zero; guaranteed status; secondary status as probability; Scald burn;
target stat drop; self boost; secondary-self boost keeps secondary chance;
multi-outcome status distribution.

Regression: action-features v4/v5/v6, mechanics-repair batch-1..5, generator audit,
action_ranker, mechanics_audit — **108 passed** (no sim-core change this batch).
`git diff --check` clean.

## INEXACT categories now modeled by v7

This batch makes **typed status** and **stat-delta** effects exact (or honest
distributions). Moves whose only INEXACT reason was a secondary/primary status or
a stat change — e.g. Thunderbolt, Scald, Ice Beam, Will-O-Wisp, Thunder Wave,
Toxic, Spore, Glare, Crunch, Earth Power, Growl, Meteor Mash — now have typed,
exact v7 fields (the completeness reclassification to PASS will be applied when the
audit generator is taught the v7 classifier, in a later step). Volatile, item,
priority/timing, recoil/drain/heal, hazard/screen/weather/terrain, and conditional
categories remain INEXACT in v6 and are scheduled for later v7 batches.

## Status

v6 unchanged and remains the stable zero-FAIL baseline. v7 batch 1 adds the schema
+ typed status/stat fields and is **not** materialized, trained, or promoted, and
does not change live defaults. Rematerialization and training remain blocked
pending explicit approval. The gate stays **closed**.
