import assert from 'node:assert/strict';
import test from 'node:test';
import {
  assertTypedStateMatchesPublicPrefix,
  PUBLIC_TYPED_STATE_LIFECYCLE,
  projectPublicTypedState,
  typedStateLifecycleEntry,
} from '../src/typed_state_lifecycle';

const switchLine = '|switch|p1a: Donor|Cyclizar, L80|100/100';

test('the pinned lifecycle atlas classifies every volatile and side condition through equivalence classes', () => {
  const contract = PUBLIC_TYPED_STATE_LIFECYCLE;
  const rows = contract.entries;
  assert.equal(rows.filter((entry: any) => entry.family === 'move_volatile').length, 88);
  assert.equal(rows.filter((entry: any) => entry.family === 'side_condition').length, 23);
  assert.deepEqual(rows.filter((entry: any) => entry.family === 'move_volatile' && entry.disposition === 'evidence-derived-typed')
    .map((entry: any) => entry.id), ['substitute']);
  assert.deepEqual(rows.filter((entry: any) => entry.family === 'side_condition' && entry.disposition === 'evidence-derived-typed')
    .map((entry: any) => entry.id).sort(), [
    'auroraveil', 'lightscreen', 'reflect', 'spikes', 'stealthrock', 'stickyweb', 'tailwind', 'toxicspikes',
  ]);
  assert.equal(typedStateLifecycleEntry('side_condition', 'matblock')?.disposition, 'unsupported-fail-closed');
  assert.equal(typedStateLifecycleEntry('move_volatile', 'confusion')?.disposition, 'raw-only');
});

test('prefix replay handles Substitute start/end, silent switch clear, Shed Tail-only transfer, faint, and terminal', () => {
  const prefix = [
    switchLine,
    '|-start|p1a: Donor|Substitute|[from] move: Shed Tail',
    '|switch|p1a: Receiver|Snorlax, L80|100/100|[from] Shed Tail',
    '|-end|p1a: Receiver|Substitute',
    '|-start|p1a: Receiver|Substitute',
    '|drag|p1a: Bench|Eevee, L80|100/100',
    '|switch|p1a: Receiver|Snorlax, L80|100/100',
    '|-start|p1a: Receiver|Substitute',
    '|faint|p1a: Receiver',
    '|tie',
  ];
  const projected = projectPublicTypedState(prefix);
  assert.deepEqual(projected.volatiles_by_ident['p1: Donor'], []);
  assert.deepEqual(projected.volatiles_by_ident['p1: Receiver'], []);
  assert.deepEqual(projected.volatiles_by_ident['p1: Bench'], []);
});

test('nonempty prefix-derived volatile state requires one canonical row on the owning perspective roster', () => {
  const prefix = [switchLine, '|-start|p1a: Donor|Substitute'];
  const view = {
    self_team: [{ ident: 'p1: Donor', volatiles: ['substitute'] }],
    opponent_team: [{ ident: 'p2: Foe', volatiles: [] }],
    field: { side_conditions: { self: {}, opponent: {} } },
  };
  assert.doesNotThrow(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', view));
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', {
    ...view, self_team: [],
  }), /exactly one canonical self_team roster row/);
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', {
    ...view, self_team: [...view.self_team, { ...view.self_team[0] }],
  }), /exactly one canonical self_team roster row/);
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', {
    ...view, self_team: [], opponent_team: [...view.opponent_team, { ident: 'p1: Donor', volatiles: ['substitute'] }],
  }), /exactly one canonical self_team roster row/);
});

test('partial containers and a missing perspective are compatible only when replay derives no typed value', () => {
  assert.doesNotThrow(() => assertTypedStateMatchesPublicPrefix([], 'p1', {}));
  const prefix = [switchLine, '|-start|p1a: Donor|Substitute'];
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', { field: {} } as any),
    /exactly one canonical self_team roster row/);
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, undefined as any, {
    self_team: [{ ident: 'p1: Donor', volatiles: ['substitute'] }],
  }), /derived typed state requires a valid perspective/);
});

test('prefix replay validates layered hazards, caps, presence screens, removal, and Court Change', () => {
  const prefix = [
    '|-sidestart|p1: One|Spikes',
    '|-sidestart|p1: One|Spikes',
    '|-sidestart|p1: One|Toxic Spikes',
    '|-sidestart|p1: One|Reflect',
    '|-sidestart|p2: Two|Tailwind',
    '|-sideend|p1: One|Spikes',
    '|-swapsideconditions',
  ];
  const projected = projectPublicTypedState(prefix);
  assert.deepEqual(projected.side_conditions_by_player.p1, { tailwind: 1 });
  assert.deepEqual(projected.side_conditions_by_player.p2, { reflect: 1, toxicspikes: 1 });
  assert.throws(() => projectPublicTypedState([...prefix.slice(0, 2), '|-sidestart|p1: One|Spikes', '|-sidestart|p1: One|Spikes']), /layer cap/);
  assert.throws(() => projectPublicTypedState(['|-sidestart|p1: One|Reflect', '|-sidestart|p1: One|Reflect']), /duplicate reflect presence/);
  assert.throws(() => projectPublicTypedState(['|-sideend|p1: One|Reflect']), /ends without a public start/);
});

test('each perspective checks its own active typed maps while raw-only evidence stays untyped and unsupported evidence fails closed', () => {
  const prefix = [
    switchLine,
    '|switch|p2a: Opponent|Mew, L80|100/100',
    '|-start|p1a: Donor|confusion',
    '|-sidestart|p1: One|Spikes',
    '|-sidestart|p2: Two|Reflect',
    '|-swapsideconditions',
  ];
  const teams = {
    p1: [{ ident: 'p1: Donor', volatiles: [] }],
    p2: [{ ident: 'p2: Opponent', volatiles: [] }],
  };
  const view = (perspective: 'p1' | 'p2'): {
    self_team: { ident: string; volatiles: string[] }[];
    opponent_team: { ident: string; volatiles: string[] }[];
    field: { side_conditions: { self: Record<string, number>; opponent: Record<string, number> } };
  } => ({
    self_team: teams[perspective],
    opponent_team: teams[perspective === 'p1' ? 'p2' : 'p1'],
    field: { side_conditions: perspective === 'p1'
      ? { self: { reflect: 1 }, opponent: { spikes: 1 } }
      : { self: { spikes: 1 }, opponent: { reflect: 1 } } },
  });
  assertTypedStateMatchesPublicPrefix(prefix, 'p1', view('p1'));
  assertTypedStateMatchesPublicPrefix(prefix, 'p2', view('p2'));
  assert.throws(() => projectPublicTypedState(['|-sidestart|p1: One|Mat Block']), /unsupported-fail-closed/);
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', {
    ...view('p1'), self_team: [{ ident: 'p1a: Donor', volatiles: ['confusion'] }],
  }), /volatile map disagrees/);
  assert.throws(() => assertTypedStateMatchesPublicPrefix(prefix, 'p1', {
    ...view('p1'), field: { side_conditions: { self: { reflect: 1, matblock: 1 }, opponent: { spikes: 1 } } },
  }), /side-condition map disagrees/);
});
