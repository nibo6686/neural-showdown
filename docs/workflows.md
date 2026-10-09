# Episode Evidence Workflow

This workflow describes the current opt-in v2 episode envelope for
`gen9randombattle`. It does not authorize dataset generation, model training,
or live-model behavior.

## Current acceptance — 2026-10-09

Pinned PIPELINE-002 capture, CE-08B incomplete/error delivery and the FCE-08
packet are accepted. Conditional faithful-result emission is independently
accepted only after validated supported original-to-terminal evidence and
successful cleanup. False remains conservative and mandatory for ineligible
results. Windows/cross-platform, datasets, training, live readiness and merge
approval remain outside this workflow's acceptance. Historical failed invocations
remain recorded; separate matching-source passes do not relabel them successful.

## Capture a fresh episode

1. Start `runPipelineEpisode` with `observable-battle-state/v2` enabled. Each
   boundary retains one owner-specific observation per player, including that
   player's request, exact normalized public prefix, cursor, and identities.
2. On each committed transition, retain both successor observations and the
   transition/actor reference. Append action bundles only for actors. A waiting
   player keeps boundary evidence but receives no action or DATA-001 row.
3. At a terminal boundary, require both observations to be terminated, agree on
   winner or tie, have null requests, and end in matching public `|win|` or
   `|tie` evidence. Keep the preceding source-backed turn-limit warning in the
   raw prefix when present.
4. The Python bridge validates the complete envelope and actor bundles before
   returning DATA-001 rows. It emits no rows for a zero-transition terminal and
   no output for an invalid result.

## Continue from a restored segment

1. Restore the simulator session to the predecessor's final committed boundary.
   The simulator snapshot stays in the simulator runtime and is never copied to
   the evidence envelope.
2. Pass the prior public evidence envelope as `predecessor_evidence` to
   `continuePipelineEpisode`. The runner validates the predecessor chain and
   requires its final nonterminal boundary to equal the current session origin
   before advancing.
3. With a valid predecessor, the new envelope includes that predecessor chain
   and inherits its origin coverage. Without one, it labels the result
   `segment_only`; a segment-local terminal is still an execution completion,
   not an initial-to-terminal capture.
4. A terminal-only fresh start is labeled `terminal_only`. It retains the final
   win/tie boundary without inventing an initial request, transition, or
   decision row.

## Validation boundary

TypeScript and Python validate envelope identities, owner/request joins,
predecessor continuity, per-perspective cursor and prefix extension, ordered
commits, actor-only records, terminal outcome and final-boundary references.
Rehashed semantic tampering fails before publication. Envelope hashes detect
inconsistent rewrites but are not signed provenance against a coordinated
rewrite of all evidence. The accepted conditional faithful-claim path validates all
current actor contracts and the supported original-to-terminal chain, closes the
owned session, then emits true only after successful cleanup. Python checks the
same claim from evidence before ordinary/bulk actor-only atomic publication.
False remains conservative; legacy v1, unbound/terminal-only, failed and incomplete
results cannot authorize true. Scoped runtime-flag review is accepted; final-tip integration/CI and merge readiness remain separate.

The simulator coverage manifest also binds callback and delayed-slot source
routes. C23 covers Wish, Healing Wish, Future Sight, and Revival Blessing while
keeping pending slot state private; Lunar Dance, Doom Desire, and Z-only
healreplacement have checked no-route dispositions. C22 callback composition
remains open for broader callback composition; Neutralizing Gas retains its
pinned generated no-route disposition. Ordered public health and item evidence
rejects false maps in both runtimes. Terminal Illusion authority comes from the
validated linked input/action/transition or full committed predecessor chain,
with stable ordered roster and exact prefix continuity. A bare terminal observation cannot authorize an unrevealed alias. Failed candidates retain no
validation authority. The bounded repairs await independent acceptance and do
not enable complete-episode publication.


The bounded terminal switch path validates the submitted canonical owned switch before using its request slot to bind an incoming unrevealed Illusion. Full results and compact sweeps stage this action against the already validated predecessor boundary before terminal semantic replay, then finish all actor/belief joins atomically. A bare envelope has no action authority for that incoming alias. Normal visible switches remain attributable only from a revealed identity or explicit addressed base/current non-Illusion abilities. Private terminal snapshot v2 switch history supports restoration separately and never grants public authority. Departed unrevealed item writers, including Frisk reveal and Recycle restoration, remain raw where the carrier cannot be attributed. Publicly established consumption history remains required across re-entry; a later ambiguous nickname collision restores that prior history. Current owned possession remains exact to the addressed request. Generated waiting requests retain full addressed side data; sparse historical wait rows cannot erase established owned evidence.


Historical prefix identity validation uses a fresh incremental SHA-256 array
stream within each parent-belief validation. It appends the existing canonical
record text and separators once, then copies the stream and closes the array
at each validated historical cursor. Canonical bytes, observation/belief
identities, cursor/order guards and wrong-hash rejection are unchanged. No
hash state is shared across candidates or validation calls. The focused npm
episode command explicitly skips the optimized long fixture; full capture
validation still checks the complete original-to-terminal chain.


### Historical implementation checkpoint — 2026-10-09, before independent review

The pending verdict below is retained as history; current scoped acceptance is
recorded above and in the closure audit.

CE-08B finalization guards run identity, evidence construction and validation before
attempting owned-session cleanup. Failure retains committed records, emits only
safe classified diagnostics and a construction/validation stage, and leaves a
null envelope unpublishable. Cleanup failure takes precedence while preserving
the earlier cause/stage. Python requires normalized exact positive-safe-integer
limits and bounded committed/rejected/stopped-attempt accounting before emitting
rows. See PIPELINE_EPISODE and the four-finding repair checkpoint; independent
CE-08B/FCE-08 acceptance remains pending.
