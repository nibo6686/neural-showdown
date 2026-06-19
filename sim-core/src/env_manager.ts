import { Battle, BattleStream, Teams, getPlayerStreams } from 'pokemon-showdown';
import { cloneChoiceRequest, removeChoiceFromRequest } from './action_codec';
import { HeuristicBaselineAgent } from './baselines/heuristic';
import { RandomBaselineAgent } from './baselines/random';
import { buildBeliefSnapshot, type BeliefForkMetadata } from './belief_fork';
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

type PlayerStream = {
  write(data: string): Promise<void> | void;
  writeEnd?: () => Promise<void> | void;
  [Symbol.asyncIterator](): AsyncIterator<string>;
};

function normalizeStepResultOptions(options?: StepResultOptions): Required<StepResultOptions> {
  return {
    view_players: options?.view_players?.length ? [...options.view_players] : [...PLAYERS],
    include_log_delta: options?.include_log_delta !== false,
    include_possible_roles: options?.include_possible_roles !== false,
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
}

class ManagedPlayer {
  readonly player: PlayerID;
  readonly tracker: PlayerStateExtractor;

  private readonly env: LocalBattleEnv;
  private readonly stream: PlayerStream;
  private readonly controller: ControllerType;
  private readonly randomAgent: RandomBaselineAgent;
  private readonly heuristicAgent: HeuristicBaselineAgent;
  private currentRequest: ChoiceRequestView | null;
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
    this.currentRequest = null;
    this.pendingChoice = null;
    this.lastChoiceError = null;
    this.invalidChoices = new Set();
  }

  async start(): Promise<void> {
    for await (const chunk of this.stream) {
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
      this.env.noteStateChange();
    }
    this.env.noteStateChange();
  }

  getView(): BattleView {
    return this.tracker.getView();
  }

  getRequest(): ChoiceRequestView | null {
    return this.currentRequest ? cloneChoiceRequest(this.currentRequest) : null;
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
    this.pendingChoice = choice;
    void this.stream.write(choice);
    this.env.noteStateChange();
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
    if (!request) {
      this.currentRequest = null;
      this.invalidChoices.clear();
      return;
    }

    if (request.wait) {
      this.currentRequest = null;
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
          this.env.noteStateChange();
          return;
        }
      }
      if (filteredRequest && !filteredRequest.wait && !filteredRequest.team_preview) {
        const decision = this.suggest(this.controller, filteredRequest);
        this.currentRequest = null;
        this.pendingChoice = decision.choice;
        void this.stream.write(decision.choice);
        this.env.noteStateChange();
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

  private readonly randomAgent: RandomBaselineAgent;
  private readonly heuristicAgent: HeuristicBaselineAgent;
  private battleStream: BattleStream | null;
  private streams: ReturnType<typeof getPlayerStreams> | null;
  private players: Record<PlayerID, ManagedPlayer> | null;
  private stateWaiters: Array<() => void>;
  private logLines: string[];
  private logCursor: number;
  private lastError: Error | null;
  private initialized: boolean;

  constructor(
    id: string,
    format: string,
    seed?: number[],
    controllers?: Partial<Record<PlayerID, ControllerSpec>>,
  ) {
    this.id = id;
    this.format = format;
    this.seed = createSeed(seed);
    this.controllers = {
      p1: controllers?.p1 || { controller: 'external' },
      p2: controllers?.p2 || { controller: 'external' },
    };
    this.randomAgent = new RandomBaselineAgent();
    this.heuristicAgent = new HeuristicBaselineAgent();
    this.battleStream = null;
    this.streams = null;
    this.players = null;
    this.stateWaiters = [];
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
    return this.drainUntilExternalDecision(options);
  }

  async resetFromSerialized(serialized: Record<string, unknown>, options?: StepResultOptions): Promise<StepResult> {
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
    const battle = Battle.fromJSON(serialized);
    battle.restart((type, data) => stream.pushMessage(type, Array.isArray(data) ? data.join('\n') : data));
    stream.battle = battle;
    battle.sentLogPos = 0;
    battle.sentEnd = false;
    battle.sendUpdates();
    for (const side of battle.sides) {
      if (side?.activeRequest) side.emitRequest(side.activeRequest);
    }
    await new Promise<void>(resolve => setImmediate(resolve));
    return this.drainUntilExternalDecision(options);
  }

  serializeBattle(): Record<string, unknown> {
    this.ensureReady();
    const battle = (this.battleStream as unknown as { battle: Battle | null })?.battle;
    if (!battle) throw new Error(`Environment ${this.id} has no active battle.`);
    return battle.toJSON();
  }

  private initializeStreams(): void {
    this.battleStream = new BattleStream({ keepAlive: true });
    this.streams = getPlayerStreams(this.battleStream);
    this.players = {
      p1: new ManagedPlayer({
        env: this,
        player: 'p1',
        stream: this.streams.p1 as unknown as PlayerStream,
        controller: this.controllers.p1.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p1'),
        randomAgent: this.randomAgent,
        heuristicAgent: this.heuristicAgent,
      }),
      p2: new ManagedPlayer({
        env: this,
        player: 'p2',
        stream: this.streams.p2 as unknown as PlayerStream,
        controller: this.controllers.p2.controller,
        tracker: new PlayerStateExtractor(this.id, this.format, 'p2'),
        randomAgent: this.randomAgent,
        heuristicAgent: this.heuristicAgent,
      }),
    };

    for (const player of PLAYERS) {
      void this.players[player].start().catch((error: Error) => this.markError(error));
    }
    void this.listenSpectator().catch((error: Error) => this.markError(error));
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

  noteStateChange(): void {
    const waiters = this.stateWaiters.splice(0, this.stateWaiters.length);
    for (const waiter of waiters) {
      waiter();
    }
  }

  markError(error: Error): void {
    this.lastError = error;
    this.noteStateChange();
  }

  private ensureReady(): void {
    if (!this.initialized || !this.players || !this.streams) {
      throw new Error(`Environment ${this.id} has not been reset.`);
    }
    if (this.lastError) {
      throw this.lastError;
    }
  }

  private async destroyBattle(): Promise<void> {
    if (this.streams?.omniscient?.writeEnd) {
      await this.streams.omniscient.writeEnd();
    }
    this.battleStream = null;
    this.streams = null;
    this.players = null;
    this.noteStateChange();
  }

  private async listenSpectator(): Promise<void> {
    if (!this.streams) {
      return;
    }
    for await (const chunk of this.streams.spectator as unknown as AsyncIterable<string>) {
      for (const line of chunk.split('\n')) {
        const trimmed = line.trim();
        if (trimmed) {
          this.logLines.push(trimmed);
        }
      }
      this.noteStateChange();
    }
  }

  private async waitForStateChange(): Promise<void> {
    if (this.lastError) {
      throw this.lastError;
    }
    await new Promise<void>((resolve) => this.stateWaiters.push(resolve));
    if (this.lastError) {
      throw this.lastError;
    }
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
      requests[player] = this.players?.[player].getRequest() || null;
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
    this.ensureReady();
    while (true) {
      if (this.isTerminated() || this.hasPendingExternalDecision()) {
        return this.buildStepResult(options);
      }
      await this.waitForStateChange();
    }
  }
}

export class EnvironmentManager {
  private readonly envs = new Map<string, LocalBattleEnv>();
  private nextId = 1;

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

  async closeEnv(envId: string): Promise<{ env_id: string; closed: true }> {
    const env = this.requireEnv(envId);
    await env.close();
    this.envs.delete(envId);
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
  }

  private requireEnv(envId: string): LocalBattleEnv {
    const env = this.envs.get(envId);
    if (!env) {
      throw new Error(`Unknown environment ${envId}.`);
    }
    return env;
  }
}
