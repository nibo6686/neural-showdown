import { isDeepStrictEqual } from 'node:util';
import type { SeededBattleSnapshot } from './transition';
import type { PipelineBoundary } from './pipeline_integration';
import type { Battle } from 'pokemon-showdown';
import { OriginalOwnerCreation, type OriginalOwnerEvidence } from './original_owner_provider';
import type { PlayerID } from './types';

export type NativeBirthHandle = Readonly<object>;
export interface NativeBirthEvidence {
  readonly owner: PlayerID;
  readonly original: OriginalOwnerEvidence;
  readonly slot_count: number;
}
const owners = ['p1', 'p2'] as const;
function index(owner: PlayerID): number {
  if (owner !== 'p1' && owner !== 'p2') throw new Error('native-birth/v1/invalid-owner');
  return owner === 'p1' ? 0 : 1;
}
function fail(reason: string): never { throw new Error('native-birth/v1/' + reason); }

/** Trusted session controller; native references never leave this private creation enrollment. */
export class NativeBirthEnrollment {
  #phase: 'new' | 'observing' | 'staged' | 'active' | 'invalid' = 'new';
  #environment: object | null = null;
  #battle: Battle | null = null;
  #birthEnvironment: object | null = null;
  #birthBattle: Battle | null = null;
  #submission: { owner: PlayerID; options: object; occurrence: object; enrolled: boolean } | null = null;
  #rows: Array<{ evidence: NativeBirthEvidence; sets: readonly object[]; occurrence: object } | undefined> = [];
  #handles: NativeBirthHandle[] = [];
  #detach: (() => void) | null = null;
  readonly #originals: OriginalOwnerCreation;
  constructor(originals: OriginalOwnerCreation) { this.#originals = originals; }

  bind(environment: object): void {
    if (this.#phase !== 'new' || this.#environment) this.reject('duplicate-environment');
    this.#environment = environment; this.#birthEnvironment = environment;
  }
  private reject(reason: string): never { this.revoke(); return fail(reason); }

  observe(environment: object, battle: Battle): void {
    if (this.#phase !== 'new' || this.#environment !== environment || this.#battle) this.reject('foreign-or-duplicate-creation');
    if (battle.started || battle.sides.some(side => !!side)) this.reject('late-observer');
    // Possession of this exact creation controller and its bound env is required;
    // packed bytes corroborate submission, never instantiate an original holder.
    for (const owner of owners) this.#originals.diagnostic(environment, owner);
    this.#battle = battle; this.#birthBattle = battle; this.#phase = 'observing';
    const native = battle as any;
    const setPlayer = native.setPlayer, getTeam = native.getTeam;
    const playerDescriptor = Object.getOwnPropertyDescriptor(native, 'setPlayer');
    const teamDescriptor = Object.getOwnPropertyDescriptor(native, 'getTeam');
    this.#detach = () => {
      if (playerDescriptor) Object.defineProperty(native, 'setPlayer', playerDescriptor); else delete native.setPlayer;
      if (teamDescriptor) Object.defineProperty(native, 'getTeam', teamDescriptor); else delete native.getTeam;
    };
    native.setPlayer = (owner: PlayerID, options: { team?: unknown }) => {
      const slot = index(owner);
      if (this.#phase !== 'observing' || this.#submission || this.#rows[slot] || battle.sides[slot]) this.reject('duplicate-or-late-submission');
      const original = this.#originals.diagnostic(environment, owner);
      if (typeof options.team !== 'string' || options.team !== original.packed_team) this.reject('submission-mismatch');
      const occurrence = Object.freeze(Object.create(null));
      const submission = this.#submission = { owner, options, occurrence, enrolled: false };
      try {
        const value = setPlayer.call(battle, owner, options);
        if (!submission.enrolled) this.reject('missing-enrollment');
        if (this.#rows[0] && this.#rows[1]) this.detach();
        return value;
      } catch (error) { this.revoke(); throw error; }
      finally { this.#submission = null; }
    };
    native.getTeam = (options: object) => {
      const submission = this.#submission;
      if (!submission || options !== submission.options || this.#phase !== 'observing') this.reject('unscoped-or-late-unpack');
      const sets = getTeam.call(battle, options);
      this.enroll(environment, battle, submission.occurrence, submission.owner, options, sets);
      return sets;
    };
  }

  /** Invoked only by the actual observed getTeam return, before Side construction. */
  enroll(environment: object, battle: Battle, occurrence: object, owner: PlayerID, options: object, sets: readonly object[]): void {
    const slot = index(owner), submission = this.#submission;
    if (this.#phase !== 'observing' || this.#environment !== environment || this.#battle !== battle
      || !submission || submission.occurrence !== occurrence || submission.owner !== owner || submission.options !== options) {
      this.reject('foreign-or-late-enrollment');
    }
    if (submission.enrolled || this.#rows[slot]) this.reject('duplicate-enrollment');
    if (battle.started || battle.sides[slot]) this.reject('post-construction-enrollment');
    const original = this.#originals.diagnostic(environment, owner);
    if ((options as { team?: unknown }).team !== original.packed_team) this.reject('submission-mismatch');
    if (!Array.isArray(sets) || sets.length !== original.raw_team.length || !sets.length
      || sets.some(set => !set || typeof set !== 'object' || Array.isArray(set)) || new Set(sets).size !== sets.length
      || this.#rows.some(row => row?.sets.some(set => sets.includes(set)))) this.reject('invalid-set-occurrence');
    this.#rows[slot] = { evidence: Object.freeze({ owner, original, slot_count: sets.length }), sets: Object.freeze([...sets]), occurrence };
    submission.enrolled = true;
    if (this.#rows[0] && this.#rows[1]) this.#phase = 'staged';
  }

  activate(): void {
    if (this.#phase !== 'staged' || !this.#battle || this.#submission) this.reject('not-staged');
    for (const owner of owners) {
      const row = this.#rows[index(owner)]!, side = this.#battle[owner];
      const held = this.#originals.read(this.#originals.holding(owner), owner);
      if (held !== row.evidence.original || !side || side.team.length !== row.sets.length
        || !side.team.every((set, i) => set === row.sets[i]) || side.pokemon.length !== row.sets.length
        || side.pokemon.some(pokemon => !row.sets.includes(pokemon.set))
        || new Set(side.pokemon.map(pokemon => pokemon.set)).size !== row.sets.length) this.reject('constructor-association-mismatch');
    }
    this.#handles = owners.map(() => Object.freeze(Object.create(null)));
    this.#phase = 'active'; this.#environment = null; this.#battle = null;
  }
  /** Trusted B2 producer transfer, not a consumer lookup or serialized certificate. */
  captureBirthObjects(environment: object, battle: Battle): AssociationRows {
    if (!['staged', 'active'].includes(this.#phase) || environment !== this.#birthEnvironment || battle !== this.#birthBattle) fail('foreign-birth-object-source');
    return Object.fromEntries(owners.map(owner => {
      const row = this.#rows[index(owner)]!, side = battle[owner];
      if (!side || side.team.length !== row.sets.length || !side.team.every((set, i) => set === row.sets[i])) fail('constructor-association-mismatch');
      const objects = row.sets.map(set => side.pokemon.find(p => p.set === set));
      if (objects.some(p => !p) || new Set(objects).size !== objects.length || side.pokemon.length !== objects.length) fail('constructor-association-mismatch');
      return [owner, { original: row.evidence.original, objects: Object.freeze(objects) }];
    })) as AssociationRows;
  }

  holding(owner: PlayerID): NativeBirthHandle {
    const slot = index(owner);
    if (this.#phase !== 'active') fail('unavailable');
    return this.#handles[slot];
  }
  read(handle: NativeBirthHandle, owner: PlayerID): NativeBirthEvidence {
    const slot = index(owner);
    if (this.#phase !== 'active' || handle !== this.#handles[slot]) fail('foreign-or-forged-holding');
    return this.#rows[slot]!.evidence;
  }
  abandonForRestore(environment: object): void {
    if (this.#phase !== 'new' || this.#environment !== environment) this.reject('restore-cannot-mint-birth');
    this.revoke();
  }
  abortStaging(): void { if (this.#phase !== 'active') this.revoke(); }
  private detach(): void { this.#detach?.(); this.#detach = null; }
  revoke(): void {
    this.detach(); this.#phase = 'invalid'; this.#environment = null; this.#battle = null;
    this.#submission = null; this.#rows = []; this.#handles = [];
    this.#birthEnvironment = null; this.#birthBattle = null;
  }
}

type AssociationRows = Record<PlayerID, { original: OriginalOwnerEvidence; objects: readonly any[] }>;
type Order = Record<PlayerID, readonly number[]>;
type StateRefs = { root: any; sides: any; rows: Array<{ side: any; pokemon: any; entries: any[]; sets: any[] }> };
type Serialization = { snapshot: SeededBattleSnapshot; expected: SeededBattleSnapshot; refs: StateRefs;
  environment: object; battle: Battle; rows: AssociationRows; order: Order };
type PendingAssociation = { ticket: object; parent: PipelineBoundary; source: Serialization;
  input?: StateRefs; battle?: Battle; rows?: AssociationRows };
export type NativeObjectHandle = Readonly<object>;
export type NativeRestoreTicket = Readonly<object>;
export interface NativeObjectEvidence {
  readonly owner: PlayerID;
  readonly original: OriginalOwnerEvidence;
  readonly original_slots: readonly number[];
  readonly observation_id: string;
  readonly branch_id: string;
  readonly step_index: number;
}
function associationFail(reason: string): never { throw new Error('native-association/v1/' + reason); }
function stateRefs(state: any): StateRefs {
  if (!state || !Array.isArray(state.sides) || state.sides.length !== 2) associationFail('invalid-native-state');
  return { root: state, sides: state.sides, rows: state.sides.map((side: any) => {
    if (!side || !Array.isArray(side.pokemon)) associationFail('invalid-native-state');
    return { side, pokemon: side.pokemon, entries: [...side.pokemon], sets: side.pokemon.map((p: any) => p.set) };
  }) };
}
function refsUnchanged(refs: StateRefs, state: any): boolean {
  return refs.root === state && refs.sides === state.sides && refs.rows.every((row, i) => row.side === state.sides[i]
    && row.pokemon === row.side.pokemon && row.entries.length === row.pokemon.length
    && row.entries.every((entry, j) => entry === row.pokemon[j] && entry.set === row.sets[j]));
}

/** Private session association: actual serializer/reconstructor occurrences, never imported mappings. */
export class NativeObjectAssociation {
  #initialEnvironment: object | null = null;
  #disabled = false;
  #closed = false;
  #serializations = new WeakMap<object, Serialization>();
  #pending = new Map<object, PendingAssociation>();
  #prepared = new Map<object, { environment: object; pending: PendingAssociation; next: PipelineBoundary; entry: Serialization }>();
  #current: { environment: object; battle: Battle; parent: PipelineBoundary; entry: Serialization;
    rows: AssociationRows; handles: NativeObjectHandle[]; evidence: NativeObjectEvidence[] } | null = null;
  readonly #birth: NativeBirthEnrollment;
  constructor(birth: NativeBirthEnrollment) { this.#birth = birth; }
  bindInitial(environment: object): void {
    if (this.#initialEnvironment || this.#closed) associationFail('duplicate-initial-environment');
    this.#initialEnvironment = environment;
  }
  disableLegacy(environment: object): void {
    if (environment !== this.#initialEnvironment || this.#current) associationFail('invalid-legacy-abandonment');
    this.#disabled = true;
  }
  private ensure(): void { if (this.#closed || this.#disabled) associationFail('unavailable'); }

  /** Called with the actual native serialization before/after the existing snapshot clone. */
  recordSerialization(environment: object, battle: Battle, raw: Record<string, unknown>, snapshot: SeededBattleSnapshot): void {
    if (this.#disabled) return;
    this.ensure();
    const pending = this.#pending.get(environment);
    const rows = this.#current?.environment === environment ? this.#current.rows : pending?.rows
      ?? (environment === this.#initialEnvironment && !this.#current ? this.#birth.captureBirthObjects(environment, battle) : undefined);
    const expectedBattle = this.#current?.environment === environment ? this.#current.battle : pending?.battle;
    if (!rows || (expectedBattle && battle !== expectedBattle)) associationFail('missing-authoritative-objects');
    const rawRefs = stateRefs(raw), order = {} as Record<PlayerID, readonly number[]>;
    for (const owner of owners) {
      const side = battle[owner]!, slotObjects = rows[owner].objects, serialized = rawRefs.rows[index(owner)];
      if (!side || side.pokemon.length !== slotObjects.length || new Set(side.pokemon).size !== slotObjects.length) associationFail('source-object-mismatch');
      const slots = side.pokemon.map(p => slotObjects.indexOf(p) + 1);
      if (slots.some(slot => !slot) || new Set(slots).size !== slots.length) associationFail('source-object-mismatch');
      const encoding = new Array(slots.length);
      slots.forEach((slot, i) => { encoding[slot - 1] = i + 1; });
      if (serialized.side.id !== owner || serialized.entries.length !== slots.length
        || serialized.side.team !== encoding.join(slots.length > 9 ? ',' : '')
        || !side.pokemon.every((p, i) => serialized.sets[i] === p.set && side.team[slots[i] - 1] === p.set)) associationFail('serializer-association-mismatch');
      order[owner] = Object.freeze(slots);
    }
    if (!isDeepStrictEqual(raw, snapshot.simulator_state)) associationFail('snapshot-clone-mismatch');
    const refs = stateRefs(snapshot.simulator_state);
    if (new Set(refs.rows.flatMap(row => row.sets)).size !== refs.rows.reduce((n, row) => n + row.sets.length, 0)) associationFail('duplicate-snapshot-set');
    this.#serializations.set(snapshot, { snapshot, expected: structuredClone(snapshot), refs, environment, battle, rows, order });
  }
  /** Actual env transition-builder handoff; preserve the held serialization occurrence across its root/clone. */
  finalizeSerialization(environment: object, source: SeededBattleSnapshot, target: SeededBattleSnapshot): void {
    if (this.#disabled) return;
    this.ensure(); const entry = this.#serializations.get(source);
    if (!entry || entry.environment !== environment) associationFail('missing-builder-source-occurrence');
    this.checkSnapshot(entry);
    if (!isDeepStrictEqual(source.simulator_state, target.simulator_state)) associationFail('builder-state-transfer-mismatch');
    this.#serializations.set(target, { ...entry, snapshot: target, expected: structuredClone(target), refs: stateRefs(target.simulator_state) });
  }

  private checkSnapshot(entry: Serialization): void {
    if (!refsUnchanged(entry.refs, entry.snapshot.simulator_state)) associationFail('snapshot-reference-mismatch');
    if (!isDeepStrictEqual(entry.snapshot, entry.expected)) associationFail('snapshot-content-mismatch');
  }
  commitInitial(environment: object, parent: PipelineBoundary, snapshot: SeededBattleSnapshot): void {
    this.ensure(); const entry = this.#serializations.get(snapshot);
    if (this.#current || environment !== this.#initialEnvironment || !entry || entry.environment !== environment) associationFail('missing-initial-serialization');
    this.checkSnapshot(entry);
    for (const owner of owners) if (this.#birth.read(this.#birth.holding(owner), owner).original !== entry.rows[owner].original) associationFail('original-holder-mismatch');
    this.install(environment, parent, entry);
  }
  private install(environment: object, parent: PipelineBoundary, entry: Serialization): void {
    const evidence = owners.map(owner => Object.freeze({ owner, original: entry.rows[owner].original,
      original_slots: Object.freeze([...entry.order[owner]]), observation_id: parent.perspectives[owner].observation.observation_id,
      branch_id: parent.branch_id, step_index: parent.step_index }));
    this.#current = { environment, battle: entry.battle, parent, entry, rows: entry.rows,
      handles: owners.map(() => Object.freeze(Object.create(null))), evidence };
  }
  prepareRestore(environment: object, parent: PipelineBoundary, snapshot: SeededBattleSnapshot): NativeRestoreTicket {
    this.ensure(); const current = this.#current;
    if (!current || parent !== current.parent) associationFail('foreign-or-missing-parent');
    if (snapshot !== current.entry.snapshot) associationFail('foreign-serialization-occurrence');
    if (environment === current.environment || this.#pending.has(environment)) associationFail('reused-candidate');
    this.checkSnapshot(current.entry);
    const ticket = Object.freeze(Object.create(null));
    this.#pending.set(environment, { ticket, parent, source: current.entry }); return ticket;
  }
  private pending(environment: object, ticket?: NativeRestoreTicket): PendingAssociation {
    this.ensure(); const pending = this.#pending.get(environment);
    if (!pending || ticket !== pending.ticket || pending.parent !== this.#current?.parent) associationFail('foreign-or-stale-restore-ticket');
    return pending;
  }
  /** Read-only admission of the already held pending B2 chain, before any clone or native probe. */
  assertRestoreAdmission(environment: object, serialized: Record<string, unknown>, ticket?: NativeRestoreTicket): void {
    const pending = this.pending(environment, ticket);
    this.checkSnapshot(pending.source);
    if (pending.source !== this.#current?.entry || serialized !== pending.source.snapshot.simulator_state
      || pending.input || pending.battle) associationFail('restore-admission-mismatch');
  }
  beforeRestore(environment: object, serialized: Record<string, unknown>, input: Record<string, unknown>, ticket?: NativeRestoreTicket): void {
    if (this.#disabled) return;
    const pending = this.pending(environment, ticket);
    this.checkSnapshot(pending.source);
    if (serialized !== pending.source.snapshot.simulator_state || pending.input || !isDeepStrictEqual(input, this.nativeState(pending.source.snapshot.simulator_state))) associationFail('restore-input-mismatch');
    pending.input = stateRefs(input);
  }
  // Env-only overlays never form native set association evidence.
  private nativeState(state: Record<string, unknown>): Record<string, unknown> {
    const { __neural_terminal_request_history: _terminal, __neural_active_request_overrides: _active, ...native } = state;
    return native;
  }
  acceptRestore(environment: object, input: Record<string, unknown>, battle: Battle, ticket?: NativeRestoreTicket): void {
    if (this.#disabled) return;
    const pending = this.pending(environment, ticket), refs = pending.input;
    if (!refs || !refsUnchanged(refs, input) || pending.battle) associationFail('reconstruction-input-occurrence-mismatch');
    const rows = {} as AssociationRows;
    const oldObjects = new Set(owners.flatMap(owner => [...pending.source.rows[owner].objects]));
    const fresh = new Set<object>();
    for (const owner of owners) {
      const side = battle[owner]!, serialized = refs.rows[index(owner)], slots = pending.source.order[owner];
      if (!side || side.pokemon.length !== slots.length || serialized.entries.length !== slots.length) associationFail('reconstructed-object-mismatch');
      const objects = new Array(slots.length);
      side.pokemon.forEach((pokemon, i) => {
        if (oldObjects.has(pokemon) || fresh.has(pokemon) || pokemon.side !== side || pokemon.set !== serialized.sets[i]
          || side.team[slots[i] - 1] !== serialized.sets[i]) associationFail('reconstructed-object-mismatch');
        objects[slots[i] - 1] = pokemon; fresh.add(pokemon);
      });
      rows[owner] = { original: pending.source.rows[owner].original, objects: Object.freeze(objects) };
    }
    pending.rows = rows; pending.battle = battle;
  }
  prepareCommit(environment: object, next: PipelineBoundary, snapshot: SeededBattleSnapshot, ticket: NativeRestoreTicket): object {
    const pending = this.pending(environment, ticket), entry = this.#serializations.get(snapshot);
    if (!pending.rows || !entry || entry.environment !== environment || entry.battle !== pending.battle || entry.rows !== pending.rows) associationFail('missing-prepared-association');
    this.checkSnapshot(entry);
    const token = Object.freeze(Object.create(null)); this.#prepared.set(token, { environment, pending, next, entry }); return token;
  }
  commit(token: object): void {
    this.ensure(); const prepared = this.#prepared.get(token);
    if (!prepared || this.#pending.get(prepared.environment) !== prepared.pending || prepared.pending.parent !== this.#current?.parent) associationFail('foreign-or-stale-preparation');
    this.install(prepared.environment, prepared.next, prepared.entry);
    this.discard(prepared.environment);
  }
  discard(environment: object): void {
    this.#pending.delete(environment);
    for (const [token, prepared] of this.#prepared) if (prepared.environment === environment) this.#prepared.delete(token);
  }
  release(environment: object): void {
    this.discard(environment);
    if (this.#current?.environment === environment) this.revoke();
  }
  holding(owner: PlayerID): NativeObjectHandle {
    const slot = index(owner); this.ensure(); if (!this.#current) associationFail('unavailable'); return this.#current.handles[slot];
  }
  read(handle: NativeObjectHandle, owner: PlayerID): NativeObjectEvidence {
    const slot = index(owner); this.ensure();
    if (!this.#current || handle !== this.#current.handles[slot]) associationFail('foreign-or-forged-holding');
    return this.#current.evidence[slot];
  }
  revoke(): void {
    this.#closed = true; this.#current = null; this.#pending.clear(); this.#prepared.clear(); this.#serializations = new WeakMap();
  }
}


/** Policy decisions only: supplied strings never enroll a native world or authorize reconstruction. */
export function snapshotRestorePolicy(packageVersion: string): 'legacy' | 'held-b2-required' {
  if (packageVersion === '0.11.10') return 'legacy';
  if (packageVersion === '0.11.11') return 'held-b2-required';
  throw new Error('snapshot-admission/v1/unsupported-runtime');
}
export function assertBeliefForkPolicy(packageVersion: string): void {
  if (snapshotRestorePolicy(packageVersion) !== 'legacy') throw new Error('snapshot-admission/v1/belief-fork-unsupported');
}
