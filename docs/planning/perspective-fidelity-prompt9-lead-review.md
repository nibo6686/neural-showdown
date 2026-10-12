# Prompt 9 lead review — 2026-10-10

Decision: return PK-01 for a focused contract/fixture revision. The proposal architecture and original-source authority direction remain accepted. Exact schema freeze and PK-02 runtime implementation are not accepted yet.

## Evidence

Fresh lead checks with encoding overrides unset: fixture checker exits 0 (15 positive, 31 negative, 16 identity vectors, compact parity, causal suffix invariance); preservation checker exits 0 (900 protected files unchanged, four permitted cross-references changed); whitespace check exits 0 with line-ending advisories. The computed comparison digest drift is expected and remains unreviewed. Three independent lead read-only reviewers examined identity/history, authority/assurance and replay/privacy. The passing fixture checker does not cover the following contract inconsistencies.

## Required revisions

1. **Exact escape mapping.** Contract line 45 says control characters use lower-case hex, but the independent checker and fixture author use short escapes for backspace/form-feed/newline/carriage-return/tab. Freeze the standard short mapping plus lower-case `\u00xx` for remaining controls and add a literal all-controls vector before ports implement IDs.
2. **Replay source fork versus discovery revision.** Contract line 37 requires changed full sources to form starting revisions, while checker lines 197/202 require both byte-identical proved-fact retention and proof.source equal to the new starting.source. Those cannot coexist for a previously proved fact. Existing suffix fixtures reconstruct revision 0 and do not test the advertised parent chain. Lead decision: discovery parent revisions are same-source only. A changed full replay source begins a separately identified revision-0 starting lineage; facts must be re-proved against that source, not blindly carried across. Preserve prior snapshots and causal IDs/bytes; do not invent a cross-source parent proof. Add distinct same-source refinement and changed-source lineage fixtures, including one already-proved fact and one unknown fact that becomes justified.
3. **Layer/power representation.** K13 promises layers and K15 proved power, but the closed effect value only carries name/source_subject/observed_since/elapsed/remaining. Add minimal explicit reviewed representations so Spikes layer 1 differs from layer 2 and pending power can be represented with legitimate evidence/uncertainty. No runtime writer is thereby accepted.
4. **Timer subject binding.** `field_remaining` is an interval and the non-effect null `effect_key` rule permits only one such fact per side. Concurrent weather/terrain remaining-time facts need distinct effect bindings. Add explicit target identity or named effect timer representation, with simultaneous independent values and cross-binding negatives. Hidden timers remain unknown; structural examples do not imply legitimate exact knowledge.
5. **Typed privacy/reference checks.** Checker line 98 bans capability-related substrings in all data, contrary to the contract's inert names/display strings. Lines 252–276 infer references from any `sha256:` text, contrary to typed closure. A reviewer independently resealed an otherwise valid projection containing inert `audit_store` text and observed rejection. Traverse declared reference positions and apply structural capability exclusions. Inert capability-like and hash-looking text must pass; real private/future references and privileged dictionary traversal must reject.
6. **Obligation expansion.** Freeze per-property original/current/request context, subject enumeration and applicability rules. Mixed families cannot rely solely on a family-level `original_required` flag. Define which relevant roster/move/effect subjects must be covered so one fact per property cannot discharge an entire family. This is contract/structural coverage, not implementation of successful aggregate semantic assurance.

## Preserved decisions

Pre-effect owner delivery at the actual generation-before-pack/write seam is feasible and remains the legitimate provider direction. Imported source labels, hashes, packed control inputs and post-effect state are insufficient authority. Current fixtures intentionally remain incomplete. No weaker profile substitutes for the user's stronger perspective-knowledge goal. Projection generation remains trusted-local, with imported receipt trust unsupported.

## Next action

Release Prompt 10 / PK-01R to repair only these contract/checker/fixture issues and rerun bounded checks plus independent review. Preserve original Prompt 9 reports, logs and hash evidence. No runtime coding, attestation, commit, publication or training. Expected contract provenance drift remains pending.
