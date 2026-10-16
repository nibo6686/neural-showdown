# Prompt29 — 0.11.10→0.11.11 migration spike

## Status

Read-only assessment complete; proposal awaiting lead decision. **Recommend verified npm 0.11.11 before B3, after a separately authorized migration and focused target gates. Do not upgrade or implement B3 yet.** No install, build, test, simulator execution, replay download, production/lock/node_modules edit, commit or publication occurred.

## Source Materials

Current AGENTS/AGENT_PROTOCOL and review state; Prompt28 lead acceptance, B1/B2 API contracts, Prompt26 B3 design; five-replay diagnostic disposition/input inventory; current plan, locks, coverage manifest/checker and version-bound local consumers. Primary remote sources: [npm 0.11.11 metadata](https://registry.npmjs.org/pokemon-showdown/0.11.11), [tagged release](https://github.com/smogon/pokemon-showdown/releases/tag/v0.11.11), [exact upstream revision](https://github.com/smogon/pokemon-showdown/tree/739a5e1fee432ad80ff7136d70cca993be358b59). Detailed [artifact evidence](perspective-fidelity-prompt29-artifacts.json), [upstream comparison](perspective-fidelity-prompt29-upstream.json), [source change matrix](perspective-fidelity-prompt29-source-matrix.md) and [migration boundary/gates](perspective-fidelity-prompt29-migration-boundary.md).

## Goal / Intent Alignment

Select a truthful target before B3 depends on native writer/routing behavior, while preserving accepted 0.11.10 evidence and B1/B2 trust/lifetime boundaries. Resolve the concrete Natural Cure compatibility question without implying replay identity authority or completeness.

## Current State

Both npm tarballs match registry SHA-512 SRI and SHA-1. 0.11.11 tarball SHA-256 is `49af14aaed1084887f756372c7386c9987905930cc848ed31e9202c10c592d66`; its `gitHead` equals tag commit `739a5e1fee432ad80ff7136d70cca993be358b59`. All 386 shipped raw files selected from sim/data/config/lib plus package/build/protocol match that upstream revision. Every 0.11.10 bundled file matches the installed package; the separate active `config/config.js` is inventoried and preserved.

The GitHub release was published 2026-07-28. Observed upstream master is `942cda71d14bf0618bd57991708a2e2734b6daba` (commit date 2026-10-10), a different revision. Neither the tag nor master identifies the deployed public server or any saved replay's exact emitter.

Fourteen relevant B1/B2 methods are raw-identical, including getTeam/setPlayer, Teams pack/unpack and serializer/fromJSON/order/reference seams. This supports source feasibility, not target runtime acceptance: constructors, state fields, battle start, requests and mechanics changed. Generic state serialization preserves new/renamed fields; old snapshot restoration cannot be inferred from unchanged serializer code.

Gen9 Random Battle retains its mod/team/ruleset, adds `bestOfDefault`, and changes generator selectors and candidate data: 507→509 species, 869→879 set rows, 131 existing entries and 30 levels changed. Move candidates 350→349; Gale Wings replaces Steely Spirit in the ability candidate union. Equal old seeds cannot be treated as equal teams or trajectories.

Package main/types layout is stable; postinstall was removed and several dependencies/optional native dependencies changed. Metadata still says Node≥16, while the build launcher advertises ≥22 and probes global fetch. Existing Node24.21.0 is a suitable proposed target; no target imports/build were executed.

Natural Cure's target switch-out callback emits ordered `[from] ability: Natural Cure`, `[silent]` tags. The current 0.11.10 grammar admits the first tag only; exact source-backed target/replay policy is needed. Other changed families and audiences are bounded by the finite source matrix, not a mechanics-wide audit.

## Constraints / Open Questions

Lead must choose explicit historical-reader/profile support, unversioned snapshot admission policy, and exact replay compatibility union. Current snapshots lack an engine-version field; existing transition/publication and K-source consumers are hard-pinned to 0.11.10. A lock bump alone would mislabel or reject target records. The K-source profile cannot automatically adopt target-native facts.

Old fixture bytes, IDs, logs and attestations remain historical. Canonical identity algorithms and same-input mathematical vectors remain applicable; target-generated goldens, source reachability, actual B1/B2 wiring and B3 indices need target proof. Pending forced-switch/Revival B2 witnesses remain mandatory. The broader three failures, capture-flag meaning and training gates remain unchanged.

## Options Considered

| Option | Benefit | Cost/risk |
|---|---|---|
| Stay 0.11.10; exact newer replay compatibility only | Small immediate grammar boundary; old native evidence retained | B3 built on older source; dual replay/native scope and later migration repeat |
| Stage 0.11.11 migration before B3 — recommended | Verified target supports reported Natural Cure form; avoids building B3 against retired seams | Moderate profile/identity/coverage work and focused fresh gates; no inherited completeness |
| Maintain two active native engines | Explicit historical snapshot execution | Higher dependency/routing/validation cost; unnecessary unless historical execution is required |

## Recommendation

Approve only the [concrete migration boundary](perspective-fidelity-prompt29-migration-boundary.md): exact dependency pin, honest version/profile consumers, new target inventory/grammar, immutable historical treatment and focused target B1/B2—including forced/revival—proof. Reuse source-equivalent evidence selectively; do not blanket-retest historical checks or carry old attestations forward. Widen validation only for a demonstrated semantic dependency, newly reachable family, consumer/schema change or broader support claim.

## Planning Handoff

Next skill: `draft-implementation-plan`, after lead resolves the three compatibility decisions. Parent retains consequential decisions; one Luna/xhigh read-only lane classified B3/protocol deltas without tests or duplicated B1/B2/generation scans. Exact commands and preservation are linked in [research evidence](perspective-fidelity-prompt29-research.json). Stop before upgrade execution or B3.
