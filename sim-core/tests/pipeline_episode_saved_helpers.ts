import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {projectBeliefState} from '../src/belief_state';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {continuePipelineEpisode, summarizeEpisodeBoundary, type PipelineEpisodeResult} from '../src/pipeline_episode';
import {createPipelineEpisodeEvidence, validatePipelineEpisodeEvidence} from '../src/pipeline_episode_evidence';
import {validatePipelineLinkedRecordBundle, type PipelineBoundary, type PipelineIntegrationSession, type PipelineLinkedRecordBundle} from '../src/pipeline_integration';
import {type SeededTransitionMetadata, type SeededSnapshotRef} from '../src/transition';
import {PLAYERS} from '../src/types';

const witnessPath = path.resolve(__dirname, '../../../artifacts/validation/ce08a-adversarial-recovery-2026-10-09/predecessor.json');
const bytes = readFileSync(witnessPath);
assert.equal(createHash('sha256').update(bytes).digest('hex'), '83165b940ab2589c001a58ccad9a7668469848d02f6865fcf55b582508f1c0f9');
export const witness = JSON.parse(bytes.toString('utf8'));
export const defaults = {max_transitions: 256, max_attempts: 512, max_rejections_per_boundary: 3};
export const causes = ['seeded-revival/v1/unsupported-request', 'seeded-forced-switch/v1/unsupported-revival-blessing'];

export function fixture() {
  const raw = structuredClone(witness.origin.boundary), nextRaw = structuredClone(witness.commits[0].boundary);
  const initial = {...raw, schema_version: 'pipeline-integration/v1', battle_id: witness.battle_id,
    perspectives: Object.fromEntries(PLAYERS.map((p) => [p, {observation: raw.perspectives[p], belief: projectBeliefState({observation: raw.perspectives[p], simulator_snapshot: {
      schema_version: 'seeded-transition/v1', snapshot_handle: 'sim-core://saved-stop-witness/initial', format: witness.ruleset,
      root_seed: [31,37,41,43], state_fingerprint: raw.state_fingerprint, parent_branch_id: null, transition_id: null, branch_id: raw.branch_id,
    }})}]))} as PipelineBoundary;
  const actions = Object.fromEntries(PLAYERS.map((p) => {
    const request = initial.perspectives[p].observation.request!;
    const action = request.legal_actions.actions.find((a) => a?.choice.startsWith('switch '))!;
    return [p, canonicalActionFromLegalAction(request, action.index)];
  }));
  const reference = witness.commits[0].transition;
  const metadata = {...reference, schema_version: 'seeded-transition/v1', root_seed: [31,37,41,43],
    action_ids: Object.fromEntries(PLAYERS.map((p) => [p, actions[p].action_id])),
    emitted_log_delta: nextRaw.perspectives.p1.protocol_prefix.slice(raw.perspectives.p1.protocol_prefix.length)} as SeededTransitionMetadata;
  const snapshot = {schema_version: 'seeded-transition/v1', snapshot_handle: 'sim-core://saved-stop-witness/step-1', format: witness.ruleset,
    root_seed: metadata.root_seed, state_fingerprint: reference.output_state_fingerprint, parent_branch_id: reference.parent_branch_id,
    transition_id: reference.transition_id, branch_id: reference.branch_id} as SeededSnapshotRef;
  const next = {...nextRaw, schema_version: 'pipeline-integration/v1', battle_id: witness.battle_id,
    perspectives: Object.fromEntries(PLAYERS.map((p) => [p, {observation: nextRaw.perspectives[p], belief: projectBeliefState({
      observation: nextRaw.perspectives[p], parent: initial.perspectives[p].belief,
      transition: {metadata, input_observation_id: raw.perspectives[p].observation_id,
        output_observation_id: nextRaw.perspectives[p].observation_id, output_snapshot: snapshot},
    })}]))} as PipelineBoundary;
  const bundles = Object.fromEntries(PLAYERS.map((p) => [p, {
    schema_version: 'pipeline-linked-record/v1', battle_id: witness.battle_id, source_ref: witness.source_ref, ruleset: witness.ruleset, perspective: p,
    input_observation: initial.perspectives[p].observation, input_belief: initial.perspectives[p].belief, action: actions[p],
    transition: {...reference, action_id: actions[p].action_id}, successor_observation: next.perspectives[p].observation,
    successor_belief: next.perspectives[p].belief,
  }])) as Record<'p1'|'p2', PipelineLinkedRecordBundle>;
  for (const p of PLAYERS) validatePipelineLinkedRecordBundle(bundles[p]);
  assert.ok(!JSON.stringify(bundles).includes('root_seed'));
  return {initial, next, bundles, reference};
}

export function publish(payload: unknown, error?: RegExp, rows = 0) {
  const before = JSON.stringify(payload);
  const r = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {input: before, encoding: 'utf8', timeout: 30_000,
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')}});
  if (r.error) {
    const name = `failed-publication-${createHash('sha256').update(before).digest('hex')}`;
    const out = path.resolve(__dirname, '../../../artifacts/validation/faithful-flag-2026-10-09');
    writeFileSync(path.join(out, `${name}.json`), before);
    writeFileSync(path.join(out, `${name}-diagnostic.json`), JSON.stringify({status:r.status, signal:r.signal, error:r.error.message, stdout_bytes:Buffer.byteLength(r.stdout || ''), stderr:r.stderr, python:process.env.PYTHON || 'python3'}));
  }
  assert.equal(r.status, error ? 2 : 0, r.stderr || r.error?.message); assert.equal(JSON.stringify(payload), before);
  if (error) {assert.equal(r.stdout, ''); assert.match(r.stderr, error);}
  else assert.equal(JSON.parse(r.stdout).length, rows);
}

export function reseal(result: PipelineEpisodeResult, f: ReturnType<typeof fixture>) {
  result.run_id = `episode-${createHash('sha256').update(JSON.stringify({schema: result.schema_version, battle_id: result.battle_id,
    format: result.ruleset, policy: result.policy_id, limits: result.limits, initial_boundary: result.initial_boundary})).digest('hex')}`;
  result.evidence_envelope = createPipelineEpisodeEvidence({run_id: result.run_id, battle_id: result.battle_id, ruleset: result.ruleset,
    kind: 'continuation_segment', boundaries: result.counts.committed_transitions ? [f.initial, f.next] : [f.initial],
    transitions: result.counts.committed_transitions ? [{actors: [...PLAYERS], transition: f.reference}] : []});
  validatePipelineEpisodeEvidence(result.evidence_envelope!, result.records);
  return result;
}

export function session(f: ReturnType<typeof fixture>, phase: 'selection'|'candidate'|'after-commit', error: Error, cleanupError = false) {
  let current = f.initial, calls = 0, closed = 0;
  const owned = {battle_id: witness.battle_id, format: witness.ruleset, get boundary() {return current;},
    assertSupportedSelectionRequests() {if (phase === 'selection') throw error;},
    async step(actions: any) {
      if (phase === 'after-commit' && calls++ === 0) {
        for (const p of PLAYERS) assert.equal(actions[p].action_id, f.bundles[p].action.action_id);
        current = f.next; return {boundary: current, transition_id: f.reference.transition_id, record_bundles: f.bundles};}
      throw error;
    },
    async close() {closed++; if (cleanupError) throw new Error('private cleanup payload');},
  } as unknown as PipelineIntegrationSession;
  return {owned, closed: () => closed};
}

export function savedEpisode(owned: PipelineIntegrationSession, options: Parameters<typeof continuePipelineEpisode>[1] = {}) {
  return continuePipelineEpisode(owned, {policy_id: 'saved-first-switch/v1', action_order(observation) {
    const request = observation.request!, preferred = request.legal_actions.actions.find((a) => a?.choice.startsWith('switch '))!;
    return [preferred.index, ...request.legal_actions.available_indices.filter((i) => i !== preferred.index)];
  }, ...options});
}

