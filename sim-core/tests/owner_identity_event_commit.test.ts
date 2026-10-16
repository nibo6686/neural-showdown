import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle } from 'pokemon-showdown';
import { SwitchEventHost, type CommittedSwitchEvent, type SwitchEventHistory } from '../src/owner_identity_events';
import { RequestDeliveryLedger } from '../src/request_delivery_ledger';
import { NativeObjectAssociation } from '../src/owner_identity_crosswalk';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import type { PlayerID } from '../src/types';
const owners = ['p1', 'p2'] as const;
const options = { battle_id: 'P46', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const env = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const native = (s: PipelineIntegrationSession): Battle => (env(s) as any).battleStream.battle;
const history = (s: PipelineIntegrationSession, owner: PlayerID): SwitchEventHistory => s.readSwitchEventHolding(s.getSwitchEventHolding(owner), owner);
const actions = (s: PipelineIntegrationSession) => Object.fromEntries(owners.map(owner => {
  const r = env(s).getRequest(owner)!;
  const i = r.legal_actions.available_indices.find(at => r.legal_actions.actions[at]?.choice === 'switch 2');
  assert.notEqual(i, undefined); return [owner, canonicalActionFromLegalAction(r, i!)];
})) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
const witness = (name: string, data: object) => console.log('P46_WITNESS ' + JSON.stringify({ name, ...data }));
function tapHost() {
  const attach = SwitchEventHost.prototype.attachBirth; let host: SwitchEventHost;
  SwitchEventHost.prototype.attachBirth = function(...args) { host = this; return attach.apply(this, args); };
  return { host: () => host!, restore: () => { SwitchEventHost.prototype.attachBirth = attach; } };
}
// Independent uninterrupted native oracle: decode split triples physically, then the finite framing policy.
function oracle(log: string[]) {
  const publicRecords: string[] = [];
  for (let i = 0; i < log.length; i++) {
    if (/^\|split\|p[12]$/.test(log[i])) { if (log[i + 2]) publicRecords.push(log[i + 2]); i += 2; }
    else if (log[i]) publicRecords.push(log[i]);
  }
  const prefix: string[] = [], indices: Array<{ publicIndex: number; prefixIndex: number; owner: PlayerID }> = [];
  publicRecords.forEach((line, i) => {
    if (line === '|' || line.startsWith('|tier|')) return;
    for (const owner of owners) if (line.startsWith('|switch|' + owner + 'a:')) indices.push({ publicIndex: i, prefixIndex: prefix.length, owner });
    prefix.push(line.startsWith('|t:|') ? '|t:|0' : line);
  });
  return { prefix, indices };
}

test('P46 committed generated indices histories and privacy', async () => {
  let s: PipelineIntegrationSession | undefined, control: Battle | undefined, sibling: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create(options);
    control = new Battle({ formatid: options.format, seed: '1,2,3,4' });
    for (const owner of owners) control.setPlayer(owner, { name: owner === 'p1' ? 'Agent-1' : 'Agent-2',
      team: s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(owner), owner).packed_team });
    const controlObjects = { p1: control.p1!.pokemon.slice(), p2: control.p2!.pokemon.slice() };
    const old = owners.map(owner => history(s!, owner)), oldHandles = owners.map(owner => s!.getSwitchEventHolding(owner));
    const states: unknown[] = [];
    for (const count of [1, 2, 3]) {
      if (count > 1) { await s.step(actions(s)); control.choose('p1', 'switch 2'); control.choose('p2', 'switch 2'); }
      const expected = oracle(control.log);
      assert.deepEqual(s.boundary.perspectives.p1.observation.protocol_prefix, expected.prefix);
      for (const owner of owners) {
        const events: readonly CommittedSwitchEvent[] = history(s, owner).events;
        const indices = expected.indices.filter(i => i.owner === owner);
        assert.deepEqual(events.map(e => e.original_slot), [1, 2, 1].slice(0, count));
        assert.deepEqual(events.map(e => [e.public_index, e.prefix_index]), indices.map(i => [i.publicIndex, i.prefixIndex]));
        const literal = owner === 'p1' ? [[15, 13], [20, 17], [28, 23]] : [[16, 14], [21, 18], [27, 22]];
        assert.deepEqual(events.map(e => [e.public_index, e.prefix_index]), literal.slice(0, count));
        assert.deepEqual(events.map(e => e.event_index), Array.from({ length: count }, (_, i) => i));
        assert.equal(controlObjects[owner].indexOf(control[owner]!.active[0]!) + 1, [1, 2, 1][count - 1]);
        assert.ok(Object.isFrozen(events) && events.every(Object.isFrozen));
        assert.equal(events.at(-1)!.step_index, s.boundary.step_index);
        if (count === 3) {
          assert.equal(expected.prefix[events[0].prefix_index], expected.prefix[events[2].prefix_index]);
          assert.notEqual(events[0].prefix_index, events[2].prefix_index);
        }
      }
      states.push(owners.map(owner => history(s!, owner).events));
    }
    for (const [i, owner] of owners.entries()) {
      assert.equal(old[i].events.length, 1);
      assert.throws(() => s!.readSwitchEventHolding(oldHandles[i], owner), /stale-event-holding/);
      assert.throws(() => s!.readSwitchEventHolding({ ...s!.getSwitchEventHolding(owner) }, owner), /copied-or-stale/);
      assert.throws(() => s!.readSwitchEventHolding(s!.getSwitchEventHolding(owner), owner === 'p1' ? 'p2' : 'p1'), /copied-or-stale/);
    }
    sibling = await PipelineIntegrationSession.create({ ...options, battle_id: 'P46-other' });
    assert.throws(() => s!.readSwitchEventHolding(sibling!.getSwitchEventHolding('p1'), 'p1'), /copied-or-stale/);
    const output = JSON.stringify({ boundary: s.boundary, snapshot: (s as any).snapshot, diagnostic: env(s).diagnostics() });
    for (const forbidden of ['original_slot', 'prefix_index', 'SwitchEvent', 'leases', 'writer']) assert.ok(!output.includes(forbidden));
    const h = s.getSwitchEventHolding('p1'); await s.close(); assert.throws(() => s!.readSwitchEventHolding(h, 'p1'), /closed/);
    witness('indices', { actual_generated_creation_and_two_held_reentries: true, owner_histories: states,
      uninterrupted_native_oracle: true, retained_frozen_evidence: true, old_handles_stale: true, wire_sidecar_absent: true });
  } finally { control?.destroy(); await s?.close(); await sibling?.close(); }
});

test('P46 positional filter splice and receipt faults', async () => {
  const tap = tapHost(), prepare = SwitchEventHost.prototype.prepare, received = SwitchEventHost.prototype.received, attachRestored = SwitchEventHost.prototype.attachRestored;
  let s: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create(options);
    const host = tap.host(), b = native(s), e = env(s);
    const fixture = ['|', '|tier|[Gen 9] Random Battle', '|t:|123', '|turn|1'];
    assert.deepEqual(projectPipelineProtocolPrefix(fixture, s.getReaderContext()), ['|t:|0', '|turn|1']);
    b.addMove('move', 'p1a: A', 'Tackle', 'p2a: B'); b.retargetLastMove(b.p2!.pokemon[0]);
    b.log.splice(b.log.length - 1, 1);
    const held = history(s, 'p1'), handle = s.getSwitchEventHolding('p1'), boundary = s.boundary;
    for (const fault of ['missing', 'duplicate', 'foreign-stream', 'parent', 'snapshot', 'future', 'writer', 'historical-marker', 'historical-secret', 'late-marker']) {
      let candidate: object | undefined, once = false;
      SwitchEventHost.prototype.received = function(world, stream, chunk) {
        candidate = world;
        if (!once) {
          once = true;
          if (fault === 'missing') return;
          if (fault === 'foreign-stream') return received.call(this, world, {}, chunk);
          received.call(this, world, stream, chunk);
          if (fault === 'duplicate') received.call(this, world, stream, chunk);
          return;
        }
        return received.call(this, world, stream, chunk);
      };
      SwitchEventHost.prototype.prepare = function(world, next, snapshot, positions, parent) {
        if (fault === 'parent') parent = { ...parent! };
        if (fault === 'snapshot') snapshot = { ...snapshot };
        if (fault === 'future') positions = { ...positions, prefix: positions.prefix.slice(0, -1) };
        if (fault.startsWith('historical-')) {
          const oldBattle: Battle = (world as any).battleStream.battle;
          const marker = oldBattle.log.findIndex(line => line === '|split|p1');
          assert.ok(marker >= 0);
          if (fault === 'historical-marker') oldBattle.log[marker] += '|bad';
          else oldBattle.log.splice(marker + 1, 1);
        }
        if (fault === 'writer') {
          const nativeBattle: Battle = (world as any).battleStream.battle;
          const proof = this.inspect(world), row = proof.rows.findIndex(r => r.token === proof.writers[0].rows[1]);
          nativeBattle.log[row] += '|bad';
        }
        const token = prepare.call(this, world, next, snapshot, positions, parent);
        if (fault === 'late-marker') {
          const late: Battle = (world as any).battleStream.battle;
          const marker = late.log.findIndex(line => line === '|split|p1'); late.log[marker] += '|late';
        }
        return token;
      };
      const rejection = ['missing', 'duplicate', 'foreign-stream'].includes(fault) ? /switch-events\/v1\/unavailable-log-proof/
        : fault === 'parent' ? /switch-events\/v1\/foreign-event-parent/ : fault === 'snapshot' ? /switch-events\/v1\/foreign-event-snapshot/
        : fault === 'future' ? /switch-events\/v1\/future-or-mismatched-cutoff/ : /switch-events\/v1\/invalid-switch-writer/;
      await assert.rejects(s.step(actions(s)), rejection);
      witness(fault, { expected: rejection.source });
      assert.equal(s.boundary, boundary); assert.equal(s.getSwitchEventHolding('p1'), handle); assert.equal(history(s, 'p1'), held);
      assert.throws(() => host.inspect(candidate!), /unavailable-world/);
      SwitchEventHost.prototype.received = received; SwitchEventHost.prototype.prepare = prepare;
    }
    let moveStimuli = 0;
    SwitchEventHost.prototype.attachRestored = function(world, b, stream, ticket) {
      attachRestored.call(this, world, b, stream, ticket);
      const send = b.sendUpdates, host = this;
      b.sendUpdates = function() {
        const lastMove = b.lastMoveLine;
        b.addMove('move', 'p1a: A', 'Tackle', 'p2a: B');
        const row = host.inspect(world).rows.at(-1)!;
        b.retargetLastMove(b.p2!.pokemon[0]);
        assert.equal(host.inspect(world).rows.at(-1)!.token, row.token);
        assert.equal(host.inspect(world).rows.at(-1)!.version, row.version + 1);
        b.log.splice(b.log.length - 1, 1); b.lastMoveLine = lastMove;
        moveStimuli++; b.sendUpdates = send; return send.call(b);
      };
    };
    await s.step(actions(s)); assert.equal(history(s, 'p1').events.length, 2); assert.equal(moveStimuli, 1);
    witness('faults', { actual_session_policy_rejections: 10, supported_move_version_splice_stimulus_before_committed_send: true,
      framing_tier_time_fixture: true, exact_prior_handles_and_retry: true });
  } finally { SwitchEventHost.prototype.received = received; SwitchEventHost.prototype.prepare = prepare; SwitchEventHost.prototype.attachRestored = attachRestored; tap.restore(); await s?.close(); }
});

test('P46 creation successor final barrier rollback and retry', async () => {
  const tap = tapHost(), preflight = SwitchEventHost.prototype.preflight, close = LocalBattleEnv.prototype.close;
  const di = RequestDeliveryLedger.prototype.installReady, bi = NativeObjectAssociation.prototype.installReady, ei = SwitchEventHost.prototype.installReady;
  const dp = RequestDeliveryLedger.prototype.preflight, bp = NativeObjectAssociation.prototype.preflight;
  let deliveryToken: object, associationToken: object, eventToken: object, deliveryController: RequestDeliveryLedger, associationController: NativeObjectAssociation;
  RequestDeliveryLedger.prototype.preflight = function(token) { dp.call(this, token); deliveryToken = token; deliveryController = this; };
  NativeObjectAssociation.prototype.preflight = function(token) { bp.call(this, token); associationToken = token; associationController = this; };
  let s: PipelineIntegrationSession | undefined, mode = 'creation', installs = 0, cleanup = 0;
  RequestDeliveryLedger.prototype.installReady = function() { installs++; return di.call(this); };
  NativeObjectAssociation.prototype.installReady = function() { installs++; return bi.call(this); };
  SwitchEventHost.prototype.installReady = function() { installs++; return ei.call(this); };
  SwitchEventHost.prototype.preflight = function(token) { preflight.call(this, token); eventToken = token; throw new Error('P46-all-prepared-' + mode); };
  LocalBattleEnv.prototype.close = async function() { cleanup++; assert.throws(() => tap.host().inspect(this), /unavailable-world/);
    assert.throws(() => tap.host().preflight(eventToken), /foreign-or-stale/);
    assert.throws(() => deliveryController.preflight(deliveryToken), /revoked/);
    assert.throws(() => associationController.preflight(associationToken), /unavailable/); return close.call(this); };
  try {
    await assert.rejects(PipelineIntegrationSession.create(options), /P46-all-prepared-creation/); assert.equal(installs, 0); assert.equal(cleanup, 1);
    SwitchEventHost.prototype.preflight = preflight; LocalBattleEnv.prototype.close = close;
    s = await PipelineIntegrationSession.create(options); assert.equal(installs, 3);
    const boundary = s.boundary, currentEnv = env(s);
    const before = owners.map(owner => ({ eventHandle: s!.getSwitchEventHolding(owner), event: history(s!, owner),
      deliveryHandle: s!.getRequestDeliveryHandle(owner), delivery: s!.readRequestDeliveryHistory(s!.getRequestDeliveryHandle(owner), owner),
      nativeHandle: s!.getNativeObjectHolding(owner), native: s!.readNativeObjectHolding(s!.getNativeObjectHolding(owner), owner) }));
    mode = 'successor'; installs = 0;
    SwitchEventHost.prototype.preflight = function(token) { preflight.call(this, token); eventToken = token; throw new Error('P46-all-prepared-successor'); };
    LocalBattleEnv.prototype.close = async function() { assert.throws(() => tap.host().inspect(this), /unavailable-world/);
      assert.throws(() => tap.host().preflight(eventToken), /foreign-or-stale/);
      assert.throws(() => deliveryController.preflight(deliveryToken), /foreign-or-stale/);
      assert.throws(() => associationController.preflight(associationToken), /foreign-or-stale/); return close.call(this); };
    await assert.rejects(s.step(actions(s)), /P46-all-prepared-successor/); assert.equal(installs, 0); assert.equal(s.boundary, boundary); assert.equal(env(s), currentEnv);
    for (const [i, owner] of owners.entries()) {
      assert.equal(s.getSwitchEventHolding(owner), before[i].eventHandle); assert.equal(history(s, owner), before[i].event);
      assert.equal(s.getRequestDeliveryHandle(owner), before[i].deliveryHandle);
      assert.equal(s.readRequestDeliveryHistory(before[i].deliveryHandle, owner), before[i].delivery);
      assert.equal(s.getNativeObjectHolding(owner), before[i].nativeHandle); assert.equal(s.readNativeObjectHolding(before[i].nativeHandle, owner), before[i].native);
    }
    SwitchEventHost.prototype.preflight = preflight; LocalBattleEnv.prototype.close = close;
    await s.step(actions(s)); assert.equal(installs, 3); assert.equal(history(s, 'p1').events.length, 2);
    // Accepted disposal failure: publication stands and retirement retries during close.
    let failed = false;
    LocalBattleEnv.prototype.close = async function() { if (this === env(s!) && !failed) return close.call(this); if (!failed) { failed = true; throw new Error('P46-disposal'); } return close.call(this); };
    await s.step(actions(s)); assert.equal(failed, true); assert.equal(history(s, 'p1').events.length, 3);
    witness('atomicity', { actual_final_preflight_creation_and_successor_faults: true, zero_partial_component_installs: true, all_preparation_tokens_revoked_before_cleanup: true,
      all_committed_references_unchanged: true, fresh_retry_three_installs: true, postpublication_disposal_retained: true });
  } finally { SwitchEventHost.prototype.preflight = preflight; LocalBattleEnv.prototype.close = close;
    RequestDeliveryLedger.prototype.preflight = dp; NativeObjectAssociation.prototype.preflight = bp;
    RequestDeliveryLedger.prototype.installReady = di; NativeObjectAssociation.prototype.installReady = bi; SwitchEventHost.prototype.installReady = ei; tap.restore(); await s?.close(); }
});
