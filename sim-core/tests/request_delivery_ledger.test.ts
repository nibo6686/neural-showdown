import assert from 'node:assert/strict';
import test from 'node:test';
import { BattleStream, Teams } from 'pokemon-showdown';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession, projectPipelineStepResult, type PipelineBoundary } from '../src/pipeline_integration';
import { RequestDeliveryLedger } from '../src/request_delivery_ledger';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID, StepResult } from '../src/types';
import type { ObservableBattleState } from '../src/observable_state';
import { canonicalActionFromLegalAction } from '../src/canonical_action';

const options = { battle_id: 'prompt25', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const owners = ['p1', 'p2'] as const;
const history = (s: PipelineIntegrationSession, owner: PlayerID) => s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(owner), owner);
const environment = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const trace = (e: LocalBattleEnv, owner: PlayerID) => e.inspectRequestEmissionTrace(e.getRequestEmissionTraceHandle(owner), owner);

async function initial() {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  let result!: StepResult;
  LocalBattleEnv.prototype.resetWithOptions = async function(...args) { result = await reset.apply(this, args); return result; };
  try { const s = await PipelineIntegrationSession.create(options); return { s, result }; }
  finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}
async function controlled(p1: string, p2: string) {
  const generate = Teams.generate; let count = 0;
  Teams.generate = function() { return Teams.import(count++ % 2 === 0 ? p1 : p2)!; };
  try { return await initial(); } finally { Teams.generate = generate; }
}
const splash = 'Snorlax\nAbility: Immunity\n- Splash\n\nBlissey\n- Splash';

test('genuine native Random Battle: both-owner literal oracles, initial and two consecutive committed transitions', async () => {
  const push = BattleStream.prototype.pushMessage, consume = PlayerStateExtractor.prototype.consumeChunk;
  const producers: Record<PlayerID, string[]> = { p1: [], p2: [] }, receipts: Record<PlayerID, string[]> = { p1: [], p2: [] };
  BattleStream.prototype.pushMessage = function(type, data) {
    if (type === 'sideupdate' && typeof data === 'string') {
      const i = data.indexOf('\n'), owner = data.slice(0, i) as PlayerID, line = data.slice(i + 1);
      if (owners.includes(owner) && line.startsWith('|request|')) producers[owner].push(line);
    }
    return push.call(this, type, data);
  };
  PlayerStateExtractor.prototype.consumeChunk = function(chunk) {
    const owner = (this as any).player as PlayerID;
    for (const line of chunk.split('\n')) if (line.startsWith('|request|')) receipts[owner].push(line);
    return consume.call(this, chunk);
  };
  let s: PipelineIntegrationSession | undefined;
  try {
    s = (await initial()).s;
    const occurrence = history(s, 'p1').boundaries[0].session_occurrence;
    for (let step = 0; step <= 2; step++) {
      for (const owner of owners) {
        const h = history(s, owner), row = h.boundaries.at(-1)!;
        const observation: ObservableBattleState = s.boundary.perspectives[owner].observation;
        assert.equal(h.boundaries.length, step + 1); assert.equal(h.deliveries.length, step + 1);
        assert.equal(row.current!.sequence, step); assert.equal(row.session_occurrence, occurrence);
        assert.equal(row.observation_id, observation.observation_id); assert.deepEqual(row.prefix, observation.protocol_prefix);
        assert.equal(row.boundary_cursor, observation.event_cursor); assert.equal(row.branch_id, s.boundary.branch_id);
        assert.equal(row.selected, row.trace.at(-1)); assert.equal(row.selected!.request_record, producers[owner].at(-1));
        assert.equal(row.selected!.receipt.record, receipts[owner].at(-1));
        assert.equal(row.selected!.owner_emission_index, step ? 2 : 1);
        assert.deepEqual(row.trace.map(r => r.origin), step ? ['restore_reemit', 'native_emission'] : ['native_emission']);
        if (step) {
          assert.equal(row.parent!.observation_id, h.boundaries[step - 1].observation_id);
          assert.notEqual(row.selected!.producer_occurrence, h.boundaries[step - 1].selected!.producer_occurrence);
          assert.deepEqual(row.prefix.slice(0, h.boundaries[step - 1].prefix.length), h.boundaries[step - 1].prefix);
        }
        assert.ok(Object.isFrozen(h) && Object.isFrozen(h.deliveries) && Object.isFrozen(row.prefix));
        assert.ok(!JSON.stringify(s.boundary).includes('delivery_reference'));
      }
      if (step < 2) await s.step();
    }
  } finally { BattleStream.prototype.pushMessage = push; PlayerStateExtractor.prototype.consumeChunk = consume; await s?.close(); }
});

test('equal-label foreign sessions, other owner and transported diagnostic/capability controls reject', async () => {
  const a = await initial(), b = await initial();
  try {
    const handle = a.s.getRequestDeliveryHandle('p1'), row = history(a.s, 'p1').boundaries[0];
    assert.equal(a.s.boundary.perspectives.p1.observation.observation_id, b.s.boundary.perspectives.p1.observation.observation_id);
    assert.throws(() => b.s.readRequestDeliveryHistory(handle, 'p1'), /foreign-or-forged/);
    assert.throws(() => a.s.readRequestDeliveryHistory(handle, 'p2'), /foreign-or-forged/);
    for (const copied of [{}, structuredClone(handle), JSON.parse(JSON.stringify(handle)), row.session_occurrence, row.current!.delivery_reference]) {
      assert.throws(() => a.s.readRequestDeliveryHistory(copied, 'p1'), /foreign-or-forged/);
    }
    for (const changes of [{ owner: 'p2' }, { observation_id: 'foreign' }, { branch_id: 'foreign' }, { parent: { observation_id: row.observation_id, branch_id: row.branch_id, step_index: 0 } }, { prefix: row.prefix.map((r, i) => i ? r : '|turn|999') }, {}]) {
      const coherentForeign = { ...row, ...changes } as any;
      assert.equal(coherentForeign.step_index, row.step_index);
      assert.throws(() => a.s.readRequestDeliveryHistory(handle, 'p1', coherentForeign), /foreign-boundary-binding/);
    }
    assert.throws(() => a.s.readRequestDeliveryHistory(handle, 'p1', history(b.s, 'p1').boundaries[0]), /foreign-boundary/);
    assert.equal(a.s.readRequestDeliveryHistory(handle, 'p1', row).boundaries[0], row);
  } finally { await a.s.close(); await b.s.close(); }
});

test('last FIFO selection: superseded requests and equal-text repetitions never backward-match', async () => {
  const { s, result } = await controlled(splash, splash), ledger = new RequestDeliveryLedger();
  try {
    const env = environment(s), first = trace(env, 'p1')[0];
    await (env as any).battleStream.write('>eval p1.emitRequest(p1.activeRequest); p1.emitRequest(p1.activeRequest);');
    const equal = await env.stepWithOptions({}, { include_wait_requests: true });
    ledger.commit(ledger.prepare(env, equal, s.boundary, null));
    const row = ledger.read(ledger.handle('p1'), 'p1').boundaries[0];
    assert.equal(row.trace.length, 3); assert.equal(row.selected!.owner_emission_index, 3);
    assert.equal(row.selected!.request_record, first.request_record); assert.equal(row.current!.sequence, 0);
    await (env as any).battleStream.write('>eval p1.emitRequest({...p1.activeRequest, wait:true});');
    await env.stepWithOptions({}, { include_wait_requests: true });
    const second = new RequestDeliveryLedger();
    assert.throws(() => second.prepare(env, result, s.boundary, null), /settled-request-mismatch/);
    assert.deepEqual(second.read(second.handle('p1'), 'p1').boundaries, []);
  } finally { ledger.revoke(); await s.close(); }
});

test('held restore continuity retains parent reference without advancing sequence; copied/missing parent cannot', async () => {
  const { s, result } = await controlled(splash, splash), ledger = new RequestDeliveryLedger();
  const restored = new LocalBattleEnv('restore-ledger', options.format, options.seed);
  try {
    ledger.commit(ledger.prepare(environment(s), result, s.boundary, null));
    const parent = s.boundary, historyBefore = ledger.read(ledger.handle('p1'), 'p1');
    const resumed = await restored.resetFromSerialized(environment(s).serializeBattle(), { include_wait_requests: true });
    const proof = ledger.restored(restored, resumed, parent);
    // Synthetic boundary model only: actual native restore and held history are the source evidence.
    const next = { ...parent, step_index: 1, branch_id: 'synthetic-restore-continuity' } as PipelineBoundary;
    assert.throws(() => ledger.prepare(restored, resumed, next, parent, structuredClone(proof)), /missing-restore/);
    assert.throws(() => ledger.restored(restored, resumed, structuredClone(parent)), /foreign-parent/);
    ledger.commit(ledger.prepare(restored, resumed, next, parent, proof));
    for (const owner of owners) {
      const h = ledger.read(ledger.handle(owner), owner);
      assert.equal(h.deliveries.length, 1); assert.equal(h.boundaries[1].current, h.boundaries[0].current);
      assert.equal(h.boundaries[1].selected!.origin, 'restore_reemit');
    }
    assert.equal(historyBefore.boundaries.length, 1);
    const missing = new RequestDeliveryLedger();
    assert.throws(() => missing.prepare(restored, resumed, parent, null), /missing-parent-delivery/);
    assert.throws(() => missing.commit({}), /foreign-or-stale/);
  } finally { ledger.revoke(); await restored.close(); await s.close(); }
});

test('accepted equal-text native deliveries still get new sequences, not restore references', async () => {
  const { s, result } = await controlled(splash, splash), ledger = new RequestDeliveryLedger();
  const envs: LocalBattleEnv[] = [];
  try {
    ledger.commit(ledger.prepare(environment(s), result, s.boundary, null));
    let parent = s.boundary, previous = environment(s);
    for (let i = 1; i <= 2; i++) {
      const env = new LocalBattleEnv('equal-native', options.format, options.seed); envs.push(env);
      const resumed = await env.resetFromSerialized(previous.serializeBattle(), { include_wait_requests: true });
      const proof = ledger.restored(env, resumed, parent);
      await (env as any).battleStream.write('>eval p1.emitRequest(p1.activeRequest); p2.emitRequest(p2.activeRequest);');
      const fresh = await env.stepWithOptions({}, { include_wait_requests: true });
      // Test-only settled-boundary model, with real unchanged native requests.
      const next = { ...parent, step_index: i, branch_id: `equal-native-${i}` };
      ledger.commit(ledger.prepare(env, fresh, next, parent, proof)); parent = next; previous = env;
    }
    for (const owner of owners) {
      const h = ledger.read(ledger.handle(owner), owner); assert.deepEqual(h.deliveries.map(d => d.sequence), [0, 1, 2]);
      assert.equal(h.deliveries[0].source.request_record, h.deliveries[1].source.request_record);
      assert.notEqual(h.deliveries[0].delivery_reference, h.deliveries[1].delivery_reference);
    }
  } finally { ledger.revoke(); for (const env of envs) await env.close(); await s.close(); }
});

for (const failure of ['rejection', 'second-owner', 'bundle'] as const) test(`real rejected candidate (${failure}) is atomic; valid continuation preserves parent history`, async () => {
  const { s } = await initial(), before = { p1: history(s, 'p1'), p2: history(s, 'p2') }, boundary = s.boundary;
  const diagnostics = LocalBattleEnv.prototype.diagnostics, inspect = LocalBattleEnv.prototype.inspectRequestEmissionTrace;
  const freeze = Object.freeze;
  try {
    if (failure === 'rejection') LocalBattleEnv.prototype.diagnostics = function() {
      const d = diagnostics.call(this) as any; return this.id.includes('step-') ? { ...d, last_error: 'synthetic rejection' } : d;
    };
    if (failure === 'second-owner') LocalBattleEnv.prototype.inspectRequestEmissionTrace = function(handle, owner) {
      const rows = inspect.call(this, handle, owner);
      if (this.id.includes('step-') && owner === 'p2' && rows.at(-1)?.origin === 'native_emission') throw new Error('synthetic second-owner failure');
      return rows;
    };
    if (failure === 'bundle') Object.freeze = function<T>(value: T): Readonly<T> {
      // Test-only fault at bundle construction, after ordinary observation/belief validation.
      if ((value as any)?.schema_version === 'pipeline-linked-record/v1' && (value as any).perspective === 'p2') (value as any).source_ref = 'foreign-source';
      return freeze(value);
    };
    await assert.rejects(s.step(), (error: Error) => {
      assert.match(error.message, /rejected-action|second-owner|invalid|mismatch/);
      if (failure === 'bundle') assert.match(error.stack!, /validatePipelineEpisodeRecordBundle/);
      return true;
    });
    assert.equal(s.boundary, boundary);
    for (const owner of owners) assert.equal(history(s, owner), before[owner]);
    LocalBattleEnv.prototype.diagnostics = diagnostics; LocalBattleEnv.prototype.inspectRequestEmissionTrace = inspect; Object.freeze = freeze;
    await s.step();
    for (const owner of owners) { assert.equal(history(s, owner).deliveries.length, 2); assert.equal(history(s, owner).deliveries[1].sequence, 1); }
  } finally { LocalBattleEnv.prototype.diagnostics = diagnostics; LocalBattleEnv.prototype.inspectRequestEmissionTrace = inspect; Object.freeze = freeze; await s.close(); }
});

test('post-commit retirement error keeps ledger; close revokes synchronously even when cleanup fails', async () => {
  const { s } = await initial(), old = environment(s), close = old.close;
  const handle = s.getRequestDeliveryHandle('p1');
  old.close = async function() { throw new Error('synthetic retirement'); };
  try {
    await s.step(); assert.equal(history(s, 'p1').deliveries.length, 2);
    old.close = close;
    const current = environment(s), end = current.close;
    current.close = async function() { assert.throws(() => s.readRequestDeliveryHistory(handle, 'p1'), /closed/); throw new Error('synthetic close'); };
    await assert.rejects(s.close(), /synthetic close/);
    assert.throws(() => s.getRequestDeliveryHandle('p1'), /closed/);
    current.close = end; await current.close(); await old.close();
  } finally { old.close = close; await s.close(); await old.close(); }
});

test('terminal/requestless observations retain history without current authority or invented sequences', async () => {
  const { s, result } = await controlled(splash, splash), ledger = new RequestDeliveryLedger(), env = environment(s);
  try {
    ledger.commit(ledger.prepare(env, result, s.boundary, null));
    const parent = s.boundary, restored = new LocalBattleEnv('terminal-ledger', options.format, options.seed);
    try {
      const resumed = await restored.resetFromSerialized(env.serializeBattle(), { include_wait_requests: true });
      const proof = ledger.restored(restored, resumed, parent);
      await (restored as any).battleStream.write('>forcewin p1');
      const ended = await restored.stepWithOptions({}, { include_wait_requests: true });
      const next = { ...parent, step_index: 1 };
      ledger.commit(ledger.prepare(restored, ended, next, parent, proof));
      for (const owner of owners) {
        const h = ledger.read(ledger.handle(owner), owner); assert.equal(h.deliveries.length, 1);
        assert.equal(h.boundaries[1].current, null); assert.equal(h.boundaries[1].selected, null);
        assert.ok(h.boundaries[1].trace.length);
      }
    } finally { await restored.close(); }
  } finally { ledger.revoke(); await s.close(); }
});

for (const owner of owners) test(`actual session force/wait/revival commitments include nonactor ${owner}`, async () => {
  const other: PlayerID = owner === 'p1' ? 'p2' : 'p1';
  const cases = [
    { label: 'force', own: 'Mewtwo\nAbility: Pressure\n- Psystrike\n- Splash\n\nBlissey\n- Splash', foe: 'Magikarp\n- Splash\n\nSnorlax\n- Splash' },
    { label: 'revival', own: 'Lead (Snorlax)\nAbility: Immunity\n- Memento\n\nPawmot\n- Revival Blessing\n- Splash', foe: 'Terminus (Snorlax)\nAbility: Immunity\n- Splash\n- Memento\n\nReserve (Blissey)\n- Splash' },
  ];
  for (const c of cases) {
    const { s } = await controlled(owner === 'p1' ? c.own : c.foe, owner === 'p1' ? c.foe : c.own);
    const action = (p: PlayerID, choice: string) => {
      const r = s.boundary.perspectives[p].observation.request!;
      const a = r.legal_actions.actions.find(a => a?.choice === choice)!;
      assert.ok(a); return canonicalActionFromLegalAction(r, a.index, p);
    };
    try {
      await s.step({ [owner]: action(owner, 'move 1'), [other]: action(other, 'move 1') } as any);
      if (c.label === 'revival') {
        await s.stepForcedSwitch(action(owner, 'switch 2'));
        await s.step({ [owner]: action(owner, 'move 1'), [other]: action(other, 'move 2') } as any);
      }
      const selector = c.label === 'force' ? other : owner;
      const waiting = selector === owner ? other : owner;
      const h = history(s, waiting), row = h.boundaries.at(-1)!;
      assert.ok(JSON.parse(row.selected!.request_json).wait);
      assert.equal(row.current!.source.origin, 'native_emission');
      assert.equal(history(s, selector).boundaries.at(-1)!.current!.source.origin, 'native_emission');
      const r = s.boundary.perspectives[selector].observation.request!;
      const legal = r.legal_actions.actions.find(a => a?.kind === (c.label === 'force' ? 'switch' : 'revive'))!;
      const selected = canonicalActionFromLegalAction(r, legal.index, selector);
      const before = history(s, waiting).deliveries.length;
      if (c.label === 'force') await s.stepForcedSwitch(selected); else await s.stepRevival(selected);
      assert.equal(history(s, waiting).deliveries.length, before + 1);
      assert.equal(history(s, waiting).boundaries.at(-1)!.parent!.observation_id, row.observation_id);
    } finally { await s.close(); }
  }
});

test('one-owner tentative preparation failure, stale commit and exact foreign parent-prefix controls', async () => {
  const { s, result } = await initial(), ledger = new RequestDeliveryLedger();
  const restored = new LocalBattleEnv('adversarial-join', options.format, options.seed);
  try {
    const prepared = ledger.prepare(environment(s), result, s.boundary, null);
    ledger.commit(prepared);
    assert.throws(() => ledger.commit(prepared), /foreign-or-stale/);
    const parent = s.boundary, resumed = await restored.resetFromSerialized(environment(s).serializeBattle(), { include_wait_requests: true });
    const proof = ledger.restored(restored, resumed, parent);
    const next = { ...parent, step_index: 1 };
    const before = ledger.read(ledger.handle('p1'), 'p1');
    const forged = structuredClone(next);
    forged.perspectives.p2.observation.protocol_prefix[0] = '|turn|999';
    assert.equal(forged.perspectives.p2.observation.protocol_prefix.length, parent.perspectives.p2.observation.protocol_prefix.length);
    assert.throws(() => ledger.prepare(restored, resumed, forged, parent, proof), /prefix-parent/);
    assert.equal(ledger.read(ledger.handle('p1'), 'p1'), before);
    const invalidRaw = { ...resumed, requests: { ...resumed.requests, p2: { ...resumed.requests.p2!, raw: { ...resumed.requests.p2!.raw as any, wrong: true } } } };
    assert.throws(() => ledger.prepare(restored, invalidRaw, next, parent, proof), /settled-request-mismatch/);
    assert.equal(ledger.read(ledger.handle('p1'), 'p1'), before);
    for (const changes of [{ perspective: 'p1' }, { event_cursor: parent.perspectives.p2.observation.event_cursor + 1 }]) {
      const wrong = structuredClone(next); Object.assign(wrong.perspectives.p2.observation, changes);
      assert.throws(() => ledger.prepare(restored, resumed, wrong, parent, proof), /observation-join/);
    }
    assert.throws(() => ledger.prepare(restored, resumed, next, structuredClone(parent), proof), /foreign-parent/);
    const twin = new RequestDeliveryLedger();
    twin.commit(twin.prepare(environment(s), result, parent, null));
    assert.throws(() => twin.prepare(restored, resumed, next, parent, proof), /missing-restore/);
    const p = ledger.prepare(restored, resumed, next, parent, proof);
    ledger.commit(p); assert.throws(() => ledger.commit(p), /foreign-or-stale/);
  } finally { ledger.revoke(); await restored.close(); await s.close(); }
});

test('failed initialization cannot escape a ledger; bare restore cannot invent original delivery', async () => {
  const generate = Teams.generate; let calls = 0;
  Teams.generate = function(...args) { if (++calls === 2) throw new Error('synthetic generation failure'); return generate.apply(this, args); };
  try { await assert.rejects(PipelineIntegrationSession.create(options), /generation failure/); }
  finally { Teams.generate = generate; }
  const { s } = await initial(), restored = new LocalBattleEnv('bare', options.format, options.seed), ledger = new RequestDeliveryLedger();
  try {
    const result = await restored.resetFromSerialized(environment(s).serializeBattle(), { include_wait_requests: true });
    assert.throws(() => ledger.prepare(restored, result, s.boundary, null), /missing-parent-delivery/);
    assert.deepEqual(ledger.read(ledger.handle('p1'), 'p1').deliveries, []);
    ledger.revoke(); assert.throws(() => ledger.handle('p1'), /revoked/);
  } finally { await restored.close(); await s.close(); }
});

test('actual team-preview auto-default remains an unselected intermediate emission', async () => {
  const generate = Teams.generate; Teams.generate = function() { return Teams.import(splash)!; };
  let s: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create({ ...options, format: 'gen9ou' });
    for (const owner of owners) {
      const h = history(s, owner), row = h.boundaries[0];
      assert.ok(row.trace.some(r => JSON.parse(r.request_json).teamPreview));
      assert.ok(!JSON.parse(row.selected!.request_json).teamPreview);
      assert.equal(row.selected, row.trace.at(-1)); assert.equal(h.deliveries.length, 1);
    }
  } finally { Teams.generate = generate; await s?.close(); }
});

test('actual consumed-restored request is suppressed; retain receipt without selected binding', async () => {
  const { s, result } = await controlled(splash, splash), ledger = new RequestDeliveryLedger(), env = environment(s);
  const restored = new LocalBattleEnv('consumed', options.format, options.seed);
  try {
    ledger.commit(ledger.prepare(env, result, s.boundary, null));
    const parent = s.boundary;
    await env.stepWithOptions({ p1: 'move 1' }, { include_wait_requests: true });
    const resumed = await restored.resetFromSerialized(env.serializeBattle(), { include_wait_requests: true });
    assert.equal(resumed.requests.p1, null); assert.ok(resumed.requests.p2);
    const proof = ledger.restored(restored, resumed, parent);
    const observations = projectPipelineStepResult(resumed, s.battle_id, [...parent.perspectives.p1.observation.protocol_prefix]);
    const next = { ...parent, step_index: 1, perspectives: {
      p1: { ...parent.perspectives.p1, observation: observations.p1 },
      p2: { ...parent.perspectives.p2, observation: observations.p2 },
    } };
    ledger.commit(ledger.prepare(restored, resumed, next, parent, proof));
    const h = ledger.read(ledger.handle('p1'), 'p1');
    assert.equal(h.boundaries[1].trace.length, 1); assert.equal(h.boundaries[1].trace[0].origin, 'restore_reemit');
    assert.equal(h.boundaries[1].selected, null); assert.equal(h.boundaries[1].current, null); assert.equal(h.deliveries.length, 1);
    assert.equal(ledger.read(ledger.handle('p2'), 'p2').boundaries[1].current!.sequence, 0);
  } finally { ledger.revoke(); await restored.close(); await s.close(); }
});

test('accepted legacy unstarted restore stays usable without any delivery ledger authority', async () => {
  const donor = new LocalBattleEnv('legacy-donor', options.format, options.seed), reset = LocalBattleEnv.prototype.resetWithOptions;
  let s: PipelineIntegrationSession | undefined;
  try {
    await donor.reset(); const snapshot = donor.serializeBattle();
    LocalBattleEnv.prototype.resetWithOptions = function(opts) { return this.resetFromSerialized(structuredClone(snapshot), opts); };
    s = await PipelineIntegrationSession.create(options);
    assert.throws(() => s!.getRequestDeliveryHandle('p1'), /revoked/);
    assert.throws(() => s!.getOriginalOwnerHolding('p1'), /inactive/);
    await s.step();
    for (const owner of owners) assert.throws(() => s!.getRequestDeliveryHandle(owner), /revoked/);
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; await s?.close(); await donor.close(); }
});
