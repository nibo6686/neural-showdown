# Prompt35 candidate API and lookup boundary

The active engine remains 0.11.10. Native11 remains unadopted. This candidate changes lookup ownership, not decoder selection, wire identities or native/source authority.

## Historical fields and ownership

`sim-core/simulator_coverage/lookups/pokemon-showdown-0.11.10.json` contains species `exists/types`, moves `exists/type/category/basePower/accuracy`, TypeChart `damageTaken`, and aliases. No native callbacks, simulator implementation or teams are copied. The asset contains 1,425 species, 936 moves, 19 types and 2,333 aliases. Extraction compared every consumed record from the accepted installation with the verified old npm artifact, after verifying nine compiled input files; tar member checks independently confirm their bytes.

`historicalToID` preserves the verified old normalizer, including object id/userid/roomid and number handling. `runtimeData(context)` keeps its existing caller API, validates the exact immutable historical context, and reads this asset instead of installed Dex. Alias targets are normalized again; missing species retain `exists:false/types:[]`, missing moves `exists:false`, and unknown type interactions remain neutral. Type attack keys retain the old case-sensitive lookup. Returned material is deeply frozen and lazily cached for the process lifetime.

The only direct helper imports changed are battle_helpers, action_codec, state_extractor and public_ability: their syntax normalizer no longer loads Showdown. Profile-independent arithmetic and reader identities are unchanged. Producer runtime ownership still performs the existing installed package/declaration/lock checks; independence does not permit an arbitrary runtime descriptor.

TS `historicalLookupData()` and Python `historical_lookup_data()` load the fixed asset with a code-owned SHA-256 pin, not a caller digest. Python exposes frozen mapping/tuple material; its existing reader paths already had no Dex dependency. No redundant Python lookup threading was added.

## Inactive candidate inspection

`sim-core/simulator_coverage/pokemon-showdown-0.11.11-gen9randombattle.json` uses `simulator-coverage-candidate/v1`. TS `loadInactiveTargetInventory(path?)` and Python `load_inactive_target_inventory(path=None)` inspect only bytes matching the reviewed candidate pin, returning frozen material. An alternate path is an integrity-test seam, not an adoption mechanism. Missing files and altered/rehashed content fail before use. No accepted ReaderContext, native profile or source token is returned.

`check-simulator-coverage.cjs --candidate-profile=native11` selects this inspection branch before installed-package resolution. It prints inactive/static/UNEXECUTED status and does not run the active semantic coverage checker. The default branch is unchanged. Existing native11 reader/producer/source-factory guards still reject.

## Provenance

| Asset | SHA-256 |
|---|---|
| Historical lookup | `21250d247e77879d0f7135a12baeee0ffadc7e00c5456a71dd07c066cd06b921` |
| Inactive inventory | `3d5760e2cc189617499cb9ab7e505ecebfeb6a3a6175f7e854c13fc7ba32dab2` |

Old npm archive: `8a96a0b4802e54c766900a0355ca1407ddb9d624146d56519825ec443acf0e7d`, revision `995b43201a2705b1cc1e707fadac239c3ddcf8ac`.
Target npm archive: `49af14aaed1084887f756372c7386c9987905930cc848ed31e9202c10c592d66`, revision `739a5e1fee432ad80ff7136d70cca993be358b59`.
The assets carry the verified npm SRI and source pins. Prompt29 records remain authoritative research inputs; no package research was repeated. Target source was parsed as text/AST/JSON only.

Detailed extraction records: [lookup](perspective-fidelity-prompt35-lookup-extraction.json), [inventory](perspective-fidelity-prompt35-inventory-extraction.json), [archive-member proof](perspective-fidelity-prompt35-verified-tar-member-parity.log). Preserved extraction scripts use the accepted host/scratch paths; they are evidence, not an installation workflow.
