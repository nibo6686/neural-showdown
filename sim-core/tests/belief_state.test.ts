import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {
  BELIEF_STATE_SCHEMA_VERSION,
  projectBeliefState,
  serializeBeliefState,
  type BeliefEvidenceInput,
  type BeliefStateInput,
} from '../src/belief_state';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION,
  projectObservableBattleState,
  type ObservableBattleState,
} from '../src/observable_state';
import { createEmptyBattleView, type PlayerID } from '../src/types';
import {
  SEEDED_TRANSITION_SCHEMA_VERSION,
  SIMULATOR_REVISION,
  type SeededSnapshotRef,
  type SeededTransitionMetadata,
} from '../src/transition';

type FixtureCase = {
  case_id: string;
  observation: {
    source_kind: 'sim_core' | 'replay' | 'live';
    battle_id: string;
    perspective: PlayerID;
    snapshot_phase: string;
    turn: number;
    protocol_prefix: string[];
  };
  candidates: Array<{ category: string; subject_key: string; value: string }>;
  evidence: Array<Record<string, any>>;
  unresolved: Array<{ category: string; subject_key: string; reason: string }>;
  expected: {
    belief_id: string;
    canonical_serialization: string;
    dispositions: Record<string, string>;
  };
};

const fixture = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../../tests/fixtures/belief_state_v1.json'), 'utf8'),
) as { fixture_schema: string; schema_version: string; cases: FixtureCase[] };

function observe(options: {
  battle_id?: string;
  perspective?: PlayerID;
  prefix?: string[];
  turn?: number;
} = {}): ObservableBattleState {
  const perspective = options.perspective || 'p1';
  const view = createEmptyBattleView('belief-env', 'gen9randombattle', perspective);
  view.gen = 9;
  view.turn = options.turn || 1;
  return projectObservableBattleState({
    schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
    source_kind: 'sim_core',
    battle_id: options.battle_id || 'belief-battle',
    perspective,
    snapshot_phase: 'post_resolution',
    protocol_prefix: options.prefix || ['|turn|1', '|move|p2a: Eevee|Tackle|p1a: Pikachu'],
    view,
    request: null,
  });
}

function recordHash(record: string): string {
  return createHash('sha256').update(record, 'utf8').digest('hex');
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value as Record<string, unknown>).sort().map((key) => `${JSON.stringify(key)}:${canonicalize((value as Record<string, unknown>)[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function digest(value: unknown): string {
  return createHash('sha256').update(canonicalize(value), 'utf8').digest('hex');
}

function rehashObservationPrefix(observation: ObservableBattleState, prefix: string[]): ObservableBattleState {
  const rehashed: any = { ...observation, protocol_prefix: prefix, event_cursor: prefix.length };
  rehashed.protocol_prefix_hash = digest(prefix);
  const { observation_id: _observationId, protocol_prefix: _prefix, ...identity } = rehashed;
  rehashed.observation_id = `obs-${digest(identity)}`;
  return rehashed as ObservableBattleState;
}

function bindFixtureEvidence(observation: ObservableBattleState, entries: FixtureCase['evidence']): BeliefEvidenceInput[] {
  return entries.map((entry) => {
    const provenance = { ...entry.provenance };
    if (provenance.kind === 'direct_observed' || provenance.kind === 'derived') {
      delete provenance.observation;
      provenance.observation_id = observation.observation_id;
      provenance.event_cursor = observation.event_cursor;
      if (provenance.kind === 'direct_observed') {
        provenance.record = observation.protocol_prefix[provenance.event_index];
        provenance.record_hash = recordHash(provenance.record);
      }
    }
    return { ...entry, provenance } as BeliefEvidenceInput;
  });
}

function fixtureInput(testCase = fixture.cases[0]): BeliefStateInput {
  const observation = observe({
    battle_id: testCase.observation.battle_id,
    perspective: testCase.observation.perspective,
    prefix: testCase.observation.protocol_prefix,
    turn: testCase.observation.turn,
  });
  return {
    observation,
    candidates: testCase.candidates as BeliefStateInput['candidates'],
    evidence: bindFixtureEvidence(observation, testCase.evidence),
    unresolved: testCase.unresolved as BeliefStateInput['unresolved'],
  };
}

function candidateDispositionMap(state: ReturnType<typeof projectBeliefState>): Record<string, string> {
  return Object.fromEntries(state.candidates.map((candidate) => [
    candidate.category + ':' + candidate.value,
    candidate.disposition,
  ]));
}

test('belief fixture has deterministic ordered candidates, serialization, and identity', () => {
  assert.equal(fixture.fixture_schema, 'belief-state-fixtures/v1');
  assert.equal(fixture.schema_version, BELIEF_STATE_SCHEMA_VERSION);
  const testCase = fixture.cases[0];
  const firstInput = fixtureInput(testCase);
  const first = projectBeliefState(firstInput);
  const reordered = projectBeliefState({
    ...firstInput,
    candidates: [...(firstInput.candidates ?? [])].reverse(),
    evidence: [...(firstInput.evidence ?? [])].reverse(),
  });

  assert.deepEqual(candidateDispositionMap(first), testCase.expected.dispositions);
  assert.deepEqual(first.candidates.map((candidate) => candidate.category), [
    'ability', 'item', 'move', 'role', 'tera_type',
  ]);
  assert.equal(first.belief_id, testCase.expected.belief_id);
  assert.equal(serializeBeliefState(first), testCase.expected.canonical_serialization);
  assert.equal(serializeBeliefState(first), serializeBeliefState(reordered));
  assert.equal(first.belief_id, reordered.belief_id);
});

test('belief snapshots clone and freeze nested inputs and later snapshots preserve their parent', () => {
  const input = fixtureInput();
  const parent = projectBeliefState(input);
  const before = serializeBeliefState(parent);
  (input.candidates![0] as any).value = 'Mutated after projection';
  (input.evidence![0].provenance as any).record = 'future record';
  assert.equal(serializeBeliefState(parent), before);
  assert.ok(Object.isFrozen(parent));
  assert.ok(Object.isFrozen(parent.candidates));
  assert.throws(() => { (parent.candidates[0] as any).value = 'mutate'; }, TypeError);

  const laterObservation = observe({
    battle_id: parent.battle_id,
    prefix: [...parent.source_protocol_prefix, '|turn|2'],
    turn: 2,
  });
  const child = projectBeliefState({
    observation: laterObservation,
    parent,
    candidates: [{ category: 'move', subject_key: 'p2:slot:1', value: 'Quick Attack' }],
    evidence: [],
    unresolved: [],
  });
  assert.equal(child.parent_belief_id, parent.belief_id);
  assert.equal(serializeBeliefState(parent), before);
  assert.notEqual(child.belief_id, parent.belief_id);
});

test('future, stale, mismatched, and cross-perspective evidence is rejected', () => {
  const observation = observe();
  const future: BeliefEvidenceInput = {
    perspective: 'p1', category: 'move', subject_key: 'p2:slot:1', value: 'Future Move', assertion: 'supports',
    provenance: {
      kind: 'direct_observed', observation_id: observation.observation_id,
      event_cursor: observation.event_cursor, event_index: observation.event_cursor,
      record: '|move|p2a: Eevee|Future Move|p1a: Pikachu',
      record_hash: recordHash('|move|p2a: Eevee|Future Move|p1a: Pikachu'),
    },
  };
  assert.throws(() => projectBeliefState({ observation, evidence: [future] }), /event_index.*before event_cursor/);

  const stale = bindFixtureEvidence(observation, fixture.cases[0].evidence)[0];
  assert.throws(() => projectBeliefState({
    observation,
    evidence: [{ ...stale, provenance: { ...stale.provenance, observation_id: 'obs-stale' } } as BeliefEvidenceInput],
  }), /does not match base observation/);
  assert.throws(() => projectBeliefState({ observation, evidence: [{ ...future, perspective: 'p2' } as BeliefEvidenceInput] }), /perspective does not match/);

  const parent = projectBeliefState({ observation });
  const diverged = observe({
    battle_id: parent.battle_id,
    prefix: ['|turn|1', '|move|p2a: Eevee|Growl|p1a: Pikachu'],
  });
  assert.throws(() => projectBeliefState({ observation: diverged, parent }), /exact prefix extension/);
  const crossPerspective = observe({ battle_id: parent.battle_id, perspective: 'p2' });
  assert.throws(() => projectBeliefState({ observation: crossPerspective, parent }), /battle and perspective/);
});

test('derived evidence requires existing evidence and imported parents are fully revalidated', () => {
  const observation = observe();
  const direct = bindFixtureEvidence(observation, [fixture.cases[0].evidence[0]])[0];
  const directState = projectBeliefState({ observation, evidence: [direct] });
  const derived: BeliefEvidenceInput = {
    perspective: 'p1', category: 'role', subject_key: 'p2:slot:1', value: 'fast-attacker', assertion: 'supports',
    provenance: {
      kind: 'derived', observation_id: observation.observation_id, event_cursor: observation.event_cursor,
      derivation_id: 'test-derived-signal', derivation_version: 'v1',
      input_evidence_ids: [directState.evidence[0].evidence_id],
    },
  };
  const withDerived = projectBeliefState({ observation, evidence: [direct, derived] });
  assert.equal(withDerived.evidence.filter((entry) => entry.provenance.kind === 'derived').length, 1);
  assert.throws(() => projectBeliefState({
    observation,
    evidence: [{
      ...derived,
      provenance: { ...derived.provenance, input_evidence_ids: ['evidence-missing'] } as any,
    } as BeliefEvidenceInput],
  }), /references missing evidence IDs/);

  const simulatorSnapshot: SeededSnapshotRef = {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    snapshot_handle: 'revalidated-parent',
    format: 'gen9randombattle',
    root_seed: [1, 2, 3, 4],
    state_fingerprint: '4'.repeat(64),
    parent_branch_id: null,
    transition_id: 'revalidated-truth',
    branch_id: 'branch-revalidated-truth',
  };
  const research = projectBeliefState({
    observation,
    information_regime: 'simulator_research',
    simulator_snapshot: simulatorSnapshot,
    evidence: [{
      perspective: 'p1', category: 'ability', subject_key: 'p2:slot:1', value: 'Hidden Ability', assertion: 'supports',
      provenance: { kind: 'simulator_only_truth', transition_id: 'revalidated-truth', simulator_revision: SIMULATOR_REVISION },
    }],
  });
  const forged = JSON.parse(JSON.stringify(research)) as Record<string, any>;
  forged.information_regime = 'player';
  const { belief_id: _oldId, ...forgedPayload } = forged;
  forged.belief_id = `belief-${digest(forgedPayload)}`;
  assert.throws(() => serializeBeliefState(forged as any), /simulator_research information_regime/);
  assert.throws(() => projectBeliefState({ observation, parent: forged as any }), /simulator_research information_regime/);
});

test('raw request payloads and incomplete observable snapshots cannot enter belief lineage', () => {
  const observation = observe();
  const rawPrefix = [...observation.protocol_prefix, '|request|{"side":[{"item":"SecretItem"}]}'];
  const malformed: any = {
    ...observation,
    protocol_prefix: rawPrefix,
    event_cursor: rawPrefix.length,
  };
  malformed.protocol_prefix_hash = digest(rawPrefix);
  const { observation_id: _oldId, protocol_prefix: _oldPrefix, ...identity } = malformed;
  malformed.observation_id = `obs-${digest(identity)}`;
  assert.throws(() => projectBeliefState({ observation: malformed }), /unsanitized request record/);

  assert.throws(() => projectBeliefState({
    observation: rehashObservationPrefix(observation, ['|move|']),
  }), /Malformed raw move record/);
  assert.throws(() => projectBeliefState({
    observation: rehashObservationPrefix(observation, ['|turn|2']),
  }), /Raw evidence disagrees with view.turn/);

  const inventedRequestlessActions: any = {
    ...observation,
    decision_availability: { available: true, reason: 'request', legal_action_indices: [0] },
  };
  const { observation_id: _inventedId, protocol_prefix: _inventedPrefix, ...inventedIdentity } = inventedRequestlessActions;
  inventedRequestlessActions.observation_id = `obs-${digest(inventedIdentity)}`;
  assert.throws(() => projectBeliefState({ observation: inventedRequestlessActions }), /decision availability disagrees/);

  const incomplete: any = { ...observation, view: { ...observation.view } };
  delete incomplete.view.field;
  const { observation_id: _incompleteId, protocol_prefix: _prefix, ...incompleteIdentity } = incomplete;
  incomplete.observation_id = `obs-${digest(incompleteIdentity)}`;
  assert.throws(() => projectBeliefState({ observation: incomplete }), /Observation battle view fields are not exact/);
});

test('contradictory evidence remains explicit and missing evidence leaves candidates possible', () => {
  const observation = observe();
  const direct = bindFixtureEvidence(observation, [fixture.cases[0].evidence[0]])[0];
  const priorRefutation: BeliefEvidenceInput = {
    perspective: 'p1', category: 'move', subject_key: 'p2:slot:1', value: 'Tackle', assertion: 'refutes',
    provenance: {
      kind: 'prior_knowledge', source_id: 'explicit-test-source', source_version: 'v1',
      source_digest: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    },
  };
  const state = projectBeliefState({
    observation,
    candidates: [{ category: 'ability', subject_key: 'p2:slot:1', value: 'Intimidate' }],
    evidence: [direct, priorRefutation],
  });
  const move = state.candidates.find((candidate) => candidate.category === 'move' && candidate.value === 'Tackle');
  const ability = state.candidates.find((candidate) => candidate.category === 'ability');
  assert.equal(move?.disposition, 'contradictory');
  assert.equal(ability?.disposition, 'possible');
  assert.equal(state.contradictions.length, 1);
  assert.equal(state.contradictions[0].evidence_ids.length, 2);
  assert.equal(state.evidence.find((entry) => entry.provenance.kind === 'direct_observed')?.provenance.kind, 'direct_observed');
});

test('transition lineage joins the parent observation, output observation, branch, and revision', () => {
  const parentObservation = observe({ battle_id: 'transition-belief-battle' });
  const inputSnapshot: SeededSnapshotRef = {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    snapshot_handle: 'opaque-input',
    format: 'gen9randombattle',
    root_seed: [1, 2, 3, 4],
    state_fingerprint: '1'.repeat(64),
    parent_branch_id: null,
    transition_id: 'transition-seed',
    branch_id: 'branch-parent',
  };
  const parent = projectBeliefState({
    observation: parentObservation,
    information_regime: 'simulator_research',
    simulator_snapshot: inputSnapshot,
    evidence: [{
      perspective: 'p1', category: 'ability', subject_key: 'p2:slot:1', value: 'Seed Snapshot Truth', assertion: 'supports',
      provenance: { kind: 'simulator_only_truth', transition_id: 'transition-seed', simulator_revision: SIMULATOR_REVISION },
    }],
  });
  const outputObservation = observe({
    battle_id: parent.battle_id,
    prefix: [...parentObservation.protocol_prefix, '|turn|2'],
    turn: 2,
  });
  const metadata: SeededTransitionMetadata = {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    transition_id: 'transition-child',
    parent_branch_id: 'branch-parent',
    branch_id: 'branch-child',
    input_state_fingerprint: '1'.repeat(64),
    output_state_fingerprint: '2'.repeat(64),
    root_seed: [1, 2, 3, 4],
    action_ids: { p1: 'act-p1', p2: 'act-p2' },
    emitted_log_delta: ['|turn|2'],
    simulator_revision: SIMULATOR_REVISION,
    step_index: 0,
  };
  const outputSnapshot: SeededSnapshotRef = {
    ...inputSnapshot,
    snapshot_handle: 'opaque-output',
    state_fingerprint: metadata.output_state_fingerprint,
    parent_branch_id: metadata.parent_branch_id,
    transition_id: metadata.transition_id,
    branch_id: metadata.branch_id,
  };
  const state = projectBeliefState({
    observation: outputObservation,
    parent,
    transition: {
      metadata,
      input_observation_id: parentObservation.observation_id,
      output_observation_id: outputObservation.observation_id,
      output_snapshot: outputSnapshot,
    },
  });
  assert.equal(state.observation.event_cursor, outputObservation.event_cursor);
  assert.equal(state.transition_lineage?.input_observation_id, parentObservation.observation_id);
  assert.equal(state.transition_lineage?.output_observation_id, outputObservation.observation_id);
  assert.equal(state.transition_lineage?.simulator_revision, SIMULATOR_REVISION);
  assert.equal(state.transition_lineage?.step_index, metadata.step_index);
  assert.equal(state.simulator_snapshot?.branch_id, metadata.branch_id);
  assert.ok(serializeBeliefState(state).length > 0);

  assert.throws(() => projectBeliefState({
    observation: outputObservation,
    parent,
    transition: {
      metadata,
      input_observation_id: `obs-${'0'.repeat(64)}`,
      output_observation_id: outputObservation.observation_id,
      output_snapshot: outputSnapshot,
    },
  }), /input observation does not match parent/);
  assert.throws(() => projectBeliefState({
    observation: outputObservation,
    parent,
    transition: {
      metadata: { ...metadata, parent_branch_id: 'branch-stale' },
      input_observation_id: parentObservation.observation_id,
      output_observation_id: outputObservation.observation_id,
      output_snapshot: outputSnapshot,
    },
  }), /parent branch does not match/);

  const nextObservation = observe({
    battle_id: parent.battle_id,
    prefix: [...outputObservation.protocol_prefix, '|turn|3'],
    turn: 3,
  });
  const nextMetadata: SeededTransitionMetadata = {
    ...metadata,
    transition_id: 'transition-grandchild',
    parent_branch_id: 'branch-child',
    branch_id: 'branch-grandchild',
    input_state_fingerprint: '2'.repeat(64),
    output_state_fingerprint: '3'.repeat(64),
    step_index: 1,
  };
  const nextSnapshot: SeededSnapshotRef = {
    ...outputSnapshot,
    snapshot_handle: 'opaque-grandchild',
    state_fingerprint: nextMetadata.output_state_fingerprint,
    parent_branch_id: nextMetadata.parent_branch_id,
    transition_id: nextMetadata.transition_id,
    branch_id: nextMetadata.branch_id,
  };
  const nextTransition = {
    metadata: nextMetadata,
    input_observation_id: state.observation.observation_id,
    output_observation_id: nextObservation.observation_id,
    output_snapshot: nextSnapshot,
  };
  const grandchild = projectBeliefState({
    observation: nextObservation,
    parent: state,
    transition: nextTransition,
  });
  assert.ok(serializeBeliefState(grandchild).length > 0);
  assert.equal(grandchild.evidence.some((entry) => entry.provenance.kind === 'simulator_only_truth'), true);
  const observationOnly = projectBeliefState({
    observation: observe({
      battle_id: parent.battle_id,
      prefix: [...nextObservation.protocol_prefix, '|upkeep'],
      turn: 3,
    }),
    parent: grandchild,
  });
  assert.equal(observationOnly.transition_lineage?.transition_id, nextMetadata.transition_id);
  assert.ok(serializeBeliefState(observationOnly).length > 0);
  assert.throws(() => projectBeliefState({
    observation: nextObservation,
    parent: state,
    transition: { ...nextTransition, metadata: { ...nextMetadata, step_index: 0 } },
  }), /revision or step index is stale/);
  assert.throws(() => projectBeliefState({
    observation: nextObservation,
    parent: state,
    transition: { ...nextTransition, metadata: { ...nextMetadata, simulator_revision: 'different-revision' as any } },
  }), /revision or step index is stale/);
  assert.throws(() => projectBeliefState({
    observation: nextObservation,
    parent: state,
    transition: { ...nextTransition, metadata: { ...nextMetadata, simulator_revision: 42 } as any },
  }), /Seeded transition simulator_revision must be/);
});

test('simulator-only truth is separately scoped and never enters an observable projection', () => {
  const observation = observe();
  const simulatorSnapshot: SeededSnapshotRef = {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    snapshot_handle: 'opaque-research-snapshot',
    format: 'gen9randombattle',
    root_seed: [1, 2, 3, 4],
    state_fingerprint: '3'.repeat(64),
    parent_branch_id: null,
    transition_id: 'truth-transition',
    branch_id: 'branch-truth',
  };
  const simulatorResearch = projectBeliefState({
    observation,
    information_regime: 'simulator_research',
    simulator_snapshot: simulatorSnapshot,
    candidates: [{ category: 'ability', subject_key: 'p2:slot:1', value: 'Private Truth Ability' }],
    evidence: [{
      perspective: 'p1', category: 'ability', subject_key: 'p2:slot:1', value: 'Private Truth Ability', assertion: 'supports',
      provenance: {
        kind: 'simulator_only_truth', transition_id: 'truth-transition', simulator_revision: SIMULATOR_REVISION,
      },
    }],
  });
  assert.equal(simulatorResearch.information_regime, 'simulator_research');
  assert.equal(JSON.parse(serializeBeliefState(simulatorResearch)).schema_version, BELIEF_STATE_SCHEMA_VERSION);
  assert.doesNotMatch(JSON.stringify(observation), /Private Truth Ability|simulator_research/);
  assert.equal('candidates' in observation, false);
  assert.throws(() => projectBeliefState({
    observation,
    evidence: [{
      perspective: 'p1', category: 'ability', subject_key: 'p2:slot:1', value: 'Private Truth Ability', assertion: 'supports',
      provenance: {
        kind: 'simulator_only_truth', transition_id: 'truth-transition', simulator_revision: SIMULATOR_REVISION,
      },
    }],
  }), /Simulator-only truth requires simulator_research/);
});

test('unsupported belief and observation schemas fail closed', () => {
  const observation = observe();
  assert.throws(() => projectBeliefState({
    observation: { ...observation, schema_version: 'observable-battle-state/v999' } as unknown as ObservableBattleState,
  }), /Unsupported observable schema/);
  assert.throws(() => projectBeliefState({
    observation,
    schema_version: 'belief-state/v2',
  } as unknown as BeliefStateInput), /Unsupported belief schema/);
});
