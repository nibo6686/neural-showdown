# Prompt 4 lead review — 2026-10-09

## Decision

Accept V01 as demonstrated field-truth validation defects. Release Prompt 5 / PR-04B for weather, terrain and Trick Room membership, plus the related ordinary Python field-schema discrepancy. Broader state-fidelity acceptance is blocked pending repair. Historical scoped capture reviews remain evidence, not blanket semantic validation of this candidate.

## Independent Reproduction

Lead inspected independent canonical resealing, joins, source-ledger assertions, compact construction and outcome classification in the new proof test. With encoding overrides removed only from child environments, lead passed each saved ordinary bundle through Python `verify_bundle_identities` and the actual publication CLI:

| Family | Public prefix truth | False supplied field | Identities | CLI |
|---|---|---|---|---|
| Weather | SunnyDay from Drought | raindance | Exit 0 | Exit 0; 1,327 stdout bytes |
| Terrain | Electric Terrain from Electric Surge | grassyterrain | Exit 0 | Exit 0; 1,326 stdout bytes |
| Pseudo-weather | No Trick Room start | trickroom present | Exit 0 | Exit 0; 1,355 stdout bytes |

All CLI stderr was empty. These are validly shaped, resealed false maps, not stale-hash attacks. DATA rows contain linkage IDs rather than literal field values: wrong observations are admitted into validated publication.

Worker matrix records 24 false attacks accepted in TS and Python ordinary/full/envelope, plus 12 terminal compact attacks publishing. Valid controls establish the applicable paths. Nonterminal compact closure rejection is unrelated to field truth. Six missing/extra-key controls demonstrate ordinary Python schema divergence. Lead inspected the matrix/construction and independently reproduced the three ordinary cases only; no claim of rerunning all 200 calls or terminal attacks.

## Repair Requirements

Independent ordered public-writer checks must run in projection AND imported-observation validation: TS `observable_state.ts` and `belief_state.ts`, Python ordinary/full/envelope/compact paths. Reject forged values without repairing them during validation.

Preserve actual coarse conventions: weather expiry `none`, terrain clear null, terrain IDs also appearing in the existing pseudo-weather list. Check proven Trick Room membership without redesigning that list or expanding every room mechanic. Suppressed weather is not a clear event. No engine timers or hidden source pointers.

Require the existing field keys/types consistently when field objects are supplied; missing required facts cannot conceal prefix evidence. Preserve documented genuine sparse/v1 compatibility through explicit source reasons. Contract conflicts return to lead.

Turn vulnerable characterization into default rejection regressions while preserving original Prompt 4 artifacts. All 24 attacks and 12 terminal compact cases must reject semantically with exit 2/empty stdout; valid lifecycle, terminal and restoration controls stay green. Add relevant waiting/requestless/v1 compatibility and immutability assertions. No blanket lifecycle/replay/full-format claim.

## Next Action

Run Prompt 5 only, then return diff/results. Provenance reconciliation follows, including new helpers/tests. No reviewed-hash update, commit, publication, dataset or training authorization.
