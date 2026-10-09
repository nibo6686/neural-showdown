import { createHash } from 'node:crypto';
import type { ChoiceRequestView, LegalAction, PlayerID } from './types';

export const CANONICAL_ACTION_SCHEMA_VERSION = 'canonical-action/v1' as const;
export const CANONICAL_REVIVAL_SCHEMA_VERSION = 'canonical-revival/v1' as const;
export type CanonicalActionKind = 'move' | 'move_tera' | 'switch' | 'revive' | 'default';

export interface CanonicalAction {
  schema_version: typeof CANONICAL_ACTION_SCHEMA_VERSION | typeof CANONICAL_REVIVAL_SCHEMA_VERSION;
  action_id: string;
  /** Revival-only binding to the addressed roster evidence. */
  request_fingerprint?: string;
  source: 'request_legal_action';
  player: PlayerID;
  rqid: number | null;
  kind: CanonicalActionKind;
  index: number;
  move_slot: number | null;
  switch_slot: number | null;
  target: null;
  choice: string;
}

export interface CanonicalActionRequestContext {
  player: PlayerID;
  rqid: number | null;
  force_switch?: boolean;
  legal_actions: ChoiceRequestView['legal_actions'];
  side?: ChoiceRequestView['side'];
}

type ActionFields = Omit<CanonicalAction, 'action_id'>;

const CANONICAL_ACTION_KEYS = [
  'schema_version', 'action_id', 'source', 'player', 'rqid', 'kind', 'index',
  'move_slot', 'switch_slot', 'target', 'choice',
] as const;

function stableFields(fields: ActionFields): ActionFields {
  return {
    schema_version: fields.schema_version,
    source: fields.source,
    player: fields.player,
    rqid: fields.rqid,
    kind: fields.kind,
    index: fields.index,
    move_slot: fields.move_slot,
    switch_slot: fields.switch_slot,
    target: fields.target,
    choice: fields.choice,
    ...(fields.kind === 'revive' ? { request_fingerprint: fields.request_fingerprint } : {}),
  };
}

function stableJson(value: unknown): string {
  return JSON.stringify(value);
}

function actionId(fields: ActionFields): string {
  return `act-${createHash('sha256').update(stableJson(stableFields(fields)), 'utf8').digest('hex')}`;
}

function isPlayer(value: unknown): value is PlayerID {
  return value === 'p1' || value === 'p2';
}

function isSafeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function revivalRequestFingerprint(request: CanonicalActionRequestContext): string {
  if (!request.side) throw new Error('Revival requires addressed roster evidence.');
  return createHash('sha256').update(JSON.stringify(request.side.map(p =>
    [p.slot, p.ident, p.details, p.condition, p.active, p.reviving === true])), 'utf8').digest('hex');
}

function expectedLegalAction(request: CanonicalActionRequestContext, action: CanonicalAction): LegalAction {
  const legal = request.legal_actions.actions[action.index];
  if (!request.legal_actions.mask[action.index] || !legal) {
    throw new Error('Canonical action index is not legal for the current request.');
  }
  return legal;
}

function assertActionShape(action: CanonicalAction, request: CanonicalActionRequestContext, perspective: PlayerID): void {
  const actualKeys = Object.keys(action).sort();
  const expectedKeys = [...CANONICAL_ACTION_KEYS, ...(action.kind === 'revive' ? ['request_fingerprint'] : [])].sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    throw new Error('Canonical action fields are not exact.');
  }
  if (action.schema_version !== (action.kind === 'revive' ? CANONICAL_REVIVAL_SCHEMA_VERSION : CANONICAL_ACTION_SCHEMA_VERSION)) throw new Error('Unsupported canonical action schema.');
  if (!isPlayer(action.player) || action.player !== perspective || action.player !== request.player) {
    throw new Error('Canonical action player does not match perspective/request.');
  }
  if (action.rqid !== request.rqid || (action.rqid !== null && !isSafeInteger(action.rqid))) {
    throw new Error('Canonical action request ID does not match the current request.');
  }
  if (!isSafeInteger(action.index) || action.index < 0 || action.index >= 13) throw new Error('Canonical action index is invalid.');
  if (action.target !== null) throw new Error('Canonical target semantics are unsupported in v1.');
  const legal = expectedLegalAction(request, action);
  if (action.kind === 'revive' && action.request_fingerprint !== revivalRequestFingerprint(request)) throw new Error('Revival request fingerprint is stale.');
  if (action.kind === 'revive' && request.force_switch !== true) throw new Error('Revival requires a current force-switch request.');
  if (request.force_switch && action.kind !== 'switch' && action.kind !== 'revive' && !(action.kind === 'default' && legal.choice === 'default')) {
    throw new Error('Forced-switch requests accept switch actions or the legacy default fallback.');
  }
  if (action.kind === 'default') {
    if (action.index !== 0 || action.move_slot !== null || action.switch_slot !== null || action.choice !== 'default') {
      throw new Error('Canonical default action fields are inconsistent.');
    }
    if (legal.choice !== 'default') throw new Error('Canonical default action is not the current fallback.');
  } else if (action.kind === 'move' || action.kind === 'move_tera') {
    if (!isSafeInteger(action.move_slot) || action.move_slot < 1 || action.move_slot > 4 || action.switch_slot !== null) {
      throw new Error('Canonical move slot fields are invalid.');
    }
    const expectedIndex = action.kind === 'move' ? action.move_slot - 1 : action.move_slot + 3;
    const expectedChoice = action.kind === 'move' ? `move ${action.move_slot}` : `move ${action.move_slot} terastallize`;
    if (action.index !== expectedIndex || action.choice !== expectedChoice) throw new Error('Canonical move fields are inconsistent.');
  } else if (action.kind === 'switch' || action.kind === 'revive') {
    if (!isSafeInteger(action.switch_slot) || action.switch_slot < 1 || action.switch_slot > 6 || action.move_slot !== null) {
      throw new Error('Canonical switch slot fields are invalid.');
    }
    if (action.index < 8 || action.index > 12) throw new Error('Canonical switch index is invalid.');
    if (action.choice !== `switch ${action.switch_slot}`) throw new Error('Canonical switch fields are inconsistent.');
  } else {
    throw new Error('Unsupported canonical action kind.');
  }
  if (legal.choice !== action.choice || legal.kind !== (action.kind === 'default' ? 'move' : action.kind)) {
    throw new Error('Canonical action does not match the current legal action.');
  }
  if (action.kind !== 'default' && legal.slot !== (action.move_slot ?? action.switch_slot)) {
    throw new Error('Canonical action slot does not match the current legal action.');
  }
}

export function canonicalActionFromLegalAction(
  request: CanonicalActionRequestContext,
  actionIndex: number,
  perspective: PlayerID = request.player,
): CanonicalAction {
  if (!isPlayer(perspective)) throw new Error('Unsupported canonical action perspective.');
  if (!isSafeInteger(actionIndex) || actionIndex < 0 || actionIndex >= 13) throw new Error('Canonical action index is invalid.');
  const legal = request.legal_actions.actions[actionIndex];
  if (!request.legal_actions.mask[actionIndex] || !legal) throw new Error('Canonical action index is not legal for the current request.');
  const isDefault = legal.choice === 'default';
  const kind = isDefault ? 'default' : legal.kind as CanonicalActionKind;
  const fields: ActionFields = {
    schema_version: kind === 'revive' ? CANONICAL_REVIVAL_SCHEMA_VERSION : CANONICAL_ACTION_SCHEMA_VERSION,
    source: 'request_legal_action',
    player: request.player,
    rqid: request.rqid,
    kind,
    index: actionIndex,
    move_slot: kind === 'move' || kind === 'move_tera' ? legal.slot ?? null : null,
    switch_slot: kind === 'switch' || kind === 'revive' ? legal.slot ?? null : null,
    target: null,
    choice: legal.choice,
    ...(kind === 'revive' ? { request_fingerprint: revivalRequestFingerprint(request) } : {}),
  };
  const action = { ...stableFields(fields), action_id: actionId(fields) } as CanonicalAction;
  assertActionShape(action, request, perspective);
  return action;
}

export function serializeCanonicalAction(action: CanonicalAction, request: CanonicalActionRequestContext, perspective = request.player): string {
  assertActionShape(action, request, perspective);
  const fields = stableFields(action);
  const expectedId = actionId(fields);
  if (action.action_id !== expectedId) throw new Error('Canonical action ID is invalid.');
  return stableJson({
    schema_version: action.schema_version,
    action_id: action.action_id,
    source: action.source,
    player: action.player,
    rqid: action.rqid,
    kind: action.kind,
    index: action.index,
    move_slot: action.move_slot,
    switch_slot: action.switch_slot,
    target: action.target,
    choice: action.choice,
    ...(action.kind === 'revive' ? { request_fingerprint: action.request_fingerprint } : {}),
  });
}

export function deserializeCanonicalAction(serialized: string, request: CanonicalActionRequestContext, perspective = request.player): CanonicalAction {
  let parsed: unknown;
  try {
    parsed = JSON.parse(serialized);
  } catch {
    throw new Error('Canonical action serialization is not valid JSON.');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Canonical action must be a JSON object.');
  const action = parsed as CanonicalAction;
  const canonical = serializeCanonicalAction(action, request, perspective);
  if (canonical !== serialized) throw new Error('Canonical action serialization is not deterministic.');
  return action;
}

export function canonicalActionToChoice(action: CanonicalAction, request: CanonicalActionRequestContext, perspective = request.player): string {
  serializeCanonicalAction(action, request, perspective);
  return action.choice;
}
