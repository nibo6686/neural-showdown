import assert from 'node:assert/strict';
import test from 'node:test';
import { BattleStream } from 'pokemon-showdown';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { SettlingBarrier, SettlingError, type SettlingOptions } from '../src/settling';

function clock() {
  let time = 0;
  const timers = new Set<() => void>();
  const options: SettlingOptions = {
    timeout_ms: 25, max_messages: 1000,
    now: () => time,
    schedule_timeout: (expire, ms) => {
      assert.equal(ms, 25);
      timers.add(expire);
      return () => { timers.delete(expire); };
    },
  };
  return { options, timers, expire() { for (const expire of [...timers]) expire(); }, advance() { time += 25; } };
}
function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => { resolve = done; });
  return { promise, resolve };
}
const SEED = [101, 202, 303, 404];
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
// These casts expose lifecycle signals only inside regressions, not production APIs.
function internals(env: LocalBattleEnv) {
  return env as unknown as { settling: SettlingBarrier; battleStream: BattleStream | null; consumerTasks: Promise<void>[] };
}

function assertFailure(error: unknown, code: string): boolean {
  assert.ok(error instanceof SettlingError, String(error));
  assert.equal(error.diagnostic.schema_version, 'settling-failure/v1');
  assert.equal(error.diagnostic.code, `settling/v1/${code}`);
  assert.deepEqual(Object.keys(error.diagnostic).sort(), ['code', 'max_messages', 'schema_version', 'timeout_ms']);
  return true;
}

test('barrier waits for both addressed requests and every public consumer, not an intermediate requestless update', async () => {
  const c = clock();
  const barrier = new SettlingBarrier(c.options);
  let decision = false;
  let resolved = false;
  const waiting = barrier.wait(() => decision ? 'decision' : null).then(() => { resolved = true; });
  barrier.emitted('update', '|turn|1');
  for (const p of ['p1', 'p2', 'spectator'] as const) barrier.acknowledge(p);
  await Promise.resolve();
  assert.equal(resolved, false);
  barrier.emitted('sideupdate', 'p1\n|request|{}');
  barrier.emitted('sideupdate', 'p2\n|request|{}');
  barrier.emitted('update', '|turn|2');
  decision = true;
  barrier.acknowledge('p1'); barrier.acknowledge('p1');
  barrier.acknowledge('p2');
  await Promise.resolve();
  assert.equal(resolved, false);
  barrier.acknowledge('p2');
  await Promise.resolve();
  assert.equal(resolved, false);
  barrier.acknowledge('spectator');
  await waiting;
  assert.equal(c.timers.size, 0);
  assert.equal(barrier.pendingWaits, 0);
});

test('terminal settling requires the end signal and all terminal deliveries; terminal EOF is normal', async () => {
  const c = clock();
  const barrier = new SettlingBarrier(c.options);
  let complete = false;
  const wait = barrier.wait(() => 'terminal').then(() => { complete = true; });
  await Promise.resolve();
  assert.equal(complete, false);
  barrier.emitted('update', '|tie|');
  barrier.emitted('end', '{"private":"not retained"}');
  barrier.streamClosed(); // EOF may precede delivery of its buffered terminal output.
  await Promise.resolve();
  assert.equal(complete, false);
  barrier.acknowledge('p1'); barrier.acknowledge('p2');
  barrier.streamClosed('p1');
  await Promise.resolve();
  assert.equal(complete, false);
  barrier.acknowledge('spectator');
  barrier.streamClosed();
  await wait;
  assert.equal(c.timers.size, 0);
});

for (const failure of ['timeout', 'message-limit', 'simulator-error', 'stream-closed', 'cancelled'] as const) {
  test(`controlled ${failure} releases barrier wait and timer`, async () => {
    const c = clock();
    const barrier = new SettlingBarrier({ ...c.options, max_messages: 1 });
    const rejection = assert.rejects(barrier.wait(() => null), (error) => assertFailure(error, failure));
    assert.equal(barrier.pendingWaits, 1);
    if (failure === 'timeout') c.expire();
    else if (failure === 'message-limit') { barrier.emitted('update', ''); barrier.emitted('update', ''); }
    else if (failure === 'stream-closed') barrier.streamClosed();
    else barrier.fail(failure);
    await rejection;
    assert.equal(barrier.pendingWaits, 0);
    assert.equal(c.timers.size, 0);
  });
}

test('deadline also bounds continuously arriving microtask output without waiting for a timer turn', async () => {
  const c = clock();
  const barrier = new SettlingBarrier(c.options);
  const rejected = assert.rejects(barrier.wait(() => null), (e) => assertFailure(e, 'timeout'));
  c.advance();
  barrier.emitted('update', '|turn|2');
  await rejected;
  assert.equal(c.timers.size, 0);
});

test('real simulator decision is not published until delayed spectator delivery completes', async () => {
  const c = clock();
  const env = new LocalBattleEnv('delayed', 'gen9randombattle', SEED, undefined, c.options);
  const control = new LocalBattleEnv('control', 'gen9randombattle', SEED);
  const seen = deferred();
  const original = SettlingBarrier.prototype.acknowledge;
  const held: { barrier: SettlingBarrier; consumer: 'spectator' }[] = [];
  try {
    const expected = await control.resetWithOptions(OPTIONS);
    SettlingBarrier.prototype.acknowledge = function (consumer) {
      if (consumer === 'spectator') { held.push({ barrier: this, consumer }); seen.resolve(); }
      else original.call(this, consumer);
    };
    let published = false;
    const reset = env.resetWithOptions(OPTIONS).then((r) => { published = true; return r; });
    await seen.promise;
    assert.equal(published, false);
    SettlingBarrier.prototype.acknowledge = original;
    for (const item of held) original.call(item.barrier, item.consumer);
    const actual = await reset;
    assert.deepEqual(actual.log_delta, expected.log_delta);
    assert.deepEqual(actual.requests, expected.requests);
    assert.equal(env.captureSeededSnapshot().state_fingerprint, control.captureSeededSnapshot().state_fingerprint);
    assert.equal(c.timers.size, 0);
  } finally {
    SettlingBarrier.prototype.acknowledge = original;
    await env.close(); await control.close();
  }
});

for (const mode of ['forcewin p1', 'forcetie']) {
  test(`real simulator ${mode} terminal output settles and restores exactly`, async () => {
    const env = new LocalBattleEnv('terminal', 'gen9randombattle', SEED);
    const restored = new LocalBattleEnv('terminal-restored', 'gen9randombattle', SEED);
    try {
      await env.resetWithOptions(OPTIONS);
      // Controlled engine command; terminal records/requests are produced by Showdown.
      const source = internals(env).battleStream!;
      const written = source.write(`>${mode}`);
      source.pushEnd(); // Buffered terminal delivery must survive normal source EOF.
      await written;
      const terminal = await env.stepWithOptions({}, OPTIONS);
      assert.equal(terminal.terminated, true);
      assert.equal(terminal.views.p1!.terminated, true);
      assert.equal(terminal.views.p2!.terminated, true);
      assert.equal(terminal.winner, mode === 'forcetie' ? 'tie' : 'p1');
      assert.equal(terminal.requests.p1, null);
      assert.equal(terminal.requests.p2, null);
      assert.ok(terminal.log_delta.some((l) => mode === 'forcetie' ? l === '|tie' : l.startsWith('|win|')));
      const snapshot = env.serializeBattle();
      const replay = await restored.resetFromSerialized(snapshot, OPTIONS);
      assert.equal(replay.terminated, true);
      assert.equal(replay.winner, terminal.winner);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, env.captureSeededSnapshot().state_fingerprint);
    } finally { await env.close(); await restored.close(); }
  });
}

for (const failure of ['timeout', 'message-limit', 'simulator-error', 'stream-closed', 'cancelled'] as const) {
  test(`pipeline ${failure} discards a progressed candidate, releases resources and preserves lineage`, async () => {
    const c = clock();
    const config = { battle_id: `settle-${failure}`, format: 'gen9randombattle', seed: SEED };
    const session = await createPipelineIntegrationSession({ ...config, settling: c.options });
    const control = await createPipelineIntegrationSession(config);
    const original = LocalBattleEnv.prototype.stepSeededTransition;
    let candidate: LocalBattleEnv | undefined;
    let barrier: SettlingBarrier | undefined;
    try {
      const before = session.boundary;
      const serialized = JSON.stringify(before);
      LocalBattleEnv.prototype.stepSeededTransition = async function (request, options) {
        candidate = this;
        barrier = internals(this).settling;
        const observed = deferred();
        const acknowledge = barrier.acknowledge.bind(barrier);
        barrier.acknowledge = (consumer) => {
          if (consumer === 'spectator') observed.resolve();
          else acknowledge(consumer);
        };
        const result = original.call(this, request, options);
        // Attach rejection before triggering a signal.
        const caught = result.catch((error: unknown) => { throw error; });
        await observed.promise;
        if (failure === 'timeout') c.expire();
        else if (failure === 'message-limit') {
          for (let i = 0; i <= 1000; i++) barrier.emitted('sideupdate', 'p1\n');
        } else if (failure === 'simulator-error') internals(this).battleStream!.pushError(new Error('injected source error'), true);
        else if (failure === 'stream-closed') internals(this).battleStream!.pushEnd();
        else await this.close();
        return caught;
      };
      await assert.rejects(session.step(), (error) => assertFailure(error, failure));
      LocalBattleEnv.prototype.stepSeededTransition = original;
      assert.ok(candidate && barrier);
      assert.equal(internals(candidate).battleStream, null);
      assert.equal(internals(candidate).consumerTasks.length, 0);
      assert.equal(barrier.pendingWaits, 0);
      assert.equal(c.timers.size, 0);
      assert.equal(session.boundary, before);
      assert.equal(JSON.stringify(session.boundary), serialized);
      const next = await session.step();
      const expected = await control.step();
      assert.equal(next.transition_id, expected.transition_id);
      assert.deepEqual(next.record_bundles, expected.record_bundles);
    } finally {
      LocalBattleEnv.prototype.stepSeededTransition = original;
      await session.close(); await control.close();
    }
  });
}


test('consumer closure with undelivered terminal output fails rather than waiting for a deadline', async () => {
  const c = clock();
  const barrier = new SettlingBarrier(c.options);
  const rejected = assert.rejects(barrier.wait(() => null), (e) => assertFailure(e, 'stream-closed'));
  barrier.emitted('update', '|tie');
  barrier.emitted('end', '{}');
  barrier.acknowledge('p1'); barrier.acknowledge('p2');
  barrier.streamClosed('spectator');
  await rejected;
  assert.equal(c.timers.size, 0);
  assert.equal(barrier.pendingWaits, 0);
});

test('settling options reject unbounded or unsupported limits', () => {
  for (const timeout_ms of [0, -1, Infinity, 0.5, 2147483648]) {
    assert.throws(() => new SettlingBarrier({ timeout_ms }));
  }
  for (const max_messages of [0, -1, Infinity, 0.5]) {
    assert.throws(() => new SettlingBarrier({ max_messages }));
  }
});
