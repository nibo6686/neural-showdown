import assert from 'node:assert/strict';
import test from 'node:test';
import {Teams} from 'pokemon-showdown';
import {LocalBattleEnv} from '../src/env_manager';
import {NativeObjectAssociation} from '../src/owner_identity_crosswalk';
import {bornSession, playTo, withBornTeams} from './helpers/born_session';
import {simulationSnapshotEnv} from './helpers/simulation_env';
import {assertAuthoritativeEnvironment} from '../src/env_manager';
import {rejectSimulationOnlyPayload} from '../src/simulation_authority';

const teams = {
  p1: 'Holder (Snorlax) @ Sitrus Berry\nEVs: 4 HP\nAbility: Immunity\n- Belly Drum\n- Splash',
  p2: 'Watcher (Giratina)\nAbility: Pressure\n- Splash',
};

test('diagnostic simulation snapshots retain the no-authority boundary', async () => {
  const env = simulationSnapshotEnv({id: 'diagnostic-only', format: 'gen9randombattle', seed: [1, 2, 3, 4]});
  try {
    await env.reset();
    const snapshot = env.captureSeededSnapshot();
    assert.throws(() => assertAuthoritativeEnvironment(env), /simulation-only\/v1\/no-authority/);
    assert.throws(() => rejectSimulationOnlyPayload(snapshot), /simulation-only\/v1\/no-authority/);
    assert.deepEqual(snapshot.simulator_state, env.serializeBattle());
  } finally {await env.close();}
});

test('born session preserves original owners and scripts legal play through held restore tickets', async () => {
  const generate = Teams.generate;
  const session = await bornSession({teams, options: {battle_id: 'born-helper', observation_schema_version: 'observable-battle-state/v2'}});
  const restore = LocalBattleEnv.prototype.resetFromSerialized;
  const prepare = NativeObjectAssociation.prototype.prepareRestore;
  let prepared = 0, restored = 0;
  NativeObjectAssociation.prototype.prepareRestore = function (...args) {prepared++; return prepare.apply(this, args);};
  LocalBattleEnv.prototype.resetFromSerialized = async function (snapshot, options, ticket) {
    assert.ok(ticket);
    await assert.rejects(restore.call(this, structuredClone(snapshot), options, ticket), /restore-admission-mismatch/);
    const result = await restore.call(this, snapshot, options, ticket);
    restored++;
    await assert.rejects(restore.call(this, snapshot, options, ticket), /restore-admission-mismatch/);
    return result;
  };
  try {
    assert.equal(Teams.generate, generate);
    const originals = (['p1', 'p2'] as const).map(owner => session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner));
    await playTo(session, [{p1: 'move 1', p2: 'move 1'}, {p1: 'move 2', p2: 'move 1'}]);
    assert.equal(prepared, 2); assert.equal(restored, 2);
    assert.equal(session.boundary.step_index, 2);
    assert.equal(session.boundary.perspectives.p1.observation.view.self_team[0].item, null);
    for (const [i, owner] of (['p1', 'p2'] as const).entries()) {
      assert.equal(session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner), originals[i]);
      assert.throws(() => session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner === 'p1' ? 'p2' : 'p1'), /foreign/);
    }
    const before = session.boundary;
    await assert.rejects(playTo(session, [{p1: 'move 2', p2: 'switch 6'}]), /switch 6 legal for p2/);
    assert.equal(session.boundary, before);
  } finally {
    LocalBattleEnv.prototype.resetFromSerialized = restore;
    NativeObjectAssociation.prototype.prepareRestore = prepare;
    await session.close();
  }
});

test('born team override restores the generator on failed creation and leaves caller teams untouched', async () => {
  const generate = Teams.generate;
  const supplied = {p1: Teams.import(teams.p1)!, p2: Teams.import(teams.p2)!};
  const original = structuredClone(supplied);
  await assert.rejects(withBornTeams(supplied, async () => {
    const own = Teams.generate('gen9randombattle');
    own[0].moves[0] = 'explosion';
    throw new Error('creation failed');
  }), /creation failed/);
  assert.equal(Teams.generate, generate);
  assert.deepEqual(supplied, original);
  const session = await bornSession({teams, seed: [5, 6, 7, 8], options: {battle_id: 'born-helper-retry'}});
  try {
    assert.equal(session.boundary.perspectives.p1.observation.view.self_team[0].name, 'Holder');
    assert.equal(session.boundary.perspectives.p2.observation.view.self_team[0].name, 'Watcher');
  } finally {await session.close();}
});

for (const owner of ['p1', 'p2'] as const) test(`born script handles forced and revival selections for ${owner}`, async () => {
  const other = owner === 'p1' ? 'p2' : 'p1';
  const own = 'First (Snorlax)\nAbility: Immunity\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash';
  const session = await bornSession({teams: {p1: owner === 'p1' ? own : teams.p2, p2: owner === 'p2' ? own : teams.p2},
    options: {battle_id: `born-selection-${owner}`, observation_schema_version: 'observable-battle-state/v2'}});
  try {
    const history = await playTo(session, [{[owner]: 'move 1', [other]: 'move 1'}, {[owner]: 'switch 2'},
      {[owner]: 'move 1', [other]: 'move 1'}, {[owner]: 'switch 2'}]);
    assert.deepEqual(history.map(boundary => boundary.kind), ['joint_actionable', 'one_sided_forced_switch',
      'joint_actionable', 'one_sided_revival', 'joint_actionable']);
    assert.equal(session.boundary.perspectives[owner].observation.view.self_team.find(row => row.name === 'First')!.fainted, false);
  } finally {await session.close();}
});
