# vNext Feature Storage Layout Recommendation

## Compared layouts

1. **Duplicated dense state per candidate:** simplest for current ranker
   loaders, but repeats a 3208D state roughly five times per decision.
2. **State table plus candidate table:** one state row per decision, 318D action
   rows per candidate, and integer group/state offsets. This removes the dominant
   duplication while remaining dense and simple.
3. **Compressed float16 arrays:** halves dense payload size and compresses
   zero/one-heavy schema slices well. Feature generation should remain float32,
   with explicit float16 conversion only at persistence.
4. **Sparse/hybrid encoding:** potentially useful for hashed identities and
   large one-hot slices, but adds model/loader complexity before dense
   measurements show it is necessary.

## Recommendation by scale

- **Tiny benchmark:** compressed float16 state table plus candidate table.
- **`diagnostic_300`:** use the same non-duplicated layout. Duplicated dense
  would be tolerable only as a temporary compatibility shortcut, not the
  preferred artifact.
- **`small_1000`:** keep the separate tables and compressed float16 arrays;
  measure decompression and training-loader throughput.
- **`medium_5000`:** require separate state/candidate tables. Consider sharded
  containers or memory mapping before considering sparse model inputs.

Do not adopt sparse/hybrid model inputs until the diagnostic and small runs
measure an actual dense I/O or memory bottleneck. Record schema fingerprints,
dtype, manifest checksum, source commit, and information boundary in every
materialized artifact.
