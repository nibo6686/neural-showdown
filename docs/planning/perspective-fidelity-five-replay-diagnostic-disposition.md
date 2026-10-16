# Five-replay diagnostic disposition — 2026-10-12

Lead assessment of the user-supplied diagnostic report; not an independent execution or acceptance verdict. No replay files were downloaded, tests run or production inputs changed in this assessment. Original local files/scripts/results remain to be located and frozen.

## Reported evidence

The report describes five saved Gen 9 Random Battle replays loaded successfully. Four admit the gameplay prefix; one stops at source44 on Natural Cure with an additional `[silent]` tag. HP/faint comparisons reportedly match on admitted prefixes. Three fainted Tera users have `terastallized:false`; owner items/abilities remain partly unknown. Scratch removal of `[silent]` is diagnostic only and cannot establish production admission or unchanged evidence.

HP/faint checks do not prove every decision boundary, identity attribution, hidden-information safety, status/stages/PP or field lifecycle truth. Exact last admitted source index, terminal record and any early leave must be recorded separately; do not infer complete terminal admission from the phrase “full battle.”

## Source-informed dispositions

| Finding | Current classification | Required next proof |
|---|---|---|
| Natural Cure `[silent]` | Replay compatibility/version uncertainty, not yet a pinned grammar defect | Pinned 0.11.10 `Abilities.naturalcure.onSwitchOut` emits only `[from] ability: Natural Cure`. Identify the actual replay emitter/revision or justified source-backed compatibility policy, audience and tag order before extending shared grammar. No generic optional-tag relaxation. |
| Fainted Tera flag | Current-state versus historical-knowledge distinction | Pinned `Battle.faintMessages` deletes `pokemon.terastallized`; extractor `handleFaint` mirrors it. Independently test what the current flag promises and whether public Tera-use history, revealed type and team resource use survive faint/revival/reentry. Do not change legacy flag semantics by assumption. Map persistent knowledge to K16/P02. |
| Owner item/ability backfill | Planned R02 attribution/source adoption gap | Recover uniquely attributable original owner facts only; separate original possession/ability from acquired items, Trace/Transform and dynamic changes. Mew Life Orb damage is evidence to classify, not automatic original-item proof. Opponent facts remain chronological; never-revealed/ambiguous facts remain unknown. |
| Rating/leave tail | Existing strict importer limitation, with terminal-cutoff uncertainty | Verify terminal/source cutoff and metadata classification. Do not silently discard or normalize unclassified records. |

## Sequencing decision

### Upstream version finding

On 2026-10-12, the lead verified GitHub's latest tagged release as v0.11.11. Its tagged `Abilities.naturalcure.onSwitchOut` emits the exact ordered `[from] ability: Natural Cure`, `[silent]` pair reported in the saved replay. This supplies a newer-version source witness; it does not establish the individual replay's engine revision or justify broadening the 0.11.10 supported scope. Sources: [release](https://github.com/smogon/pokemon-showdown/releases/tag/v0.11.11), [tagged ability source](https://github.com/smogon/pokemon-showdown/blob/v0.11.11/data/abilities.ts). The published npm artifact and its integrity still require verification before migration.

After B2 review, perform a bounded 0.11.10→0.11.11 impact assessment before B3 depends on native writer/serialization hooks. Compare birth/restore/event seams, protocol forms, generation/configuration, snapshots/identities, dependency/runtime requirements and affected evidence. Preserve the accepted old baseline. No install, lock change, package replacement or blanket retest is authorized by this note.

Keep ongoing Prompt28/B2 unchanged. Parallel work, if assigned, is read-only diagnostic/fixture intake with no shared runtime writes. After B2 review, resolve compatibility and Tera semantics before selecting narrow repairs. Add the five source fixtures to replay acceptance coverage once acquisition/privacy/storage and exact hashes are settled. Do not enlarge the replay oracle to every family immediately or rerun native long-chain evidence.

These findings refine existing P02/R02 obligations and add a concrete replay compatibility checkpoint. They do not authorize early owner-backfill implementation, B3/B4 bypass, changing capture-flag meaning, datasets/training, publication or commits.
