# Prompt22 proposed original-owner provider and causal binding prerequisites

Design/source proof only. The frozen knowledge contract, accepted source seam,
Prompt21 companion and Prompt15/16 decisions govern; this document adopts no
provider, schema, source registry or runtime caller. All Prompt21 carriers remain
null. A source row or a matching content hash is not a legitimate provider.

## Source feasibility and precise seams

Safe raw originals **can** be obtained in `LocalBattleEnv.resetWithOptions`
(`sim-core/src/env_manager.ts:793-802`): retain each `Teams.generate` array
immediately, before `Teams.pack`, then finish both owner-addressed original
deliveries before writing the `>start`/two `>player` payload. Existing code retains
only packed strings. `Teams.generate` delegates to the pinned generator
(`pokemon-showdown/sim/teams.ts:638-639`); gen9 `randomSet` returns ordered shuffled
moves and submitted fields at `data/random-battles/gen9/teams.ts:1586-1600`.
Native creation probe captures two six-member arrays through this actual env
path. Test taps are evidence of availability, **not** production certificates.

Packing preserves order but loses submission presence and nonpacked metadata
(`sim/teams.ts:114-205`). The literal absent/default pair produces identical
packed bytes. Generated arrays include `role`, omit named nature and may have
empty/undefined gender. Preserve the entire raw deep copy and a separately
reviewed enumeration of omitted/undefined fields; do not equate an unavailable
array with known submission absence. Generated `role` is not packed/submitted.
Propose treating it as privileged generator metadata, with an explicit pinned
packing rule; unsupported *submitted* fields still block eligibility under the
frozen contract. Lead must approve that interpretation before an adapter drops
metadata from the enumerated wire sets. Do not invent Hardy, RNG-derived gender,
HP, PP, effective ability/form or calculated stats from the provider alone.

`BattleStream` player command calls `Battle.setPlayer`
(`sim/battle-stream.ts:112-115`); `Battle.getTeam` unpacks the exact submission
(`sim/battle.ts:3094-3097`). `Side` retains team order and constructs Pokémon
(`sim/side.ts:207-212,267-272`). `Pokemon.set` aliases the constructor set and
normalizes/defaults it (`sim/pokemon.ts:316-387`). When the second side is present,
`setPlayer` starts immediately (`sim/battle.ts:3155-3187`). Format `onBegin`
precedes start actions (`1820-1887`); initial Crowned changes even `baseSpecies`
and `baseMoveSlots` (`2585-2618`). Initial abilities then alter current state.
Thus neither the first request nor any `base*` runtime field is original evidence.

Fresh request text arrives by native owner routing (`sim/battle-stream.ts`,
`getPlayerStreams`, sideupdate branch), from `Side.emitRequest`'s
`JSON.stringify(update)`. Actual env `ManagedPlayer.start` consumes the chunk
then handles requests (`env_manager.ts:513-527`); extractor `handleRequest`
(`state_extractor.ts:362-367`) parses/discards exact text. `request.raw` is parsed
state, not delivered bytes. S01c-2 must retain exact text and producer provenance.

`Side.getRequestData` enumerates **current** party order (`sim/side.ts:318-331`);
`getSwitchRequestData` emits mutable current/base fields (`sim/pokemon.ts:1099`).
Switching swaps Pokémon/positions (`sim/battle-actions.ts:127-134`). Duplicate
nicknames/species give identical request idents. Native object/set associations
can preserve identity locally; the addressed request alone cannot recover it.

Restoration uses original-order→current-position encoding
(`sim/state.ts:180-198`) and reconstructs set references/order (`94-128`), then
regenerates requests (`132-142`). This encoding is useful to validate continuity
against an independently held provider; its mutable `.set` values cannot create
that provider. Current env has Prompt16 active-request overrides
(`env_manager.ts:808-928`); Prompt15's original stale-request defect is historical.
Restore reemits and terminal history restoration remain different from fresh
addressed delivery (`850-866`).

## Proposed provider contract — internal capability, not new wire

The trusted creation owner holds a private immutable capability per origin with
two separately addressed views. Its private evidence includes exact public
origin tuple (battle_key/format/engine/rule_version), owner, original delivery
sequence0/cursor0, before_effects, complete raw generated array/presence ledger,
ordered roster slots1..N, ordered original moves1..M, exact packed submission and
pinned packing/generator rule versions. No seed/env_id or other-owner team goes
to a perspective consumer. Generation seed is creation machinery, never a fact
or consumer resolver. These are proposed internal fields, not additions to old
StepResult, snapshots, boundaries or the frozen source schema.

Capture by structured deep copy **before** packing; recursively freeze retained
values. Packing operates on a separate mutable copy, with equality to the exact
submitted bytes checked by the creation owner. Do not reconstruct omissions from
unpacking. Assign immutable roster identities from the retained original array
order, not a later side.pokemon position. Keep submitted absence, public pinned
normalization/default derivations and current effects distinct. Stats need their
own independently checked public Dex/rule calculation, not hidden state reads.

The session already knows the public battle_id before `resetWithOptions`
(`pipeline_integration.ts:372-396`); create/hold origin authority there and pass a
private creation capability to the future env provider. Standalone envs without
that legitimate association remain unsupported. Never derive origin authority
from an env-id string, seed, transported certificate or caller-supplied registry.
Owner addressing must finish before simulator submission. Missing either own
delivery/source association blocks original authority; no later request repair
may backfill it.

The current `SourceRegistryBuilder.addInitializationWitness`
(`perspective_knowledge_source.ts:111-116`) remains test-only.
`availability.original_provider` stays `not_adopted`; diagnostics still list
original_provider/fact_semantics/attribution/completeness as unsupported.
A later reviewed factory must accept the private native creation capability,
not JSON initialization witnesses, and separately validate the permitted wire
normalization. Source adoption is a later gate; it cannot be inferred from these
characterization controls.

Capabilities remain process-local and nonserializable. Sending TS provider JSON
to Python can prove structure/byte/held-row parity only; it cannot recreate
original authority. Independent Python source authority requires a separately
reviewed trusted creation-owner bridge supplying independently held provenance,
outside caller-controlled audit JSON. That bridge is an unresolved prerequisite,
not a new signing framework or adopted transport in this design. External/imported
capability or projection trust remains unsupported.

## Delivery prerequisites and causal request contract

Retain an internal emission trace at exact addressed text reception with owner,
producer-local emission identity, exact text, and producer-labelled
fresh_delivery/restore_reemit. Arrival alone is not a causal cursor. Requests are
emitted before update fanout (`env_manager.ts:935-940`). Settle first, then bind
the accepted delivery to the exact projected owner prefix and committed boundary
observation ID. Match parsed text to the request.raw actually used, while retaining
the byte-exact text. Equal-length prefixes or equal JSON text are not equal causal
delivery. Bind prefix records/ID as well as cursor, origin and owner.

Every transition creates a new candidate env (`pipeline_integration.ts:494-505`),
so local counters restart. Maintain a **session-owned committed per-owner request
sequence**0..N separately from local emission identity. Registry `freeze`
requires unique contiguous owner sequences (`perspective_knowledge_source.ts:139`).
Forks retain parent authority and independently append branch deliveries; never
mix candidate counters or sibling rows. Multiple equal-text fresh emissions remain
distinct deliveries; preserve all emissions privately, select the causally
applicable one explicitly. Original sequence0 and request sequence0 are separate
source-type namespaces. Candidate rejection discards tentative joins for both
owners atomically; capture before candidate retirement/commit, not afterward.

Wait rows may have fresh addressed wait delivery but grant no action authority.
Requestless/terminal boundaries have no current request; retained text is stale
history only. Restore reemit retains its original delivery reference/provenance;
it cannot masquerade as a new fresh delivery. Original provider persists through
restoration unchanged. A fresh post-restore delivery needs its own causal prefix
and committed sequence. Snapshot/import-only restoration without independently
held original/delivery history remains incomplete. Prompt16 legal overrides do
not establish request or original source authority.

S01c-2 dependencies: private env text/provenance ledger; session commit/fork
sequence; settled per-owner prefix/observation joins; tentative-candidate rollback;
wait/requestless/terminal suppression; restore provenance and lifetime through
publication/consumer verification. Prompt15 S01c-3 publication and S01c-4 K adapter
remain separate and blocked on these plus the carrier resolver. No normalized
flags/default PP become knowledge through the ledger.

## Causal crosswalk prerequisites

There is currently no supported production carrier crosswalk. Add no crosswalk
argument to Prompt21. A future internal owner-only crosswalk must prove:

1. Same independently held origin/provider/owner and immutable original slot.
2. Native constructor birth association from the exact submitted team order to
   stable set/Pokémon object identity, before effects and party reorder.
3. Request-time current party-position and active-position association from that
   retained identity, with fresh addressed delivery/prefix/boundary join.
4. Appearance-opening source event identity/index in the **same causal public
   ledger**, and context/cursor at which the association was established.
5. Restore continuity with original provider and trusted parent/candidate history;
   missing/duplicate/foreign associations or malformed order mapping reject.

Necessary extension: env-local native source observer at the unpack→Side
constructor seam and request/public-event emission seams. One candidate mechanism
for later proof is the local BattleStream start/player command bridge installing
a **per-instance** getTeam observer before either player command: associate exact
unpacked set references with addressed original order before Side constructs.
Track those references through native switches and validated restore order,
collect request-time mappings and actor→public-event mappings before visibility
formatting. No prototype patch/node_modules edit is proposed. This mechanism is
source-feasible but **not runtime-proved here**; callback order, constructor
references, automatic drag, event indexing and restoration need their own gate.
If that observer cannot be made complete without an engine hook, return the
specific hook extension to the lead; never use post-effect values as a fallback.

Only identity association may be read at this seam; no opponent hidden values,
RNG, timers or dynamic hidden state may become facts. Each owner gets its own
association only. Illusion may change display and replace discloses the same
appearance; neither proves a carrier. Transform/called/acquired execution changes
context/inventory, not birth identity. Move incarnations remain a separate writer
problem. A display, nickname, species, level, current party index or extractor
slot cannot discharge any of these joins.

Receipt interpretation is a separate derived relation, never mutation/relabeling
of historical Prompt21 receipts or their null carrier fields. Require a supported
crosswalk established causally at/before the execution's exclusive observed_at;
join its exact appearance/source index/origin/owner. A later opponent reveal or
restoration-only association cannot backdate it. Unsupported origin/writer issues
remain blocking even with a proven carrier; execution proves no PP/selectability
or original membership. Existing supplied Random/OU HTML histories have no local
birth/provider provenance and remain unbound.

Preserve `public-replay-owner-starting/v1` separately: full-source original
certificates may retrospectively refine **own starting** facts/crosswalk only,
under a complete supported exclusion/continuity scan. They never enter causal
current prefixes, relabel earlier appearances or resolve opponent dynamics.
Simulator owner delivery is not a substitute public-replay certificate.

## Lead decisions and remaining blockers

Approve the narrow proposed scopes/gates in the companion runtime-boundaries
document before any coding. Decisions: raw generator metadata/undefined omission
normalization; lifecycle/lifetime of private origin/provider and branch delivery
capabilities; source-observer mechanism and supported event inventory; whether
registry provider adoption is reviewed with provider capture or separately.
The cross-process trusted creation-owner bridge is also a required lead decision
before Python source authority or semantic publication can be claimed.
Missing originals, unsupported writer/identity lifecycle, incomplete delivery
joins and absent crosswalk remain blocking. Complete owner loadout/fidelity is
unverified even if this provider later passes; no assurance profile is promoted.
