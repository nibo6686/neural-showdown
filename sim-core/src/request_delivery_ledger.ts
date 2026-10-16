import { isDeepStrictEqual } from 'node:util';
import type { LocalBattleEnv } from './env_manager';
import type { PipelineBoundary } from './pipeline_integration';
import type { RequestEmissionReceipt } from './request_emission_trace';
import { PLAYERS, type PlayerID, type StepResult } from './types';

export type RequestDeliveryHandle = Readonly<object>;
export interface CommittedRequestDelivery {
  readonly owner: PlayerID;
  readonly session_occurrence: Readonly<object>;
  readonly sequence: number;
  readonly delivery_reference: Readonly<object>;
  readonly source: RequestEmissionReceipt;
}
export interface RequestDeliveryBoundary {
  readonly owner: PlayerID;
  readonly session_occurrence: Readonly<object>;
  readonly observation_id: string;
  readonly branch_id: string;
  readonly step_index: number;
  readonly prefix: readonly string[];
  readonly boundary_cursor: number;
  readonly parent: Readonly<{ observation_id: string; branch_id: string; step_index: number }> | null;
  readonly trace: readonly RequestEmissionReceipt[];
  readonly selected: RequestEmissionReceipt | null;
  readonly current: CommittedRequestDelivery | null;
}
export interface RequestDeliveryHistory {
  readonly boundaries: readonly RequestDeliveryBoundary[];
  readonly deliveries: readonly CommittedRequestDelivery[];
}
const token = (): Readonly<object> => Object.freeze(Object.create(null));
function fail(reason: string): never { throw new Error(`request-delivery/v1/${reason}`); }
const raw = (result: StepResult, owner: PlayerID): unknown => result.requests[owner]?.raw ?? null;

/** Trusted session controller; no transported trace or certificate admission API. */
export class RequestDeliveryLedger {
  readonly #occurrence = token();
  #valid = true;
  #parent: PipelineBoundary | null = null;
  #histories: Record<PlayerID, RequestDeliveryHistory> = {
    p1: Object.freeze({ boundaries: Object.freeze([]), deliveries: Object.freeze([]) }),
    p2: Object.freeze({ boundaries: Object.freeze([]), deliveries: Object.freeze([]) }),
  };
  #handles: Record<PlayerID, RequestDeliveryHandle> = { p1: token(), p2: token() };
  #raw: Record<PlayerID, unknown> = { p1: null, p2: null };
  #restores = new WeakMap<object, { environment: LocalBattleEnv; parent: PipelineBoundary; traces: Record<PlayerID, readonly RequestEmissionReceipt[]> }>();
  #prepared = new WeakMap<object, { parent: PipelineBoundary | null; boundary: PipelineBoundary; histories: Record<PlayerID, RequestDeliveryHistory>; raws: Record<PlayerID, unknown> }>();

  #healthTransfers = new WeakMap<object, { prepared: object; owner: PlayerID; environment: LocalBattleEnv; boundary: PipelineBoundary; row: RequestDeliveryBoundary }>();
  #healthEnvironments = new WeakMap<object, LocalBattleEnv>();

  #ready: { token: object; state: NonNullable<ReturnType<RequestDeliveryLedger["preparedState"]>> } | null = null;
  private preparedState(token: object) { return this.#prepared.get(token); }
  #open(): void { if (!this.#valid) fail('revoked'); }
  #owner(owner: PlayerID): void { if (!PLAYERS.includes(owner)) fail('invalid-owner'); }
  #traces(environment: LocalBattleEnv): Record<PlayerID, readonly RequestEmissionReceipt[]> {
    return { p1: environment.inspectRequestEmissionTrace(environment.getRequestEmissionTraceHandle('p1'), 'p1'),
      p2: environment.inspectRequestEmissionTrace(environment.getRequestEmissionTraceHandle('p2'), 'p2') };
  }
  #select(trace: readonly RequestEmissionReceipt[], result: StepResult, owner: PlayerID): RequestEmissionReceipt | null {
    if (!result.requests[owner] || result.views[owner]?.terminated) return null;
    // The pinned single-record owner FIFO feeds the external handler in order.
    // Only its last receipt can populate a settled reported request.
    const selected = trace.at(-1);
    if (!selected || selected.owner !== owner || !isDeepStrictEqual(JSON.parse(selected.request_json), raw(result, owner))) fail('settled-request-mismatch');
    if (result.requests[owner]!.team_preview) fail('suppressed-request');
    return selected;
  }

  /** Capture restoration before actions, while the held parent is still live. */
  restored(environment: LocalBattleEnv, result: StepResult, parent: PipelineBoundary): object {
    this.#open();
    if (parent !== this.#parent) fail('foreign-parent');
    const traces = this.#traces(environment);
    for (const owner of PLAYERS) {
      if (traces[owner].some(row => row.origin !== 'restore_reemit')) fail('unexpected-native-restore');
      const selected = this.#select(traces[owner], result, owner);
      if (selected && (!this.#histories[owner].boundaries.at(-1)?.current || !isDeepStrictEqual(raw(result, owner), this.#raw[owner]))) fail('missing-parent-delivery');
    }
    const proof = token(); this.#restores.set(proof, { environment, parent, traces }); return proof;
  }

  /** Both-owner preparation is detached; only this ledger can commit its token. */
  prepare(environment: LocalBattleEnv, result: StepResult, boundary: PipelineBoundary, parent: PipelineBoundary | null, restoration?: object): object {
    this.#open();
    if (parent !== this.#parent || (parent ? boundary.step_index !== parent.step_index + 1 : boundary.step_index !== 0)) fail('foreign-parent');
    const restore = restoration && this.#restores.get(restoration);
    if (parent && (!restore || restore.environment !== environment || restore.parent !== parent)) fail('missing-restore-continuity');
    const traces = this.#traces(environment);
    const histories = {} as Record<PlayerID, RequestDeliveryHistory>;
    const raws = {} as Record<PlayerID, unknown>;
    for (const owner of PLAYERS) {
      const observation = boundary.perspectives[owner].observation;
      if (observation.perspective !== owner || observation.battle_id !== boundary.battle_id || observation.event_cursor !== observation.protocol_prefix.length) fail('observation-join');
      const prior = this.#histories[owner];
      const priorBoundary = prior.boundaries.at(-1);
      if (parent && (!priorBoundary || priorBoundary.observation_id !== parent.perspectives[owner].observation.observation_id
        || priorBoundary.branch_id !== parent.branch_id || priorBoundary.step_index !== parent.step_index
        || priorBoundary.prefix.some((line, index) => observation.protocol_prefix[index] !== line))) fail('prefix-parent-join');
      if (restore && (restore.traces[owner].length > traces[owner].length || restore.traces[owner].some((row, index) => row !== traces[owner][index]))) fail('foreign-trace-occurrence');
      const selected = this.#select(traces[owner], result, owner);
      let current: CommittedRequestDelivery | null = null;
      let deliveries = prior.deliveries;
      if (selected?.origin === 'native_emission') {
        if (prior.boundaries.some(row => row.trace.some(receipt => receipt.producer_occurrence === selected.producer_occurrence))) fail('reused-occurrence');
        current = Object.freeze({ owner, session_occurrence: this.#occurrence, sequence: deliveries.length,
          delivery_reference: token(), source: selected });
        deliveries = Object.freeze([...deliveries, current]);
      } else if (selected) {
        if (!restore || !restore.traces[owner].includes(selected) || !priorBoundary?.current
          || !isDeepStrictEqual(raw(result, owner), this.#raw[owner])) fail('missing-parent-delivery');
        current = priorBoundary.current;
      }
      const row: RequestDeliveryBoundary = Object.freeze({ owner, session_occurrence: this.#occurrence,
        observation_id: observation.observation_id, branch_id: boundary.branch_id, step_index: boundary.step_index,
        prefix: Object.freeze([...observation.protocol_prefix]), boundary_cursor: observation.protocol_prefix.length,
        parent: parent ? Object.freeze({ observation_id: parent.perspectives[owner].observation.observation_id, branch_id: parent.branch_id, step_index: parent.step_index }) : null,
        trace: traces[owner], selected, current });
      histories[owner] = Object.freeze({ boundaries: Object.freeze([...prior.boundaries, row]), deliveries });
      raws[owner] = structuredClone(raw(result, owner));
    }
    const prepared = token(); this.#healthEnvironments.set(prepared, environment); this.#prepared.set(prepared, { parent, boundary, histories, raws }); return prepared;
  }
  prepareHealthTransfer(prepared: object, owner: PlayerID): object {
    this.#open(); this.#owner(owner); const state = this.#prepared.get(prepared), environment = this.#healthEnvironments.get(prepared);
    if (!state || !environment) fail('foreign-health-preparation');
    const key = token(); this.#healthTransfers.set(key, { prepared, owner, environment, boundary: state.boundary, row: state.histories[owner].boundaries.at(-1)! }); return key;
  }
  readHealthTransfer(key: object, owner: PlayerID, environment: object, boundary: PipelineBoundary): RequestDeliveryBoundary {
    this.#open(); this.#owner(owner); const entry = this.#healthTransfers.get(key);
    if (!entry || entry.owner !== owner || entry.environment !== environment || entry.boundary !== boundary
      || !this.#prepared.has(entry.prepared)) fail('foreign-or-revoked-health-transfer'); return entry.row;
  }
  discard(prepared: object): void { this.#prepared.delete(prepared); if (this.#ready?.token === prepared) this.#ready = null; }
  preflight(prepared: object): void {
    this.#open(); const state = this.#prepared.get(prepared);
    if (!state || state.parent !== this.#parent) fail('foreign-or-stale-preparation');
    this.#ready = { token: prepared, state };
  }
  /** Session-only, immediately after preflight; assignment-only installation. */
  installReady(): void {
    const ready = this.#ready!;
    this.#parent = ready.state.boundary; this.#histories = ready.state.histories; this.#raw = ready.state.raws;
    this.#prepared.delete(ready.token); this.#ready = null;
  }
  commit(prepared: object): void { this.preflight(prepared); this.installReady(); }
  handle(owner: PlayerID): RequestDeliveryHandle { this.#open(); this.#owner(owner); return this.#handles[owner]; }
  read(handle: RequestDeliveryHandle, owner: PlayerID, expected?: RequestDeliveryBoundary): RequestDeliveryHistory {
    this.#open(); this.#owner(owner);
    if (handle !== this.#handles[owner]) fail('foreign-or-forged-handle');
    const history = this.#histories[owner];
    if (expected && !history.boundaries.includes(expected)) fail('foreign-boundary-binding');
    return history;
  }
  revoke(): void {
    this.#ready = null; this.#valid = false; this.#handles = { p1: token(), p2: token() };
    this.#healthTransfers = new WeakMap(); this.#healthEnvironments = new WeakMap(); this.#restores = new WeakMap(); this.#prepared = new WeakMap(); this.#raw = { p1: null, p2: null };
    this.#histories = { p1: { boundaries: [], deliveries: [] }, p2: { boundaries: [], deliveries: [] } };
  }
}
