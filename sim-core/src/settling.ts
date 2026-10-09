/** Delivery barrier for the pinned Showdown getPlayerStreams fan-out. */
export type SettlingConsumer = 'p1' | 'p2' | 'spectator';
export interface SettlingOptions {
  timeout_ms?: number;
  max_messages?: number;
  /** In-process clock/scheduler injection; never part of observations or identity. */
  now?: () => number;
  schedule_timeout?: (expire: () => void, milliseconds: number) => () => void;
}
export type SettlingFailureCode = 'timeout' | 'message-limit' | 'simulator-error' | 'stream-closed' | 'cancelled';
export class SettlingError extends Error {
  readonly diagnostic: { schema_version: 'settling-failure/v1'; code: string; timeout_ms: number; max_messages: number };
  constructor(code: SettlingFailureCode, timeout: number, messages: number) {
    super(`settling/v1/${code}`);
    this.diagnostic = { schema_version: 'settling-failure/v1', code: this.message, timeout_ms: timeout, max_messages: messages };
  }
}

export class SettlingBarrier {
  readonly timeout: number;
  readonly maxMessages: number;
  private readonly now: () => number;
  private readonly schedule: NonNullable<SettlingOptions['schedule_timeout']>;
  private expected = { p1: 0, p2: 0, spectator: 0 };
  private consumed = { p1: 0, p2: 0, spectator: 0 };
  private messages = 0;
  private settledMessages = 0;
  private deadline: number | null = null;
  private waiters = new Set<() => void>();
  private closed = new Set<SettlingConsumer | 'source'>();
  private ended = false;
  private failure: SettlingError | null = null;

  constructor(options: SettlingOptions = {}) {
    this.timeout = options.timeout_ms ?? 5000;
    this.maxMessages = options.max_messages ?? 100000;
    for (const value of [this.timeout, this.maxMessages]) {
      if (!Number.isSafeInteger(value) || value <= 0) throw new Error('Settling limits must be positive safe integers.');
    }
    if (this.timeout > 2147483647) throw new Error('Settling timeout exceeds the timer range.');
    this.now = options.now ?? (() => performance.now());
    this.schedule = options.schedule_timeout ?? ((expire, ms) => {
      const timer = setTimeout(expire, ms);
      return () => clearTimeout(timer);
    });
  }

  get stopped(): boolean { return !!this.failure; }
  get terminalEmitted(): boolean { return this.ended; }
  get pendingWaits(): number { return this.waiters.size; }
  private notify(): void {
    const waiting = [...this.waiters];
    this.waiters.clear();
    for (const wake of waiting) wake();
  }
  fail(code: SettlingFailureCode): void {
    this.failure ??= new SettlingError(code, this.timeout, this.maxMessages);
    this.notify();
  }
  streamClosed(consumer: SettlingConsumer | 'source' = 'source'): void {
    this.closed.add(consumer);
    this.notify();
  }
  emitted(type: string, data: string): void {
    this.messages++;
    if (type === 'update') {
      for (const consumer of ['p1', 'p2', 'spectator'] as const) this.expected[consumer]++;
    } else if (type === 'sideupdate') {
      const side = data.split('\n', 1)[0];
      if (side === 'p1' || side === 'p2') this.expected[side]++;
    } else if (type === 'end') {
      // Only the existence of the signal is retained, never its private payload.
      this.ended = true;
    }
    this.checkLimits();
    this.notify();
  }
  acknowledge(consumer: SettlingConsumer): void {
    this.consumed[consumer]++;
    if (this.consumed[consumer] > this.expected[consumer]) this.fail('simulator-error');
    this.notify();
  }
  private checkLimits(): void {
    if (this.messages - this.settledMessages > this.maxMessages) this.fail('message-limit');
    if (this.deadline !== null && this.now() >= this.deadline) this.fail('timeout');
  }
  async wait(boundary: () => 'decision' | 'terminal' | null): Promise<void> {
    if (this.deadline !== null) throw new Error('Settling operations must be serialized.');
    this.deadline = this.now() + this.timeout;
    const cancelTimeout = this.schedule(() => this.fail('timeout'), this.timeout);
    try {
      while (true) {
        this.checkLimits();
        if (this.failure) throw this.failure;
        const delivered = (['p1', 'p2', 'spectator'] as const).every((p) => this.expected[p] === this.consumed[p]);
        const kind = delivered ? boundary() : null;
        // EOF is only normal after complete terminal output, never at a decision.
        if (kind === 'terminal' && this.ended) break;
        if (this.closed.size && (!this.ended || delivered
          || [...this.closed].some((c) => c !== 'source' && this.expected[c] !== this.consumed[c]))) {
          throw new SettlingError('stream-closed', this.timeout, this.maxMessages);
        }
        if (kind === 'decision' && !this.ended) break;
        await new Promise<void>((resolve) => this.waiters.add(resolve));
      }
      this.settledMessages = this.messages;
    } finally {
      cancelTimeout();
      this.deadline = null;
      this.waiters.clear();
    }
  }
}
