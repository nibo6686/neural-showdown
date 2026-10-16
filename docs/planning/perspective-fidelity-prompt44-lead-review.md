# Prompt44 lead decision — direct-switch design accepted with staged implementation

**Date:** 2026-10-13. **Verdict:** accept the corrected bounded design. No complete B3 authority or atomicity acceptance.

The lead read the design and its independent-review disposition, inspected the actual candidate session commit order, B2/delivery commits, native log mutators and serialization callsites. No validation workload ran. Original creation and restored re-emission remain distinct: replaying historical rows creates no new writer event.

## Three API decisions

| Decision | Lead disposition |
| --- | --- |
| Private B1/B2 actor-reference transfer | Approved only as controller/session-owned internal registration. No public native-object accessor, caller map, public holding metadata resolver or name/position fallback. Creation staging and validated pending restore are separate sources. |
| Tracked log and plain serialization | Approved for bounded candidate implementation and proof. Track known operations, preserve surviving row occurrences, reject dependent proof on unknown replacement/mutation, and produce plain serialized logs before clone/build paths. Preserve native set references and ordinary output bytes. No upstream package edits or persisted sidecar fields. |
| Synchronous no-fail install | Approved as the required transaction model, not a proven existing guarantee. All validation, detached allocation and user/native callbacks must finish before irreversible installation. Existing delivery/B2 commits contain checks; later integration must resolve that seam explicitly rather than assuming sequential calls are atomic. Ordinary resource-exhaustion/privileged monkeypatch attacks are outside the stated threat model. |

## First implementation boundary

[Prompt45](perspective-fidelity-prompt45-first-prompt.md) implements and proves only private actor leases, tracked native log/writer/send infrastructure and plain serialization/restored lineage transport. It does not expose usable committed event holdings or change prefix projection. This isolates the invasive runtime hook/serialization uncertainty before the final session commit/normalized-index association.

The next boundary will join routing/committed normalized indices and resolve the final installation transaction after these foundations pass. Do not combine drag/replace/Transform, replay attribution, B4/catalog or K-fact adoption. Unsupported source/mutation paths remain unbound; trusted native producer execution is not universal authentication of arbitrary calls.

One focused implementation/proof boundary is authorized, not another general design cycle. Original checkout stays intact, target positive fidelity disabled, and historical/semantic quarantines preserved. No staging, commits, publication, promotion or training.
