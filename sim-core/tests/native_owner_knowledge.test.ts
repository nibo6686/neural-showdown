import assert from 'node:assert/strict';
import test from 'node:test';
import { Teams } from 'pokemon-showdown';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { NativeOwnerKnowledgeController } from '../src/native_owner_knowledge';
import { OriginalOwnerCreation } from '../src/original_owner_provider';
import { LocalBattleEnv } from '../src/env_manager';
import { checkNativeOwnerDetailsProjection, checkKnowledgeStructure, knowledgeIdentity } from '../src/perspective_knowledge';
import { installedNativeProfile } from '../src/version_profile';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import type { PlayerID } from '../src/types';
const owners = ['p1', 'p2'] as const;
const base = { battle_id: 'P48', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const recipients = () => ({ p1: {}, p2: {} });
const environment = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const read = (s: PipelineIntegrationSession, recipient: object) => s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(recipient), recipient);
const value = (pair: ReturnType<typeof read>, slot: number, property: string) => pair.projection.starting.find((f: any) => f.subject.endsWith(':roster:' + slot) && f.property === property);
const witness = (name: string, data: object) => console.log('P48_WITNESS ' + JSON.stringify({ name, ...data }));
function switches(s: PipelineIntegrationSession) {
  return Object.fromEntries(owners.map(owner => {
    const request = environment(s).getRequest(owner)!;
    const index = request.legal_actions.available_indices.find(i => request.legal_actions.actions[i]?.choice === 'switch 2');
    assert.notEqual(index, undefined); return [owner, canonicalActionFromLegalAction(request, index!)];
  })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
}

test('P48 generated authentic consumer restore and isolation', async () => {
  const r = recipients(); let s: PipelineIntegrationSession | undefined, other: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create({ ...base, knowledge_recipients: r });
    const initial = { p1: read(s, r.p1), p2: read(s, r.p2) }, handles = owners.map(owner => s!.getOwnerKnowledgeHandle(r[owner]));
    for (const owner of owners) {
      const pair = initial[owner], raw = s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(owner), owner).raw_team as any[];
      assert.equal(pair.projection.owner, owner); assert.equal(pair.projection.result, 'incomplete'); assert.equal(pair.projection.request.schema, 'owned-active-options/v1');
      assert.deepEqual(pair.projection.starting_crosswalk, []); assert.equal(pair.binding.request_adaptation, 'owned_health/v1');
      assert.equal(pair.binding.prefix_cursor, s.boundary.perspectives[owner].observation.event_cursor);
      assert.ok(Object.isFrozen(pair) && Object.isFrozen(pair.projection) && Object.isFrozen(pair.binding));
      assert.ok(pair.projection.current.filter((f: any) => !['K03','K04','K05','K18','K19'].includes(f.family)).every((f: any) => f.state === 'unknown' && f.reason === 'unimplemented_family' && f.value === null));
      assert.equal(pair.projection.starting.find((f: any) => f.property === 'roster_size').value.data, 6);
      for (let i = 0; i < 6; i++) {
        for (const property of ['ability', 'item']) assert.equal(value(pair, i + 1, property).value?.data ?? '', raw[i][property]);
        assert.equal(value(pair, i + 1, 'roster_species').value.data, raw[i].species);
        assert.deepEqual(value(pair, i + 1, 'starting_moves').value.data, raw[i].moves);
        assert.equal(value(pair, i + 1, 'roster_order').value.data, i + 1);
      }
      checkNativeOwnerDetailsProjection(pair.projection);
      assert.throws(() => checkKnowledgeStructure(pair.projection));
      assert.throws(() => s!.getOwnerKnowledgeHandle({ ...r[owner] }), /foreign-recipient/);
      assert.throws(() => s!.getOwnerKnowledgeHandle(owner as any), /foreign-recipient/);
      assert.throws(() => s!.readOwnerKnowledge({ ...s!.getOwnerKnowledgeHandle(r[owner]) }, r[owner]), /copied-or-stale/);
      assert.throws(() => s!.readOwnerKnowledge(s!.getOwnerKnowledgeHandle(r[owner]), r[owner === 'p1' ? 'p2' : 'p1']), /copied-or-stale/);
    }
    other = await PipelineIntegrationSession.create({ ...base, knowledge_recipients: r });
    assert.throws(() => s!.readOwnerKnowledge(other!.getOwnerKnowledgeHandle(r.p1), r.p1), /copied-or-stale/);
    for (let n = 1; n <= 2; n++) {
      const step = await s.step(switches(s));
      for (const owner of owners) {
        const current = read(s, r[owner]);
        assert.equal(current.projection.starting, initial[owner].projection.starting);
        assert.equal(current.projection.starting[0], initial[owner].projection.starting[0]);
        assert.equal(current.projection.boundary, n); assert.equal(initial[owner].projection.boundary, 0);
        assert.equal(current.binding.observation_id, s.boundary.perspectives[owner].observation.observation_id);
        assert.ok(current.binding.prefix_cursor > initial[owner].binding.prefix_cursor);
        assert.throws(() => s!.readOwnerKnowledge(handles[owner === 'p1' ? 0 : 1], r[owner]), /stale-handle/);
      }
      const ordinary = JSON.stringify({ step, snapshot: (s as any).snapshot, diagnostics: environment(s).diagnostics() });
      for (const field of ['request_adaptation', 'native-owner-original', 'knowledge_recipients', 'original_slot']) assert.ok(!ordinary.includes(field));
    }
    const h = s.getOwnerKnowledgeHandle(r.p1); await s.close(); assert.throws(() => s!.readOwnerKnowledge(h, r.p1), /closed/);
    witness('generated', { genuine_both_owner_prepacking_source: true, exact_consumer_values: true, two_held_reorders: true,
      identical_starting_fact_objects: true, recipient_and_issuer_isolation: true, stale_closed_denial: true, ordinary_outputs_private: true });
  } finally { await s?.close(); await other?.close(); }
});

test('P48 constructed initial effects and empty original item', async () => {
  const generate = Teams.generate;
  for (const effect of ['Trace', 'form']) {
    let s: PipelineIntegrationSession | undefined, calls = 0; const r = recipients();
    const chosen = Teams.import(effect === 'Trace' ? 'Gardevoir @ Leftovers\nAbility: Trace\n- Psychic'
      : 'Zacian @ Rusted Sword\nAbility: Intrepid Sword\n- Iron Head')!;
    const opposite = Teams.import('Blissey\nAbility: Natural Cure\n- Soft-Boiled')!; opposite[0].item = '';
    Teams.generate = function() { return structuredClone(calls++ === 0 ? chosen : opposite); };
    try {
      s = await PipelineIntegrationSession.create({ ...base, knowledge_recipients: r });
      const native = (environment(s) as any).battleStream.battle;
      const p1 = read(s, r.p1), p2 = read(s, r.p2);
      assert.equal(value(p1, 1, 'roster_species').value.data, chosen[0].species);
      assert.equal(value(p1, 1, 'ability').value.data, chosen[0].ability);
      assert.deepEqual(value(p1, 1, 'starting_moves').value.data, chosen[0].moves);
      if (effect === 'Trace') assert.equal(native.p1.active[0].ability, 'naturalcure');
      else { assert.equal(native.p1.active[0].species.name, 'Zacian-Crowned'); assert.equal(native.p1.activeRequest.active[0].moves[0].id, 'behemothblade'); }
      assert.equal(value(p2, 1, 'item').state, 'known_absent'); assert.equal(value(p2, 1, 'item').value, null);
      assert.ok(p1.projection.current.filter((f: any) => !['K03','K04','K05','K18','K19'].includes(f.family)).every((f: any) => f.state === 'unknown'));
      witness(effect, { actual_session_constructed_initial_mechanic: true, generated_reachability: 'not-certified',
        original_fields_retained: true, current_blocked: true, explicit_empty_item_absence: true });
    } finally { Teams.generate = generate; await s?.close(); }
  }
});

test('P48 rejects copied source attacks and projection nonauthority', async () => {
  const register = OriginalOwnerCreation.prototype.registerKnowledgeReceiver, generate = Teams.generate;
  const cases = ['missing', 'duplicate', 'environment', 'occurrence-copy', 'rows-copy', 'wrong-owner', 'missing-item', 'undefined-ability', 'unsupported', 'role'];
  for (const fault of cases) {
    const r = recipients();
    OriginalOwnerCreation.prototype.registerKnowledgeReceiver = function(receiver) {
      if (fault === 'missing') return;
      register.call(this, (environment, occurrence, rows) => {
        if (fault === 'environment') environment = {};
        if (fault === 'occurrence-copy') occurrence = { ...occurrence };
        if (fault === 'rows-copy') rows = rows.map(row => ({ ...row }));
        if (fault === 'wrong-owner') rows = [rows[1], rows[0]];
        receiver(environment, occurrence, rows);
        if (fault === 'duplicate') receiver(environment, occurrence, rows);
      });
    };
    Teams.generate = function(...args) {
      const teams = generate.apply(this, args);
      if (fault === 'missing-item') delete (teams[0] as any).item;
      if (fault === 'undefined-ability') (teams[0] as any).ability = undefined;
      if (fault === 'unsupported') (teams[0] as any).alien_field = 'not submitted';
      if (fault === 'role') (teams[0] as any).role = undefined;
      return teams;
    };
    try {
      const expected = fault === 'missing' ? /missing-enrollment/ : fault === 'duplicate' ? /duplicate-or-late-enrollment/
        : ['environment', 'occurrence-copy', 'rows-copy', 'wrong-owner'].includes(fault) ? /foreign-knowledge-enrollment/
        : ['missing-item', 'undefined-ability'].includes(fault) ? /native-original\/missing-required-field/
        : fault === 'unsupported' ? /native-original\/unsupported-field/ : /native-original\/generator-metadata/;
      await assert.rejects(PipelineIntegrationSession.create({ ...base, knowledge_recipients: r }), expected);
      witness(fault, { actual_session_rejection: true, expected: expected.source });
    } finally { OriginalOwnerCreation.prototype.registerKnowledgeReceiver = register; Teams.generate = generate; }
  }
  const r = recipients(); let s: PipelineIntegrationSession | undefined;
  try {
    const runtime = installedNativeProfile(), creation = new OriginalOwnerCreation({ battle_id: 'model', format: base.format, simulator_revision: runtime.reader.profile.revision });
    assert.throws(() => new NativeOwnerKnowledgeController(creation, { ...runtime }, r), /unowned-runtime-profile/);
    assert.throws(() => new NativeOwnerKnowledgeController(creation, runtime, { p1: r.p1, p2: r.p1 }), /recipient-registration/);
    s = await PipelineIntegrationSession.create({ ...base, knowledge_recipients: r });
    const live = read(s, r.p1);
    for (const kind of ['profile', 'current-known', 'missing-fact', 'absence', 'crosswalk', 'complete']) {
      const copy: any = structuredClone(live.projection);
      if (kind === 'profile') copy.required_profile = 'sha256:' + '0'.repeat(64);
      if (kind === 'current-known') copy.current[0] = { ...copy.starting[0], freshness: 'current' };
      if (kind === 'missing-fact') copy.starting.splice(1, 1);
      if (kind === 'absence') { copy.starting[1].state = 'known_absent'; copy.starting[1].value = null; copy.starting[1].precision = 'not_applicable'; }
      if (kind === 'crosswalk') copy.starting_crosswalk = [{ appearance: 'p1:appearance:1', roster: 'p1:roster:1' }];
      if (kind === 'complete') copy.result = 'strong_complete';
      copy.id = knowledgeIdentity(copy);
      assert.throws(() => checkNativeOwnerDetailsProjection(copy));
    }
    const falseOriginal: any = structuredClone(live.projection);
    falseOriginal.starting.find((f: any) => f.property === 'ability').value.data = 'NotTheOriginal';
    falseOriginal.id = knowledgeIdentity(falseOriginal); checkNativeOwnerDetailsProjection(falseOriginal);
    assert.throws(() => s!.readOwnerKnowledge(falseOriginal, r.p1), /copied-or-stale/);
    assert.throws(() => s!.readOwnerKnowledge(structuredClone(live) as any, r.p1), /copied-or-stale/);
    witness('structure', { coherent_negative_classes: 6, raw_false_original_structural_only: true, no_import_or_authority_mint: true,
      runtime_constructor_checks: 'lower-level-unowned-profile-and-recipient', ordinary_action_authority_unchanged: true });
  } finally { await s?.close(); }
});

test('P48 final barrier revocation rollback and fresh retry', async () => {
  const prepare = NativeOwnerKnowledgeController.prototype.prepare, preflight = NativeOwnerKnowledgeController.prototype.preflight,
    install = NativeOwnerKnowledgeController.prototype.installReady, close = LocalBattleEnv.prototype.close;
  let controller: NativeOwnerKnowledgeController, token: object, mode = 'creation', installed = 0, s: PipelineIntegrationSession | undefined;
  const r = recipients();
  NativeOwnerKnowledgeController.prototype.prepare = function(...args) { controller = this; token = prepare.apply(this, args); return token; };
  NativeOwnerKnowledgeController.prototype.preflight = function(token) { preflight.call(this, token); throw new Error('P48-final-' + mode); };
  NativeOwnerKnowledgeController.prototype.installReady = function() { installed++; return install.call(this); };
  LocalBattleEnv.prototype.close = async function() { assert.throws(() => controller!.preflight(token), /revoked|foreign-or-stale-preparation/); return close.call(this); };
  try {
    await assert.rejects(PipelineIntegrationSession.create({ ...base, knowledge_recipients: r }), /P48-final-creation/); assert.equal(installed, 0);
    NativeOwnerKnowledgeController.prototype.preflight = preflight; LocalBattleEnv.prototype.close = close;
    s = await PipelineIntegrationSession.create({ ...base, knowledge_recipients: r }); const before = owners.map(owner => ({ handle: s!.getOwnerKnowledgeHandle(r[owner]), read: read(s!, r[owner]),
      event: s!.getSwitchEventHolding(owner), delivery: s!.readRequestDeliveryHistory(s!.getRequestDeliveryHandle(owner), owner), native: s!.getNativeObjectHolding(owner) }));
    const boundary = s.boundary; installed = 0; mode = 'successor';
    NativeOwnerKnowledgeController.prototype.preflight = function(token) { preflight.call(this, token); throw new Error('P48-final-successor'); };
    LocalBattleEnv.prototype.close = async function() { assert.throws(() => controller!.preflight(token), /foreign-or-stale-preparation/); return close.call(this); };
    await assert.rejects(s.step(switches(s)), /P48-final-successor/); assert.equal(installed, 0); assert.equal(s.boundary, boundary);
    for (const [i, owner] of owners.entries()) {
      assert.equal(s.getOwnerKnowledgeHandle(r[owner]), before[i].handle); assert.equal(read(s, r[owner]), before[i].read);
      assert.equal(s.getSwitchEventHolding(owner), before[i].event); assert.equal(s.getNativeObjectHolding(owner), before[i].native);
      assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(owner), owner), before[i].delivery);
    }
    NativeOwnerKnowledgeController.prototype.preflight = preflight; LocalBattleEnv.prototype.close = close;
    await s.step(switches(s)); assert.equal(installed, 1); assert.equal(read(s, r.p1).projection.starting, before[0].read.projection.starting);
    const current = s.getOwnerKnowledgeHandle(r.p1); await s.close(); assert.throws(() => s!.readOwnerKnowledge(current, r.p1), /closed/);
    witness('barrier', { actual_creation_and_successor_final_preflight_faults: true, revocation_before_cleanup: true,
      exact_all_committed_handles_preserved: true, fresh_retry_identical_starting: true, closed_denial: true });
  } finally { NativeOwnerKnowledgeController.prototype.prepare = prepare; NativeOwnerKnowledgeController.prototype.preflight = preflight;
    NativeOwnerKnowledgeController.prototype.installReady = install; LocalBattleEnv.prototype.close = close; await s?.close(); }
});
