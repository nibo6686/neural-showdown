import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle } from 'pokemon-showdown';
import { NativeObjectAssociation, NativeBirthEnrollment } from '../src/owner_identity_crosswalk';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { LocalBattleEnv } from '../src/env_manager';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import type { PlayerID } from '../src/types';
const owners = ['p1', 'p2'] as const;
const options = { battle_id: 'B2', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const environment = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const battle = (s: PipelineIntegrationSession): Battle => (environment(s) as any).battleStream.battle;
const snapshot = (s: PipelineIntegrationSession) => (s as any).snapshot;
const row = (s: PipelineIntegrationSession, owner: PlayerID) => s.readNativeObjectHolding(s.getNativeObjectHolding(owner), owner);
const original = (s: PipelineIntegrationSession, owner: PlayerID) => s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(owner), owner);
const witness = (name: string, data: object) => console.log('B2_WITNESS ' + JSON.stringify({ name, ...data }));
function switches(s: PipelineIntegrationSession) {
  return Object.fromEntries(owners.map(owner => {
    const request = environment(s).getRequest(owner)!;
    const index = request.legal_actions.available_indices.find(i => request.legal_actions.actions[i]?.choice === 'switch 2');
    assert.notEqual(index, undefined, 'literal second party slot must be legal');
    return [owner, canonicalActionFromLegalAction(request, index!)];
  })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
}

test('B2 generated reordered continuity', async () => {
  let s: PipelineIntegrationSession | undefined, control: Battle | undefined;
  try {
    s = await PipelineIntegrationSession.create(options);
    control = new Battle({ formatid: options.format, seed: '1,2,3,4' });
    for (const owner of owners) control.setPlayer(owner, { name: owner === 'p1' ? 'Agent-1' : 'Agent-2', team: original(s, owner).packed_team });
    const controlObjects = { p1: control.p1!.pokemon.slice(), p2: control.p2!.pokemon.slice() };
    const expected = [[2, 1, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6], [2, 1, 3, 4, 5, 6]];
    for (const order of expected) {
      const actions = switches(s); const old = owners.map(owner => s!.getNativeObjectHolding(owner));
      await s.step(actions);
      control.choose('p1', 'switch 2'); control.choose('p2', 'switch 2');
      for (const [i, owner] of owners.entries()) {
        assert.deepEqual(row(s, owner).original_slots, order);
        assert.deepEqual(control[owner]!.pokemon.map(p => controlObjects[owner].indexOf(p) + 1), order);
        assert.deepEqual(battle(s)[owner]!.activeRequest, control[owner]!.activeRequest);
        assert.equal(row(s, owner).original, original(s, owner));
        assert.throws(() => s!.readNativeObjectHolding(old[i], owner), /foreign-or-forged-holding/);
      }
    }
    witness('reordered', { level: 'actual-generated-session-plus-generated-input-uninterrupted-native-control', expected_orders: expected,
      both_owner_orders_match: true, requests_match: true, originals_same_reference: true, no_name_or_position_inference: true });
  } finally { control?.destroy(); await s?.close(); }
});

test('B2 reference continuity', async () => {
  const accept = NativeObjectAssociation.prototype.acceptRestore, observe = NativeBirthEnrollment.prototype.observe;
  let s: PipelineIntegrationSession | undefined, births = 0, restores = 0;
  let old: object[] = [], oldSets: object[] = [];
  NativeBirthEnrollment.prototype.observe = function(...args) { births++; return observe.apply(this, args); };
  NativeObjectAssociation.prototype.acceptRestore = function(env, input, native, ticket) {
    accept.call(this, env, input, native, ticket); restores++;
    for (const owner of owners) {
      const side = native[owner]!, raw = (input as any).sides[owner === 'p1' ? 0 : 1];
      for (const [i, p] of side.pokemon.entries()) {
        assert.ok(!old.includes(p)); assert.ok(!oldSets.includes(p.set)); assert.equal(p.set, raw.pokemon[i].set);
        assert.equal(side.team.indexOf(p.set) + 1, raw.team.split('').indexOf(String(i + 1)) + 1);
      }
    }
  };
  try {
    s = await PipelineIntegrationSession.create(options);
    const held = owners.map(owner => original(s!, owner));
    old = owners.flatMap(owner => [...battle(s!)[owner]!.pokemon]);
    oldSets = owners.flatMap(owner => battle(s!)[owner]!.pokemon.map(p => p.set));
    await s.step(switches(s));
    old = owners.flatMap(owner => [...battle(s!)[owner]!.pokemon]);
    oldSets = owners.flatMap(owner => battle(s!)[owner]!.pokemon.map(p => p.set));
    await s.step(switches(s));
    assert.equal(births, 1); assert.equal(restores, 2);
    for (const [i, owner] of owners.entries()) assert.equal(row(s, owner).original, held[i]);
    witness('references', { level: 'actual-session-serializer-reconstructor-wiring', restored_occurrences: restores,
      all_objects_fresh: true, sets_disjoint_from_prior_live_refs: true, final_input_set_refs_exact: true, held_originals_same: true, birth_occurrences: births });
  } finally { NativeObjectAssociation.prototype.acceptRestore = accept; NativeBirthEnrollment.prototype.observe = observe; await s?.close(); }
});

test('B2 parent and snapshot faults', async () => {
  const prepare = NativeObjectAssociation.prototype.prepareRestore, reset = LocalBattleEnv.prototype.resetFromSerialized;
  const accept = NativeObjectAssociation.prototype.acceptRestore;
  const cases: Array<[string, RegExp]> = [
    ['missing-parent', /foreign-or-missing-parent/], ['copied-parent', /foreign-or-missing-parent/],
    ['foreign-parent', /foreign-or-missing-parent/], ['same-label-sibling-parent', /foreign-or-missing-parent/],
    ['copied-snapshot', /foreign-serialization-occurrence/], ['set-copy', /snapshot-reference-mismatch/],
    ['permutation', /snapshot-content-mismatch/], ['snapshot-owner', /snapshot-content-mismatch/],
    ['missing-ticket', /foreign-or-stale-restore-ticket/], ['copied-ticket', /foreign-or-stale-restore-ticket/],
    ['wrong-native-owner', /reconstructed-object-mismatch/],
    ['final-input-set-copy', /reconstruction-input-occurrence-mismatch/],
    ['final-input-row-copy', /reconstruction-input-occurrence-mismatch/],
  ];
  for (const [fault, pattern] of cases) {
    let s: PipelineIntegrationSession | undefined, foreign: PipelineIntegrationSession | undefined, undo = () => {};
    try {
      s = await PipelineIntegrationSession.create(options);
      if (fault.includes('parent') && fault !== 'missing-parent' && fault !== 'copied-parent') foreign = await PipelineIntegrationSession.create({ ...options, battle_id: fault === 'foreign-parent' ? 'B2-other' : 'B2' });
      const before = owners.map(owner => ({ handle: s!.getNativeObjectHolding(owner), evidence: row(s!, owner) })), boundary = s.boundary;
      NativeObjectAssociation.prototype.prepareRestore = function(env, parent, state) {
        if (fault === 'missing-parent') parent = null as any;
        if (fault === 'copied-parent') parent = { ...parent };
        if (fault === 'foreign-parent' || fault === 'same-label-sibling-parent') parent = foreign!.boundary;
        if (fault === 'copied-snapshot') state = { ...state };
        const side = (state.simulator_state as any).sides[0];
        if (fault === 'set-copy') { const old = side.pokemon[0].set; side.pokemon[0].set = structuredClone(old); undo = () => { side.pokemon[0].set = old; }; }
        if (fault === 'permutation') { const old = side.team; side.team = '213456'; undo = () => { side.team = old; }; }
        if (fault === 'snapshot-owner') { const old = side.id; side.id = 'p2'; undo = () => { side.id = old; }; }
        return prepare.call(this, env, parent, state);
      };
      LocalBattleEnv.prototype.resetFromSerialized = function(state, opts, ticket) {
        return reset.call(this, state, opts, fault === 'missing-ticket' ? undefined : fault === 'copied-ticket' ? { ...ticket } : ticket);
      };
      NativeObjectAssociation.prototype.acceptRestore = function(env, input, native, ticket) {
        const rows = (input as any).sides[0].pokemon;
        if (fault === 'final-input-set-copy') rows[0].set = structuredClone(rows[0].set);
        if (fault === 'final-input-row-copy') rows[0] = structuredClone(rows[0]);
        if (fault === 'wrong-native-owner') Object.defineProperty(native.p1!.pokemon[0], 'side', { value: native.p2 });
        return accept.call(this, env, input, native, ticket);
      };
      await assert.rejects(s.step(), pattern);
      assert.equal(s.boundary, boundary);
      for (const [i, owner] of owners.entries()) {
        assert.equal(s.getNativeObjectHolding(owner), before[i].handle);
        assert.equal(s.readNativeObjectHolding(before[i].handle, owner), before[i].evidence);
      }
      witness(fault, { level: 'actual-session-rejection', expected: pattern.source, committed_associations_unchanged: true });
    } finally {
      undo(); NativeObjectAssociation.prototype.prepareRestore = prepare; LocalBattleEnv.prototype.resetFromSerialized = reset;
      NativeObjectAssociation.prototype.acceptRestore = accept; await s?.close(); await foreign?.close();
    }
  }
});

test('B2 rollback', async () => {
  const prepare = NativeObjectAssociation.prototype.prepareCommit, close = LocalBattleEnv.prototype.close;
  let s: PipelineIntegrationSession | undefined, controller: NativeObjectAssociation | undefined, token: object | undefined, checked = false;
  try {
    s = await PipelineIntegrationSession.create(options);
    const boundary = s.boundary, before = owners.map(owner => ({ handle: s!.getNativeObjectHolding(owner), value: row(s!, owner) }));
    NativeObjectAssociation.prototype.prepareCommit = function(...args) {
      controller = this; token = prepare.apply(this, args);
      assert.throws(() => this.read(token!, 'p1'), /foreign-or-forged-holding/);
      throw new Error('B2-post-prepare-before-commit');
    };
    LocalBattleEnv.prototype.close = function() {
      if (this.id.includes('step-')) {
        assert.throws(() => controller!.commit(token!), /foreign-or-stale-preparation/);
        for (const [i, owner] of owners.entries()) assert.equal(s!.readNativeObjectHolding(before[i].handle, owner), before[i].value);
        checked = true;
      }
      return close.call(this);
    };
    await assert.rejects(s.step(switches(s)), /B2-post-prepare-before-commit/);
    assert.ok(checked); assert.equal(s.boundary, boundary);
    NativeObjectAssociation.prototype.prepareCommit = prepare; LocalBattleEnv.prototype.close = close;
    await s.step(switches(s));
    for (const [i, owner] of owners.entries()) {
      assert.deepEqual(row(s, owner).original_slots, [2, 1, 3, 4, 5, 6]);
      assert.notEqual(s.getNativeObjectHolding(owner), before[i].handle);
    }
    assert.throws(() => controller!.commit(token!), /foreign-or-stale-preparation/);
    witness('rollback', { level: 'actual-session-post-prepare-failure', old_handles_and_rows_unchanged: true,
      candidate_revoked_before_cleanup: true, valid_fresh_retry: true });
  } finally { NativeObjectAssociation.prototype.prepareCommit = prepare; LocalBattleEnv.prototype.close = close; await s?.close(); }
});

test('B2 owner privacy', async () => {
  let s: PipelineIntegrationSession | undefined, foreign: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create(options); foreign = await PipelineIntegrationSession.create(options);
    await s.step(switches(s));
    for (const owner of owners) {
      const handle = s.getNativeObjectHolding(owner), other = owner === 'p1' ? 'p2' : 'p1';
      assert.throws(() => s!.readNativeObjectHolding(handle, other), /foreign-or-forged-holding/);
      for (const copy of [{}, { ...handle }, structuredClone(handle), JSON.parse(JSON.stringify(handle)), foreign.getNativeObjectHolding(owner)]) assert.throws(() => s!.readNativeObjectHolding(copy, owner), /foreign-or-forged-holding/);
      assert.equal(row(s, owner).original.owner, owner);
      assert.deepEqual(Object.keys(row(s, owner)), ['owner', 'original', 'original_slots', 'observation_id', 'branch_id', 'step_index']);
      const wire = JSON.stringify({ boundary: s.boundary, snapshot: snapshot(s), diagnostics: environment(s).diagnostics() });
      for (const key of ['original_slots', 'objectAssociation', 'objectAssociationTicket', 'raw_team', 'packed_team']) assert.ok(!wire.includes('"' + key + '"'));
      assert.equal(Reflect.ownKeys(handle).length, 0);
    }
    witness('privacy', { level: 'actual-generated-session', wrong_owner_rejections: 2, forged_foreign_rejections: 10,
      no_new_association_fields_in_legacy_outputs: true });
  } finally { await s?.close(); await foreign?.close(); }
});

test('B2 close and legacy', async () => {
  const initial = NativeObjectAssociation.prototype.commitInitial, close = LocalBattleEnv.prototype.close, reset = LocalBattleEnv.prototype.resetWithOptions;
  let controller: NativeObjectAssociation | undefined, handle: object | undefined;
  let s: PipelineIntegrationSession | undefined;
  const donor = new LocalBattleEnv('B2-legacy', options.format, options.seed);
  try {
    NativeObjectAssociation.prototype.commitInitial = function(...args) { initial.apply(this, args); controller = this; handle = this.holding('p1'); throw new Error('B2-init-after-association'); };
    LocalBattleEnv.prototype.close = function() { assert.throws(() => controller!.read(handle!, 'p1'), /unavailable/); return close.call(this); };
    await assert.rejects(PipelineIntegrationSession.create(options), /B2-init-after-association/);
    NativeObjectAssociation.prototype.commitInitial = initial; LocalBattleEnv.prototype.close = close;
    s = await PipelineIntegrationSession.create(options); const live = s.getNativeObjectHolding('p1');
    const closing = s.close(); assert.throws(() => s!.readNativeObjectHolding(live, 'p1'), /closed/); await closing;
    await donor.reset(); const state = donor.serializeBattle();
    LocalBattleEnv.prototype.resetWithOptions = function(opts) { return this.resetFromSerialized(structuredClone(state), opts); };
    await assert.rejects(PipelineIntegrationSession.create(options), /native-association\/v1\/foreign-or-stale-restore-ticket/);
    await assert.rejects(donor.resetFromSerialized(state), /snapshot-admission\/v1\/raw-restore-unsupported/);
    witness('close-legacy', { level: 'actual-target-init-failure-close-and-rejected-authority-free-restore', init_revoked_before_cleanup: true,
      synchronous_close_denial: true, target_authority_free_admission_rejected: true });
  } finally { NativeObjectAssociation.prototype.commitInitial = initial; LocalBattleEnv.prototype.close = close;
    LocalBattleEnv.prototype.resetWithOptions = reset; await s?.close(); await donor.close(); }
});
