import assert from 'node:assert/strict';
import test from 'node:test';
import { types } from 'node:util';
import { Battle } from 'pokemon-showdown';
import { SwitchEventHost } from '../src/owner_identity_events';
import { NativeObjectAssociation } from '../src/owner_identity_crosswalk';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import type { PlayerID } from '../src/types';
const owners = ['p1', 'p2'] as const;
const withoutTimestamps = (lines: readonly string[]) => lines.filter(line => !line.startsWith('|t:|'));
const options = { battle_id: 'P45', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const env = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const native = (s: PipelineIntegrationSession): Battle => (env(s) as any).battleStream.battle;
function switches(s: PipelineIntegrationSession) {
  return Object.fromEntries(owners.map(owner => {
    const request = env(s).getRequest(owner)!;
    const at = request.legal_actions.available_indices.find(i => request.legal_actions.actions[i]?.choice === 'switch 2');
    assert.notEqual(at, undefined);
    return [owner, canonicalActionFromLegalAction(request, at!)];
  })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
}
function taps() {
  const birth = SwitchEventHost.prototype.attachBirth, restored = SwitchEventHost.prototype.attachRestored;
  let host: SwitchEventHost;
  const worlds: object[] = [];
  SwitchEventHost.prototype.attachBirth = function(...args) { host = this; worlds.push(args[0]); return birth.apply(this, args); };
  SwitchEventHost.prototype.attachRestored = function(...args) { host = this; worlds.push(args[0]); return restored.apply(this, args); };
  return { host: () => host!, worlds, restore: () => { SwitchEventHost.prototype.attachBirth = birth; SwitchEventHost.prototype.attachRestored = restored; } };
}
const witness = (name: string, data: object) => console.log('P45_WITNESS ' + JSON.stringify({ name, ...data }));

test('P45 generated creation restore and plain parity', async () => {
  const tap = taps(); let s: PipelineIntegrationSession | undefined, control: Battle | undefined;
  try {
    s = await PipelineIntegrationSession.create(options);
    const host = tap.host(), birthEnv = env(s), birthBattle = native(s), first = host.inspect(birthEnv);
    assert.equal(first.valid, true); assert.equal(first.pending, 0);
    assert.deepEqual(first.writers.map(w => [w.owner, w.slot]).sort(), [['p1', 1], ['p2', 1]]);
    assert.ok(first.writers.every(w => w.rows.length === 3 && w.valid));
    const originalObjects = owners.flatMap(owner => [...birthBattle[owner]!.pokemon]);
    const originals = owners.map(owner => s!.readOriginalOwnerHolding(s!.getOriginalOwnerHolding(owner), owner));
    for (const owner of owners) for (let i = 0; i < 6; i++) {
      assert.equal(host.checkActor(birthEnv, first.leases[owner], owner, birthBattle[owner]!.pokemon[i]), i + 1);
    }
    control = new Battle({ formatid: options.format, seed: '1,2,3,4' });
    for (const [i, owner] of owners.entries()) control.setPlayer(owner, { name: owner === 'p1' ? 'Agent-1' : 'Agent-2', team: originals[i].packed_team });
    assert.deepEqual(withoutTimestamps(birthBattle.log), withoutTimestamps(control.log));
    const raw = birthEnv.serializeBattle();
    assert.equal(types.isProxy(raw.log), false); assert.notEqual(raw.log, birthBattle.log);
    assert.ok(Array.isArray(raw.log));
    assert.deepEqual(withoutTimestamps(raw.log), withoutTimestamps(control.log)); assert.deepEqual(raw, structuredClone(raw));
    assert.equal((raw as any).sides[0].pokemon[0].set, birthBattle.p1!.pokemon[0].set);
    assert.equal(JSON.stringify(raw), JSON.stringify(birthBattle.toJSON()));
    // Lower-level post-send stimulus: a held snapshot must not inherit later leaf invalidation.
    const leaf = first.rows.findIndex(r => r.token === first.writers[0].rows[1]);
    birthBattle.log[leaf] += '|post-send-mutation';
    assert.equal(host.inspect(birthEnv).writers[0].valid, false);
    for (const expectedSlot of [2, 1]) {
      const previous = env(s), old = host.inspect(previous);
      await s.step(switches(s));
      const next = host.inspect(env(s));
      assert.equal(next.valid, true); assert.equal(next.pending, 0);
      assert.deepEqual(next.writers.map(w => [w.owner, w.slot]).sort(), [['p1', expectedSlot], ['p2', expectedSlot]]);
      assert.ok(next.writers.every(w => w.valid));
      assert.deepEqual(next.sends[0].rows.slice(0, old.rows.length).map(r => r.token), old.rows.map(r => r.token));
      assert.notEqual(next.sends[0].token, old.sends[0].token);
      if (expectedSlot === 2) assert.equal(next.sends[0].rows[leaf].version, first.rows[leaf].version,
        'held lineage retains the serialization-time version, not later live mutations');
      assert.throws(() => host.inspect(previous), /unavailable-world/);
      for (const owner of owners) {
        assert.ok(!originalObjects.includes(native(s)[owner]!.pokemon[0]));
        assert.equal(host.checkActor(env(s), next.leases[owner], owner, native(s)[owner]!.pokemon[0]), expectedSlot);
      }
      assert.notEqual(next.leases.p1, old.leases.p1);
      const state = env(s).serializeBattle();
      assert.equal(types.isProxy(state.log), false); assert.deepEqual(state, structuredClone(state));
      assert.equal(JSON.stringify(state), JSON.stringify(native(s).toJSON()));
      const output = JSON.stringify({ boundary: s.boundary, snapshot: (s as any).snapshot, state });
      for (const forbidden of ['switchEvents', 'actorLease', 'publicRows', 'writerToken']) assert.ok(!output.includes(forbidden));
    }
    await s.close(); assert.throws(() => host.inspect(env(s!)), /unavailable-world/);
    witness('generated-restoration', { generated_both_owners: true, literal_slots: [1, 2, 1], historical_row_tokens_preserved: true,
      historical_reemission_new_writers: 0, plain_clone_and_native_json_parity: true, native_set_reference_parity: true, no_output_sidecar: true });
  } finally { tap.restore(); control?.destroy(); await s?.close(); }
});

test('P45 constructed mutations split sends and equal text', async () => {
  const tap = taps(); let s: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create(options);
    const host = tap.host(), e = env(s), b = native(s), initial = host.inspect(e);
    b.add('switch', b.p1!.pokemon[0], b.p1!.pokemon[0].getFullDetails);
    assert.equal(host.inspect(e).writers.length, initial.writers.length, 'arbitrary add cannot mint writer');
    b.add('equal'); b.add('equal');
    const before = host.inspect(e), end = before.rows.length;
    assert.notEqual(before.rows[end - 1].token, before.rows[end - 2].token);
    b.addMove('move', 'p1a: A', 'Tackle', 'p2a: B');
    const move = host.inspect(e).rows.at(-1)!;
    b.retargetLastMove(b.p2!.pokemon[0]);
    assert.equal(host.inspect(e).rows.at(-1)!.token, move.token);
    assert.equal(host.inspect(e).rows.at(-1)!.version, 1);
    b.log.splice(end, 1);
    assert.deepEqual(host.inspect(e).rows.slice(0, end).map(r => r.token), before.rows.map(r => r.token));
    b.log.push('temporary'); delete b.log[b.log.length - 1]; b.log.length--;
    b.sendUpdates(); await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve));
    const sent = host.inspect(e); assert.equal(sent.valid, true); assert.equal(sent.pending, 0);
    assert.ok(sent.sends.at(-1)!.pushed);
    b.add('equal'); b.sendUpdates(); await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve));
    const again = host.inspect(e); assert.notEqual(again.sends.at(-1)!.token, sent.sends.at(-1)!.token);
    const writerCount = again.writers.length;
    const gameType = b.gameType;
    try {
      (b as any).gameType = 'doubles'; // Synthetic shape gate, not generated doubles reachability.
      b.actions.switchIn(b.p1!.pokemon[1], 0);
    } finally { (b as any).gameType = gameType; }
    b.actions.switchIn(b.p2!.pokemon[1], 0, b.dex.moves.get('uturn'));
    b.actions.switchIn(b.p1!.pokemon[1], 0, null, true);
    assert.equal(host.inspect(e).writers.length, writerCount, 'shape/tagged/drag paths remain unbound');
    const writerRow = initial.rows.findIndex(r => r.token === initial.writers[0].rows[1]);
    b.log[writerRow] += '|changed';
    assert.equal(host.inspect(e).writers[0].valid, false);
    b.log.splice(writerRow, 1); assert.equal(host.inspect(e).writers[0].valid, false);
    (b as any).log = [...b.log]; assert.equal(host.inspect(e).valid, false);
    assert.throws(() => e.captureSeededSnapshot(), /unavailable-log-proof/);
    witness('constructed-mutation', { genuine_creation_then_lower_level_stimulus: true, arbitrary_add_unbound: true,
      equal_strings_distinct_rows_and_sends: true, split_one_writer_three_rows: true, surviving_tokens_and_versions: true,
      synthetic_shape_gate_and_native_tagged_drag_unbound: true, switch_rewrite_removal_and_array_replacement_deny: true });
  } finally { tap.restore(); await s?.close(); }
});

test('P45 copied foreign owner and closed lease rejection', async () => {
  const tap = taps(); let a: PipelineIntegrationSession | undefined, b: PipelineIntegrationSession | undefined;
  try {
    a = await PipelineIntegrationSession.create(options); const ah = tap.host(), ae = env(a), ar = ah.inspect(ae);
    b = await PipelineIntegrationSession.create({ ...options, battle_id: 'P45-sibling' }); const bh = tap.host(), be = env(b), br = bh.inspect(be);
    for (const owner of owners) {
      const other = owner === 'p1' ? 'p2' : 'p1';
      assert.throws(() => ah.checkActor(ae, { ...ar.leases[owner] }, owner, native(a!)[owner]!.pokemon[0]), /foreign-or-revoked/);
      assert.throws(() => ah.checkActor(ae, ar.leases[other], owner, native(a!)[owner]!.pokemon[0]), /foreign-or-revoked/);
      assert.throws(() => ah.checkActor(ae, ar.leases[owner], other, native(a!)[owner]!.pokemon[0]), /foreign-or-revoked/);
      assert.throws(() => ah.checkActor(ae, br.leases[owner], owner, native(a!)[owner]!.pokemon[0]), /foreign-or-revoked/);
      assert.throws(() => ah.checkActor(ae, ar.leases[owner], owner, native(b!)[owner]!.pokemon[0]), /foreign-or-revoked/);
    }
    assert.throws(() => bh.inspect(ae), /unavailable-world/);
    const actor = native(a).p1!.pokemon[0]; await a.close();
    assert.throws(() => ah.checkActor(ae, ar.leases.p1, 'p1', actor), /unavailable-world/);
    witness('lease-faults', { both_direction_owner_isolation: true, copied_foreign_and_foreign_actor_reject: true, closed_lease_revoked: true });
  } finally { tap.restore(); await a?.close(); await b?.close(); }
});

test('P45 actual postcapture rollback and fresh retry', async () => {
  const tap = taps(), prepare = NativeObjectAssociation.prototype.prepareCommit, close = LocalBattleEnv.prototype.close;
  let s: PipelineIntegrationSession | undefined, captured: object | undefined, rejectedBeforeCleanup = false;
  try {
    s = await PipelineIntegrationSession.create(options); const host = tap.host(), committedEnv = env(s), before = host.inspect(committedEnv);
    const boundary = s.boundary, holdings = owners.map(owner => s!.getNativeObjectHolding(owner));
    NativeObjectAssociation.prototype.prepareCommit = function(e, next, snapshot, ticket) {
      const result = prepare.call(this, e, next, snapshot, ticket); captured = e;
      assert.deepEqual(host.inspect(e).writers.map(w => w.slot), [2, 2]);
      throw new Error('P45-after-capture-before-commit');
    };
    LocalBattleEnv.prototype.close = async function() {
      if (this === captured) { assert.throws(() => host.inspect(this), /unavailable-world/); rejectedBeforeCleanup = true; }
      return close.call(this);
    };
    await assert.rejects(s.step(switches(s)), /P45-after-capture-before-commit/);
    assert.equal(rejectedBeforeCleanup, true); assert.equal(s.boundary, boundary); assert.equal(env(s), committedEnv);
    assert.deepEqual(host.inspect(committedEnv), before);
    for (const [i, owner] of owners.entries()) assert.equal(s.getNativeObjectHolding(owner), holdings[i]);
    NativeObjectAssociation.prototype.prepareCommit = prepare;
    await s.step(switches(s));
    assert.equal(host.inspect(env(s)).valid, true); assert.notEqual(env(s), captured);
    witness('rollback', { actual_postcapture_fault: true, revocation_before_awaited_cleanup: true,
      committed_B2_and_tentative_history_unchanged: true, fresh_retry_chain: true });
  } finally { NativeObjectAssociation.prototype.prepareCommit = prepare; LocalBattleEnv.prototype.close = close; tap.restore(); await s?.close(); }
});


test('P45 overridden producer remains unbound', async () => {
  const tap = taps(), attach = SwitchEventHost.prototype.attachBirth;
  let s: PipelineIntegrationSession | undefined;
  SwitchEventHost.prototype.attachBirth = function(e, b, stream) {
    const canonical = b.actions.switchIn;
    // Lower-level own override stimulus; no claim about generated mod reachability.
    b.actions.switchIn = function(...args) { return canonical.apply(this, args); };
    return attach.call(this, e, b, stream);
  };
  try {
    s = await PipelineIntegrationSession.create(options);
    assert.equal(native(s).gameType, 'singles');
    assert.equal(tap.host().inspect(env(s)).writers.length, 0);
    assert.ok(s.getNativeBirthHolding('p1'));
    witness('override', { actual_session_with_synthetic_own_producer_override: true, no_tentative_switch_writer: true,
      generated_mod_reachability: 'not-certified' });
  } finally { SwitchEventHost.prototype.attachBirth = attach; tap.restore(); await s?.close(); }
});
