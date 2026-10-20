import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {Battle, Teams} from 'pokemon-showdown';
import {LocalBattleEnv, assertAuthoritativeEnvironment} from '../src/env_manager';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {PipelineIntegrationSession, validatePipelineEpisodeRecordBundle} from '../src/pipeline_integration';
import {OriginalOwnerCreation} from '../src/original_owner_provider';
import {NativeBirthEnrollment, NativeObjectAssociation, assertBeliefForkPolicy, snapshotRestorePolicy} from '../src/owner_identity_crosswalk';
import {NativeOwnerKnowledgeController} from '../src/native_owner_knowledge';
import {OwnedRequestHealthHost} from '../src/owned_request_health';
import {OwnedDecisionInputController} from '../src/owned_decision_input';
import {RequestDeliveryLedger} from '../src/request_delivery_ledger';
import {installedNativeProfile} from '../src/version_profile';
import {simulationEnv} from './helpers/simulation_env';

const options = {id: 'simulation', format: 'gen9randombattle', seed: [1, 2, 3, 4]};
const denied = /simulation-only\/v1\/no-authority/;
function battle(): Battle {
  return new Battle({formatid: options.format, seed: '1,2,3,4',
    p1: {name: 'One', team: Teams.import('Pikachu\nAbility: Static\n- Splash\n\nBlissey\nAbility: Natural Cure\n- Splash')!},
    p2: {name: 'Two', team: Teams.import('Magikarp\nAbility: Swift Swim\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash')!}});
}

test('simulation-only raw restore preserves addressed requests, public views and canonical actions', async () => {
  const source = battle();
  const {env, result} = await simulationEnv(source, options);
  try {
    assert.equal(result.authority, 'simulation-only');
    assert.equal(result.omniscient, null);
    for (const owner of ['p1', 'p2'] as const) {
      const request = result.requests[owner]!;
      assert.equal(request.player, owner);
      assert.deepEqual(request.side.map(p => p.details.split(',')[0]), owner === 'p1' ? ['Pikachu', 'Blissey'] : ['Magikarp', 'Snorlax']);
      assert.equal(result.views[owner]!.opponent_team.length, 1);
      assert.deepEqual(result.views[owner]!.opponent_team[0].moves, []);
      assert.ok(!JSON.stringify(request).includes(owner === 'p1' ? 'Snorlax' : 'Blissey'));
    }
    assert.ok(result.log_delta.every(line => !line.startsWith('|request|')));
    const addressed = await env.stepWithOptions({}, {view_players: ['p1'], include_log_delta: false});
    assert.deepEqual(Object.keys(addressed.requests), ['p1']);
    assert.deepEqual(Object.keys(addressed.views), ['p1']);
    const actions = Object.fromEntries((['p1', 'p2'] as const).map(owner => [owner,
      canonicalActionFromLegalAction(result.requests[owner]!, result.requests[owner]!.legal_actions.available_indices[0])]));
    const next = await env.stepWithCanonicalOptions(actions);
    assert.equal(next.authority, 'simulation-only');
    assert.equal(next.info.turn, 2);
    assert.equal((await env.resetFromSerialized(env.serializeBattle())).authority, 'simulation-only');
  } finally { source.destroy(); await env.close(); }
});

test('simulation-only blocks every authority entry and cannot enroll authority hosts', async () => {
  const env = LocalBattleEnv.createSimulationOnly(options);
  const originals = new OriginalOwnerCreation({battle_id: 'sim', format: options.format, simulator_revision: 'sim'});
  const birth = new NativeBirthEnrollment(originals), association = new NativeObjectAssociation(birth);
  const health = new OwnedRequestHealthHost(birth, association);
  const knowledge = new NativeOwnerKnowledgeController(originals, installedNativeProfile(), {p1: {}, p2: {}});
  const ledger = new RequestDeliveryLedger();
  for (const operation of [
    () => assertAuthoritativeEnvironment(env),
    () => env.captureSeededSnapshot(),
    () => env.getLiveWorldOccurrence(),
    () => env.inspectStagedOriginalOwner('p1'),
    () => env.getRequestEmissionTraceHandle('p1'),
    () => env.inspectRequestEmissionTrace({} as any, 'p1'),
    () => originals.bind(env), () => birth.bind(env), () => association.bindInitial(env),
    () => association.prepareRestore(env, {} as any, {} as any),
    () => association.assertRestoreAdmission(env, {}),
    () => health.decode(env, {}, () => { throw new Error('must not decode'); }),
    () => health.prepare(env, {} as any, ledger, {}),
    () => knowledge.prepare(env, {} as any, null),
    () => ledger.prepare(env, {} as any, {} as any, null),
    () => ledger.restored(env, {} as any, {} as any),
    () => new OwnedDecisionInputController().issue({environment: env} as any, () => [], () => {}),
  ]) assert.throws(operation, denied);
  const controller = new OwnedDecisionInputController();
  const control = new LocalBattleEnv('order-control', options.format, options.seed);
  try {
    const frame = {owner: 'p1', environment: control, observation: {}, knowledge: {}, action_context: {}, legal_indices: [0]} as any;
    const order = controller.issue(frame, () => [0], () => {});
    assert.throws(() => controller.issue({...frame, environment: env}, () => [0], () => {}), denied);
    assert.throws(() => controller.assertBatch([order], ['p1'], () => {}), /foreign-or-stale-order/);
  } finally { await control.close(); }
  await env.close();
});

test('authoritative sessions cannot wrap a simulation-only env or expose its authority', async () => {
  const prototype = PipelineIntegrationSession.prototype as any;
  const original = prototype.newEnvironment;
  const env = LocalBattleEnv.createSimulationOnly(options);
  try {
    prototype.newEnvironment = () => env;
    await assert.rejects(PipelineIntegrationSession.create({battle_id: 'wrapped', format: options.format, seed: options.seed}), denied);
  } finally { prototype.newEnvironment = original; await env.close(); }
  const session = await PipelineIntegrationSession.create({battle_id: 'guarded', format: options.format, seed: options.seed});
  const authoritative = (session as any).environment;
  (session as any).environment = env;
  try {
    for (const operation of [
      () => session.boundary, () => session.getOriginalOwnerHolding('p1'),
      () => session.readOriginalOwnerHolding({} as any, 'p1'),
      () => session.getNativeBirthHolding('p1'), () => session.readNativeBirthHolding({} as any, 'p1'),
      () => session.getNativeObjectHolding('p1'), () => session.readNativeObjectHolding({} as any, 'p1'),
      () => session.getOwnerKnowledgeHandle({}), () => session.readOwnerKnowledge({} as any, {}),
      () => session.getRequestDeliveryHandle('p1'), () => session.getSwitchEventHolding('p1'),
      () => session.withOwnedDecisionInput({}, () => []),
    ]) assert.throws(operation, denied);
  } finally { (session as any).environment = authoritative; await session.close(); }
});

test('simulation-only result markers cannot enter TS or Python episode bundles', async () => {
  const root = path.resolve(__dirname, '../../..');
  const fixture = JSON.parse(readFileSync(path.join(root, 'docs/planning/perspective-fidelity-prompt31-reader-fixtures.json'), 'utf8')).bundle;
  validatePipelineEpisodeRecordBundle(fixture);
  const source = battle();
  const {env: simulation, result} = await simulationEnv(source, options);
  try {
    for (const bundle of [{...fixture, authority: result.authority}, {...fixture, transition: {...fixture.transition, result}}]) {
      assert.throws(() => validatePipelineEpisodeRecordBundle(bundle), denied);
      const env: NodeJS.ProcessEnv = {...process.env, PYTHONPATH: path.join(root, 'trainer/src')};
      delete env.PYTHONUTF8; delete env.PYTHONIOENCODING;
      const checked = spawnSync('D:\\Anaconda\\envs\\neuralgpu\\python.exe', ['-m', 'neural.pipeline_record'], {env, input: JSON.stringify(bundle), encoding: 'utf8', timeout: 15000});
      assert.equal(checked.status, 2, checked.stderr);
      assert.equal(checked.stdout, '');
      assert.match(checked.stderr, denied);
    }
  } finally { source.destroy(); await simulation.close(); }
});

test('authoritative raw admission and simulation snapshot metadata validation stay strict', async () => {
  const source = battle(), raw = source.toJSON();
  const authoritative = new LocalBattleEnv('auth', options.format, options.seed);
  const {env} = await simulationEnv(raw, options);
  try {
    assert.equal(snapshotRestorePolicy('0.11.11'), 'held-b2-required');
    assert.throws(() => assertBeliefForkPolicy('0.11.11'), /belief-fork-unsupported/);
    await assert.rejects(authoritative.resetFromSerialized(raw), /raw-restore-unsupported/);
    const before = env.serializeBattle();
    await assert.rejects(env.resetFromSerialized({...raw, __neural_terminal_request_history: {schema_version: 'unknown'}}), /terminal request history schema/);
    await assert.rejects(env.resetFromSerialized({...raw, __neural_active_request_overrides: {schema_version: 'unknown'}}), /active request override/i);
    assert.deepEqual(env.serializeBattle(), before);
    assert.throws(() => env.captureSeededSnapshot(), denied);
    await assert.rejects(env.stepSeededForcedSwitch({} as any), denied);
    await assert.rejects(env.stepSeededTransition({} as any), denied);
    const generated = await authoritative.reset();
    assert.ok(!Object.hasOwn(generated, 'authority'));
    assert.match(authoritative.captureSeededSnapshot().state_fingerprint, /^[a-f0-9]{64}$/);
  } finally { source.destroy(); await env.close(); await authoritative.close(); }
});
