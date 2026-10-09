# SLICE-002A Scanner Expansion Progress

## Current status — 2026-10-01

SLICE-002A scanner expansion was separately reviewed and accepted with local
coverage digest
`06305dab8ac7abeb9172e7e42f38988d169dac95b0024e221eb1236af0a28e5a`.
SLICE-002B format provenance and Gen 9 Random Battle reachability were also
accepted separately; see
[`SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md#slice-002b-format-provenance-and-random-set-reachability--accepted-2026-09-29)
for its reviewed simulator and local-source digests. These accept the listed
scanner, source-coverage, and reachability evidence only. They do not establish
complete simulator semantics or faithful episode capture. The complete-episode
closure audit is complete as an audit/backlog; implementation remains open and
`faithful_complete_episode:false` remains required. The current milestone and
delivery order are in [`PROJECT_STATUS.md`](../PROJECT_STATUS.md).

## Original implementation checkpoint

- Branch: `refactor/state-001-observable-state`
- HEAD: `b056f7ef5433cef254d2cfdaf822cc23c0c24b0c`
- Starting worktree: pre-existing user changes are present in simulator coverage, pipeline integration and tests, Python pipeline recording and tests, protocol contract, and schema-closure audit documents. These are preserved.
- Scope: expand the source-backed effect inventory and enforce fail-closed classification at TypeScript projection and Python publication boundaries.
- Excluded at this checkpoint: SLICE-002B provenance/reachability (accepted
  separately on 2026-09-29); simulator mechanics, lifecycle, counters,
  features, training, replays, installation/network behavior, README/dependency
  or aggregate-status changes; coverage digest attestation/recomputation.

## Status at original implementation checkpoint

Inventory is complete and enforcement is implemented at the TypeScript raw-record/projection boundary and Python publication validator. The coverage digest was unreviewed at this checkpoint; a later separate review accepted and attested the scanner closure, as recorded above.

## Inventory checkpoint

- Existing condition inventory: 142 IDs (125 represented, 17 raw-only).
- Expanded inventory: 169 IDs total (137 represented, 32 raw-only), including 27 source-discovered IDs: 4 move volatiles, 8 side conditions, and 15 raw-only internal effects.
- Source-discovered families include resolved `Move.condition`, `Move.slotCondition`, `Move.self.volatileStatus`, nested self/hit/secondary/secondaries volatile fields, `Ability.condition`, and `Item.condition`.
- Seven computed `addVolatile` call sites are tracked. Six remain unknown/fail-closed at the emitted protocol value; the pinned `Pokemon.copyVolatile` loop is explicitly represented for its four inventoried candidate IDs.
- Special values `typechange`, `typeadd`, and weather `none` retain their existing explicit projection routes. `-singleturn` remains raw-only and `-singlemove` remains unsupported.

## Implementation checkpoint

- The coverage checker now traverses nested resolved effect records, verifies their family patterns and per-ID inventory classification, tracks computed `addVolatile` call sites and family labels, and has nested-source and computed-family drift self-tests.
- TypeScript classifies `start/end`, weather, field, and side effect values before event routing; raw-only inventory rows remain evidence-only and do not mutate typed state.
- Python validates the same manifest and rejects unknown, unsupported, and family-mismatched values before pipeline publication.
- The extractor regression for out-of-scope Eternamax Dynamax now confirms that the manifest's raw-only classification is not projected into typed state; no mechanics or inventory classification was broadened.
- Recursive source discovery now scans complete resolved Move, Ability, and Item records, including condition and callback subtrees. Current pinned-source ability/item findings are 10 `Ability.condition` IDs, 2 `Item.condition` IDs, and 1 nested item callback value (`Item.fling.volatileStatus` = `flinch`); they already exist in the 169-ID inventory, so no new identifier dispositions were added. The checker self-test verifies the real `micleberry` Item.condition ID and `flinch` callback field are classified, while an unlisted nested callback family remains rejected.
- A real constructed pinned-simulator Costar callback test now verifies the dynamic `Abilities.costar.onStart` `addVolatile(volatile)` path emits a `dragoncheer` protocol record and projects it only because the ID is already explicitly classified. This fixture does not expand random-battle format scope or simulator mechanics.
- Pinned `sim/pokemon.ts` scanner coverage now includes both computed calls: line 1281 `this.addVolatile(volatile)` in the copied-volatile loop is represented for `dragoncheer`, `focusenergy`, `gmaxchistrike`, and `laserfocus`; line 1946 `source.addVolatile(linkedStatus, ...)` is unknown and fail-closed at the emitted protocol value. The manifest records both families, callsite arguments, and dispositions. Total computed callsites: 7 (6 fail-closed, 1 represented); changes to either callsite or family label cause scanner drift.
- `src/effect_inventory.ts` is now listed in `local_coverage_sources.files`; no digest fields were changed.
- Matched TS/Python regressions submit represented side-condition ID `stealthrock` under `-start`. TypeScript raises the structured family-mismatch before projection and preserves the prior view; Python rejects bundle validation with the structured diagnostic, leaves the candidate unchanged, returns code 2, and emits no stdout.
- Ability/item source pairs and dispositions: `Ability.condition` has 8 represented (`cudchew`, `flashfire`, `protosynthesis`, `quarkdrive`, `slowstart`, `truant`, `unburden`, `zenmode`) and 2 raw-only (`magicbounce`, `rebound`); `Item.condition` has represented `metronome` and `micleberry`; `Item.fling.volatileStatus` has raw-only `flinch`. Costar's dynamic candidate IDs (`dragoncheer`, `focusenergy`, `gmaxchistrike`, `laserfocus`) are already represented move volatiles; runtime unknown values remain fail-closed.
- `faithful_complete_episode:false` and all excluded 002B/later work remain unchanged.

## Validation checkpoint

- Repair validation: `npm run build` passed; focused TypeScript coverage/protocol/extractor run passed (35 tests, 0 failures); focused Python unknown-effect and category-mismatch publication tests passed (2 tests); scanner `--self-test` synthetic checks passed, including both Pokemon callsites and family-label drift.
- Separate standard review accepted the scanner closure. The coverage source list includes the scanner, manifest, validation, and regression files, including `src/effect_inventory.ts`. Attested local digest: `06305dab8ac7abeb9172e7e42f38988d169dac95b0024e221eb1236af0a28e5a`; prior reviewed digest: `6648d4b3836f4e90cc416a941810f0271ad2e934f0bd94a7983042711dfa9691`.
- `git diff --check`: passed.

## Family totals after expansion

| Inventory category | Count |
| --- | ---: |
| move_volatile | 88 |
| internal_effect (raw-only) | 32 |
| side_condition | 23 |
| pseudo_weather | 8 |
| weather | 8 |
| major_status | 6 |
| terrain | 4 |
| Total | 169 |

The inventory contains 137 represented IDs and 32 raw-only IDs. The 27 added source-discovered IDs are four move volatiles (`glaiverush`, `rage`, `roost`, `uproar`), eight side conditions (`firepledge`, `gmaxcannonade`, `gmaxsteelsurge`, `gmaxvinelash`, `gmaxvolcalith`, `gmaxwildfire`, `grasspledge`, `waterpledge`), and 15 raw-only internal effects (`bounce`, `dig`, `dive`, `echoedvoice`, `fly`, `healingwish`, `lunardance`, `magicbounce`, `phantomforce`, `pursuit`, `rebound`, `revivalblessing`, `shadowforce`, `skydrop`, `wish`).
