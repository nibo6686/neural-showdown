import { assertAuthoritativeEnvironment } from './env_manager';
import { declaredRequestValues, DECLARED_PROPERTIES, DECLARED_STATS } from './owned_request_values';
import { Battle, Side, Pokemon } from 'pokemon-showdown';
import { isDeepStrictEqual } from 'node:util';
import { NativeBirthEnrollment, NativeObjectAssociation, type AssociationRows, type NativeRestoreTicket } from './owner_identity_crosswalk';
import type { PipelineBoundary } from './pipeline_integration';
import type { SeededBattleSnapshot } from './transition';
import type { PlayerID } from './types';
import type { OriginalOwnerEvidence } from './original_owner_provider';
import type { RequestEmissionReceipt, RequestProducerEmission } from './request_emission_trace';
import type { RequestDeliveryLedger, RequestDeliveryBoundary } from './request_delivery_ledger';
import {OwnedRequestMoveState, type OwnedMovesData} from './owned_request_moves';
const owners = ['p1', 'p2'] as const;
const pinned = Object.getOwnPropertyDescriptor(Battle.prototype, 'getRequests')!;
const sideDataPin = Object.getOwnPropertyDescriptor(Side.prototype, 'getRequestData')!;
const sideEmitPin = Object.getOwnPropertyDescriptor(Side.prototype, 'emitRequest')!;
const rowPin = Object.getOwnPropertyDescriptor(Pokemon.prototype, 'getSwitchRequestData')!;
const movePins = Object.fromEntries(['getMoveRequestData','getMoves','getLockedMove','getSemiLockedMove'].map(key => [key, Object.getOwnPropertyDescriptor(Pokemon.prototype, key)!]));
let decoding = false;
function need(value: unknown, reason: string): asserts value { if (!value) throw new Error('request-health/v1/' + reason); }
const token = (): object => Object.freeze(Object.create(null));
type Identifiers = { itemPresent: boolean; item: unknown; abilityPresent: boolean; ability: unknown; nativeItem: unknown; nativeAbility: unknown };
type DeclaredRow = { statsPresent: boolean; statsReference: any; stats: any; detailsPresent: boolean; details: any; ballPresent: boolean; ball: any;
  nativeStatsReference: any; nativeStats: any; nativeDetails: string; nativeBall: string };
type Row = { declaration?: DeclaredRow; identifiers?: Identifiers; actor: any; data: any; condition: string; hp: number; maxhp: number; status: string; fainted: boolean };
type NativeMoveSlot = { reference: any; id: string; pp: number; maxpp: number; virtual: unknown };
type MoveSource = { actor: any; data?: any; array?: any[]; slots?: readonly NativeMoveSlot[]; moves?: any[];
  rows?: readonly { reference: any; id: string; label: string; pp: number; maxpp: number }[];
  locked?: unknown; semi?: unknown; semiArgument?: unknown; argument?: unknown; trace: string[]; calls: Record<string, number>; transformed: unknown; ordinary: boolean; emitted?: any; emittedArray?:any[]; emittedRows?:any[] };
type Capture = { owner: PlayerID; request: any; rows: readonly Row[]; move?: MoveSource; active?: any[] };
export interface OwnedActiveOptions { readonly schema: 'owned-active-options/v1'; readonly subject: string | null; readonly sequence: number | null;
  readonly cursor: number; readonly state: 'ordinary_pp' | 'exact_options' | 'unsupported' | 'waiting' | 'forced_switch' | 'revival_selection' | 'terminal' | 'requestless';
  readonly reason: 'none' | 'not_emitted' | 'unsupported_writer'; readonly options: readonly Record<string, any>[] | null }

type World = { battle: Battle; rows?: AssociationRows; undo: Array<() => void>; sides: Set<object>; decodeCalls: number; receipts: Set<object>; moveData: Set<object> };
type SnapshotRows = { rows: Partial<Record<PlayerID, readonly { slot: number; condition: string }[]>>; originals: Partial<Record<PlayerID, object>> };
type Prepared = { environment: object; boundary: PipelineBoundary; ledger: RequestDeliveryLedger;
  transfers: Record<PlayerID, object>; captures: Partial<Record<PlayerID, Capture>>; facts: Record<PlayerID, readonly any[]>; states: Record<PlayerID, string>; descriptors: Record<PlayerID, OwnedActiveOptions>; moves?:Record<PlayerID,OwnedMovesData> };
/** Exact native writer lineage and held B1/B2 associations. No JSON/source admission. */
export class OwnedRequestHealthHost {
  readonly #birth: NativeBirthEnrollment;
  #closed = false;
  #worlds = new Map<object, World>();
  #moveData = new WeakMap<object, MoveSource>();
  #moving: MoveSource | null = null;
  #requesting: World | null = null;
  #rowData = new WeakMap<object, Row>();
  #sideData = new WeakMap<object, readonly Row[]>();
  #requests = new WeakMap<object, Capture>();
  #emissions = new WeakMap<object, Capture>();
  #receipts = new WeakMap<object, Capture>();
  #latest = new Map<object, Partial<Record<PlayerID, Capture>>>();
  #snapshots = new WeakMap<object, SnapshotRows>();
  #restores = new Map<object, { parent: PipelineBoundary; snapshot: SeededBattleSnapshot; ticket: object; rows?: SnapshotRows }>();
  #sending: { environment: object; capture: Capture } | null = null;
  #prepared = new Map<object, Prepared>();
  #ready: Prepared | null = null;
  #parent: PipelineBoundary | null = null;
  readonly #moves: OwnedRequestMoveState | undefined;
  constructor(birth: NativeBirthEnrollment, association: NativeObjectAssociation, moves = false) {
    this.#moves = moves ? new OwnedRequestMoveState() : undefined;
    this.#birth = birth;
    const receiver = (issuer: NativeBirthEnrollment | NativeObjectAssociation) => ({
      observe: (environment: object, battle: Battle) => this.attach(environment, battle, true),
      enroll: (frame: object, environment: object, battle: Battle, rows: AssociationRows) => {
        this.open(); issuer.assertRequestHealthTransfer(frame, environment, battle, rows);
        const world = this.#worlds.get(environment); need(world?.battle === battle && !world.rows, 'foreign-or-duplicate-enrollment');
        need(owners.every(owner => rows[owner]?.original.owner === owner
          && rows[owner].objects.length === rows[owner].original.raw_team.length
          && rows[owner].objects.every(actor => actor?.side === battle[owner])), 'owner-association');
        world.rows = rows;
        this.#moves?.enroll(environment,rows);
      },
      restore: (environment: object, parent: PipelineBoundary, snapshot: SeededBattleSnapshot, ticket: NativeRestoreTicket) => {
        this.open(); need(parent === this.#parent && !this.#restores.has(environment), 'foreign-restore-parent');
        this.#restores.set(environment, { parent, snapshot, ticket, rows: this.#snapshots.get(snapshot) });
      },
    });
    birth.registerRequestHealthReceiver(receiver(birth)); association.registerRequestHealthReceiver(receiver(association));
  }
  private open(): void { need(!this.#closed, 'revoked'); }
  private replace(world: World, object: any, key: string, value: any): void {
    const descriptor = Object.getOwnPropertyDescriptor(object, key);
    Object.defineProperty(object, key, { configurable: true, writable: true, value });
    world.undo.push(() => { if (descriptor) Object.defineProperty(object, key, descriptor); else delete object[key]; });
  }
  private attach(environment: object, battle: Battle, initial: boolean): void {
    this.open(); need(!this.#worlds.has(environment) && !Object.hasOwn(battle, 'getRequests')
      && battle.getRequests === pinned.value && isDeepStrictEqual(Object.getOwnPropertyDescriptor(Battle.prototype, 'getRequests'), pinned), 'noncanonical-producer');
    const world: World = { battle, undo: [], sides: new Set(), decodeCalls: 0, receipts: new Set(), moveData: new Set() }; this.#worlds.set(environment, world);
    this.#moves?.attach(environment,battle,initial);
    this.replace(world, battle, 'getRequests', (...args: any[]) => {
      if (decoding) need(++world.decodeCalls === 1, 'multiple-regeneration');
      if (initial && !world.rows) this.#birth.transferRequestHealthActors(environment, battle);
      this.attachSides(environment, world);
      need(!this.#requesting, 'nested-request-producer'); this.#requesting = world;
      try { return pinned.value.apply(battle, args); } finally { this.#requesting = null; }
    });
  }
  private attachSides(environment: object, world: World): void {
    for (const owner of owners) {
      const side: any = world.battle[owner]; if (!side) continue;
      if (world.sides.has(side)) continue;
      need(!Object.hasOwn(side, 'getRequestData') && !Object.hasOwn(side, 'emitRequest')
        && side.getRequestData === sideDataPin.value && side.emitRequest === sideEmitPin.value
        && isDeepStrictEqual(Object.getOwnPropertyDescriptor(Side.prototype, 'getRequestData'), sideDataPin)
        && isDeepStrictEqual(Object.getOwnPropertyDescriptor(Side.prototype, 'emitRequest'), sideEmitPin), 'noncanonical-side');
      const getData = side.getRequestData, emit = side.emitRequest;
      for (const actor of side.pokemon) {
        need(!Object.hasOwn(actor, 'getSwitchRequestData') && actor.getSwitchRequestData === rowPin.value
          && isDeepStrictEqual(Object.getOwnPropertyDescriptor(Pokemon.prototype, 'getSwitchRequestData'), rowPin), 'noncanonical-pokemon');
        this.attachMoveWriter(world, actor);
        this.#moves?.wrapActor(environment,actor);
        const writer = actor.getSwitchRequestData;
        this.replace(world, actor, 'getSwitchRequestData', (...args: any[]) => {
          const data = writer.apply(actor, args);
          if (args[0] !== true) this.#rowData.set(data, { actor, data, condition: data.condition,
            hp: actor.hp, maxhp: actor.maxhp, status: actor.status, fainted: actor.fainted, declaration: {
              statsPresent: Object.hasOwn(data, 'stats'), statsReference: data.stats, stats: structuredClone(data.stats),
              detailsPresent: Object.hasOwn(data, 'details'), details: data.details, ballPresent: Object.hasOwn(data, 'pokeball'), ball: data.pokeball,
              nativeStatsReference: actor.baseStoredStats, nativeStats: Object.fromEntries(DECLARED_STATS.map(key => [key, actor.baseStoredStats[key]])),
              nativeDetails: actor.details, nativeBall: actor.pokeball }, identifiers: {
              itemPresent: Object.hasOwn(data, 'item'), item: data.item, abilityPresent: Object.hasOwn(data, 'ability'), ability: data.ability, nativeItem: actor.item, nativeAbility: actor.ability } });
          return data;
        });
      }
      this.replace(world, side, 'getRequestData', (...args: any[]) => {
        const data = getData.apply(side, args), rows = data.pokemon.map((entry: any) => this.#rowData.get(entry));
        if (args[0] !== true && rows.every(Boolean)) this.#sideData.set(data, Object.freeze(rows));
        return data;
      });
      this.replace(world, side, 'emitRequest', (request: any = side.activeRequest, updated = false) => {
        const rows = request && this.#sideData.get(request.side);
        const capture = rows && { owner, request, rows, active: request.active,
          move: Array.isArray(request.active) && request.active.length === 1 ? this.#moveData.get(request.active[0]) : undefined };
        if (capture) { this.checkCapture(capture, world, false); this.checkMove(capture, world); this.#requests.set(request, capture); }
        need(!this.#sending, 'nested-send'); this.#sending = capture ? { environment, capture } : null;
        try { return emit.call(side, request, updated); } finally { this.#sending = null; }
      });
      world.sides.add(side);
    }
  }
  private attachMoveWriter(world: World, actor: any): void {
    for (const [key, descriptor] of Object.entries(movePins)) need(!Object.hasOwn(actor, key)
      && actor[key] === descriptor.value && isDeepStrictEqual(Object.getOwnPropertyDescriptor(Pokemon.prototype, key), descriptor), 'noncanonical-active-writer');
    const host = this;
    for (const key of ['getLockedMove','getSemiLockedMove','getMoves']) {
      const original = movePins[key].value;
      this.replace(world, actor, key, function(this: any, ...args: any[]) {
        need(this === actor, 'foreign-active-this'); const cycle = host.#moving?.actor === actor ? host.#moving : null;
        if (cycle) {
          cycle.trace.push(key + ':start'); cycle.calls[key] = (cycle.calls[key] ?? 0) + 1;
          if (key === 'getSemiLockedMove') cycle.semiArgument = args[0];
          if (key === 'getMoves') {
            cycle.argument = args[0]; cycle.array = actor.moveSlots;
            cycle.slots = Object.freeze(actor.moveSlots.map((slot: any) => Object.freeze({ reference: slot, id: slot.id, pp: slot.pp, maxpp: slot.maxpp, virtual: slot.virtual })));
          }
        }
        const result = original.apply(actor, args);
        if (cycle) {
          cycle.trace.push(key + ':end');
          if (key === 'getLockedMove') cycle.locked = result;
          if (key === 'getSemiLockedMove') cycle.semi = result;
          if (key === 'getMoves') {
            cycle.moves = result;
            cycle.rows = Object.freeze(result.map((row: any) => Object.freeze({ reference: row, id: row.id, label: row.move, pp: row.pp, maxpp: row.maxpp })));
          }
        }
        return result;
      });
    }
    this.replace(world, actor, 'getMoveRequestData', function(this: any, ...args: any[]) {
      need(this === actor, 'foreign-active-this');
      if (host.#requesting !== world) return movePins.getMoveRequestData.value.apply(actor, args);
      need(!host.#moving, 'nested-active-writer');
      const source: MoveSource = { actor, calls: {}, trace: [], transformed: actor.transformed, ordinary: false }; host.#moving = source;
      try {
        const data = movePins.getMoveRequestData.value.apply(actor, args); source.data = data;
        if (host.#moves) {source.emitted = structuredClone(data);source.emittedArray=data.moves;source.emittedRows=[...data.moves];}
        source.ordinary = source.trace.join(',') === 'getLockedMove:start,getLockedMove:end,getSemiLockedMove:start,getSemiLockedMove:end,getMoves:start,getMoves:end'
          && source.calls.getLockedMove === 1 && source.calls.getSemiLockedMove === 1 && source.calls.getMoves === 1
          && source.locked === null && source.semi === null && source.semiArgument === true && source.argument === null && !source.transformed && !!source.slots
          && source.slots.length >= 1 && source.slots.length <= 4 && source.slots.every(slot => !slot.virtual)
          && data.moves === source.moves && source.rows!.length === source.slots.length
          && source.rows!.every(row => Object.hasOwn(row.reference, 'pp') && Object.hasOwn(row.reference, 'maxpp'));
        host.#moveData.set(data, source); world.moveData.add(data); return data;
      } finally { host.#moving = null; }
    });
  }
  private checkMove(capture: Capture, world: World): void {
    const source = capture.move; if (!source) return;
    need(capture.request.active === capture.active && capture.active?.length === 1 && capture.active[0] === source.data
      && source.actor.side === world.battle[capture.owner] && world.battle[capture.owner]!.active[0] === source.actor
      && (!world.rows || world.rows[capture.owner].objects.includes(source.actor)), 'foreign-active-binding');
    if (this.#moves) {
      need(source.data.moves===source.emittedArray&&source.data.moves.length===source.emittedRows?.length&&source.emittedRows!.every((row,i)=>source.data.moves[i]===row),'copied-active-emission');
      need(isDeepStrictEqual(source.data, source.emitted), 'altered-active-emission');
    }
    if (!source.ordinary) return;
    need(source.actor.transformed === source.transformed && source.actor.moveSlots === source.array
      && source.array!.length === source.slots!.length && source.slots!.every((slot, i) => source.array![i] === slot.reference
        && slot.reference.id === slot.id && slot.reference.pp === slot.pp && slot.reference.maxpp === slot.maxpp
        && slot.reference.virtual === slot.virtual), 'stale-active-slot');
    need(source.data.moves === source.moves && source.moves!.length === source.rows!.length
      && source.rows!.every((row, i) => source.moves![i] === row.reference && row.reference.id === row.id && row.reference.move === row.label
        && Object.hasOwn(row.reference, 'pp') && Object.hasOwn(row.reference, 'maxpp') && row.reference.pp === row.pp && row.reference.maxpp === row.maxpp
        && row.id === source.slots![i].id && row.pp === source.slots![i].pp && row.maxpp === source.slots![i].maxpp
        && typeof row.id === 'string' && row.id.length > 0 && typeof row.label === 'string' && row.label.length > 0
        && Number.isSafeInteger(row.pp) && Number.isSafeInteger(row.maxpp) && row.pp >= 0 && row.pp <= row.maxpp && row.maxpp <= 2147483647), 'altered-active-row');
  }
  private descriptor(capture: Capture | undefined, world: World, owner: PlayerID, state: string, delivery: RequestDeliveryBoundary): OwnedActiveOptions {
    const source = state === 'move' ? capture?.move : undefined;
    if (capture) this.checkMove(capture, world);
    const slot = source ? world.rows![owner].objects.indexOf(source.actor) + 1 : 0;
    const ordinary = !!source?.ordinary && state === 'move';
    const exact = !!this.#moves && !!source?.emitted && state === 'move' && source.calls.getMoves === 1
      && Array.isArray(source.emitted.moves) && source.emitted.moves.length >= 1 && source.emitted.moves.length <= 4
      && source.emitted.moves.every((m:any) => typeof m.id === 'string' && m.id.length && typeof m.move === 'string' && m.move.length
        && (!Object.hasOwn(m,'disabled') || typeof m.disabled === 'boolean'));
    const unavailable = ['waiting','forced_switch','revival_selection','terminal','requestless'].includes(state);
    return Object.freeze({ schema: 'owned-active-options/v1', subject: slot ? owner + ':roster:' + slot : null,
      sequence: delivery.current?.sequence ?? null, cursor: delivery.boundary_cursor,
      state: ordinary ? 'ordinary_pp' : exact ? 'exact_options' : unavailable ? state as OwnedActiveOptions['state'] : 'unsupported',
      reason: ordinary || exact ? 'none' : unavailable ? 'not_emitted' : 'unsupported_writer',
      options: ordinary ? Object.freeze(source!.rows!.map((row, i) => Object.freeze({ option_index: i + 1, request_move_id: row.id, request_move_label: row.label,
        pp: Object.freeze({ state: 'known', value: row.pp, precision: 'exact', reason: 'none' }),
        max_pp: Object.freeze({ state: 'known', value: row.maxpp, precision: 'exact', reason: 'none' }) }))) : exact ? Object.freeze(source!.emitted.moves.map((row:any,i:number)=>Object.freeze({option_index:i+1,request_move_id:row.id,request_move_label:row.move,
          pp:Object.freeze({state:'unknown',value:null,precision:'not_applicable',reason:Object.hasOwn(row,'pp')?'unsupported_writer':'not_emitted'}),
          max_pp:Object.freeze({state:'unknown',value:null,precision:'not_applicable',reason:Object.hasOwn(row,'maxpp')?'unsupported_writer':'not_emitted'})}))) : null });
  }
  /** Only the final admitted synchronous native decode. Probe callers never use this seam. */
  decode(environment: object, ticket: object, operation: () => Battle, input?:Record<string,unknown>): Battle {
    assertAuthoritativeEnvironment(environment);
    this.open(); const restore = this.#restores.get(environment);
    need(restore?.ticket === ticket && !decoding, 'foreign-or-nested-decode');
    const descriptor = Object.getOwnPropertyDescriptor(Battle.prototype, 'getRequests');
    need(isDeepStrictEqual(descriptor, pinned), 'prototype-descriptor');
    decoding = true; let captured: Battle | undefined, count = 0, returned: Battle | undefined;
    Object.defineProperty(Battle.prototype, 'getRequests', { ...pinned, value: function(this: Battle, ...args: any[]) {
      need(++count === 1 && !Object.hasOwn(this, 'getRequests'), 'multiple-or-noncanonical-decode');
      captured = this;
      // Restore canonical prototype during instance installation, then retain interception until decode returns.
      Object.defineProperty(Battle.prototype, 'getRequests', pinned);
      host.attach(environment, this, false); host.attachSides(environment, host.#worlds.get(environment)!);
      Object.defineProperty(Battle.prototype, 'getRequests', intercept);
      return (this.getRequests as any)(...args);
    } });
    const host = this, intercept = Object.getOwnPropertyDescriptor(Battle.prototype, 'getRequests')!;
    try {
      returned = this.#moves ? this.#moves.decode(environment,restore.snapshot,input,operation) : operation(); need(!captured || captured === returned, 'foreign-decoded-battle');
      need(returned,'missing-decoded-battle');
      const expected = (restore.snapshot.simulator_state as any).sides.some((side: any) => side.activeRequest === undefined);
      need(count === (expected ? 1 : 0), 'missing-regeneration');
      if (!captured) { Object.defineProperty(Battle.prototype, 'getRequests', pinned); this.attach(environment, returned, false); }
      return returned;
    } catch (error) { this.release(environment); throw error; }
    finally { Object.defineProperty(Battle.prototype, 'getRequests', pinned); decoding = false; }
  }
  sent(environment: object, emission: RequestProducerEmission | undefined): void {
    if (!emission || !this.#sending) return;
    const context = this.#sending;
    need(context.environment === environment && context.capture.owner === emission.owner
      && JSON.stringify(context.capture.request) === emission.request_json, 'send-join');
    this.#emissions.set(emission, context.capture);
  }
  received(environment: object, emission: RequestProducerEmission, receipt: RequestEmissionReceipt): void {
    const capture = this.#emissions.get(emission); if (!capture) return;
    need(capture.owner === receipt.owner && this.#worlds.has(environment), 'receipt-join');
    this.#receipts.set(receipt, capture); this.#worlds.get(environment)!.receipts.add(receipt);
    const latest = this.#latest.get(environment) ?? {}; latest[capture.owner] = capture; this.#latest.set(environment, latest);
  }
  private checkDeclared(row: Row, settled: boolean): void {
    const source = row.declaration; if (!source) return; // No adopted declaration lineage for overlay clones.
    need(Object.hasOwn(row.data,'stats') === source.statsPresent && Object.hasOwn(row.data,'details') === source.detailsPresent
      && Object.hasOwn(row.data,'pokeball') === source.ballPresent, 'altered-declared-presence');
    if (source.statsPresent) {
      need(row.data.stats === source.statsReference && isDeepStrictEqual(row.data.stats,source.stats), 'altered-declared-stats');
      need(isDeepStrictEqual(source.stats,source.nativeStats),'contradictory-declared-stats');
      if (settled) need(row.actor.baseStoredStats === source.nativeStatsReference
        && DECLARED_STATS.every(key => row.actor.baseStoredStats[key] === source.nativeStats[key]),'stale-declared-stats');
    }
    if (source.detailsPresent) {
      need(row.data.details === source.details && source.details === source.nativeDetails,'altered-declared-details');
      if (settled) need(row.actor.details === source.nativeDetails,'stale-declared-details');
    }
    if (source.ballPresent) {
      need(row.data.pokeball === source.ball && source.ball === source.nativeBall,'altered-declared-ball');
      if (settled) need(row.actor.pokeball === source.nativeBall,'stale-declared-ball');
    }
    declaredRequestValues(row.data);
  }
  private checkCapture(capture: Capture, world: World, settled: boolean): void {
    const data = capture.request.side;
    need(data?.id === capture.owner && data.pokemon.length === capture.rows.length
      && capture.rows.every((row, i) => data.pokemon[i] === row.data && row.data.condition === row.condition
        && row.actor.side === world.battle[capture.owner]), 'altered-writer-row');
    if (world.rows) need(capture.rows.length === world.rows[capture.owner].objects.length
      && new Set(capture.rows.map(row => row.actor)).size === capture.rows.length
      && capture.rows.every(row => world.rows![capture.owner].objects.includes(row.actor)), 'unbound-or-duplicate-subject');
    for (const row of capture.rows) {
      this.checkDeclared(row, settled);
      const ids = row.identifiers; if (!ids) continue; // Overlay clones have no admitted identifier writer lineage.
      for (const property of ['item','ability'] as const) {
        const present = property === 'item' ? ids.itemPresent : ids.abilityPresent;
        const value = ids[property], native = property === 'item' ? ids.nativeItem : ids.nativeAbility;
        need(Object.hasOwn(row.data, property) === present && row.data[property] === value, 'altered-identifier-row');
        if (present) {
          need(typeof value === 'string' && (value === '' || /^[a-z0-9]+$/.test(value)), 'identifier-grammar');
          const catalog = property === 'item' ? world.battle.dex.items : world.battle.dex.abilities;
          need(value === '' || catalog.get(value as string).exists === true && catalog.get(value as string).id === value, 'unknown-identifier');
          need(value === native, 'contradictory-identifier');
        }
        if (settled) need(row.actor[property] === native, 'stale-identifier');
      }
    }
    if (settled) need(capture.rows.every(row => row.actor.hp === row.hp && row.actor.maxhp === row.maxhp
      && row.actor.status === row.status && row.actor.fainted === row.fainted), 'stale-settled-value');
  }
  serialize(environment:object,battle:Battle,operation:()=>Record<string,unknown>):Record<string,unknown> {
    return this.#moves ? this.#moves.serialize(environment,battle,operation) : operation();
  }
  recordSnapshot(environment: object, snapshot: SeededBattleSnapshot, raw?:Record<string,unknown>): void {
    this.#moves?.recordSnapshot(environment,raw,snapshot);
    const world = this.#worlds.get(environment); if (!world?.rows) return;
    const saved: SnapshotRows = { rows: {}, originals: {} };
    for (const owner of owners) {
      const capture = this.#latest.get(environment)?.[owner];
      if (!capture || capture.request !== world.battle[owner]?.activeRequest) continue;
      this.checkCapture(capture, world, true);
      const actors = world.rows[owner].objects;
      saved.rows[owner] = Object.freeze(capture.rows.map(row => {
        const slot = actors.indexOf(row.actor) + 1; need(slot, 'unbound-serialization-row'); return Object.freeze({ slot, condition: row.condition });
      })); saved.originals[owner] = world.rows[owner].original;
    }
    this.#snapshots.set(snapshot, saved);
  }
  finalizeSnapshot(source: SeededBattleSnapshot, target: SeededBattleSnapshot): void {
    this.#moves?.finalizeSnapshot(source,target);
    const held = this.#snapshots.get(source); if (held) this.#snapshots.set(target, held);
  }
  cloneOverlay(environment: object, battle: Battle, owner: PlayerID, override: any): any {
    const pending = this.#restores.get(environment), world = this.#worlds.get(environment);
    need(pending && world?.battle === battle && world.rows, 'overlay-world');
    need((pending.snapshot.simulator_state as any).__neural_active_request_overrides?.requests?.[owner] === override, 'foreign-overlay-occurrence');
    const result = structuredClone(override), held = pending.rows?.rows[owner];
    if (!held || pending.rows!.originals[owner] !== world.rows[owner].original) return result;
    need(result.side?.pokemon.length === held.length, 'overlay-row-count');
    const rows = held.map((entry, i) => {
      const actor = world.rows![owner].objects[entry.slot - 1], data = result.side.pokemon[i];
      need(actor && data.condition === entry.condition, 'overlay-lineage');
      return { actor, data, condition: data.condition, hp: actor.hp, maxhp: actor.maxhp, status: actor.status, fainted: actor.fainted };
    });
    this.#sideData.set(result.side, Object.freeze(rows)); return result;
  }
  prepare(environment: object, boundary: PipelineBoundary, ledger: RequestDeliveryLedger, delivery: object): object {
    assertAuthoritativeEnvironment(environment);
    this.open(); const world = this.#worlds.get(environment); need(world?.rows, 'missing-enrollment');
    const facts = {} as Record<PlayerID, readonly any[]>, states = {} as Record<PlayerID, string>, captures: Prepared['captures'] = {};
    const transfers = {} as Record<PlayerID, object>, descriptors = {} as Record<PlayerID, OwnedActiveOptions>, deliveries={} as Record<PlayerID,RequestDeliveryBoundary>;
    for (const owner of owners) {
      const transfer = transfers[owner] = ledger.prepareHealthTransfer(delivery, owner);
      const row = ledger.readHealthTransfer(transfer, owner, environment, boundary);
      deliveries[owner]=row;
      const capture = row.selected && this.#receipts.get(row.selected);
      const observation = boundary.perspectives[owner].observation;
      states[owner] = observation.view.terminated ? 'terminal' : !row.current ? 'requestless' : capture?.request.wait ? 'waiting'
        : capture?.request.forceSwitch ? capture.request.side.pokemon.some((entry: any) => entry.reviving) ? 'revival_selection' : 'forced_switch'
        : capture?.request.active ? 'move' : 'unsupported';
      const usable = !!capture && row.current !== null && !observation.view.terminated && states[owner] !== 'unsupported';
      if (usable) { this.checkCapture(capture!, world, true); captures[owner] = capture!; }
      const out: any[] = [];
      for (const [i, actor] of world.rows[owner].objects.entries()) {
        const writer = usable ? capture!.rows.filter(row => row.actor === actor) : [];
        need(writer.length <= 1, 'duplicate-subject');
        const condition = writer[0]?.condition;
        const positive = condition?.match(/^([1-9][0-9]*)\/([1-9][0-9]*)(?: (brn|par|slp|frz|psn|tox))?$/);
        if (condition !== undefined) need(condition === '0 fnt' || positive && positive[0] === condition, 'condition-grammar');
        if (positive) need(Number.isSafeInteger(+positive[1]) && +positive[1] <= +positive[2] && +positive[2] <= 2147483647
          && +positive[1] === actor.hp && +positive[2] === actor.maxhp && (positive[3] ?? '') === actor.status && !actor.fainted, 'condition-value');
        if (condition === '0 fnt') need(actor.hp === 0 && actor.fainted === true, 'faint-value');
        const absent = !usable || condition === undefined;
        for (const property of ['hp', 'fainted', 'status']) {
          const unknown = absent || property === 'status' && condition === '0 fnt';
          const value = property === 'hp' ? condition === '0 fnt' ? 0 : positive ? +positive[1] : null
            : property === 'fainted' ? condition === '0 fnt' : positive?.[3] ?? null;
          out.push(Object.freeze({ owner, subject: owner + ':roster:' + (i + 1), family: 'K05', property, effect_key: null,
            state: unknown ? 'unknown' : value === null ? 'known_absent' : 'known',
            value: unknown || value === null ? null : Object.freeze({ type: property === 'hp' ? 'integer' : property === 'fainted' ? 'boolean' : 'text', data: value }),
            reason: unknown ? states[owner] === 'terminal' || states[owner] === 'requestless' || property === 'status' && condition === '0 fnt' ? 'not_emitted' : 'unsupported_writer' : 'none',
            freshness: 'current', precision: unknown || value === null ? 'not_applicable' : 'exact', observed_at: unknown ? null : row.boundary_cursor }));
        }
      }
      for (const [i, actor] of world.rows[owner].objects.entries()) {
        const writer = usable ? capture!.rows.find(row => row.actor === actor) : undefined;
        for (const property of ['item','ability'] as const) {
          const ids = writer?.identifiers;
          const present = ids && (property === 'item' ? ids.itemPresent : ids.abilityPresent);
          const value = present ? ids![property] : undefined;
          const unknown = !present || property === 'ability' && value === '';
          out.push(Object.freeze({ owner, subject: owner + ':roster:' + (i + 1), family: property === 'item' ? 'K18' : 'K19', property, effect_key: null,
            state: unknown ? 'unknown' : value === '' ? 'known_absent' : 'known',
            value: unknown || value === '' ? null : Object.freeze({ type: 'text', data: value }),
            reason: unknown ? states[owner] === 'terminal' || states[owner] === 'requestless' || usable && !present ? 'not_emitted' : 'unsupported_writer' : 'none',
            freshness: 'current', precision: unknown || value === '' ? 'not_applicable' : 'exact', observed_at: unknown ? null : row.boundary_cursor }));
        }
      }
      for (const [i, actor] of world.rows[owner].objects.entries()) {
        const writer = usable ? capture!.rows.find(row => row.actor === actor) : undefined;
        const values = writer?.declaration ? declaredRequestValues(writer.data) : DECLARED_PROPERTIES.map(property => ({ property,
          tag: '', state: 'unknown', value: null, reason: ['terminal','requestless'].includes(states[owner]) ? 'not_emitted' : 'unsupported_writer' }));
        for (const value of values) out.push(Object.freeze({ owner, subject: owner + ':roster:' + (i + 1),
          family: ['calculated_stats','hp_max'].includes(value.property) ? 'K03' : 'K04', property: value.property, effect_key: null,
          state: value.state, value: value.value === null ? null : Object.freeze({ type: value.tag, data: typeof value.value === 'object' ? Object.freeze(value.value) : value.value }),
          reason: value.reason, freshness: 'current', precision: value.state === 'known' ? 'exact' : 'not_applicable',
          observed_at: value.state === 'unknown' ? null : row.boundary_cursor }));
      }
      facts[owner] = Object.freeze(out);
      descriptors[owner] = this.descriptor(usable ? capture! : undefined, world, owner, states[owner], row);
    }
    const key = token(), moves=this.#moves?.prepare(key,environment,boundary,captures,deliveries);
    this.#prepared.set(key, { environment, boundary, ledger, transfers, captures, facts, states, descriptors, ...(moves?{moves}:{}) }); return key;
  }
  assertPreparedBinding(key: object, environment: object, boundary: PipelineBoundary, originals: readonly OriginalOwnerEvidence[]): void {
    this.open(); const entry = this.#prepared.get(key), world = this.#worlds.get(environment);
    need(entry?.environment === environment && entry.boundary === boundary && world?.rows
      && owners.every((owner, i) => world.rows![owner].original === originals[i]), 'foreign-knowledge-binding');
  }
  readPrepared(key: object, owner: PlayerID): { facts: readonly any[]; state: string; descriptor: OwnedActiveOptions; moves?:OwnedMovesData } {
    this.open(); const entry = this.#prepared.get(key); need(entry && owners.includes(owner), 'foreign-preparation');
    return { facts: entry.facts[owner], state: entry.states[owner], descriptor: entry.descriptors[owner], ...(entry.moves?{moves:entry.moves[owner]}:{}) };
  }
  preflight(key: object): void {
    this.open(); const entry = this.#prepared.get(key); need(entry, 'foreign-preparation');
    const world = this.#worlds.get(entry.environment); need(world?.rows, 'revoked-world');
    for (const owner of owners) {
      entry.ledger.readHealthTransfer(entry.transfers[owner], owner, entry.environment, entry.boundary);
      if (entry.captures[owner]) { this.checkCapture(entry.captures[owner]!, world, true); this.checkMove(entry.captures[owner]!, world); }
    }
    this.#moves?.preflight(key); this.#ready = entry;
  }
  installReady(): void { this.#moves?.installReady(); this.#parent = this.#ready!.boundary; this.#ready = null; this.#prepared.clear(); }
  release(environment: object): void {
    const world = this.#worlds.get(environment); world?.moveData.forEach(data => this.#moveData.delete(data)); world?.receipts.forEach(receipt => this.#receipts.delete(receipt)); world?.undo.reverse().forEach(undo => undo());
    this.#moves?.release(environment);
    this.#worlds.delete(environment); this.#latest.delete(environment); this.#restores.delete(environment);
    for (const [key, value] of this.#prepared) if (value.environment === environment) this.#prepared.delete(key);
    if (this.#ready?.environment === environment) this.#ready = null;
  }
  revoke(): void { for (const environment of this.#worlds.keys()) this.release(environment); this.#closed = true;
    this.#moves?.revoke();
    this.#prepared.clear(); this.#ready = null; this.#receipts = new WeakMap(); this.#emissions = new WeakMap(); this.#snapshots = new WeakMap(); this.#moveData = new WeakMap(); }
}
