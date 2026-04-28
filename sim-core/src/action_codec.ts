import { Dex, toID } from 'pokemon-showdown';
import { ACTION_SPACE_SIZE, createEmptyLegalActionSet, type ChoiceRequestView, type LegalAction, type LegalActionSet, type PlayerID, type RequestActiveView, type RequestMoveView, type RequestSidePokemonView } from './types';
import { isFainted } from './battle_helpers';

function normalizeMove(move: any, slot: number): RequestMoveView {
  const dexMove = Dex.moves.get(move?.move || '');
  return {
    slot,
    move: move?.move || `move-${slot}`,
    id: move?.id || toID(move?.move || `move-${slot}`),
    pp: Number.isFinite(move?.pp) ? move.pp : 0,
    maxpp: Number.isFinite(move?.maxpp) ? move.maxpp : 0,
    target: move?.target || 'normal',
    disabled: !!move?.disabled,
    type: dexMove.exists ? dexMove.type : null,
    category: dexMove.exists ? dexMove.category : null,
    base_power: dexMove.exists ? dexMove.basePower : 0,
    accuracy: dexMove.exists && typeof dexMove.accuracy === 'number' ? dexMove.accuracy : null,
  };
}

function normalizeSidePokemon(pokemon: any, slot: number): RequestSidePokemonView {
  return {
    slot,
    ident: pokemon?.ident || '',
    details: pokemon?.details || '',
    condition: pokemon?.condition || '',
    active: !!pokemon?.active,
    moves: Array.isArray(pokemon?.moves) ? [...pokemon.moves] : [],
    stats: { ...(pokemon?.stats || {}) },
    base_ability: pokemon?.baseAbility || null,
    ability: pokemon?.ability || null,
    item: pokemon?.item || null,
    tera_type: pokemon?.teraType || null,
    terastallized: !!pokemon?.terastallized,
  };
}

function buildSwitchActions(sidePokemon: RequestSidePokemonView[], set: LegalActionSet): void {
  const availableBench = sidePokemon
    .filter((pokemon) => !pokemon.active && !isFainted(pokemon.condition))
    .slice(0, 5);

  for (const [benchIndex, pokemon] of availableBench.entries()) {
    const index = 8 + benchIndex;
    const action: LegalAction = {
      index,
      kind: 'switch',
      choice: `switch ${pokemon.slot}`,
      label: `switch:${pokemon.details || pokemon.ident || pokemon.slot}`,
      slot: pokemon.slot,
    };
    set.mask[index] = true;
    set.actions[index] = action;
  }
}

function ensureNonEmptyActionSet(set: LegalActionSet): void {
  set.available_indices = set.mask.flatMap((enabled, index) => (enabled ? [index] : []));
  if (set.available_indices.length > 0) {
    return;
  }

  const fallback: LegalAction = {
    index: 0,
    kind: 'move',
    choice: 'default',
    label: 'default',
    move: null,
    slot: null,
  };
  set.mask[0] = true;
  set.actions[0] = fallback;
  set.available_indices = [0];
}

function removeChoiceFromActionSet(set: LegalActionSet, choice: string): LegalActionSet {
  const next: LegalActionSet = {
    mask: [...set.mask],
    actions: set.actions.map((action) => (action ? { ...action } : null)),
    available_indices: [...set.available_indices],
  };

  for (const action of next.actions) {
    if (!action || action.choice !== choice) {
      continue;
    }
    next.mask[action.index] = false;
    next.actions[action.index] = null;
  }

  ensureNonEmptyActionSet(next);
  return next;
}

export function buildLegalActionSet(rawRequest: any): LegalActionSet {
  const set = createEmptyLegalActionSet();

  if (!rawRequest || rawRequest.wait || rawRequest.teamPreview) {
    return set;
  }

  const sidePokemon = Array.isArray(rawRequest.side?.pokemon)
    ? rawRequest.side.pokemon.map((pokemon: any, index: number) => normalizeSidePokemon(pokemon, index + 1))
    : [];

  if (Array.isArray(rawRequest.forceSwitch) && rawRequest.forceSwitch.some(Boolean)) {
    buildSwitchActions(sidePokemon, set);
    ensureNonEmptyActionSet(set);
    return set;
  }

  const active = rawRequest.active?.[0];
  if (!active) {
    ensureNonEmptyActionSet(set);
    return set;
  }

  const moves = Array.isArray(active.moves)
    ? active.moves.map((move: any, index: number) => normalizeMove(move, index + 1))
    : [];

  const teraAlreadyUsed = sidePokemon.some((pokemon: RequestSidePokemonView) => pokemon.terastallized);
  const canTerastallize = !!active.canTerastallize && !teraAlreadyUsed;

  for (const move of moves.slice(0, 4)) {
    if (move.disabled || move.pp <= 0) {
      continue;
    }

    const baseAction: LegalAction = {
      index: move.slot - 1,
      kind: 'move',
      choice: `move ${move.slot}`,
      label: `move:${move.move}`,
      move: move.move,
      slot: move.slot,
    };
    set.mask[baseAction.index] = true;
    set.actions[baseAction.index] = baseAction;

    if (canTerastallize) {
      const teraIndex = move.slot - 1 + 4;
      const teraAction: LegalAction = {
        index: teraIndex,
        kind: 'move_tera',
        choice: `move ${move.slot} terastallize`,
        label: `move_tera:${move.move}`,
        move: move.move,
        slot: move.slot,
      };
      set.mask[teraIndex] = true;
      set.actions[teraIndex] = teraAction;
    }
  }

  if (!active.trapped) {
    buildSwitchActions(sidePokemon, set);
  }

  ensureNonEmptyActionSet(set);
  return set;
}

export function normalizeRequest(player: PlayerID, rawRequest: any): ChoiceRequestView {
  const side = Array.isArray(rawRequest?.side?.pokemon)
    ? rawRequest.side.pokemon.map((pokemon: any, index: number) => normalizeSidePokemon(pokemon, index + 1))
    : [];

  const rawActive = rawRequest?.active?.[0];
  const teraAlreadyUsed = side.some((pokemon: RequestSidePokemonView) => pokemon.terastallized);
  const active: RequestActiveView | null = rawActive ? {
    moves: Array.isArray(rawActive.moves)
      ? rawActive.moves.map((move: any, index: number) => normalizeMove(move, index + 1))
      : [],
    can_terastallize: !!rawActive.canTerastallize && !teraAlreadyUsed,
    tera_type: typeof rawActive.canTerastallize === 'string' ? rawActive.canTerastallize : null,
    trapped: !!rawActive.trapped,
    can_switch: !rawActive.trapped && side.some((pokemon: RequestSidePokemonView) => !pokemon.active && !isFainted(pokemon.condition)),
  } : null;

  return {
    player,
    wait: !!rawRequest?.wait,
    team_preview: !!rawRequest?.teamPreview,
    force_switch: Array.isArray(rawRequest?.forceSwitch) && rawRequest.forceSwitch.some(Boolean),
    trapped: !!rawActive?.trapped,
    rqid: Number.isFinite(rawRequest?.rqid) ? rawRequest.rqid : null,
    active,
    side,
    legal_actions: buildLegalActionSet(rawRequest),
    raw: rawRequest ?? null,
  };
}

export function actionIndexToChoice(request: ChoiceRequestView, actionIndex: number): string | null {
  if (actionIndex < 0 || actionIndex >= ACTION_SPACE_SIZE) {
    return null;
  }

  return request.legal_actions.actions[actionIndex]?.choice || null;
}

export function cloneChoiceRequest(request: ChoiceRequestView): ChoiceRequestView {
  return {
    ...request,
    side: request.side.map((pokemon) => ({ ...pokemon, stats: { ...pokemon.stats }, moves: [...pokemon.moves] })),
    active: request.active
      ? {
          ...request.active,
          moves: request.active.moves.map((move) => ({ ...move })),
        }
      : null,
    legal_actions: {
      mask: [...request.legal_actions.mask],
      actions: request.legal_actions.actions.map((action) => (action ? { ...action } : null)),
      available_indices: [...request.legal_actions.available_indices],
    },
  };
}

export function removeChoiceFromRequest(request: ChoiceRequestView, choice: string | null): ChoiceRequestView {
  const next = cloneChoiceRequest(request);
  if (!choice) {
    return next;
  }
  next.legal_actions = removeChoiceFromActionSet(next.legal_actions, choice);
  return next;
}
