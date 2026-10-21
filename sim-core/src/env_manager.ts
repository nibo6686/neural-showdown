import { OwnedRequestHealthHost } from './owned_request_health';
import { SimulationOnlyAuthorityError } from './simulation_authority';
import { SwitchEventHost } from './owner_identity_events';
import { randomBytes } from 'node:crypto';
import { snapshotRestorePolicy, assertBeliefForkPolicy } from './owner_identity_crosswalk';
import { installedNativeProfile, NATIVE_ENGINE_COMMIT, assertNativeRuntimeProfile, readerContext, HISTORICAL10_CONTEXT, type ReaderContext, type NativeRuntimeProfile } from './version_profile';
import { NativeBirthEnrollment, NativeObjectAssociation, type NativeRestoreTicket } from './owner_identity_crosswalk';
import { RequestEmissionTrace, type RequestTraceHandle, type RequestEmissionReceipt } from './request_emission_trace';
import { OriginalOwnerCreation, type OriginalOwnerEvidence } from './original_owner_provider';
import { isDeepStrictEqual } from 'node:util';
import { Battle, BattleStream, Dex, Teams, getPlayerStreams } from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import { cloneChoiceRequest, removeChoiceFromRequest, normalizeRequest } from './action_codec';
import { HeuristicBaselineAgent } from './baselines/heuristic';
import { createSeededRandom, RandomBaselineAgent } from './baselines/random';
import { buildBeliefSnapshot, type BeliefForkMetadata } from './belief_fork';
import { canonicalActionToChoice, type CanonicalAction } from './canonical_action';
import {
  buildSeededTransitionResult,
  buildSeededForcedSwitchResult,
  validateSeededForcedSwitchRequest,
  assertOrdinaryForcedSwitch,
  assertRevivalSelection,
  SEEDED_REVIVAL_SCHEMA_VERSION,
  type SeededForcedSwitchRequest,
  type SeededForcedSwitchResult,
  createSeededBattleSnapshot,
  fingerprintSimulatorState,
  toSeededSnapshotRef,
  toSeededTransitionPublicResult,
  validateSeededTransitionRequest,
  type SeededBattleSnapshot,
  type SeededSnapshotRef,
  type SeededTransitionRequest,
  type SeededTransitionPublicResult,
  type SeededTransitionWireRequest,
  type SeededTransitionResult,
} from './transition';
import { PlayerStateExtractor, isOwnerPrivateHealingWishHeal } from './state_extractor';
import { validateRawProtocolRecord } from './observable_state';
import type {
  BaselineDecision,
  BattleView,
  ChoiceRequestView,
  ControllerSpec,
  ControllerType,
  PlayerID,
  StepResult,
  StepResultOptions,
  Winner,
} from './types';
import { PLAYERS } from './types';
import { SettlingBarrier, SettlingError, type SettlingOptions } from './settling';

type PlayerStream = {
  write(data: string): Promise<void> | void;
  writeEnd?: () => Promise<void> | void;
  [Symbol.asyncIterator](): AsyncIterator<string>;
};

const TERMINAL_REQUEST_HISTORY_KEY = '__neural_terminal_request_history';
const TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION = 'terminal-request-history/v1' as const;
const TERMINAL_SWITCH_HISTORY_SCHEMA_VERSION = 'terminal-request-history/v2' as const;
const ACTIVE_REQUEST_OVERRIDES_KEY = '__neural_active_request_overrides';
const ACTIVE_REQUEST_OVERRIDES_SCHEMA_VERSION = 'active-request-overrides/v1' as const;
const PRIVATE_SPECTATOR_COMMANDS = new Set(['request', 'error', 'split', 'debug', 'showteam']);

/** The spectator channel is the sole source of public-prefix evidence. */
export function validatePublicSpectatorRecord(record: string, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): void {
  readerContext(rulesContext);
  if (!record.startsWith('|')) throw new Error('Spectator output contained a non-protocol record.');
  const command = record.slice(1).split('|', 1)[0];
  if (PRIVATE_SPECTATOR_COMMANDS.has(command)) {
    throw new Error(`Private ${command} record entered the spectator channel.`);
  }
  if (command === 'bigerror') validateRawProtocolRecord(record, rulesContext);
}

/** Validate each spectator transport record before it becomes public-log evidence. */
export function appendPublicSpectatorChunk(chunk: string, logLines: string[], rulesContext: ReaderContext = HISTORICAL10_CONTEXT): void {
  readerContext(rulesContext);
  const acceptedLines: string[] = [];
  for (const rawLine of chunk.split('\n')) {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
    if (!line) continue;
    validatePublicSpectatorRecord(line, rulesContext);
    acceptedLines.push(line);
  }
  logLines.push(...acceptedLines);
}

type TerminalRequestPokemon = {
  ident: string;
  details: string;
  condition: string;
  active: boolean;
  moves: string[];
  stats: Record<string, number>;
  baseAbility: string;
  item: string;
  ability: string;
  teraType: string;
  terastallized: boolean;
};

type TerminalHistoryRequest = {
  side: {
    id: PlayerID;
    pokemon: TerminalRequestPokemon[];
  };
};

type TerminalRequestHistory = {
  schema_version: typeof TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION | typeof TERMINAL_SWITCH_HISTORY_SCHEMA_VERSION;
  requests: Partial<Record<PlayerID, TerminalHistoryRequest>>;
  submitted_switches?: Partial<Record<PlayerID, {action: CanonicalAction; cursor: number; force_switch: boolean}>>;
};

/** A safe, public-value-free error for optional private restoration metadata. */
export class TerminalRequestHistoryValidationError extends Error {
  readonly code: 'terminal-request-history/invalid' | 'terminal-request-history/unsupported-schema';
  readonly path: string;
  readonly reason: string;

  constructor(
    code: TerminalRequestHistoryValidationError['code'],
    path: string,
    reason: string,
  ) {
    super(`${code === 'terminal-request-history/unsupported-schema' ? 'Unsupported terminal request history schema' : 'Invalid terminal request history'} at ${path}: ${reason}.`);
    this.name = 'TerminalRequestHistoryValidationError';
    this.code = code;
    this.path = path;
    this.reason = reason;
  }
}

function terminalHistoryInvalid(path: string, reason: string): never {
  throw new TerminalRequestHistoryValidationError('terminal-request-history/invalid', path, reason);
}

function terminalHistoryUnsupported(path: string, reason: string): never {
  throw new TerminalRequestHistoryValidationError('terminal-request-history/unsupported-schema', path, reason);
}

function recordAt(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    terminalHistoryInvalid(path, 'must be an object');
  }
  return value as Record<string, unknown>;
}

function stringAt(value: unknown, path: string, allowEmpty = false): string {
  if (typeof value !== 'string' || (!allowEmpty && value.trim() === '')) {
    terminalHistoryInvalid(path, allowEmpty ? 'must be a string' : 'must be a non-empty string');
  }
  return value;
}

function booleanAt(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') terminalHistoryInvalid(path, 'must be a boolean');
  return value;
}

function denseArrayAt(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) terminalHistoryInvalid(path, 'must be an array');
  for (let index = 0; index < value.length; index++) {
    if (!(index in value)) terminalHistoryInvalid(`${path}[${index}]`, 'must not contain a sparse entry');
  }
  return value;
}

function validateCondition(condition: string, path: string): void {
  if (!condition) return;
  const pieces = condition.trim().split(/\s+/);
  const hp = pieces[0];
  const fainted = pieces.includes('fnt');
  if (fainted) {
    if (pieces.length !== 2 || hp !== '0' || pieces[1] !== 'fnt') {
      terminalHistoryInvalid(path, 'must use the canonical fainted condition');
    }
    return;
  }
  if (pieces.length > 2 || (pieces[1] !== undefined && !['brn', 'par', 'slp', 'psn', 'tox', 'frz'].includes(pieces[1]))) {
    terminalHistoryInvalid(path, 'has an invalid status token');
  }
  const ratio = /^(\d+)(?:\/(\d+))?$/.exec(hp);
  if (!ratio) terminalHistoryInvalid(path, 'has an invalid HP value');
  const numerator = Number(ratio[1]);
  const denominator = ratio[2] === undefined ? null : Number(ratio[2]);
  if (!Number.isSafeInteger(numerator) || numerator < 0
    || (denominator !== null && (!Number.isSafeInteger(denominator) || denominator <= 0 || numerator > denominator))) {
    terminalHistoryInvalid(path, 'has an invalid HP ratio');
  }
}

function validateDetails(details: string, path: string): void {
  const parts = details.split(',').map((part) => part.trim());
  if (!parts[0]) {
    terminalHistoryInvalid(path, 'must begin with a species name');
  }
  for (const part of parts.slice(1)) {
    if (!part || part === 'M' || part === 'F' || part === 'shiny') continue;
    const level = /^L(\d+)$/.exec(part);
    if (level && Number(level[1]) >= 1 && Number(level[1]) <= 100) continue;
    const tera = /^tera:(.+)$/.exec(part);
    if (tera && Dex.types.get(tera[1]).exists) continue;
    terminalHistoryInvalid(path, 'has an invalid details token');
  }
}

function validateIdentifier(value: string, path: string, allowEmpty: boolean): void {
  if (value === '' && allowEmpty) return;
  if (!/^[a-z0-9]+$/i.test(value)) terminalHistoryInvalid(path, 'must be an identifier string');
}

function canonicalizeTerastallized(value: unknown, teraType: string, path: string): boolean {
  if (typeof value === 'boolean') return value;
  // Historical v1 serializer copied Showdown's string-valued field. Accept
  // only its two encodings while canonicalizing all future output to boolean.
  if (typeof value === 'string' && (value === '' || value === teraType)) return value !== '';
  terminalHistoryInvalid(path, 'must be a boolean or a legacy Tera-type marker');
}

function canonicalizeTerminalPokemon(value: unknown, player: PlayerID, path: string): TerminalRequestPokemon {
  const pokemon = recordAt(value, path);
  const ident = stringAt(pokemon.ident, `${path}.ident`);
  const addressed = /^(p1|p2):\s+(\S(?:.*\S)?)$/.exec(ident);
  if (!addressed || addressed[1] !== player) {
    terminalHistoryInvalid(`${path}.ident`, 'must address its owner');
  }
  const details = stringAt(pokemon.details, `${path}.details`);
  validateDetails(details, `${path}.details`);
  const condition = stringAt(pokemon.condition, `${path}.condition`);
  validateCondition(condition, `${path}.condition`);
  const active = booleanAt(pokemon.active, `${path}.active`);
  const rawMoves = denseArrayAt(pokemon.moves, `${path}.moves`);
  const moves = rawMoves.map((move, index) => {
    const id = stringAt(move, `${path}.moves[${index}]`);
    validateIdentifier(id, `${path}.moves[${index}]`, false);
    return id;
  });
  const rawStats = recordAt(pokemon.stats, `${path}.stats`);
  const stats: Record<string, number> = {};
  const statKeys = ['atk', 'def', 'spa', 'spd', 'spe'];
  if (Object.keys(rawStats).length !== statKeys.length || statKeys.some((stat) => !(stat in rawStats))) {
    terminalHistoryInvalid(`${path}.stats`, 'must contain exactly atk, def, spa, spd, and spe');
  }
  for (const [stat, amount] of Object.entries(rawStats)) {
    if (!statKeys.includes(stat) || typeof amount !== 'number' || !Number.isFinite(amount)
      || !Number.isSafeInteger(amount) || amount < 0) {
      terminalHistoryInvalid(`${path}.stats.<key>`, 'must be a non-negative finite integer');
    }
    stats[stat] = amount;
  }
  const baseAbility = stringAt(pokemon.baseAbility, `${path}.baseAbility`, true);
  const item = stringAt(pokemon.item, `${path}.item`, true);
  const ability = stringAt(pokemon.ability, `${path}.ability`, true);
  const teraType = stringAt(pokemon.teraType, `${path}.teraType`, true);
  validateIdentifier(baseAbility, `${path}.baseAbility`, true);
  validateIdentifier(item, `${path}.item`, true);
  validateIdentifier(ability, `${path}.ability`, true);
  if (teraType && !Dex.types.get(teraType).exists) {
    terminalHistoryInvalid(`${path}.teraType`, 'must be a known type');
  }
  const terastallized = canonicalizeTerastallized(pokemon.terastallized, teraType, `${path}.terastallized`);
  if (terastallized && !teraType) {
    terminalHistoryInvalid(`${path}.teraType`, 'is required when terastallized');
  }
  return { ident, details, condition, active, moves, stats, baseAbility, item, ability, teraType, terastallized };
}

function canonicalizeTerminalRequest(value: unknown, player: PlayerID, path: string): TerminalHistoryRequest {
  const request = recordAt(value, path);
  const side = recordAt(request.side, `${path}.side`);
  if (side.id !== player || !Array.isArray(side.pokemon)) {
    terminalHistoryInvalid(`${path}.side`, 'does not match its addressed side');
  }
  const roster = denseArrayAt(side.pokemon, `${path}.side.pokemon`);
  if (roster.length === 0 || roster.length > 6) {
    terminalHistoryInvalid(`${path}.side.pokemon`, 'must contain one to six roster entries');
  }
  const pokemon = roster.map((entry, index) => canonicalizeTerminalPokemon(entry, player, `${path}.side.pokemon[${index}]`));
  const identities = new Set<string>();
  let activeCount = 0;
  for (const member of pokemon) {
    if (identities.has(member.ident)) terminalHistoryInvalid(`${path}.side.pokemon`, 'must not repeat an identity');
    identities.add(member.ident);
    if (member.active) activeCount++;
  }
  if (activeCount > 1) terminalHistoryInvalid(`${path}.side.pokemon`, 'must have at most one active member');
  return { side: { id: player, pokemon } };
}

function readTerminalRequestHistory(serialized: Record<string, unknown>, rulesContext: ReaderContext): TerminalRequestHistory | null {
  readerContext(rulesContext);
  const raw = serialized[TERMINAL_REQUEST_HISTORY_KEY];
  if (raw === undefined) return null;
  const history = recordAt(raw, TERMINAL_REQUEST_HISTORY_KEY);
  if (history.schema_version !== TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION && history.schema_version !== TERMINAL_SWITCH_HISTORY_SCHEMA_VERSION) {
    terminalHistoryUnsupported(`${TERMINAL_REQUEST_HISTORY_KEY}.schema_version`, 'schema is not supported');
  }
  const requests = recordAt(history.requests, `${TERMINAL_REQUEST_HISTORY_KEY}.requests`);
  if (Object.keys(requests).length === 0) {
    terminalHistoryInvalid(`${TERMINAL_REQUEST_HISTORY_KEY}.requests`, 'must contain at least one addressed request');
  }
  const canonicalRequests: Partial<Record<PlayerID, TerminalHistoryRequest>> = {};
  for (const [player, request] of Object.entries(requests)) {
    if (player !== 'p1' && player !== 'p2') {
      terminalHistoryInvalid(`${TERMINAL_REQUEST_HISTORY_KEY}.requests.<key>`, 'has an unknown player');
    }
    canonicalRequests[player] = canonicalizeTerminalRequest(request, player, `${TERMINAL_REQUEST_HISTORY_KEY}.requests.${player}`);
  }
  if ((history.schema_version === TERMINAL_SWITCH_HISTORY_SCHEMA_VERSION) !== (history.submitted_switches !== undefined)) terminalHistoryInvalid(TERMINAL_REQUEST_HISTORY_KEY, 'switch provenance requires the v2 private history schema');
  const switches: NonNullable<TerminalRequestHistory['submitted_switches']> = {};
  if (history.submitted_switches !== undefined) {
    const supplied = recordAt(history.submitted_switches, `${TERMINAL_REQUEST_HISTORY_KEY}.submitted_switches`);
    for (const [key, rawSwitch] of Object.entries(supplied)) {
      if (key !== 'p1' && key !== 'p2') terminalHistoryInvalid(`${TERMINAL_REQUEST_HISTORY_KEY}.submitted_switches`, 'must address an owned player');
      const player = key as PlayerID, path = `${TERMINAL_REQUEST_HISTORY_KEY}.submitted_switches.${player}`;
      const value = recordAt(rawSwitch, path), request = canonicalRequests[player];
      if (!request || Object.keys(value).sort().join('|') !== 'action|cursor|force_switch' || !Number.isSafeInteger(value.cursor) || (value.cursor as number) < 0
        || typeof value.force_switch !== 'boolean' || value.force_switch !== request.side.pokemon.some((row) => row.active && row.condition === '0 fnt')) terminalHistoryInvalid(path, 'must contain a historical owned action and prefix cursor');
      const action = recordAt(value.action, `${path}.action`) as unknown as CanonicalAction;
      if (action.kind !== 'switch') terminalHistoryInvalid(`${path}.action`, 'must be a submitted switch');
      try {canonicalActionToChoice(action, normalizeRequest(player, {...request, rqid: action.rqid, active: [{moves: []}], forceSwitch: value.force_switch ? [true] : undefined}, rulesContext));}
      catch {terminalHistoryInvalid(`${path}.action`, 'must match the historical owned switch choices');}
      const owner = request.side.pokemon[action.switch_slot! - 1];
      const side = (serialized.sides as any[])?.find((entry) => entry.id === player);
      let sourceActive: any;
      let restoredSource: Battle | undefined;
      try {
        const source = structuredClone(serialized); delete source[TERMINAL_REQUEST_HISTORY_KEY];
        restoredSource = Battle.fromJSON(source as any);
        const activePokemon = restoredSource.sides.find((entry) => entry.id === player)?.active[0];
        sourceActive = activePokemon && {fullname: activePokemon.fullname, set: structuredClone(activePokemon.set)};
      } catch {terminalHistoryInvalid(path, 'does not contain a restorable source terminal active identity');}
      finally {restoredSource?.destroy();}
      const active = sourceActive && [sourceActive];
      const name = owner?.ident.slice(4);
      if (!owner || active?.length !== 1 || active[0].fullname !== owner.ident || String(active[0].set?.name || Dex.species.get(active[0].set?.species || '').name) !== name
        || Dex.species.get(owner.details.split(',')[0]).id !== Dex.species.get(active[0].set?.species || '').id) terminalHistoryInvalid(path, 'does not join the source terminal owned base identity');
      const channel = player === 'p1' ? 1 : 2;
      const prefix = extractChannelMessages((serialized.log as string[]).join('\n'), [channel])[channel]
        .filter((line) => line.startsWith('|') && !line.startsWith('|request|') && !isOwnerPrivateHealingWishHeal(line, player, rulesContext));
      const cursor = value.cursor as number;
      const ownSwitches = prefix.flatMap((line, index) => line.startsWith(`|switch|${player}a: `) ? [index] : []);
      const switchIndex = ownSwitches.at(-1);
      let turnIndex = -1;
      for (const [index, line] of prefix.entries()) if (line.startsWith('|turn|')) turnIndex = index;
      // A joint choice follows the last turn boundary; a forced replacement
      // starts with Battle.go's blank/timestamp frame before its sole switch.
      if (switchIndex === undefined || cursor !== (value.force_switch ? switchIndex - 2 : turnIndex + 1)
        || value.force_switch && (prefix[cursor] !== '|' || !prefix[cursor + 1]?.startsWith('|t:|'))
        || prefix.slice(cursor).filter((line) => line.startsWith(`|switch|${player}a: `) || line.startsWith(`|drag|${player}a: `)).length !== 1) terminalHistoryInvalid(`${path}.cursor`, 'does not identify the exact source choice boundary');
      switches[player] = {action: structuredClone(action), cursor: value.cursor as number, force_switch: value.force_switch};
    }
  }
  return {
    schema_version: history.schema_version,
    requests: canonicalRequests,
    ...(Object.keys(switches).length ? {submitted_switches: switches} : {}),
  };
}

/** A safe, public-value-free error for the optional live-request restoration key. */
export class ActiveRequestOverrideValidationError extends Error {
  readonly code = 'active-request-override/invalid' as const;
  readonly path: string;
  readonly reason: string;

  constructor(path: string, reason: string) {
    super(`Invalid active request override at ${path}: ${reason}.`);
    this.name = 'ActiveRequestOverrideValidationError';
    this.path = path;
    this.reason = reason;
  }
}

/** Observability for the byte-preserving fallback in serializeBattle; inert unless read or hooked. */
export const activeRequestOverrideDiagnostics: {
  dropped: number;
  onDrop: ((info: {player: PlayerID; path: string; reason: string}) => void) | null;
} = {dropped: 0, onDrop: null};

function overrideInvalid(path: string, reason: string): never {
  throw new ActiveRequestOverrideValidationError(path, reason);
}

function overrideRecord(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) overrideInvalid(path, 'must be an object');
  return value as Record<string, unknown>;
}

const has = (record: Record<string, unknown>, key: string) => Object.prototype.hasOwnProperty.call(record, key);

function readActiveRequestOverrides(serialized: Record<string, unknown>): Partial<Record<PlayerID, Record<string, unknown>>> | null {
  if (serialized[ACTIVE_REQUEST_OVERRIDES_KEY] === undefined) return null;
  const wrapper = overrideRecord(serialized[ACTIVE_REQUEST_OVERRIDES_KEY], ACTIVE_REQUEST_OVERRIDES_KEY);
  if (Object.keys(wrapper).sort().join() !== 'requests,schema_version' || wrapper.schema_version !== ACTIVE_REQUEST_OVERRIDES_SCHEMA_VERSION) {
    overrideInvalid(ACTIVE_REQUEST_OVERRIDES_KEY, 'must be exactly the supported schema_version and requests');
  }
  const requests = overrideRecord(wrapper.requests, `${ACTIVE_REQUEST_OVERRIDES_KEY}.requests`);
  if (!Object.keys(requests).length) overrideInvalid(`${ACTIVE_REQUEST_OVERRIDES_KEY}.requests`, 'must contain at least one request');
  const out: Partial<Record<PlayerID, Record<string, unknown>>> = {};
  for (const [key, value] of Object.entries(requests)) {
    if (key !== 'p1' && key !== 'p2') overrideInvalid(`${ACTIVE_REQUEST_OVERRIDES_KEY}.requests`, 'must address an owned player');
    const request = overrideRecord(value, `${ACTIVE_REQUEST_OVERRIDES_KEY}.requests.${key}`);
    if (overrideRecord(request.side, `${ACTIVE_REQUEST_OVERRIDES_KEY}.requests.${key}.side`).id !== key) {
      overrideInvalid(`${ACTIVE_REQUEST_OVERRIDES_KEY}.requests.${key}.side.id`, 'must name the addressed player');
    }
    out[key] = request;
  }
  return out;
}

/**
 * Accepts only the edits Showdown's rejected-choice paths make in place to a
 * live request (side.js updateRequestForPokemon): maybeTrapped removed with
 * trapped:true added, and a move row gaining disabled:true with a string
 * disabledSource. Anything else, and a no-op, is rejected: the result becomes
 * side.activeRequest, which the engine's choose paths treat as authority.
 */
function validateActiveRequestOverride(live: Record<string, unknown>, regeneratedSide: Battle['sides'][number] | undefined, path: string, runtime: NativeRuntimeProfile): void {
  assertNativeRuntimeProfile(runtime);
  const base = regeneratedSide?.activeRequest;
  if (!base || typeof base !== 'object') overrideInvalid(path, 'has no regenerated request to edit');
  const regenerated = base as unknown as Record<string, unknown>;
  const nativeMarker = runtime.engine_commit === NATIVE_ENGINE_COMMIT && has(live, 'update') && !has(regenerated, 'update');
  if (nativeMarker && live.update !== true) overrideInvalid(`${path}.update`, 'must be the literal native update:true marker');
  const liveKeys = Object.keys(live).filter(key => !nativeMarker || key !== 'update');
  if (liveKeys.sort().join() !== Object.keys(regenerated).sort().join()) overrideInvalid(path, 'has keys that differ from the regenerated request');
  for (const key of Object.keys(live)) {
    if (key !== 'active' && !(nativeMarker && key === 'update') && !isDeepStrictEqual(live[key], regenerated[key])) overrideInvalid(`${path}.${key}`, 'is not an engine-legal edit');
  }
  if (!Array.isArray(live.active) || !Array.isArray(regenerated.active) || live.active.length !== regenerated.active.length) {
    overrideInvalid(`${path}.active`, 'must edit the regenerated active entries');
  }
  let edits = 0;
  for (const [index, entry] of (live.active as unknown[]).entries()) {
    const at = `${path}.active.${index}`;
    const edited = overrideRecord(entry, at);
    const original = overrideRecord((regenerated.active as unknown[])[index], at);
    const fixed = (key: string) => key !== 'moves' && key !== 'maybeTrapped' && key !== 'trapped';
    const keys = new Set([...Object.keys(edited), ...Object.keys(original)].filter(fixed));
    for (const key of keys) if (has(edited, key) !== has(original, key) || !isDeepStrictEqual(edited[key], original[key])) overrideInvalid(`${at}.${key}`, 'is not an engine-legal edit');
    const sameTrap = ['maybeTrapped', 'trapped'].every((key) => has(edited, key) === has(original, key) && isDeepStrictEqual(edited[key], original[key]));
    if (!sameTrap) {
      if (original.maybeTrapped !== true || has(original, 'trapped') || has(edited, 'maybeTrapped') || edited.trapped !== true) {
        overrideInvalid(at, 'trapped may only replace maybeTrapped');
      }
      // The edit is only reachable when the engine's own state says the Pokemon is trapped.
      if (!regeneratedSide?.active[index]?.trapped) overrideInvalid(at, 'trapped edit on a Pokemon that is not trapped in the regenerated battle');
      edits++;
    }
    if (!Array.isArray(edited.moves) || !Array.isArray(original.moves) || edited.moves.length !== original.moves.length) overrideInvalid(`${at}.moves`, 'must edit the regenerated moves');
    for (const [slot, row] of edited.moves.entries()) {
      const rowPath = `${at}.moves.${slot}`;
      const before = overrideRecord(original.moves[slot], rowPath), after = overrideRecord(row, rowPath);
      if (isDeepStrictEqual(before, after)) continue;
      const fixedRow = (key: string) => key !== 'disabled' && key !== 'disabledSource';
      const rowKeys = new Set([...Object.keys(before), ...Object.keys(after)].filter(fixedRow));
      for (const key of rowKeys) if (has(after, key) !== has(before, key) || !isDeepStrictEqual(after[key], before[key])) overrideInvalid(`${rowPath}.${key}`, 'is not an engine-legal edit');
      if (before.disabled === true || has(before, 'disabledSource') || after.disabled !== true || typeof after.disabledSource !== 'string') {
        overrideInvalid(rowPath, 'may only gain disabled:true with a string disabledSource');
      }
      // Likewise a disabled edit needs the move to be genuinely disabled in the regenerated battle.
      const pokemon = regeneratedSide?.active[index];
      const hidden = pokemon?.getMoves(pokemon.getLockedMove(), false).find((move) => move.id === before.id);
      if (!hidden?.disabled) overrideInvalid(rowPath, 'disabled edit on a move that is not disabled in the regenerated battle');
      edits++;
    }
  }
  if (!edits) overrideInvalid(path, 'does not edit the regenerated request');
}

function normalizeStepResultOptions(options?: StepResultOptions): Required<StepResultOptions> {
  return {
    view_players: options?.view_players?.length ? [...options.view_players] : [...PLAYERS],
    include_log_delta: options?.include_log_delta !== false,
    include_possible_roles: options?.include_possible_roles !== false,
    include_wait_requests: options?.include_wait_requests === true,
  };
}

interface ManagedPlayerDeps {
  rulesContext: ReaderContext;
  receiveRequestRecord: (record: string) => void;
  env: LocalBattleEnv;
  player: PlayerID;
  stream: PlayerStream;
  controller: ControllerType;
  tracker: PlayerStateExtractor;
  randomAgent: RandomBaselineAgent;
  heuristicAgent: HeuristicBaselineAgent;
  settling: SettlingBarrier;
}

class ManagedPlayer {
  readonly player: PlayerID;
  readonly tracker: PlayerStateExtractor;

  private readonly receiveRequestRecord: (record: string) => void;
  private readonly env: LocalBattleEnv;
  private readonly stream: PlayerStream;
  private readonly controller: ControllerType;
  private readonly randomAgent: RandomBaselineAgent;
  private readonly heuristicAgent: HeuristicBaselineAgent;
  private readonly settling: SettlingBarrier;
  private currentRequest: ChoiceRequestView | null;
  private waitingRequest: ChoiceRequestView | null = null;
  private restoredRequestConsumed = false;
  private pendingChoice: string | null;
  private lastChoiceError: { choice: string | null; message: string } | null;
  private invalidChoices: Set<string>;

  constructor(deps: ManagedPlayerDeps) {
    if (readerContext(deps.rulesContext) !== deps.env.getReaderContext() || deps.tracker.getReaderContext() !== deps.rulesContext) throw new Error('reader-profile/v1/producer-context-mismatch');
    this.receiveRequestRecord = deps.receiveRequestRecord;
    this.env = deps.env;
    this.player = deps.player;
    this.stream = deps.stream;
    this.controller = deps.controller;
    this.tracker = deps.tracker;
    this.randomAgent = deps.randomAgent;
    this.heuristicAgent = deps.heuristicAgent;
    this.settling = deps.settling;
    this.currentRequest = null;
    this.pendingChoice = null;
    this.lastChoiceError = null;
    this.invalidChoices = new Set();
  }

  async start(): Promise<void> {
    for await (const chunk of this.stream) {
      if (this.settling.stopped) return;
      for (const record of chunk.split('\n')) {
        if (record.trimStart().startsWith('|request|')) this.receiveRequestRecord(record);
      }
      this.tracker.consumeChunk(chunk);
      for (const rawLine of chunk.split('\n')) {
        const line = rawLine.trim();
        if (!line.startsWith('|')) {
          continue;
        }
        if (line.startsWith('|request|')) {
          this.handleRequest();
        } else if (line.startsWith('|error|')) {
          this.handleError(line.slice('|error|'.length));
        }
      }
      this.settling.acknowledge(this.player);
    }
    this.settling.streamClosed(this.player);
  }

  getView(): BattleView {
    return this.tracker.getView();
  }

  getRequest(): ChoiceRequestView | null {
    return this.currentRequest ? cloneChoiceRequest(this.currentRequest) : null;
  }

  getReportedRequest(): ChoiceRequestView | null {
    if (this.tracker.getView().terminated) return null;
    const request = this.currentRequest ?? this.waitingRequest;
    return request ? cloneChoiceRequest(request) : null;
  }

  getOwnRequestData(): unknown | null {
    return this.tracker.getOwnRequestData();
  }

  restoreTerminalRequestData(rawRequest: unknown): void {
    this.tracker.restoreOwnRequestData(rawRequest);
  }

  markRestoredRequestConsumed(): void {
    this.restoredRequestConsumed = true;
  }

  diagnostics(): Record<string, unknown> {
    const request = this.getRequest();
    return {
      player: this.player,
      controller: this.controller,
      has_current_request: !!request,
      pending_choice: this.pendingChoice,
      last_choice_error: this.lastChoiceError,
      invalid_choices: [...this.invalidChoices],
      request: request
        ? {
            wait: request.wait,
            team_preview: request.team_preview,
            force_switch: request.force_switch,
            rqid: request.rqid,
            legal_action_count: request.legal_actions.available_indices.length,
            legal_choices: request.legal_actions.actions
              .filter((action) => !!action)
              .map((action) => action?.choice),
          }
        : null,
    };
  }

  submitExternalChoice(choice: string): void {
    if (this.controller !== 'external') {
      throw new Error(`Player ${this.player} is not externally controlled.`);
    }
    if (!this.currentRequest) {
      throw new Error(`Player ${this.player} does not have a pending request.`);
    }
    this.currentRequest = null;
    this.waitingRequest = null;
    this.pendingChoice = choice;
    this.env.noteLiveWrite();
    void this.stream.write(choice);
  }

  submitCanonicalAction(action: CanonicalAction): void {
    if (!this.currentRequest) {
      throw new Error(`Player ${this.player} does not have a pending request.`);
    }
    const request = this.currentRequest;
    const choice = canonicalActionToChoice(action, {
      player: this.player,
      rqid: request.rqid,
      force_switch: request.force_switch,
      legal_actions: request.legal_actions, side: request.side,
    });
    this.tracker.recordSubmittedSwitch(action.kind === 'switch' ? action : null, request.force_switch);
    this.submitExternalChoice(choice);
  }

  suggest(agent: ControllerType, requestOverride?: ChoiceRequestView): BaselineDecision {
    const request = requestOverride || this.tracker.getRequest();
    if (!request) {
      throw new Error(`Player ${this.player} does not have a pending actionable request.`);
    }
    const context = {
      player: this.player,
      request,
      view: this.tracker.getView(),
    };
    return agent === 'heuristic'
      ? this.heuristicAgent.choose(context)
      : this.randomAgent.choose(context);
  }

  private handleRequest(): void {
    const request = this.tracker.getRequest();
    this.waitingRequest = null;
    // Replay private request data into the tracker, but do not re-offer a
    // choice which the restored simulator has already accepted.
    if (this.restoredRequestConsumed) {
      this.restoredRequestConsumed = false;
      this.currentRequest = null;
      return;
    }
    if (!request) {
      this.currentRequest = null;
      this.invalidChoices.clear();
      return;
    }

    if (request.wait) {
      this.currentRequest = null;
      this.waitingRequest = request;
      this.pendingChoice = null;
      this.invalidChoices.clear();
      return;
    }

    if (request.team_preview) {
      this.currentRequest = null;
      this.pendingChoice = 'default';
      this.invalidChoices.clear();
      this.env.noteLiveWrite();
    void this.stream.write('default');
      return;
    }

    this.invalidChoices.clear();
    if (this.controller === 'external') {
      this.currentRequest = request;
      this.pendingChoice = null;
      return;
    }

    const decision = this.suggest(this.controller);
    this.currentRequest = null;
    this.pendingChoice = decision.choice;
    this.env.noteLiveWrite();
    void this.stream.write(decision.choice);
  }

  private handleError(message: string): void {
    if (
      message.startsWith('[Invalid choice]') ||
      message.startsWith('[Unavailable choice]')
    ) {
      const choice = this.pendingChoice;
      this.pendingChoice = null;
      this.lastChoiceError = { choice, message };
      if (choice) {
        this.invalidChoices.add(choice);
      }
      const request = this.tracker.getRequest();
      const filteredRequest = request ? this.filterInvalidChoices(request) : null;
      if (this.controller === 'external') {
        if (filteredRequest && !filteredRequest.wait && !filteredRequest.team_preview) {
          this.currentRequest = filteredRequest;
          return;
        }
      }
      if (filteredRequest && !filteredRequest.wait && !filteredRequest.team_preview) {
        const decision = this.suggest(this.controller, filteredRequest);
        this.currentRequest = null;
        this.pendingChoice = decision.choice;
        this.env.noteLiveWrite();
    void this.stream.write(decision.choice);
        return;
      }
      this.env.markError(new Error(`Player ${this.player}: ${message} after choice ${choice || 'unknown'}.`));
      return;
    }
    this.env.markError(new Error(`Player ${this.player}: ${message}`));
  }

  private filterInvalidChoices(request: ChoiceRequestView): ChoiceRequestView {
    let filtered = cloneChoiceRequest(request);
    for (const choice of this.invalidChoices) {
      filtered = removeChoiceFromRequest(filtered, choice);
    }
    return filtered;
  }
}

function createSeed(seed?: number[]): [number, number, number, number] {
  if (seed && seed.length === 4 && seed.every((value) => Number.isInteger(value))) {
    return [seed[0], seed[1], seed[2], seed[3]];
  }

  const next = () => Math.floor(Math.random() * 0x10000);
  return [next(), next(), next(), next()];
}

function offsetSeed(seed: [number, number, number, number], delta: number): [number, number, number, number] {
  return [
    (seed[0] + delta) & 0xffff,
    (seed[1] + delta * 2) & 0xffff,
    (seed[2] + delta * 3) & 0xffff,
    (seed[3] + delta * 4) & 0xffff,
  ];
}

const simulationEnvironments = new WeakSet<object>();

/** Process-local mode identity cannot be removed or supplied through constructor options. */
export function assertAuthoritativeEnvironment(environment: object): void {
  if (simulationEnvironments.has(environment)) throw new SimulationOnlyAuthorityError();
}

export interface SimulationOnlyOptions {
  id: string;
  format: string;
  seed?: number[];
  controllers?: Partial<Record<PlayerID, ControllerSpec>>;
  settling?: SettlingOptions;
}

export class LocalBattleEnv {
  static createSimulationOnly(options: SimulationOnlyOptions): LocalBattleEnv {
    const environment = new LocalBattleEnv(options.id, options.format, options.seed, options.controllers, options.settling);
    simulationEnvironments.add(environment);
    return environment;
  }
  #liveWorldOccurrence: object = Object.freeze(Object.create(null));
  getLiveWorldOccurrence(): object { assertAuthoritativeEnvironment(this); return this.#liveWorldOccurrence; }
  noteLiveWrite(): void { this.#liveWorldOccurrence = Object.freeze(Object.create(null)); }
  readonly #runtimeProfile: NativeRuntimeProfile;
  getReaderContext(): ReaderContext { return this.#runtimeProfile.reader; }
  readonly id: string;
  readonly format: string;
  readonly seed: [number, number, number, number];
  readonly controllers: Record<PlayerID, ControllerSpec>;

  #requestTrace: RequestEmissionTrace | null = null;
  readonly #originalCreation: OriginalOwnerCreation | undefined;
  readonly #nativeBirth: NativeBirthEnrollment | undefined;
  readonly #objectAssociation: NativeObjectAssociation | undefined;
  readonly #switchEvents: SwitchEventHost | undefined;
  readonly #requestHealth: OwnedRequestHealthHost | undefined;
  private readonly randomAgents: Record<PlayerID, RandomBaselineAgent>;
  private readonly heuristicAgent: HeuristicBaselineAgent;
  private battleStream: BattleStream | null;
  private streams: ReturnType<typeof getPlayerStreams> | null;
  private players: Record<PlayerID, ManagedPlayer> | null;
  private settling: SettlingBarrier;
  private consumerTasks: Promise<void>[] = [];
  private destruction: Promise<void> | null = null;
  private readonly settlingOptions: SettlingOptions;
  private logLines: string[];
  private logCursor: number;
  private lastError: Error | null;
  private initialized: boolean;

  constructor(
    id: string,
    format: string,
    seed?: number[],
    controllers?: Partial<Record<PlayerID, ControllerSpec>>,
    settlingOptions: SettlingOptions = {},
    originalCreation?: OriginalOwnerCreation,
    nativeBirth?: NativeBirthEnrollment,
    objectAssociation?: NativeObjectAssociation,
    runtimeProfile: NativeRuntimeProfile = installedNativeProfile(),
    switchEvents?: SwitchEventHost,
    requestHealth?: OwnedRequestHealthHost,
  ) {
    assertNativeRuntimeProfile(runtimeProfile);
    this.#runtimeProfile = runtimeProfile;
    this.#originalCreation = originalCreation;
    originalCreation?.bind(this);
    this.#nativeBirth = nativeBirth;
    nativeBirth?.bind(this);
    this.#objectAssociation = objectAssociation;
    this.#switchEvents = switchEvents; this.#requestHealth = requestHealth;
    if (nativeBirth) objectAssociation?.bindInitial(this);
    this.id = id;
    this.format = format;
    this.seed = createSeed(seed);
    this.controllers = {
      p1: controllers?.p1 || { controller: 'external' },
      p2: controllers?.p2 || { controller: 'external' },
    };
    this.randomAgents = {
      p1: this.createRandomAgent(this.controllers.p1),
      p2: this.createRandomAgent(this.controllers.p2),
    };
    this.heuristicAgent = new HeuristicBaselineAgent();
    this.battleStream = null;
    this.streams = null;
    this.players = null;
    this.settlingOptions = { ...settlingOptions };
    this.settling = new SettlingBarrier(this.settlingOptions);
    this.logLines = [];
    this.logCursor = 0;
    this.lastError = null;
    this.initialized = false;
  }

  async reset(): Promise<StepResult> {
    return this.resetWithOptions();
  }

  async resetWithOptions(options?: StepResultOptions): Promise<StepResult> {
    this.noteLiveWrite();
    this.#originalCreation?.begin(this);
    try {
      await this.destroyBattle();
      this.logLines = [];
      this.logCursor = 0;
      this.lastError = null;
      this.initialized = true;

      this.initializeStreams();
      if (!this.streams) throw new Error('Battle streams failed to initialize.');
      const prepare = (owner: PlayerID, offset: number): string => {
        const generated = Teams.generate(this.format, { seed: offsetSeed(this.seed, offset) });
        const packingCopy = this.#originalCreation?.capture(this, owner, generated) ?? generated;
        const packed = Teams.pack(packingCopy);
        this.#originalCreation?.associate(this, owner, packed);
        return packed;
      };
      const p1Team = prepare('p1', 11);
      const p2Team = prepare('p2', 29);

      const payload = [
        `>start ${JSON.stringify({ formatid: this.format, seed: this.seed })}`,
        `>player p1 ${JSON.stringify({ name: 'Agent-1', team: p1Team })}`,
        `>player p2 ${JSON.stringify({ name: 'Agent-2', team: p2Team })}`,
      ].join('\n');

      await this.streams.omniscient.write(payload);
      const result = await this.drainUntilExternalDecision(options);
      this.logCursor = this.logLines.length;
      return result;
    } catch (error) {
      this.#originalCreation?.abortStaging();
      this.#nativeBirth?.abortStaging();
      this.#requestHealth?.release(this);
      this.#switchEvents?.release(this);
      this.#requestTrace?.invalidate();
      this.#requestTrace = null;
      throw error;
    }
  }

  /** Privileged pre-submission diagnostics; never an authorizing handle. */
  inspectStagedOriginalOwner(owner: PlayerID): OriginalOwnerEvidence {
    assertAuthoritativeEnvironment(this);
    if (!this.#originalCreation) throw new Error('original-owner/v1/no-creation');
    return this.#originalCreation.diagnostic(this, owner);
  }

  async resetFromSerialized(serialized: Record<string, unknown>, options?: StepResultOptions, associationTicket?: NativeRestoreTicket): Promise<StepResult> {
    if (!simulationEnvironments.has(this) && snapshotRestorePolicy(this.#runtimeProfile.package_version) === 'held-b2-required') {
      if (!this.#objectAssociation) throw new Error('snapshot-admission/v1/raw-restore-unsupported');
      this.#objectAssociation.assertRestoreAdmission(this, serialized, associationTicket);
    }
    this.noteLiveWrite();
    this.#originalCreation?.abandonForRestore(this);
    this.#nativeBirth?.abandonForRestore(this);
    if (this.#nativeBirth) this.#objectAssociation?.disableLegacy(this);
    // Validate a cloned snapshot before disrupting a running battle. The
    // optional history is opaque restoration metadata, not simulator input.
    const terminalHistory = readTerminalRequestHistory(serialized, this.getReaderContext());
    const requestOverrides = readActiveRequestOverrides(serialized);
    const { [TERMINAL_REQUEST_HISTORY_KEY]: _history, [ACTIVE_REQUEST_OVERRIDES_KEY]: _overrides, ...simulatorSnapshot } = serialized;
    const snapshot = structuredClone(simulatorSnapshot) as Record<string, unknown>;
    if (terminalHistory && !snapshot.ended) {
      terminalHistoryInvalid(TERMINAL_REQUEST_HISTORY_KEY, 'is only valid for terminal snapshots');
    }
    if (requestOverrides) {
      if (snapshot.ended) overrideInvalid(ACTIVE_REQUEST_OVERRIDES_KEY, 'is only valid for live snapshots');
      const regenerated = Battle.fromJSON(structuredClone(snapshot) as any);
      try {
        for (const [player, request] of Object.entries(requestOverrides)) {
          validateActiveRequestOverride(request, regenerated.sides.find((side) => side.id === player),
            `${ACTIVE_REQUEST_OVERRIDES_KEY}.requests.${player}`, this.#runtimeProfile);
        }
      } finally { regenerated.destroy(); }
    }
    try {
      await this.destroyBattle();
      this.logLines = [];
      this.logCursor = 0;
      this.lastError = null;
      this.initialized = true;
      this.initializeStreams();
      if (!this.battleStream) throw new Error('Battle stream failed to initialize.');
      const stream = this.battleStream as unknown as {
        battle: Battle | null;
        pushMessage: (type: string, data: string | string[]) => void;
      };
      // Battle.fromJSON may retain nested references from the supplied object;
      // clone the simulator-only snapshot so exact branches cannot share mutable
      // state with their source or siblings.
      this.#objectAssociation?.beforeRestore(this, serialized, snapshot, associationTicket);
      const battle = associationTicket && this.#requestHealth
        ? this.#requestHealth.decode(this, associationTicket, () => Battle.fromJSON(snapshot)) : Battle.fromJSON(snapshot);
      try { this.#objectAssociation?.acceptRestore(this, snapshot, battle, associationTicket); }
      catch (error) { battle.destroy(); throw error; }
      if (associationTicket) this.#switchEvents?.attachRestored(this, battle, this.battleStream!, associationTicket);
      battle.restart((type, data) => stream.pushMessage(type, Array.isArray(data) ? data.join('\n') : data));
      stream.battle = battle;
      battle.sentLogPos = 0;
      battle.sentEnd = false;
      battle.sendUpdates();
      for (const side of battle.sides) {
        const override = requestOverrides?.[side.id as PlayerID];
        if (override) side.activeRequest = (this.#requestHealth ? this.#requestHealth.cloneOverlay(this, battle, side.id as PlayerID, override) : structuredClone(override)) as typeof side.activeRequest;
        if (side?.activeRequest) {
          if (battle.ended || (!side.activeRequest.wait && side.isChoiceDone())) {
            this.players?.[side.id as PlayerID].markRestoredRequestConsumed();
          }
          if (this.#requestTrace) this.#requestTrace.atProducer('restore_reemit', () => side.emitRequest(side.activeRequest!));
          else side.emitRequest(side.activeRequest!);
        }
      }
      // Terminal battles emit no new private requests. Restore only the
      // addressed request history that originally populated each owner's view;
      // it is deliberately not a live request and never enters the log prefix.
      if (battle.ended && terminalHistory) {
        for (const player of PLAYERS) {
          const rawRequest = terminalHistory.requests[player];
          if (rawRequest) this.players?.[player].restoreTerminalRequestData(rawRequest);
          const submitted = terminalHistory.submitted_switches?.[player];
          if (submitted) this.players?.[player].tracker.restoreSubmittedSwitch(submitted);
        }
      }
      const result = await this.drainUntilExternalDecision(options);
      this.logCursor = this.logLines.length;
      return result;
    } catch (error) {
      this.#requestTrace?.invalidate();
      this.#requestTrace = null;
      this.#requestHealth?.release(this);
      this.#switchEvents?.release(this);
      this.#objectAssociation?.discard(this);
      throw error;
    }
  }

  serializeBattle(): Record<string, unknown> {
    this.ensureReady();
    const battle = (this.battleStream as unknown as { battle: Battle | null })?.battle;
    if (!battle) throw new Error(`Environment ${this.id} has no active battle.`);
    const serialized = battle.toJSON() as Record<string, unknown>;
    this.#switchEvents?.plainSerialization(this, battle, serialized);
    if (!battle.ended) return this.withActiveRequestOverrides(battle, serialized);
    const requests: Partial<Record<PlayerID, TerminalHistoryRequest>> = {};
    const switches: NonNullable<TerminalRequestHistory['submitted_switches']> = {};
    for (const player of PLAYERS) {
      const rawRequest = this.players?.[player].getOwnRequestData();
      if (rawRequest) {
        requests[player] = canonicalizeTerminalRequest(
          rawRequest,
          player,
          `${TERMINAL_REQUEST_HISTORY_KEY}.requests.${player}`,
        );
        const submitted = this.players?.[player].tracker.getSubmittedSwitch();
        if (submitted) switches[player] = submitted;
      }
    }
    if (!Object.keys(requests).length) return serialized;
    return {
      ...serialized,
      [TERMINAL_REQUEST_HISTORY_KEY]: {
        schema_version: Object.keys(switches).length ? TERMINAL_SWITCH_HISTORY_SCHEMA_VERSION : TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION,
        requests,
        ...(Object.keys(switches).length ? {submitted_switches: switches} : {}),
      },
    };
  }

  /**
   * Showdown's toJSON omits side.activeRequest and fromJSON regenerates it, so
   * an in-place edit made by a rejected choice is lost on restore. Carry a
   * live request only when it differs from the regenerated one by an
   * engine-legal edit; every other snapshot is unchanged (an unexplained
   * difference is not carried, which preserves the previous bytes).
   */
  private withActiveRequestOverrides(battle: Battle, serialized: Record<string, unknown>): Record<string, unknown> {
    const regenerated = Battle.fromJSON(structuredClone(serialized) as any);
    const requests: Record<string, unknown> = {};
    try {
      for (const side of battle.sides) {
        const live = side?.activeRequest, twin = regenerated.sides.find((entry) => entry.id === side.id);
        if (!live || isDeepStrictEqual(live, twin?.activeRequest)) continue;
        try { validateActiveRequestOverride(live as unknown as Record<string, unknown>, twin, side.id, this.#runtimeProfile); } catch (error) {
          if (!(error instanceof ActiveRequestOverrideValidationError)) throw error;
          // Byte-preserving fallback: the old snapshot is returned, but the drop is observable.
          activeRequestOverrideDiagnostics.dropped++;
          activeRequestOverrideDiagnostics.onDrop?.({player: side.id as PlayerID, path: error.path, reason: error.reason});
          continue;
        }
        requests[side.id] = structuredClone(live);
      }
    } finally { regenerated.destroy(); }
    if (!Object.keys(requests).length) return serialized;
    return {...serialized, [ACTIVE_REQUEST_OVERRIDES_KEY]: {schema_version: ACTIVE_REQUEST_OVERRIDES_SCHEMA_VERSION, requests}};
  }

  private initializeStreams(): void {
    const trace = this.#requestTrace = simulationEnvironments.has(this) ? null
      : new RequestEmissionTrace((emission, receipt) => this.#requestHealth?.received(this, emission, receipt));
    const nativeBirth = this.#nativeBirth, environment = this, switchEvents = this.#switchEvents, requestHealth = this.#requestHealth;
    const settling = this.settling = new SettlingBarrier(this.settlingOptions);
    // _write synchronously emits requests then sendUpdates. Count at the source,
    // before getPlayerStreams asynchronously fans out each message.
    this.battleStream = new class extends BattleStream {
      override _write(chunk: string): void {
        if (trace) trace.atProducer('native_emission', () => super._write(chunk));
        else super._write(chunk);
      }
      override _writeLine(type: string, message: string): void {
        super._writeLine(type, message);
        if (type === 'start' && nativeBirth) {
          nativeBirth.observe(environment, this.battle!);
          switchEvents?.attachBirth(environment, this.battle!, this);
        }
      }
      override pushMessage(type: string, data: string): void {
        switchEvents?.pushed(environment, this, type, data);
        if (trace) {
          const emission = trace.emitted(type, data);
          requestHealth?.sent(environment, emission);
        }
        settling.emitted(type, data);
        super.pushMessage(type, data);
      }
      override pushError(error: Error, recoverable?: boolean): void {
        settling.fail('simulator-error', error);
        super.pushError(error, recoverable);
      }
      override pushEnd(): void {
        settling.streamClosed();
        super.pushEnd();
      }
    }({ keepAlive: true });
    this.streams = getPlayerStreams(this.battleStream);
    switchEvents?.bindSpectator(this, this.streams.spectator);
    trace?.bind('p1', this.streams.p1);
    trace?.bind('p2', this.streams.p2);
    const ownerStreams = this.streams;
    this.players = {
      p1: new ManagedPlayer({
        rulesContext: this.getReaderContext(),
        env: this,
        player: 'p1',
        stream: this.streams.p1 as unknown as PlayerStream,
        receiveRequestRecord: (record) => { trace?.received('p1', ownerStreams.p1, record); },
        controller: this.controllers.p1.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p1', this.getReaderContext()),
        randomAgent: this.randomAgents.p1,
        heuristicAgent: this.heuristicAgent,
        settling,
      }),
      p2: new ManagedPlayer({
        rulesContext: this.getReaderContext(),
        env: this,
        player: 'p2',
        stream: this.streams.p2 as unknown as PlayerStream,
        receiveRequestRecord: (record) => { trace?.received('p2', ownerStreams.p2, record); },
        controller: this.controllers.p2.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p2', this.getReaderContext()),
        randomAgent: this.randomAgents.p2,
        heuristicAgent: this.heuristicAgent,
        settling,
      }),
    };

    for (const player of PLAYERS) {
      this.consumerTasks.push(this.players[player].start().catch((error: Error) => this.markError(error)));
    }
    this.consumerTasks.push(this.listenSpectator().catch((error: Error) => this.markError(error)));
  }

  private createRandomAgent(controller: ControllerSpec): RandomBaselineAgent {
    if (controller.random_seed === undefined) return new RandomBaselineAgent();
    if (controller.controller !== 'random') {
      throw new Error('random_seed is only valid for a random controller.');
    }
    return new RandomBaselineAgent(createSeededRandom(controller.random_seed));
  }

  async step(choices: Partial<Record<PlayerID, string>>): Promise<StepResult> {
    return this.stepWithOptions(choices);
  }

  async stepWithOptions(choices: Partial<Record<PlayerID, string>>, options?: StepResultOptions): Promise<StepResult> {
    this.ensureReady();
    for (const player of PLAYERS) {
      const choice = choices[player];
      if (!choice) {
        continue;
      }
      this.players?.[player].submitExternalChoice(choice);
    }
    return this.drainUntilExternalDecision(options);
  }

  async stepWithCanonicalOptions(actions: Partial<Record<PlayerID, CanonicalAction>>, options?: StepResultOptions): Promise<StepResult> {
    this.ensureReady();
    for (const player of PLAYERS) {
      const action = actions[player];
      if (!action) {
        continue;
      }
      this.players?.[player].submitCanonicalAction(action);
    }
    return this.drainUntilExternalDecision(options);
  }

  captureSeededSnapshot(parentBranchId: string | null = null): SeededBattleSnapshot {
    assertAuthoritativeEnvironment(this);
    this.ensureReady();
    const raw = this.serializeBattle();
    const snapshot = createSeededBattleSnapshot(this.format, this.seed, raw, parentBranchId);
    this.#objectAssociation?.recordSerialization(this, this.battleStream!.battle!, raw, snapshot);
    this.#switchEvents?.recordSnapshot(this, raw, snapshot);
    this.#requestHealth?.recordSnapshot(this, snapshot);
    return snapshot;
  }

  getRequest(player: PlayerID): ChoiceRequestView | null {
    this.ensureReady();
    return this.players?.[player].getRequest() || null;
  }

  getReportedRequest(player: PlayerID): ChoiceRequestView | null {
    this.ensureReady();
    return this.players?.[player].getReportedRequest() ?? null;
  }

  /** Execute only on a disposable pipeline candidate; publication/rollback is session-owned. */
  async stepSeededForcedSwitch(request: SeededForcedSwitchRequest, options?: StepResultOptions): Promise<SeededForcedSwitchResult> {
    assertAuthoritativeEnvironment(this);
    this.ensureReady();
    validateSeededForcedSwitchRequest(request);
    const current = this.captureSeededSnapshot(null);
    if (current.state_fingerprint !== request.snapshot.state_fingerprint || current.format !== request.snapshot.format
      || JSON.stringify(current.root_seed) !== JSON.stringify(request.snapshot.root_seed)) {
      throw new Error('Forced-switch snapshot is stale or belongs to a different simulator state.');
    }
    for (const player of PLAYERS) {
      const live = this.getReportedRequest(player);
      const observed = request.observations[player].request!;
      if (!live || live.player !== player || live.rqid !== observed.rqid || live.wait !== observed.wait
        || live.force_switch !== observed.force_switch || live.team_preview !== observed.team_preview
        || JSON.stringify(live.legal_actions) !== JSON.stringify(observed.legal_actions)) {
        throw new Error(`Forced-switch live request mismatch for ${player}.`);
      }
    }
    const actor = this.getRequest(request.acting_player);
    if (!actor || this.getRequest(request.waiting_player)) throw new Error('Forced-switch pending players are inconsistent.');
    if (request.schema_version === SEEDED_REVIVAL_SCHEMA_VERSION) assertRevivalSelection(actor);
    else assertOrdinaryForcedSwitch(actor);
    const action = request.actions[request.acting_player]!;
    canonicalActionToChoice(action, {
      player: request.acting_player, rqid: actor.rqid, force_switch: true, legal_actions: actor.legal_actions, side: actor.side,
    });
    const result = await this.stepWithCanonicalOptions(request.actions, { ...options, include_wait_requests: true });
    const output = this.captureSeededSnapshot(request.snapshot.branch_id);
    const built = buildSeededForcedSwitchResult(request, output, result);
    this.#objectAssociation?.finalizeSerialization(this, output, built.output_snapshot);
    this.#switchEvents?.finalizeSnapshot(this, output, built.output_snapshot);
    this.#requestHealth?.finalizeSnapshot(output, built.output_snapshot);
    return built;
  }

  async stepSeededTransition(request: SeededTransitionRequest, options?: StepResultOptions): Promise<SeededTransitionResult> {
    assertAuthoritativeEnvironment(this);
    this.ensureReady();
    validateSeededTransitionRequest(request);
    const currentSnapshot = this.captureSeededSnapshot(null);
    if (currentSnapshot.format !== request.snapshot.format || currentSnapshot.state_fingerprint !== request.snapshot.state_fingerprint) {
      throw new Error('Seeded transition snapshot is stale or belongs to a different simulator state.');
    }
    if (JSON.stringify(currentSnapshot.root_seed) !== JSON.stringify(request.snapshot.root_seed)) {
      throw new Error('Seeded transition root seed does not match the simulator.');
    }
    const pendingPlayers = PLAYERS.filter((player) => this.players?.[player].getRequest() !== null);
    if (pendingPlayers.length !== 2 || pendingPlayers.some((player) => !request.actions[player])) {
      throw new Error('Seeded transition requires exactly the currently pending joint requests.');
    }
    // Preflight every live request before forwarding any raw choice. This keeps
    // mixed-validity joint actions atomic at the transition boundary.
    for (const player of PLAYERS) {
      const liveRequest = this.players?.[player].getRequest();
      if (!liveRequest) throw new Error(`Seeded transition has no live request for ${player}.`);
      canonicalActionToChoice(request.actions[player], {
        player,
        rqid: liveRequest.rqid,
        force_switch: liveRequest.force_switch,
        legal_actions: liveRequest.legal_actions, side: liveRequest.side,
      });
    }
    const stepResult = await this.stepWithCanonicalOptions(request.actions, options);
    const outputSnapshot = this.captureSeededSnapshot(request.snapshot.branch_id);
    // Keep this explicit fingerprint check close to execution so a future
    // simulator serialization change cannot silently weaken branch identity.
    if (fingerprintSimulatorState(outputSnapshot.simulator_state) !== outputSnapshot.state_fingerprint) {
      throw new Error('Seeded transition output fingerprint is inconsistent.');
    }
    const built = buildSeededTransitionResult(request, outputSnapshot, stepResult);
    this.#objectAssociation?.finalizeSerialization(this, outputSnapshot, built.output_snapshot);
    this.#switchEvents?.finalizeSnapshot(this, outputSnapshot, built.output_snapshot);
    this.#requestHealth?.finalizeSnapshot(outputSnapshot, built.output_snapshot);
    return built;
  }

  async close(): Promise<void> {
    this.noteLiveWrite();
    this.#originalCreation?.abortStaging();
    this.#nativeBirth?.abortStaging();
    this.#requestHealth?.release(this);
      this.#switchEvents?.release(this);
    this.#objectAssociation?.release(this);
    await this.destroyBattle();
    this.initialized = false;
  }

  getAgentAction(player: PlayerID, agent: ControllerType): BaselineDecision {
    this.ensureReady();
    if (agent !== 'random' && agent !== 'heuristic') {
      throw new Error(`Unsupported agent ${agent}.`);
    }
    return this.players?.[player].suggest(agent) as BaselineDecision;
  }

  /** Privileged owner-only diagnostics; no current request or publication authority. */
  getRequestEmissionTraceHandle(owner: PlayerID): RequestTraceHandle {
    assertAuthoritativeEnvironment(this);
    if (!this.#requestTrace) throw new Error('request-trace/v1/unavailable');
    return this.#requestTrace.handle(owner);
  }

  inspectRequestEmissionTrace(handle: RequestTraceHandle, owner: PlayerID): readonly RequestEmissionReceipt[] {
    assertAuthoritativeEnvironment(this);
    if (!this.#requestTrace) throw new Error('request-trace/v1/unavailable');
    return this.#requestTrace.inspect(handle, owner);
  }

  diagnostics(): Record<string, unknown> {
    const state: Record<string, unknown> = {
      id: this.id,
      format: this.format,
      seed: this.seed,
      initialized: this.initialized,
      controllers: this.controllers,
      log_lines: this.logLines.length,
      last_error: this.lastError ? this.lastError.message : null,
    };

    try {
      const p1View = this.players?.p1.getView();
      const p2View = this.players?.p2.getView();
      state.turn = Math.max(p1View?.turn || 0, p2View?.turn || 0);
      state.terminated = this.isTerminated();
      state.winner = this.getWinner();
      state.pending_external = this.hasPendingExternalDecision();
      state.p1_active = p1View?.self_team.filter((pokemon) => pokemon.active).map((pokemon) => pokemon.species);
      state.p2_active = p2View?.self_team.filter((pokemon) => pokemon.active).map((pokemon) => pokemon.species);
      state.players = {
        p1: this.players?.p1.diagnostics(),
        p2: this.players?.p2.diagnostics(),
      };
    } catch (error) {
      state.state_error = (error as Error).message;
    }

    return state;
  }

  buildResponseView(player: PlayerID, includePossibleRoles: boolean): BattleView {
    const baseView = this.players?.[player].getView();
    if (!baseView) {
      throw new Error(`View for ${player} is unavailable.`);
    }

    const clonePokemon = (pokemon: BattleView['self_team'][number]): BattleView['self_team'][number] => ({
      ...pokemon,
      moves: [...pokemon.moves],
      revealed_moves: [...pokemon.revealed_moves],
      types: [...pokemon.types],
      stats: { ...pokemon.stats },
      boosts: { ...pokemon.boosts },
      volatiles: [...pokemon.volatiles],
      possible_roles: includePossibleRoles ? [...pokemon.possible_roles] : [],
      possible_moves: [...pokemon.possible_moves],
      possible_abilities: [...pokemon.possible_abilities],
      possible_tera_types: [...pokemon.possible_tera_types],
    });

    const clonedView: BattleView = {
      ...baseView,
      names: { ...baseView.names },
      team_size: { ...baseView.team_size },
      active: { ...baseView.active },
      field: {
        weather: baseView.field.weather,
        terrain: baseView.field.terrain,
        pseudo_weather: [...baseView.field.pseudo_weather],
        side_conditions: {
          self: { ...baseView.field.side_conditions.self },
          opponent: { ...baseView.field.side_conditions.opponent },
        },
      },
      self_team: baseView.self_team.map(clonePokemon),
      opponent_team: baseView.opponent_team.map(clonePokemon),
    };

    if (includePossibleRoles) {
      for (const pokemon of clonedView.opponent_team) {
        pokemon.possible_roles = this.heuristicAgent.getPossibleRoles(pokemon);
      }
    }

    return clonedView;
  }

  markError(error: Error): void {
    this.noteLiveWrite();
    this.lastError = error;
    this.settling.fail('simulator-error', error);
  }

  /** Diagnostic replay only: no decisions, observations or identity authority. */
  async replaySimulation(input: string, consume: (owner: PlayerID, chunk: string) => void,
    consumePublic?: (chunk: string) => void): Promise<void> {
    if (!simulationEnvironments.has(this)) throw new Error('simulation-only/v1/replay-required');
    if (this.initialized || this.battleStream) throw new Error('simulation-only/v1/replay-requires-fresh-env');
    const allowed = new Set(['>start', '>player', '>p1', '>p2', '>reseed', '>forcewin', '>forcelose', '>forcetie']);
    for (const line of input.split('\n')) {
      if (line && !allowed.has(line.split(' ')[0])) throw new Error('Unsupported simulation replay command');
    }
    const stream = new BattleStream({noCatch: true, keepAlive: true});
    const streams = getPlayerStreams(stream);
    const tasks = (['p1', 'p2', 'spectator'] as const).map(async owner => {
      for await (const chunk of streams[owner]) {
        if (owner === 'spectator') consumePublic?.(chunk);
        else consume(owner, chunk);
      }
    });
    try { await stream.write(input); }
    finally { await stream.writeEnd(); await Promise.all(tasks); }
  }

  private ensureReady(): void {
    if (!this.initialized || !this.players || !this.streams) {
      throw new Error(`Environment ${this.id} has not been reset.`);
    }
    if (this.lastError) {
      throw new SettlingError('simulator-error', this.settling.timeout, this.settling.maxMessages, this.lastError);
    }
  }

  private destroyBattle(): Promise<void> {
    if (this.destruction) return this.destruction;
    const destruction = this.destroyCurrentBattle();
    this.destruction = destruction;
    return destruction.finally(() => { this.destruction = null; });
  }

  private async destroyCurrentBattle(): Promise<void> {
    this.noteLiveWrite();
    this.#requestTrace?.invalidate();
    this.#requestTrace = null;
    this.settling.fail('cancelled');
    const stream = this.battleStream;
    if (stream) {
      if (!stream.atEOF) await stream.writeEnd();
      else stream._destroy();
    }
    await Promise.all(this.consumerTasks);
    this.consumerTasks = [];
    this.battleStream = null;
    this.streams = null;
    this.players = null;
    this.initialized = false;
  }

  private async listenSpectator(): Promise<void> {
    if (!this.streams) {
      return;
    }
    for await (const chunk of this.streams.spectator as unknown as AsyncIterable<string>) {
      if (this.settling.stopped) return;
      appendPublicSpectatorChunk(chunk, this.logLines, this.getReaderContext());
      this.#switchEvents?.received(this, this.streams.spectator, chunk);
      for (const rawLine of chunk.split('\n')) {
        const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
        if (!line) continue;
        // Healing Wish's owner branch is a private exact-HP split. Route only
        // its paired public result into typed state for both perspectives.
        this.players?.p1.tracker.consumePublicHealingWishRecord(line);
        this.players?.p2.tracker.consumePublicHealingWishRecord(line);
      }
      this.settling.acknowledge('spectator');
    }
    this.settling.streamClosed('spectator');
  }

  private hasPendingExternalDecision(): boolean {
    return PLAYERS.some((player) => {
      const controller = this.controllers[player].controller;
      return controller === 'external' && !!this.players?.[player].getRequest();
    });
  }

  private isTerminated(): boolean {
    return PLAYERS.some((player) => this.players?.[player].getView().terminated);
  }

  private getWinner(): Winner {
    const p1Winner = this.players?.p1.getView().winner;
    const p2Winner = this.players?.p2.getView().winner;
    return p1Winner || p2Winner || null;
  }

  private buildStepResult(options?: StepResultOptions): StepResult {
    const normalized = normalizeStepResultOptions(options);
    const views: StepResult['views'] = {};
    const requests: StepResult['requests'] = {};
    for (const player of normalized.view_players) {
      views[player] = this.buildResponseView(player, normalized.include_possible_roles);
      requests[player] = normalized.include_wait_requests
        ? this.players?.[player].getReportedRequest() ?? null
        : this.players?.[player].getRequest() ?? null;
    }

    const p1View = this.players?.p1.getView();
    const p2View = this.players?.p2.getView();

    const winner = this.getWinner();
    const rewards = {
      p1: winner === 'p1' ? 1 : winner === 'p2' ? -1 : 0,
      p2: winner === 'p2' ? 1 : winner === 'p1' ? -1 : 0,
    };

    const logDelta = normalized.include_log_delta ? this.logLines.slice(this.logCursor) : [];
    this.logCursor = this.logLines.length;

    return {
      ...(simulationEnvironments.has(this) ? { authority: 'simulation-only' as const } : {}),
      env_id: this.id,
      terminated: this.isTerminated(),
      winner,
      rewards,
      requests,
      views,
      omniscient: null,
      log_delta: logDelta,
      info: {
        turn: Math.max(p1View?.turn || 0, p2View?.turn || 0),
        format: this.format,
      },
    };
  }

  private async drainUntilExternalDecision(options?: StepResultOptions): Promise<StepResult> {
    try {
      this.ensureReady();
      await this.settling.wait(() => {
        const p1 = this.players!.p1.getView();
        const p2 = this.players!.p2.getView();
        if (p1.terminated && p2.terminated && p1.winner === p2.winner) return 'terminal';
        if (!p1.terminated && !p2.terminated && this.hasPendingExternalDecision()) return 'decision';
        return null;
      });
      return this.buildStepResult(options);
    } catch (error) {
      await this.destroyBattle();
      throw error;
    }
  }
}

export class EnvironmentManager {
  readonly #runtimeProfile: NativeRuntimeProfile;
  constructor(runtimeProfile: NativeRuntimeProfile = installedNativeProfile()) {
    assertNativeRuntimeProfile(runtimeProfile); this.#runtimeProfile = runtimeProfile;
  }
  private readonly envs = new Map<string, LocalBattleEnv>();
  private readonly snapshotHandles = new Map<string, { envId: string; environment: LocalBattleEnv; occurrence: object; snapshot: SeededBattleSnapshot }>();
  private readonly snapshotNamespace = BigInt('0x' + randomBytes(16).toString('hex')).toString();
  private nextId = 1;
  private nextSnapshotHandle = 1;

  createEnv(format: string, seed?: number[], controllers?: Partial<Record<PlayerID, ControllerSpec>>): { env_id: string } {
    const envId = `env-${this.nextId++}`;
    const env = new LocalBattleEnv(envId, format, seed, controllers, {}, undefined, undefined, undefined, this.#runtimeProfile);
    this.envs.set(envId, env);
    return { env_id: envId };
  }

  async resetEnv(envId: string, options?: StepResultOptions): Promise<StepResult> {
    this.revokeSnapshots(envId);
    return this.requireEnv(envId).resetWithOptions(options);
  }

  async forkBeliefEnv(
    sourceEnvId: string,
    perspective: PlayerID,
    beliefSeed: number[],
    options?: StepResultOptions,
  ): Promise<{ env_id: string; result: StepResult; belief: BeliefForkMetadata }> {
    assertBeliefForkPolicy(this.#runtimeProfile.package_version);
    const source = this.requireEnv(sourceEnvId);
    const serialized = source.serializeBattle();
    const view = source.buildResponseView(perspective, false);
    const built = buildBeliefSnapshot(serialized, view, perspective, source.format, beliefSeed, this.#runtimeProfile);
    const envId = `env-${this.nextId++}`;
    const env = new LocalBattleEnv(envId, source.format, source.seed, {
      p1: { controller: 'external' },
      p2: { controller: 'external' },
    }, {}, undefined, undefined, undefined, this.#runtimeProfile);
    this.envs.set(envId, env);
    try {
      const result = await env.resetFromSerialized(built.snapshot, options);
      const forkView = result.views[perspective];
      if (forkView) {
        for (const publicMon of view.opponent_team) {
          const forkMon = forkView.opponent_team.find(mon => mon.species === publicMon.species);
          if (!forkMon) {
            built.metadata.public_info_constraint_violations++;
            continue;
          }
          if (publicMon.revealed_moves.some(move => !forkMon.revealed_moves.includes(move))) {
            built.metadata.public_info_constraint_violations++;
          }
          if (publicMon.ability && forkMon.ability !== publicMon.ability) {
            built.metadata.public_info_constraint_violations++;
          }
          if (publicMon.item && publicMon.item !== 'has-item' && forkMon.item !== publicMon.item) {
            built.metadata.public_info_constraint_violations++;
          }
          if (publicMon.terastallized && forkMon.tera_type !== publicMon.tera_type) {
            built.metadata.public_info_constraint_violations++;
          }
          if (publicMon.status !== forkMon.status || publicMon.fainted !== forkMon.fainted) {
            built.metadata.public_info_constraint_violations++;
          }
          if (Math.abs((publicMon.hp_ratio ?? 1) - (forkMon.hp_ratio ?? 1)) > 0.011) {
            built.metadata.public_info_constraint_violations++;
          }
        }
      }
      return { env_id: envId, result, belief: built.metadata };
    } catch (error) {
      await env.close();
      this.envs.delete(envId);
      throw error;
    }
  }

  async stepEnv(envId: string, choices: Partial<Record<PlayerID, string>>, options?: StepResultOptions): Promise<StepResult> {
    return this.requireEnv(envId).stepWithOptions(choices, options);
  }

  async stepCanonicalEnv(envId: string, actions: Partial<Record<PlayerID, CanonicalAction>>, options?: StepResultOptions): Promise<StepResult> {
    return this.requireEnv(envId).stepWithCanonicalOptions(actions, options);
  }

  captureSeededSnapshotEnv(envId: string): SeededSnapshotRef {
    const snapshot = this.requireEnv(envId).captureSeededSnapshot(null);
    return toSeededSnapshotRef(snapshot, this.storeSnapshot(envId, snapshot));
  }

  async stepSeededTransitionEnv(envId: string, request: SeededTransitionWireRequest, options?: StepResultOptions): Promise<SeededTransitionPublicResult> {
    const env = this.requireEnv(envId);
    if (Object.prototype.hasOwnProperty.call(request.snapshot as object, 'simulator_state')) {
      throw new Error('Seeded transition RPC snapshots must use an opaque server-managed handle.');
    }
    const stored = this.snapshotHandles.get(request.snapshot.snapshot_handle);
    if (!stored || stored.envId !== envId || stored.environment !== env || stored.occurrence !== env.getLiveWorldOccurrence()) {
      throw new Error('Unknown seeded transition snapshot handle.');
    }
    const snapshot = stored.snapshot;
    if (
      request.snapshot.schema_version !== snapshot.schema_version
      || request.snapshot.format !== snapshot.format
      || request.snapshot.root_seed.join(',') !== snapshot.root_seed.join(',')
      || request.snapshot.state_fingerprint !== snapshot.state_fingerprint
      || request.snapshot.parent_branch_id !== snapshot.parent_branch_id
      || request.snapshot.transition_id !== snapshot.transition_id
      || request.snapshot.branch_id !== snapshot.branch_id
    ) {
      throw new Error('Seeded transition snapshot handle metadata is inconsistent.');
    }
    const internalRequest: SeededTransitionRequest = {
      schema_version: request.schema_version,
      snapshot,
      observations: request.observations,
      actions: request.actions,
      step_index: request.step_index,
    };
    let result: SeededTransitionResult;
    try { result = await env.stepSeededTransition(internalRequest, options); }
    catch (error) {
      if (stored.occurrence !== env.getLiveWorldOccurrence()) this.revokeSnapshots(envId);
      throw error;
    }
    this.revokeSnapshots(envId);
    const outputHandle = this.storeSnapshot(envId, result.output_snapshot);
    return toSeededTransitionPublicResult(result, outputHandle);
  }

  async closeEnv(envId: string): Promise<{ env_id: string; closed: true }> {
    const env = this.requireEnv(envId);
    this.revokeSnapshots(envId);
    await env.close();
    this.envs.delete(envId);
    for (const [handle, stored] of this.snapshotHandles) {
      if (stored.envId === envId) this.snapshotHandles.delete(handle);
    }
    return { env_id: envId, closed: true };
  }

  getAgentAction(envId: string, player: PlayerID, agent: ControllerType): BaselineDecision {
    return this.requireEnv(envId).getAgentAction(player, agent);
  }

  describeEnv(envId: string): Record<string, unknown> {
    const env = this.envs.get(envId);
    if (!env) {
      return {
        id: envId,
        missing: true,
      };
    }
    return env.diagnostics();
  }

  diagnostics(): Record<string, unknown> {
    return {
      open_env_count: this.envs.size,
      next_env_id: this.nextId,
      envs: [...this.envs.values()].map((env) => env.diagnostics()),
    };
  }

  async closeAll(): Promise<void> {
    this.snapshotHandles.clear();
    for (const env of this.envs.values()) {
      await env.close();
    }
    this.envs.clear();
    this.snapshotHandles.clear();
  }

  private storeSnapshot(envId: string, snapshot: SeededBattleSnapshot): string {
    const environment = this.requireEnv(envId), occurrence = environment.getLiveWorldOccurrence();
    for (const [key, held] of this.snapshotHandles) if (held.envId === envId && held.occurrence !== occurrence) this.snapshotHandles.delete(key);
    const handle = `snapshot-${this.snapshotNamespace}${this.nextSnapshotHandle++}`;
    this.snapshotHandles.set(handle, { envId, environment, occurrence, snapshot: structuredClone(snapshot) });
    return handle;
  }

  private revokeSnapshots(envId: string): void {
    for (const [handle, held] of this.snapshotHandles) if (held.envId === envId) this.snapshotHandles.delete(handle);
  }

  private requireEnv(envId: string): LocalBattleEnv {
    const env = this.envs.get(envId);
    if (!env) {
      throw new Error(`Unknown environment ${envId}.`);
    }
    return env;
  }
}
