import { withTerminalOwner } from './public_health';
import {serializeCanonicalAction, type CanonicalAction} from './canonical_action';
import { createHash } from 'node:crypto';
import { validateObservableBattleState } from './belief_state';
import type { PipelineBoundary } from './pipeline_integration';
import type { ObservableBattleState } from './observable_state';
import { PLAYERS, type PlayerID } from './types';

export const PIPELINE_EPISODE_EVIDENCE_VERSION = 'pipeline-episode-evidence/v2' as const;
export const LEGACY_PIPELINE_EPISODE_EVIDENCE_VERSION = 'pipeline-episode-evidence/v1' as const;
export const PIPELINE_EPISODE_ORIGIN_VERSION = 'pipeline-episode-origin/v1' as const;
export const PIPELINE_EPISODE_CLOSURE_VERSION = 'pipeline-episode-closure/v1' as const;

export interface EpisodeEvidenceBoundary {
  step_index: number;
  kind: PipelineBoundary['kind'];
  branch_id: string;
  state_fingerprint: string;
  perspectives: Record<PlayerID, ObservableBattleState>;
}

export interface EpisodeEvidenceTransition {
  schema_version: string;
  transition_id: string;
  parent_branch_id: string;
  branch_id: string;
  input_state_fingerprint: string;
  output_state_fingerprint: string;
  simulator_revision: string;
  step_index: number;
}

export interface PipelineEpisodeEvidence {
  schema_version: typeof PIPELINE_EPISODE_EVIDENCE_VERSION | typeof LEGACY_PIPELINE_EPISODE_EVIDENCE_VERSION;
  run_id: string;
  battle_id: string;
  ruleset: string;
  source_ref: string;
  origin: {
    schema_version: typeof PIPELINE_EPISODE_ORIGIN_VERSION;
    origin_id: string;
    kind: 'fresh_episode' | 'continuation_segment';
    boundary: EpisodeEvidenceBoundary;
  };
  commits: Array<{
    origin_id: string;
    transition: EpisodeEvidenceTransition;
    actors: PlayerID[];
    boundary: EpisodeEvidenceBoundary;
  }>;
  closure?: {
    schema_version: typeof PIPELINE_EPISODE_CLOSURE_VERSION;
    origin_coverage: 'original_initial_requests' | 'segment_only' | 'terminal_only';
    predecessor: PipelineEpisodeEvidence | null;
    terminal: {
      schema_version: 'pipeline-terminal-evidence/v1';
      outcome: 'win' | 'tie';
      winner: PlayerID | 'tie';
      final_boundary: {
        step_index: number;
        branch_id: string;
        state_fingerprint: string;
        perspectives: Record<PlayerID, { observation_id: string; event_cursor: number; protocol_prefix_hash: string }>;
      };
    } | null;
    complete_capture: boolean;
  };
  evidence_id: string;
}

export interface EpisodeEvidenceRecord {
  perspective: PlayerID;
  input_observation: ObservableBattleState;
  successor_observation: ObservableBattleState;
  action: CanonicalAction;
  transition: EpisodeEvidenceTransition & {
    action_id: string;
    acting_player?: PlayerID;
    waiting_player?: PlayerID;
  };
}

export interface EpisodeEvidenceExpectation {
  run_id: string;
  battle_id: string;
  ruleset: string;
  policy_id: string;
  limits: Record<string, number> | null;
  origin_kind: PipelineEpisodeEvidence['origin']['kind'];
  initial_boundary: {
    step_index: number;
    kind: PipelineBoundary['kind'];
    branch_id: string;
    state_fingerprint: string;
    perspectives: Record<PlayerID, {
      observation_id: string;
      belief_id: string;
      event_cursor: number;
      request_state: string;
      winner: ObservableBattleState['view']['winner'];
    }>;
  } | null;
}

const EVIDENCE_TRANSITION_SCHEMAS = new Set([
  'pipeline-transition-reference/v1',
  'pipeline-forced-switch-reference/v1',
  'pipeline-revival-reference/v1',
]);
const EVIDENCE_KINDS = new Set([
  'joint_actionable', 'one_sided_revival', 'one_sided_forced_switch',
  'one_sided_requestless', 'waiting', 'requestless', 'terminal',
]);
const FORBIDDEN_KEYS = new Set([
  'simulator_snapshot', 'simulator_state', 'rng_seed', 'root_seed', 'seed',
  'emitted_log_delta', 'raw_log_delta', 'raw_request', 'opponent_request',
  'private_team', 'opponent_private', 'hidden_roster', 'hidden_set', 'future_events', 'omniscient',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value: Record<string, unknown>, keys: readonly string[], label: string): void {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new Error(`${label}-fields`);
  }
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  const serialized = JSON.stringify(value);
  if (serialized === undefined) throw new Error('unsupported-evidence-value');
  return serialized;
}

function digest(value: unknown): string {
  return createHash('sha256').update(canonical(value), 'utf8').digest('hex');
}
export {canonical as canonicalEpisodeEvidenceJson, digest as episodeEvidenceContentDigest};

function rejectPrivateKeys(value: unknown): void {
  if (Array.isArray(value)) {
    value.forEach(rejectPrivateKeys);
  } else if (isRecord(value)) {
    for (const [key, child] of Object.entries(value)) {
      if (FORBIDDEN_KEYS.has(key)) throw new Error('private-evidence-field');
      rejectPrivateKeys(child);
    }
  }
}

function evidenceBoundary(boundary: PipelineBoundary): EpisodeEvidenceBoundary {
  return {
    step_index: boundary.step_index,
    kind: boundary.kind,
    branch_id: boundary.branch_id,
    state_fingerprint: boundary.state_fingerprint,
    perspectives: {
      p1: boundary.perspectives.p1.observation,
      p2: boundary.perspectives.p2.observation,
    },
  };
}

function isTerminalBoundary(boundary: EpisodeEvidenceBoundary): boolean {
  return boundary.kind === 'terminal';
}

function originalInitialRequests(boundary: EpisodeEvidenceBoundary): boolean {
  return boundary.step_index === 0 && boundary.kind === 'joint_actionable' && PLAYERS.every((player) => {
    const observation = boundary.perspectives[player];
    return !observation.view.terminated && observation.request !== null
      && observation.request.player === player && !observation.request.wait;
  });
}

function terminalEvidence(boundary: EpisodeEvidenceBoundary): NonNullable<PipelineEpisodeEvidence['closure']>['terminal'] {
  if (!isTerminalBoundary(boundary)) return null;
  const p1 = boundary.perspectives.p1;
  const p2 = boundary.perspectives.p2;
  const winner = p1.view.winner;
  if (!p1.view.terminated || !p2.view.terminated || p1.request !== null || p2.request !== null
    || p1.snapshot_phase !== 'terminal' || p2.snapshot_phase !== 'terminal'
    || winner !== p2.view.winner || (winner !== 'p1' && winner !== 'p2' && winner !== 'tie')) {
    throw new Error('evidence-terminal-perspectives');
  }
  const finalRecord = p1.protocol_prefix.at(-1);
  const expectedRecord = winner === 'tie' ? '|tie' : `|win|${p1.view.names[winner] ?? ''}`;
  if ((winner !== 'tie' && (!p1.view.names[winner]?.trim() || finalRecord !== expectedRecord))
    || (winner === 'tie' && finalRecord !== '|tie')) throw new Error('evidence-terminal-outcome-record');
  return {
    schema_version: 'pipeline-terminal-evidence/v1',
    outcome: winner === 'tie' ? 'tie' : 'win',
    winner,
    final_boundary: {
      step_index: boundary.step_index,
      branch_id: boundary.branch_id,
      state_fingerprint: boundary.state_fingerprint,
      perspectives: Object.fromEntries(PLAYERS.map((player) => [player, {
        observation_id: boundary.perspectives[player].observation_id,
        event_cursor: boundary.perspectives[player].event_cursor,
        protocol_prefix_hash: boundary.perspectives[player].protocol_prefix_hash,
      }])) as Record<PlayerID, { observation_id: string; event_cursor: number; protocol_prefix_hash: string }>,
    },
  };
}

function sameBoundary(left: EpisodeEvidenceBoundary, right: EpisodeEvidenceBoundary): boolean {
  return canonical(left) === canonical(right);
}

function derivedCoverage(envelope: PipelineEpisodeEvidence): 'original_initial_requests' | 'segment_only' | 'terminal_only' {
  if (envelope.origin.kind === 'fresh_episode') {
    if (originalInitialRequests(envelope.origin.boundary)) return 'original_initial_requests';
    return terminalEvidence(envelope.origin.boundary) ? 'terminal_only' : 'segment_only';
  }
  const predecessor = envelope.closure?.predecessor;
  if (!predecessor) return 'segment_only';
  if (predecessor.closure) return predecessor.closure.origin_coverage;
  return predecessor.origin.kind === 'fresh_episode' && originalInitialRequests(predecessor.origin.boundary)
    ? 'original_initial_requests' : 'segment_only';
}

function originIdentity(envelope: Omit<PipelineEpisodeEvidence, 'evidence_id'>): Record<string, unknown> {
  return {
    schema_version: PIPELINE_EPISODE_ORIGIN_VERSION,
    run_id: envelope.run_id,
    battle_id: envelope.battle_id,
    ruleset: envelope.ruleset,
    source_ref: envelope.source_ref,
    kind: envelope.origin.kind,
    boundary: envelope.origin.boundary,
  };
}

export function sealPipelineEpisodeEvidence(
  envelope: Omit<PipelineEpisodeEvidence, 'evidence_id'>,
): PipelineEpisodeEvidence {
  return { ...envelope, evidence_id: `episode-evidence-${digest(envelope)}` };
}

export function createPipelineEpisodeEvidence(input: {
  run_id: string;
  battle_id: string;
  ruleset: string;
  kind: PipelineEpisodeEvidence['origin']['kind'];
  boundaries: readonly PipelineBoundary[];
  transitions: readonly { transition: EpisodeEvidenceTransition; actors: PlayerID[] }[];
  predecessor?: PipelineEpisodeEvidence | null;
}): PipelineEpisodeEvidence | null {
  if (!input.boundaries.length || input.transitions.length !== input.boundaries.length - 1) return null;
  const boundaries = input.boundaries.map(evidenceBoundary);
  if (boundaries.some((boundary) => PLAYERS.some((player) =>
    boundary.perspectives[player].schema_version !== 'observable-battle-state/v2'))) return null;
  const sourceRef = `sim-core://${input.battle_id}`;
  const partial = {
    schema_version: PIPELINE_EPISODE_EVIDENCE_VERSION,
    run_id: input.run_id,
    battle_id: input.battle_id,
    ruleset: input.ruleset,
    source_ref: sourceRef,
    origin: {
      schema_version: PIPELINE_EPISODE_ORIGIN_VERSION,
      origin_id: '',
      kind: input.kind,
      boundary: boundaries[0],
    },
    commits: input.transitions.map(({ transition, actors }, index) => ({
      origin_id: '', transition, actors: [...actors], boundary: boundaries[index + 1],
    })),
  } satisfies Omit<PipelineEpisodeEvidence, 'evidence_id' | 'closure'>;
  const originId = `episode-origin-${digest(originIdentity(partial))}`;
  partial.origin.origin_id = originId;
  for (const commit of partial.commits) commit.origin_id = originId;
  const predecessor = input.predecessor ?? null;
  const closureBase: NonNullable<PipelineEpisodeEvidence['closure']> = {
    schema_version: PIPELINE_EPISODE_CLOSURE_VERSION,
    origin_coverage: 'segment_only',
    predecessor,
    terminal: terminalEvidence(boundaries.at(-1)!),
    complete_capture: false,
  };
  const withClosure = { ...partial, closure: closureBase } as Omit<PipelineEpisodeEvidence, 'evidence_id'>;
  if (input.kind === 'fresh_episode' && predecessor) throw new Error('evidence-fresh-predecessor');
  if (input.kind === 'continuation_segment' && predecessor) {
    validatePipelineEpisodeEvidence(predecessor);
    if (predecessor.battle_id !== input.battle_id || predecessor.ruleset !== input.ruleset
      || predecessor.source_ref !== sourceRef || terminalEvidence(predecessor.commits.at(-1)?.boundary ?? predecessor.origin.boundary)
      || !sameBoundary(predecessor.commits.at(-1)?.boundary ?? predecessor.origin.boundary, boundaries[0])) {
      throw new Error('evidence-predecessor-origin');
    }
  }
  closureBase.origin_coverage = input.kind === 'fresh_episode'
    ? (originalInitialRequests(boundaries[0]) ? 'original_initial_requests' : (terminalEvidence(boundaries[0]) ? 'terminal_only' : 'segment_only'))
    : (predecessor ? derivedCoverage(predecessor) : 'segment_only');
  closureBase.complete_capture = closureBase.origin_coverage === 'original_initial_requests' && closureBase.terminal !== null;
  return sealPipelineEpisodeEvidence(withClosure);
}

function requestState(observation: ObservableBattleState): string {
  if (observation.view.terminated) return 'terminal';
  if (!observation.request) return 'requestless';
  if (observation.request.wait) return 'waiting';
  if (observation.request.side.some((pokemon) => pokemon.reviving)) return 'revival_selection';
  if (!observation.decision_availability.available || !observation.request.legal_actions.available_indices.length) {
    return 'no_legal_actions';
  }
  return observation.request.force_switch ? 'forced_switch' : 'actionable';
}

function expectedBoundaryKind(boundary: EpisodeEvidenceBoundary): EpisodeEvidenceBoundary['kind'] {
  const states = { p1: requestState(boundary.perspectives.p1), p2: requestState(boundary.perspectives.p2) };
  if (states.p1 === 'terminal' && states.p2 === 'terminal') return 'terminal';
  if (states.p1 === 'terminal' || states.p2 === 'terminal') throw new Error('evidence-terminal-perspective-disagreement');
  if (states.p1 === 'no_legal_actions' || states.p2 === 'no_legal_actions') throw new Error('evidence-no-legal-actions');
  if (states.p1 === 'revival_selection' || states.p2 === 'revival_selection') return 'one_sided_revival';
  const p1 = states.p1 === 'actionable' || states.p1 === 'forced_switch';
  const p2 = states.p2 === 'actionable' || states.p2 === 'forced_switch';
  if (p1 && p2) return 'joint_actionable';
  if (p1 !== p2) {
    const actor = p1 ? states.p1 : states.p2;
    if (actor === 'forced_switch') return 'one_sided_forced_switch';
    return (p1 ? states.p2 : states.p1) === 'waiting' ? 'waiting' : 'one_sided_requestless';
  }
  return states.p1 === 'waiting' || states.p2 === 'waiting' ? 'waiting' : 'requestless';
}

function expectedActors(boundary: EpisodeEvidenceBoundary): PlayerID[] | null {
  const states = { p1: requestState(boundary.perspectives.p1), p2: requestState(boundary.perspectives.p2) };
  if (boundary.kind === 'joint_actionable'
    && PLAYERS.every((player) => states[player] === 'actionable' || states[player] === 'forced_switch')) return [...PLAYERS];
  if (boundary.kind === 'one_sided_forced_switch') {
    const actor = PLAYERS.find((player) => states[player] === 'forced_switch');
    if (actor && states[actor === 'p1' ? 'p2' : 'p1'] === 'waiting') return [actor];
  }
  if (boundary.kind === 'one_sided_revival') {
    const actor = PLAYERS.find((player) => states[player] === 'revival_selection');
    if (actor && states[actor === 'p1' ? 'p2' : 'p1'] === 'waiting') return [actor];
  }
  return null;
}

function validateBoundary(value: unknown, label: string, battleId: string, predecessor?: EpisodeEvidenceBoundary, transition?: EpisodeEvidenceTransition, actions?: Partial<Record<PlayerID, CanonicalAction>>): asserts value is EpisodeEvidenceBoundary {
  if (!isRecord(value)) throw new Error(`${label}-object`);
  exactKeys(value, ['step_index', 'kind', 'branch_id', 'state_fingerprint', 'perspectives'], label);
  if (!Number.isSafeInteger(value.step_index) || (value.step_index as number) < 0
    || typeof value.kind !== 'string' || !EVIDENCE_KINDS.has(value.kind)
    || typeof value.branch_id !== 'string' || !value.branch_id.trim()
    || typeof value.state_fingerprint !== 'string' || !/^[a-f0-9]{64}$/.test(value.state_fingerprint)
    || !isRecord(value.perspectives)) throw new Error(`${label}-metadata`);
  exactKeys(value.perspectives, ['p1', 'p2'], `${label}-perspectives`);
  for (const player of PLAYERS) {
    const observation = value.perspectives[player];
    if (predecessor?.perspectives[player].request?.side.length && isRecord(observation)
      && isRecord(observation.request) && observation.request.wait === true
      && Array.isArray(observation.request.side) && observation.request.side.length === 0) throw new Error('Public item evidence mismatch: waiting request omits previously established owned roster authority');
    if (predecessor && transition) withTerminalOwner({
      predecessor: predecessor.perspectives[player] as unknown as Record<string, unknown>, before: predecessor,
      transition, after: value as unknown as EpisodeEvidenceBoundary,
      action: actions?.[player],
    }, observation as Record<string, unknown>, () => validateObservableBattleState(observation));
    else validateObservableBattleState(observation);
    const validatedObservation = observation as ObservableBattleState;
    if (validatedObservation.schema_version !== 'observable-battle-state/v2'
      || validatedObservation.source_kind !== 'sim_core' || validatedObservation.battle_id !== battleId
      || validatedObservation.perspective !== player) throw new Error(`${label}-${player}-origin`);
  }
  const p1 = value.perspectives.p1 as ObservableBattleState;
  const p2 = value.perspectives.p2 as ObservableBattleState;
  if (canonical(p1.protocol_prefix) !== canonical(p2.protocol_prefix)) throw new Error(`${label}-public-prefix-disagreement`);
  if (value.kind !== expectedBoundaryKind(value as unknown as EpisodeEvidenceBoundary)) throw new Error(`${label}-kind-disagrees-with-observations`);
}

function validateTransition(value: unknown): asserts value is EpisodeEvidenceTransition {
  if (!isRecord(value)) throw new Error('evidence-transition-object');
  exactKeys(value, [
    'schema_version', 'transition_id', 'parent_branch_id', 'branch_id',
    'input_state_fingerprint', 'output_state_fingerprint', 'simulator_revision', 'step_index',
  ], 'evidence-transition');
  if (typeof value.schema_version !== 'string' || !EVIDENCE_TRANSITION_SCHEMAS.has(value.schema_version)
    || typeof value.transition_id !== 'string' || !/^transition-[a-f0-9]{64}$/.test(value.transition_id)
    || typeof value.parent_branch_id !== 'string' || !value.parent_branch_id.trim()
    || typeof value.branch_id !== 'string' || !value.branch_id.trim()
    || typeof value.input_state_fingerprint !== 'string' || !/^[a-f0-9]{64}$/.test(value.input_state_fingerprint)
    || typeof value.output_state_fingerprint !== 'string' || !/^[a-f0-9]{64}$/.test(value.output_state_fingerprint)
    || typeof value.simulator_revision !== 'string' || !value.simulator_revision.trim()
    || !Number.isSafeInteger(value.step_index) || (value.step_index as number) < 0) {
    throw new Error('evidence-transition-metadata');
  }
}

function validateEpisodeClosure(
  envelope: Record<string, unknown>,
  origin: PipelineEpisodeEvidence['origin'],
  finalBoundary: EpisodeEvidenceBoundary,
  depth: number,
): void {
  if (!isRecord(envelope.closure)) throw new Error('evidence-closure-object');
  const closure = envelope.closure;
  exactKeys(closure, ['schema_version', 'origin_coverage', 'predecessor', 'terminal', 'complete_capture'], 'evidence-closure');
  if (closure.schema_version !== PIPELINE_EPISODE_CLOSURE_VERSION
    || !['original_initial_requests', 'segment_only', 'terminal_only'].includes(String(closure.origin_coverage))
    || typeof closure.complete_capture !== 'boolean'
    || (closure.predecessor !== null && !isRecord(closure.predecessor))) throw new Error('evidence-closure-metadata');

  const terminal = terminalEvidence(finalBoundary);
  if (terminal) {
    if (!isRecord(closure.terminal)) throw new Error('evidence-terminal-omitted');
    exactKeys(closure.terminal, ['schema_version', 'outcome', 'winner', 'final_boundary'], 'evidence-terminal');
    if (canonical(closure.terminal) !== canonical(terminal)) throw new Error('evidence-terminal-join');
  } else if (closure.terminal !== null) {
    throw new Error('evidence-terminal-without-final-boundary');
  }

  let expectedCoverage: 'original_initial_requests' | 'segment_only' | 'terminal_only';
  if (origin.kind === 'fresh_episode') {
    if (closure.predecessor !== null) throw new Error('evidence-fresh-predecessor');
    expectedCoverage = originalInitialRequests(origin.boundary) ? 'original_initial_requests'
      : (terminalEvidence(origin.boundary) ? 'terminal_only' : 'segment_only');
  } else if (closure.predecessor === null) {
    expectedCoverage = 'segment_only';
  } else {
    const predecessor = closure.predecessor as unknown as PipelineEpisodeEvidence;
    validatePipelineEpisodeEvidence(predecessor, undefined, undefined, depth + 1);
    if (predecessor.battle_id !== envelope.battle_id || predecessor.ruleset !== envelope.ruleset
      || predecessor.source_ref !== envelope.source_ref) throw new Error('evidence-predecessor-episode');
    const predecessorFinal = predecessor.commits.at(-1)?.boundary ?? predecessor.origin.boundary;
    if (terminalEvidence(predecessorFinal) || !sameBoundary(predecessorFinal, origin.boundary)) {
      throw new Error('evidence-predecessor-origin');
    }
    expectedCoverage = predecessor.closure?.origin_coverage
      ?? (predecessor.origin.kind === 'fresh_episode' && originalInitialRequests(predecessor.origin.boundary)
        ? 'original_initial_requests' : 'segment_only');
  }
  if (closure.origin_coverage !== expectedCoverage) throw new Error('evidence-origin-coverage');
  const completeCapture = closure.origin_coverage === 'original_initial_requests' && terminal !== null;
  if (closure.complete_capture !== completeCapture) throw new Error('evidence-complete-capture');
}

export function validatePipelineEpisodeEvidence(
  value: unknown,
  records?: Record<PlayerID, readonly EpisodeEvidenceRecord[]>,
  expected?: EpisodeEvidenceExpectation,
  depth = 0,
): asserts value is PipelineEpisodeEvidence {
  if (depth > 64) throw new Error('evidence-predecessor-depth');
  rejectPrivateKeys(value);
  if (!isRecord(value)) throw new Error('evidence-object');
  const isLegacy = value.schema_version === LEGACY_PIPELINE_EPISODE_EVIDENCE_VERSION;
  exactKeys(value, isLegacy
    ? ['schema_version', 'run_id', 'battle_id', 'ruleset', 'source_ref', 'origin', 'commits', 'evidence_id']
    : ['schema_version', 'run_id', 'battle_id', 'ruleset', 'source_ref', 'origin', 'commits', 'closure', 'evidence_id'], 'evidence');
  if ((!isLegacy && value.schema_version !== PIPELINE_EPISODE_EVIDENCE_VERSION)
    || typeof value.run_id !== 'string' || !/^episode-[a-f0-9]{64}$/.test(value.run_id)
    || typeof value.battle_id !== 'string' || !value.battle_id.trim()
    || typeof value.ruleset !== 'string' || !value.ruleset.trim()
    || value.source_ref !== `sim-core://${value.battle_id}`
    || typeof value.evidence_id !== 'string' || !/^episode-evidence-[a-f0-9]{64}$/.test(value.evidence_id)
    || !isRecord(value.origin) || !Array.isArray(value.commits)) throw new Error('evidence-metadata');
  if (expected && (value.run_id !== expected.run_id || value.battle_id !== expected.battle_id
    || value.ruleset !== expected.ruleset || expected.initial_boundary === null)) throw new Error('evidence-result-origin');
  exactKeys(value.origin, ['schema_version', 'origin_id', 'kind', 'boundary'], 'evidence-origin');
  if (value.origin.schema_version !== PIPELINE_EPISODE_ORIGIN_VERSION
    || !['fresh_episode', 'continuation_segment'].includes(String(value.origin.kind))
    || (expected && value.origin.kind !== expected.origin_kind)
    || typeof value.origin.origin_id !== 'string' || !/^episode-origin-[a-f0-9]{64}$/.test(value.origin.origin_id)) {
    throw new Error('evidence-origin-metadata');
  }
  let ownerSource: {before: EpisodeEvidenceBoundary; transition: EpisodeEvidenceTransition} | undefined;
  if (!isLegacy && isRecord(value.closure) && value.closure.predecessor !== null) {
    const predecessor = value.closure.predecessor;
    validatePipelineEpisodeEvidence(predecessor, undefined, undefined, depth + 1);
    if (value.origin.kind !== 'continuation_segment' || predecessor.battle_id !== value.battle_id
      || predecessor.ruleset !== value.ruleset || predecessor.source_ref !== value.source_ref
      || canonical((predecessor.commits.at(-1)?.boundary || predecessor.origin.boundary)) !== canonical(value.origin.boundary)) throw new Error('evidence-predecessor-boundary-join');
    const authoritySource = (prior: PipelineEpisodeEvidence): typeof ownerSource => {
      const last = prior.commits.at(-1);
      if (last) return {before: prior.commits.at(-2)?.boundary || prior.origin.boundary, transition: last.transition};
      return prior.closure?.predecessor ? authoritySource(prior.closure.predecessor) : undefined;
    };
    ownerSource = authoritySource(predecessor);
  }
  validateBoundary(value.origin.boundary, 'origin-boundary', value.battle_id, ownerSource?.before, ownerSource?.transition);
  const originBoundary = value.origin.boundary as unknown as EpisodeEvidenceBoundary;
  if (expected) {
    const rootSummary = expected.initial_boundary!;
    const expectedRunId = `episode-${createHash('sha256').update(JSON.stringify({
      schema: 'pipeline-episode/v1', battle_id: expected.battle_id, format: expected.ruleset,
      policy: expected.policy_id, limits: expected.limits, initial_boundary: rootSummary,
    })).digest('hex')}`;
    if (expected.run_id !== expectedRunId) throw new Error('evidence-result-run-identity');
    if (originBoundary.step_index !== rootSummary.step_index || originBoundary.kind !== rootSummary.kind
      || originBoundary.branch_id !== rootSummary.branch_id || originBoundary.state_fingerprint !== rootSummary.state_fingerprint) {
      throw new Error('evidence-result-origin-boundary');
    }
    for (const player of PLAYERS) {
      const observation = originBoundary.perspectives[player];
      const summary = rootSummary.perspectives[player];
      if (observation.observation_id !== summary.observation_id || observation.event_cursor !== summary.event_cursor
        || requestState(observation) !== summary.request_state || observation.view.winner !== summary.winner
        || !/^belief-[a-f0-9]{64}$/.test(summary.belief_id)) throw new Error('evidence-result-origin-perspective');
    }
  }
  const partial = { ...value } as Record<string, unknown>;
  delete partial.evidence_id;
  if (value.evidence_id !== `episode-evidence-${digest(partial)}`) throw new Error('evidence-identity');
  const envelopeWithoutId = partial as Omit<PipelineEpisodeEvidence, 'evidence_id'>;
  if (value.origin.origin_id !== `episode-origin-${digest(originIdentity(envelopeWithoutId))}`) {
    throw new Error('evidence-forged-origin');
  }

  const typedOrigin = value.origin as unknown as PipelineEpisodeEvidence['origin'];
  const commits = value.commits as PipelineEpisodeEvidence['commits'];
  const allBoundaries: EpisodeEvidenceBoundary[] = [typedOrigin.boundary];
  const seenTransitions = new Set<string>();
  let previous = allBoundaries[0];
  for (const [index, rawCommit] of commits.entries()) {
    if (!isRecord(rawCommit)) throw new Error(`evidence-commit-${index}-object`);
    exactKeys(rawCommit, ['origin_id', 'transition', 'actors', 'boundary'], `evidence-commit-${index}`);
    if (rawCommit.origin_id !== typedOrigin.origin_id || !Array.isArray(rawCommit.actors)
      || rawCommit.actors.some((player) => player !== 'p1' && player !== 'p2')) throw new Error(`evidence-commit-${index}-origin`);
    validateTransition(rawCommit.transition);
    const transition = rawCommit.transition as EpisodeEvidenceTransition;
    const expected = expectedActors(previous);
    if (!expected || canonical(rawCommit.actors) !== canonical(expected)) throw new Error(`evidence-commit-${index}-actors`);
    const expectedTransitionSchema = expected.length === 2 ? 'pipeline-transition-reference/v1'
      : previous.kind === 'one_sided_revival' ? 'pipeline-revival-reference/v1' : 'pipeline-forced-switch-reference/v1';
    if (transition.schema_version !== expectedTransitionSchema) throw new Error(`evidence-commit-${index}-transition-schema`);
    const actions: Partial<Record<PlayerID, CanonicalAction>> = {};
    if (records && (rawCommit.boundary as EpisodeEvidenceBoundary)?.kind === 'terminal') for (const player of expected) {
      const matching = records[player]?.filter((record) => record.transition.transition_id === transition.transition_id);
      const record = matching?.[0];
      if (matching?.length !== 1 || !record || record.perspective !== player
        || canonical(record.input_observation) !== canonical(previous.perspectives[player])
        || canonical(record.successor_observation) !== canonical(rawCommit.boundary && (rawCommit.boundary as EpisodeEvidenceBoundary).perspectives[player])) throw new Error(`evidence-commit-${index}-${player}-record-join`);
      const {action_id, acting_player, waiting_player, ...reference} = record.transition;
      if (canonical(reference) !== canonical(transition) || action_id !== record.action.action_id
        || expected.length === 1 && (acting_player !== player || waiting_player !== (player === 'p1' ? 'p2' : 'p1'))) throw new Error(`evidence-commit-${index}-${player}-transition-join`);
      const request = previous.perspectives[player].request!;
      serializeCanonicalAction(record.action, request, player);
      actions[player] = record.action;
    }
    validateBoundary(rawCommit.boundary, `commit-${index}-boundary`, value.battle_id, previous, transition, actions);
    const next = rawCommit.boundary as EpisodeEvidenceBoundary;
    if (seenTransitions.has(transition.transition_id)) throw new Error('evidence-duplicate-transition');
    seenTransitions.add(transition.transition_id);
    if (next.step_index !== previous.step_index + 1 || transition.step_index !== previous.step_index
      || transition.parent_branch_id !== previous.branch_id || transition.branch_id !== next.branch_id
      || transition.input_state_fingerprint !== previous.state_fingerprint
      || transition.output_state_fingerprint !== next.state_fingerprint) throw new Error(`evidence-commit-${index}-lineage`);
    for (const player of PLAYERS) {
      const before = previous.perspectives[player];
      const after = next.perspectives[player];
      if (after.event_cursor < before.event_cursor
        || before.protocol_prefix.some((line, prefixIndex) => after.protocol_prefix[prefixIndex] !== line)) {
        throw new Error(`evidence-commit-${index}-${player}-prefix-lineage`);
      }
    }
    allBoundaries.push(next);
    previous = next;
  }

  if (!isLegacy) validateEpisodeClosure(value, typedOrigin, previous, depth);

  if (records) for (const player of PLAYERS) {
    const expectedIds = commits.flatMap((commit) => commit.actors.includes(player) ? [commit.transition.transition_id] : []);
    const playerRecords = records[player];
    if (!Array.isArray(playerRecords) || canonical(playerRecords.map((record) => record.transition.transition_id)) !== canonical(expectedIds)) {
      throw new Error(`evidence-${player}-record-order`);
    }
  }
  if (records) for (const [index, commit] of commits.entries()) {
    const before = allBoundaries[index];
    const after = allBoundaries[index + 1];
    for (const player of commit.actors) {
      const record = records[player].find((item) => item.transition.transition_id === commit.transition.transition_id);
      if (!record || record.perspective !== player
        || canonical(record.input_observation) !== canonical(before.perspectives[player])
        || canonical(record.successor_observation) !== canonical(after.perspectives[player])) {
        throw new Error(`evidence-commit-${index}-${player}-record-join`);
      }
      const { action_id: _actionId, acting_player: _actingPlayer, waiting_player: _waitingPlayer, ...transition } = record.transition;
      if (canonical(transition) !== canonical(commit.transition)) throw new Error(`evidence-commit-${index}-${player}-transition-join`);
      if (commit.actors.length === 1 && commit.transition.schema_version !== 'pipeline-transition-reference/v1'
        && (record.transition.acting_player !== player || record.transition.waiting_player !== (player === 'p1' ? 'p2' : 'p1'))) {
        throw new Error(`evidence-commit-${index}-${player}-waiting-role`);
      }
    }
  }
}

/** Validate the supplied predecessor before a continuation session advances. */
export function validatePipelineEpisodePredecessor(
  value: unknown,
  currentBoundary: PipelineBoundary,
  ruleset?: string,
): asserts value is PipelineEpisodeEvidence {
  validatePipelineEpisodeEvidence(value);
  const predecessor = value as PipelineEpisodeEvidence;
  const final = predecessor.commits.at(-1)?.boundary ?? predecessor.origin.boundary;
  if (predecessor.battle_id !== currentBoundary.battle_id
    || (ruleset !== undefined && predecessor.ruleset !== ruleset)
    || predecessor.source_ref !== `sim-core://${currentBoundary.battle_id}`
    || terminalEvidence(final)
    || !sameBoundary(final, evidenceBoundary(currentBoundary))) throw new Error('evidence-predecessor-origin');
}
