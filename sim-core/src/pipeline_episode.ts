import { createHash } from 'node:crypto';
import { canonicalActionFromLegalAction, type CanonicalAction } from './canonical_action';
import {
  createPipelineEpisodeEvidence, validatePipelineEpisodeEvidence,
  validatePipelineEpisodePredecessor,
  type EpisodeEvidenceExpectation,
  type EpisodeEvidenceRecord, type EpisodeEvidenceTransition, type PipelineEpisodeEvidence,
} from './pipeline_episode_evidence';
import {
  classifyPipelineRequestState, createPipelineIntegrationSession, PipelineIntegrationError, validatePipelineEpisodeRecordBundle,
  type PipelineBoundary, type PipelineIntegrationOptions, type PipelineIntegrationSession,
  type PipelineLinkedRecordBundle, type PipelineForcedSwitchRecordBundle,
} from './pipeline_integration';
import type { ObservableBattleState } from './observable_state';
import { SettlingError } from './settling';
import { PLAYERS, type PlayerID } from './types';

export const PIPELINE_EPISODE_VERSION = 'pipeline-episode/v1' as const;
export interface EpisodeLimits {
  max_transitions: number;
  max_attempts: number;
  max_rejections_per_boundary: number;
}
export interface EpisodeExecutionOptions {
  limits?: Partial<EpisodeLimits>;
  signal?: AbortSignal;
  /** Required with custom ordering; this caller-supplied version binds run identity. */
  policy_id?: string;
  /** Synchronous permutation of this player's current legal indices. No opponent input. */
  action_order?: (observation: ObservableBattleState) => readonly number[];
}
export interface EpisodeContinuationOptions extends EpisodeExecutionOptions {
  /** Fully validated previous evidence ending exactly at the session boundary. */
  predecessor_evidence?: PipelineEpisodeEvidence | null;
}
export interface PipelineEpisodeOptions extends PipelineIntegrationOptions, EpisodeExecutionOptions {}
export type EpisodeRecord = PipelineLinkedRecordBundle | PipelineForcedSwitchRecordBundle;
export function summarizeEpisodeBoundary(boundary: PipelineBoundary) {
  return {
    step_index: boundary.step_index, kind: boundary.kind,
    branch_id: boundary.branch_id, state_fingerprint: boundary.state_fingerprint,
    perspectives: Object.fromEntries(PLAYERS.map((p) => {
      const { observation, belief } = boundary.perspectives[p];
      return [p, { observation_id: observation.observation_id, belief_id: belief.belief_id,
        event_cursor: observation.event_cursor, request_state: classifyPipelineRequestState(observation),
        winner: observation.view.winner }];
    })) as Record<PlayerID, { observation_id: string; belief_id: string; event_cursor: number;
      request_state: ReturnType<typeof classifyPipelineRequestState>; winner: ObservableBattleState['view']['winner'] }>,
  };
}
export interface PipelineEpisodeResult {
  schema_version: typeof PIPELINE_EPISODE_VERSION;
  run_id: string;
  battle_id: string;
  ruleset: string;
  policy_id: string;
  limits: EpisodeLimits | null;
  status: 'completed' | 'truncated' | 'failed';
  stop: { code: string; reason: string; cause_code?: string; cause_record_index?: number; evidence_failure_stage?: 'construction' | 'validation' };
  counts: { attempts: number; committed_transitions: number; rejected_candidates: number; rejections_at_final_boundary: number };
  initial_boundary: ReturnType<typeof summarizeEpisodeBoundary> | null;
  final_boundary: ReturnType<typeof summarizeEpisodeBoundary> | null;
  transition_ids: string[];
  records: Record<PlayerID, EpisodeRecord[]>;
  evidence_envelope: PipelineEpisodeEvidence | null;
  /** Simulator completion is not an attestation of faithful typed-state publication. */
  faithful_complete_episode: boolean;
}

/** False is conservative; true requires the full accepted capture and actor contracts. */
export function validatePipelineEpisodeFaithfulClaim(result: PipelineEpisodeResult): boolean {
  const fields = ['schema_version','run_id','battle_id','ruleset','policy_id','limits','status','stop','counts','initial_boundary','final_boundary','transition_ids','records','evidence_envelope','faithful_complete_episode'];
  if (result.schema_version !== PIPELINE_EPISODE_VERSION || typeof result.faithful_complete_episode !== 'boolean'
    || Object.keys(result).sort().join('|') !== fields.sort().join('|')) throw new Error('episode-faithful-schema');
  const envelope = result.evidence_envelope;
  const eligible = result.ruleset === 'gen9randombattle' && result.status === 'completed'
    && result.stop.code === 'episode/v1/terminal' && envelope?.schema_version === 'pipeline-episode-evidence/v2'
    && envelope.closure?.complete_capture === true;
  if (!eligible) {
    if (result.faithful_complete_episode) throw new Error('episode-faithful-ineligible');
    return false;
  }
  validatePipelineEpisodeEvidence(envelope, result.records as unknown as Record<PlayerID, EpisodeEvidenceRecord[]>, {
    run_id: result.run_id, battle_id: result.battle_id, ruleset: result.ruleset, policy_id: result.policy_id,
    limits: result.limits, origin_kind: envelope.origin.kind, initial_boundary: result.initial_boundary,
  } as EpisodeEvidenceExpectation);
  const keys = ['max_transitions', 'max_attempts', 'max_rejections_per_boundary'];
  if (!result.limits || Object.keys(result.limits).sort().join('|') !== keys.sort().join('|')
    || Object.values(result.limits).some(v => !Number.isSafeInteger(v) || v <= 0)) throw new Error('episode-faithful-limits');
  const counts = result.counts;
  if (Object.keys(counts).sort().join('|') !== ['attempts','committed_transitions','rejected_candidates','rejections_at_final_boundary'].sort().join('|')
    || Object.values(counts).some(v => !Number.isSafeInteger(v) || v < 0)
    || counts.committed_transitions !== envelope.commits.length || counts.attempts !== counts.committed_transitions + counts.rejected_candidates
    || counts.rejections_at_final_boundary > counts.rejected_candidates || counts.attempts > result.limits.max_attempts
    || counts.committed_transitions > result.limits.max_transitions || counts.rejections_at_final_boundary > result.limits.max_rejections_per_boundary
    || JSON.stringify(result.transition_ids) !== JSON.stringify(envelope.commits.map(c => c.transition.transition_id))) throw new Error('episode-faithful-counts');
  const final = envelope.commits.at(-1)?.boundary ?? envelope.origin.boundary, summary = result.final_boundary;
  if (!summary || ['step_index','kind','branch_id','state_fingerprint'].some(k => summary[k as keyof typeof summary] !== final[k as keyof typeof final])
    || PLAYERS.some(p => summary.perspectives[p].observation_id !== final.perspectives[p].observation_id
      || summary.perspectives[p].event_cursor !== final.perspectives[p].event_cursor
      || summary.perspectives[p].request_state !== classifyPipelineRequestState(final.perspectives[p])
      || summary.perspectives[p].winner !== final.perspectives[p].view.winner
      || !/^belief-[a-f0-9]{64}$/.test(summary.perspectives[p].belief_id))) throw new Error('episode-faithful-final-boundary');
  for (const p of PLAYERS) for (const record of result.records[p]) validatePipelineEpisodeRecordBundle(record);
  return true;
}

const DEFAULT_LIMITS: EpisodeLimits = { max_transitions: 256, max_attempts: 512, max_rejections_per_boundary: 3 };
function limitsFor(options: EpisodeExecutionOptions): EpisodeLimits {
  const supplied = options.limits ?? {};
  if (Object.keys(supplied).some((k) => !Object.hasOwn(DEFAULT_LIMITS, k))) throw new Error('invalid-options');
  const limits = { ...DEFAULT_LIMITS, ...supplied };
  if (Object.values(limits).some((v) => !Number.isSafeInteger(v) || v <= 0)
    || (options.action_order && !options.policy_id?.trim())
    || (options.policy_id !== undefined && !options.policy_id.trim())) throw new Error('invalid-options');
  return limits;
}
function terminal(boundary: PipelineBoundary): boolean {
  const [p1, p2] = PLAYERS.map((p) => boundary.perspectives[p].observation.view);
  if (boundary.kind !== 'terminal') return false;
  const observations = PLAYERS.map((player) => boundary.perspectives[player].observation);
  const winner = p1.winner;
  const winnerName = winner === 'p1' || winner === 'p2' ? p1.names[winner] : null;
  const expected = winner === 'tie' ? '|tie' : (winnerName ? `|win|${winnerName}` : null);
  if (!p1.terminated || !p2.terminated || !winner || p1.winner !== p2.winner
    || observations.some((observation) => observation.request !== null || observation.snapshot_phase !== 'terminal')
    || observations.some((observation) => observation.decision_availability.reason !== 'terminal')
    || observations[0].protocol_prefix.at(-1) !== expected) throw new Error('invalid-terminal');
  return true;
}
function actingPlayers(boundary: PipelineBoundary): PlayerID[] | null {
  const states = PLAYERS.map((p) => classifyPipelineRequestState(boundary.perspectives[p].observation));
  if (boundary.kind === 'joint_actionable' && states.every((s) => s === 'actionable' || s === 'forced_switch')) return [...PLAYERS];
  if (boundary.kind === 'one_sided_forced_switch' || boundary.kind === 'one_sided_revival') {
    const actor = states.indexOf(boundary.kind === 'one_sided_revival' ? 'revival_selection' : 'forced_switch');
    if (actor >= 0 && states[1 - actor] === 'waiting') return [PLAYERS[actor]];
  }
  return null;
}
function actionTuples(boundary: PipelineBoundary, actors: PlayerID[], options: EpisodeExecutionOptions): Partial<Record<PlayerID, CanonicalAction>>[] {
  let tuples: Partial<Record<PlayerID, CanonicalAction>>[] = [{}];
  for (const player of actors) {
    const observation = boundary.perspectives[player].observation;
    const request = observation.request!;
    const legal = [...request.legal_actions.available_indices].sort((a, b) => a - b);
    const ordered = options.action_order ? [...options.action_order(observation)] : legal;
    if (ordered.length !== legal.length || new Set(ordered).size !== legal.length
      || ordered.some((i) => !legal.includes(i))) throw new Error('invalid-policy-order');
    const actions = ordered.map((i) => canonicalActionFromLegalAction(request, i));
    tuples = tuples.flatMap((tuple) => actions.map((action) => ({ ...tuple, [player]: action })));
  }
  return tuples;
}
function tupleKey(actions: Partial<Record<PlayerID, CanonicalAction>>): string {
  return PLAYERS.map((p) => actions[p]?.action_id ?? '').join(':');
}
function classifyError(error: unknown): { status: 'truncated' | 'failed'; stop: PipelineEpisodeResult['stop'] } {
  const recordCause = error instanceof PipelineIntegrationError && Number.isSafeInteger(error.diagnostic.record_index)
    && error.diagnostic.record_index! >= 0 ? {cause_record_index: error.diagnostic.record_index} : {};
  if (error instanceof Error && (error.message === 'seeded-forced-switch/v1/unsupported-revival-blessing' || error.message === 'seeded-revival/v1/unsupported-request')) {
    return { status: 'truncated', stop: { code: 'episode/v1/unsupported-revival-blessing', reason: 'Revival request variant is outside the supported singles selection scope.', cause_code: error.message } };
  }
  if (error instanceof PipelineIntegrationError && (error.code === 'pipeline/v1/unresolved-protocol-alias'
    || error.code === 'pipeline/v1/unsupported-protocol-record'
    || (error.code === 'pipeline/v1/unsupported-observable-protocol' && error.diagnostic.detail.startsWith('Unsupported raw protocol event:')))) {
    return { status: 'truncated', stop: { code: 'episode/v1/unsupported-protocol', reason: 'Protocol evidence is outside the supported scope.', cause_code: error.code, ...recordCause } };
  }
  if (error instanceof SettlingError) {
    return { status: 'failed', stop: { code: 'episode/v1/settling-failed', reason: 'The simulator did not settle successfully.', cause_code: error.diagnostic.code } };
  }
  return { status: 'failed', stop: { code: 'episode/v1/execution-failed', reason: 'Initialization, action selection, or transition validation failed.',
    ...(error instanceof PipelineIntegrationError ? { cause_code: error.code, ...recordCause } : {}) } };
}

/** Owns and closes a fresh session. Only the returned per-player bundles are records. */
export async function runPipelineEpisode(options: PipelineEpisodeOptions): Promise<PipelineEpisodeResult> {
  return executeEpisode(options.battle_id, options.format, options, () => createPipelineIntegrationSession(options));
}
/** Transfers exclusive ownership of an existing session; outcome covers this segment only. */
export async function continuePipelineEpisode(session: PipelineIntegrationSession, options: EpisodeContinuationOptions = {}): Promise<PipelineEpisodeResult> {
  if (options.predecessor_evidence) validatePipelineEpisodePredecessor(options.predecessor_evidence, session.boundary, session.format);
  return executeEpisode(session.battle_id, session.format, options, async () => session, session, options.predecessor_evidence ?? null);
}

async function executeEpisode(
  battleId: string, format: string, options: EpisodeExecutionOptions,
  create: () => Promise<PipelineIntegrationSession>, owned?: PipelineIntegrationSession,
  predecessorEvidence: PipelineEpisodeEvidence | null = null,
): Promise<PipelineEpisodeResult> {
  const policy = options.policy_id ?? 'ascending-request-indices/v1';
  const result: PipelineEpisodeResult = {
    schema_version: PIPELINE_EPISODE_VERSION, run_id: '', battle_id: battleId, ruleset: format, policy_id: policy,
    limits: null, status: 'failed', stop: { code: 'episode/v1/invalid-options', reason: 'Episode options must specify valid finite limits and a versioned policy.' },
    counts: { attempts: 0, committed_transitions: 0, rejected_candidates: 0, rejections_at_final_boundary: 0 },
    initial_boundary: null, final_boundary: null, transition_ids: [], records: { p1: [], p2: [] },
    evidence_envelope: null, faithful_complete_episode: false,
  };
  let session = owned;
  const evidenceBoundaries: PipelineBoundary[] = [];
  const evidenceTransitions: Array<{ transition: EpisodeEvidenceTransition; actors: PlayerID[] }> = [];
  const stop = (code: string, reason: string) => {
    result.status = 'truncated'; result.stop = { code: `episode/v1/${code}`, reason };
  };
  try {
    if (session) {
      result.initial_boundary = result.final_boundary = summarizeEpisodeBoundary(session.boundary);
      evidenceBoundaries.push(session.boundary);
    }
    try { result.limits = limitsFor(options); } catch { return result; }
    if (format !== 'gen9randombattle') { stop('unsupported-format', 'Only gen9randombattle is supported.'); return result; }
    session = await create();
    let boundary = session.boundary;
    result.initial_boundary = result.final_boundary = summarizeEpisodeBoundary(boundary);
    if (!evidenceBoundaries.length) evidenceBoundaries.push(boundary);
    const attempted = new Set<string>();
    while (true) {
      if (terminal(boundary)) { result.status = 'completed'; result.stop = { code: 'episode/v1/terminal', reason: 'The committed simulator boundary is a win or tie.' }; break; }
      if (options.signal?.aborted) { stop('cancelled', 'The caller cancelled at a committed boundary.'); break; }
      if (result.counts.committed_transitions >= result.limits.max_transitions) { stop('transition-budget', 'The committed-transition budget is exhausted.'); break; }
      if (result.counts.attempts >= result.limits.max_attempts) { stop('attempt-budget', 'The total candidate-attempt budget is exhausted.'); break; }
      const actors = actingPlayers(boundary);
      if (!actors) { stop('unsupported-boundary', 'No supported transition exists for the committed request states.'); break; }
      session.assertSupportedSelectionRequests();
      const actions = actionTuples(boundary, actors, options).find((a) => !attempted.has(tupleKey(a)));
      if (!actions) { stop('action-exhausted', 'Every request-derived action combination at this boundary was rejected.'); break; }
      attempted.add(tupleKey(actions));
      result.counts.attempts++;
      try {
        const committed = actors.length === 2
          ? await session.step(actions as Record<PlayerID, CanonicalAction>)
          : actions[actors[0]]!.kind === 'revive'
            ? await session.stepRevival(actions[actors[0]]!)
            : await session.stepForcedSwitch(actions[actors[0]]!);
        // The accepted session validates lineage and publishes atomically before returning.
        // Accumulate once, synchronously, before observing cancellation or another budget.
        boundary = committed.boundary;
        const actorTransition = committed.record_bundles[actors[0]]!.transition;
        evidenceBoundaries.push(boundary);
        evidenceTransitions.push({
          actors: [...actors],
          transition: {
            schema_version: actorTransition.schema_version,
            transition_id: actorTransition.transition_id,
            parent_branch_id: actorTransition.parent_branch_id,
            branch_id: actorTransition.branch_id,
            input_state_fingerprint: actorTransition.input_state_fingerprint,
            output_state_fingerprint: actorTransition.output_state_fingerprint,
            simulator_revision: actorTransition.simulator_revision,
            step_index: actorTransition.step_index,
          },
        });
        result.final_boundary = summarizeEpisodeBoundary(boundary);
        result.transition_ids.push(committed.transition_id);
        for (const player of actors) result.records[player].push(committed.record_bundles[player]!);
        result.counts.committed_transitions++;
        result.counts.rejections_at_final_boundary = 0;
        attempted.clear();
      } catch (error) {
        if (session.boundary !== boundary) throw new Error('rejection-changed-committed-boundary');
        if (!(error instanceof PipelineIntegrationError) || error.code !== 'pipeline/v1/rejected-action') throw error;
        result.counts.rejected_candidates++;
        result.counts.rejections_at_final_boundary++;
        if (result.counts.rejections_at_final_boundary >= result.limits.max_rejections_per_boundary) {
          stop('rejection-limit', 'The rejected-candidate limit for this committed boundary is exhausted.'); break;
        }
      }
    }
  } catch (error) {
    Object.assign(result, classifyError(error));
  } finally {
    let faithfulCandidate = false;
    let evidenceStage: 'construction' | 'validation' = 'construction';
    try {
      // Run identity binds the segment origin, policy and budgets, never private state or wall time.
      result.run_id = `episode-${createHash('sha256').update(JSON.stringify({ schema: PIPELINE_EPISODE_VERSION,
        battle_id: battleId, format, policy, limits: result.limits, initial_boundary: result.initial_boundary })).digest('hex')}`;
      result.evidence_envelope = createPipelineEpisodeEvidence({
        run_id: result.run_id, battle_id: battleId, ruleset: format,
        kind: owned ? 'continuation_segment' : 'fresh_episode',
        boundaries: evidenceBoundaries, transitions: evidenceTransitions, predecessor: predecessorEvidence,
      });
      if (result.evidence_envelope) {
        evidenceStage = 'validation';
        faithfulCandidate = validatePipelineEpisodeFaithfulClaim(result);
        if (!faithfulCandidate) validatePipelineEpisodeEvidence(
          result.evidence_envelope,
          result.records as unknown as Record<PlayerID, EpisodeEvidenceRecord[]>,
          {
            run_id: result.run_id, battle_id: result.battle_id, ruleset: result.ruleset,
            policy_id: result.policy_id, limits: result.limits,
            origin_kind: owned ? 'continuation_segment' : 'fresh_episode',
            initial_boundary: result.initial_boundary,
          } as EpisodeEvidenceExpectation,
        );
      }
    } catch {
      const previous = result.stop;
      result.status = 'failed';
      result.stop = { code: 'episode/v1/evidence-invalid', reason: 'The committed two-perspective evidence envelope failed construction or validation.',
        cause_code: previous.cause_code ?? previous.code, evidence_failure_stage: evidenceStage,
        ...(previous.cause_record_index === undefined ? {} : {cause_record_index: previous.cause_record_index}) };
      result.evidence_envelope = null;
    }
    if (session) {
      try { await session.close(); } catch {
        const previous = result.stop;
        result.status = 'failed'; result.stop = { code: 'episode/v1/cleanup-failed',
          reason: 'Session resource cleanup failed; committed records remain valid.',
          cause_code: previous.cause_code ?? previous.code,
          ...(previous.cause_record_index === undefined ? {} : {cause_record_index: previous.cause_record_index}),
          ...(previous.evidence_failure_stage === undefined ? {} : {evidence_failure_stage: previous.evidence_failure_stage}) };
      }
    }
    result.faithful_complete_episode = faithfulCandidate && result.status === 'completed' && result.stop.code === 'episode/v1/terminal';
  }
  return result;
}
