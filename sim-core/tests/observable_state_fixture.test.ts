import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {
  ObservableStateProjector,
  projectObservableBattleState,
  type ObservableStateInput,
} from '../src/observable_state';
import { createEmptyBattleView, type PokemonView, type RequestActiveView, type RequestSidePokemonView } from '../src/types';
import { OBSERVABLE_STATE_SCHEMA_VERSION } from '../src/observable_state';

type FixtureCase = {
  name: string;
  input: {
    protocol_prefix: string[];
    snapshot_phase: string;
    request?: null;
    private_request?: { side: RequestSidePokemonView[]; active: RequestActiveView };
    terminated?: boolean;
    winner?: 'p1' | 'p2' | 'tie';
  };
  expected: {
    schema_version: string;
    source_kind: string;
    battle_id: string;
    perspective: string;
    snapshot_phase: string;
    event_cursor: number;
    protocol_prefix: string[];
    decision_availability: unknown;
    request_assertions?: {
      player: string;
      rqid: number;
      side_slot: number;
      private_move: string;
      private_item: string;
      private_ability: string;
      active_move: string;
    } | null;
    view_assertions?: {
      self_slots: number[];
      opponent_slots: number[];
      self_species: string[];
      opponent_species: string[];
      active: { self: number; opponent: number };
      self_status: string;
      self_hp_ratio: number;
      self_tera_type: string;
      self_transformed: boolean;
      self_illusion_revealed: boolean;
      opponent_fainted: boolean;
    };
  };
};

const fixture = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../../tests/fixtures/observable_state_v1.json'), 'utf8'),
) as {
  fixture_schema: string;
  schema_version: string;
  provenance: { source_kind: string; battle_id: string; description: string };
  cases: FixtureCase[];
  sequences: Array<{ prefixes: string[][]; expected_cursors: number[]; invalid_prefixes?: string[][] }>;
};

function fixtureInput(testCase: FixtureCase, prefix = testCase.input.protocol_prefix): ObservableStateInput {
  const view = createEmptyBattleView('fixture-observable-1', 'gen9randombattle', 'p1');
  view.gen = 9;
  view.turn = 1;
  view.terminated = testCase.input.terminated ?? false;
  view.winner = testCase.input.winner ?? null;
  if (testCase.name === 'decision-cutoff-redacts-private-request') {
    view.opponent_team = [{
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
      possible_roles: [],
      possible_moves: [],
      possible_abilities: [],
      possible_tera_types: [],
    }];
  }
  if (testCase.name === 'battle-events-preserve-ordered-prefix') {
    const hasFaint = prefix.some((record) => record === '|faint|p2a: Eevee');
    const pokemon = (slot: number, ident: string, species: string, overrides: Partial<PokemonView> = {}): PokemonView => ({
      slot,
      ident,
      name: species,
      species,
      base_species: species,
      current_species: species,
      displayed_species: species,
      species_source: 'protocol',
      transformed: false,
      displayed_species_uncertain: false,
      illusion_revealed: false,
      details: `${species}, L80`,
      active: false,
      fainted: false,
      hp_text: '100/100',
      hp_ratio: 1,
      status: null,
      status_source: 'protocol',
      status_started_turn: null,
      status_turns_public: null,
      gender: null,
      level: 80,
      item: null,
      last_item: null,
      item_state: 'none',
      item_suppressed: false,
      ability: null,
      base_ability: null,
      ability_state: 'none',
      ability_suppressed: false,
      moves: [],
      revealed_moves: [],
      types: ['Normal'],
      tera_type: null,
      terastallized: false,
      stats: {},
      boosts: {},
      volatiles: [],
      possible_roles: [],
      possible_moves: [],
      possible_abilities: [],
      possible_tera_types: [],
      ...overrides,
    });
    view.active = { self: 2, opponent: 3 };
    view.self_team = [
      pokemon(2, 'p1a: Zoroark', 'Zoroark', { active: true, status: 'brn', hp_text: '75/100', hp_ratio: 0.75, current_species: 'Pikachu', displayed_species: 'Pikachu', transformed: true, illusion_revealed: true, tera_type: 'Water', terastallized: true, boosts: { atk: 1 } }),
      pokemon(4, 'p1b: Zoroark', 'Zoroark'),
    ];
    view.opponent_team = [
      pokemon(1, 'p2a: Eevee', 'Eevee'),
      pokemon(3, 'p2b: Eevee', 'Eevee', { active: true, fainted: hasFaint, hp_text: hasFaint ? '0 fnt' : '100/100', hp_ratio: hasFaint ? 0 : 1 }),
    ];
  }
  const base = {
    schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
    source_kind: 'sim_core' as const,
    battle_id: 'fixture-observable-1',
    perspective: 'p1' as const,
    snapshot_phase: testCase.input.snapshot_phase,
    protocol_prefix: prefix,
    view,
    request: null,
  };
  if (testCase.input.request === null) return base;
  return {
    ...base,
    request: {
      player: 'p1',
      wait: false,
      team_preview: false,
      force_switch: false,
      trapped: false,
      rqid: 7,
      active: testCase.input.private_request?.active ?? null,
      side: testCase.input.private_request?.side ?? [],
      legal_actions: {
        mask: [true, ...Array(12).fill(false)],
        actions: [{ index: 0, kind: 'move', choice: 'move 1', label: 'move: Tackle', move: 'Tackle', slot: 1 }, ...Array(12).fill(null)],
        available_indices: [0],
      },
      raw: null,
    },
  } as ObservableStateInput;
}

test('observable-state golden fixtures preserve expected decision-time projections', () => {
  assert.equal(fixture.fixture_schema, 'observable-state-fixtures/v1');
  assert.equal(fixture.schema_version, OBSERVABLE_STATE_SCHEMA_VERSION);
  assert.deepEqual(fixture.provenance, {
    source_kind: 'sim_core',
    battle_id: 'fixture-observable-1',
    description: 'Deterministic protocol-prefix cutoffs for the accepted ObservableBattleState adapter',
  });
  for (const testCase of fixture.cases) {
    const state = projectObservableBattleState(fixtureInput(testCase));
    assert.equal(state.schema_version, testCase.expected.schema_version, testCase.name);
    assert.equal(state.source_kind, testCase.expected.source_kind, testCase.name);
    assert.equal(state.battle_id, testCase.expected.battle_id, testCase.name);
    assert.equal(state.perspective, testCase.expected.perspective, testCase.name);
    assert.equal(state.snapshot_phase, testCase.expected.snapshot_phase, testCase.name);
    assert.equal(state.event_cursor, testCase.expected.event_cursor, testCase.name);
    assert.deepEqual(state.protocol_prefix, testCase.expected.protocol_prefix, testCase.name);
    assert.deepEqual(state.decision_availability, testCase.expected.decision_availability, testCase.name);
    if (testCase.expected.request_assertions) {
      const request = state.request;
      assert.ok(request);
      assert.equal(request.player, testCase.expected.request_assertions.player);
      assert.equal(request.rqid, testCase.expected.request_assertions.rqid);
      assert.equal(request.side[0]?.slot, testCase.expected.request_assertions.side_slot);
      assert.equal(request.side[0]?.moves[0], testCase.expected.request_assertions.private_move);
      assert.equal(request.side[0]?.item, testCase.expected.request_assertions.private_item);
      assert.equal(request.side[0]?.ability, testCase.expected.request_assertions.private_ability);
      assert.equal(request.active?.moves[0]?.move, testCase.expected.request_assertions.active_move);
      assert.doesNotMatch(JSON.stringify(state.protocol_prefix), /SecretMove|SecretItem|SecretAbility/);
      assert.doesNotMatch(JSON.stringify(state.view.opponent_team), /SecretMove|SecretItem|SecretAbility/);
    } else if (testCase.expected.request_assertions === null) {
      assert.equal(state.request, null);
    }
    if (testCase.expected.view_assertions) {
      const assertions = testCase.expected.view_assertions;
      assert.deepEqual(state.view.self_team.map((pokemon) => pokemon.slot), assertions.self_slots);
      assert.deepEqual(state.view.opponent_team.map((pokemon) => pokemon.slot), assertions.opponent_slots);
      assert.deepEqual(state.view.self_team.map((pokemon) => pokemon.species), assertions.self_species);
      assert.deepEqual(state.view.opponent_team.map((pokemon) => pokemon.species), assertions.opponent_species);
      assert.deepEqual(state.view.active, assertions.active);
      assert.equal(state.view.self_team[0]?.status, assertions.self_status);
      assert.equal(state.view.self_team[0]?.hp_ratio, assertions.self_hp_ratio);
      assert.equal(state.view.self_team[0]?.tera_type, assertions.self_tera_type);
      assert.equal(state.view.self_team[0]?.transformed, assertions.self_transformed);
      assert.equal(state.view.self_team[0]?.illusion_revealed, assertions.self_illusion_revealed);
      assert.equal(state.view.opponent_team[1]?.fainted, assertions.opponent_fainted);
    }
  }
});

test('observable-state golden fixture sequence requires exact ordered prefix extension', () => {
  for (const sequence of fixture.sequences) {
    const projector = new ObservableStateProjector();
    sequence.prefixes.forEach((prefix, index) => {
      const state = projector.project(fixtureInput(fixture.cases[1], prefix));
      assert.equal(state.event_cursor, sequence.expected_cursors[index]);
    });
    const early = projectObservableBattleState(fixtureInput(fixture.cases[1], sequence.prefixes[1]));
    const later = projectObservableBattleState(fixtureInput(fixture.cases[1], sequence.prefixes[2]));
    assert.equal(early.protocol_prefix.includes('|faint|p2a: Eevee'), false);
    assert.equal(later.protocol_prefix.includes('|faint|p2a: Eevee'), true);
    assert.equal(early.view.opponent_team[1]?.fainted, false);
    assert.equal(later.view.opponent_team[1]?.fainted, true);
    const invalidProjector = new ObservableStateProjector();
    invalidProjector.project(fixtureInput(fixture.cases[1], sequence.prefixes[1]));
    for (const invalid of sequence.invalid_prefixes ?? []) {
      assert.throws(() => invalidProjector.project(fixtureInput(fixture.cases[1], invalid)));
    }
  }
});
