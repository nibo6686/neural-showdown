# diagnostic_1000_v7_v7_post_magic_bounce Materialization Report

The explicitly approved one-time post-Magic-Bounce rematerialization completed
in a new output directory. No training, checkpoint promotion, live/default
change, schema change, v8 work, old-gen work, or push occurred.

## Source and command

- Source commit:
  `4cba668d28491cf3aaf3b171660c47f113a57edc`
- Manifest:
  `artifacts/training_plan/manifests/diagnostic_1000_v7_v7_post_ditto_manifest.json`
- Manifest SHA-256:
  `d19727107fc88e03b1eecf12ad3538cb056ee699e4e1f2cfd743fce44e0b4c46`
- Manifest catalog checksum:
  `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`
- Output:
  `artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_magic_bounce`

The materializer ran once with the documented neuralgpu Python runtime,
configured sim-core server, six workers, full-manifest mode, and
`legal-action-v7`. It completed with exit code 0 in 1,033.26 seconds.

## Result

- Dataset:
  `artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_magic_bounce/diagnostic_1000_v7_v7_post_magic_bounce.npz`
- Dataset SHA-256:
  `9f27c4b83776a0744f657d0ff54683123c893e30d07f96745004ecff51c9ecd3`
- Dataset size: 33.58 MiB; total final output: 35.66 MiB
- Shards retained: 1,000
- Battles: 1,000 requested / 1,000 processed / 1,000 valid / 0 failed
- Decision states: 80,635
- Action candidates: 617,555 (7.66 average/state)
- Candidate kinds: 239,889 move / 130,866 move-Tera / 246,800 switch
- State splits: 64,455 train / 7,853 validation / 8,327 test
- State-value labels: 40,272 wins / 40,363 losses / 0 draws
- Action-rank positives: 80,594
- Unchosen candidates: 536,961
- Matched / unmatched decisions: 80,594 / 41
- Match rate: 99.9492%
- Matched by kind: 58,192 move / 1,447 move-Tera / 20,955 switch
- Unmatched by kind: 23 move / 18 switch
- Initial-deployment nondecisions: 2,000
- Reflected Magic Bounce protocol rows classified as nondecisions: 9
- Action-value labels: 0

Relative to the stale post-Ditto artifact, the corrected build has nine fewer
decision states and 132 fewer candidates. The nine explicit reflected Magic
Bounce rows are no longer actor-selected decisions or moveset evidence, while
the genuine later Psychic decision in `gen9randombattle-2589608300` now matches.

## Schema and validation

- State: `live-private-belief-v7`, 3208D,
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`
- Action: `legal-action-v7`, 552D,
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
- On-disk dtype: float16
- Source commit embedded in the NPZ and metadata matches the fix commit.
- All 18 built-in validation checks passed, including schema/name
  fingerprints, split isolation, candidate indices, labels, source-manifest
  traceability, no duplicated state vectors, no action-value labels, and
  unchanged live defaults.
- Independent NPZ inspection found no NaN or Inf in any numeric array.
- Exactly 80,594 state groups have one positive, 41 quarantined groups have
  zero positives, and no group has multiple positives.

Live defaults remain `live-private-belief-v2` 115D and `legal-action-v3` 165D.

## Old-artifact integrity

All nine pre-existing dataset `.npz` files rehashed byte-identically after the
run, including the stale 1,000-battle post-Ditto artifact
(`e8c3b4dde2d3eb59154563ce7595d07535507eaa2771c5faec424c81b393bf22`)
and the 300-battle post-Ditto artifact
(`64e1f6eee11f6a6ee0f91a47acf4bf0943a6aeeb3f86c7299a46717fd420af07`).
No prior dataset was overwritten.

## Materialization decision

The post-Magic-Bounce materialization passes. The independent quality audit
classifies all 41 unmatched groups as the previously known, explicitly
quarantined public-replay Illusion ambiguity set. This artifact supersedes the
stale post-Ditto 1,000-battle artifact as the v7/v7 rank-diagnostic baseline.
Training remains a separate explicit approval gate.
