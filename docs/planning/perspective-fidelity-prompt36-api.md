# Prompt36 private decoder/context API

Active package and owned producer profile remain 0.11.10. `native11` remains unadopted. Existing historical protocol JSON, inventories, identities, wire shapes, B1/B2 and K-source contracts are unchanged.

## Fixed contexts

| Context / selector | Permitted caller paths | Authority |
|---|---|---|
| `HISTORICAL10_CONTEXT` / explicit importer `historical10` | Existing readers/helpers/projectors; historical replay forms | Existing reviewed historical decoder semantics only |
| `NATIVE11_GRAMMAR_CONTEXT` | Raw grammar via `protocolContext`; TS `validateRawProtocolRecord`, Python `validate_protocol_record` | Inactive PRE shape rules only; rejected by readers, extractor and semantic helpers; no target publication |
| `REPLAY_COMPAT_CONTEXT` / importer `replay-compat-v1` | Fixed local helpers and replay APIs through `helperContext` / grammar `protocolContext` | Untrusted importer view/history only; no engine, originals, B1/B2, registry, K facts or fidelity claim |

`readerContext` / Python `reader_context` remain historical-only. A copied context or caller-built descriptor rejects. `helperContext` accepts only the exact historical or replay object. `protocolContext` additionally accepts the exact inactive grammar object, never creating a native profile. No mutable global selection or engine registry is added.

The assets are `trainer/src/neural/protocol_contract_0_11_11.json` and `protocol_contract_replay_compat_v1.json`. Both are deeply frozen after code-owned SHA-256 checking. `loadPreparedProtocolAsset` / `load_prepared_protocol_asset` expose integrity-checked inspection; an alternate path cannot replace the trusted pin or create a context. Missing/altered/omitted/rehashed content rejects. Historical strict `validateProtocolContract` / Python old contract loader remains unchanged; candidate containers are separately fixed and are not admitted by the old loader.

Historical raw shape definitions are a prepared baseline. Old positive controls, rejection controls and represented token fixtures are not adopted: candidate controls are explicit PRE rows that pass the selected context. Wholly stopped cant/swap tokens are recognized unsupported. Target effect/lifecycle records stop before consulting historical inventory. [Writer dispositions](perspective-fidelity-prompt36-writer-matrix.md) separate grammar preparation from typed and runtime closure.

## Import APIs and propagation

Both `importReplayPrefix(records,cursor,context)` and `importReplayPrefixWithMoveHistory` require `context.protocol_profile` as `historical10` or `replay-compat-v1`, including empty input. Missing, auto, unknown, and native11 selection reject before extraction. This is an intentional caller API restriction under A3. The three existing importer/history/retention test context builders now explicitly select historical10; fixture bytes and assertions are untouched.

Both entries snapshot the four primitive caller fields once before validation. A mutable selector getter cannot switch profiles between import and history; the companion reuses the frozen snapshot. One immutable selected context reaches source admission → `PlayerStateExtractor` → per-row/final `validateObservableProtocolPrefix` → `reconstructPublicMoveHistory`. Direct move-history reconstruction retains historical default and accepts an explicit local helper context additively. Necessary field/ability/boost/lifecycle/effect/lookup helper entry gates accept the fixed importer context; their algorithms remain unchanged. Profile-independent health/item replay and move-history bookkeeping stay unchanged.

Natural Cure policies are exact: historical from-tag only; candidate native from-tag then silent; compatibility enumerates these two forms. No silent removal, optional-tag widening, ability substitution or actor/status relaxation occurs. Tags affect presentation, not transport routing. `source_rows`, source/routed maps and raw prefixes preserve records exactly after documented HTML transport decoding. Neither import result nor move history introduces a profile/fidelity/authority wire field; appearance carriers remain null.

## Publication and lifetime

The replay helper context cannot enter historical pipeline readers, belief validators or native producer contexts. Observable/step wire projectors explicitly reject replay publication. Default historical raw validation rejects the silent Natural Cure form. Python CLI has no replay publication selector and exits 2 with empty stdout for that unsupported choice. These are actual PRE restrictions, not target-native publication checks.

There is no persisted replay-union publication contract. Relabeling an importer context or stripping its mode does not enable silent records in old grammar. Identical old-form bytes cannot attest replay provenance; caller metadata is never an authority certificate. Portable union publication needs a separately reviewed persisted contract.

Contexts/assets are immutable for process lifetime and require no revokeable holdings. Native/session/source authority lifetimes are unchanged. Full historical/target coexistence, target producer grammar ownership and target publication remain deferred to controlled activation.

## Mandatory preactivation validator gate

The new containers are fixed PRE grammar-rule payloads with shared structural member typing. Their nested `protocol` objects are intentionally not drop-in historically validated `ProtocolContract` assets: token fixtures are empty, prepared unsupported dispositions are profile-specific, and Natural Cure differs. Activation must provide profile-aware full-contract validation and evidence without relaxing historical invariants, then bind actual target producers/readers to that validated context. Code-owned byte integrity establishes the reviewed PRE payload, not native semantic closure. This limitation is independent of package installation and cannot be hidden in a lock bump.
