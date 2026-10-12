# Prompt21 internal API and evidence interpretation

This candidate is an untrusted companion, not an adopted knowledge wire,
carrier provider, completeness verdict or source certificate.

`importReplayPrefixWithMoveHistory(records, sourceCursor, context)` takes exactly
the existing importer arguments and returns recursively frozen
`{ replay: ReplayImportResult, public_move_history: PublicMoveHistory }`.
It completely admits/extracts the original replay first. History then reads only
the selected `source_rows`, `source_to_routed` and `routed_to_source`. It has no
crosswalk, request, private-binding or source-authority input. The original API,
result shape, active views and observable identity algorithms are unchanged.

The readonly history shape is:

```typescript
{
  source_cursor: number;
  appearances: {
    subject: string; // p1|p2:appearance:N, independently counted per side
    side: 'p1' | 'p2';
    start_source_index: number;
    end_source_index: number | null;
    disclosure_source_indices: readonly number[];
    carrier: null;
  }[];
  executions: {
    appearance: string;
    source_index: number;
    observed_at: number; // source_index + 1, exclusive boundary
    record: string;
    move: string;
    origin_tags: readonly string[];
    context_witnesses: {
      source_index: number;
      record: string;
      kind: 'transform' | 'called_move' | 'unsupported_writer';
    }[];
    origin_status: 'unannotated' | 'classified' | 'unsupported';
  }[];
  issues: {
    source_index: number | null;
    code: 'missing_carrier_provider' | 'unsupported_execution_origin'
      | 'unsupported_writer' | 'unresolved_appearance';
  }[];
}
```

Arrays, entries, nested context witnesses and companion replay are frozen. Exact
records/tokens are retained; duplicate executions remain separate indexed facts.
No subject uses display names, species, level, slot crosswalks or future evidence.
Each opening emits `missing_carrier_provider`; every carrier remains null. This
issue blocks carrier-dependent interpretation and cannot discharge assurance.

Supported lifecycle is single active position `p1a`/`p2a`. Switch/drag closes the
outgoing stint at that event index and opens a fresh stint. Replace records a
same-stint disclosure; it cannot reassign old receipts. Faint closes that side at
its index; win/tie closes every open side at its terminal index. Context starts
empty with each new appearance; executions snapshot context, so later resets and
disclosures never rewrite them.

Supported interpretation is deliberately narrow: bare four-field `-transform`
and the exact fifth field `[from] ability: Imposter`, plus move annotations
`[from] move: Sleep Talk` and `[from] move: Metronome`. Transform and called-move
witnesses coexist. Each exact `[from]` field is retained in source order.
Other origin tags produce `unsupported_execution_origin` while retaining the
receipt. Unknown `-transform` annotations, raw-admitted plain `transform`, and
`-activate`/plain `activate` with `move: Sketch` produce `unsupported_writer`
context; subsequent dependent executions remain unsupported. No acquisition
writer is implemented. Existing Mimic raw rejection remains in the original
admission path. This is not an exhaustive writer inventory.

Pinned source basis under `sim-core/node_modules/pokemon-showdown`:
`sim/battle-actions.ts:450-455` emits `[from] sourceEffect.fullname`;
`data/moves.ts:17520-17550` and `12202-12225` call Sleep Talk/Metronome;
`sim/pokemon.ts:1287-1290` emits Transform;
`data/abilities.ts:2056-2065` emits Imposter context. Temporary transformed slots
and reset are `sim/pokemon.ts:1251-1272,1449-1459`; Sketch writes current/base slots
at `data/moves.ts:17198-17202`, hence unsupported here. Source suppresses some
annotations (including Instruct at `sim/battle-actions.ts:386`): unannotated is
never proof of direct/original possession or current selectability. Nothing in
this API supplies starting originals, PP, legal actions or a verified current
move inventory.

Admission failures propagate unchanged `ReplayImportError` (`input`, `admission`,
`prefix` or `extraction` stage). History failures throw `PublicMoveHistoryError`:
`name`, `stage='history'`, `source_index:number|null`, `record:string|null`,
`code='malformed_history'|'unresolved_appearance'`, and a message. A malformed
global ledger has null index; selected row/lifecycle failures expose the original
source index. Move/replace/faint/Transform/Sketch requires an open supported
appearance; Transform also requires its target appearance. Terminal reopening
and unsupported active slots reject. No error returns replay/history/partial
executions. `unresolved_appearance` is a rejection, not successful ambiguity.

The exported reconstruction helper checks selected ledger shape, metadata-row
compatibility and positional inverse maps. It does not prove exhaustive
classification equivalence with the importer: a directly fabricated protocol row
containing valid framing or tier can pass these checks. The production companion
supplies the importer's checked classification. The helper is internal and
untrusted; successful reconstruction does not replace admission or certify source
emission, display-name continuity, roster identity or complete battle semantics.
