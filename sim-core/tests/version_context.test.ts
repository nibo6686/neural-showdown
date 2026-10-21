import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { HISTORICAL10_CONTEXT as C, NATIVE11_CONTEXT as N, readerContext, installedNativeProfile, assertNativeRuntimeProfile, NATIVE11, runtimeData } from '../src/version_profile';
import { validatePipelineLinkedRecordBundle, validateHistoricalPipelineLinkedRecordBundle, PipelineIntegrationSession } from '../src/pipeline_integration';
import { validatePipelineEpisodeEvidence } from '../src/pipeline_episode_evidence';
import { validatePipelineEpisodeFaithfulClaim } from '../src/pipeline_episode';
import * as protocol from '../src/protocol_contract';
import * as belief from '../src/belief_state';
import { validateRawProtocolRecord } from '../src/observable_state';
import { projectPublicTypedState } from '../src/typed_state_lifecycle';
import { publicBoostEvidence } from '../src/public_boosts';
import { EnvironmentManager, LocalBattleEnv } from '../src/env_manager';
import { PlayerStateExtractor } from '../src/state_extractor';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
const root = path.resolve(__dirname, '../../..');
const fixtures = JSON.parse(readFileSync(path.join(root, 'docs/planning/perspective-fidelity-prompt31-reader-fixtures.json'), 'utf8'));
const emit = (name: string, data: object) => console.log('P32_WITNESS ' + JSON.stringify({name, ...data}));
const target = { profile: NATIVE11 } as any;

test('P32 historical semantic context', () => {
  const before = JSON.stringify(fixtures);
  const observations: unknown[] = [], calls = (belief as any).validateObservableBattleState;
  (belief as any).validateObservableBattleState = function(value: unknown, context: unknown) { observations.push(context); return calls(value, context); };
  const supported = [...protocol.SUPPORTED_RAW_COMMANDS], old = protocol.PROTOCOL_CONTRACT.validation_rules.player_ident.side_ids;
  try {
    protocol.SUPPORTED_RAW_COMMANDS.clear(); protocol.PROTOCOL_CONTRACT.validation_rules.player_ident.side_ids = ['p9'];
    validatePipelineLinkedRecordBundle(fixtures.bundle, C);
    validateHistoricalPipelineLinkedRecordBundle(fixtures.bundle);
    validatePipelineEpisodeEvidence(fixtures.continuation, undefined, undefined, 0, C);
    assert.equal(validatePipelineEpisodeFaithfulClaim(fixtures.result, C), true);
    assert.ok(observations.length > 8 && observations.every(c => c === C), 'bundle, nested predecessor and result observations retain exact context');
    validateRawProtocolRecord('|turn|1', C);
    validateRawProtocolRecord('|-singlemove|p1a: A|Destiny Bond', C);
    const prefix = ['|switch|p1a: A|Pikachu|100/100', '|-start|p1a: A|Substitute', '|-boost|p1a: A|atk|1'];
    assert.deepEqual(projectPublicTypedState(prefix, C).volatiles_by_ident['p1: A'], ['substitute']);
    assert.equal(publicBoostEvidence(prefix, C).get('p1: A')?.atk, 1);
    assert.throws(() => validatePipelineLinkedRecordBundle(fixtures.bundle, target), /native11-unadopted/);
    assert.throws(() => validateRawProtocolRecord('|turn|1', target), /native11-unadopted/);
    assert.throws(() => readerContext({...C}), /unsupported-context/);
    assert.throws(() => (C.protocol.validation_rules.player_ident.side_ids as any).push('p9'), TypeError);
    validateHistoricalPipelineLinkedRecordBundle(fixtures.bundle);
    assert.equal(JSON.stringify(fixtures), before);
    emit('historical-context', {actual_saved_readers: true, nested_observation_calls: observations.length, exact_context: true,
      legacy_global_mutation_isolated: true, identities_unchanged: true, target_semantics_unproved: true});
  } finally {
    (belief as any).validateObservableBattleState = calls;
    protocol.PROTOCOL_CONTRACT.validation_rules.player_ident.side_ids = old;
    for (const command of supported) protocol.SUPPORTED_RAW_COMMANDS.add(command);
  }
});

test('P32 installed runtime ownership', () => {
  const owned = installedNativeProfile(); assertNativeRuntimeProfile(owned);
  assert.equal(owned.reader, N); assert.equal(owned.package_version, '0.11.11'); assert.ok(Object.isFrozen(owned));
  assert.throws(() => new EnvironmentManager({...owned}), /unowned-runtime-profile/);
  assert.throws(() => new LocalBattleEnv('foreign', 'gen9randombattle', [1, 2, 3, 4], undefined, {}, undefined, undefined, undefined, {...owned}), /unowned-runtime-profile/);
  const disk = require('node:fs'), read = disk.readFileSync;
  let checked = 0;
  disk.readFileSync = function(file: any, ...args: any[]) {
    const content = read.call(this, file, ...args);
    if (String(file) === path.join(owned.package_root, 'package.json')) {
      checked++; const pkg = JSON.parse(String(content)); pkg.version = '0.11.10'; return JSON.stringify(pkg);
    }
    return content;
  };
  try {
    assert.throws(() => new EnvironmentManager(), /installed-runtime-mismatch/);
    assert.throws(() => new LocalBattleEnv('mismatch', 'gen9randombattle'), /installed-runtime-mismatch/);
    assert.equal(checked, 2);
  } finally { disk.readFileSync = read; }
  assertNativeRuntimeProfile(installedNativeProfile());
  emit('runtime-ownership', {actual_installed_paths_checked: true, model_metadata_fault_injected_at_real_read: true,
    constructors_rejected_before_native_creation: true, copied_descriptor_rejected: true});
});

test('P32 current runtime producer canary', async () => {
  const consume = PlayerStateExtractor.prototype.consumeChunk;
  const contexts: unknown[] = [];
  PlayerStateExtractor.prototype.consumeChunk = function(chunk) { contexts.push(this.getReaderContext()); return consume.call(this, chunk); };
  let session: PipelineIntegrationSession | undefined, manager: EnvironmentManager | undefined, envId: string | undefined;
  try {
    manager = new EnvironmentManager(); envId = manager.createEnv('gen9randombattle', [1, 2, 3, 4]).env_id;
    const result = await manager.resetEnv(envId);
    assert.equal(result.requests.p1?.side.length, 6);
    await manager.closeEnv(envId); envId = undefined;
    session = await PipelineIntegrationSession.create({battle_id: 'P32', format: 'gen9randombattle', seed: [1, 2, 3, 4]});
    assert.equal(session.getReaderContext(), N);
    const handles = (['p1', 'p2'] as const).map(o => session!.getNativeBirthHolding(o));
    const actions = Object.fromEntries((['p1', 'p2'] as const).map(owner => {
      const request = session!.boundary.perspectives[owner].observation.request!;
      return [owner, canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0])];
    }));
    const next = await session.step(actions as Record<'p1' | 'p2', ReturnType<typeof canonicalActionFromLegalAction>>);
    assert.ok(next.record_bundles.p1); validatePipelineLinkedRecordBundle(next.record_bundles.p1!, N);
    for (const [i, owner] of (['p1', 'p2'] as const).entries()) {
      assert.equal(session.readNativeBirthHolding(handles[i], owner).slot_count, 6);
      assert.equal(session.readNativeObjectHolding(session.getNativeObjectHolding(owner), owner).original_slots.length, 6);
      assert.ok(session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner).boundaries.length >= 2);
    }
    const wire = JSON.stringify(next);
    for (const token of ['runtimeProfile','rulesContext','package_root','original_slots','reader-profile']) assert.ok(!wire.includes(token));
    assert.ok(contexts.length > 4 && contexts.every(c => c === N));
    assert.equal(runtimeData(N).species.get('Pikachu').types[0], 'Electric');
    assert.throws(() => runtimeData(N).species.get('Pikachu').types.push('Fire'), TypeError);
    assert.throws(() => { runtimeData(N).moves.get('Thunderbolt').type = 'Fire'; }, TypeError);
    emit('producer-canary', {actual_generated_old_runtime: true, manager_and_session: true, one_step: true, extractor_contexts: contexts.length,
      both_owner_birth_restore_delivery_available: true, context_absent_from_wire: true, target_coexistence_unproved: true});
  } finally {
    PlayerStateExtractor.prototype.consumeChunk = consume;
    await session?.close(); if (envId) await manager?.closeEnv(envId);
  }
});
