import { Battle, BattleStream, Dex, Teams, getPlayerStreams } from 'pokemon-showdown';
import { cloneChoiceRequest, removeChoiceFromRequest } from './action_codec';
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
import { PlayerStateExtractor } from './state_extractor';
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
  schema_version: typeof TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION;
  requests: Partial<Record<PlayerID, TerminalHistoryRequest>>;
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

function readTerminalRequestHistory(serialized: Record<string, unknown>): TerminalRequestHistory | null {
  const raw = serialized[TERMINAL_REQUEST_HISTORY_KEY];
  if (raw === undefined) return null;
  const history = recordAt(raw, TERMINAL_REQUEST_HISTORY_KEY);
  if (history.schema_version !== TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION) {
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
  return {
    schema_version: TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION,
    requests: canonicalRequests,
  };
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

export class LocalBattleEnv {
  readonly id: string;
  readonly format: string;
  readonly seed: [number, number, number, number];
  readonly controllers: Record<PlayerID, ControllerSpec>;

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
  ) {
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
    await this.destroyBattle();
    this.logLines = [];
    this.logCursor = 0;
    this.lastError = null;
    this.initialized = true;

    this.initializeStreams();
    if (!this.streams) throw new Error('Battle streams failed to initialize.');
    const p1Team = Teams.pack(Teams.generate(this.format, { seed: offsetSeed(this.seed, 11) }));
    const p2Team = Teams.pack(Teams.generate(this.format, { seed: offsetSeed(this.seed, 29) }));

    const payload = [
      `>start ${JSON.stringify({ formatid: this.format, seed: this.seed })}`,
      `>player p1 ${JSON.stringify({ name: 'Agent-1', team: p1Team })}`,
      `>player p2 ${JSON.stringify({ name: 'Agent-2', team: p2Team })}`,
    ].join('\n');

    await this.streams.omniscient.write(payload);
    const result = await this.drainUntilExternalDecision(options);
    this.logCursor = this.logLines.length;
    return result;
  }

  async resetFromSerialized(serialized: Record<string, unknown>, options?: StepResultOptions): Promise<StepResult> {
    // Validate a cloned snapshot before disrupting a running battle. The
    // optional history is opaque restoration metadata, not simulator input.
    const terminalHistory = readTerminalRequestHistory(serialized);
    const { [TERMINAL_REQUEST_HISTORY_KEY]: _history, ...simulatorSnapshot } = serialized;
    const snapshot = structuredClone(simulatorSnapshot) as Record<string, unknown>;
    if (terminalHistory && !snapshot.ended) {
      terminalHistoryInvalid(TERMINAL_REQUEST_HISTORY_KEY, 'is only valid for terminal snapshots');
    }
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
    const battle = Battle.fromJSON(snapshot);
    battle.restart((type, data) => stream.pushMessage(type, Array.isArray(data) ? data.join('\n') : data));
    stream.battle = battle;
    battle.sentLogPos = 0;
    battle.sentEnd = false;
    battle.sendUpdates();
    for (const side of battle.sides) {
      if (side?.activeRequest) {
        if (battle.ended || (!side.activeRequest.wait && side.isChoiceDone())) {
          this.players?.[side.id as PlayerID].markRestoredRequestConsumed();
        }
        side.emitRequest(side.activeRequest);
      }
    }
    // Terminal battles emit no new private requests. Restore only the
    // addressed request history that originally populated each owner's view;
    // it is deliberately not a live request and never enters the log prefix.
    if (battle.ended && terminalHistory) {
      for (const player of PLAYERS) {
        const rawRequest = terminalHistory.requests[player];
        if (rawRequest) this.players?.[player].restoreTerminalRequestData(rawRequest);
      }
    }
    const result = await this.drainUntilExternalDecision(options);
    this.logCursor = this.logLines.length;
    return result;
  }

  serializeBattle(): Record<string, unknown> {
    this.ensureReady();
    const battle = (this.battleStream as unknown as { battle: Battle | null })?.battle;
    if (!battle) throw new Error(`Environment ${this.id} has no active battle.`);
    const serialized = battle.toJSON() as Record<string, unknown>;
    if (!battle.ended) return serialized;
    const requests: Partial<Record<PlayerID, TerminalHistoryRequest>> = {};
    for (const player of PLAYERS) {
      const rawRequest = this.players?.[player].getOwnRequestData();
      if (rawRequest) {
        requests[player] = canonicalizeTerminalRequest(
          rawRequest,
          player,
          `${TERMINAL_REQUEST_HISTORY_KEY}.requests.${player}`,
        );
      }
    }
    if (!Object.keys(requests).length) return serialized;
    return {
      ...serialized,
      [TERMINAL_REQUEST_HISTORY_KEY]: {
        schema_version: TERMINAL_REQUEST_HISTORY_SCHEMA_VERSION,
        requests,
      },
    };
  }

  private initializeStreams(): void {
    const settling = this.settling = new SettlingBarrier(this.settlingOptions);
    // _write synchronously emits requests then sendUpdates. Count at the source,
    // before getPlayerStreams asynchronously fans out each message.
    this.battleStream = new class extends BattleStream {
      override pushMessage(type: string, data: string): void {
        settling.emitted(type, data);
        super.pushMessage(type, data);
      }
      override pushError(error: Error, recoverable?: boolean): void {
        settling.fail('simulator-error');
        super.pushError(error, recoverable);
      }
      override pushEnd(): void {
        settling.streamClosed();
        super.pushEnd();
      }
    }({ keepAlive: true });
    this.streams = getPlayerStreams(this.battleStream);
    this.players = {
      p1: new ManagedPlayer({
        env: this,
        player: 'p1',
        stream: this.streams.p1 as unknown as PlayerStream,
        controller: this.controllers.p1.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p1'),
        randomAgent: this.randomAgents.p1,
        heuristicAgent: this.heuristicAgent,
        settling,
      }),
      p2: new ManagedPlayer({
        env: this,
        player: 'p2',
        stream: this.streams.p2 as unknown as PlayerStream,
        controller: this.controllers.p2.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p2'),
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
    this.ensureReady();
    return createSeededBattleSnapshot(this.format, this.seed, this.serializeBattle(), parentBranchId);
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
    return buildSeededForcedSwitchResult(request, this.captureSeededSnapshot(request.snapshot.branch_id), result);
  }

  async stepSeededTransition(request: SeededTransitionRequest, options?: StepResultOptions): Promise<SeededTransitionResult> {
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
    return buildSeededTransitionResult(request, outputSnapshot, stepResult);
  }

  async close(): Promise<void> {
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
    this.lastError = error;
    this.settling.fail('simulator-error');
  }

  private ensureReady(): void {
    if (!this.initialized || !this.players || !this.streams) {
      throw new Error(`Environment ${this.id} has not been reset.`);
    }
    if (this.lastError) {
      throw new SettlingError('simulator-error', this.settling.timeout, this.settling.maxMessages);
    }
  }

  private destroyBattle(): Promise<void> {
    if (this.destruction) return this.destruction;
    const destruction = this.destroyCurrentBattle();
    this.destruction = destruction;
    return destruction.finally(() => { this.destruction = null; });
  }

  private async destroyCurrentBattle(): Promise<void> {
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
      for (const line of chunk.split('\n')) {
        const trimmed = line.trim();
        if (trimmed) {
          this.logLines.push(trimmed);
        }
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
  private readonly envs = new Map<string, LocalBattleEnv>();
  private readonly snapshotHandles = new Map<string, { envId: string; snapshot: SeededBattleSnapshot }>();
  private nextId = 1;
  private nextSnapshotHandle = 1;

  createEnv(format: string, seed?: number[], controllers?: Partial<Record<PlayerID, ControllerSpec>>): { env_id: string } {
    const envId = `env-${this.nextId++}`;
    const env = new LocalBattleEnv(envId, format, seed, controllers);
    this.envs.set(envId, env);
    return { env_id: envId };
  }

  async resetEnv(envId: string, options?: StepResultOptions): Promise<StepResult> {
    return this.requireEnv(envId).resetWithOptions(options);
  }

  async forkBeliefEnv(
    sourceEnvId: string,
    perspective: PlayerID,
    beliefSeed: number[],
    options?: StepResultOptions,
  ): Promise<{ env_id: string; result: StepResult; belief: BeliefForkMetadata }> {
    const source = this.requireEnv(sourceEnvId);
    const serialized = source.serializeBattle();
    const view = source.buildResponseView(perspective, false);
    const built = buildBeliefSnapshot(serialized, view, perspective, source.format, beliefSeed);
    const envId = `env-${this.nextId++}`;
    const env = new LocalBattleEnv(envId, source.format, source.seed, {
      p1: { controller: 'external' },
      p2: { controller: 'external' },
    });
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
    if (!stored || stored.envId !== envId) {
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
    const result = await env.stepSeededTransition(internalRequest, options);
    const outputHandle = this.storeSnapshot(envId, result.output_snapshot);
    return toSeededTransitionPublicResult(result, outputHandle);
  }

  async closeEnv(envId: string): Promise<{ env_id: string; closed: true }> {
    const env = this.requireEnv(envId);
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
    for (const env of this.envs.values()) {
      await env.close();
    }
    this.envs.clear();
    this.snapshotHandles.clear();
  }

  private storeSnapshot(envId: string, snapshot: SeededBattleSnapshot): string {
    const handle = `snapshot-${this.nextSnapshotHandle++}`;
    this.snapshotHandles.set(handle, { envId, snapshot: structuredClone(snapshot) });
    return handle;
  }

  private requireEnv(envId: string): LocalBattleEnv {
    const env = this.envs.get(envId);
    if (!env) {
      throw new Error(`Unknown environment ${envId}.`);
    }
    return env;
  }
}
