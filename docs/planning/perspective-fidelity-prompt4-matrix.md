# Prompt 4 actual result matrix

Source: final `perspective-fidelity-prompt4-results.json` (200 actual production CLI invocations). Every result has label, actual status, stdout bytes/row count, stderr, TS observation pair, record/episode/claim outcomes. Both perspectives and initial-input/final-successor attacks are included. Identity verification/direct joins precede semantic probes.

| Cases | TS observation / record / episode | Python ordinary | Python full | Python envelope | Python compact |
|---|---|---|---|---|---|
| 12 lifecycle controls (initial/last ordinary bundles, both players, three families) | Accepted | 12 exit 0, one row each | 12 exit 0, all actor rows | 12 exit 0, validation receipt | 12 exit 2, zero stdout: closure obstruction |
| 8 terminal controls (initial/last as distinct, both players, three families) | Accepted | 8 exit 0, one row each | 8 exit 0, all actor rows | 8 exit 0, validation receipt | 8 exit 0, all actor rows |
| 12 lifecycle false values (three families × both players × input/successor) | Accepted | 12 exit 0, wrong observation admitted | 12 exit 0, wrong observation admitted | 12 exit 0, wrong observation validated | 12 exit 2, zero stdout: closure obstruction |
| 12 terminal false values (three families × both players × input/successor) | Accepted | 12 exit 0, wrong observation admitted | 12 exit 0, wrong observation admitted | 12 exit 0, wrong observation validated | 12 exit 0, wrong observation admitted |
| 6 missing/extra field keys (three families × two schema controls, p1 input) | Exact-key schema rejection in observation/record/episode; faithful-claim metadata check accepts | 6 exit 0: schema divergence | 6 exit 2, zero stdout: exact-key schema | 6 exit 2, zero stdout: exact-key schema | 6 exit 2, zero stdout: exact-key schema |

The cloned standalone observation measurement occurs before record/episode validation and has no bound terminal authority carried by the original objects. All 44 control and false-value observation pairs accept, including these fixture terminal observations. The six schema cases reject only the input observation; their unchanged successor accepts. Terminal health/item/ability schemas beyond these fixtures are outside this proof.

## Independent truth and minimal contradictions

| Family | Ordered source control | Saved smallest false input | Additional proof |
|---|---|---|---|
| Weather | Drought `SunnyDay` → move `RainDance` → expiry `none` → move `RainDance` | Retained opening `|-weather|SunnyDay|[from] ability: Drought|[of] p1a: Sun`, typed `weather='raindance'` | Source expiry coarse wire value is literal `'none'`; weather remains active at terminal without fabricated clear |
| Terrain | Electric Surge → Grassy Surge replacement → Ice Spinner Grassy clear → Electric Surge reapplication | Retained opening Electric Terrain writer, typed `terrain='grassyterrain'` | Scalar tested independently of pseudo-weather list; no terrain list-lifecycle redesign inferred |
| Pseudo-weather | Absent → Trick Room start → reapplication clears → start again | No Trick Room writer in prefix, typed `pseudo_weather=['trickroom']` | Terminal attack removes existing Trick Room from the typed list while its start remains retained |

Six `*-ledger.json` files contain exact ordered writers and hand-authored values at every observed boundary. Neither expected truth nor attack values use a projection helper. False string values already meet the nullable-string schema; pseudo-weather toggles use admitted string arrays. Prefixes/requests remain byte-content identical after JSON transport; only one selected field at one observation boundary is changed, with repeated copies of that boundary consistently updated.

## Exact classifications

- **Successful wrong-state admission/publication:** all ordinary/full false values and all applicable complete terminal compact cases. DATA-001 rows carry IDs rather than serializing weather/terrain/pseudo-weather. Emitted input observation and belief linkage equals the resealed candidate; successor attacks pass actual validation but the row does not directly serialize that successor value. Envelope output is an evidence validation receipt, not DATA rows.
- **Unrelated closure obstruction:** lifecycle compact control and false-value attack emit `pipeline-record validation failed: episode publication sweep requires a validated original-to-terminal chain`, exit 2 / empty stdout. This is neither semantic rejection nor compact success. Terminal complete controls establish compact coverage independently.
- **Schema rejection:** full/envelope/compact missing/extra-key controls emit `... field fields are not exact; missing=['weather'|'terrain'|'pseudo_weather'], unexpected=[]` or `missing=[], unexpected=['unreviewed_field']`. TS emits `Error: Observation field fields are not exact.` Ordinary Python admits these separate cases; this does not prove a field-truth guard exists elsewhere.
- **Hash/join failures:** none in the completed matrix. No timeout or unresolved execution outcome occurred.
- **Semantic guard rejection:** none in the completed false-value matrix.

## Limits

Terminal restoration checks `LocalBattleEnv.resetFromSerialized` valid field views and legitimate retained terminal request history. Forged states were not published through a restored session. No one-sided waiting/nonterminal requestless capture, all weather/terrain IDs, suppression, hidden timers, Magic Room interactions, legacy v1, replay, training or universal mechanics proof. Existing scoped faithful capture acceptance and source flag remain unchanged.
