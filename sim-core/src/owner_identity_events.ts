import type { PipelineBoundary } from './pipeline_integration';
import { isDeepStrictEqual } from 'node:util';
import type { Battle } from 'pokemon-showdown';
import { BattleActions } from 'pokemon-showdown/dist/sim/battle-actions';
import { NativeBirthEnrollment, NativeObjectAssociation, type NativeRestoreTicket, type SwitchActorReceiver } from './owner_identity_crosswalk';
import type { SeededBattleSnapshot } from './transition';
import type { PlayerID } from './types';

const token = (): object => Object.freeze(Object.create(null));
function fail(reason: string): never { throw new Error('switch-events/v1/' + reason); }
type Actor = { owner: PlayerID; slot: number; original: object; lease: object };
type Writer = { token: object; actor: Readonly<Omit<Actor, 'lease'>>; rows: Row[]; valid: boolean };
type Row = { token: object; version: number; writer?: Writer; alive: boolean };
type Frame = { token: object; bytes: string[]; rows: Array<{ token: object; version: number }>; publicRows: number[]; received: boolean };
export type SwitchEventHandle = Readonly<object>;
export interface CommittedSwitchEvent {
  readonly owner: PlayerID; readonly original_slot: number; readonly event_index: number;
  readonly public_index: number; readonly prefix_index: number; readonly branch_id: string; readonly step_index: number;
}
export interface SwitchEventHistory {
  readonly owner: PlayerID; readonly events: readonly CommittedSwitchEvent[];
  readonly branch_id: string; readonly step_index: number;
}
type EventState = { parent: PipelineBoundary; snapshot: SeededBattleSnapshot;
  histories: Record<PlayerID, SwitchEventHistory>; handles: Record<PlayerID, SwitchEventHandle>;
  bindings: Map<object, { version: number; publicIndex: number; prefixIndex: number }> };
type Preparation = { environment: object; parent: PipelineBoundary | null; state: EventState };
type Lineage = { rows: Row[]; expected: string[] };
function copyRows(rows: Row[]): Row[] {
  const writers = new Map<Writer, Writer>();
  return rows.map(row => {
    let writer: Writer | undefined;
    if (row.writer) {
      writer = writers.get(row.writer);
      if (!writer) {
        writer = { token: row.writer.token, actor: row.writer.actor, rows: [],
          valid: row.writer.valid && row.writer.rows.every(leaf => leaf.alive) };
        writers.set(row.writer, writer);
      }
    }
    const copy = { ...row, ...(writer ? { writer } : {}) };
    writer?.rows.push(copy); return copy;
  });
}

type World = {
  battle: any; stream: object; spectator?: object; load: () => void; actors: Map<object, Actor>;
  leases: Record<PlayerID, object>; rows: Row[]; log: string[]; proxy: string[];
  writers: Writer[]; frames: Frame[]; fifo: Frame[]; valid: boolean; active: boolean;
  public: Array<{ token: object; version: number; byte: string }>; source?: SeededBattleSnapshot; parent?: PipelineBoundary;
  detach: Array<() => void>; sending?: Frame;
};

/** Session-private tentative infrastructure. No committed event capability or wire projection. */
export class SwitchEventHost {
  #worlds = new Map<object, World>();
  #spectators = new Map<object, object>();
  #snapshots = new WeakMap<object, Lineage>();
  #raw = new WeakMap<object, Lineage>();
  #closed = false;
  #current: EventState | null = null;
  #prepared = new Map<object, Preparation>();
  #ready: Preparation | null = null;
  readonly #birth: NativeBirthEnrollment;
  readonly #association: NativeObjectAssociation;
  constructor(birth: NativeBirthEnrollment, association: NativeObjectAssociation) {
    this.#birth = birth; this.#association = association;
    const receive: SwitchActorReceiver = (env, battle, rows, source, parent) => {
      const world = this.world(env);
      if (world.battle !== battle || world.actors.size) fail('foreign-or-duplicate-actor-source');
      const actors = new Map<object, Actor>();
      for (const owner of ['p1', 'p2'] as const) {
        rows[owner].objects.forEach((actor, i) => {
          if (!actor || actors.has(actor) || actor.side !== battle[owner]) fail('invalid-actor-source');
          actors.set(actor, { owner, slot: i + 1, original: rows[owner].original, lease: world.leases[owner] });
        });
      }
      if (source) {
        const lineage = this.#snapshots.get(source);
        if (!lineage || !isDeepStrictEqual(lineage.expected, battle.log)) fail('missing-held-log-lineage');
        // The B2 controller validates exact snapshot/parent/ticket before this callback.
        world.rows = copyRows(lineage.rows); world.source = source; world.parent = parent;
      }
      world.actors = actors;
    };
    birth.registerSwitchActorReceiver(receive); association.registerSwitchActorReceiver(receive);
  }
  private world(env: object): World {
    const world = this.#worlds.get(env);
    if (this.#closed || !world?.active) fail('unavailable-world');
    return world!;
  }
  attachBirth(env: object, battle: Battle, stream: object): void {
    this.attach(env, battle, stream, () => this.#birth.transferSwitchActors(env, battle));
  }
  attachRestored(env: object, battle: Battle, stream: object, ticket: NativeRestoreTicket): void {
    this.attach(env, battle, stream, () => this.#association.transferSwitchActors(env, battle, ticket));
    try { this.world(env).load(); } catch (error) { this.release(env); throw error; }
  }
  private attach(env: object, battle: Battle, stream: object, load: () => void): void {
    if (this.#closed || this.#worlds.has(env)) fail('duplicate-world');
    const native = battle as any, log = native.log as string[];
    const world: World = { battle: native, stream, load, actors: new Map(), leases: { p1: token(), p2: token() },
      rows: log.map(() => ({ token: token(), version: 0, alive: true })), log, proxy: log,
      writers: [], frames: [], fifo: [], public: [], active: true, valid: true, detach: [] };
    this.#worlds.set(env, world); world.spectator = this.#spectators.get(env);
    let writing: Writer | undefined;
    const removed = (rows: Row[]) => { for (const row of rows) { row.alive = false; if (row.writer) row.writer.valid = false; } };
    const fresh = (): Row => {
      const row: Row = { token: token(), version: 0, alive: true, ...(writing ? { writer: writing } : {}) };
      writing?.rows.push(row); return row;
    };
    const index = (key: PropertyKey): number | null => typeof key === 'string' && /^(0|[1-9][0-9]*)$/.test(key) ? Number(key) : null;
    const proxy = new Proxy(log, {
      get(target, key, receiver) {
        if (key === 'push') return (...values: string[]) => { world.rows.push(...values.map(fresh)); return target.push(...values); };
        if (key === 'splice') return (...args: any[]) => {
          const n = target.length, start = Number(args[0]) || 0;
          const at = start < 0 ? Math.max(n + Math.trunc(start), 0) : Math.min(Math.trunc(start), n);
          const count = args.length === 1 ? n - at : Math.min(Math.max(Math.trunc(Number(args[1])) || 0, 0), n - at);
          const values = args.slice(2); removed(world.rows.splice(at, count, ...values.map(fresh)));
          return target.splice(at, count, ...values);
        };
        if (['sort', 'reverse', 'copyWithin', 'fill', 'shift', 'unshift', 'pop'].includes(String(key))) {
          return (...args: any[]) => { world.valid = false; return (Array.prototype as any)[key].apply(receiver, args); };
        }
        return Reflect.get(target, key, receiver);
      },
      set(target, key, value) {
        if (key === 'length') {
          const length = Number(value);
          if (!Number.isInteger(length) || length < 0 || length > target.length) world.valid = false;
          if (length < target.length) removed(world.rows.splice(length));
        } else {
          const at = index(key);
          if (at === null || at > target.length) world.valid = false;
          else if (at === target.length) world.rows.push(fresh());
          else { const row = world.rows[at]; row.version++; if (row.writer) row.writer.valid = false; }
        }
        return Reflect.set(target, key, value);
      },
      deleteProperty(target, key) {
        const at = index(key);
        if (at === null || !world.rows[at]) world.valid = false;
        else { const row = world.rows[at]; removed([row]); row.version++; }
        return Reflect.deleteProperty(target, key);
      },
      defineProperty(target, key, descriptor) { world.valid = false; return Reflect.defineProperty(target, key, descriptor); },
    });
    world.proxy = proxy; native.log = proxy;
    world.detach.push(() => { if (native.log === proxy) native.log = log; });
    const wrap = (object: any, key: string, make: (original: any) => any) => {
      const descriptor = Object.getOwnPropertyDescriptor(object, key), original = object[key];
      object[key] = make(original);
      world.detach.push(() => { if (descriptor) Object.defineProperty(object, key, descriptor); else delete object[key]; });
    };
    let actorFrame: { actor: object; supported: boolean; used: boolean } | undefined;
    const canonicalProducer = !Object.hasOwn(native.actions, 'switchIn')
      && native.actions.switchIn === BattleActions.prototype.switchIn;
    wrap(native.actions, 'switchIn', original => (...args: any[]) => {
      if (!world.actors.size) world.load();
      const previous = actorFrame;
      actorFrame = { actor: args[0], supported: canonicalProducer && native.gameType === 'singles' && native.activePerHalf === 1
        && native.sides.length === 2 && native.sides.every((side: any) => side?.active.length === 1)
        && args[1] === 0 && !args[2] && !args[3], used: false };
      try { return original.apply(native.actions, args); } finally { actorFrame = previous; }
    });
    wrap(native, 'add', original => (...args: any[]) => {
      if (!writing && actorFrame?.supported && !actorFrame.used && args.length === 3 && args[0] === 'switch'
        && args[1] === actorFrame.actor && args[2] === (actorFrame.actor as any).getFullDetails) {
        const actor = world.actors.get(actorFrame.actor);
        if (!actor) fail('unregistered-direct-switch-actor');
        actorFrame.used = true;
        const writer: Writer = { token: token(), actor: Object.freeze({ owner: actor.owner, slot: actor.slot, original: actor.original }), rows: [], valid: true };
        world.writers.push(writer); writing = writer;
        try { return original.apply(native, args); } finally { writing = undefined; }
      }
      return original.apply(native, args);
    });
    let updating = false;
    wrap(native, 'sendUpdates', original => (...args: any[]) => {
      const previous = updating; updating = true;
      try { return original.apply(native, args); } finally { updating = previous; }
    });
    const wrapSend = () => {
      wrap(native, 'send', original => (type: string, data: string | string[]) => {
        if (type !== 'update' || !updating) { if (type === 'update') world.valid = false; return original.call(native, type, data); }
        if (native.log !== proxy || !Array.isArray(data) || !isDeepStrictEqual(data, log.slice(native.sentLogPos))) world.valid = false;
        const bytes = Array.isArray(data) ? [...data] : data.split('\n');
        const rows = world.rows.slice(native.sentLogPos).map(row => ({ token: row.token, version: row.version }));
        const publicRows: number[] = [];
        for (let i = 0; i < bytes.length; i++) {
          if (/^\|split\|p[1234]$/.test(bytes[i])) { if (i + 2 >= bytes.length) world.valid = false; else if (bytes[i + 2]) publicRows.push(i + 2); i += 2; }
          else if (bytes[i]) publicRows.push(i);
        }
        const frame: Frame = { token: token(), bytes, rows, publicRows, received: false };
        world.frames.push(frame); world.sending = frame;
        try { return original.call(native, type, data); } finally { world.sending = undefined; }
      });
    };
    wrapSend();
    wrap(native, 'restart', original => (...args: any[]) => { const result = original.apply(native, args); wrapSend(); return result; });
  }
  bindSpectator(env: object, stream: object): void {
    this.#spectators.set(env, stream); const world = this.#worlds.get(env); if (world) world.spectator = stream;
  }
  pushed(env: object, stream: object, type: string, data: string): void {
    if (type !== 'update') return;
    if (!this.#worlds.has(env)) return;
    const world = this.world(env), frame = world.sending;
    if (world.stream !== stream || !frame || frame.received || data !== frame.bytes.join('\n')) { world.valid = false; return; }
    frame.received = true; world.fifo.push(frame);
  }
  received(env: object, stream: object, chunk: string): void {
    const world = this.world(env), frame = world.fifo.shift();
    if (world.spectator !== stream || !frame || chunk !== frame.publicRows.map(i => frame.bytes[i]).join('\n')) { world.valid = false; return; }
    world.public.push(...frame.publicRows.map(i => ({ ...frame.rows[i], byte: frame.bytes[i] })));
  }
  plainSerialization(env: object, battle: Battle, raw: Record<string, unknown>): void {
    const world = this.world(env);
    if (world.battle !== battle || (battle as any).log !== world.proxy || raw.log !== world.proxy) world.valid = false;
    raw.log = [...(raw.log as string[])];
    this.#raw.set(raw.log as object, { rows: copyRows(world.rows), expected: [...raw.log as string[]] });
  }
  recordSnapshot(env: object, raw: object, snapshot: SeededBattleSnapshot): void {
    const world = this.world(env), lineage = this.#raw.get((raw as any).log);
    if (!lineage || !isDeepStrictEqual(lineage.expected, snapshot.simulator_state.log)) fail('snapshot-lineage-mismatch');
    if (!world.valid) fail('unavailable-log-proof');
    this.#snapshots.set(snapshot, lineage);
  }
  finalizeSnapshot(env: object, source: SeededBattleSnapshot, target: SeededBattleSnapshot): void {
    this.world(env); const lineage = this.#snapshots.get(source);
    if (!lineage || !isDeepStrictEqual(source.simulator_state, target.simulator_state)) fail('builder-lineage-mismatch');
    this.#snapshots.set(target, lineage);
  }
  private validateWriters(world: World): void {
    const writers = new Set([...world.writers, ...world.rows.flatMap(row => row.writer ? [row.writer] : [])]);
    for (const writer of writers) {
      if (!writer.valid || writer.rows.length !== 3 || writer.rows.some(row => !row.alive)) fail('invalid-switch-writer');
      const [marker, secret, shared] = writer.rows, at = world.rows.indexOf(marker);
      if (at < 0 || world.rows[at + 1] !== secret || world.rows[at + 2] !== shared) fail('split-lineage-shape');
    }
  }
  prepare(env: object, boundary: PipelineBoundary, snapshot: SeededBattleSnapshot,
    projection: { prefix: string[]; positions: Array<number | null> }, parent: PipelineBoundary | null): object {
    const world = this.world(env), prior = this.#current, lineage = this.#snapshots.get(snapshot);
    if (!world.valid || world.battle.log !== world.proxy || world.fifo.length || world.frames.some(frame => !frame.received)) fail('incomplete-routed-proof');
    this.validateWriters(world);
    if (parent !== (prior?.parent ?? null) || (parent ? world.parent !== parent || world.source !== prior!.snapshot : !!world.source)) fail('foreign-event-parent');
    if (!lineage || !isDeepStrictEqual(lineage.expected, snapshot.simulator_state.log)) fail('foreign-event-snapshot');
    if (projection.positions.length !== world.public.length) fail('public-position-count');
    for (const owner of ['p1', 'p2'] as const) {
      const obs = boundary.perspectives[owner].observation;
      if (obs.event_cursor !== projection.prefix.length || !isDeepStrictEqual(obs.protocol_prefix, projection.prefix)) fail('future-or-mismatched-cutoff');
    }
    const publicByToken = new Map<object, { position: number; prefix: number | null; version: number }>();
    let cursor = 0;
    world.public.forEach((row, i) => {
      if (publicByToken.has(row.token)) fail('duplicate-public-occurrence');
      const at = projection.positions[i];
      if (at !== null && (at !== cursor++ || projection.prefix[at] !== row.byte.replace(/^\|t:\|[0-9]+$/, '|t:|0'))) fail('invalid-positional-projection');
      publicByToken.set(row.token, { position: i, prefix: at, version: row.version });
    });
    if (cursor !== projection.prefix.length) fail('projection-cutoff');
    const bindings = new Map(prior?.bindings), events = { p1: [...(prior?.histories.p1.events ?? [])], p2: [...(prior?.histories.p2.events ?? [])] };
    // Every prior source occurrence must reappear at its exact accepted positions/version.
    for (const [row, binding] of prior?.bindings ?? []) {
      const routed = publicByToken.get(row);
      if (!routed || routed.position !== binding.publicIndex || routed.prefix !== binding.prefixIndex || routed.version !== binding.version) fail('historical-event-continuity');
    }
    for (const writer of world.writers) {
      const [marker, secret, shared] = writer.rows;
      const routed = publicByToken.get(shared.token);
      if (!routed || publicByToken.has(secret.token) || publicByToken.has(marker.token)
        || routed.prefix === null || routed.prefix >= projection.prefix.length || routed.version !== shared.version) fail('missing-switch-public-binding');
      if (bindings.has(shared.token)) fail('reused-switch-writer');
      bindings.set(shared.token, { version: shared.version, publicIndex: routed.position, prefixIndex: routed.prefix });
      const owner = writer.actor.owner;
      events[owner].push(Object.freeze({ owner, original_slot: writer.actor.slot, event_index: events[owner].length,
        public_index: routed.position, prefix_index: routed.prefix, branch_id: boundary.branch_id, step_index: boundary.step_index }));
    }
    // Direct switch rows lacking a qualified writer do not gain partial authority.
    for (const row of world.public) if (row.byte.startsWith('|switch|') && !bindings.has(row.token)) fail('unbound-switch-source');
    const histories = Object.fromEntries((['p1', 'p2'] as const).map(owner => [owner, Object.freeze({ owner,
      events: Object.freeze(events[owner]), branch_id: boundary.branch_id, step_index: boundary.step_index })])) as Record<PlayerID, SwitchEventHistory>;
    const prepared = token(); this.#prepared.set(prepared, { environment: env, parent,
      state: { parent: boundary, snapshot, histories, handles: { p1: token(), p2: token() }, bindings } }); return prepared;
  }
  preflight(prepared: object): void {
    const entry = this.#prepared.get(prepared);
    if (this.#closed || !entry || entry.parent !== (this.#current?.parent ?? null)) fail('foreign-or-stale-event-preparation');
    const world = this.world(entry.environment);
    this.validateWriters(world);
    if (!world.valid || world.fifo.length || world.battle.log !== world.proxy
      || !isDeepStrictEqual(world.log, entry.state.snapshot.simulator_state.log)) fail('changed-prepared-world');
    this.#ready = entry;
  }
  /** Session-only synchronous assignment; all checks/allocation precede this call. */
  installReady(): void { this.#current = this.#ready!.state; this.#ready = null; this.#prepared.clear(); }
  holding(owner: PlayerID): SwitchEventHandle {
    if (this.#closed || !this.#current || !['p1', 'p2'].includes(owner)) fail('unavailable-event-history');
    return this.#current.handles[owner];
  }
  read(handle: SwitchEventHandle, owner: PlayerID): SwitchEventHistory {
    if (handle !== this.holding(owner)) fail('foreign-copied-or-stale-event-holding');
    return this.#current!.histories[owner];
  }
  /** Internal diagnostics only; tokens are tentative and have no commit/read capability. */
  inspect(env: object) {
    const world = this.world(env);
    return { valid: world.valid && world.battle.log === world.proxy, pending: world.fifo.length,
      leases: { ...world.leases }, rows: world.rows.map(r => ({ token: r.token, version: r.version, alive: r.alive })),
      writers: world.writers.map(w => ({ token: w.token, owner: w.actor.owner, slot: w.actor.slot,
        valid: w.valid && w.rows.every(r => r.alive), rows: w.rows.map(r => r.token) })),
      sends: world.frames.map(f => ({ token: f.token, bytes: [...f.bytes], rows: f.rows.map(r => ({ ...r })), publicRows: [...f.publicRows], pushed: f.received })) };
  }
  checkActor(env: object, lease: object, owner: PlayerID, actor: object): number {
    const world = this.world(env), row = world.actors.get(actor);
    if (!world.valid || !row || row.owner !== owner || row.lease !== lease) fail('foreign-or-revoked-actor-lease');
    return row!.slot;
  }
  release(env: object): void {
    if (this.#ready?.environment === env) this.#ready = null;
    for (const [key, entry] of this.#prepared) if (entry.environment === env) this.#prepared.delete(key);
    const world = this.#worlds.get(env);
    if (world) { world.active = false; for (const detach of world.detach.reverse()) detach(); world.actors.clear(); world.fifo = []; this.#worlds.delete(env); }
    this.#spectators.delete(env);
  }
  revoke(): void { this.#ready = null; this.#prepared.clear(); this.#current = null; for (const env of this.#worlds.keys()) this.release(env); this.#snapshots = new WeakMap(); this.#raw = new WeakMap(); this.#closed = true; }
}
