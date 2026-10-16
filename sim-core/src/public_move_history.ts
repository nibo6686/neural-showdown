import { helperContext as readerContext, HISTORICAL10_CONTEXT, type ReaderContext } from './version_profile';
import { validateRawProtocolRecord } from './observable_state';
import type { ReplayImportResult } from './replay_import';
import type { PlayerID } from './types';

export interface PublicMoveAppearance {
  readonly subject: string;
  readonly side: PlayerID;
  readonly start_source_index: number;
  readonly end_source_index: number | null;
  readonly disclosure_source_indices: readonly number[];
  readonly carrier: null;
}
export interface PublicMoveContextWitness {
  readonly source_index: number;
  readonly record: string;
  readonly kind: 'transform' | 'called_move' | 'unsupported_writer';
}
export interface PublicMoveExecution {
  readonly appearance: string;
  readonly source_index: number;
  readonly observed_at: number;
  readonly record: string;
  readonly move: string;
  readonly origin_tags: readonly string[];
  readonly context_witnesses: readonly PublicMoveContextWitness[];
  readonly origin_status: 'unannotated' | 'classified' | 'unsupported';
}
export interface PublicMoveHistoryIssue {
  readonly source_index: number | null;
  readonly code: 'missing_carrier_provider' | 'unsupported_execution_origin' | 'unsupported_writer' | 'unresolved_appearance';
}
export interface PublicMoveHistory {
  readonly source_cursor: number;
  readonly appearances: readonly PublicMoveAppearance[];
  readonly executions: readonly PublicMoveExecution[];
  readonly issues: readonly PublicMoveHistoryIssue[];
}
export class PublicMoveHistoryError extends Error {
  readonly stage = 'history';
  constructor(public readonly source_index: number | null, public readonly record: string | null,
    public readonly code: 'malformed_history' | 'unresolved_appearance', reason: unknown) {
    super(`Public move history at source ${source_index ?? 'input'}: ${String(reason)}`);
    this.name = 'PublicMoveHistoryError';
  }
}

type HistorySource = Pick<ReplayImportResult, 'source_cursor' | 'source_rows' | 'source_to_routed' | 'routed_to_source'>;
type Stint = { subject: string; side: PlayerID; start_source_index: number; end_source_index: number | null;
  disclosure_source_indices: number[]; carrier: null };
type ActiveStint = { appearance: Stint; context: PublicMoveContextWitness[] };
const CALL_TAGS = new Set(['[from] move: Sleep Talk', '[from] move: Metronome']);

function freezeTree<T>(value: T): T {
  if (value !== null && typeof value === 'object') {
    for (const child of Object.values(value)) freezeTree(child);
    Object.freeze(value);
  }
  return value;
}

/** Internal history only: source admission is the replay adapter's responsibility. */
export function reconstructPublicMoveHistory(source: HistorySource, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): PublicMoveHistory {
  readerContext(rulesContext);
  if (!source || !Number.isSafeInteger(source.source_cursor) || source.source_cursor < 0
    || !Array.isArray(source.source_rows) || source.source_rows.length !== source.source_cursor
    || !Array.isArray(source.source_to_routed) || source.source_to_routed.length !== source.source_cursor
    || !Array.isArray(source.routed_to_source)) {
    throw new PublicMoveHistoryError(null, null, 'malformed_history', 'Invalid selected source ledger/cursor/maps.');
  }
  const appearances: Stint[] = [];
  const executions: PublicMoveExecution[] = [];
  const issues: PublicMoveHistoryIssue[] = [];
  const counts = { p1: 0, p2: 0 };
  const active: Partial<Record<PlayerID, ActiveStint>> = {};
  let routed = 0;
  let terminal = false;
  let started = false;
  const requireAppearance = (ident: string, index: number, record: string): ActiveStint => {
    const side = /^p([12])a: /u.exec(ident)?.[1];
    const stint = side ? active[`p${side}` as PlayerID] : undefined;
    if (!stint) throw new PublicMoveHistoryError(index, record, 'unresolved_appearance', 'No open supported single-active appearance.');
    return stint;
  };
  for (let index = 0; index < source.source_cursor; index++) {
    const row = source.source_rows[index];
    const record = row?.record;
    try {
      if (!row || row.source_index !== index || typeof record !== 'string'
        || /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/u.test(record)
        || row.routed_index !== source.source_to_routed[index]) throw new Error('Malformed indexed row.');
      if (row.kind !== 'protocol') {
        if (row.routed_index !== null || !['room-presence', 'replay-rated', 'framing', 'tier'].includes(row.kind)) {
          throw new Error('Malformed metadata mapping.');
        }
        if (row.kind === 'framing' && record !== '|'
          || row.kind === 'tier' && record.split('|')[1] !== 'tier'
          || row.kind === 'replay-rated' && (started || record !== '|rated|')
          || row.kind === 'room-presence' && (started || !record.startsWith('|j|☆')
            || !record.slice(4) || record.slice(4).trim() !== record.slice(4) || record.slice(4).includes('|'))) {
          throw new Error('Record does not match admitted metadata classification.');
        }
        if (row.kind === 'framing' || row.kind === 'tier') validateRawProtocolRecord(record, rulesContext);
        continue;
      }
      if (row.routed_index !== routed || source.routed_to_source[routed] !== index) throw new Error('Malformed inverse mapping.');
      routed++;
      validateRawProtocolRecord(record, rulesContext);
      const parts = record.split('|');
      const command = parts[1];
      if (command === 'start') started = true;
      if (command === 'request' || command === 'split') throw new Error('Private transport is not history input.');
      if (command === 'switch' || command === 'drag') {
        if (terminal || !/^p[12]a: /u.test(parts[2])) {
          throw new PublicMoveHistoryError(index, record, 'unresolved_appearance', 'Unsupported opening lifecycle.');
        }
        const side = parts[2].slice(0, 2) as PlayerID;
        if (active[side]) active[side]!.appearance.end_source_index = index;
        const appearance: Stint = { subject: `${side}:appearance:${++counts[side]}`, side,
          start_source_index: index, end_source_index: null, disclosure_source_indices: [], carrier: null };
        appearances.push(appearance);
        active[side] = { appearance, context: [] };
        issues.push({ source_index: index, code: 'missing_carrier_provider' });
      } else if (command === 'replace') {
        requireAppearance(parts[2], index, record).appearance.disclosure_source_indices.push(index);
      } else if (command === '-transform' || command === 'transform') {
        const stint = requireAppearance(parts[2], index, record);
        requireAppearance(parts[3], index, record);
        const supported = command === '-transform' && (parts.length === 4
          || parts.length === 5 && parts[4] === '[from] ability: Imposter');
        stint.context.push({ source_index: index, record, kind: supported ? 'transform' : 'unsupported_writer' });
        if (!supported) issues.push({ source_index: index, code: 'unsupported_writer' });
      } else if ((command === '-activate' || command === 'activate') && parts[3] === 'move: Sketch') {
        requireAppearance(parts[2], index, record).context.push({ source_index: index, record, kind: 'unsupported_writer' });
        issues.push({ source_index: index, code: 'unsupported_writer' });
      } else if (command === 'move') {
        const stint = requireAppearance(parts[2], index, record);
        const tags = parts.slice(5).filter(tag => tag.startsWith('[from]'));
        const unsupported = tags.some(tag => !CALL_TAGS.has(tag)) || stint.context.some(w => w.kind === 'unsupported_writer');
        const context = stint.context.map(w => ({ ...w }));
        for (const tag of tags) if (CALL_TAGS.has(tag)) context.push({ source_index: index, record, kind: 'called_move' });
        if (unsupported) issues.push({ source_index: index, code: 'unsupported_execution_origin' });
        executions.push({ appearance: stint.appearance.subject, source_index: index, observed_at: index + 1,
          record, move: parts[3], origin_tags: tags, context_witnesses: context,
          origin_status: unsupported ? 'unsupported' : context.length ? 'classified' : 'unannotated' });
      } else if (command === 'faint') {
        const stint = requireAppearance(parts[2], index, record);
        stint.appearance.end_source_index = index;
        delete active[stint.appearance.side];
      } else if (command === 'win' || command === 'tie') {
        for (const side of ['p1', 'p2'] as const) {
          if (active[side]) active[side]!.appearance.end_source_index = index;
          delete active[side];
        }
        terminal = true;
      }
    } catch (error) {
      if (error instanceof PublicMoveHistoryError) throw error;
      throw new PublicMoveHistoryError(index, typeof record === 'string' ? record : null, 'malformed_history', error);
    }
  }
  if (routed !== source.routed_to_source.length) {
    throw new PublicMoveHistoryError(null, null, 'malformed_history', 'Extra inverse mapping rows.');
  }
  return freezeTree({ source_cursor: source.source_cursor, appearances, executions, issues });
}
