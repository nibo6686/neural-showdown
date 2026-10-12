# Prompt22 ordered proposed runtime scopes and review gates

Proposal only. Every row needs a separate lead-authorized prompt. Do not combine
provider, delivery ledger, carrier resolver, publication and consumer adoption.
Preserve existing v1/v2 bytes, IDs, capture-flag meaning, registry test-witness
semantics and snapshots unless a later lead explicitly reviews an extension.

| Order | Smallest boundary / proposed files | Required gate before continuing |
|---|---|---|
|1|S02a pre-effect owner retention: new `sim-core/src/original_owner_provider.ts`, new provider test; narrow `env_manager.ts` creation tap; private origin handoff in `pipeline_integration.ts` only if needed|Actual native generate→copy→pack→submission path, both owners; immutable complete array/order/omissions; packed-byte association; initial Trace/Imposter/Schooling/Crowned controls. No registry promotion or current carrier binding yet.|
|2|S01c-2 delivery ledger: private `ManagedPlayer`/env ledger and session commit map in `env_manager.ts`/`pipeline_integration.ts`; new `request_delivery_ledger.test.ts`|Exact native JSON text, owner routing, producer provenance, settled-prefix joins; env-local counter collision, candidate rollback, wait/revival/requestless/terminal and restore/reemit. Old result/snapshot/bundle identity comparisons pass.|
|3|S02b native birth and causal owner crosswalk: new `owner_identity_crosswalk.ts` + tests; narrowly reviewed instance observer/restore association in env/session|Pre-effect constructor identity; actual native request/current-order and appearance-opening event mappings; duplicates, automatic drag, Illusion/Transform, both owners, original-index events, causal prefix mismatch, branch/restore continuity. No caller name/position fallback.|
|4|S02c source verifier/provider adoption: reviewed private capability factory in TS/Python source seam + new tests, normalization/rule proofs separately scoped|Real creation capability required, test witness/imported JSON rejected as production authority; exact owner/origin/submission/prefix checks and resealed foreign/missing/source-swapped negatives. Independent serialized UTF-8 TS/Python checks; source presence alone leaves semantics/completeness unverified.|
|5|S01c-4 resolver-backed request/knowledge adapter, separately authorized new modules/tests|Requires1–4. Fresh owner request facts only; omissions unknown, PP0 retained, incarnation proofs, bench/wait K08/K20 obligations independently enumerated. No unsupported resolver fallback; originals/current facts remain separate.|
|6|S01c-3 joined publication and later consumer adoption, separate prompts/modules/tests|Real full contiguous history/legacy joins, both-owner closure/nonactor rows, ordinary/full/compact parity; Python publication must reject resealed semantic/privacy attacks with zero output; genuine single-perspective consumer has no other-owner/audit/future capability. Neither is authorized here.|

Order1 can be reviewed without2, but fresh addressed current binding/retention
cannot pass until2. Both1/2 are prerequisites to3;3/4 precede any facts or bindings
that depend on roster identity. Original calculations/defaults/required-family
semantic coverage may need additional bounded writer work. None of these selected
gates establishes strong completeness or changes faithful_complete_episode.

Gate4's TS/Python factory names are proposed scopes, not a portable capability.
Current capabilities are process-local/nonserializable (Python source seam
`__reduce_ex__`, line81). Serialized parity verifies structure/held-row agreement
only. An independently reviewed trusted creation-owner bridge must establish
Python source authority before semantic publication; transported TS provider JSON
alone is never authority. This prerequisite needs its own lead decision and
bounded write scope. No bridge/signing mechanism is adopted here.

## Review-plan-tests gap analysis

P0 before provider adoption: a test-owned pre-pack tap alone does not prove a
production provider is invoked. Gate1 must fail red on the present env path, then
prove the actual creation owner receives and retains the legitimate addressed
capability before payload write. A caller-supplied matching certificate is a
negative, not an oracle. Capture originals lost by packing; compare literal
fields/omissions independently of production normalization helpers.

P0 before causal bindings: a flat request and a private WeakMap demonstration
do not prove the full source route. Gate3 must use the actual producer's birth,
request and appearance-event hooks through the exact selected indexed ledger.
Throwing suffix guards remain; provider bytes alone do not prove the current
carrier. Absent/duplicate/unsupported actor mappings block output atomically.

P0 before ledger adoption: local sequence reuse across candidate restores can
graft deliveries or make registry construction fail. Gate2 needs two consecutive
real transitions and a rejected candidate, proving unique committed sequences,
same-origin parent closure and no tentative rows. Equal JSON/rqid/cursor is
insufficient: equal-length foreign records must reject. Force restore reemits to
arrive before fresh deliveries and prove only the supported delivery is selected.

P1 before any consumer/publication: require actual creation→private delivery→
source validator→causal binding→UTF-8 serialization→independent Python verifier→
publication→owner-only consumer. Every helper has a real caller-path gate. Existing
structural positives cannot stand in for original fact semantics or source
provenance. Raw secrets remain outside old artifacts; hashes never grant access.

## Explicit validation controls for later boundaries

- Both-owner native generated six-member teams; copy-before-pack mutations to
  raw array/moves/EV/IV prove original copy detached; omitted nature/happiness/ball,
  empty item, EV0/IV0 and random gender remain distinct. Unknown extra submitted
  fields reject; generator metadata disposition is source-backed.
- Initial Trace/Imposter/Schooling and Crowned start; first request/current/base
  fields differ while retained originals remain byte-identical. Calculated stats
  use a separately implemented public pinned Dex/rule oracle, no hidden reads.
- Duplicate same nickname/species/level/moves and equal request idents; actual
  switch2 swaps current order while immutable subjects stay roster1/2. Drag and
  team-order lifecycle admitted explicitly; no positional/nickname fallback.
- Illusion impersonation, same-stint replace, restoration and reentry; Transform
  and called/acquired execution keep identity independent of inventory and retain
  unsupported writers. Earlier receipt bytes/appearance subjects never change.
- Fresh equal-text re-deliveries differ in delivery identity; stale request,
  restore reemit, wait, forced/revival selection, requestless and terminal never
  resurrect actionable knowledge. Terminal retains no request authority.
- Uninterrupted versus serialize/restore/continue: preserve original authority,
  parent prefix, both owner delivery history, committed sequence and crosswalk;
  bare snapshot without original capability fails. Sibling graft/rejected candidate
  drops both-owner tentative joins. Verify cleanup as well as positive continuation.
- Foreign owner/source/origin, forged before_effects, swapped packed submission,
  lost original delivery, mismatched request text, wrong/equal-length prefix,
  missing/duplicate birth or event association: fully resealed negative rejects
  before any usable binding/publication/consumer result. Match IDs first so a
  cryptographic rejection cannot mask the semantic test.
- Receipt-to-carrier only with supported same-origin opening proof available by
  execution cursor. Remove it, date it later, replace it with future opponent
  disclosure or replay-starting hindsight proof: binding blocks and old receipts
  remain unchanged. Identical prefix histories for both perspectives stay equal.

Current test file proves ten bounded source-characterization cases, not these
future production gates. Existing source tests cover their accepted held-row
join scope only. Future implementation must explicitly label which controls
remain red/unsupported; no skipped cases, weakened positives or guessed providers.
