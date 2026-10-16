# Prompt60 private current request-field contract

Candidate: `/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/native11-recovery-2026-10-14/candidate`.

Authority is the existing exact canonical Pokemon.getSwitchRequestData return → actual B1/B2 native actor/original slot → side request/emit → receipt → selected committed delivery. No value equality, name, position, snapshot label or decoded profile can create that chain. The row tap captures stats reference/value, details/ball presence and literal values, plus contemporaneous native tuples strictly for corroboration. Before installation, presence, nested reference, values and native freshness are rechecked. Facts come from the emitted row, never from native fields used to fill omissions.

| Current fact | Exact source and meaning | Presence/absence policy |
|---|---|---|
| K03 calculated_stats | Returned `stats.{atk,def,spa,spd,spe}`; pinned Pokemon writer copies `baseStoredStats`, not `storedStats`, boosts or effective getStat | Exact five integer values. Missing key → unknown/not_emitted; malformed/copied/altered tuple rejects. Transform may copy effective storedStats while this declared tuple remains different |
| K03 hp_max | Exact positive denominator in returned `condition`, joined to existing health tuple and cursor | `0 fnt` or no denominator → unknown/not_emitted. No native maxHP or original maxHP substitution. Positive HP must not exceed max |
| K04 details | Returned `details` unchanged; writer uses `this.details`, not a rebuilt current/hidden view | Missing key → unknown/not_emitted; exact ordered details grammar only; raw string retained |
| K04 level | Complete details `, L<n>` or pinned writer's omitted-level100 convention | Known100 only from a complete admitted details string; missing details → unknown |
| K04 gender | Complete details M/F tag | No tag in this complete writer form → known_absent (declared genderless); missing details → unknown, never absence |
| K04 shiny | Complete details trailing `, shiny` | Present tag true; absent tag in a complete admitted details string false. Missing details → unknown, not false |
| K04 ball | Returned `pokeball` literal ID | Missing key → unknown/not_emitted, not default Poké Ball. Present nonempty ID retained literally; no alias normalization or inferred absence |

Source: pinned npm0.11.11 `sim/pokemon.ts:getSwitchRequestData` (stats/baseStoredStats, details/condition/pokeball), `getUpdatedDetails` (species, omitted level100, M/F and shiny ordering), `transformInto` (storedStats copied independently), `setSpecies`/`formeChange`; existing `battle_helpers.ts:parseDetails` reused behind the exact-writer guard. Names are inert values, never identity authority. This adapter interprets **request-declared** stats/details, not every effective/rendered transformation attribute.

New fixed profile `native-owner-details/v1`, ID `sha256:210f8744aa1019801975c4490fc9c75442ac4721a2ec49a0a46533a82149d7c8`, discriminator `perspective-knowledge-consumer/native11-details-v1`, carries explicit `current_stats_semantics: request-declared-baseStoredStats/v1`. Earlier private assets remain immutable. Existing Prompt59 original interpretation checks are shared unchanged with the fixed successor decoder. Existing health/identifier/options and canonical actions retain their semantics; result stays incomplete. Arbitrary candidate decoding grants no authentic consumer capability.

Original starting and interpretation objects persist by reference. Emitted resolved current gender/details cannot repair original submitted absence, unresolved random gender or partial submitted EV/IV facts. Current request fields are prepared for both owners with existing atomic preflight/install/discard. Previous immutable reads remain unchanged. Failed candidates retain committed pairs and use fresh retry; close revokes through the existing lifetime.

Actual captured move/forced/Revival/wait rows may supply fields. Fainted rows can supply stats/details/ball while lacking a maxHP denominator. Terminal/requestless boundaries have no fresh fields (unknown/not_emitted). Missing capture or unsupported overlay declaration lineage stays unknown/unsupported_writer; no stale carry or new recoverable-choice support. Public/opponent adapters, move incarnations, Python, completeness and positive fidelity remain outside this boundary.
