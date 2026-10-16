import type { PlayerID } from './types';

const SUBMITTED_FIELDS = ['name', 'species', 'item', 'ability', 'moves', 'nature', 'evs', 'gender',
  'ivs', 'shiny', 'level', 'happiness', 'hpType', 'pokeball', 'gigantamax', 'dynamaxLevel', 'teraType'] as const;
export type OriginalOwnerHandle = Readonly<object>;
export interface OriginalOwnerEvidence {
  readonly owner: PlayerID;
  readonly labels: Readonly<{ battle_id: string; format: string; simulator_revision: string }>;
  readonly raw_team: readonly unknown[];
  readonly packed_team: string;
  readonly creation_sequence: 0;
  readonly creation_cursor: 0;
  readonly field_presence: readonly Readonly<Record<string, 'present' | 'undefined' | 'omitted'>>[];
  readonly non_submitted_fields: readonly Readonly<{ generator_metadata: readonly PropertyKey[]; unsupported: readonly PropertyKey[] }>[];
}

function fail(message: string): never { throw new Error(`original-owner/v1/${message}`); }
function ownerIndex(owner: PlayerID): number {
  if (owner !== 'p1' && owner !== 'p2') fail('invalid-owner');
  return owner === 'p1' ? 0 : 1;
}

// Raw generator data, including own undefined and non-enumerable properties,
// cannot pass through JSON or the lossy packer to establish originals.
function detach<T>(value: T, seen = new Map<object, object>()): T {
  if (typeof value === 'function') fail('unsupported-raw-value');
  if (value === null || typeof value !== 'object') return value;
  const prior = seen.get(value);
  if (prior) return prior as T;
  const proto = Object.getPrototypeOf(value);
  if (!Array.isArray(value) && proto !== Object.prototype && proto !== null) fail('unsupported-raw-object');
  const copy = Array.isArray(value) ? [] : Object.create(proto);
  seen.set(value, copy);
  for (const key of Reflect.ownKeys(value)) {
    if (Array.isArray(value) && key === 'length') continue;
    const property = Object.getOwnPropertyDescriptor(value, key)!;
    if (!('value' in property)) fail('unsupported-raw-accessor');
    Object.defineProperty(copy, key, { value: detach(property.value, seen), enumerable: property.enumerable,
      writable: true, configurable: true });
  }
  if (Array.isArray(value)) copy.length = value.length;
  return copy;
}
function freeze<T>(value: T, seen = new Set<object>()): T {
  if (value === null || typeof value !== 'object' || seen.has(value)) return value;
  seen.add(value);
  for (const key of Reflect.ownKeys(value)) freeze((value as any)[key], seen);
  return Object.freeze(value);
}

/** Internal, process-local creation controller. Never carried by wire APIs. */
export class OriginalOwnerCreation {
  #phase: 'new' | 'capturing' | 'staged' | 'active' | 'restored_without_originals' | 'invalid' = 'new';
  #environment: object | null = null;
  #raw: (readonly unknown[] | undefined)[] = [];
  #evidence: (OriginalOwnerEvidence | undefined)[] = [];
  #handles: OriginalOwnerHandle[] = [];
  #knowledgeReceiver: ((environment: object, occurrence: object, rows: readonly OriginalOwnerEvidence[]) => void) | null = null;
  #knowledgeEnvironment: object | null = null;
  #knowledgeOccurrence: object | null = null;
  registerKnowledgeReceiver(receiver: (environment: object, occurrence: object, rows: readonly OriginalOwnerEvidence[]) => void): void {
    if (this.#phase !== 'new' || this.#knowledgeReceiver || typeof receiver !== 'function') fail('knowledge-receiver-registration');
    this.#knowledgeReceiver = receiver;
  }
  assertKnowledgeEnrollment(environment: object, occurrence: object, rows: readonly OriginalOwnerEvidence[]): void {
    if (!['staged', 'active'].includes(this.#phase) || environment !== this.#knowledgeEnvironment
      || occurrence !== this.#knowledgeOccurrence || rows.length !== 2 || rows.some((row, i) => row !== this.#evidence[i])) fail('foreign-knowledge-enrollment');
  }
  readonly #labels: OriginalOwnerEvidence['labels'];

  constructor(labels: OriginalOwnerEvidence['labels']) { this.#labels = freeze(detach(labels)); }
  bind(environment: object): void {
    if (this.#phase !== 'new' || this.#environment) fail('duplicate-enrollment');
    this.#environment = environment;
  }
  begin(environment: object): void {
    if (this.#phase !== 'new' || this.#environment !== environment) fail('duplicate-or-foreign-creation');
    this.#phase = 'capturing';
    this.#knowledgeEnvironment = environment; this.#knowledgeOccurrence = Object.freeze(Object.create(null));
  }
  capture<T extends unknown[]>(environment: object, owner: PlayerID, generated: T): T {
    const index = ownerIndex(owner);
    if (this.#phase !== 'capturing' || this.#environment !== environment || this.#raw[index]) fail('invalid-capture');
    if (!Array.isArray(generated) || !generated.length || generated.some(set => !set || typeof set !== 'object' || Array.isArray(set))) fail('invalid-team');
    this.#raw[index] = freeze(detach(generated));
    return detach(generated);
  }
  associate(environment: object, owner: PlayerID, packed: string): void {
    const index = ownerIndex(owner), raw = this.#raw[index];
    if (this.#phase !== 'capturing' || this.#environment !== environment || !raw || this.#evidence[index]) fail('invalid-association');
    if (typeof packed !== 'string' || !packed) fail('invalid-packed-team');
    const field_presence = raw.map(set => Object.fromEntries(SUBMITTED_FIELDS.map(field => [field,
      !Object.hasOwn(set as object, field) ? 'omitted' as const : (set as any)[field] === undefined ? 'undefined' as const : 'present' as const])));
    const non_submitted_fields = raw.map(set => ({
      generator_metadata: Object.hasOwn(set as object, 'role') ? ['role'] : [],
      unsupported: Reflect.ownKeys(set as object).filter(key => key !== 'role' && !SUBMITTED_FIELDS.includes(key as any)),
    }));
    this.#evidence[index] = freeze({ owner, labels: this.#labels, raw_team: raw, packed_team: packed,
      creation_sequence: 0, creation_cursor: 0, field_presence, non_submitted_fields });
    if (this.#evidence[0] && this.#evidence[1]) {
      this.#phase = 'staged';
      this.#knowledgeReceiver?.(this.#knowledgeEnvironment!, this.#knowledgeOccurrence!, Object.freeze([...this.#evidence] as OriginalOwnerEvidence[]));
    }
  }
  diagnostic(environment: object, owner: PlayerID): OriginalOwnerEvidence {
    const row = this.#evidence[ownerIndex(owner)];
    if (this.#phase !== 'staged' || this.#environment !== environment || !row) fail('not-staged');
    return row;
  }
  abandonForRestore(environment: object): void {
    if (this.#phase !== 'new' || this.#environment !== environment) fail('creation-restore-forbidden');
    this.revoke();
    this.#phase = 'restored_without_originals';
  }
  activate(): boolean {
    // Preserve the legacy unstarted restore path without minting originals.
    if (this.#phase === 'restored_without_originals') return false;
    if (this.#phase !== 'staged') fail('not-staged');
    this.#handles = [Object.freeze(Object.create(null)), Object.freeze(Object.create(null))];
    this.#phase = 'active';
    this.#environment = null;
    this.#raw = [];
    return true;
  }
  holding(owner: PlayerID): OriginalOwnerHandle {
    const index = ownerIndex(owner);
    if (this.#phase !== 'active') fail('inactive');
    return this.#handles[index];
  }
  read(handle: OriginalOwnerHandle, owner: PlayerID, packed?: string): OriginalOwnerEvidence {
    const index = ownerIndex(owner);
    if (this.#phase !== 'active' || handle !== this.#handles[index]) fail('foreign-or-forged-holding');
    const row = this.#evidence[index]!;
    if (packed !== undefined && packed !== row.packed_team) fail('packed-association-mismatch');
    return row;
  }
  abortStaging(): void { if (this.#phase !== 'active') this.revoke(); }
  revoke(): void {
    this.#knowledgeReceiver = null; this.#knowledgeEnvironment = null; this.#knowledgeOccurrence = null;
    this.#phase = 'invalid'; this.#environment = null; this.#raw = []; this.#evidence = []; this.#handles = [];
  }
}
