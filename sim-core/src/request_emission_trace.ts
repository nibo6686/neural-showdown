import type { PlayerID } from './types';

export type RequestEmissionOrigin = 'native_emission' | 'restore_reemit';
export type RequestTraceHandle = Readonly<object>;
export interface RequestEmissionReceipt {
  readonly owner: PlayerID;
  readonly producer_occurrence: Readonly<object>;
  readonly emission_index: number;
  readonly owner_emission_index: number;
  readonly origin: RequestEmissionOrigin;
  readonly request_record: string;
  readonly request_json: string;
  readonly receipt: Readonly<{ owner_receipt_index: number; record: string; json: string }>;
}
export type RequestProducerEmission = Omit<RequestEmissionReceipt, 'receipt'>;
type Emission = RequestProducerEmission;
const token = (): Readonly<object> => Object.freeze(Object.create(null));

/** Private producer/owner-stream FIFO evidence, not freshness or action authority. */
export class RequestEmissionTrace {
  #valid = true;
  #origin: RequestEmissionOrigin | null = null;
  #nextEmission = 0;
  readonly #occurrence = token();
  #streams: Partial<Record<PlayerID, object>> = {};
  #handles: Partial<Record<PlayerID, RequestTraceHandle>> = {};
  #pending: Record<PlayerID, Emission[]> = { p1: [], p2: [] };
  #rows: Record<PlayerID, RequestEmissionReceipt[]> = { p1: [], p2: [] };
  #counts: Record<PlayerID, number> = { p1: 0, p2: 0 };

  constructor(private readonly healthReceipt?: (emission: RequestProducerEmission, receipt: RequestEmissionReceipt) => void) {}

  #requireValid(): void { if (!this.#valid) throw new Error('request-trace/v1/invalidated'); }
  #owner(owner: PlayerID): void {
    if (owner !== 'p1' && owner !== 'p2') throw new Error('request-trace/v1/invalid-owner');
  }
  #reject(reason: string): never {
    this.invalidate();
    throw new Error(`request-trace/v1/${reason}`);
  }
  bind(owner: PlayerID, stream: object): void {
    this.#requireValid(); this.#owner(owner);
    if (this.#streams[owner] || !stream || typeof stream !== 'object'
      || Object.values(this.#streams).includes(stream)) this.#reject('invalid-stream-enrollment');
    this.#streams[owner] = stream;
    this.#handles[owner] = token();
  }
  atProducer(origin: RequestEmissionOrigin, emit: () => void): void {
    this.#requireValid();
    if (origin !== 'native_emission' && origin !== 'restore_reemit') this.#reject('unsupported-origin');
    const previous = this.#origin;
    this.#origin = origin;
    try {
      if (emit() !== undefined) this.#reject('non-synchronous-producer');
    } finally { this.#origin = previous; }
  }
  emitted(type: string, data: string): RequestProducerEmission | undefined {
    this.#requireValid();
    if (type !== 'sideupdate') return;
    const split = data.indexOf('\n'), record = data.slice(split + 1);
    if (!record.trimStart().startsWith('|request|')) return;
    const owner = data.slice(0, split) as PlayerID;
    if (split < 0 || (owner !== 'p1' && owner !== 'p2')) this.#reject('unsupported-owner');
    if (!this.#origin || !this.#streams[owner]) this.#reject('unsupported-producer');
    if (record.includes('\n')) this.#reject('multi-record-request');
    const emission = Object.freeze({ owner, producer_occurrence: this.#occurrence,
      emission_index: ++this.#nextEmission, owner_emission_index: ++this.#counts[owner], origin: this.#origin,
      request_record: record, request_json: record.slice(record.indexOf('|request|') + '|request|'.length) });
    this.#pending[owner].push(emission); return emission;
  }
  received(owner: PlayerID, stream: object, record: string): void {
    this.#requireValid(); this.#owner(owner);
    if (this.#streams[owner] !== stream) this.#reject('foreign-receipt-stream');
    const next = this.#pending[owner][0];
    if (!next) this.#reject('missing-or-duplicate-emission');
    if (next.request_record !== record) this.#reject('receipt-order-or-text-mismatch');
    this.#pending[owner].shift();
    const receipt = Object.freeze({ ...next, receipt: Object.freeze({
      owner_receipt_index: this.#rows[owner].length + 1, record,
      json: record.slice(record.indexOf('|request|') + '|request|'.length),
    }) });
    this.#rows[owner].push(receipt); this.healthReceipt?.(next, receipt);
  }
  handle(owner: PlayerID): RequestTraceHandle {
    this.#requireValid(); this.#owner(owner);
    const handle = this.#handles[owner];
    if (!handle) throw new Error('request-trace/v1/unbound-owner');
    return handle;
  }
  inspect(handle: RequestTraceHandle, owner: PlayerID): readonly RequestEmissionReceipt[] {
    this.#requireValid(); this.#owner(owner);
    if (!this.#handles[owner] || handle !== this.#handles[owner]) throw new Error('request-trace/v1/foreign-or-forged-handle');
    if (this.#pending.p1.length || this.#pending.p2.length) throw new Error('request-trace/v1/unreceived-emission');
    return Object.freeze([...this.#rows[owner]]);
  }
  invalidate(): void {
    this.#valid = false; this.#origin = null; this.#streams = {}; this.#handles = {};
    this.#pending = { p1: [], p2: [] }; this.#rows = { p1: [], p2: [] };
  }
}
