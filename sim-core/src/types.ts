export const PLAYERS = ['p1', 'p2'] as const;
export const ACTION_SPACE_SIZE = 13;

export type PlayerID = typeof PLAYERS[number];
export type Winner = PlayerID | 'tie' | null;
export type ControllerType = 'external' | 'random' | 'heuristic';
export type ActionKind = 'move' | 'move_tera' | 'switch';

export interface ControllerSpec {
  controller: ControllerType;
}

export interface LegalAction {
  index: number;
  kind: ActionKind;
  choice: string;
  label: string;
  move?: string | null;
  slot?: number | null;
}

export interface LegalActionSet {
  mask: boolean[];
  actions: Array<LegalAction | null>;
  available_indices: number[];
}

export interface RequestMoveView {
  slot: number;
  move: string;
  id: string;
  pp: number;
  maxpp: number;
  target: string;
  disabled: boolean;
  type: string | null;
  category: string | null;
  base_power: number;
  accuracy: number | null;
}

export interface RequestSidePokemonView {
  slot: number;
  ident: string;
  details: string;
  condition: string;
  active: boolean;
  moves: string[];
  stats: Record<string, number>;
  base_ability: string | null;
  ability: string | null;
  item: string | null;
  tera_type: string | null;
  terastallized: boolean;
}

export interface RequestActiveView {
  moves: RequestMoveView[];
  can_terastallize: boolean;
  tera_type: string | null;
  trapped: boolean;
  can_switch: boolean;
}

export interface ChoiceRequestView {
  player: PlayerID;
  wait: boolean;
  team_preview: boolean;
  force_switch: boolean;
  trapped: boolean;
  rqid: number | null;
  active: RequestActiveView | null;
  side: RequestSidePokemonView[];
  legal_actions: LegalActionSet;
  raw: unknown;
}

export interface PokemonView {
  slot: number;
  ident: string;
  name: string;
  species: string;
  details: string;
  active: boolean;
  fainted: boolean;
  hp_text: string | null;
  hp_ratio: number | null;
  status: string | null;
  gender: string | null;
  level: number | null;
  item: string | null;
  ability: string | null;
  base_ability: string | null;
  moves: string[];
  revealed_moves: string[];
  types: string[];
  tera_type: string | null;
  terastallized: boolean;
  stats: Record<string, number>;
  boosts: Record<string, number>;
  volatiles: string[];
  possible_roles: string[];
  possible_moves: string[];
  possible_abilities: string[];
  possible_tera_types: string[];
}

export interface FieldView {
  weather: string | null;
  terrain: string | null;
  pseudo_weather: string[];
  side_conditions: {
    self: Record<string, number>;
    opponent: Record<string, number>;
  };
}

export interface BattleView {
  env_id: string;
  format: string;
  gen: number | null;
  turn: number;
  player: PlayerID;
  opponent: PlayerID;
  terminated: boolean;
  winner: Winner;
  names: Record<PlayerID, string | null>;
  team_size: Record<PlayerID, number>;
  active: {
    self: number | null;
    opponent: number | null;
  };
  field: FieldView;
  self_team: PokemonView[];
  opponent_team: PokemonView[];
}

export interface StepResultOptions {
  view_players?: PlayerID[];
  include_log_delta?: boolean;
  include_possible_roles?: boolean;
}

export interface StepResult {
  env_id: string;
  terminated: boolean;
  winner: Winner;
  rewards: Record<PlayerID, number>;
  requests: Partial<Record<PlayerID, ChoiceRequestView | null>>;
  views: Partial<Record<PlayerID, BattleView>>;
  omniscient: null;
  log_delta: string[];
  info: {
    turn: number;
    format: string;
  };
}

export interface BaselineDecision {
  choice: string;
  action_index: number;
  score: number;
  reason: string;
}

export interface BaselineContext {
  player: PlayerID;
  request: ChoiceRequestView;
  view: BattleView;
}

export function createEmptyLegalActionSet(): LegalActionSet {
  return {
    mask: Array.from({ length: ACTION_SPACE_SIZE }, () => false),
    actions: Array.from({ length: ACTION_SPACE_SIZE }, () => null),
    available_indices: [],
  };
}

export function createEmptyBattleView(envId: string, format: string, player: PlayerID): BattleView {
  return {
    env_id: envId,
    format,
    gen: null,
    turn: 0,
    player,
    opponent: player === 'p1' ? 'p2' : 'p1',
    terminated: false,
    winner: null,
    names: { p1: null, p2: null },
    team_size: { p1: 0, p2: 0 },
    active: { self: null, opponent: null },
    field: {
      weather: null,
      terrain: null,
      pseudo_weather: [],
      side_conditions: {
        self: {},
        opponent: {},
      },
    },
    self_team: [],
    opponent_team: [],
  };
}
