import { assertAuthoritativeEnvironment } from './env_manager';
import { SimulationOnlyAuthorityError } from './simulation_authority';
import { isDeepStrictEqual, types as utilTypes } from 'node:util';
import type { CanonicalActionRequestContext } from './canonical_action';
import type { ObservableBattleState } from './observable_state';
import type { OwnerKnowledgeHandle, OwnerKnowledgeRead } from './native_owner_knowledge';
import type { PlayerID } from './types';
import type { PipelineBoundary } from './pipeline_integration';
import type { CommittedRequestDelivery, RequestDeliveryBoundary } from './request_delivery_ledger';
import type { RequestEmissionReceipt } from './request_emission_trace';

export interface OwnedDecisionInput {
  readonly observation: ObservableBattleState;
  readonly knowledge: OwnerKnowledgeRead;
  readonly action_context: CanonicalActionRequestContext;
  readonly legal_indices: readonly number[];
  readonly completeness: 'incomplete';
}

export interface OwnedDecisionOrder {
  readonly indices: readonly number[];
}

export type OwnedActionOrderCallback = (input: OwnedDecisionInput) => readonly number[];
export interface OwnedActionOrderRegistration {
  readonly recipient: object;
  readonly callback: OwnedActionOrderCallback;
}
export type OwnedActionOrderRegistrations = Readonly<Record<PlayerID, OwnedActionOrderRegistration>>;

export interface OwnedDecisionFrame {
  readonly owner: PlayerID;
  readonly recipient: object;
  readonly knowledge_handle: OwnerKnowledgeHandle;
  readonly knowledge: OwnerKnowledgeRead;
  readonly observation: ObservableBattleState;
  readonly environment: object;
  readonly boundary: PipelineBoundary;
  readonly session_occurrence: object;
  readonly delivery_boundary: RequestDeliveryBoundary;
  readonly current_delivery: CommittedRequestDelivery;
  readonly selected_receipt: RequestEmissionReceipt;
  readonly action_context: CanonicalActionRequestContext;
  readonly legal_indices: readonly number[];
}

type PrivateFrame = OwnedDecisionFrame & { order: OwnedDecisionOrder; input: OwnedDecisionInput };
const fixed = (code: string): Error => new Error(`owned-decision-input/v1/${code}`);
const SAFE_ERRORS = new Set([
  'owned-decision-input/v1/revoked',
  'owned-decision-input/v1/invalid-order',
  'owned-decision-input/v1/callback-failed',
  'owned-decision-input/v1/synchronous-callback-required',
  'owned-decision-input/v1/foreign-or-stale-order',
  'owned-decision-input/v1/invalid-batch',
  'owned-decision-input/v1/stale-or-unsupported-frame',
  'owned-decision-input/v1/stale-action-context',
  'owned-decision-input/v1/unsupported-frame',
  'owned-decision-input/v1/reentrant-call',
]);

export function sanitizeOwnedDecisionInputError(error: unknown): Error | undefined {
  try {
    if (!(error instanceof Error)) return undefined;
    const message = error.message;
    if (typeof message !== 'string' || !SAFE_ERRORS.has(message)) return undefined;
    return fixed(message.slice('owned-decision-input/v1/'.length));
  } catch {
    return undefined;
  }
}

function deepFreeze<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function permutation(value: unknown, legal: readonly number[]): readonly number[] {
  try {
    if (!Array.isArray(value) || value.length !== legal.length) throw fixed('invalid-order');
    const result: number[] = [];
    for (let i = 0; i < value.length; i++) {
      if (!Object.hasOwn(value, i)) throw fixed('invalid-order');
      const index: unknown = value[i];
      if (typeof index !== 'number' || !Number.isSafeInteger(index) || !legal.includes(index) || result.includes(index)) {
        throw fixed('invalid-order');
      }
      result.push(index);
    }
    if (result.length !== legal.length) throw fixed('invalid-order');
    return Object.freeze(result);
  } catch (error) {
    throw fixed('invalid-order');
  }
}

/** Session-local issuer. The private frame table is keyed only by held order identity. */
export class OwnedDecisionInputController {
  readonly #frames = new WeakMap<object, PrivateFrame>();
  readonly #pending = new Map<PlayerID, PrivateFrame>();
  #closed = false;

  issue(frame: OwnedDecisionFrame, callback: OwnedActionOrderCallback, validate: () => void): OwnedDecisionOrder {
    try {
      assertAuthoritativeEnvironment(frame.environment);
      if (this.#closed) throw fixed('revoked');
      validate();
      if (this.#pending.has(frame.owner)) this.#pending.clear();
      const input = deepFreeze({
        observation: frame.observation,
        knowledge: frame.knowledge,
        action_context: frame.action_context,
        legal_indices: Object.freeze([...frame.legal_indices]),
        completeness: 'incomplete' as const,
      });
      let returned: unknown;
      try { returned = callback(input); } catch { throw fixed('callback-failed'); }
      if (utilTypes.isPromise(returned)) {
        try { void Promise.prototype.then.call(returned as Promise<unknown>, undefined, () => undefined); } catch { /* fixed denial below */ }
        throw fixed('synchronous-callback-required');
      }
      if (!Array.isArray(returned)) throw fixed('synchronous-callback-required');
      const indices = permutation(returned, frame.legal_indices);
      validate();
      const order: OwnedDecisionOrder = Object.freeze({ indices });
      const privateFrame: PrivateFrame = Object.freeze({ ...frame, order, input });
      this.#frames.set(order as object, privateFrame);
      this.#pending.set(frame.owner, privateFrame);
      return order;
    } catch (error) {
      this.#pending.clear();
      if (error instanceof SimulationOnlyAuthorityError) throw error;
      const safeError = sanitizeOwnedDecisionInputError(error);
      if (safeError) throw safeError;
      throw fixed('stale-or-unsupported-frame');
    }
  }

  assertBatch(
    orders: readonly OwnedDecisionOrder[],
    expectedOwners: readonly PlayerID[],
    validate: (frame: OwnedDecisionFrame) => void,
  ): ReadonlyMap<PlayerID, OwnedDecisionFrame> {
    if (this.#closed) throw fixed('revoked');
    try {
      if (!Array.isArray(orders) || orders.length !== expectedOwners.length
        || new Set(expectedOwners).size !== expectedOwners.length) throw fixed('invalid-batch');
      const frames = new Map<PlayerID, OwnedDecisionFrame>();
      for (const order of orders) {
        const frame = order && typeof order === 'object' ? this.#frames.get(order as object) : undefined;
        if (!frame || frames.has(frame.owner) || this.#pending.get(frame.owner) !== frame) throw fixed('foreign-or-stale-order');
        validate(frame);
        if (!isDeepStrictEqual(order.indices, frame.order.indices)) throw fixed('foreign-or-stale-order');
        frames.set(frame.owner, frame);
      }
      if (expectedOwners.some(owner => !frames.has(owner)) || this.#pending.size !== frames.size) throw fixed('invalid-batch');
      this.#pending.clear();
      return frames;
    } catch (error) {
      this.#pending.clear();
      const safeError = sanitizeOwnedDecisionInputError(error);
      if (safeError) throw safeError;
      throw fixed('stale-or-unsupported-frame');
    }
  }

  invalidate(): void { this.#pending.clear(); }
  revoke(): void { this.#closed = true; this.#pending.clear(); }
}

export function assertCanonicalContextEqual(
  expected: CanonicalActionRequestContext,
  actual: CanonicalActionRequestContext,
): void {
  if (!isDeepStrictEqual(expected, actual)) throw fixed('stale-action-context');
}
