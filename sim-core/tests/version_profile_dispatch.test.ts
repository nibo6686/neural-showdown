import {testOutput} from './helpers/test_outputs';
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { selectReaderProfile, recognizedReaderRevisions, HISTORICAL10, HISTORICAL10_REVISION as OLD, NATIVE11_REVISION as TARGET } from '../src/version_profile';
import { validateHistoricalPipelineLinkedRecordBundle, validateHistoricalPipelineEpisodeRecordBundle, validatePipelineLinkedRecordBundle } from '../src/pipeline_integration';
import { createPipelineEpisodeEvidence, sealPipelineEpisodeEvidence, validateHistoricalPipelineEpisodeEvidence, episodeEvidenceContentDigest as digest } from '../src/pipeline_episode_evidence';
import { summarizeEpisodeBoundary, validateHistoricalPipelineEpisodeFaithfulClaim } from '../src/pipeline_episode';
import { rehash } from './public_consequence_test_helpers';
const root = path.resolve(__dirname, '../../..');
const load = (f: string) => JSON.parse(readFileSync(path.join(root, f), 'utf8'));
const saved = load('docs/planning/perspective-fidelity-prompt25-wire-before.json').find((r: any) => r.schema.endsWith('/v2'));
const savedBundle = () => structuredClone(saved.next.record_bundles.p1);
const witness = (name: string, detail: object) => console.log('P31_WITNESS ' + JSON.stringify({ name, ...detail }));

// Reader-only constructed terminal form over saved native inputs. No battle runs.
function fixtures() {
  const records = structuredClone(saved.next.record_bundles), terminal = structuredClone(saved.next.boundary);
  for (const owner of ['p1', 'p2']) {
    const b = records[owner], o = b.successor_observation;
    o.protocol_prefix.push('|win|Agent-1'); o.event_cursor = o.protocol_prefix.length; o.protocol_prefix_hash = digest(o.protocol_prefix);
    o.request = null; o.snapshot_phase = 'terminal'; o.view.terminated = true; o.view.winner = 'p1';
    o.decision_availability = { available: false, reason: 'terminal', legal_action_indices: null };
    b.successor_belief.source_protocol_prefix = [...o.protocol_prefix]; rehash(b);
    terminal.perspectives[owner] = { observation: o, belief: b.successor_belief };
  }
  terminal.kind = 'terminal';
  const limits = { max_transitions: 2, max_attempts: 2, max_rejections_per_boundary: 1 }, policy = 'P31-reader-control';
  const initial = summarizeEpisodeBoundary(saved.initial), final = summarizeEpisodeBoundary(terminal);
  const run = 'episode-' + createHash('sha256').update(JSON.stringify({ schema: 'pipeline-episode/v1', battle_id: saved.initial.battle_id,
    format: 'gen9randombattle', policy, limits, initial_boundary: initial })).digest('hex');
  const { action_id: _action, ...transition } = records.p1.transition;
  const envelope = createPipelineEpisodeEvidence({ run_id: run, battle_id: saved.initial.battle_id, ruleset: 'gen9randombattle', kind: 'fresh_episode',
    boundaries: [saved.initial, terminal], transitions: [{ transition, actors: ['p1', 'p2'] }] })!;
  const result = { schema_version: 'pipeline-episode/v1', run_id: run, battle_id: saved.initial.battle_id, ruleset: 'gen9randombattle', policy_id: policy,
    limits, status: 'completed', stop: { code: 'episode/v1/terminal', reason: 'reader-only constructed terminal' },
    counts: { attempts: 1, committed_transitions: 1, rejected_candidates: 0, rejections_at_final_boundary: 0 }, initial_boundary: initial,
    final_boundary: final, transition_ids: [transition.transition_id], records: { p1: [records.p1], p2: [records.p2] }, evidence_envelope: envelope, faithful_complete_episode: true };
  const arrays = ['observation_history', 'simulator_snapshot_history', 'transition_history', 'candidates', 'evidence', 'contradictions', 'unresolved'];
  const beliefs: any[] = [], compactRecords: any = { p1: [], p2: [] };
  for (const owner of ['p1', 'p2']) {
    const b = records[owner];
    for (const belief of [b.input_belief, b.successor_belief]) {
      const fields = structuredClone(belief), encoded: any = {};
      delete fields.belief_id; delete fields.source_protocol_prefix;
      for (const k of arrays) { encoded[k] = { mode: 'full', items: fields[k] }; delete fields[k]; }
      beliefs.push({ belief_id: belief.belief_id, base_belief_id: null, fields, arrays: encoded });
    }
    compactRecords[owner].push({ transition_id: b.transition.transition_id, action: b.action,
      input_belief_id: b.input_belief.belief_id, successor_belief_id: b.successor_belief.belief_id });
  }
  const { records: _records, evidence_envelope: _env, ...metadata } = result;
  const sweep = { schema_version: 'pipeline-episode-publication-sweep/v1', result: metadata, evidence_envelope: envelope, records: compactRecords, beliefs };
  return { bundle: savedBundle(), envelope, result, sweep };
}

function resealRevision(b: any, revision: string) {
  const oldId = b.transition.transition_id, oldBranch = b.transition.branch_id;
  const id = 'transition-' + digest({ schema_version: 'seeded-transition/v1', parent_branch_id: b.transition.parent_branch_id,
    input_state_fingerprint: b.transition.input_state_fingerprint, output_state_fingerprint: b.transition.output_state_fingerprint,
    root_seed: saved.snapshot.root_seed, action_ids: { p1: saved.next.record_bundles.p1.action.action_id, p2: saved.next.record_bundles.p2.action.action_id },
    simulator_revision: revision, step_index: b.transition.step_index });
  const branch = 'branch-' + digest({ schema_version: 'seeded-transition/v1', parent_branch_id: b.transition.parent_branch_id,
    root_seed: saved.snapshot.root_seed, state_fingerprint: b.transition.output_state_fingerprint, transition_id: id });
  const update = (t: any) => { if (t?.transition_id === oldId) { t.transition_id = id; t.simulator_revision = revision; if (t.branch_id === oldBranch) t.branch_id = branch; } };
  update(b.transition);
  for (const belief of [b.input_belief, b.successor_belief]) {
    update(belief.transition_lineage); belief.transition_history.forEach(update);
    update(belief.simulator_snapshot); belief.simulator_snapshot_history.forEach(update);
    // Snapshot references have no revision field; preserve their schema.
    for (const t of [belief.simulator_snapshot, ...belief.simulator_snapshot_history]) if (t) delete t.simulator_revision;
  }
  rehash(b);
}
test('P31 historical TS readers', () => {
  const b = savedBundle(), ids = [b.input_observation.observation_id, b.action.action_id, b.transition.transition_id, b.successor_belief.belief_id];
  validatePipelineLinkedRecordBundle(b); validateHistoricalPipelineLinkedRecordBundle(b); validateHistoricalPipelineEpisodeRecordBundle(b);
  assert.deepEqual([b.input_observation.observation_id, b.action.action_id, b.transition.transition_id, b.successor_belief.belief_id], ids);
  const f: any = fixtures(); validateHistoricalPipelineEpisodeEvidence(f.envelope);
  assert.equal(validateHistoricalPipelineEpisodeFaithfulClaim(f.result as any), true);
  writeFileSync(testOutput('perspective-fidelity-prompt31-reader-fixtures.json'), JSON.stringify(f));
  const negatives: any = {};
  for (const [name, revision] of [['target', TARGET], ['unknown', 'sim-core@unknown']]) { const b = savedBundle(); resealRevision(b, revision); negatives[name] = b; }
  negatives.conflict = savedBundle(); negatives.conflict.successor_belief.transition_lineage.simulator_revision = TARGET; rehash(negatives.conflict);
  const prior = load('artifacts/validation/ce08a-adversarial-recovery-2026-10-09/predecessor.json');
  const current: any = { ...prior.commits.at(-1).boundary, battle_id: prior.battle_id, perspectives: Object.fromEntries(['p1','p2'].map(p => [p,{observation: prior.commits.at(-1).boundary.perspectives[p]}])) };
  const continuation = createPipelineEpisodeEvidence({ run_id: 'episode-' + 'a'.repeat(64), battle_id: prior.battle_id, ruleset: prior.ruleset, kind: 'continuation_segment', boundaries: [current], transitions: [], predecessor: prior })!;
  validateHistoricalPipelineEpisodeEvidence(continuation); f.continuation = continuation;
  writeFileSync(testOutput('perspective-fidelity-prompt31-reader-fixtures.json'), JSON.stringify(f));
  const changedPrior = structuredClone(prior); changedPrior.commits[0].transition.simulator_revision = TARGET;
  continuation.closure!.predecessor = sealPipelineEpisodeEvidence(changedPrior); negatives.predecessor = sealPipelineEpisodeEvidence(continuation);
  writeFileSync(testOutput('perspective-fidelity-prompt31-resealed-negatives.json'), JSON.stringify(negatives));
  witness('historical', { saved_ids: ids, constructed_terminal: true, native_execution: false, evidence_id: f.envelope.evidence_id });
});

test('P31 recognized revision dispatch', () => {
  const b = savedBundle(); assert.equal(selectReaderProfile(b), HISTORICAL10);
  const empty = load('artifacts/validation/ce08b-independent-review-2026-10-09/valid-cancellation-control.json');
  assert.equal(selectReaderProfile(empty, 'historical10'), HISTORICAL10); assert.throws(() => selectReaderProfile(empty), /ambiguous-revision/);
  assert.equal(validateHistoricalPipelineEpisodeFaithfulClaim(empty), false);
  for (const selection of ['native11', 'unknown']) assert.throws(() => selectReaderProfile(b, selection as any), /native11-unadopted|unknown-profile/);
  const cases: any[] = [
    { schema_version: 'pipeline-episode-evidence/v2', commits: [{ transition: { simulator_revision: OLD } }], closure: { predecessor: { schema_version: 'pipeline-episode-evidence/v1', commits: [{ transition: { simulator_revision: TARGET } }] } } },
    { schema_version: 'pipeline-episode-publication-sweep/v1', beliefs: [{ fields: { transition_lineage: { simulator_revision: TARGET } }, arrays: { transition_history: { items: [{ simulator_revision: OLD }] } } }] },
    { schema_version: 'pipeline-linked-record/v1', transition: { simulator_revision: OLD }, successor_belief: { evidence: [{ provenance: { kind: 'simulator_only_truth', simulator_revision: TARGET } }] } },
  ];
  for (const c of cases) assert.throws(() => selectReaderProfile(c, 'historical10'), /conflicting-revisions/);
  assert.deepEqual(recognizedReaderRevisions({ schema_version: 'pipeline-linked-record/v1', request: { simulator_revision: TARGET }, transition: { simulator_revision: OLD } }), [OLD]);
  const cycle: any = { schema_version: 'pipeline-episode-evidence/v2', closure: {} }; cycle.closure.predecessor = cycle;
  assert.throws(() => selectReaderProfile(cycle, 'historical10'), /invalid-predecessor-chain/);
  witness('dispatch', { schema_paths: 'bundle/evidence/predecessor/result/sweep/compact/evidence-provenance', explicit_empty_historical: true, no_arbitrary_key_scan: true });
});

test('P31 coherent rejection before old rules', () => {
  for (const revision of [TARGET, 'sim-core@unknown']) {
    const b = savedBundle(); resealRevision(b, revision); assert.throws(() => validateHistoricalPipelineLinkedRecordBundle(b), /native11-unadopted|unknown-revision/);
    // Malformed old grammar deliberately behind dispatch: profile error must win.
    b.input_observation.protocol_prefix.push('|unrecognized|');
    assert.throws(() => validatePipelineLinkedRecordBundle(b), /native11-unadopted|unknown-revision/);
  }
  const conflict = savedBundle(); conflict.successor_belief.transition_lineage.simulator_revision = TARGET; rehash(conflict);
  assert.throws(() => validateHistoricalPipelineLinkedRecordBundle(conflict), /conflicting-revisions/);
  const f = fixtures(), e = structuredClone(f.envelope); e.commits[0].transition.simulator_revision = TARGET;
  const sealed = sealPipelineEpisodeEvidence(e); assert.throws(() => validateHistoricalPipelineEpisodeEvidence(sealed), /native11-unadopted/);
  validatePipelineLinkedRecordBundle(savedBundle());
  witness('negative', { canonical_belief_evidence_resealing: true, profile_error_before_old_grammar: true, interleaved_old_unchanged: true });
});
