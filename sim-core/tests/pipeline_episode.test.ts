import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { continuePipelineEpisode, runPipelineEpisode, summarizeEpisodeBoundary, type PipelineEpisodeResult } from '../src/pipeline_episode';
import { createPipelineIntegrationSession, PipelineIntegrationError, type PipelineBoundary } from '../src/pipeline_integration';
import { SettlingError } from '../src/settling';
import { PLAYERS, type PlayerID } from '../src/types';

const CONFIG = { battle_id: 'episode-regression', format: 'gen9randombattle', seed: [101, 202, 303, 404] };
function assertRecords(result: PipelineEpisodeResult) {
  assert.equal(result.faithful_complete_episode, false);
  assert.equal(result.transition_ids.length, result.counts.committed_transitions);
  assert.equal(new Set(result.transition_ids).size, result.transition_ids.length);
  const seen = new Set<string>();
  let parentBranch = result.initial_boundary?.branch_id;
  for (const id of result.transition_ids) {
    const bundles = PLAYERS.flatMap((p) => result.records[p].filter((r) => r.transition.transition_id === id));
    assert.ok(bundles.length === 1 || bundles.length === 2);
    for (const bundle of bundles) {
      assert.equal(bundle.transition.parent_branch_id, parentBranch);
      assert.equal(bundle.successor_belief.parent_belief_id, bundle.input_belief.belief_id);
      assert.equal(bundle.successor_belief.transition_lineage?.transition_id, id);
      assert.equal(bundle.successor_belief.observation.observation_id, bundle.successor_observation.observation_id);
      if (bundle.schema_version === 'pipeline-forced-switch-record/v1') {
        assert.equal(bundles.length, 1);
        assert.equal(bundle.transition.acting_player, bundle.perspective);
      }
    }
    parentBranch = bundles[0].transition.branch_id;
  }
  for (const player of PLAYERS) for (const bundle of result.records[player]) {
    assert.equal(bundle.perspective, player);
    assert.ok(result.transition_ids.includes(bundle.transition.transition_id));
    const key = `${player}:${bundle.transition.transition_id}`;
    assert.ok(!seen.has(key)); seen.add(key);
  }
  if (parentBranch) assert.equal(result.final_boundary?.branch_id, parentBranch);
}
function pythonValidate(bundle: unknown) {
  const processResult = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
  assert.equal(processResult.status, 0, processResult.stderr);
}
function choose(boundary: PipelineBoundary, p: PlayerID, choice: string) {
  const r = boundary.perspectives[p].observation.request!;
  const a = r.legal_actions.actions.find((a) => a?.choice === choice)!;
  assert.ok(a); return canonicalActionFromLegalAction(r, a.index);
}

test('real episode completes repeatably through joint and both one-sided actor paths, with valid partial lineage', async () => {
  const first = await runPipelineEpisode(CONFIG);
  const repeated = await runPipelineEpisode(CONFIG);
  assert.equal(first.status, 'completed');
  assert.equal(first.stop.code, 'episode/v1/terminal');
  assert.equal(first.counts.committed_transitions, 55);
  assert.deepEqual(first, repeated);
  assertRecords(first);
  assert.equal(first.final_boundary?.kind, 'terminal');
  for (const p of PLAYERS) {
    assert.equal(first.final_boundary?.perspectives[p].request_state, 'terminal');
    assert.ok(first.records[p].some((r) => r.schema_version === 'pipeline-forced-switch-record/v1'));
    pythonValidate(first.records[p].at(-1));
  }
});

for (const [limit, code] of [['max_transitions', 'transition-budget'], ['max_attempts', 'attempt-budget']] as const) {
  test(`${limit} stops after one committed transition without duplicate records`, async () => {
    const result = await runPipelineEpisode({ ...CONFIG, limits: { [limit]: 1 } });
    assert.equal(result.status, 'truncated');
    assert.equal(result.stop.code, `episode/v1/${code}`);
    assert.equal(result.counts.attempts, 1); assert.equal(result.counts.committed_transitions, 1);
    assertRecords(result);
  });
}

test('natural Arena Trap rejection retries a different current-request tuple and preserves control identity', async () => {
  const config = { ...CONFIG, seed: [46, 101, 202, 303] };
  const session = await createPipelineIntegrationSession(config);
  const control = await createPipelineIntegrationSession(config);
  for (const s of [session, control]) {
    await s.step({ p1: choose(s.boundary, 'p1', 'switch 3'), p2: choose(s.boundary, 'p2', 'switch 6') });
  }
  const before = summarizeEpisodeBoundary(session.boundary);
  const result = await continuePipelineEpisode(session, {
    limits: { max_transitions: 1 }, policy_id: 'arena-trap-regression/v1',
    action_order: (o) => {
      const legal = o.request!.legal_actions;
      const first = o.perspective === 'p2' ? legal.actions.find((a) => a?.choice === 'switch 2')?.index : undefined;
      return first === undefined ? legal.available_indices : [first, ...legal.available_indices.filter((i) => i !== first)];
    },
  });
  const expected = await control.step(); await control.close();
  assert.equal(result.status, 'truncated'); assert.equal(result.stop.code, 'episode/v1/transition-budget');
  assert.equal(result.counts.rejected_candidates, 1); assert.equal(result.counts.attempts, 2);
  assert.equal(result.counts.rejections_at_final_boundary, 0);
  assert.deepEqual(result.initial_boundary, before);
  assert.equal(result.transition_ids[0], expected.transition_id);
  assertRecords(result);
  assert.throws(() => session.boundary, /closed/);
});

for (const max_attempts of [10, 2]) {
  test(`controlled rejections stop at ${max_attempts === 10 ? 'default three per boundary' : 'episode attempt cap'}`, async () => {
    const session = await createPipelineIntegrationSession(CONFIG);
    const before = session.boundary;
    const tried: string[] = [];
    session.step = async (actions) => {
      assert.equal(session.boundary, before);
      tried.push(JSON.stringify(actions));
      throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled rejection');
    };
    const r = await continuePipelineEpisode(session, { limits: { max_attempts } });
    assert.equal(r.stop.code, max_attempts === 10 ? 'episode/v1/rejection-limit' : 'episode/v1/attempt-budget');
    assert.equal(r.status, 'truncated'); assert.equal(r.counts.attempts, Math.min(3, max_attempts));
    assert.equal(new Set(tried).size, tried.length);
    assert.equal(r.counts.rejected_candidates, tried.length);
    assert.deepEqual(r.initial_boundary, r.final_boundary); assertRecords(r);
  });
}

test('episode attempt budget counts rejections and successes without resetting after commit', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const original = session.step.bind(session);
  let attempts = 0;
  session.step = async (actions) => {
    if (++attempts === 1) throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled once');
    return original(actions);
  };
  const r = await continuePipelineEpisode(session, { limits: { max_attempts: 3 } });
  assert.equal(r.stop.code, 'episode/v1/attempt-budget');
  assert.equal(r.counts.attempts, 3); assert.equal(r.counts.committed_transitions, 2);
  assert.equal(r.counts.rejected_candidates, 1); assert.equal(r.counts.rejections_at_final_boundary, 0);
  assertRecords(r);
});

test('cancellation is observed at committed boundaries including after an in-flight commit', async () => {
  const pre = new AbortController(); pre.abort();
  const cancelled = await runPipelineEpisode({ ...CONFIG, signal: pre.signal });
  assert.equal(cancelled.stop.code, 'episode/v1/cancelled'); assert.equal(cancelled.counts.attempts, 0);
  const session = await createPipelineIntegrationSession(CONFIG);
  const signal = new AbortController();
  const original = session.step.bind(session);
  session.step = async (a) => { const result = await original(a); signal.abort(); return result; };
  const r = await continuePipelineEpisode(session, { signal: signal.signal });
  assert.equal(r.stop.code, 'episode/v1/cancelled'); assert.equal(r.counts.committed_transitions, 1);
  assertRecords(r);
});

test('controlled requestless boundary explicitly truncates without submitting or fabricating an action', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const synthetic = structuredClone(session.boundary);
  synthetic.kind = 'requestless';
  for (const p of PLAYERS) synthetic.perspectives[p].observation.request = null;
  Object.defineProperty(session, 'boundary', { get: () => synthetic });
  session.step = async () => { throw new Error('must not submit'); };
  const r = await continuePipelineEpisode(session);
  assert.equal(r.status, 'truncated'); assert.equal(r.stop.code, 'episode/v1/unsupported-boundary');
  assert.equal(r.counts.attempts, 0); assertRecords(r);
});

test('source-shaped Revival Blessing flag at a real force/wait boundary truncates before any attempt', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  while (session.boundary.kind === 'joint_actionable') await session.step();
  assert.equal(session.boundary.kind, 'one_sided_forced_switch');
  const getRequest = LocalBattleEnv.prototype.getRequest;
  try {
    LocalBattleEnv.prototype.getRequest = function (p) {
      const request = getRequest.call(this, p);
      if (request?.force_switch) request.raw = { side: { pokemon: [{ reviving: true }] } };
      return request;
    };
    const r = await continuePipelineEpisode(session);
    assert.equal(r.status, 'truncated'); assert.equal(r.stop.code, 'episode/v1/unsupported-revival-blessing');
    assert.equal(r.counts.attempts, 0); assertRecords(r);
  } finally { LocalBattleEnv.prototype.getRequest = getRequest; await session.close(); }
});

for (const record of ['|nothing|', '|turn|broken']) {
  test(`controlled ${record} candidate output stops with no uncommitted records`, async () => {
    const session = await createPipelineIntegrationSession(CONFIG);
    const original = LocalBattleEnv.prototype.stepSeededTransition;
    try {
      LocalBattleEnv.prototype.stepSeededTransition = async function (r, o) {
        const result = await original.call(this, r, o); result.metadata.emitted_log_delta.push(record); return result;
      };
      const r = await continuePipelineEpisode(session);
      assert.equal(r.status, record === '|nothing|' ? 'truncated' : 'failed');
      assert.equal(r.stop.code, record === '|nothing|' ? 'episode/v1/unsupported-protocol' : 'episode/v1/execution-failed');
      assert.equal(r.counts.attempts, 1); assert.equal(r.counts.rejected_candidates, 0);
      assert.deepEqual(r.initial_boundary, r.final_boundary); assertRecords(r);
    } finally { LocalBattleEnv.prototype.stepSeededTransition = original; await session.close(); }
  });
}

test('simulator failure after a valid commit retains only committed records and final lineage', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const original = LocalBattleEnv.prototype.stepSeededTransition;
  let calls = 0;
  try {
    LocalBattleEnv.prototype.stepSeededTransition = async function (r, o) {
      if (++calls === 2) this.markError(new Error('controlled simulator error'));
      return original.call(this, r, o);
    };
    const r = await continuePipelineEpisode(session);
    assert.equal(r.status, 'failed'); assert.equal(r.stop.cause_code, 'settling/v1/simulator-error');
    assert.equal(r.counts.attempts, 2); assert.equal(r.counts.committed_transitions, 1);
    assert.equal(r.final_boundary?.step_index, 1); assertRecords(r);
    assert.throws(() => session.boundary, /closed/);
  } finally { LocalBattleEnv.prototype.stepSeededTransition = original; await session.close(); }
});

test('initialization failure returns a versioned failed outcome with no committed boundary', async () => {
  const original = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = async () => { throw new SettlingError('stream-closed', 5000, 100000); };
    const r = await runPipelineEpisode(CONFIG);
    assert.equal(r.status, 'failed'); assert.equal(r.stop.cause_code, 'settling/v1/stream-closed');
    assert.equal(r.initial_boundary, null); assert.equal(r.final_boundary, null); assertRecords(r);
  } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
});

test('invalid budgets/policy fail explicitly; cleanup failure retains committed records', async () => {
  for (const max_attempts of [0, -1, Infinity, 0.5]) {
    const r = await runPipelineEpisode({ ...CONFIG, limits: { max_attempts } });
    assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/invalid-options');
    assert.equal(r.counts.attempts, 0); assert.equal(r.limits, null);
  }
  const badPolicy = await runPipelineEpisode({ ...CONFIG, action_order: () => [] });
  assert.equal(badPolicy.stop.code, 'episode/v1/invalid-options');
  const invalidOrder = await runPipelineEpisode({ ...CONFIG, policy_id: 'invalid/v1', action_order: () => [99] });
  assert.equal(invalidOrder.status, 'failed'); assert.equal(invalidOrder.counts.attempts, 0);
  const session = await createPipelineIntegrationSession(CONFIG);
  const close = session.close.bind(session);
  session.close = async () => { await close(); throw new Error('controlled cleanup error'); };
  const r = await continuePipelineEpisode(session, { limits: { max_transitions: 1 } });
  assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/cleanup-failed');
  assert.equal(r.counts.committed_transitions, 1); assertRecords(r);
});


test('invalid continuation options retain the existing committed origin and close its session', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  await session.step();
  const before = summarizeEpisodeBoundary(session.boundary);
  const r = await continuePipelineEpisode(session, { limits: { max_attempts: 0 } });
  assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/invalid-options');
  assert.deepEqual(r.initial_boundary, before); assert.deepEqual(r.final_boundary, before);
  assert.equal(r.counts.attempts, 0); assertRecords(r);
  assert.throws(() => session.boundary, /closed/);
});

test('rejection cap resets only on commit, while total rejection and attempt counts accumulate', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const step = session.step.bind(session);
  let attempts = 0;
  session.step = async (actions) => {
    if (++attempts === 1 || attempts === 3) throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled rejection at each origin');
    return step(actions);
  };
  const r = await continuePipelineEpisode(session, { limits: { max_transitions: 2, max_rejections_per_boundary: 2 } });
  assert.equal(r.stop.code, 'episode/v1/transition-budget');
  assert.equal(r.counts.attempts, 4); assert.equal(r.counts.rejected_candidates, 2);
  assert.equal(r.counts.rejections_at_final_boundary, 0); assertRecords(r);
});
