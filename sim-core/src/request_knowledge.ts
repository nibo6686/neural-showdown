import { createHash } from 'node:crypto';
import { parseKnowledgeJson } from './perspective_knowledge';

/**
 * request-knowledge/v1 sidecar (Prompt 14 / S01b). Pure builder from the exact addressed request text, the
 * owner and the already-validated v1/v2 observation of the same boundary. It never feeds legal-action
 * construction and never changes an observation. Null means "the raw key was absent", never a default.
 * See docs/contracts/REQUEST_KNOWLEDGE.md.
 */
export const REQUEST_KNOWLEDGE_SCHEMA = 'request-knowledge/v1';
export const FRESH_DELIVERY = 'fresh_delivery';
const MAX_RAW_SCALARS = 65536;
const OBSERVATION_SCHEMAS = ['observable-battle-state/v1', 'observable-battle-state/v2'];
const OWNERS = ['p1', 'p2'];

export class RequestKnowledgeError extends Error {
  constructor(readonly code: string) { super(code); this.name = 'RequestKnowledgeError'; }
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;
const need = (condition: unknown, code: string): void => { if (!condition) throw new RequestKnowledgeError(code); };
const isObject = (value: Json): boolean => typeof value === 'object' && value !== null && !Array.isArray(value);
const isInt = (value: Json): boolean => Number.isInteger(value) && value >= 0 && value <= 2147483647;
const onlyKeys = (value: Json, allowed: string[], code: string): void => need(Object.keys(value).every(key => allowed.includes(key)), code);

export interface RequestKnowledge {
  schema_version: string; id: string; battle_id: string; perspective: string; observation_schema_version: string;
  observation_id: string; event_cursor: number; presence: string; request_present: boolean; raw_request: string | null;
  rqid: number | null; active: Json;
}

function scalars(text: string): number { let n = 0; for (const _ of text) n++; return n; }

/** Canonical form of PERSPECTIVE_KNOWLEDGE.md for this record class: ASCII keys sorted, minimal integers, no normalization. */
export function canonicalRequestKnowledgeJson(value: Json, key = ''): string {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') { need(isInt(value), 'wire-number'); return String(value); }
  if (typeof value === 'string') { need(scalars(value) <= (key === 'raw_request' ? MAX_RAW_SCALARS : 256), 'wire-size'); need(!/[\ud800-\udfff]/.test(value.replace(/[\ud800-\udbff][\udc00-\udfff]/g, '')), 'wire-surrogate'); return JSON.stringify(value); }
  if (Array.isArray(value)) return '[' + value.map((entry: Json) => canonicalRequestKnowledgeJson(entry)).join(',') + ']';
  need(isObject(value), 'wire-type');
  return '{' + Object.keys(value).sort().map(key => { need(/^[\x00-\x7f]*$/.test(key), 'wire-key'); return JSON.stringify(key) + ':' + canonicalRequestKnowledgeJson(value[key], key); }).join(',') + '}';
}

export function requestKnowledgeId(record: Json): string {
  const { id: _id, ...body } = record;
  return 'rkn-' + createHash('sha256').update(REQUEST_KNOWLEDGE_SCHEMA + '\n', 'ascii').update(canonicalRequestKnowledgeJson(body), 'utf8').digest('hex');
}

const fainted = (condition: string): boolean => /(^| )fnt$/.test(condition);

/** Strict singles grammar of one addressed request; unknown keys fail closed. */
function parseRaw(owner: string, text: string): { kind: string; raw: Json } {
  need(typeof text === 'string' && scalars(text) <= MAX_RAW_SCALARS, 'raw-size');
  let raw: Json;
  try { raw = parseKnowledgeJson(text); } catch { throw new RequestKnowledgeError('raw-json'); }
  need(isObject(raw), 'raw-grammar');
  need(!raw.teamPreview, 'team-preview');
  onlyKeys(raw, ['active', 'wait', 'forceSwitch', 'side', 'rqid', 'noCancel'], 'raw-grammar');
  need(['active', 'wait', 'forceSwitch'].filter(key => key in raw).length === 1, 'raw-grammar');
  need(!('rqid' in raw) || isInt(raw.rqid), 'raw-grammar');
  need(!('noCancel' in raw) || (raw.noCancel === true && 'forceSwitch' in raw), 'raw-grammar');
  need(isObject(raw.side) && Array.isArray(raw.side.pokemon) && raw.side.pokemon.length >= 1, 'raw-grammar');
  need(raw.side.pokemon.length <= 6 && typeof raw.side.name === 'string', 'raw-grammar');
  need(Object.keys(raw.side).every(key => ['name', 'id', 'pokemon'].includes(key)), 'raw-grammar');
  need(raw.side.id === owner, 'wrong-owner');
  for (const pokemon of raw.side.pokemon) {
    need(isObject(pokemon) && typeof pokemon.ident === 'string' && typeof pokemon.condition === 'string' && typeof pokemon.active === 'boolean', 'raw-grammar');
    need(pokemon.ident.startsWith(owner + ': '), 'wrong-owner');
  }
  need(raw.side.pokemon.filter((p: Json) => p.active).length <= 1, 'doubles');
  need(raw.side.pokemon.filter((p: Json) => p.active).length === 1, 'raw-grammar');
  if ('wait' in raw) { need(raw.wait === true, 'raw-grammar'); return { kind: 'waiting', raw }; }
  if ('forceSwitch' in raw) {
    need(Array.isArray(raw.forceSwitch), 'raw-grammar');
    need(raw.forceSwitch.length <= 1, 'doubles');
    need(raw.forceSwitch.length === 1 && raw.forceSwitch[0] === true, 'raw-grammar');
    return { kind: raw.side.pokemon.some((p: Json) => p.reviving === true) ? 'revival_selection' : 'forced_switch', raw };
  }
  need(Array.isArray(raw.active), 'raw-grammar');
  need(raw.active.length <= 1, 'doubles');
  need(raw.active.length === 1 && isObject(raw.active[0]), 'raw-grammar');
  return { kind: 'actionable', raw };
}

function deriveActive(raw: Json): Json {
  const source = raw.active[0];
  onlyKeys(source, ['moves', 'maybeDisabled', 'maybeTrapped', 'trapped', 'canTerastallize'], 'raw-grammar');
  for (const key of ['maybeDisabled', 'maybeTrapped', 'trapped']) need(!(key in source) || source[key] === true, 'raw-grammar');
  need(!('canTerastallize' in source) || typeof source.canTerastallize === 'string', 'raw-grammar');
  need(Array.isArray(source.moves) && source.moves.length >= 1 && source.moves.length <= 4, 'raw-grammar');
  const rows = source.moves.map((row: Json, index: number) => {
    need(isObject(row), 'raw-grammar');
    onlyKeys(row, ['move', 'id', 'pp', 'maxpp', 'target', 'disabled'], 'raw-grammar');
    need(typeof row.move === 'string' && row.move !== '' && typeof row.id === 'string' && row.id !== '', 'raw-grammar');
    need(scalars(row.move) <= 256 && scalars(row.id) <= 256 && (!('target' in row) || (typeof row.target === 'string' && scalars(row.target) <= 256)), 'raw-grammar');
    need(!('pp' in row) || isInt(row.pp), 'raw-grammar');
    need(!('maxpp' in row) || isInt(row.maxpp), 'raw-grammar');
    need(!('target' in row) || typeof row.target === 'string', 'raw-grammar');
    need(!('disabled' in row) || typeof row.disabled === 'boolean', 'raw-grammar');
    return { slot: index + 1, id: row.id, name: row.move, pp: 'pp' in row ? row.pp : null, max_pp: 'maxpp' in row ? row.maxpp : null,
      target: 'target' in row ? row.target : null, disabled: 'disabled' in row ? row.disabled : null };
  });
  const lockedShape = rows.length === 1 && rows[0].pp === null && rows[0].max_pp === null;
  const lock = !lockedShape ? 'no_hard_lock' : rows[0].id === 'recharge' ? 'recharge' : rows[0].id === 'struggle' ? 'struggle' : 'locked_move';
  const switchIn = raw.side.pokemon.some((p: Json) => !p.active && !fainted(p.condition));
  need(!(source.trapped === true && source.maybeTrapped === true), 'raw-grammar');
  // Pinned singles source rule (pokemon.js getMoveRequestData): trapped/maybeTrapped are only emitted while a switch-in exists.
  const trapped = source.trapped === true ? true : switchIn ? false : null;
  const maybeTrapped = source.maybeTrapped === true ? true : source.trapped === true ? false : switchIn ? false : null;
  return {
    lock, trapped, maybe_trapped: maybeTrapped, maybe_disabled: source.maybeDisabled === true, switch_in_available: switchIn,
    derivation: {
      lock: lockedShape ? 'bare_single_row' : 'pp_bearing_rows',
      trapped: source.trapped === true ? 'raw_true' : switchIn ? 'omitted_with_switch_in' : 'omitted_without_switch_in',
      maybe_trapped: source.maybeTrapped === true ? 'raw_true' : source.trapped === true ? 'superseded_by_trapped' : switchIn ? 'omitted_with_switch_in' : 'omitted_without_switch_in',
      maybe_disabled: source.maybeDisabled === true ? 'raw_true' : 'omitted_singles_rule',
    },
    moves: rows,
  };
}

/** Join to the unchanged observation: every carried request fact must equal `value ?? legacy default`, and legality must follow the request. */
function joinObservation(owner: string, kind: string, raw: Json, active: Json, observation: Json): void {
  const request = observation.request;
  need(isObject(request) && request.player === owner && !request.team_preview, request && request.team_preview ? 'team-preview' : 'observation-mismatch');
  need(request.wait === (kind === 'waiting') && request.force_switch === (kind === 'forced_switch' || kind === 'revival_selection'), 'presence-mismatch');
  need((request.rqid ?? null) === (raw.rqid ?? null), 'observation-mismatch');
  need(raw.side.pokemon.length === request.side.length && raw.side.pokemon.every((p: Json, i: number) => request.side[i].ident === p.ident
    && request.side[i].condition === p.condition && request.side[i].active === p.active && (request.side[i].reviving === true) === (p.reviving === true)), 'observation-mismatch');
  const availability = observation.decision_availability;
  need(kind === 'waiting' || (availability.available && request.legal_actions.available_indices.length > 0), 'no-legal-actions');
  if (!active) { need(request.active === null, 'observation-mismatch'); return; }
  const seen = request.active;
  need(isObject(seen) && seen.moves.length === active.moves.length, 'observation-mismatch');
  active.moves.forEach((row: Json, i: number) => {
    const carried = seen.moves[i];
    need(carried.slot === row.slot && carried.id === row.id && carried.move === row.name && carried.pp === (row.pp ?? 0)
      && carried.maxpp === (row.max_pp ?? 0) && carried.target === (row.target ?? 'normal') && carried.disabled === (row.disabled ?? false), 'observation-mismatch');
  });
  need(seen.trapped === (active.trapped === true) && request.trapped === (active.trapped === true), 'observation-mismatch');
  need(seen.can_switch === (active.trapped !== true && active.switch_in_available), 'observation-mismatch');
  // A numbered move action must be a request-supplied, enabled row with PP (or the request-supplied Struggle row).
  for (const action of request.legal_actions.actions) {
    if (!action || (action.kind !== 'move' && action.kind !== 'move_tera') || action.slot === null) continue;
    const row = active.moves[action.slot - 1];
    need(row && row.disabled !== true && ((row.pp !== null && row.pp > 0) || (row.id === 'struggle' && row.pp === null)), 'legality-mismatch');
  }
}

export function buildRequestKnowledge(owner: string, rawText: string | null, observation: Json, provenance: string): RequestKnowledge {
  need(provenance === FRESH_DELIVERY, 'provenance');
  need(OWNERS.includes(owner) && isObject(observation) && observation.perspective === owner, 'wrong-owner');
  need(OBSERVATION_SCHEMAS.includes(observation.schema_version) && /^obs-[0-9a-f]{64}$/.test(observation.observation_id)
    && isInt(observation.event_cursor) && typeof observation.battle_id === 'string' && observation.battle_id !== '' && scalars(observation.battle_id) <= 256, 'observation-mismatch');
  let presence: string; let raw: Json = null; let active: Json = null;
  if (observation.view.terminated) { presence = 'terminal'; need(rawText === null && observation.request === null, 'presence-mismatch'); }
  else if (observation.request === null) { presence = 'requestless'; need(rawText === null, 'presence-mismatch'); }
  else {
    need(typeof rawText === 'string', 'presence-mismatch');
    const parsed = parseRaw(owner, rawText as string);
    presence = parsed.kind; raw = parsed.raw;
    active = presence === 'actionable' ? deriveActive(raw) : null;
    joinObservation(owner, presence, raw, active, observation);
  }
  const record = {
    schema_version: REQUEST_KNOWLEDGE_SCHEMA, id: '', battle_id: observation.battle_id, perspective: owner,
    observation_schema_version: observation.schema_version, observation_id: observation.observation_id, event_cursor: observation.event_cursor,
    presence, request_present: rawText !== null, raw_request: rawText, rqid: raw && 'rqid' in raw ? raw.rqid : null, active,
  };
  record.id = requestKnowledgeId(record);
  return record;
}
