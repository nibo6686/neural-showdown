# Diagnostic 300 v8/v7 Belief-Slice Quality Audit

## Decision

The 299 materializable battles pass the v8 state / v7 action diagnostic quality
gate. The single invalid battle is a known property of the frozen original
manifest, not a feature-generation failure. The artifact is suitable evidence
for choosing the next representation step, but it does not authorize training
or live use.

## Structural and schema checks

- Arrays: state `(25020, 3229)`, action `(194967, 552)`, both float16.
- All 19 built-in validation checks passed.
- No NaN or infinity.
- Embedded state/action names match metadata and requested schemas.
- v8's first 3,208 names exactly equal frozen v7.
- Action Batch 7: 49/59 columns active; 120,478/194,967 candidate rows nonzero.
- Action Batch 8: 25/41 columns active; 29,981/194,967 candidate rows nonzero.
- Hash comparison found all 11 pre-existing dataset NPZ files unchanged.

## v8 belief-slice activity

All 21 appended columns are active, and every state row has at least one nonzero
belief-slice value.

- Prior available: 24,904/25,020 rows (99.5364%).
- Explicit unknown: 116 rows across 14 replays; every such row has
  `has_meta_prior=0` and `prior_other_mass=1`.
- Alias provenance: 373 rows.
- Explicit prior contradiction: 188 rows. This is repeated-state exposure of
  source-covered mismatches; it remains visible rather than silently repaired.
- `prior_other_mass`: 0.5–1.0.
- Confirmed-fact summary active on 22,069 rows.
- Ruled-out-fact summary active on 11,067 rows.
- Current-state-only evidence active on 426 rows.
- Source-absent evidence active on 12,761 rows.
- Confirmed ability/item/Tera flags active on 6,731 / 12,677 / 3,635 rows.
- All four source-quality flags are 1 on exactly the 24,904 prior-bearing rows
  and 0 on the 116 explicit-unknown rows.

The initial materialization exposed that source-covered
`OpponentSetBelief.update` reconstruction omitted `prior_source_key`,
`prior_alias_policy_version`, `prior_joint_quality`, and
`prior_coverage_warnings`. That caused quality and alias provenance to disappear
after supported evidence. The update now preserves those immutable fields, a
regression test covers it, and this audit describes the clean rematerialization.

## Label audit

25,017/25,020 decision groups match (99.9880%). The only three unmatched groups
are explicit quarantined Illusion/public-replay ambiguity rows:

| Replay | Turn | Public actor | Chosen move |
| --- | ---: | --- | --- |
| `gen9randombattle-2593348981` | 1 | displayed Avalugg | `Will-O-Wisp` |
| `gen9randombattle-2593348981` | 2 | displayed Avalugg | `Poltergeist` |
| `gen9randombattle-2593283718` | 3 | displayed Gumshoos | `Hyper Voice` |

This is the same known three-row floor from the post-Ditto v7/v7 audit. There
are no new matcher categories and no evidence that v8 state construction changed
action labels.

## Next step

The 300-battle state-slice gate is complete. The recommended next step is
candidate/action-v8 design, because the present v8 state slice is structurally
and semantically active and the existing 1,000-battle v7 baseline already
provides scale comparison. A 1,000-battle v8/v7 materialization is reasonable
only as a separately approved scale-confirmation step after deciding whether the
candidate/action-v8 slice should be included; it was not run here.
