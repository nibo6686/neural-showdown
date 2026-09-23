import assert from 'node:assert/strict';
import test from 'node:test';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION,
  ObservableStateProjector,
  projectObservableBattleState,
  type ObservableStateInput,
} from '../src/observable_state';
import {
  createEmptyBattleView,
  createEmptyLegalActionSet,
  type BattleView,
  type ChoiceRequestView,
} from '../src/types';

function input(overrides: Partial<ObservableStateInput> = {}): ObservableStateInput {
  const view = createEmptyBattleView('env-1', 'gen9randombattle', 'p1');
  view.gen = 9;
  view.turn = 1;
  const legalActions = createEmptyLegalActionSet();
  legalActions.mask[0] = true;
  legalActions.actions[0] = {
    index: 0,
    kind: 'move',
    choice: 'move 1',
    label: 'move: Tackle',
    move: 'Tackle',
    slot: 1,
  };
  legalActions.available_indices.push(0);
  const request: ChoiceRequestView = {
    player: 'p1',
    wait: false,
    team_preview: false,
    force_switch: false,
    trapped: false,
    rqid: 7,
    active: null,
    side: [],
    legal_actions: legalActions,
    raw: { secret: 'must-not-cross-boundary' },
  };
  return {
    schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
    source_kind: 'sim_core',
    battle_id: 'battle-1',
    perspective: 'p1',
    snapshot_phase: 'pre_decision',
    protocol_prefix: ['|turn|1', '|request|{"rqid":7}'],
    view,
    request,
    ...overrides,
  };
}

test('observable state hashes normalized protocol prefixes deterministically', () => {
  const first = projectObservableBattleState(input({ protocol_prefix: [' |turn|1\n', '|request|{"rqid":7}'] }));
  const second = projectObservableBattleState(input({ protocol_prefix: ['|turn|1', '|request|{"rqid":7}'] }));
  assert.equal(first.event_cursor, 2);
  assert.equal(first.protocol_prefix_hash, second.protocol_prefix_hash);
  assert.equal(first.observation_id, second.observation_id);
  assert.equal(first.schema_version, OBSERVABLE_STATE_SCHEMA_VERSION);
});

test('observable state projector rejects cursor rollback and same-cursor hash changes', () => {
  const projector = new ObservableStateProjector();
  projector.project(input({ protocol_prefix: ['|move|p1a: Pikachu|Tackle|p2a: Eevee', '|request|{"rqid":7}'] }));
  assert.throws(
    () => projector.project(input({ protocol_prefix: ['|move|p1a: Pikachu|Tackle|p2a: Eevee'] })),
    /event cursor moved backwards/,
  );
  assert.throws(
    () => projector.project(input({
      protocol_prefix: ['|move|p1a: Pikachu|Growl|p2a: Eevee', '|request|{"rqid":7}'],
    })),
    /exact extension/,
  );
});

test('snapshots are immutable and later protocol events cannot alter earlier observations', () => {
  const prefix = ['|turn|1', '|request|{"rqid":7}'];
  const source = input({ protocol_prefix: prefix });
  const earlier = projectObservableBattleState(source);
  (source.protocol_prefix as string[]).push('|move|p1a: Pikachu|Tackle|p2a: Eevee');
  source.view.turn = 2;
  assert.equal(earlier.event_cursor, 2);
  assert.equal(earlier.protocol_prefix.length, 2);
  assert.equal(earlier.view.turn, 1);
  assert.ok(Object.isFrozen(earlier));
  assert.throws(() => ((earlier.protocol_prefix as string[])[0] = '|future|'));
});

test('requestless observations do not invent actions and projection omits hidden fields', () => {
  const source = input({
    request: null,
    snapshot_phase: 'terminal',
    view: { ...input().view, terminated: true } as BattleView,
  });
  const state = projectObservableBattleState(source);
  assert.equal(state.request, null);
  assert.equal(state.decision_availability.available, false);
  assert.equal(state.decision_availability.legal_action_indices, null);
  const encoded = JSON.stringify(state);
  assert.doesNotMatch(encoded, /secret|raw|possible_roles|rewards|omniscient|env_id/);
});

test('invalid perspectives, request-side mismatches, contradictions, and schemas fail closed', () => {
  assert.throws(
    () => projectObservableBattleState(input({ perspective: 'p3' as 'p1' })),
    /Unsupported perspective/,
  );
  assert.throws(
    () => projectObservableBattleState(input({ request: { ...input().request!, player: 'p2' } })),
    /does not match perspective/,
  );
  assert.throws(
    () => projectObservableBattleState(input({ contradictions: ['raw protocol disagrees with derived state'] })),
    /Observable state contradiction/,
  );
  assert.throws(
    () => projectObservableBattleState(input({ schema_version: 'observable-battle-state/v999' })),
    /Unsupported observable state schema/,
  );
});

test('adapter allowlists opponent state for both acting-player perspectives', () => {
  const privatePokemon = {
    slot: 1,
    ident: 'p2a: Secretmon',
    name: 'Secretmon',
    species: 'Secretmon',
    base_species: 'Secretmon',
    current_species: 'Secretmon',
    displayed_species: 'Secretmon',
    species_source: 'protocol',
    transformed: false,
    displayed_species_uncertain: false,
    illusion_revealed: false,
    details: 'Secretmon, L80',
    active: true,
    fainted: false,
    hp_text: '100/100',
    hp_ratio: 1,
    status: null,
    status_source: 'protocol',
    status_started_turn: null,
    status_turns_public: null,
    gender: null,
    level: 80,
    item: 'SecretItem',
    last_item: 'SecretItem',
    item_state: 'held',
    item_suppressed: false,
    ability: 'SecretAbility',
    base_ability: 'SecretAbility',
    ability_state: 'known',
    ability_suppressed: false,
    moves: ['SecretMove'],
    revealed_moves: ['SecretMove'],
    types: ['Normal'],
    tera_type: 'Ghost',
    terastallized: false,
    stats: { hp: 999 },
    boosts: { atk: 6 },
    volatiles: [],
    possible_roles: ['secret-role'],
    possible_moves: ['secret-move'],
    possible_abilities: ['secret-ability'],
    possible_tera_types: ['secret-tera'],
  };
  for (const perspective of ['p1', 'p2'] as const) {
    const view = input().view;
    view.player = perspective;
    view.opponent = perspective === 'p1' ? 'p2' : 'p1';
    view.self_team = [privatePokemon] as BattleView['self_team'];
    view.opponent_team = [privatePokemon] as BattleView['opponent_team'];
    const state = projectObservableBattleState(input({
      perspective,
      request: null,
      protocol_prefix: ['|turn|1'],
      view,
    }));
    const opponent = state.view.opponent_team[0];
    assert.equal('ability' in opponent, false);
    assert.equal('moves' in opponent, false);
    assert.equal('stats' in opponent, false);
    assert.equal('tera_type' in opponent, false);
    assert.doesNotMatch(JSON.stringify(opponent), /SecretItem|SecretAbility|SecretMove|secret-role/);
    assert.equal(state.view.self_team[0].ability, 'SecretAbility');
  }
});

test('runtime phases are validated, normalized, retained, and identity-bearing', () => {
  for (const phase of ['pre_decision', 'post_resolution'] as const) {
    const state = projectObservableBattleState(input({ snapshot_phase: phase }));
    assert.equal(state.snapshot_phase, phase);
    assert.equal(state.other_phase, null);
  }
  assert.notEqual(
    projectObservableBattleState(input({ snapshot_phase: 'pre_decision' })).observation_id,
    projectObservableBattleState(input({ snapshot_phase: 'post_resolution' })).observation_id,
  );
  const forced = projectObservableBattleState(input({
    snapshot_phase: 'forced_switch',
    request: { ...input().request!, force_switch: true },
  }));
  assert.equal(forced.snapshot_phase, 'forced_switch');
  const terminal = projectObservableBattleState(input({
    snapshot_phase: 'terminal',
    request: null,
    view: { ...input().view, terminated: true },
  }));
  assert.equal(terminal.snapshot_phase, 'terminal');
  const unknown = projectObservableBattleState(input({ snapshot_phase: 'between_request_and_resolution' }));
  const other = projectObservableBattleState(input({ snapshot_phase: 'after_effect_resolution' }));
  assert.equal(unknown.snapshot_phase, 'other');
  assert.equal(unknown.other_phase, 'between_request_and_resolution');
  assert.notEqual(unknown.observation_id, other.observation_id);
  for (const malformed of ['', ' pre_decision', 'bad phase', 7 as unknown as string]) {
    assert.throws(() => projectObservableBattleState(input({ snapshot_phase: malformed })), /Malformed snapshot phase/);
  }
});

test('projector requires true exact prefix extension and rejects hash-only evidence', () => {
  const base = ['|turn|1', '|move|p1a: Pikachu|Tackle|p2a: Eevee'];
  const extended = [...base, '|faint|p2a: Eevee'];
  const projector = new ObservableStateProjector();
  projector.project(input({ protocol_prefix: base }));
  assert.equal(projector.project(input({ protocol_prefix: extended })).event_cursor, 3);

  for (const replacement of [
    ['|turn|1', '|move|p1a: Pikachu|Growl|p2a: Eevee'],
    ['|move|p1a: Pikachu|Tackle|p2a: Eevee', '|turn|1', '|faint|p2a: Eevee'],
    ['|turn|1', '|move|p1a: Pikachu|Growl|p2a: Eevee', '|faint|p2a: Eevee'],
  ]) {
    const fresh = new ObservableStateProjector();
    fresh.project(input({ protocol_prefix: base }));
    assert.throws(() => fresh.project(input({ protocol_prefix: replacement })), /exact extension/);
  }
  const rollback = new ObservableStateProjector();
  rollback.project(input({ protocol_prefix: base }));
  assert.throws(() => rollback.project(input({ protocol_prefix: ['|turn|1'] })), /moved backwards/);
  assert.throws(
    () => projectObservableBattleState({ ...input(), protocol_prefix: undefined as unknown as string[] }),
    /protocol_prefix must be an array/,
  );
});

test('raw protocol evidence is independently validated and incomplete evidence remains explicit', () => {
  assert.doesNotThrow(() => projectObservableBattleState(input({
    protocol_prefix: ['|gen|9', '|turn|1', '|request|{"rqid":7}'],
  })));
  assert.throws(
    () => projectObservableBattleState(input({ protocol_prefix: ['|gen|8'] })),
    /Raw evidence disagrees with view.gen/,
  );
  assert.doesNotThrow(() => projectObservableBattleState(input({
    protocol_prefix: ['|move|p1a: Pikachu|Tackle|p2a: Eevee'],
  })));
  assert.throws(
    () => projectObservableBattleState(input({ protocol_prefix: ['|turn|not-a-number'] })),
    /Malformed raw turn record/,
  );
  assert.throws(
    () => projectObservableBattleState(input({ protocol_prefix: ['|request|not-json'] })),
    /Malformed raw request record/,
  );
  assert.throws(
    () => projectObservableBattleState(input({ protocol_prefix: ['|unsupported|evidence'] })),
    /Unsupported raw protocol event/,
  );
  assert.throws(
    () => projectObservableBattleState(input({
      protocol_prefix: ['|request|{"rqid":8}'],
    })),
    /Raw evidence disagrees with request.rqid/,
  );
});
