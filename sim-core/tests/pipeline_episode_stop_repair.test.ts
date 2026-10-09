import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
import {projectBeliefState} from '../src/belief_state';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {continuePipelineEpisode, summarizeEpisodeBoundary, type PipelineEpisodeResult} from '../src/pipeline_episode';
import {createPipelineEpisodeEvidence, validatePipelineEpisodeEvidence} from '../src/pipeline_episode_evidence';
import {validatePipelineLinkedRecordBundle, type PipelineBoundary, type PipelineIntegrationSession, type PipelineLinkedRecordBundle} from '../src/pipeline_integration';
import {type SeededTransitionMetadata, type SeededSnapshotRef} from '../src/transition';
import {PLAYERS} from '../src/types';

import {fixture, publish, reseal, session, savedEpisode, defaults, causes} from './pipeline_episode_saved_helpers';

test('CE-08B repair exact limits schema rejects canonical ordinary and compact metadata', async () => {
  const f = fixture(), controller = session(f, 'selection', new Error('control'));
  const base = await savedEpisode(controller.owned, {signal: AbortSignal.abort()});
  assert.deepEqual(base.limits, defaults); publish(base);
  const validCommitted = reseal({...structuredClone(base), status: 'truncated', stop: {code: 'episode/v1/transition-budget', reason: 'saved control'},
    counts: {attempts: 1, committed_transitions: 1, rejected_candidates: 0, rejections_at_final_boundary: 0},
    final_boundary: summarizeEpisodeBoundary(f.next), transition_ids: [f.reference.transition_id], records: {p1: [f.bundles.p1], p2: [f.bundles.p2]},
    limits: {...defaults, max_transitions: 1}}, f);
  publish(validCommitted, undefined, 2);
  const badLimits: unknown[] = [null, [], 42, 'budgets', {}, {...defaults, extra_budget: 1}];
  for (const key of Object.keys(defaults)) {
    const missing: any = {...defaults}; delete missing[key]; badLimits.push(missing);
    for (const value of [null, true, '1', 0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1]) badLimits.push({...defaults, [key]: value});
  }
  const original = structuredClone(base);
  for (const limits of badLimits) {
    const candidate = reseal({...structuredClone(base), limits: limits as any}, f);
    publish(candidate, /episode limits schema/);
    // Compact sweep uses the same metadata gate before its terminal/belief hydration gate.
    const {records: _records, evidence_envelope, ...result} = candidate;
    publish({schema_version: 'pipeline-episode-publication-sweep/v1', result, evidence_envelope,
      records: {p1: [], p2: []}, beliefs: []}, /episode limits schema/);
  }
  assert.deepEqual(base, original);
  const invalidOptions = session(fixture(), 'selection', new Error('must not select'));
  const failedOptions = await savedEpisode(invalidOptions.owned, {limits: {max_attempts: 0}});
  assert.equal(failedOptions.stop.code, 'episode/v1/invalid-options'); assert.equal(failedOptions.limits, null);
  assert.equal(failedOptions.counts.attempts, 0); assert.equal(invalidOptions.closed(), 1);
  publish(failedOptions, /episode limits schema/);
  const atMax = reseal({...structuredClone(base), limits: {max_transitions: Number.MAX_SAFE_INTEGER,
    max_attempts: Number.MAX_SAFE_INTEGER, max_rejections_per_boundary: Number.MAX_SAFE_INTEGER}}, f); publish(atMax);
});

test('CE-08B repair Revival causes and stopped-candidate accounting agree across runtimes', async () => {
  for (const cause of causes) for (const phase of ['selection','candidate','after-commit'] as const) {
    console.log(`CE-08B repaired Revival ${cause}/${phase}`);
    const f = fixture(), frozen = structuredClone(f), control = session(f, phase, new Error(cause));
    const result = await savedEpisode(control.owned);
    assert.equal(control.closed(), 1); assert.equal(result.status, 'truncated'); assert.equal(result.stop.cause_code, cause);
    assert.equal(result.counts.attempts, phase === 'selection' ? 0 : phase === 'candidate' ? 1 : 2);
    assert.equal(result.counts.rejected_candidates, 0); assert.equal(result.counts.committed_transitions, phase === 'after-commit' ? 1 : 0);
    validatePipelineEpisodeEvidence(result.evidence_envelope!, result.records);
    publish(result, undefined, phase === 'after-commit' ? 2 : 0); assert.deepEqual(f, frozen);
    for (const mutate of [
      (r: PipelineEpisodeResult) => {r.stop.cause_code = 'untrusted private payload';},
      (r: PipelineEpisodeResult) => {delete r.stop.cause_code;},
      (r: PipelineEpisodeResult) => {r.counts.attempts += 2;},
      (r: PipelineEpisodeResult) => {r.counts.rejected_candidates = r.counts.attempts + 1;},
      (r: PipelineEpisodeResult) => {r.counts.rejections_at_final_boundary = 1;},
    ]) {const candidate = structuredClone(result); mutate(candidate); validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records);
      publish(candidate, /episode (Revival stop|counter)/);}
    const cleanup = session(fixture(), phase, new Error(cause), true);
    const failed = await savedEpisode(cleanup.owned); assert.equal(failed.stop.code, 'episode/v1/cleanup-failed');
    assert.equal(failed.stop.cause_code, cause); assert.equal(cleanup.closed(), 1); publish(failed, undefined, phase === 'after-commit' ? 2 : 0);
  }
  const f = fixture(), generic = session(f, 'candidate', new Error('private arbitrary exception payload'));
  const result = await savedEpisode(generic.owned); assert.equal(result.stop.code, 'episode/v1/execution-failed');
  assert.equal(result.stop.cause_code, undefined); assert.ok(!JSON.stringify(result.stop).includes('private')); publish(result);
  for (const code of ['episode/v1/cancelled','episode/v1/action-exhausted']) {
    const candidate = structuredClone(result); candidate.status = 'truncated'; candidate.stop = {code, reason: 'forged clean stop', cause_code: causes[0]};
    publish(candidate, /unaccounted attempt/);
  }
});

test('CE-08B repair construction validation and cleanup failures retain structured committed evidence', async () => {
  const evidence = require('../src/pipeline_episode_evidence') as typeof import('../src/pipeline_episode_evidence');
  for (const mode of ['before-validation','construction','validation'] as const) for (const cleanupError of [false,true]) {
    console.log(`CE-08B repaired evidence ${mode}/cleanup=${cleanupError}`);
    const f = fixture(), frozen = structuredClone(f), control = session(f, 'after-commit', new Error('private execution payload'), cleanupError);
    const create = evidence.createPipelineEpisodeEvidence, validate = evidence.validatePipelineEpisodeEvidence;
    let result: PipelineEpisodeResult;
    try {
      if (mode === 'before-validation') evidence.createPipelineEpisodeEvidence = () => {throw new Error('private construction payload');};
      if (mode === 'construction') evidence.createPipelineEpisodeEvidence = (input) => {
        const boundaries = input.boundaries.map((b) => structuredClone(b)); boundaries[boundaries.length-1].kind = 'terminal';
        return create({...input, boundaries});
      };
      if (mode === 'validation') evidence.validatePipelineEpisodeEvidence = () => {throw new Error('private validation payload');};
      result = await savedEpisode(control.owned);
    } finally {evidence.createPipelineEpisodeEvidence = create; evidence.validatePipelineEpisodeEvidence = validate;}
    assert.equal(control.closed(), 1); assert.equal(result!.status, 'failed');
    assert.equal(result!.stop.code, cleanupError ? 'episode/v1/cleanup-failed' : 'episode/v1/evidence-invalid');
    assert.equal(result!.stop.evidence_failure_stage, mode === 'validation' ? 'validation' : 'construction');
    assert.equal(result!.stop.cause_code, 'episode/v1/execution-failed');
    assert.ok(!JSON.stringify(result!.stop).includes('private')); assert.equal(result!.evidence_envelope, null);
    assert.equal(result!.counts.committed_transitions, 1); assert.deepEqual(result!.records, {p1: [f.bundles.p1], p2: [f.bundles.p2]});
    assert.deepEqual(result!.final_boundary, summarizeEpisodeBoundary(f.next)); assert.deepEqual(f, frozen);
    publish(result!, /episode evidence envelope/);
  }
  const f = fixture(), control = session(f, 'selection', new Error('unused'));
  Object.defineProperty(control.owned, 'boundary', {get: () => ({...f.initial, kind: 'terminal'})});
  const result = await savedEpisode(control.owned); assert.equal(result.stop.code, 'episode/v1/evidence-invalid');
  assert.equal(control.closed(), 1); assert.equal(result.evidence_envelope, null); publish(result, /episode evidence envelope/);
});
